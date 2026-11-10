# Repo tidy-up at hand-off (2026-11)

Branch `handoff/2026-11-cleanup`. Scope: clutter at the repo root and loose evidence folders. Code stays where it is, except for two stray one-off files at the root. Every move was done with `git mv`, so `git log --follow <new path>` still shows the full history.

Reference check (A2): before each move, `git grep -n "<filename>"` was run over the whole repo. "Code refs" below lists the code files (`*.py`, `*.ipynb`, `*.yaml`, `*.json`, `*.ps1`, `*.bat`, `*.sh`) that name the file and what was done about them. Mentions of a file name in docstrings, comments or prose (no path is opened) are not functional references and were left as they are.

## Moves

| Current path | New path | Reason | Code refs |
|---|---|---|---|
| `bnei_reem_3d_render_followup_prompt.md` | `00_docs/prompts/` | agent prompt | none |
| `bnei_reem_i3_retrain_pipeline_prompt.md` | `00_docs/prompts/` | agent prompt | none |
| `bnei_reem_samp_2_0_repreprocess_prompt.md` | `00_docs/prompts/` | agent prompt | docstring only (`run_pom_shape_clustering_final.py`) |
| `bnei_reem_specB_visual_proof_prompt.md` | `00_docs/prompts/` | agent prompt | none |
| `connectivity_replicate_expansion_followup_prompt.md` | `00_docs/prompts/` | agent prompt | none |
| `connectivity_replicate_expansion_prompt.md` | `00_docs/prompts/` | agent prompt | none |
| `connectivity_topology_validation_kickoff.md` | `00_docs/prompts/` | agent prompt (kickoff) | none |
| `connectivity_topology_validation_prompt.md` | `00_docs/prompts/` | agent prompt | none |
| `ct_scan_parameters_discovery_prompt.md` | `00_docs/prompts/` | agent prompt | none |
| `local_asset_recovery_check_prompt.md` | `00_docs/prompts/` | agent prompt | none |
| `mishmar_5p85_3d_render_prompt.md` | `00_docs/prompts/` | agent prompt | none |
| `mishmar_downsample_ablation_prompt.md` | `00_docs/prompts/` | agent prompt | docstrings only (`pom_analysis_20260824_*/scripts/*.py`) |
| `missing_data_completion_prompt.md` | `00_docs/prompts/` | agent prompt | none |
| `pom_final_clustering_prompt.md` | `00_docs/prompts/` | agent prompt | docstring only (`part2_downsample_mishmar.py`) |
| `pom_interface_metrics_prompt.md` | `00_docs/prompts/` | agent prompt | docstring only |
| `pom_interface_metrics_resolution_fix_prompt.md` | `00_docs/prompts/` | agent prompt | docstring only |
| `pom_replicate_comparison_prompt.md` | `00_docs/prompts/` | agent prompt | docstrings only |
| `pom_resolution_and_clustering_prompt.md` | `00_docs/prompts/` | agent prompt | none |
| `pom_roi_expansion_and_final_clustering_prompt.md` | `00_docs/prompts/` | agent prompt | docstring only (`part1_margin_check.py`) |
| `setup_prompt.md` | `00_docs/prompts/` | agent prompt | printed text in a notebook cell output only |
| `tortuosity_subvolume_prompt.md` | `00_docs/prompts/` | agent prompt | none |
| `track_e_correction_prompt.md` | `00_docs/prompts/` | agent prompt | none |
| `bnei_reem_unified_pipeline_results.md` | `00_docs/reports/` | results write-up | **written by** `04_inference/scripts/run_bnei_reem_unified_pipeline.py` (`REPO_DIR / REPORT_NAME`): output path updated to `00_docs/reports/` in the same commit |
| `ct_scan_parameters_findings.md` | `00_docs/reports/` | findings write-up | none |
| `local_asset_recovery_findings.md` | `00_docs/reports/` | findings write-up | none |
| `subvolume_psd_stats_summary_v1.md` | `00_docs/reports/` | results summary | none |
| `psd_binning_recommendation.md` | `00_docs/reports/` | recommendation write-up | none |
| `figures_data_export.md` | `00_docs/reports/` | figure-data record | none |
| `_comparison_iter04_continue_vs_fresh.pdf` / `.png` | `00_docs/reports/` | one-off comparison render | **written by** `04_inference/scripts/legacy_per_iteration/_run_fresh_then_compare_napari.py`: output path updated in the same commit |
| `bnei_reem_specB_visual_evidence/` | `00_docs/reports/bnei_reem_specB_visual_evidence/` | evidence folder for the Specimen B investigation | docstring only (`run_bnei_reem_samp_2_0_true_recon_pipeline.py`) |
| `REORG_PLAN.md` | `00_docs/reorg_2026-07/` | reorganisation record | YAML header comments only (`*/run_configs/*.yaml`), docstring in `launch_napari_review.py` |
| `REORG_EXECUTION_REPORT.md` | `00_docs/reorg_2026-07/` | reorganisation record | none |
| `REPO_SCAN.md` | `00_docs/reorg_2026-07/` | reorganisation record | none |
| `convert_pred_to_tif.py` | `07_utilities/scripts/` | stray one-off script (CLI, paths are arguments) | none |
| `colab_nnUNet_pipeline.ipynb` | `07_utilities/scripts/` | stray one-off notebook (uses absolute `REPO_DIR`, so the move does not change its behaviour) | docstring only (`run_bnei_reem_samp_2_0_true_recon_pipeline.py`) |
| `README.md` (UFZ upstream tutorial) | `00_docs/UPSTREAM_README_UFZ.md` | replaced by a project front page; image and `RESOURCES.md` links fixed | `example_workflow.py` prints "pores_analysis/README.md" (a different file) |

