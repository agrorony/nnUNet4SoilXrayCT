# Missing-data completion — 2026-10-04

Gap-filling only: no retraining, no new metrics, no existing output modified. Everything new is in this folder. Share root below = `E:\PROJECTS\Yael_Mishael\Rony\` (`RB` = `remote_computer backup`).

## Step 0 — access
`\\HIVE3065\Yael_Mishael\Rony` **does not resolve from this host** (Test-Path False); `Z:` is **not mapped**. `E:\PROJECTS\Yael_Mishael` is readable and has everything. (Log files and scripts still contain `\\hive3065\...` paths — they are the same files.)

| Path | Status |
|---|---|
| `10.12.25 Rehovot` (samp1), `10.12.25_Rehovot_samp_2`, `_samp_3`, `_samp_3_clean` | exists |
| `18.12.25 bnei_reem_samp_2`, `18.12.25 bnei_reem_samp_2.0` (+ `..._samp_2.0_Rec`) | exists |
| `29.3.26 mishmar_hanegev_samp_1/2/3` | exists |
| `mishmar_hanegev_maoz\3-16mm_diam_5.85um`, `\2-16mm_diam_8.8um` | exists |
| `test`; `RB\Topology_Metrics_Aug2026\raw` | exists |
| `RB\nnUNet_resources\` `multi_sample_fresh_bnei_reem_i4`, `multi_sample_mishmar_hanegev_maoz_3_5p85um_loess_i2` | exists (exact names) |
| `...\bnei_reem_specA_unified`, `bnei_reem_specB_unified`, `bnei_reem_fresh_bnei_reem_i4` (inference_concatenated) | exists |
| `...\mishmar_hanegev_maoz_3_5p85um`, `mishmar_hanegev_maoz_2_8p8um`, `rehovot_inference_rehovot_samp_2`, `rehovot_inference_Rehovot_samp3_...` | exists |

Nothing missing. Not located: `figures draft - updated v8/v9.docx` (not on E:, nor C:\Users\rony.schwartz Documents/Desktop/Downloads).

## Step 1 — Rehovot samp3 Track E → `rehovot_samp3_track_e/`
Source run: `RB\Topology_Metrics_Aug2026\raw\psd_diag_20260829T164636_rehovot_samp3_full_volume\` (summary.json, psd_table.csv, config.json copied); χ(r): `...\connectivity_function\chi_r_rehovot_samp3.csv` + `.meta.json` (samp2's `chi_r_rehovot.csv` also copied for comparison). Table: `rehovot_track_e_samp2_samp3_mean_se.csv`.

| | samp2 (15.0 µm) | samp3 (15.034357 µm) | mean ± SE (n=2) |
|---|---|---|---|
| Pore fraction % | 30.498* | 40.848 | 35.67 ± 5.17 |
| χ | −53,704 | −70,319 | −62,012 ± 8,308 |
| Conn. density mm⁻³ | 57.94 | 75.35 | 66.65 ± 8.70 |
| Γ | 0.98892 | 0.99738 | 0.99315 ± 0.00423 |
| DA | 0.19562 | 0.17008 | 0.1829 ± 0.0128 |
| r* (µm) | 100.8 | 147.00 | 123.9 ± 23.1 |
| PSD 30–150 µm | 0.70304 | 0.56033 | 0.6317 ± 0.0714 |
| Tortuosity ax0/1/2 | 3.666/3.398/3.148 | 2.516/2.106/1.908 | 3.091/2.752/2.528 ± 0.575/0.646/0.620 |

SE = |a−b|/2 (SD with n−1, divided by √2). *Pore fractions: samp3 = `n_pore_voxels_raw`/650³ (meta.json); samp2 = `n_voxels_ge_r` at r=2 µm in `chi_r_rehovot.csv` ÷ 650³ (matches 0.3050 in `connectivity_validation_summary.md`). samp2 r* from `crossover_radius_summary.md`; samp3 r* from `chi_r_rehovot_samp3.meta.json`.

Cross-checks: values/means agree with `Topology_Metrics_Aug2026\connectivity_replicate_expansion_summary.md` (§Rehovot n=2 table) and `figures_data_export.md`. **Table 3 of the docx could not be checked (file not found).**

Provenance flags (not resolved, not hidden):
- The log does **not** show the `10.12.25_Rehovot_samp_3_clean` folder by name. Run input = `RB\10.5\Rehovot_samp3_highkV_Cu0.11_15um.npy`, whose source `.tif` is dated 2026-08-04 (= clean re-reconstruction date in DATA_CATALOG), 15.034357 µm per config. Consistent, but indirect.
- The `.npy` mask is dated 2026-08-29 17:40, i.e. ~1 h **after** the run (16:46). Not explained; the pore count in meta.json (112,178,509 voxels = 40.848%) equals the Otsu mask described in the summary.
- Rehovot masks (both samp2 and samp3) are **global-Otsu binary, not nnU-Net** (`connectivity_replicate_expansion_summary.md` §1).

## Step 2 — training curves → `training_curves/`
Used the existing `06_reporting/scripts/plot_training_metrics.py` unmodified, pointed (`--results-dir`) at **copies** of the logs in `training_curves/<model>/src/` so nothing was written to the share. Outputs: `training_metrics_bnei_reem_i4.png/.pdf`, `training_metrics_mishmar_i2_loess.png/.pdf` (train/val loss + mean pseudo-Dice), plus nnU-Net's own `progress_nnunet_*.png`. Sources: `RB\nnUNet_resources\<model>\nnUNet_results\Dataset777_GCEF\<trainer>__nnUNetPlans__3d_fullres\fold_0\training_log_*.txt`.

**Bnei Re'em `multi_sample_fresh_bnei_reem_i4`** (trainer `..._earlyStopValLoss_lowlr`, log 2026-07-05): 88 epochs (0–87), stopped by the custom early-stop (wait 20/20), no max-epoch limit hit. Lowest val loss −0.6317 at epoch 67 (log: "best_val_loss −0.631746"); final −0.626 (train −0.6153). Mean pseudo-Dice peaked 0.977 (epoch 74), final 0.976. Val loss tracks train loss (gap ≈ −0.01 over last 10 epochs) — no divergence/overfitting signature. **Split: 1 train / 1 val case, same volume (`nlm_volume`); log warns "validation cases are also in the training set".** Val loss/Dice are therefore not held-out measures; Dice ≈ 0.97 does not show generalization.

**Mishmar `..._loess_i2`** (log 2026-07-15): 69 epochs (0–68), early-stopped (20/20). Lowest val loss −0.9118 at epoch 48; final −0.9062 (train −0.8841). Mean pseudo-Dice peaked 0.968 (epoch 62), final 0.964. No train/val divergence (gap ≈ −0.013). **Split: 1 train / 1 val, same volume (`mishmar_hanegev_maoz_3_5p85um`), same overlap warning** — Dice is not a reliable success measure.

Both: pseudo-Dice has 5 entries, classes 3 and 4 are NaN (unused labels) → mean is over 3 classes. (Epoch numbers = 0-indexed log counter.) Naming: the loess_i2 log's splits path says `..._scratch_i2` — the same run under its earlier iteration name; `run_inference` args for loess chunks also say `scratch_i2`.

## Step 3 — Figure 7 → `figure7/figure7_prediction_panels.png` (300 dpi, + .svg, `make_fig7.py`, `figure7_slice_info.json`)
Mid-volume slice (axis 2 index 325 / 500 for Mishmar 1000³), same for raw and overlay; pore = blue, POM = red, matrix and Stones (label 1) transparent; scale bar 2 mm (15 µm) / 1 mm (5.85 µm). Deployed labels: **pore=5, POM=2** (dataset.json lists 7 labels incl. POM_type2=3, unused=4; none present).

| Soil | Segmentation used | Validity evidence |
|---|---|---|
| Vertisol Spec A | `nnUNet_resources\bnei_reem_specA_unified\inference_concatenated\bnei_reem_specA_unified.nii.gz` (2026-09-07 12:16) | `bnei_reem_unified_pipeline_log.txt`: `--trainer ..._lowlr`, model `multi_sample_fresh_bnei_reem_i4`, `checkpoint_final.pth` (2026-07-05 19:41) → output is 2 months newer. Labels: pore 15.169 %, POM 0.240 % = catalog. |
| Loess 5.85 µm | `...\mishmar_hanegev_maoz_3_5p85um\inference_output_concat_loess_i2\...nii.gz` (2026-07-16 00:27) | Newer than `loess_i2` `checkpoint_final.pth` (2026-07-15 15:19). **No run log exists**; chunk args.json says `scratch_i2` (old name). Labels: pore 27.038 %, POM 1.615 % = catalog exactly. |
| Sand samp2 | `RB\10.5\rehovot_samp_2.npy` — global-Otsu binary pore mask, the one Rehovot's Track E uses | Not nnU-Net (deliberate, see Step 1). nnU-Net outputs (`rehovot_inference_rehovot_samp_2\inference_concatenated_{bnei_reem_i4,loess_i2}`, 2026-08-15, `checkpoint_final.pth` per its pipeline_log) exist if you prefer those; I did not render them. |

Note: nnU-Net outputs are **y-flipped relative to the raw nifti** (found by correlating the pore mask with raw under all axis permutations/flips; best = flip axis 1, r −0.77 / −0.86 vs. unflipped much weaker). The script flips the segmentation for display only. Rehovot's npy needed axis permutation (2,1,0) (r −0.85). No inference was re-run. Bnei Re'em panel is Specimen A (unified), not the legacy "canonical"; Specimen B not rendered.

## Step 4 — read-only checks
- **`fresh_bnei_reem_i3` checkpoint: exists.** `nnUNet_resources\multi_sample_fresh_bnei_reem_i3\...\nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss__nnUNetPlans__3d_fullres\fold_0\`: `checkpoint_final.pth` 2026-07-01 16:06, `checkpoint_best.pth` 15:24. Variants: `..._i3_lowlr` (final 2026-07-02 15:45), `..._i3_scratch` (final 2026-07-05 20:36). I did not verify the class count inside the checkpoints (dataset.json is the shared 7-label schema).
- **Native 8.8 µm POM %: not found.** Recorded for `maoz_2_8p8um` native: pore 22.984 % only (`connectivity_replicate_expansion_summary.md`; `raw\psd_diag_20260829T164703_..._native\` has no POM fraction). The only POM number is **7.859 %**, for the *label-downsampled ROI-expanded* volume (`track_e_correction_summary.md` Step 1–2 table) — not the native 1000³ volume. Not computed fresh.

## Disagreements / open items
1. UNC `\\HIVE3065` and `Z:` don't resolve here; `E:` does. Docs/scripts that hard-code the UNC path (incl. `plot_training_metrics.py` HIVE_BASE) need `--results-dir` on this host.
2. figures draft docx not found → Table 3 unchecked.
3. samp3 provenance caveats above (clean-folder not named in log; npy timestamp after run).
4. Mishmar loess_i2 inference has no log; validity rests on timestamp + label percentages.
5. DATA_CATALOG still lists Bnei Re'em canonical (`..._i4` legacy) POM numbers as Table 1/2 source and its identity is unresolved (unchanged; Fig 7 uses Spec A unified).

## Step 5
One dated line appended to the repo copies of `PROJECT_STATUS.md`, `DATA_CATALOG.md`, `local_asset_recovery_findings.md`. No git commit made.
