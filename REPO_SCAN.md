# Repository Scan — nnUNet4SoilXrayCT

Read-only reconnaissance pass. Generated 2026-07-07. Excludes `.git`, `__pycache__`, `venv`/`.venv`, build artifacts.

Headline numbers: 106 files tracked by git (`git ls-files`); ~418 files on disk excluding `.git`. The ~300-file gap is almost entirely untracked scratch scripts, logs, and output dumps concentrated in the repo root and in three newer, entirely-untracked module folders (`microsam_3d/`, `seg_plausibility/`, `analysis/pore_metrics_research/`, `analysis/selected_outputs/`).

---

## 1. Full file tree

Legend: **T** = tracked in git (date/msg = last commit touching it), **U** = untracked (date = mtime only). Sizes rounded.

### Repo root (`.`)

| File | Size | Status | Date | Note |
|---|---|---|---|---|
| LICENSE | 7.2KB | T | 2025-01-08 | |
| README.md | 40KB | T | 2026-05-24 | |
| .gitignore | 396B | T | 2026-05-24 | |
| setup_prompt.md | 4.1KB | T | 2026-04-21 | |
| __path__.py | 422B | T | 2026-06-22 | |
| dataset_info.json | 507B | T | 2026-05-24 | canonical label map |
| chunk_extractor.py | 833B | T | 2026-05-31 | |
| colab_nnUNet_pipeline.ipynb | 58KB | T (M) | 2026-06-22 | uncommitted changes pending |
| debug_labels_777.py | 9.1KB | T | 2026-04-20 | |
| debug_labels_777_followup.py | 4.0KB | T | 2026-04-20 | |
| extract_trainlog.py | 4.6KB | T | 2025-05-14 | |
| inspect_predictions.py | 8.7KB | T | 2026-05-24 | |
| make_annotations.py | 7.4KB | T | 2026-05-24 | |
| make_psd_plot.py | 1.7KB | T | 2026-05-31 | |
| merge_annotations.py | 6.8KB | T | 2026-05-18 | |
| mishmar_psd.log | 126B | T | 2026-05-31 | **log file committed to git** |
| nnUNetTrainer_betterIgnoreSampling.py | 25KB | T (M) | 2026-05-24 | uncommitted changes pending |
| otsu_threshold_3d.py | 5.4KB | T | 2026-04-19 | |
| postprocessing_nnUNet_predict.py | 1.5KB | T | 2025-02-18 | |
| postprocessing_nnUNet_predict_concatenate.py | 3.0KB | T | 2026-05-24 | |
| postprocessing_pipeline.ipynb | 14KB | T | 2026-04-30 | |
| preprocessing_nnUNet_predict.py | 2.4KB | T | 2026-04-20 | |
| preprocessing_nnUNet_predict_split.py | 4.2KB | T | 2025-02-18 | |
| preprocessing_nnUNet_predict_tif.py | 2.4KB | T | 2026-04-20 | |
| preprocessing_nnUNet_train.py | 15KB | T | 2026-05-24 | |
| retrieve_dice_score.py | 4.3KB | T | 2025-03-24 | |
| run_remaining_fullctx_overnight.ipynb | 19KB | T | 2026-05-18 | |
| select_slices_and_predict.py | 37KB | T | 2026-05-18 | |
| _inference_err.txt / _inference_log.txt | 55KB / 6.4KB | T | 2026-06-22 | **log file committed to git** |
| _inference_nlm_err.txt / _inference_nlm_log.txt | 55KB / 5.7KB | T | 2026-06-22 | **log file committed to git** |
| _napari_nlm_err.txt / _napari_nlm_log.txt | 310B / 149B | T | 2026-06-22 | **log file committed to git** |
| _run_inference_mishmar_iter02.py | 3.9KB | T | 2026-06-22 | |
| _run_inference_nlm_iter02.py | 3.7KB | T | 2026-06-22 | |

**Untracked scratch sprawl in root (~110 files, all `U`)** — grouped by theme rather than listed individually (full detail is dense; ask if per-file dates are needed):

- **Training run logs** (`.log`/`_err.log` pairs, 2026-06-28→2026-07-07): `_fresh_bnei_reem_i2`, `_i3`, `_i3_lowlr`, `_i3_scratch`, `_i4`, `_train_fresh_bnei_reem`, `_train_iter4_continue_bnei_reem`, `_mishmar_hnegev_scratch`, `_mishmar_hnegev_trained`. Sizes up to 127KB.
- **Inference run logs** (2026-06-23→2026-07-06): `_fresh_inference_napari`, `_i4_inference`, `_iter03_inference`, `_iter03_run4`, `_iter03_run5`, `_iter04_continue_inference`, `_iter04_run1`, `_iter04_run2`, `_scratch_inference`, `_seg_plausibility_i3_scratch_run` (0B empty), `_seg_plausibility_i4_run`/`_run_gpu`.
- **Napari launcher scripts** (near-duplicate family, 650B–1.8KB each, 2026-06-23→2026-07-07): `_launch_napari_compare_gt.py`, `_comparison.py`, `_fresh_i2.py`, `_fresh_i2_fullvol.py`, `_fresh_i3_fullvol.py`, `_i3_lowlr_fullvol.py`, `_iter04.py`, `_mishmar_microSAM.py`, `_nlm_iter04_continue.py`, `_nlm_microSAM.py`, `_seg_plausibility_i3_scratch.py`, `_seg_plausibility_i4.py`, plus matching `_napari_*_log.txt`/`_err.txt` output pairs (one, `_napari_seg_plausibility_i4_log3.txt`, is 0B).
- **Per-iteration training/inference driver scripts** (clear copy-paste family, 2.3–36KB each, 2026-06-23→2026-07-06): `_run_fresh_bnei_reem_i2/i3/i3_lowlr/i3_scratch/i4.py`, `_run_fresh_then_compare_napari.py`, `_run_inference_fresh_bnei_reem*.py` (6 variants), `_run_inference_iter03/04/04_continue.py`, `_run_iter03/04/04_continue.py`, `_run_mishmar_hnegev_scratch/trained.py`; plus untracked siblings of tracked-looking names `train_fresh_bnei_reem.py`, `train_iter4_continue_bnei_reem.py` (2026-06-28).
- **Misc scratch/debug scripts**: `_compare_predictions.py`, `_find_dataset_json.py`, `_inspect_labels.py`, `_plot_i3_metrics.py`, `_plot_lowlr_metrics.py`, `_train_wrapper.py`, `_verify_i2_paths.py`, `_launch_parallel_training.ps1`, `_make_ann_err/log.txt`, `_make_synopsis_i3/i4.py` + logs (i3_err/i4_err are 0B empty).
- **Loose output artifacts in repo root**: `_comparison_iter04_continue_vs_fresh.pdf` (33KB), `_comparison_iter04_continue_vs_fresh.png` (163KB), 2026-06-29.

