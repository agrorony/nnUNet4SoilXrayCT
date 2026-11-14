"""Part B1: find, for every segmentation in the package, the signed axis permutation that maps it onto its image.

For each (segmentation, reference image) pair, every signed axis permutation (48) whose transformed shape
equals the image shape is scored on stride-4 views in two independent ways:
  (a) point-biserial r between image intensity and the pore mask (pores dark -> most negative r wins)
  (b) Dice between the transformed pore mask and a fresh global-Otsu mask of the image (dark = pore)
The winner must be the same on both scores, otherwise the file is flagged and not fixed.
Both scores are then recomputed at full resolution for the identity (or, if identity is shape-incompatible,
the plain axis reversal) and for the chosen transform.

Sparse annotation files (annotation space, labelsTr) are scored only over labelled voxels (diagnostic).

Reference images for 15 um label-downsamples are block means of the source image using the same
partition as the downsampling code (edges = round(linspace(0, n, m+1)), downsample_common.py).

Usage: python b1_find_transforms.py <package_dir> <cache_dir> <repo_dir> <out_json>
"""
import itertools
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

PKG = CACHE = REPO = None


def cache_path(rel):
    return Path(CACHE) / (rel.replace('/', '__') + '.npy')


def load_rel(rel):
    p = cache_path(rel)
    if p.exists():
        return np.load(p)
    import nibabel as nib
    return np.asanyarray(nib.load(str(Path(PKG) / rel)).dataobj)


def block_mean(vol, m):
    n = vol.shape[0]
    assert vol.shape == (n, n, n)
    edges = np.round(np.linspace(0, n, m + 1)).astype(np.int64)
    starts = edges[:-1]
    a = np.add.reduceat(vol.astype(np.float64), starts, axis=0)
    a = np.add.reduceat(a, starts, axis=1)
    a = np.add.reduceat(a, starts, axis=2)
    w = np.diff(edges).astype(np.float64)
    a /= w[:, None, None]; a /= w[None, :, None]; a /= w[None, None, :]
    return a.astype(np.float32)


def ref_image(spec):
    """Return the reference image array for a pair spec (cached on disk)."""
    src = spec['image']
    if spec.get('block_to') is None:
        if src.startswith('PKG:'):
            return load_rel(src[4:])
        raise ValueError(src)
    cp = Path(CACHE) / f"ref_{spec['name']}_bm{spec['block_to']}.npy"
    if cp.exists():
        return np.load(cp)
    if src.startswith('PKG:'):
        vol = load_rel(src[4:])
    else:
        import nibabel as nib
        vol = np.asanyarray(nib.load(src[5:]).dataobj)  # 'FILE:' absolute path, read-only
    out = block_mean(vol, spec['block_to'])
    np.save(cp, out)
    return out


def signed_perms():
    for perm in itertools.permutations(range(3)):
        for flips in itertools.product([False, True], repeat=3):
            yield perm, flips


def apply_t(a, perm, flips):
    a = np.transpose(a, perm)
    return a[tuple(slice(None, None, -1) if f else slice(None) for f in flips)]


def masks(seg, spec):
    pore = seg == spec['pore']
    if spec['labelled'] == 'all':
        valid = None
    elif spec['labelled'] == 'nonzero':
        valid = seg != 0
    elif spec['labelled'] == 'not6':
        valid = seg != 6
    return pore, valid


def scores(img, pore, valid, otsu_mask):
    if valid is not None:
        img = img[valid]; pore = pore[valid]; otsu_mask = otsu_mask[valid]
    x = img.astype(np.float64).ravel(); y = pore.astype(np.float64).ravel()
    x = x - x.mean(); y = y - y.mean()
    den = np.sqrt((x @ x) * (y @ y))
    r = float((x @ y) / den) if den > 0 else float('nan')
    s = int(pore.sum()) + int(otsu_mask.sum())
    d = float(2 * np.logical_and(pore, otsu_mask).sum() / s) if s else float('nan')
    return r, d


