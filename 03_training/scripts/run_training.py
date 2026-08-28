"""run_training.py — consolidated per-iteration training driver (S1).

Replaces the ~12 near-duplicate repo-root scripts (`_run_iter03.py`,
`_run_iter04.py`, `_run_fresh_bnei_reem_i2/i3/i3_lowlr/i3_scratch/i4.py`,
`_run_mishmar_hnegev_scratch/trained.py`, `train_fresh_bnei_reem.py`,
`train_iter4_continue_bnei_reem.py`), which all did the same 6 steps with
different hardcoded constants: register the custom trainer, prepare the
nnUNet dataset from a raw TIF + annotation NIfTI, plan+preprocess, write a
train=val=sample_id split, fine-tune (or train from scratch), parse the
training log into a metrics CSV + plot, and optionally chain into inference.

The originals are preserved for reference (unexecuted, pending a live
verification cycle) under
03_training/scripts/legacy_per_iteration/.

Usage (CLI args, or --config path.yaml with the same keys):
    python run_training.py --config ../run_configs/fresh_bnei_reem_i3.yaml
    python run_training.py --iteration-name fresh_bnei_reem_i3 \
        --sample-id nlm_volume --gpu 0 \
        --annotation-path "\\hive...\annotations_i3.nii.gz" \
        --base-checkpoint "\\hive...\multi_sample_fresh_bnei_reem_i2\...\checkpoint_final.pth" \
        --run-inference-after
"""
import argparse
import glob
import gc
import json
import os
import re
import shutil
import subprocess
import sys

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_REGISTRY_PATH = os.path.join(REPO_DIR, '01_data_ingestion', 'registry', 'data_registry.json')
DATASET_INFO_PATH = os.path.join(REPO_DIR, 'dataset_info.json')
TRAIN_WRAPPER = os.path.join(REPO_DIR, '03_training', 'scripts', 'train_wrapper.py')
TRAINER_SRC = os.path.join(REPO_DIR, '03_training', 'nnUNetTrainer_betterIgnoreSampling.py')
RUN_INFERENCE_SCRIPT = os.path.join(REPO_DIR, '04_inference', 'scripts', 'run_inference.py')


def load_config(args):
    """Merge a --config YAML (if given) with explicit CLI overrides."""
    cfg = {}
    if args.config:
        import yaml
        with open(args.config, 'r', encoding='utf-8') as f:
            cfg = yaml.safe_load(f) or {}
    for key, value in vars(args).items():
        if key == 'config':
            continue
        if value is not None:
            cfg[key] = value
    return cfg


def resolve_raw_tiff_path(sample_id, explicit_path):
    if explicit_path:
        return explicit_path
    with open(DATA_REGISTRY_PATH) as f:
        registry = json.load(f)
    matches = [s for s in registry['samples'] if s['sample_id'] == sample_id]
    if not matches:
        raise ValueError(f'{sample_id!r} not found in data_registry.json and --raw-tiff-path not given')
    return matches[0]['raw_tiff_path']


def register_trainer():
    import nnunetv2
    trainers_dir = os.path.join(os.path.dirname(nnunetv2.__file__), 'training', 'nnUNetTrainer', 'variants', 'sampling')
    os.makedirs(trainers_dir, exist_ok=True)
    dst = os.path.join(trainers_dir, os.path.basename(TRAINER_SRC))
    shutil.copy2(TRAINER_SRC, dst)
    print(f'Copied: {TRAINER_SRC} -> {dst}')
    modname = 'nnunetv2.training.nnUNetTrainer.variants.sampling.nnUNetTrainer_betterIgnoreSampling'
    if modname in sys.modules:
        del sys.modules[modname]


def mask_to_nnunet(mask_data, num_classes):
    import numpy as np
    m = mask_data.copy().astype('int16')
    m[m == 0] = num_classes
    m[m > num_classes] = num_classes
    m -= 1
    return m.astype('uint8')


