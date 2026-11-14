"""Gate G check (read-only): each re-oriented segmentation in the package vs its pre-flip original.

Compares on-disk dtype (NIfTI header datatype / .npy dtype), loaded array dtype, shape, voxel sizes,
scl_slope/inter, label set and voxel count per label (orientation changes must not change counts), and file size.
Usage: python g4_dtype_check.py <package_dir> <pre_flip_backup_dir> <out_json>
"""
import json
import sys
from pathlib import Path

import nibabel as nib
import numpy as np


def info(p):
    if p.suffix == '.npy':
        a = np.load(p, mmap_mode='r')
        d = dict(header_dtype=str(a.dtype), zooms=None, slope_inter=None)
        a = np.asarray(a)
    else:
        img = nib.load(str(p))
        h = img.header
        d = dict(header_dtype=str(h.get_data_dtype()), zooms=[float(z) for z in h.get_zooms()],
                 slope_inter=[None if v is None or np.isnan(v) else float(v) for v in h.get_slope_inter()])
        a = np.asanyarray(img.dataobj)
    u, c = np.unique(a, return_counts=True)
    d.update(array_dtype=str(a.dtype), shape=list(a.shape), labels={str(k): int(v) for k, v in zip(u.tolist(), c)},
             bytes=p.stat().st_size)
    return d


def main():
    pkg, bak, out = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    rows, bad = [], 0
    for b in sorted(bak.rglob('*')):
        if not b.is_file() or b.name == 'README.md':
            continue
        rel = b.relative_to(bak).as_posix()
        o, n = info(b), info(pkg / rel)
        same_dtype = o['header_dtype'] == n['header_dtype'] and o['array_dtype'] == n['array_dtype']
        same_counts = sorted(o['labels'].items()) == sorted(n['labels'].items())
        same_shape_multiset = sorted(o['shape']) == sorted(n['shape'])
        bad += not same_dtype
        rows.append(dict(path=rel, same_dtype=same_dtype, same_label_counts=same_counts,
                         same_shape_up_to_permutation=same_shape_multiset, original=o, reoriented=n))
        print(f"{'OK ' if same_dtype else 'DIFF'} {rel}: dtype {o['header_dtype']}/{o['array_dtype']} -> "
              f"{n['header_dtype']}/{n['array_dtype']}; shape {o['shape']} -> {n['shape']}; zooms {o['zooms']} -> {n['zooms']}; "
              f"slope {o['slope_inter']} -> {n['slope_inter']}; labels same: {same_counts}; "
              f"bytes {o['bytes']:,} -> {n['bytes']:,} ({(n['bytes'] - o['bytes']) / 1e6:+.0f} MB)")
    tot_o = sum(r['original']['bytes'] for r in rows); tot_n = sum(r['reoriented']['bytes'] for r in rows)
    print(f"{len(rows)} files; dtype differs in {bad}; total {tot_o / 1e9:.3f} GB -> {tot_n / 1e9:.3f} GB")
    json.dump(dict(n=len(rows), n_dtype_diff=bad, bytes_before=tot_o, bytes_after=tot_n, rows=rows), open(out, 'w'), indent=1)


if __name__ == '__main__':
    main()
