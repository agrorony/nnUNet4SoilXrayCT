"""Euler-number connectivity function chi(r) + crossover-radius sweep.

Standalone re-creation of the ad-hoc script from the 2026-08-26 Track E
crossover-radius session (see Topology_Metrics_Aug2026/crossover_radius_summary.md).
That script was never committed; this re-implements it from the documented
methodology, including the one real bug-and-fix that session found:

    porespy.filters.local_thickness(method='imj') assigns nonzero thickness
    to a shell of voxels OUTSIDE the true binary pore mask (~22% extra
    voxels in the original bug repro). Every r-threshold must therefore be
    ANDed with the raw pore mask, never applied to the diameter map alone:

        pore_mask_r = raw_pore_mask & (diameter_map_px >= r_px)

Diameter-map convention matches psd_diagnostics_core.py exactly (same
algorithm, so this script's chi(r=smallest edge) sanity-checks against
that run's own recorded full-mask euler_number):
    - EDT computed with UNIT (1,1,1) voxel spacing (psd_diagnostics_core's
      "legacy behaviour" -- diameter map lives in voxel units, not um).
    - porespy.filters.local_thickness(im, dt=edt_map, method='imj',
      smooth=False), result * 2 (radius -> diameter), in voxel units (px).
    - r_px = r_um / voxel_size_um (voxel_size_um = mean of the run's
      isotropic voxel spacing, matching run_psd_diagnostics.py's
      `voxel_size_um = float(np.mean(spacing))`).
    - euler_number computed via skimage.measure.euler_number(mask,
      connectivity=3) directly on the (unthresholded-by-border) mask --
      psd_topology_metrics.connectivity_density() does NOT border-trim
      before calling sk_euler_number, and the recorded 'euler_number' in
      summary.json/result_psd.json comes from that same untrimmed call, so
      no border trim is applied here either (verified by code inspection
      2026-08-29; this is why the prior session's diff=0 sanity check held
      exactly, not just approximately).

Usage
-----
    python compute_chi_r_sweep.py \\
        --input <labeled volume .nii.gz/.npy/.tif> \\
        --pore-label <int> \\
        --voxel-size-um <float> \\
        --run-dir <psd_diag_..._run/ containing result_psd.json + summary.json> \\
        --output-csv <path/to/chi_r_<run>.csv>

Output CSV columns: r_um, r_px, chi, n_pore_voxels_at_r
Also prints the two required sanity checks (chi@smallest-r vs recorded
euler_number; back-calculated volume vs -euler/connectivity_density) and,
if a sign-change crossover exists, the log-interpolated r*.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Optional

import numpy as np
from scipy.ndimage import distance_transform_edt
from skimage.measure import euler_number as sk_euler_number


def _load_labeled_volume(path: Path) -> np.ndarray:
    name_lower = path.name.lower()
    if name_lower.endswith(".nii") or name_lower.endswith(".nii.gz"):
        import nibabel as nib
        img = nib.load(str(path))
        return np.asarray(img.dataobj)
    if name_lower.endswith(".npy"):
        return np.load(str(path))
    if name_lower.endswith(".tif") or name_lower.endswith(".tiff"):
        import tifffile
        return tifffile.imread(str(path))
    raise ValueError(f"Unsupported input format: {path}")


def compute_diameter_map_px(raw_pore_mask: np.ndarray) -> np.ndarray:
    """Reproduce psd_diagnostics_core._compute_opening_map exactly.

    EDT at unit (1,1,1) spacing -> porespy local_thickness(method='imj',
    smooth=False) on that EDT -> *2 (radius -> diameter), voxel units.
    """
    from porespy.filters import local_thickness as _ps_local_thickness

    print("  Computing EDT (unit spacing, matches psd_diagnostics_core legacy convention)...")
    edt_map = distance_transform_edt(raw_pore_mask).astype(np.float64)
    print(f"  Max EDT radius: {edt_map.max():.2f} voxels")
    print("  Computing local_thickness (porespy, method='imj', smooth=False)...")
    lt = _ps_local_thickness(raw_pore_mask, dt=edt_map, method="imj", smooth=False)
    diameter_map_px = (np.asarray(lt) * 2).astype(np.float32)
    print(f"  Max diameter: {diameter_map_px.max():.2f} voxels")
    return diameter_map_px


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True)
    ap.add_argument("--pore-label", type=int, required=True)
    ap.add_argument("--voxel-size-um", type=float, required=True,
                     help="Isotropic voxel size in um (mean of the run's voxel_spacing).")
    ap.add_argument("--run-dir", required=True,
                     help="Path to the extended-mode run dir with result_psd.json + summary.json.")
    ap.add_argument("--output-csv", required=True)
    ap.add_argument("--run-label", default=None, help="Label for console output only.")
    args = ap.parse_args()

    input_path = Path(args.input)
    run_dir = Path(args.run_dir)
    voxel_size_um = float(args.voxel_size_um)
    run_label = args.run_label or run_dir.name

    result_psd_path = run_dir / "result_psd.json"
    summary_path = run_dir / "summary.json"
    if not result_psd_path.exists():
        print(json.dumps({"error": f"missing {result_psd_path}"}))
        sys.exit(1)
    if not summary_path.exists():
        print(json.dumps({"error": f"missing {summary_path}"}))
        sys.exit(1)

    result_psd = json.loads(result_psd_path.read_text(encoding="utf-8"))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    bin_edges_um = np.asarray(result_psd["bin_edges_um"], dtype=np.float64)
    bin_edges_um = np.unique(bin_edges_um[bin_edges_um > 0])
    recorded_euler = int(summary["euler_number"])
    recorded_conn_density = float(summary["connectivity_density_per_mm3"])

    print(f"=== {run_label} ===")
    print(f"Loading labeled volume: {input_path}")
    vol = _load_labeled_volume(input_path)
    print(f"  shape={vol.shape} dtype={vol.dtype}")

    raw_pore_mask = (vol == args.pore_label)
    n_pore_total = int(raw_pore_mask.sum())
    n_total_voxels = int(raw_pore_mask.size)
    print(f"  raw pore voxels: {n_pore_total:,} / {n_total_voxels:,} ({100*n_pore_total/n_total_voxels:.3f}%)")

    # --- Sanity check 2: volume back-calculation --------------------------
    back_calc_volume_mm3 = n_total_voxels * (voxel_size_um / 1000.0) ** 3
    if recorded_conn_density != 0:
        recorded_volume_mm3 = -recorded_euler / recorded_conn_density
    else:
        recorded_volume_mm3 = float("nan")
    vol_rel_diff = (
        abs(back_calc_volume_mm3 - recorded_volume_mm3) / recorded_volume_mm3
        if recorded_volume_mm3 not in (0, float("nan")) and not np.isnan(recorded_volume_mm3)
        else float("nan")
    )
    print(f"  Back-calc volume: {back_calc_volume_mm3:.6f} mm^3")
    print(f"  Recorded volume (from -euler/conn_density): {recorded_volume_mm3:.6f} mm^3")
    print(f"  Relative diff: {vol_rel_diff:.3e}")
    volume_check_pass = np.isfinite(vol_rel_diff) and vol_rel_diff < 1e-6

    # --- Diameter map + leak-masking fix -----------------------------------
    diameter_map_px = compute_diameter_map_px(raw_pore_mask)
    pore_mask_true = raw_pore_mask & (diameter_map_px > 0)
    n_leaked = int((diameter_map_px > 0).sum()) - int(((diameter_map_px > 0) & raw_pore_mask).sum())
    n_pore_missing_thickness = int(raw_pore_mask.sum()) - int(pore_mask_true.sum())
    print(f"  Leaked non-pore voxels with diameter>0: {n_leaked:,}")
    print(f"  True pore voxels with diameter==0 (excluded from pore_mask_true): {n_pore_missing_thickness:,}")

    # --- chi(r) sweep -------------------------------------------------------
    rows = []
    for r_um in bin_edges_um:
        r_px = float(r_um) / voxel_size_um
        mask_r = raw_pore_mask & (diameter_map_px >= r_px)
        n_at_r = int(mask_r.sum())
        if n_at_r == 0:
            chi = 0
        else:
            chi = int(sk_euler_number(mask_r, connectivity=3))
        rows.append({"r_um": float(r_um), "r_px": r_px, "chi": chi, "n_pore_voxels_at_r": n_at_r})

    # --- Sanity check 1: chi at smallest r == recorded full-mask euler ----
    chi_at_smallest = rows[0]["chi"]
    sanity1_pass = (chi_at_smallest == recorded_euler)
    print(f"  chi(r={rows[0]['r_um']:.3f} um) = {chi_at_smallest}")
    print(f"  recorded full-mask euler_number = {recorded_euler}")
    print(f"  SANITY CHECK 1 (chi@min_r == recorded euler): {'PASS' if sanity1_pass else 'FAIL'}")
    print(f"  SANITY CHECK 2 (volume back-calc): {'PASS' if volume_check_pass else 'FAIL'}")

    if not sanity1_pass:
        print(f"  *** STOPPING processing of {run_label}: sanity check 1 failed. ***")
        rows_out_path = Path(args.output_csv)
        rows_out_path.parent.mkdir(parents=True, exist_ok=True)
        with rows_out_path.with_suffix(".FAILED_SANITY_CHECK.txt").open("w", encoding="utf-8") as fh:
            fh.write(
                f"chi(r=min)={chi_at_smallest} != recorded euler_number={recorded_euler}\n"
                f"Volume check pass={volume_check_pass}\n"
            )
        sys.exit(2)

    # --- Monotonicity check (informational only, not blocking) ------------
    chis = np.array([r["chi"] for r in rows])
    diffs = np.diff(chis)
    n_violations = int((diffs < 0).sum())
    print(f"  Monotonicity: {n_violations} non-increasing-to-increasing violations out of {len(diffs)} steps"
          f" (strict monotonic-non-decrease not required/expected; small wobbles are normal per prior session).")

    # --- Crossover radius r* (log-r interpolation of sign change) ---------
    r_star = None
    resolution_limited = None
    trend = None
    signs = np.sign(chis)
    sign_change_idx = None
    for i in range(len(signs) - 1):
        if signs[i] != 0 and signs[i + 1] != 0 and signs[i] != signs[i + 1]:
            sign_change_idx = i
            break
    if sign_change_idx is not None:
        r0, r1 = rows[sign_change_idx]["r_um"], rows[sign_change_idx + 1]["r_um"]
        c0, c1 = rows[sign_change_idx]["chi"], rows[sign_change_idx + 1]["chi"]
        log_r0, log_r1 = np.log10(r0), np.log10(r1)
        frac = -c0 / (c1 - c0)
        log_r_star = log_r0 + frac * (log_r1 - log_r0)
        r_star = float(10 ** log_r_star)
        trend = "negative_to_positive" if c0 < c1 else "positive_to_negative"
        resolution_limited = bool(r_star < 3 * voxel_size_um)
        print(f"  Crossover r* = {r_star:.2f} um (between r={r0:.2f} [chi={c0}] and r={r1:.2f} [chi={c1}])")
        print(f"  Trend: {trend}")
        print(f"  Resolution-limited (r* within ~2-3 voxel widths of {voxel_size_um} um voxel): {resolution_limited}")
    else:
        if np.all(chis >= 0):
            trend = "all_positive_in_range"
        elif np.all(chis <= 0):
            trend = "all_negative_in_range"
        else:
            trend = "no_clean_single_crossing_found"
        print(f"  No sign-change crossover found in range. Trend: {trend}")

    # --- Write CSV ----------------------------------------------------------
    out_path = Path(args.output_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["r_um", "r_px", "chi", "n_pore_voxels_at_r"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote: {out_path}")

    meta = {
        "run_label": run_label,
        "input": str(input_path),
        "pore_label": args.pore_label,
        "voxel_size_um": voxel_size_um,
        "n_total_voxels": n_total_voxels,
        "n_pore_voxels_raw": n_pore_total,
        "n_leaked_diameter_shell_voxels": n_leaked,
        "n_pore_voxels_missing_thickness": n_pore_missing_thickness,
        "sanity_check_1_chi_at_min_r_matches_recorded_euler": sanity1_pass,
        "sanity_check_2_volume_back_calc": volume_check_pass,
        "back_calc_volume_mm3": back_calc_volume_mm3,
        "recorded_volume_mm3": recorded_volume_mm3,
        "volume_rel_diff": vol_rel_diff,
        "chi_at_min_r": chi_at_smallest,
        "recorded_euler_number": recorded_euler,
        "r_star_um": r_star,
        "trend": trend,
        "resolution_limited": resolution_limited,
        "n_monotonicity_violations": n_violations,
    }
    meta_path = out_path.with_suffix(".meta.json")
    with meta_path.open("w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
    print(f"Wrote: {meta_path}")


if __name__ == "__main__":
    main()
