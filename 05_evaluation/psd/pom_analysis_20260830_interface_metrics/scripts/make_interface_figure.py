import json, numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = r"/sessions/rcw-0172edhrn4y2cw33r8eglxhz/mnt/nnUNet4SoilXrayCT/05_evaluation/psd/pom_analysis_20260830_interface_metrics"
with open(f"{BASE}/all_soils_interface_summary.json") as f:
    D = json.load(f)

BR = D["bnei_reem"]
M1 = D["mishmar_native"]
M2 = D["mishmar_sample2"]

COL_V = "#6B4F35"   # Vertisol / Bnei Re'em
COL_L = "#C8A24B"   # Loess / Mishmar HaNegev
LABEL_V = "Vertisol (Bnei Re'em, n=1)"
LABEL_L = "Loess (Mishmar HaNegev, n=2)"

def mean_se(a, b):
    arr = np.array([a, b], dtype=float)
    return arr.mean(), arr.std(ddof=1) / np.sqrt(2)

def bar_pair(ax, x_labels, br_vals, m_vals_pairs, ylabel, title, pct=False):
    """m_vals_pairs: list of (native_val, sample2_val) per x category."""
    n = len(x_labels)
    x = np.arange(n)
    w = 0.35
    br_plot = [v * 100 if pct else v for v in br_vals]
    m_means, m_ses = [], []
    for (a, b) in m_vals_pairs:
        mn, se = mean_se(a, b)
        if pct:
            mn, se = mn * 100, se * 100
        m_means.append(mn); m_ses.append(se)

    ax.bar(x - w/2, m_means, width=w, yerr=m_ses, capsize=5,
           color=COL_L, edgecolor="k", lw=0.5, label=LABEL_L,
           error_kw={"elinewidth": 1, "capthick": 1})
    ax.bar(x + w/2, br_plot, width=w, color=COL_V, edgecolor="k", lw=0.5, label=LABEL_V)
    ax.set_xticks(x); ax.set_xticklabels(x_labels)
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=10, loc="left")
    ax.spines[["top", "right"]].set_visible(False)
    return ax

fig, axes = plt.subplots(2, 3, figsize=(13, 8.2))

# (a) Specific surface area (SSA) -- POM-intrinsic, abundance-independent
ax = axes[0, 0]
bar_pair(
    ax,
    ["Total", "Pore-facing", "Matrix-facing"],
    [BR["part3_ssa_iad"]["ssa_total_mm2_per_mm3"],
     BR["part3_ssa_iad"]["ssa_pore_facing_mm2_per_mm3"],
     BR["part3_ssa_iad"]["ssa_matrix_facing_mm2_per_mm3"]],
    [(M1["part3_ssa_iad"]["ssa_total_mm2_per_mm3"], M2["part3_ssa_iad"]["ssa_total_mm2_per_mm3"]),
     (M1["part3_ssa_iad"]["ssa_pore_facing_mm2_per_mm3"], M2["part3_ssa_iad"]["ssa_pore_facing_mm2_per_mm3"]),
     (M1["part3_ssa_iad"]["ssa_matrix_facing_mm2_per_mm3"], M2["part3_ssa_iad"]["ssa_matrix_facing_mm2_per_mm3"])],
    "SSA (mm$^2$ mm$^{-3}$ POM)",
    "(a) Specific surface area\n(POM-intrinsic - similar)",
)

# (b) Interfacial area density (IAD) -- bulk-soil-scaled, the headline
ax = axes[0, 1]
bar_pair(
    ax,
    ["POM-pore", "POM-matrix"],
    [BR["part3_ssa_iad"]["iad_pore_mm2_per_mm3"], BR["part3_ssa_iad"]["iad_matrix_mm2_per_mm3"]],
    [(M1["part3_ssa_iad"]["iad_pore_mm2_per_mm3"], M2["part3_ssa_iad"]["iad_pore_mm2_per_mm3"]),
     (M1["part3_ssa_iad"]["iad_matrix_mm2_per_mm3"], M2["part3_ssa_iad"]["iad_matrix_mm2_per_mm3"])],
    "IAD (mm$^2$ mm$^{-3}$ bulk soil)",
    "(b) Interfacial area density\n(bulk-soil-scaled - Loess higher)",
)

