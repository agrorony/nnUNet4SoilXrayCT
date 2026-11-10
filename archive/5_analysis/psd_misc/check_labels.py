import numpy as np
import tifffile
import nibabel as nib
import os
import sys

# 1) Original annotation TIF
ANN_TIF = r'\\HIVE3065\Yael_Mishael\Rony\remote_computer backup\10.5\annotations\nlm_volume.tif'
print("=== Original annotation TIF ===")
if os.path.exists(ANN_TIF):
    ann = tifffile.imread(ANN_TIF)
    u, c = np.unique(ann, return_counts=True)
    print(f"  shape={ann.shape}  dtype={ann.dtype}")
    for uu, cc in zip(u, c):
        print(f"    label {int(uu):2d}: {cc:10,} voxels ({100*cc/ann.size:.1f}%)")
    sys.stdout.flush()
else:
    print(f"  NOT FOUND: {ANN_TIF}")

# 2) Prediction — sample first 20 slices along NIfTI X axis
PRED_NII = r'C:\Users\rony.schwartz\Documents\nnUNet_resources\bnei_reem\inference_output_concat\nlm_volume.nii.gz'
print("\n=== Prediction NIfTI (sampled first 20 slices along X) ===")
if os.path.exists(PRED_NII):
    proxy = nib.load(PRED_NII)
    print(f"  full shape={proxy.shape}")
    sample = np.array(proxy.dataobj[:20, :, :]).astype(np.int16)
    u, c = np.unique(sample, return_counts=True)
    for uu, cc in zip(u, c):
        print(f"    label {int(uu):2d}: {cc:10,} voxels")
    sys.stdout.flush()
else:
    print(f"  NOT FOUND: {PRED_NII}")
