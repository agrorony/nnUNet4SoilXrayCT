"""Part G, Gate G summary (read-only): compare the staging folder with v1's MANIFEST.csv by sha256.

Lists files changed (same path, new content), added (path not in v1) and removed (in v1, not in staging),
with sizes. MANIFEST.csv itself is skipped (it is regenerated when v2 is built).

Usage: python g3_diff_vs_v1.py <package_dir> <out_json>
"""
import csv
import hashlib
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 24), b''):
            h.update(b)
    return h.hexdigest()


def main():
    pkg, out = Path(sys.argv[1]), sys.argv[2]
    v1 = {r['relative_path']: r for r in csv.DictReader(open(pkg / 'MANIFEST.csv', encoding='utf-8'))}
    now = {}
    for d, _, fs in os.walk(pkg):
        for f in fs:
            rel = (Path(d) / f).relative_to(pkg).as_posix()
            if rel != 'MANIFEST.csv':
                now[rel] = Path(d) / f
    with ThreadPoolExecutor(8) as ex:
        hashes = dict(zip(now, ex.map(sha, now.values())))
    changed = [dict(path=p, bytes_v1=int(v1[p]['bytes']), bytes_v2=now[p].stat().st_size) for p in sorted(now)
               if p in v1 and v1[p]['sha256'] != hashes[p]]
    added = [dict(path=p, bytes=now[p].stat().st_size) for p in sorted(now) if p not in v1]
    removed = [dict(path=p, bytes=int(v1[p]['bytes'])) for p in sorted(v1) if p not in now and p != 'MANIFEST.csv']
    res = dict(v1_files=len(v1), staging_files=len(now) + 1, changed=changed, added=added, removed=removed,
               hashes={p: hashes[p] for p in sorted(now)})
    json.dump(res, open(out, 'w'), indent=1)
    print(f"v1 manifest {len(v1)} files; staging {len(now)} files + MANIFEST.csv")
    for k in ('changed', 'added', 'removed'):
        print(f'== {k}: {len(res[k])}')
        for e in res[k]:
            print('  ', e)


if __name__ == '__main__':
    main()
