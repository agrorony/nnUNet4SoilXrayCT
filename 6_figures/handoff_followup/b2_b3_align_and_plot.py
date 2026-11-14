"""Part B2 + B3: write aligned copies and one evidence PNG per (primary) segmentation.

B2: for every primary segmentation whose two B1 scores agree on a non-identity transform, write
    <name>_aligned.<ext> next to the original (same dtype). NIfTI: the image's affine + header when the
    reference is a packaged NIfTI of the same shape, otherwise the segmentation's own affine/header.
    Asserts label set and per-label voxel counts are unchanged, after re-reading the written file.
B3: PNG per segmentation. Rows: axes 0/1/2 (mid-slice). Columns: raw | before (pore red, POM green outlines)
    | after | 150x150 px zooms of the after overlay at the 25 %, 50 % and 75 % slices.

Usage: python b2_b3_align_and_plot.py <B1_transforms.json> <package_dir> <cache_dir> <evidence_dir> [--no-write]
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b1_find_transforms as b1  # noqa: E402


def outlines(lbl2d, value):
    from skimage.segmentation import find_boundaries
    return find_boundaries(lbl2d == value, mode='inner')


def overlay(img2d, seg2d, pore, pom, lo, hi):
    g = np.clip((img2d - lo) / (hi - lo + 1e-12), 0, 1)
    rgb = np.stack([g, g, g], -1)
    rgb[outlines(seg2d, pore)] = (1, 0, 0)
    if pom is not None:
        rgb[outlines(seg2d, pom)] = (0, 1, 0)
    return rgb


def zoom_window(seg2d, pore, pom, size=150):
    from scipy.ndimage import uniform_filter
    tgt = (seg2d == pom) if pom is not None and (seg2d == pom).any() else outlines(seg2d, pore)
    h, w = seg2d.shape
    if h <= size or w <= size:
        return 0, 0
    dens = uniform_filter(tgt.astype(np.float32), size=size, mode='constant')
    half = size // 2
    dens[:half, :] = dens[-half:, :] = 0; dens[:, :half] = dens[:, -half:] = 0
    cy, cx = np.unravel_index(np.argmax(dens), dens.shape)
    return int(cy - half), int(cx - half)


def take(a, axis, idx):
    return np.take(a, idx, axis=axis)


def work(args):
    x, pkg, cache, evid, write = args
    b1.init(pkg, cache, None)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    s = x['spec']
    img = b1.ref_image(s)
    seg = b1.load_rel(s['seg'])
    pore = s['pore']
    pom = None if seg.dtype == bool else 2
    base, ch = x['baseline'], x['best_by_r']
    before = b1.apply_t(seg, base['perm'], base['flips'])
    after = b1.apply_t(seg, ch['perm'], ch['flips'])
    is_identity = ch['perm'] == [0, 1, 2] and not any(ch['flips'])
    rec = dict(name=s['name'], seg=s['seg'], transform=dict(perm=ch['perm'], flips=ch['flips']), agree=x['agree'],
               identity=is_identity, aligned_path=None, label_counts_identical=None)

    # ---- B2
    v0, c0 = np.unique(seg, return_counts=True)
    va, ca = np.unique(after, return_counts=True)
    same = bool(np.array_equal(v0, va) and np.array_equal(c0, ca))
    rec['label_counts_identical'] = same
    rec['label_counts'] = {str(int(v)): int(c) for v, c in zip(v0, c0)}
    if write and x['agree'] and not is_identity:
        assert same, s['name']
        src = Path(pkg) / s['seg']
        if src.name.endswith('.nii.gz'):
            import nibabel as nib
            out = src.with_name(src.name[:-7] + '_aligned.nii.gz')
            seg_nii = nib.load(str(src))
            imgsrc = s['image'][4:] if s['image'].startswith('PKG:') else None
            if s.get('block_to') is None and imgsrc and imgsrc.endswith('.nii.gz') and \
                    tuple(nib.load(str(Path(pkg) / imgsrc)).shape) == after.shape:
                ref = nib.load(str(Path(pkg) / imgsrc))
                hdr = ref.header.copy(); aff = ref.affine.copy(); rec['header_from'] = 'image'
            else:
                hdr = seg_nii.header.copy(); aff = seg_nii.affine.copy(); rec['header_from'] = 'segmentation (no NIfTI image of this shape)'
            hdr.set_data_dtype(seg.dtype)
            nii = nib.Nifti1Image(np.ascontiguousarray(after), aff, header=hdr)
            nii.header.set_slope_inter(1, 0)
            nib.save(nii, str(out))
            back = np.asanyarray(nib.load(str(out)).dataobj)
        else:
            out = src.with_name(src.stem + '_aligned.npy')
            np.save(out, np.ascontiguousarray(after))
            back = np.load(out)
            rec['header_from'] = 'n/a (.npy)'
        assert back.dtype == seg.dtype and back.shape == after.shape and np.array_equal(back, after), s['name']
        vb, cb = np.unique(back, return_counts=True)
        assert np.array_equal(vb, v0) and np.array_equal(cb, c0), s['name']
        rec['aligned_path'] = str(out)

    # ---- B3
    lo, hi = np.percentile(img[::4, ::4, ::4], [1, 99])
    fb, fc = x['full']['baseline'], x['full']['chosen']
    fmt = lambda v: 'n/c' if v is None else f'{v:+.3f}'
    tr = f"perm {tuple(ch['perm'])}, flip axes {[i for i, f in enumerate(ch['flips']) if f] or 'none'}"
    base_lbl = 'as stored' if x['baseline_is_identity'] else 'as stored, axes reversed (TIF z,y,x vs NIfTI x,y,z)'
    title = (f"{s['name']}  —  {s['seg']}\n"
             f"transform found: {tr}   |   scores agree: {'yes' if x['agree'] else 'NO (flagged, not fixed)'}   |   "
             f"r before→after {fmt(fb['r'])} → {fmt(fc['r'])}   |   Otsu-Dice before→after {fmt(fb['dice'])} → {fmt(fc['dice'])}   |   "
             f"label counts identical: {'yes' if same else 'NO'}\n"
             f"before = {base_lbl}; image: {s['note'] or s['image'].split('/')[-1]}; pore = red, POM = green")
    fig, axs = plt.subplots(3, 6, figsize=(27, 13.5))
    for ax_i in range(3):
        n = img.shape[ax_i]
        mid = n // 2
        im2 = take(img, ax_i, mid)
        axs[ax_i, 0].imshow(im2, cmap='gray', vmin=lo, vmax=hi)
        axs[ax_i, 0].set_title(f'raw, axis {ax_i} slice {mid}', fontsize=9)
        if before.shape == img.shape:
            axs[ax_i, 1].imshow(overlay(im2, take(before, ax_i, mid), pore, pom, lo, hi))
            axs[ax_i, 1].set_title('BEFORE fix', fontsize=9)
        else:
            axs[ax_i, 1].text(0.5, 0.5, 'n/c (shape differs)', ha='center'); axs[ax_i, 1].set_title('BEFORE fix', fontsize=9)
        axs[ax_i, 2].imshow(overlay(im2, take(after, ax_i, mid), pore, pom, lo, hi))
        axs[ax_i, 2].set_title('AFTER fix', fontsize=9)
        for k, frac in enumerate((0.25, 0.5, 0.75)):
            idx = int(round(frac * (n - 1)))
            sl_img = take(img, ax_i, idx); sl_seg = take(after, ax_i, idx)
            y0, x0 = zoom_window(sl_seg, pore, pom)
            ov = overlay(sl_img[y0:y0 + 150, x0:x0 + 150], sl_seg[y0:y0 + 150, x0:x0 + 150], pore, pom, lo, hi)
            axs[ax_i, 3 + k].imshow(ov, interpolation='nearest')
            axs[ax_i, 3 + k].set_title(f'AFTER zoom 150px, slice {idx} ({int(frac*100)} %), y{y0} x{x0}', fontsize=9)
    for a in axs.ravel():
        a.set_xticks([]); a.set_yticks([])
    fig.suptitle(title, fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    safe = s['name'].replace(' ', '_').replace('/', '_')
    png = Path(evid) / f"B3_{safe}.png"
    fig.savefig(png, dpi=72)
    plt.close(fig)
    rec['png'] = str(png)
    rec['full'] = x['full']
    return rec


def main():
    j, pkg, cache, evid = sys.argv[1:5]
    write = '--no-write' not in sys.argv
    res = [x for x in json.load(open(j)) if x['spec']['primary']]
    with ProcessPoolExecutor(max_workers=8) as ex:
        recs = list(ex.map(work, [(x, pkg, cache, evid, write) for x in res]))
    json.dump(recs, open(Path(evid) / 'B2_B3_results.json', 'w'), indent=1)
    for i, r in enumerate(recs, 1):
        print(i, r['name'], r['transform'], 'agree' if r['agree'] else 'DISAGREE', 'identity' if r['identity'] else '',
              'counts_same' if r['label_counts_identical'] else 'COUNTS DIFFER', r['aligned_path'], r['png'])


if __name__ == '__main__':
    main()
