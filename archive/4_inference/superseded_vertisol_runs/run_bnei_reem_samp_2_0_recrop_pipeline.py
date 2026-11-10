"""Re-preprocess and re-segment bnei_reem_samp_2_0 through the standard pipeline.

Follow-up to the root-cause finding (2026-08-24) that bnei_reem_samp_2_0 was
excluded from pom_replicate_comparison_prompt.md because its driver script
(run_bnei_reem_samp_2_0_pipeline.py) went straight from raw NLM-denoised
output to inference, skipping the canonical center-crop step every other
volume in this project goes through (crop_center_and_preprocess.py / the
manual colab_cli_runner.ipynb steps for Rehovot).

This script redoes the FULL sequence from the raw scan, in the canonical
order (stack real slices only, dropping non-slice reconstruction-preview
TIFFs -> center-crop to a 650^3 cube, matching the canonical Bnei Re'em
nlm_volume.tif's own 650x650x652 convention -> norm200 -> CUDA NLM), then
runs inference with the already-confirmed-correct Bnei Re'em model
(multi_sample_fresh_bnei_reem_i4, checkpoint_final.pth).

Raw folder audit (2026-08-24): the raw slice folder contains 1800 real
numbered slices (matching the scanner log's "Number Of Files=1800") plus 12
non-CT auxiliary/reconstruction-preview TIFFs (ar0-ar6, arc, pp1, pp2,
rec_spr, disp -- SkyScan reconstruction diagnostics), 3 of which have a
different shape than the real slices. A naive glob (as run_preprocess.py's
stack_slices_to_volume does on its own) would pick up all 1812 files. This
script filters to the 1800 real numbered slices by filename pattern before
doing anything else, so the center-crop is computed from the correct slice
count and no preview frames leak into the stack.

Does NOT overwrite the original excluded bnei_reem_samp_2_0 output -- all
paths here are suffixed `_recropped`.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import tifffile

REPO_DIR = Path(__file__).resolve().parents[2]
FILTERS_DIR = REPO_DIR / "02_preprocessing" / "filters"
NNUNET_DIR = REPO_DIR / "02_preprocessing" / "nnunet"
SCRIPTS_DIR = REPO_DIR / "04_inference" / "scripts"

HIVE_BASE = r"\\hive3065\Yael_Mishael\Rony\remote_computer backup"
RAW_DIR = Path(r"\\hive3065\Yael_Mishael\Rony\18.12.25 bnei_reem_samp_2.0")
NEW_SAMPLE_ID = "bnei_reem_samp_2_0_recropped"
CROP_SIZE = 650  # matches canonical Bnei Re'em nlm_volume.tif (650x650x652)

SLICE_RE = re.compile(r"^bnei_reem_highkV_cu011_samp_2\.0\d{8}\.tif$")

LOCAL_CROP_DIR = FILTERS_DIR / "_tmp_center_crop" / NEW_SAMPLE_ID
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


def _run(cmd: list, step: str, cwd: Path) -> None:
    print(f"\n{'=' * 70}\n[{step}] {' '.join(str(c) for c in cmd)}\n{'=' * 70}", flush=True)
    result = subprocess.run(cmd, cwd=str(cwd))
    if result.returncode != 0:
        raise RuntimeError(f"[{step}] failed with returncode {result.returncode}")


def step1_crop() -> None:
    if LOCAL_CROP_DIR.exists() and len(list(LOCAL_CROP_DIR.glob("*.tif"))) == CROP_SIZE:
        print(f"[1/5] SKIP (already cropped): {LOCAL_CROP_DIR}", flush=True)
        return

    all_files = sorted(RAW_DIR.glob("*.tif"))
    real_slices = [p for p in all_files if SLICE_RE.match(p.name)]
    print(f"[1/5] raw folder: {len(all_files)} .tif files total, {len(real_slices)} real numbered slices "
          f"({len(all_files) - len(real_slices)} auxiliary/reconstruction-preview files excluded)", flush=True)
    if len(real_slices) != 1800:
        raise RuntimeError(f"Expected exactly 1800 real slices, found {len(real_slices)}")

    z_start = (len(real_slices) // 2) - (CROP_SIZE // 2)
    z_end = z_start + CROP_SIZE
    selected = real_slices[z_start:z_end]
    print(f"[1/5] Z crop: slices [{z_start}:{z_end}] of {len(real_slices)} (centered)", flush=True)

    first = tifffile.imread(str(selected[0]))
    h, w = first.shape
    y_start = (h - CROP_SIZE) // 2
    x_start = (w - CROP_SIZE) // 2
    print(f"[1/5] XY crop: raw ({h},{w}) -> [{y_start}:{y_start+CROP_SIZE}, {x_start}:{x_start+CROP_SIZE}]", flush=True)

    if LOCAL_CROP_DIR.exists():
        shutil.rmtree(LOCAL_CROP_DIR)
    LOCAL_CROP_DIR.mkdir(parents=True, exist_ok=True)

    for i, src in enumerate(selected):
        img = tifffile.imread(str(src))
        if img.shape != (h, w):
            raise ValueError(f"Unexpected shape change in {src.name}: {img.shape} vs {(h, w)}")
        cropped = img[y_start: y_start + CROP_SIZE, x_start: x_start + CROP_SIZE]
        tifffile.imwrite(str(LOCAL_CROP_DIR / f"slice_{i:06d}.tif"), cropped)
        if i % 200 == 0:
            print(f"[1/5]   wrote {i}/{CROP_SIZE}", flush=True)

    print(f"[1/5] Cropped {CROP_SIZE}^3 volume written to {LOCAL_CROP_DIR}", flush=True)


def step2_norm_nlm() -> None:
    # NOTE: nlm_output/nlm_volume.tif is a SHARED scratch slot reused by every
    # run_preprocess.py invocation regardless of sample -- a shape-only
    # existence check previously caused this step to be silently skipped
    # against a stale file left over from an unrelated 650^3 sample (caught
    # 2026-08-24: the file's mtime was three weeks old). Always regenerate.
    _run(
        [sys.executable, "run_preprocess.py", "--input_dir", str(LOCAL_CROP_DIR)],
        "2/5 norm200+NLM",
        FILTERS_DIR,
    )


def step3_export() -> None:
    if NETWORK_TIF.exists():
        print(f"[3/5] SKIP (already exists): {NETWORK_TIF}", flush=True)
        return
    NETWORK_TIF.parent.mkdir(parents=True, exist_ok=True)
    print(f"[3/5] Copying {LOCAL_NLM_TIF} -> {NETWORK_TIF}", flush=True)
    shutil.copy2(LOCAL_NLM_TIF, NETWORK_TIF)


def step4_tif_to_nifti_and_split(splits: int) -> None:
    nifti_out = NIFTI_PREDICT_DIR / f"{NEW_SAMPLE_ID}_0000.nii.gz"
    if nifti_out.exists():
        print(f"[4/5] SKIP tif_direct (already exists): {nifti_out}", flush=True)
    else:
        _run(
            [
                sys.executable, str(NNUNET_DIR / "preprocessing_nnUNet_predict_tif_direct.py"),
                "--input_tif", str(NETWORK_TIF),
                "--output_dir", str(NIFTI_PREDICT_DIR),
                "--sample_id", NEW_SAMPLE_ID,
            ],
            "4/5 tif_direct",
            REPO_DIR,
        )

    if SPLIT_DIR.exists() and any(SPLIT_DIR.glob("*_0000.nii.gz")):
        print(f"[4/5] SKIP split (already populated): {SPLIT_DIR}", flush=True)
    else:
        _run(
            [
                sys.executable, str(NNUNET_DIR / "preprocessing_nnUNet_predict_split.py"),
                "-i", str(NIFTI_PREDICT_DIR),
                "-o", str(SPLIT_DIR),
                "-m", str(MODEL_DIR),
                "-s", str(splits),
                "-a", "2",
            ],
            "4/5 split",
            REPO_DIR,
        )


def step5_inference(gpu: int) -> None:
    concat_out = CONCAT_DIR / f"{NEW_SAMPLE_ID}.nii.gz"
    if concat_out.exists():
        print(f"[5/5] SKIP (already exists): {concat_out}", flush=True)
        return
    _run(
        [
            sys.executable, str(SCRIPTS_DIR / "run_inference.py"),
            "--iteration-name", "fresh_bnei_reem_i4",
            "--sample-id", NEW_SAMPLE_ID,
            "--trainer-name", TRAINER_NAME,
            "--gpu", str(gpu),
            "--model-dir", str(MODEL_DIR),
            "--input-dir", str(SPLIT_DIR),
            "--output-dir", str(PRED_DIR),
            "--concat-dir", str(CONCAT_DIR),
        ],
        "5/5 inference",
        REPO_DIR,
    )
    print(f"\nDONE: {concat_out}", flush=True)


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--gpu", type=int, default=0)
    parser.add_argument("--splits", type=int, default=4)
    args = parser.parse_args()

    step1_crop()
    step2_norm_nlm()
    step3_export()
    step4_tif_to_nifti_and_split(args.splits)
    step5_inference(args.gpu)


if __name__ == "__main__":
    main()
