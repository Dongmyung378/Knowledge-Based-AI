"""Build a byte-verified source distribution from a Git working checkout."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
REPO = PROJECT.parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def files_in_checkout():
    output = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=REPO)
    files = sorted(set(name for name in output.decode('utf-8').split('\0') if name))
    return [name for name in files if not (name.startswith('downloads/') and name.endswith(('.zip', '.sha256')))]


def initial_record():
    provenance = json.loads((PROJECT / 'legacy/initial-provenance.json').read_text(encoding='utf-8'))
    snapshot_path = PROJECT / provenance['snapshot']
    with zipfile.ZipFile(snapshot_path) as archive:
        if archive.testzip():
            raise ValueError('Initial snapshot CRC failed')
        shared = {record['path'] for record in provenance['shared_reference_files']}
        for record in provenance['files']:
            data = (PROJECT / record['path']).read_bytes() if record['path'] in shared else archive.read(record['path'])
            if sha(data) != record['sha256']:
                raise ValueError(f'Initial payload no longer matches: {record["path"]}')
        old_attribute_source = archive.read('learning/attr_learner.py').decode('utf-8').replace('\r\n', '\n')
        current_attribute_source = (PROJECT / 'learning/attr_learner.py').read_text(encoding='utf-8')
        if not current_attribute_source.startswith(old_attribute_source):
            raise ValueError('Preserved initial DTL source prefix changed')
        historical_reports = [name for name in archive.namelist() if name.startswith('docs/experiment-report')]
        for name in historical_reports:
            if (PROJECT / name).read_bytes() != archive.read(name):
                raise ValueError('Historical experiment report was modified')
    receipt = {'schema_version': 1, 'initial_git_commit': provenance['git_commit'],
               'initial_payloads_verified': len(provenance['files']), 'snapshot_payloads': len(provenance['files']) - len(shared),
               'unchanged_shared_reference_pdfs': len(shared), 'initial_dtl_source_prefix_preserved': True,
               'historical_experiment_reports_byte_identical': historical_reports,
               'scope': 'Initial source and records are retrieved byte-for-byte from the preserved source ZIP or the unchanged shared reference PDFs. New variants are appended after the initial DTL code.'}
    path = PROJECT / 'reports/source-preservation.json'
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8', newline='\n')
    return {'path': provenance['snapshot'], 'sha256': sha(snapshot_path.read_bytes()),
            'size_bytes': snapshot_path.stat().st_size, 'git_commit': provenance['git_commit']}


def build(output):
    output = Path(output).resolve()
    if output.suffix != '.zip':
        raise ValueError('Choose a .zip output file')
    if output.is_relative_to(PROJECT):
        raise ValueError('Place release ZIPs outside the project payload, such as repository downloads/')
    snapshot = initial_record()
    manifest_path = PROJECT / 'release-manifest.json'
    prefix = 'projects/symbolic-machine-learning/'
    files = []
    for name in files_in_checkout():
        if name.startswith(prefix) and name != prefix + 'release-manifest.json':
            path = REPO / name
            files.append({'path': name[len(prefix):], 'sha256': sha(path.read_bytes()), 'size_bytes': path.stat().st_size})
    manifest = {'schema_version': 1, 'source_version': '1', 'files': files, 'initial_snapshot': snapshot,
                'scope': 'Declared symbolic-learning project payloads. The source ZIP also retains the repository companion projects; the manifest does not claim to validate their optional runtimes.'}
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8', newline='\n')
    from verify_release import verify_directory, verify_archive
    verified = verify_directory(PROJECT, 'release-manifest.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in files_in_checkout():
            info = zipfile.ZipInfo('Knowledge-Based-AI/' + name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, (REPO / name).read_bytes(), compresslevel=9)
    checked_zip = verify_archive(output, None, 'release-manifest.json')
    archive_hash = sha(output.read_bytes())
    output.with_suffix('.sha256').write_text(f'{archive_hash}  {output.name}\n', encoding='ascii', newline='\n')
    print(json.dumps({'status': 'passed', 'payload_files': verified['payload_files'],
                      'archive_bytes': output.stat().st_size, 'archive_sha256': archive_hash,
                      'archive_prefix': checked_zip['archive_prefix']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build(args.output)
