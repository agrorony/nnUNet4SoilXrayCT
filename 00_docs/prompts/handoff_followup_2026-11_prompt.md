# Hand-off follow-up (2026-11): duplicates, flip, verification, Vertisol identity, lab data, rebuild the ZIP

For Claude Code (or Copilot) on the lab computer. It follows `00_docs/reports/HANDOFF_REPORT.md` (PR #1, merged 2026-11-10). Read that report first.

Rony is at the computer while this runs. He will approve each step in chat, and you wait for his reply at every **⏸ GATE**. Do not go past a gate without an explicit "approved" (or a per-item yes/no) from him.

## Rules

1. **Never change or delete source data.** This covers the share (`E:\PROJECTS\Yael_Mishael\Rony\`, `\\hive3065\Yael_Mishael\Rony\`), `nnUNet_resources\`, raw scan folders and `10.5\`. Work only in the hand-off staging folder the ZIP was built from (under `E:\PROJECTS\Yael_Mishael\Rony\handoff\`; `MANIFEST.csv` lists it), and in new folders this prompt names.
2. **Write new files and never overwrite an original in place.** The only exception is the swap in B5, which happens after Rony approves, and the originals move to a backup folder first.
3. **How to show evidence.** Draw static PNGs with matplotlib, save them to `E:\PROJECTS\Yael_Mishael\Rony\handoff\_evidence_followup_2026-11\`, and open each one on screen (`start "" "<png>"`). Then list them in chat with their numbers. Where this prompt says so, also open a live napari window (start it with `subprocess.Popen` so you can keep waiting for Rony's reply). Automated napari screenshots came out blank in an earlier run (no interactive desktop), so never rely on a napari screenshot. Ask Rony whether the window appeared, and use the PNGs if it did not.
4. Python: `C:/Users/rony.schwartz/.conda/envs/venv-napari/python.exe`. Save every script you write under `07_utilities/scripts/handoff_followup/` in the repo.
5. **The repo is public.** No volumes, checkpoints, ZIPs or third-party PDFs go into git. Small evidence PNGs (under 2 MB each) and scripts are fine.
6. **Git.** If a git command fails with a lock or permission error, retry once after 30 s. If it fails again, write the remaining commands to `GIT_COMMANDS_FOR_RONY.md` and carry on.
7. **Label convention:** pore = 5 and POM = 2 in nnU-Net predictions. `dataset_info.json` is the annotation space, where every class is one higher, because nnU-Net maps annotation 0 (unlabelled) to the ignore label and shifts the rest down by one. That is expected behaviour, not a disagreement.

## Part A: duplicate check (read-only, do this first)

The hand-off hash checks compared each copy with its own source. Nothing checked whether two files in the package hold the same data. Check that now:

- **A1 (file level).** Group `MANIFEST.csv` by sha256. List every group with more than one path, and every zero-byte file.
- **A2 (array level).** Load every volume file in the package: images and segmentations, `.nii.gz`, `.tif`, `.npy`. For each, compute sha256 over `dtype + shape + C-contiguous array bytes`. This ignores headers and compression. Group identical arrays.
- **A3 (content level).** For every pair of *image* volumes with the same shape, compute Pearson r on the z-scored arrays (stride 2 is fine). Do the same for every pair of *segmentations* with the same shape, using pore Dice. Report full matrices and mark pairs with different shapes "n/c".
  - Expected values: `bnei_reem_fresh_bnei_reem_i4` (canonical) vs `bnei_reem_specB_unified` should give r ≈ 0.9999. This is known; see Part D.
  - The genuine control is specA vs specB, at r ≈ −0.01.
  - Any other pair above r = 0.9 is a new duplicate.
- **⏸ GATE A.** Post the tables. If anything beyond the known canonical/specB pair is a duplicate, stop and ask Rony what to do.

## Part B: flip every segmentation to its image's orientation

The hand-off found segmentations flipped on axis 1 relative to their images, and Otsu masks with reversed axes. It checked only one segmentation per volume. Now check and fix **every** segmentation in the package, including the ~15 µm label-downsamples and both Rehovot Otsu masks.

- **B1 (find the transform; don't assume it).** Pair each segmentation with its image. If no packaged image has the mask's shape (e.g. a 15 µm label-downsample of the 5.85 µm scan), block-average the image to the mask's shape.
  - Try every signed axis permutation (48) that gives a matching shape, on stride-4 views.
  - Score each candidate in two independent ways:
    - (a) Point-biserial r between image intensity and the pore mask (pores are dark, so the correct transform gives the most negative r).
    - (b) Dice between the transformed pore mask and a fresh global-Otsu mask of the image (dark = pore).
  - Pick the transform that wins on both. If the two scores disagree, flag that segmentation and do not fix it.
  - Recompute both scores at full resolution for the identity transform and for the chosen one.
- **B2 (write aligned copies).** Save `<name>_aligned.<ext>` next to each original, with the same dtype. For NIfTI, copy the image's affine and header.
  - Assert that the set of label values and the voxel count of every label are unchanged. A flip or transpose only reorders voxels, so the pore and POM fractions must be identical.
- **B3 (evidence: one PNG per segmentation).**
  - Rows: axes 0, 1 and 2.
  - Columns:
    - raw slice;
    - raw slice with pore (red) and POM (green) outlines **before** the fix;
    - the same **after** the fix;
    - a 150 × 150 px zoom of the after panel, at the mid-slice and at the 25 % and 75 % slices.
  - Title: transform found, r before/after, Otsu-Dice before/after, "label counts identical: yes/no".
  - Also open a napari window with the image plus the aligned labels for any volume Rony asks to see.
- **⏸ GATE B.** Open all the PNGs and post a numbered list: specimen, file, transform, r before→after, Dice before→after. Ask Rony: "For each number, is it aligned? (yes/no)". Record his answer per file. Investigate any "no" before continuing. Fix only the files he approved.
- **B4 (swap in the package, approved files only).**
  - Move the pre-flip originals to `handoff\_pre_flip_backup_2026-11\`, outside the ZIP.
  - Rename the aligned copies to the original filenames so the README paths still hold.
  - In every package README and napari snippet, remove the "flip axis 1" instructions. Add instead: "Segmentations were re-oriented to their images on <date> (transform: …). The copies on the share are still in the original orientation."
  - For the Rehovot Otsu masks (a transpose), note that any per-axis result computed on the old mask (e.g. tortuosity per axis) refers to the old mask's axis order, and give the mapping.
  - Metrics are not recomputed: a flip or transpose doesn't change them.

## Part C: verify the four UNVERIFIED segmentations

These have no inference log, so it is not proven that they came from the claimed checkpoint (the project's known stale-output risk):

- `bnei_reem_fresh_bnei_reem_i4` (canonical)
- `mishmar_hanegev_maoz_3_5p85um`
- `mishmar_hanegev_maoz_2_8p8um`
- the Rehovot samp3 Otsu mask

The test is to reproduce each segmentation and compare:

- **C1.** For each nnU-Net volume, identify the exact model input (`*_0000.nii.gz` under its `nnUNet_resources\<run>\` folder) and the claimed model: model folder, `3d_fullres`, fold 0, `checkpoint_final.pth`.
  - Record the checkpoint's sha256 and mtime and the input's sha256.
  - Find out how the original was run (whole volume, or chunks followed by `inference_concatenated`) from the drivers in `04_inference/`, and use the same route. If the route can't be established, run on the whole volume and say so.
- **C2.** Run `nnUNetv2_predict` into a **new** folder, `E:\PROJECTS\Yael_Mishael\Rony\handoff\_verification_2026-11\<run>\`, and never into an existing output folder.
  - Write an inference log there: command line, start/end time, GPU, checkpoint path + sha256 + mtime, input sha256, nnU-Net version. This log is the record that was missing.
  - Trainers come from `03_training/nnUNetTrainer_betterIgnoreSampling.py`, which must be on nnU-Net's trainer path.
- **C3.** Compare fresh and packaged predictions in the same orientation:
  - % voxel agreement;
  - per-class Dice for 5 (pore), 2 (POM) and 1 (stones);
  - per-class fractions.
  - Guide: pore Dice ≥ 0.99, POM Dice ≥ 0.95 and fractions within 0.05 percentage points mean "VERIFIED (re-inference match)". Anything less is a "MISMATCH". Report the numbers either way and let Rony decide.
- **C4 (Rehovot samp3 Otsu).** Recompute `skimage.filters.threshold_otsu` on the same image the Track E run used (pore = below threshold), then compare with the packaged mask after aligning axes. Identical, or Dice ≥ 0.99, means VERIFIED. Otherwise report the Dice.
- **C5 (evidence: one PNG per volume).**
  - Columns: raw, packaged segmentation, fresh segmentation, difference map (differing voxels in red).
  - Rows: three axes at the mid-slices.
  - Title: the C3 numbers.
  - Offer a napari window with four layers: image, packaged, fresh, diff.
- **⏸ GATE C.** Post the table and open the PNGs. Ask Rony to approve the status of each volume.
- **C6 (after approval).**
  - Change UNVERIFIED to "VERIFIED (re-inference match, <date>, log: …)" in the package READMEs and in a new section of the follow-up report.
  - Copy the new inference logs into the package; they are small text files.
  - Keep the fresh predictions in `_verification_2026-11\`, outside the ZIP. They would duplicate the packaged ones.
  - If the result is MISMATCH, change nothing and report.

## Part D: confirm which Bnei Re'em scan the "canonical" volume is

Rony recalls it is one of the two existing scans (`18.12.25 bnei_reem_samp_2` or `18.12.25 bnei_reem_samp_2.0`) but not which one. The evidence already in the repo points to **samp_2.0 (specimen B)**:

- Canonical's model input vs the samp_2.0 reconstruction: r = 0.999929 and pore Dice 0.988. Model-free Otsu Dice is 0.947 (expected 0.18 for different specimens). See `00_docs/reports/bnei_reem_specB_visual_evidence/part0d_otsu_and_identity_check.md`.
- Specimen A vs specimen B: r = −0.0119.
- Every reconstruction of the no-dot `samp_2` folder found anywhere is dated 2026-08-25 (part0d §1.1). Canonical's `10.5\nlm_volume.tif` is dated 2026-04-20. So no samp_2 reconstruction existed when canonical was made.
- The "15.000149 µm" `DATA_CATALOG.md` gives for canonical was used in August as evidence that canonical is samp_2. But no scan log for canonical's own reconstruction was ever found, and the NIfTI headers store 1 × 1 × 1. So that number is not evidence of where the pixels came from.

The one alternative left is that the samp_2.0 `_Rec` folder itself holds misfiled data. Close it:

- **D1.** In `E:\...\18.12.25 bnei_reem_samp_2.0\bnei_reem_highkV_cu011_samp_2.0_Rec\` (the full 804-slice reconstruction):
  - give the min/max mtime of the `*_rec########.tif` slices;
  - quote verbatim from the reconstruction log (`*_rec.log`) the lines `Data Directory`, `Filename Prefix`, `Image Pixel Size (um)`, `Study Date and Time` and the reconstruction date/time.
- **D2.** Do the same for every reconstruction under `18.12.25 bnei_reem_samp_2\` and `C:\Users\rony.schwartz\Desktop\new_rec\`.
- **D3.** List any file in `remote_computer backup\10.5\` or `C:\Users\rony.schwartz\Documents\nnUNet_resources\bnei_reem\` older than 2026-04-20 that could be canonical's pre-NLM crop.
- **D4.** Pearson r of canonical's model input against the packaged specB_unified input and against the packaged specA_unified input, at the best-matching common crop. Report the crop offsets found.
- **Decision rule:** canonical = specimen B if all of these hold. If any fails, change nothing and report.
  - The samp_2.0 `_Rec` slices predate 2026-04-20.
  - Its log names the samp_2.0 data directory with 15.034357 µm.
  - D4 gives r > 0.99 against specB and |r| < 0.2 against specA.
- **⏸ GATE D.** Post the evidence table and the verdict, and wait for Rony.
- **D5 (after approval).** Update:
  - `DATA_CATALOG.md` (repo copy): replace the "⚠ OPEN" flag with the resolution and its evidence; voxel size 15.034357 µm; a change-log line.
  - The `README.md` specimen table and its "Known limitations" bullet.
  - The package READMEs, and the HANDOFF_REPORT flag 4 (with a "resolved in the follow-up" note).

  Wording: "Specimen B (raw core `18.12.25 bnei_reem_samp_2.0`), legacy processing (April 2026). Source of all Vertisol POM results." Add one line saying the 0.23 % voxel-size difference (15.000149 vs 15.034357 µm) is negligible for the reported metrics, which are not recomputed.

## Part E: lab data

Rony will copy `lab_data_Schwartz_2026-11.zip` and its `.sha256` from his home computer into `E:\PROJECTS\Yael_Mishael\Rony\handoff\`.

- Check the sha256: `e8aa566aa304f31ea3c59d951420a2c12308c7e4e194e24efb92e4755c181b1e`.
- Extract it into the staging folder so that `07_lab_data_and_writeup\` holds `README.md`, `raw_workbooks\` (7 workbooks) and `quotients_and_stats\`. Replace the placeholder README.
- The write-up itself is not included unless Rony adds it.

## Part F: literature (local only, never in git or in the ZIP)

`00_docs/literature/` is gitignored except for `REFERENCES.md`, which lists every paper behind the analysis with a key per paper. Copy (don't move) the third-party PDFs that exist on this host into that folder, named `<key>.pdf`:

- `00_docs/literature/nnUNet4SoilCT_atricle.pdf` → `Phalempin_2025.pdf`
- `05_evaluation/psd/vogel_psd.pdf` → `Vogel_Roth_2001.pdf`
- The six papers that were in `analysis/pore_metrics_research/papers/` before the July reorg (find where they are now on disk):
  - `1-s2.0-S0016706116302737-main.pdf` → `Jarvis_2017.pdf`
  - `1-s2.0-S0309170811002223-main.pdf` → `Renard_Allard_2013.pdf`
  - `1-s2.0-S0309170815000317-main.pdf` → `Herring_2015.pdf`
  - `1-s2.0-S8756328297000070-main.pdf` → `Odgaard_1997.pdf`
  - the Vogel *European J Soil Science* file → `Vogel_1997.pdf`
  - the Ghanbarian *SSSAJ* file → `Ghanbarian_2013.pdf`
- If Rony brings a `literature_pdfs` ZIP from his home computer, extract it into the same folder.

Then run `git status` and `git check-ignore -v 00_docs/literature/*.pdf`: no PDF may be staged.

Note for the report: those six papers were committed on 2026-07-08 (`d7882f0`) and removed in `d90e0bd`. So they are also still in the public history, in addition to the three files the hand-off report lists. Do not rewrite history; Rony decides that separately.

## Part G: rebuild the ZIP

- **⏸ GATE G.** Summarise every change to the package (files replaced, added, moved to backup) and wait for approval.
- Build `Schwartz_soil_uCT_handoff_2026-11_v2.zip` next to v1. Keep v1 until Rony deletes it.
- Regenerate `MANIFEST.csv` and the `.sha256`, and run `testzip()`.
- Re-extract all READMEs plus 5 random files and compare hashes.
- Report the size, file count and sha256.

## Part H: repo, report, PR

- Branch `handoff/2026-11-followup` from an up-to-date `main`.
- Commit:
  - the scripts (`07_utilities/scripts/handoff_followup/`);
  - the evidence PNGs (`00_docs/reports/handoff_followup_2026-11/`);
  - the doc updates (`DATA_CATALOG.md`, `README.md`, `HANDOFF_REPORT.md` notes);
  - the report `00_docs/reports/HANDOFF_FOLLOWUP_2026-11.md`.
- The report should contain:
  - Part A tables;
  - per-segmentation transform, scores and Rony's answer;
  - Part C table and statuses;
  - Part D evidence and verdict;
  - lab-data and literature notes;
  - ZIP stats;
  - anything NOT FOUND.
- In `HANDOFF_REPORT.md`, mark "Disagreement 1" (`dataset_info.json` vs `dataset.json`) as explained by the +1 annotation shift (rule 7).
- Push and open a PR to `main`. Do not merge it.
