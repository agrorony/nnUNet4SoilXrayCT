"""Part 2 step 3-4 -- run the full standard pipeline (norm200 -> NLM ->
nnUNet inference) on a volume's newly-exported ROI-expanded crop, then run
the channel-collapse sanity check against that volume's existing-crop
baseline pore/POM fractions.

Usage: python part2_run_pipeline.py --volume-key bnei_reem_canonical
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import nibabel as nib
import numpy as np
import tifffile

HERE = Path(__file__).resolve().parent
RUN_DIR = HERE.parent
REPO_DIR = RUN_DIR.parents[2]  # .../nnUNet4SoilXrayCT
FILTERS_DIR = REPO_DIR / "02_preprocessing" / "filters"
NNUNET_DIR = REPO_DIR / "02_preprocessing" / "nnunet"
CONCAT_SCRIPT = REPO_DIR / "04_inference" / "postprocessing_nnUNet_predict_concatenate.py"
HIVE_BASE = Path(r"\\hive3065\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources")

PORE_LABEL, POM_LABEL = 5, 2
POM_COLLAPSE_FLOOR_PCT = 0.3  # same explicit floor used throughout this project's POM work

VOLUME_CONFIGS = {
    "bnei_reem_canonical": dict(
        model_dir=HIVE_BASE / "multi_sample_fresh_bnei_reem_i4" / "nnUNet_results" / "Dataset777_GCEF"
                   / "nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss_lowlr__nnUNetPlans__3d_fullres",
        baseline_pore_pct=21.636,
        baseline_pom_pct=0.819,
    ),
    "mishmar_native_5p85um": dict(
        model_dir=HIVE_BASE / "multi_sample_mishmar_hanegev_maoz_3_5p85um_loess_i2" / "nnUNet_results" / "Dataset777_GCEF"
                   / "nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss__nnUNetPlans__3d_fullres",
        baseline_pore_pct=27.038,
        baseline_pom_pct=1.615,
    ),
    "mishmar_second_8p8um": dict(
        model_dir=HIVE_BASE / "multi_sample_mishmar_hanegev_maoz_3_5p85um_loess_i2" / "nnUNet_results" / "Dataset777_GCEF"
                   / "nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss__nnUNetPlans__3d_fullres",
        baseline_pore_pct=22.984,
        baseline_pom_pct=1.643,
    ),
}


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print(f"$ {' '.join(str(c) for c in cmd)}" + (f"  (cwd={cwd})" if cwd else ""))
    result = subprocess.run(cmd, cwd=str(cwd) if cwd else None)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed (exit {result.returncode}): {cmd}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--volume-key", required=True, choices=list(VOLUME_CONFIGS.keys()))
    args = parser.parse_args()
    key = args.volume_key
    cfg = VOLUME_CONFIGS[key]

    work_dir = RUN_DIR / "pipeline_work" / key
    work_dir.mkdir(parents=True, exist_ok=True)
    crop_dir = RUN_DIR / "raw_crops" / key
    assert crop_dir.exists() and list(crop_dir.glob("*.tif")), f"No exported crop slices at {crop_dir}"

    print(f"=== [{key}] Step 1/5: norm200 -> CUDA NLM (run_preprocess.py) ===")
    run([sys.executable, "run_preprocess.py", "--input_dir", str(crop_dir)], cwd=FILTERS_DIR)
    nlm_src = FILTERS_DIR / "nlm_output" / "nlm_volume.tif"
    assert nlm_src.exists(), f"Expected NLM output missing: {nlm_src}"

    nlm_export = work_dir / f"{key}_nlm.tif"
    shutil.copy2(nlm_src, nlm_export)
    print(f"[{key}] Copied NLM output to {nlm_export}")
    # Clean the shared scratch dirs so the next volume's run_preprocess.py
    # call doesn't get confused by stale outputs from this one.
    shutil.rmtree(FILTERS_DIR / "norm200_output", ignore_errors=True)
    shutil.rmtree(FILTERS_DIR / "nlm_output", ignore_errors=True)

    print(f"=== [{key}] Step 2/5: TIFF -> zscore-normalized NIfTI ===")
    nifti_dir = work_dir / "nifti_predict"
    nifti_dir.mkdir(exist_ok=True)
    vol = tifffile.imread(str(nlm_export)).astype(np.float32)
    mean, std = vol.mean(), vol.std()
    vol = (vol - mean) / (std + 1e-8)
    vol = vol.transpose(2, 1, 0)  # (Z,Y,X) -> (X,Y,Z) for nibabel, matching the notebook convention
    nifti_path = nifti_dir / f"{key}_0000.nii.gz"
    nib.save(nib.Nifti1Image(vol, affine=np.eye(4)), str(nifti_path))
    print(f"[{key}] Saved {nifti_path}  shape={vol.shape}")
    del vol

    print(f"=== [{key}] Step 3/5: split into chunks for inference ===")
    split_dir = work_dir / "inference_input"
    split_dir.mkdir(exist_ok=True)
    run([
        sys.executable, str(NNUNET_DIR / "preprocessing_nnUNet_predict_split.py"),
        "-i", str(nifti_dir), "-o", str(split_dir), "-m", str(cfg["model_dir"]),
    ])

    print(f"=== [{key}] Step 4/5: nnUNet inference ===")
    pred_dir = work_dir / "inference_output"
    pred_dir.mkdir(exist_ok=True)
    _run_inference(cfg["model_dir"], split_dir, pred_dir)

    print(f"=== [{key}] Step 5/5: concatenate chunks ===")
    concat_dir = work_dir / "inference_concatenated"
    concat_dir.mkdir(exist_ok=True)
    run([sys.executable, str(CONCAT_SCRIPT), "-i", str(pred_dir), "-o", str(concat_dir)])
    concat_path = concat_dir / f"{key}.nii.gz"
    assert concat_path.exists(), f"Missing concatenated output: {concat_path}"
    print(f"[{key}] DONE -- concatenated segmentation: {concat_path} "
          f"({concat_path.stat().st_size / 1e6:.1f} MB)")

    print(f"=== [{key}] Sanity check: pore/POM voxel fractions vs existing-crop baseline ===")
    seg = np.asarray(nib.load(str(concat_path)).dataobj)
    n_total = seg.size
    pore_pct = 100.0 * np.sum(seg == PORE_LABEL) / n_total
    pom_pct = 100.0 * np.sum(seg == POM_LABEL) / n_total
    baseline_pore = cfg["baseline_pore_pct"]
    baseline_pom = cfg["baseline_pom_pct"]

    pore_collapsed = pore_pct < POM_COLLAPSE_FLOOR_PCT or pore_pct < 0.3 * baseline_pore
    pom_collapsed = pom_pct < POM_COLLAPSE_FLOOR_PCT or pom_pct < 0.3 * baseline_pom
    channel_collapse = pore_collapsed or pom_collapsed

    sanity = {
        "volume_key": key,
        "crop_shape": list(seg.shape),
        "n_total_voxels": int(n_total),
        "new_pore_voxel_fraction_pct": float(pore_pct),
        "new_pom_voxel_fraction_pct": float(pom_pct),
        "baseline_pore_voxel_fraction_pct": baseline_pore,
        "baseline_pom_voxel_fraction_pct": baseline_pom,
        "collapse_floor_pct": POM_COLLAPSE_FLOOR_PCT,
        "pore_collapsed": bool(pore_collapsed),
        "pom_collapsed": bool(pom_collapsed),
        "channel_collapse_detected": bool(channel_collapse),
        "concat_path": str(concat_path),
    }
    with (RUN_DIR / f"sanity_check_{key}.json").open("w", encoding="utf-8") as fh:
        json.dump(sanity, fh, indent=2)
    print(json.dumps(sanity, indent=2))
    if channel_collapse:
        print(f"[{key}] !!! CHANNEL COLLAPSE DETECTED -- discard enlarged crop, fall back to existing crop !!!")
    else:
        print(f"[{key}] Sanity check PASSED -- enlarged crop is usable.")


def _run_inference(model_dir: Path, split_dir: Path, pred_dir: Path) -> None:
    import torch

    _orig_load = torch.load
    def _patched(f, *a, **kw):
        kw.setdefault("weights_only", False)
        return _orig_load(f, *a, **kw)
    torch.load = _patched

    from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor

    fold_dir = model_dir / "fold_0"
    ckpt = "checkpoint_final.pth" if (fold_dir / "checkpoint_final.pth").exists() else "checkpoint_best.pth"
    print(f"Checkpoint: {ckpt}  CUDA: {torch.cuda.is_available()}")

    import gc
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    gc.collect()

    predictor = nnUNetPredictor(
        tile_step_size=0.5, use_gaussian=True, use_mirroring=False,
        perform_everything_on_device=False,
        device=torch.device("cuda" if torch.cuda.is_available() else "cpu"),
        verbose=True, allow_tqdm=True,
    )
    predictor.initialize_from_trained_model_folder(str(model_dir), use_folds=(0,), checkpoint_name=ckpt)
    predictor.predict_from_files(
        str(split_dir), str(pred_dir),
        save_probabilities=False, overwrite=True,
        num_processes_preprocessing=1, num_processes_segmentation_export=1,
        folder_with_segs_from_prev_stage=None, num_parts=1, part_id=0,
    )
    del predictor
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
