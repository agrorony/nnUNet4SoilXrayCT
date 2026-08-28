"""launch_napari_review.py — consolidated napari review launcher (S6).

Replaces the 12 root-level `_launch_napari_*.py` scripts. Each of the
originals did one of a small number of shapes:
  - open `microsam_3d/run.py`'s viewer with a volume, a GT layer, and one
    or more prediction layers (`compare_gt`, `comparison`, `fullvol`,
    `microsam_multi` below all funnel into this — they differ only in
    zrange and how many prediction layers are passed);
  - open `seg_plausibility/napari_review.py` for the seg-plausibility
    results-dir viewer (`seg_plausibility` mode).

Note: `_launch_napari_iter04.py` is the one exception in the original set
— it opens `inspect_predictions.py`, a genuinely different underlying
tool (not `microsam_3d/run.py`), per REORG_PLAN.md §3.3 row 33. This is
handled here via `--viewer inspect_predictions` rather than being forced
into the microsam dispatch path.

Usage:
    python launch_napari_review.py --mode fullvol \
        --volume-path .../nlm_volume.tif --gt-path .../annotations_i3.nii.gz \
        --pred-paths fresh_bnei_reem_i3=.../nlm_volume.nii.gz --zrange 50 70

    python launch_napari_review.py --mode seg_plausibility \
        --seg-plausibility-results-dir .../seg_plausibility_i4 \
        --volume-path .../nlm_volume.tif --pred-paths pred=.../nlm_volume.nii.gz

    python launch_napari_review.py --viewer inspect_predictions \
        --pred-paths iter04=.../nlm_volume.nii.gz
"""
import argparse
import os
import subprocess
import sys

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
MICROSAM_DIR = os.path.join(REPO_DIR, '05_evaluation', 'microsam_3d')
SEG_PLAUSIBILITY_DIR = os.path.join(REPO_DIR, '05_evaluation', 'seg_plausibility')
DATASET_INFO_PATH = os.path.join(REPO_DIR, 'dataset_info.json')
INSPECT_PREDICTIONS = os.path.join(REPO_DIR, '06_reporting', 'scripts', 'inspect_predictions.py')


def parse_pred_paths(pred_paths):
    """Parse repeatable name=path pairs. First entry is the primary `pred_path`;
    remaining ones become `extra_label_paths` (matches microsam_3d/run.py's main() signature)."""
    parsed = []
    for spec in pred_paths or []:
        name, path = spec.split('=', 1)
        parsed.append((name, path))
    return parsed


def run_microsam(args):
    sys.path.insert(0, MICROSAM_DIR)
    os.chdir(MICROSAM_DIR)
    from run import main as microsam_main

    preds = parse_pred_paths(args.pred_paths)
    if not preds:
        raise ValueError('--mode ' + args.mode + ' requires at least one --pred-paths entry')

    checks = [('volume', args.volume_path)]
    if args.gt_path:
        checks.append(('GT', args.gt_path))
    checks += preds
    for name, path in checks:
        if not os.path.isfile(path):
            raise FileNotFoundError(f'Missing {name}: {path}')
        print(f'[OK] {name}: {path}')

    primary_name, primary_path = preds[0]
    extra_label_paths = {name: path for name, path in preds[1:]} or None

    zrange = tuple(args.zrange) if args.zrange else None
    microsam_main(
        volume_path=args.volume_path,
        pred_path=primary_path,
        gt_path=args.gt_path,
        extra_label_paths=extra_label_paths,
        zrange=zrange,
        debug=args.debug,
        title=args.title,
    )


def run_seg_plausibility(args):
    if not args.seg_plausibility_results_dir:
        raise ValueError('--mode seg_plausibility requires --seg-plausibility-results-dir')
    preds = parse_pred_paths(args.pred_paths)
    if not preds:
        raise ValueError('--mode seg_plausibility requires exactly one --pred-paths entry (the prediction volume)')
    _, prediction_path = preds[0]

    cmd = [
        sys.executable, os.path.join(SEG_PLAUSIBILITY_DIR, 'napari_review.py'),
        '--results-dir', args.seg_plausibility_results_dir,
        '--original', args.volume_path,
        '--prediction', prediction_path,
        '--dataset-info', DATASET_INFO_PATH,
    ]
    if args.exclude_classes:
        cmd += ['--exclude-classes', args.exclude_classes]
    subprocess.run(cmd, check=True)


def run_inspect_predictions(args):
    preds = parse_pred_paths(args.pred_paths)
    if not preds:
        raise ValueError('--viewer inspect_predictions requires a --pred-paths entry')
    _, pred_path = preds[0]
    cmd = [sys.executable, INSPECT_PREDICTIONS, pred_path]
    if args.reverse_label_map:
        cmd.append('--reverse_label_map')
    subprocess.run(cmd, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--mode', choices=['compare_gt', 'comparison', 'fullvol', 'microsam_multi', 'seg_plausibility'],
                         default='fullvol', help='Dispatch mode. All microsam-based modes share the same code path.')
    parser.add_argument('--viewer', choices=['microsam', 'inspect_predictions'], default='microsam',
                         help='"inspect_predictions" replicates the one original script (_launch_napari_iter04.py) '
                              'that used a genuinely different tool, per REORG_PLAN.md row 33.')
    parser.add_argument('--volume-path')
    parser.add_argument('--gt-path')
    parser.add_argument('--pred-paths', action='append', metavar='NAME=PATH',
                         help='Repeatable. First entry is the primary prediction; rest become extra label layers.')
    parser.add_argument('--zrange', type=int, nargs=2, metavar=('START', 'END'))
    parser.add_argument('--title', default=None, help='Custom napari window title (only used with --viewer microsam).')
    parser.add_argument('--debug', action='store_true', default=True)
    parser.add_argument('--seg-plausibility-results-dir')
    parser.add_argument('--exclude-classes', default=None, help='Only used with --mode seg_plausibility.')
    parser.add_argument('--reverse-label-map', action='store_true', help='Only used with --viewer inspect_predictions.')
    args = parser.parse_args()

    if args.viewer == 'inspect_predictions':
        run_inspect_predictions(args)
    elif args.mode == 'seg_plausibility':
        run_seg_plausibility(args)
    else:
        run_microsam(args)


if __name__ == '__main__':
    main()
