# Architecture

## 1. Purpose

This document describes the pipeline-stage folder layout introduced by
the 2026-07 repository reorganization (see `REORG_PLAN.md` for the full
plan and `REORG_EXECUTION_REPORT.md` for what was actually executed).
Previously, the repository had ~110 scratch scripts scattered at repo
root (mostly one-off per-iteration training/inference/napari scripts),
several inconsistently-named top-level folders (`preprocess/`,
`preprocess_playground/`, `legacy/`, `analysis/`, `Utilities/`, ...), and
committed log files. This reorg groups everything into eight numbered
pipeline-stage folders plus a log archive.

## 2. Pipeline stage overview

- **`00_docs/`** — Static documentation assets: `Figures/` (logos,
  workflow diagram) and `literature/` (project article PDF; renamed from
  the `litreture/` typo).
- **`01_data_ingestion/`** — Ground-truth annotation and the data
  registry. Entry points: `make_annotations.py` (napari-based labeling),
  `merge_annotations.py`, `chunk_extractor.py`,
  `select_slices_and_predict.py`. `registry/` holds `data_registry.json`,
  `iteration_state.json`, `hash_report_annotations.json`, and the slice
  injection history. `scripts/verify_paths.py` is the generalized
  manifest-driven path checker (S11).
- **`02_preprocessing/`** — Converts raw `.tif`/`.mha` volumes into
  nnUNet-ready `.nii.gz` datasets. `nnunet/` holds the core
  `preprocessing_nnUNet_*.py` scripts and `__path__.py`; `filters/` is
  the CUDA-accelerated NLM/norm200 branch (was `preprocess/`);
  `playground/` is explicitly experimental (was `preprocess_playground/`);
  `legacy/` is historical reference (`preprocess_ct_images.py`).
- **`03_training/`** — `nnUNetTrainer_betterIgnoreSampling.py` (the
  custom trainer, copied into the nnUNet package at training time) and
  `scripts/run_training.py` (S1), the consolidated per-iteration training
  driver, plus `scripts/train_wrapper.py` (S2, subprocess target) and
  `scripts/launch_parallel_runs.ps1` (S3). `run_configs/*.yaml` holds one
  config per iteration.
- **`04_inference/`** — `postprocessing_nnUNet_predict*.py` (chunk
  concatenation and `.mha` export) and `scripts/run_inference.py` (S4),
  the consolidated per-iteration inference driver, plus
  `scripts/run_inference_then_review.py` (S5), which runs inference and
  then opens a napari review session (optionally building a two-model
  comparison chart). `run_configs/*.yaml` mirrors `03_training/`'s naming.
- **`05_evaluation/`** — Model/segmentation QA tooling: `labels_debug/`,
  `scripts/compare_predictions.py` (S9), `scripts/inspect_labels.py`
  (S10), `psd/` (pore-size-distribution diagnostics, including the
  `pore_metrics_research/` subproject), `legacy_pores_analysis/` (see §4
  below), `seg_plausibility/` and `microsam_3d/` (both folded in as
  self-contained modules — see §3).
- **`06_reporting/`** — Human-facing output generation:
  `scripts/launch_napari_review.py` (S6, consolidated viewer dispatcher),
  `scripts/make_synopsis.py` (S7), `scripts/plot_training_metrics.py`
  (S8), plus `extract_trainlog.py`, `make_psd_plot.py`,
  `inspect_predictions.py`, `aggregate_training_diagnostics.py` (S13,
  cross-run training-curve comparison across both soil branches).
  `synopsis_outputs/`, `selected_outputs/`, and `training_diagnostics/`
  hold regenerable QA renders (gitignored — see `.gitignore`).
- **`07_utilities/`** — `Utilities/` (SLURM submission scripts,
  `nifti_io.jar` — see §5 below), `Fiji_macros/` (image-format conversion
  macros), `config/pores_analysis/`, and `scripts/find_dataset_json.py`
  (S12).

`colab_nnUNet_pipeline.ipynb` stays at repo root as the master reference
notebook spanning stages 02-04. `dataset_info.json` stays canonical at
repo root only (per amendment E / plan §9 Q5 — most scripts resolve it
relative to `REPO_DIR`).

## 3. Folded-in modules

