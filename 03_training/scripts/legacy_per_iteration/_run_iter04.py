import sys

# Guard against Windows multiprocessing spawn re-executing this script.
# nnUNetPredictor uses multiprocessing.Pool; on Windows (spawn method), each
# worker re-imports the main script as '__mp_main__'. Without this exit, every
# worker would restart the entire training+inference pipeline — an infinite cascade.
if __name__ != '__main__':
    sys.exit(0)

import matplotlib
matplotlib.use('Agg')  # non-interactive backend for headless script execution

# --- cell ---
# Verify GPU runtime
import subprocess; subprocess.run(['nvidia-smi'], check=False)

# --- cell ---
import os

# Local repository directory
REPO_DIR = r'C:\Users\rony.schwartz\Documents\nnUNet4SoilXrayCT'
assert os.path.isdir(REPO_DIR), f'Repo not found: {REPO_DIR}'
print('Repo dir:', os.listdir(REPO_DIR))

# --- cell ---
import shutil
import sys
import importlib
import nnunetv2
import os

# Find nnunetv2 trainers directory
nnunet_trainers_dir = os.path.join(
    os.path.dirname(nnunetv2.__file__),
    'training', 'nnUNetTrainer', 'variants', 'sampling'
)
os.makedirs(nnunet_trainers_dir, exist_ok=True)

src = os.path.join(REPO_DIR, 'nnUNetTrainer_betterIgnoreSampling.py')
dst = os.path.join(nnunet_trainers_dir, 'nnUNetTrainer_betterIgnoreSampling.py')
shutil.copy2(src, dst)
print(f'Copied: {src} -> {dst}')

# Force reload the module to pick up the updated file
if 'nnunetv2.training.nnUNetTrainer.variants.sampling.nnUNetTrainer_betterIgnoreSampling' in sys.modules:
    del sys.modules['nnunetv2.training.nnUNetTrainer.variants.sampling.nnUNetTrainer_betterIgnoreSampling']

# Import and verify the new trainer
from nnunetv2.training.nnUNetTrainer.variants.sampling.nnUNetTrainer_betterIgnoreSampling import (
    nnUNetTrainer_betterIgnoreSampling,
    nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss
)
print('[OK] Custom trainer registered:', nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss.__name__)
print('[OK] Base trainer registered:', nnUNetTrainer_betterIgnoreSampling.__name__)

# --- cell ---
import os, json

# ── Data Registry ──────────────────────────────────────────────────────────────
REGISTRY_PATH = os.path.join(REPO_DIR, 'analysis', 'data_registry.json')
with open(REGISTRY_PATH) as _f:
    _registry = json.load(_f)

# iter04: train ONLY on nlm_volume (Beni Ram) with corrected annotations
TRAINING_SAMPLES = [s for s in _registry['samples'] if s['sample_id'] == 'nlm_volume']
assert TRAINING_SAMPLES, 'nlm_volume not found in registry'

SAMPLE_ID = 'nlm_volume'
_sample_rec = TRAINING_SAMPLES[0]
RAW_TIFF_PATH = _sample_rec['raw_tiff_path']

# Corrected annotation for iter04 (already .nii.gz — no TIF conversion needed)
NEW_ANNOTATION_PATH = r'E:\PROJECTS\Yael_Mishael\Rony\remote_computer backup\annotations_iter03\new_annotations.nii.gz'
assert os.path.isfile(NEW_ANNOTATION_PATH), f'New annotation not found: {NEW_ANNOTATION_PATH}'

print(f'Training sample:   {SAMPLE_ID}')
print(f'Raw TIF:           {RAW_TIFF_PATH}')
print(f'New annotation:    {NEW_ANNOTATION_PATH}')

# ── nnUNet workspace (HIVE) ────────────────────────────────────────────────────
HIVE_BASE   = r'\\hive3065\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources'
LOCAL_BASE  = os.path.join(HIVE_BASE, 'multi_sample_iter04')

TRAINER_NAME = 'nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss'

