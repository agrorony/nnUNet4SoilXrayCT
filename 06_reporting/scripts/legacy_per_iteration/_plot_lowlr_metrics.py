"""
Generate training metrics plot for fresh_bnei_reem_i3_lowlr.
Parses train_loss, val_loss, and Pseudo dice directly from the nnUNet training log.
Can be run while training is still in progress.
"""
import sys
if __name__ != '__main__':
    sys.exit(0)

import os
import re
import glob
import ast
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HIVE_BASE    = r'\\hive3065\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources'
TRAINER_NAME = 'nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss_lowlr'

results_dir = os.path.join(
    HIVE_BASE, 'multi_sample_fresh_bnei_reem_i3_lowlr',
    'nnUNet_results', 'Dataset777_GCEF',
    f'{TRAINER_NAME}__nnUNetPlans__3d_fullres'
)

log_files = sorted(
    p for p in glob.glob(os.path.join(results_dir, 'fold_*', 'training_log*.txt'))
)
if not log_files:
    raise FileNotFoundError(f'No training_log*.txt found under {results_dir}')

log_path = log_files[-1]
print(f'Parsing: {log_path}')

epoch_re     = re.compile(r'Epoch\s+(\d+)')
train_re     = re.compile(r'train_loss\s+(-?[\d.eE]+)')
val_re       = re.compile(r'val_loss\s+(-?[\d.eE]+)')
pseudo_re    = re.compile(r'Pseudo dice\s+(\[.*?\])')

epochs = {}
current_epoch = None

with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        m = epoch_re.search(line)
        if m:
            current_epoch = int(m.group(1))
            if current_epoch not in epochs:
                epochs[current_epoch] = {
                    'train_loss': float('nan'),
                    'val_loss':   float('nan'),
                    'mean_dice':  float('nan'),
                }
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
            raw = m.group(1)
            # extract values from np.float32(x) or plain floats
            vals = re.findall(r'np\.float32\(([-\d.eEnaninf]+)\)|(?<![a-zA-Z\d(])([-\d.eE]+)(?![a-zA-Z\d])', raw)
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

if not epochs:
    raise RuntimeError('No epochs parsed.')

ep_sorted = sorted(epochs.keys())
x          = np.array(ep_sorted)
train_loss = np.array([epochs[e]['train_loss'] for e in ep_sorted])
val_loss   = np.array([epochs[e]['val_loss']   for e in ep_sorted])
mean_dice  = np.array([epochs[e]['mean_dice']  for e in ep_sorted])

n_epochs   = len(ep_sorted)
n_dice_ok  = int(np.sum(~np.isnan(mean_dice)))
print(f'Parsed {n_epochs} epochs  |  Dice populated: {n_dice_ok}/{n_epochs}')
for e in ep_sorted:
    d = epochs[e]['mean_dice']
    print(f'  epoch {e:3d}  train={epochs[e]["train_loss"]:.4f}  '
          f'val={epochs[e]["val_loss"]:.4f}  dice={d:.4f}' if not np.isnan(d)
          else f'  epoch {e:3d}  train={epochs[e]["train_loss"]:.4f}  '
               f'val={epochs[e]["val_loss"]:.4f}  dice=NaN')

analytics_dir = os.path.join(results_dir, 'analytics')
os.makedirs(analytics_dir, exist_ok=True)

# ── Plot ──────────────────────────────────────────────────────────────────────
fig, ax1 = plt.subplots(figsize=(12, 6))

ax1.plot(x, train_loss, label='Train Loss', color='tab:blue',   lw=2.5)
ax1.plot(x, val_loss,   label='Val Loss',   color='tab:orange', lw=2.5)
ax1.set_xlabel('Epoch', fontsize=12)
ax1.set_ylabel('Loss',  fontsize=12)
ax1.grid(True, alpha=0.3)

ax2 = ax1.twinx()
dice_valid = ~np.isnan(mean_dice)
if dice_valid.any():
    ax2.plot(x[dice_valid], mean_dice[dice_valid],
             label='Mean Dice', color='tab:green', lw=2.5, marker='o', markersize=4)
    ax2.set_ylabel('Mean Dice (non-NaN classes)', fontsize=12)
    ax2.set_ylim(0, 1)

title = (
    f'Training Metrics — fresh_bnei_reem_i3_lowlr  (LR 1e-2 -> 2e-3)\n'
    f'{n_epochs} epochs shown  |  Dice: {n_dice_ok}/{n_epochs} populated'
)
plt.title(title, fontsize=11, fontweight='bold')

lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right')

fig.tight_layout()

png_path = os.path.join(analytics_dir, 'training_metrics_lowlr.png')
pdf_path = os.path.join(analytics_dir, 'training_metrics_lowlr.pdf')
fig.savefig(png_path, dpi=150, bbox_inches='tight')
fig.savefig(pdf_path, bbox_inches='tight')
plt.close(fig)

print(f'\nSaved PNG: {png_path}')
print(f'Saved PDF: {pdf_path}')
