"""Part B4 (docs): update the package READMEs after the re-orientation swap.

- backs up each README it changes to <backup_dir>/<relative path> first
- volume READMEs: replaces "## Alignment check (hand-off, read-only)" with "## Orientation (re-oriented <date>)",
  removes flip/transpose instructions from the napari snippets, updates sha256/size/shape in the Files table,
  adds the old->new axis mapping for files whose axes were reordered (Otsu masks, canonical)
- top-level README: Quick start snippet, the orientation warning and the Known-limitations bullet

Usage: python b4_update_readmes.py <package_dir> <B4_swap_log.json> <B2_B3_results.json> <backup_dir> <date>
"""
import json
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path


def tr_text(t):
    perm, flips = tuple(t['perm']), [i for i, f in enumerate(t['flips']) if f]
    parts = []
    if perm != (0, 1, 2):
        parts.append(f'axes reordered {perm}')
    if flips:
        parts.append('flip axis ' + ', '.join(map(str, flips)))
    return ' + '.join(parts) or 'none'


def inverse_code(t, var):
    perm, flips = tuple(t['perm']), [i for i, f in enumerate(t['flips']) if f]
    code = var
    for ax in flips:
        code = f'np.flip({code}, axis={ax})'
    if perm != (0, 1, 2):
        inv = [perm.index(i) for i in range(3)]
        code = f'{code}.transpose{tuple(inv)}'
    return code


def size_txt(n):
    return f'{n / 1e9:.2f} GB' if n >= 1e9 else f'{n / 1e6:.1f} MB'


