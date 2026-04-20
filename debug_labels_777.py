"""
Diagnostic script: trace where Dataset777_GCEF labels went wrong.
READ-ONLY — does not modify any files.
"""
import os
import sys
import numpy as np

LOCAL_BASE = r"G:\האחסון שלי\soil_microCT_images\nnUNet_resources\bnei_reem"
RAW_LABEL  = os.path.join(LOCAL_BASE, "nnUNet_raw", "Dataset777_GCEF", "labelsTr", "nlm_volume.nii.gz")
RAW_IMAGE  = os.path.join(LOCAL_BASE, "nnUNet_raw", "Dataset777_GCEF", "imagesTr", "nlm_volume_0000.nii.gz")
SRC_ANNOT_TIF   = os.path.join(LOCAL_BASE, "annotations", "nlm_volume.tif")
TEMP_ANNOT_TIF  = os.path.join(LOCAL_BASE, "temp_nlm_annotations", "nlm_volume.tif")
SRC_IMAGE_TIF   = os.path.join(LOCAL_BASE, "temp_nlm_images", "nlm_volume.tif")
SRC_IMAGE_NPY   = os.path.join(LOCAL_BASE, "images", "nlm_volume.npy")
PREPROCESSED    = os.path.join(LOCAL_BASE, "nnUNet_preprocessed", "Dataset777_GCEF")
# Bonus: intermediate temp NIfTI (before crop/remap)
TEMP_LABEL_NII  = os.path.join(LOCAL_BASE, "nnUNet_raw", "Dataset777_GCEF", "temp_labels_nii", "nlm_volume.nii.gz")

SEPARATOR = "=" * 60

def file_exists(path, label):
    if not os.path.isfile(path):
        print(f"  FILE NOT FOUND: {path}")
        return False
    size_mb = os.path.getsize(path) / (1024 * 1024)
    print(f"  File: {path}")
    print(f"  Size: {size_mb:.2f} MB")
    return True

# ────────────────────────────────────────────────────────────
# CHECK 1 — NIfTI label file
# ────────────────────────────────────────────────────────────
print(f"\n{SEPARATOR}")
print("CHECK 1 — Verify NIfTI label file (RAW_LABEL)")
print(SEPARATOR)

import nibabel as nib

if not file_exists(RAW_LABEL, "RAW_LABEL"):
    print("STOP: RAW_LABEL file missing — cannot continue.")
    sys.exit(1)

label_nii = nib.load(RAW_LABEL)
label_data = label_nii.get_fdata()
label_unique = np.unique(label_data)
label_nonzero = np.count_nonzero(label_data)

print(f"  shape:          {label_data.shape}")
print(f"  dtype (on disk):{label_nii.header.get_data_dtype()}")
print(f"  dtype (loaded): {label_data.dtype}")
print(f"  unique values:  {label_unique}")
print(f"  count_nonzero:  {label_nonzero}")
print(f"  total voxels:   {label_data.size}")

if label_nonzero > 0:
    print("\n  RESULT: Label file is NOT all-zero.")
    print("  → The problem may be in nnUNet preprocessing or Drive sync, not in conversion.")
    print("  → However, if unique=[9] only + 0, all voxels are 'ignore' class.")
    # Don't stop — continue checks for full picture
else:
    print("\n  RESULT: Label file IS all-zero (confirmed).")
    print("  → All voxels = 0 (nnUNet class 0 = 'Matrix' after remap).")
    print("  → This means source TIFF had ONLY label 1 (Wall), or file was never written.")

del label_data
label_shape = label_nii.shape  # keep shape for CHECK 4

# ────────────────────────────────────────────────────────────
# CHECK 2 — Source TIFF annotations
# ────────────────────────────────────────────────────────────
print(f"\n{SEPARATOR}")
print("CHECK 2 — Verify source TIFF annotations")
print(SEPARATOR)

import tifffile

tif_shapes = {}

for tag, path in [("SRC_ANNOT_TIF", SRC_ANNOT_TIF), ("TEMP_ANNOT_TIF", TEMP_ANNOT_TIF)]:
    print(f"\n  --- {tag} ---")
    if not file_exists(path, tag):
        continue
    arr = tifffile.imread(path)
    tif_unique = np.unique(arr)
    print(f"  shape: {arr.shape}")
    print(f"  dtype: {arr.dtype}")
    print(f"  unique values: {tif_unique}")
    print(f"  count_nonzero: {np.count_nonzero(arr)}")
    if tag == "TEMP_ANNOT_TIF":
        tif_shapes["annot"] = arr.shape  # (Z, Y, X) — keep for CHECK 4
    elif tag == "SRC_ANNOT_TIF":
        tif_shapes["annot_src"] = arr.shape
    del arr

