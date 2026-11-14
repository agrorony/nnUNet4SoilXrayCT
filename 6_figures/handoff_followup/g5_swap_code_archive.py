"""Part G (Gate G option 1, approved 2026-11-14): replace the package's code archive with a `git archive` of HEAD.

The HEAD commit must be clean (no tracked changes) and already on origin, so the hash in the READMEs can be found on GitHub.
- writes <package>/04_code/nnUNet4SoilXrayCT_<short>.zip (same layout as v1's archive: prefix folder, commit in the ZIP comment)
- checks it: testzip, file count = `git ls-tree -r`, and every repo path cited in a package README exists in it
  (except the deliberate history mentions in ALLOWED_MISSING)
- moves v1's archive to <removed_dir>/04_code/ (sha256 checked)
- names the commit in 04_code/README.md and the top-level README (backups in <backup_dir>)

Usage: python g5_swap_code_archive.py <repo_dir> <package_dir> <removed_dir> <backup_dir> <evidence_dir>
"""
import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

OLD = 'nnUNet4SoilXrayCT_198c5b5.zip'
OLD_FULL = '198c5b5dc3da729954e9a5efc20aec6d208d3bad'
ROOTS = ('1_', '2_', '3_', '4_', '5_', '6_', 'docs/', 'archive/', '0')
# old-layout paths the READMEs mention on purpose, as history (see G2 / G2b logs)
ALLOWED_MISSING = {'00_docs/prompts/', '06_reporting/', '06_reporting/scripts/', '02_data/',
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


def read(p):
    with open(p, encoding='utf-8', newline='') as f:
        return f.read()


def write(p, s):
    with open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(s)


def main():
    repo, pkg, rem, bak, evid = map(Path, sys.argv[1:6])
    commit = git(repo, 'rev-parse', 'HEAD').strip()
    branch = git(repo, 'rev-parse', '--abbrev-ref', 'HEAD').strip()
    short = commit[:7]
    assert git(repo, 'status', '--porcelain', '--untracked-files=no') == '', 'tracked changes in the working tree'
    assert f'origin/{branch}' in git(repo, 'branch', '-r', '--contains', commit), 'HEAD is not pushed'
    name = f'nnUNet4SoilXrayCT_{short}.zip'
    out = pkg / '04_code' / name
    assert not out.exists() and (pkg / '04_code' / OLD).is_file() and not (rem / '04_code' / OLD).exists()

    # 1. archive + checks
    subprocess.run(['git', '-C', str(repo), 'archive', '--format=zip', f'--prefix={name[:-4]}/', '-o', str(out), commit], check=True)
    z = zipfile.ZipFile(out)
    assert z.testzip() is None
    assert z.comment.decode() == commit
    files = {n[len(name) - 3:] for n in z.namelist() if not n.endswith('/')}
    tree = set(git(repo, 'ls-tree', '-r', '--name-only', commit).splitlines())
    assert files == tree, (len(files), len(tree))
    dirs = set()
    for f in files:
        parts = f.split('/')[:-1]
        dirs |= {'/'.join(parts[:i]) + '/' for i in range(1, len(parts) + 1)}
    missing = set()
    for md in pkg.rglob('README.md'):
        for blk in re.findall(r'`([^`]+)`', md.read_text(encoding='utf-8')):
            for t in blk.split():
                t = t.strip('"\',;:()')
                if not t.startswith(ROOTS) or '/' not in t or '*' in t or '<' in t:
                    continue
                if (md.parent / t).exists() or (pkg / t).exists() or t in files or t.rstrip('/') + '/' in dirs:
                    continue
                missing.add(t)
    assert missing <= ALLOWED_MISSING, sorted(missing - ALLOWED_MISSING)

    # 2. README edits (planned first, all must match once)
    url = f'https://github.com/agrorony/nnUNet4SoilXrayCT/tree/{commit}'
    edits = {
        '04_code/README.md': [(
            f"| `{OLD}` | `git archive` of this project's repository, branch `handoff/2026-11-cleanup` (PR https://github.com/agrorony/nnUNet4SoilXrayCT/pull/1) | `{OLD_FULL}` |",
            f"| `{name}` | `git archive` of this project's repository at commit `{commit}`, branch `{branch}`, made 2026-11-14 for v2 of this package "
            f"(on GitHub: {url}). The paths this package's READMEs cite follow this commit's layout (2026-11 restructure; its "
            f"`archive/PATH_MAP_2026-11.csv` maps the older paths). v1 of the package shipped `{OLD}` (commit `{OLD_FULL}`, older layout) | `{commit}` |")],
        'README.md': [
            (f"(scripts are in `04_code/{OLD}`)", f"(scripts are in `04_code/{name}`)"),
            (f"Archived commit `{OLD_FULL}`, branch `handoff/2026-11-cleanup`, pull request https://github.com/agrorony/nnUNet4SoilXrayCT/pull/1.",
             f"Archived commit `{commit}`, branch `{branch}` ({url}). v1 of this package archived `{OLD_FULL}` "
             f"(branch `handoff/2026-11-cleanup`, pull request https://github.com/agrorony/nnUNet4SoilXrayCT/pull/1)."),
        ],
    }
    plans = {}
    for rel, reps in edits.items():
        s = read(pkg / rel)
        for o, n in reps:
            assert s.count(o) == 1, (rel, o)
            s = s.replace(o, n)
        plans[rel] = s

    # 3. move the v1 archive out, apply README edits
    src, dst = pkg / '04_code' / OLD, rem / '04_code' / OLD
    h_old = sha(src)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    assert sha(dst) == h_old and not src.exists()
    log = dict(commit=commit, branch=branch, archive=str(out), archive_bytes=out.stat().st_size, archive_sha256=sha(out),
               archive_files=len(files), cited_paths_missing_allowed=sorted(missing),
               moved=dict(path=f'04_code/{OLD}', to=str(dst), sha256=h_old), edited=[])
    for rel, s in plans.items():
        b = bak / rel
        assert not b.exists(), b
        b.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pkg / rel, b)
        write(pkg / rel, s)
        log['edited'].append(dict(path=rel, backup=str(b), sha256_before=sha(b), sha256_after=sha(pkg / rel)))
    json.dump(log, open(evid / 'G5_log.json', 'w'), indent=1)
    print(json.dumps({k: v for k, v in log.items() if k != 'edited'}, indent=1))


if __name__ == '__main__':
    main()
