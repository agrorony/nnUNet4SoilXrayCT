# REORG_PLAN.md — Detailed Reorganization Plan (Planning Only)

Generated 2026-07-08. Builds on `REPO_SCAN.md` (2026-07-07). **Nothing has been moved, renamed, deleted, merged, or edited** except the creation of this file. All decisions listed in `.claude/prompts/repo-reorg-plan-prompt.md` are treated as final; this document works out the mechanics only.

---

## 1. Final folder tree

```
nnUNet4SoilXrayCT/
├── LICENSE
├── README.md                              # updated, paths re-pointed (see §7)
├── ARCHITECTURE.md                        # new (see §7)
├── RESOURCES.md                            # new (see §7)
├── setup_prompt.md
├── dataset_info.json
├── .gitignore                             # updated: logs, large binaries (see §5, §8)
├── .github/
│   ├── copilot-instructions.md            # updated (see §7)
│   └── agents/*.agent.md                  # updated (see §7)
├── .vscode/                               # unchanged
├── .claude/                               # unchanged (tooling config)
│
├── 00_docs/
│   ├── Figures/                           # HI_Logo.png, UFZ_Logo.png, Workflow.png
│   └── literature/                        # renamed from `litreture/` (typo fix, §8)
│       └── nnUNet4SoilCT_atricle.pdf
│
├── 01_data_ingestion/
│   ├── make_annotations.py
│   ├── merge_annotations.py
│   ├── chunk_extractor.py
│   ├── select_slices_and_predict.py
│   ├── scripts/
│   │   └── verify_paths.py                # NEW consolidated (was _verify_i2_paths.py)
│   └── registry/
│       ├── data_registry.json
│       ├── iteration_state.json
│       ├── hash_report_annotations.json
│       ├── iter02_registry_mutation_request.json              # candidate for deletion, see §8
│       ├── iter_02_registry_mutation_request_corrected_latest_predictions.json  # candidate for deletion, see §8
│       ├── iter_02_registry_mutation_request_corrected_latest_predictions_yfix.json  # KEEP (latest of the chain)
│       └── start_iter02_slice_injection.py
│
├── 02_preprocessing/
│   ├── nnunet/
│   │   ├── preprocessing_nnUNet_train.py
│   │   ├── preprocessing_nnUNet_predict.py
│   │   ├── preprocessing_nnUNet_predict_tif.py
│   │   ├── preprocessing_nnUNet_predict_split.py
│   │   └── __path__.py
│   ├── filters/                           # was preprocess/
│   │   ├── gpu_nlm_torch.py
│   │   ├── normalization.py
│   │   ├── run_preprocess.py
│   │   └── colab_cli_runner.ipynb
│   │   (preprocess/nlm_output/, preprocess/norm200_output/ — empty, dropped, see §8)
│   ├── playground/                        # preprocess_playground/, kept separate (explicitly experimental)
│   │   ├── README.md
│   │   ├── filters_3d.py
│   │   ├── normalization.py
│   │   └── run_napari_filters.py
│   ├── legacy/
│   │   └── preprocess_ct_images.py        # from legacy/preprocess_ct_images.py
│   └── otsu_threshold_3d.py
│
├── 03_training/
│   ├── nnUNetTrainer_betterIgnoreSampling.py
│   ├── scripts/
│   │   ├── train_wrapper.py               # was _train_wrapper.py (shared library, not per-iteration)
│   │   ├── run_training.py                # NEW consolidated (was _run_iter03/04/04_continue.py,
│   │   │                                  #   _run_fresh_bnei_reem_i2/i3/i3_lowlr/i3_scratch/i4.py,
│   │   │                                  #   _run_mishmar_hnegev_scratch/trained.py,
│   │   │                                  #   train_fresh_bnei_reem.py, train_iter4_continue_bnei_reem.py)
│   │   └── launch_parallel_runs.ps1       # NEW consolidated (was _launch_parallel_training.ps1)
│   └── run_configs/                       # per-run JSON/YAML configs consumed by run_training.py
│       ├── iter03.yaml
│       ├── iter04.yaml
│       ├── iter04_continue.yaml
│       ├── fresh_bnei_reem_i2.yaml
│       ├── fresh_bnei_reem_i3.yaml
│       ├── fresh_bnei_reem_i3_lowlr.yaml
│       ├── fresh_bnei_reem_i3_scratch.yaml
│       ├── fresh_bnei_reem_i4.yaml
│       ├── mishmar_hnegev_scratch.yaml
│       ├── mishmar_hnegev_trained.yaml
│       ├── train_fresh_bnei_reem.yaml
│       └── train_iter4_continue_bnei_reem.yaml
│
├── 04_inference/
│   ├── postprocessing_nnUNet_predict.py
│   ├── postprocessing_nnUNet_predict_concatenate.py
│   ├── postprocessing_pipeline.ipynb
│   ├── run_remaining_fullctx_overnight.ipynb
│   ├── scripts/
│   │   ├── run_inference.py               # NEW consolidated (was _run_inference_iter03/04/04_continue.py,
│   │   │                                  #   _run_inference_fresh_bnei_reem*.py (6), _run_inference_mishmar_iter02.py,
│   │   │                                  #   _run_inference_nlm_iter02.py)
│   │   └── run_inference_then_review.py   # NEW consolidated orchestrator (was _run_fresh_then_compare_napari.py)
│   └── run_configs/                       # mirrors 03_training/run_configs/ naming per iteration
│       └── *.yaml
│
├── 05_evaluation/
│   ├── labels_debug/
│   │   ├── debug_labels_777.py
│   │   ├── debug_labels_777_followup.py
│   │   ├── retrieve_dice_score.py
│   │   └── check_data.py                  # from training_diag/check_data.py
│   ├── scripts/
│   │   ├── compare_predictions.py         # NEW consolidated (was _compare_predictions.py)
│   │   └── inspect_labels.py              # NEW consolidated (was _inspect_labels.py)
│   ├── psd/
│   │   ├── psd_diagnostics_core.py
│   │   ├── psd_topology_metrics.py
│   │   ├── run_psd_diagnostics.py
│   │   ├── recover_missing_plots.py
│   │   ├── check_labels.py
│   │   ├── colab_psd_diagnostics.ipynb
│   │   ├── implementation_contract.md
│   │   ├── _inspect_nb.py, _inspect_nb2.py, _inspect_step8.py
│   │   ├── _patch_nb.py, _patch_nb_step8.py
│   │   └── pore_metrics_research/          # decisions.md, stage1/2 prompts, papers/, validation_run/
│   ├── legacy_pores_analysis/              # ARCHIVE candidate, not folded in — see §6
│   │   └── (unchanged contents of legacy/pores_analysis/, pending maintainer sign-off to delete/archive)
│   ├── seg_plausibility/                  # kept intact, self-contained module
│   └── microsam_3d/                       # kept intact, self-contained module
│
├── 06_reporting/
│   ├── scripts/
│   │   ├── extract_trainlog.py
│   │   ├── plot_training_metrics.py       # NEW consolidated (was _plot_i3_metrics.py, _plot_lowlr_metrics.py)
│   │   ├── make_synopsis.py               # NEW consolidated (was _make_synopsis_i3.py, _make_synopsis_i4.py)
│   │   ├── make_psd_plot.py
│   │   ├── launch_napari_review.py        # NEW consolidated (was all 12 root _launch_napari_*.py)
│   │   └── inspect_predictions.py
│   ├── synopsis_outputs/                  # analysis/synopsis_i3/, analysis/synopsis_i4/ (flagged for pruning, §5)
│   └── selected_outputs/                  # analysis/selected_outputs/ (large-file flags apply, §5)
│
├── 07_utilities/
│   ├── Utilities/                         # mkdir_movefiles.sh, nifti_io.jar, submit_nnUNet_*
│   ├── Fiji_macros/                       # unchanged
│   ├── config/pores_analysis/config.yaml
│   ├── scripts/
│   │   └── find_dataset_json.py           # NEW consolidated (was _find_dataset_json.py)
│   └── dataset_info.json  (symlink/reference; canonical copy stays at repo root)
│
├── colab_nnUNet_pipeline.ipynb            # kept at root: master reference notebook, spans stages 02-04
│
└── logs_archive/                          # NEW — see §4
    ├── log_index.csv
    ├── training/
    ├── inference/
    └── napari/
```

