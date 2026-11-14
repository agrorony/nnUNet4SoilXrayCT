"""Step 4: Figure 4 replacement -- left panel: full-volume PSD curves per soil
(same as before, just recomputed/reused from the existing full-volume runs);
right panel: subvolume-replicate headline metrics as mean +/- SE bars with
compact letters, PERMANOVA line printed on the panel per advisor's standard.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

OUT_ROOT = Path(__file__).resolve().parents[1]

FULL_VOLUME_PSD = {
    "bnei_reem": r"\\hive3065\Yael_Mishael\Rony\remote_computer backup\10.5\psd_outputs\psd_diag_20260802T104738_nlm_volume_fresh_bnei_reem_i4\psd_table.csv",
    "mishmar": r"\\hive3065\Yael_Mishael\Rony\remote_computer backup\10.5\psd_outputs\psd_diag_20260803T010446_mishmar_hanegev_maoz_3_5p85um_scratch_i2\psd_table.csv",
    # rehovot: filled in at runtime from the local batch output (timestamp varies)
}

SOIL_LABELS = {
    "bnei_reem": "Bnei Re'em (Vertisol)",
    "mishmar": "Mishmar HaNegev (Loess)",
    "rehovot": "Rehovot (Sand)",
}
SOIL_ORDER = ["bnei_reem", "mishmar", "rehovot"]
COLORS = {"bnei_reem": "#e08214", "mishmar": "#3b7dd8", "rehovot": "#4daf4a"}


def find_rehovot_full_run() -> Path:
    matches = sorted((OUT_ROOT / "psd_runs").glob("psd_diag_*_rehovot_full_volume"))
    if not matches:
        raise FileNotFoundError("Rehovot full-volume PSD run not found yet")
    return matches[-1] / "psd_table.csv"


def panel_psd_curves(ax):
    paths = dict(FULL_VOLUME_PSD)
    paths["rehovot"] = str(find_rehovot_full_run())
    for soil in SOIL_ORDER:
        df = pd.read_csv(paths[soil])
        ax.plot(df["Diameter_um"], df["Differential_PSD"], label=SOIL_LABELS[soil],
                color=COLORS[soil], linewidth=2)
    ax.set_xscale("log")
    ax.set_xlabel("Pore diameter (µm)")
    ax.set_ylabel("Differential pore-volume fraction")
    ax.set_title("Full-volume pore-size distribution")
    ax.axvspan(30, 150, color="gray", alpha=0.1, label="30–150 µm (microbially active)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)


def panel_metric_bars(ax, results: dict, metric: str, ylabel: str, title: str):
    part_a = results["A_univariate"][metric]
    gs = part_a["group_stats"]
    letters = part_a["letters"]
    means = [gs[s]["mean"] for s in SOIL_ORDER]
    ses = [gs[s]["se"] for s in SOIL_ORDER]
    colors = [COLORS[s] for s in SOIL_ORDER]
    x = np.arange(len(SOIL_ORDER))
    bars = ax.bar(x, means, yerr=ses, capsize=4, color=colors, alpha=0.85)
    for xi, m, se, s in zip(x, means, ses, SOIL_ORDER):
        ax.text(xi, m + se + 0.02 * max(means), letters[s], ha="center", fontsize=11, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([SOIL_LABELS[s].split(" (")[1].rstrip(")") for s in SOIL_ORDER])
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=10)
    test_str = f"{part_a['test']}: p={part_a['p']:.2g}, {part_a['effect_size_name']}={part_a['effect_size']:.3f}"
    ax.text(0.5, -0.28, test_str, transform=ax.transAxes, ha="center", fontsize=8, style="italic")


def main() -> None:
    results = json.loads((OUT_ROOT / "stats_results.json").read_text())

    fig = plt.figure(figsize=(14, 8), dpi=200)
    gs = fig.add_gridspec(2, 3, height_ratios=[1.3, 1], hspace=0.55, wspace=0.4)

    ax_psd = fig.add_subplot(gs[0, :])
    panel_psd_curves(ax_psd)

    ax1 = fig.add_subplot(gs[1, 0])
    panel_metric_bars(ax1, results, "porosity", "Porosity", "Porosity")

    ax2 = fig.add_subplot(gs[1, 1])
    panel_metric_bars(ax2, results, "median_diameter_um", "Median diameter (µm)",
                       "Median pore diameter")

    ax3 = fig.add_subplot(gs[1, 2])
    panel_metric_bars(ax3, results, "frac_30_150um_of_pore_volume", "Fraction of pore volume",
                       "30–150 µm fraction")

    permanova = results["B_permanova"]["omnibus"]
    fig.suptitle(
        f"Figure 4 — Pore-size distribution across three soils (subvolume-replicate inference)\n"
        f"PERMANOVA (Bray-Curtis, {permanova['n_perm']+1} perms): "
        f"pseudo-F({permanova['df_among']},{permanova['df_within']})={permanova['pseudo_F']:.2f}, "
        f"R²={permanova['R2']:.3f}, p={permanova['p']:.4f}",
        fontsize=12, fontweight="bold", y=1.02
    )

    fig.savefig(str(OUT_ROOT / "figure4_replacement.png"), dpi=200, bbox_inches="tight")
    fig.savefig(str(OUT_ROOT / "figure4_replacement.svg"), bbox_inches="tight")
    print("Wrote figure4_replacement.png / .svg")


if __name__ == "__main__":
    main()
