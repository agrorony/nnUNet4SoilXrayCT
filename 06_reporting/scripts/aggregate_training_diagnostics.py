"""aggregate_training_diagnostics.py (S13) — cross-run training diagnostics.

Walks the HIVE nnUNet_resources tree, finds every nnU-Net training_log_*.txt
across both soil branches (Mishmar HaNegev / Loess, Bnei Re'em / Vertisol),
parses per-epoch train_loss / val_loss / pseudo Dice, and writes:

  06_reporting/training_diagnostics/
    all_runs_epoch_metrics.csv          long-form epoch metrics, every run
    run_summary_mishmar_hanegev.csv     summary table (also .png render)
    run_summary_bnei_reem.csv
    curves_mishmar_hanegev.png          3-panel overlay: train/val loss, dice
    curves_bnei_reem.png
    branch_comparison.png               side-by-side branch comparison
    SUMMARY.md                          written narrative

Re-run any time after new training runs land on the HIVE share:
    python aggregate_training_diagnostics.py

A run directory is any directory that directly contains training_log*.txt
files (nnU-Net writes a new file each time a fold's training (re)starts, so
a directory with several tiny files plus one large one is a single run with
aborted restarts — all files in a directory are merged by epoch number).
Duplicated backup copies under `_clean_essential/` are skipped.

Note on Dice inflation: every run here trains on a single CT volume split
into one train + one validation case (per-epoch log line: "This split has 1
training and 1 validation cases", with an explicit nnU-Net warning that
validation cases may overlap the training set). Dice values are therefore
optimistic relative to a held-out-volume evaluation and should be read as a
training-convergence diagnostic, not a generalization estimate.
"""
import glob
import math
import os
import re

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HIVE_BASE = r"\\hive3065\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources"
REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT_DIR = os.path.join(REPO_DIR, '06_reporting', 'training_diagnostics')

TIMESTAMP_RE = re.compile(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})')
EPOCH_RE = re.compile(r'Epoch (\d+) *$')
TRAIN_LOSS_RE = re.compile(r'train_loss\s+(-?[\d.eE]+)')
VAL_LOSS_RE = re.compile(r'val_loss\s+(-?[\d.eE]+)')
DICE_LIST_RE = re.compile(r'Pseudo dice \[(.*)\]')
FLOAT_RE = re.compile(r'np\.float32\(([^)]+)\)')

MISHMAR = "Mishmar HaNegev (Loess)"
BNEI_REEM = "Bnei Re'em (Vertisol)"

# Runs excluded from analysis/plots (kept on the HIVE share — this is a report-level
# filter, not a deletion). Each is an intermediate checkpoint in a Bnei Re'em fine-tune
# chain that was strictly superseded by a later, better run in the same lineage, or a
# crashed/aborted attempt. Reviewed and confirmed 2026-07-22.
EXCLUDED_RUNS = {
    'iter01': "superseded by iter04 (dice 0.67 -> 0.96 in the same iter0X lineage)",
    'iter02': "superseded by iter04 (dice 0.71 -> 0.96 in the same iter0X lineage)",
    'iter03': "crashed — 7 restarts, only 38 epochs, dice 0.47; abandoned in favor of iter04",
    'fresh_bnei_reem_i2': "superseded by fresh_bnei_reem_i4 (dice 0.79 -> 0.98 in the fresh_bnei_reem lineage)",
    'fresh_bnei_reem_i3': "superseded by fresh_bnei_reem_i4 (dice 0.83 -> 0.98 in the fresh_bnei_reem lineage)",
    'fresh_bnei_reem_i3_lowlr': "superseded by fresh_bnei_reem_i4 (dice 0.90 -> 0.98 in the fresh_bnei_reem lineage)",
}

# Fixed categorical (identity) palette — Okabe-Ito, colorblind-safe, assigned in a fixed
# chronological order per branch. Used now that exclusion has trimmed each branch to a
# small run count where per-run identity (not a sequential "recency" ramp) is the goal.
CATEGORICAL_PALETTE = ['#0072B2', '#D55E00', '#009E73', '#CC79A7', '#E69F00', '#56B4E9', '#000000', '#F0E442']
BRANCH_COLOR = {MISHMAR: '#c2540a', BNEI_REEM: '#1a5aa8'}  # mid-tone anchor for comparison plots


def classify_branch(rel_path):
    return MISHMAR if 'mishmar' in rel_path.lower() else BNEI_REEM


