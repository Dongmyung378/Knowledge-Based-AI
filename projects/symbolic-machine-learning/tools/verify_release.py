"""Verify declared release payloads and the preserved initial source snapshot."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import stat
import unicodedata
import zipfile


class VerificationError(ValueError):
    """A manifest, path, archive or payload violated the release contract."""


def safe_path(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise VerificationError("Manifest paths must be nonempty relative POSIX paths.")
    path = PurePosixPath(value)
    if path.is_absolute() or ":" in value or any(part in ("", ".", "..") for part in value.split("/")):
        raise VerificationError("Unsafe relative path in manifest or ZIP.")
    for part in path.parts:
        if (part.endswith((" ", ".")) or any(ord(char) < 32 or ord(char) == 127 for char in part)
                or any(char in '<>"|?*' for char in part)):
            raise VerificationError("Paths must use portable Windows/Linux file names.")
        device = part.split(".", 1)[0].upper()
        if (device in {"CON", "PRN", "AUX", "NUL", "CLOCK$", "CONIN$", "CONOUT$"}
                or re.fullmatch(r"(?:COM|LPT)[1-9\u00b9\u00b2\u00b3]", device)):
            raise VerificationError("Windows reserved device names are unsupported.")
    return str(path)


def path_key(value: str) -> str:
    """Treat case and canonical Unicode aliases as one portable payload path."""
    return unicodedata.normalize("NFC", value).casefold()


def load_manifest(data: bytes) -> dict:
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise VerificationError("Duplicate JSON object key in manifest.")
            result[key] = value
        return result
    try:
        return json.loads(data, object_pairs_hook=unique_object)
    except UnicodeDecodeError as exc:
        raise VerificationError("Manifest must contain valid Unicode JSON.") from exc


def check_record(record: dict, data: bytes) -> None:
    digest = record.get("sha256", "")
    size = record.get("size_bytes")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise VerificationError("Invalid SHA-256 in manifest.")
    if isinstance(size, bool) or not isinstance(size, int) or size < 0:
        raise VerificationError("Invalid size_bytes in manifest.")
    if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
        raise VerificationError(f"Payload hash or size mismatch: {record['path']}")


def inspect_zip(archive: zipfile.ZipFile) -> None:
    names = set()
    for info in archive.infolist():
        name = safe_path(info.filename[:-1] if info.is_dir() else info.filename)
        key = path_key(name)
        if key in names:
            raise VerificationError("Duplicate ZIP member name.")
        names.add(key)
        if stat.S_ISLNK(info.external_attr >> 16) or info.external_attr & 0x400:
            raise VerificationError("ZIP symlinks are unsupported.")
    if archive.testzip() is not None:
        raise VerificationError("ZIP CRC verification failed.")


def verify(manifest: dict, reader, *, manifest_name: str = "release-manifest.json") -> dict:
    manifest_name = safe_path(manifest_name)
    if (not isinstance(manifest, dict) or type(manifest.get("schema_version")) is not int
            or manifest["schema_version"] != 1 or not isinstance(manifest.get("files"), list)):
        raise VerificationError("Expected schema_version 1 and a files list.")
    names = set()
    portable_names = set()
    for record in manifest["files"]:
        if not isinstance(record, dict):
            raise VerificationError("Every file record must be an object.")
        name = safe_path(record.get("path"))
        key = path_key(name)
        if key in portable_names or key == path_key(manifest_name):
            raise VerificationError("Duplicate or self-referential manifest entry.")
        names.add(name)
        portable_names.add(key)
        check_record(record, reader(name))
    initial = manifest.get("initial_snapshot")
    if not isinstance(initial, dict):
        raise VerificationError("initial_snapshot must identify the preserved initial ZIP.")
    initial_path = safe_path(initial.get("path"))
    if initial_path not in names:
        raise VerificationError("Initial snapshot must also appear in files.")
    commit = initial.get("git_commit", "")
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise VerificationError("Initial snapshot requires its full Git commit.")
    data = reader(initial_path)
    check_record(initial, data)
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            inspect_zip(archive)
            source_count = len([member for member in archive.infolist() if not member.is_dir()])
            if source_count == 0:
                raise VerificationError("Initial snapshot contains no source payload.")
    except zipfile.BadZipFile as exc:
        raise VerificationError("Initial snapshot is not a readable ZIP.") from exc
    return {
        "schema_version": 1,
        "passed": True,
        "payload_files": len(names),
        "initial_source_files": source_count,
        "initial_git_commit": commit,
    }


def verify_directory(project: Path, manifest_name: str) -> dict:
    project = project.resolve(strict=True)
    manifest_name = safe_path(manifest_name)

    def reader(name):
        target = project
        try:
            for part in PurePosixPath(name).parts:
                target = target / part
                attributes = getattr(target.lstat(), "st_file_attributes", 0)
                if target.is_symlink() or attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
                    raise VerificationError("Payload symlinks and reparse points are unsupported.")
            resolved = target.resolve(strict=True)
            if (not resolved.is_relative_to(project)
                    or path_key(resolved.relative_to(project).as_posix()) != path_key(name)):
                raise VerificationError("Payload resolves outside the project or through a path alias.")
            return target.read_bytes()
        except OSError as exc:
            raise VerificationError("Missing or unreadable release payload.") from exc

    manifest = load_manifest(reader(manifest_name))
    return verify(manifest, reader, manifest_name=manifest_name)


def verify_archive(path: Path, prefix: str | None, manifest_name: str) -> dict:
    manifest_name = safe_path(manifest_name)
    with zipfile.ZipFile(path) as archive:
        inspect_zip(archive)
        if prefix is None:
            candidates = [name for name in archive.namelist() if name == manifest_name or name.endswith("/" + manifest_name)]
            if len(candidates) != 1:
                raise VerificationError("Could not uniquely find the release manifest; use --prefix.")
            manifest_path = candidates[0]
            prefix = manifest_path[:-len(manifest_name)].rstrip("/")
        else:
            prefix = safe_path(prefix) if prefix else ""
        base = prefix + "/" if prefix else ""

        def reader(name):
            try:
                return archive.read(base + safe_path(name))
            except KeyError as exc:
                raise VerificationError("Missing declared ZIP payload.") from exc

        manifest = load_manifest(reader(manifest_name))
        result = verify(manifest, reader, manifest_name=manifest_name)
        result["archive_prefix"] = prefix
        return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--manifest", default="release-manifest.json", help="Project-relative manifest path.")
    parser.add_argument("--zip", type=Path, dest="archive", help="Verify inside a source ZIP without extracting it.")
    parser.add_argument("--prefix", help="Project directory inside the ZIP; otherwise discover its manifest.")
    args = parser.parse_args(argv)
    if args.prefix is not None and args.archive is None:
        parser.error("--prefix requires --zip")
    try:
        result = (verify_archive(args.archive, args.prefix, args.manifest) if args.archive
                  else verify_directory(args.project, args.manifest))
    except (VerificationError, OSError, KeyError, TypeError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        # Do not print host paths, tracebacks or secrets from machine-local errors.
        message = str(exc) if isinstance(exc, VerificationError) else type(exc).__name__
        print(json.dumps({"passed": False, "error": message}))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
