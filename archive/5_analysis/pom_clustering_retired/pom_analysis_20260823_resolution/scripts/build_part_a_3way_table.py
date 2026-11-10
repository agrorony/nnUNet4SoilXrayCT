"""Part A -- 3-way resolution-matched comparison table + interpretation.

Reads the three independently-computed summary_pom_metrics.json files
(bnei_reem, mishmar_native from the 2026-08-15 run; mishmar_15um new) and
builds the paste-ready comparison table plus a plain-language interpretation
of resolution-confound vs. soil-type-effect per dataset/metric.
"""
from __future__ import annotations

import json
from pathlib import Path

OUT_ROOT = Path(__file__).resolve().parents[1]

PATHS = {
    "bnei_reem": OUT_ROOT.parent / "pom_analysis_20260815" / "bnei_reem" / "summary_pom_metrics.json",
    "mishmar_native": OUT_ROOT.parent / "pom_analysis_20260815" / "mishmar" / "summary_pom_metrics.json",
    "mishmar_15um": OUT_ROOT / "mishmar_15um" / "summary_pom_metrics.json",
}
LABELS = {
    "bnei_reem": "Bnei Re'em (15.00 um)",
    "mishmar_native": "Mishmar native (5.85 um)",
    "mishmar_15um": "Mishmar new (15.00 um)",
}
VOXEL_UM = {"bnei_reem": 15.000149, "mishmar_native": 5.85, "mishmar_15um": 15.000149}


def cell(d):
    if d["degenerate"] or d["mean_um"] is None:
        return "degenerate"
    return f"{d['mean_um']:.1f} ({d['median_um']:.1f})"


