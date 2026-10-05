# Tortuosity on subvolumes — report (2026-10-04)

## 1. What was used
- **Function:** `tortuosity_diffusive()` in `05_evaluation/psd/psd_topology_metrics.py` (line ~402), the same one `run_psd_diagnostics.py` calls on whole volumes. It calls `porespy.simulations.tortuosity_fd(im=pore_mask, axis=ax)` with no other arguments. `--no-tortuosity` in `run_bnei_reem_unified_pipeline.py` just switches this off.
- **Versions/settings:** porespy 3.0.4, openpnm 3.6.3, pyamg 5.3.0. Default solver `PyamgRugeStubenSolver(tol=1e-8, maxiter=1000)`; tortuosity = ε_eff·D_AB/D_eff, 6-connected network, unit spacing. Non-percolating voxels are trimmed by porespy itself.
- **Input:** boolean pore mask, `labels == 5` (3-class NIfTI) or the stored boolean (Rehovot `.npy`, True = pore; Track E config used `pore_label 1`). **Axes** = numpy array axes 0/1/2 as loaded, no transpose, as in the original runs.
- **New code only:** `run_tortuosity_subvolumes.py` (cube extraction, 6-connectivity spanning pre-check, process pool with timeout, collection), `aggregate.py`, `rerun_timeouts.py`. The solver was not touched. The wrapper only captures the warning text and porespy's "Inlet/outlet rates don't match" log line per solve.
- **Inputs (same segmentation files as the Track E runs):**
  - Vertisol: `nnUNet_resources\bnei_reem_spec{A,B}_unified\inference_concatenated\*.nii.gz`
  - Loess: `...\pom_analysis_20260829_roi_expansion\pipeline_work\mishmar_native_5p85um\mishmar_native_5p85um_label_downsample.nii.gz`; `...\mishmar_second_8p8um\mishmar_second_8p8um_label_downsample.nii.gz`; `nnUNet_resources\mishmar_hanegev_Cu011_samp_2_Rec_nlm\inference_output_concat_loess_i2\*.nii.gz`
  - Sand: `10.5\rehovot_samp_2.npy`, `10.5\Rehovot_samp3_highkV_Cu0.11_15um.npy`
  - Every row of `tortuosity_subvolumes.csv` carries its input path and pore label.
- **Cubes:** non-overlapping tiling centred in each volume, then 8 picked by evenly spaced index (`linspace`) from the sorted tile list — not cherry-picked. 200³ (main) and 128³ (size check). The label volumes carry no padding marker; only `mishmar_2_8p8um` shows a circular container wall, so for it only tiles whose xy corners lie inside 0.9× the inscribed disk were eligible (16 tiles). The other volumes are centre crops/full cores with no visible outside region (checked on mid-slices).
- **Pilot:** 1 central 200³ cube, 3 axes, Vertisol A and Sand (Rehovot s2): 6/6 ok, median 58 s (53–140 s). Projected total ≈ 3 h serial → no reduction of cubes needed. Per-solve timeout = 3 × median ≈ 175 s.
- Timings: full runs used 8 parallel workers; median per-solve runtime 73 s (200³), 20 s (128³).

## 2. Did subvolumes fix convergence? Yes — on this scale the problem did not occur
`convergence_summary.csv` (original pass, rows = cube × axis):

| Soil | size | rows | ok | no_spanning_path | nonconvergence | timeout |
|---|---|---|---|---|---|---|
| Vertisol | 200 | 48 | 47 (98%) | 0 | 0 | 1 |
| Loess | 200 | 72 | 68 (94%) | 0 | 0 | 4 |
| Sand | 200 | 48 | 48 (100%) | 0 | 0 | 0 |
| Vertisol | 128 | 48 | 41 (85%) | 7 | 0 | 0 |
| Loess | 128 | 72 | 71 (99%) | 1 | 0 | 0 |
| Sand | 128 | 48 | 48 (100%) | 0 | 0 | 0 |

- **0 of 336 solves hit "Solver failed to converge"; no AMG library crash.** Hence the planned single retry with another solver setting was never triggered.
- The 5 `timeout`s at 175 s are not failures of the solver: all 5 were re-solved with a 900 s limit (`work/timeout_rerun_900s.csv`) and converged (177–323 s). The 175 s rule (3 × pilot median) was too tight for slower cubes. Headline numbers keep them as `timeout`; a "plus 900 s rerun" variant is in `tortuosity_summary.csv`.
- At 128³ the 8 `no_spanning_path` cases (mostly Vertisol) are genuine: no pore cluster joins the opposite faces — the only skips the pre-check made.
- Results were bit-identical between two full passes (I repeated the run once to add the flow-mismatch logging).
- **Caveat on "converged":** porespy logged "Inlet/outlet rates don't match" (rtol 1e-4 conservation check) for **55 of 323 ok solves** (flag `flow_mismatch`): Vertisol 33/47 at 200³ and 11/41 at 128³, Loess 5/68 and 1/71, Sand 5/48 and 0/48. The mismatches are small (≈0.03–0.5 % in the cases inspected), but they are concentrated in the highest-τ cubes (median τ 13.5 flagged vs 3.1 unflagged), i.e. the poorly connected, bottlenecked Vertisol cubes. These values are less reliable.

