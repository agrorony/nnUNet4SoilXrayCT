"""One-off driver: run both Rehovot scans through both selected models.

Two Rehovot volumes (confirmed genuinely different scans, not duplicates,
2026-08-15):
    - Rehovot_samp3_highkV_Cu0.11_15um  (registered in data_registry.json)
    - rehovot_samp_2                     (undocumented in registry, but
      traced to colab_cli_runner.ipynb: same crop_center_and_preprocess.py
      pipeline -- center-crop 650^3, norm200, CUDA NLM, 15um voxels)

Two models:
    - mishmar_hanegev_maoz_3_5p85um_loess_i2  (nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss)
    - fresh_bnei_reem_i4                       (nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss_lowlr)

Both models share the same plans (patch_size [32,256,256], spacing
[1,1,1]), so each volume is split into chunks ONCE and reused for both
models' predictions.

Usage
-----
::

    python run_rehovot_inference_pipeline.py [--gpu 1] [--splits 8]
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[2]
FILTERS_DIR = REPO_DIR / "02_preprocessing" / "filters"
NNUNET_DIR = REPO_DIR / "02_preprocessing" / "nnunet"
SCRIPTS_DIR = REPO_DIR / "04_inference" / "scripts"

HIVE_BASE = r"\\hive3065\Yael_Mishael\Rony\remote_computer backup"
NNUNET_RESOURCES = Path(HIVE_BASE) / "nnUNet_resources"

VOLUMES = {
    "Rehovot_samp3_highkV_Cu0.11_15um": Path(HIVE_BASE) / "10.5" / "Rehovot_samp3_highkV_Cu0.11_15um.tif",
    "rehovot_samp_2": Path(HIVE_BASE) / "10.5" / "rehovot_samp_2.tif",
}

MODELS = {
    "loess_i2": dict(
        iteration_name="mishmar_hanegev_maoz_3_5p85um_loess_i2",
        trainer_name="nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss",
        model_dir=(
            NNUNET_RESOURCES / "multi_sample_mishmar_hanegev_maoz_3_5p85um_loess_i2"
            / "nnUNet_results" / "Dataset777_GCEF"
            / "nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss__nnUNetPlans__3d_fullres"
        ),
    ),
    "bnei_reem_i4": dict(
        iteration_name="fresh_bnei_reem_i4",
        trainer_name="nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss_lowlr",
        model_dir=(
            NNUNET_RESOURCES / "multi_sample_fresh_bnei_reem_i4"
            / "nnUNet_results" / "Dataset777_GCEF"
            / "nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss_lowlr__nnUNetPlans__3d_fullres"
        ),
    ),
}


def _run(cmd: list, step: str, log_lines: list) -> float:
    header = f"\n{'=' * 70}\n[{step}] {' '.join(str(c) for c in cmd)}\n{'=' * 70}"
    print(header)
    log_lines.append(header)
    t0 = time.time()
    result = subprocess.run(cmd, cwd=str(REPO_DIR), capture_output=True, text=True)
    elapsed = time.time() - t0
    log_lines.append(result.stdout)
    if result.stderr:
        log_lines.append("STDERR:\n" + result.stderr)
    log_lines.append(f"[{step}] elapsed: {elapsed:.1f}s, returncode: {result.returncode}")
    print(result.stdout[-3000:])
    if result.returncode != 0:
        print("STDERR:", result.stderr[-3000:])
        raise RuntimeError(f"[{step}] failed with returncode {result.returncode}")
    return elapsed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--gpu", type=int, default=1)
    parser.add_argument("--splits", type=int, default=8)
    args = parser.parse_args()

    for sample_id, tif_path in VOLUMES.items():
        log_lines = [f"Rehovot inference log -- {sample_id}", f"Started: {time.ctime()}"]
        if not tif_path.exists():
            print(f"SKIP {sample_id}: source tif not found at {tif_path}")
            continue

        sample_base = NNUNET_RESOURCES / f"rehovot_inference_{sample_id}"
        nifti_dir = sample_base / "nifti_predict"
        split_dir = sample_base / "inference_input"

        nifti_out = nifti_dir / f"{sample_id}_0000.nii.gz"
        if nifti_out.exists():
            print(f"[tif->nifti] SKIP (exists): {nifti_out}")
        else:
            _run(
                [
                    sys.executable, str(NNUNET_DIR / "preprocessing_nnUNet_predict_tif_direct.py"),
                    "--input_tif", str(tif_path),
                    "--output_dir", str(nifti_dir),
                    "--sample_id", sample_id,
                ],
                f"{sample_id}/tif->nifti", log_lines,
            )

        if split_dir.exists() and any(split_dir.glob("*_0000.nii.gz")):
            print(f"[split] SKIP (populated): {split_dir}")
        else:
            any_model_dir = next(iter(MODELS.values()))["model_dir"]
            _run(
                [
                    sys.executable, str(NNUNET_DIR / "preprocessing_nnUNet_predict_split.py"),
                    "-i", str(nifti_dir),
                    "-o", str(split_dir),
                    "-m", str(any_model_dir),
                    "-s", str(args.splits),
                    "-a", "2",
                ],
                f"{sample_id}/split", log_lines,
            )

        for model_key, model_cfg in MODELS.items():
            pred_dir = sample_base / f"inference_output_{model_key}"
            concat_dir = sample_base / f"inference_concatenated_{model_key}"
            concat_path = concat_dir / f"{sample_id}.nii.gz"
            if concat_path.exists():
                print(f"[{model_key}] SKIP (exists): {concat_path}")
                continue
            elapsed = _run(
                [
                    sys.executable, str(SCRIPTS_DIR / "run_inference.py"),
                    "--iteration-name", model_cfg["iteration_name"],
                    "--sample-id", sample_id,
                    "--trainer-name", model_cfg["trainer_name"],
                    "--gpu", str(args.gpu),
                    "--model-dir", str(model_cfg["model_dir"]),
                    "--input-dir", str(split_dir),
                    "--output-dir", str(pred_dir),
                    "--concat-dir", str(concat_dir),
                ],
                f"{sample_id}/{model_key}/predict+concat", log_lines,
            )
            log_lines.append(f"{model_key} runtime: {elapsed:.1f}s -> {concat_path}")

        log_path = sample_base / "pipeline_log.txt"
        log_path.write_text("\n".join(log_lines), encoding="utf-8")
        print(f"\nDONE {sample_id}. Log: {log_path}")


if __name__ == "__main__":
    main()
