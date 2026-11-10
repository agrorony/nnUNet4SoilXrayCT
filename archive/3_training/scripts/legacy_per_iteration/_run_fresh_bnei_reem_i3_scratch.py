"""
Train from scratch on annotations_i3.nii.gz.
GPU 0  |  LR 1e-2 (default)  |  Early stopping
Output: multi_sample_fresh_bnei_reem_i3_scratch
"""
import sys
if __name__ != '__main__':
    sys.exit(0)

import matplotlib
matplotlib.use('Agg')

import subprocess
subprocess.run(['nvidia-smi'], check=False)

import os, shutil, glob, json, re
import numpy as np
import nibabel as nib
import tifffile

REPO_DIR = r'C:\Users\rony.schwartz\Documents\nnUNet4SoilXrayCT'
assert os.path.isdir(REPO_DIR)

os.environ['CUDA_VISIBLE_DEVICES'] = '0'

# ── Register trainer ──────────────────────────────────────────────────────────
import nnunetv2
nnunet_trainers_dir = os.path.join(
    os.path.dirname(nnunetv2.__file__),
    'training', 'nnUNetTrainer', 'variants', 'sampling'
)
os.makedirs(nnunet_trainers_dir, exist_ok=True)
shutil.copy2(
    os.path.join(REPO_DIR, 'nnUNetTrainer_betterIgnoreSampling.py'),
    os.path.join(nnunet_trainers_dir, 'nnUNetTrainer_betterIgnoreSampling.py')
)

# ── Paths ─────────────────────────────────────────────────────────────────────
HIVE_ROOT = r'\\hive3065\Yael_Mishael\Rony\remote_computer backup'
HIVE_BASE = os.path.join(HIVE_ROOT, 'nnUNet_resources')

SAMPLE_ID           = 'nlm_volume'
RAW_TIFF_PATH       = os.path.join(HIVE_ROOT, '10.5', 'nlm_volume.tif')
NEW_ANNOTATION_PATH = os.path.join(HIVE_BASE, 'fresh_train_annotations_bnei_reem', 'annotations_i3.nii.gz')
TRAINER_NAME        = 'nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss'
LOCAL_BASE          = os.path.join(HIVE_BASE, 'multi_sample_fresh_bnei_reem_i3_scratch')

assert os.path.isfile(RAW_TIFF_PATH),       f'Missing TIF: {RAW_TIFF_PATH}'
assert os.path.isfile(NEW_ANNOTATION_PATH), f'Missing annotation: {NEW_ANNOTATION_PATH}'

nnUNet_raw          = os.path.join(LOCAL_BASE, 'nnUNet_raw')
nnUNet_preprocessed = os.path.join(LOCAL_BASE, 'nnUNet_preprocessed')
nnUNet_results      = os.path.join(LOCAL_BASE, 'nnUNet_results')
os.environ['nnUNet_raw']          = nnUNet_raw
os.environ['nnUNet_preprocessed'] = nnUNet_preprocessed
os.environ['nnUNet_results']      = nnUNet_results
os.environ['nnUNet_compile']      = 'false'
for d in [nnUNet_raw, nnUNet_preprocessed, nnUNet_results]:
    os.makedirs(d, exist_ok=True)

print(f'Trainer:     {TRAINER_NAME}  (LR=1e-2, from scratch)')
print(f'Annotation:  {NEW_ANNOTATION_PATH}')
print(f'LOCAL_BASE:  {LOCAL_BASE}')

# ── Dataset preparation ────────────────────────────────────────────────────────
from nnunetv2.dataset_conversion.generate_dataset_json import generate_dataset_json

with open(os.path.join(REPO_DIR, 'dataset_info.json')) as f:
    _meta = json.load(f)
_classes = list(_meta['labels'].values())
del _classes[0]
num_classes = len(_classes) + 1   # 7

NUMBER_OF_OFFSET_LAYERS = 48

def mask_to_nnunet(mask_data, nc):
    m = mask_data.copy().astype(np.int16)
    m[m == 0] = nc
    m[m > nc] = nc
    m -= 1
    return m.astype(np.uint8)

