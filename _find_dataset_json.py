import os, json

HIVE_BASE = r'\\hive3065\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources'

# Search more broadly
search_roots = [
    os.path.join(HIVE_BASE, 'multi_sample_fresh_bnei_reem'),
    os.path.join(HIVE_BASE, 'multi_sample_iter02'),
]

for root_dir in search_roots:
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
