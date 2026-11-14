"""Part D4 (read-only): Pearson r of the canonical model input against the packaged specB_unified and
specA_unified model inputs, at the best-matching common crop.

Search: all 48 signed axis permutations of the canonical image (b1_find_transforms.apply_t), and every offset that
leaves >= MIN_OVERLAP of the smaller volume overlapping, scored by masked normalised cross-correlation (Pearson r
on the overlap, computed for all offsets at once with FFTs) on 8x block means. The best transform is then refined
locally (+-2 voxels) at 4x, 2x and full resolution. Offset d means canonical_transformed[i] <-> target[i + d].

Usage: python d4_crop_match.py <package_dir> <out_json>
"""
import itertools
import json
import sys
from pathlib import Path

import nibabel as nib
import numpy as np
import tifffile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from b1_find_transforms import apply_t  # noqa: E402

MIN_OVERLAP = 0.5


def bm(a, f):
    s = [n // f * f for n in a.shape]
    a = a[:s[0], :s[1], :s[2]].astype(np.float64)
    return a.reshape(s[0] // f, f, s[1] // f, f, s[2] // f, f).mean((1, 3, 5))


def ncc_all(x, y):
    """Pearson r on the overlap for every integer offset d (x[i] <-> y[i+d]). Returns r array and offset origin."""
    shp = [a + b - 1 for a, b in zip(x.shape, y.shape)]
    F = lambda a: np.fft.rfftn(a, shp, axes=(0, 1, 2))  # noqa: E731
    I = lambda a: np.fft.irfftn(a, shp, axes=(0, 1, 2))  # noqa: E731
    mx, my = np.ones_like(x), np.ones_like(y)
    # correlation corr(a, b)(d) = sum_i a(i) b(i+d) = ifft(conj(F(a)) F(b))
    Fx, Fx2, Fmx = np.conj(F(x)), np.conj(F(x * x)), np.conj(F(mx))
    Fy, Fy2, Fmy = F(y), F(y * y), F(my)
    n = I(Fmx * Fmy); sx = I(Fx * Fmy); sy = I(Fmx * Fy)
    sxy = I(Fx * Fy); sxx = I(Fx2 * Fmy); syy = I(Fmx * Fy2)
    n = np.round(n)
    with np.errstate(divide='ignore', invalid='ignore'):
        cov = sxy - sx * sy / n
        r = cov / np.sqrt(np.clip(sxx - sx ** 2 / n, 1e-12, None) * np.clip(syy - sy ** 2 / n, 1e-12, None))
    need = MIN_OVERLAP * min(x.size, y.size)
    r[n < need] = np.nan
    # index k in the circular result corresponds to offset d = k for k < y.shape, else k - shp
    return r, shp


def idx_to_off(k, shp, yshape):
    # offsets run from -(nx-1) to ny-1; index k < ny -> d = k, else d = k - (nx+ny-1)
    return tuple(int(kk if kk < ny else kk - s) for kk, s, ny in zip(k, shp, yshape))


def r_at(x, y, d, step=1):
    sx, sy = [], []
    for n_x, n_y, dd in zip(x.shape, y.shape, d):
        lo = max(0, -dd); hi = min(n_x, n_y - dd)
        if hi <= lo:
            return float('nan'), 0
        sx.append(slice(lo, hi, step)); sy.append(slice(lo + dd, hi + dd, step))
    a = x[tuple(sx)].astype(np.float64).ravel(); b = y[tuple(sy)].astype(np.float64).ravel()
    return float(np.corrcoef(a, b)[0, 1]), int(np.prod([(s.stop - s.start) for s in sx]))


def refine(x_full, y_full, d_full):
    """Local +-2 search at 4x, 2x, 1x around the running full-resolution guess d_full."""
    g = np.array(d_full, float)
    trace = []
    for f in (4, 2, 1):
        x, y = (bm(x_full, f), bm(y_full, f)) if f > 1 else (x_full, y_full)
        d = np.round(g / f).astype(int)
        step = 2 if f == 1 else 1
        best = None
        for dd in itertools.product(range(-2, 3), repeat=3):
            c = tuple(int(v) for v in d + np.array(dd))
            r, _ = r_at(x, y, c, step)
            if best is None or r > best[0]:
                best = (r, c)
        g = np.array(best[1]) * f
        trace.append(dict(factor=f, offset_at_factor=list(best[1]), r=best[0]))
    d = tuple(int(v) for v in g)
    r, nvox = r_at(x_full, y_full, d, 1)
    return dict(offset_full_res=list(map(int, d)), r_full_res=r, overlap_voxels=nvox, trace=trace)


def main():
    pkg, out = Path(sys.argv[1]), sys.argv[2]
    v = pkg / '01_volumes'
    can = tifffile.imread(v / 'bnei_reem_fresh_bnei_reem_i4/image_preprocessed.tif')  # (Z, Y, X) as read
    targets = {k: np.asanyarray(nib.load(str(v / f'{k}/image_preprocessed.nii.gz')).dataobj)
               for k in ('bnei_reem_specB_unified', 'bnei_reem_specA_unified')}
    res = dict(canonical=dict(path='01_volumes/bnei_reem_fresh_bnei_reem_i4/image_preprocessed.tif', shape=list(can.shape),
                              dtype=str(can.dtype), note='TIFF as read by tifffile (Z, Y, X)'))
    F0 = 8
    for name, tgt in targets.items():
        y8 = bm(tgt, F0)
        rows = []
        for perm in itertools.permutations(range(3)):
            for flips in itertools.product([False, True], repeat=3):  # per-axis mask, as apply_t expects
                x8 = bm(np.ascontiguousarray(apply_t(can, list(perm), list(flips))), F0)
                r, shp = ncc_all(x8, y8)
                k = np.unravel_index(np.nanargmax(r), r.shape)
                kmin = np.unravel_index(np.nanargmin(r), r.shape)
                rows.append(dict(perm=list(perm), flips=list(flips), flipped_axes=[i for i, f in enumerate(flips) if f],
                                 r_max=float(r[k]), offset8=idx_to_off(k, shp, y8.shape),
                                 r_min=float(r[kmin]), offset8_min=idx_to_off(kmin, shp, y8.shape)))
        assert len(rows) == 48
        rows.sort(key=lambda z: -z['r_max'])
        best = rows[0]
        xb = np.ascontiguousarray(apply_t(can, best['perm'], best['flips']))
        ref = refine(xb, tgt, [o * F0 for o in best['offset8']])
        max_abs = max(max(abs(z['r_max']), abs(z['r_min'])) for z in rows)
        res[name] = dict(target_shape=list(tgt.shape), target_dtype=str(tgt.dtype),
                         best_transform=dict(perm=best['perm'], flips=best['flips'], flipped_axes=best['flipped_axes'],
                                             note='canonical TIFF (Z,Y,X) -> np.transpose(perm) -> flip flipped_axes'),
                         coarse_8x=best, refined=ref,
                         second_best_transform_r8=rows[1]['r_max'],
                         max_abs_r_any_transform_any_offset_8x=max_abs,
                         all_transforms_8x=rows)
        print(name, 'target', tgt.shape, '| best perm', best['perm'], 'flip axes', best['flipped_axes'], 'r8', round(best['r_max'], 5),
              'off8', best['offset8'], '| refined', ref['offset_full_res'], 'r', round(ref['r_full_res'], 6),
              'overlap', ref['overlap_voxels'], '| 2nd best r8', round(rows[1]['r_max'], 4), '| max|r| 8x', round(max_abs, 4), flush=True)
    json.dump(res, open(out, 'w'), indent=1)


if __name__ == '__main__':
    main()
