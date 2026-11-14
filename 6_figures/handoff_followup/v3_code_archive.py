"""Package v3 (Gate 1 change, approved 2026-11-14): the code archive in 04_code/ is a `git archive` of current main
(the merge of PR #5) instead of v2's a01686e archive.

- writes <v3>/04_code/nnUNet4SoilXrayCT_<short>.zip from origin/main (must equal <expected_commit>)
- checks it: testzip, ZIP comment = commit, file list = `git ls-tree -r`, and every repo path cited in a v3 README
  exists in it (except the deliberate history mentions in ALLOWED_MISSING)
- removes v3's copy of the a01686e archive (the v2 original is checked to exist with the same sha256 first)
- updates PACKAGE_MAP_v2_to_v3.csv

Usage: python v3_code_archive.py <repo_dir> <v2_package_dir> <v3_package_dir> <map_csv> <expected_commit> <log_json>
"""
import csv
import hashlib
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

OLD = '04_code/nnUNet4SoilXrayCT_a01686e.zip'
ROOTS = ('1_', '2_', '3_', '4_', '5_', '6_', 'docs/', 'archive/', '00_', '05_evaluation/', '06_reporting/')
ALLOWED_MISSING = {'00_docs/prompts/', '06_reporting/', '06_reporting/scripts/',
                   '05_evaluation/psd/full_volume_batch/logs/nlm_volume_fresh_bnei_reem_i4.log',
                   '05_evaluation/psd/full_volume_batch/logs/mishmar_hanegev_maoz_3_5p85um_scratch_i2.log'}


def git(repo, *a):
    return subprocess.run(['git', '-C', str(repo), *a], capture_output=True, text=True, encoding='utf-8', check=True).stdout


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 24), b''):
            h.update(b)
    return h.hexdigest()


def main():
    repo, v2, v3, map_csv, expected, log_json = (Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]),
                                                 Path(sys.argv[4]), sys.argv[5], Path(sys.argv[6]))
    commit = git(repo, 'rev-parse', 'origin/main').strip()
    assert commit == expected, (commit, expected)
    name = f'nnUNet4SoilXrayCT_{commit[:7]}.zip'
    out = v3 / '04_code' / name
    assert not out.exists()
    subprocess.run(['git', '-C', str(repo), 'archive', '--format=zip', f'--prefix={name[:-4]}/', '-o', str(out), commit], check=True)
    z = zipfile.ZipFile(out)
    assert z.testzip() is None
    assert z.comment.decode() == commit
    pre = name[:-4] + '/'
    files = {n[len(pre):] for n in z.namelist() if not n.endswith('/')}
    tree = set(git(repo, 'ls-tree', '-r', '--name-only', commit).splitlines())
    assert files == tree, (len(files), len(tree))
    dirs = set()
    for f in files:
        parts = f.split('/')[:-1]
        dirs |= {'/'.join(parts[:i]) + '/' for i in range(1, len(parts) + 1)}
    missing, checked = set(), 0
    for md in v3.rglob('README.md'):
        for blk in re.findall(r'`([^`]+)`', md.read_text(encoding='utf-8')):
            for t in blk.split():
                t = t.strip('"\',;:()')
                if not t.startswith(ROOTS) or '/' not in t or '*' in t or '<' in t:
                    continue
                if (md.parent / t).exists() or (v3 / t).exists():
                    continue
                checked += 1
                if t not in files and t.rstrip('/') + '/' not in dirs:
                    missing.add(t)
    assert missing <= ALLOWED_MISSING, sorted(missing - ALLOWED_MISSING)

    # remove v3's copy of the v2 archive (original stays in v2)
    old3, old2 = v3 / OLD, v2 / OLD
    h_old = sha(old3)
    assert old2.is_file() and sha(old2) == h_old
    old3.unlink()

    rows = list(csv.reader(open(map_csv, encoding='utf-8')))
    hit = [r for r in rows if r[0] == OLD]
    assert len(hit) == 1 and hit[0][1] == OLD
    hit[0][1] = 'not in v3'
    hit[0][2] = f'replaced in v3 by 04_code/{name} (git archive of main, commit {commit})'
    rows.insert(len(rows) - 1, ['(new in v3)', f'04_code/{name}', f'git archive of main, commit {commit} (the merge of PR #5)'])
    with open(map_csv, 'w', encoding='utf-8', newline='') as f:
        csv.writer(f).writerows(rows)

    log = dict(commit=commit, archive=str(out), bytes=out.stat().st_size, sha256=sha(out), files=len(files),
               readme_repo_paths_checked=checked, allowed_missing=sorted(missing), removed_copy=OLD, removed_sha256=h_old)
    json.dump(log, open(log_json, 'w'), indent=1)
    print(json.dumps(log, indent=1))


if __name__ == '__main__':
    main()