Notes on this tree:
- `microsam_3d/` and `seg_plausibility/` are folded under `05_evaluation/` per decision #1 (their napari-facing launcher scripts are separately consolidated into `06_reporting/scripts/launch_napari_review.py`, which will subprocess/import into these modules rather than duplicate their logic).
- `legacy/pores_analysis/` is **not** folded into any numbered stage — it is kept as an explicitly separate `05_evaluation/legacy_pores_analysis/` archive folder pending the maintainer's decision to delete outright (see §6 for the re-verification that justifies this).
- `dataset_info.json` remains canonical at repo root (many scripts hardcode `REPO_DIR`-relative access to it); the `07_utilities/` entry is a documentation note, not a literal duplicate — **open question**, see §9.

---

## 2. Ordered operation checklist

Executed in this order so nothing breaks mid-move (cross-referencing `REPO_SCAN.md` §8 dependency notes).

1. **Create new directory skeleton** (`00_docs/` … `07_utilities/`, `logs_archive/{training,inference,napari}/`) — empty dirs, no moves yet.
2. **Rename `litreture/` → `00_docs/literature/`** (git mv). No importers reference this path — safe, isolated first step.
3. **Move root-level `.md`/asset docs** into `00_docs/`: `Figures/` → `00_docs/Figures/`. Update `README.md` image references in the same step (README embeds `Figures/*.png` paths).
4. **Move `__path__.py`, `preprocessing_nnUNet_*.py`, `otsu_threshold_3d.py`, `dataset_info.json` (copy, not move — see open question in §9) into `02_preprocessing/nnunet/`.** In the same step, update the two importers: `preprocessing_nnUNet_predict.py` and `preprocessing_nnUNet_predict_tif.py` (`from preprocessing_nnUNet_train import ...`) and `postprocessing_nnUNet_predict.py` (`from __path__ import ...`) — all three move together so relative imports keep working; update any `sys.path.insert(REPO_DIR)` calls in scripts outside this folder that expect `__path__.py` at repo root.
5. **Move `preprocess/` → `02_preprocessing/filters/`, `preprocess_playground/` → `02_preprocessing/playground/`, `legacy/preprocess_ct_images.py` → `02_preprocessing/legacy/preprocess_ct_images.py`.** Drop empty `preprocess/nlm_output/`, `preprocess/norm200_output/` (confirm empty at move time, not carried over).
6. **Move `nnUNetTrainer_betterIgnoreSampling.py` → `03_training/`.** This file is distributed by `shutil.copy2` (not import) from every training/inference driver — in the SAME step, update the hardcoded `src = os.path.join(REPO_DIR, 'nnUNetTrainer_betterIgnoreSampling.py')` line inside the new consolidated `run_training.py` and `run_inference.py` (built in step 9/10) to point at `03_training/nnUNetTrainer_betterIgnoreSampling.py`.
7. **Move `_train_wrapper.py` → `03_training/scripts/train_wrapper.py`.** Update the one hardcoded reference in `_verify_i2_paths.py`'s successor (`verify_paths.py`, built in step 12) and any consolidated training script's subprocess call path.
8. **Move `_launch_parallel_training.ps1`** logic into new `03_training/scripts/launch_parallel_runs.ps1` (rewritten, generalized — see §3). Retire the old file.
9. **Build `03_training/scripts/run_training.py`** (new consolidated script, see §3) and the 12 `run_configs/*.yaml` files. Do NOT delete the 12 originals yet — keep them side by side for one verification cycle (run each new config once, diff key outputs against the last known-good run of the original script) before deletion. Record verification status in a `run_configs/VERIFIED.md` checklist.
10. **Build `04_inference/scripts/run_inference.py`** and its `run_configs/*.yaml` (see §3), same side-by-side verification approach as step 9.
11. **Build `04_inference/scripts/run_inference_then_review.py`** replacing `_run_fresh_then_compare_napari.py`; wire it to call the new `run_inference.py` + `06_reporting/scripts/launch_napari_review.py` (built in step 14) rather than the old per-iteration scripts.
12. **Build `01_data_ingestion/scripts/verify_paths.py`** (generalized manifest-driven existence checker, replacing `_verify_i2_paths.py`). Move `select_slices_and_predict.py`, `make_annotations.py`, `merge_annotations.py`, `chunk_extractor.py` into `01_data_ingestion/` unchanged (no internal repo imports found).
13. **Move `analysis/data_registry.json`, `iteration_state.json`, `hash_report_annotations.json`, `iter02_registry_mutation_request*.json`, `start_iter02_slice_injection.py` → `01_data_ingestion/registry/`.** Update `.github/agents/data-registry-path-validation.agent.md` and `.github/skills/report-agent-run-status.skill.md` path references in the SAME step (both hardcode `analysis/data_registry.json` / `analysis/iteration_state.json`).
14. **Build `06_reporting/scripts/launch_napari_review.py`** (consolidates all 12 `_launch_napari_*.py`, see §3). Internally it does `sys.path.insert(0, MICROSAM_DIR)` / imports `seg_plausibility/napari_review.py` — update these paths to the new `05_evaluation/microsam_3d/` and `05_evaluation/seg_plausibility/` locations in this same step (steps 16-17 move those folders — do this step and 16/17 together, in one atomic batch).
15. **Build `06_reporting/scripts/make_synopsis.py`** and `plot_training_metrics.py` (consolidating `_make_synopsis_i3/i4.py`, `_plot_i3_metrics.py`, `_plot_lowlr_metrics.py`, see §3). Move `extract_trainlog.py`, `make_psd_plot.py`, `inspect_predictions.py` into `06_reporting/scripts/` unchanged.
16. **Move `microsam_3d/` → `05_evaluation/microsam_3d/` intact** (internal flat imports like `predictor.py`'s `from embedder import VolumeEmbedder` are unaffected by moving the whole folder as a unit). Update every caller identified in step 14.
17. **Move `seg_plausibility/` → `05_evaluation/seg_plausibility/` intact**, same rationale. Update callers from step 14.
18. **Move `debug_labels_777.py`, `debug_labels_777_followup.py`, `retrieve_dice_score.py`, `training_diag/check_data.py` → `05_evaluation/labels_debug/`.** Build `05_evaluation/scripts/compare_predictions.py` and `inspect_labels.py` consolidating `_compare_predictions.py`/`_inspect_labels.py`.
19. **Move `analysis/psd_diagnostics_core.py`, `psd_topology_metrics.py`, `run_psd_diagnostics.py`, `recover_missing_plots.py`, `check_labels.py`, `colab_psd_diagnostics.ipynb`, `implementation_contract.md`, `_inspect_nb*.py`, `_patch_nb*.py`, `pore_metrics_research/` → `05_evaluation/psd/`.** In the SAME step: update `run_psd_diagnostics.py`'s flat same-folder imports of `psd_diagnostics_core`/`psd_topology_metrics` are unaffected since both move together; update `.github/agents/psd-analysis-runner.agent.md` and `setup_prompt.md` path references to `analysis/...` → `05_evaluation/psd/...`. Update `_inspect_nb*.py`/`_patch_nb*.py` hardcoded relative path to `colab_psd_diagnostics.ipynb` (still same-folder, so no change needed if moved as a batch).
20. **Do NOT move `legacy/pores_analysis/` into the numbered tree.** Per §6, park it at `05_evaluation/legacy_pores_analysis/` as an explicit archive-pending-deletion folder (rename only, no internal edits) OR delete outright if the maintainer confirms at sign-off — this step is gated on the maintainer's answer to Q1 in §9.
21. **Move `analysis/selected_outputs/` → `06_reporting/selected_outputs/` and `analysis/synopsis_i3/`, `synopsis_i4/` → `06_reporting/synopsis_outputs/`.** Apply large-file handling from §5 in this same step (gitignore entries added before anything here is ever committed).
22. **Move `Utilities/`, `Fiji_macros/`, `config/pores_analysis/` → `07_utilities/`.** Update `legacy_pores_analysis/config_loader.py`'s `Path(__file__).resolve().parents[2]` resolution — since `legacy_pores_analysis/` itself doesn't move to a new depth in this plan (see step 20), and `config/` moves under `07_utilities/config/`, this path resolution WILL break; flag as an open item (see §9) rather than silently patch it, since decision #5 leaves `legacy/pores_analysis`'s ultimate fate (archive vs. delete) to the maintainer.
23. **Build `07_utilities/scripts/find_dataset_json.py`** from `_find_dataset_json.py` (generalize `search_roots` to a CLI arg).
24. **Summarize and archive all logs** into `logs_archive/` per §4. This is the last content-moving step since it has no import dependencies to break.
25. **Delete now-empty directories** (`preprocess/nlm_output/`, `preprocess/norm200_output/`, `legacy/pores_analysis/results/` — the last one only if step 20 resolves to deletion) and the empty 0-byte files listed in §8.
26. **Write `ARCHITECTURE.md` and `RESOURCES.md`**, and update `README.md`, `.github/copilot-instructions.md`, `.github/agents/*.agent.md` for every path touched above (per §7 outlines).
27. **Final verification pass**: re-run `verify_paths.py`/a repo-wide "does every referenced path exist" script (analogous to `REPO_SCAN.md`'s method) before considering the reorg complete.

---

## 3. Consolidated-script design

### 3.1 Design summary

Eight new consolidated entry points replace the ~44 per-iteration root scripts (this excludes the pure log/output files, handled in §4):

| # | New script | Location | Replaces (families) |
|---|---|---|---|
| S1 | `run_training.py` | `03_training/scripts/` | all `_run_iter*`, `_run_fresh_bnei_reem_*`, `_run_mishmar_hnegev_*`, `train_*_bnei_reem.py` |
| S2 | `train_wrapper.py` | `03_training/scripts/` | `_train_wrapper.py` (shared library, imported/subprocessed by S1, not per-iteration) |
| S3 | `launch_parallel_runs.ps1` | `03_training/scripts/` | `_launch_parallel_training.ps1` |
| S4 | `run_inference.py` | `04_inference/scripts/` | all `_run_inference_*.py` |
| S5 | `run_inference_then_review.py` | `04_inference/scripts/` | `_run_fresh_then_compare_napari.py` |
| S6 | `launch_napari_review.py` | `06_reporting/scripts/` | all 12 root `_launch_napari_*.py` |
| S7 | `make_synopsis.py` | `06_reporting/scripts/` | `_make_synopsis_i3.py`, `_make_synopsis_i4.py` |
| S8 | `plot_training_metrics.py` | `06_reporting/scripts/` | `_plot_i3_metrics.py`, `_plot_lowlr_metrics.py` |
| S9 | `compare_predictions.py` | `05_evaluation/scripts/` | `_compare_predictions.py` |
| S10 | `inspect_labels.py` | `05_evaluation/scripts/` | `_inspect_labels.py` |
| S11 | `verify_paths.py` | `01_data_ingestion/scripts/` | `_verify_i2_paths.py` |
| S12 | `find_dataset_json.py` | `07_utilities/scripts/` | `_find_dataset_json.py` |

Rationale for folder placement: each consolidated script lives in the `scripts/` subfolder of the pipeline stage it operates on, per the prompt's suggestion — training and inference each get their own because the parameter sets genuinely differ (training needs a base-checkpoint + annotation-file + hyperparameters; inference only needs a checkpoint + input volume). `launch_napari_review.py`, `make_synopsis.py`, and `plot_training_metrics.py` are all "look at existing outputs" tools, hence grouped under `06_reporting/`. `run_inference_then_review.py` spans two stages (inference + reporting) — it is placed under `04_inference/scripts/` since inference is the more expensive/stateful half, and it calls out to `06_reporting/scripts/launch_napari_review.py` rather than duplicating viewer logic.

### 3.2 Parameter sets

**S1 `run_training.py`** — CLI args (or single YAML config, `--config path.yaml`):
- `--iteration-name` (str, e.g. `fresh_bnei_reem_i3`) — used to derive `LOCAL_BASE` = `multi_sample_{iteration_name}` under the HIVE resources root.
- `--sample-id` (str, e.g. `nlm_volume` or `mishmar_hanegev_Cu011_samp_2_Rec_nlm`).
- `--raw-tiff-path` (str; can also be resolved from `data_registry.json` by `sample-id` when omitted, as the original i3 script did).
- `--annotation-path` (str, absolute).
- `--trainer-name` (str, default `nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss`; `_lowlr` variant selectable).
- `--base-checkpoint` (str path, or literal `scratch` for from-scratch training).
- `--gpu` (int, sets `CUDA_VISIBLE_DEVICES`).
- `--dataset-id` (default `777`).
- `--force-rebuild` (bool flag, default true, matches observed `FORCE_REBUILD = True` in every script).
- `--offset-layers` (int, default 48 — the z-crop padding constant).
- `--early-stop-patience` / `--early-stop-min-delta` (defaults `20` / `0.001`).
- `--run-inference-after` (bool flag) — if set, subprocess-calls S4 with the resulting checkpoint (replicates the train→infer chaining seen in `_run_fresh_bnei_reem_i3.py`, `_run_iter03.py`, `_run_iter04.py`).

**S4 `run_inference.py`**:
- `--iteration-name`, `--sample-id`, `--trainer-name`, `--gpu`, `--dataset-id` (same semantics as S1).
- `--model-dir` (override; else derived from `iteration-name`).
- `--input-dir` (pre-split chunks dir; supports the observed "reuse another iteration's split" pattern via `--reuse-split-from <iteration-name>`).
- `--output-dir` / `--concat-dir` (defaults derived from `iteration-name`).
- `--checkpoint-name` (default: try `checkpoint_final.pth` then fall back to `checkpoint_best.pth`, matching every script's existing fallback logic).

**S6 `launch_napari_review.py`**:
- `--mode {compare_gt, comparison, fullvol, microsam_multi, seg_plausibility}` — collapses the 12 variants into one dispatcher.
- `--volume-path`, `--gt-path`, `--pred-paths` (repeatable `name=path` pairs, replacing the various `pred`/`pred_new`/`pred_iter02`/`pred_continue`/`pred_fresh` ad hoc names via `extra_label_paths`).
- `--zrange START END` (optional; some scripts pass `--zrange 50 70`, others run full-volume).
- `--debug` (flag, always true in current scripts — kept as default-true, overridable).
- `--seg-plausibility-results-dir` (only used when `--mode seg_plausibility`).

**S7 `make_synopsis.py`**: `--iteration-name`, `--volume-path`, `--annotation-path`, `--prediction-path`, `--output-dir` (default `06_reporting/synopsis_outputs/{iteration_name}/`).

**S8 `plot_training_metrics.py`**: `--iteration-name`, `--trainer-name`, `--results-dir` (else derived), `--in-progress` (flag — i3_lowlr's version explicitly supports parsing while training is still running).

**S9 `compare_predictions.py`**: `--gt-path`, `--model paths` (repeatable `label=path`, replacing the hardcoded OLD/NEW/LOW_LR triple), `--gt-slices` (list of ints, or `--all-slices`), `--eval-pairs` (repeatable `gt_label:pred_label:name`, default the observed `2:1:Stones,3:2:POM,6:5:Pore`).

**S10 `inspect_labels.py`**: `--paths name=path` (repeatable, replacing hardcoded GT/NEW/OLD), `--axis-summary` (flag to print non-zero slice indices per axis, as the original did for GT only).

**S11 `verify_paths.py`**: `--manifest path.yaml` — a list of `{name, path}` checks (replacing the hardcoded 6-entry dict), returns nonzero exit if any missing (same behavior as original).

**S12 `find_dataset_json.py`**: `--search-roots path [path ...]` (replacing the hardcoded 2-entry list).

**S2 `train_wrapper.py`**: unchanged logic, just relocated; it's invoked as a subprocess target by S1 (`[sys.executable, train_wrapper_path, dataset_id, config, fold, '-tr', trainer, '-pretrained_weights', checkpoint]`), not a CLI tool in its own right.

**S3 `launch_parallel_runs.ps1`**: generalized to accept an array of `{ScriptArgs, Label}` pairs (or a JSON list) rather than the two hardcoded jobs, so it can launch any N configured `run_training.py` invocations across GPUs, each with its own log/err redirect into `logs_archive/training/`.

**S5 `run_inference_then_review.py`**: `--iteration-name-a`, `--iteration-name-b` (the two models being compared), `--gt-path`, `--zrange` — orchestrates: run S4 for iteration-name-a if not already done → build comparison chart (reuses S8's CSV-plotting logic) → subprocess-call S6 in `comparison` mode.

### 3.3 Full per-file mapping table

Parameter values below were confirmed by direct source inspection for one representative file per family (`_run_fresh_bnei_reem_i3.py`, `_run_inference_fresh_bnei_reem_i3.py`, `_launch_napari_fresh_i3_fullvol.py`, `_train_wrapper.py`, `_launch_parallel_training.ps1`, `_verify_i2_paths.py`, `_find_dataset_json.py`, `_compare_predictions.py`, `_inspect_labels.py`, `_make_synopsis_i3/i4.py`, `_plot_i3/lowlr_metrics.py`, `_run_iter03/04/04_continue.py`, `_run_inference_iter04_continue.py`, `_run_inference_mishmar_iter02/nlm_iter02.py`, both `_launch_napari_*microSAM.py`) — the family is extremely regular (same variable names, same structure) so the remaining files' parameters are pattern-matched from filename + the one-line `grep` evidence collected for `TRAINER_NAME`/`SAMPLE_ID`/`CUDA_VISIBLE_DEVICES`/`PRETRAINED_CHECKPOINT` shown below. Ambiguous cases are flagged explicitly rather than guessed.

| # | Existing file | Consolidated script | Key parameter values |
|---|---|---|---|
| 1 | `_run_iter03.py` | S1 (+ inline S4 call at end) | iteration=`iter03`, sample=`nlm_volume`, trainer=`...earlyStopValLoss`, annotation=`E:\...\annotations_iter03\new_annotations.nii.gz`, base_checkpoint=iter02, dataset=777. **Combined train+infer** — chains to `_run_inference_iter03.py`. |
| 2 | `_run_iter04.py` | S1 (+ inline S4 call) | iteration=`iter04`, sample=`nlm_volume`, trainer=`...earlyStopValLoss`, annotation=same iter03 annotation path (reused), base_checkpoint=iter02, dataset=777. Combined train+infer. |
| 3 | `_run_iter04_continue.py` | **Flagged — ambiguous.** Content inspected is orchestration-only (subprocess to `_run_inference_iter04_continue.py`); no visible training/dataset-prep code in the read portion. Needs full-file read before consolidation to confirm whether it's S1+S4 combined or purely an S5-style orchestrator. |
| 4 | `_run_fresh_bnei_reem_i2.py` | S1 (+ inline S4 call) | iteration=`fresh_bnei_reem_i2`, sample=`nlm_volume`, gpu=0, trainer=`...earlyStopValLoss`, annotation=`annotations_i2.nii.gz`, base_checkpoint=`fresh_bnei_reem` (baseline), dataset=777. |
| 5 | `_run_fresh_bnei_reem_i3.py` | S1 (+ inline S4 call) | iteration=`fresh_bnei_reem_i3`, sample=`nlm_volume`, gpu=0, trainer=`...earlyStopValLoss`, annotation=`annotations_i3.nii.gz`, base_checkpoint=`fresh_bnei_reem_i2`, dataset=777. |
| 6 | `_run_fresh_bnei_reem_i3_lowlr.py` | S1 (+ inline S4 call) | iteration=`fresh_bnei_reem_i3_lowlr`, sample=`nlm_volume`, gpu=0, trainer=`..._lowlr`, annotation=`annotations_i3.nii.gz`, base_checkpoint=`fresh_bnei_reem_i2`, dataset=777. |
| 7 | `_run_fresh_bnei_reem_i3_scratch.py` | S1 | iteration=`fresh_bnei_reem_i3_scratch`, sample=`nlm_volume`, gpu=0, trainer=`...earlyStopValLoss`, annotation=`annotations_i3.nii.gz`, base_checkpoint=`scratch` (comment: "Train from scratch"), dataset=777. |
| 8 | `_run_fresh_bnei_reem_i4.py` | S1 | iteration=`fresh_bnei_reem_i4`, sample=`nlm_volume`, gpu=1, trainer=`..._lowlr`, annotation=`fine_tuning_annotations.nii.gz`, base_checkpoint=`fresh_bnei_reem_i3_lowlr`, dataset=777. |
| 9 | `_run_mishmar_hnegev_scratch.py` | S1 | iteration=`mishmar_hnegev_scratch`, sample=`mishmar_hanegev_Cu011_samp_2_Rec_nlm`, gpu=1, trainer=`...earlyStopValLoss`, annotation=`mishmar_hanegev_new_work/annotations/{sample}.nii.gz`, base_checkpoint=`scratch`, dataset=777. |
| 10 | `_run_mishmar_hnegev_trained.py` | S1 | iteration=`mishmar_hnegev_trained`, sample=`mishmar_hanegev_Cu011_samp_2_Rec_nlm`, gpu=0, trainer=`..._lowlr`, annotation=same mishmar annotation, base_checkpoint=scratch-run checkpoint (fine-tune off `mishmar_hnegev_scratch`), dataset=777. |
| 11 | `train_fresh_bnei_reem.py` | S1 | iteration=`fresh_bnei_reem` (baseline/original run — see `_launch_parallel_training.ps1` comment: "from scratch", GPU 1). |
| 12 | `train_iter4_continue_bnei_reem.py` | S1 | iteration=`iter04_continue` (per `_launch_parallel_training.ps1` comment: "fine-tune from iter04", GPU 0). |
| 13 | `_train_wrapper.py` | S2 | shared library module — no per-iteration params; invoked with `(dataset_id, config, fold, -tr trainer, -pretrained_weights path)`. |
| 14 | `_launch_parallel_training.ps1` | S3 | job1=`train_iter4_continue_bnei_reem` (GPU 0), job2=`train_fresh_bnei_reem` (GPU 1) — generalize to N jobs. |
| 15 | `_run_inference_iter03.py` | S4 | iteration=`iter03`, sample=`nlm_volume`, trainer=`...earlyStopValLoss`. |
| 16 | `_run_inference_iter04.py` | S4 | iteration=`iter04`, sample=`nlm_volume`, trainer=`...earlyStopValLoss`. |
| 17 | `_run_inference_iter04_continue.py` | S4 | iteration=`iter04_continue`, sample=`nlm_volume`, trainer=`...earlyStopValLoss`, model_dir=`multi_sample_iter04_continue`, reuses split from `bnei_reem_iter04`. |
| 18 | `_run_inference_fresh_bnei_reem.py` | S4 | iteration=`fresh_bnei_reem`, sample=`nlm_volume`, trainer=`...earlyStopValLoss`. |
| 19 | `_run_inference_fresh_bnei_reem_i2.py` | S4 | iteration=`fresh_bnei_reem_i2`, sample=`nlm_volume`, trainer=`...earlyStopValLoss`. |
| 20 | `_run_inference_fresh_bnei_reem_i3.py` | S4 | iteration=`fresh_bnei_reem_i3`, sample=`nlm_volume`, trainer=`...earlyStopValLoss`, reuses split from `bnei_reem_iter04/inference_input`. |
| 21 | `_run_inference_fresh_bnei_reem_i3_lowlr.py` | S4 | iteration=`fresh_bnei_reem_i3_lowlr`, sample=`nlm_volume`, trainer=`..._lowlr`. |
| 22 | `_run_inference_fresh_bnei_reem_i3_scratch.py` | S4 | iteration=`fresh_bnei_reem_i3_scratch`, sample=`nlm_volume`, trainer=`...earlyStopValLoss`. |
| 23 | `_run_inference_fresh_bnei_reem_i4.py` | S4 | iteration=`fresh_bnei_reem_i4`, sample=`nlm_volume`, trainer=`..._lowlr`. |
| 24 | `_run_inference_mishmar_iter02.py` (tracked) | S4 | iteration=`iter02` model applied to sample=`mishmar_hanegev_Cu011_samp_2_Rec_nlm`, trainer=`...earlyStopValLoss`, model_dir=`multi_sample_iter02`. |
| 25 | `_run_inference_nlm_iter02.py` (tracked) | S4 | iteration=`iter02` model applied to sample=`nlm_volume` (aka `bnei_reem`), trainer=`...earlyStopValLoss`, output=`inference_output_iter02`. |
| 26 | `_run_fresh_then_compare_napari.py` | S5 | compares iteration-a=`iter04_continue` vs iteration-b=`fresh_bnei_reem`; runs S4 for fresh_bnei_reem then chart then S6 `comparison` mode. gpu=0. |
| 27 | `_launch_napari_compare_gt.py` | S6 `--mode compare_gt` | vol=`nlm_volume.tif`, gt=`annotations_i3.nii.gz` (no full pred set inspected — likely a GT-only viewer). |
| 28 | `_launch_napari_comparison.py` | S6 `--mode comparison` | gt=`merged_GT.nii.gz`; used as the final step of `_run_fresh_then_compare_napari.py`. |
| 29 | `_launch_napari_fresh_i2.py` | S6 `--mode fullvol` (zrange 50-70) | vol=`nlm_volume.tif`, pred=`bnei_reem_fresh_bnei_reem_i2`, gt=`annotations_i2.nii.gz`. |
| 30 | `_launch_napari_fresh_i2_fullvol.py` | S6 `--mode fullvol` (no zrange) | same paths as #29, full volume. |
| 31 | `_launch_napari_fresh_i3_fullvol.py` | S6 `--mode fullvol` | vol=`nlm_volume.tif`, pred=`bnei_reem_fresh_bnei_reem_i3`, gt=`annotations_i3.nii.gz`. |
| 32 | `_launch_napari_i3_lowlr_fullvol.py` | S6 `--mode fullvol` | pred=`bnei_reem_fresh_bnei_reem_i3_lowlr`, gt=`annotations_i3.nii.gz`. |
| 33 | `_launch_napari_iter04.py` | S6 (uses `inspect_predictions.py`, not `microsam_3d/run.py` — **flagged, different underlying tool**) | pred=`bnei_reem_iter04/inference_concatenated/nlm_volume.nii.gz`. Needs a `--viewer {microsam,inspect_predictions}` sub-flag or separate handling since it doesn't go through `microsam_3d/run.py`. |
| 34 | `_launch_napari_mishmar_microSAM.py` | S6 `--mode microsam_multi` | vol=`mishmar_hanegev...tif`, gt=mishmar annotation, preds={pred_new, pred_iter02} (2 extra labels). |
| 35 | `_launch_napari_nlm_iter04_continue.py` | S6 `--mode fullvol` (zrange 50-70) | vol=`nlm_volume.tif`, pred=`bnei_reem_iter04_continue`, gt=`merged_GT.nii.gz`. |
| 36 | `_launch_napari_nlm_microSAM.py` | S6 `--mode microsam_multi` | vol=`nlm_volume.tif`, gt=`merged_GT.nii.gz`, preds={pred_continue, pred_fresh}. |
| 37 | `_launch_napari_seg_plausibility_i3_scratch.py` | S6 `--mode seg_plausibility` | results_dir=`analysis/selected_outputs/bnei_reem/seg_plausibility_i3_scratch`. |
| 38 | `_launch_napari_seg_plausibility_i4.py` | S6 `--mode seg_plausibility` | results_dir=`analysis/selected_outputs/bnei_reem/seg_plausibility_i4`. |
| 39 | `_compare_predictions.py` | S9 | gt=`annotations_i2.nii.gz`, models={OLD=fresh_bnei_reem, NEW=fresh_bnei_reem_i2, LOW_LR=fresh_bnei_reem_i3_lowlr}, gt_slices=31 hardcoded indices, eval_pairs=`(2,1,Stones),(3,2,POM),(6,5,Pore)`. |
| 40 | `_inspect_labels.py` | S10 | paths={GT=annotations_i2, NEW=fresh_bnei_reem_i2 pred, OLD=fresh_bnei_reem pred}, axis-summary=true (GT only). |
| 41 | `_find_dataset_json.py` | S12 | search_roots=[`multi_sample_fresh_bnei_reem`, `multi_sample_iter02`]. |
| 42 | `_verify_i2_paths.py` | S11 | manifest of 6 checks (annotation i2, raw tif, fresh checkpoint, inference input dir, train wrapper, inference script i2). |
| 43 | `_make_synopsis_i3.py` | S7 | iteration=`fresh_bnei_reem_i3`, vol=`nlm_volume.tif`, pred=`bnei_reem_fresh_bnei_reem_i3`, ann=`annotations_i3.nii.gz`, output=`analysis/synopsis_i3`. |
| 44 | `_make_synopsis_i4.py` | S7 | iteration=`fresh_bnei_reem_i3_scratch` (despite the "i4" filename — **flagged naming mismatch**: pred path points at `bnei_reem_fresh_bnei_reem_i3_scratch`, output dir is `analysis/synopsis_i4`), ann=`annotations_i3.nii.gz`. |
| 45 | `_plot_i3_metrics.py` | S8 | iteration=`fresh_bnei_reem_i3`, trainer=`...earlyStopValLoss`. |
| 46 | `_plot_lowlr_metrics.py` | S8 (`--in-progress`) | iteration=`fresh_bnei_reem_i3_lowlr`, trainer=`..._lowlr`. |

**Files not requiring consolidation (flagged as-is / kept, per prompt instruction to flag anything that doesn't cleanly fit):**
- `_train_wrapper.py` → becomes S2, a shared library, not a per-iteration fork — correctly excluded from the "one script per iteration" anti-pattern already.
- `_launch_napari_iter04.py` (#33) — genuinely different underlying viewer (`inspect_predictions.py` vs. `microsam_3d/run.py`); don't force it into the same dispatcher without adding a `--viewer` sub-selector.
- `_run_iter04_continue.py` (#3) — needs a full read before deciding its consolidation target; flagged rather than guessed.
- `_make_synopsis_i4.py` (#44) — internal naming inconsistency (script says "i4" in filename/output dir but processes `i3_scratch` data) should be resolved/renamed at execution time, not silently preserved.

---

## 4. Log summarization + archive design

### 4.1 Summary index format

A single `logs_archive/log_index.csv` with columns:

```
run_type, iteration_name, log_file, err_log_file, date, gpu, final_epoch, final_train_loss, final_val_loss, final_mean_dice, duration_min, status, notes
```

- `run_type` ∈ {`training`, `inference`, `napari`}.
- `status` ∈ {`success`, `failed`, `incomplete`, `empty`} (the four 0-byte files become `status=empty`).
- Fields are extracted with the same regex patterns already used by `extract_trainlog.py`/`_plot_i3_metrics.py` (`Epoch\s+(\d+)`, `train_loss\s+(-?[\d.eE]+)`, `val_loss\s+(-?[\d.eE]+)`, the Dice regex) — no new parsing logic needed, just applied uniformly to every log at archive time.
- One row per log **pair** (`.log` + `_err.log`), not per file.

### 4.2 Archive folder layout

```
logs_archive/
├── log_index.csv
├── training/
│   ├── fresh_bnei_reem_i2/    _fresh_bnei_reem_i2.log, _err.log
│   ├── fresh_bnei_reem_i3/    _fresh_bnei_reem_i3.log, _err.log
│   ├── fresh_bnei_reem_i3_lowlr/
│   ├── fresh_bnei_reem_i3_scratch/
│   ├── fresh_bnei_reem_i4/
│   ├── mishmar_hnegev_scratch/
│   ├── mishmar_hnegev_trained/
│   ├── train_fresh_bnei_reem/       (from repo-root train_fresh_bnei_reem.log)
│   └── train_iter4_continue_bnei_reem/
├── inference/
│   ├── fresh_inference_napari/
│   ├── i4_inference/
│   ├── iter03_inference/, iter03_run4/, iter03_run5/
│   ├── iter04_continue_inference/
│   ├── iter04_run1/, iter04_run2/
│   ├── scratch_inference/
│   ├── seg_plausibility_i3_scratch_run/   (0 bytes — status=empty)
│   ├── seg_plausibility_i4_run/, seg_plausibility_i4_run_gpu/
│   ├── make_ann_log/  (_make_ann_log.txt, _make_ann_err.txt)
│   └── make_synopsis_i3/, make_synopsis_i4/   (i3_err/i4_err are 0 bytes — status=empty)
└── napari/
    ├── mishmar_microSAM/
    ├── nlm_iter04_continue/
    ├── nlm_iter04/
    ├── nlm_microSAM/
    ├── seg_plausibility_i3_scratch/
    └── seg_plausibility_i4/    (log.txt, log2.txt, log3.txt — log3 is 0 bytes → status=empty, note as separate row)
```

Sorting scheme: **top-level by run_type, then one subfolder per iteration_name** (not by date) — this matches how the maintainer already thinks about the data (per-iteration, not chronologically), and keeps each iteration's train/err pair together for at-a-glance debugging. Date is preserved as a CSV column instead of a folder axis so both "what happened on iteration X" and "what happened on date Y" queries are possible (via CSV filter) without duplicating files into two folder trees.

The 7 tracked (committed) log/txt files (`mishmar_psd.log`, `_inference_err/log.txt`, `_inference_nlm_err/log.txt`, `_napari_nlm_err/log.txt`) get the same archival treatment but are additionally flagged in §8 (git-history question).

---

## 5. Large-file recommendations

| File/folder | Size | Recommendation | Rationale |
|---|---|---|---|
| `analysis/selected_outputs/bnei_reem/seg_plausibility_i4/instance_map.tif` | ~1.05GB | **Move outside repo folder** (e.g. keep only on the HIVE network share, reference by path in a manifest/README) | Git (even with LFS) is a poor fit for a single-GB binary that's a regenerable pipeline output, not source; LFS quota costs would be substantial for zero benefit over just documenting the HIVE path. |
| `analysis/selected_outputs/bnei_reem/seg_plausibility_i4/errors.json` | ~66MB | **Gitignore in place** (keep on disk, exclude from git) | Regenerable diagnostic output; too large for normal git, not valuable enough for LFS. |
| `analysis/selected_outputs/bnei_reem/seg_plausibility_i4/track_table.csv` | ~7.5MB | **Gitignore in place** | Same — regenerable per-run output; a CSV this size is a build artifact, not a tracked source file. |
| `analysis/pore_metrics_research/papers/*.pdf` (6 files, ~15MB) | ~15MB | **Move outside repo (external reference manager) + cite by DOI/URL in `decisions.md`** | These are third-party reference PDFs, not repo-authored content; committing them risks copyright/redistribution issues and bloats clone size for no code benefit. |
| `analysis/synopsis_i3/` + `synopsis_i4/` (~35MB PNGs) | ~35MB | **Gitignore in place** | Fully regenerable via `make_synopsis.py`; keeping them untracked but on disk is sufficient, no need for LFS since they're throwaway QA renders re-generated per iteration. |
| `validation_run/sub_z200_300.nii.gz` | ~3MB | **Gitignore in place** | Binary test-fixture volume; small enough that LFS overhead isn't justified, but still shouldn't bloat normal git history since it's test data, not source. |

General rule applied: **Git LFS was not recommended for anything** in this repo — every large file identified is either (a) a fully regenerable pipeline output (gitignore) or (b) third-party/large reference material better stored outside version control entirely (move out + cite). Nothing here is source code or hand-authored content that must be versioned at that size.

---

## 6. `legacy/pores_analysis/` dependency re-verification result

**Re-verified 2026-07-08, specifically for the concern raised about the 2026-07-06/07 work.**

Method: grepped every import statement (`^import|^from`) in `analysis/psd_topology_metrics.py`, `analysis/run_psd_diagnostics.py`, `analysis/psd_diagnostics_core.py`, `legacy/pores_analysis/topology_metrics.py`, and `legacy/pores_analysis/extended_pipeline.py`, and separately grepped both `analysis/` files for the literal strings `legacy` / `pores_analysis`.

**Finding: no accidental dependency exists. The concern raised did not materialize.**

- `analysis/psd_topology_metrics.py` — imports only `numpy`, `scipy.ndimage`, `skimage.measure` (`euler_number`, `marching_cubes`, `mesh_surface_area`), stdlib. Zero references to `legacy`. Its own module docstring (line 25) explicitly states: *"no dependency on legacy/pores_analysis"* — self-declared and confirmed by the import grep.
- `analysis/run_psd_diagnostics.py` and `analysis/psd_diagnostics_core.py` — no `legacy`/`pores_analysis` imports or `sys.path` manipulation toward that folder. The word "legacy" appears only in **comments** inside `psd_diagnostics_core.py` (e.g. "Preserved from legacy psd_calculator.compute_psd_from_opening_map", "legacy behaviour") — these are documentation notes about which historical algorithm a function's numeric behavior was ported from, not runtime imports. Confirmed by reading each flagged line: none is a live `from legacy...` or `import legacy...` statement.
- `legacy/pores_analysis/extended_pipeline.py` (new, 2026-07-06) — imports `.psd_calculator`, `.psd_output`, `.topology_metrics` — all three are **internal to `legacy/pores_analysis/` itself** (relative imports within the same package, with a flat-import fallback for direct script execution). This is expected internal package structure, not a leak of legacy code into the new `analysis/` work — `extended_pipeline.py` orchestrates other legacy modules, it doesn't get called by anything in `analysis/`.
- `legacy/pores_analysis/topology_metrics.py` (new, 2026-07-06) — imports only `scipy.ndimage`, `skimage.measure`, stdlib. No cross-import with `analysis/`.
- Grep across the full repo for any file importing `legacy.pores_analysis` or `pores_analysis` as a package: only files physically inside `legacy/pores_analysis/` itself do so (their own `__init__.py` relative-import chain, documented in `REPO_SCAN.md` §8).

**Confirmation of the specific near-duplicate question:** `analysis/psd_topology_metrics.py` (502 lines, written 2026-07-07 11:44) and `legacy/pores_analysis/topology_metrics.py` (479 lines, written 2026-07-06 23:11) are **independent, non-importing near-duplicates**, as `REPO_SCAN.md` originally found. This re-verification, done specifically because the earlier scan predates the concern, reaches the same conclusion: they are two separately-written implementations of similar topology metrics (Euler characteristic, connectivity density/probability, anisotropy, tortuosity), one for the live pipeline and one inside the dead legacy package, with no import edge between them in either direction. `analysis/run_psd_diagnostics.py` imports the `analysis/` copy only.

**Consequence for the reorg proposal:** `legacy/pores_analysis/` is confirmed safe to treat as fully dead code. It is **not** folded into any numbered stage folder (reversing the earlier tentative assumption in `REPO_SCAN.md` §9 that treated it as "kept intact... flag for deprecation"). Per §1/§2 of this plan, it becomes a `05_evaluation/legacy_pores_analysis/` archive-pending-deletion folder, with outright deletion as the maintainer's preferred final action once they've had a chance to confirm nothing external (e.g. a personal script outside this repo) still calls into it.

---

## 7. Documentation outlines

### `README.md`
Every path reference changes; outline of sections needing edits (content stays the same conceptually, paths updated):
1. Header / badges — no path changes.
2. Overview — `Figures/Workflow.png` → `00_docs/Figures/Workflow.png`.
3. Setup instructions — references to `preprocessing_nnUNet_train.py`, `preprocessing_nnUNet_predict*.py` → `02_preprocessing/nnunet/...`.
4. Training section — `nnUNetTrainer_betterIgnoreSampling.py` → `03_training/nnUNetTrainer_betterIgnoreSampling.py`; any mention of `_train_wrapper.py` → `03_training/scripts/train_wrapper.py`.
5. Inference section — `postprocessing_nnUNet_predict*.py` → `04_inference/...`.
6. Any mention of `analysis/` PSD tooling → `05_evaluation/psd/...`.
7. Citations/links section — replaced with a pointer to the new `RESOURCES.md` (full list moves there; README keeps only the 1-2 most essential citations inline if the maintainer wants that, else all move out — flagged as an open question, §9).
8. Footer/license — unchanged.

### `ARCHITECTURE.md` (new)
1. **Purpose** — one-paragraph statement that this describes the pipeline-stage folder layout introduced in the 2026-07 reorg.
2. **Pipeline stage overview** — one subsection per numbered folder (`01_data_ingestion` … `07_utilities`), each with: what lives there, what stage of the ML workflow it covers, its primary entry point(s).
3. **Folded-in modules** — explicit subsection for `microsam_3d/` (now under `05_evaluation/`) and `seg_plausibility/` (same), explaining they remain internally self-contained (own README/environment.yml) despite being nested, and why (independent conda environments, optional/interactive tooling not needed for the core train/infer loop).
4. **`legacy/pores_analysis/`** — subsection documenting it as an archived/dead package retained temporarily at `05_evaluation/legacy_pores_analysis/` for historical reference, explicitly superseded by `05_evaluation/psd/psd_diagnostics_core.py`, with a note that it re-verified as having zero runtime coupling to the live pipeline (link to §6 of this plan or its executed equivalent).
5. **Consolidated scripts** — brief map of S1-S12 (§3 of this plan) and where their `run_configs/` live.
6. **Data flow diagram** (textual or simple ASCII) — registry → preprocessing → training → inference → evaluation → reporting.
7. **Logs and outputs** — pointer to `logs_archive/` and its index format.

### `RESOURCES.md` (new)
Grouped by topic, each entry noting its prior location:
1. **Citations** — Nature Methods DOI, Geoderma DOI, project ESSOAr publication DOI (previously `README.md` L9, L12, L59/124).
2. **Institutional links** — UFZ, Helmholtz Imaging, EVE cluster (previously `README.md` L2, L56).
3. **Tooling install docs** — miniforge, devbio-napari, nnU-Net install instructions + repo, Fiji/ImageJ downloads (previously `README.md` L96, L114, L155, L157, L169).
4. **PyTorch wheel indices** — cu117 (README L247), cu124 (`setup_prompt.md` L18/21, `preprocess/run_preprocess.py:24`, `preprocess/gpu_nlm_torch.py:24`, now `02_preprocessing/filters/...`).
5. **micro-SAM background reading** — the 5 URLs from `microsam_3d/README.md` (L39, 43, 47, 51, 55), now `05_evaluation/microsam_3d/README.md`.
6. Footnote: nnU-Net's own auto-emitted doc link (`resenc_presets.md`) appearing in training log stdout is NOT included here — it's tool-generated log noise, not an authored reference (see `logs_archive/`).

### `.github/copilot-instructions.md` and `.github/agents/*.agent.md`
1. Update every literal path in all 4 agent files and copilot-instructions.md's environment-rules sections to match the new tree (`analysis/data_registry.json` → `01_data_ingestion/registry/data_registry.json`, `analysis/run_psd_diagnostics.py` → `05_evaluation/psd/run_psd_diagnostics.py`, etc.).
2. **§8 "Agent Permission Matrix" naming 5 agents (`@architect`, `@scientist`, `@segmentation`, `@performance`, `@reviewer`) vs. 4 actual files is explicitly flagged as an open decision — not resolved here.** Options for the maintainer to choose from at execution time: (a) delete §8 as aspirational/stale, (b) rename existing agents to match, (c) author the missing 5th agent file. This plan takes no position.

---

## 8. Small flagged items with proposed actions

| Item | Proposed action |
|---|---|
| `litreture/` typo | Rename to `00_docs/literature/` during the reorg move (step 2 of §2) — low risk, nothing references it by exact path outside its own listing. |
| `legacy/pores_analysis/PSD_DIAGNOSTICS_SUMMARY.md` referencing nonexistent `experiments/synthetic_psd_diagnostics.py` | Leave as-is if `legacy/pores_analysis/` is archived/deleted per §6 (the whole file goes with it); if the maintainer instead chooses to keep the folder around longer, correct the reference to point at the real `05_evaluation/psd/` equivalent test/synthetic-volume tooling. |
| 3-way chain `iter02_registry_mutation_request.json` → `..._corrected_latest_predictions.json` → `..._yfix.json` | Keep only the last (`..._yfix.json`) as the live registry-mutation record; delete the first two once confirmed their mutations were fully superseded (a one-time diff check before deletion, not assumed) — flagged as a step-2/9 item, not deleted in this pass. |
| Empty files (`_make_synopsis_i3_err.log`, `_make_synopsis_i4_err.log`, `_napari_seg_plausibility_i4_log3.txt`, `_seg_plausibility_i3_scratch_run.log`, `analysis/selected_outputs/.../_terminal_probe.txt`) | Delete outright (step 25, §2) — zero content, zero information loss. |
| Empty directories (`preprocess/nlm_output/`, `preprocess/norm200_output/`, `legacy/pores_analysis/results/`) | Delete outright (step 25, §2), contingent on `legacy/pores_analysis/results/` only if that folder is itself deleted per §6. |
| Log files already committed to git (`mishmar_psd.log`, `_inference_err.txt`, `_inference_log.txt`, `_inference_nlm_err.txt`, `_inference_nlm_log.txt`, `_napari_nlm_err.txt`, `_napari_nlm_log.txt`) | **Two separate operations, proposing only the first for this pass:** (1) remove from the working tree going forward and add to `.gitignore` (safe, non-destructive — history keeps the old blobs). (2) Purging them from git *history* (e.g. `git filter-repo`) is a separate, more invasive operation — **not proposed here**; flagged as an open question for the maintainer in §9 since it rewrites shared history and needs explicit sign-off. |

---

## 9. Remaining open questions for the maintainer

1. **`legacy/pores_analysis/` final fate** — this plan proposes outright deletion once the maintainer confirms nothing outside this repo depends on it (§6 found zero *internal* dependency, but cannot rule out an external personal script). Archive-folder-for-one-release vs. immediate deletion — which do you want?
2. **`.github/copilot-instructions.md` §8 Agent Permission Matrix** — per the prompt's instruction, this is explicitly not resolved here: delete the stale section, rename the 4 real agents to match the 5 named ones, or author the missing 5th agent?
3. **Git history purge of the 7 already-committed log/txt files** — remove-going-forward only (proposed default), or also rewrite history? Rewriting history affects anyone else with a clone/fork.
4. **`iter02_registry_mutation_request.json` chain** — confirm the first two files in the 3-way chain are safe to delete (i.e., their mutations were fully applied and are captured in the final `_yfix.json` or in `data_registry.json` itself) before step 2/9 executes.
5. **`dataset_info.json` — single canonical location vs. duplicate/symlink** — many scripts resolve it relative to `REPO_DIR` at repo root; should it stay at root only (safest, requires zero path changes across most scripts) or does the "utilities" grouping in §1 need it referenced by relative path instead? This plan defaults to **keep it at repo root only** and treats the `07_utilities/` listing as documentation, not a literal duplicate — please confirm.
6. **README citations** — should `RESOURCES.md` take over *all* external links (moving them entirely out of `README.md`), or should README keep the 1-2 headline citations inline with `RESOURCES.md` as a supplementary index? Both are common; pick one so the doc rewrite at execution time doesn't have to guess.
7. **`_run_iter04_continue.py` (mapping table row #3)** — needs a full read (only ~40 lines were sampled) before its consolidation target (S1 vs. a pure S5-style orchestrator) can be finalized. Not blocking for this plan, but blocking for execution of step 9 in §2.
8. **`_make_synopsis_i4.py` naming/content mismatch (row #44)** — the file is named for iteration i4 but its code processes `fresh_bnei_reem_i3_scratch` data into an `analysis/synopsis_i4` folder. Was this an intentional relabeling (i4 folder = "4th synopsis batch," not "iteration 4 model"), or a copy-paste bug where a genuine i4-model synopsis was never actually generated? Affects whether `run_configs/` for S7 should have a `synopsis_i4` config pointing at `fresh_bnei_reem_i3_scratch` (preserving current, possibly-buggy behavior) or a corrected one pointing at the real `fresh_bnei_reem_i4` model.
9. **`analysis/pore_metrics_research/papers/*.pdf` licensing** — before moving these out of the repo per §5, confirm none of them need to stay bundled for reproducibility/offline-access reasons specific to this project's institutional requirements.
10. **`Utilities/nifti_io.jar`** — REPO_SCAN flagged this as possibly unused (Fiji may bundle its own equivalent). Confirm whether any Fiji macro still explicitly loads this jar before deciding whether it moves to `07_utilities/` as active tooling or gets flagged for removal in a future pass.
