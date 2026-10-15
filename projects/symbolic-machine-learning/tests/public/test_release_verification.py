"""Release integrity checks using independent small directory/ZIP fixtures."""

from copy import deepcopy
import hashlib
import io
import json
import stat
import struct
import zipfile

import pytest

from tools.verify_release import (
    VerificationError, inspect_zip, safe_path, verify, verify_archive, verify_directory,
)


MANIFEST = "release-manifest.json"


def zip_bytes(entries):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, data in entries:
            archive.writestr(name, data)
    return output.getvalue()


def record(path, data):
    return {"path": path, "size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def release():
    payloads = {"README.md": b"A portable release.\n",
                "legacy/initial-source.zip": zip_bytes([("learning/initial.py", b"print('initial')\n")])}
    records = [record(name, data) for name, data in payloads.items()]
    initial = dict(records[1], git_commit="a" * 40)
    return payloads, {"schema_version": 1, "files": records, "initial_snapshot": initial}


def write_directory(root, payloads, manifest):
    root.mkdir(parents=True, exist_ok=True)
    for name, data in payloads.items():
        destination = root / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    (root / MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")


def write_archive(path, payloads, manifest, prefix=""):
    base = prefix + "/" if prefix else ""
    path.write_bytes(zip_bytes([(base + name, data) for name, data in payloads.items()]
                               + [(base + MANIFEST, json.dumps(manifest).encode())]))


def test_valid_directory_verifies_payloads_and_the_preserved_source(tmp_path):
    payloads, manifest = release()
    write_directory(tmp_path, payloads, manifest)
    result = verify_directory(tmp_path, MANIFEST)
    assert result == {"schema_version": 1, "passed": True, "payload_files": 2,
                      "initial_source_files": 1, "initial_git_commit": "a" * 40}


def test_zip_manifest_at_archive_root_is_discovered(tmp_path):
    payloads, manifest = release()
    destination = tmp_path / "release.zip"
    write_archive(destination, payloads, manifest)
    result = verify_archive(destination, None, MANIFEST)
    assert result["passed"] and result["archive_prefix"] == ""


def test_zip_nested_project_prefix_is_discovered(tmp_path):
    payloads, manifest = release()
    destination = tmp_path / "release.zip"
    write_archive(destination, payloads, manifest, "repository/projects/symbolic")
    result = verify_archive(destination, None, MANIFEST)
    assert result["passed"] and result["archive_prefix"] == "repository/projects/symbolic"


def test_ambiguous_manifests_require_an_explicit_archive_prefix(tmp_path):
    payloads, manifest = release()
    files = []
    for prefix in ("first", "second"):
        files.extend((prefix + "/" + name, data) for name, data in payloads.items())
        files.append((prefix + "/" + MANIFEST, json.dumps(manifest).encode()))
    destination = tmp_path / "release.zip"
    destination.write_bytes(zip_bytes(files))
    with pytest.raises(VerificationError, match="uniquely"):
        verify_archive(destination, None, MANIFEST)
    assert verify_archive(destination, "second", MANIFEST)["passed"]


def test_payload_bytes_and_declared_size_tampering_are_detected(tmp_path):
    payloads, original = release()
    for change in ("content", "size"):
        manifest = deepcopy(original)
        changed = dict(payloads)
        if change == "content":
            changed["README.md"] = b"B portable release.\n"  # Same length, different digest.
        else:
            manifest["files"][0]["size_bytes"] += 1
        root = tmp_path / change
        write_directory(root, changed, manifest)
        with pytest.raises(VerificationError, match="hash or size mismatch"):
            verify_directory(root, MANIFEST)


def test_missing_declared_payload_is_rejected_for_directory_and_zip(tmp_path):
    payloads, manifest = release()
    del payloads["README.md"]
    write_directory(tmp_path / "directory", payloads, manifest)
    with pytest.raises(VerificationError, match="Missing"):
        verify_directory(tmp_path / "directory", MANIFEST)
    destination = tmp_path / "release.zip"
    write_archive(destination, payloads, manifest)
    with pytest.raises(VerificationError, match="Missing"):
        verify_archive(destination, None, MANIFEST)


def test_manifest_duplicate_paths_and_case_aliases_are_rejected():
    payloads, original = release()
    for duplicate in ("README.md", "readme.MD"):
        manifest = deepcopy(original)
        manifest["files"].append(record(duplicate, payloads["README.md"]))
        with pytest.raises(VerificationError, match="Duplicate"):
            verify(manifest, payloads.__getitem__)


def test_manifest_cannot_declare_itself_even_with_different_case():
    payloads, manifest = release()
    manifest["files"].append(record("RELEASE-MANIFEST.JSON", b""))
    with pytest.raises(VerificationError, match="self-referential"):
        verify(manifest, payloads.__getitem__)


def test_traversal_absolute_paths_and_ambiguous_separators_are_rejected():
    for path in ("../secret", "/absolute", "C:/absolute", "a\\b", "a//b", "a/./b",
                 "a/../b", "a/", "x\x00y", "x\ny", "README.md:stream"):
        with pytest.raises(VerificationError):
            safe_path(path)


def test_windows_device_names_trailing_dots_spaces_and_reserved_characters_are_rejected():
    for path in ("CON", "aux.txt", "NUL/a.txt", "COM1.md", "LPT9", "COM\u00b9.log",
                 "CONIN$", "name.", "name ", "dir /a", "a?b", "a|b", 'a"b'):
        with pytest.raises(VerificationError):
            safe_path(path)
    assert safe_path("comparison/COM10.md") == "comparison/COM10.md"


def test_zip_case_aliases_and_file_directory_aliases_are_rejected():
    for entries in (([('README', b'one'), ('readme', b'two')]),
                    ([('folder/', b''), ('folder', b'file')])):
        with zipfile.ZipFile(io.BytesIO(zip_bytes(entries))) as archive:
            with pytest.raises(VerificationError, match="Duplicate"):
                inspect_zip(archive)


def test_preserved_initial_zip_must_not_contain_traversal_or_symlinks():
    payloads, original = release()
    link = zipfile.ZipInfo("link.py")
    link.create_system = 3
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    for entry in (("../escape.py", b"outside"), (link, b"target.py")):
        manifest = deepcopy(original)
        payloads["legacy/initial-source.zip"] = zip_bytes([entry])
        updated = record("legacy/initial-source.zip", payloads["legacy/initial-source.zip"])
        manifest["files"][1] = updated
        manifest["initial_snapshot"].update(updated)
        with pytest.raises(VerificationError):
            verify(manifest, payloads.__getitem__)


def test_directory_payload_symlink_is_rejected_even_when_target_stays_inside(tmp_path):
    payloads, manifest = release()
    write_directory(tmp_path, payloads, manifest)
    target = tmp_path / "actual-readme.txt"
    target.write_bytes(payloads["README.md"])
    link = tmp_path / "README.md"
    link.unlink()
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("This Windows account cannot create symlinks; ZIP symlink rejection is still tested.")
    with pytest.raises(VerificationError, match="symlinks"):
        verify_directory(tmp_path, MANIFEST)


def test_symlink_in_a_payload_parent_directory_is_rejected(tmp_path):
    payloads, manifest = release()
    write_directory(tmp_path, payloads, manifest)
    directory = tmp_path / "real"
    directory.mkdir()
    (directory / "data.txt").write_bytes(b"content")
    manifest["files"].append(record("alias/data.txt", b"content"))
    (tmp_path / MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")
    try:
        (tmp_path / "alias").symlink_to(directory, target_is_directory=True)
    except OSError:
        pytest.skip("This Windows account cannot create directory symlinks.")
    with pytest.raises(VerificationError, match="symlinks"):
        verify_directory(tmp_path, MANIFEST)


def test_boolean_schema_version_and_duplicate_json_keys_are_rejected(tmp_path):
    payloads, manifest = release()
    invalid = dict(manifest, schema_version=True)
    with pytest.raises(VerificationError, match="schema_version"):
        verify(invalid, payloads.__getitem__)
    write_directory(tmp_path, payloads, manifest)
    encoded = json.dumps(manifest)
    (tmp_path / MANIFEST).write_text('{"schema_version": 1, ' + encoded[1:], encoding="utf-8")
    with pytest.raises(VerificationError, match="Duplicate JSON"):
        verify_directory(tmp_path, MANIFEST)
    (tmp_path / MANIFEST).write_bytes(b"\xff\xffinvalid-json")
    with pytest.raises(VerificationError, match="Unicode JSON"):
        verify_directory(tmp_path, MANIFEST)


def test_zip_crc_damage_is_detected_before_payload_acceptance(tmp_path):
    payloads, manifest = release()
    destination = tmp_path / "release.zip"
    write_archive(destination, payloads, manifest)
    data = bytearray(destination.read_bytes())
    with zipfile.ZipFile(destination) as archive:
        info = archive.getinfo("README.md")
        filename_size, extra_size = struct.unpack_from("<HH", data, info.header_offset + 26)
        payload_offset = info.header_offset + 30 + filename_size + extra_size
    data[payload_offset] ^= 1
    destination.write_bytes(data)
    with pytest.raises(VerificationError, match="CRC"):
        verify_archive(destination, None, MANIFEST)
