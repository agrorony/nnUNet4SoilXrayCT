"""Confirm pred vs GT overlap at z=413-433."""
import tifffile, nibabel as nib, numpy as np

BASE  = r"\\hive3065\Yael_Mishael\Rony\remote_computer backup"
raw_p = BASE + r"\10.5\nlm_volume.tif"
gt_p  = BASE + r"\nnUNet_resources\multi_sample_iter02\_multi_sample_stage\annotations\nlm_volume.tif"
pr_p  = BASE + r"\nnUNet_resources\bnei_reem_iter03\inference_concatenated\nlm_volume.nii.gz"
Z0, Z1 = 413, 433

with tifffile.TiffFile(raw_p) as tf:
    raw = np.stack([tf.pages[z].asarray() for z in range(Z0, Z1)])
with tifffile.TiffFile(gt_p) as tf:
    gt  = np.stack([tf.pages[z].asarray() for z in range(Z0, Z1)])
pred_full = np.asarray(nib.load(pr_p).dataobj).T
pred = pred_full[Z0:Z1].copy()

print("raw  shape:", raw.shape,  "min/max:", raw.min(), raw.max())
print("gt   shape:", gt.shape,   "unique:", np.unique(gt).tolist())
print("pred shape:", pred.shape, "unique:", np.unique(pred).tolist())
err = (pred != gt).astype(np.float32)
print("error voxels:", int(err.sum()), f"({100*err.mean():.1f}%)")
