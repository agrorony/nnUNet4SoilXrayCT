"""Inference for fresh_bnei_reem_i4 on nlm_volume."""
import os, gc, sys, subprocess
import torch

_orig = torch.load
def _patched(f, *a, **kw):
    kw.setdefault('weights_only', False)
    return _orig(f, *a, **kw)
torch.load = _patched

if __name__ == '__main__':
    from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor

    REPO_DIR     = r'C:\Users\rony.schwartz\Documents\nnUNet4SoilXrayCT'
    HIVE_BASE    = r'\\hive3065\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources'
    TRAINER_NAME = 'nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss_lowlr'

    MODEL_DIR  = os.path.join(HIVE_BASE, 'multi_sample_fresh_bnei_reem_i4',
                              'nnUNet_results', 'Dataset777_GCEF',
                              f'{TRAINER_NAME}__nnUNetPlans__3d_fullres')
    SPLIT_DIR  = os.path.join(HIVE_BASE, 'bnei_reem_iter04', 'inference_input')
    PRED_DIR   = os.path.join(HIVE_BASE, 'bnei_reem_fresh_bnei_reem_i4', 'inference_output')
    CONCAT_DIR = os.path.join(HIVE_BASE, 'bnei_reem_fresh_bnei_reem_i4', 'inference_concatenated')
    os.makedirs(PRED_DIR,   exist_ok=True)
    os.makedirs(CONCAT_DIR, exist_ok=True)

    assert os.path.isdir(MODEL_DIR),  f'Model dir not found: {MODEL_DIR}'
    assert os.path.isdir(SPLIT_DIR),  f'Split dir not found: {SPLIT_DIR}'

    fold_dir = os.path.join(MODEL_DIR, 'fold_0')
    ckpt = 'checkpoint_final.pth' if os.path.isfile(os.path.join(fold_dir, 'checkpoint_final.pth')) else 'checkpoint_best.pth'
    print(f'Checkpoint: {ckpt}')
    print(f'CUDA: {torch.cuda.is_available()}')

    if torch.cuda.is_available(): torch.cuda.empty_cache()
    gc.collect()

    predictor = nnUNetPredictor(
        tile_step_size=0.5, use_gaussian=True, use_mirroring=False,
        perform_everything_on_device=False,
        device=torch.device('cuda' if torch.cuda.is_available() else 'cpu'),
        verbose=True, allow_tqdm=True,
    )
    predictor.initialize_from_trained_model_folder(MODEL_DIR, use_folds=(0,), checkpoint_name=ckpt)
    predictor.predict_from_files(
        SPLIT_DIR, PRED_DIR,
        save_probabilities=False, overwrite=True,
        num_processes_preprocessing=1, num_processes_segmentation_export=1,
        folder_with_segs_from_prev_stage=None, num_parts=1, part_id=0,
    )
    del predictor; gc.collect()
    if torch.cuda.is_available(): torch.cuda.empty_cache()

    res = subprocess.run(
        [sys.executable, os.path.join(REPO_DIR, 'postprocessing_nnUNet_predict_concatenate.py'),
         '-i', PRED_DIR, '-o', CONCAT_DIR],
        capture_output=True, text=True
    )
    print(res.stdout)
    if res.returncode != 0:
        print('STDERR:', res.stderr)
        raise RuntimeError(f'Concatenation failed (exit {res.returncode})')

    out = os.path.join(CONCAT_DIR, 'nlm_volume.nii.gz')
    print(f'DONE: {out}  ({os.path.getsize(out)/1e6:.1f} MB)')