def main():
    pkg, swap_log, res_json, bak, date = sys.argv[1:6]
    pkg, bak = Path(pkg), Path(bak)
    swaps = {s['file']: s for s in json.load(open(swap_log))}
    res = {r['seg']: r for r in json.load(open(res_json))}
    by_dir = defaultdict(list)
    for f in swaps:
        by_dir[str(Path(f).parent).replace('\\', '/')].append(f)

    def backup(p):
        rel = p.relative_to(pkg)
        dst = bak / rel
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dst)

    for d, files in sorted(by_dir.items()):
        rp = pkg / d / 'README.md'
        backup(rp)
        txt = rp.read_text(encoding='utf-8')
        # ---- orientation section
        rows, mapping, inverses = [], [], []
        transforms = sorted({tr_text(res[f]['transform']) for f in files})
        for f in sorted(files):
            r = res[f]; t = r['transform']; fb, fc = r['full']['baseline'], r['full']['chosen']
            fn = Path(f).name
            rows.append(f"| `{fn}` | {tr_text(t)} | {fb['r']:+.3f} → {fc['r']:+.3f} | {fb['dice']:.3f} → {fc['dice']:.3f} | {'yes' if r['label_counts_identical'] else 'NO'} |")
            inverses.append(f"- `{fn}`: `old = {inverse_code(t, 'new')}`")
            if tuple(t['perm']) != (0, 1, 2):
                inv = {old: t['perm'].index(old) for old in range(3)}
                mapping.append(f"- `{fn}`: old axis 0 = new axis {inv[0]}, old axis 1 = new axis {inv[1]}, old axis 2 = new axis {inv[2]}.")
        canon_note = ''
        if 'bnei_reem_fresh_bnei_reem_i4' in d:
            canon_note = ('The image is a TIFF read as (Z, Y, X) = (652, 650, 650); the segmentation is now stored in that same axis order '
                          '(652×650×650), so `tifffile.imread()` and `nib.load()` overlay without any transpose.\n\n')
        sec = [f'## Orientation (re-oriented {date})',
               f'Segmentations were re-oriented to their images on {date} (transform: {"; ".join(transforms)}). '
               'The copies on the share are still in the original orientation.', '',
               canon_note + 'How the transform was found: every signed axis permutation (48) that gives a matching shape was scored on '
               'stride-4 views by (a) the point-biserial r between image intensity and the pore mask (pores are dark, so the right '
               'orientation gives the most negative r) and (b) Dice against a fresh global-Otsu mask of the image. Both scores picked the '
               'same transform for every file, and Rony confirmed the overlays visually (hand-off follow-up, Gate B). Scores below are at '
               'full resolution, stored (before) vs packaged (after):', '',
               '| File | Transform applied | r before → after | Otsu-Dice before → after | Label counts identical |',
               '|---|---|---|---|---|'] + rows + ['',
               'A flip or axis reordering only moves voxels: label values and per-label voxel counts are unchanged (checked), so no '
               'metric was recomputed. To get the share (pre-' + date + ') orientation back from a packaged array `new`:'] + inverses
        if mapping:
            sec += ['', '**Per-axis results.** Any per-axis result computed on the old file (e.g. tortuosity per axis in the Track E runs '
                    'or the 2026-10-04 subvolume tortuosity, whose axes are the numpy array axes of the stored file) refers to the old axis order:'] + mapping
        sec_txt = '\n'.join(sec) + '\n'
        txt, n = re.subn(r'## Alignment check \(hand-off, read-only\)\n.*?(?=\n## )', sec_txt.rstrip('\n') + '\n', txt, flags=re.S)
        assert n == 1, rp
        # ---- napari snippet
        txt = re.sub(r'np\.flip\((np\.asarray\(nib\.load\("[^"]+"\)\.dataobj\)), axis=1\)[ \t]*#[^\n]*',
                     r'\1  # stored in the image orientation (re-oriented ' + date + ')', txt)
        txt = txt.replace('np.load("segmentation_otsu.npy").transpose(2, 1, 0).astype(np.uint8)  # 1 = pore; axes reversed vs image',
                          'np.load("segmentation_otsu.npy").astype(np.uint8)  # 1 = pore; stored in the image orientation (re-oriented ' + date + ')')
        txt = txt.replace('tifffile.imread("image_preprocessed.tif").transpose(2, 1, 0)  # TIFF (Z,Y,X) -> NIfTI axis order',
                          'tifffile.imread("image_preprocessed.tif")  # (Z,Y,X) = (652, 650, 650); the segmentation is stored in this axis order')
        assert 'np.flip(' not in txt.split('## How to open it')[-1] and '.transpose(2, 1, 0)' not in txt.split('## How to open it')[-1], rp
        # ---- Known issues bullet (Rehovot)
        txt = txt.replace("- `missing_data_20261004/REPORT.md` found that the `.npy` needed axis permutation (2,1,0) to line up with the raw NIfTI; see the alignment check above before overlaying.",
                          f"- `missing_data_20261004/REPORT.md` found that the `.npy` needed axis permutation (2,1,0) to line up with the raw NIfTI. The packaged `.npy` has been re-oriented ({date}, see *Orientation*); the copy on the share still needs it.")
        # ---- Files table
        for f in files:
            fn = Path(f).name
            s = swaps[f]
            p = pkg / f
            nbytes = p.stat().st_size
            pat = re.compile(r'^\| `' + re.escape(fn) + r'` \|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|$', re.M)
            m = pat.search(txt)
            assert m, (rp, fn)
            shape = m.group(1)
            if 'bnei_reem_fresh_bnei_reem_i4' in d and fn == 'segmentation.nii.gz':
                shape = ' 652×650×650 '
            new = f"| `{fn}` |{shape}|{m.group(2)}|{m.group(3)}| {size_txt(nbytes)} | `{s['new_sha256'][:16]}…` |"
            txt = txt[:m.start()] + new + txt[m.end():]
        rp.write_text(txt, encoding='utf-8')
        print('updated', rp.relative_to(pkg))

    # ---- top-level README
    rp = pkg / 'README.md'
    backup(rp)
    txt = rp.read_text(encoding='utf-8')
    old_snip = 'seg = np.flip(np.asarray(nib.load("01_volumes/bnei_reem_specA_unified/segmentation.nii.gz").dataobj), axis=1)'
    assert old_snip in txt
    txt = txt.replace(old_snip, 'seg = np.asarray(nib.load("01_volumes/bnei_reem_specA_unified/segmentation.nii.gz").dataobj)')
    txt, n = re.subn(r'⚠ \*\*Every nnU-Net segmentation, read as an array, is flipped along axis 1 relative to its image\*\*[^\n]*',
                     f'**Orientation.** Segmentations were re-oriented to their images on {date} (transform: flip axis 1 for every nnU-Net '
                     'segmentation and 15 µm label-downsample; axes reordered (2, 1, 0) for the two Rehovot Otsu masks; for the Vertisol '
                     '"canonical" segmentation flip axis 1 plus axes reordered (2, 1, 0) so it matches its TIFF image). The copies on the share '
                     'are still in the original orientation. Images and segmentations in this package overlay as stored, with no flip. The metrics '
                     'were computed on the label volumes alone and are not affected (label counts are unchanged). Per-axis results computed on '
                     'the old Otsu or canonical files use the old axis order; the mapping is in those volumes\' READMEs.', txt)
    assert n == 1
    txt, n = re.subn(r'- \*\*Segmentation orientation:\*\* stored segmentations are flipped on axis 1 relative to their images \(see Quick start\)\.',
                     f'- **Segmentation orientation:** re-oriented to their images on {date} in this package; copies on the share are still flipped (see Quick start).', txt)
    assert n == 1
    rp.write_text(txt, encoding='utf-8')
    print('updated README.md')


if __name__ == '__main__':
    main()
