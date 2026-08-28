"""CLI: python calibrate.py trusted1.tif trusted2.tif ... --out thresholds.yaml

Runs the matcher + metrics on each trusted volume, pools all transition
metrics per class, prints 1st/5th/95th/99th percentiles for IoU / area_ratio /
centroid distance, and writes a starter thresholds.yaml from the 5th/95th
percentiles.
"""
import argparse
from collections import defaultdict

import numpy as np
import yaml

from instance_matcher import build_track_graph
from continuity_metrics import compute_transition_metrics
from run import load_volume


def pool_metrics(paths, device='auto'):
    pooled = defaultdict(lambda: {'iou': [], 'area_ratio': [], 'centroid_dist': []})
    for path in paths:
        volume = load_volume(path)
        print(f'Processing {path}: shape={volume.shape}')
        graph, props_by_zc, all_matches = build_track_graph(volume, device=device)
        for (z, cls), matches in all_matches.items():
            props_z = props_by_zc.get((z, cls), [])
            props_z1 = props_by_zc.get((z + 1, cls), [])
            tms = compute_transition_metrics(props_z, props_z1, matches)
            for tm in tms:
                pooled[cls]['iou'].append(tm['iou'])
                pooled[cls]['area_ratio'].append(tm['area_ratio'])
                pooled[cls]['centroid_dist'].append(tm['centroid_dist'])
    return pooled


def summarize(pooled):
    percentiles = [1, 5, 95, 99]
    summary = {}
    for cls, metrics in sorted(pooled.items()):
        summary[cls] = {}
        print(f'\nClass {cls}:')
        for name, values in metrics.items():
            if not values:
                continue
            arr = np.array(values, dtype=float)
            pct = {p: float(np.percentile(arr, p)) for p in percentiles}
            summary[cls][name] = pct
            print(f'  {name}: ' + ', '.join(f'p{p}={v:.3f}' for p, v in pct.items()))
    return summary


def build_thresholds_yaml(summary):
    thresholds = {}
    for cls, metrics in summary.items():
        cls_th = {}
        if 'iou' in metrics:
            cls_th['min_iou'] = round(metrics['iou'][5], 4)
        if 'area_ratio' in metrics:
            cls_th['min_area_ratio'] = round(metrics['area_ratio'][5], 4)
            cls_th['max_area_ratio'] = round(metrics['area_ratio'][95], 4)
        if 'centroid_dist' in metrics:
            cls_th['max_centroid_jump'] = round(metrics['centroid_dist'][95], 4)
        thresholds[int(cls)] = cls_th
    return thresholds


def main():
    parser = argparse.ArgumentParser(description='Calibrate plausibility thresholds from trusted volumes')
    parser.add_argument('volumes', nargs='+', help='Trusted label volumes (.tif/.nii.gz)')
    parser.add_argument('--out', default='thresholds.yaml', help='Output thresholds YAML path')
    parser.add_argument('--device', default='auto', choices=['auto', 'cpu', 'cuda'],
                         help="Where to compute IoU overlap matrices ('auto' = cuda if available)")
    args = parser.parse_args()

    pooled = pool_metrics(args.volumes, device=args.device)
    summary = summarize(pooled)
    thresholds = build_thresholds_yaml(summary)

    with open(args.out, 'w') as fh:
        yaml.safe_dump(thresholds, fh, default_flow_style=False, sort_keys=True)
    print(f'\n[OK] wrote {args.out}')


if __name__ == '__main__':
    main()