The reorganisation records go in `00_docs/reorg_2026-07/`, not `reorg_2026-08/` as first proposed: the files are dated 2026-07-07/08 and describe "the 2026-07 reorganization" (`RESOURCES.md`, `REORG_EXECUTION_REPORT.md`).

## Stop tracking (file kept on disk, added to `.gitignore`)

| Path | Reason |
|---|---|
| `freetype.dll` | binary DLL, not project source |
| `_napari_mishmar_microSAM_log.txt`, `_napari_mishmar_microSAM_err.txt` | orphaned napari logs, already listed in `.gitignore` but still tracked |
| `00_docs/literature/nnUNet4SoilCT_atricle.pdf` | third-party paper, added in this fork (2026-04-19, `86e8663`), not in upstream `MaxPhal/nnUNet4SoilXrayCT` |
| `05_evaluation/psd/vogel_psd.pdf` | third-party paper, added in this fork (2026-04-21, `4d16ba3`), not upstream |
| `dor2025_fig1a_reference.png` | figure from a published paper (Dor et al. 2025), added in `2efa4c8` (2026-11-03). The render scripts read it from the repo root by path; it stays there on disk, so they keep working |

Removing a file from tracking does not remove it from history. All five are still in earlier commits of this public repo. Purging them would need a history rewrite, which this tidy-up does not do (see the hand-off report).

## Left alone on purpose

- Root files kept: `README.md` (new), `LICENSE`, `DATA_CATALOG.md`, `PROJECT_STATUS.md`, `ARCHITECTURE.md`, `RESOURCES.md`, `dataset_info.json` (scripts read it from the root), `.github/`, `.gitignore`.
- `logs_archive/`: archive folder created by the 2026-07 reorg, referenced from `RESOURCES.md` and the reorg records.
- `.claude/` and `.vscode/` (6 tracked files): editor/agent settings; `.vscode/` is already in `.gitignore` but tracked. Not touched.
- `microsam_3d/` and `predictions_rehovot_20260815/` at the root are untracked local folders, so they are not part of the repo.
- Prose mentions of moved files inside prompts and reports (historical records) were not rewritten.
