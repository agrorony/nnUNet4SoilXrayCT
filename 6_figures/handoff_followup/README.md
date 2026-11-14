# Hand-off follow-up scripts (2026-11)

These scripts produced `docs/HANDOFF_FOLLOWUP_2026-11.md` and the evidence in `docs/handoff_followup_2026-11/`.
- **Python:** `C:/Users/rony.schwartz/.conda/envs/venv-napari/python.exe`.
- **Usage:** each script's docstring gives its arguments.
- **Inputs:** most read the hand-off staging folder (`E:\PROJECTS\Yael_Mishael\Rony\handoff\Schwartz_soil_uCT_handoff_2026-11\`), so they only run on the lab computer.
- **Order:** the scripts that edit the package (b4, c6, d5, g2*) must run in this order, and each runs once: they refuse to overwrite an existing backup.

| Part | Script | What |
|---|---|---|
| A | `a1_a2_duplicates.py` | file-level (sha256) and array-level (dtype + shape + bytes) duplicate groups |
| A | `a3_content_matrices.py`, `a3_plot.py` | Pearson r between images and pore Dice between segmentations; `A3_matrices.png` |
| B | `b1_find_transforms.py` | 48 signed axis permutations per segmentation, scored by point-biserial r and Otsu Dice. The other scripts import its `apply_t`, so keep it in this folder |
| B | `b2_b3_align_and_plot.py` | writes `_aligned` copies (label counts asserted) and the `B3_*.png` overlays |
| B | `b4_swap.py`, `b4_update_readmes.py` | swaps the aligned copies into the package (originals backed up) and rewrites the orientation sections |
| C | `c2_verify_inference.py` | re-inference through the original chunk → predict → concatenate route, writing an inference log |
| C | `c3_c5_compare.py`, `c4_otsu_check.py`, `c4_plot.py` | packaged vs fresh: agreement, per-class Dice and fractions; Otsu recomputation; `C5_*.png` |
| C | `c6_update_status.py` | VERIFIED statuses in the package READMEs; logs copied into `provenance/`. Its replacement strings quote the v1 README text, including the old repo paths |
| D | `d1_d3_scan_provenance.py`, `d2b_raw_projection_check.py` | reconstruction slice dates and scan-log lines; raw-projection timing and content check |
| D | `d4_crop_match.py`, `d_plot.py` | FFT masked cross-correlation over 48 transforms × all offsets, refined at full resolution; `D_canonical_identity.png` |
| D | `d5_record_canonical_identity.py` | records canonical = specimen B in `DATA_CATALOG.md`, `README.md`, `docs/HANDOFF_REPORT.md` and the package READMEs |
| G | `g1_find_repo_paths.py`, `g2_prepare_v2.py`, `g2b_fix_paths.py`, `g2c_fix_command_paths.py` | Gate A removals and additions; repo paths in package READMEs updated to the 2026-11 layout |
| G | `g3_diff_vs_v1.py`, `g4_dtype_check.py` | staging vs the v1 manifest; dtype of re-oriented vs original segmentations |
| G | `g5_swap_code_archive.py`, `g6_build_v2_zip.py` | replace the code archive with a `git archive` of this branch; build and check the v2 ZIP |

Paths updated for the 2026-11 layout:
- `c2` calls `4_inference/postprocessing_nnUNet_predict_concatenate.py`.
- `b1` reads the ROI-expanded model inputs from `archive/5_analysis/pom_clustering_retired/pom_analysis_20260829_roi_expansion/pipeline_work/`. Those inputs are gitignored, so if they are missing it falls back to the pre-2026-11 path, where they still are on the lab computer.
