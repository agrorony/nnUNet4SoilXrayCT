"""Build and segment `bnei_reem_samp_2_0_true_recon` — the CORRECTED pipeline
for Bnei Re'em Specimen B, using the real tomographic reconstruction.

Background (see bnei_reem_specB_visual_evidence/part0b_CRITICAL_CORRECTION.md
and part0c_TRUE_RECONSTRUCTION_RESULTS.md): `bnei_reem_samp_2_0_recropped`
(built by run_bnei_reem_samp_2_0_recrop_pipeline.py) was retroactively found
to have been built from 1800 raw ROTATIONAL PROJECTION images (896x1344,
compressed value range, no true zero) matching the raw folder's top-level
filename pattern, NOT from a reconstructed depth volume. Those projections
were mistaken for depth slices because the driver script's filename regex
matched them.

The REAL reconstruction was located on this machine's local E: drive (NOT
the network share's identically-named `_Rec` folder, which is stale and
holds only single-slice parameter-tuning previews):

    E:\\PROJECTS\\Yael_Mishael\\Rony\\18.12.25 bnei_reem_samp_2.0\\
        bnei_reem_highkV_cu011_samp_2.0_Rec\\

804 sequential real reconstructed slices, filenames
`bnei_reem_highkV_cu011_samp_2.0_rec00000049.tif` .. `..._rec00000852.tif`
(indices 49-852, zero gaps), shape (1344, 1344), dtype uint16, full dynamic
range to 65535 -- consistent with genuine CT density reconstruction and
clearly distinct from the projections' (896, 1344) shape / compressed range.

This script follows the SAME crop/norm200/NLM convention as every other
Bnei Re'em volume in this project (crop_size 650, matching canonical
nlm_volume.tif's 650x650x651-652 convention), pointed at the real
reconstruction instead of the projections. The only deliberate deviation
from run_bnei_reem_samp_2_0_recrop_pipeline.py is the final tif->NIfTI
normalization step: instead of that script's `noNorm` passthrough (norm200
output is already float32 [0,1], so nifti conversion was a no-op), this
script replicates canonical Bnei Re'em's own normalization convention --
global mean/std z-score applied to the NLM-denoised volume, exactly as done
inline in colab_nnUNet_pipeline.ipynb's inference-data-prep cell (search
"zscore norm" in that notebook):

    vol = tifffile.imread(...).astype(np.float32)
    mean, std = vol.mean(), vol.std()
    vol = (vol - mean) / (std + 1e-8)
    vol = vol.transpose(2, 1, 0)  # (Z, Y, X) -> (X, Y, Z) for nibabel

This exact formula is independently corroborated by this repo's own
preprocessing_nnUNet_predict.py / preprocessing_nnUNet_train.py:img_normalize
`zscore` branch: `(img - mean) / max(std, 1e-8)` -- the same global-statistics
z-score, modulo a negligible max() vs +epsilon difference. Two independent
code paths computing the identical formula is treated here as a confirmed
replication of canonical's normalization convention, not a guessed fallback.

Does NOT touch bnei_reem_samp_2_0_recropped (which stays as the retracted,
invalid-input run) or bnei_reem_samp_2_0 -- all paths here are new, suffixed
`_true_recon`.
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
RAW_DIR = Path(
    r"E:\PROJECTS\Yael_Mishael\Rony\18.12.25 bnei_reem_samp_2.0"
    r"\bnei_reem_highkV_cu011_samp_2.0_Rec"
)
NEW_SAMPLE_ID = "bnei_reem_samp_2_0_true_recon"
CROP_SIZE = 650  # matches canonical Bnei Re'em nlm_volume.tif (650x650x651-652)
EXPECTED_SLICES = 804  # real reconstructed slices, indices 49-852, zero gaps

SLICE_RE = re.compile(r"^bnei_reem_highkV_cu011_samp_2\.0_rec\d{8}\.tif$")

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


def _describe(img: np.ndarray, label: str) -> None:
    print(f"  {label}: shape={img.shape} dtype={img.dtype} "
          f"min={img.min()} max={img.max()} mean={img.mean():.1f}", flush=True)


def step1_crop() -> None:
    if LOCAL_CROP_DIR.exists() and len(list(LOCAL_CROP_DIR.glob("*.tif"))) == CROP_SIZE:
        print(f"[1/5] SKIP (already cropped): {LOCAL_CROP_DIR}", flush=True)
        return

    all_files = sorted(RAW_DIR.glob("*.tif"))
    real_slices = [p for p in all_files if SLICE_RE.match(p.name)]
    print(f"[1/5] raw recon folder: {len(all_files)} .tif files total, {len(real_slices)} real "
          f"numbered reconstructed slices ({len(all_files) - len(real_slices)} excluded: "
          f"parameter-preview/aux files)", flush=True)
    if len(real_slices) != EXPECTED_SLICES:
        raise RuntimeError(f"Expected exactly {EXPECTED_SLICES} real slices, found {len(real_slices)}")

    # contiguity check
    idxs = [int(re.search(r"(\d{8})\.tif$", p.name).group(1)) for p in real_slices]
    if idxs != list(range(idxs[0], idxs[0] + len(idxs))):
        raise RuntimeError("Real slice indices are not contiguous -- aborting.")
    print(f"[1/5] index range confirmed contiguous: {idxs[0]}-{idxs[-1]} ({len(idxs)} slices)", flush=True)

    z_start = (len(real_slices) // 2) - (CROP_SIZE // 2)
    z_end = z_start + CROP_SIZE
    selected = real_slices[z_start:z_end]
    orig_idx_first = idxs[z_start]
    orig_idx_last = idxs[z_end - 1]
    print(f"[1/5] Z crop: sorted-list positions [{z_start}:{z_end}] of {len(real_slices)} (centered) "
          f"-> original file index range {orig_idx_first}-{orig_idx_last}", flush=True)

    first_raw = tifffile.imread(str(selected[0]))
    mid_raw = tifffile.imread(str(selected[len(selected) // 2]))
    last_raw = tifffile.imread(str(selected[-1]))
    print("[1/5] pre-crop sanity (first/mid/last of the 650 selected slices):", flush=True)
    _describe(first_raw, "first")
    _describe(mid_raw, "mid")
    _describe(last_raw, "last")

    h, w = first_raw.shape
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
        if i == 0:
            _describe(cropped, "post-crop first")
        if i == len(selected) // 2:
            _describe(cropped, "post-crop mid")
        if i == len(selected) - 1:
            _describe(cropped, "post-crop last")
        if i % 200 == 0:
            print(f"[1/5]   wrote {i}/{CROP_SIZE}", flush=True)

    print(f"[1/5] Cropped {CROP_SIZE}^3 volume written to {LOCAL_CROP_DIR}", flush=True)


def step2_norm_nlm() -> None:
    # nlm_output/nlm_volume.tif is a SHARED scratch slot reused by every
    # run_preprocess.py invocation -- always regenerate, never trust a
    # shape-only existence check (see run_bnei_reem_samp_2_0_recrop_pipeline.py
    # for the 2026-08-24 incident this guards against).
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


def _zscore_tif_to_nifti() -> Path:
    """Replicate canonical Bnei Re'em's exact normalization convention
    (colab_nnUNet_pipeline.ipynb inference-data-prep cell): global mean/std
    z-score on the NLM-denoised volume, transpose (Z,Y,X)->(X,Y,Z), save
    NIfTI with identity affine. This REPLACES Specimen B's original invalid
    `noNorm` passthrough (preprocessing_nnUNet_predict_tif_direct.py).
    """
    import nibabel as nib

    out_path = NIFTI_PREDICT_DIR / f"{NEW_SAMPLE_ID}_0000.nii.gz"
    if out_path.exists():
        print(f"[4/5] SKIP zscore nifti (already exists): {out_path}", flush=True)
        return out_path

    NIFTI_PREDICT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[4/5] Reading NLM volume for z-score normalization: {NETWORK_TIF}", flush=True)
    vol = tifffile.imread(str(NETWORK_TIF)).astype(np.float32)
    mean, std = float(vol.mean()), float(vol.std())
    print(f"[4/5] pre-zscore stats: shape={vol.shape} min={vol.min():.5f} max={vol.max():.5f} "
          f"mean={mean:.5f} std={std:.5f}", flush=True)
    vol = (vol - mean) / (std + 1e-8)
    print(f"[4/5] post-zscore stats: min={vol.min():.4f} max={vol.max():.4f} mean={vol.mean():.6f} "
          f"std={vol.std():.4f}", flush=True)
    vol = vol.transpose(2, 1, 0)  # (Z, Y, X) -> (X, Y, Z) for nibabel, matches canonical convention
    nib.save(nib.Nifti1Image(vol, affine=np.eye(4)), str(out_path))
    print(f"[4/5] Saved: {out_path}  shape={vol.shape}", flush=True)
    return out_path


def step4_tif_to_nifti_and_split(splits: int) -> None:
    _zscore_tif_to_nifti()

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
