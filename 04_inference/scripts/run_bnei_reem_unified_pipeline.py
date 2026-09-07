r"""Unified Bnei Re'em two-specimen pipeline — ONE script, ONE code path.

Puts BOTH Bnei Re'em specimens through the *identical* existing pipeline,
raw reconstruction -> structural metrics, so that any difference in the
resulting numbers is attributable to the specimens and not to the
processing.

This is a straight parameterization of
``run_bnei_reem_samp_2_0_true_recon_pipeline.py`` over two volumes. The
steps, their order, and every parameter are byte-identical between the two
specimens. The ONLY per-volume differences are the four entries in
``VOLUMES`` below: input folder, slice-filename regex, output sample ID,
and voxel spacing.

    Specimen A: C:\Users\rony.schwartz\Desktop\new_rec
                voxel 15.000149 um
    Specimen B: \\HIVE3065\Yael_Mishael\Rony\18.12.25 bnei_reem_samp_2.0
                \bnei_reem_highkV_cu011_samp_2.0_Rec
                voxel 15.034357 um

Why this rerun exists
---------------------
The previous Specimen B run (``bnei_reem_samp_2_0_true_recon``) produced
structural metrics essentially identical to Specimen A's (pore fraction
21.6403% vs 21.636%, Gamma 0.8593 vs 0.8594, DA 0.0967 vs 0.0983). A
follow-up identity check found Pearson r = 0.9999 between the two z-scored
input volumes and pore-label Dice = 0.988 between the two segmentations —
i.e. the two "different specimens" were, at the point of segmentation, the
same data. Two genuinely different Bnei Re'em reconstructions correlate at
roughly r ~ 0.58; the raw center-crops of these two folders correlate at
r ~ 0.00, so the source data is unambiguously different and the collapse
happened inside the pipeline.

TWO HAZARDS, HANDLED EXPLICITLY
-------------------------------
1. ``02_preprocessing/filters/nlm_output/nlm_volume.tif`` is a SHARED
   SCRATCH SLOT. Every ``run_preprocess.py`` invocation in this repo writes
   that exact path (likewise ``norm200_output/norm200_volume.tif``). This is
   the near-certain cause of the r=0.9999 collapse: if volume 2's NLM result
   is read after volume 1 has overwritten the slot -- or if volume 2's
   preprocess is skipped and volume 1's leftover file is read -- both
   specimens end up carrying the same voxels.

   Mitigation here, belt and braces:
     * the two volumes are processed STRICTLY SEQUENTIALLY, never in
       parallel;
     * both scratch slots are DELETED immediately before each
       ``run_preprocess.py`` call, so a stale file cannot be silently
       inherited;
     * the freshly written ``nlm_volume.tif`` is copied out to a
       per-specimen path BEFORE the next specimen is started;
     * an MD5 of every copied-out volume is recorded and asserted DISTINCT
       from every previously processed specimen's, which aborts the run
       immediately rather than producing another pair of identical results.

2. SKIP GUARDS. Every ``if <output>.exists(): SKIP`` short-circuit from the
   parent script has been DELETED. Nothing is reused from a prior run;
   every stage recomputes and overwrites. The sample IDs are fresh
   (``bnei_reem_specA_unified`` / ``bnei_reem_specB_unified``) and no path
   here collides with ``bnei_reem_samp_2_0``,
   ``bnei_reem_samp_2_0_recropped`` or ``bnei_reem_samp_2_0_true_recon``.

Stages
------
  A. Per specimen, sequentially (venv-napari python, CUDA):
       verify -> step1_crop (center 650^3) -> run_preprocess.py
       (norm200 + CUDA NLM) -> copy NLM out -> _zscore_tif_to_nifti ->
       split -> run_inference.py (multi_sample_fresh_bnei_reem_i4,
       nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss_lowlr)
  B. IDENTITY CHECK (gating): Pearson r between the two z-scored
       ``_0000.nii.gz`` arrays, and pore-label Dice between the two
       segmentations. If either lands near the previous failure's values
       (r ~ 0.99 / Dice ~ 0.99) the run STOPS here and stage C is not
       executed -- the metrics would be meaningless.
  C. Analysis, per specimen (D:\Anaconda python):
       run_psd_diagnostics.py extended --pore-label 5 --pom-label 2 3
       --n-anisotropy-directions 800 --no-tortuosity (tortuosity costs
       ~15 h/volume and returns NaN on axis0 here anyway), then
       pore_metrics_research/compute_chi_r_sweep.py.
  D. Report: bnei_reem_unified_pipeline_results.md, written to the repo
       root and to the network drive.

Usage
-----
    <venv-napari python> run_bnei_reem_unified_pipeline.py [--gpu 0]
        [--splits 4] [--stage all|A|B|C|D]

Stage A must run under the CUDA env (``PY_CUDA``); stage C is dispatched as
a subprocess under ``PY_TOPO`` automatically, so a single invocation of this
script under venv-napari runs everything.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import tifffile

# ===========================================================================
# Fixed layout / shared constants (IDENTICAL for both specimens)
# ===========================================================================
REPO_DIR = Path(__file__).resolve().parents[2]
FILTERS_DIR = REPO_DIR / "02_preprocessing" / "filters"
NNUNET_DIR = REPO_DIR / "02_preprocessing" / "nnunet"
SCRIPTS_DIR = REPO_DIR / "04_inference" / "scripts"
PSD_DIR = REPO_DIR / "05_evaluation" / "psd"

HIVE_BASE = Path(r"\\hive3065\Yael_Mishael\Rony\remote_computer backup")
TOPOLOGY_ROOT = HIVE_BASE / "Topology_Metrics_Aug2026"
PSD_OUTPUT_ROOT = TOPOLOGY_ROOT / "raw"
CHI_OUTPUT_DIR = TOPOLOGY_ROOT / "connectivity_function"

# Interpreters (per the task spec).
PY_CUDA = Path(r"C:\Users\rony.schwartz\.conda\envs\venv-napari\python.exe")
PY_TOPO = Path(r"D:\Anaconda\python.exe")

CROP_SIZE = 650            # canonical Bnei Re'em convention (650x650x650)
EXPECTED_SLICES = 804      # both specimens: reconstructed indices 49-852
EXPECTED_SLICE_SHAPE = (1344, 1344)
PORE_LABEL = 5             # dataset.json: Pore
POM_LABELS = [2, 3]        # dataset.json: POM_type1, POM_type2
N_ANISOTROPY_DIRECTIONS = 800

MODEL_DIR = (
    HIVE_BASE / "nnUNet_resources" / "multi_sample_fresh_bnei_reem_i4"
    / "nnUNet_results" / "Dataset777_GCEF"
    / "nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss_lowlr__nnUNetPlans__3d_fullres"
)
TRAINER_NAME = "nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss_lowlr"
ITERATION_NAME = "fresh_bnei_reem_i4"

# The SHARED scratch slots that caused the previous collapse.
SHARED_NLM_TIF = FILTERS_DIR / "nlm_output" / "nlm_volume.tif"
SHARED_NORM200_TIF = FILTERS_DIR / "norm200_output" / "norm200_volume.tif"

# Identity-check thresholds.
COLLAPSE_R_THRESHOLD = 0.95      # previous failure: 0.9999
COLLAPSE_DICE_THRESHOLD = 0.95   # previous failure: 0.988
BASELINE_DIFFERENT_R = 0.58      # two genuinely different Bnei Re'em recons

STATE_PATH = HIVE_BASE / "nnUNet_resources" / "_bnei_reem_unified_state.json"
REPORT_NAME = "bnei_reem_unified_pipeline_results.md"


# ===========================================================================
# The ONLY per-volume differences allowed.
# ===========================================================================
VOLUMES: List[Dict[str, Any]] = [
    {
        "key": "A",
        "label": "Specimen A",
        "sample_id": "bnei_reem_specA_unified",
        "raw_dir": Path(r"C:\Users\rony.schwartz\Desktop\new_rec"),
        "slice_regex": r"^bnei_reem_highkV_cu011_samp_2_rec\d{8}\.tif$",
        "voxel_spacing_um": 15.000149,
    },
    {
        "key": "B",
        "label": "Specimen B",
        "sample_id": "bnei_reem_specB_unified",
        "raw_dir": Path(
            r"\\HIVE3065\Yael_Mishael\Rony\18.12.25 bnei_reem_samp_2.0"
            r"\bnei_reem_highkV_cu011_samp_2.0_Rec"
        ),
        # Documented fallback, used ONLY if the network _Rec copy turns out to
        # be preview-only. Never substituted silently: `raw_dir_used` in the
        # state file and the report records which copy was actually read.
        "raw_dir_fallback": Path(
            r"E:\PROJECTS\Yael_Mishael\Rony\18.12.25 bnei_reem_samp_2.0"
            r"\bnei_reem_highkV_cu011_samp_2.0_Rec"
        ),
        "slice_regex": r"^bnei_reem_highkV_cu011_samp_2\.0_rec\d{8}\.tif$",
        "voxel_spacing_um": 15.034357,
    },
]


def paths_for(vol: Dict[str, Any]) -> Dict[str, Path]:
    """Derive every per-specimen path from its sample_id (same rule for both)."""
    sid = vol["sample_id"]
    base = HIVE_BASE / "nnUNet_resources" / sid
    return {
        "crop_dir": FILTERS_DIR / "_tmp_center_crop" / sid,
        "nlm_tif": HIVE_BASE / "10.5" / f"{sid}.tif",
        "sample_base": base,
        "nifti_predict": base / "nifti_predict",
        "split_dir": base / "inference_input",
        "pred_dir": base / "inference_output",
        "concat_dir": base / "inference_concatenated",
        "concat_file": base / "inference_concatenated" / f"{sid}.nii.gz",
        "zscore_nifti": base / "nifti_predict" / f"{sid}_0000.nii.gz",
    }


# ===========================================================================
# Small helpers
# ===========================================================================
def log(msg: str = "") -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def banner(msg: str) -> None:
    print(f"\n{'=' * 78}\n{msg}\n{'=' * 78}", flush=True)


def _run(cmd: List[Any], step: str, cwd: Path) -> None:
    banner(f"[{step}] {' '.join(str(c) for c in cmd)}")
    t0 = time.time()
    result = subprocess.run([str(c) for c in cmd], cwd=str(cwd))
    dt = time.time() - t0
    if result.returncode != 0:
        raise RuntimeError(f"[{step}] failed with returncode {result.returncode} after {dt/60:.1f} min")
    log(f"[{step}] OK ({dt/60:.1f} min)")


def _describe(img: np.ndarray, label: str) -> None:
    log(f"    {label}: shape={img.shape} dtype={img.dtype} "
        f"min={img.min()} max={img.max()} mean={float(img.mean()):.1f}")


def _md5_file(path: Path, chunk: int = 1 << 22) -> str:
    h = hashlib.md5()
    with path.open("rb") as fh:
        while True:
            b = fh.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def load_state() -> Dict[str, Any]:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_state(state: Dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")


# ===========================================================================
# STAGE A0 — verify the raw reconstruction stack
# ===========================================================================
def verify_volume(vol: Dict[str, Any]) -> Dict[str, Any]:
    """Confirm the folder holds a real reconstruction stack: 1344x1344, uint16,
    range reaching 65535, contiguous slice indices. Returns a verification
    record. If the primary folder is preview-only (no full numbered rec
    stack) and a fallback is configured, the fallback is used and that
    substitution is recorded loudly -- never silently."""
    banner(f"[VERIFY] {vol['label']} ({vol['sample_id']})")
    rx = re.compile(vol["slice_regex"])

    candidates = [("primary", vol["raw_dir"])]
    if vol.get("raw_dir_fallback"):
        candidates.append(("fallback_local", vol["raw_dir_fallback"]))

    chosen = None
    attempts = []
    for tag, d in candidates:
        if not d.exists():
            attempts.append({"tag": tag, "dir": str(d), "status": "MISSING"})
            log(f"  {tag}: {d} -> MISSING")
            continue
        all_tifs = sorted(d.glob("*.tif"))
        matching = [p for p in all_tifs if rx.match(p.name)]
        log(f"  {tag}: {d}")
        log(f"    {len(all_tifs)} .tif total, {len(matching)} matching the slice regex "
            f"({len(all_tifs) - len(matching)} excluded: preview/param-tuning/aux files)")
        attempts.append({"tag": tag, "dir": str(d), "status": "OK" if matching else "NO_MATCHING_SLICES",
                         "n_tif_total": len(all_tifs), "n_matching": len(matching)})
        if matching and chosen is None:
            chosen = (tag, d, all_tifs, matching)

    if chosen is None:
        raise RuntimeError(
            f"{vol['label']}: no folder yielded slices matching {vol['slice_regex']!r}. "
            f"Attempts: {attempts}"
        )

    tag, raw_dir, all_tifs, matching = chosen
    if tag != "primary":
        log("")
        log("  *** SUBSTITUTION NOTICE ***")
        log(f"  The specified folder {vol['raw_dir']} is preview-only / unusable;")
        log(f"  reading the identically-named local copy instead: {raw_dir}")
        log("  *** This substitution is recorded in the state file and the report. ***")
        log("")

    if len(matching) != EXPECTED_SLICES:
        raise RuntimeError(
            f"{vol['label']}: expected {EXPECTED_SLICES} reconstructed slices, found {len(matching)}")

    idxs = [int(re.search(r"(\d{8})\.tif$", p.name).group(1)) for p in matching]
    contiguous = idxs == list(range(idxs[0], idxs[0] + len(idxs)))
    if not contiguous:
        raise RuntimeError(f"{vol['label']}: slice indices are NOT contiguous -- aborting.")
    log(f"    index range {idxs[0]}-{idxs[-1]}, contiguous=True, {len(idxs)} slices")

    probes = {}
    for lbl, p in (("first", matching[0]), ("mid", matching[len(matching) // 2]),
                   ("last", matching[-1])):
        img = tifffile.imread(str(p))
        _describe(img, f"{lbl} ({p.name})")
        if tuple(img.shape) != EXPECTED_SLICE_SHAPE:
            raise RuntimeError(f"{vol['label']}: {p.name} shape {img.shape} != {EXPECTED_SLICE_SHAPE}")
        if img.dtype != np.uint16:
            raise RuntimeError(f"{vol['label']}: {p.name} dtype {img.dtype} != uint16")
        probes[lbl] = {"name": p.name, "shape": list(img.shape), "dtype": str(img.dtype),
                       "min": int(img.min()), "max": int(img.max()), "mean": float(img.mean())}

    reaches_full_range = any(pr["max"] == 65535 for pr in probes.values())
    if not reaches_full_range:
        raise RuntimeError(
            f"{vol['label']}: no probed slice reaches 65535 -- not a full-range uint16 "
            f"reconstruction (maxima: {[pr['max'] for pr in probes.values()]})")
    log(f"    dtype uint16, shape {EXPECTED_SLICE_SHAPE}, dynamic range reaches 65535: VERIFIED")

    record = {
        "label": vol["label"],
        "sample_id": vol["sample_id"],
        "raw_dir_specified": str(vol["raw_dir"]),
        "raw_dir_used": str(raw_dir),
        "used_fallback": tag != "primary",
        "slice_regex": vol["slice_regex"],
        "voxel_spacing_um": vol["voxel_spacing_um"],
        "n_tif_total": len(all_tifs),
        "n_matching_slices": len(matching),
        "n_excluded": len(all_tifs) - len(matching),
        "index_first": idxs[0],
        "index_last": idxs[-1],
        "contiguous": contiguous,
        "slice_shape": list(EXPECTED_SLICE_SHAPE),
        "dtype": "uint16",
        "reaches_65535": reaches_full_range,
        "probes": probes,
        "attempts": attempts,
    }
    vol["_raw_dir_used"] = raw_dir
    vol["_matching"] = matching
    return record


# ===========================================================================
# STAGE A1 — center 650^3 crop  (no SKIP guard)
# ===========================================================================
def step1_crop(vol: Dict[str, Any]) -> Dict[str, Any]:
    P = paths_for(vol)
    crop_dir = P["crop_dir"]
    matching = vol["_matching"]
    banner(f"[A1 crop] {vol['label']} -> {crop_dir}")

    idxs = [int(re.search(r"(\d{8})\.tif$", p.name).group(1)) for p in matching]
    z_start = (len(matching) // 2) - (CROP_SIZE // 2)
    z_end = z_start + CROP_SIZE
    selected = matching[z_start:z_end]
    log(f"  Z crop: sorted positions [{z_start}:{z_end}] of {len(matching)} (centered) "
        f"-> original file indices {idxs[z_start]}-{idxs[z_end - 1]}")

    first_raw = tifffile.imread(str(selected[0]))
    h, w = first_raw.shape
    y_start = (h - CROP_SIZE) // 2
    x_start = (w - CROP_SIZE) // 2
    log(f"  XY crop: ({h},{w}) -> [{y_start}:{y_start + CROP_SIZE}, {x_start}:{x_start + CROP_SIZE}]")

    # No SKIP guard: always rebuild from scratch.
    if crop_dir.exists():
        log(f"  removing pre-existing crop dir (no reuse): {crop_dir}")
        shutil.rmtree(crop_dir)
    crop_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    for i, src in enumerate(selected):
        img = tifffile.imread(str(src))
        if img.shape != (h, w):
            raise ValueError(f"Unexpected shape change in {src.name}: {img.shape} vs {(h, w)}")
        cropped = img[y_start:y_start + CROP_SIZE, x_start:x_start + CROP_SIZE]
        tifffile.imwrite(str(crop_dir / f"slice_{i:06d}.tif"), cropped)
        if i == 0:
            _describe(cropped, "post-crop first")
        elif i == len(selected) // 2:
            _describe(cropped, "post-crop mid")
        elif i == len(selected) - 1:
            _describe(cropped, "post-crop last")
        if i % 200 == 0 and i:
            log(f"  wrote {i}/{CROP_SIZE}")
    n_written = len(list(crop_dir.glob("*.tif")))
    if n_written != CROP_SIZE:
        raise RuntimeError(f"{vol['label']}: crop wrote {n_written} slices, expected {CROP_SIZE}")
    log(f"  cropped {CROP_SIZE}^3 volume written ({time.time() - t0:.0f}s, {n_written} slices)")

    return {
        "crop_dir": str(crop_dir),
        "z_positions": [z_start, z_end],
        "z_original_indices": [idxs[z_start], idxs[z_end - 1]],
        "xy_offsets": [y_start, x_start],
        "n_slices_written": n_written,
    }


# ===========================================================================
# STAGE A2 — norm200 + CUDA NLM  (SHARED SCRATCH SLOT — handled)
# ===========================================================================
def step2_norm_nlm_and_export(vol: Dict[str, Any], seen_md5: Dict[str, str]) -> Dict[str, Any]:
    P = paths_for(vol)
    banner(f"[A2 norm200+NLM] {vol['label']}")

    # HAZARD 1 mitigation: purge both shared scratch slots so a stale volume
    # from a previous specimen (or a previous session) cannot be inherited.
    for slot in (SHARED_NLM_TIF, SHARED_NORM200_TIF):
        if slot.exists():
            log(f"  purging shared scratch slot before run: {slot}")
            slot.unlink()
    if SHARED_NLM_TIF.exists():
        raise RuntimeError(f"Could not clear shared scratch slot {SHARED_NLM_TIF}")

    t_start = time.time()
    _run([PY_CUDA, "run_preprocess.py", "--input_dir", P["crop_dir"]],
         f"A2 norm200+NLM {vol['key']}", FILTERS_DIR)

    if not SHARED_NLM_TIF.exists():
        raise RuntimeError(f"run_preprocess.py did not produce {SHARED_NLM_TIF}")
    mtime = SHARED_NLM_TIF.stat().st_mtime
    if mtime < t_start:
        raise RuntimeError(
            f"{SHARED_NLM_TIF} was NOT rewritten by this run (mtime {mtime} < start {t_start}) "
            "-- stale shared-scratch-slot content, aborting.")
    log(f"  freshness verified: nlm_volume.tif mtime is after this run's start")

    # Copy the result OUT to a per-specimen path before anything else runs.
    P["nlm_tif"].parent.mkdir(parents=True, exist_ok=True)
    if P["nlm_tif"].exists():
        log(f"  removing pre-existing per-specimen NLM export (no reuse): {P['nlm_tif']}")
        P["nlm_tif"].unlink()
    log(f"  copying {SHARED_NLM_TIF} -> {P['nlm_tif']}")
    shutil.copy2(SHARED_NLM_TIF, P["nlm_tif"])

    md5 = _md5_file(P["nlm_tif"])
    log(f"  NLM volume MD5: {md5}")
    for other_sid, other_md5 in seen_md5.items():
        if other_md5 == md5:
            raise RuntimeError(
                f"COLLAPSE DETECTED: {vol['sample_id']}'s NLM volume is byte-identical to "
                f"{other_sid}'s (MD5 {md5}). The shared nlm_volume.tif scratch slot has "
                "produced duplicate data again -- aborting before any metrics are computed.")
    seen_md5[vol["sample_id"]] = md5

    arr = tifffile.imread(str(P["nlm_tif"]))
    log(f"  NLM volume: shape={arr.shape} dtype={arr.dtype} min={arr.min():.5f} "
        f"max={arr.max():.5f} mean={arr.mean():.5f} std={arr.std():.5f}")
    if tuple(arr.shape) != (CROP_SIZE, CROP_SIZE, CROP_SIZE):
        raise RuntimeError(f"NLM volume shape {arr.shape} != {(CROP_SIZE,) * 3}")

    return {
        "nlm_tif": str(P["nlm_tif"]),
        "md5": md5,
        "shape": list(arr.shape),
        "dtype": str(arr.dtype),
        "min": float(arr.min()), "max": float(arr.max()),
        "mean": float(arr.mean()), "std": float(arr.std()),
    }


# ===========================================================================
# STAGE A3 — z-score -> NIfTI  (no SKIP guard)
# ===========================================================================
def step3_zscore_tif_to_nifti(vol: Dict[str, Any]) -> Dict[str, Any]:
    """Canonical Bnei Re'em normalization: global mean/std z-score on the
    NLM-denoised volume, transpose (Z,Y,X)->(X,Y,Z), identity affine.
    Identical formula for both specimens."""
    import nibabel as nib

    P = paths_for(vol)
    banner(f"[A3 zscore->NIfTI] {vol['label']}")
    P["nifti_predict"].mkdir(parents=True, exist_ok=True)
    out_path = P["zscore_nifti"]
    if out_path.exists():
        log(f"  removing pre-existing NIfTI (no reuse): {out_path}")
        out_path.unlink()

    v = tifffile.imread(str(P["nlm_tif"])).astype(np.float32)
    mean, std = float(v.mean()), float(v.std())
    log(f"  pre-zscore : shape={v.shape} min={v.min():.5f} max={v.max():.5f} "
        f"mean={mean:.5f} std={std:.5f}")
    v = (v - mean) / (std + 1e-8)
    log(f"  post-zscore: min={v.min():.4f} max={v.max():.4f} mean={v.mean():.6f} std={v.std():.4f}")
    v = v.transpose(2, 1, 0)  # (Z,Y,X) -> (X,Y,Z) for nibabel
    nib.save(nib.Nifti1Image(v, affine=np.eye(4)), str(out_path))
    log(f"  saved {out_path}  shape={v.shape}")
    return {"zscore_nifti": str(out_path), "pre_mean": mean, "pre_std": std,
            "shape": list(v.shape)}


# ===========================================================================
# STAGE A4 — split  (no SKIP guard)
# ===========================================================================
def step4_split(vol: Dict[str, Any], splits: int) -> Dict[str, Any]:
    P = paths_for(vol)
    banner(f"[A4 split] {vol['label']}")
    if P["split_dir"].exists():
        log(f"  removing pre-existing split dir (no reuse): {P['split_dir']}")
        shutil.rmtree(P["split_dir"])
    P["split_dir"].mkdir(parents=True, exist_ok=True)
    _run([PY_CUDA, NNUNET_DIR / "preprocessing_nnUNet_predict_split.py",
          "-i", P["nifti_predict"], "-o", P["split_dir"],
          "-m", MODEL_DIR, "-s", str(splits), "-a", "2"],
         f"A4 split {vol['key']}", REPO_DIR)
    chunks = sorted(P["split_dir"].glob("*_0000.nii.gz"))
    if len(chunks) != splits:
        raise RuntimeError(f"{vol['label']}: split produced {len(chunks)} chunks, expected {splits}")
    log(f"  {len(chunks)} chunks written")
    return {"split_dir": str(P["split_dir"]), "n_chunks": len(chunks),
            "chunks": [c.name for c in chunks]}


# ===========================================================================
# STAGE A5 — inference  (no SKIP guard)
# ===========================================================================
def step5_inference(vol: Dict[str, Any], gpu: int) -> Dict[str, Any]:
    P = paths_for(vol)
    banner(f"[A5 inference] {vol['label']}")
    for d in (P["pred_dir"], P["concat_dir"]):
        if d.exists():
            log(f"  removing pre-existing dir (no reuse): {d}")
            shutil.rmtree(d)
        d.mkdir(parents=True, exist_ok=True)

    _run([PY_CUDA, SCRIPTS_DIR / "run_inference.py",
          "--iteration-name", ITERATION_NAME,
          "--sample-id", vol["sample_id"],
          "--trainer-name", TRAINER_NAME,
          "--gpu", str(gpu),
          "--model-dir", MODEL_DIR,
          "--input-dir", P["split_dir"],
          "--output-dir", P["pred_dir"],
          "--concat-dir", P["concat_dir"]],
         f"A5 inference {vol['key']}", REPO_DIR)

    if not P["concat_file"].exists():
        raise RuntimeError(f"{vol['label']}: missing concatenated prediction {P['concat_file']}")

    import nibabel as nib
    seg = np.asarray(nib.load(str(P["concat_file"])).dataobj)
    labels, counts = np.unique(seg, return_counts=True)
    total = int(seg.size)
    dist = {int(l): {"voxels": int(c), "fraction": float(c) / total}
            for l, c in zip(labels, counts)}
    pore_frac = float((seg == PORE_LABEL).sum()) / total
    pom_frac = float(np.isin(seg, POM_LABELS).sum()) / total
    log(f"  segmentation: shape={seg.shape} dtype={seg.dtype}")
    for l, d_ in sorted(dist.items()):
        log(f"    label {l}: {d_['voxels']:,} ({100 * d_['fraction']:.4f}%)")
    log(f"  pore fraction = {100 * pore_frac:.4f}%   POM fraction = {100 * pom_frac:.4f}%")
    return {"concat_file": str(P["concat_file"]), "shape": list(seg.shape),
            "label_distribution": dist, "pore_fraction": pore_frac, "pom_fraction": pom_frac}


# ===========================================================================
# STAGE A — one specimen end to end (called STRICTLY SEQUENTIALLY)
# ===========================================================================
def run_stage_a_for_volume(vol: Dict[str, Any], gpu: int, splits: int,
                           seen_md5: Dict[str, str], state: Dict[str, Any]) -> None:
    banner(f"STAGE A -- {vol['label']} ({vol['sample_id']}) -- START")
    t0 = time.time()
    rec: Dict[str, Any] = state.setdefault("volumes", {}).setdefault(vol["sample_id"], {})
    rec["label"] = vol["label"]
    rec["key"] = vol["key"]
    rec["voxel_spacing_um"] = vol["voxel_spacing_um"]

    rec["verification"] = verify_volume(vol)
    save_state(state)
    rec["crop"] = step1_crop(vol)
    save_state(state)
    rec["nlm"] = step2_norm_nlm_and_export(vol, seen_md5)
    save_state(state)
    rec["zscore"] = step3_zscore_tif_to_nifti(vol)
    save_state(state)
    rec["split"] = step4_split(vol, splits)
    save_state(state)
    rec["inference"] = step5_inference(vol, gpu)
    rec["stage_a_minutes"] = (time.time() - t0) / 60.0
    save_state(state)
    banner(f"STAGE A -- {vol['label']} -- DONE in {rec['stage_a_minutes']:.1f} min")


# ===========================================================================
# STAGE B — the mandatory identity check (GATING)
# ===========================================================================
def stage_b_identity_check(state: Dict[str, Any]) -> Dict[str, Any]:
    import nibabel as nib

    banner("STAGE B -- MANDATORY IDENTITY CHECK")
    a, b = VOLUMES[0], VOLUMES[1]
    PA, PB = paths_for(a), paths_for(b)

    log("Pearson correlation between the two z-scored _0000.nii.gz arrays:")
    va = np.asarray(nib.load(str(PA["zscore_nifti"])).dataobj, dtype=np.float64).ravel()
    vb = np.asarray(nib.load(str(PB["zscore_nifti"])).dataobj, dtype=np.float64).ravel()
    if va.shape != vb.shape:
        raise RuntimeError(f"z-scored volumes differ in shape: {va.shape} vs {vb.shape}")
    pearson = float(np.corrcoef(va, vb)[0, 1])
    identical_inputs = bool(np.array_equal(va, vb))
    log(f"  A: {PA['zscore_nifti']}  n={va.size:,}")
    log(f"  B: {PB['zscore_nifti']}  n={vb.size:,}")
    log(f"  Pearson r = {pearson:.6f}   byte-identical = {identical_inputs}")
    del va, vb

    log("Pore-label Dice between the two segmentations:")
    sa = np.asarray(nib.load(str(PA["concat_file"])).dataobj)
    sb = np.asarray(nib.load(str(PB["concat_file"])).dataobj)
    if sa.shape != sb.shape:
        raise RuntimeError(f"segmentations differ in shape: {sa.shape} vs {sb.shape}")
    ma, mb = (sa == PORE_LABEL), (sb == PORE_LABEL)
    inter = int(np.logical_and(ma, mb).sum())
    na, nb = int(ma.sum()), int(mb.sum())
    union = int(np.logical_or(ma, mb).sum())
    dice = (2.0 * inter / (na + nb)) if (na + nb) else float("nan")
    iou = (inter / union) if union else float("nan")
    total = int(sa.size)
    fa, fb = na / total, nb / total
    expected_dice = (2.0 * fa * fb / (fa + fb)) if (fa + fb) else float("nan")
    log(f"  pore voxels A = {na:,} ({100 * fa:.4f}%)   B = {nb:,} ({100 * fb:.4f}%)")
    log(f"  intersection = {inter:,}   union = {union:,}")
    log(f"  pore Dice = {dice:.6f}   IoU = {iou:.6f}")
    log(f"  Dice expected under independence (marginals) = {expected_dice:.6f}")
    seg_identical = bool(np.array_equal(sa, sb))
    log(f"  segmentations byte-identical = {seg_identical}")
    del sa, sb, ma, mb

    collapsed = bool(
        identical_inputs or seg_identical
        or (np.isfinite(pearson) and pearson >= COLLAPSE_R_THRESHOLD)
        or (np.isfinite(dice) and dice >= COLLAPSE_DICE_THRESHOLD)
    )
    result = {
        "pearson_r_zscored_inputs": pearson,
        "inputs_byte_identical": identical_inputs,
        "pore_dice": dice,
        "pore_iou": iou,
        "pore_voxels_A": na, "pore_voxels_B": nb,
        "pore_fraction_A": fa, "pore_fraction_B": fb,
        "intersection": inter, "union": union,
        "dice_expected_under_independence": expected_dice,
        "segmentations_byte_identical": seg_identical,
        "collapse_r_threshold": COLLAPSE_R_THRESHOLD,
        "collapse_dice_threshold": COLLAPSE_DICE_THRESHOLD,
        "baseline_different_specimen_r": BASELINE_DIFFERENT_R,
        "previous_failed_run": {"pearson_r": 0.9999, "pore_dice": 0.988},
        "collapsed": collapsed,
    }

    banner("IDENTITY-CHECK VERDICT: " + ("*** COLLAPSE -- DATA PROBLEM ***" if collapsed
                                         else "PASS -- the two volumes are genuinely different"))
    if collapsed:
        log("The two specimens are (near-)identical at the point of segmentation, exactly as in")
        log("the previous failed run. Structural metrics computed from this would be meaningless.")
        log("STOPPING before stage C. No metrics will be written up as results.")
    else:
        log(f"r = {pearson:.4f} (previous failure: 0.9999; genuinely-different baseline ~{BASELINE_DIFFERENT_R})")
        log(f"pore Dice = {dice:.4f} (previous failure: 0.988)")
    state["identity_check"] = result
    save_state(state)
    return result


# ===========================================================================
# STAGE C — PSD/topology + chi(r), per specimen (D:\Anaconda)
# ===========================================================================
def _latest_run_dir(sample_id: str, since: float) -> Path:
    cands = [d for d in PSD_OUTPUT_ROOT.glob(f"psd_diag_*_{sample_id}")
             if d.is_dir() and d.stat().st_mtime >= since - 5]
    if not cands:
        cands = [d for d in PSD_OUTPUT_ROOT.glob(f"psd_diag_*_{sample_id}") if d.is_dir()]
    if not cands:
        raise RuntimeError(f"No psd run dir found for {sample_id} under {PSD_OUTPUT_ROOT}")
    return sorted(cands, key=lambda d: d.name)[-1]


def stage_c_for_volume(vol: Dict[str, Any], state: Dict[str, Any]) -> None:
    P = paths_for(vol)
    sid = vol["sample_id"]
    vs = vol["voxel_spacing_um"]
    rec = state.setdefault("volumes", {}).setdefault(sid, {})
    banner(f"STAGE C -- {vol['label']} -- PSD/topology diagnostics")

    t0 = time.time()
    PSD_OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    _run([PY_TOPO, PSD_DIR / "run_psd_diagnostics.py", "extended",
          "--input", P["concat_file"],
          "--pore-label", str(PORE_LABEL),
          "--pom-label", *[str(v) for v in POM_LABELS],
          "--voxel-spacing", f"{vs}", f"{vs}", f"{vs}",
          "--output-root", PSD_OUTPUT_ROOT,
          "--run-name", sid,
          "--n-anisotropy-directions", str(N_ANISOTROPY_DIRECTIONS),
          "--no-tortuosity"],
         f"C1 psd {vol['key']}", PSD_DIR)

    run_dir = _latest_run_dir(sid, t0)
    log(f"  psd run dir: {run_dir}")
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    rec["psd_run_dir"] = str(run_dir)
    rec["psd_summary"] = summary
    rec["psd_minutes"] = (time.time() - t0) / 60.0
    save_state(state)

    banner(f"STAGE C -- {vol['label']} -- chi(r) crossover sweep")
    t1 = time.time()
    CHI_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    chi_csv = CHI_OUTPUT_DIR / f"chi_r_{sid}.csv"
    _run([PY_TOPO, PSD_DIR / "pore_metrics_research" / "compute_chi_r_sweep.py",
          "--input", P["concat_file"],
          "--pore-label", str(PORE_LABEL),
          "--voxel-size-um", f"{vs}",
          "--run-dir", run_dir,
          "--output-csv", chi_csv,
          "--run-label", sid],
         f"C2 chi(r) {vol['key']}", PSD_DIR / "pore_metrics_research")

    meta_path = chi_csv.with_suffix(".meta.json")
    rec["chi_csv"] = str(chi_csv)
    rec["chi_meta"] = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else None
    rec["chi_minutes"] = (time.time() - t1) / 60.0
    save_state(state)
    log(f"  chi(r) done ({rec['chi_minutes']:.1f} min)")


# ===========================================================================
# STAGE D — report
# ===========================================================================
def _fmt(x: Any, spec: str = ".6g", na: str = "n/a") -> str:
    if x is None:
        return na
    if isinstance(x, float) and not np.isfinite(x):
        return "NaN"
    try:
        return format(float(x), spec)
    except (TypeError, ValueError):
        return str(x)


def _pct_diff(a: Any, b: Any) -> str:
    try:
        a, b = float(a), float(b)
    except (TypeError, ValueError):
        return "n/a"
    if not (np.isfinite(a) and np.isfinite(b)) or a == 0:
        return "n/a"
    return f"{100.0 * (b - a) / abs(a):+.2f}%"


def stage_d_report(state: Dict[str, Any]) -> str:
    banner("STAGE D -- report")
    a, b = VOLUMES[0], VOLUMES[1]
    ra = state["volumes"][a["sample_id"]]
    rb = state["volumes"][b["sample_id"]]
    ident = state.get("identity_check", {})
    collapsed = bool(ident.get("collapsed"))
    L: List[str] = []
    A = L.append

    A(f"# Bnei Re'em — unified two-specimen pipeline results")
    A("")
    A(f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} by "
      f"`04_inference/scripts/run_bnei_reem_unified_pipeline.py`.")
    A("")
    A("Both specimens were put through **one script, one code path**: raw reconstruction → "
      "center 650³ crop → norm200 + CUDA NLM → global-mean/std z-score → 4-way split → "
      "nnU-Net inference (`multi_sample_fresh_bnei_reem_i4`, trainer "
      "`nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss_lowlr`) → PSD/topology diagnostics "
      "→ χ(r) sweep. The only per-volume differences are input folder, slice regex, output "
      "sample ID, and voxel spacing; every other step, order and parameter is identical.")
    A("")

    # ---- 1. verification -------------------------------------------------
    A("## 1. Input verification")
    A("")
    for r, v in ((ra, a), (rb, b)):
        ver = r["verification"]
        A(f"### {ver['label']} — `{ver['sample_id']}`")
        A("")
        A(f"- Folder read: `{ver['raw_dir_used']}`")
        if ver["used_fallback"]:
            A(f"- **SUBSTITUTION**: the specified folder `{ver['raw_dir_specified']}` was "
              f"preview-only (no full numbered reconstruction stack). The identically-named "
              f"local copy above was used instead. This is stated explicitly, not silent.")
        else:
            A(f"- This is the folder specified in the task (no substitution).")
        A(f"- Slice regex: `{ver['slice_regex']}`")
        A(f"- **Slice count: {ver['n_matching_slices']}** matching slices "
          f"({ver['n_tif_total']} .tif in the folder, {ver['n_excluded']} excluded as "
          f"preview/parameter-tuning/aux files)")
        A(f"- Index range {ver['index_first']}–{ver['index_last']}, **contiguous: "
          f"{ver['contiguous']}** (zero gaps)")
        A(f"- Shape **{ver['slice_shape'][0]}×{ver['slice_shape'][1]}**, dtype **{ver['dtype']}**, "
          f"dynamic range reaches **65535**: real reconstruction stack ✔")
        A(f"- Voxel spacing: **{ver['voxel_spacing_um']} µm** (isotropic)")
        A("")
        A("| probe | file | min | max | mean |")
        A("|---|---|---|---|---|")
        for lbl in ("first", "mid", "last"):
            p = ver["probes"][lbl]
            A(f"| {lbl} | `{p['name']}` | {p['min']} | {p['max']} | {p['mean']:.1f} |")
        A("")
        A(f"- Center crop: Z positions {r['crop']['z_positions'][0]}–{r['crop']['z_positions'][1]} "
          f"(original indices {r['crop']['z_original_indices'][0]}–"
          f"{r['crop']['z_original_indices'][1]}), XY offset "
          f"{r['crop']['xy_offsets']} → {CROP_SIZE}³")
        A(f"- NLM volume MD5 `{r['nlm']['md5']}` "
          f"(mean {r['nlm']['mean']:.5f}, std {r['nlm']['std']:.5f})")
        A("")

    same_md5 = ra["nlm"]["md5"] == rb["nlm"]["md5"]
    A(f"**Shared-scratch-slot hazard**: `02_preprocessing/filters/nlm_output/nlm_volume.tif` is "
      f"overwritten by every `run_preprocess.py` call. The two volumes were processed strictly "
      f"sequentially, both scratch slots were deleted before each call, each NLM result was "
      f"copied out to a per-specimen path before the next specimen started, and the two "
      f"copied-out volumes were MD5-compared: "
      f"**{'IDENTICAL — COLLAPSE' if same_md5 else 'DISTINCT ✔'}**.")
    A("")

    # ---- 2. identity check ----------------------------------------------
    A("## 2. Identity check — the reason for this rerun")
    A("")
    A("| Quantity | This run | Previous failed run | Genuinely-different baseline |")
    A("|---|---|---|---|")
    A(f"| Pearson r between the two z-scored `_0000.nii.gz` arrays | "
      f"**{_fmt(ident.get('pearson_r_zscored_inputs'), '.6f')}** | 0.9999 | ~{BASELINE_DIFFERENT_R} |")
    A(f"| Pore-label (5) Dice between the two segmentations | "
      f"**{_fmt(ident.get('pore_dice'), '.6f')}** | 0.988 | — |")
    A(f"| Pore-label IoU | {_fmt(ident.get('pore_iou'), '.6f')} | — | — |")
    A(f"| Dice expected under independence (from marginals) | "
      f"{_fmt(ident.get('dice_expected_under_independence'), '.6f')} | — | — |")
    A(f"| Inputs byte-identical | {ident.get('inputs_byte_identical')} | — | — |")
    A(f"| Segmentations byte-identical | {ident.get('segmentations_byte_identical')} | — | — |")
    A("")
    if collapsed:
        A("> ### ⛔ COLLAPSE — THIS IS A DATA PROBLEM, NOT A RESULT")
        A(">")
        A("> The two specimens are (near-)identical at the point of segmentation, exactly as in "
          "the previous failed run. **The structural metrics below are NOT reported as results** — "
          "any apparent agreement between the two specimens is an artifact of the two pipelines "
          "having consumed the same data, and any apparent difference is noise on top of that. "
          "Stage C was not executed.")
        A("")
    else:
        A(f"**PASS.** r = {_fmt(ident.get('pearson_r_zscored_inputs'), '.4f')} and pore Dice = "
          f"{_fmt(ident.get('pore_dice'), '.4f')} are both far below the previous run's "
          f"0.9999 / 0.988. The two volumes carry genuinely different data through the pipeline, "
          f"so the metrics below are interpretable.")
        A("")

    # ---- 3. metrics ------------------------------------------------------
    A("## 3. Structural metrics, side by side")
    A("")
    if collapsed:
        A("_Not computed — the identity check failed and the run stopped at stage B._")
        A("")
    else:
        sa = ra.get("psd_summary", {}) or {}
        sb = rb.get("psd_summary", {}) or {}
        ca = ra.get("chi_meta") or {}
        cb = rb.get("chi_meta") or {}
        rows = [
            ("Pore fraction (label 5)", 100 * ra["inference"]["pore_fraction"],
             100 * rb["inference"]["pore_fraction"], ".4f", "%"),
            ("POM fraction (labels 2+3)", 100 * ra["inference"]["pom_fraction"],
             100 * rb["inference"]["pom_fraction"], ".4f", "%"),
            ("Euler number χ", sa.get("euler_number"), sb.get("euler_number"), ".6g", ""),
            ("Connectivity density (mm⁻³)", sa.get("connectivity_density_per_mm3"),
             sb.get("connectivity_density_per_mm3"), ".6g", ""),
            ("Γ (connectivity probability)", sa.get("connectivity_probability_gamma"),
             sb.get("connectivity_probability_gamma"), ".6f", ""),
            ("DA (degree of anisotropy)", sa.get("degree_of_anisotropy"),
             sb.get("degree_of_anisotropy"), ".6f", ""),
            ("PSD 30–150 µm volume fraction", sa.get("psd_30_150um_volume_fraction"),
             sb.get("psd_30_150um_volume_fraction"), ".6f", ""),
            ("r* crossover radius (µm)", ca.get("r_star_um"), cb.get("r_star_um"), ".2f", ""),
        ]
        A("| Metric | Specimen A (`bnei_reem_specA_unified`) | Specimen B (`bnei_reem_specB_unified`) | B vs A |")
        A("|---|---|---|---|")
        for name, x, y, spec, unit in rows:
            A(f"| {name} | {_fmt(x, spec)}{unit} | {_fmt(y, spec)}{unit} | {_pct_diff(x, y)} |")
        A(f"| χ(r) trend | {ca.get('trend', 'n/a')} | {cb.get('trend', 'n/a')} | — |")
        A(f"| r* resolution-limited? | {ca.get('resolution_limited', 'n/a')} | "
          f"{cb.get('resolution_limited', 'n/a')} | — |")
        A(f"| Voxel spacing (µm) | {a['voxel_spacing_um']} | {b['voxel_spacing_um']} | — |")
        A("")
        A(f"- Tortuosity was **not computed** (`--no-tortuosity`): ~15 h per volume, and axis0 "
          f"returns NaN via solver non-convergence on these volumes anyway. Its keys are omitted "
          f"from every output rather than filled with placeholders.")
        A(f"- PSD run dirs: `{ra.get('psd_run_dir', 'n/a')}` and `{rb.get('psd_run_dir', 'n/a')}`")
        A(f"- χ(r) CSVs: `{ra.get('chi_csv', 'n/a')}` and `{rb.get('chi_csv', 'n/a')}`")
        A("")
        A("### χ(r) sanity checks")
        A("")
        A("| Check | Specimen A | Specimen B |")
        A("|---|---|---|")
        A(f"| χ(r=min) == recorded full-mask Euler number | "
          f"{ca.get('sanity_check_1_chi_at_min_r_matches_recorded_euler', 'n/a')} | "
          f"{cb.get('sanity_check_1_chi_at_min_r_matches_recorded_euler', 'n/a')} |")
        A(f"| voxel-count × voxel-size³ back-calculation | "
          f"{ca.get('sanity_check_2_volume_back_calc', 'n/a')} | "
          f"{cb.get('sanity_check_2_volume_back_calc', 'n/a')} |")
        A("")

    # ---- 4. verdict ------------------------------------------------------
    A("## 4. Do the two specimens actually differ?")
    A("")
    if collapsed:
        A("**No — and that is a data problem, not a finding.** The identity check reproduced the "
          "previous failure: the two volumes reaching segmentation are (near-)identical "
          f"(r = {_fmt(ident.get('pearson_r_zscored_inputs'), '.6f')}, pore Dice = "
          f"{_fmt(ident.get('pore_dice'), '.6f')}). Whatever is collapsing the two inputs onto "
          "one another survived the mitigations in this script and must be found before any "
          "two-specimen comparison can be reported. No structural metrics are presented as results.")
    else:
        A(f"**Yes.** Pearson r = {_fmt(ident.get('pearson_r_zscored_inputs'), '.4f')} between the "
          f"two z-scored inputs and pore-label Dice = {_fmt(ident.get('pore_dice'), '.4f')} "
          f"between the two segmentations — nowhere near the previous run's 0.9999 / 0.988. The "
          f"two folders hold genuinely different reconstructions and the pipeline carried that "
          f"difference through to the segmentations. The metrics in §3 are a real two-specimen "
          f"comparison.")
    A("")

    # ---- 5. provenance ---------------------------------------------------
    A("## 5. Provenance")
    A("")
    A("| Item | Value |")
    A("|---|---|")
    A(f"| Driver | `04_inference/scripts/run_bnei_reem_unified_pipeline.py` |")
    A(f"| Model | `multi_sample_fresh_bnei_reem_i4` / `Dataset777_GCEF` |")
    A(f"| Trainer | `{TRAINER_NAME}` |")
    A(f"| Labels | Pore=5, POM=2,3 (dataset.json) |")
    A(f"| Crop | center {CROP_SIZE}³ |")
    A(f"| Anisotropy directions | {N_ANISOTROPY_DIRECTIONS} |")
    A(f"| CUDA env | `{PY_CUDA}` |")
    A(f"| Topology env | `{PY_TOPO}` |")
    A(f"| State file | `{STATE_PATH}` |")
    A(f"| Stage A wall time | A: {_fmt(ra.get('stage_a_minutes'), '.1f')} min, "
      f"B: {_fmt(rb.get('stage_a_minutes'), '.1f')} min |")
    if not collapsed:
        A(f"| Stage C wall time | A: PSD {_fmt(ra.get('psd_minutes'), '.1f')} min + χ(r) "
          f"{_fmt(ra.get('chi_minutes'), '.1f')} min, B: PSD {_fmt(rb.get('psd_minutes'), '.1f')} "
          f"min + χ(r) {_fmt(rb.get('chi_minutes'), '.1f')} min |")
    A("")

    text = "\n".join(L) + "\n"
    for dest in (REPO_DIR / REPORT_NAME, HIVE_BASE / REPORT_NAME):
        dest.write_text(text, encoding="utf-8")
        log(f"  wrote {dest}")
    state["report_paths"] = [str(REPO_DIR / REPORT_NAME), str(HIVE_BASE / REPORT_NAME)]
    save_state(state)
    return text


# ===========================================================================
# main
# ===========================================================================
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gpu", type=int, default=0)
    ap.add_argument("--splits", type=int, default=4)
    ap.add_argument("--stage", default="all", choices=["all", "A", "B", "C", "D"])
    args = ap.parse_args()

    t_start = time.time()
    state = load_state()
    state["started"] = datetime.now().isoformat(timespec="seconds")
    state["gpu"] = args.gpu
    state["splits"] = args.splits
    save_state(state)

    banner("BNEI RE'EM UNIFIED TWO-SPECIMEN PIPELINE")
    log(f"repo         : {REPO_DIR}")
    log(f"CUDA python  : {PY_CUDA}")
    log(f"topo python  : {PY_TOPO}")
    log(f"stage        : {args.stage}   gpu={args.gpu}   splits={args.splits}")
    for v in VOLUMES:
        log(f"  {v['label']}: {v['sample_id']}  voxel={v['voxel_spacing_um']} um  <- {v['raw_dir']}")

    if args.stage in ("all", "A"):
        # STRICTLY SEQUENTIAL. Never parallel: nlm_volume.tif is a shared slot.
        seen_md5: Dict[str, str] = {}
        for vol in VOLUMES:
            run_stage_a_for_volume(vol, args.gpu, args.splits, seen_md5, state)
    else:
        # Populate _matching lazily for any stage that needs it (none of B/C/D do).
        pass

    ident = state.get("identity_check")
    if args.stage in ("all", "A", "B"):
        ident = stage_b_identity_check(state)

    if args.stage in ("all", "C"):
        if ident and ident.get("collapsed"):
            banner("SKIPPING STAGE C -- identity check reported a collapse. "
                   "Metrics would be meaningless.")
        else:
            for vol in VOLUMES:
                stage_c_for_volume(vol, state)

    if args.stage in ("all", "D"):
        stage_d_report(state)

    state["finished"] = datetime.now().isoformat(timespec="seconds")
    state["total_minutes"] = (time.time() - t_start) / 60.0
    save_state(state)
    banner(f"ALL DONE in {state['total_minutes']:.1f} min")
    if state.get("identity_check", {}).get("collapsed"):
        log("EXIT 3: identity check reported a collapse -- see the report.")
        sys.exit(3)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.stdout.flush()
        raise