def run(spec):
    from skimage.filters import threshold_otsu
    img = ref_image(spec)
    seg = load_rel(spec['seg'])
    t = float(threshold_otsu(img[::2, ::2, ::2]))
    otsu = img < t
    pore, valid = masks(seg, spec)
    cands = []
    st = (slice(None, None, 4),) * 3
    for perm, flips in signed_perms():
        P = apply_t(pore, perm, flips)
        if P.shape != img.shape:
            continue
        V = apply_t(valid, perm, flips)[st] if valid is not None else None
        r, d = scores(img[st], P[st], V, otsu[st])
        cands.append(dict(perm=list(perm), flips=list(flips), r=r, dice=d))
    best_r = min(cands, key=lambda c: c['r'] if not np.isnan(c['r']) else 9)
    best_d = max(cands, key=lambda c: c['dice'] if not np.isnan(c['dice']) else -9)
    agree = best_r['perm'] == best_d['perm'] and best_r['flips'] == best_d['flips']
    ident_ok = seg.shape == img.shape
    base = dict(perm=[0, 1, 2], flips=[False] * 3) if ident_ok else dict(perm=[2, 1, 0], flips=[False] * 3)
    full = {}
    for tag, tr in (('baseline', base), ('chosen', best_r)):
        P = apply_t(pore, tr['perm'], tr['flips'])
        V = apply_t(valid, tr['perm'], tr['flips']) if valid is not None else None
        if P.shape != img.shape:
            full[tag] = dict(r=None, dice=None); continue
        r, d = scores(img, P, V, otsu)
        full[tag] = dict(r=r, dice=d)
    sr = sorted(c['r'] for c in cands if not np.isnan(c['r']))
    sd = sorted((c['dice'] for c in cands if not np.isnan(c['dice'])), reverse=True)
    return dict(spec=spec, seg_shape=list(seg.shape), img_shape=list(img.shape), otsu_threshold=t,
                n_candidates=len(cands), candidates=cands,
                best_by_r=best_r, best_by_dice=best_d, agree=agree,
                runner_up_r=sr[1] if len(sr) > 1 else None, runner_up_dice=sd[1] if len(sd) > 1 else None,
                baseline=base, baseline_is_identity=ident_ok, full=full)