## 3. Tortuosity per soil (mean ± SE of specimen means; n = specimens)
200³ cubes (all `ok` values, original pass):

| Soil | n specimens | mean ± SE | specimen means |
|---|---|---|---|
| Vertisol | 2 | **18.2 ± 11.6** | A 29.7, B 6.6 |
| Loess | 3 | **3.77 ± 0.36** | 4.48, 3.35, 3.47 |
| Sand | 2 | **2.91 ± 0.62** | 3.53, 2.29 |

- Excluding flow-mismatch solves: Vertisol 8.0 ± 2.5 (only 14 cube×axis values left), Loess 3.19 ± 0.16, Sand 2.89 ± 0.57.
- 128³ cubes: Vertisol 12.9 ± 3.7, Loess 5.14 ± 1.17 (driven by one 8.8 µm cube/mean 7.4), Sand 3.09 ± 0.58.
- Kruskal–Wallis on specimen means (n = 2/3/2, so almost no power): 200³ H = 3.93, p = 0.14; 128³ H = 4.46, p = 0.11. Not significant; this says nothing about whether soils differ.
- **Ranking:** Vertisol is highest in every variant (matches earlier 4.99). **Loess vs Sand flipped**: here Loess (3.8) > Sand (2.9), the earlier whole-volume partial result had Sand 3.40 > Loess 3.04. The Loess–Sand gap is about 1 SE, so the order of those two is not resolved. The Vertisol values are far above the whole-volume 4.99 and extremely heterogeneous (specimen A: 20–60 in several cubes; specimen B ≈ 5–7), so the Vertisol mean is not a stable number.

## 4. Tortuosity vs porosity (Spearman, cubes pooled, descriptive only — cubes are pseudo-replicates, p-values not meaningful)
- 200³: ρ = −0.80 (n = 163); excluding flow-mismatch ρ = −0.70 (n = 120). Within soil: Vertisol −0.68, Loess −0.49, Sand −0.89.
- 128³: ρ = −0.64 (n = 160); excluding flow-mismatch −0.57.
- Lower cube porosity → higher τ (in all soils separately too), which is the expected direction; part of the pooled value reflects Vertisol having both the lowest porosity and the highest τ.

## 5. Recommendation for the paper
Report this as a **limitation with a supporting descriptive result**, not as a headline soil comparison. Subvolumes remove the solver non-convergence/crash (0/336 failures) and make tortuosity computable, but (i) τ is very scale- and location-dependent in the Vertisol (cube values 2 to 160, specimen means 6.6 vs 29.7), (ii) 3 mm (200³) and 1.9 mm (128³) cubes are likely below the REV for connectivity measures (Koestel et al. 2020, Geoderma 366:114206) and 128³ vs 200³ means differ materially, (iii) with n = 2–3 specimens per soil no test has power, and (iv) the largest values carry porespy flow-conservation warnings. What can be stated: Vertisol τ is consistently the highest and most variable, and Loess and Sand are similar (≈3 vs ≈3) with the order between them not resolved; the whole-volume ranking Vertisol > Sand > Loess is therefore not confirmed beyond its first place. A defensible sentence: "Tortuosity could only be obtained on 3 mm subvolumes; it was highest and most heterogeneous in the Vertisol and similar in Loess and Sand (mean ± SE across specimens, n = 2–3), but the subvolumes may be smaller than the REV, so we do not use it for between-soil inference."

## Files
`tortuosity_subvolumes.csv` (336 rows, includes flow_mismatch), `convergence_summary.csv`, `tortuosity_summary.csv` (specimen- and soil-level, `basis` column: original / excluding flow mismatch / plus 900 s timeout rerun), `tortuosity_by_soil.png/.svg`, `stats.json`, logs, scripts. Cube `.npy` files were deleted after the run (regenerable). `work/firstpass/` keeps the first pass of the raw CSVs. `DATA_CATALOG.md`, `PROJECT_STATUS.md` and existing run outputs were not modified; nothing is committed.