def prepare_dataset(cfg, hive_base, local_base):
    import numpy as np
    import nibabel as nib
    import tifffile
    from nnunetv2.dataset_conversion.generate_dataset_json import generate_dataset_json

    nnUNet_raw = os.path.join(local_base, 'nnUNet_raw')
    nnUNet_preprocessed = os.path.join(local_base, 'nnUNet_preprocessed')
    nnUNet_results = os.path.join(local_base, 'nnUNet_results')
    for d in (nnUNet_raw, nnUNet_preprocessed, nnUNet_results):
        os.makedirs(d, exist_ok=True)
    os.environ['nnUNet_raw'] = nnUNet_raw
    os.environ['nnUNet_preprocessed'] = nnUNet_preprocessed
    os.environ['nnUNet_results'] = nnUNet_results
    os.environ['nnUNet_compile'] = 'false'

    dataset_id = cfg.get('dataset_id', '777')
    dataset_raw_dir = os.path.join(nnUNet_raw, f'Dataset{dataset_id}_GCEF')
    preprocessed_dataset_dir = os.path.join(nnUNet_preprocessed, f'Dataset{dataset_id}_GCEF')

    if cfg.get('force_rebuild', True):
        for d in (dataset_raw_dir, preprocessed_dataset_dir):
            if os.path.isdir(d):
                shutil.rmtree(d)
                print(f'Removed: {d}')

    images_dir = os.path.join(dataset_raw_dir, 'imagesTr')
    labels_dir = os.path.join(dataset_raw_dir, 'labelsTr')
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(labels_dir, exist_ok=True)

    with open(DATASET_INFO_PATH) as f:
        meta = json.load(f)
    classes = list(meta['labels'].values())
    del classes[0]  # drop 'ToPredict'
    num_classes = len(classes) + 1

    sample_id = cfg['sample_id']
    raw_tiff_path = cfg['raw_tiff_path']
    annotation_path = cfg['annotation_path']
    offset_layers = int(cfg.get('offset_layers', 48))

    print('Step 1: Loading raw image TIF...')
    img_arr = tifffile.imread(raw_tiff_path).transpose(2, 1, 0)  # (Z,Y,X) -> (X,Y,Z)

    print('Step 2: Loading annotation NIfTI...')
    ann_data = nib.load(annotation_path).get_fdata().astype('uint8')
    if ann_data.shape[:2] == img_arr.shape[:2]:
        pass
    elif ann_data.shape[1:] == img_arr.shape[:2]:
        ann_data = ann_data.transpose(2, 1, 0)
    elif ann_data.shape[0] == img_arr.shape[2] and ann_data.shape[1:] == img_arr.shape[:2][::-1]:
        ann_data = ann_data.transpose(1, 2, 0)
    else:
        print(f'  WARNING: unclear axis convention {ann_data.shape} vs image {img_arr.shape}. Proceeding as-is.')

    print('Step 3: Cropping to annotated z-range...')
    _, _, z_coords = np.where(ann_data != 0)
    if len(z_coords) == 0:
        raise ValueError('No annotated voxels found!')
    z_min = max(0, int(z_coords.min()) - offset_layers)
    z_max = min(int(z_coords.max()) + offset_layers + 1, ann_data.shape[2] - 1)
    img_crop = img_arr[:, :, z_min:z_max]
    ann_crop = ann_data[:, :, z_min:z_max]
    del img_arr, ann_data

    print('Step 4: Applying nnUNet label mapping...')
    ann_nnunet = mask_to_nnunet(ann_crop, num_classes)
    del ann_crop

    print('Step 5: Saving nnUNet dataset...')
    affine = np.eye(4)
    img_out = os.path.join(images_dir, f'{sample_id}_0000.nii.gz')
    nib.save(nib.Nifti1Image(img_crop, affine), img_out)
    del img_crop
    lbl_nii = nib.Nifti1Image(ann_nnunet, affine)
    lbl_nii.header.set_data_dtype(np.uint8)
    lbl_out = os.path.join(labels_dir, f'{sample_id}.nii.gz')
    nib.save(lbl_nii, lbl_out)
    del ann_nnunet

    print('Step 6: Generating dataset.json...')
    classes[0] = 'background'
    classes.append('ignore')
    labels_dict = {name: i for i, name in enumerate(classes)}
    generate_dataset_json(
        output_folder=dataset_raw_dir, channel_names={0: 'noNorm'}, labels=labels_dict,
        num_training_cases=1, file_ending='.nii.gz', dataset_name=meta['DatasetName'],
    )

    images = sorted(glob.glob(os.path.join(dataset_raw_dir, 'imagesTr', '*_0000.nii.gz')))
    labels = sorted(glob.glob(os.path.join(dataset_raw_dir, 'labelsTr', '*.nii.gz')))
    assert len(images) == 1 and len(labels) == 1, 'Expected exactly 1 image+label pair'
    print('[OK] Dataset ready.')
    return nnUNet_raw, nnUNet_preprocessed, nnUNet_results, dataset_id


def plan_and_preprocess(dataset_id):
    result = subprocess.run(
        [sys.executable, '-m', 'nnunetv2.experiment_planning.plan_and_preprocess_entrypoints',
         '-d', dataset_id, '--verify_dataset_integrity'],
        env=os.environ, timeout=3600,
    )
    if result.returncode != 0:
        raise RuntimeError(f'plan_and_preprocess failed (exit {result.returncode})')


