"""
Standalone inference for iter04_continue model on nlm_volume (Beni Ram).

Reuses pre-split chunks from bnei_reem_iter04/inference_input (identical plans).
Outputs predictions to bnei_reem_iter04_continue/inference_output/.
Concatenates to bnei_reem_iter04_continue/inference_concatenated/nlm_volume.nii.gz.

Must run as __main__ on Windows: nnUNetPredictor spawns multiprocessing workers
via the 'spawn' method; without this guard, every worker re-enters the script.
"""
import os
import gc
import sys
import subprocess
import torch

_orig_torch_load = torch.load
def _patched_load(f, *args, **kwargs):
    kwargs.setdefault('weights_only', False)
    return _orig_torch_load(f, *args, **kwargs)
torch.load = _patched_load


if __name__ == '__main__':
    from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor

    REPO_DIR     = r'C:\Users\rony.schwartz\Documents\nnUNet4SoilXrayCT'
    HIVE_BASE    = r'\\hive3065\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources'
    TRAINER_NAME = 'nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss'
    SAMPLE_ID    = 'nlm_volume'

    # iter04_continue model
    MODEL_DIR = os.path.join(
        HIVE_BASE, 'multi_sample_iter04_continue', 'nnUNet_results', 'Dataset777_GCEF',
        f'{TRAINER_NAME}__nnUNetPlans__3d_fullres'
    )

    # Reuse iter04 pre-split input chunks (identical 3d_fullres plan)
    SPLIT_DIR  = os.path.join(HIVE_BASE, 'bnei_reem_iter04', 'inference_input')

    SAMPLE_BASE = os.path.join(HIVE_BASE, 'bnei_reem_iter04_continue')
    PRED_DIR    = os.path.join(SAMPLE_BASE, 'inference_output')
    CONCAT_DIR  = os.path.join(SAMPLE_BASE, 'inference_concatenated')

    os.makedirs(PRED_DIR,   exist_ok=True)
    os.makedirs(CONCAT_DIR, exist_ok=True)

    assert os.path.isdir(MODEL_DIR), f'Model dir not found: {MODEL_DIR}'
    assert os.path.isdir(SPLIT_DIR), f'Inference input dir not found: {SPLIT_DIR}'

    chunks = sorted(f for f in os.listdir(SPLIT_DIR) if f.endswith('_0000.nii.gz'))
    if not chunks:
        raise FileNotFoundError(
            f'No input chunks found in {SPLIT_DIR}. '
            'Re-run preprocessing_nnUNet_predict_split.py for bnei_reem_iter04 first.'
        )
    print(f'Input chunks ({len(chunks)}):')
    for c in chunks:
        print(f'  {c}')

    fold_dir = os.path.join(MODEL_DIR, 'fold_0')
    for candidate in ('checkpoint_final.pth', 'checkpoint_best.pth'):
        if os.path.isfile(os.path.join(fold_dir, candidate)):
            checkpoint_name = candidate
            break
    else:
        raise FileNotFoundError(f'No checkpoint found in {fold_dir}')
    print(f'Checkpoint: {checkpoint_name}')
    print(f'CUDA available: {torch.cuda.is_available()}')
    if torch.cuda.is_available():
        print(f'CUDA device: {torch.cuda.get_device_name(0)}')

    print('\n=== Step 1: Inference ===')
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    gc.collect()

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
        SPLIT_DIR, PRED_DIR,
        save_probabilities=False, overwrite=True,
        num_processes_preprocessing=1, num_processes_segmentation_export=1,
        folder_with_segs_from_prev_stage=None, num_parts=1, part_id=0,
    )
    del predictor
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    print('Inference complete.')

    print('\n=== Step 2: Concatenation ===')
    res = subprocess.run(
        [sys.executable,
         os.path.join(REPO_DIR, 'postprocessing_nnUNet_predict_concatenate.py'),
         '-i', PRED_DIR, '-o', CONCAT_DIR],
        capture_output=True, text=True
    )
    print(res.stdout)
    if res.returncode != 0:
        print('STDERR:', res.stderr)
        raise RuntimeError(f'Concatenation failed (exit {res.returncode})')

    concat_path = os.path.join(CONCAT_DIR, f'{SAMPLE_ID}.nii.gz')
    if not os.path.isfile(concat_path):
        raise FileNotFoundError(f'Expected concatenated file missing: {concat_path}')

    size_mb = os.path.getsize(concat_path) / 1e6
    print(f'\n{"="*70}')
    print(f'DONE - iter04_continue final prediction:')
    print(f'  {concat_path}  ({size_mb:.1f} MB)')
    print(f'{"="*70}')
