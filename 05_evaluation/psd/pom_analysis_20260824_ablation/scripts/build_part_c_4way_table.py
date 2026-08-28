"""Part C -- 4-way resolution-matched comparison table + branch-agreement
discussion (mishmar_downsample_ablation_prompt.md).

Replaces part_a_3way_comparison.md (which included the discarded, failed
mishmar_15um branch from a different physical sample) with a clean 4-way
comparison on genuinely matched/same-sample branches:
  bnei_reem (15.00um), mishmar_native (5.85um),
  mishmar_label_downsample (~15um, majority-vote), mishmar_image_then_predict (~15um, fresh predict).
"""
from __future__ import annotations

import json
from pathlib import Path

OUT_ROOT = Path(__file__).resolve().parents[1]

PATHS = {
    "bnei_reem": OUT_ROOT.parent / "pom_analysis_20260815" / "bnei_reem" / "summary_pom_metrics.json",
    "mishmar_native": OUT_ROOT.parent / "pom_analysis_20260815" / "mishmar" / "summary_pom_metrics.json",
    "mishmar_label_downsample": OUT_ROOT / "mishmar_label_downsample" / "summary_pom_metrics.json",
    "mishmar_image_then_predict": OUT_ROOT / "mishmar_image_then_predict" / "summary_pom_metrics.json",
}
COLS = ["bnei_reem", "mishmar_native", "mishmar_label_downsample", "mishmar_image_then_predict"]
LABELS = {
    "bnei_reem": "Bnei Re'em (15.00 um)",
    "mishmar_native": "Mishmar native (5.85 um)",
    "mishmar_label_downsample": "Mishmar label-downsample (~15 um)",
    "mishmar_image_then_predict": "Mishmar image-then-predict (~15 um)",
}


def cell(d):
    if d["degenerate"] or d["mean_um"] is None:
        return "degenerate"
    return f"{d['mean_um']:.1f} ({d['median_um']:.1f})"