nnUNet_raw          = os.path.join(LOCAL_BASE, 'nnUNet_raw')
nnUNet_preprocessed = os.path.join(LOCAL_BASE, 'nnUNet_preprocessed')
nnUNet_results      = os.path.join(LOCAL_BASE, 'nnUNet_results')

os.environ['nnUNet_raw']          = nnUNet_raw
os.environ['nnUNet_preprocessed'] = nnUNet_preprocessed
os.environ['nnUNet_results']      = nnUNet_results
os.environ['nnUNet_compile']      = 'false'

for d in [nnUNet_raw, nnUNet_preprocessed, nnUNet_results]:
    os.makedirs(d, exist_ok=True)

# ── Iter02 checkpoint — same starting point as iter03 ─────────────────────────
ITER02_BASE = os.path.join(HIVE_BASE, 'multi_sample_iter02')
PRETRAINED_CHECKPOINT = os.path.join(
    ITER02_BASE, 'nnUNet_results', 'Dataset777_GCEF',
    f'{TRAINER_NAME}__nnUNetPlans__3d_fullres',
    'fold_0', 'checkpoint_final.pth'
)
assert os.path.isfile(PRETRAINED_CHECKPOINT), f'Iter02 checkpoint not found: {PRETRAINED_CHECKPOINT}'
print(f'Pretrained weights: {PRETRAINED_CHECKPOINT}')

print()
print('LOCAL_BASE:',          LOCAL_BASE)
print('nnUNet_raw:',          nnUNet_raw)
print('nnUNet_preprocessed:', nnUNet_preprocessed)
print('nnUNet_results:',      nnUNet_results)
print('TRAINER_NAME:',        TRAINER_NAME)

# --- cell ---
import os, shutil, json
import numpy as np
import nibabel as nib
import tifffile
from pathlib import Path
from nnunetv2.dataset_conversion.generate_dataset_json import generate_dataset_json

FORCE_REBUILD = True

dataset_raw_dir        = os.path.join(nnUNet_raw, 'Dataset777_GCEF')
preprocessed_dataset_dir = os.path.join(nnUNet_preprocessed, 'Dataset777_GCEF')

if FORCE_REBUILD:
    for d in [dataset_raw_dir, preprocessed_dataset_dir]:
        if os.path.isdir(d):
            shutil.rmtree(d)
            print(f'Removed: {d}')

images_dir = os.path.join(dataset_raw_dir, 'imagesTr')
labels_dir = os.path.join(dataset_raw_dir, 'labelsTr')
os.makedirs(images_dir, exist_ok=True)
os.makedirs(labels_dir, exist_ok=True)

# Load dataset metadata for label mapping
import sys; sys.path.insert(0, REPO_DIR)
with open(os.path.join(REPO_DIR, 'dataset_info.json')) as _f:
    _meta = json.load(_f)
# num_classes = 7: labels 1-6 are annotation classes, 0 = ToPredict/ignore
_classes = list(_meta['labels'].values())   # ['ToPredict','Matrix',...,'Pore'] = 7 items
del _classes[0]                             # remove ToPredict, keep 6
num_classes = len(_classes) + 1            # = 7

NUMBER_OF_OFFSET_LAYERS = 48

def mask_to_nnunet(mask_data, nc):
    """Remap: label 0 (ToPredict) → nc (ignore), shift all -1."""
    m = mask_data.copy().astype(np.int16)
    m[m == 0] = nc
    m[m > nc] = nc
    m -= 1
    return m.astype(np.uint8)

# ── Step 1: raw image TIF → NIfTI (no normalization; nnUNet normalises internally) ──
print('Step 1: Loading raw image TIF...')
img_arr = tifffile.imread(RAW_TIFF_PATH)        # (Z, Y, X)
img_arr = img_arr.transpose(2, 1, 0)             # → (X, Y, Z)
print(f'  Image shape (X, Y, Z): {img_arr.shape}')

# ── Step 2: load annotation (.nii.gz) ────────────────────────────────────────────
print('Step 2: Loading annotation NIfTI...')
ann_nii  = nib.load(NEW_ANNOTATION_PATH)
ann_data = ann_nii.get_fdata().astype(np.uint8)
print(f'  Annotation shape as loaded: {ann_data.shape}')
print(f'  Unique labels: {np.unique(ann_data).tolist()}')

