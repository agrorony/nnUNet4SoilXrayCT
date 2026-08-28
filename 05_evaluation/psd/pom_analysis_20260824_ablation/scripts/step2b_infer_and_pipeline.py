"""Part B steps 2-3 -- mishmar_image_then_predict.

Runs the existing split -> nnUNetPredictor(loess_i2) -> concatenate pipeline
on the block-averaged ~15um image produced by step2a_image_downsample.py,
sanity-checks pore/POM voxel fractions BEFORE running the expensive POM
pipeline (this is exactly the check the failed 2026-08-23 mishmar_15um
branch skipped), and only proceeds to the full A1/A2/A3/B pipeline if it
passes.
"""
from __future__ import annotations

import gc
import json
import os
import subprocess
import sys
import time
import warnings
from pathlib import Path
from typing import Dict, Optional

os.environ.setdefault('CUDA_VISIBLE_DEVICES', '1')  # GPU 0 busy with another job; GPU 1 idle

import nibabel as nib
import numpy as np
import tifffile
import torch
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # .../05_evaluation/psd
from psd_topology_metrics import get_percolating_mask  # noqa: E402

OUT_ROOT = Path(__file__).resolve().parents[1]
BORDER_WIDTH = 1
CUTOFFS = (2, 8, 27)
STRUCT_26 = np.ones((3, 3, 3), dtype=np.uint8)
STRUCT_FACE = ndi.generate_binary_structure(3, 1)

SOIL_KEY = "mishmar_image_then_predict"
PORE_LABEL, POM_LABEL = 5, 2
VALID_LABELS = {0, 1, 2, 5}
TARGET_VOXEL_UM = 15.000149  # nominal; actual achieved value read back from step2a's log/report

HIVE = r"\\hive3065\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources"
TRAINER = "nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss"
MODEL_DIR = os.path.join(
    HIVE, "multi_sample_mishmar_hanegev_maoz_3_5p85um_loess_i2", "nnUNet_results", "Dataset777_GCEF",
    f"{TRAINER}__nnUNetPlans__3d_fullres",
)
SID = SOIL_KEY
SAMPLE_BASE = os.path.join(HIVE, "mishmar_hanegev_maoz_3_5p85um", "ablation_image_downsample")
NIFTI_PREDICT_DIR = os.path.join(SAMPLE_BASE, "nifti_predict_ds15um")
SPLIT_INPUT_DIR = os.path.join(SAMPLE_BASE, "inference_input_ds15um")
OUTPUT_DIR = os.path.join(SAMPLE_BASE, "inference_output_ds15um")
CONCAT_DIR = os.path.join(SAMPLE_BASE, "inference_output_concat_ds15um")

REPO_DIR = r"C:\Users\rony.schwartz\Documents\nnUNet4SoilXrayCT"
SPLIT_SCRIPT = os.path.join(REPO_DIR, "02_preprocessing", "nnunet", "preprocessing_nnUNet_predict_split.py")
CONCATENATE_SCRIPT = os.path.join(REPO_DIR, "04_inference", "postprocessing_nnUNet_predict_concatenate.py")

os.environ["nnUNet_compile"] = "false"
os.environ["nnUNet_raw"] = os.path.join(HIVE, "multi_sample_mishmar_hanegev_maoz_3_5p85um_loess_i2", "nnUNet_raw")
os.environ["nnUNet_preprocessed"] = os.path.join(HIVE, "multi_sample_mishmar_hanegev_maoz_3_5p85um_loess_i2", "nnUNet_preprocessed")
os.environ["nnUNet_results"] = os.path.join(HIVE, "multi_sample_mishmar_hanegev_maoz_3_5p85um_loess_i2", "nnUNet_results")

# PyTorch 2.6+ checkpoint compatibility
_orig_load = torch.load
def _patched_load(f, *args, **kwargs):
    kwargs.setdefault("weights_only", False)
    return _orig_load(f, *args, **kwargs)
torch.load = _patched_load

