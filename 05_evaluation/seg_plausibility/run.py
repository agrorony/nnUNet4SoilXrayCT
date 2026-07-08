"""CLI: python run.py labels.tif --thresholds thresholds.yaml --out-dir results/"""
import argparse
import os
import sys

import numpy as np
import tifffile
import yaml

from instance_matcher import build_track_graph, assign_persistent_ids, rasterize_instance_map, default_device
from continuity_metrics import compute_transition_metrics, aggregate_track_metrics
from plausibility_report import (
    detect_events, flag_transitions, build_track_table,
    export_errors_json, export_track_table_csv,
)

DEFAULT_THRESHOLDS = {
    'default': {
        'min_iou': 0.3,
        'min_area_ratio': 0.5,
        'max_area_ratio': 2.0,
        'max_centroid_jump': 15.0,
    }
}


def load_volume(path):
    if path.lower().endswith(('.tif', '.tiff')):
        return tifffile.imread(path)
    if path.lower().endswith(('.nii', '.nii.gz')):
        import nibabel as nib
        img = nib.load(path)
        data = np.asarray(img.dataobj)
        # nnUNet nifti volumes here are stored (X, Y, Z); this pipeline
        # iterates slices along axis 0, so reorder to (Z, Y, X).
        if data.ndim == 3:
            data = np.transpose(data, (2, 1, 0))
        return data.astype(np.int32)
    raise ValueError(f'Unsupported file type: {path}')


def load_thresholds(path):
    if path is None:
        print('WARNING: no --thresholds given, using built-in defaults.')
        return DEFAULT_THRESHOLDS
    with open(path) as fh:
        th = yaml.safe_load(fh)
    return th


def run_pipeline(volume, thresholds, out_dir, device='auto'):
    os.makedirs(out_dir, exist_ok=True)

    graph, props_by_zc, all_matches = build_track_graph(volume, device=device)
    id_map, lineage = assign_persistent_ids(graph)
    instance_map = rasterize_instance_map(volume, id_map)

    all_transition_metrics = []
    for (z, cls), matches in all_matches.items():
        props_z = props_by_zc.get((z, cls), [])
        props_z1 = props_by_zc.get((z + 1, cls), [])
        tms = compute_transition_metrics(props_z, props_z1, matches)
        for tm in tms:
            tm['z'] = z
            tm['class'] = cls
            tm['label_z'] = id_map[(z, cls, tm['local_id_z'])]
            tm['label_z1'] = id_map[(z + 1, cls, tm['local_id_z1'])]
            all_transition_metrics.append(tm)

    aggregated = aggregate_track_metrics(lineage, all_transition_metrics)

    events = detect_events(graph, id_map)
    flagged = flag_transitions(all_transition_metrics, thresholds)

    track_df = build_track_table(lineage, aggregated)

    instance_map_path = os.path.join(out_dir, 'instance_map.tif')
    track_table_path = os.path.join(out_dir, 'track_table.csv')
    errors_path = os.path.join(out_dir, 'errors.json')

    tifffile.imwrite(instance_map_path, instance_map)
    export_track_table_csv(track_df, track_table_path)
    errors = export_errors_json(events, flagged, errors_path)

    return {
        'instance_map_path': instance_map_path,
        'track_table_path': track_table_path,
        'errors_path': errors_path,
        'n_tracks': len(lineage),
        'n_events': len(events),
        'n_flagged': len(flagged),
        'n_errors': len(errors),
    }


def main():
    parser = argparse.ArgumentParser(description='Segmentation plausibility / plane-continuity checker')
    parser.add_argument('labels', help='Path to label volume (.tif/.tiff or .nii/.nii.gz)')
    parser.add_argument('--thresholds', default=None, help='Path to thresholds.yaml (optional)')
    parser.add_argument('--out-dir', default='results', help='Output directory')
    parser.add_argument('--device', default='auto', choices=['auto', 'cpu', 'cuda'],
                         help="Where to compute IoU overlap matrices ('auto' = cuda if available)")
    args = parser.parse_args()

    volume = load_volume(args.labels)
    print(f'Loaded volume {args.labels}: shape={volume.shape}, dtype={volume.dtype}, '
          f'classes={sorted(int(c) for c in np.unique(volume) if c != 0)}')
    resolved_device = default_device() if args.device == 'auto' else args.device
    print(f'Device: {resolved_device}')

    thresholds = load_thresholds(args.thresholds)
    summary = run_pipeline(volume, thresholds, args.out_dir, device=args.device)

    print(f"[OK] instance_map -> {summary['instance_map_path']}")
    print(f"[OK] track_table  -> {summary['track_table_path']}")
    print(f"[OK] errors.json  -> {summary['errors_path']}")
    print(f"Tracks: {summary['n_tracks']}  Events: {summary['n_events']}  "
          f"Flagged transitions: {summary['n_flagged']}  Total errors: {summary['n_errors']}")


if __name__ == '__main__':
    main()