dataset_raw_dir          = os.path.join(nnUNet_raw, 'Dataset777_GCEF')
preprocessed_dataset_dir = os.path.join(nnUNet_preprocessed, 'Dataset777_GCEF')
for d in [dataset_raw_dir, preprocessed_dataset_dir]:
    if os.path.isdir(d):
        shutil.rmtree(d)

images_dir = os.path.join(dataset_raw_dir, 'imagesTr')
labels_dir = os.path.join(dataset_raw_dir, 'labelsTr')
os.makedirs(images_dir, exist_ok=True)
os.makedirs(labels_dir, exist_ok=True)

print('Loading TIF...')
img_arr = tifffile.imread(RAW_TIFF_PATH).transpose(2, 1, 0)
print(f'  image shape (X,Y,Z): {img_arr.shape}')

print('Loading annotation...')
ann_data = nib.load(NEW_ANNOTATION_PATH).get_fdata().astype(np.uint8)
print(f'  annotation shape: {ann_data.shape}  labels: {np.unique(ann_data).tolist()}')
if ann_data.shape[:2] != img_arr.shape[:2] and ann_data.shape[1:] == img_arr.shape[:2]:
    ann_data = ann_data.transpose(2, 1, 0)

_, _, z_coords = np.where(ann_data != 0)
z_min = max(0, int(z_coords.min()) - NUMBER_OF_OFFSET_LAYERS)
z_max = min(int(z_coords.max()) + NUMBER_OF_OFFSET_LAYERS + 1, ann_data.shape[2] - 1)
print(f'  z-range: {z_coords.min()}-{z_coords.max()} -> crop [{z_min}, {z_max}]')

img_crop = img_arr[:, :, z_min:z_max]
ann_crop = ann_data[:, :, z_min:z_max]
del img_arr, ann_data
ann_nnunet = mask_to_nnunet(ann_crop, num_classes)
del ann_crop

affine = np.eye(4)
nib.save(nib.Nifti1Image(img_crop, affine), os.path.join(images_dir, 'nlm_volume_0000.nii.gz'))
del img_crop
lbl_nii = nib.Nifti1Image(ann_nnunet, affine)
lbl_nii.header.set_data_dtype(np.uint8)
nib.save(lbl_nii, os.path.join(labels_dir, 'nlm_volume.nii.gz'))
del ann_nnunet

_classes_copy = list(_meta['labels'].values())
del _classes_copy[0]
_classes_copy[0] = 'background'
_classes_copy.append('ignore')
generate_dataset_json(
    output_folder=dataset_raw_dir,
    channel_names={0: 'noNorm'},
    labels={name: i for i, name in enumerate(_classes_copy)},
    num_training_cases=1,
    file_ending='.nii.gz',
    dataset_name=_meta['DatasetName'],
)
print('[OK] Dataset ready.')

# ── Plan + preprocess ──────────────────────────────────────────────────────────
result = subprocess.run(
    [sys.executable, '-m', 'nnunetv2.experiment_planning.plan_and_preprocess_entrypoints',
     '-d', '777', '--verify_dataset_integrity'],
    env=os.environ, timeout=3600, capture_output=False
)
if result.returncode != 0:
    raise RuntimeError(f'plan_and_preprocess failed (exit {result.returncode})')

preprocessed_dir = os.path.join(nnUNet_preprocessed, 'Dataset777_GCEF')
splits = [{'train': [SAMPLE_ID], 'val': [SAMPLE_ID]}]
with open(os.path.join(preprocessed_dir, 'splits_final.json'), 'w') as f:
    json.dump(splits, f, indent=2)
print('[OK] Planning and preprocessing complete.')

# ── Training (from scratch — no pretrained weights) ───────────────────────────
os.environ['NNUNET_EARLY_STOP_ENABLED']   = '1'
os.environ['NNUNET_EARLY_STOP_PATIENCE']  = '20'
os.environ['NNUNET_EARLY_STOP_MIN_DELTA'] = '0.001'

print(f'Trainer: {TRAINER_NAME}  (LR=1e-2, from scratch)')

_wrapper = os.path.join(REPO_DIR, '_train_wrapper.py')
proc = subprocess.Popen(
    [sys.executable, _wrapper, '777', '3d_fullres', '0', '-tr', TRAINER_NAME],
    env=os.environ, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    text=True, bufsize=1,
)
for line in proc.stdout:
    print(line, end='', flush=True)
