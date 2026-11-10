"""Part 2 step 1-2 -- for each volume that qualified in Part 1, determine
the largest safe symmetric center-aligned cubic crop: propose the 90%-cap
size, then scan intensity in nested-cube shells moving outward from the
current (known-good) crop boundary toward the proposed boundary, stopping
at the first shell that shows a sample-holder/mount signature (a sharply
different, low-texture-variance ring: either a dense/bright plateau or a
uniform air-gap trough relative to normal soil-shell texture).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from raw_volume_io import read_centered_cube

HERE = Path(__file__).resolve().parent
RUN_DIR = HERE.parent

SHELL_STEP = 10  # voxels of half-extent per shell scanned

# Anomaly heuristics, evaluated per shell against the interior (known-good
# crop) baseline:
#  - saturated: voxel >= 99.9th percentile of the whole loaded (max-candidate)
#    cube -- a dense/metal holder ring should show a jump in this fraction.
#  - near_zero: voxel <= max(5, 0.1th percentile) -- an air-gap ring should
#    show a jump in this fraction combined with a collapse in shell std
#    (uniform air, not textured soil/pore edge).
SATURATED_JUMP_PP = 0.02   # +2 percentage points over baseline triggers a look
NEAR_ZERO_JUMP_PP = 0.15   # +15 percentage points over baseline
STD_COLLAPSE_RATIO = 0.30  # shell std below 30% of baseline std, combined
                            # with a near_zero jump, confirms a uniform gap


def shell_stats(cube: np.ndarray, r_lo: int, r_hi: int, center: int,
                 sat_thresh: float, zero_thresh: float) -> dict:
    """Stats for the nested-cube shell {v : r_lo <= chebyshev_dist(v) < r_hi}."""
    outer = _subcube(cube, center, r_hi)
    if r_lo == 0:
        shell = outer
    else:
        inner = _subcube(cube, center, r_lo)
        shell = _ring_voxels(outer, inner)
    shell = shell.ravel()
    n = shell.size
    return {
        "n_voxels": int(n),
        "mean": float(shell.mean()),
        "std": float(shell.std()),
        "frac_saturated": float(np.mean(shell >= sat_thresh)),
        "frac_near_zero": float(np.mean(shell <= zero_thresh)),
    }


def _subcube(cube: np.ndarray, center: int, half: int) -> np.ndarray:
    lo, hi = center - half, center + half
    return cube[lo:hi, lo:hi, lo:hi]


def _ring_voxels(outer: np.ndarray, inner: np.ndarray) -> np.ndarray:
    mask = np.ones(outer.shape, dtype=bool)
    off = (outer.shape[0] - inner.shape[0]) // 2
    mask[off: off + inner.shape[0], off: off + inner.shape[0], off: off + inner.shape[0]] = False
    return outer[mask]


def scan_volume(key: str, cfg: dict) -> dict:
    raw_z, raw_h, raw_w = cfg["raw_shape_zhw"]
    cur_z, cur_h, cur_w = cfg["current_crop_shape_zhw"]
    # The "current crop" tif isn't always perfectly cubic (e.g. Bnei Re'em's
    # nlm_volume.tif is 652x650x650 -- likely a +2 Z edge artifact from the
    # inference-chunk concatenation step, not the crop itself). Use the
    # smallest axis as the known-good interior baseline size so it's a
    # subset of every axis actually trusted so far.
    if not (cur_z == cur_h == cur_w):
        print(f"[{key}] NOTE: current crop not perfectly cubic {cfg['current_crop_shape_zhw']} "
              f"-- using min axis as the known-good baseline size.")
    current_size = min(cur_z, cur_h, cur_w)

    shortest_raw_axis = min(raw_z, raw_h, raw_w)
    proposed_max = int(0.9 * shortest_raw_axis)
    proposed_max = min(proposed_max, raw_z, raw_h, raw_w)
    print(f"[{key}] raw={cfg['raw_shape_zhw']} current_crop={current_size} "
          f"shortest_raw_axis={shortest_raw_axis} proposed_max={proposed_max}")

    if proposed_max <= current_size:
        print(f"[{key}] proposed_max ({proposed_max}) <= current crop ({current_size}) "
              f"even though Part 1 flagged margin -- keeping existing crop.")
        return {
            "raw_shape_zhw": cfg["raw_shape_zhw"],
            "current_crop_size": current_size,
            "proposed_max_size": proposed_max,
            "final_crop_size": current_size,
            "holder_signature_shell": None,
            "shells": [],
            "decision": "kept existing crop -- proposed 90%-cap size did not exceed current crop",
        }

    print(f"[{key}] loading centered cube of size {proposed_max} from raw stack "
          f"({cfg['raw_slice_dir']}) ...")
    cube = read_centered_cube(Path(cfg["raw_slice_dir"]), proposed_max).astype(np.float32)
    print(f"[{key}] loaded, shape={cube.shape}, dtype was uint16, "
          f"value range=[{cube.min():.0f}, {cube.max():.0f}]")

    sat_thresh = float(np.percentile(cube, 99.9))
    zero_thresh = max(5.0, float(np.percentile(cube, 0.1)))
    print(f"[{key}] saturation threshold (99.9th pct)={sat_thresh:.1f}  "
          f"near-zero threshold={zero_thresh:.1f}")

    center = proposed_max // 2
    baseline_half = current_size // 2
    baseline = shell_stats(cube, 0, baseline_half, center, sat_thresh, zero_thresh)
    print(f"[{key}] baseline (interior, known-good crop) stats: {baseline}")

    shells = []
    holder_shell_r = None
    r_lo = baseline_half
    max_half = proposed_max // 2
    while r_lo < max_half:
        r_hi = min(r_lo + SHELL_STEP, max_half)
        st = shell_stats(cube, r_lo, r_hi, center, sat_thresh, zero_thresh)
        st["r_lo"] = r_lo
        st["r_hi"] = r_hi
        st["edge_size_at_r_hi"] = 2 * r_hi

        sat_jump = st["frac_saturated"] - baseline["frac_saturated"]
        zero_jump = st["frac_near_zero"] - baseline["frac_near_zero"]
        std_ratio = st["std"] / baseline["std"] if baseline["std"] > 0 else 1.0
        is_anomaly = False
        reason = None
        if sat_jump > SATURATED_JUMP_PP:
            is_anomaly = True
            reason = f"saturated-voxel fraction jumped +{sat_jump*100:.2f}pp vs interior baseline (dense/metal holder signature)"
        elif zero_jump > NEAR_ZERO_JUMP_PP and std_ratio < STD_COLLAPSE_RATIO:
            is_anomaly = True
            reason = (f"near-zero fraction jumped +{zero_jump*100:.2f}pp AND shell texture collapsed "
                       f"to {std_ratio*100:.1f}% of interior std (uniform air-gap signature)")
        st["is_anomaly"] = is_anomaly
        st["anomaly_reason"] = reason
        shells.append(st)
        print(f"[{key}]   shell r=[{r_lo},{r_hi}) edge={2*r_hi}: mean={st['mean']:.1f} std={st['std']:.1f} "
              f"sat={st['frac_saturated']*100:.3f}% zero={st['frac_near_zero']*100:.2f}% "
              f"anomaly={is_anomaly}" + (f" ({reason})" if reason else ""))

        if is_anomaly:
            holder_shell_r = r_lo
            break
        r_lo = r_hi

    if holder_shell_r is not None:
        final_size = 2 * holder_shell_r
        decision = (f"holder/mount signature detected at shell starting r={holder_shell_r} "
                    f"(edge {final_size}) -- stopped at the shell just before it")
    else:
        final_size = 2 * max_half
        decision = "no holder/mount signature found before reaching the 90%-cap boundary -- using proposed_max"

    final_size = max(final_size, current_size)
    print(f"[{key}] FINAL crop size decision: {final_size}  ({decision})")

    del cube
    return {
        "raw_shape_zhw": cfg["raw_shape_zhw"],
        "current_crop_size": current_size,
        "proposed_max_size": proposed_max,
        "final_crop_size": final_size,
        "holder_signature_shell_r": holder_shell_r,
        "saturation_threshold": sat_thresh,
        "near_zero_threshold": zero_thresh,
        "baseline_interior_stats": baseline,
        "shells": shells,
        "decision": decision,
    }


def main() -> None:
    with (RUN_DIR / "part1_margin_report.json").open(encoding="utf-8") as fh:
        part1 = json.load(fh)

    report = {}
    for key, cfg in part1.items():
        if not cfg["qualifies_for_part2"]:
            print(f"[{key}] Part 1 said insufficient margin -- skipping Part 2, keeping existing crop.")
            report[key] = {
                "final_crop_size": cfg["current_crop_shape_zhw"][0],
                "decision": "insufficient extra volume (Part 1), kept existing crop",
            }
            continue
        report[key] = scan_volume(key, cfg)
        print()

    out_path = RUN_DIR / "part2_holder_safety_report.json"
    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