### `.claude/` (U — local tool config)
`.claude/prompts/repo-scan-prompt.md` (3.6KB, 2026-07-07), `.claude/scheduled_tasks.lock` (91B), `.claude/settings.local.json` (79B).

### `.github/` (all T)
`agents/data-registry-path-validation.agent.md` (5.5KB, 2026-06-02), `agents/ml-workflow-orchestrator.agent.md` (8.8KB, 2026-06-02), `agents/notebook-builder.agent.md` (3.2KB, 2026-05-24), `agents/psd-analysis-runner.agent.md` (3.7KB, 2026-05-24), `copilot-instructions.md` (18.8KB, 2026-06-02), `skills/report-agent-run-status.skill.md` (6.0KB, 2026-05-31).

### `.vscode/` (T)
`mcp.json` (1.7KB), `settings.json` (135B) — both 2026-04-19.

### `Figures/` (T, image assets)
`HI_Logo.png` (450KB), `UFZ_Logo.png` (48KB), `Workflow.png` (334KB) — all 2025-02-14.

### `Fiji_macros/` (T — Windows + Ubuntu macro pairs, deliberate, not clutter)
`convert_mha_to_img(.ijm/_ubuntu.ijm)`, `convert_nii_to_mha(.ijm/_ubuntu.ijm)`, `convert_tif_to_img(.ijm/_ubuntu.ijm)` — ~1KB each, 2025-02-18/2025-03-27.

### `Utilities/` (T)
`mkdir_movefiles.sh` (1.4KB), `nifti_io.jar` (39KB binary), `submit_nnUNet_inference` (1.1KB), `submit_nnUNet_training` (1.1KB) — 2025-02-18→2026-05-24.

### `litreture/` (T — note: directory name is misspelled "litreture")
`nnUNet4SoilCT_atricle.pdf` (5.0MB, 2026-04-19).

### `preprocess_playground/` (T)
`README.md` (2.6KB), `filters_3d.py` (2.6KB), `normalization.py` (5.5KB), `run_napari_filters.py` (2.2KB) — all 2026-04-19. Plus untracked `__pycache__/*.pyc` (build artifact).

### `training_diag/` (T)
`check_data.py` (11.8KB, 2026-04-19).

### `preprocess/` (T)
`colab_cli_runner.ipynb` (34KB, 2026-05-31), `gpu_nlm_torch.py` (7.5KB), `normalization.py` (3.5KB), `run_preprocess.py` (4.1KB) — 2026-04-21. `preprocess/nlm_output/` and `preprocess/norm200_output/` exist but are **empty**.

### `config/pores_analysis/`
`config.yaml` (985B, U, 2026-07-06).

### `legacy/` (mostly T; several files modified uncommitted; two new untracked files)
`legacy/preprocess_ct_images.py` (5.4KB, T, 2026-04-19).
`legacy/pores_analysis/`: `BUGFIX_CHANGELOG.md`, `PSD_DIAGNOSTICS_SUMMARY.md`, `README.md` (M), `USAGE_GUIDE.md`, `__init__.py` (M), `block_processor.py`, `check_imports.py`, `checkpoint_manager.py`, `config_loader.py` (M), `distance_transform.py`, `example_workflow.py`, `local_thickness.py`, `psd_calculator.py` (M), `psd_diagnostics.py`, `psd_entrypoint.py`, `psd_output.py`, `run_tests.py`, `synthetic_volume.py`, `test_psd_synthetic.py` — all committed 2026-04-19, five currently modified uncommitted. New untracked: `environment.yml` (1.5KB, 2026-07-07), `extended_pipeline.py` (14KB, 2026-07-06), `topology_metrics.py` (18.6KB, 2026-07-06). `legacy/pores_analysis/results/` exists, **empty**. `__pycache__` contains both cpython-311 and cpython-312 `.pyc` files (two different Python envs used over time).

### `microsam_3d/` (entirely U — a whole new untracked module)
`README.md` (7.4KB), `correction_store.py` (1.4KB), `debug.log` (1.3KB, log sitting in module root), `embedder.py` (1.7KB), `environment.yml` (363B), `error_map.py` (2.0KB), `napari_plugin.py` (25.6KB), `predictor.py` (1.6KB), `propagation_guide.md` (7.7KB), `run.py` (8.9KB) — 2026-06-27→2026-06-30. `microsam_3d/dev/`: `_inspect_sam.py`, `_launch_nlm.py`, `_launch_pores.py`, `_make_test_tifs.py`, `_probe_shapes.py`, `_test_e2e.py`, `_test_suite.py` (17.6KB), plus binary test fixtures `_test_pred.tif` (331KB), `_test_vol.tif` (659KB).

### `seg_plausibility/` (entirely U — parallel new module, mirrors microsam_3d/ structure)
`README.md` (5.2KB), `calibrate.py` (3.3KB), `continuity_metrics.py` (2.7KB), `environment.yml` (156B), `instance_matcher.py` (9.9KB), `napari_review.py` (10.2KB), `plausibility_report.py` (7.5KB), `run.py` (4.6KB) — 2026-07-06/07. `seg_plausibility/dev/`: `_make_synthetic.py`, `_test_pipeline.py`.

### `analysis/` (most actively developed area; mixed T/U)
Tracked: `_inspect_nb.py`, `_inspect_nb2.py`, `_inspect_step8.py`, `_patch_nb.py`, `_patch_nb_step8.py` (one-off notebook-patch scripts, committed 2026-05-31), `check_labels.py`, `colab_psd_diagnostics.ipynb` (249KB), `data_registry.json` (30.7KB, M — actively edited), `hash_report_annotations.json`, `implementation_contract.md`, `iter02_registry_mutation_request.json`, `iter_02_registry_mutation_request_corrected_latest_predictions.json`, `iter_02_registry_mutation_request_corrected_latest_predictions_yfix.json` (3-way patch-on-patch naming), `nlm_annotation_audit.txt`, `psd_diagnostics_core.py` (47KB, M), `recover_missing_plots.py`, `run_psd_diagnostics.py` (35KB, M), `start_iter02_slice_injection.py`, `vogel_psd.pdf` (541KB).
Untracked: `iteration_state.json` (7.3KB), `psd_topology_metrics.py` (19.7KB, 2026-07-07 — likely near-duplicate of `legacy/pores_analysis/topology_metrics.py`, see §7).

**`analysis/pore_metrics_research/`** (entirely U, new research staging area): `decisions.md`, `stage1_research_prompt.md`, `stage2_implementation_prompt.md`, plus `papers/` — 6 reference PDFs totaling ~15MB, plus `validation_run/sub_z200_300.nii.gz` (~3MB binary test data).

