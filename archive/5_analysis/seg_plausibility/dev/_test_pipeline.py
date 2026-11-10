"""Runs the full run.py pipeline on the synthetic volume and asserts
expected outputs / events are produced. Prints PASS/FAIL per assertion plus
a final summary line.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import tifffile

from _make_synthetic import build_synthetic_volume, OUT_PATH
from run import run_pipeline

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, 'test_results')

# Tuned for the synthetic geometry: A is perfectly static (dist=0, iou=1),
# D's normal frames are also static, its one deliberate jump is ~18px.
THRESHOLDS = {
    'default': {
        'min_iou': 0.05,
        'min_area_ratio': 0.3,
        'max_area_ratio': 3.0,
        'max_centroid_jump': 10.0,
    }
}

results = []


def check(name, condition):
    status = 'PASS' if condition else 'FAIL'
    print(f'[{status}] {name}')
    results.append(condition)
    return condition


def main():
    if not os.path.isfile(OUT_PATH):
        vol = build_synthetic_volume()
        tifffile.imwrite(OUT_PATH, vol)
    vol = tifffile.imread(OUT_PATH)

    summary = run_pipeline(vol, THRESHOLDS, OUT_DIR)

    instance_map_path = summary['instance_map_path']
    track_table_path = summary['track_table_path']
    errors_path = summary['errors_path']

    check('instance_map.tif created', os.path.isfile(instance_map_path))
    check('track_table.csv created', os.path.isfile(track_table_path))
    check('errors.json created', os.path.isfile(errors_path))

    with open(errors_path) as fh:
        errors = json.load(fh)
    track_df = pd.read_csv(track_table_path)

    events_by_type = {}
    for e in errors:
        events_by_type.setdefault(e['event'], []).append(e)

    check('disappearance present in errors.json',
          any(e['z'] == 19 for e in events_by_type.get('disappear', [])))

    check('split present in errors.json',
          any(e['z'] == 14 for e in events_by_type.get('split', [])))

    check('implausible jump present in errors.json',
          any(e['z'] == 19 for e in events_by_type.get('centroid_jump', [])))

    # Identify the clean-continuation object A: full-depth track (0..39)
    # with essentially perfect IoU throughout (unlike D, which also spans
    # 0..39 but has a bad transition at its jump).
    full_depth = track_df[(track_df['z_start'] == 0) & (track_df['z_end'] == 39)]
    clean_candidates = full_depth[full_depth['worst_iou'] > 0.9]
    clean_ok = len(clean_candidates) >= 1
    check('clean-continuation object identified in track_table', clean_ok)

    if clean_ok:
        clean_ids = set(clean_candidates['label'].tolist())
        flagged_types = {'low_iou', 'area_shrink', 'area_growth', 'centroid_jump'}
        clean_flags = [e for e in errors if e['event'] in flagged_types and e['object_id'] in clean_ids]
        check('clean-continuation object has zero flagged transitions', len(clean_flags) == 0)
    else:
        check('clean-continuation object has zero flagged transitions', False)

    n_pass = sum(results)
    n_total = len(results)
    print(f'\n{n_pass}/{n_total} assertions passed')
    if n_pass == n_total:
        print('SUMMARY: PASS')
        sys.exit(0)
    else:
        print('SUMMARY: FAIL')
        sys.exit(1)


if __name__ == '__main__':
    main()
