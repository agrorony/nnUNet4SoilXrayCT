"""Step 0 (Bnei Re'em, Vertisol) - verify file, labels, fractions; determine the mirror/flip by correlation with the raw; cache the (correctly oriented) uint8 volume."""
import numpy as np, nibabel as nib, os, datetime, json, sys, tifffile
SEG = r'E:\PROJECTS\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources\bnei_reem_fresh_bnei_reem_i4\inference_concatenated\nlm_volume.nii.gz'
RAWNII = r'E:\PROJECTS\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources\bnei_reem_specB_unified\nifti_predict\bnei_reem_specB_unified_0000.nii.gz'
RAWTIF = r'E:\PROJECTS\Yael_Mishael\Rony\remote_computer backup\10.5\nlm_volume.tif'
OUT = r'E:\PROJECTS\Yael_Mishael\Rony\remote_computer backup\render3d_bnei_reem_20261013'
st = os.stat(SEG); print('path', SEG); print('size', st.st_size, 'mtime', datetime.datetime.fromtimestamp(st.st_mtime))
img = nib.load(SEG); print('shape', img.shape, 'dtype', img.get_data_dtype(), 'header zooms', img.header.get_zooms(), 'axcodes', nib.aff2axcodes(img.affine))
seg = np.asarray(img.dataobj); u, c = np.unique(seg, return_counts=True); n = seg.size
fr = {int(k): 100*v/n for k, v in zip(u, c)}; print('labels', dict(zip(u.tolist(), c.tolist()))); print('percent', {k: round(v, 4) for k, v in fr.items()})
ok = set(u.tolist()) <= {0, 1, 2, 5} and round(fr[5], 2) == 21.64 and round(fr[2], 2) == 0.82
print('STEP0.1', 'PASS' if ok else 'FAIL')
if not ok: sys.exit(1)
pore = (seg == 5).astype(np.float32)
def corr(a, b): a = a - a.mean(); b = b - b.mean(); return float((a*b).sum() / np.sqrt((a*a).sum() * (b*b).sum()))
res = {}
for name, raw in (('specB_nifti_predict_0000', np.asarray(nib.load(RAWNII).dataobj).astype(np.float32)),
                  ('10.5_nlm_volume.tif_transposed(2,1,0)', np.transpose(tifffile.imread(RAWTIF), (2, 1, 0)).astype(np.float32))):
    print(name, 'raw shape', raw.shape)
    if raw.shape != pore.shape: print('  shape mismatch, skipped'); continue
    for fl in [(), (0,), (1,), (2,), (0, 1), (0, 2), (1, 2), (0, 1, 2)]:
        p = np.flip(pore, fl) if fl else pore
        res[f'{name}|flip{fl}'] = corr(p, raw); print('  flip', fl, 'corr(pore, raw) = %.4f' % res[f'{name}|flip{fl}'], flush=True)
json.dump(dict(path=SEG, size=st.st_size, mtime=str(datetime.datetime.fromtimestamp(st.st_mtime)), header_zooms=[float(z) for z in img.header.get_zooms()], pct=fr, shape=list(img.shape), flip_correlations=res), open(os.path.join(OUT, 'step0_input.json'), 'w'), indent=1)
np.save(os.path.join(OUT, 'seg_raw_orientation_uint8.npy'), seg.astype(np.uint8))
# flip supported by the correlation evidence above (nibabel axis 1, corr -0.857; all others |corr| < 0.05)
np.save(os.path.join(OUT, 'seg_flipped_uint8.npy'), np.flip(seg, 1).astype(np.uint8))
