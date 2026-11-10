"""Step 0.1 - verify the segmentation file, labels and fractions; prepare the flipped uint8 volume cache."""
import numpy as np, nibabel as nib, os, time, datetime, json, sys
SEG = r'E:\PROJECTS\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources\mishmar_hanegev_maoz_3_5p85um\inference_output_concat_loess_i2\mishmar_hanegev_maoz_3_5p85um.nii.gz'
OUT = r'E:\PROJECTS\Yael_Mishael\Rony\remote_computer backup\render3d_mishmar_5p85_20261012'
st = os.stat(SEG)
print('path', SEG); print('size', st.st_size, 'mtime', datetime.datetime.fromtimestamp(st.st_mtime))
img = nib.load(SEG)
print('shape', img.shape, 'dtype', img.get_data_dtype(), 'header zooms', img.header.get_zooms())
print('axcodes', nib.aff2axcodes(img.affine)); print('affine\n', img.affine)
seg = np.asarray(img.dataobj)
u, c = np.unique(seg, return_counts=True)
n = seg.size; fr = {int(k): 100*v/n for k, v in zip(u, c)}
print('labels', dict(zip(u.tolist(), c.tolist()))); print('percent', {k: round(v, 4) for k, v in fr.items()})
ok = set(u.tolist()) <= {0, 1, 2, 5} and abs(fr[5]-27.038) <= .01 and abs(fr[2]-1.615) <= .01
print('STEP0.1 PASS' if ok else 'STEP0.1 FAIL')
if not ok: sys.exit(1)
seg = np.flip(seg, 1)  # as make_fig7.py
np.save(os.path.join(OUT, 'seg_flipped_uint8.npy'), seg.astype(np.uint8))
json.dump(dict(path=SEG, size=st.st_size, mtime=str(datetime.datetime.fromtimestamp(st.st_mtime)), header_zooms=[float(z) for z in img.header.get_zooms()], pct=fr), open(os.path.join(OUT, 'step0_input.json'), 'w'), indent=1)
