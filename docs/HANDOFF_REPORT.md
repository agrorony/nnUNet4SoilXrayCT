# Hand-off report (2026-11-03)

> **Paths:** the repository was reorganised on 2026-11-10. Paths below are from before that; `archive/PATH_MAP_2026-11.csv` maps old paths to new ones.

Packaging and documentation only: no retraining, no new inference, no new metrics. Nothing outside the repo working tree and `E:\PROJECTS\Yael_Mishael\Rony\handoff\` was written; everything was copied, never moved.

## Bottom line

- **PR:** https://github.com/agrorony/nnUNet4SoilXrayCT/pull/1 ("Hand-off tidy-up (2026-11)", `handoff/2026-11-cleanup` → `main`, not merged). Code archived at `198c5b5dc3da729954e9a5efc20aec6d208d3bad`. This report was committed on top of that afterwards.
- **ZIP:** `E:\PROJECTS\Yael_Mishael\Rony\handoff\Schwartz_soil_uCT_handoff_2026-11.zip`, 15,893,041,194 bytes (15.9 GB; 1,176 files), sha256 `a7b67ae0e33c8f7e659f68d7d911a0a6b6fbd57bb53ade71ea446d75f2c2380b` (also in `….zip.sha256`). One archive (16.7 GB of content < 25 GB). `testzip()` → None; ZIP and `MANIFEST.csv` list the same files; 3 random files plus all 21 READMEs re-extracted, 24/24 sha256 match. Every copied file was also hash-checked against its source at copy time.
- **Verification:** 4 of 8 volumes VERIFIED (Vertisol A, Vertisol B, `Cu011_samp_2`, Rehovot samp2); 3 UNVERIFIED (Vertisol "canonical", Loess 5.85 µm, Loess 8.8 µm: no inference log); Rehovot samp3: nnU-Net VERIFIED, Otsu mask UNVERIFIED. 0 MISMATCH.
- `for_rony\`: 26 fig4 `psd_table.csv` (24 = 8 per soil, plus an early `bnei_reem_sub_00` test and the Rehovot full-volume run) and 14 `chi_r_*.csv`.

## Step 0

| Check | Result |
|---|---|
| `git status` | clean (the untracked render folders in the session snapshot were already committed in `2efa4c8`). `git diff --ignore-all-space`: empty. No "uncommitted local changes" commit was needed |
| `main` vs `origin/main` | at first `main` was 1 ahead (`2efa4c8`, dated 2026-11-03 14:31). It was pushed from this machine at 14:50 (reflog "update by push"), so `main` = `origin/main` = `2efa4c8` when the branch was cut |
| Remote / fork parent | `origin` = `https://github.com/agrorony/nnUNet4SoilXrayCT.git`; public fork of `MaxPhal/nnUNet4SoilXrayCT` (GitHub API) |
| `gh` | not installed. Push over HTTPS worked (Windows credential manager); the PR was opened through the GitHub REST API with that stored credential |
| Git lock / line-ending problems | none hit. The "~350 files modified by line endings" did not reproduce; renormalising touched 9 files |
| Disk (staging on E:) | E: 30,205 GB free (C: 133, D: 11,102, P: 431); package 16.7 GB |

Paths (all exist):

