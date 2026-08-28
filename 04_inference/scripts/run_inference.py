"""run_inference.py — consolidated per-iteration inference driver (S4).

Replaces the ~13 near-duplicate repo-root `_run_inference_*.py` scripts,
which all did the same thing with different hardcoded constants: load a
trained nnUNet model, predict over a pre-split chunk directory, and
concatenate/trim the overlapped predictions back into one volume.

The originals are preserved for reference (unexecuted, pending a live
verification cycle) under 04_inference/scripts/legacy_per_iteration/.

Usage:
    python run_inference.py --iteration-name fresh_bnei_reem_i3 \
        --sample-id nlm_volume --trainer-name nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss \
        --reuse-split-from iter04
"""
import argparse
import gc
import os
import subprocess
import sys

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CONCATENATE_SCRIPT = os.path.join(REPO_DIR, '04_inference', 'postprocessing_nnUNet_predict_concatenate.py')
HIVE_BASE = r'\\hive3065\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources'


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--iteration-name', required=True)
    parser.add_argument('--sample-id', required=True)
    parser.add_argument('--trainer-name', default='nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss')
    parser.add_argument('--gpu', type=int)
    parser.add_argument('--dataset-id', default='777')
    parser.add_argument('--model-dir', help='Override; else derived from --iteration-name.')
    parser.add_argument('--input-dir', help='Pre-split chunks dir; else derived, or use --reuse-split-from.')
    parser.add_argument('--reuse-split-from', help='Reuse another iteration\'s inference_input dir (bnei_reem_<name>/inference_input).')
    parser.add_argument('--output-dir')
    parser.add_argument('--concat-dir')
    parser.add_argument('--checkpoint-name', default=None,
                         help='Default: try checkpoint_final.pth then checkpoint_best.pth.')
    args = parser.parse_args()

    if args.gpu is not None:
        os.environ['CUDA_VISIBLE_DEVICES'] = str(args.gpu)

    import torch
    _orig_torch_load = torch.load

    def _patched_load(f, *a, **kw):
        kw.setdefault('weights_only', False)
        return _orig_torch_load(f, *a, **kw)
    torch.load = _patched_load

    from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor

    model_dir = args.model_dir or os.path.join(
        HIVE_BASE, f'multi_sample_{args.iteration_name}', 'nnUNet_results', f'Dataset{args.dataset_id}_GCEF',
        f'{args.trainer_name}__nnUNetPlans__3d_fullres')

    if args.input_dir:
        split_dir = args.input_dir
    elif args.reuse_split_from:
        split_dir = os.path.join(HIVE_BASE, f'bnei_reem_{args.reuse_split_from}', 'inference_input')
    else:
        split_dir = os.path.join(HIVE_BASE, f'bnei_reem_{args.iteration_name}', 'inference_input')

    sample_base = os.path.join(HIVE_BASE, f'bnei_reem_{args.iteration_name}')
    pred_dir = args.output_dir or os.path.join(sample_base, 'inference_output')
    concat_dir = args.concat_dir or os.path.join(sample_base, 'inference_concatenated')
    os.makedirs(pred_dir, exist_ok=True)
    os.makedirs(concat_dir, exist_ok=True)

    assert os.path.isdir(model_dir), f'Model dir not found: {model_dir}'
    assert os.path.isdir(split_dir), (
        f'Inference input dir not found: {split_dir}. '
        'Re-run 02_preprocessing/nnunet/preprocessing_nnUNet_predict_split.py first.')

    chunks = sorted(f for f in os.listdir(split_dir) if f.endswith('_0000.nii.gz'))
    if not chunks:
        raise FileNotFoundError(f'No input chunks in {split_dir}')
    print(f'Input chunks ({len(chunks)}):')
    for c in chunks:
        print(f'  {c}')

    fold_dir = os.path.join(model_dir, 'fold_0')
    if args.checkpoint_name:
        checkpoint_name = args.checkpoint_name
        assert os.path.isfile(os.path.join(fold_dir, checkpoint_name)), f'Checkpoint not found: {checkpoint_name}'
    else:
        for candidate in ('checkpoint_final.pth', 'checkpoint_best.pth'):
            if os.path.isfile(os.path.join(fold_dir, candidate)):
                checkpoint_name = candidate
                break
        else:
            raise FileNotFoundError(f'No checkpoint found in {fold_dir}')
    print(f'Checkpoint: {checkpoint_name}')
    print(f'CUDA available: {torch.cuda.is_available()}')

    print('\n=== Step 1: Inference ===')
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    gc.collect()

    predictor = nnUNetPredictor(
        tile_step_size=0.5, use_gaussian=True, use_mirroring=False,
        perform_everything_on_device=False,
        device=torch.device('cuda' if torch.cuda.is_available() else 'cpu'),
        verbose=True, allow_tqdm=True,
    )
    predictor.initialize_from_trained_model_folder(model_dir, use_folds=(0,), checkpoint_name=checkpoint_name)
    predictor.predict_from_files(
        split_dir, pred_dir, save_probabilities=False, overwrite=True,
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
        [sys.executable, CONCATENATE_SCRIPT, '-i', pred_dir, '-o', concat_dir],
        capture_output=True, text=True,
    )
    print(res.stdout)
    if res.returncode != 0:
        print('STDERR:', res.stderr)
        raise RuntimeError(f'Concatenation failed (exit {res.returncode})')

    concat_path = os.path.join(concat_dir, f'{args.sample_id}.nii.gz')
    if not os.path.isfile(concat_path):
        raise FileNotFoundError(f'Missing: {concat_path}')

    size_mb = os.path.getsize(concat_path) / 1e6
    print(f'\n{"="*70}')
    print(f'DONE - {args.iteration_name} prediction:')
    print(f'  {concat_path}  ({size_mb:.1f} MB)')
    print(f'{"="*70}')


if __name__ == '__main__':
    main()
