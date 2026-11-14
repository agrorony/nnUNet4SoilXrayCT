"""Part D evidence PNG: canonical model input vs specB / specA at the best D4 transform + crop, and the scan timeline.

Rows = the three axes (middle slice of the overlap). Columns = canonical (transformed), specB at the D4 offset,
specA at its best D4 offset. Bottom panel: timeline from D1_D3_provenance.json and D2b_raw_projections.json.

Usage: python d_plot.py <package_dir> <evidence_dir>
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import nibabel as nib
import numpy as np
import tifffile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from b1_find_transforms import apply_t  # noqa: E402


def crop_pair(x, y, d):
    sx, sy = [], []
    for nx, ny, dd in zip(x.shape, y.shape, d):
        lo, hi = max(0, -dd), min(nx, ny - dd)
        sx.append(slice(lo, hi)); sy.append(slice(lo + dd, hi + dd))
    return x[tuple(sx)], y[tuple(sy)]


def main():
    pkg, ev = Path(sys.argv[1]), Path(sys.argv[2])
    d4 = json.load(open(ev / 'D4_crop_match.json'))
    d13 = json.load(open(ev / 'D1_D3_provenance.json'))
    d2b = json.load(open(ev / 'D2b_raw_projections.json'))
    v = pkg / '01_volumes'
    can = tifffile.imread(v / 'bnei_reem_fresh_bnei_reem_i4/image_preprocessed.tif')
    tg = {k: np.asanyarray(nib.load(str(v / f'{k}/image_preprocessed.nii.gz')).dataobj)
          for k in ('bnei_reem_specB_unified', 'bnei_reem_specA_unified')}
    pairs = {}
    for k, y in tg.items():
        b = d4[k]['best_transform']
        x = np.ascontiguousarray(apply_t(can, b['perm'], b['flips']))
        pairs[k] = crop_pair(x, y, d4[k]['refined']['offset_full_res'])

    fig = plt.figure(figsize=(18, 22))
    gs = fig.add_gridspec(4, 4, height_ratios=[1, 1, 1, 0.75])
    for a in range(3):
        cols = [('canonical (aligned to specB)', pairs['bnei_reem_specB_unified'][0]),
                ('specB_unified, same crop', pairs['bnei_reem_specB_unified'][1]),
                ('canonical (best transform vs specA)', pairs['bnei_reem_specA_unified'][0]),
                ('specA_unified, best crop found', pairs['bnei_reem_specA_unified'][1])]
        for c, (title, vol) in enumerate(cols):
            ax = fig.add_subplot(gs[a, c])
            m = vol.shape[a] // 2
            s = np.take(vol, m, axis=a)
            lo, hi = np.percentile(vol[::4, ::4, ::4], [1, 99])
            ax.imshow(s, cmap='gray', vmin=lo, vmax=hi)
            ax.set_title(f'{title}\naxis {a}, slice {m} of overlap', fontsize=10)
            ax.set_xticks([]); ax.set_yticks([])
    B, A = d4['bnei_reem_specB_unified'], d4['bnei_reem_specA_unified']

    def recs(root):
        r = d13['reconstructions'][root]
        return r if isinstance(r, list) else []
    lines = ['Timeline (file mtimes; "Study Date and Time" in SkyScan logs = end of scan):']
    for key, lab in (('A', 'samp_2.0'), ('B', 'samp_2')):
        x = d2b[key]
        study = [ln for ln in next(iter(x['log_lines'].values())) if ln.startswith('Study Date')][0]
        px = [ln for ln in next(iter(x['log_lines'].values())) if ln.startswith('Image Pixel Size')][0]
        lines.append(f"  raw {lab}: projections {x['proj_mtime_min']} .. {x['proj_mtime_max']}  | log: {study} | {px}")
    for root, rr in d13['reconstructions'].items():
        for r in (rr if isinstance(rr, list) else []):
            if r['n_slices']:
                lines.append(f"  reconstruction {Path(r['folder']).name}: {r['n_slices']} slices dated {r['slice_mtime_min']} .. {r['slice_mtime_max']}")
    lines.append("  canonical 10.5\\nlm_volume.tif: 2026-04-20 16:00 (oldest file in 10.5\\ and nnUNet_resources\\bnei_reem\\; nothing older found)")
    lines.append('')
    lines.append(f"D4 canonical vs specB: perm {B['best_transform']['perm']}, flip axes {B['best_transform']['flipped_axes']}, "
                 f"offset {B['refined']['offset_full_res']}, r = {B['refined']['r_full_res']:.6f} on {B['refined']['overlap_voxels']:,} voxels")
    lines.append(f"D4 canonical vs specA: best of 48 transforms x all offsets: perm {A['best_transform']['perm']}, flip axes "
                 f"{A['best_transform']['flipped_axes']}, offset {A['refined']['offset_full_res']}, r = {A['refined']['r_full_res']:.4f} "
                 f"on {A['refined']['overlap_voxels']:,} voxels; max |r| any transform/offset (8x) = {A['max_abs_r_any_transform_any_offset_8x']:.4f}")
    ax = fig.add_subplot(gs[3, :]); ax.axis('off')
    ax.text(0, 1, '\n'.join(lines), va='top', family='monospace', fontsize=10)
    fig.suptitle("Part D: which Bnei Re'em scan is the canonical volume?", fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(ev / 'D_canonical_identity.png', dpi=60)


if __name__ == '__main__':
    main()