# Reference: native Mishmar (5.85um) fractions, from pom_analysis_20260815/mishmar/summary_pom_metrics.json
NATIVE_MISHMAR_POM_PCT = 1.6146797
NATIVE_MISHMAR_PORE_PCT = 27.0384653
POM_COLLAPSE_FLOOR_PCT = 0.3


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def trim_border(arr: np.ndarray, bw: int = BORDER_WIDTH) -> np.ndarray:
    return arr[bw:-bw, bw:-bw, bw:-bw]


def stats_for_map(dmap: np.ndarray) -> Dict[str, Optional[float]]:
    trimmed = trim_border(dmap)
    is_degenerate = bool(trimmed.max() == 0.0 and trimmed.min() == 0.0)
    if is_degenerate:
        return {
            "degenerate": True,
            "degenerate_reason": "Map is uniformly zero after border trim -- empty target mask. Stats withheld.",
            "mean_um": None, "median_um": None, "n_voxels": int(trimmed.size),
        }
    return {
        "degenerate": False, "degenerate_reason": None,
        "mean_um": float(np.mean(trimmed)), "median_um": float(np.median(trimmed)),
        "n_voxels": int(trimmed.size),
    }


def edt_to_mask(mask: np.ndarray, voxel_um: float) -> np.ndarray:
    if not np.any(mask):
        warnings.warn("Empty target mask; returning all-inf distance map.", UserWarning)
        return np.full(mask.shape, np.inf, dtype=np.float32)
    dmap = ndi.distance_transform_edt(~mask, sampling=(voxel_um,) * 3)
    return dmap.astype(np.float32)


def write_tif(out_dir: Path, name: str, dmap: np.ndarray) -> None:
    finite = np.where(np.isfinite(dmap), dmap, 0.0).astype(np.float32)
    tifffile.imwrite(str(out_dir / f"{name}.tif"), finite)
    mid = finite.shape[0] // 2
    tifffile.imwrite(str(out_dir / f"{name}_midslice.tif"), finite[mid])


def find_elbow(sizes: np.ndarray, counts: np.ndarray) -> int:
    valid = counts > 0
    x = sizes[valid].astype(np.float64)
    y = np.log10(counts[valid].astype(np.float64))
    if len(x) < 3:
        return int(sizes[0])
    xn = (x - x.min()) / (x.max() - x.min())
    yn = (y - y.min()) / (y.max() - y.min() + 1e-12)
    dist = (xn + yn - 1.0) / np.sqrt(2.0)
    knee_idx = int(np.argmin(dist))
    return int(x[knee_idx])


