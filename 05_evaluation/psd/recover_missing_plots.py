"""Recovery script: regenerate missing plots for existing PSD run folders.

Usage
-----
::

    python recover_missing_plots.py <run_folder_path>

This script reads the existing result_psd.json from a completed run folder
and regenerates the missing plot files:
  - psd_hist_30bins.png
  - psd_kde.png
  - psd_20bins_30_150um.png
  - psd_raw_data.csv

It does NOT re-run the PSD pipeline; only reproduces output artifacts.
"""

import json
import sys
from pathlib import Path

# Non-interactive backend — set before pyplot import
import matplotlib
matplotlib.use("Agg")

import numpy as np


def recover_plots(run_folder: Path) -> None:
    """Regenerate plots from existing result_psd.json.
    
    Parameters
    ----------
    run_folder : Path
        Path to the run folder containing result_psd.json
    """
    run_folder = Path(run_folder)
    result_file = run_folder / "result_psd.json"
    
    if not result_file.exists():
        print(f"ERROR: {result_file} not found", file=sys.stderr)
        sys.exit(1)
    
    # Load result
    try:
        with result_file.open("r", encoding="utf-8") as fh:
            psd_dict = json.load(fh)
    except Exception as exc:
        print(f"ERROR: Failed to load {result_file}: {exc}", file=sys.stderr)
        sys.exit(1)
    
    # Import plotting helpers
    try:
        from psd_diagnostics_core import plot_psd_extras
    except ImportError as exc:
        print(f"ERROR: Cannot import psd_diagnostics_core: {exc}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Regenerating plots for: {run_folder}")
    
    # --- Regenerate psd_hist_30bins.png and psd_kde.png ---
    print("  Generating psd_30bins_microbial_active_domain.png, psd_kde.png...")
    try:
        plot_psd_extras(psd_dict, run_folder)
    except Exception as exc:
        print(f"  WARNING: plot_psd_extras failed: {exc}")

    # --- Regenerate psd_20bins_30_150um.png ---
    print("  Generating psd_20bins_30_150um.png...")
    try:
        _write_20bins_plot(run_folder, psd_dict)
    except Exception as exc:
        print(f"  WARNING: _write_20bins_plot failed: {exc}")
    
    # --- Regenerate psd_raw_data.csv ---
    print("  Generating psd_raw_data.csv...")
    try:
        _write_raw_csv_from_dict(run_folder, psd_dict)
    except Exception as exc:
        print(f"  WARNING: _write_raw_csv_from_dict failed: {exc}")
    
    print(f"Done: {run_folder}")


def _write_20bins_plot(run_dir: Path, psd_dict: dict) -> None:
    """Generate psd_20bins_30_150um.png — per-bin pore volume fraction, 30–150 µm."""
    import matplotlib.pyplot as plt

    bin_centers_um = np.asarray(psd_dict.get("bin_centers_um", np.array([])))
    volume_counts = np.asarray(psd_dict.get("volume_counts", np.array([])))
    total_pore_voxels = int(psd_dict.get("total_pore_voxels", max(int(volume_counts.sum()), 1)))

    if bin_centers_um.size == 0:
        return

    volume_fraction = volume_counts / total_pore_voxels

    # Filter to [30, 150] µm range
    mask = (bin_centers_um >= 30.0) & (bin_centers_um <= 150.0)
    filtered_centers = bin_centers_um[mask]
    filtered_fracs = volume_fraction[mask]

    if filtered_centers.size == 0:
        return

    target_bin_edges = np.logspace(np.log10(30.0), np.log10(150.0), 21)
    target_bin_centers = (target_bin_edges[:-1] + target_bin_edges[1:]) / 2

    hist_counts, _ = np.histogram(filtered_centers, bins=target_bin_edges,
                                   weights=filtered_fracs)

    fig, ax = plt.subplots(figsize=(10, 6), dpi=100)

    ax.bar(
        target_bin_centers,
        hist_counts,
        width=np.diff(target_bin_edges),
        color="#e67300",
        edgecolor="white",
        linewidth=0.5,
        alpha=0.85,
        label="Pore volume fraction per bin (30–150 µm)",
    )

    ax.set_xlabel("Pore Diameter (µm)", fontsize=11)
    ax.set_ylabel("Pore volume fraction", fontsize=11)
    ax.set_title("Microbial Active Domain — PSD (20 bins, 30–150 µm)",
                  fontsize=12, fontweight="bold")
    ax.set_xscale("log")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend()
    
    f = run_dir / "psd_20bins_30_150um.png"
    fig.savefig(str(f), dpi=100, bbox_inches="tight")
    plt.close(fig)


def _write_raw_csv_from_dict(run_dir: Path, psd_dict: dict) -> None:
    """Generate psd_raw_data.csv from psd_dict (copied from run_psd_diagnostics logic)."""
    import csv
    
    bin_centers_px = np.asarray(psd_dict.get("bin_centers_px", np.array([])))
    bin_centers_um = np.asarray(psd_dict.get("bin_centers_um", np.array([])))
    volume_counts = np.asarray(psd_dict.get("volume_counts", np.array([])))
    cumulative_volume = np.asarray(psd_dict.get("cumulative_volume", np.array([])))
    differential_volume = np.asarray(psd_dict.get("differential_volume", np.array([])))
    
    n = len(bin_centers_um)
    rows = []
    for i in range(n):
        rows.append({
            "Diameter_px": float(bin_centers_px[i]) if i < len(bin_centers_px) else 0.0,
            "Diameter_um": float(bin_centers_um[i]),
            "Volume_Count": int(volume_counts[i]) if i < len(volume_counts) else 0,
            "Cumulative_Porosity": float(cumulative_volume[i]),
            "Differential_PSD": float(differential_volume[i]),
        })
    
    column_names = ("Diameter_px", "Diameter_um", "Volume_Count", 
                    "Cumulative_Porosity", "Differential_PSD")
    
    path = run_dir / "psd_raw_data.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=column_names)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python recover_missing_plots.py <run_folder_path>", 
              file=sys.stderr)
        sys.exit(1)
    
    run_folder = Path(sys.argv[1])
    recover_plots(run_folder)


if __name__ == "__main__":
    main()