def main():
    data = {k: json.loads(p.read_text()) for k, p in PATHS.items()}

    lines = []
    lines.append("## Part A -- 3-way resolution-matched comparison\n")
    lines.append("| Metric | Bnei Re'em (15.00 um) | Mishmar native (5.85 um) | Mishmar new (15.00 um) |")
    lines.append("|---|---|---|---|")

    for cond, label in [
        ("distance_to_pom_denoised", "Distance-to-POM, denoised, mean (median) um"),
        ("distance_to_pom_pore_adjacent", "Distance-to-POM, pore-adjacent, mean (median) um"),
        ("distance_to_pom_connected_pore_adjacent", "Distance-to-POM, connected-pore-adjacent, mean (median) um"),
    ]:
        row = [label]
        for k in ("bnei_reem", "mishmar_native", "mishmar_15um"):
            row.append(cell(data[k]["A2_conditioned_distance_maps"][cond]))
        lines.append("| " + " | ".join(row) + " |")

    for key, label, fmt in [
        ("median_diameter_um", "Count-median object diameter, um", "{:.1f}"),
        ("volume_weighted_median_diameter_um", "Volume-weighted median diameter, um", "{:.1f}"),
        ("largest_object_pct_of_denoised_pom_volume", "Largest single object, % of denoised POM volume", "{:.1f}"),
    ]:
        row = [label]
        for k in ("bnei_reem", "mishmar_native", "mishmar_15um"):
            row.append(fmt.format(data[k]["B_size_distribution_summary"][key]))
        lines.append("| " + " | ".join(row) + " |")

    for key, label, fmt in [
        ("pom_volume_fraction_pct_denoised", "POM volume fraction, % of total volume", "{:.3f}"),
        ("pom_pore_contact_fraction", "POM-pore contact fraction", "{:.3f}"),
        ("n_pom_objects_ge_cutoff", "N POM objects (>= own elbow cutoff)", "{:d}"),
    ]:
        row = [label]
        for k in ("bnei_reem", "mishmar_native", "mishmar_15um"):
            v = data[k]["A3_accessibility_metrics"][key]
            row.append(fmt.format(int(v)) if key == "n_pom_objects_ge_cutoff" else fmt.format(v))
        lines.append("| " + " | ".join(row) + " |")

    cutoff_row = ["Elbow cutoff (voxels / equiv um)"]
    for k in ("bnei_reem", "mishmar_native", "mishmar_15um"):
        c = data[k]["A1_noise_floor"]["proposed_default_cutoff"]
        cutoff_row.append(f"{c['cutoff_voxels']} vox / {c['cutoff_equiv_diameter_um']:.1f} um")
    lines.append("| " + " | ".join(cutoff_row) + " |")

    table_md = "\n".join(lines)

    # ---- directional interpretation ----
    br = data["bnei_reem"]
    mn = data["mishmar_native"]
    m15 = data["mishmar_15um"]

    def dist(k, cond):
        return data[k]["A2_conditioned_distance_maps"][cond]["mean_um"]

    def closer_to(x, a, b):
        return "bnei_reem" if abs(x - a) < abs(x - b) else "mishmar_native"

    denoised_verdict = closer_to(dist("mishmar_15um", "distance_to_pom_denoised"),
                                  dist("bnei_reem", "distance_to_pom_denoised"),
                                  dist("mishmar_native", "distance_to_pom_denoised"))
    median_verdict = closer_to(m15["B_size_distribution_summary"]["median_diameter_um"],
                                br["B_size_distribution_summary"]["median_diameter_um"],
                                mn["B_size_distribution_summary"]["median_diameter_um"])

    interpretation = f"""
### Interpretation

**Distance-to-POM (all three conditions) and count-median object diameter: resolution-driven.**
Matching Mishmar to Bnei Re'em's resolution (15.00 um) moves its distance-to-POM mean from
{mn['A2_conditioned_distance_maps']['distance_to_pom_denoised']['mean_um']:.1f} um (native 5.85 um) to
{m15['A2_conditioned_distance_maps']['distance_to_pom_denoised']['mean_um']:.1f} um (new 15.00 um sample) --
landing closer to Bnei Re'em's {br['A2_conditioned_distance_maps']['distance_to_pom_denoised']['mean_um']:.1f} um
than to native-resolution Mishmar. Same pattern for count-median object diameter
({mn['B_size_distribution_summary']['median_diameter_um']:.1f} -> {m15['B_size_distribution_summary']['median_diameter_um']:.1f} um,
vs. Bnei Re'em's {br['B_size_distribution_summary']['median_diameter_um']:.1f} um). This is consistent evidence that
a substantial part of the original Mishmar-vs-Bnei-Re'em distance/size gap in Table 2 was a **resolution artifact**
(the finer 5.85 um scan resolves smaller POM fragments and finer pore throats the coarser scans cannot), not a pure
soil-type effect.

**POM volume fraction, volume-weighted median diameter, and largest-object share: NOT cleanly resolution- or
soil-type-driven -- dominated by sample-to-sample variability.** The new 15 um Mishmar sample's POM volume fraction
({m15['A3_accessibility_metrics']['pom_volume_fraction_pct_denoised']:.3f}%) is *lower* than both native Mishmar
({mn['A3_accessibility_metrics']['pom_volume_fraction_pct_denoised']:.3f}%) and Bnei Re'em
({br['A3_accessibility_metrics']['pom_volume_fraction_pct_denoised']:.3f}%), and its volume-weighted median diameter
({m15['B_size_distribution_summary']['volume_weighted_median_diameter_um']:.1f} um) is far below both
({mn['B_size_distribution_summary']['volume_weighted_median_diameter_um']:.1f} and
{br['B_size_distribution_summary']['volume_weighted_median_diameter_um']:.1f} um) -- neither "moves toward Bnei Re'em"
nor "stays with native Mishmar." The largest-single-object share is also wildly different between the two Mishmar
samples (native {mn['B_size_distribution_summary']['largest_object_pct_of_denoised_pom_volume']:.1f}% vs. new
{m15['B_size_distribution_summary']['largest_object_pct_of_denoised_pom_volume']:.1f}%) despite being the same soil
type. These volume-dominated metrics are sensitive to whether a core happened to intersect one or two large POM
fragments -- a natural within-soil-type sampling variability, exactly the caveat this prompt asked to keep in view.

**Caveats (do not overclaim from n=1 additional sample):** this is a different physical core, not a controlled
resolution ablation of the same sample -- natural within-soil variability and the resolution change are riding
together, so this cannot cleanly attribute the distance/diameter shift to resolution alone versus a partly-real
soil-type difference that happens to point the same direction. The loess_i2 model was originally tuned on 5.85 um
patches; nnU-Net resamples internally to its training spacing, but applying it to a native-15um input is still a
secondary, smaller possible confound worth flagging. As already noted in the prompt itself, the clean ablation
(computationally downsampling native Mishmar to 15 um, same physical sample) is the recommended next step to
separate these explanations with more confidence -- not executed here.
"""
    out = table_md + "\n" + interpretation
    (OUT_ROOT / "part_a_3way_comparison.md").write_text(out, encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
