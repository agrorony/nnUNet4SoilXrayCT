"""
Launch micro-SAM napari session for mishmar_hanegev volume with GT + 2 prediction layers.

Layers:
  volume      — mishmar_hanegev_Cu011_samp_2_Rec_nlm.tif
  gt          — mishmar_hanegev_new_work/annotations/mishmar_hanegev_Cu011_samp_2_Rec_nlm.nii.gz
  pred_new    — mishmar_hanegev_new_work/mishmar_hanegev_Cu011_samp_2_Rec_nlm.nii.gz
  pred_iter02 — inference_output_concat_iter02/mishmar_hanegev_Cu011_samp_2_Rec_nlm.nii.gz
"""
import sys
import os

MICROSAM_DIR = r'C:\Users\rony.schwartz\Documents\nnUNet4SoilXrayCT\microsam_3d'
sys.path.insert(0, MICROSAM_DIR)
os.chdir(MICROSAM_DIR)

HIVE_ROOT = r'\\hive3065\Yael_Mishael\Rony\remote_computer backup'
HIVE_NN   = os.path.join(HIVE_ROOT, 'nnUNet_resources')

VOL       = os.path.join(HIVE_ROOT, '10.5', 'mishmar_hanegev_Cu011_samp_2_Rec_nlm.tif')
GT        = os.path.join(HIVE_NN, 'mishmar_hanegev_new_work', 'annotations',
                         'mishmar_hanegev_Cu011_samp_2_Rec_nlm.nii.gz')
PRED_NEW  = os.path.join(HIVE_NN, 'mishmar_hanegev_new_work',
                         'mishmar_hanegev_Cu011_samp_2_Rec_nlm.nii.gz')
PRED_IT02 = os.path.join(HIVE_NN, 'mishmar_hanegev_Cu011_samp_2_Rec_nlm',
                         'inference_output_concat_iter02',
                         'mishmar_hanegev_Cu011_samp_2_Rec_nlm.nii.gz')

for p, name in [
    (VOL,       'volume'),
    (GT,        'GT'),
    (PRED_NEW,  'pred_new'),
    (PRED_IT02, 'pred_iter02'),
]:
    if not os.path.isfile(p):
        raise FileNotFoundError(f'Missing {name}: {p}')
    print(f'[OK] {name}: {p}')

from run import main

main(
    volume_path=VOL,
    pred_path=PRED_NEW,
    gt_path=GT,
    extra_label_paths={'pred_iter02': PRED_IT02},
    debug=True,
)