def discover_runs():
    runs = []
    for root, dirs, files in os.walk(HIVE_BASE):
        if '_clean_essential' in root:
            continue
        logs = sorted(f for f in files if f.startswith('training_log') and f.endswith('.txt'))
        if not logs:
            continue
        rel = os.path.relpath(root, HIVE_BASE)
        # run name = the first path component that isn't a container/nnUNet-internal dir
        parts = rel.split(os.sep)
        name = parts[0]
        if name in ('bnei_reem_iter04',):
            name = parts[1]
        if name.startswith('multi_sample_'):
            name = name[len('multi_sample_'):]
        if name in EXCLUDED_RUNS:
            print(f'[skip] {name}: {EXCLUDED_RUNS[name]}')
            continue
        runs.append({
            'name': name,
            'rel_path': rel,
            'branch': classify_branch(rel),
            'log_files': [os.path.join(root, f) for f in logs],
        })
    return runs


def parse_run(log_files):
    epoch_data = {}
    current_epoch = None
    timestamps = []
    for lf in log_files:
        with open(lf, encoding='utf-8', errors='ignore') as f:
            for line in f:
                ts_m = TIMESTAMP_RE.match(line)
                if ts_m:
                    timestamps.append(ts_m.group(1))
                m = EPOCH_RE.search(line)
                if m and 'Epoch time' not in line:
                    current_epoch = int(m.group(1))
                    epoch_data.setdefault(current_epoch, {'epoch': current_epoch})
                    continue
                if current_epoch is None:
                    continue
                m = TRAIN_LOSS_RE.search(line)
                if m:
                    epoch_data[current_epoch]['train_loss'] = float(m.group(1))
                    continue
                m = VAL_LOSS_RE.search(line)
                if m:
                    epoch_data[current_epoch]['val_loss'] = float(m.group(1))
                    continue
                m = DICE_LIST_RE.search(line)
                if m:
                    vals = [float(x) for x in FLOAT_RE.findall(m.group(1))]
                    vals = [v for v in vals if not math.isnan(v)]
                    if vals:
                        epoch_data[current_epoch]['mean_dice'] = sum(vals) / len(vals)
    return epoch_data, (min(timestamps) if timestamps else None), (max(timestamps) if timestamps else None)


def build_dataframes(runs):
    epoch_rows = []
    summary_rows = []
    for run in runs:
        epoch_data, start_ts, end_ts = parse_run(run['log_files'])
        if not epoch_data:
            continue
        for e in epoch_data.values():
            epoch_rows.append({'run': run['name'], 'branch': run['branch'], **e})
        edf = pd.DataFrame(epoch_data.values()).sort_values('epoch')
        dice_rows = edf.dropna(subset=['mean_dice']) if 'mean_dice' in edf else edf.iloc[0:0]
        if len(dice_rows):
            best = dice_rows.loc[dice_rows['mean_dice'].idxmax()]
            best_epoch, best_dice = int(best['epoch']), float(best['mean_dice'])
        else:
            best_epoch, best_dice = None, None
        last = edf.iloc[-1]
        final_dice = round(float(last['mean_dice']), 4) if 'mean_dice' in last and pd.notna(last.get('mean_dice')) else None
        n_epochs = int(edf['epoch'].max()) + 1
        n_restarts = len(run['log_files'])

        flags = []
        if best_dice is not None and final_dice is not None and (best_dice - final_dice) > 0.05:
            flags.append('declining')  # dice fell >5pp from its peak by the end of the run
        if n_epochs < 40:
            flags.append('short_run')
        if n_restarts >= 5:
            flags.append('many_restarts')
        if best_dice is not None and best_dice < 0.75:
            flags.append('low_peak')

        summary_rows.append({
            'run': run['name'],
            'branch': run['branch'],
            'start_date': start_ts[:10] if start_ts else None,
            'n_epochs': n_epochs,
            'n_restarts': n_restarts,
            'best_epoch': best_epoch,
            'best_dice_val': round(best_dice, 4) if best_dice is not None else None,
            'final_epoch': int(last['epoch']),
            'final_train_loss': round(float(last['train_loss']), 4) if 'train_loss' in last and pd.notna(last.get('train_loss')) else None,
            'final_val_loss': round(float(last['val_loss']), 4) if 'val_loss' in last and pd.notna(last.get('val_loss')) else None,
            'final_dice_val': final_dice,
            'flags': ';'.join(flags),
        })
    epoch_df = pd.DataFrame(epoch_rows)
    summary_df = pd.DataFrame(summary_rows).sort_values(['branch', 'start_date'])
    return epoch_df, summary_df