# Determine axis convention by matching spatial dims to the image
# img_arr is (X=650, Y=650, Z=N); annotation must end up (X, Y, Z)
if ann_data.shape[:2] == img_arr.shape[:2]:
    print('  Axis convention: (X, Y, Z) - no transpose needed.')
elif ann_data.shape[1:] == img_arr.shape[:2]:
    print('  Axis convention: (Z, Y, X) - transposing to (X, Y, Z).')
    ann_data = ann_data.transpose(2, 1, 0)
elif ann_data.shape[0] == img_arr.shape[2] and ann_data.shape[1:] == img_arr.shape[:2][::-1]:
    print('  Axis convention: (Z, X, Y) - transposing.')
    ann_data = ann_data.transpose(1, 2, 0)
else:
    print(f'  WARNING: annotation {ann_data.shape} shape unclear vs image {img_arr.shape}. Proceeding without transpose.')
print(f'  Annotation shape after axis alignment: {ann_data.shape}')

# ── Step 3: crop to annotated region ──────────────────────────────────────────────
_, _, z_coords = np.where(ann_data != 0)
if len(z_coords) == 0:
    raise ValueError('No annotated voxels found in annotation! Check the file.')
z_min = max(0, int(z_coords.min()) - NUMBER_OF_OFFSET_LAYERS)
z_max = min(int(z_coords.max()) + NUMBER_OF_OFFSET_LAYERS + 1, ann_data.shape[2] - 1)
print(f'  Annotated z-range: {z_coords.min()}-{z_coords.max()} -> crop to [{z_min}, {z_max}]')

img_crop = img_arr[:, :, z_min:z_max]
ann_crop = ann_data[:, :, z_min:z_max]
del img_arr, ann_data
print(f'  Cropped shapes - image: {img_crop.shape}, annotation: {ann_crop.shape}')

# ── Step 4: apply nnUNet label mapping ───────────────────────────────────────────
ann_nnunet = mask_to_nnunet(ann_crop, num_classes)
print(f'  nnUNet labels after remapping: {np.unique(ann_nnunet).tolist()}')
del ann_crop

# ── Step 5: save to nnUNet dataset structure ─────────────────────────────────────
affine = np.eye(4)

img_out = os.path.join(images_dir, 'nlm_volume_0000.nii.gz')
nib.save(nib.Nifti1Image(img_crop, affine), img_out)
print(f'  Saved image:  {img_out}')
del img_crop

lbl_nii = nib.Nifti1Image(ann_nnunet, affine)
lbl_nii.header.set_data_dtype(np.uint8)
lbl_out = os.path.join(labels_dir, 'nlm_volume.nii.gz')
nib.save(lbl_nii, lbl_out)
print(f'  Saved label:  {lbl_out}')
del ann_nnunet

# ── Step 6: generate dataset.json ────────────────────────────────────────────────
_classes[0] = 'background'
_classes.append('ignore')
labels_dict = {name: i for i, name in enumerate(_classes)}
generate_dataset_json(
    output_folder=dataset_raw_dir,
    channel_names={0: 'noNorm'},
    labels=labels_dict,
    num_training_cases=1,
    file_ending='.nii.gz',
    dataset_name=_meta['DatasetName'],
)
print(f'  Generated dataset.json in {dataset_raw_dir}')
print('\nDataset preparation complete.')

# --- cell ---
# Verify all training samples are present in the dataset
dataset_dir = os.path.join(nnUNet_raw, 'Dataset777_GCEF')
assert os.path.isdir(dataset_dir), f'Dataset folder not found: {dataset_dir}'

import glob, os
images = sorted(glob.glob(os.path.join(dataset_dir, 'imagesTr', '*_0000.nii.gz')))
labels = sorted(glob.glob(os.path.join(dataset_dir, 'labelsTr', '*.nii.gz')))
dataset_json = os.path.join(dataset_dir, 'dataset.json')

print(f'imagesTr: {len(images)} files')
print(f'labelsTr: {len(labels)} files')
print(f'dataset.json exists: {os.path.isfile(dataset_json)}')
for p in images:
    print('  image:', os.path.basename(p))
