"""Part 4 -- group comparison (Bnei Re'em group vs. Mishmar-label-downsample
group), per pom_replicate_comparison_prompt.md.

Per-replicate table (every volume's own value) + group mean +/- SE, with n
stated explicitly per group. Bnei Re'em has n=1 (see Part 0 discovery: the
only other candidate, bnei_reem_samp_2_0, was excluded for an implausible
POM/pore fraction) so no SE/test is computed for it -- its single value is
reported plainly. Mishmar has n=2 (mean +/- SE reported, but per the
prompt's own guidance, n=2 is descriptive only, not a basis for a
hypothesis test).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

OUT_ROOT = Path(__file__).resolve().parents[1]
ABLATION_ROOT = OUT_ROOT.parent / "pom_analysis_20260824_ablation"
OLD_20260815_ROOT = OUT_ROOT.parent / "pom_analysis_20260815"

REPLICATES = {
    "bnei_reem": {
        "group": "Bnei Re'em",
        "label": "Bnei Re'em (canonical, 15.00um) -- n=1",
        "path": OLD_20260815_ROOT / "bnei_reem" / "summary_pom_metrics.json",
    },
    "mishmar_label_downsample_1": {
        "group": "Mishmar",
        "label": "Mishmar sample 1 (native 5.85um -> ~15um)",
        "path": ABLATION_ROOT / "mishmar_label_downsample" / "summary_pom_metrics.json",
    },
    "mishmar_label_downsample_2": {
        "group": "Mishmar",
        "label": "Mishmar sample 2 (native 8.8um -> ~15um)",
        "path": OUT_ROOT / "mishmar_label_downsample_2" / "summary_pom_metrics.json",
    },
}

METRICS = [
    ("dist_denoised", "Distance-to-POM, denoised, mean um",
     lambda d: d["A2_conditioned_distance_maps"]["distance_to_pom_denoised"]["mean_um"]),
    ("dist_pore_adj", "Distance-to-POM, pore-adjacent, mean um",
     lambda d: d["A2_conditioned_distance_maps"]["distance_to_pom_pore_adjacent"]["mean_um"]),
    ("dist_conn_pore_adj", "Distance-to-POM, connected-pore-adjacent, mean um",
     lambda d: d["A2_conditioned_distance_maps"]["distance_to_pom_connected_pore_adjacent"]["mean_um"]),
    ("count_median_diam", "Count-median object diameter, um",
     lambda d: d["B_size_distribution_summary"]["median_diameter_um"]),
    ("vol_weighted_median_diam", "Volume-weighted median diameter, um",
     lambda d: d["B_size_distribution_summary"]["volume_weighted_median_diameter_um"]),
    ("pom_vol_frac", "POM volume fraction, % of total volume",
     lambda d: d["A3_accessibility_metrics"]["pom_volume_fraction_pct_denoised"]),
    ("pom_pore_contact", "POM-pore contact fraction",
     lambda d: d["A3_accessibility_metrics"]["pom_pore_contact_fraction"]),
    ("largest_obj_share", "Largest object, % of denoised POM volume",
     lambda d: d["B_size_distribution_summary"]["largest_object_pct_of_denoised_pom_volume"]),
]


def mean_se(values):
    n = len(values)
    m = sum(values) / n
    if n < 2:
        return m, None
    var = sum((v - m) ** 2 for v in values) / (n - 1)
    se = math.sqrt(var / n)
    return m, se


def main():
    missing = [k for k, r in REPLICATES.items() if not r["path"].is_file()]
    if missing:
        print(f"NOT READY -- missing summary_pom_metrics.json for: {missing}")
        return

    data = {k: json.loads(r["path"].read_text()) for k, r in REPLICATES.items()}
    groups = {}
    for k, r in REPLICATES.items():
        groups.setdefault(r["group"], []).append(k)

    lines = []
    lines.append("## Part 4 -- group comparison (Bnei Re'em vs. Mishmar label-downsample, n stated per group)\n")
    n_br = len(groups["Bnei Re'em"])
    n_mish = len(groups['Mishmar'])
    lines.append(f"Group n: Bnei Re'em n={n_br}, Mishmar n={n_mish}.\n")
    lines.append(
        "**Caveat:** Bnei Re'em is n=1 (Part 0 found only one plausible physical replicate -- "
        "`bnei_reem_samp_2_0` was excluded for an implausible POM/pore fraction, see Part 0 report). "
        "Its 'group' value below is a single observation, not a mean, and has no SE. Mishmar is n=2: "
        "mean +/- SE is descriptive only, not a basis for a hypothesis test at this sample size, per the "
        "prompt's own instruction.\n"
    )

    # Per-replicate table.
    lines.append("### Per-replicate values\n")
    header = "| Metric | " + " | ".join(REPLICATES[k]["label"] for k in REPLICATES) + " |"
    lines.append(header)
    lines.append("|---|" + "---|" * len(REPLICATES))
    for key, label, fn in METRICS:
        row = [label]
        for k in REPLICATES:
            v = fn(data[k])
            row.append(f"{v:.3f}" if v is not None else "n/a")
        lines.append("| " + " | ".join(row) + " |")

    # Group mean +/- SE table.
    lines.append("\n### Group mean +/- SE\n")
    lines.append("| Metric | Bnei Re'em (n=1) | Mishmar (n=2, mean +/- SE) |")
    lines.append("|---|---|---|")
    group_stats = {}
    for key, label, fn in METRICS:
        br_val = fn(data["bnei_reem"])
        mish_vals = [fn(data[k]) for k in groups["Mishmar"]]
        m, se = mean_se(mish_vals)
        group_stats[key] = {"bnei_reem_n1": br_val, "mishmar_mean": m, "mishmar_se": se, "mishmar_values": mish_vals}
        se_str = f"{se:.3f}" if se is not None else "n/a"
        lines.append(f"| {label} | {br_val:.3f} | {m:.3f} +/- {se_str} |")

    # Comparison to single-point figures from prior runs.
    lines.append("\n### Comparison to prior single-point figures (distance-to-POM, denoised mean)\n")
    prior_bnei_reem = 597.9
    prior_native_mishmar = 268.1
    prior_ablation_label_downsample = 347.3
    new_mishmar_mean = group_stats["dist_denoised"]["mishmar_mean"]
    new_mishmar_vals = group_stats["dist_denoised"]["mishmar_values"]
    lines.append(
        f"- `pom_analysis_20260815_light/`: Bnei Re'em {prior_bnei_reem:.1f} um vs. native Mishmar {prior_native_mishmar:.1f} um (both n=1, no downsampling).\n"
        f"- 2026-08-24 ablation (native sample only, label-downsampled): {prior_ablation_label_downsample:.1f} um (n=1).\n"
        f"- This run's Mishmar group (n=2, both samples label-downsampled): individual values {['%.1f' % v for v in new_mishmar_vals]} um, "
        f"mean {new_mishmar_mean:.1f} um.\n"
    )
    shift_pct = 100 * abs(new_mishmar_mean - prior_ablation_label_downsample) / prior_ablation_label_downsample
    lines.append(
        f"Adding the second Mishmar replicate shifts the group mean by {shift_pct:.1f}% relative to the single-sample "
        f"08-24 ablation figure -- "
        + ("a small shift, suggesting the original n=1 label-downsample result was not a fluke of that one physical sample."
           if shift_pct < 15 else
           "a non-trivial shift, indicating meaningful within-Mishmar physical-sample variability that the n=1 figure could not have revealed.")
    )

    out = "\n".join(lines)
    (OUT_ROOT / "part4_group_comparison.md").write_text(out, encoding="utf-8")
    with (OUT_ROOT / "part4_group_stats.json").open("w", encoding="utf-8") as fh:
        json.dump(group_stats, fh, indent=2)
    print(out)


if __name__ == "__main__":
    main()
