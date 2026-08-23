"""Part B: split each full-volume segmentation into N equal spatial blocks
and recompute, per block: PSD bin counts, the four distance-map means
(reusing the already-computed full-volume distance .tif files, sliced --
NOT re-run through a fresh EDT), and euler_number / connectivity_density /
connectivity_probability_gamma.

Deliberately EXCLUDED per block (see decisions.md-style reasoning below,
and the accompanying report to Rony): degree_of_anisotropy and
tortuosity_axis0/1/2. Both need a mask that spans/percolates the block
being measured; at 2x2x2 block scale that is not guaranteed, and
tortuosity's porespy solver was already the dominant cost (>13h of the
~14h full-run runtime) even at full-volume scale, before any percolation
concerns.

Methodology notes (see the full explanation sent to Rony in chat -- this
is the terse in-code version):

- Block partition: as-equal-as-possible split of each axis into `n_blocks`
  pieces (default 2x2x2=8). Both volumes here split evenly (650/2=325,
  652/2=326; 1000/2=500) so no remainder handling was needed in practice,
  but _axis_bounds below handles uneven splits anyway.

- Border exclusion: mirrors the existing pipeline convention exactly, not
  a new one. psd_diagnostics_core only 1-voxel-border-trims the mask that
  feeds the PSD/opening-map step (exclude_borders=True there); it does NOT
  border-trim the mask used for euler_number/connectivity_density/gamma.
  Extended to blocks: a block's PSD input mask gets a 1-voxel trim on
  whichever of its 6 faces are TRUE outer faces of the whole volume (not
  on the 3 internal faces newly created by splitting -- those aren't a
  real imaging-FOV edge, they're just where we cut). The euler/gamma mask
  gets no border trim at all, same as the full-volume computation.

- PSD per block: calls the SAME run_psd_pipeline() used for the full-volume
  runs, with the SAME bin_edges_um as that sample's whole-volume run (from
  its config.json) so block histograms are comparable to each other and to
  the whole-volume result. use_chunking/chunk_size/halo_width match the
  parent run's settings.

- KNOWN, UNAVOIDABLE-AT-THIS-SCALE bias (flagged, not fixed here): cropping
  a continuous pore network at the 3 internal split faces (a) truncates
  local-thickness estimates for pores near those faces (no halo across an
  inter-block face -- a halo only helps within a block's own chunked EDT,
  it does not see past the block crop itself), and (b) changes euler_number
  particularly (loops/cavities that cross a cut face are counted as open
  rather than closed). This is a standard finite-size/edge effect for any
  block-based topology estimate; not something a per-block halo can undo
  for euler/gamma since those are computed directly on each block's own
  mask by definition. Treat block-level euler/connectivity/gamma and PSD
  bin counts as descriptive/within-volume-spread data only, per the
  scoping already agreed with Rony -- not edge-corrected stereology.

- Distance-map means per block: NOT recomputed from a fresh per-block EDT.
  Sliced directly out of the full-volume distance_to_*.tif arrays (which
  already have correct whole-volume 3D context and the standard 1-voxel
  outer-border trim applied face-aware, same rule as above). This avoids
  introducing a new edge-effect at internal block faces for this metric
  entirely, since the underlying distance values were never computed
  block-locally in the first place.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

_HERE = Path(__file__).resolve().parent
_PSD_DIR = _HERE.parent  # 05_evaluation/psd
sys.path.insert(0, str(_PSD_DIR))

from psd_diagnostics_core import run_psd_pipeline, to_json_serializable  # noqa: E402
from psd_topology_metrics import connectivity_density, connectivity_probability  # noqa: E402

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

_BORDER_WIDTH = 1
_N_BLOCKS = (2, 2, 2)  # (Z, Y, X)


def _axis_bounds(size: int, n: int) -> List[Tuple[int, int]]:
    """As-equal-as-possible split of [0, size) into n contiguous pieces."""
    base = size // n
    rem = size % n
    bounds = []
    start = 0
    for i in range(n):
        length = base + (1 if i < rem else 0)
        bounds.append((start, start + length))
        start += length
    return bounds


def _block_list(shape: Tuple[int, int, int]) -> List[Dict[str, Tuple[int, int]]]:
    zb = _axis_bounds(shape[0], _N_BLOCKS[0])
    yb = _axis_bounds(shape[1], _N_BLOCKS[1])
    xb = _axis_bounds(shape[2], _N_BLOCKS[2])
    blocks = []
    idx = 0
    for z0, z1 in zb:
        for y0, y1 in yb:
            for x0, x1 in xb:
                blocks.append({"idx": idx, "z": (z0, z1), "y": (y0, y1), "x": (x0, x1)})
                idx += 1
    return blocks


def _face_aware_trim_bounds(
    block: Dict, full_shape: Tuple[int, int, int], bw: int = _BORDER_WIDTH
) -> Tuple[Tuple[int, int], Tuple[int, int], Tuple[int, int]]:
    """Return (z0,z1),(y0,y1),(x0,x1) trimmed by bw only on faces that are
    TRUE outer faces of the whole volume (not on internal split faces)."""
    (z0, z1), (y0, y1), (x0, x1) = block["z"], block["y"], block["x"]
    Z, Y, X = full_shape
    ez0 = z0 + bw if z0 == 0 else z0
    ez1 = z1 - bw if z1 == Z else z1
    ey0 = y0 + bw if y0 == 0 else y0
    ey1 = y1 - bw if y1 == Y else y1
    ex0 = x0 + bw if x0 == 0 else x0
    ex1 = x1 - bw if x1 == X else x1
    return (ez0, ez1), (ey0, ey1), (ex0, ex1)


def _block_slice(arr: np.ndarray, bounds) -> np.ndarray:
    (z0, z1), (y0, y1), (x0, x1) = bounds
    return arr[z0:z1, y0:y1, x0:x1]


def _distance_stats(arr: np.ndarray) -> Dict[str, Optional[float]]:
    if arr.size == 0:
        return {"degenerate": None, "mean_um": None, "median_um": None, "sd_um": None, "n_voxels": 0}
    degenerate = bool(arr.max() == 0.0 and arr.min() == 0.0)
    if degenerate:
        return {
            "degenerate": True,
            "mean_um": None,
            "median_um": None,
            "sd_um": None,
            "n_voxels": int(arr.size),
        }
    return {
        "degenerate": False,
        "mean_um": float(np.mean(arr)),
        "median_um": float(np.median(arr)),
        "sd_um": float(np.std(arr)),
        "n_voxels": int(arr.size),
    }


def process_run(run_name: str, block_indices: Optional[List[int]] = None) -> None:
    import nibabel as nib
    import tifffile

    run_dir = _SOURCE_ROOT / run_name
    config = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))

    pore_label = int(config["pore_label"])
    spacing = tuple(float(v) for v in config["voxel_spacing"])
    voxel_size_um = float(np.mean(spacing))
    bin_edges_um = np.array(config["extended_bin_edges_um"], dtype=np.float64)
    input_path = config["input"]

    print(f"\n=== {run_name} ===")
    print(f"Loading segmentation: {input_path}")
    t0 = time.time()
    labeled_vol = np.asarray(nib.load(input_path).dataobj)
    pore_mask = labeled_vol == pore_label
    del labeled_vol
    shape = pore_mask.shape
    print(f"  shape={shape}  pore voxels={int(pore_mask.sum()):,}  load_time={time.time()-t0:.1f}s")

    blocks = _block_list(shape)
    if block_indices is not None:
        blocks = [b for b in blocks if b["idx"] in block_indices]

    dest_blocks_dir = _DEST_ROOT / run_name / "blocks"
    source_blocks_dir = run_dir / "blocks"

    for block in blocks:
        idx = block["idx"]
        (z0, z1), (y0, y1), (x0, x1) = block["z"], block["y"], block["x"]
        block_label = f"block_{idx:03d}"
        print(f"\n--- {run_name} / {block_label}  bounds=Z{z0}:{z1}/Y{y0}:{y1}/X{x0}:{x1} ---")
        t_block = time.time()

        # ------------------------------------------------------------
        # PSD (face-aware border-trimmed pore mask, same bin edges as
        # the parent whole-volume run).
        # ------------------------------------------------------------
        psd_bounds = _face_aware_trim_bounds(block, shape)
        block_pore_mask_psd = _block_slice(pore_mask, psd_bounds)

        t0 = time.time()
        result = run_psd_pipeline(
            block_pore_mask_psd,
            spacing,
            use_chunking=True,
            chunk_size=(128, 128, 128),
            halo_width=50,
            exclude_borders=False,  # already face-aware-trimmed above
            bin_edges_um=bin_edges_um,
            use_gpu=False,  # GPU EDT known broken in this env (CUDA<12); skip the failed attempt
            diagnostics_cfg={"run_tag": f"{run_name}_{block_label}"},
        )
        psd = result["psd"]
        t_psd = time.time() - t0
        print(f"  PSD done in {t_psd:.1f}s  total_pore_voxels={psd['total_pore_voxels']:,}")

        # ------------------------------------------------------------
        # Euler / connectivity density / gamma (NO border trim, matches
        # how the full-volume run treats these -- computed on the block's
        # own raw pore mask, un-trimmed).
        # ------------------------------------------------------------
        block_pore_mask_raw = _block_slice(pore_mask, (block["z"], block["y"], block["x"]))
        t0 = time.time()
        conn = connectivity_density(block_pore_mask_raw, voxel_size_um)
        gamma = connectivity_probability(block_pore_mask_raw)
        t_topo = time.time() - t0
        print(f"  Euler/gamma done in {t_topo:.1f}s  euler={conn['euler_number']}  gamma={gamma:.4f}")

        # ------------------------------------------------------------
        # Distance-map means: slice the ALREADY-computed full-volume
        # .tif arrays (face-aware border-trimmed), no fresh EDT.
        # ------------------------------------------------------------
        dist_bounds = psd_bounds  # same face-aware trim rule
        dist_stats: Dict[str, Dict] = {}
        t0 = time.time()
        for key, fname in _DIST_FILES.items():
            path = run_dir / fname
            if not path.is_file():
                dist_stats[key] = {"degenerate": None, "error": "file not found"}
                continue
            full_arr = tifffile.imread(str(path))
            block_arr = _block_slice(full_arr, dist_bounds)
            dist_stats[key] = _distance_stats(block_arr)
            del full_arr, block_arr
        t_dist = time.time() - t0
        print(f"  Distance-map stats done in {t_dist:.1f}s")

        block_elapsed = time.time() - t_block
        print(f"  Block total: {block_elapsed:.1f}s")

        out = {
            "run_name": run_name,
            "block_index": idx,
            "n_blocks_split": list(_N_BLOCKS),
            "block_bounds_zyx": {"z": [z0, z1], "y": [y0, y1], "x": [x0, x1]},
            "psd_border_trimmed_bounds_zyx": {
                "z": list(psd_bounds[0]), "y": list(psd_bounds[1]), "x": list(psd_bounds[2]),
            },
            "voxel_spacing_um": list(spacing),
            "psd": {
                "total_pore_voxels": int(psd["total_pore_voxels"]),
                "bin_centers_um": psd["bin_centers_um"].tolist(),
                "bin_edges_um": psd["bin_edges_um"].tolist(),
                "volume_counts": [int(v) for v in psd["volume_counts"]],
                "cumulative_volume": psd["cumulative_volume"].tolist(),
                "differential_volume": psd["differential_volume"].tolist(),
            },
            "euler_number": conn["euler_number"],
            "connectivity_density_per_mm3": conn["connectivity_density_per_mm3"],
            "connectivity_probability_gamma": gamma,
            "distance_maps": dist_stats,
            "skipped_metrics": {
                "degree_of_anisotropy": "skipped -- needs a percolating mask not guaranteed at block scale",
                "tortuosity_axis0/1/2": "skipped -- same reason, and was >13h of the ~14h full-run cost even at full-volume scale",
            },
            "caveats": (
                "PSD and euler/connectivity/gamma are computed on this block's own "
                "cropped mask; pores/loops/cavities that cross an internal split face "
                "are truncated/cut, which biases these metrics relative to a true "
                "full-volume measurement (unavoidable at block scale, not a bug). "
                "Distance-map stats are NOT subject to this bias -- they are sliced "
                "from the full-volume EDT, which had complete 3D context."
            ),
            "elapsed_s": {"psd": t_psd, "euler_gamma": t_topo, "distance_maps": t_dist, "total": block_elapsed},
        }

        for out_dir in (source_blocks_dir / block_label, dest_blocks_dir / block_label):
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / "block_summary.json"
            with out_path.open("w", encoding="utf-8") as fh:
                json.dump(to_json_serializable(out), fh, indent=2)
            print(f"  Wrote: {out_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--run", choices=_RUNS, required=True)
    parser.add_argument("--blocks", type=int, nargs="*", default=None,
                         help="Subset of block indices to run (default: all 8).")
    args = parser.parse_args()
    process_run(args.run, block_indices=args.blocks)