**`analysis/selected_outputs/`** (entirely U, large binary/JSON output dump — see §7 for size flags): `bnei_reem/inference_chunks_preview.png`, `psd_table.csv`, `smoother.png`, and **`bnei_reem/seg_plausibility_i4/errors.json` (~66MB)** and **`bnei_reem/seg_plausibility_i4/instance_map.tif` (~1.05GB — largest file in the repo)**, `track_table.csv` (~7.5MB). `mishmar_hanegev2_slice_exports/` has an empty `_terminal_probe.txt`, `export_slice_triplets.py`, and triplicated slice-preview PNGs across the parent dir and two subfolders. `mishmar_hanegev_Cu011_samp_2_Rec_nlm/` and `nlm_volume/` each carry a near-identical 9-file set of `bad_slices_iter*`/`eligibility_iter*`/`injected_predictions_iter*` JSONs.

**`analysis/synopsis_i3/`** (32 files) and **`analysis/synopsis_i4/`** (35 files) — entirely U, `slice_NNNN.png` dumps (~500-675KB each, ~35MB combined), largely overlapping slice-number sets between the two iterations.

### Empty files (0 bytes) repo-wide
`_make_synopsis_i3_err.log`, `_make_synopsis_i4_err.log`, `_napari_seg_plausibility_i4_log3.txt`, `_seg_plausibility_i3_scratch_run.log` (all root), `analysis/selected_outputs/mishmar_hanegev2_slice_exports/_terminal_probe.txt`.

---

## 2. Per-file purpose

### Repo root
- `__path__.py` — central path constants (ImageJ path, nnUNet_raw path, staging dirs) imported by preprocessing scripts.
- `chunk_extractor.py` — extracts first 150 Z-slices from full volumes for smaller test chunks.
- `debug_labels_777.py` / `_followup.py` — diagnostic tracing of label-value divergence across annotation/raw/preprocessed stages for Dataset777_GCEF.
- `extract_trainlog.py` — parses nnUNet training logs (epoch/loss/dice) into a DataFrame/plots.
- `inspect_predictions.py` — CLI opening a prediction + original volume together in Napari.
- `make_annotations.py` — Napari-based interactive polygon annotation tool with Otsu threshold assist.
- `make_psd_plot.py` — plots a pore-size-distribution histogram from a PSD result CSV.
- `merge_annotations.py` — merges two sparse 3D TIFF annotation stacks voxel-wise.
- `otsu_threshold_3d.py` — global Otsu threshold CLI for a 3D TIFF volume.
- `postprocessing_nnUNet_predict.py` — converts `.nii.gz` predictions to `.mha` via ImageJ macro.
- `postprocessing_nnUNet_predict_concatenate.py` — reassembles split inference outputs into whole volumes.
- `preprocessing_nnUNet_predict.py` / `_tif.py` — converts raw volumes to normalized `.nii.gz` for inference; both import `preprocessing_nnUNet_train.py`.
- `preprocessing_nnUNet_predict_split.py` — splits a volume into chunks for nnUNet prediction.
- `preprocessing_nnUNet_train.py` — builds the nnUNet training dataset (conversion, normalization, dataset.json); imports `__path__.py`.
- `retrieve_dice_score.py` — aggregates Dice/FP/FN metrics from nnUNet `summary.json` files into CSV.
- `select_slices_and_predict.py` — selects informative slices, optionally runs `nnUNetv2_predict`, exports a bootstrap annotation volume.
- `train_fresh_bnei_reem.py` / `train_iter4_continue_bnei_reem.py` — GPU-pinned training launchers for specific model iterations.
- `nnUNetTrainer_betterIgnoreSampling.py` — custom nnUNet trainer/dataloader overriding foreground sampling / ignore-label logic; distributed by file-copy into the installed nnunetv2 package, not by import.
- `_train_wrapper.py` — training entry wrapper patching `torch.load` and pretrained-weight shape mismatches for PyTorch 2.6.
- `_run_iter03/04/04_continue.py`, `_run_fresh_bnei_reem_i2/i3/i3_lowlr/i3_scratch/i4.py`, `_run_mishmar_hnegev_scratch/trained.py` — per-iteration train-from-scratch/fine-tune driver scripts (copy-paste variants of one pattern).
- `_run_inference_*.py` (iter03/04/04_continue, fresh_bnei_reem variants, mishmar_iter02, nlm_iter02) — per-model standalone inference scripts; Windows multiprocessing-spawn guarded.
- `_run_fresh_then_compare_napari.py` — subprocess-orchestrates inference then launches a Napari comparison.
- `_compare_predictions.py` — prints comparison metrics between GT and OLD/NEW/LOW_LR predictions.
- `_find_dataset_json.py` — walks HIVE directories to locate `dataset.json`/`plans.json`.
- `_inspect_labels.py` — prints per-label voxel counts for GT vs. prediction.
- `_verify_i2_paths.py` — checks existence of expected files/dirs for the i2 iteration pipeline.
- `_launch_napari_*.py` (12 variants) — one-off launchers opening `microsam_3d/run.py` or `inspect_predictions.py` with iteration-specific paths.
- `_launch_napari_seg_plausibility_i3_scratch/i4.py` — launchers for `seg_plausibility/napari_review.py`.
- `_make_synopsis_i3/i4.py` — export PNG triptych synopsis (raw|GT|prediction) per annotated slice.
- `_plot_i3_metrics.py` / `_plot_lowlr_metrics.py` — parse a training log and plot loss/dice curves.
- `_launch_parallel_training.ps1` — kicks off multiple training runs in parallel (likely per-GPU).

### analysis/
- `psd_diagnostics_core.py` — the live, maintained PSD compute/diagnostics module (`run_psd_pipeline`, `build_psd_table`, `build_summary`); no CLI, designed to be imported.
- `psd_topology_metrics.py` — topology/connectivity metrics extension (Euler characteristic, connectivity density/probability, anisotropy, tortuosity); imported by `run_psd_diagnostics.py`.
- `run_psd_diagnostics.py` — CLI entrypoint running the full PSD pipeline on real data.
- `recover_missing_plots.py` — regenerates missing plot/CSV artifacts from an existing run's `result_psd.json`.
- `check_labels.py` — inspects annotation vs. prediction label distributions.
- `start_iter02_slice_injection.py` — selects unannotated prediction slices and writes a proposed annotation-registry mutation JSON (does not mutate the registry directly).
- `_inspect_nb*.py` / `_patch_nb*.py` — throwaway scripts to inspect/patch specific cells of `colab_psd_diagnostics.ipynb`.
- `colab_psd_diagnostics.ipynb` — Colab notebook counterpart to `run_psd_diagnostics.py`.
- `data_registry.json`, `iteration_state.json`, `hash_report_annotations.json`, `iter02_registry_mutation_request*.json` — pipeline state/registries, not code.
- `selected_outputs/mishmar_hanegev2_slice_exports/export_slice_triplets.py` — exports per-slice PNG triplets for QA, reading paths from `data_registry.json`.