`microsam_3d/` (now `05_evaluation/microsam_3d/`) and `seg_plausibility/`
(now `05_evaluation/seg_plausibility/`) remain internally self-contained
— each has its own `README.md` and `environment.yml`, reflecting that
they run in independent conda environments and are optional/interactive
tooling not needed for the core train/infer loop. They were moved as
intact units (not merged file-by-file into the surrounding
`05_evaluation/` structure) specifically so their internal flat imports
(e.g. `microsam_3d/predictor.py`'s `from embedder import VolumeEmbedder`)
continue to work unmodified.

## 4. `legacy_pores_analysis/`

`05_evaluation/legacy_pores_analysis/` (moved from `legacy/pores_analysis/`)
is an **archived, not-yet-deleted** package. Per `REORG_PLAN.md` §6, a
re-verification confirmed zero internal runtime dependency between it and
the live PSD pipeline (`05_evaluation/psd/psd_diagnostics_core.py`,
`psd_topology_metrics.py`) — the two are independently-written
implementations of similar metrics with no import edge in either
direction. It is retained (not deleted) only because that re-verification
could not rule out an external, personal script outside this repo still
calling into it. See `05_evaluation/legacy_pores_analysis/ARCHIVED.md`
for the archive note and scheduled deletion in a future cleanup cycle.
**Do not build new work on this folder.**

## 5. Consolidated scripts (S1-S12)

| # | Script | Location | Replaces |
|---|---|---|---|
| S1 | `run_training.py` | `03_training/scripts/` | 12 per-iteration training scripts |
| S2 | `train_wrapper.py` | `03_training/scripts/` | `_train_wrapper.py` |
| S3 | `launch_parallel_runs.ps1` | `03_training/scripts/` | `_launch_parallel_training.ps1` |
| S4 | `run_inference.py` | `04_inference/scripts/` | 12 per-iteration inference scripts |
| S5 | `run_inference_then_review.py` | `04_inference/scripts/` | `_run_fresh_then_compare_napari.py`, `_run_iter04_continue.py` |
| S6 | `launch_napari_review.py` | `06_reporting/scripts/` | 12 `_launch_napari_*.py` |
| S7 | `make_synopsis.py` | `06_reporting/scripts/` | `_make_synopsis_i3.py`, `_make_synopsis_i4.py` |
| S8 | `plot_training_metrics.py` | `06_reporting/scripts/` | `_plot_i3_metrics.py`, `_plot_lowlr_metrics.py` |
| S9 | `compare_predictions.py` | `05_evaluation/scripts/` | `_compare_predictions.py` |
| S10 | `inspect_labels.py` | `05_evaluation/scripts/` | `_inspect_labels.py` |
| S11 | `verify_paths.py` | `01_data_ingestion/scripts/` | `_verify_i2_paths.py` |
| S12 | `find_dataset_json.py` | `07_utilities/scripts/` | `_find_dataset_json.py` |
| S13 | `aggregate_training_diagnostics.py` | `06_reporting/scripts/` | (new — no per-iteration predecessor) |

Each `<stage>/scripts/legacy_per_iteration/` folder holds the retired
originals pending a live verification cycle (see
`03_training/run_configs/VERIFIED.md` — this cycle has **not** been run
as of this reorg; do not delete the legacy copies until it has).

## 6. Data flow

```
01_data_ingestion (annotate, register)
        |
        v
02_preprocessing (tif/mha -> nii.gz, normalize, crop)
        |
        v
03_training (nnUNetv2_train, custom trainer)
        |
        v
04_inference (nnUNetv2_predict, split/concatenate)
        |
        v
05_evaluation (Dice/PSD/topology metrics, plausibility checks)
        |
        v
06_reporting (synopsis renders, napari review, plots)
```

`07_utilities/` supports every stage (SLURM submission, Fiji macros,
path-finding helpers) rather than sitting in the linear flow.

## 7. Logs and outputs

All training/inference/napari run logs live under `logs_archive/`,
indexed by `logs_archive/log_index.csv` (columns: run_type,
iteration_name, log paths, date, gpu, parsed final epoch/losses/dice,
status). See that CSV's generation note in `REORG_EXECUTION_REPORT.md`
for known heuristic-parsing limitations.