for p in labels:
    print('  label:', os.path.basename(p))

expected_imgs = sorted(f'{s["sample_id"]}_0000.nii.gz' for s in TRAINING_SAMPLES)
expected_lbls = sorted(f'{s["sample_id"]}.nii.gz'       for s in TRAINING_SAMPLES)

assert [os.path.basename(p) for p in images] == expected_imgs, f'imagesTr mismatch: {[os.path.basename(p) for p in images]} != {expected_imgs}'
assert [os.path.basename(p) for p in labels] == expected_lbls, f'labelsTr mismatch: {[os.path.basename(p) for p in labels]} != {expected_lbls}'
assert os.path.isfile(dataset_json), 'dataset.json missing'
print(f'[OK] Dataset contains all {len(TRAINING_SAMPLES)} training samples.')

# --- cell ---
import subprocess, sys, os

result = subprocess.run(
    [sys.executable, '-m', 'nnunetv2.experiment_planning.plan_and_preprocess_entrypoints',
     '-d', '777', '--verify_dataset_integrity'],
    env=os.environ,
    timeout=3600,
    capture_output=False
)

if result.returncode != 0:
    raise RuntimeError(f"plan_and_preprocess failed (exit {result.returncode})")
print("[OK] Planning and preprocessing complete.")

# --- cell ---
print("PolyLRScheduler: using patched polylr.py (PyTorch 2.x compatible)")

# --- cell ---
# Create custom splits_final.json — all training samples in both train and val
import json, os

preprocessed_dir = os.path.join(os.environ['nnUNet_preprocessed'], 'Dataset777_GCEF')
sample_ids = [s['sample_id'] for s in TRAINING_SAMPLES]
splits = [{"train": sample_ids, "val": sample_ids}]

splits_path = os.path.join(preprocessed_dir, 'splits_final.json')
with open(splits_path, 'w') as f:
    json.dump(splits, f, indent=2)

print(f"Wrote {splits_path}")
print(json.dumps(splits, indent=2))

# --- cell ---
import subprocess, sys, os

# Early stopping controls (env-driven in trainer)
os.environ['NNUNET_EARLY_STOP_ENABLED'] = '1'
os.environ['NNUNET_EARLY_STOP_PATIENCE'] = '20'
os.environ['NNUNET_EARLY_STOP_MIN_DELTA'] = '0.001'
print('Early stopping env:', {
    'NNUNET_EARLY_STOP_ENABLED': os.environ['NNUNET_EARLY_STOP_ENABLED'],
    'NNUNET_EARLY_STOP_PATIENCE': os.environ['NNUNET_EARLY_STOP_PATIENCE'],
    'NNUNET_EARLY_STOP_MIN_DELTA': os.environ['NNUNET_EARLY_STOP_MIN_DELTA'],
})
print(f'Pretrained weights: {PRETRAINED_CHECKPOINT}')

# Fine-tune from iter02 checkpoint.
# Use _train_wrapper.py so the torch.load patch (weights_only=False) is applied
# before nnunetv2 tries to load the checkpoint (PyTorch 2.6 compatibility fix).
_wrapper = os.path.join(REPO_DIR, '_train_wrapper.py')
proc = subprocess.Popen(
    [sys.executable, _wrapper,
     '777', '3d_fullres', '0', '-tr', TRAINER_NAME,
     '-pretrained_weights', PRETRAINED_CHECKPOINT],
    env=os.environ,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1
)

for line in proc.stdout:
    print(line, end='', flush=True)

proc.wait()
if proc.returncode != 0:
    raise RuntimeError(f"run_training failed (exit {proc.returncode})")

# --- cell ---
# List training results
results_dir = os.path.join(
    nnUNet_results, 'Dataset777_GCEF',
    f'{TRAINER_NAME}__nnUNetPlans__3d_fullres'
)
if os.path.isdir(results_dir):
    for item in sorted(os.listdir(results_dir)):
        print(item)
else:
    print(f'Results dir not found yet: {results_dir}')

# --- cell ---
# Training analytics: mean Dice, val loss, and train loss
import os
import re
import glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