# ────────────────────────────────────────────────────────────
# CHECK 2.5 (BONUS) — Intermediate temp NIfTI
# ────────────────────────────────────────────────────────────
print(f"\n{SEPARATOR}")
print("CHECK 2.5 — Intermediate temp NIfTI (before crop/remap)")
print(SEPARATOR)

if file_exists(TEMP_LABEL_NII, "TEMP_LABEL_NII"):
    tmp_nii = nib.load(TEMP_LABEL_NII)
    tmp_data = tmp_nii.get_fdata()
    print(f"  shape:          {tmp_data.shape}")
    print(f"  dtype (on disk):{tmp_nii.header.get_data_dtype()}")
    print(f"  unique values:  {np.unique(tmp_data)}")
    print(f"  count_nonzero:  {np.count_nonzero(tmp_data)}")
    del tmp_data, tmp_nii
else:
    print("  (Intermediate temp NIfTI not found — may have been cleaned up or lives on C: drive)")

# ────────────────────────────────────────────────────────────
# CHECK 3 — NIfTI image file
# ────────────────────────────────────────────────────────────
print(f"\n{SEPARATOR}")
print("CHECK 3 — Verify NIfTI image file (RAW_IMAGE)")
print(SEPARATOR)

if file_exists(RAW_IMAGE, "RAW_IMAGE"):
    img_nii = nib.load(RAW_IMAGE)
    img_data = img_nii.get_fdata()
    print(f"  shape: {img_data.shape}")
    print(f"  dtype (on disk): {img_nii.header.get_data_dtype()}")
    print(f"  min:   {np.min(img_data)}")
    print(f"  max:   {np.max(img_data)}")
    print(f"  mean:  {np.mean(img_data):.4f}")
    image_shape = img_nii.shape
    del img_data, img_nii
else:
    image_shape = None
    print("  RAW_IMAGE not found!")

# ────────────────────────────────────────────────────────────
# CHECK 4 — Shape/orientation consistency
# ────────────────────────────────────────────────────────────
print(f"\n{SEPARATOR}")
print("CHECK 4 — Shape/orientation consistency")
print(SEPARATOR)

print(f"  NIfTI label shape (X,Y,Z):  {label_shape}")
if image_shape is not None:
    print(f"  NIfTI image shape (X,Y,Z):  {image_shape}")
    if label_shape != image_shape:
        print("  WARNING: label and image shapes DIFFER!")
    else:
        print("  OK: label and image shapes match.")
else:
    print("  NIfTI image shape: N/A (file not found)")

for tag, key in [("TEMP_ANNOT_TIF (Z,Y,X)", "annot"), ("SRC_ANNOT_TIF (Z,Y,X)", "annot_src")]:
    if key in tif_shapes:
        s = tif_shapes[key]
        transposed = (s[2], s[1], s[0])  # (X, Y, Z) after transpose
        print(f"  {tag}: {s} → transposed (X,Y,Z): {transposed}")
        print(f"    vs NIfTI label (X,Y,Z): {label_shape}")
        print(f"    NOTE: NIfTI may be Z-cropped (±48 layers), so Z can be smaller.")

# ────────────────────────────────────────────────────────────
# CHECK 5 — Preprocessed .npz
# ────────────────────────────────────────────────────────────
print(f"\n{SEPARATOR}")
print("CHECK 5 — Preprocessed .npz content")
print(SEPARATOR)

npz_path = os.path.join(PREPROCESSED, "nnUNetPlans_3d_fullres", "nlm_volume.npz")
if file_exists(npz_path, "npz"):
    data = np.load(npz_path)
    print(f"  keys: {list(data.keys())}")
    if 'seg' in data:
        seg = data['seg']
    else:
        last_key = list(data.keys())[-1]
        seg = data[last_key]
        print(f"  (using key '{last_key}' as seg)")
    print(f"  seg shape:  {seg.shape}")
    print(f"  seg dtype:  {seg.dtype}")
    print(f"  seg unique: {np.unique(seg)}")
    del data, seg
else:
    print("  Preprocessed .npz not found.")

# ────────────────────────────────────────────────────────────
# SUMMARY
# ────────────────────────────────────────────────────────────
print(f"\n{SEPARATOR}")
print("SUMMARY — All checks completed. Review results above.")
print(SEPARATOR)