def write_split(nnUNet_preprocessed, dataset_id, sample_id):
    preprocessed_dir = os.path.join(nnUNet_preprocessed, f'Dataset{dataset_id}_GCEF')
    splits = [{'train': [sample_id], 'val': [sample_id]}]
    splits_path = os.path.join(preprocessed_dir, 'splits_final.json')
    with open(splits_path, 'w') as f:
        json.dump(splits, f, indent=2)
    print(f'Wrote {splits_path}')


def resolve_checkpoint(base_checkpoint, hive_base, trainer_name, dataset_id):
    if base_checkpoint in (None, '', 'scratch'):
        return None
    if os.path.isfile(base_checkpoint):
        return base_checkpoint
    # Treat as an iteration name and resolve the conventional checkpoint path.
    base_dir = os.path.join(hive_base, f'multi_sample_{base_checkpoint}', 'nnUNet_results', f'Dataset{dataset_id}_GCEF',
                             f'{trainer_name}__nnUNetPlans__3d_fullres', 'fold_0')
    for candidate in ('checkpoint_final.pth', 'checkpoint_best.pth'):
        p = os.path.join(base_dir, candidate)
        if os.path.isfile(p):
            return p
    raise FileNotFoundError(f'Could not resolve base checkpoint for {base_checkpoint!r} under {base_dir}')


def run_training_subprocess(dataset_id, trainer_name, pretrained_checkpoint, patience, min_delta):
    os.environ['NNUNET_EARLY_STOP_ENABLED'] = '1'
    os.environ['NNUNET_EARLY_STOP_PATIENCE'] = str(patience)
    os.environ['NNUNET_EARLY_STOP_MIN_DELTA'] = str(min_delta)
    cmd = [sys.executable, TRAIN_WRAPPER, dataset_id, '3d_fullres', '0', '-tr', trainer_name]
    if pretrained_checkpoint:
        cmd += ['-pretrained_weights', pretrained_checkpoint]
    proc = subprocess.Popen(cmd, env=os.environ, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    for line in proc.stdout:
        print(line, end='', flush=True)
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f'Training failed (exit {proc.returncode})')


