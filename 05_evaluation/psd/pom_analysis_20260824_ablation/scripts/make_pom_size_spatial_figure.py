import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Source data (n=1 per soil, no error bars):
# - median diameter + largest-object share: part_c_4way_comparison.md
#   (pom_analysis_20260824_ablation), Bnei Re'em 15.00um column vs Mishmar
#   native 5.85um column -- these are each soil's own analysis resolution,
#   matching the numbers already pinned in PROJECT_STATUS.md.
# - Clark-Evans R: pom_spatial_pattern_summary_2soil_clean.json
#   (pom_analysis_20260824_ablation), bnei_reem vs mishmar_native.
DATA = {
    "median_diameter_um": {"L": 734.0, "V": 690.2},
    "largest_object_share_pct": {"L": 45.1, "V": 17.1},
    "clark_evans_r": {"L": 0.8180965803946613, "V": 0.6396316094365245},
}

COLORS = {"L": "#C8A24B", "V": "#6B4F35", "S": "#D97B4F"}
LABELS = {"L": "Loess (Mishmar HaNegev)", "V": "Vertisol (Bnei Re'em)", "S": "Sand (Rehovot)"}
ORDER = ["L", "V"]  # Rehovot has no POM class -- N/A, dropped as in every other POM figure

fig, axes = plt.subplots(1, 3, figsize=(11.5, 4.2))

def bar_panel(ax, key, ylabel, title, ref_line=None, ref_label=None, fmt="{:.1f}"):
    vals = [DATA[key][s] for s in ORDER]
    x = np.arange(len(ORDER))
    bars = ax.bar(x, vals, width=0.6, color=[COLORS[s] for s in ORDER],
                   edgecolor="k", lw=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(["Loess", "Vertisol"])
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=10, loc="left")
    ax.spines[["top", "right"]].set_visible(False)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.02 * max(vals),
                 fmt.format(v), ha="center", va="bottom", fontsize=8.5)
    if ref_line is not None:
        ax.axhline(ref_line, color="0.4", ls="--", lw=0.9)
        ax.text(ax.get_xlim()[1], ref_line, " " + ref_label, fontsize=7.5,
                 color="0.35", va="center", ha="left")
        ax.set_xlim(ax.get_xlim()[0], ax.get_xlim()[1] + 0.55)
    return ax

bar_panel(axes[0], "median_diameter_um",
          "Volume-weighted median\nobject diameter (µm)",
          "(a) POM object size")
bar_panel(axes[1], "largest_object_share_pct",
          "Largest object, % of\ndenoised POM volume",
          "(b) Size concentration")
bar_panel(axes[2], "clark_evans_r",
          "Clark-Evans R index",
          "(c) Spatial pattern", fmt="{:.3f}",
          ref_line=1.0, ref_label="R=1\n(CSR)")
axes[2].set_ylim(0, 1.15)

handles = [plt.Rectangle((0, 0), 1, 1, fc=COLORS[s], ec="k", lw=0.5) for s in ORDER]
fig.legend(handles, [LABELS[s] for s in ORDER], loc="lower center",
           ncol=2, frameon=False, fontsize=9, bbox_to_anchor=(0.5, -0.02))

fig.suptitle("POM size distribution and spatial clustering — Vertisol (Bnei Re'em) vs. Loess (Mishmar HaNegev)",
             fontsize=11.5, y=1.03)
note = ("Both soils n=1 (single reconstructed volume); no SE, no significance test "
        "(same convention as Table 3's connectivity metrics). R<1 in both soils "
        "indicates a spatially aggregated (clustered) POM object arrangement, "
        "not complete spatial randomness (CSR, R=1); Loess is closer to CSR "
        "(R=0.818) than Vertisol (R=0.640), i.e. Vertisol's POM is more strongly clustered.")
fig.text(0.5, -0.16, note, ha="center", va="top", fontsize=7.8, wrap=True,
          transform=fig.transFigure)

fig.tight_layout(rect=[0, 0.06, 1, 0.95])

BASE = "/tmp/docx_work"
fig.savefig(f"{BASE}/pom_size_spatial_figure.png", dpi=200, bbox_inches="tight")
fig.savefig(f"{BASE}/pom_size_spatial_figure.svg", bbox_inches="tight")
print("saved")
