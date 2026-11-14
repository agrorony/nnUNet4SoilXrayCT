# v2 package change log (hand-off follow-up 2026-11)

Staging folder: `E:\PROJECTS\Yael_Mishael\Rony\handoff\Schwartz_soil_uCT_handoff_2026-11\`.
Nothing is deleted: removed files move to `E:\PROJECTS\Yael_Mishael\Rony\handoff\_removed_from_v2_2026-11\` (same relative paths).

## Approved at Gate A (Rony, 2026-11-10) — status: DONE 2026-11-14 (log `G2_log.json`)

| # | Change | Path |
|---|---|---|
| A-1 | remove (blank white napari screenshot, byte-identical to A-2) | `05_analysis_outputs/connectivity/Topology_Metrics_Aug2026/bnei_reem_specB_visual_evidence/canonical_napari_3d_screenshot.png` |
| A-2 | remove (blank white napari screenshot) | `05_analysis_outputs/connectivity/Topology_Metrics_Aug2026/bnei_reem_specB_visual_evidence/specB_napari_3d_screenshot.png` |
| A-3 | remove (zero-byte file) | `06_figures/selected_outputs/mishmar_hanegev2_slice_exports/_terminal_probe.txt` |
| A-4 | add one-line README: tortuosity failed (pyamg int32 error), not re-run; write-up tortuosity = 200³ subvolume run | `05_analysis_outputs/connectivity/Topology_Metrics_Aug2026/raw/psd_diag_20260829T164703_mishmar_hanegev_maoz_2_8p8um_native/README.md` |
| A-5 | same | `05_analysis_outputs/connectivity/Topology_Metrics_Aug2026/raw/psd_diag_20260902T215639_mishmar_second_8p8um_label_downsample_15um/README.md` |

## B4 — re-orientation swap (approved at Gate B, Rony: "all yes", 2026-11-10) — status: DONE

16 segmentations replaced by their re-oriented copies (same filenames); the pre-flip originals moved to
`E:\PROJECTS\Yael_Mishael\Rony\handoff\_pre_flip_backup_2026-11\<same relative path>` (sha256 checked before/after; log `B4_swap_log.json`).
READMEs changed (backups of the previous versions in the same backup folder): the 8 `01_volumes/*/README.md` and the top-level `README.md`
(orientation section, napari snippets, Files-table sha256/size/shape, Known-limitations bullet).
Canonical `segmentation.nii.gz` is now 652×650×650 (TIFF axis order); nibabel's gzip makes it 20.5 MB (was 11.9 MB), array content identical up to the transform.

## C6 — verification status (approved at Gate C, Rony: "approved", 2026-11-10) — status: DONE

The four UNVERIFIED items are now VERIFIED. Log `C6_log.json`; README backups (state after B4) in
`E:\PROJECTS\Yael_Mishael\Rony\handoff\_pre_C6_backup_2026-11\<same relative path>`.

| Volume | New status | Basis | Added to `provenance/` |
|---|---|---|---|
| `bnei_reem_fresh_bnei_reem_i4` (canonical) | VERIFIED (re-inference match, 2026-11-10) | 99.9988 % voxels agree (3,284 differ); Dice pore/POM/stones 0.99998/0.99992/0.99994 | `inference_log_verification_2026-11-10.txt`, `.json` |
| `mishmar_hanegev_maoz_3_5p85um` | VERIFIED (re-inference match, 2026-11-10) | 99.9992 % (8,424 differ); 0.99999/0.99997/0.99995 | same two files |
| `mishmar_hanegev_maoz_2_8p8um` | VERIFIED (re-inference match, 2026-11-10) | 99.9991 % (8,791 differ); 0.99998/0.99997/0.99994 | same two files |
| `Rehovot_samp3_highkV_Cu0.11_15um` Otsu mask | VERIFIED (re-computation match, 2026-11-10) | fresh `threshold_otsu` mask identical (0 voxels differ, threshold 0.43167716); timestamp oddity kept as a note | `otsu_verification_2026-11-10.json`, `.txt` |

READMEs edited: the 4 volume READMEs (status line, Known-issues bullet; samp3 also its Segmentation bullet; 5.85 µm also the
"which checkpoint" sentence, now answered: `checkpoint_final.pth`) and the top-level `README.md` (Specimens table, definition paragraph).
The fresh predictions stay in `E:\PROJECTS\Yael_Mishael\Rony\handoff\_verification_2026-11\` and are **not** in the ZIP.

## D5 — canonical = specimen B (approved at Gate D, Rony, 2026-11-14) — status: DONE

Package READMEs edited (backups of the previous versions in `E:\PROJECTS\Yael_Mishael\Rony\handoff\_pre_D5_backup_2026-11\`; log `D5_log.json`):
`01_volumes/bnei_reem_fresh_bnei_reem_i4/README.md` (Specimen, Scan: raw reconstruction = specimen B's `_Rec`, voxel size 15.034357 µm, Known issues),
`01_volumes/bnei_reem_specB_unified/README.md` (Known-issues bullet), top-level `README.md` (Specimens table row: specimen B, 15.034357; Known-limitations bullet).
Wording: "Specimen B (raw core `18.12.25 bnei_reem_samp_2.0`), legacy processing (April 2026). Source of all Vertisol POM results." plus
"The 0.23 % voxel-size difference (15.000149 vs 15.034357 µm) is negligible for the reported metrics, which are not recomputed."
Historical run reports under `05_analysis_outputs/` still say 15.000149 µm for canonical; they are records of those runs and are left unchanged.
Repo (branch `handoff/2026-11-followup`): `DATA_CATALOG.md`, `README.md`, `docs/HANDOFF_REPORT.md` flag 4.

## E — lab data (Part E) — status: DONE 2026-11-14

`E:\PROJECTS\Yael_Mishael\Rony\handoff\lab_data_Schwartz_2026-11.zip` sha256 = e8aa566aa304f31ea3c59d951420a2c12308c7e4e194e24efb92e4755c181b1e (matches the expected value; no `.sha256` file was next to it), `testzip()` clean.
Extracted into `07_lab_data_and_writeup/`: `README.md` (replaces the placeholder, which moved to `_removed_from_v2_2026-11\07_lab_data_and_writeup\README_placeholder.md`),
`raw_workbooks/` (7 workbooks), `quotients_and_stats/` (5 files). The write-up itself is not included.

## G prep — status: DONE 2026-11-14 (log `G2_log.json`, README backups in `_pre_G_backup_2026-11\`)

- Gate A items A-1…A-5 applied (3 files moved to `_removed_from_v2_2026-11\`, 2 one-line READMEs added); the specB visual-evidence README notes the screenshot removal.
- Top-level README: `07_lab_data_and_writeup/` row and "where things are" row updated; `RESOURCES.md` → `docs/RESOURCES.md` + `docs/literature/REFERENCES.md`.
- Repo paths in 15 package READMEs moved to the 2026-11 layout (`archive/PATH_MAP_2026-11.csv`): 45 backticked paths + 9 hand-written directory/removed-file cases.
  Historical reports copied into the package (not named README.md) keep their original paths. Inventory before/after: `G1_repo_path_citations.json`, `G1_after_G2.json`.
- Full diff against v1's MANIFEST: `G3_diff_vs_v1.json` (33 changed, 22 added, 3 removed; 1,195 files + MANIFEST.csv).
