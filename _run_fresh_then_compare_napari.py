import sys

if __name__ != '__main__':
    sys.exit(0)

import os
import subprocess

os.environ['CUDA_VISIBLE_DEVICES'] = '0'

REPO_DIR  = r'C:\Users\rony.schwartz\Documents\nnUNet4SoilXrayCT'
HIVE_BASE = r'\\hive3065\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources'
TRAINER   = 'nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss__nnUNetPlans__3d_fullres'

# ── Step 1: Fresh model inference ─────────────────────────────────────────────
print('=' * 70)
print('Step 1: Inference — fresh_bnei_reem model')
print('=' * 70)
proc = subprocess.Popen(
    [sys.executable, os.path.join(REPO_DIR, '_run_inference_fresh_bnei_reem.py')],
    env=os.environ,
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    text=True, bufsize=1,
)
for line in proc.stdout:
    print(line, end='', flush=True)
proc.wait()
if proc.returncode != 0:
    raise RuntimeError(f'Inference failed (exit {proc.returncode})')
print('\n[OK] Fresh inference complete.')

# ── Step 2: Comparison chart ───────────────────────────────────────────────────
print('\n' + '=' * 70)
print('Step 2: Generating comparison chart')
print('=' * 70)

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

csv_continue = os.path.join(HIVE_BASE, 'multi_sample_iter04_continue',
    'nnUNet_results', 'Dataset777_GCEF', TRAINER,
    'analytics', 'training_metrics_summary.csv')
csv_fresh = os.path.join(HIVE_BASE, 'multi_sample_fresh_bnei_reem',
    'nnUNet_results', 'Dataset777_GCEF', TRAINER,
    'analytics', 'training_metrics_summary.csv')

df_c = pd.read_csv(csv_continue)
df_f = pd.read_csv(csv_fresh)

# Filter out mean_dice=32.0 (parsing artifact)
df_c['mean_dice'] = df_c['mean_dice'].where(df_c['mean_dice'] < 2, np.nan)
df_f['mean_dice'] = df_f['mean_dice'].where(df_f['mean_dice'] < 2, np.nan)

fig, axes = plt.subplots(1, 3, figsize=(18, 5))

# Train loss
axes[0].plot(df_c['epoch'], df_c['train_loss'], color='tab:blue',   lw=2, label='iter04_continue (44 ep)')
axes[0].plot(df_f['epoch'], df_f['train_loss'], color='tab:orange', lw=2, label='fresh_bnei_reem (167 ep)')
axes[0].set_title('Train Loss', fontsize=13, fontweight='bold')
axes[0].set_xlabel('Epoch'); axes[0].set_ylabel('Loss')
axes[0].legend(); axes[0].grid(alpha=0.3)

# Val loss
axes[1].plot(df_c['epoch'], df_c['val_loss'], color='tab:blue',   lw=2, label='iter04_continue')
axes[1].plot(df_f['epoch'], df_f['val_loss'], color='tab:orange', lw=2, label='fresh_bnei_reem')
best_c = df_c['val_loss'].min(); best_c_ep = df_c.loc[df_c['val_loss'].idxmin(), 'epoch']
best_f = df_f['val_loss'].min(); best_f_ep = df_f.loc[df_f['val_loss'].idxmin(), 'epoch']
axes[1].axhline(best_c, color='tab:blue',   ls='--', lw=1, alpha=0.6, label=f'best={best_c:.4f} @ep{int(best_c_ep)}')
axes[1].axhline(best_f, color='tab:orange', ls='--', lw=1, alpha=0.6, label=f'best={best_f:.4f} @ep{int(best_f_ep)}')
axes[1].set_title('Val Loss', fontsize=13, fontweight='bold')
axes[1].set_xlabel('Epoch'); axes[1].set_ylabel('Loss')
axes[1].legend(); axes[1].grid(alpha=0.3)

# EMA Dice
axes[2].plot(df_c['epoch'], df_c['mean_dice'], color='tab:blue',   lw=2, label='iter04_continue')
axes[2].plot(df_f['epoch'], df_f['mean_dice'], color='tab:orange', lw=2, label='fresh_bnei_reem')
axes[2].set_title('EMA Pseudo Dice', fontsize=13, fontweight='bold')
axes[2].set_xlabel('Epoch'); axes[2].set_ylabel('Dice')
axes[2].set_ylim(0, 1.05); axes[2].legend(); axes[2].grid(alpha=0.3)

plt.suptitle('iter04_continue vs fresh_bnei_reem — nlm_volume (merged_GT)', fontsize=14, fontweight='bold')
plt.tight_layout()

out_png = os.path.join(REPO_DIR, '_comparison_iter04_continue_vs_fresh.png')
out_pdf = os.path.join(REPO_DIR, '_comparison_iter04_continue_vs_fresh.pdf')
plt.savefig(out_png, dpi=150, bbox_inches='tight')
plt.savefig(out_pdf, bbox_inches='tight')
plt.close()
print(f'Saved: {out_png}')
print(f'Saved: {out_pdf}')

# Print summary
print('\n=== Summary ===')
print(f'iter04_continue : epochs=44  | best_val_loss={best_c:.4f} (ep {int(best_c_ep)}) | final_val={df_c["val_loss"].iloc[-1]:.4f}')
print(f'fresh_bnei_reem : epochs=167 | best_val_loss={best_f:.4f} (ep {int(best_f_ep)}) | final_val={df_f["val_loss"].iloc[-1]:.4f}')

# ── Step 3: napari with all layers ─────────────────────────────────────────────
print('\n' + '=' * 70)
print('Step 3: Launching napari — GT + both predictions (slices 50-70)')
print('=' * 70)
subprocess.run(
    [sys.executable, os.path.join(REPO_DIR, '_launch_napari_comparison.py')],
    cwd=os.path.join(REPO_DIR, 'microsam_3d'),
    env=os.environ,
    check=True,
)
