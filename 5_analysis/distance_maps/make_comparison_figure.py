"""One-off comparison figure: Mishmar Ha'Negev vs Bnei Re'em, extended PSD metrics.

Reads the two extended-mode run outputs already on disk (summary.json,
psd_table.csv) plus the freshly-computed mean-distance scalars in
comparison_mean_distances.json (computed directly from the segmented volumes,
not from the saved distance-map .tif files, since those zero-fill unreachable
voxels and would silently bias a naive mean). Produces one PNG with one panel
per extended metric, both soils side by side.
"""
import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

_HERE = __file__.rsplit("\\", 1)[0] if "\\" in __file__ else __file__.rsplit("/", 1)[0]

BNEI_DIR = f"{_HERE}/validation_run/out/psd_diag_20260722T122636_bnei_reem_i4_crop200_CORRECTED_15um"
MISHMAR_DIR = f"{_HERE}/mishmar_run/out/psd_diag_20260722T122619_mishmar_hanegev_maoz3_5p85um_scratch_i2_zcenter200"
DIST_JSON = f"{_HERE}/comparison_mean_distances.json"
OUT_PATH = f"{_HERE}/comparison_mishmar_vs_bnei_reem.png"

# Fixed categorical color assignment, used consistently across every panel.
COLOR_MISHMAR = "#3b7dd8"   # blue
COLOR_BNEI = "#e08214"      # orange
LABEL_MISHMAR = "Mishmar Ha'Negev (5.85 µm)"
LABEL_BNEI = "Bnei Re'em (15 µm, corrected)"

with open(f"{BNEI_DIR}/summary.json") as f:
    bnei_summary = json.load(f)
with open(f"{MISHMAR_DIR}/summary.json") as f:
    mishmar_summary = json.load(f)
with open(DIST_JSON) as f:
    dist = json.load(f)
bnei_dist = dist["bnei_reem_corrected_15um"]
mishmar_dist = dist["mishmar_hanegev_5p85um"]

bnei_psd = pd.read_csv(f"{BNEI_DIR}/psd_table.csv")
mishmar_psd = pd.read_csv(f"{MISHMAR_DIR}/psd_table.csv")

fig, axes = plt.subplots(2, 4, figsize=(20, 9))
fig.suptitle("Extended PSD/connectivity metrics — Mishmar Ha'Negev vs Bnei Re'em", fontsize=15, fontweight="bold")


def two_bar_panel(ax, title, mishmar_val, bnei_val, ylabel, fmt="{:.3g}"):
    bars = ax.bar(
        [LABEL_MISHMAR, LABEL_BNEI], [mishmar_val, bnei_val],
        color=[COLOR_MISHMAR, COLOR_BNEI], width=0.6,
    )
    for b, v in zip(bars, [mishmar_val, bnei_val]):
        label = "N/A" if (v is None or (isinstance(v, float) and np.isnan(v))) else fmt.format(v)
        ax.text(b.get_x() + b.get_width() / 2, b.get_height(), label,
                ha="center", va="bottom", fontsize=9)
    ax.set_title(title, fontsize=11)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.set_xticks([])
    ax.grid(axis="y", alpha=0.25)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)


# 1. Euler number (raw, dimensionless/topological)
two_bar_panel(
    axes[0, 0], "Euler number (χ)",
    mishmar_summary["euler_number"], bnei_summary["euler_number"], "χ (dimensionless)",
)

# 2. Connectivity density (mm^-3, scales with 1/voxel_size^3)
two_bar_panel(
    axes[0, 1], "Connectivity density",
    mishmar_summary["connectivity_density_per_mm3"], bnei_summary["connectivity_density_per_mm3"],
    "mm⁻³",
)

# 3. Connectivity probability Gamma (dimensionless)
two_bar_panel(
    axes[0, 2], "Connectivity probability (Γ)",
    mishmar_summary["connectivity_probability_gamma"], bnei_summary["connectivity_probability_gamma"],
    "Γ (0–1)",
)

# 4. Degree of anisotropy (dimensionless)
two_bar_panel(
    axes[0, 3], "Degree of anisotropy (DA)",
    mishmar_summary["degree_of_anisotropy"], bnei_summary["degree_of_anisotropy"],
    "DA (0–1)",
)