results_dir = os.path.join(
    nnUNet_results, 'Dataset777_GCEF',
    f'{TRAINER_NAME}__nnUNetPlans__3d_fullres'
)

assert os.path.isdir(results_dir), f'Results dir not found: {results_dir}'

log_files = sorted(
    p for p in glob.glob(os.path.join(results_dir, 'fold_*', '*.txt'))
    if 'training_log' in os.path.basename(p).lower()
)

if not log_files:
    raise FileNotFoundError(f'No training_log*.txt files found under {results_dir}')

print('Found log files:')
for lf in log_files:
    print(f'  {lf}')

epoch_re = re.compile(r'Epoch\s+(\d+)')
train_re = re.compile(r'train_loss\s+(-?[\d.eE]+)')
val_re = re.compile(r'val_loss\s+(-?[\d.eE]+)')
dice_re = re.compile(
    r'(?:EMA\s+pseudo\s+Dice|pseudo\s+Dice|mean\s+foreground\s+Dice)[^\d-]*(-?[\d.eE]+)',
    re.IGNORECASE,
)

all_rows = []
for lf in log_files:
    fold_name = os.path.basename(os.path.dirname(lf))
    epoch_data = {}
    current_epoch = None

    with open(lf, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            m_epoch = epoch_re.search(line)
            if m_epoch:
                current_epoch = int(m_epoch.group(1))
                if current_epoch not in epoch_data:
                    epoch_data[current_epoch] = {'epoch': current_epoch, 'fold': fold_name}

            if current_epoch is None:
                continue

            m_train = train_re.search(line)
            if m_train:
                epoch_data[current_epoch]['train_loss'] = float(m_train.group(1))

            m_val = val_re.search(line)
            if m_val:
                epoch_data[current_epoch]['val_loss'] = float(m_val.group(1))

            m_dice = dice_re.search(line)
            if m_dice:
                epoch_data[current_epoch]['mean_dice'] = float(m_dice.group(1))

    all_rows.extend(epoch_data.values())

df = pd.DataFrame(all_rows).sort_values(['epoch', 'fold'])
if df.empty:
    raise RuntimeError('Parsed zero epochs from training logs.')

summary = df.groupby('epoch', as_index=False).agg({
    'train_loss': 'mean',
    'val_loss': 'mean',
    'mean_dice': 'mean',
})

analytics_dir = os.path.join(results_dir, 'analytics')
os.makedirs(analytics_dir, exist_ok=True)
summary_csv = os.path.join(analytics_dir, 'training_metrics_summary.csv')
summary.to_csv(summary_csv, index=False)
print(f'\nSaved summary CSV: {summary_csv}')

fig, ax1 = plt.subplots(figsize=(12, 6))
x = summary['epoch']

ax1.plot(x, summary['train_loss'], label='Train Loss', color='tab:blue', linewidth=2.5)
ax1.plot(x, summary['val_loss'], label='Val Loss', color='tab:orange', linewidth=2.5)
ax1.set_xlabel('Epoch', fontsize=12)
ax1.set_ylabel('Loss', fontsize=12)
ax1.grid(True, alpha=0.3)

ax2 = ax1.twinx()
if summary['mean_dice'].notna().any():
    ax2.plot(x, summary['mean_dice'], label='Mean Dice', color='tab:green', linewidth=2.5)
    ax2.set_ylabel('Mean Dice', fontsize=12)
    ax2.set_ylim(0, 1)

lines_1, labels_1 = ax1.get_legend_handles_labels()
lines_2, labels_2 = ax2.get_legend_handles_labels()
ax1.legend(lines_1 + lines_2, labels_1 + labels_2, loc='best', fontsize=11)
plt.title('Training Metrics by Epoch (iter04)', fontsize=14, fontweight='bold')
plt.tight_layout()

combined_png = os.path.join(analytics_dir, 'training_metrics_combined.png')
combined_pdf = os.path.join(analytics_dir, 'training_metrics_combined.pdf')
plt.savefig(combined_png, dpi=150, bbox_inches='tight')
plt.savefig(combined_pdf, bbox_inches='tight')
plt.close()

last = summary.iloc[-1]
print('\nLatest epoch metrics:')
print(f"  epoch={int(last['epoch'])}")
print(f"  train_loss={last['train_loss']:.6f}")
print(f"  val_loss={last['val_loss']:.6f}")
if pd.notna(last['mean_dice']):
    print(f"  mean_dice={last['mean_dice']:.6f}")
print(f'\n[OK] Training plots saved to {analytics_dir}')

# --- cell ---
# Preprocessing for inference: TIFF → NIfTI → split chunks
import subprocess, sys, os
import numpy as np
import tifffile
import nibabel as nib

INFERENCE_SAMPLE_ID = 'nlm_volume'
_inf_rec = next(s for s in _registry['samples'] if s['sample_id'] == INFERENCE_SAMPLE_ID)
INF_RAW_TIFF_PATH = _inf_rec['raw_tiff_path']

# iter04 inference workspace — separate from iter03 to avoid collision
INF_SAMPLE_BASE = os.path.join(HIVE_BASE, 'bnei_reem_iter04')
NIFTI_DIR       = os.path.join(INF_SAMPLE_BASE, 'nifti_predict')
INFERENCE_INPUT = os.path.join(INF_SAMPLE_BASE, 'inference_input')
os.makedirs(NIFTI_DIR,       exist_ok=True)
os.makedirs(INFERENCE_INPUT, exist_ok=True)

MODEL_DIR = os.path.join(
    nnUNet_results, 'Dataset777_GCEF',
    f'{TRAINER_NAME}__nnUNetPlans__3d_fullres'
)

print(f'Inference sample:  {INFERENCE_SAMPLE_ID}')
print(f'Raw TIF:           {INF_RAW_TIFF_PATH}')
print(f'NIfTI dir:         {NIFTI_DIR}')
print(f'Inference input:   {INFERENCE_INPUT}')
print(f'Model dir:         {MODEL_DIR}')

# Step 1: TIFF → NIfTI (z-score norm for inference)
print('\n=== Step 1: TIFF -> NIfTI ===')
vol = tifffile.imread(INF_RAW_TIFF_PATH).astype(np.float32)
mean, std = vol.mean(), vol.std()
vol = (vol - mean) / (std + 1e-8)
vol = vol.transpose(2, 1, 0)  # (Z, Y, X) → (X, Y, Z)
stem = os.path.splitext(os.path.basename(INF_RAW_TIFF_PATH))[0]
out_path = os.path.join(NIFTI_DIR, f'{stem}_0000.nii.gz')
nib.save(nib.Nifti1Image(vol, affine=np.eye(4)), out_path)
print(f'  Saved: {out_path}  shape={vol.shape}')
del vol
print('Step 1 done.')

# Step 2: NIfTI → split chunks
print('=== Step 2: Split into chunks ===')
result = subprocess.run(
    [sys.executable,
     os.path.join(REPO_DIR, 'preprocessing_nnUNet_predict_split.py'),
     '-i', NIFTI_DIR,
     '-o', INFERENCE_INPUT,
     '-m', MODEL_DIR],
    env=os.environ, capture_output=True, text=True
)
print(result.stdout)
if result.returncode != 0:
    print('STDERR:\n', result.stderr)
    raise RuntimeError(f'preprocessing_nnUNet_predict_split.py failed (exit {result.returncode})')
print('Step 2 done.')

# --- cell ---
# Step 3-4: Run inference via standalone script (avoids multiprocessing cascade on Windows)
print('=== Steps 3-4: Inference + Concatenation ===')
inf_script = os.path.join(REPO_DIR, '_run_inference_iter04.py')
assert os.path.isfile(inf_script), f'Inference script not found: {inf_script}'

inf_proc = subprocess.Popen(
    [sys.executable, inf_script],
    env=os.environ,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
)
for line in inf_proc.stdout:
    print(line, end='', flush=True)
inf_proc.wait()
if inf_proc.returncode != 0:
    raise RuntimeError(f'_run_inference_iter04.py failed (exit {inf_proc.returncode})')

print('\n[OK] iter04 pipeline complete.')
