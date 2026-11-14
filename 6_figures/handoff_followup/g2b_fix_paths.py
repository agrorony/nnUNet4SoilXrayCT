"""Part G follow-up: correct the README repo/package paths that the post-G2 existence check (every backticked path
must exist in the package or in the repo tree) found missing. README backed up before editing; every match must be unique.

Usage: python g2b_fix_paths.py <package_dir> <backup_dir> <evidence_dir>
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

TE = '05_analysis_outputs/connectivity/Topology_Metrics_Aug2026/raw'
TORT = ("`05_analysis_outputs/tortuosity_subvolumes_20261004/`", "`05_analysis_outputs/tortuosity/tortuosity_subvolumes_20261004/`")
LOG_NOTE = " (run log on the lab computer, in the pre-2026-11 working tree; never in git)"
EDITS = {
    f'{TE}/psd_diag_20260829T164703_mishmar_hanegev_maoz_2_8p8um_native/README.md': [TORT],
    f'{TE}/psd_diag_20260902T215639_mishmar_second_8p8um_label_downsample_15um/README.md': [TORT],
    '01_volumes/bnei_reem_fresh_bnei_reem_i4/README.md': [
        ("`05_evaluation/psd/full_volume_batch/logs/nlm_volume_fresh_bnei_reem_i4.log`",
         "`05_evaluation/psd/full_volume_batch/logs/nlm_volume_fresh_bnei_reem_i4.log`" + LOG_NOTE)],
    '01_volumes/mishmar_hanegev_maoz_3_5p85um/README.md': [
        ("`05_evaluation/psd/full_volume_batch/logs/mishmar_hanegev_maoz_3_5p85um_scratch_i2.log`",
         "`05_evaluation/psd/full_volume_batch/logs/mishmar_hanegev_maoz_3_5p85um_scratch_i2.log`" + LOG_NOTE)],
    '02_annotations/bnei_reem_i4/README.md': [
        ("(`03_training/run_configs/*.yaml`, `preprocessing_nnUNet_train.py`)",
         "(`3_training/vertisol_i4/fresh_bnei_reem_i4.yaml`, `preprocessing_nnUNet_train.py`)")],
    '02_annotations/mishmar_loess_i2/README.md': [
        ("(`03_training/run_configs/*.yaml`, `preprocessing_nnUNet_train.py`)",
         "(`3_training/loess_i2/mishmar_hanegev_maoz_3_5p85um_loess_i2.yaml`, `preprocessing_nnUNet_train.py`)")],
    '05_analysis_outputs/README.md': [
        ("`05_evaluation/psd/fig4_inference_20260815/scripts/extract_subvolumes.py`",
         "`5_analysis/pore_size_distribution/scripts/extract_subvolumes.py`")],
}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    pkg, bak, evid = map(Path, sys.argv[1:4])
    plans = {}
    for rel, reps in EDITS.items():
        with open(pkg / rel, encoding='utf-8', newline='') as f:
            s = f.read()
        for o, n in reps:
            assert s.count(o) == 1, (rel, o)
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
    json.dump(log, open(evid / 'G2b_log.json', 'w'), indent=1, ensure_ascii=False)


if __name__ == '__main__':
    main()