def build_specs(repo):
    V = '01_volumes/'
    # 2026-11 layout; the large ROI inputs (nifti_predict/, gitignored) are still under the pre-2026-11 path on the lab computer
    roi = Path(repo) / 'archive/5_analysis/pom_clustering_retired/pom_analysis_20260829_roi_expansion/pipeline_work'
    old = Path(repo) / '05_evaluation/psd/pom_analysis_20260829_roi_expansion/pipeline_work'
    if not (roi / 'mishmar_native_5p85um' / 'nifti_predict').is_dir() and old.is_dir():
        roi = old
    S = []

    def add(name, seg, image, pore=5, labelled='all', block_to=None, primary=True, note=''):
        S.append(dict(name=name, seg=seg, image=image, pore=pore, labelled=labelled, block_to=block_to, primary=primary, note=note))

    add('Cu011_samp_2', V + 'Cu011_samp_2/segmentation.nii.gz', 'PKG:' + V + 'Cu011_samp_2/image_preprocessed.nii.gz')
    for r in ('Rehovot_samp2_highkV_Cu0.11_15um', 'Rehovot_samp3_highkV_Cu0.11_15um'):
        im = 'PKG:' + V + r + '/image_preprocessed.nii.gz'
        add(r + ' nnU-Net i4', V + r + '/segmentation_nnunet_bnei_reem_i4.nii.gz', im)
        add(r + ' nnU-Net loess_i2', V + r + '/segmentation_nnunet_loess_i2.nii.gz', im)
        add(r + ' Otsu', V + r + '/segmentation_otsu.npy', im, pore=1)
    add('bnei_reem canonical', V + 'bnei_reem_fresh_bnei_reem_i4/segmentation.nii.gz', 'PKG:' + V + 'bnei_reem_fresh_bnei_reem_i4/image_preprocessed.tif')
    add('bnei_reem specA', V + 'bnei_reem_specA_unified/segmentation.nii.gz', 'PKG:' + V + 'bnei_reem_specA_unified/image_preprocessed.nii.gz')
    add('bnei_reem specB', V + 'bnei_reem_specB_unified/segmentation.nii.gz', 'PKG:' + V + 'bnei_reem_specB_unified/image_preprocessed.nii.gz')
    for m, (pm, tm, roiname, roin) in {'mishmar_hanegev_maoz_3_5p85um': (390, 474, 'mishmar_native_5p85um', 1216),
                                        'mishmar_hanegev_maoz_2_8p8um': (587, 947, 'mishmar_second_8p8um', 1614)}.items():
        im = 'PKG:' + V + m + '/image_preprocessed.nii.gz'
        add(m, V + m + '/segmentation.nii.gz', im)
        add(m + ' 15um_pom', V + m + '/segmentation_15um_pom.nii.gz', im, block_to=pm, note='image = block mean of packaged 1000^3 image')
        add(m + ' 15um_trackE', V + m + '/segmentation_15um_trackE.nii.gz', 'FILE:' + str(roi / roiname / 'nifti_predict' / f'{roiname}_0000.nii.gz'),
            block_to=tm, note=f'image = block mean of ROI-expanded {roin}^3 model input (not packaged)')
    # diagnostics only (sparse / training data)
    A = '02_annotations/'
    can = 'PKG:' + V + 'bnei_reem_fresh_bnei_reem_i4/image_preprocessed.tif'
    for f in ('original_annotations/annotations_i2', 'original_annotations/annotations_i3', 'original_annotations/fine_tuning_annotations',
              'registry_merged_GT/merged_GT'):
        add('i4 ' + f.split('/')[-1], A + 'bnei_reem_i4/' + f + '.nii.gz', can, pore=6, labelled='nonzero', primary=False)
    add('i4 labelsTr', A + 'bnei_reem_i4/nnUNet_raw_Dataset777_GCEF/labelsTr/nlm_volume.nii.gz',
        'PKG:' + A + 'bnei_reem_i4/nnUNet_raw_Dataset777_GCEF/imagesTr/nlm_volume_0000.nii.gz', labelled='not6', primary=False)
    add('i4 validation', '03_models/bnei_reem_i4/nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss_lowlr__nnUNetPlans__3d_fullres/fold_0/validation/nlm_volume.nii.gz',
        'PKG:' + A + 'bnei_reem_i4/nnUNet_raw_Dataset777_GCEF/imagesTr/nlm_volume_0000.nii.gz', primary=False)
    lim = 'PKG:' + V + 'mishmar_hanegev_maoz_3_5p85um/image_preprocessed.nii.gz'
    for f in ('mishmar_hanegev_maoz_3_5p85um', 'mishmar_hanegev_maoz_3_5p85um-1'):
        add('loess_i2 annot ' + f[-2:], A + 'mishmar_loess_i2/original_annotations/' + f + '.nii.gz', lim, pore=6, labelled='nonzero', primary=False)
    add('loess_i2 labelsTr', A + 'mishmar_loess_i2/nnUNet_raw_Dataset777_GCEF/labelsTr/mishmar_hanegev_maoz_3_5p85um.nii.gz',
        'PKG:' + A + 'mishmar_loess_i2/nnUNet_raw_Dataset777_GCEF/imagesTr/mishmar_hanegev_maoz_3_5p85um_0000.nii.gz', labelled='not6', primary=False)
    add('loess_i2 validation', '03_models/mishmar_loess_i2/nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss__nnUNetPlans__3d_fullres/fold_0/validation/mishmar_hanegev_maoz_3_5p85um.nii.gz',
        'PKG:' + A + 'mishmar_loess_i2/nnUNet_raw_Dataset777_GCEF/imagesTr/mishmar_hanegev_maoz_3_5p85um_0000.nii.gz', primary=False)
    return S


def init(p, c, r):
    global PKG, CACHE, REPO
    PKG, CACHE, REPO = p, c, r


def main():
    pkg, cache, repo, out = sys.argv[1:5]
    init(pkg, cache, repo)
    specs = build_specs(repo)
    # build the two expensive ROI-expanded references first (one process each), then everything in parallel
    heavy = [s for s in specs if s['image'].startswith('FILE:')]
    with ProcessPoolExecutor(max_workers=len(heavy), initializer=init, initargs=(pkg, cache, repo)) as ex:
        list(ex.map(ref_image, heavy))
    with ProcessPoolExecutor(max_workers=12, initializer=init, initargs=(pkg, cache, repo)) as ex:
        res = list(ex.map(run, specs))
    json.dump(res, open(out, 'w'), indent=1)
    print(f"{'name':48s} {'chosen':28s} agree  r(4) base->chosen(full)       dice base->chosen(full)   runner-up r / dice")
    for x in res:
        b = x['best_by_r']; f = x['full']
        fmt = lambda v: 'n/c' if v is None else f'{v:+.4f}'
        print(f"{x['spec']['name']:48s} perm={b['perm']} flip={[int(v) for v in b['flips']]}  {'YES' if x['agree'] else 'NO '}  "
              f"{fmt(f['baseline']['r'])} -> {fmt(f['chosen']['r'])}   {fmt(f['baseline']['dice'])} -> {fmt(f['chosen']['dice'])}   "
              f"{x['runner_up_r']:+.4f} / {x['runner_up_dice']:.4f}  {'(diag)' if not x['spec']['primary'] else ''}")


if __name__ == '__main__':
    main()