def build_analytics(nnUNet_results, dataset_id, trainer_name, iteration_name):
    import pandas as pd
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    results_dir = os.path.join(nnUNet_results, f'Dataset{dataset_id}_GCEF', f'{trainer_name}__nnUNetPlans__3d_fullres')
    log_files = sorted(p for p in glob.glob(os.path.join(results_dir, 'fold_*', '*.txt'))
                        if 'training_log' in os.path.basename(p).lower())
    if not log_files:
        raise FileNotFoundError(f'No training_log*.txt found under {results_dir}')

    epoch_re = re.compile(r'Epoch\s+(\d+)')
    train_re = re.compile(r'train_loss\s+(-?[\d.eE]+)')
    val_re = re.compile(r'val_loss\s+(-?[\d.eE]+)')
    dice_re = re.compile(r'(?:EMA\s+pseudo\s+Dice|pseudo\s+Dice|mean\s+foreground\s+Dice)[^\d-]*(-?[\d.eE]+)', re.IGNORECASE)

    all_rows = []
    for lf in log_files:
        fold_name = os.path.basename(os.path.dirname(lf))
        epoch_data = {}
        current_epoch = None
        with open(lf, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                m = epoch_re.search(line)
                if m:
                    current_epoch = int(m.group(1))
                    epoch_data.setdefault(current_epoch, {'epoch': current_epoch, 'fold': fold_name})
                if current_epoch is None:
                    continue
                m = train_re.search(line)
                if m:
                    epoch_data[current_epoch]['train_loss'] = float(m.group(1))
                m = val_re.search(line)
                if m:
                    epoch_data[current_epoch]['val_loss'] = float(m.group(1))
                m = dice_re.search(line)
                if m:
                    epoch_data[current_epoch]['mean_dice'] = float(m.group(1))
        all_rows.extend(epoch_data.values())

    df = pd.DataFrame(all_rows).sort_values(['epoch', 'fold'])
    if df.empty:
        raise RuntimeError('Parsed zero epochs from training logs.')
    summary = df.groupby('epoch', as_index=False).agg({'train_loss': 'mean', 'val_loss': 'mean', 'mean_dice': 'mean'})

    analytics_dir = os.path.join(results_dir, 'analytics')
    os.makedirs(analytics_dir, exist_ok=True)
    summary.to_csv(os.path.join(analytics_dir, 'training_metrics_summary.csv'), index=False)

    fig, ax1 = plt.subplots(figsize=(12, 6))
    x = summary['epoch']
    ax1.plot(x, summary['train_loss'], label='Train Loss', color='tab:blue', lw=2.5)
    ax1.plot(x, summary['val_loss'], label='Val Loss', color='tab:orange', lw=2.5)
    ax1.set_xlabel('Epoch'); ax1.set_ylabel('Loss'); ax1.grid(True, alpha=0.3)
    ax2 = ax1.twinx()
    if summary['mean_dice'].notna().any():
        ax2.plot(x, summary['mean_dice'], label='Mean Dice', color='tab:green', lw=2.5)
        ax2.set_ylabel('Mean Dice'); ax2.set_ylim(0, 1)
    l1, la1 = ax1.get_legend_handles_labels()
    l2, la2 = ax2.get_legend_handles_labels()
    ax1.legend(l1 + l2, la1 + la2, loc='best')
    plt.title(f'Training Metrics — {iteration_name}', fontsize=14, fontweight='bold')
    plt.tight_layout()
    for ext in ('png', 'pdf'):
        plt.savefig(os.path.join(analytics_dir, f'training_metrics_combined.{ext}'), dpi=150, bbox_inches='tight')
    plt.close()
    print(f'[OK] Analytics saved to {analytics_dir}')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--config', help='YAML config with the same keys as the CLI args below.')
    parser.add_argument('--iteration-name')
    parser.add_argument('--sample-id')
    parser.add_argument('--raw-tiff-path')
    parser.add_argument('--annotation-path')
    parser.add_argument('--trainer-name', default=None)
    parser.add_argument('--base-checkpoint', help='Absolute path, an iteration name, or literal "scratch".')
    parser.add_argument('--gpu', type=int)
    parser.add_argument('--dataset-id', default=None)
    parser.add_argument('--force-rebuild', action='store_true', default=None)
    parser.add_argument('--offset-layers', type=int)
    parser.add_argument('--early-stop-patience', type=int)
    parser.add_argument('--early-stop-min-delta', type=float)
    parser.add_argument('--run-inference-after', action='store_true', default=None)
    args = parser.parse_args()

    cfg = load_config(args)
    cfg.setdefault('trainer_name', 'nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss')
    cfg.setdefault('dataset_id', '777')
    cfg.setdefault('force_rebuild', True)
    cfg.setdefault('offset_layers', 48)
    cfg.setdefault('early_stop_patience', 20)
    cfg.setdefault('early_stop_min_delta', 0.001)

    if 'gpu' in cfg:
        os.environ['CUDA_VISIBLE_DEVICES'] = str(cfg['gpu'])

    hive_base = r'\\hive3065\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources'
    cfg['raw_tiff_path'] = resolve_raw_tiff_path(cfg['sample_id'], cfg.get('raw_tiff_path'))
    local_base = os.path.join(hive_base, f"multi_sample_{cfg['iteration_name']}")

    print(f"Iteration:    {cfg['iteration_name']}")
    print(f"Sample:       {cfg['sample_id']}")
    print(f"Raw TIF:      {cfg['raw_tiff_path']}")
    print(f"Annotation:   {cfg['annotation_path']}")
    print(f"Trainer:      {cfg['trainer_name']}")
    print(f"Base ckpt:    {cfg.get('base_checkpoint', 'scratch')}")

    register_trainer()
    nnUNet_raw, nnUNet_preprocessed, nnUNet_results, dataset_id = prepare_dataset(cfg, hive_base, local_base)
    plan_and_preprocess(dataset_id)
    write_split(nnUNet_preprocessed, dataset_id, cfg['sample_id'])

    pretrained_checkpoint = resolve_checkpoint(cfg.get('base_checkpoint'), hive_base, cfg['trainer_name'], dataset_id)
    run_training_subprocess(dataset_id, cfg['trainer_name'], pretrained_checkpoint,
                             cfg['early_stop_patience'], cfg['early_stop_min_delta'])
    build_analytics(nnUNet_results, dataset_id, cfg['trainer_name'], cfg['iteration_name'])

    if cfg.get('run_inference_after'):
        print('\n' + '=' * 70)
        print(f"Running inference for {cfg['iteration_name']} ...")
        print('=' * 70)
        result = subprocess.run(
            [sys.executable, RUN_INFERENCE_SCRIPT,
             '--iteration-name', cfg['iteration_name'],
             '--sample-id', cfg['sample_id'],
             '--trainer-name', cfg['trainer_name'],
             '--dataset-id', dataset_id],
            env=os.environ,
        )
        if result.returncode != 0:
            raise RuntimeError(f'Inference failed (exit {result.returncode})')

    print(f"\n[OK] {cfg['iteration_name']} pipeline complete.")


if __name__ == '__main__':
    main()
