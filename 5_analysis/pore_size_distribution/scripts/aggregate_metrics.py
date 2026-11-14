"""Step 2: aggregate per-subvolume PSD outputs into subvolume_metrics.csv.

Porosity is taken directly from the extraction manifest (untrimmed, exact
np.mean of the pore mask) rather than from the PSD run's total_pore_voxels
(which reflects a 1-voxel border-exclusion trim internal to the local-thickness
pipeline) -- this keeps "porosity" an unambiguous, trim-independent physical
quantity. Diameter stats and the 30-150um fraction come from the PSD run's
psd_table.csv (binned local-thickness distribution), which is unaffected by the
trim distinction at the >=300**3-voxel subvolume scale.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pandas as pd

OUT_ROOT = Path(__file__).resolve().parents[1]
PSD_RUNS = OUT_ROOT / "psd_runs"
MANIFEST = json.loads((OUT_ROOT / "subvolume_extraction_manifest.json").read_text())


def find_run_dir(run_name: str) -> Path:
    matches = sorted(PSD_RUNS.glob(f"psd_diag_*_{run_name}"))
    if not matches:
        raise FileNotFoundError(f"No psd_diag run dir found for {run_name}")
    return matches[-1]


def median_diameter(df: pd.DataFrame) -> float:
    cp = df["Cumulative_Porosity"].to_numpy()
    d = df["Diameter_um"].to_numpy()
    if cp[-1] <= 0:
        return float("nan")
    cp_norm = cp / cp[-1]
    idx = np.searchsorted(cp_norm, 0.5)
    if idx == 0:
        return float(d[0])
    if idx >= len(cp_norm):
        return float(d[-1])
    c0, c1 = cp_norm[idx - 1], cp_norm[idx]
    d0, d1 = d[idx - 1], d[idx]
    if c1 == c0:
        return float(d1)
    frac = (0.5 - c0) / (c1 - c0)
    return float(d0 + frac * (d1 - d0))


def main() -> None:
    rows = []
    bin_centers_ref = None

    for soil, entries in MANIFEST.items():
        for entry in entries:
            if entry["excluded"]:
                continue
            run_name = f"{soil}_{entry['subvolume_id']}"
            run_dir = find_run_dir(run_name)
            df = pd.read_csv(run_dir / "psd_table.csv")

            total_pore_voxels = int(df["Volume_Count"].sum())
            porosity = entry["porosity"]  # from extraction, untrimmed

            mean_d = float((df["Diameter_um"] * df["Volume_Count"]).sum() / total_pore_voxels)
            median_d = median_diameter(df)

            in_30_150 = (df["Diameter_um"] >= 30.0) & (df["Diameter_um"] < 150.0)
            frac_30_150_pore = float(df.loc[in_30_150, "Volume_Count"].sum() / total_pore_voxels)
            frac_30_150_total = frac_30_150_pore * porosity

            if bin_centers_ref is None:
                bin_centers_ref = df["Diameter_um"].to_numpy()
            psd_vec = df["Differential_PSD"].to_numpy()

            row = {
                "soil": soil,
                "subvolume_id": entry["subvolume_id"],
                "origin_z": entry["origin_z"],
                "origin_y": entry["origin_y"],
                "origin_x": entry["origin_x"],
                "edge_voxels": entry["edge_voxels"],
                "edge_mm": entry["edge_mm"],
                "porosity": porosity,
                "mean_diameter_um": mean_d,
                "median_diameter_um": median_d,
                "frac_30_150um_of_pore_volume": frac_30_150_pore,
                "frac_30_150um_of_total_volume": frac_30_150_total,
                "total_pore_voxels_trimmed": total_pore_voxels,
                "psd_run_dir": str(run_dir),
            }
            for i, v in enumerate(psd_vec):
                row[f"PSD_bin_{i}_d{bin_centers_ref[i]:.2f}um"] = float(v)
            rows.append(row)
            print(f"{run_name}: porosity={porosity:.4f} mean_d={mean_d:.2f} "
                  f"median_d={median_d:.2f} frac30-150(pore)={frac_30_150_pore:.4f}")

    out_df = pd.DataFrame(rows)
    out_path = OUT_ROOT / "subvolume_metrics.csv"
    out_df.to_csv(out_path, index=False)
    print(f"\nWrote {out_path} ({len(out_df)} rows)")


if __name__ == "__main__":
    main()
