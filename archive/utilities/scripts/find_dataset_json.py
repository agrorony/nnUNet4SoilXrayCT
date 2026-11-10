"""find_dataset_json.py — generalized dataset.json/plans.json locator (S12).

Replaces the old repo-root `_find_dataset_json.py`, which hardcoded a
2-entry search_roots list (multi_sample_fresh_bnei_reem, multi_sample_iter02).
This version takes search roots as a CLI arg.

Usage:
    python find_dataset_json.py --search-roots "\\\\hive3065\\...\\multi_sample_fresh_bnei_reem" "\\\\hive3065\\...\\multi_sample_iter02"
"""
import argparse
import json
import os


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--search-roots', nargs='+', required=True,
                         help='One or more directories to walk looking for dataset.json / dataset_fingerprint.json / plans.json.')
    args = parser.parse_args()

    for root_dir in args.search_roots:
        if not os.path.isdir(root_dir):
            print(f'Not found: {root_dir}')
            continue
        print(f'\nSearching: {root_dir}')
        for root, dirs, files in os.walk(root_dir):
            for f in files:
                if f in ('dataset.json', 'dataset_fingerprint.json', 'plans.json'):
                    path = os.path.join(root, f)
                    print(f'  {path}')
                    if f == 'dataset.json':
                        with open(path) as fh:
                            d = json.load(fh)
                        print('  labels:', json.dumps(d.get('labels', {}), indent=4))


if __name__ == '__main__':
    main()
