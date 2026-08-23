"""
Standalone inference script for mishmar_hanegev_maoz_2_8p8um
using the mishmar_hanegev_maoz_3_5p85um_loess_i2 model (renamed from scratch_i2).

Run from PowerShell:
  conda activate venv-napari
  python _run_inference_maoz_2_8p8um_loess_i2.py

This avoids the Jupyter kernel crash caused by nnUNet's multiprocessing
workers trying to import __main__ inside a notebook kernel on Windows.
"""
import gc
import os
import subprocess
import sys

import torch

HIVE = r'\\hive3065\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources'
TRAINER = 'nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss'
MODEL_DIR = os.path.join(
    HIVE, 'multi_sample_mishmar_hanegev_maoz_3_5p85um_loess_i2', 'nnUNet_results', 'Dataset777_GCEF',
    f'{TRAINER}__nnUNetPlans__3d_fullres'
)
SID = 'mishmar_hanegev_maoz_2_8p8um'
SAMPLE_BASE = os.path.join(HIVE, SID)
INPUT_DIR = os.path.join(SAMPLE_BASE, 'inference_input')
OUTPUT_DIR = os.path.join(SAMPLE_BASE, 'inference_output_loess_i2')
CONCAT_DIR = os.path.join(SAMPLE_BASE, 'inference_output_concat_loess_i2')

REPO_DIR = r'C:\Users\rony.schwartz\Documents\nnUNet4SoilXrayCT'
CONCATENATE_SCRIPT = os.path.join(REPO_DIR, '04_inference', 'postprocessing_nnUNet_predict_concatenate.py')

os.environ['nnUNet_compile'] = 'false'
os.environ['nnUNet_raw'] = os.path.join(HIVE, 'multi_sample_mishmar_hanegev_maoz_3_5p85um_loess_i2', 'nnUNet_raw')
os.environ['nnUNet_preprocessed'] = os.path.join(HIVE, 'multi_sample_mishmar_hanegev_maoz_3_5p85um_loess_i2', 'nnUNet_preprocessed')
os.environ['nnUNet_results'] = os.path.join(HIVE, 'multi_sample_mishmar_hanegev_maoz_3_5p85um_loess_i2', 'nnUNet_results')

# PyTorch 2.6 checkpoint compatibility
_orig_load = torch.load
def _patched_load(f, *args, **kwargs):
    kwargs.setdefault('weights_only', False)
    return _orig_load(f, *args, **kwargs)
torch.load = _patched_load

from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor

if __name__ == '__main__':
    print(f'Model dir:   {MODEL_DIR}')
    print(f'Input dir:   {INPUT_DIR}')
    print(f'Output dir:  {OUTPUT_DIR}')
    print(f'CUDA:        {torch.cuda.is_available()}')

    assert os.path.isdir(MODEL_DIR), f'Model dir not found: {MODEL_DIR}'
    assert os.path.isdir(INPUT_DIR), f'Input dir not found: {INPUT_DIR}'

    n_chunks = len([f for f in os.listdir(INPUT_DIR) if f.endswith('_0000.nii.gz')])
    print(f'Chunks:      {n_chunks}')
    assert n_chunks > 0, 'No input chunks found'

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(CONCAT_DIR, exist_ok=True)

    fold_dir = os.path.join(MODEL_DIR, 'fold_0')
    for ckpt in ('checkpoint_final.pth', 'checkpoint_best.pth', 'checkpoint_latest.pth'):
        if os.path.isfile(os.path.join(fold_dir, ckpt)):
            checkpoint_name = ckpt
            break
    else:
        raise FileNotFoundError(f'No checkpoint in {fold_dir}')
    print(f'Checkpoint:  {checkpoint_name}')

    print('\n=== Step 1: Inference ===')
    predictor = nnUNetPredictor(
        tile_step_size=0.5,
        use_gaussian=True,
        use_mirroring=False,
        perform_everything_on_device=False,
        device=torch.device('cuda' if torch.cuda.is_available() else 'cpu'),
        verbose=True,
        allow_tqdm=True,
    )
    predictor.initialize_from_trained_model_folder(
        MODEL_DIR, use_folds=(0,), checkpoint_name=checkpoint_name
    )
    predictor.predict_from_files(
        INPUT_DIR,
        OUTPUT_DIR,
        save_probabilities=False,
        overwrite=True,
        num_processes_preprocessing=1,
        num_processes_segmentation_export=1,
        folder_with_segs_from_prev_stage=None,
        num_parts=1,
        part_id=0,
    )

    del predictor
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    pred_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('_.nii.gz')]
    print(f'\nDone. {len(pred_files)} prediction files in {OUTPUT_DIR}')
    for f in sorted(pred_files):
        print(f'  {f}')

    print('\n=== Step 2: Concatenation ===')
    res = subprocess.run(
        [sys.executable, CONCATENATE_SCRIPT, '-i', OUTPUT_DIR, '-o', CONCAT_DIR],
        capture_output=True, text=True,
    )
    print(res.stdout)
    if res.returncode != 0:
        print('STDERR:', res.stderr)
        raise RuntimeError(f'Concatenation failed (exit {res.returncode})')

    concat_path = os.path.join(CONCAT_DIR, f'{SID}.nii.gz')
    if not os.path.isfile(concat_path):
        raise FileNotFoundError(f'Missing: {concat_path}')

    size_mb = os.path.getsize(concat_path) / 1e6
    print(f'\n{"="*70}')
    print(f'DONE - {SID} prediction with loess_i2 model:')
    print(f'  {concat_path}  ({size_mb:.1f} MB)')
    print(f'{"="*70}')
