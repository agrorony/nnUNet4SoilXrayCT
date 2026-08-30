"""Part 3 prep -- decide, per volume, whether to use the ROI-expanded crop
or fall back to the existing (already-trusted) crop, based on the Part 1
margin check, Part 2 holder-safety decision, and Part 2 channel-collapse
sanity check(s). Writes datasets_this_run.json for
run_pom_shape_clustering_generalized.py / run_all_cutoffs.py.

Decision logic per volume (conservative-default, matching the prompt's
sanity-check rule: "if any step is ambiguous ... make the most
conservative choice: keep the existing, already-trusted crop"):
  - Part 1 said insufficient margin -> existing crop.
  - Part 2 native-resolution sanity check flagged channel collapse ->
    existing crop.
  - (Mishmar only) downsample-stage sanity check flagged collapse ->
    existing crop.
  - Otherwise -> the new ROI-expanded crop.
"""
from __future__ import annotations

import json
from pathlib import Path

RUN_DIR = Path(__file__).resolve().parent.parent
LOCAL_REPO = Path(r"C:\Users\rony.schwartz\Documents\nnUNet4SoilXrayCT")

EXISTING_CROP = {
    "bnei_reem_canonical": dict(
        label="Bnei Re'em (Vertisol) -- canonical nlm_volume, n=1 [EXISTING CROP]",
        path=r"\\hive3065\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources\bnei_reem_fresh_bnei_reem_i4\inference_concatenated\nlm_volume.nii.gz",
        voxel_um=15.000149, pore_label=5, pom_label=2,
    ),
    "mishmar_native_5p85um": dict(
        label="Mishmar HaNegev (Loess) -- sample 1 (native 5.85um), label-downsampled ~15um [EXISTING CROP]",
        path=str(LOCAL_REPO / "05_evaluation" / "psd" / "pom_analysis_20260824_ablation" / "mishmar_label_downsample" / "mishmar_label_downsample.nii.gz"),
        voxel_um=15.000149, pore_label=5, pom_label=2,
    ),
    "mishmar_second_8p8um": dict(
        label="Mishmar HaNegev (Loess) -- sample 2 (native 8.8um), label-downsampled ~15um [EXISTING CROP]",
        path=str(LOCAL_REPO / "05_evaluation" / "psd" / "pom_analysis_20260824_replicates" / "mishmar_label_downsample_2" / "mishmar_label_downsample_2.nii.gz"),
        voxel_um=15.000149, pore_label=5, pom_label=2,
    ),
}

# Output dataset key names expected by the downstream comparison table /
# report (mirrors the prior "final" run's soil keys for bnei_reem's group
# tagging in SOIL_GROUP; kept distinct here per volume for clarity).
DATASET_KEY_FOR = {
    "bnei_reem_canonical": "bnei_reem",
    "mishmar_native_5p85um": "mishmar_label_downsample_1",
    "mishmar_second_8p8um": "mishmar_label_downsample_2",
}


def new_crop_path(key: str) -> Path:
    if key == "bnei_reem_canonical":
        return RUN_DIR / "pipeline_work" / key / "inference_concatenated" / f"{key}.nii.gz"
    return RUN_DIR / "pipeline_work" / key / f"{key}_label_downsample.nii.gz"


def main() -> None:
    with (RUN_DIR / "part1_margin_report.json").open(encoding="utf-8") as fh:
        part1 = json.load(fh)
    with (RUN_DIR / "part2_holder_safety_report.json").open(encoding="utf-8") as fh:
        part2 = json.load(fh)

    decisions = {}
    datasets = {}
    for key in EXISTING_CROP:
        out_key = DATASET_KEY_FOR[key]
        reasons = []
        use_new = True

        if not part1[key]["qualifies_for_part2"]:
            use_new = False
            reasons.append("Part 1: insufficient margin (<15% on some axis)")

        native_sanity_path = RUN_DIR / f"sanity_check_{key}.json"
        if use_new:
            if not native_sanity_path.exists():
                use_new = False
                reasons.append("Part 2 pipeline did not complete / no sanity_check file found")
            else:
                with native_sanity_path.open(encoding="utf-8") as fh:
                    ns = json.load(fh)
                if ns["channel_collapse_detected"]:
                    use_new = False
                    reasons.append(f"Part 2 native-res channel collapse: pore={ns['new_pore_voxel_fraction_pct']:.3f}% "
                                    f"pom={ns['new_pom_voxel_fraction_pct']:.3f}% vs baseline pore="
                                    f"{ns['baseline_pore_voxel_fraction_pct']}% pom={ns['baseline_pom_voxel_fraction_pct']}%")

        if use_new and key != "bnei_reem_canonical":
            ds_sanity_path = RUN_DIR / "pipeline_work" / key / "downsample_sanity_check.json"
            if not ds_sanity_path.exists():
                use_new = False
                reasons.append("downsample step did not complete / no downsample_sanity_check.json found")
            else:
                with ds_sanity_path.open(encoding="utf-8") as fh:
                    ds = json.load(fh)
                if ds["downsampled_collapse_detected"]:
                    use_new = False
                    reasons.append(f"Part 2 downsampled-res channel collapse: pore={ds['pore_voxel_fraction_pct']:.3f}% "
                                    f"pom={ds['pom_voxel_fraction_pct']:.3f}%")

        if use_new:
            p = new_crop_path(key)
            if not p.exists():
                use_new = False
                reasons.append(f"expected new-crop output missing: {p}")

        if use_new:
            cfg = dict(EXISTING_CROP[key])
            cfg["path"] = str(new_crop_path(key))
            cfg["label"] = cfg["label"].replace("[EXISTING CROP]", "[ROI-EXPANDED CROP]")
            crop_size = part2[key]["final_crop_size"]
            decision = f"ROI-expanded crop used (final_crop_size={crop_size})"
        else:
            cfg = EXISTING_CROP[key]
            decision = "existing crop used -- " + "; ".join(reasons)

        datasets[out_key] = cfg
        decisions[key] = {"used_new_crop": use_new, "decision": decision, "reasons": reasons}
        print(f"[{key}] -> {out_key}: {decision}")

    with (RUN_DIR / "datasets_this_run.json").open("w", encoding="utf-8") as fh:
        json.dump(datasets, fh, indent=2)
    with (RUN_DIR / "crop_decisions_final.json").open("w", encoding="utf-8") as fh:
        json.dump(decisions, fh, indent=2)
    print(f"\nWrote {RUN_DIR / 'datasets_this_run.json'} and crop_decisions_final.json")


if __name__ == "__main__":
    main()
