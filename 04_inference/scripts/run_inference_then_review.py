"""run_inference_then_review.py — consolidated inference+review orchestrator (S5).

Replaces two repo-root orchestration scripts that both followed the same
"run inference, then open napari" shape but differed in whether they also
built a two-model comparison chart:

  * `_run_fresh_then_compare_napari.py` — runs inference for one model
    (fresh_bnei_reem), builds a train-loss/val-loss/Dice comparison chart
    against a second, already-inferred model (iter04_continue), then opens
    the napari `comparison` viewer.
  * `_run_iter04_continue.py` — full read confirmed this is PURE
    orchestration (no training/dataset-prep code at all): it only
    subprocess-calls the per-iteration inference script and then opens the
    napari `fullvol` viewer on slices 50-70. No second model, no chart.
    Per REORG amendment/§9 Q7, this maps to S5 as a single-model variant,
    not to S1.

This script supports both shapes: give only --iteration-name-a for the
single-model "infer then review" flow (as `_run_iter04_continue.py` did),
or give both --iteration-name-a and --iteration-name-b to also build the
two-model comparison chart (as `_run_fresh_then_compare_napari.py` did).

The originals are preserved for reference under
04_inference/scripts/legacy_per_iteration/.

Usage:
    python run_inference_then_review.py --iteration-name-a fresh_bnei_reem \
        --iteration-name-b iter04_continue --gt-path "\\hive...\merged_GT.nii.gz" --zrange 50 70

    python run_inference_then_review.py --iteration-name-a iter04_continue \
        --gt-path "\\hive...\merged_GT.nii.gz" --zrange 50 70
"""
import argparse
import os
import subprocess
import sys

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
RUN_INFERENCE = os.path.join(REPO_DIR, '04_inference', 'scripts', 'run_inference.py')
LAUNCH_NAPARI = os.path.join(REPO_DIR, '06_reporting', 'scripts', 'launch_napari_review.py')
HIVE_BASE = r'\\hive3065\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources'
HIVE_ROOT = r'\\hive3065\Yael_Mishael\Rony\remote_computer backup'
TRAINER = 'nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss__nnUNetPlans__3d_fullres'


def run_inference(iteration_name, sample_id, gpu):
    print('=' * 70)
    print(f'Running inference — {iteration_name} model')
    print('=' * 70)
    cmd = [sys.executable, RUN_INFERENCE, '--iteration-name', iteration_name, '--sample-id', sample_id]
    if gpu is not None:
        cmd += ['--gpu', str(gpu)]
    proc = subprocess.Popen(cmd, env=os.environ, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    for line in proc.stdout:
        print(line, end='', flush=True)
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f'Inference failed for {iteration_name} (exit {proc.returncode})')


