"""make_synopsis.py — consolidated per-slice synopsis PNG exporter (S7).

Replaces `_make_synopsis_i3.py` and `_make_synopsis_i4.py`. Renders one PNG
per annotated z-slice: [Raw CT] | [GT Annotations] | [Prediction], with a
class-colour legend from dataset_info.json.

Amendment D note: `_make_synopsis_i4.py` was misnamed — despite the "i4" in
its filename and its `analysis/synopsis_i4` output folder, it actually
processed `fresh_bnei_reem_i3_scratch` data (confirmed by reading its
hardcoded pred_path). The data it processes is NOT changed here; only the
label is corrected. Use `--iteration-name fresh_bnei_reem_i3_scratch` and
`--output-dir 06_reporting/synopsis_outputs/fresh_bnei_reem_i3_scratch_synopsis`
to reproduce what the old "i4" script actually did. A genuine i4-model
synopsis (if one is later wanted) should use
`--iteration-name fresh_bnei_reem_i4` with its own real prediction path.

Usage:
    python make_synopsis.py --iteration-name fresh_bnei_reem_i3 \
        --volume-path .../nlm_volume.tif \
        --annotation-path .../annotations_i3.nii.gz \
        --prediction-path .../nlm_volume.nii.gz \
        --output-dir ../synopsis_outputs/synopsis_i3
"""
import argparse
import json
import os

import numpy as np
import nibabel as nib
import tifffile
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import ListedColormap

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATASET_INFO_PATH = os.path.join(REPO_DIR, 'dataset_info.json')
BG = '#111111'


def nii_to_zyx(arr):
    arr = np.transpose(arr, (2, 1, 0))  # (X,Y,Z) -> (Z,Y,X)
    arr = np.flip(arr, axis=1)
    return np.ascontiguousarray(arr)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--iteration-name', required=True, help='Used only in panel/title labels.')
    parser.add_argument('--volume-path', required=True)
    parser.add_argument('--annotation-path', required=True)
    parser.add_argument('--prediction-path', required=True)
    parser.add_argument('--output-dir', required=True,
                         help='Default convention: 06_reporting/synopsis_outputs/{iteration_name}/')
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    for name, path in [('vol', args.volume_path), ('pred', args.prediction_path), ('ann', args.annotation_path)]:
        assert os.path.isfile(path), f'Missing {name}: {path}'

    with open(DATASET_INFO_PATH) as f:
        info = json.load(f)
    class_names = {int(k): v for k, v in info['labels'].items()}
    class_colors_rgb = {int(k): [c / 255.0 for c in v] for k, v in info['colors'].items()}

    cmap_rgba = [(0.0, 0.0, 0.0, 0.0)]
    for lbl in range(1, 7):
        r, g, b = class_colors_rgb[lbl]
        cmap_rgba.append((r, g, b, 0.65))
    label_cmap = ListedColormap(cmap_rgba)

    legend_patches = [
        mpatches.Patch(facecolor=(*class_colors_rgb[k], 0.85), edgecolor='white', linewidth=0.6,
                        label=f'{k} — {class_names[k]}')
        for k in sorted(class_names) if k not in (0, 5)
    ]

    print('Loading volume TIF ...')
    vol = tifffile.imread(args.volume_path)
    print(f'  shape: {vol.shape}  dtype: {vol.dtype}')

    print('Loading annotation NIfTI ...')
    ann = nii_to_zyx(nib.load(args.annotation_path).get_fdata().astype(np.uint8))
    ann = np.ascontiguousarray(np.flip(ann, axis=1))
    print(f'  shape: {ann.shape}  labels: {np.unique(ann).tolist()}')

    print('Loading prediction NIfTI ...')
    pred_raw = nib.load(args.prediction_path).get_fdata().astype(np.uint8)
    pred = nii_to_zyx(pred_raw)
    pred = (pred.astype(np.int16) + 1).clip(0, 6).astype(np.uint8)
    print(f'  shape: {pred.shape}  labels: {np.unique(pred).tolist()}')

    assert vol.shape == ann.shape == pred.shape, f'Shape mismatch: vol={vol.shape} ann={ann.shape} pred={pred.shape}'

    ann_slices = [z for z in range(ann.shape[0]) if ann[z].any()]
    print(f'\nAnnotated slices: {len(ann_slices)}  (z = {ann_slices[0]} … {ann_slices[-1]})')

    def render_overlay(ax, ct_slice, mask, title):
        ax.imshow(ct_slice, cmap='gray', interpolation='nearest',
                   vmin=np.percentile(ct_slice, 1), vmax=np.percentile(ct_slice, 99))
        ax.imshow(mask, cmap=label_cmap, vmin=0, vmax=6, interpolation='nearest')
        ax.set_title(title, fontsize=9, fontweight='bold', color='white', pad=5)
        ax.axis('off')

    sample_name = os.path.splitext(os.path.basename(args.volume_path))[0]
    print(f'Writing {len(ann_slices)} PNGs to:\n  {args.output_dir}\n', flush=True)

    for idx, z in enumerate(ann_slices):
        ct, a, p = vol[z], ann[z], pred[z]

        fig, axes = plt.subplots(1, 3, figsize=(15, 5.2), gridspec_kw={'wspace': 0.04})
        fig.patch.set_facecolor(BG)

        axes[0].imshow(ct, cmap='gray', interpolation='nearest', vmin=np.percentile(ct, 1), vmax=np.percentile(ct, 99))
        axes[0].set_title('Raw CT', fontsize=9, fontweight='bold', color='white', pad=5)
        axes[0].axis('off')

        render_overlay(axes[1], ct, a, 'GT Annotations')
        render_overlay(axes[2], ct, p, f'Prediction  ({args.iteration_name})')

        fig.suptitle(f'{sample_name}   |   Z-slice {z:04d}   ({idx + 1} / {len(ann_slices)})',
                     fontsize=11, fontweight='bold', color='white', y=1.00)
        fig.legend(handles=legend_patches, loc='lower center', ncol=len(legend_patches), fontsize=9,
                   framealpha=0.25, edgecolor='#888888', labelcolor='white',
                   bbox_to_anchor=(0.5, -0.07), handlelength=1.4, handleheight=1.0)

        out_path = os.path.join(args.output_dir, f'slice_{z:04d}.png')
        plt.savefig(out_path, dpi=120, bbox_inches='tight', facecolor=BG, pad_inches=0.15)
        plt.close(fig)

        if idx == 0 or (idx + 1) % 100 == 0 or idx == len(ann_slices) - 1:
            print(f'  [{idx + 1:>3}/{len(ann_slices)}]  z={z:04d}  ->  {os.path.basename(out_path)}')

    print(f'\n[DONE] {len(ann_slices)} images in {args.output_dir}')


if __name__ == '__main__':
    main()
