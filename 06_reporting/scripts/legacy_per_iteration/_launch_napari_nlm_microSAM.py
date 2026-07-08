"""
Launch micro-SAM napari session for nlm_volume with GT + two predictions.

Layers:
  volume        — nlm_volume.tif
  gt            — merged_GT.nii.gz
  pred_continue — bnei_reem_iter04_continue/inference_concatenated/nlm_volume.nii.gz
  pred_fresh    — bnei_reem_fresh_bnei_reem/inference_concatenated/nlm_volume.nii.gz
"""
import sys
import os

MICROSAM_DIR = r'C:\Users\rony.schwartz\Documents\nnUNet4SoilXrayCT\microsam_3d'
sys.path.insert(0, MICROSAM_DIR)
os.chdir(MICROSAM_DIR)

HIVE_ROOT = r'\\hive3065\Yael_Mishael\Rony\remote_computer backup'
HIVE_NN   = os.path.join(HIVE_ROOT, 'nnUNet_resources')

VOL           = os.path.join(HIVE_ROOT, '10.5', 'nlm_volume.tif')
GT            = os.path.join(HIVE_ROOT, 'microSAM_inputs', 'merged_GT.nii.gz')
PRED_CONTINUE = os.path.join(HIVE_NN, 'bnei_reem_iter04_continue',
                              'inference_concatenated', 'nlm_volume.nii.gz')
PRED_FRESH    = os.path.join(HIVE_NN, 'bnei_reem_fresh_bnei_reem',
                              'inference_concatenated', 'nlm_volume.nii.gz')

for p, name in [
    (VOL,           'volume'),
    (GT,            'GT'),
    (PRED_CONTINUE, 'pred_continue'),
    (PRED_FRESH,    'pred_fresh'),
]:
    if not os.path.isfile(p):
        raise FileNotFoundError(f'Missing {name}: {p}')
    print(f'[OK] {name}: {p}')

from run import main

main(
    volume_path=VOL,
    pred_path=PRED_CONTINUE,
    gt_path=GT,
    extra_label_paths={'pred_fresh': PRED_FRESH},
    debug=True,
)
