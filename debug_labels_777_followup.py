"""Follow-up diagnostics: deeper stats on image, label, and preprocessed data."""
import numpy as np
import nibabel as nib
import os
import json

LOCAL_BASE = r"G:\האחסון שלי\soil_microCT_images\nnUNet_resources\bnei_reem"

# === IMAGE deeper stats ===
RAW_IMAGE = os.path.join(LOCAL_BASE, "nnUNet_raw", "Dataset777_GCEF", "imagesTr", "nlm_volume_0000.nii.gz")
img = nib.load(RAW_IMAGE)
d = img.get_fdata()
print("=== IMAGE deeper stats ===")
print(f"  mean (full precision): {np.mean(d)}")
print(f"  std:  {np.std(d)}")
print(f"  nonzero count: {np.count_nonzero(d)} / {d.size}")
print(f"  percentiles [1,25,50,75,99]: {np.percentile(d, [1,25,50,75,99])}")
print(f"  affine:\n{img.affine}")
pixdim = img.header["pixdim"]
print(f"  header pixdim: {pixdim}")
del d

# === LABEL deeper stats ===
RAW_LABEL = os.path.join(LOCAL_BASE, "nnUNet_raw", "Dataset777_GCEF", "labelsTr", "nlm_volume.nii.gz")
lbl = nib.load(RAW_LABEL)
ld = lbl.get_fdata().astype(np.uint8)
print()
print("=== LABEL deeper stats ===")
print(f"  affine:\n{lbl.affine}")
pixdim_lbl = lbl.header["pixdim"]
print(f"  header pixdim: {pixdim_lbl}")
vals, counts = np.unique(ld, return_counts=True)
for v, c in zip(vals, counts):
    pct = 100 * c / ld.size
    print(f"  label {int(v)}: {c} voxels ({pct:.2f}%)")
del ld

# === PREPROCESSED .npz deeper stats ===
npz_path = os.path.join(LOCAL_BASE, "nnUNet_preprocessed", "Dataset777_GCEF", "nnUNetPlans_3d_fullres", "nlm_volume.npz")
if os.path.isfile(npz_path):
    data = np.load(npz_path)
    print()
    print("=== PREPROCESSED .npz deeper stats ===")
    print(f"  data shape: {data['data'].shape}")
    print(f"  data unique (first 20): {np.unique(data['data'])[:20]}")
    print(f"  data mean: {np.mean(data['data'])}")
    print(f"  seg shape: {data['seg'].shape}")
    print(f"  seg unique: {np.unique(data['seg'])}")
    del data

# === plans.json ===
plans_path = os.path.join(LOCAL_BASE, "nnUNet_preprocessed", "Dataset777_GCEF", "nnUNetPlans.json")
if os.path.isfile(plans_path):
    with open(plans_path, "r") as f:
        j = json.load(f)
    cfg = j.get("configurations", {}).get("3d_fullres", {})
    print()
    print("=== plans.json 3d_fullres config ===")
    print(f"  spacing: {cfg.get('spacing')}")
    print(f"  patch_size: {cfg.get('patch_size')}")
    print(f"  median_image_size_in_voxels: {cfg.get('median_image_size_in_voxels')}")
    print(f"  batch_size: {cfg.get('batch_size')}")
    # Also check dataset fingerprint
    fp_key = "dataset_fingerprint" if "dataset_fingerprint" in j else None
    if fp_key is None:
        # Check in experiment planner
        fp_path = os.path.join(LOCAL_BASE, "nnUNet_preprocessed", "Dataset777_GCEF", "dataset_fingerprint.json")
        if os.path.isfile(fp_path):
            with open(fp_path, "r") as f2:
                fp_data = json.load(f2)
            print()
            print("=== dataset_fingerprint.json ===")
            for k, v in fp_data.items():
                print(f"  {k}: {v}")
else:
    print(f"  plans.json not found")

# === dataset.json ===
ds_path = os.path.join(LOCAL_BASE, "nnUNet_preprocessed", "Dataset777_GCEF", "dataset.json")
if os.path.isfile(ds_path):
    with open(ds_path, "r") as f:
        ds = json.load(f)
    print()
    print("=== dataset.json ===")
    print(f"  numTraining: {ds.get('numTraining')}")
    print(f"  file_ending: {ds.get('file_ending')}")
    print(f"  labels: {ds.get('labels')}")
else:
    print(f"  dataset.json not found at preprocessed location")
    # Check in nnUNet_raw
    ds_raw = os.path.join(LOCAL_BASE, "nnUNet_raw", "Dataset777_GCEF", "dataset.json")
    if os.path.isfile(ds_raw):
        with open(ds_raw, "r") as f:
            ds = json.load(f)
        print(f"  (Found in nnUNet_raw)")
        print(f"  numTraining: {ds.get('numTraining')}")
        print(f"  file_ending: {ds.get('file_ending')}")
        print(f"  labels: {ds.get('labels')}")
