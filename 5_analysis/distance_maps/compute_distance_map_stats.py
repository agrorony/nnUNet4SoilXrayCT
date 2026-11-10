"""Part A: scalar (mean/median/SD) summaries of the four distance_to_*.tif
maps for the two completed extended-mode full-volume runs.

reading_masks_and_metrics.md documents these maps as "diagnostic/visual
only, not reduced to a scalar anywhere in the current pipeline" -- this
script adds that reduction as a NEW summary_distance_metrics.json file,
written alongside (not replacing) the existing summary.json in each run
directory. It does not touch run_psd_diagnostics.py or any existing output.

Border handling: matches the 1-voxel border exclusion already applied
elsewhere in the pipeline (psd_diagnostics_core._mask_border_voxels,
border_width=1) -- the outer 1-voxel shell of the *whole volume* is
trimmed before computing statistics, once, on the six true faces.

Degenerate-map detection: the .tif files were written by
run_psd_diagnostics._write_distance_map_tifs, which replaces non-finite
(inf) values with 0.0 before saving (voxels with no reachable target
distance -- e.g. an empty percolating-POM mask -- become indistinguishable
from a true zero-distance voxel on disk). A map that is uniformly zero
almost certainly means "no percolating target found", not "every voxel is
adjacent to the target" -- this script flags that case explicitly
(degenerate=true, stats=null) rather than reporting a misleading 0.0/0.0/0.0.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import tifffile

_SOURCE_ROOT = Path(
    r"\\hive3065\Yael_Mishael\Rony\remote_computer backup\10.5\psd_outputs"
)
_DEST_ROOT = Path(
    r"\\hive3065\Yael_Mishael\Rony\remote_computer backup\Topology_Metrics_Aug2026\raw"
)

_RUNS = (
    "psd_diag_20260802T104738_nlm_volume_fresh_bnei_reem_i4",
    "psd_diag_20260803T010446_mishmar_hanegev_maoz_3_5p85um_scratch_i2",
)

_DIST_FILES = {
    "distance_to_pore_unconditioned": "distance_to_pore_unconditioned.tif",
    "distance_to_pore_connected": "distance_to_pore_connected.tif",
    "distance_to_pom_unconditioned": "distance_to_pom_unconditioned.tif",
    "distance_to_pom_connected": "distance_to_pom_connected.tif",
}

_BORDER_WIDTH = 1  # matches psd_diagnostics_core._DEFAULT_BORDER_WIDTH


def _trim_border(arr: np.ndarray, bw: int = _BORDER_WIDTH) -> np.ndarray:
    """Trim the outer bw-voxel shell off all six faces (whole-volume border,
    same convention as psd_diagnostics_core._mask_border_voxels)."""
    return arr[bw:-bw, bw:-bw, bw:-bw]


def _stats_for_map(path: Path) -> Dict[str, Optional[float]]:
    arr = tifffile.imread(str(path))
    trimmed = _trim_border(arr)

    is_degenerate = bool(trimmed.max() == 0.0 and trimmed.min() == 0.0)

    if is_degenerate:
        return {
            "degenerate": True,
            "degenerate_reason": (
                "Map is uniformly zero after border trim -- almost certainly "
                "means no percolating target mask was found (all-inf distance "
                "map at source, zeroed on write by _write_distance_map_tifs), "
                "not that every voxel is adjacent to the target. Stats withheld."
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


def main() -> None:
    for run_name in _RUNS:
        run_dir = _SOURCE_ROOT / run_name
        print(f"\n=== {run_name} ===")

        out: Dict[str, Dict[str, Optional[float]]] = {
            "run_name": run_name,
            "border_width_excluded_voxels": _BORDER_WIDTH,
            "note": (
                "Mean/median/SD computed voxel-wise over the whole volume "
                "(outer 1-voxel border trimmed, matching the pipeline's "
                "existing exclude_borders convention). Source .tif files "
                "already have non-finite (inf) values zeroed at write time; "
                "see 'degenerate' flag per map for maps where that zeroing "
                "makes the mean/median/SD meaningless."
            ),
        }

        for key, fname in _DIST_FILES.items():
            path = run_dir / fname
            if not path.is_file():
                print(f"  [SKIP] missing: {path}")
                out[key] = {"degenerate": None, "error": "file not found"}
                continue
            print(f"  Computing stats: {fname}")
            stats = _stats_for_map(path)
            out[key] = stats
            if stats.get("degenerate"):
                print(f"    [DEGENERATE] {stats['degenerate_reason']}")
            else:
                print(
                    f"    mean={stats['mean_um']:.4f} um  "
                    f"median={stats['median_um']:.4f} um  "
                    f"sd={stats['sd_um']:.4f} um"
                )

        # Write alongside the existing summary.json in the source run dir.
        source_out_path = run_dir / "summary_distance_metrics.json"
        with source_out_path.open("w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=2)
        print(f"  Wrote: {source_out_path}")

        # Copy to the usual destination.
        dest_dir = _DEST_ROOT / run_name
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_out_path = dest_dir / "summary_distance_metrics.json"
        with dest_out_path.open("w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=2)
        print(f"  Copied to: {dest_out_path}")


if __name__ == "__main__":
    main()
