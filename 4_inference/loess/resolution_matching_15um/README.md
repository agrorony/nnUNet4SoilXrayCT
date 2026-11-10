# Loess at ~15 µm: the resolution-matched volumes

The two external Loess scans have finer voxels (5.85 and 8.8 µm) than the other scans (~15 µm). For every cross-soil comparison, their segmentations were brought to ~15 µm by majority-vote label downsampling. That keeps the segmentation itself and only coarsens it; the image is not re-predicted.

| Folder | Produced | Used by |
|---|---|---|
| `roi_expansion/` | Larger crops of both Loess scans (1000³ → 1216³ and 1614³ voxels), run through the same preprocessing and model (`part2_run_pipeline.py`), then label-downsampled to ~15 µm (`part2_downsample_mishmar.py`). The order is `part1_margin_check.py` → `part2_holder_safety_scan.py` → `part2_driver.py` (which runs `part2_export_crop.py` and `part2_run_pipeline.py` for each scan) → `part2_downsample_mishmar.py` | connectivity at matched resolution (graph 5) and tortuosity |
| `label_downsample_for_pom/` | ~15 µm label-downsamples of the original crops: `step1_label_downsample.py` for the 5.85 µm scan, `step_mishmar2_label_downsample.py` for the 8.8 µm scan (shared functions in `downsample_common.py`) | POM interface metrics (graph 6) |

These were one-off runs. The volumes they read and wrote are not in git. They stay in their original run folders on the lab computer: `05_evaluation/psd/pom_analysis_20260829_roi_expansion/`, `…_20260824_ablation/` and `…_20260824_replicates/`. The scripts point there.

The run logs are next to the scripts. The full report of the ROI-expansion run is `archive/5_analysis/pom_clustering_retired/pom_analysis_20260829_roi_expansion/final_report.md`. Its later parts cover the POM clustering, which was dropped.
