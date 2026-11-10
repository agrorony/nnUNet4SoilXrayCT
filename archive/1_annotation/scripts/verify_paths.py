"""verify_paths.py — generalized manifest-driven existence checker (S11).

Replaces the old repo-root `_verify_i2_paths.py`, which hardcoded a 6-entry
dict of {name: path} checks for one specific iteration (fresh_bnei_reem_i2).
This version reads the checks from a YAML manifest so it can be reused for
any iteration without editing code.

Usage:
    python verify_paths.py --manifest path/to/manifest.yaml

Manifest format:
    checks:
      - name: annotation i2
        path: "\\\\hive3065\\...\\annotations_i2.nii.gz"
      - name: raw tif
        path: "\\\\hive3065\\...\\nlm_volume.tif"
      ...

Exit code is nonzero if any path is missing (same behavior as the original
script raising SystemExit).
"""
import argparse
import os
import sys

try:
    import yaml
except ImportError:
    yaml = None


def load_manifest(manifest_path):
    with open(manifest_path, 'r', encoding='utf-8') as f:
        text = f.read()
    if yaml is not None:
        data = yaml.safe_load(text)
        return data.get('checks', [])
    # Minimal fallback parser if pyyaml isn't installed: expects the simple
    # "- name: X\n  path: Y" structure used by this repo's manifests.
    checks = []
    current = {}
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('- name:'):
            if current:
                checks.append(current)
            current = {'name': stripped.split(':', 1)[1].strip().strip('"\'')}
        elif stripped.startswith('path:'):
            current['path'] = stripped.split(':', 1)[1].strip().strip('"\'')
    if current:
        checks.append(current)
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True, help='Path to a YAML manifest of {name, path} checks.')
    args = parser.parse_args()

    checks = load_manifest(args.manifest)
    if not checks:
        print(f'No checks found in manifest: {args.manifest}')
        sys.exit(2)

    all_ok = True
    for check in checks:
        name, path = check['name'], check['path']
        exists = os.path.isfile(path) or os.path.isdir(path)
        tag = 'OK' if exists else 'MISSING'
        print(f'{tag} {name}')
        if not exists:
            print(f'       -> {path}')
            all_ok = False

    if all_ok:
        print('\nAll paths OK - ready to proceed.')
    else:
        raise SystemExit('One or more paths are missing!')


if __name__ == '__main__':
    main()