def run_split_infer_concat() -> str:
    assert os.path.isfile(os.path.join(NIFTI_PREDICT_DIR, f"{SID}_0000.nii.gz")), (
        f"Missing downsampled image -- run step2a_image_downsample.py first"
    )
    os.makedirs(SPLIT_INPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(CONCAT_DIR, exist_ok=True)

    log("=== Step A: split (s=1, reuses existing split/concat orientation convention) ===")
    res = subprocess.run(
        [sys.executable, SPLIT_SCRIPT, "-i", NIFTI_PREDICT_DIR, "-o", SPLIT_INPUT_DIR,
         "-m", MODEL_DIR, "-s", "1", "-a", "2"],
        capture_output=True, text=True,
    )
    print(res.stdout)
    if res.returncode != 0:
        print("STDERR:", res.stderr)
        raise RuntimeError(f"Split failed (exit {res.returncode})")

    chunks = [f for f in os.listdir(SPLIT_INPUT_DIR) if f.endswith("_0000.nii.gz")]
    log(f"  {len(chunks)} chunk(s): {chunks}")
    assert len(chunks) > 0, "No split chunks produced"

    log("=== Step B: nnUNet inference (loess_i2) ===")
    assert os.path.isdir(MODEL_DIR), f"Model dir not found: {MODEL_DIR}"
    fold_dir = os.path.join(MODEL_DIR, "fold_0")
    for ckpt in ("checkpoint_final.pth", "checkpoint_best.pth", "checkpoint_latest.pth"):
        if os.path.isfile(os.path.join(fold_dir, ckpt)):
            checkpoint_name = ckpt
            break
    else:
        raise FileNotFoundError(f"No checkpoint in {fold_dir}")
    log(f"  checkpoint: {checkpoint_name}  CUDA available: {torch.cuda.is_available()}")

    from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor

    predictor = nnUNetPredictor(
        tile_step_size=0.5, use_gaussian=True, use_mirroring=False,
        perform_everything_on_device=False,
        device=torch.device("cuda" if torch.cuda.is_available() else "cpu"),
        verbose=True, allow_tqdm=True,
    )
    predictor.initialize_from_trained_model_folder(MODEL_DIR, use_folds=(0,), checkpoint_name=checkpoint_name)
    predictor.predict_from_files(
        SPLIT_INPUT_DIR, OUTPUT_DIR, save_probabilities=False, overwrite=True,
        num_processes_preprocessing=1, num_processes_segmentation_export=1,
        folder_with_segs_from_prev_stage=None, num_parts=1, part_id=0,
    )
    del predictor
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    log("  inference done")

    log("=== Step C: concatenation ===")
    res = subprocess.run(
        [sys.executable, CONCATENATE_SCRIPT, "-i", OUTPUT_DIR, "-o", CONCAT_DIR],
        capture_output=True, text=True,
    )
    print(res.stdout)
    if res.returncode != 0:
        print("STDERR:", res.stderr)
        raise RuntimeError(f"Concatenation failed (exit {res.returncode})")

    concat_path = os.path.join(CONCAT_DIR, f"{SID}.nii.gz")
    assert os.path.isfile(concat_path), f"Missing: {concat_path}"
    log(f"  wrote {concat_path}")
    return concat_path


def run_full_pom_pipeline(vol: np.ndarray, voxel_um: float, out_dir: Path, label: str, source_desc: str) -> Dict:
    voxel_vol_um3 = voxel_um ** 3
    pore_mask = (vol == PORE_LABEL)
    pom_mask_all = (vol == POM_LABEL)
    n_total = int(vol.size)

    n_pore = int(pore_mask.sum())
    n_pom = int(pom_mask_all.sum())
    log(f"  pore voxels={n_pore:,} ({100*n_pore/n_total:.3f}%)  pom voxels={n_pom:,} ({100*n_pom/n_total:.3f}%)")

    log("Labeling POM objects (26-connectivity)...")
    t0 = time.time()
    labels, n_objects_raw = ndi.label(pom_mask_all, structure=STRUCT_26)
    counts = np.bincount(labels.ravel())[1:]
    log(f"  n_objects_raw={n_objects_raw:,}  ({time.time()-t0:.1f}s)")

    hist_sizes = np.arange(1, 51)
    hist_counts, _ = np.histogram(counts, bins=np.arange(1, 52))
    proposed_cutoff = find_elbow(hist_sizes, hist_counts)

    total_pom_voxels = int(counts.sum())
    cutoff_report = {}
    for c in CUTOFFS:
        keep = counts >= c
        vol_frac = float(counts[keep].sum() / total_pom_voxels) if total_pom_voxels else float("nan")
        cutoff_report[str(c)] = {
            "cutoff_voxels": c,
            "cutoff_equiv_diameter_um": float((6 * c * voxel_vol_um3 / np.pi) ** (1 / 3)),
            "n_objects_kept": int(keep.sum()),
            "n_objects_removed": int(n_objects_raw - keep.sum()),
            "pom_volume_fraction_retained": vol_frac,
        }

    default_cutoff = proposed_cutoff
    default_report = {
        "cutoff_voxels": default_cutoff,
        "cutoff_volume_um3": float(default_cutoff * voxel_vol_um3),
        "cutoff_equiv_diameter_um": float((6 * default_cutoff * voxel_vol_um3 / np.pi) ** (1 / 3)),
    }
    log(f"  proposed elbow cutoff = {default_cutoff} voxels ({default_report['cutoff_equiv_diameter_um']:.2f} um equiv diameter)")

    keep_default = np.zeros(n_objects_raw + 1, dtype=bool)
    keep_default[1:] = counts >= default_cutoff
    denoised_mask = keep_default[labels]
    n_denoised = int(denoised_mask.sum())
    default_report["n_objects_kept"] = int(keep_default.sum())
    default_report["pom_volume_fraction_retained"] = float(n_denoised / total_pom_voxels) if total_pom_voxels else float("nan")
    log(f"  denoised POM voxels={n_denoised:,} ({default_report['pom_volume_fraction_retained']*100:.2f}% of raw POM volume)")

    log("Building pore-dilation masks for adjacency conditions...")
    pore_dilated = ndi.binary_dilation(pore_mask, structure=STRUCT_FACE)

    candidate_labels = labels[denoised_mask & pore_dilated]
    pore_adj_label_set = np.unique(candidate_labels)
    pore_adj_label_set = pore_adj_label_set[pore_adj_label_set > 0]
    keep_pore_adj = np.zeros(n_objects_raw + 1, dtype=bool)
    keep_pore_adj[pore_adj_label_set] = True
    pore_adjacent_mask = keep_pore_adj[labels]
    n_pore_adj = int(pore_adjacent_mask.sum())
    log(f"  pore-adjacent POM voxels={n_pore_adj:,}")

    log("Computing percolating pore mask (axis=0, 26-connectivity)...")
    connected_pore_mask = get_percolating_mask(pore_mask, axis=0)
    connected_pore_dilated = ndi.binary_dilation(connected_pore_mask, structure=STRUCT_FACE)
    candidate2 = labels[pore_adjacent_mask & connected_pore_dilated]
    conn_pore_adj_label_set = np.unique(candidate2)
    conn_pore_adj_label_set = conn_pore_adj_label_set[conn_pore_adj_label_set > 0]
    keep_conn_pore_adj = np.zeros(n_objects_raw + 1, dtype=bool)
    keep_conn_pore_adj[conn_pore_adj_label_set] = True
    connected_pore_adjacent_mask = keep_conn_pore_adj[labels]
    n_conn_pore_adj = int(connected_pore_adjacent_mask.sum())
    log(f"  connected-pore-adjacent POM voxels={n_conn_pore_adj:,}")

    targets = {
        "distance_to_pom_denoised": denoised_mask,
        "distance_to_pom_pore_adjacent": pore_adjacent_mask,
        "distance_to_pom_connected_pore_adjacent": connected_pore_adjacent_mask,
    }
    target_n_voxels = {
        "distance_to_pom_denoised": n_denoised,
        "distance_to_pom_pore_adjacent": n_pore_adj,
        "distance_to_pom_connected_pore_adjacent": n_conn_pore_adj,
    }

    a2_results = {}
    for name, mask in targets.items():
        log(f"Computing {name} EDT...")
        t0 = time.time()
        dmap = edt_to_mask(mask, voxel_um)
        log(f"  EDT done ({time.time()-t0:.1f}s)")
        write_tif(out_dir, name, dmap)
        stats = stats_for_map(dmap)
        stats["n_target_voxels"] = target_n_voxels[name]
        stats["pom_volume_fraction_of_total_pom"] = float(target_n_voxels[name] / total_pom_voxels) if total_pom_voxels else float("nan")
        stats["pom_volume_fraction_of_denoised_pom"] = float(target_n_voxels[name] / n_denoised) if n_denoised else float("nan")
        a2_results[name] = stats
        del dmap

    log("Computing A3 accessibility metrics...")
    surface_voxels = denoised_mask & ~ndi.binary_erosion(denoised_mask, structure=STRUCT_FACE, border_value=0)
    n_surface = int(surface_voxels.sum())
    surface_pore_adjacent = surface_voxels & pore_dilated
    n_surface_pore_adjacent = int(surface_pore_adjacent.sum())
    pom_pore_contact_fraction = float(n_surface_pore_adjacent / n_surface) if n_surface else float("nan")

    a3 = {
        "soil": SOIL_KEY,
        "pom_volume_fraction_pct_raw": float(100 * n_pom / n_total),
        "pom_volume_fraction_pct_denoised": float(100 * n_denoised / n_total),
        "n_pom_objects_ge_cutoff": int(keep_default.sum()),
        "cutoff_voxels": default_cutoff,
        "pom_pore_contact_fraction": pom_pore_contact_fraction,
        "n_surface_voxels_denoised_pom": n_surface,
    }
    log(f"  POM volume fraction (denoised) = {a3['pom_volume_fraction_pct_denoised']:.3f}%  contact fraction = {pom_pore_contact_fraction:.3f}")

    log("Computing Part B object diameters...")
    keep_counts = counts[counts >= default_cutoff]
    eq_diam_um = (6.0 * keep_counts.astype(np.float64) * voxel_vol_um3 / np.pi) ** (1.0 / 3.0)
    np.save(out_dir / "pom_object_diameters_um.npy", eq_diam_um)
    np.save(out_dir / "pom_object_voxel_counts.npy", keep_counts)

    largest_idx = int(np.argmax(keep_counts))
    largest_diam_um = float(eq_diam_um[largest_idx])
    largest_frac_of_denoised_vol = float(keep_counts[largest_idx] / keep_counts.sum())

    def weighted_median(values: np.ndarray, weights: np.ndarray) -> float:
        order = np.argsort(values)
        v, w = values[order], weights[order]
        cw = np.cumsum(w)
        cutoff_w = cw[-1] / 2.0
        idx = int(np.searchsorted(cw, cutoff_w))
        return float(v[min(idx, len(v) - 1)])

    b_summary = {
        "soil": SOIL_KEY,
        "cutoff_voxels": default_cutoff,
        "n_objects": int(len(eq_diam_um)),
        "median_diameter_um": float(np.median(eq_diam_um)),
        "volume_weighted_median_diameter_um": weighted_median(eq_diam_um, keep_counts.astype(np.float64)),
        "largest_object_diameter_um": largest_diam_um,
        "largest_object_pct_of_denoised_pom_volume": float(100 * largest_frac_of_denoised_vol),
        "total_denoised_pom_voxels": int(keep_counts.sum()),
    }
    log(f"  n_objects={b_summary['n_objects']:,}  median={b_summary['median_diameter_um']:.2f}um  "
        f"vol-weighted median={b_summary['volume_weighted_median_diameter_um']:.2f}um  "
        f"largest={largest_diam_um:.2f}um ({largest_frac_of_denoised_vol*100:.2f}% of denoised POM volume)")

    log("Saving mid-slice kept/removed diagnostic PNG...")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    mid_z = pore_mask.shape[0] // 2
    pore_slice = pore_mask[mid_z]
    pom_all_slice = pom_mask_all[mid_z]
    denoised_slice = denoised_mask[mid_z]
    removed_slice = pom_all_slice & ~denoised_slice

    rgb = np.zeros((*pore_slice.shape, 3), dtype=np.float32)
    rgb[..., :] = 0.85
    rgb[pore_slice] = (0.15, 0.15, 0.15)
    rgb[denoised_slice] = (0.9, 0.55, 0.05)
    rgb[removed_slice] = (0.85, 0.1, 0.85)

    fig, ax = plt.subplots(figsize=(7, 7), dpi=150)
    ax.imshow(rgb)
    ax.set_title(
        f"{label} -- mid Z-slice (z={mid_z})\n"
        f"orange=kept POM (>= {default_cutoff} vox), magenta=removed (speckle)",
        fontsize=10,
    )
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(str(out_dir / "midslice_kept_removed_pom.png"), dpi=150)
    plt.close(fig)

    summary = {
        "soil": SOIL_KEY,
        "soil_label": label,
        "source_input": source_desc,
        "voxel_size_um": voxel_um,
        "shape": list(pore_mask.shape),
        "label_convention": {"pore_label": PORE_LABEL, "pom_label": POM_LABEL},
        "n_total_voxels": n_total,
        "n_pore_voxels": n_pore,
        "n_pom_voxels_raw": n_pom,
        "border_width_excluded_voxels": BORDER_WIDTH,
        "A1_noise_floor": {
            "n_objects_raw": n_objects_raw,
            "size_histogram_1_50vox": {str(k): int(v) for k, v in zip(hist_sizes.tolist(), hist_counts.tolist())},
            "proposed_default_cutoff": default_report,
            "sensitivity_cutoffs": cutoff_report,
        },
        "A2_conditioned_distance_maps": a2_results,
        "A3_accessibility_metrics": a3,
        "B_size_distribution_summary": b_summary,
    }
    with (out_dir / "summary_pom_metrics.json").open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    log(f"Wrote {out_dir / 'summary_pom_metrics.json'}")

    log("=== Sanity checks ===")
    denoised_mean = a2_results["distance_to_pom_denoised"]["mean_um"]
    pore_adj_mean = a2_results["distance_to_pom_pore_adjacent"]["mean_um"]
    conn_mean = a2_results["distance_to_pom_connected_pore_adjacent"]["mean_um"]
    vals = [v for v in (denoised_mean, pore_adj_mean, conn_mean) if v is not None]
    ordered = all(vals[i] <= vals[i + 1] for i in range(len(vals) - 1))
    log(f"ordering denoised({denoised_mean}) <= pore_adj({pore_adj_mean}) <= conn_pore_adj({conn_mean}): {ordered}")
    rightshift = b_summary["volume_weighted_median_diameter_um"] >= b_summary["median_diameter_um"]
    log(f"volume-weighted median >= count median: {rightshift}")

    return summary


def main() -> None:
    out_dir = OUT_ROOT / SOIL_KEY
    out_dir.mkdir(parents=True, exist_ok=True)

    concat_path = run_split_infer_concat()

    log(f"Loading {concat_path}")
    vol = np.asarray(nib.load(concat_path).dataobj)
    n = vol.shape[0]
    v_um = TARGET_VOXEL_UM  # step2a's block partition matches step1's (same source n, same target)
    uniq = np.unique(vol)
    log(f"  shape={vol.shape} unique_labels={uniq.tolist()}")
    if not (set(uniq.tolist()) <= VALID_LABELS):
        log(f"!!! WARNING: unexpected labels {uniq.tolist()} outside deployed convention {VALID_LABELS} !!!")

    n_total = int(vol.size)
    n_pore = int((vol == PORE_LABEL).sum())
    n_pom = int((vol == POM_LABEL).sum())
    pore_pct = 100 * n_pore / n_total
    pom_pct = 100 * n_pom / n_total
    log(f"  pore={n_pore:,} ({pore_pct:.3f}%)  pom={n_pom:,} ({pom_pct:.3f}%)")
    log(f"  reference: native Mishmar (5.85um) pore={NATIVE_MISHMAR_PORE_PCT:.3f}%  pom={NATIVE_MISHMAR_POM_PCT:.3f}%")

    sanity = {
        "branch": SOIL_KEY,
        "source_prediction": concat_path,
        "target_voxel_um": TARGET_VOXEL_UM,
        "shape": list(vol.shape),
        "unique_labels": uniq.tolist(),
        "pore_voxel_fraction_pct": pore_pct,
        "pom_voxel_fraction_pct": pom_pct,
        "native_mishmar_pore_voxel_fraction_pct": NATIVE_MISHMAR_PORE_PCT,
        "native_mishmar_pom_voxel_fraction_pct": NATIVE_MISHMAR_POM_PCT,
        "pom_collapse_floor_pct": POM_COLLAPSE_FLOOR_PCT,
        "pom_collapsed": bool(pom_pct < POM_COLLAPSE_FLOOR_PCT),
    }
    with (out_dir / "sanity_check.json").open("w", encoding="utf-8") as fh:
        json.dump(sanity, fh, indent=2)

    print("\n" + "=" * 70)
    print(f"SANITY CHECK -- {SOIL_KEY}")
    print("=" * 70)
    print(json.dumps(sanity, indent=2))

    if sanity["pom_collapsed"]:
        log("!!! STOP: POM fraction collapsed below the floor -- NOT running the full pipeline. !!!")
        return

    log("Sanity check passed. Running full POM pipeline...")
    label = f"Mishmar HaNegev (Loess) -- image downsampled to {v_um:.2f}um then loess_i2 predicted fresh"
    run_full_pom_pipeline(vol, v_um, out_dir, label, source_desc=concat_path)
    log("=== DONE ===")


if __name__ == "__main__":
    main()
