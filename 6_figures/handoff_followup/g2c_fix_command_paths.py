"""Part G follow-up 2: repo paths inside backticked commands (tokens with spaces), which g1/g2b did not scan.
Same rules as g2b: README backed up first, every replacement counted and asserted.

Usage: python g2c_fix_command_paths.py <package_dir> <backup_dir> <evidence_dir>
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

SPLIT = ('02_preprocessing/nnunet/preprocessing_nnUNet_predict_split.py', '2_preprocessing/nnunet_dataset/preprocessing_nnUNet_predict_split.py')
EDITS = {  # rel: [(old, new, expected count)]
    '03_models/bnei_reem_i4/README.md': [(*SPLIT, 1)],
    '03_models/mishmar_loess_i2/README.md': [(*SPLIT, 1)],
    'README.md': [(*SPLIT, 1),
                  ('`04_inference/postprocessing_nnUNet_predict_concatenate.py -i', '`4_inference/postprocessing_nnUNet_predict_concatenate.py -i', 1)],
    '05_analysis_outputs/README.md': [('`05_evaluation/psd/run_psd_diagnostics.py extended`', '`5_analysis/shared_code/run_psd_diagnostics.py extended`', 1)],
}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    pkg, bak, evid = map(Path, sys.argv[1:4])
    plans = {}
    for rel, reps in EDITS.items():
        with open(pkg / rel, encoding='utf-8', newline='') as f:
            s = f.read()
        for o, n, c in reps:
            assert s.count(o) == c, (rel, o, s.count(o))
            s = s.replace(o, n)
        plans[rel] = s
    log = []
    for rel, s in plans.items():
        p, b = pkg / rel, bak / rel
        assert not b.exists(), b
        b.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, b)
        with open(p, 'w', encoding='utf-8', newline='') as f:
            f.write(s)
        log.append(dict(path=rel, edits=EDITS[rel], sha256_before=sha(b), sha256_after=sha(p), backup=str(b)))
        print('edited', rel)
    json.dump(log, open(evid / 'G2c_log.json', 'w'), indent=1, ensure_ascii=False)


if __name__ == '__main__':
    main()
