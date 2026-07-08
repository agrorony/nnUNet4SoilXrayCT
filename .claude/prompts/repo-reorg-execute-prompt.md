# Phase 3 Prompt — Execute the Reorganization

> Paste this into Claude Code, running inside the repo root. Read `REORG_PLAN.md` in full first — it is the approved plan. This pass actually moves, renames, deletes, and rewrites files. Work carefully and in the dependency-safe order specified in the plan's §2.

Execute `REORG_PLAN.md` exactly as written, **except** for the five amendments below, which override or add to specific parts of the plan (the maintainer decided these after the plan was written):

## Amendments to REORG_PLAN.md

**A. `legacy/pores_analysis/` (overrides plan §6/§9 Q1 final-fate framing):**
Proceed with the plan's step 20 — move it to `05_evaluation/legacy_pores_analysis/` as an archive folder, do not delete it in this pass. Additionally, create a short `05_evaluation/legacy_pores_analysis/ARCHIVED.md` note stating: archived on today's date, confirmed zero internal runtime dependency (per plan §6), scheduled for outright deletion in the next reorg/cleanup cycle. Reflect this "archived, pending deletion" status in `ARCHITECTURE.md` §4 rather than describing it as a permanent fixture.

**B. `.github/agents/` system (overrides plan §7's "update paths" treatment and §9 Q2 — broader than originally scoped):**
Delete the entire agent system, not just the stale §8 section:
- Delete all four `.github/agents/*.agent.md` files (`data-registry-path-validation.agent.md`, `ml-workflow-orchestrator.agent.md`, `notebook-builder.agent.md`, `psd-analysis-runner.agent.md`).
- Delete `.github/skills/report-agent-run-status.skill.md`.
- In `.github/copilot-instructions.md`, remove §8 "Agent Permission Matrix" entirely, and also remove any other section/reference that describes or depends on these agent files existing (scan the whole file, not just §8 — do not leave dangling references).
- `ARCHITECTURE.md` should not include an "agent system" section at all.

**C. Committed log files (confirms plan §8/§9 Q3 default — no change, stated for clarity):**
For `mishmar_psd.log`, `_inference_err.txt`, `_inference_log.txt`, `_inference_nlm_err.txt`, `_inference_nlm_log.txt`, `_napari_nlm_err.txt`, `_napari_nlm_log.txt`: stop tracking going forward (`git rm --cached` + add to `.gitignore`) and move them into `logs_archive/` per plan §4. Do **not** rewrite git history.

**D. `_make_synopsis_i4.py` naming mismatch (overrides plan §9 Q8 — resolves the flagged ambiguity):**
This script is misnamed: it's labeled "i4" but actually processes `fresh_bnei_reem_i3_scratch` data. Do not change what data it processes — instead rename it to accurately reflect reality. When consolidating into `06_reporting/scripts/make_synopsis.py` (script S7), name the corresponding config file something accurate (e.g. `fresh_bnei_reem_i3_scratch_synopsis.yaml`, not `synopsis_i4.yaml`), and likewise give its output folder an accurate name rather than perpetuating `analysis/synopsis_i4` as if it were real iteration-4 output. Note this rename explicitly in whatever execution log/report you produce, so historical "synopsis_i4" output isn't later confused with an actual i4-model run.

**E. Remaining minor open items from plan §9 — proceed with the plan's own stated defaults, no further sign-off needed:**
- `dataset_info.json` stays canonical at repo root only (§9 Q5 default).
- `RESOURCES.md` takes over *all* external links; `README.md` keeps only a pointer to it (§9 Q6, resolved toward the "move everything out" option).
- `analysis/pore_metrics_research/papers/*.pdf` — move out of the repo per §5's recommendation, cited by DOI/URL in `decisions.md` (§9 Q9 default accepted).
- `Utilities/nifti_io.jar` (§9 Q10) — before relocating it to `07_utilities/`, check whether any `Fiji_macros/*.ijm` explicitly loads it; if none do, flag it clearly as unused in the execution report rather than silently keeping it.
- `iter02_registry_mutation_request.json` chain (§8/§9 Q4) — do the one-time diff check the plan calls for before deleting the first two files in the chain; if the diff shows anything not fully captured in `..._yfix.json` or `data_registry.json`, stop and flag it instead of deleting.
- `_run_iter04_continue.py` (§9 Q7) — do the full read the plan calls for before finalizing whether it maps to S1 or a pure S5-style orchestrator.

## Execution requirements

- Follow `REORG_PLAN.md` §2's ordered checklist, folding in the amendments above at the corresponding steps (B affects step 26/docs; A affects step 20; C affects step 24; D affects step 15).
- Commit at logical checkpoints (e.g. after the directory skeleton + first moves, after script consolidation, after doc rewrites) rather than one giant commit, so the reorg is reviewable/revertible in pieces.
- Run the final verification pass (plan step 27) — confirm every referenced path in every doc/script actually resolves post-move.
- Produce `REORG_EXECUTION_REPORT.md` summarizing: what was done, any place reality diverged from the plan (e.g. what the full read of `_run_iter04_continue.py` or the `nifti_io.jar` check revealed), and confirmation that the five amendments above were applied.