### legacy/pores_analysis/ (self-described as superseded by `analysis/psd_diagnostics_core.py`)
- `__init__.py` — package init exposing the public API.
- `distance_transform.py` — anisotropic EDT (CuPy/SciPy fallback).
- `local_thickness.py` — morphological-opening local thickness (Hildebrand & Rüegsegger).
- `psd_calculator.py` — main PSD pipeline (Vogel et al. 2010 constraints).
- `psd_output.py` — DataFrame/CSV/plot formatting.
- `topology_metrics.py` — legacy topology/connectivity port; docstring self-identifies as dead code (nothing in the live pipeline imports it).
- `extended_pipeline.py` — orchestrates `psd_calculator` + `topology_metrics` (`compute_psd_extended`).
- `block_processor.py` — chunked processing with halo overlap for large volumes.
- `checkpoint_manager.py` — Colab-timeout-resilient checkpointing.
- `config_loader.py` — loads `config/pores_analysis/config.yaml`.
- `psd_diagnostics.py` — observability helpers (histograms, spike detection).
- `psd_entrypoint.py` — CLI tying config + calculator + output together.
- `synthetic_volume.py` — generates synthetic sphere-packing test volumes.
- `test_psd_synthetic.py`, `run_tests.py`, `check_imports.py`, `example_workflow.py` — test/demo scaffolding.

### preprocess/ and preprocess_playground/
- `preprocess/gpu_nlm_torch.py` — GPU (CUDA/PyTorch) 3D non-local-means denoising, chunked.
- `preprocess/normalization.py` — slice-stacking + "norm200" normalization (ported from `legacy/preprocess_ct_images.py`).
- `preprocess/run_preprocess.py` — stack → normalize → NLM → write TIFF pipeline.
- `preprocess_playground/filters_3d.py` — gaussian/median/NLM filters for interactive experimentation.
- `preprocess_playground/normalization.py` — playground copy of the norm200 logic.
- `preprocess_playground/run_napari_filters.py` — interactive Napari viewer for filter experimentation.
- `legacy/preprocess_ct_images.py` — original per-slice CT preprocessing (source both normalization.py copies port from).

### microsam_3d/
- `correction_store.py` — accumulates accepted manual corrections for retraining export.
- `embedder.py` — lazy per-Z-slice SAM embedding cache.
- `error_map.py` — computes a prediction/GT disagreement map.
- `napari_plugin.py` — Napari dock-widget helpers, ROI loading.
- `predictor.py` — runs SAM per Z-slice within a bbox.
- `run.py` — CLI launching the interactive Napari micro-SAM proofreading session (the module most root `_launch_napari_*.py` scripts invoke).
- `dev/*` — smoke tests and dev launchers (`_inspect_sam.py`, `_launch_nlm.py`, `_launch_pores.py`, `_make_test_tifs.py`, `_probe_shapes.py`, `_test_e2e.py`, `_test_suite.py`).

### seg_plausibility/
- `calibrate.py` — computes IoU/area-ratio/centroid-distance percentiles to calibrate thresholds.yaml.
- `continuity_metrics.py` — per-transition continuity metrics between consecutive slices.
- `instance_matcher.py` — per-slice instance labeling + cross-slice IoU matching + persistent ID assignment.
- `napari_review.py` — Napari viewer for reviewing flagged plausibility errors.
- `plausibility_report.py` — event detection (appear/disappear/split/merge) + report export.
- `run.py` — CLI entrypoint tying the above together.
- `dev/_make_synthetic.py`, `dev/_test_pipeline.py` — synthetic-data test harness.

### training_diag/, config/, Utilities/
- `training_diag/check_data.py` — diagnostic CLI for nnU-Net training data (value audit, label integrity, intensity stats, Napari view).
- `config/pores_analysis/config.yaml` — config consumed by `legacy/pores_analysis/config_loader.py`.
- `Utilities/mkdir_movefiles.sh` — creates output dirs and moves/organizes files.

### .claude/, .github/, .vscode/
- `.claude/settings.local.json` — local Claude Code permission allowlist.
- `.github/agents/*.agent.md` — four agent specs: data-registry path validation, ML workflow orchestration, notebook building, PSD analysis running.
- `.github/copilot-instructions.md` — project mental model + environment rules for Copilot/agents (see §4 — one section is stale).
- `.github/skills/report-agent-run-status.skill.md` — read-only status-report skill reading `iteration_state.json`.
- `.vscode/mcp.json` — placeholder/disabled MCP server config.

### Data/config files
- `dataset_info.json` — canonical label map for Dataset777_GCEF (0=ToPredict, 1=Matrix, 2=Stones, 3/4=POM types, 5=unused, 6=Pore) + display colors.

---

## 3. Pipeline-stage mapping

**Data ingestion**
`chunk_extractor.py`, `_find_dataset_json.py`, `_verify_i2_paths.py`, `merge_annotations.py`, `make_annotations.py`, `analysis/start_iter02_slice_injection.py`, `select_slices_and_predict.py` (selection half), `analysis/data_registry.json`, `analysis/iteration_state.json`, `analysis/hash_report_annotations.json`, `analysis/iter02_registry_mutation_request*.json`

**Preprocessing**
`preprocessing_nnUNet_train.py`, `preprocessing_nnUNet_predict.py`, `preprocessing_nnUNet_predict_tif.py`, `preprocessing_nnUNet_predict_split.py`, `__path__.py`, `preprocess/gpu_nlm_torch.py`, `preprocess/normalization.py`, `preprocess/run_preprocess.py`, `preprocess/colab_cli_runner.ipynb`, `preprocess_playground/filters_3d.py`, `preprocess_playground/normalization.py`, `preprocess_playground/run_napari_filters.py`, `legacy/preprocess_ct_images.py`, `otsu_threshold_3d.py`

**Model / training**
`nnUNetTrainer_betterIgnoreSampling.py`, `_train_wrapper.py`, `train_fresh_bnei_reem.py`, `train_iter4_continue_bnei_reem.py`, `_run_iter03/04/04_continue.py`, `_run_fresh_bnei_reem_i2/i3/i3_lowlr/i3_scratch/i4.py`, `_run_mishmar_hnegev_scratch/trained.py`, `_launch_parallel_training.ps1`, `colab_nnUNet_pipeline.ipynb` (spans training + inference)

