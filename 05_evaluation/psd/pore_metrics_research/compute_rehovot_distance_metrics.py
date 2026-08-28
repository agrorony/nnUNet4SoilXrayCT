"""Rehovot distance-to-target metrics for Table 2 (binary-mask columns only).

Rehovot has no 3-phase nnUNet segmentation (no POM class) -- the only
full-volume segmentation available is `rehovot_samp_2.npy`, a binary
solid/pore Otsu mask (True = pore), 650x650x650, 15.0 um isotropic. This
is the exact file used for the Rehovot row of the existing PSD/bulk-density
report (06_reporting/selected_outputs/psd_bulk_density/psd_bulk_density_report.md,
porosity 0.3050 -- reproduced below as a sanity check that this is the right
file/convention).

This computes only the two pore-based distance columns (dist-to-pore
unconditioned / connected). POM columns are not computable and are recorded
as degenerate in the output JSON so the schema matches the two existing
(3-phase) runs' summary_distance_metrics.json files.

Standalone script (not run_psd_diagnostics.py `extended` mode) because
extended mode unconditionally also runs the full PSD/granulometry and
topology suite (connectivity density, gamma, anisotropy, tortuosity),
none of which this task needs -- it reuses the pipeline's own
psd_topology_metrics.distance_map_from_mask / get_percolating_mask
functions directly, same as extended mode does internally, and matches
pore_metrics_research/compute_distance_map_stats.py's stats/border/
degenerate conventions exactly.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import tifffile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from psd_topology_metrics import distance_map_from_mask, get_percolating_mask  # noqa: E402

_INPUT_PATH = Path(
    r"\\hive3065\Yael_Mishael\Rony\remote_computer backup\10.5\rehovot_samp_2.npy"
)
_OUTPUT_DIR = Path(__file__).resolve().parent / "rehovot_distance_metrics_20260815"
_VOXEL_SIZE_UM = 15.0  # isotropic; see psd_bulk_density_report.md Sec 1.3
_BORDER_WIDTH = 1  # matches psd_diagnostics_core._DEFAULT_BORDER_WIDTH
_RUN_NAME = "rehovot_samp_2_full_volume"


def _trim_border(arr: np.ndarray, bw: int = _BORDER_WIDTH) -> np.ndarray:
    return arr[bw:-bw, bw:-bw, bw:-bw]


def _stats_for_map(dmap: np.ndarray) -> Dict[str, Optional[float]]:
    trimmed = _trim_border(dmap)
    is_degenerate = bool(trimmed.max() == 0.0 and trimmed.min() == 0.0)
    if is_degenerate:
        return {
            "degenerate": True,
            "degenerate_reason": (
                "Map is uniformly zero after border trim -- almost certainly "
                "means no percolating target mask was found, not that every "
                "voxel is adjacent to the target. Stats withheld."
            ),
            "mean_um": None,
            "median_um": None,
            "sd_um": None,
            "n_voxels": int(trimmed.size),
        }
    return {
        "degenerate": False,
        "degenerate_reason": None,
        "mean_um": float(np.mean(trimmed)),
        "median_um": float(np.median(trimmed)),
        "sd_um": float(np.std(trimmed)),
        "n_voxels": int(trimmed.size),
    }


def _write_tif(run_dir: Path, name: str, dmap: np.ndarray) -> None:
    finite = np.where(np.isfinite(dmap), dmap, 0.0).astype(np.float32)
    tifffile.imwrite(str(run_dir / f"{name}.tif"), finite)
    mid_z = finite.shape[0] // 2
    tifffile.imwrite(str(run_dir / f"{name}_midslice.tif"), finite[mid_z])


def main() -> None:
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Loading {_INPUT_PATH} ...")
    vol = np.load(str(_INPUT_PATH))
    print(f"  shape={vol.shape} dtype={vol.dtype} unique={np.unique(vol)}")
    assert vol.dtype == np.bool_, f"expected bool mask, got {vol.dtype}"

    pore_mask = vol  # True = pore (Otsu pore_is_dark=True convention; see report Sec 5.2)
    n_total = pore_mask.size
    porosity = float(pore_mask.mean())
    print(f"  n_total={n_total:,} porosity={porosity:.4f} (report value: 0.3050)")

    print("Computing dist_pore_unconditioned ...")
    dist_pore_unconditioned = distance_map_from_mask(pore_mask, _VOXEL_SIZE_UM, connected_only=False)

    print("Computing percolating (axis=0, 26-connectivity) pore subset ...")
    connected_pore_mask = get_percolating_mask(pore_mask, axis=0)
    print(f"  connected pore voxels: {int(connected_pore_mask.sum()):,} / {int(pore_mask.sum()):,}")

    print("Computing dist_pore_connected ...")
    dist_pore_conditioned = distance_map_from_mask(pore_mask, _VOXEL_SIZE_UM, connected_only=True, axis=0)

    print("Writing .tif maps ...")
    _write_tif(_OUTPUT_DIR, "distance_to_pore_unconditioned", dist_pore_unconditioned)
    _write_tif(_OUTPUT_DIR, "distance_to_pore_connected", dist_pore_conditioned)

    stats_unconditioned = _stats_for_map(dist_pore_unconditioned)
    stats_connected = _stats_for_map(dist_pore_conditioned)

    n_voxels_trimmed = int(_trim_border(pore_mask).size)

    out = {
        "run_name": _RUN_NAME,
        "border_width_excluded_voxels": _BORDER_WIDTH,
        "note": (
            "Mean/median/SD computed voxel-wise over the whole volume "
            "(outer 1-voxel border trimmed, matching the pipeline's "
            "existing exclude_borders convention). Non-finite (inf) values "
            "zeroed at .tif write time; see 'degenerate' flag per map for "
            "maps where that zeroing makes the mean/median/SD meaningless."
        ),
        "distance_to_pore_unconditioned": stats_unconditioned,
        "distance_to_pore_connected": stats_connected,
        "distance_to_pom_unconditioned": {
            "degenerate": True,
            "degenerate_reason": "binary segmentation - no POM class",
            "mean_um": None,
            "median_um": None,
            "sd_um": None,
            "n_voxels": n_voxels_trimmed,
        },
        "distance_to_pom_connected": {
            "degenerate": True,
            "degenerate_reason": "binary segmentation - no POM class",
            "mean_um": None,
            "median_um": None,
            "sd_um": None,
            "n_voxels": n_voxels_trimmed,
        },
        "source_input": str(_INPUT_PATH),
        "voxel_size_um": _VOXEL_SIZE_UM,
        "voxel_size_source": (
            "15.0 um isotropic, assumed (uncalibrated raw .tif metadata); "
            "matches the convention established for this exact rehovot_samp_2 "
            "volume in psd_bulk_density_report.md Sec 1.3 (confirmed with "
            "user 2026-07-12)."
        ),
        "label_convention": "bool array; True = pore (Otsu pore_is_dark=True; verified porosity matches report)",
        "porosity": porosity,
        "n_total_voxels": int(n_total),
    }

    out_path = _OUTPUT_DIR / "summary_distance_metrics.json"
    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print(f"\nWrote: {out_path}")

    print("\n=== Sanity checks ===")
    if stats_unconditioned["mean_um"] is not None and stats_connected["mean_um"] is not None:
        ok = stats_connected["mean_um"] >= stats_unconditioned["mean_um"]
        print(
            f"connected mean ({stats_connected['mean_um']:.4f}) >= "
            f"unconditioned mean ({stats_unconditioned['mean_um']:.4f}): {ok}"
        )
    print(f"unconditioned mean vs Mishmar (21um) / Bnei Reem (64um): "
          f"{stats_unconditioned['mean_um']:.4f} um")

    # Mid-slice PNG for eyeball check.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    mid_z = dist_pore_unconditioned.shape[0] // 2
    fig, axes = plt.subplots(1, 2, figsize=(10, 5))
    for ax, (name, dmap) in zip(
        axes,
        [
            ("distance_to_pore_unconditioned", dist_pore_unconditioned),
            ("distance_to_pore_connected", dist_pore_conditioned),
        ],
    ):
        finite = np.where(np.isfinite(dmap[mid_z]), dmap[mid_z], np.nan)
        im = ax.imshow(finite, cmap="viridis")
        ax.set_title(name, fontsize=9)
        ax.axis("off")
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="distance (um)")
    fig.suptitle(f"Rehovot distance-to-pore maps (mid Z-slice, z={mid_z})")
    fig.tight_layout()
    png_path = _OUTPUT_DIR / "distance_maps_midslice.png"
    fig.savefig(str(png_path), dpi=150)
    plt.close(fig)
    print(f"Wrote: {png_path}")


if __name__ == "__main__":
    main()