def plot_branch_curves(epoch_df, summary_df, branch, out_path):
    runs_ordered = summary_df.loc[summary_df['branch'] == branch].sort_values('start_date')['run'].tolist()
    n = len(runs_ordered)
    colors = [CATEGORICAL_PALETTE[i % len(CATEGORICAL_PALETTE)] for i in range(n)]

    branch_epochs = epoch_df.loc[epoch_df['branch'] == branch, 'epoch']
    max_epoch = branch_epochs.max() if len(branch_epochs) else 0
    median_run_len = epoch_df[epoch_df['branch'] == branch].groupby('run')['epoch'].max().median()
    use_symlog = max_epoch > 4 * max(median_run_len, 1)

    fig, axes = plt.subplots(1, 3, figsize=(18, 5.2))
    metrics = [('train_loss', 'Train loss (lower/more negative = better)'),
               ('val_loss', 'Val loss (lower/more negative = better)'),
               ('mean_dice', 'Val Dice')]
    for ax, (col, title) in zip(axes, metrics):
        for run_name, color in zip(runs_ordered, colors):
            sub = epoch_df[(epoch_df['branch'] == branch) & (epoch_df['run'] == run_name)].sort_values('epoch')
            sub = sub.dropna(subset=[col])
            if sub.empty:
                continue
            ax.plot(sub['epoch'], sub[col], color=color, lw=1.8, alpha=0.9, label=run_name)
        ax.set_xlabel('Epoch' + (' (symlog scale — one run ran far longer than the rest)' if use_symlog else ''))
        ax.set_title(title, fontsize=11)
        ax.grid(True, alpha=0.25)
        if use_symlog:
            ax.set_xscale('symlog', linthresh=20)
        if col == 'mean_dice':
            ax.set_ylim(0, 1)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower center', ncol=min(n, 6), bbox_to_anchor=(0.5, -0.15),
               fontsize=9, title='Run (chronological order)')
    fig.suptitle(f'{branch} — all training runs ({n} runs)', fontsize=14, fontweight='bold')
    fig.tight_layout(rect=[0, 0.05, 1, 1])
    fig.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)


def render_table_png(df, title, out_path):
    cols = ['run', 'start_date', 'n_epochs', 'best_epoch', 'best_dice_val',
            'final_epoch', 'final_train_loss', 'final_val_loss', 'final_dice_val']
    col_widths = [0.26, 0.11, 0.09, 0.09, 0.11, 0.09, 0.11, 0.09, 0.11]
    fig, ax = plt.subplots(figsize=(16, 0.5 + 0.4 * len(df)))
    ax.axis('off')
    tbl = ax.table(cellText=df[cols].values, colLabels=cols, colWidths=col_widths,
                    loc='center', cellLoc='center')
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(9)
    tbl.scale(1, 1.5)
    for j in range(len(cols)):
        tbl[0, j].set_facecolor('#2c3e50')
        tbl[0, j].set_text_props(color='white', fontweight='bold')
    for i in range(len(df)):
        tbl[i + 1, 0].set_text_props(ha='left')
    ax.set_title(title, fontsize=13, fontweight='bold', pad=20)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)


def plot_branch_comparison(summary_df, out_path):
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.2))
    branches = [MISHMAR, BNEI_REEM]
    positions = [0, 1]

    # Panel A: best Dice per run, by branch
    ax = axes[0]
    for pos, branch in zip(positions, branches):
        vals = summary_df.loc[summary_df['branch'] == branch, 'best_dice_val'].dropna()
        jitter = np.random.default_rng(0).uniform(-0.08, 0.08, size=len(vals))
        ax.scatter(np.full(len(vals), pos) + jitter, vals, color=BRANCH_COLOR[branch], s=50, alpha=0.85, zorder=3)
        if len(vals):
            ax.scatter([pos], [vals.median()], color=BRANCH_COLOR[branch], marker='_', s=800, lw=3, zorder=4)
    ax.set_xticks(positions)
    ax.set_xticklabels(['Mishmar\nHaNegev', "Bnei\nRe'em"])
    ax.set_ylabel('Best val Dice reached')
    ax.set_ylim(0, 1)
    ax.set_title('Peak Dice per run (bar = median)', fontsize=11)
    ax.grid(True, axis='y', alpha=0.25)

    # Panel B: final val_loss per run, by branch
    ax = axes[1]
    for pos, branch in zip(positions, branches):
        vals = summary_df.loc[summary_df['branch'] == branch, 'final_val_loss'].dropna()
        jitter = np.random.default_rng(1).uniform(-0.08, 0.08, size=len(vals))
        ax.scatter(np.full(len(vals), pos) + jitter, vals, color=BRANCH_COLOR[branch], s=50, alpha=0.85, zorder=3)
        if len(vals):
            ax.scatter([pos], [vals.median()], color=BRANCH_COLOR[branch], marker='_', s=800, lw=3, zorder=4)
    ax.set_xticks(positions)
    ax.set_xticklabels(['Mishmar\nHaNegev', "Bnei\nRe'em"])
    ax.set_ylabel('Final val loss (more negative = better)')
    ax.set_title('Final val loss per run (bar = median)', fontsize=11)
    ax.grid(True, axis='y', alpha=0.25)

    # Panel C: convergence speed (epoch of best dice) vs quality (best dice)
    ax = axes[2]
    for branch in branches:
        sub = summary_df[summary_df['branch'] == branch].dropna(subset=['best_epoch', 'best_dice_val'])
        ax.scatter(sub['best_epoch'], sub['best_dice_val'], color=BRANCH_COLOR[branch], s=60, alpha=0.85,
                   label=branch, zorder=3)
    ax.set_xlabel('Epoch of peak Dice (convergence speed)')
    ax.set_ylabel('Peak val Dice')
    ax.set_ylim(0, 1)
    ax.set_title('Convergence speed vs. peak quality', fontsize=11)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=9, loc='lower right')

    fig.suptitle("Branch comparison — Mishmar HaNegev vs. Bnei Re'em", fontsize=14, fontweight='bold')
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)


