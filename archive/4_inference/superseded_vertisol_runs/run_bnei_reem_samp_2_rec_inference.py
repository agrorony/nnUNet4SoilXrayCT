"""Run inference on the already-preprocessed bnei_reem_samp_2_rec_recropped.tif
with the Bnei Re'em model branch (multi_sample_fresh_bnei_reem_i4).

Preprocessing (crop to 650^3 + norm200 + NLM) was done separately by
run_bnei_reem_samp_2_rec_preprocess_only.py, from Rony's corrected
reconstruction at C:\\Users\\rony.schwartz\\Desktop\\new_rec. This script
picks up from that preprocessed volume and only does tif->nifti, split,
and inference.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[2]
NNUNET_DIR = REPO_DIR / "02_preprocessing" / "nnunet"
SCRIPTS_DIR = REPO_DIR / "04_inference" / "scripts"

HIVE_BASE = r"\\hive3065\Yael_Mishael\Rony\remote_computer backup"
SAMPLE_ID = "bnei_reem_samp_2_rec_recropped"

NETWORK_TIF = Path(HIVE_BASE) / "10.5" / f"{SAMPLE_ID}.tif"

SAMPLE_BASE = Path(HIVE_BASE) / "nnUNet_resources" / SAMPLE_ID
NIFTI_PREDICT_DIR = SAMPLE_BASE / "nifti_predict"
SPLIT_DIR = SAMPLE_BASE / "inference_input"
PRED_DIR = SAMPLE_BASE / "inference_output"
CONCAT_DIR = SAMPLE_BASE / "inference_concatenated"

MODEL_DIR = (
    Path(HIVE_BASE) / "nnUNet_resources" / "multi_sample_fresh_bnei_reem_i4"
    / "nnUNet_results" / "Dataset777_GCEF"
    / "nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss_lowlr__nnUNetPlans__3d_fullres"
)
TRAINER_NAME = "nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss_lowlr"


def _run(cmd: list, step: str) -> None:
    print(f"\n{'=' * 70}\n[{step}] {' '.join(str(c) for c in cmd)}\n{'=' * 70}", flush=True)
    result = subprocess.run(cmd, cwd=str(REPO_DIR))
    if result.returncode != 0:
        raise RuntimeError(f"[{step}] failed with returncode {result.returncode}")


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--gpu", type=int, default=0)
    parser.add_argument("--splits", type=int, default=4)
    args = parser.parse_args()

    if not NETWORK_TIF.exists():
        raise FileNotFoundError(f"Preprocessed volume not found: {NETWORK_TIF}")

    nifti_out = NIFTI_PREDICT_DIR / f"{SAMPLE_ID}_0000.nii.gz"
    if nifti_out.exists():
        print(f"[1/2] SKIP tif_direct (already exists): {nifti_out}", flush=True)
    else:
        _run(
            [
                sys.executable, str(NNUNET_DIR / "preprocessing_nnUNet_predict_tif_direct.py"),
                "--input_tif", str(NETWORK_TIF),
                "--output_dir", str(NIFTI_PREDICT_DIR),
                "--sample_id", SAMPLE_ID,
            ],
            "1/2 tif_direct",
        )

    if SPLIT_DIR.exists() and any(SPLIT_DIR.glob("*_0000.nii.gz")):
        print(f"[1/2] SKIP split (already populated): {SPLIT_DIR}", flush=True)
    else:
        _run(
            [
                sys.executable, str(NNUNET_DIR / "preprocessing_nnUNet_predict_split.py"),
                "-i", str(NIFTI_PREDICT_DIR),
                "-o", str(SPLIT_DIR),
                "-m", str(MODEL_DIR),
                "-s", str(args.splits),
                "-a", "2",
            ],
            "1/2 split",
        )

    concat_out = CONCAT_DIR / f"{SAMPLE_ID}.nii.gz"
    if concat_out.exists():
        print(f"[2/2] SKIP (already exists): {concat_out}", flush=True)
    else:
        _run(
            [
                sys.executable, str(SCRIPTS_DIR / "run_inference.py"),
                "--iteration-name", "fresh_bnei_reem_i4",
                "--sample-id", SAMPLE_ID,
                "--trainer-name", TRAINER_NAME,
                "--gpu", str(args.gpu),
                "--model-dir", str(MODEL_DIR),
                "--input-dir", str(SPLIT_DIR),
                "--output-dir", str(PRED_DIR),
                "--concat-dir", str(CONCAT_DIR),
            ],
            "2/2 inference",
        )

    print(f"\nDONE: {concat_out}", flush=True)


if __name__ == "__main__":
    main()
