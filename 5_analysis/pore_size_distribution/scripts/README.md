# Pore-size distribution scripts (graph 4 and the 15 µm resolution check)

These are the scripts that produced the results, copied unchanged from the lab computer (originals dated 2026-08-15 and 2026-08-22). They still contain the paths they ran with: `C:\Users\rony.schwartz\Documents\nnUNet4SoilXrayCT\05_evaluation\psd\...` and `\\hive3065\...`.

`OUT_ROOT` in each script is the script's parent folder. When they ran, that was `05_evaluation/psd/fig4_inference_20260815/` or `05_evaluation/psd/psd_A2_reanalysis_20260822/`. Here it is `pore_size_distribution/`, so set the paths before running them again.

## Fig. 4 subvolume pipeline (outputs in `../fig4_subvolumes/`)

Run in this order:

| Script | What it does | Reads | Writes |
|---|---|---|---|
| `extract_subvolumes.py` | Cuts 8 non-overlapping cubic subvolumes per soil from the pore mask: 300³ voxels for Vertisol and Sand, 430³ for Loess at 5.85 µm | Vertisol `bnei_reem_fresh_bnei_reem_i4/inference_concatenated/nlm_volume.nii.gz`, Loess `mishmar_hanegev_maoz_3_5p85um/inference_output_concat_loess_i2/*.nii.gz`, Sand `10.5/rehovot_samp_2.npy` | `subvolumes/<soil>/*.npy` (not in git), `subvolume_extraction_manifest.json` |
| `rev_check.py` | REV check: how porosity changes with cube size, on the Vertisol | Vertisol segmentation | `rev_check_bnei_reem.json`, `.png` |
| `batch_run_psd.py` | Runs `run_psd_diagnostics.py` (local thickness) on every subvolume, one GPU per call, with a checkpoint to resume from | `subvolume_extraction_manifest.json`, `bin_edges_um.json` | `psd_runs/psd_diag_*/` (`psd_table.csv`, `summary.json`, `config.json`), `logs/`, `checkpoint_gpu{0,1}.json` |
| `poll_batches.sh` | Prints progress of the two GPU batches | `checkpoint_gpu{0,1}.json` | stdout |
| `aggregate_metrics.py` | One row per subvolume: porosity, mean and median diameter, 30–150 µm share, binned PSD | `psd_runs/*/psd_table.csv` | `subvolume_metrics.csv` |
| `step3c_pore_objects.py` | Labels pore objects in each full volume (26-connectivity, objects < 2 voxels dropped) and keeps their equivalent spherical diameters | the three segmentations | `pore_objects/*_object_diameters_um.npy` (not in git), `pore_objects_summary.json` |
| `run_stats.py` | Part A: ANOVA or Kruskal–Wallis per metric. Part B: PERMANOVA on the binned PSD. Part C: KS tests on object diameters | `subvolume_metrics.csv`, `pore_objects/`, `pore_objects_summary.json` | `stats_results.json` |
| `make_figure4.py` | Draws the replacement Fig. 4 | `stats_results.json`, the full-volume `psd_table.csv` per soil (`10.5/psd_outputs/...` and the `rehovot_full_volume` run) | `figure4_replacement.png`, `.svg` |

`subvolume_metrics.csv`, `stats_results.json` and `figure4_replacement.png` were rewritten on 2026-08-22 by re-running the last steps with these same scripts. The scripts have not changed since 2026-08-15. One early test run (`psd_diag_20260815T151237_bnei_reem_sub_00`) is left out of `../fig4_subvolumes/psd_runs/`, because `aggregate_metrics.py` does not read it.

## Pore-size classes (A2 re-analysis, 2026-08-22)

| Script | What it does | Reads | Writes |
|---|---|---|---|
| `reaggregate_classes.py` | Re-bins the 24 subvolume PSDs into 30–150, 150–300 and > 300 µm classes and tests them: ANOVA or Kruskal–Wallis, Holm-corrected pairwise tests | `fig4_inference_20260815/subvolume_extraction_manifest.json`, `psd_runs/*/psd_table.csv` | `../class_metrics.csv`, `../class_stats_results.json` (what graph 4 reads) |
| `downsample_mishmar.py` | Resamples the 8 Loess subvolume masks from 5.85 µm to about 15 µm (trilinear on the mask as float, re-thresholded at 0.5) | Fig. 4 subvolume manifest and masks | `mishmar_downsample/subvolumes_15um/*.npy` (not in git), `downsample_manifest.json` |
| `run_downsample_psd_batch.py` | Runs `run_psd_diagnostics.py` on the downsampled subvolumes | `downsample_manifest.json`, `bin_edges_um.json` | `mishmar_downsample/psd_runs/`, `logs/`, `checkpoint.json` |
| `downsample_compare.py` | Compares class metrics at 5.85 µm and 15 µm | the downsampled runs, `class_metrics.csv`, `class_stats_results.json` | `../mishmar_downsample_check/mishmar_downsampled_class_metrics.csv`, `downsample_comparison.json` |

## Which `run_psd_diagnostics.py` these ran with

The PSD engine is now `5_analysis/shared_code/run_psd_diagnostics.py`; it was `05_evaluation/psd/run_psd_diagnostics.py` when these ran.

- **The commit that was current on 2026-08-22** is `d90e0bd4b92e4cd64ff4b7789b2af18c32dcf9cc` (2026-07-08). To get that version:

  ```
  git show d90e0bd:05_evaluation/psd/run_psd_diagnostics.py
  ```

- **The next commit came the day after.** `6a271a2` (2026-08-23, "commit pending code/config/docs") changed POM-label handling to accept several labels, changed the default number of anisotropy directions from 100 to 800, and added options for chunked EDT. These may already have been on disk, uncommitted, when the runs on 2026-08-15 and 08-22 were made, so the exact version that ran cannot be proven.
- **The script has changed since:** `36c2b7e` (2026-09-07) and the move in `4c3386a` (2026-11-10). The current file is not byte-identical to either version above.
