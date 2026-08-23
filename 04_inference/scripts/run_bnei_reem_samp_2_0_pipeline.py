"""One-off driver: take the preprocessed samp_2.0 volume through inference.

Chains the existing, previously-proven pipeline stages for a brand-new Bnei
Re'em sample (raw slices at '18.12.25 bnei_reem_samp_2.0', no prior
inference_concatenated output anywhere on the share):

    1. Copy the locally-preprocessed NLM volume
       (02_preprocessing/filters/nlm_output/nlm_volume.tif, produced by
       run_preprocess.py --input_dir ".../18.12.25 bnei_reem_samp_2.0") to the
       canonical network root under a name that does NOT collide with the
       existing nlm_volume.tif (that name is reserved for sample_2).
    2. preprocessing_nnUNet_predict_tif_direct.py -> single _0000.nii.gz
    3. preprocessing_nnUNet_predict_split.py -> chunked inference_input/
    4. run_inference.py (fresh_bnei_reem_i4 checkpoint) -> predict + concatenate

All output paths are sample-specific (bnei_reem_samp_2_0/...) so nothing here
touches the existing bnei_reem_fresh_bnei_reem_i4/ folder that nlm_volume's
results live in and that the PSD batch may still be reading.

Each step is skipped if its output already exists, so this script is safe to
re-run after an interruption.

Usage
-----
::

    python run_bnei_reem_samp_2_0_pipeline.py [--gpu 0]
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[2]
FILTERS_DIR = REPO_DIR / "02_preprocessing" / "filters"
NNUNET_DIR = REPO_DIR / "02_preprocessing" / "nnunet"
SCRIPTS_DIR = REPO_DIR / "04_inference" / "scripts"

HIVE_BASE = r"\\hive3065\Yael_Mishael\Rony\remote_computer backup"
NEW_SAMPLE_ID = "bnei_reem_samp_2_0"

LOCAL_NLM_TIF = FILTERS_DIR / "nlm_output" / "nlm_volume.tif"
NETWORK_TIF = Path(HIVE_BASE) / "10.5" / f"{NEW_SAMPLE_ID}.tif"

SAMPLE_BASE = Path(HIVE_BASE) / "nnUNet_resources" / NEW_SAMPLE_ID
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
    print(f"\n{'=' * 70}\n[{step}] {' '.join(str(c) for c in cmd)}\n{'=' * 70}")
    result = subprocess.run(cmd, cwd=str(REPO_DIR))
    if result.returncode != 0:
        raise RuntimeError(f"[{step}] failed with returncode {result.returncode}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--gpu", type=int, default=0)
    parser.add_argument("--splits", type=int, default=8)
    args = parser.parse_args()

    if not LOCAL_NLM_TIF.exists():
        raise FileNotFoundError(
            f"Preprocessed volume not found: {LOCAL_NLM_TIF}. "
            f"Run: python run_preprocess.py --input_dir \"...\\18.12.25 bnei_reem_samp_2.0\" "
            f"from {FILTERS_DIR} first."
        )

    # Step 1: copy preprocessed volume to canonical network location.
    if NETWORK_TIF.exists():
        print(f"[1/4] SKIP (already exists): {NETWORK_TIF}")
    else:
        print(f"[1/4] Copying {LOCAL_NLM_TIF} -> {NETWORK_TIF}")
        NETWORK_TIF.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(LOCAL_NLM_TIF, NETWORK_TIF)

    # Step 2: tif -> single _0000.nii.gz (identity affine, matches project convention).
    nifti_out = NIFTI_PREDICT_DIR / f"{NEW_SAMPLE_ID}_0000.nii.gz"
    if nifti_out.exists():
        print(f"[2/4] SKIP (already exists): {nifti_out}")
    else:
        _run(
            [
                sys.executable, str(NNUNET_DIR / "preprocessing_nnUNet_predict_tif_direct.py"),
                "--input_tif", str(NETWORK_TIF),
                "--output_dir", str(NIFTI_PREDICT_DIR),
                "--sample_id", NEW_SAMPLE_ID,
            ],
            "2/4 tif_direct",
        )

    # Step 3: split into overlapping chunks sized for the model's 3d_fullres patch.
    if SPLIT_DIR.exists() and any(SPLIT_DIR.glob("*_0000.nii.gz")):
        print(f"[3/4] SKIP (already populated): {SPLIT_DIR}")
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
            "3/4 split",
        )

    # Step 4: predict per chunk + concatenate back into one volume.
    concat_out = CONCAT_DIR / f"{NEW_SAMPLE_ID}.nii.gz"
    if concat_out.exists():
        print(f"[4/4] SKIP (already exists): {concat_out}")
    else:
        _run(
            [
                sys.executable, str(SCRIPTS_DIR / "run_inference.py"),
                "--iteration-name", "fresh_bnei_reem_i4",
                "--sample-id", NEW_SAMPLE_ID,
                "--trainer-name", TRAINER_NAME,
                "--gpu", str(args.gpu),
                "--model-dir", str(MODEL_DIR),
                "--input-dir", str(SPLIT_DIR),
                "--output-dir", str(PRED_DIR),
                "--concat-dir", str(CONCAT_DIR),
            ],
            "4/4 inference",
        )

    print(f"\nDONE: {concat_out}")


if __name__ == "__main__":
    main()
