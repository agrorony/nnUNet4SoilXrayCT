# Phase 2 Prompt — Detailed Reorganization Plan (Planning Only, No Execution)

> Paste this into Claude Code, running inside the repo root. Read `REPO_SCAN.md` first — it is the source of truth for current repo state and must not be re-derived from scratch.

---

You are producing a **detailed execution plan** for reorganizing this repository. Do NOT move, rename, delete, merge, or edit any file in this pass. Output a single new file, `REORG_PLAN.md`, that is precise enough to execute mechanically in a later, separate pass. Every decision below has already been made by the maintainer — do not re-litigate them, only work out the mechanics.

## Decisions already made (implement these, don't second-guess them)

**1. Final structure:** Pipeline-stage based, numbered top-level folders (data ingestion → preprocessing → training → inference → evaluation → reporting → utilities, per the proposal in `REPO_SCAN.md` §9). `microsam_3d/` and `seg_plausibility/` are **not** kept as independent sibling packages — fold them fully into the numbered stage folders. `legacy/pores_analysis/` is handled per decision #5 below (it may end up archived/removed instead of folded in, depending on the dependency check).

**2. Root scratch scripts (~110 files: `_run_*`, `_launch_napari_*`, `_plot_*`, `_make_synopsis_*`, `train_*`, etc.):** These must become parameterized scripts (iteration name/config passed as CLI args or a config file) that call into the solid, importable modules — not copy-pasted per-iteration forks. Design and specify:
   - How many distinct consolidated scripts are actually needed (one per logical operation — e.g. run-training, run-inference, launch-napari-comparison — not one per iteration).
   - The exact parameter set each one takes.
   - A dedicated folder to hold these consolidated runner scripts (propose a name and location within the numbered structure — e.g. under the relevant stage folder's own `scripts/` subfolder, or a single shared location if a script spans stages — justify whichever you pick).
   - A per-file mapping table: every one of the ~110 existing scratch scripts → which consolidated script + parameter values it maps to, so no iteration's specific behavior is silently lost. Flag any script whose logic doesn't cleanly fit the consolidation pattern.

**3. Logs:** Every training/inference log currently dumped at repo root must be (a) summarized — extract key fields per run (iteration name, final loss/dice, duration, date, success/fail) into a single structured index (propose format: CSV or a table in a markdown file) — and (b) the raw log files relocated into one dedicated, sorted log-archive folder (propose the exact path and the sorting scheme, e.g. by iteration name then date). Specify both the summary format and the archive folder layout precisely.

**4. Large binary outputs** (`analysis/selected_outputs/.../instance_map.tif` ~1.05GB, `errors.json` ~66MB, `track_table.csv` ~7.5MB, `analysis/pore_metrics_research/papers/*.pdf` ~15MB total, `analysis/synopsis_i3/`+`synopsis_i4/` ~35MB of PNGs, `validation_run/sub_z200_300.nii.gz` ~3MB): for each file/folder, propose a specific handling — gitignore in place, move outside the repo folder, or Git LFS — with a one-line rationale each. This is a recommendation for maintainer sign-off, not something to act on yet.

**5. `legacy/pores_analysis/`:** This is genuinely dead/superseded code (superseded by `analysis/psd_diagnostics_core.py`, per its own README). However, on 2026-07-07 the maintainer gave an agent an imprecise prompt while developing the next pipeline stage, and that agent may have built the new work (`legacy/pores_analysis/extended_pipeline.py`, `topology_metrics.py`, `environment.yml`, and/or `analysis/psd_topology_metrics.py`) with an accidental dependency on this legacy code rather than on the live `analysis/psd_diagnostics_core.py` module. Do the following, in order, and do not skip the verification even though the prior scan reported no cross-dependency — that scan predates this concern being raised and must be re-checked specifically for it:
   - Search explicitly for any import of, call into, or other runtime dependency on anything under `legacy/pores_analysis/` from any file added or modified on 2026-07-06 or 2026-07-07 (this includes `analysis/psd_topology_metrics.py`, and the three new legacy files themselves calling back into older legacy modules in a way that would survive legacy's removal).
   - If such a dependency is found: report exactly what depends on what (file + line), and flag it as a problem to fix — the new stage-in-progress work should be decoupled from legacy and rebuilt against `analysis/psd_diagnostics_core.py` instead. Do not attempt the fix yourself in this pass; just produce a precise diagnosis for the maintainer to act on.
   - If no such dependency is found: confirm `legacy/pores_analysis/` is safe to treat as dead code, and include it as a candidate for archiving/removal (not a kept module) in the final reorg proposal — this reverses the earlier assumption that it should be preserved as active WIP.
   - Either way, explicitly re-confirm or correct the scan's finding that `analysis/psd_topology_metrics.py` and `legacy/pores_analysis/topology_metrics.py` are independent, non-importing near-duplicates — this is the crux of the concern.

## Documentation to specify (outline, not full prose yet)

For each of the following, give a section-by-section outline of what it will contain post-reorg (not the final text — that comes at execution time):

- **`README.md`** — updated so every file path/reference matches the new structure. Note every place a path will need to change.
- **`ARCHITECTURE.md`** (new) — describes the pipeline-stage layout: what lives in each numbered folder, and how the modules that got folded in (`microsam_3d`, `seg_plausibility`, `legacy/pores_analysis`) fit within it.
- **Consolidated links/resources file** (new, e.g. `RESOURCES.md`) — gather every external URL currently scattered across `README.md`, `setup_prompt.md`, `microsam_3d/README.md`, and code comments (full list in `REPO_SCAN.md` §6) into one place, grouped by topic (citations, tooling downloads, install docs, etc.), with a note of what referenced it before.
- **`.github/copilot-instructions.md`** and **`.github/agents/*.agent.md`** — update every path reference to match the new structure. Separately and explicitly flag §8 ("Agent Permission Matrix," which currently lists 5 agents while only 4 exist) as an open decision for the maintainer — do not silently pick a resolution.

## Small flagged items — include a proposed action for every one, batched for one sign-off

- `litreture/` directory name typo (should be `literature`).
- `legacy/pores_analysis/PSD_DIAGNOSTICS_SUMMARY.md` referencing a nonexistent `experiments/synthetic_psd_diagnostics.py`.
- The 3-way superseded chain `iter02_registry_mutation_request.json` → `..._corrected_latest_predictions.json` → `..._yfix.json`.
- Empty files and empty directories listed in `REPO_SCAN.md` §1/§7.
- Log files already committed to git that shouldn't be (`mishmar_psd.log`, `_inference_*.txt`, `_napari_nlm_*.txt`) — note that removing them going forward and purging them from git history are different operations; specify which you're proposing.

## Output format for `REORG_PLAN.md`

1. Final folder tree (complete, every file placed).
2. Ordered operation checklist — every move/rename/create/delete as a literal, executable step, in dependency-safe order (e.g. update import paths in the same step as a move that breaks them — cross-reference `REPO_SCAN.md` §8 for what breaks when).
3. Consolidated-script design (per decision #2) with the full per-file mapping table.
4. Log summarization + archive design (per decision #3).
5. Large-file recommendations table (per decision #4).
6. `legacy/pores_analysis/` dependency re-verification result (per decision #5).
7. Documentation outlines (per the section above).
8. Small flagged items with proposed actions.
9. Remaining open questions that still need a maintainer decision before execution can start.

No file should be created, moved, or edited in this pass other than `REORG_PLAN.md` itself.
