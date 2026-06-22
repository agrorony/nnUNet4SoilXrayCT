"""
Standalone inference script for nlm_volume using the multi_sample_iter02 model.
Existing inference_input chunks (iter01 split, same plans) are reused directly.

Run from PowerShell:
  & venv-napari python.exe _run_inference_nlm_iter02.py
"""
import gc
import os
import shutil

import torch

HIVE = r'\\hive3065\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources'
TRAINER = 'nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss'
MODEL_DIR = os.path.join(
    HIVE, 'multi_sample_iter02', 'nnUNet_results', 'Dataset777_GCEF',
    f'{TRAINER}__nnUNetPlans__3d_fullres'
)
NLM_BASE   = os.path.join(HIVE, 'bnei_reem')
INPUT_DIR  = os.path.join(NLM_BASE, 'inference_input')
OUTPUT_DIR = os.path.join(NLM_BASE, 'inference_output_iter02')

os.environ['nnUNet_compile']      = 'false'
os.environ['nnUNet_raw']          = os.path.join(HIVE, 'multi_sample_iter02', 'nnUNet_raw')
os.environ['nnUNet_preprocessed'] = os.path.join(HIVE, 'multi_sample_iter02', 'nnUNet_preprocessed')
os.environ['nnUNet_results']      = os.path.join(HIVE, 'multi_sample_iter02', 'nnUNet_results')

# Register custom trainer
import nnunetv2
trainers_dir = os.path.join(
    os.path.dirname(nnunetv2.__file__),
    'training', 'nnUNetTrainer', 'variants', 'sampling'
)
os.makedirs(trainers_dir, exist_ok=True)
shutil.copy2(
    r'C:\Users\rony.schwartz\Documents\nnUNet4SoilXrayCT\nnUNetTrainer_betterIgnoreSampling.py',
    os.path.join(trainers_dir, 'nnUNetTrainer_betterIgnoreSampling.py')
)

# PyTorch 2.6 compatibility
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
    assert os.path.isdir(INPUT_DIR),  f'Input dir not found: {INPUT_DIR}'

    n_chunks = len([f for f in os.listdir(INPUT_DIR) if f.endswith('_0000.nii.gz')])
    print(f'Chunks:      {n_chunks}')
    assert n_chunks > 0, 'No input chunks found'

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    fold_dir = os.path.join(MODEL_DIR, 'fold_0')
    for ckpt in ('checkpoint_final.pth', 'checkpoint_best.pth', 'checkpoint_latest.pth'):
        if os.path.isfile(os.path.join(fold_dir, ckpt)):
            checkpoint_name = ckpt
            break
    else:
        raise FileNotFoundError(f'No checkpoint in {fold_dir}')
    print(f'Checkpoint:  {checkpoint_name}')

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
