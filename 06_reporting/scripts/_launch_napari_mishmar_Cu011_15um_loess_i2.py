"""
Launch micro-SAM napari session for the Mishmar HaNegev 15um sample
(mishmar_hanegev_Cu011_samp_2_Rec_nlm) with its raw volume + the new
loess_i2 model prediction (run 2026-08-23, model-matched to mishmar_native
for the resolution-comparison POM analysis).

Layers:
  volume — mishmar_hanegev_Cu011_samp_2_Rec_nlm.tif (raw, 15.000149um)
  pred   — inference_output_concat_loess_i2/mishmar_hanegev_Cu011_samp_2_Rec_nlm.nii.gz
"""
import os
import sys

MICROSAM_DIR = r'C:\Users\rony.schwartz\Documents\nnUNet4SoilXrayCT\05_evaluation\microsam_3d'
sys.path.insert(0, MICROSAM_DIR)
os.chdir(MICROSAM_DIR)

HIVE_ROOT = r'\\hive3065\Yael_Mishael\Rony\remote_computer backup'
HIVE_NN = os.path.join(HIVE_ROOT, 'nnUNet_resources')

VOL = os.path.join(HIVE_ROOT, '10.5', 'mishmar_hanegev_Cu011_samp_2_Rec_nlm.tif')
PRED = os.path.join(
    HIVE_NN, 'mishmar_hanegev_Cu011_samp_2_Rec_nlm',
    'inference_output_concat_loess_i2', 'mishmar_hanegev_Cu011_samp_2_Rec_nlm.nii.gz'
)

for p, name in [(VOL, 'volume'), (PRED, 'pred')]:
    if not os.path.isfile(p):
        raise FileNotFoundError(f'Missing {name}: {p}')
    print(f'[OK] {name}: {p}')

from run import main

main(
    volume_path=VOL,
    pred_path=PRED,
    debug=True,
    title="Mishmar HaNegev 15um (Cu011_samp_2) -- loess_i2 prediction",
)