def main():
    missing = [k for k, p in PATHS.items() if not p.is_file()]
    if missing:
        print(f"NOT READY -- missing summary_pom_metrics.json for: {missing}")
        print("(a branch's sanity check may have failed and stopped before the full pipeline ran)")
        return

    data = {k: json.loads(p.read_text()) for k, p in PATHS.items()}

    lines = []
    lines.append("## Part C -- 4-way resolution-matched comparison\n")
    header = "| Metric | " + " | ".join(LABELS[k] for k in COLS) + " |"
    lines.append(header)
    lines.append("|---|" + "---|" * len(COLS))

    for cond, label in [
        ("distance_to_pom_denoised", "Distance-to-POM, denoised, mean (median) um"),
        ("distance_to_pom_pore_adjacent", "Distance-to-POM, pore-adjacent, mean (median) um"),
        ("distance_to_pom_connected_pore_adjacent", "Distance-to-POM, connected-pore-adjacent, mean (median) um"),
    ]:
        row = [label]
        for k in COLS:
            row.append(cell(data[k]["A2_conditioned_distance_maps"][cond]))
        lines.append("| " + " | ".join(row) + " |")

    for key, label, fmt in [
        ("median_diameter_um", "Count-median object diameter, um", "{:.1f}"),
        ("volume_weighted_median_diameter_um", "Volume-weighted median diameter, um", "{:.1f}"),
        ("largest_object_pct_of_denoised_pom_volume", "Largest single object, % of denoised POM volume", "{:.1f}"),
    ]:
        row = [label]
        for k in COLS:
            row.append(fmt.format(data[k]["B_size_distribution_summary"][key]))
        lines.append("| " + " | ".join(row) + " |")

    for key, label, fmt in [
        ("pom_volume_fraction_pct_denoised", "POM volume fraction, % of total volume", "{:.3f}"),
        ("pom_pore_contact_fraction", "POM-pore contact fraction", "{:.3f}"),
        ("n_pom_objects_ge_cutoff", "N POM objects (>= own elbow cutoff)", "{:d}"),
    ]:
        row = [label]
        for k in COLS:
            v = data[k]["A3_accessibility_metrics"][key]
            row.append(fmt.format(int(v)) if key == "n_pom_objects_ge_cutoff" else fmt.format(v))
        lines.append("| " + " | ".join(row) + " |")

    cutoff_row = ["Elbow cutoff (voxels / equiv um)"]
    for k in COLS:
        c = data[k]["A1_noise_floor"]["proposed_default_cutoff"]
        cutoff_row.append(f"{c['cutoff_voxels']} vox / {c['cutoff_equiv_diameter_um']:.1f} um")
    lines.append("| " + " | ".join(cutoff_row) + " |")

    voxel_row = ["Voxel size, um"]
    for k in COLS:
        voxel_row.append(f"{data[k]['voxel_size_um']:.3f}")
    lines.append("| " + " | ".join(voxel_row) + " |")

    table_md = "\n".join(lines)

    br = data["bnei_reem"]
    mn = data["mishmar_native"]
    ld = data["mishmar_label_downsample"]
    ip = data["mishmar_image_then_predict"]

    def d_denoised(k):
        return data[k]["A2_conditioned_distance_maps"]["distance_to_pom_denoised"]["mean_um"]

    def closer_to(x, a, b):
        return "bnei_reem" if abs(x - a) < abs(x - b) else "mishmar_native"

    ld_dist_verdict = closer_to(d_denoised("mishmar_label_downsample"), d_denoised("bnei_reem"), d_denoised("mishmar_native"))
    ip_dist_verdict = closer_to(d_denoised("mishmar_image_then_predict"), d_denoised("bnei_reem"), d_denoised("mishmar_native"))

    # branch agreement: relative difference between the two ~15um branches on
    # the core metrics, as a fraction of the bnei_reem-vs-mishmar_native gap
    # they're meant to help interpret.
    def rel_diff(a, b):
        denom = max(abs(a), abs(b), 1e-9)
        return abs(a - b) / denom

    ld_pom_frac = ld["A3_accessibility_metrics"]["pom_volume_fraction_pct_denoised"]
    ip_pom_frac = ip["A3_accessibility_metrics"]["pom_volume_fraction_pct_denoised"]
    ld_dist = d_denoised("mishmar_label_downsample")
    ip_dist = d_denoised("mishmar_image_then_predict")
    ld_med = ld["B_size_distribution_summary"]["median_diameter_um"]
    ip_med = ip["B_size_distribution_summary"]["median_diameter_um"]

    agreement_lines = []
    for name, a, b in [
        ("distance-to-POM (denoised, mean)", ld_dist, ip_dist),
        ("POM volume fraction (denoised)", ld_pom_frac, ip_pom_frac),
        ("count-median object diameter", ld_med, ip_med),
    ]:
        rd = rel_diff(a, b)
        agreement_lines.append(
            f"- **{name}**: label-downsample={a:.3f}, image-then-predict={b:.3f} "
            f"(relative difference {rd*100:.1f}%) -- {'CLOSE' if rd < 0.15 else 'DIVERGENT'}"
        )

    interpretation = f"""
### Interpretation

**Directional check against Bnei Re'em / native Mishmar (distance-to-POM, denoised mean):**
- mishmar_label_downsample ({ld_dist:.1f} um) is closer to **{ld_dist_verdict}**
  (Bnei Re'em {d_denoised('bnei_reem'):.1f} um vs. native Mishmar {d_denoised('mishmar_native'):.1f} um).
- mishmar_image_then_predict ({ip_dist:.1f} um) is closer to **{ip_dist_verdict}**.

**Branch agreement (label-downsample vs. image-then-predict, same physical sample, same target ~15um):**

{chr(10).join(agreement_lines)}

If these two branches agree closely, the ~15um-vs-5.85um shift in Mishmar's POM metrics is mostly a *geometric*
consequence of coarser voxels (fewer resolvable small fragments, less-precise object boundaries) that the model
would reproduce regardless of how it arrives at the coarse-resolution segmentation. If they diverge noticeably,
that is evidence the segmentation model **itself behaves differently** when given native-resolution-vs-downsampled
input at the same physical scale -- e.g. loess_i2 was trained on 5.85um patches and may not generalize cleanly to
directly-downsampled 15um input even though nnU-Net internally resamples to its training spacing. That would be a
separate, reportable finding about model robustness to input resolution, not just a POM-geometry effect.

**No cross-sample caveat this time.** Unlike the discarded mishmar_15um branch (a different physical core), both
new branches here operate on the exact same physical sample as mishmar_native -- so any distance/diameter shift
toward Bnei Re'em's numbers can be attributed to resolution/segmentation-pathway effects, not sample-to-sample
variability. The only remaining caveat is n=1 physical sample overall (as for all Mishmar numbers in this project) --
these ablations isolate *resolution*, not soil-type sampling variability.
"""
    out = table_md + "\n" + interpretation
    (OUT_ROOT / "part_c_4way_comparison.md").write_text(out, encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
