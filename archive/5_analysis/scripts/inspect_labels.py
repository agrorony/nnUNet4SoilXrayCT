"""inspect_labels.py — generalized label histogram + axis-summary inspector (S10).

Replaces the old repo-root `_inspect_labels.py`, which hardcoded a fixed
GT/NEW/OLD path triple. This version takes an arbitrary set of name=path
pairs.

Usage:
    python inspect_labels.py --paths GT=gt.nii.gz NEW=new_pred.nii.gz OLD=old_pred.nii.gz --axis-summary
"""
import argparse

import numpy as np
import nibabel as nib


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--paths', nargs='+', required=True, metavar='NAME=PATH',
                         help='Repeatable name=path pairs, e.g. GT=gt.nii.gz NEW=pred.nii.gz')
    parser.add_argument('--axis-summary', action='store_true',
                         help='Print non-zero slice indices per axis (matches original behavior, GT only by default).')
    parser.add_argument('--axis-summary-for', nargs='+', default=['GT'],
                         help='Which of the given names to print axis summaries for (default: GT, matching original).')
    args = parser.parse_args()

    entries = []
    for spec in args.paths:
        name, path = spec.split('=', 1)
        entries.append((name, path))

    for tag, path in entries:
        arr = np.asarray(nib.load(path).dataobj).astype(np.int32)
        unique, counts = np.unique(arr, return_counts=True)
        print(f'--- {tag} ---  shape={arr.shape}')
        for u, c in zip(unique, counts):
            print(f'  label {u:3d}: {c:>12,} voxels')
        if args.axis_summary and tag in args.axis_summary_for:
            for axis, name in [(0, 'x'), (1, 'y'), (2, 'z')]:
                nz = [i for i in range(arr.shape[axis]) if np.take(arr, i, axis=axis).any()]
                print(f'  Non-zero slices ({name}-axis): {len(nz)} / {arr.shape[axis]}')
                if nz:
                    print(f'    indices: {nz}')
        print()


if __name__ == '__main__':
    main()