# (c) Voxel-face contact fractions
ax = axes[0, 2]
bar_pair(
    ax,
    ["POM-pore", "POM-matrix"],
    [BR["part1_voxel_face_contact"]["pom_pore_contact_fraction_voxel"],
     BR["part1_voxel_face_contact"]["pom_matrix_contact_fraction_voxel"]],
    [(M1["part1_voxel_face_contact"]["pom_pore_contact_fraction_voxel"], M2["part1_voxel_face_contact"]["pom_pore_contact_fraction_voxel"]),
     (M1["part1_voxel_face_contact"]["pom_matrix_contact_fraction_voxel"], M2["part1_voxel_face_contact"]["pom_matrix_contact_fraction_voxel"])],
    "Contact fraction (voxel-face)",
    "(c) POM surface-voxel\ncontact fraction",
    pct=False,
)

# (d) Total POM surface area -- two methods, cross-check (secondary/validation panel)
ax = axes[1, 0]
bar_pair(
    ax,
    ["Marching\ncubes", "Voxel-face\n(cross-check)"],
    [BR["part2_marching_cubes"]["pom_surface_area_um2_marching_cubes_total"] / 1e6,
     BR["part2_marching_cubes"]["pom_surface_area_um2_voxel_face_count_total"] / 1e6],
    [(M1["part2_marching_cubes"]["pom_surface_area_um2_marching_cubes_total"] / 1e6,
      M2["part2_marching_cubes"]["pom_surface_area_um2_marching_cubes_total"] / 1e6),
     (M1["part2_marching_cubes"]["pom_surface_area_um2_voxel_face_count_total"] / 1e6,
      M2["part2_marching_cubes"]["pom_surface_area_um2_voxel_face_count_total"] / 1e6)],
    "Total POM surface area (mm$^2$)",
    "(d) Total surface area\n(2 methods - see note)",
)

# (e) Interface-area concentration (largest object / top-5 share)
ax = axes[1, 1]
bar_pair(
    ax,
    ["Largest\nobject", "Top-5\nobjects"],
    [BR["part4_object_level"]["largest_object_interface_area_share"],
     BR["part4_object_level"]["top5_objects_interface_area_share"]],
    [(M1["part4_object_level"]["largest_object_interface_area_share"], M2["part4_object_level"]["largest_object_interface_area_share"]),
     (M1["part4_object_level"]["top5_objects_interface_area_share"], M2["part4_object_level"]["top5_objects_interface_area_share"])],
    "Share of total POM-pore interfacial area (%)",
    "(e) Interfacial-area\nconcentration",
    pct=True,
)

# (f) Legend + note panel (no axes)
ax = axes[1, 2]
ax.axis("off")
handles = [
    plt.Rectangle((0, 0), 1, 1, fc=COL_L, ec="k", lw=0.5),
    plt.Rectangle((0, 0), 1, 1, fc=COL_V, ec="k", lw=0.5),
]
ax.legend(handles, [LABEL_L, LABEL_V], loc="upper left", frameon=False, fontsize=10)
note = (
    "Bnei Re'em: single volume (n=1), no error bar --\n"
    "descriptive point, not a distribution.\n"
    "Mishmar: mean +/- SE across native (5.85 um) and\n"
    "second-specimen (8.8 um) reconstructions (n=2).\n\n"
    "No significance testing shown: n=1 for Bnei Re'em\n"
    "precludes an omnibus test (same convention as the\n"
    "connectivity Table 3 metrics elsewhere in this draft).\n\n"
    "Panel (d): marching-cubes and voxel-face methods\n"
    "disagree in absolute mm$^2$ (validated against synthetic\n"
    "spheres -- marching cubes is closer to true area); their\n"
    "pore-vs-matrix SPLIT agrees within 3-7 pp (panels a-c\n"
    "rely on the split, not the absolute totals)."
)
ax.text(0.0, 0.62, note, transform=ax.transAxes, fontsize=8.2, va="top",
        bbox=dict(boxstyle="round", fc="white", ec="0.6", lw=0.7))

fig.suptitle("POM interface metrics - Bnei Re'em (Vertisol) vs. Mishmar HaNegev (Loess)",
             fontsize=12, y=0.995)
fig.tight_layout(rect=[0, 0, 1, 0.97])
fig.subplots_adjust(hspace=0.55, wspace=0.32)

out_png = f"{BASE}/pom_interface_metrics_figure.png"
out_svg = f"{BASE}/pom_interface_metrics_figure.svg"
fig.savefig(out_png, dpi=200, bbox_inches="tight")
fig.savefig(out_svg, bbox_inches="tight")
print("saved:", out_png, out_svg)
