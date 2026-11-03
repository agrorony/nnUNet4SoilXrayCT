# Prompt — complete the missing data (run on the remote lab computer, HIVE3065)

Paste this into a Claude Code session on the lab computer that has the `nnUNet4SoilXrayCT` repo and the `Yael_Mishael` share. Access to that share was restored on 2026-10-04 after a permissions problem; nothing was deleted.

---

You are helping Rony close the remaining data gaps in his soil µCT research exercise. **The write-up is in its final stage. This is a gap-filling job, not new research:** no retraining, no new metrics, no new pipeline. Reuse existing scripts and outputs. Do not modify or overwrite any existing output; write everything new into one folder: `06_reporting/missing_data_20261004/` inside the repo.

## Read first
1. `DATA_CATALOG.md` in the repo root (canonical specimen list; the short mirror version in Rony's project folder agrees with it). Rules that matter: distinct names ≠ distinct specimens; never add or count a specimen without a raw folder + log-confirmed voxel size; the Bnei Re'em "canonical" volume's specimen identity is unresolved (numerically identical to Specimen B) — don't relabel it.
2. `PROJECT_STATUS.md` and `local_asset_recovery_findings.md` (repo root) — background only.

## Step 0 — verify access (stop and report if this fails)
- Confirm the share is readable (`\\HIVE3065\Yael_Mishael\Rony\...`, also mounted as `E:\PROJECTS\Yael_Mishael` on this host; `Z:` may or may not be mapped).
- For every path in DATA_CATALOG's specimen rows and every model folder under `remote_computer backup\nnUNet_resources\` named below, report exists / missing. If a path is missing, **do not guess a replacement** — list it and continue with the rest.

## Step 1 — Rehovot samp3 Track E numbers (highest priority)
Rehovot has n=2 physical specimens (`samp2`, `samp3`). The local analysis mirror only has samp2's topology summary. Find samp3's existing Track E run (expected under `remote_computer backup\Topology_Metrics_Aug2026\raw\`, run folder containing `samp3`/`samp_3`; check its log shows it was built from `10.12.25_Rehovot_samp_3_clean`, 15.034357 µm).
- Copy its `summary.json`, `psd_table.csv` and any connectivity-function (χ(r)) output into `missing_data_20261004/rehovot_samp3_track_e/`.
- Extract into one CSV row, same columns as samp2: pore fraction, χ, connectivity density, Γ, DA, r*, PSD 30–150 µm fraction, tortuosity if present.
- Compute Rehovot mean ± SE (n=2) for each metric. **SE, never SD.**
- Cross-check against Table 3 of `figures draft - updated v8/v9.docx` if you can find it; report any mismatch rather than choosing one.

## Step 2 — real training curves for the two models used in the paper
Models: Bnei Re'em `multi_sample_fresh_bnei_reem_i4` and Mishmar `i2_loess` (confirm exact folder names). The repo's `logs_archive/training/*.log` are launcher logs only; the real per-epoch logs are in each model's `nnUNet_results\...\fold_*\training_log_*.txt` (and `progress.png`) on the share.
- Locate and use the existing `06_reporting/scripts/plot_training_metrics.py` / `aggregate_training_diagnostics.py`. Don't write a new plotting script if these work.
- Output: one train/val loss + pseudo-Dice curve per model, plus a 3–5 line note per model: epochs run, best vs final epoch, whether validation loss diverged from training loss (overfitting sign), and the train/val split size. Remember the dataset is tiny (sometimes 1 volume with a forced split), so Dice is not a reliable success measure — say so in the note.

## Step 3 — prediction images for Figure 7 (minimal)
Goal: one panel per soil — raw slice | segmentation overlay — for the paper's Figure 7.
- Volumes: Vertisol `bnei_reem_specA_unified` (and/or Specimen B), Loess `mishmar_hanegev_maoz_3_5p85um`, Sand `Rehovot_samp2_highkV_Cu0.11_15um`.
- **Use existing inference outputs** (`inference_concatenated\*.nii.gz`). Before using one, verify it was produced by the stated checkpoint: compare the output's timestamp with the checkpoint's, and check the inference log. (This project has a documented failure where stale predictions were reused.) Only if no valid output exists, run inference with the latest checkpoint of that soil's model and log the exact checkpoint path and time.
- Use the same mid-volume z-slice for raw and prediction, the same colors for all soils (matrix transparent, pore one color, POM another; Rehovot is binary pore/solid), and a scale bar in mm from the log-confirmed voxel size. Export PNG at 300 dpi.
- Note the label convention actually deployed (pore=5, POM=2), not `dataset_info.json`.

## Step 4 — two read-only checks (report only, do nothing else)
- Does a `fresh_bnei_reem_i3` (5-class) checkpoint exist anywhere on the share? Report path/date or "not found". **Do not retrain.**
- Is the native 8.8 µm POM % of `mishmar_hanegev_maoz_2_8p8um` recorded in any existing run output? Report it with source file or "not found". Don't compute it fresh.

## Step 5 — housekeeping
Add one dated line to the repo copies of `PROJECT_STATUS.md`, `DATA_CATALOG.md` and `local_asset_recovery_findings.md`: share access restored 2026-10-04, nothing was deleted, earlier "inaccessible" statements are superseded. Do not otherwise edit these files. Leave the git commit to Rony (git from agents on this repo has been unreliable).

## Deliverable
`06_reporting/missing_data_20261004/REPORT.md` with: Step-0 path table; each step's result with the exact source file for every number; anything not found; anything that disagreed with existing documents. Keep it short. Rony will copy the folder into his project folder (`07_analysis_runs/`) for the write-up.