proc.wait()
if proc.returncode != 0:
    raise RuntimeError(f'Training failed (exit {proc.returncode})')

# ── Analytics ─────────────────────────────────────────────────────────────────
import matplotlib.pyplot as plt

results_dir = os.path.join(
    nnUNet_results, 'Dataset777_GCEF',
    f'{TRAINER_NAME}__nnUNetPlans__3d_fullres'
)
log_files = sorted(
    p for p in glob.glob(os.path.join(results_dir, 'fold_*', 'training_log*.txt'))
)
if not log_files:
    print('WARNING: no training log found for analytics')
else:
    epoch_re  = re.compile(r'Epoch\s+(\d+)')
    train_re  = re.compile(r'train_loss\s+(-?[\d.eE]+)')
    val_re    = re.compile(r'val_loss\s+(-?[\d.eE]+)')
    pseudo_re = re.compile(r'Pseudo dice\s+(\[.*?\])')

    epochs = {}
    current_epoch = None
    with open(log_files[-1], 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            m = epoch_re.search(line)
            if m:
                current_epoch = int(m.group(1))
                epochs.setdefault(current_epoch, {'train_loss': float('nan'), 'val_loss': float('nan'), 'mean_dice': float('nan')})
                continue
            if current_epoch is None:
                continue
            m = train_re.search(line)
            if m:
                epochs[current_epoch]['train_loss'] = float(m.group(1))
            m = val_re.search(line)
            if m:
                epochs[current_epoch]['val_loss'] = float(m.group(1))
            m = pseudo_re.search(line)
            if m:
                vals = re.findall(r'np\.float32\(([-\d.eEnaninf]+)\)|(?<![a-zA-Z\d(])([-\d.eE]+)(?![a-zA-Z\d])', m.group(1))
                arr = []
                for g1, g2 in vals:
                    v = g1 if g1 else g2
                    try:
                        arr.append(float('nan') if v == 'nan' else float(v))
                    except ValueError:
                        pass
                arr = np.array(arr, dtype=float)
                valid = arr[~np.isnan(arr)]
                if len(valid) > 0:
                    epochs[current_epoch]['mean_dice'] = float(np.mean(valid))

    ep  = sorted(epochs.keys())
    x   = np.array(ep)
    tl  = np.array([epochs[e]['train_loss'] for e in ep])
    vl  = np.array([epochs[e]['val_loss']   for e in ep])
    md  = np.array([epochs[e]['mean_dice']  for e in ep])

    analytics_dir = os.path.join(results_dir, 'analytics')
    os.makedirs(analytics_dir, exist_ok=True)

    import pandas as pd
    pd.DataFrame({'epoch': ep, 'train_loss': tl, 'val_loss': vl, 'mean_dice': md}).to_csv(
        os.path.join(analytics_dir, 'training_metrics.csv'), index=False
    )

    fig, ax1 = plt.subplots(figsize=(12, 6))
    ax1.plot(x, tl, label='Train Loss', color='tab:blue',   lw=2.5)
    ax1.plot(x, vl, label='Val Loss',   color='tab:orange', lw=2.5)
    ax1.set_xlabel('Epoch'); ax1.set_ylabel('Loss'); ax1.grid(True, alpha=0.3)
    ax2 = ax1.twinx()
    mask = ~np.isnan(md)
    if mask.any():
        ax2.plot(x[mask], md[mask], label='Mean Dice', color='tab:green', lw=2.5, marker='o', markersize=4)
        ax2.set_ylabel('Mean Dice'); ax2.set_ylim(0, 1)
    plt.title(f'Training Metrics — fresh_bnei_reem_i3_scratch  (LR 1e-2, from scratch)\n{len(ep)} epochs', fontweight='bold')
    lines1, l1 = ax1.get_legend_handles_labels()
    lines2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, l1 + l2, loc='upper right')
    fig.tight_layout()
    fig.savefig(os.path.join(analytics_dir, 'training_metrics.png'), dpi=150, bbox_inches='tight')
    fig.savefig(os.path.join(analytics_dir, 'training_metrics.pdf'), bbox_inches='tight')
    plt.close(fig)
    print(f'[OK] Analytics saved to {analytics_dir}')

print('\n=== fresh_bnei_reem_i3_scratch training complete ===')