# 5. Tortuosity per axis (dimensionless, grouped bar)
ax = axes[1, 0]
axes_labels = ["axis0 (Z)", "axis1 (Y)", "axis2 (X)"]
mishmar_tort = [mishmar_summary[f"tortuosity_axis{i}"] for i in range(3)]
bnei_tort = [bnei_summary[f"tortuosity_axis{i}"] for i in range(3)]
x = np.arange(3)
w = 0.35
ax.bar(x - w / 2, mishmar_tort, width=w, color=COLOR_MISHMAR, label=LABEL_MISHMAR)
ax.bar(x + w / 2, bnei_tort, width=w, color=COLOR_BNEI, label=LABEL_BNEI)
ax.set_xticks(x)
ax.set_xticklabels(axes_labels, fontsize=9)
ax.set_title("Diffusive tortuosity (τ) by axis", fontsize=11)
ax.set_ylabel("τ (dimensionless)", fontsize=9)
ax.grid(axis="y", alpha=0.25)
for spine in ("top", "right"):
    ax.spines[spine].set_visible(False)

# 6. Mean distance to pore, unconditioned vs connected (um, grouped bar)
ax = axes[1, 1]
groups = ["unconditioned", "connected\n(percolating)"]
mishmar_vals = [mishmar_dist["dist_pore_unconditioned_mean_um"], mishmar_dist["dist_pore_connected_mean_um"]]
bnei_vals = [bnei_dist["dist_pore_unconditioned_mean_um"], bnei_dist["dist_pore_connected_mean_um"]]
x = np.arange(2)
ax.bar(x - w / 2, mishmar_vals, width=w, color=COLOR_MISHMAR, label=LABEL_MISHMAR)
ax.bar(x + w / 2, bnei_vals, width=w, color=COLOR_BNEI, label=LABEL_BNEI)
ax.set_xticks(x)
ax.set_xticklabels(groups, fontsize=9)
ax.set_title("Mean distance to pore", fontsize=11)
ax.set_ylabel("distance (µm)", fontsize=9)
ax.grid(axis="y", alpha=0.25)
for spine in ("top", "right"):
    ax.spines[spine].set_visible(False)

# 7. Mean distance to POM, unconditioned vs connected (connected = N/A, POM never percolates)
ax = axes[1, 2]
mishmar_vals = [mishmar_dist["dist_pom_unconditioned_mean_um"], mishmar_dist["dist_pom_connected_mean_um"]]
bnei_vals = [bnei_dist["dist_pom_unconditioned_mean_um"], bnei_dist["dist_pom_connected_mean_um"]]
mishmar_plot = [v if not np.isnan(v) else 0 for v in mishmar_vals]
bnei_plot = [v if not np.isnan(v) else 0 for v in bnei_vals]
bars_m = ax.bar(x - w / 2, mishmar_plot, width=w, color=COLOR_MISHMAR, label=LABEL_MISHMAR)
bars_b = ax.bar(x + w / 2, bnei_plot, width=w, color=COLOR_BNEI, label=LABEL_BNEI)
for bars, vals in [(bars_m, mishmar_vals), (bars_b, bnei_vals)]:
    for b, v in zip(bars, vals):
        if np.isnan(v):
            ax.text(b.get_x() + b.get_width() / 2, 0.02 * max(mishmar_plot + bnei_plot),
                     "N/A\n(no percolating\nPOM)", ha="center", va="bottom", fontsize=7)
ax.set_xticks(x)
ax.set_xticklabels(groups, fontsize=9)
ax.set_title("Mean distance to POM", fontsize=11)
ax.set_ylabel("distance (µm)", fontsize=9)
ax.grid(axis="y", alpha=0.25)
for spine in ("top", "right"):
    ax.spines[spine].set_visible(False)

# 8. Surface area by pore-size class (identical bin_edges_um in both runs -> directly comparable)
ax = axes[1, 3]
ax.plot(mishmar_psd["Diameter_um"], mishmar_psd["Surface_Area_um2"], "-o",
        color=COLOR_MISHMAR, markersize=3, linewidth=1.5, label=LABEL_MISHMAR)
ax.plot(bnei_psd["Diameter_um"], bnei_psd["Surface_Area_um2"], "-o",
        color=COLOR_BNEI, markersize=3, linewidth=1.5, label=LABEL_BNEI)
ax.set_xscale("log")
ax.set_yscale("log")
ax.set_title("Surface area by pore-size class", fontsize=11)
ax.set_xlabel("pore diameter (µm)", fontsize=9)
ax.set_ylabel("surface area (µm²)", fontsize=9)
ax.grid(alpha=0.25, which="both")
for spine in ("top", "right"):
    ax.spines[spine].set_visible(False)

handles, labels = axes[1, 0].get_legend_handles_labels()
fig.legend(handles, labels, loc="lower center", ncol=2, fontsize=11, bbox_to_anchor=(0.5, -0.02))
fig.tight_layout(rect=(0, 0.03, 1, 0.96))
fig.savefig(OUT_PATH, dpi=150, bbox_inches="tight")
print(f"Saved: {OUT_PATH}")
