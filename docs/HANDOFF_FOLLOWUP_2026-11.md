# Hand-off follow-up (2026-11-10 to 2026-11-14)

Follows `docs/HANDOFF_REPORT.md` (the 2026-11-03 hand-off). Prompt: `00_docs/prompts/handoff_followup_2026-11_prompt.md` (on the lab computer; prompts are no longer kept in the repo). Rony approved every gate in chat.

Nothing on the share, in `nnUNet_resources\`, the raw scan folders or `10.5\` was changed. All package edits were made in the staging folder `E:\PROJECTS\Yael_Mishael\Rony\handoff\Schwartz_soil_uCT_handoff_2026-11\`, and a copy of every file was saved before it was changed or removed (folders listed under Part G). v1 of the ZIP is kept.

- **Scripts:** `6_figures/handoff_followup/`, named after the part they belong to.
- **Evidence:**
  - PNGs: `docs/handoff_followup_2026-11/`
  - JSON and text logs: `docs/handoff_followup_2026-11/logs/`
  - Originals: `E:\PROJECTS\Yael_Mishael\Rony\handoff\_evidence_followup_2026-11\`

## Bottom line

- **Duplicates (A):** no new duplicates. The only near-identical image pair is canonical vs specB (r = 0.9999), which is the same specimen (Part D).
- **Orientation (B):** all 16 segmentations in the package were re-oriented to match their images. Rony confirmed every one (Gate B, "all yes").
  - 14 nnU-Net masks: flip axis 1 (canonical: also reorder the TIFF axes).
  - 2 Otsu masks: axes reversed.
  - Label counts are unchanged, so no metric was recomputed.
- **Verification (C):** the four UNVERIFIED segmentations are now VERIFIED.
  - Canonical, Loess 5.85 µm and Loess 8.8 µm: fresh re-inference agrees on ≥ 99.9988 % of voxels.
  - Rehovot samp3 Otsu: identical voxel for voxel.
- **Vertisol identity (D):** canonical = **specimen B** (raw core `18.12.25 bnei_reem_samp_2.0`), voxel size 15.034357 µm. `DATA_CATALOG.md`, `README.md`, `docs/HANDOFF_REPORT.md` flag 4 and the package READMEs are updated.
- **Lab data (E):** the lab data is in the package, under `07_lab_data_and_writeup/`.
- **Literature (F):** 8 PDFs are in `docs/literature/` locally. They are gitignored and not in the ZIP.
- **Package (G):** v2 is built next to v1 (stats below). The code archive is replaced by a `git archive` of this branch.
- **New problem found:** in the 8.8 µm Track E label-downsample, about 80 % of the POM voxels are the sample holder (Part B, #16). This may affect 8.8 µm Track E POM results. Nothing was changed.

## Part A: duplicate check (Gate A approved 2026-11-10)

Full tables: `logs/A1_file_level.json`, `logs/A2_array_level.json`, `logs/A3_content_level.md`. Heatmaps: `A3_matrices.png`.

**A1, file level (v1 `MANIFEST.csv`, 1,176 files).** There are 1,032 distinct sha256 values. All 108 repeated hashes are small files; no volume repeats.
- 42 are `psd_raw_data.csv` = `psd_table.csv` within the same PSD run folder (the pipeline writes the same content under both names).
- 66 are the same small file packaged in two places (`dataset.json`/`plans.json` per model, training logs, shared render scripts, `_yfix` JSONs identical to the files they were meant to fix). Three of them matter:
  - `canonical_napari_3d_screenshot.png` = `specB_napari_3d_screenshot.png`. Both are blank white images; they were removed from v2.
  - `extended_tortuosity.png` is the same file in the two 8.8 µm Track E runs (`…T164703_mishmar_hanegev_maoz_2_8p8um_native`, `…T215639_mishmar_second_8p8um_label_downsample_15um`). Both are empty: `tortuosity_fd` failed on all three axes in both runs (a pyamg int32 argument error, in `diagnostics.json`), and neither was re-run. The tortuosity in the write-up comes from the 200³ subvolume run (`05_analysis_outputs/tortuosity/tortuosity_subvolumes_20261004/` in the package). v2 adds a one-line README to both run folders saying so.
  - The PNGs of the two Rehovot samp2 full-volume PSD runs (08-15 and 08-24) are identical: the same mask went through the same deterministic pipeline.
- One zero-byte file, `06_figures/selected_outputs/mishmar_hanegev2_slice_exports/_terminal_probe.txt`, was removed from v2.

**A2, array level (38 volumes).** Hashing dtype, shape and the C-contiguous bytes gives 38 distinct arrays: no two volume files hold identical data.

**A3, content level.**

| Pair | Result |
|---|---|
| specA vs specB images (the control) | r = −0.0120 |
| Rehovot 2 vs 3, and either vs specA or specB | r = 0.001–0.021 |
| Loess 8.8 vs 5.85 µm | r = 0.064 |
| canonical vs specB | n/c as stored (the TIFF is 652×650×650). With the TIFF axes reversed: **r = 0.9999** (known; Part D) |
| canonical vs specA, best of 48 transforms × offsets | r = −0.056 |
| any other image pair, best of 48 transforms × offsets | \|r\| < 0.07 |
| segmentation pairs with Dice > 0.9 | all explained: `less_reliable_solid_pores_GT` ⊂ `merged_GT` (0.994); canonical vs specB (0.988, same specimen); Rehovot i4 vs loess_i2 (0.970 / 0.958, same image, two models); Rehovot nnU-Net vs Otsu (0.29–0.40 as stored, 0.92–0.96 after reversing the Otsu axes, which was flag 1) |

## Part B: re-orientation (Gate B: Rony answered "all yes", 2026-11-10)

The transform was searched, not assumed: every signed axis permutation (48) with a matching shape was tried on stride-4 views. Each candidate was scored two ways:
- (a) the point-biserial r between image intensity and the pore mask (pores are dark, so the most negative r wins);
- (b) Dice against a fresh global-Otsu mask of the image.

Both scores picked the same transform for all 16 files. The scores below are at full resolution. The PNGs are `B3_<name>.png`: rows are the three axes; columns are raw | before | after | 150 px zooms. Every aligned copy was re-read and has the same per-label voxel counts as the original.

| # | Specimen | File | Transform | r before → after | Otsu-Dice before → after | Rony |
|---|---|---|---|---|---|---|
| 1 | Cu011_samp_2 | `segmentation` | flip axis 1 | −0.026 → −0.864 | 0.27 → 0.91 | yes |
| 2 | Rehovot samp2 | `segmentation_nnunet_bnei_reem_i4` | flip axis 1 | −0.013 → −0.830 | 0.30 → 0.92 | yes |
| 3 | Rehovot samp2 | `segmentation_nnunet_loess_i2` | flip axis 1 | −0.014 → −0.836 | 0.30 → 0.93 | yes |
| 4 | Rehovot samp2 | `segmentation_otsu.npy` | axes (2,1,0) | −0.023 → −0.846 | 0.32 → 0.9995 | yes |
| 5 | Rehovot samp3 | `segmentation_nnunet_bnei_reem_i4` | flip axis 1 | −0.014 → −0.889 | 0.40 → 0.95 | yes |
| 6 | Rehovot samp3 | `segmentation_nnunet_loess_i2` | flip axis 1 | −0.014 → −0.894 | 0.41 → 0.96 | yes |
| 7 | Rehovot samp3 | `segmentation_otsu.npy` | axes (2,1,0) | −0.022 → −0.902 | 0.42 → 1.0000 | yes |
| 8 | Vertisol canonical | `segmentation` | axes (2,1,0) + flip axis 1 (stored 652×650×650, overlays the TIFF as read) | −0.019 → −0.857 | 0.21 → 0.87 | yes |
| 9 | Vertisol specA | `segmentation` | flip axis 1 | −0.013 → −0.782 | 0.13 → 0.75 | yes |
| 10 | Vertisol specB | `segmentation` | flip axis 1 | −0.019 → −0.859 | 0.21 → 0.87 | yes |
| 11 | Loess 5.85 µm | `segmentation` | flip axis 1 | −0.013 → −0.849 | 0.29 → 0.90 | yes |
| 12 | Loess 5.85 µm | `segmentation_15um_pom` | flip axis 1 | −0.014 → −0.841 | 0.28 → 0.89 | yes |
| 13 | Loess 5.85 µm | `segmentation_15um_trackE` | flip axis 1 | −0.014 → −0.811 | 0.28 → 0.87 | yes |
| 14 | Loess 8.8 µm | `segmentation` | flip axis 1 | −0.021 → −0.817 | 0.26 → 0.87 | yes |
| 15 | Loess 8.8 µm | `segmentation_15um_pom` | flip axis 1 | −0.020 → −0.811 | 0.25 → 0.85 | yes |
| 16 | Loess 8.8 µm | `segmentation_15um_trackE` | flip axis 1 | +0.093 → −0.401 | 0.21 → 0.54 | yes (see below) |

How each mask was matched to an image:
- #12 and #15 were scored against the 1000³ image, block-averaged with the same partition the downsampling code used.
- #13 and #16 were scored against the ROI-expanded model inputs (1216³ and 1614³; the packaged 1000³ image does not cover them).

**Swap (B4).** The aligned copies took the original filenames in the package. The pre-flip originals are in `E:\PROJECTS\Yael_Mishael\Rony\handoff\_pre_flip_backup_2026-11\`; the log is `logs/B4_swap_log.json`. The volume READMEs now say "Segmentations were re-oriented to their images on 2026-11-10 (transform: …). The copies on the share are still in the original orientation." They also give the inverse transform. For the Otsu masks they add the axis mapping for per-axis results computed on the old file (old axis 0 = new axis 2, old 1 = new 1, old 2 = new 0).

**dtype check (before the v2 build, 2026-11-14).** All 16 re-oriented files have the same dtype as their originals: uint8 in the NIfTI header and in the array, and bool for the two `.npy` files. Shape (up to axis order), voxel size, scl_slope/inter and per-label voxel counts are also the same (`logs/G4_dtype_check.json`). The 14 NIfTI files grew from 0.36 to 0.53 GB, because nibabel's gzip compresses the new axis order less well. The package as a whole went from 16.70 to 16.88 GB of content.

**#16: the sample holder is labelled as POM.** The flip is clearly correct (the runner-up scores r = +0.02, and the pores follow the dark voxels), but the score is weak because the 1614³ crop includes the sample holder.
- About 80 % of that mask's POM voxels lie at or beyond the core edge. Inside the core, POM is about 1.2–4 %, like the other masks.
- So its 7.86 % POM, and the "tripled POM fraction" noted for the 8.8 µm ROI expansion, are mostly holder.
- #13 (the 5.85 µm equivalent) does not show this.
- Nothing was changed. Any 8.8 µm Track E POM result should be read with this in mind.

**Where the flip comes from (likely).** Everything that never went through full-volume inference is aligned with its image: the annotations, `labelsTr` and nnU-Net's own validation predictions. Only full-volume predictions are flipped on axis 1, and the fresh re-inference in Part C, run through the same chunk-and-concatenate route (`2_preprocessing/nnunet_dataset/preprocessing_nnUNet_predict_split.py` → `nnUNetPredictor` → `4_inference/postprocessing_nnUNet_predict_concatenate.py`), reproduces the flip exactly. The `_yfix` JSONs in the package suggest a y-axis issue was known in that route. The concatenate step was not debugged here.

**Otsu masks.** `10.5\<name>.tif` is the packaged `image_preprocessed.nii.gz` with its axes reversed. Thresholding the TIFF in its own axis order reproduces the share copy bit for bit, which explains the reversed axes.

## Part C: verification of the four UNVERIFIED segmentations (Gate C approved 2026-11-10)

**Route.** It was taken from the original drivers (`4_inference/run_inference.py`, the packaged pipeline logs):
- `nnUNetPredictor` on the original pre-split chunk folders: tile step 0.5, Gaussian weighting, no mirroring/TTA, fold 0, `checkpoint_final.pth`, `perform_everything_on_device=False`;
- then `4_inference/postprocessing_nnUNet_predict_concatenate.py`, whose content is unchanged since 2026-05-24.

The Python API was used rather than the CLI, as in the drivers; the equivalent `nnUNetv2_predict` line is in each log.

**Where it ran.** Outputs went only to new folders, `E:\PROJECTS\Yael_Mishael\Rony\handoff\_verification_2026-11\<run>\`, on an RTX A6000 with nnU-Net 2.4.2 and torch 2.11.

**Inputs.**
- The checkpoints on the share are byte-identical to `03_models` in the package: i4 `9543f9ac…` (2026-07-05 19:41) and loess_i2 `c712022e…` (2026-07-15 15:19).
- Each run's `inference_log.{txt,json}` records the command, times, GPU, checkpoint sha256 and mtime, every input sha256, the nnU-Net version and the trainer-file hash. That is the record that was missing.

| Volume | Voxel agreement | Dice pore (5) | Dice POM (2) | Dice stones (1) | Pore / POM %, packaged vs fresh | Status (approved) |
|---|---|---|---|---|---|---|
| `bnei_reem_fresh_bnei_reem_i4` (canonical) | 99.9988 % (3,284 differ) | 0.99998 | 0.99992 | 0.99994 | 21.6364 / 0.8189 vs 21.6364 / 0.8189 | VERIFIED (re-inference match, 2026-11-10) |
| `mishmar_hanegev_maoz_3_5p85um` | 99.9992 % (8,424) | 0.99999 | 0.99997 | 0.99995 | 27.0385 / 1.6147 vs 27.0385 / 1.6147 | VERIFIED (re-inference match, 2026-11-10) |
| `mishmar_hanegev_maoz_2_8p8um` | 99.9991 % (8,791) | 0.99998 | 0.99997 | 0.99994 | 22.9840 / 1.6431 vs 22.9841 / 1.6431 | VERIFIED (re-inference match, 2026-11-10) |
| Rehovot samp3 Otsu mask | 100 % (0 differ) | 1.0 | n/a | n/a | 40.8479 vs 40.8479 (threshold 0.43167716) | VERIFIED (re-computation match, 2026-11-10) |

- **The differences:** the largest class-fraction difference is 0.00001 percentage points (the guide allows 0.05). The differing voxels are scattered single pixels at class boundaries (GPU floating-point non-determinism); see `C5_<volume>.png`.
- **samp2 Otsu:** the samp2 Otsu mask, already VERIFIED at hand-off, was recomputed as well and is identical (`logs/C4_otsu.json`).
- **C6 (after approval):** the four statuses were changed in the package READMEs, and the logs were copied into each volume's `provenance/` as `inference_log_verification_2026-11-10.{txt,json}` or `otsu_verification_2026-11-10.{txt,json}`. The fresh predictions stay in `_verification_2026-11\`, outside the ZIP.

## Part D: which Bnei Re'em scan is the canonical volume (Gate D approved 2026-11-14)

Evidence: `D_canonical_identity.png`, `logs/D1_D3_provenance.json`, `logs/D2b_raw_projections.json`, `logs/D4_crop_match.json`.

| # | Check | Evidence | Pass |
|---|---|---|---|
| D1 | samp_2.0 `_Rec` predates 2026-04-20 | `18.12.25 bnei_reem_samp_2.0\bnei_reem_highkV_cu011_samp_2.0_Rec\`: 804 slices, mtime 2025-12-23 09:29:57 → 09:31:33 | ✅ |
| D1 | its log names samp_2.0 at 15.034357 µm | `Data Directory=\\HIVE3065\Yael_Mishael\Rony\18.12.25 bnei_reem_samp_2.0` · `Filename Prefix=bnei_reem_highkV_cu011_samp_2.0` · `Image Pixel Size (um)=15.034357` · `Study Date and Time=18 Dec 2025  15h:20m:12s`. Reconstruction date/time: **NOT FOUND** (not in the NRecon log or the TIFF tags; only the slice mtimes) | ✅ |
| D2 | samp_2 reconstructions | samp_2 folder: 804 slices dated 2026-08-25 16:11–16:12. `C:\Users\rony.schwartz\Desktop\new_rec`: 804 slices dated 2026-08-25 17:16–17:18. Both logs: `…\18.12.25 bnei_reem_samp_2`, 15.000149 µm, Study 13h:34m:02s. The December `samp_2_Rec\` holds only 2 preview images | context |
| D2b | misfiling check on the raw scans | Two separate scans, back to back: samp_2 projections 12:11:35 → 13:36:02, samp_2.0 13:57:45 → 15:22:12. In SkyScan logs "Study Date and Time" is the end of the scan. All 5 sampled projections differ between the folders | context |
| D3 | older candidate source files | Nothing in `10.5\` or `nnUNet_resources\bnei_reem\` (125 files) is older than 2026-04-20. The oldest is `nlm_volume.tif` itself (2026-04-20 16:00) | context |
| D4 | r > 0.99 vs specB | best of 48 transforms × all offsets: axes (2,1,0), no flips, offset (0,0,0), **r = 0.999929** on 274,625,000 voxels. Next-best transform: 0.357 | ✅ |
| D4 | \|r\| < 0.2 vs specA | best of 48 transforms × all offsets: axes (1,2,0), flip axes 0 and 2, offset (69,155,206), **r = 0.140** at full resolution; highest \|r\| at 8× is 0.170 | ✅ |

**Verdict:** canonical = specimen B (raw core `18.12.25 bnei_reem_samp_2.0`). It was made in April 2026 from the December samp_2.0 reconstruction; no samp_2 reconstruction existed until August. The packaged scan logs agree: specB_unified comes from samp_2.0 (15.034357 µm) and specA_unified from samp_2 (15.000149 µm).

**D4 bug (fixed before the gate).** The first D4 run passed flips as lists of axis indices to a function that expects a boolean mask per axis, so 3 of the 8 flip combinations were never tried and the runner-up was a duplicate of the winner. The specB result did not change; the specA numbers above are from the corrected run. The flawed outputs are kept as `logs/D4_*_run1_flipbug.*`. B1, B2 and C3 pass boolean masks and were not affected.

**D5 (after approval).** Recorded in:
- `DATA_CATALOG.md`: ⚠ OPEN → RESOLVED, with the evidence. The original flag is kept below; the legacy block moved to Specimen B with 15.034357 µm; the 2026-08-29 voxel-size argument is marked withdrawn; change-log line.
- `README.md`: specimen table and Known-limitations bullet.
- `docs/HANDOFF_REPORT.md`: flag 4.
- The package READMEs for canonical, specB and the top level.

Wording: "Specimen B (raw core `18.12.25 bnei_reem_samp_2.0`), legacy processing (April 2026). Source of all Vertisol POM results. The 0.23 % voxel-size difference (15.000149 vs 15.034357 µm) is negligible for the reported metrics, which are not recomputed."

**Not changed.** The historical run records in the package still give 15.000149 µm for canonical. Examples: `psd_diag_20260802T104738_nlm_volume_fresh_bnei_reem_i4/` configs and block summaries, `connectivity_function/chi_r_bnei_reem_canonical_recheck.meta.json`, `connectivity_validation_summary.md`. They record what those runs used and were left unchanged.

## Part E: lab data

- **Check:** `lab_data_Schwartz_2026-11.zip` sha256 = `e8aa566aa304f31ea3c59d951420a2c12308c7e4e194e24efb92e4755c181b1e`, which matches. No `.sha256` file was next to it; the hash was checked against the value in the prompt. `testzip()` was clean.
- **In the package:** 13 files extracted into `07_lab_data_and_writeup/`: `README.md` (replaces the placeholder), `raw_workbooks/` (7 workbooks) and `quotients_and_stats/` (5 files). The placeholder README is in `_removed_from_v2_2026-11\07_lab_data_and_writeup\README_placeholder.md`.
- **Not included:** the write-up itself.

## Part F: literature (local only)

Eight PDFs were copied (not moved) into `docs/literature/` as `<key>.pdf`, with sha256 checked against the source. `git check-ignore` confirms all eight are ignored (`.gitignore:106`), and `REFERENCES.md` stays tracked. They are not in the ZIP.

| Key | Source |
|---|---|
| `Phalempin_2025` | `00_docs/literature/nnUNet4SoilCT_atricle.pdf` (old working tree) |
| `Vogel_Roth_2001` | `05_evaluation/psd/vogel_psd.pdf` (old working tree) |
| `Jarvis_2017`, `Renard_Allard_2013`, `Herring_2015`, `Odgaard_1997` | `05_evaluation/psd/pore_metrics_research/papers/1-s2.0-*.pdf` (an untracked leftover folder in the Documents clone) |
| `Vogel_1997` | same folder, `European J Soil Science - 2008 - VOGEL - …pdf`. The "2008" is Wiley's online date; the first page gives *EJSS* 48, 365–377 (1997), matching `REFERENCES.md` |
| `Ghanbarian_2013` | same folder, `Soil Science Soc of Amer J - 2013 - Ghanbarian - …pdf` |

No `literature_pdfs` ZIP was brought over.

**Public history.** The six papers are still there. They were committed on 2026-07-08 in `d7882f0`, moved in `d90e0bd` and deleted in `6ef2dd6` (the prompt said `d90e0bd` removed them; it only moved them). All three commits are on `origin/main`. This adds six files to the three that `HANDOFF_REPORT.md` flag 5 lists (Phalempin 2025, Vogel & Roth 2001, the Dor 2025 figure). History was not rewritten; that is Rony's decision.

## Part G: package v2 (Gate G approved 2026-11-14, option 1)

Compared with v1's `MANIFEST.csv` by sha256 (`logs/G3_diff_vs_v1.json`, written before the code-archive swap and the G2b path corrections):

| | Count | What |
|---|---|---|
| Changed | 33 | the 16 re-oriented segmentations (B4) and 17 READMEs (C6 statuses, D5 identity, lab-data rows, screenshot notes, repo paths) |
| Added | 22 | 8 verification logs (C6), 2 one-line tortuosity READMEs (Gate A), 12 lab-data files (E) |
| Removed | 3 | the 2 blank napari screenshots and the zero-byte `_terminal_probe.txt` (Gate A) |

**Repo paths.** The package READMEs now cite the 2026-11 layout (`archive/PATH_MAP_2026-11.csv`): 45 backticked paths, plus hand wording where a folder was split or a file now exists only in git history (`logs/G2_log.json`). A second check confirmed that every path written in backticks, including those inside command lines, exists in the package or in this branch's tree. It corrected 12 more citations (`logs/G2b_log.json`, `logs/G2c_log.json`):
- The tortuosity READMEs had pointed to `05_analysis_outputs/tortuosity_subvolumes_20261004/`; the package folder is `05_analysis_outputs/tortuosity/tortuosity_subvolumes_20261004/`.
- `run_configs/*.yaml` now points to the two kept configs.
- `extract_subvolumes.py` now points to its PR #4 location.
- The two `full_volume_batch` logs are marked as lab-computer-only; they were never in git.
- In the "run a model" commands: the split, concatenate and `run_psd_diagnostics.py` paths.

Historical reports copied into the package (files not named `README.md`) keep their original paths.

**Code archive.** `04_code/nnUNet4SoilXrayCT_198c5b5.zip` (old layout) was replaced by a `git archive` of this branch at the commit that added this report, so every path the READMEs cite exists in the ZIP and on GitHub. The old archive is in `_removed_from_v2_2026-11\04_code\`. `04_code/README.md` and the top-level package README name the commit.

**Kept outside the ZIP, nothing deleted:**
- `_pre_flip_backup_2026-11\`: the 16 pre-flip segmentations and the READMEs before B4.
- `_pre_C6_backup_2026-11\`, `_pre_D5_backup_2026-11\`, `_pre_G_backup_2026-11\`, `_pre_G2b_backup_2026-11\`, `_pre_G2c_backup_2026-11\`, `_pre_H_backup_2026-11\`: README versions before each step.
- `_removed_from_v2_2026-11\`: files that are not in v2.
- `_verification_2026-11\`: the fresh predictions from Part C.

**v2 ZIP (built 2026-11-14, `logs/G6_log.json`):**

| | |
|---|---|
| File | `E:\PROJECTS\Yael_Mishael\Rony\handoff\Schwartz_soil_uCT_handoff_2026-11_v2.zip` (v1 kept next to it) |
| Size | 16,099,070,658 bytes (16.1 GB); content 16,907,947,743 bytes |
| Files | 1,195 + `MANIFEST.csv` (v1: 1,176 + `MANIFEST.csv`) |
| sha256 | `4a747fbfed8cc372a27f3f823329b23cab0214daea8f18d4f79545dba845c26c` (also in `….zip.sha256`) |
| Code archive inside | `04_code/nnUNet4SoilXrayCT_a01686e.zip`: `git archive` of commit **`a01686ea9852742328a9fec07854d1ba7f5489ae`** (branch `handoff/2026-11-followup`; https://github.com/agrorony/nnUNet4SoilXrayCT/tree/a01686ea9852742328a9fec07854d1ba7f5489ae); 231,042,331 bytes, 871 files, sha256 `665d64041772955e6e52a8309ac9abeff7534759891cdc95b63d3254c3619cf0` (`logs/G5_log.json`) |
| Compared with v1 (final `MANIFEST.csv`) | 1,138 unchanged, 34 changed, 23 added, 4 removed. These are the G3 counts above plus the code-archive swap: one added (the new archive), one removed (the 198c5b5 archive) and one changed (`04_code/README.md`) |
| Checks | `testzip()` → None. The ZIP's file list equals `MANIFEST.csv`. All 23 READMEs, 5 random files (seed 20261114) and `MANIFEST.csv` were re-extracted and hashed: 29/29 match |

`MANIFEST.csv` was regenerated. Unchanged files keep v1's `source`; changed and added files carry a follow-up note. v1's manifest is in `_pre_H_backup_2026-11\MANIFEST_v1.csv`.

## NOT FOUND

- The reconstruction date/time of the samp_2.0 `_Rec`. NRecon logs have no date in `[Reconstruction]`, and the TIFFs have no DateTime tag; only the file mtimes exist.
- Canonical's crop position, normalisation mode and NLM σ/h. Its raw reconstruction is now identified (samp_2.0 `_Rec`), but there is no preprocessing log.
- The `.sha256` file for the lab-data ZIP; the hash was checked against the prompt's value.
- A `literature_pdfs` ZIP.
- The write-up.
- Everything else in `HANDOFF_REPORT.md` § NOT FOUND, except "the canonical volume's raw reconstruction" (now found) and the inference logs for canonical, Loess 5.85 and Loess 8.8 µm (now produced by re-inference).

## Changes to `docs/HANDOFF_REPORT.md`

- Disagreement 1 (`dataset_info.json` vs `dataset.json`) is marked as explained by the +1 annotation shift.
- Flags 1, 2, 3 and 4 have "resolved in the follow-up" notes.
