import sys

if __name__ != '__main__':
    sys.exit(0)

import matplotlib
matplotlib.use('Agg')

import subprocess; subprocess.run(['nvidia-smi'], check=False)

import os

REPO_DIR = r'C:\Users\rony.schwartz\Documents\nnUNet4SoilXrayCT'
assert os.path.isdir(REPO_DIR), f'Repo not found: {REPO_DIR}'

os.environ['CUDA_VISIBLE_DEVICES'] = '0'

# ── Register custom trainer ───────────────────────────────────────────────────
import shutil, importlib
import nnunetv2

nnunet_trainers_dir = os.path.join(
    os.path.dirname(nnunetv2.__file__),
    'training', 'nnUNetTrainer', 'variants', 'sampling'
)
os.makedirs(nnunet_trainers_dir, exist_ok=True)

src = os.path.join(REPO_DIR, 'nnUNetTrainer_betterIgnoreSampling.py')
dst = os.path.join(nnunet_trainers_dir, 'nnUNetTrainer_betterIgnoreSampling.py')
shutil.copy2(src, dst)
print(f'Copied: {src} -> {dst}')

if 'nnunetv2.training.nnUNetTrainer.variants.sampling.nnUNetTrainer_betterIgnoreSampling' in sys.modules:
    del sys.modules['nnunetv2.training.nnUNetTrainer.variants.sampling.nnUNetTrainer_betterIgnoreSampling']

