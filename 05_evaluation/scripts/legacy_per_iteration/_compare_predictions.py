"""
Compare predictions against GT annotations (fresh_bnei_reem_i2).

GT annotation labels (user scheme, 1-indexed):
  1=soil matrix  2=stones  3=POM  6=pore
nnUNet shifts labels by -1 in predictions:
  0=matrix  1=stones  2=POM  5=pore

Models compared:
  OLD     — fresh_bnei_reem   (baseline)
  NEW     — fresh_bnei_reem_i2 (fine-tuned with i2 annotations)
  LOW_LR  — fresh_bnei_reem_i3_lowlr (fine-tuned with i3 annotations, low LR)
"""
import numpy as np
import nibabel as nib

HIVE_BASE = r'\\hive3065\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources'
GT_PATH    = rf'{HIVE_BASE}\fresh_train_annotations_bnei_reem\annotations_i2.nii.gz'
OLD_PATH   = rf'{HIVE_BASE}\bnei_reem_fresh_bnei_reem\inference_concatenated\nlm_volume.nii.gz'
NEW_PATH   = rf'{HIVE_BASE}\bnei_reem_fresh_bnei_reem_i2\inference_concatenated\nlm_volume.nii.gz'
LOWLR_PATH = rf'{HIVE_BASE}\bnei_reem_fresh_bnei_reem_i3_lowlr\inference_concatenated\nlm_volume.nii.gz'

GT_SLICES = [26,29,30,31,32,33,54,55,56,57,58,59,232,233,234,
             321,322,323,324,325,326,334,367,368,369,
             544,545,546,547,548,550,551]

# GT annotation labels (user's scheme, 1-indexed):
#   1=soil matrix  2=stones  3=POM  4=other POM  5=nan  6=pore
# nnUNet shifts all labels by -1 in predictions:
#   pred 0=matrix  pred 1=stones  pred 2=POM  pred 5=pore
# GT label 6 (pore) maps to pred label 5 — NOT an ignore label.
# GT label 1 (soil matrix) maps to pred label 0 (background) — excluded from Dice.
# Evaluation pairs: (gt_label, pred_label, name)
EVAL_PAIRS = [
    (2, 1, 'Stones'),
    (3, 2, 'POM'),
    (6, 5, 'Pore'),
]


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
    rec  = (tp / (tp + fn)) if (tp + fn) > 0 else float('nan')
    gt_v  = int(g.sum())
    pr_v  = int(p.sum())
    bias  = ((pr_v - gt_v) / gt_v * 100) if gt_v > 0 else float('nan')
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
        r_str = f'{rec:.4f}'  if not np.isnan(rec)  else '   N/A'
        b_str = f'{bias:+.1f}' if not np.isnan(bias) else '   N/A'
        print(f'{name:>8}  {d_str:>6}  {p_str:>6}  {r_str:>6}  {b_str:>9}  {gv:>10,}  {pv:>10,}')
        if not np.isnan(dice):
            dices.append(dice)
    if dices:
        print(f'  Mean Dice: {np.mean(dices):.4f}')


def main():
    print('Loading volumes...')
    gt    = load_vol(GT_PATH)
    old   = load_vol(OLD_PATH)
    new   = load_vol(NEW_PATH)
    lowlr = load_vol(LOWLR_PATH)

    print(f'\nRestricting to {len(GT_SLICES)} annotated z-slices...')
    gt_ann    = gt[:, :, GT_SLICES]
    old_ann   = old[:, :, GT_SLICES]
    new_ann   = new[:, :, GT_SLICES]
    lowlr_ann = lowlr[:, :, GT_SLICES]

    # GT=0 unannotated, GT=1 soil matrix (background) — both excluded
    annotated = gt_ann > 1
    print(f'Annotated voxels (GT > 1, excluding matrix and empty): {annotated.sum():,}')

    gt_v    = gt_ann[annotated]
    old_v   = old_ann[annotated]
    new_v   = new_ann[annotated]
    lowlr_v = lowlr_ann[annotated]

    print(f'\nGT label distribution in annotated voxels:')
    for gt_lbl, pred_lbl, name in EVAL_PAIRS:
        n = (gt_v == gt_lbl).sum()
        print(f'  GT label {gt_lbl} ({name}): {n:>10,}  -> pred label {pred_lbl}')

    models = [
        ('OLD      (fresh_bnei_reem)',           old_v),
        ('NEW      (fresh_bnei_reem_i2)',         new_v),
        ('LOW_LR   (fresh_bnei_reem_i3_lowlr)',   lowlr_v),
    ]

    all_rows = []
    for title, pred_v in models:
        rows = [(name,) + dice_metrics(gt_v, pred_v, gt_lbl, pred_lbl)
                for gt_lbl, pred_lbl, name in EVAL_PAIRS]
        all_rows.append(rows)
        print_table(title, rows)

    # Delta vs OLD
    rows_old = all_rows[0]
    print(f'\n{"="*80}')
    print('  Delta vs OLD  (positive = better than baseline)')
    print(f'{"="*80}')
    hdr = f'{"Model":>10}  {"Class":>8}  {"dDice":>7}  {"dPrec":>7}  {"dRecall":>7}  {"dVolBias%":>10}'
    print(hdr)
    print('-' * 80)
    for (model_label, _), rows in zip(models[1:], all_rows[1:]):
        short = model_label.split('(')[0].strip()
        for (name, d_n, p_n, r_n, b_n, *_), (_, d_o, p_o, r_o, b_o, *__) in zip(rows, rows_old):
            dd = d_n - d_o if not (np.isnan(d_n) or np.isnan(d_o)) else float('nan')
            dp = p_n - p_o if not (np.isnan(p_n) or np.isnan(p_o)) else float('nan')
            dr = r_n - r_o if not (np.isnan(r_n) or np.isnan(r_o)) else float('nan')
            db = b_n - b_o if not (np.isnan(b_n) or np.isnan(b_o)) else float('nan')
            flag = '  <<< WORSE' if not np.isnan(dd) and dd < -0.02 else ''
            print(f'{short:>10}  {name:>8}  {dd:>+7.4f}  {dp:>+7.4f}  {dr:>+7.4f}  {db:>+10.1f}{flag}')
        print()



if __name__ == '__main__':
    main()
