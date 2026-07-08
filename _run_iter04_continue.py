import sys

if __name__ != '__main__':
    sys.exit(0)

import os
import subprocess

os.environ['CUDA_VISIBLE_DEVICES'] = '0'

REPO_DIR  = r'C:\Users\rony.schwartz\Documents\nnUNet4SoilXrayCT'
HIVE_BASE = r'\\hive3065\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources'
HIVE_ROOT = r'\\hive3065\Yael_Mishael\Rony\remote_computer backup'

RAW_TIF    = os.path.join(HIVE_ROOT, '10.5', 'nlm_volume.tif')
PRED_NII   = os.path.join(HIVE_BASE, 'bnei_reem_iter04_continue',
                           'inference_concatenated', 'nlm_volume.nii.gz')
GT_NII     = os.path.join(HIVE_ROOT, 'microSAM_inputs', 'merged_GT.nii.gz')
MICROSAM_DIR = os.path.join(REPO_DIR, 'microsam_3d')

INF_SCRIPT = os.path.join(REPO_DIR, '_run_inference_iter04_continue.py')
assert os.path.isfile(INF_SCRIPT), f'Inference script not found: {INF_SCRIPT}'
assert os.path.isfile(RAW_TIF),    f'Raw TIF not found: {RAW_TIF}'
assert os.path.isfile(GT_NII),     f'GT not found: {GT_NII}'

# ── Step 1: Inference ──────────────────────────────────────────────────────────
print('=' * 70)
print('Step 1: Running inference with iter04_continue model ...')
print('=' * 70)

inf_proc = subprocess.Popen(
    [sys.executable, INF_SCRIPT],
    env=os.environ,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
)
for line in inf_proc.stdout:
    print(line, end='', flush=True)
inf_proc.wait()
if inf_proc.returncode != 0:
    raise RuntimeError(f'_run_inference_iter04_continue.py failed (exit {inf_proc.returncode})')

assert os.path.isfile(PRED_NII), f'Prediction not found after inference: {PRED_NII}'
print(f'\n[OK] Prediction ready: {PRED_NII}')

# ── Step 2: Launch microsam napari on slices 50-70 ────────────────────────────
print('=' * 70)
print('Step 2: Launching microsam napari plugin (slices 50-70) ...')
print(f'  volume:     {RAW_TIF}')
print(f'  prediction: {PRED_NII}')
print(f'  GT:         {GT_NII}')
print('=' * 70)

subprocess.run(
    [sys.executable, 'run.py',
     RAW_TIF, PRED_NII, GT_NII,
     '--zrange', '50', '70',
     '--debug'],
    cwd=MICROSAM_DIR,
    env=os.environ,
    check=True,
)