def write_summary_md(summary_df, out_path):
    lines = ['# Training diagnostics — cross-run summary\n']
    lines.append('Auto-generated by `06_reporting/scripts/aggregate_training_diagnostics.py`. '
                  'Re-run after new training runs land on the HIVE share.\n')
    lines.append('**Caveat:** every run trains on a single CT volume split into one train + one '
                  'validation case, and nnU-Net logs a leakage warning ("Some validation cases are '
                  'also in the training set") on every run. Dice values here measure training '
                  'convergence, not held-out generalization.\n')

    for branch in [MISHMAR, BNEI_REEM]:
        sub = summary_df[summary_df['branch'] == branch]
        lines.append(f'\n## {branch} ({len(sub)} runs)\n')
        lines.append(sub.drop(columns=['branch']).to_markdown(index=False))

        dice = sub['best_dice_val'].dropna()
        lines.append('')
        lines.append(f'- Peak Dice across runs: median {dice.median():.3f}, '
                      f'range {dice.min():.3f}-{dice.max():.3f}, std {dice.std():.3f}.')
        conv = sub['best_epoch'].dropna()
        if len(conv):
            lines.append(f'- Epochs to peak Dice: median {conv.median():.0f} '
                          f'(range {conv.min():.0f}-{conv.max():.0f}).')
        flagged = sub[sub['flags'] != '']
        if len(flagged):
            lines.append('- Flagged runs:')
            for _, r in flagged.iterrows():
                lines.append(f"  - `{r['run']}` ({r['start_date']}): {r['flags'].replace(';', ', ')} "
                              f"— peak Dice {r['best_dice_val']}, final Dice {r['final_dice_val']}, "
                              f"{r['n_epochs']} epochs, {r['n_restarts']} restart(s).")
        else:
            lines.append('- No runs flagged (no >5pp decline from peak, no runs under 40 epochs, '
                          'no runs with 5+ restarts, no runs peaking below 0.75 Dice).')
        lines.append('')

    m = summary_df[summary_df['branch'] == MISHMAR]['best_dice_val'].dropna()
    b = summary_df[summary_df['branch'] == BNEI_REEM]['best_dice_val'].dropna()
    lines.append('\n## Branch comparison\n')
    lines.append(f'- Mishmar HaNegev: n={len(m)} runs, median peak Dice {m.median():.3f}, std {m.std():.3f}.')
    lines.append(f"- Bnei Re'em: n={len(b)} runs, median peak Dice {b.median():.3f}, std {b.std():.3f}.")
    if m.std() < b.std():
        lines.append(f'- Mishmar HaNegev runs are more *consistent* run-to-run (lower Dice std) '
                      f"than Bnei Re'em, though on far fewer runs (n={len(m)} vs n={len(b)}), so this "
                      f'read is provisional.')
    lines.append('')

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    runs = discover_runs()
    print(f'Discovered {len(runs)} run directories on HIVE share.')
    epoch_df, summary_df = build_dataframes(runs)

    epoch_df.to_csv(os.path.join(OUT_DIR, 'all_runs_epoch_metrics.csv'), index=False)
    summary_df.to_csv(os.path.join(OUT_DIR, 'run_summary_all.csv'), index=False)

    for branch, tag in [(MISHMAR, 'mishmar_hanegev'), (BNEI_REEM, 'bnei_reem')]:
        sub = summary_df[summary_df['branch'] == branch].reset_index(drop=True)
        sub.to_csv(os.path.join(OUT_DIR, f'run_summary_{tag}.csv'), index=False)
        render_table_png(sub, f'{branch} — run summary', os.path.join(OUT_DIR, f'run_summary_{tag}.png'))
        plot_branch_curves(epoch_df, summary_df, branch, os.path.join(OUT_DIR, f'curves_{tag}.png'))

    plot_branch_comparison(summary_df, os.path.join(OUT_DIR, 'branch_comparison.png'))
    write_summary_md(summary_df, os.path.join(OUT_DIR, 'SUMMARY.md'))
    print(f'[OK] Wrote diagnostics to {OUT_DIR}')


if __name__ == '__main__':
    main()
