"""Part C3 + C5: compare the fresh re-inference with the packaged segmentation, in the same orientation,
and draw one evidence PNG per volume.

The fresh prediction comes out of the same chunk+concatenate route as the original, i.e. in the share
orientation. It is brought into the packaged orientation with the B4 transform of that file, and also
compared directly with the pre-flip original (share orientation) as a cross-check.

Metrics: % voxel agreement; Dice for labels 5 (pore), 2 (POM), 1 (stones); per-class fractions.
Guide: pore Dice >= 0.99, POM Dice >= 0.95 and all fractions within 0.05 percentage points -> VERIFIED (re-inference match).

Usage: python c3_c5_compare.py <package_dir> <backup_dir> <verification_dir> <B2_B3_results.json> <evidence_dir> <run_key>...
"""
import json
import sys
from pathlib import Path

import nibabel as nib
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from b1_find_transforms import apply_t  # noqa: E402

FILES = {
    'bnei_reem_fresh_bnei_reem_i4': ('01_volumes/bnei_reem_fresh_bnei_reem_i4/segmentation.nii.gz', '01_volumes/bnei_reem_fresh_bnei_reem_i4/image_preprocessed.tif', 'nlm_volume.nii.gz'),
    'mishmar_hanegev_maoz_3_5p85um': ('01_volumes/mishmar_hanegev_maoz_3_5p85um/segmentation.nii.gz', '01_volumes/mishmar_hanegev_maoz_3_5p85um/image_preprocessed.nii.gz', 'mishmar_hanegev_maoz_3_5p85um.nii.gz'),
    'mishmar_hanegev_maoz_2_8p8um': ('01_volumes/mishmar_hanegev_maoz_2_8p8um/segmentation.nii.gz', '01_volumes/mishmar_hanegev_maoz_2_8p8um/image_preprocessed.nii.gz', 'mishmar_hanegev_maoz_2_8p8um.nii.gz'),
}
NAMES = {0: 'matrix', 1: 'stones', 2: 'POM', 5: 'pore'}


def load(p):
    p = str(p)
    if p.endswith('.tif'):
        import tifffile
        return tifffile.imread(p)
    return np.asanyarray(nib.load(p).dataobj)


def compare(a, b):
    out = dict(voxel_agreement_pct=float(100 * (a == b).mean()), n_diff=int((a != b).sum()))
    for lab in (5, 2, 1):
        ma, mb = a == lab, b == lab
        s = int(ma.sum()) + int(mb.sum())
        out[f'dice_{lab}'] = float(2 * np.logical_and(ma, mb).sum() / s) if s else float('nan')
    labs = sorted(set(np.unique(a)) | set(np.unique(b)))
    out['fractions_pct'] = {str(int(l)): [float(100 * (a == l).mean()), float(100 * (b == l).mean())] for l in labs}
    out['max_fraction_diff_pp'] = max(abs(x - y) for x, y in out['fractions_pct'].values())
    ok = out['dice_5'] >= 0.99 and out['dice_2'] >= 0.95 and out['max_fraction_diff_pp'] <= 0.05
    out['status'] = 'VERIFIED (re-inference match)' if ok else 'MISMATCH'
    return out


def lut_rgb(seg2d):
    rgb = np.zeros(seg2d.shape + (3,), np.float32)
    rgb[seg2d == 1] = (0.55, 0.55, 0.55)
    rgb[seg2d == 2] = (0.1, 0.8, 0.1)
    rgb[seg2d == 5] = (0.9, 0.15, 0.15)
    return rgb


def main():
    pkg, bak, ver, b23, evid = map(Path, sys.argv[1:6])
    keys = sys.argv[6:]
    tr = {r['seg']: r['transform'] for r in json.load(open(b23))}
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    allres = {}
    for key in keys:
        seg_rel, img_rel, out_name = FILES[key]
        fresh_share = load(ver / key / 'inference_concatenated' / out_name)
        share = load(bak / seg_rel)
        packaged = load(pkg / seg_rel)
        t = tr[seg_rel]
        fresh = np.ascontiguousarray(apply_t(fresh_share, t['perm'], t['flips']))
        res = dict(transform_applied_to_fresh=t,
                   packaged_vs_fresh=compare(packaged, fresh),
                   share_vs_fresh_share_orientation=compare(share, fresh_share),
                   fresh_identical_to_share=bool(np.array_equal(share, fresh_share)))
        allres[key] = res
        c = res['packaged_vs_fresh']
        print(key, json.dumps({k: v for k, v in c.items()}, indent=1), 'identical:', res['fresh_identical_to_share'], flush=True)
        img = load(pkg / img_rel)
        lo, hi = np.percentile(img[::4, ::4, ::4], [1, 99])
        fig, axs = plt.subplots(3, 4, figsize=(20, 15))
        for ax_i in range(3):
            mid = img.shape[ax_i] // 2
            im2 = np.take(img, mid, axis=ax_i); p2 = np.take(packaged, mid, axis=ax_i); f2 = np.take(fresh, mid, axis=ax_i)
            axs[ax_i, 0].imshow(im2, cmap='gray', vmin=lo, vmax=hi); axs[ax_i, 0].set_title(f'raw, axis {ax_i} slice {mid}')
            axs[ax_i, 1].imshow(lut_rgb(p2)); axs[ax_i, 1].set_title('packaged segmentation')
            axs[ax_i, 2].imshow(lut_rgb(f2)); axs[ax_i, 2].set_title('fresh re-inference (same orientation)')
            g = np.clip((im2 - lo) / (hi - lo), 0, 1); d = np.stack([g, g, g], -1) * 0.6
            diff = p2 != f2
            d[diff] = (1, 0, 0)
            axs[ax_i, 3].imshow(d); axs[ax_i, 3].set_title(f'difference (red) — {int(diff.sum())} px differ in this slice')
        for a in axs.ravel():
            a.set_xticks([]); a.set_yticks([])
        fr = c['fractions_pct']
        frs = ', '.join(f"{NAMES.get(int(k), k)} {v[0]:.4f}/{v[1]:.4f}" for k, v in fr.items())
        fig.suptitle(f"{key}: packaged vs fresh re-inference  —  {c['status']}\n"
                     f"voxel agreement {c['voxel_agreement_pct']:.4f} % ({c['n_diff']:,} voxels differ) | Dice pore {c['dice_5']:.5f}, "
                     f"POM {c['dice_2']:.5f}, stones {c['dice_1']:.5f}\nfractions % packaged/fresh: {frs} | max diff {c['max_fraction_diff_pp']:.4f} pp"
                     f" | fresh identical to share original (same orientation): {'yes' if res['fresh_identical_to_share'] else 'no'}"
                     "\ncolours: pore red, POM green, stones grey", fontsize=11)
        fig.tight_layout(rect=(0, 0, 1, 0.9))
        png = evid / f'C5_{key}.png'
        fig.savefig(png, dpi=72); plt.close(fig)
        res['png'] = str(png)
    prev = {}
    pj = evid / 'C3_results.json'
    if pj.exists():
        prev = json.load(open(pj))
    prev.update(allres)
    json.dump(prev, open(pj, 'w'), indent=1)


if __name__ == '__main__':
    main()
