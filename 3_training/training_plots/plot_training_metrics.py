"""plot_training_metrics.py — consolidated training-log-to-plot tool (S8).

Replaces `_plot_i3_metrics.py` and `_plot_lowlr_metrics.py`. Parses
train_loss/val_loss/Pseudo-dice directly from an nnUNet training log and
plots them; supports --in-progress for parsing a log while training is
still running (matching the i3_lowlr script's original behavior of just
reading whatever is in the log so far, without asserting completion).

Usage:
    python plot_training_metrics.py --iteration-name fresh_bnei_reem_i3 \
        --trainer-name nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss
"""
import argparse
import glob
import os
import re

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HIVE_BASE = r'\\hive3065\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources'


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--iteration-name', required=True)
    parser.add_argument('--trainer-name', default='nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss')
    parser.add_argument('--results-dir', default=None, help='Override; else derived from --iteration-name.')
    parser.add_argument('--in-progress', action='store_true',
                         help='Parse whatever is in the log so far, without asserting training is complete '
                              '(matches the original i3_lowlr script, which ran mid-training).')
    args = parser.parse_args()

    results_dir = args.results_dir or os.path.join(
        HIVE_BASE, f'multi_sample_{args.iteration_name}', 'nnUNet_results', 'Dataset777_GCEF',
        f'{args.trainer_name}__nnUNetPlans__3d_fullres')

    log_files = sorted(glob.glob(os.path.join(results_dir, 'fold_*', 'training_log*.txt')))
    if not log_files:
        raise FileNotFoundError(f'No training_log*.txt found under {results_dir}')
    log_path = log_files[-1]
    print(f'Parsing: {log_path}' + (' (in-progress run)' if args.in_progress else ''))

    epoch_re = re.compile(r'Epoch\s+(\d+)')
    train_re = re.compile(r'train_loss\s+(-?[\d.eE]+)')
    val_re = re.compile(r'val_loss\s+(-?[\d.eE]+)')
    pseudo_re = re.compile(r'Pseudo dice\s+(\[.*?\])')

    epochs = {}
    current_epoch = None
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
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
                raw = m.group(1)
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

    if not epochs and not args.in_progress:
        raise RuntimeError('No epochs parsed.')
    if not epochs:
        print('No epochs parsed yet (in-progress run) — nothing to plot.')
        return

    ep_sorted = sorted(epochs.keys())
    x = np.array(ep_sorted)
    train_loss = np.array([epochs[e]['train_loss'] for e in ep_sorted])
    val_loss = np.array([epochs[e]['val_loss'] for e in ep_sorted])
    mean_dice = np.array([epochs[e]['mean_dice'] for e in ep_sorted])

    n_epochs = len(ep_sorted)
    n_dice_ok = int(np.sum(~np.isnan(mean_dice)))
    print(f'Parsed {n_epochs} epochs  |  Dice populated: {n_dice_ok}/{n_epochs}')

    analytics_dir = os.path.join(results_dir, 'analytics')
    os.makedirs(analytics_dir, exist_ok=True)

    fig, ax1 = plt.subplots(figsize=(12, 6))
    ax1.plot(x, train_loss, label='Train Loss', color='tab:blue', lw=2.5)
    ax1.plot(x, val_loss, label='Val Loss', color='tab:orange', lw=2.5)
    ax1.set_xlabel('Epoch'); ax1.set_ylabel('Loss'); ax1.grid(True, alpha=0.3)

    ax2 = ax1.twinx()
    dice_valid = ~np.isnan(mean_dice)
    if dice_valid.any():
        ax2.plot(x[dice_valid], mean_dice[dice_valid], label='Mean Dice', color='tab:green', lw=2.5, marker='o', markersize=4)
        ax2.set_ylabel('Mean Dice (non-NaN classes)'); ax2.set_ylim(0, 1)

    title = f'Training Metrics — {args.iteration_name}\n{n_epochs} epochs  |  Dice: {n_dice_ok}/{n_epochs} populated'
    if args.in_progress:
        title += '  [IN PROGRESS]'
    plt.title(title, fontsize=11, fontweight='bold')

    l1, la1 = ax1.get_legend_handles_labels()
    l2, la2 = ax2.get_legend_handles_labels()
    ax1.legend(l1 + l2, la1 + la2, loc='upper right')
    fig.tight_layout()

    png_path = os.path.join(analytics_dir, f'training_metrics_{args.iteration_name}.png')
    pdf_path = os.path.join(analytics_dir, f'training_metrics_{args.iteration_name}.pdf')
    fig.savefig(png_path, dpi=150, bbox_inches='tight')
    fig.savefig(pdf_path, bbox_inches='tight')
    plt.close(fig)

    print(f'\nSaved PNG: {png_path}')
    print(f'Saved PDF: {pdf_path}')


if __name__ == '__main__':
    main()
