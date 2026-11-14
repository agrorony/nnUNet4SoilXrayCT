"""Part C5 for the Rehovot samp3 Otsu mask: raw | packaged | fresh Otsu | difference, three axes.
Usage: python c4_plot.py <package_dir> <C4_otsu.json> <out_png>
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import nibabel as nib
import numpy as np
from skimage.filters import threshold_otsu

pkg, js, out = Path(sys.argv[1]), json.load(open(sys.argv[2])), sys.argv[3]
case = 'Rehovot_samp3_highkV_Cu0.11_15um'
img = np.asanyarray(nib.load(str(pkg / f'01_volumes/{case}/image_preprocessed.nii.gz')).dataobj)
packaged = np.load(pkg / f'01_volumes/{case}/segmentation_otsu.npy')
t = threshold_otsu(img)
fresh = img < t
r = js[case]
lo, hi = np.percentile(img[::4, ::4, ::4], [1, 99])
fig, axs = plt.subplots(3, 4, figsize=(20, 15))
for a in range(3):
    m = img.shape[a] // 2
    i2, p2, f2 = (np.take(x, m, axis=a) for x in (img, packaged, fresh))
    axs[a, 0].imshow(i2, cmap='gray', vmin=lo, vmax=hi); axs[a, 0].set_title(f'raw, axis {a} slice {m}')
    axs[a, 1].imshow(p2, cmap='gray_r'); axs[a, 1].set_title('packaged Otsu mask (black = pore)')
    axs[a, 2].imshow(f2, cmap='gray_r'); axs[a, 2].set_title(f'fresh threshold_otsu, pore < {t:.6f}')
    g = np.clip((i2 - lo) / (hi - lo), 0, 1); d = np.stack([g] * 3, -1) * 0.6; diff = p2 != f2; d[diff] = (1, 0, 0)
    axs[a, 3].imshow(d); axs[a, 3].set_title(f'difference (red): {int(diff.sum())} px')
for x in axs.ravel():
    x.set_xticks([]); x.set_yticks([])
c = r['fresh_from_nii_vs_packaged']
fig.suptitle(f"{case} Otsu mask: packaged vs fresh global Otsu — {'VERIFIED (identical)' if c['identical'] else 'Dice %.5f' % c['dice']}\n"
             f"threshold {r['threshold_nii']:.6f} (same on 10.5 TIFF and packaged NIfTI; TIFF == NIfTI transposed: {r['tif_equals_packaged_image_transposed']}) | "
             f"voxels differing {c['n_diff']} | pore {r['packaged_pore_pct']:.4f} % packaged vs {r['fresh_pore_pct']:.4f} % fresh\n"
             f"fresh mask from the TIFF in its own (Z,Y,X) order is identical to the share copy: {r['fresh_from_tif_vs_share_copy']['identical']}", fontsize=11)
fig.tight_layout(rect=(0, 0, 1, 0.92))
fig.savefig(out, dpi=72)
