"""Part 3 output checklist item -- object counts before/after the
resolvability cutoff, THIS run (ROI expansion, cutoff=20) vs. the prior
"final" run, per volume. Also folds in the Part 1/2 crop-size decisions so
the effect of ROI expansion on object count is visible directly.
"""
from __future__ import annotations

import json
from pathlib import Path

RUN_DIR = Path(__file__).resolve().parent.parent
PRIOR_RUN_DIR = RUN_DIR.parent / "pom_analysis_20260826_final_shape"

# Maps this run's dataset keys to the prior "final" run's dataset keys.
KEY_MAP = {
    "bnei_reem_canonical": "bnei_reem",
    "mishmar_native_5p85um": "mishmar_label_downsample_1",
    "mishmar_second_8p8um": "mishmar_label_downsample_2",
}


def main() -> None:
    with (PRIOR_RUN_DIR / "object_counts_before_after_cutoff_final.json").open(encoding="utf-8") as fh:
        prior = json.load(fh)
    with (RUN_DIR / "object_counts_before_after_cutoff_roi_expansion_cutoff20.json").open(encoding="utf-8") as fh:
        this_run = json.load(fh)
    with (RUN_DIR / "part1_margin_report.json").open(encoding="utf-8") as fh:
        part1 = json.load(fh)
    with (RUN_DIR / "part2_holder_safety_report.json").open(encoding="utf-8") as fh:
        part2 = json.load(fh)

    rows = []
    for this_key, prior_key in KEY_MAP.items():
        p = prior[prior_key]
        t = this_run[prior_key]
        rows.append({
            "volume": this_key,
            "prior_crop_size_vox": part1[this_key]["current_crop_shape_zhw"][0],
            "this_run_crop_size_vox": part2[this_key].get("final_crop_size"),
            "crop_decision": part2[this_key].get("decision"),
            "prior_n_objects_raw": p["n_objects_raw"],
            "prior_n_kept": p["n_objects_kept_by_resolvability_cutoff"],
            "this_run_n_objects_raw": t["n_objects_raw"],
            "this_run_n_kept": t["n_objects_kept_by_resolvability_cutoff"],
            "delta_n_kept": t["n_objects_kept_by_resolvability_cutoff"] - p["n_objects_kept_by_resolvability_cutoff"],
        })

    out_path = RUN_DIR / "object_count_comparison_this_run_vs_prior_final.json"
    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=2)
    print(f"Wrote {out_path}")

    print(f"\n{'volume':28s} {'prior_crop':>11s} {'new_crop':>9s} {'prior_raw':>10s} {'prior_kept':>11s} {'new_raw':>8s} {'new_kept':>9s} {'delta':>6s}")
    for r in rows:
        print(f"{r['volume']:28s} {r['prior_crop_size_vox']:>11} {str(r['this_run_crop_size_vox']):>9} "
              f"{r['prior_n_objects_raw']:>10} {r['prior_n_kept']:>11} "
              f"{r['this_run_n_objects_raw']:>8} {r['this_run_n_kept']:>9} {r['delta_n_kept']:>+6}")


if __name__ == "__main__":
    main()
