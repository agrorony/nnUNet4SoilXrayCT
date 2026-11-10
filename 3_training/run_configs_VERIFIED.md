# Verification status — run_configs/*.yaml vs. legacy_per_iteration/*.py

Per `REORG_PLAN.md` step 9/10, the 12 training configs (and the mirrored
inference configs in `04_inference/run_configs/`) should be run once each
and diffed against the last known-good output of the original per-iteration
script before the `legacy_per_iteration/` copies are deleted.

**This verification cycle was NOT performed in this reorg execution pass.**
Running these configs requires the actual GPU/HIVE-network training and
inference pipeline (multi-hour nnUNet training jobs, network-mounted data),
which was outside the scope/capability of the automated reorg pass. The
YAML values were derived from:

- Direct source inspection of one representative script per family
  (`_run_fresh_bnei_reem_i3.py` for the training shape,
  `_run_inference_fresh_bnei_reem_i3.py` for inference), matching
  `REORG_PLAN.md` §3.3's own stated methodology.
- The `REORG_PLAN.md` §3.3 mapping table for the remaining configs'
  parameter values (trainer name, GPU, base checkpoint, annotation path).

**Known approximation**: the `iter03`, `iter04`, `train_fresh_bnei_reem`,
and `iter04_continue` configs' `annotation_path` values could not be
independently re-verified against the original scripts in this pass (the
plan's own table already listed `iter03`/`iter04`'s annotation path as a
placeholder, `E:\...\annotations_iter03\new_annotations.nii.gz`, rather
than a confirmed absolute path; `train_fresh_bnei_reem` and
`iter04_continue`'s annotation paths were inferred from naming convention,
not read from source). **Do not treat these two YAMLs as trustworthy
without a maintainer re-check against `legacy_per_iteration/_run_iter03.py`,
`_run_iter04.py`, `legacy_per_iteration/train_fresh_bnei_reem.py`, and
`legacy_per_iteration/train_iter4_continue_bnei_reem.py`.**

| Config | Verified (run + diffed)? |
|---|---|
| iter03 | No |
| iter04 | No |
| fresh_bnei_reem_i2 | No |
| fresh_bnei_reem_i3 | No |
| fresh_bnei_reem_i3_lowlr | No |
| fresh_bnei_reem_i3_scratch | No |
| fresh_bnei_reem_i4 | No |
| mishmar_hnegev_scratch | No |
| mishmar_hnegev_trained | No |
| train_fresh_bnei_reem | No |
| iter04_continue | No |

**Action required**: before deleting any `legacy_per_iteration/` script,
run its corresponding new consolidated script + config side by side and
confirm equivalent output, per the plan's original intent.
