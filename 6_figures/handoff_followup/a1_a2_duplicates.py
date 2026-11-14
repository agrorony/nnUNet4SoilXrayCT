"""Part A1 + A2 of the 2026-11 hand-off follow-up (read-only on the package).

A1: group MANIFEST.csv by sha256; list multi-path groups and zero-byte files.
A2: load every volume file (.nii.gz/.tif/.npy), hash dtype+shape+C-contiguous bytes,
    group identical arrays. Also records label values/counts for integer volumes and
    caches each decompressed array as .npy (cache dir given on the command line) so
    later parts do not decompress again.

Usage: python a1_a2_duplicates.py <package_dir> <cache_dir> <out_dir>
"""
import csv
import hashlib
import json
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

VOL_EXT = ('.nii.gz', '.nii', '.tif', '.tiff', '.npy')


def load_volume(path: Path) -> np.ndarray:
    s = str(path).lower()
    if s.endswith(('.nii.gz', '.nii')):
        import nibabel as nib
        return np.asanyarray(nib.load(str(path)).dataobj)
    if s.endswith(('.tif', '.tiff')):
        import tifffile
        return tifffile.imread(str(path))
    if s.endswith('.npy'):
        return np.load(str(path))
    raise ValueError(path)


def cache_name(rel: str) -> str:
    return rel.replace('/', '__').replace('\\', '__') + '.npy'


def work(args):
    pkg, rel, cache = args
    a = load_volume(Path(pkg) / rel)
    a = np.ascontiguousarray(a)
    h = hashlib.sha256()
    h.update(str(a.dtype).encode())
    h.update(str(tuple(a.shape)).encode())
    h.update(memoryview(a.reshape(-1).view(np.uint8)))
    out = {'rel': rel, 'shape': list(a.shape), 'dtype': str(a.dtype), 'array_sha256': h.hexdigest()}
    if a.dtype.kind in 'biu':
        vals, cnts = np.unique(a, return_counts=True)
        out['labels'] = {str(int(v)): int(c) for v, c in zip(vals, cnts)}
    else:
        out['min'] = float(a.min()); out['max'] = float(a.max()); out['mean'] = float(a.mean(dtype=np.float64))
    cp = Path(cache) / cache_name(rel)
    if not cp.exists():
        np.save(cp, a)
    out['cache'] = str(cp)
    return out


def main():
    pkg, cache, outdir = map(Path, sys.argv[1:4])
    cache.mkdir(parents=True, exist_ok=True); outdir.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(open(pkg / 'MANIFEST.csv', encoding='utf-8')))

    # ---- A1
    by_hash = defaultdict(list)
    for r in rows:
        by_hash[r['sha256']].append(r)
    dup_groups = [[(r['relative_path'], int(r['bytes'])) for r in g] for g in by_hash.values() if len(g) > 1]
    zero = [r['relative_path'] for r in rows if int(r['bytes']) == 0]
    a1 = {'n_files': len(rows), 'n_unique_sha256': len(by_hash), 'duplicate_groups': dup_groups, 'zero_byte': zero}
    json.dump(a1, open(outdir / 'A1_file_level.json', 'w'), indent=1)
    print(f"A1: {len(rows)} files, {len(by_hash)} unique sha256, {len(dup_groups)} multi-path groups, {len(zero)} zero-byte")
    for g in dup_groups:
        print('  GROUP (%d B):' % g[0][1], ' | '.join(p for p, _ in g))
    for z in zero:
        print('  ZERO:', z)

    # ---- A2
    vols = sorted(r['relative_path'] for r in rows if r['relative_path'].lower().endswith(VOL_EXT))
    with ProcessPoolExecutor(max_workers=min(20, len(vols))) as ex:
        res = list(ex.map(work, [(str(pkg), v, str(cache)) for v in vols]))
    json.dump(res, open(outdir / 'A2_array_level.json', 'w'), indent=1)
    groups = defaultdict(list)
    for r in res:
        groups[r['array_sha256']].append(r['rel'])
    print(f"\nA2: {len(res)} volumes, {len(groups)} distinct arrays")
    for r in res:
        extra = r.get('labels') or {k: round(r[k], 4) for k in ('min', 'max', 'mean')}
        print(f"  {r['array_sha256'][:12]}  {r['dtype']:8s} {str(tuple(r['shape'])):20s} {r['rel']}  {extra}")
    for h, g in groups.items():
        if len(g) > 1:
            print('  IDENTICAL ARRAYS:', ' | '.join(g))


if __name__ == '__main__':
    main()