from nnunetv2.training.nnUNetTrainer.variants.sampling.nnUNetTrainer_betterIgnoreSampling import (
    nnUNetTrainer_betterIgnoreSampling,
    nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss,
)
print('[OK] Custom trainer registered:', nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss.__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────
import json

HIVE_ROOT = r'\\hive3065\Yael_Mishael\Rony\remote_computer backup'
HIVE_BASE = os.path.join(HIVE_ROOT, 'nnUNet_resources')

with open(os.path.join(REPO_DIR, 'analysis', 'data_registry.json')) as _f:
    _registry = json.load(_f)

TRAINING_SAMPLES = [s for s in _registry['samples'] if s['sample_id'] == 'nlm_volume']
assert TRAINING_SAMPLES, 'nlm_volume not found in registry'
SAMPLE_ID = 'nlm_volume'
RAW_TIFF_PATH = TRAINING_SAMPLES[0]['raw_tiff_path']

NEW_ANNOTATION_PATH = os.path.join(
    HIVE_BASE, 'fresh_train_annotations_bnei_reem', 'annotations_i2.nii.gz'
)
assert os.path.isfile(NEW_ANNOTATION_PATH), f'Annotation not found: {NEW_ANNOTATION_PATH}'

print(f'Training sample:   {SAMPLE_ID}')
print(f'Raw TIF:           {RAW_TIFF_PATH}')
print(f'New annotation:    {NEW_ANNOTATION_PATH}')

TRAINER_NAME = 'nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss'

LOCAL_BASE          = os.path.join(HIVE_BASE, 'multi_sample_fresh_bnei_reem_i2')
nnUNet_raw          = os.path.join(LOCAL_BASE, 'nnUNet_raw')
nnUNet_preprocessed = os.path.join(LOCAL_BASE, 'nnUNet_preprocessed')
nnUNet_results      = os.path.join(LOCAL_BASE, 'nnUNet_results')

os.environ['nnUNet_raw']          = nnUNet_raw
os.environ['nnUNet_preprocessed'] = nnUNet_preprocessed
os.environ['nnUNet_results']      = nnUNet_results
os.environ['nnUNet_compile']      = 'false'

for d in [nnUNet_raw, nnUNet_preprocessed, nnUNet_results]:
    os.makedirs(d, exist_ok=True)

# Pretrained weights: fresh_bnei_reem checkpoint (fine-tuning from it)
FRESH_BASE = os.path.join(
    HIVE_BASE, 'bnei_reem_iter04', 'multi_sample_fresh_bnei_reem'
)
PRETRAINED_CHECKPOINT = os.path.join(
    FRESH_BASE, 'nnUNet_results', 'Dataset777_GCEF',
    f'{TRAINER_NAME}__nnUNetPlans__3d_fullres',
    'fold_0', 'checkpoint_final.pth'
)
if not os.path.isfile(PRETRAINED_CHECKPOINT):
    PRETRAINED_CHECKPOINT = os.path.join(
        FRESH_BASE, 'nnUNet_results', 'Dataset777_GCEF',
        f'{TRAINER_NAME}__nnUNetPlans__3d_fullres',
        'fold_0', 'checkpoint_best.pth'
    )
assert os.path.isfile(PRETRAINED_CHECKPOINT), f'Checkpoint not found: {PRETRAINED_CHECKPOINT}'
print(f'Pretrained weights: {PRETRAINED_CHECKPOINT}')

print()
print('LOCAL_BASE:',          LOCAL_BASE)
print('nnUNet_raw:',          nnUNet_raw)
print('nnUNet_preprocessed:', nnUNet_preprocessed)
print('nnUNet_results:',      nnUNet_results)

# ── Dataset preparation ────────────────────────────────────────────────────────
import numpy as np
import nibabel as nib
import tifffile
from nnunetv2.dataset_conversion.generate_dataset_json import generate_dataset_json

FORCE_REBUILD = True

dataset_raw_dir          = os.path.join(nnUNet_raw, 'Dataset777_GCEF')
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

sys.path.insert(0, REPO_DIR)
with open(os.path.join(REPO_DIR, 'dataset_info.json')) as _f:
    _meta = json.load(_f)
_classes = list(_meta['labels'].values())   # 7 items: ['ToPredict', 'Matrix', ..., 'Pore']
del _classes[0]                             # drop 'ToPredict', keep 6 classes
num_classes = len(_classes) + 1            # = 7

NUMBER_OF_OFFSET_LAYERS = 48


def mask_to_nnunet(mask_data, nc):
    """Remap: label 0 (ToPredict) -> nc (ignore), clamp out-of-range, shift all by -1."""
    m = mask_data.copy().astype(np.int16)
    m[m == 0] = nc
    m[m > nc] = nc
    m -= 1
    return m.astype(np.uint8)


print('Step 1: Loading raw image TIF...')
img_arr = tifffile.imread(RAW_TIFF_PATH)   # (Z, Y, X)
img_arr = img_arr.transpose(2, 1, 0)        # -> (X, Y, Z)
print(f'  Image shape (X, Y, Z): {img_arr.shape}')

print('Step 2: Loading annotation NIfTI...')
ann_nii  = nib.load(NEW_ANNOTATION_PATH)
ann_data = ann_nii.get_fdata().astype(np.uint8)
print(f'  Annotation shape as loaded: {ann_data.shape}')
print(f'  Unique labels: {np.unique(ann_data).tolist()}')

# Axis auto-detection
if ann_data.shape[:2] == img_arr.shape[:2]:
    print('  Axis convention: (X, Y, Z) — no transpose needed.')
elif ann_data.shape[1:] == img_arr.shape[:2]:
    print('  Axis convention: (Z, Y, X) — transposing to (X, Y, Z).')
    ann_data = ann_data.transpose(2, 1, 0)
elif ann_data.shape[0] == img_arr.shape[2] and ann_data.shape[1:] == img_arr.shape[:2][::-1]:
    print('  Axis convention: (Z, X, Y) — transposing.')
    ann_data = ann_data.transpose(1, 2, 0)
else:
    print(f'  WARNING: unclear axis convention {ann_data.shape} vs image {img_arr.shape}. Proceeding as-is.')
print(f'  Annotation shape after axis alignment: {ann_data.shape}')

print('Step 3: Cropping to annotated z-range...')
_, _, z_coords = np.where(ann_data != 0)
if len(z_coords) == 0:
    raise ValueError('No annotated voxels found!')
z_min = max(0, int(z_coords.min()) - NUMBER_OF_OFFSET_LAYERS)
z_max = min(int(z_coords.max()) + NUMBER_OF_OFFSET_LAYERS + 1, ann_data.shape[2] - 1)
print(f'  Annotated z-range: {z_coords.min()}-{z_coords.max()} -> crop [{z_min}, {z_max}]')

img_crop = img_arr[:, :, z_min:z_max]
ann_crop = ann_data[:, :, z_min:z_max]
del img_arr, ann_data
print(f'  Cropped — image: {img_crop.shape}, annotation: {ann_crop.shape}')

print('Step 4: Applying nnUNet label mapping...')
ann_nnunet = mask_to_nnunet(ann_crop, num_classes)
print(f'  nnUNet labels after remapping: {np.unique(ann_nnunet).tolist()}')
del ann_crop

print('Step 5: Saving nnUNet dataset...')
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

print('Step 6: Generating dataset.json...')
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

# ── Dataset integrity check ───────────────────────────────────────────────────
import glob
images = sorted(glob.glob(os.path.join(dataset_raw_dir, 'imagesTr', '*_0000.nii.gz')))
labels = sorted(glob.glob(os.path.join(dataset_raw_dir, 'labelsTr', '*.nii.gz')))
print(f'imagesTr: {len(images)} | labelsTr: {len(labels)}')
assert len(images) == 1 and len(labels) == 1, 'Expected exactly 1 image+label pair'
print(f'[OK] Dataset ready.')

# ── Plan + preprocess ──────────────────────────────────────────────────────────
result = subprocess.run(
    [sys.executable, '-m', 'nnunetv2.experiment_planning.plan_and_preprocess_entrypoints',
     '-d', '777', '--verify_dataset_integrity'],
    env=os.environ,
    timeout=3600,
    capture_output=False
)
if result.returncode != 0:
    raise RuntimeError(f'plan_and_preprocess failed (exit {result.returncode})')
print('[OK] Planning and preprocessing complete.')

# ── Custom splits: train=val=nlm_volume ───────────────────────────────────────
preprocessed_dir = os.path.join(os.environ['nnUNet_preprocessed'], 'Dataset777_GCEF')
splits = [{'train': [SAMPLE_ID], 'val': [SAMPLE_ID]}]
splits_path = os.path.join(preprocessed_dir, 'splits_final.json')
with open(splits_path, 'w') as f:
    json.dump(splits, f, indent=2)
print(f'Wrote {splits_path}')
print(json.dumps(splits, indent=2))

# ── Fine-tune training ─────────────────────────────────────────────────────────
os.environ['NNUNET_EARLY_STOP_ENABLED']   = '1'
os.environ['NNUNET_EARLY_STOP_PATIENCE']  = '20'
os.environ['NNUNET_EARLY_STOP_MIN_DELTA'] = '0.001'
print('Early stopping env:', {
    'NNUNET_EARLY_STOP_ENABLED':   os.environ['NNUNET_EARLY_STOP_ENABLED'],
    'NNUNET_EARLY_STOP_PATIENCE':  os.environ['NNUNET_EARLY_STOP_PATIENCE'],
    'NNUNET_EARLY_STOP_MIN_DELTA': os.environ['NNUNET_EARLY_STOP_MIN_DELTA'],
})
print(f'Pretrained weights: {PRETRAINED_CHECKPOINT}')

_wrapper = os.path.join(REPO_DIR, '_train_wrapper.py')
proc = subprocess.Popen(
    [sys.executable, _wrapper,
     '777', '3d_fullres', '0', '-tr', TRAINER_NAME,
     '-pretrained_weights', PRETRAINED_CHECKPOINT],
    env=os.environ,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
)
for line in proc.stdout:
    print(line, end='', flush=True)
proc.wait()
if proc.returncode != 0:
    raise RuntimeError(f'Training failed (exit {proc.returncode})')

# ── Analytics ─────────────────────────────────────────────────────────────────
import re
import pandas as pd

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
    raise FileNotFoundError(f'No training_log*.txt found under {results_dir}')

epoch_re = re.compile(r'Epoch\s+(\d+)')
train_re = re.compile(r'train_loss\s+(-?[\d.eE]+)')
val_re   = re.compile(r'val_loss\s+(-?[\d.eE]+)')
dice_re  = re.compile(
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
            m = epoch_re.search(line)
            if m:
                current_epoch = int(m.group(1))
                if current_epoch not in epoch_data:
                    epoch_data[current_epoch] = {'epoch': current_epoch, 'fold': fold_name}
            if current_epoch is None:
                continue
            m = train_re.search(line)
            if m:
                epoch_data[current_epoch]['train_loss'] = float(m.group(1))
            m = val_re.search(line)
            if m:
                epoch_data[current_epoch]['val_loss'] = float(m.group(1))
            m = dice_re.search(line)
            if m:
                epoch_data[current_epoch]['mean_dice'] = float(m.group(1))
    all_rows.extend(epoch_data.values())

df = pd.DataFrame(all_rows).sort_values(['epoch', 'fold'])
if df.empty:
    raise RuntimeError('Parsed zero epochs from training logs.')

summary = df.groupby('epoch', as_index=False).agg(
    {'train_loss': 'mean', 'val_loss': 'mean', 'mean_dice': 'mean'}
)

analytics_dir = os.path.join(results_dir, 'analytics')
os.makedirs(analytics_dir, exist_ok=True)
summary_csv = os.path.join(analytics_dir, 'training_metrics_summary.csv')
summary.to_csv(summary_csv, index=False)
print(f'\nSaved summary CSV: {summary_csv}')

import matplotlib.pyplot as plt

fig, ax1 = plt.subplots(figsize=(12, 6))
x = summary['epoch']
ax1.plot(x, summary['train_loss'], label='Train Loss', color='tab:blue',   lw=2.5)
ax1.plot(x, summary['val_loss'],   label='Val Loss',   color='tab:orange', lw=2.5)
ax1.set_xlabel('Epoch', fontsize=12)
ax1.set_ylabel('Loss',  fontsize=12)
ax1.grid(True, alpha=0.3)

ax2 = ax1.twinx()
if summary['mean_dice'].notna().any():
    ax2.plot(x, summary['mean_dice'], label='Mean Dice', color='tab:green', lw=2.5)
    ax2.set_ylabel('Mean Dice', fontsize=12)
    ax2.set_ylim(0, 1)

lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='best', fontsize=11)
plt.title('Training Metrics — fresh_bnei_reem_i2 (fine-tune from fresh)', fontsize=14, fontweight='bold')
plt.tight_layout()

for ext in ('png', 'pdf'):
    out = os.path.join(analytics_dir, f'training_metrics_combined.{ext}')
    plt.savefig(out, dpi=150, bbox_inches='tight')
plt.close()

last = summary.iloc[-1]
print('\n=== Training Summary ===')
print(f"  epochs:      {int(last['epoch'])}")
print(f"  train_loss:  {last['train_loss']:.6f}")
print(f"  val_loss:    {last['val_loss']:.6f}")
if pd.notna(last['mean_dice']):
    print(f"  mean_dice:   {last['mean_dice']:.6f}")
print(f'\n[OK] Analytics saved to {analytics_dir}')

# ── Inference ─────────────────────────────────────────────────────────────────
print('\n' + '=' * 70)
print('Running inference with fresh_bnei_reem_i2 model ...')
print('=' * 70)

inf_script = os.path.join(REPO_DIR, '_run_inference_fresh_bnei_reem_i2.py')
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
    raise RuntimeError(f'Inference failed (exit {inf_proc.returncode})')

print('\n[OK] fresh_bnei_reem_i2 pipeline complete.')