def build_comparison_chart(iteration_a, iteration_b, out_dir):
    import numpy as np
    import pandas as pd
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    def csv_path(iteration_name):
        return os.path.join(HIVE_BASE, f'multi_sample_{iteration_name}', 'nnUNet_results',
                             'Dataset777_GCEF', TRAINER, 'analytics', 'training_metrics_summary.csv')

    df_a = pd.read_csv(csv_path(iteration_a))
    df_b = pd.read_csv(csv_path(iteration_b))
    df_a['mean_dice'] = df_a['mean_dice'].where(df_a['mean_dice'] < 2, np.nan)
    df_b['mean_dice'] = df_b['mean_dice'].where(df_b['mean_dice'] < 2, np.nan)

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    axes[0].plot(df_a['epoch'], df_a['train_loss'], color='tab:blue', lw=2, label=iteration_a)
    axes[0].plot(df_b['epoch'], df_b['train_loss'], color='tab:orange', lw=2, label=iteration_b)
    axes[0].set_title('Train Loss', fontweight='bold'); axes[0].legend(); axes[0].grid(alpha=0.3)

    best_a = df_a['val_loss'].min(); best_a_ep = df_a.loc[df_a['val_loss'].idxmin(), 'epoch']
    best_b = df_b['val_loss'].min(); best_b_ep = df_b.loc[df_b['val_loss'].idxmin(), 'epoch']
    axes[1].plot(df_a['epoch'], df_a['val_loss'], color='tab:blue', lw=2, label=iteration_a)
    axes[1].plot(df_b['epoch'], df_b['val_loss'], color='tab:orange', lw=2, label=iteration_b)
    axes[1].axhline(best_a, color='tab:blue', ls='--', lw=1, alpha=0.6, label=f'best={best_a:.4f} @ep{int(best_a_ep)}')
    axes[1].axhline(best_b, color='tab:orange', ls='--', lw=1, alpha=0.6, label=f'best={best_b:.4f} @ep{int(best_b_ep)}')
    axes[1].set_title('Val Loss', fontweight='bold'); axes[1].legend(); axes[1].grid(alpha=0.3)

    axes[2].plot(df_a['epoch'], df_a['mean_dice'], color='tab:blue', lw=2, label=iteration_a)
    axes[2].plot(df_b['epoch'], df_b['mean_dice'], color='tab:orange', lw=2, label=iteration_b)
    axes[2].set_title('EMA Pseudo Dice', fontweight='bold'); axes[2].set_ylim(0, 1.05)
    axes[2].legend(); axes[2].grid(alpha=0.3)

    plt.suptitle(f'{iteration_a} vs {iteration_b}', fontsize=14, fontweight='bold')
    plt.tight_layout()
    os.makedirs(out_dir, exist_ok=True)
    png = os.path.join(out_dir, f'comparison_{iteration_a}_vs_{iteration_b}.png')
    pdf = os.path.join(out_dir, f'comparison_{iteration_a}_vs_{iteration_b}.pdf')
    plt.savefig(png, dpi=150, bbox_inches='tight')
    plt.savefig(pdf, bbox_inches='tight')
    plt.close()
    print(f'Saved: {png}')
    print(f'Saved: {pdf}')
    print(f'{iteration_a}: best_val_loss={best_a:.4f} (ep {int(best_a_ep)})')
    print(f'{iteration_b}: best_val_loss={best_b:.4f} (ep {int(best_b_ep)})')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--iteration-name-a', required=True)
    parser.add_argument('--iteration-name-b', help='If given, also build a two-model comparison chart.')
    parser.add_argument('--sample-id', default='nlm_volume')
    parser.add_argument('--gt-path', required=True)
    parser.add_argument('--zrange', type=int, nargs=2, metavar=('START', 'END'))
    parser.add_argument('--gpu', type=int, default=0)
    parser.add_argument('--skip-inference', action='store_true',
                         help='Skip running inference for iteration-a (assume already inferred).')
    parser.add_argument('--comparison-out-dir', default=os.path.join(REPO_DIR, '06_reporting', 'selected_outputs'))
    args = parser.parse_args()

    vol_path = os.path.join(HIVE_ROOT, '10.5', f'{args.sample_id}.tif')
    pred_a_path = os.path.join(HIVE_BASE, f'bnei_reem_{args.iteration_name_a}', 'inference_concatenated', f'{args.sample_id}.nii.gz')

    if not args.skip_inference:
        run_inference(args.iteration_name_a, args.sample_id, args.gpu)
    assert os.path.isfile(pred_a_path), f'Prediction not found after inference: {pred_a_path}'
    print(f'[OK] Prediction ready: {pred_a_path}')

    napari_preds = [f'{args.iteration_name_a}={pred_a_path}']

    if args.iteration_name_b:
        print('\n' + '=' * 70)
        print('Building comparison chart')
        print('=' * 70)
        build_comparison_chart(args.iteration_name_a, args.iteration_name_b, args.comparison_out_dir)
        pred_b_path = os.path.join(HIVE_BASE, f'bnei_reem_{args.iteration_name_b}', 'inference_concatenated', f'{args.sample_id}.nii.gz')
        napari_preds.append(f'{args.iteration_name_b}={pred_b_path}')
        mode = 'comparison'
    else:
        mode = 'fullvol'

    print('\n' + '=' * 70)
    print(f'Launching napari review — mode={mode}')
    print('=' * 70)
    cmd = [sys.executable, LAUNCH_NAPARI, '--mode', mode,
           '--volume-path', vol_path, '--gt-path', args.gt_path]
    for p in napari_preds:
        cmd += ['--pred-paths', p]
    if args.zrange:
        cmd += ['--zrange', str(args.zrange[0]), str(args.zrange[1])]
    subprocess.run(cmd, env=os.environ, check=True)


if __name__ == '__main__':
    main()