| Path | Status |
|---|---|
| `nnUNet_resources\multi_sample_fresh_bnei_reem_i4`, `\multi_sample_mishmar_hanegev_maoz_3_5p85um_loess_i2` | exists |
| `nnUNet_resources\bnei_reem_specA_unified`, `bnei_reem_specB_unified`, `bnei_reem_fresh_bnei_reem_i4` | exists |
| `nnUNet_resources\mishmar_hanegev_maoz_3_5p85um`, `mishmar_hanegev_maoz_2_8p8um`, `mishmar_hanegev_Cu011_samp_2_Rec_nlm` | exists |
| `nnUNet_resources\rehovot_inference_rehovot_samp_2`, `rehovot_inference_Rehovot_samp3_highkV_Cu0.11_15um` | exists |
| Raw: `18.12.25 bnei_reem_samp_2`, `18.12.25 bnei_reem_samp_2.0`, `29.3.26 mishmar_hanegev_samp_{1,2,3}`, `mishmar_hanegev_maoz\{3-16mm_diam_5.85um,2-16mm_diam_8.8um}`, `10.12.25_Rehovot_samp_2`, `_samp_3`, `_samp_3_clean`, `C:\Users\rony.schwartz\Desktop\new_rec` | exists |
| `remote_computer backup\10.5\`, `Topology_Metrics_Aug2026\` | exists |
| `handoff_inputs\` | **NOT FOUND** |

## Part A: repo

Commits on `handoff/2026-11-cleanup`: tidy (67 `git mv` renames; 2 scripts' output paths updated; `freetype.dll` and 2 napari logs untracked) → final-state notes → upstream README move (own commit, keeps `--follow` history) → new README → `.gitattributes` + renormalise (EOL only, verified with `--ignore-all-space`) → `.gitignore` → untrack third-party files → this report. Full move table: `00_docs/REPO_TIDY_2026-11.md`. Reorg records went to `00_docs/reorg_2026-07/` (the files are dated 2026-07, not 2026-08).

Public-repo checks: secret scan no hits; tracked files > 10 MB: two own render PNGs (13 MB, 16 MB), left tracked; third-party files untracked at the tip: `docs/literature/nnUNet4SoilCT_atricle.pdf`, `5_analysis/shared_code/vogel_psd.pdf`, `dor2025_fig1a_reference.png`. **All three remain in public history**; the Dor 2025 figure was pushed in `2efa4c8` today.

DATA_CATALOG fixes (each with evidence):
1. Loess model = folder `multi_sample_mishmar_hanegev_maoz_3_5p85um_loess_i2`, trainer `nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss`, `checkpoint_final.pth` (folder listing; `cu011_loess_i2_inference_log.txt`).
2. Rehovot metrics came from global-Otsu `.npy` masks (`config.json` of both Rehovot Track E runs: `.npy` input, `pore_label 1`).
3. NUL byte → "0" in `docs/missing_data_20261004_REPORT.md` (also in PROJECT_STATUS and local_asset_recovery_findings).
Already correct, not changed: Rehovot = 2 specimens; share restored 2026-10-04, nothing deleted.

## Per-specimen verification

| Specimen | Status | Reason |
|---|---|---|
| `bnei_reem_specA_unified` | VERIFIED | unified-pipeline log names i4 model + `checkpoint_final.pth`; 2026-09-07 > 2026-07-05; 15.1688 / 0.2403 % = catalog |
| `bnei_reem_specB_unified` | VERIFIED | same log; 21.6403 / 0.8170 % = catalog |
| `bnei_reem_fresh_bnei_reem_i4` | UNVERIFIED | no inference log; driver script, timestamp (07-06 > 07-05), byte-identical `plans.json` and 21.6364 / 0.8189 % all consistent. Image = `10.5\nlm_volume.tif`, r = 1.0000 against the model-input chunk |
| `mishmar_hanegev_maoz_3_5p85um` | UNVERIFIED | no inference log; timestamp (07-16 > 07-15), `plans.json`, 27.0385 / 1.6147 % = catalog. 15 µm masks: POM one = catalog 26.108 / 1.614; Track E one VERIFIED (ROI-expansion log) |
| `mishmar_hanegev_maoz_2_8p8um` | UNVERIFIED | no inference log; driver script, timestamp, `plans.json`; no catalog % (pore 22.984 % = Track E record). Track E 15 µm mask VERIFIED (20.343 / 7.859 %) |
| `Cu011_samp_2` | VERIFIED | inference log; 08-23 > 07-15; 26.38 / 0.120 % = catalog |
| `Rehovot_samp2…` | VERIFIED | Otsu mask = Track E input, 30.498 % = run record; nnU-Net references logged |
| `Rehovot_samp3…` | nnU-Net VERIFIED / Otsu UNVERIFIED | `.npy` dated 17:40, one hour after the 16:46 run that used it; content matches (40.848 %) |

Other checks made at hand-off (read-only): the canonical image TIFF equals its model-input chunk (r = 1.000); each `imagesTr` equals a slab of the packaged volume (Vertisol slices 206–304, Loess 667–764, r = 1.000); `labelsTr` per-class counts equal `fine_tuning_annotations.nii.gz` (i4) and the z 715–716 annotation file (loess_i2). Excluded from the package as retracted: the `bnei_reem_samp_2_0_recropped` / `_true_recon` run folders and χ(r) tables (30 files).

## NOT FOUND

Sampling dates (all specimens); the canonical volume's raw reconstruction, scan log, crop position, norm200 mode and NLM σ/h; scan logs for both external Loess scans (none exist); preprocessing logs (crop position, NLM σ/h, normalisation) for Loess 5.85/8.8 µm, `Cu011_samp_2` and both Rehovot volumes; inference logs for canonical, Loess 5.85 and 8.8 µm; the script that made the Rehovot Otsu masks; a catalog POM % for native Loess 8.8 µm; how the registry's `merged_GT.nii.gz` relates to the i4 training labels; a record of which corrected predictions were fed back per annotation round; `handoff_inputs\` and the write-up docx.

## Disagreements between documents (reported, not resolved)

1. `dataset_info.json` (annotation space: 6 = Pore) vs the deployed models' `dataset.json` (5 = Pore, 2 = POM). Consistent through `mask_to_nnUNet()`, but misleading; the README now explains it. **Explained (follow-up, 2026-11-14):** not a disagreement. nnU-Net maps annotation 0 (unlabelled) to the ignore label and shifts every other class down by one, so `dataset_info.json` (annotation space) is one higher than the predictions by design.
2. `docs/ct_scan_parameters_findings.md` says the ROI-expanded volumes were used only for the retired clustering, but the matched-resolution Track E runs (`psd_diag_20260902T*_label_downsample_15um` configs) and the 2026-10-04 tortuosity used the ROI-expanded label-downsamples.
3. `mishmar_hanegev_maoz_3_5p85um_scratch.yaml` lists the same annotation file as `…_loess_i2.yaml`, while the registry says loess_i2 used *new* 2-slice annotations (z 715–716). The YAMLs are flagged as reconstructed and unverified (`VERIFIED.md`).
4. `DATA_CATALOG.md` still points canonical's location at `Z:\Rony\…` (not mapped); the README gives the `E:`/UNC equivalents.

## Flags for Rony before sending the ZIP

1. **Segmentations are flipped on axis 1 relative to their images** (checked on one nnU-Net segmentation per volume, 7 files: r ≈ −0.8 only after flipping; identical affines). Otsu masks have reversed axes. Packaged unchanged; every README and napari snippet says so. Metrics are unaffected, but anyone overlaying image and labels must flip. **Resolved in the follow-up (2026-11-10):** all 16 segmentations in the package (including the 15 µm label-downsamples and both Otsu masks) were checked and re-oriented to their images in v2 of the ZIP; see `docs/HANDOFF_FOLLOWUP_2026-11.md`, Part B.
2. `07_lab_data_and_writeup/` is a placeholder: add the submitted write-up and the lab data (respiration, Cmic, quotients, Table 1) if Maoz should have them. The ZIP would then need rebuilding (`MANIFEST.csv` and the `.sha256` would change). **Resolved in the follow-up (2026-11-14):** the lab data is in v2 (`07_lab_data_and_writeup/`); the write-up itself is still not included.
3. Three volumes are UNVERIFIED (no inference log) and the Rehovot samp3 Otsu mask is UNVERIFIED (timestamp). The evidence is consistent; say so to Maoz rather than calling them verified. **Resolved in the follow-up (2026-11-10):** all four reproduced (re-inference ≥ 99.9988 % voxel agreement; Otsu mask identical) and are VERIFIED; see `docs/HANDOFF_FOLLOWUP_2026-11.md`, Part C.
4. Vertisol "canonical" specimen label is still unresolved; every Vertisol POM result depends on it. **Resolved in the follow-up (2026-11-14):** Specimen B (raw core `18.12.25 bnei_reem_samp_2.0`), legacy processing (April 2026). Source of all Vertisol POM results. See `docs/HANDOFF_FOLLOWUP_2026-11.md`, Part D.
5. Third-party files are still in the public repo history (incl. `dor2025_fig1a_reference.png`, pushed today). Removing them needs a history rewrite and force-push: your call.
6. A render README notes "HIVE3065 60-day retention applies" to share folders. If that covers `nnUNet_resources` or the raw scans, the ZIP may become the only copy of some files.
7. All NIfTI headers store a voxel size of 1 × 1 × 1. Physical sizes are in the READMEs only.
8. `merged_GT.nii.gz` (registry annotation) has a few hundred voxels with values 7 and 8, outside the label scheme.
9. The PR is not merged. After merging, `docs/HANDOFF_REPORT.md` is on `main`.
