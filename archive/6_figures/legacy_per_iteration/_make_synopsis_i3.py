"""
Synopsis export: one PNG per annotated z-slice showing
  [Raw CT]  |  [GT Annotations i3]  |  [Prediction fresh_bnei_reem_i3]
with class-colour legend.

Transforms applied:
  - NIfTI (X,Y,Z) -> (Z,Y,X) + Y-flip  (both annotation and prediction)
  - Prediction labels shifted +1 to restore original class numbering
"""
import sys
if __name__ != '__main__':
    sys.exit(0)

import os
import json
import numpy as np
import nibabel as nib
import tifffile
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import ListedColormap

# ── Paths ──────────────────────────────────────────────────────────────────────
HIVE_ROOT = r'\\hive3065\Yael_Mishael\Rony\remote_computer backup'
HIVE_BASE = os.path.join(HIVE_ROOT, 'nnUNet_resources')
REPO_DIR  = r'C:\Users\rony.schwartz\Documents\nnUNet4SoilXrayCT'

vol_path  = os.path.join(HIVE_ROOT, '10.5', 'nlm_volume.tif')
pred_path = os.path.join(HIVE_BASE, 'bnei_reem_fresh_bnei_reem_i3',
                         'inference_concatenated', 'nlm_volume.nii.gz')
ann_path  = os.path.join(HIVE_BASE, 'fresh_train_annotations_bnei_reem',
                         'annotations_i3.nii.gz')
out_dir   = os.path.join(REPO_DIR, 'analysis', 'synopsis_i3')
os.makedirs(out_dir, exist_ok=True)

for name, path in [('vol', vol_path), ('pred', pred_path), ('ann', ann_path)]:
    assert os.path.isfile(path), f'Missing {name}: {path}'

# ── Class metadata ─────────────────────────────────────────────────────────────
with open(os.path.join(REPO_DIR, 'dataset_info.json')) as f:
    info = json.load(f)

class_names  = {int(k): v for k, v in info['labels'].items()}
# Normalise colours to [0,1]
class_colors_rgb = {int(k): [c / 255.0 for c in v]
                    for k, v in info['colors'].items()}

# ListedColormap: index == label value (0-6)
#   index 0 → fully transparent (unannotated background)
#   indices 1-6 → class colours at 65% opacity
cmap_rgba = [(0.0, 0.0, 0.0, 0.0)]          # label 0: transparent
for lbl in range(1, 7):
    r, g, b = class_colors_rgb[lbl]
    cmap_rgba.append((r, g, b, 0.65))
label_cmap = ListedColormap(cmap_rgba)

# Legend: skip class 0 (unannotated) and class 5 (unused)
legend_patches = [
    mpatches.Patch(
        facecolor=(*class_colors_rgb[k], 0.85),
        edgecolor='white',
        linewidth=0.6,
        label=f'{k} — {class_names[k]}',
    )
    for k in sorted(class_names) if k not in (0, 5)
]

# ── NIfTI → (Z,Y,X) with Y-flip ───────────────────────────────────────────────
def _nii_to_zyx(arr):
    arr = np.transpose(arr, (2, 1, 0))   # (X,Y,Z) → (Z,Y,X)
    arr = np.flip(arr, axis=1)            # correct scan-direction Y-flip
    return np.ascontiguousarray(arr)

# ── Load data ──────────────────────────────────────────────────────────────────
print('Loading volume TIF ...')
vol = tifffile.imread(vol_path)           # (Z, Y, X) uint16
print(f'  shape: {vol.shape}  dtype: {vol.dtype}')

print('Loading annotation NIfTI ...')
ann = _nii_to_zyx(nib.load(ann_path).get_fdata().astype(np.uint8))
ann = np.ascontiguousarray(np.flip(ann, axis=1))   # undo extra Y-flip; TIF has no flip
print(f'  shape: {ann.shape}  labels: {np.unique(ann).tolist()}')

print('Loading prediction NIfTI ...')
pred_raw = nib.load(pred_path).get_fdata().astype(np.uint8)
pred = _nii_to_zyx(pred_raw)
pred = (pred.astype(np.int16) + 1).clip(0, 6).astype(np.uint8)
print(f'  shape: {pred.shape}  labels: {np.unique(pred).tolist()}')

# Sanity-check shapes align
assert vol.shape == ann.shape == pred.shape, (
    f'Shape mismatch: vol={vol.shape} ann={ann.shape} pred={pred.shape}'
)

# ── Annotated slices ───────────────────────────────────────────────────────────
ann_slices = [z for z in range(ann.shape[0]) if ann[z].any()]
print(f'\nAnnotated slices: {len(ann_slices)}  '
      f'(z = {ann_slices[0]} … {ann_slices[-1]})')

# ── Rendering helper ───────────────────────────────────────────────────────────
BG = '#111111'

def render_overlay(ax, ct_slice, mask, title):
    """Draw grayscale CT with coloured label overlay."""
    ax.imshow(ct_slice, cmap='gray', interpolation='nearest',
              vmin=np.percentile(ct_slice, 1),
              vmax=np.percentile(ct_slice, 99))
    ax.imshow(mask, cmap=label_cmap, vmin=0, vmax=6,
              interpolation='nearest')
    ax.set_title(title, fontsize=9, fontweight='bold', color='white', pad=5)
    ax.axis('off')

# ── Export ─────────────────────────────────────────────────────────────────────
print(f'Writing {len(ann_slices)} PNGs to:\n  {out_dir}\n', flush=True)

for idx, z in enumerate(ann_slices):
    ct  = vol[z]
    a   = ann[z]
    p   = pred[z]

    fig, axes = plt.subplots(1, 3, figsize=(15, 5.2),
                             gridspec_kw={'wspace': 0.04})
    fig.patch.set_facecolor(BG)

    # Panel 1 — Raw CT
    axes[0].imshow(ct, cmap='gray', interpolation='nearest',
                   vmin=np.percentile(ct, 1), vmax=np.percentile(ct, 99))
    axes[0].set_title('Raw CT', fontsize=9, fontweight='bold',
                      color='white', pad=5)
    axes[0].axis('off')

    # Panel 2 — GT Annotations
    render_overlay(axes[1], ct, a, 'GT Annotations  (i3)')

    # Panel 3 — Prediction
    render_overlay(axes[2], ct, p, 'Prediction  (fresh_bnei_reem_i3)')

    # Super-title
    fig.suptitle(
        f'nlm_volume   |   Z-slice {z:04d}   '
        f'({idx + 1} / {len(ann_slices)})',
        fontsize=11, fontweight='bold', color='white', y=1.00,
    )

    # Legend
    fig.legend(
        handles=legend_patches,
        loc='lower center',
        ncol=len(legend_patches),
        fontsize=9,
        framealpha=0.25,
        edgecolor='#888888',
        labelcolor='white',
        bbox_to_anchor=(0.5, -0.07),
        handlelength=1.4,
        handleheight=1.0,
    )

    out_path = os.path.join(out_dir, f'slice_{z:04d}.png')
    plt.savefig(out_path, dpi=120, bbox_inches='tight',
                facecolor=BG, pad_inches=0.15)
    plt.close(fig)

    if idx == 0 or (idx + 1) % 100 == 0 or idx == len(ann_slices) - 1:
        print(f'  [{idx + 1:>3}/{len(ann_slices)}]  z={z:04d}  ->  '
              f'{os.path.basename(out_path)}')

print(f'\n[DONE] {len(ann_slices)} images in {out_dir}')
