"""compare_predictions.py — generalized GT-vs-model Dice/precision/recall comparison (S9).

Replaces the old repo-root `_compare_predictions.py`, which hardcoded a GT
path, a fixed three-model set (OLD/NEW/LOW_LR), 31 GT slice indices, and
three eval pairs. This version takes all of that as CLI args so it can be
reused for any GT/model set.

Label convention (unchanged from the original): GT annotation labels are
1-indexed (1=matrix, 2=stones, 3=POM, 6=pore); nnUNet predictions are
shifted by -1 (0=matrix, 1=stones, 2=POM, 5=pore). The first --model given
is treated as the baseline for the "delta vs baseline" table.

Usage:
    python compare_predictions.py \
        --gt-path GT.nii.gz \
        --model OLD=path/to/old_pred.nii.gz \
        --model NEW=path/to/new_pred.nii.gz \
        --gt-slices 26 29 30 31 32 33 ... \
        --eval-pairs 2:1:Stones 3:2:POM 6:5:Pore
"""
import argparse

import numpy as np
import nibabel as nib

DEFAULT_EVAL_PAIRS = '2:1:Stones,3:2:POM,6:5:Pore'


def parse_model_arg(spec):
    name, path = spec.split('=', 1)
    return name, path


def parse_eval_pairs(pairs):
    result = []
    for pair in pairs:
        gt_lbl, pred_lbl, name = pair.split(':')
        result.append((int(gt_lbl), int(pred_lbl), name))
    return result


def load_vol(path):
    print(f'  Loading {path}')
    return np.asarray(nib.load(path).dataobj).astype(np.int32)


def dice_metrics(gt_flat, pred_flat, gt_lbl, pred_lbl):
    g = gt_flat == gt_lbl
    p = pred_flat == pred_lbl
    tp = np.logical_and(g, p).sum()
    fp = np.logical_and(~g, p).sum()
    fn = np.logical_and(g, ~p).sum()
    denom = 2 * tp + fp + fn
    dice = (2 * tp / denom) if denom > 0 else float('nan')
    prec = (tp / (tp + fp)) if (tp + fp) > 0 else float('nan')
    rec = (tp / (tp + fn)) if (tp + fn) > 0 else float('nan')
    gt_v = int(g.sum())
    pr_v = int(p.sum())
    bias = ((pr_v - gt_v) / gt_v * 100) if gt_v > 0 else float('nan')
    return dice, prec, rec, bias, gt_v, pr_v


def print_table(title, rows):
    print(f'\n{"="*80}')
    print(f'  {title}')
    print(f'{"="*80}')
    hdr = f'{"Class":>8}  {"Dice":>6}  {"Prec":>6}  {"Recall":>6}  {"VolBias%":>9}  {"GT vox":>10}  {"Pred vox":>10}'
    print(hdr)
    print('-' * 80)
    dices = []
    for name, dice, prec, rec, bias, gv, pv in rows:
        d_str = f'{dice:.4f}' if not np.isnan(dice) else '   N/A'
        p_str = f'{prec:.4f}' if not np.isnan(prec) else '   N/A'
        r_str = f'{rec:.4f}' if not np.isnan(rec) else '   N/A'
        b_str = f'{bias:+.1f}' if not np.isnan(bias) else '   N/A'
        print(f'{name:>8}  {d_str:>6}  {p_str:>6}  {r_str:>6}  {b_str:>9}  {gv:>10,}  {pv:>10,}')
        if not np.isnan(dice):
            dices.append(dice)
    if dices:
        print(f'  Mean Dice: {np.mean(dices):.4f}')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--gt-path', required=True)
    parser.add_argument('--model', action='append', required=True, metavar='LABEL=PATH',
                         help='Repeatable. First one given is the baseline for the delta table.')
    parser.add_argument('--gt-slices', type=int, nargs='+', default=None,
                         help='Z-slice indices to restrict comparison to (matches original per-file hardcoded lists).')
    parser.add_argument('--all-slices', action='store_true', help='Use the full volume instead of --gt-slices.')
    parser.add_argument('--eval-pairs', nargs='+', default=DEFAULT_EVAL_PAIRS.split(','),
                         help='gt_label:pred_label:name triples, default matches original 2:1:Stones,3:2:POM,6:5:Pore.')
    args = parser.parse_args()

    if not args.all_slices and not args.gt_slices:
        parser.error('Provide --gt-slices or --all-slices')

    eval_pairs = parse_eval_pairs(args.eval_pairs)
    models = [parse_model_arg(m) for m in args.model]

    print('Loading volumes...')
    gt = load_vol(args.gt_path)
    preds = {name: load_vol(path) for name, path in models}

    if args.all_slices:
        gt_ann = gt
        pred_ann = {name: v for name, v in preds.items()}
    else:
        print(f'\nRestricting to {len(args.gt_slices)} annotated z-slices...')
        gt_ann = gt[:, :, args.gt_slices]
        pred_ann = {name: v[:, :, args.gt_slices] for name, v in preds.items()}

    # GT=0 unannotated, GT=1 soil matrix (background) both excluded, matching original.
    annotated = gt_ann > 1
    print(f'Annotated voxels (GT > 1, excluding matrix and empty): {annotated.sum():,}')

    gt_v = gt_ann[annotated]
    pred_v = {name: v[annotated] for name, v in pred_ann.items()}

    print('\nGT label distribution in annotated voxels:')
    for gt_lbl, pred_lbl, name in eval_pairs:
        n = (gt_v == gt_lbl).sum()
        print(f'  GT label {gt_lbl} ({name}): {n:>10,}  -> pred label {pred_lbl}')

    all_rows = {}
    for name, _ in models:
        rows = [(pair_name,) + dice_metrics(gt_v, pred_v[name], gt_lbl, pred_lbl)
                for gt_lbl, pred_lbl, pair_name in eval_pairs]
        all_rows[name] = rows
        print_table(name, rows)

    # Delta vs baseline (first model given)
    baseline_name = models[0][0]
    rows_base = all_rows[baseline_name]
    print(f'\n{"="*80}')
    print(f'  Delta vs baseline ({baseline_name})  (positive = better than baseline)')
    print(f'{"="*80}')
    hdr = f'{"Model":>10}  {"Class":>8}  {"dDice":>7}  {"dPrec":>7}  {"dRecall":>7}  {"dVolBias%":>10}'
    print(hdr)
    print('-' * 80)
    for name, _ in models[1:]:
        rows = all_rows[name]
        for (pname, d_n, p_n, r_n, b_n, *_), (_, d_o, p_o, r_o, b_o, *__) in zip(rows, rows_base):
            dd = d_n - d_o if not (np.isnan(d_n) or np.isnan(d_o)) else float('nan')
            dp = p_n - p_o if not (np.isnan(p_n) or np.isnan(p_o)) else float('nan')
            dr = r_n - r_o if not (np.isnan(r_n) or np.isnan(r_o)) else float('nan')
            db = b_n - b_o if not (np.isnan(b_n) or np.isnan(b_o)) else float('nan')
            flag = '  <<< WORSE' if not np.isnan(dd) and dd < -0.02 else ''
            print(f'{name:>10}  {pname:>8}  {dd:>+7.4f}  {dp:>+7.4f}  {dr:>+7.4f}  {db:>+10.1f}{flag}')
        print()


if __name__ == '__main__':
    main()