**Inference**
`_run_inference_iter03/04/04_continue.py`, `_run_inference_fresh_bnei_reem*.py`, `_run_inference_mishmar_iter02.py`, `_run_inference_nlm_iter02.py`, `_run_fresh_then_compare_napari.py`, `postprocessing_nnUNet_predict_concatenate.py`, `postprocessing_nnUNet_predict.py`, `postprocessing_pipeline.ipynb`, `run_remaining_fullctx_overnight.ipynb`, `select_slices_and_predict.py` (predict half)

**Evaluation**
`_compare_predictions.py`, `_inspect_labels.py`, `analysis/check_labels.py`, `retrieve_dice_score.py`, `debug_labels_777.py`, `debug_labels_777_followup.py`, `training_diag/check_data.py`, `seg_plausibility/*` (calibrate.py, continuity_metrics.py, instance_matcher.py, plausibility_report.py, run.py, dev/*), `legacy/pores_analysis/*` (PSD/topology metrics as evaluation of segmentation output), `analysis/psd_diagnostics_core.py`, `analysis/psd_topology_metrics.py`, `analysis/run_psd_diagnostics.py`, `analysis/recover_missing_plots.py`, `analysis/colab_psd_diagnostics.ipynb`

**Output / reporting**
`extract_trainlog.py`, `_plot_i3_metrics.py`, `_plot_lowlr_metrics.py`, `_make_synopsis_i3/i4.py`, `make_psd_plot.py`, `analysis/selected_outputs/mishmar_hanegev2_slice_exports/export_slice_triplets.py`, `seg_plausibility/napari_review.py`, `microsam_3d/napari_plugin.py`, `microsam_3d/error_map.py`, all root `_launch_napari_*.py`, `inspect_predictions.py`

**Utilities / shared**
`microsam_3d/embedder.py`, `predictor.py`, `correction_store.py`, `run.py`, `dev/*`, `legacy/pores_analysis/config_loader.py`, `checkpoint_manager.py`, `block_processor.py`, `distance_transform.py`, `local_thickness.py`, `synthetic_volume.py`, `check_imports.py`, `run_tests.py`, `config/pores_analysis/config.yaml`, `Utilities/mkdir_movefiles.sh`, `__path__.py`, `dataset_info.json`, `.claude/`, `.vscode/`

**Unclear**
`analysis/_inspect_nb*.py`, `_patch_nb*.py` (meta-scripts editing the notebook itself), `legacy/pores_analysis/example_workflow.py`, `test_psd_synthetic.py` (demo/test, not a pipeline stage per se), `legacy/pores_analysis/topology_metrics.py` (self-described dead code)

---

## 4. Existing markdown docs audit

21 `.md` files found.

| File | Flag | Notes |
|---|---|---|
| `README.md` | **accurate** | Full workflow doc; every referenced script/image verified to exist and match. |
| `.claude/prompts/repo-scan-prompt.md` | **orphaned/unclear purpose** | The prompt that generates this very report; its required output (`REPO_SCAN.md`) did not exist before this run — never previously executed or its output was discarded. |
| `.github/agents/data-registry-path-validation.agent.md` | **accurate** | Schema matches `analysis/data_registry.json` (plus one undocumented extra key, `training_runs` — minor gap). |
| `.github/agents/ml-workflow-orchestrator.agent.md` | **accurate** | Matches `analysis/iteration_state.json` fields and `dataset_info.json` class semantics exactly. |
| `.github/agents/notebook-builder.agent.md` | **accurate** | Consistent with actual `colab_nnUNet_pipeline.ipynb`. |
| `.github/agents/psd-analysis-runner.agent.md` | **accurate** | Matches `analysis/run_psd_diagnostics.py` + `psd_diagnostics_core.py` (both actively maintained). |
| `.github/copilot-instructions.md` | **outdated (partial)** | Sections 1-7 accurate; §8 "Agent Permission Matrix" describes 5 agents (`@architect`, `@scientist`, `@segmentation`, `@performance`, `@reviewer`) whose files do not exist — only 4 different agent files are actually present in `.github/agents/`. Stale, superseded section. |
| `.github/skills/report-agent-run-status.skill.md` | **accurate (minor staleness)** | Primary source (`iteration_state.json`) valid; secondary fallback source `analysis/plan.md` does not exist. |
| `analysis/implementation_contract.md` | **accurate** | Matches `psd_diagnostics_core.py` + `run_psd_diagnostics.py` output schema. |
| `analysis/pore_metrics_research/decisions.md` | **accurate** | D1-D5 decisions verified reflected in `stage2_implementation_prompt.md` and implemented in `legacy/pores_analysis/topology_metrics.py`. |
| `analysis/pore_metrics_research/stage1_research_prompt.md` | **accurate (historical, fulfilled)** | Instructions carried out; `decisions.md` complete. |
| `analysis/pore_metrics_research/stage2_implementation_prompt.md` | **accurate (historical, fulfilled)** | Referenced functions all exist and are exported. |
| `legacy/pores_analysis/README.md` | **accurate (recently updated)** | Matches `compute_psd()` signature; module-structure list is incomplete (omits `topology_metrics.py`, `extended_pipeline.py`, `config_loader.py`, and 5 others) but not incorrect. |
| `legacy/pores_analysis/BUGFIX_CHANGELOG.md` | **accurate (historical record)** | Point-in-time changelog; described fix still reflects current behavior. |
| `legacy/pores_analysis/PSD_DIAGNOSTICS_SUMMARY.md` | **outdated** | References `experiments/synthetic_psd_diagnostics.py`, which does not exist anywhere in the repo (no `experiments/` dir at all); functionality has moved to `analysis/psd_diagnostics_core.py`. |
| `legacy/pores_analysis/USAGE_GUIDE.md` | **accurate** | Consistent with sibling README, no drift detected. |
| `microsam_3d/README.md` | **accurate** | All referenced modules/CLI verified to exist. |
| `microsam_3d/propagation_guide.md` | **accurate** | Complements README (deeper UI layer), not a duplicate. |
| `preprocess_playground/README.md` | **accurate** | Matches actual filter modules and CLI usage. |
| `seg_plausibility/README.md` | **accurate** | All referenced modules and output schema verified. |
| `setup_prompt.md` | **accurate** | Correctly points at current `analysis/` locations (unlike the stale legacy summary doc above). |

Summary: 18 accurate (2 with minor staleness noted), 2 outdated, 1 orphaned/unclear, 0 true duplicates.

---

## 5. AI model references

**None found.** No hardcoded AI model name/version strings (`claude-*`, `gpt-*`, `sonnet`, `opus`, `haiku`, `fable`, `anthropic`, `gemini`, `llama-`, `mistral`, `cohere`, or model IDs in config/env/json/yaml files) exist anywhere in the repository's code, notebooks, or configs.

The only keyword matches are the prompt file describing this very search task, which is self-referential, not an actual model reference:
- `.claude/prompts/repo-scan-prompt.md:29-30` — the "### 5. AI model references" instruction text itself
- `.claude/prompts/repo-scan-prompt.md:45` — mentions "ambiguous model references" as a category to flag, in the abstract

Checked and clean: `.claude/settings.local.json`, `.claude/scheduled_tasks.lock`, all `.ipynb` files (searched as raw JSON text), all `*.json`/`*.yaml`/`*.yml`/`*.env` files.

**Conclusion for the stated purpose ("reconcile all model references against the finalized choice")**: there is nothing to reconcile — no model name is currently hardcoded anywhere in this repo.

---

## 6. Links / external resources

**`README.md`**
- L2 — `https://www.ufz.de/` (UFZ)
- L2 — `https://www.helmholtz-imaging.de/`
- L9 — `https://doi.org/10.1038/s41592-020-01008-z` (Nature Methods citation)
- L12 — `https://doi.org/10.1016/j.geoderma.2025.117321` (Geoderma citation)
- L56 — `https://www.ufz.de/index.php?en=51499` (EVE cluster)
- L59, L124 — `https://doi.org/10.22541/essoar.173395846.68597189/v1` (project publication)
- L96 — `https://github.com/conda-forge/miniforge#miniforge3`
- L114 — `https://github.com/haesleinhuepf/devbio-napari`
- L155 — `https://github.com/MIC-DKFZ/nnUNet/blob/master/documentation/installation_instructions.md#installation-instructions`
- L157 — `https://github.com/MIC-DKFZ/nnUNet.git`
- L169 — `https://imagej.net/software/fiji/downloads#other-downloads`
- L247 — `https://download.pytorch.org/whl/cu117`

**`setup_prompt.md`**
- L18 — `https://pytorch.org/get-started/locally/`
- L21 — `https://download.pytorch.org/whl/cu124`

**`microsam_3d/README.md`**
- L39 — `https://www.nature.com/articles/s41592-024-02580-4`
- L43 — `https://arxiv.org/abs/2503.08373`
- L47 — `https://www.frontiersin.org/articles/10.3389/fcell.2022.842342/full`
- L51 — `https://www.nature.com/articles/nmeth.4331`
- L55 — `https://arxiv.org/abs/2304.02643`

**Code comments**
- `preprocess/run_preprocess.py:24` — `https://download.pytorch.org/whl/cu124`
- `preprocess/gpu_nlm_torch.py:24` — `https://download.pytorch.org/whl/cu124`

**Notebook metadata (not real content links, Colab execution metadata)**
- `analysis/colab_psd_diagnostics.ipynb:67,127,183,255,467` — `"base_uri": "https://localhost:8080/"`

**Untracked training/inference log files** (repeating nnU-Net's own stdout notice, not authored links)
- `_fresh_bnei_reem_i2/i3/i3_lowlr/i3_scratch/i4.log`, `_iter03_run4/run5.log`, `_iter04_run2.log`, `_train_fresh_bnei_reem.log`, `_train_iter4_continue_bnei_reem.log` — all repeat `https://github.com/MIC-DKFZ/nnUNet/blob/master/documentation/resenc_presets.md`; `_iter03_run4.log:265` additionally has `https://docs.python.org/3/library/multiprocessing.html`.

No URLs found in: `colab_nnUNet_pipeline.ipynb`, `postprocessing_pipeline.ipynb`, `preprocess/colab_cli_runner.ipynb`, `run_remaining_fullctx_overnight.ipynb`.

---

## 7. Clutter candidates

**High-priority (repo bloat / accidental commit risk):**
- `analysis/selected_outputs/bnei_reem/seg_plausibility_i4/instance_map.tif` — **~1.05GB**, untracked. Largest file in the repo by a huge margin; would be catastrophic to `git add`.
- `analysis/selected_outputs/bnei_reem/seg_plausibility_i4/errors.json` — **~66MB**, untracked.
- `analysis/selected_outputs/bnei_reem/seg_plausibility_i4/track_table.csv` — ~7.5MB, untracked.
- `analysis/pore_metrics_research/papers/*.pdf` — 6 files, ~15MB total, untracked reference PDFs (probably fine to keep, but worth deciding whether they belong in git or an external references folder).
- `analysis/pore_metrics_research/validation_run/sub_z200_300.nii.gz` — ~3MB binary test volume, untracked.
- `analysis/synopsis_i3/` (32 files) + `analysis/synopsis_i4/` (35 files) — ~35MB combined PNG dumps, largely overlapping slice sets between the two iterations (re-rendered per iteration rather than reused).

**Committed-but-should-not-be (log/scratch files already in git history):**
- `mishmar_psd.log`, `_inference_err.txt`, `_inference_log.txt`, `_inference_nlm_err.txt`, `_inference_nlm_log.txt`, `_napari_nlm_err.txt`, `_napari_nlm_log.txt` — all tracked log outputs, committed alongside the "Add inference scripts and logs" commit. Flagged because logs are regenerable run artifacts, not source.
- `analysis/_inspect_nb.py`, `_inspect_nb2.py`, `_inspect_step8.py`, `_patch_nb.py`, `_patch_nb_step8.py` — tracked one-off notebook-patching scripts; useful history but arguably scratch tooling rather than pipeline source.

**Untracked scratch sprawl (root, ~110 files):** the entire `_run_*`, `_launch_napari_*`, `_*_log/_err.log`, `_plot_*`, `_make_synopsis_*` family described in §1. This is the dominant clutter pattern in the repo: each new model iteration or comparison spawns 3-6 new copy-pasted scripts plus their log output, none of which get cleaned up or consolidated. Two loose output files sit directly in repo root: `_comparison_iter04_continue_vs_fresh.pdf/.png`.

**Empty files (0 bytes, no content, safe to remove):**
`_make_synopsis_i3_err.log`, `_make_synopsis_i4_err.log`, `_napari_seg_plausibility_i4_log3.txt`, `_seg_plausibility_i3_scratch_run.log`, `analysis/selected_outputs/mishmar_hanegev2_slice_exports/_terminal_probe.txt`.

**Empty directories (no files):**
`preprocess/nlm_output/`, `preprocess/norm200_output/`, `legacy/pores_analysis/results/`.

**Likely duplicate implementations (not simple file dupes, but overlapping code):**
- `analysis/psd_topology_metrics.py` (19.7KB, 2026-07-07) vs. `legacy/pores_analysis/topology_metrics.py` (18.6KB, 2026-07-06) — similar name/size, written a day apart. `analysis/psd_topology_metrics.py` is the one actually imported by `run_psd_diagnostics.py`; the legacy one is self-described as dead code. Worth confirming these aren't meant to be the same file forked by accident.
- `preprocess/normalization.py` vs. `preprocess_playground/normalization.py` — both port the same norm200 logic from `legacy/preprocess_ct_images.py`; one is "production," one is "playground," per `.github/copilot-instructions.md`, but they duplicate logic.
- Triplicated slice-export PNGs across `analysis/selected_outputs/mishmar_hanegev2_slice_exports/` and its two subfolders (same slice numbers 0086/0253/0543, slightly different file sizes each copy).
- Duplicated JSON metric families (`bad_slices_iter*`, `eligibility_iter*`, `injected_predictions_iter*`) mirrored near-identically across `mishmar_hanegev_Cu011_samp_2_Rec_nlm/` and `nlm_volume/` subfolders.
- 3-way patch-on-patch naming in `analysis/iter02_registry_mutation_request.json` → `iter_02_registry_mutation_request_corrected_latest_predictions.json` → `..._yfix.json` — superseding versions kept side by side rather than replaced.

**No-incoming-reference candidates:**
- `legacy/pores_analysis/topology_metrics.py` — docstring itself states nothing in the live pipeline imports it.
- `.vscode/mcp.json` — described as a "placeholder/disabled stub" per its own content; not wired to anything active.
- `Utilities/nifti_io.jar` — a binary jar committed to the repo; unclear if anything still invokes it directly versus the Fiji macros calling ImageJ's own bundled functionality.

---

## 8. Dependency notes

**Within `analysis/`**
- `run_psd_diagnostics.py` imports `psd_diagnostics_core` and `psd_topology_metrics` (flat, same-folder imports — relies on `analysis/` being on `sys.path` or CWD).
- `recover_missing_plots.py` imports `plot_psd_extras` from `psd_diagnostics_core`.
- `psd_diagnostics_core.py` has no internal repo imports (stdlib/numpy only) — it's the most depended-upon analysis module; moving/renaming it breaks both files above.
- `psd_topology_metrics.py` is not actually imported by `psd_diagnostics_core.py` (only referenced in docstrings) — but IS imported by `run_psd_diagnostics.py`.
- No file in `analysis/` imports from `legacy/pores_analysis/` or vice versa — confirmed parallel/duplicate implementations.
- `analysis/_inspect_nb*.py` / `_patch_nb*.py` hardcode a relative path to `colab_psd_diagnostics.ipynb` — only valid if run with CWD = `analysis/`.

**Within `legacy/pores_analysis/`**
- Internal package uses relative imports rooted at `__init__.py` (`from .distance_transform import ...` etc.) covering `distance_transform.py`, `local_thickness.py`, `psd_calculator.py`, `psd_output.py`, `block_processor.py`, `checkpoint_manager.py`, `topology_metrics.py`, `extended_pipeline.py`. Renaming/moving any of these breaks `__init__.py`'s import block and anything doing `from legacy.pores_analysis import ...`.
- `config_loader.py` resolves `config/pores_analysis/config.yaml` via `Path(__file__).resolve().parents[2]` — moving `legacy/pores_analysis/` up or down a directory level breaks this path resolution.
- `test_psd_synthetic.py` uses flat (non-relative) imports (`from psd_calculator import compute_psd`), inconsistent with the rest of the package; `run_tests.py` and `check_imports.py` compensate with an explicit `sys.path.insert(0, ...)`.

**`nnUNetTrainer_betterIgnoreSampling.py`**
- Not imported via Python `import` anywhere — instead **file-copied** at runtime into the installed `nnunetv2` package's trainer-variants directory by every `_run_*`/`train_*` script and by `colab_nnUNet_pipeline.ipynb`, then invoked by trainer **name string**. Renaming this file breaks the copy-step (the `shutil.copy` source path) in essentially every training/inference script in the repo, but not the trainer-name string itself unless the class name inside also changes.

**Root `_*.py` scripts**
- `preprocessing_nnUNet_predict.py` and `preprocessing_nnUNet_predict_tif.py` both `from preprocessing_nnUNet_train import convert_mha_to_hdr, img_normalize` — renaming `preprocessing_nnUNet_train.py` breaks both.
- `preprocessing_nnUNet_train.py` and `postprocessing_nnUNet_predict.py` both `from __path__ import ...` — renaming `__path__.py` breaks both.
- `_run_fresh_then_compare_napari.py` invokes `_run_inference_fresh_bnei_reem.py` as a subprocess (not import) — renaming the target breaks the orchestrator.
- `_run_iter04_continue.py` asserts the existence of `_run_inference_iter04_continue.py` by path (subprocess-style soft dependency).
- All root `_launch_napari_*.py` scripts invoke `microsam_3d/run.py` via subprocess or `sys.path.insert(0, MICROSAM_DIR)`; `_launch_napari_seg_plausibility_*.py` scripts invoke `seg_plausibility/napari_review.py` the same way.
- `_verify_i2_paths.py` hardcodes and checks absolute paths to `_train_wrapper.py` and `_run_inference_fresh_bnei_reem_i2.py`.
- `_run_inference_*.py` scripts each independently import `nnunetv2.inference.predict_from_raw_data.nnUNetPredictor` and duplicate a `torch.load` patch inline — no cross-imports between them, but the patch logic is copy-pasted N times rather than shared.

**`microsam_3d/` and `seg_plausibility/`**
- `microsam_3d/predictor.py` does `from embedder import VolumeEmbedder` (flat import, requires the module dir on `sys.path`).
- `seg_plausibility/run.py` and `calibrate.py` import flat-style from `instance_matcher`, `continuity_metrics`, `plausibility_report` — renaming any of the three breaks both entrypoints.
- `seg_plausibility/dev/_test_pipeline.py` imports `dev/_make_synthetic.py` via an explicit `sys.path.insert`.

**`colab_nnUNet_pipeline.ipynb` role**
This is the master, generalized reference pipeline (GPU check → register custom trainer by file-copy → set nnUNet env paths → build dataset → plan/preprocess → patch `polylr.py` → train via `_train_wrapper.py` → parse logs → split volume via `preprocessing_nnUNet_predict_split.py` → infer → reassemble via `postprocessing_nnUNet_predict_concatenate.py`). The many root-level `_run_*`/`train_*`/`_run_inference_*.py` scripts are ad-hoc, hardcoded per-iteration derivatives of this same sequence — meaning the notebook is the "canonical" version and the ~40 root scripts are one-off forks of it per model iteration. `postprocessing_pipeline.ipynb` is narrower, focused only on the postprocessing/concatenation step.

---

## 9. Proposed reorganization (proposal only — not executed)

This groups the current 106 tracked + ~300 untracked files by pipeline stage, mirroring §3. **Nothing has been moved.** This is a starting point for discussion, not a final layout — in particular, the sheer number of near-duplicate `_run_*`/`_launch_napari_*` scripts (§7) suggests consolidating them into parameterized scripts (one script + a config/CLI arg per iteration) rather than just relocating ~40 near-identical files into a folder.

```
nnUNet4SoilXrayCT/
├── 00_docs/                      README.md, setup_prompt.md, LICENSE, Figures/, litreture/
├── 01_data_ingestion/            make_annotations.py, merge_annotations.py, chunk_extractor.py,
│                                  _find_dataset_json.py, _verify_i2_paths.py,
│                                  select_slices_and_predict.py (selection half)
│   └── registry/                 analysis/data_registry.json, iteration_state.json,
│                                  hash_report_annotations.json, iter02_registry_mutation_request*.json,
│                                  analysis/start_iter02_slice_injection.py
├── 02_preprocessing/
│   ├── nnunet/                   preprocessing_nnUNet_train.py, preprocessing_nnUNet_predict*.py, __path__.py
│   ├── filters/                  preprocess/  (gpu_nlm_torch.py, normalization.py, run_preprocess.py)
│   ├── playground/               preprocess_playground/  (kept separate — explicitly experimental)
│   ├── legacy/                   legacy/preprocess_ct_images.py
│   └── otsu_threshold_3d.py
├── 03_training/
│   ├── nnUNetTrainer_betterIgnoreSampling.py, _train_wrapper.py
│   ├── runs/                      all per-iteration _run_*.py / train_*.py driver scripts
│   │                              (candidate for consolidation into one parameterized script)
│   └── _launch_parallel_training.ps1
├── 04_inference/
│   ├── runs/                      all _run_inference_*.py (same consolidation candidate)
│   ├── postprocessing_nnUNet_predict.py, postprocessing_nnUNet_predict_concatenate.py
│   ├── postprocessing_pipeline.ipynb, run_remaining_fullctx_overnight.ipynb
│   └── _run_fresh_then_compare_napari.py
├── 05_evaluation/
│   ├── psd/                       analysis/psd_diagnostics_core.py, psd_topology_metrics.py,
│   │                              run_psd_diagnostics.py, recover_missing_plots.py,
│   │                              colab_psd_diagnostics.ipynb, implementation_contract.md,
│   │                              analysis/pore_metrics_research/
│   ├── legacy_pores_analysis/     legacy/pores_analysis/ (kept intact as a self-contained package;
│   │                              flag for deprecation once analysis/ fully supersedes it — see Q1)
│   ├── seg_plausibility/          seg_plausibility/ (kept intact — self-contained module)
│   ├── labels_debug/              debug_labels_777*.py, _compare_predictions.py, _inspect_labels.py,
│   │                              analysis/check_labels.py, retrieve_dice_score.py,
│   │                              training_diag/check_data.py
│   └── microsam_3d/               microsam_3d/ (kept intact — self-contained module)
├── 06_reporting/
│   ├── logs/                       extract_trainlog.py, _plot_i3_metrics.py, _plot_lowlr_metrics.py
│   ├── synopsis/                   _make_synopsis_i3/i4.py, make_psd_plot.py,
│   │                                analysis/selected_outputs/, analysis/synopsis_i3/, synopsis_i4/
│   ├── napari_launchers/           all root _launch_napari_*.py + inspect_predictions.py
│   └── run_logs_archive/           all *.log / *_err.log (candidate: .gitignore + delete from history)
├── 07_utilities/                   Utilities/, config/, Fiji_macros/, dataset_info.json
├── .claude/, .github/, .vscode/    unchanged (tooling config, not pipeline)
```

Key open design choice: whether `legacy/pores_analysis/`, `microsam_3d/`, and `seg_plausibility/` should be flattened into the numbered structure or kept as self-contained sibling packages (each already has its own README + environment.yml, suggesting they're meant to be somewhat independent). The sketch above keeps them intact under the evaluation stage as the more conservative option.

---

## 10. Open questions for the maintainer

1. **`analysis/psd_topology_metrics.py` vs `legacy/pores_analysis/topology_metrics.py`** — near-identical size, written a day apart (2026-07-06 vs 07-07). Is the legacy one truly dead, or was this an intentional fork that should be reconciled/deleted?
2. **Is `legacy/pores_analysis/` still needed at all?** Its own README says it's superseded by `analysis/psd_diagnostics_core.py`, yet it received modifications as recently as 2026-07-06/07 (new `extended_pipeline.py`, `topology_metrics.py`, `environment.yml`). Is it being actively extended in parallel with `analysis/`, or should that work move into `analysis/` instead?
3. **`.github/copilot-instructions.md` §8** references 5 agents (`@architect`, `@scientist`, `@segmentation`, `@performance`, `@reviewer`) that don't exist as files — was this section aspirational, superseded, or should the 4 actual agent files be renamed/expanded to match it?
4. **Should the ~110 untracked root-level `_*` scratch scripts and logs be deleted, gitignored, or archived?** They represent real experiment history (each is tied to a specific model iteration) but are cluttering the repo root badly. A few already leaked into git history (`mishmar_psd.log`, `_inference_*.txt`, `_napari_nlm_*.txt`) — should those be purged from tracked files (note: purging git *history* is a separate, more invasive operation from just removing them going forward)?
5. **The ~1.05GB `instance_map.tif` and ~66MB `errors.json`** under `analysis/selected_outputs/bnei_reem/seg_plausibility_i4/` — is this expected to stay untracked forever (add to `.gitignore` explicitly), or does it need to go somewhere with proper large-file handling (e.g., Git LFS, external storage)?
6. **`analysis/pore_metrics_research/papers/`** — 6 reference PDFs (~15MB). Intended to be committed as part of the repo's research trail, or should these move to an external reference manager and just be cited by DOI/URL in `decisions.md`?
7. **Naming pattern `iter02_registry_mutation_request.json` → `..._corrected_latest_predictions.json` → `..._yfix.json`** — is the oldest of the three still needed, or can superseded mutation-request files be deleted once applied?
8. **`litreture/` directory name** — typo ("litreture" instead of "literature"). Intentional/long-standing, or worth fixing now while nothing else references it by that exact path? (Flagging since a rename is exactly the kind of small thing best batched into the later reorg pass rather than done ad hoc.)
9. **`preprocess/normalization.py` vs `preprocess_playground/normalization.py`** — is the playground copy meant to diverge permanently (experimental variants), or should playground eventually reuse the production module directly?
10. **Should `microsam_3d/`, `seg_plausibility/`, and `legacy/pores_analysis/` be treated as independent sibling packages (each with their own env/README) or folded into the main pipeline-stage folder structure in the eventual reorg?** This materially changes the shape of §9's proposal.
