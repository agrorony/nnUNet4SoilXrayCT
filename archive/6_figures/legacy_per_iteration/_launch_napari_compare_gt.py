"""
Launch microsam with all current predictions as separate layers for comparison.

Layers:
  pred_scratch  — fresh_bnei_reem_i3_scratch  (from scratch, LR 1e-2, annotations_i3)
  pred_i4       — fresh_bnei_reem_i4          (fine-tune i3_lowlr, LR 2e-3, fine_tuning_annotations)
  pred_i3_lowlr — fresh_bnei_reem_i3_lowlr    (fine-tune i2, LR 2e-3, annotations_i3)
  gt            — annotations_i3.nii.gz
"""
import sys, os

MICROSAM_DIR = r'C:\Users\rony.schwartz\Documents\nnUNet4SoilXrayCT\microsam_3d'
sys.path.insert(0, MICROSAM_DIR)

HIVE_ROOT = r'\\hive3065\Yael_Mishael\Rony\remote_computer backup'
HIVE_BASE = os.path.join(HIVE_ROOT, 'nnUNet_resources')

vol           = os.path.join(HIVE_ROOT, '10.5', 'nlm_volume.tif')
pred_scratch  = os.path.join(HIVE_BASE, 'bnei_reem_fresh_bnei_reem_i3_scratch', 'inference_concatenated', 'nlm_volume.nii.gz')
pred_i4       = os.path.join(HIVE_BASE, 'bnei_reem_fresh_bnei_reem_i4',         'inference_concatenated', 'nlm_volume.nii.gz')
pred_i3_lowlr = os.path.join(HIVE_BASE, 'bnei_reem_fresh_bnei_reem_i3_lowlr',   'inference_concatenated', 'nlm_volume.nii.gz')
gt            = os.path.join(HIVE_BASE, 'fresh_train_annotations_bnei_reem', 'annotations_i3.nii.gz')

for name, path in [
    ('vol',           vol),
    ('pred_scratch',  pred_scratch),
    ('pred_i4',       pred_i4),
    ('pred_i3_lowlr', pred_i3_lowlr),
    ('gt',            gt),
]:
    if os.path.isfile(path):
        print(f'[OK] {name}: {path}')
    else:
        print(f'[MISSING] {name}: {path}')
        sys.exit(1)

from run import main
main(
    volume_path=vol,
    pred_path=pred_scratch,
    gt_path=gt,
    extra_label_paths={
        'pred_i4':       pred_i4,
        'pred_i3_lowlr': pred_i3_lowlr,
    },
    debug=True,
)
