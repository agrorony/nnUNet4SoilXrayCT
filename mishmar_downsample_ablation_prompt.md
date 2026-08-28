# Prompt — Mishmar downsample ablation (label-downsample vs. image-downsample-then-predict)

> Paste this into Claude Code, in the PSD/topology pipeline repo. Replaces the failed "new physical 15 µm Mishmar sample" branch from `pom_analysis_20260823_resolution/` with two computational ablations on the *same, already-validated* Mishmar 5.85 µm sample.

---

## Why this task exists

The 2026-08-23 run added a third POM dataset, `mishmar_15um`, from a *different* physical Mishmar sample (`Cu011_samp_2`) scanned natively at ~15 µm and segmented with the `i2_loess` nnU-Net model. That branch failed: POM voxel fraction came out at 0.120% (vs. 1.613% for native Mishmar and 0.818% for Bnei Re'em) while pore fraction was normal (26.4%, in line with native Mishmar's 27.0%). Pore detection working while POM collapses by ~90% is not a plausible soil effect — it means the segmentation model failed to recognize POM on that input. **Discard every result derived from that branch**: the "Mishmar new (15 µm)" column in `part_a_3way_comparison.md`, its entry in `pom_spatial_pattern_summary.json`, and the 3-soil clustering run (`run_log_shape_clustering_3soil.txt`, `pom_cluster_profiles.csv`, `pom_archetype_crosssoil_comparison.json`).

**Also fix a contamination bug this exposed.** The clustering script fits one `StandardScaler` pooled across every soil passed into a given run, then clusters each soil against that shared normalization. Because the failed `mishmar_15um` branch's features were pooled in, they also corrupted the clustering *for the two good soils in that same run* — Bnei Re'em's own POM objects clustered cleanly into k=2 (silhouette 0.811) in the 2-soil run, but came out as k=6 (silhouette 0.247) in the 3-soil run using the *same* Bnei Re'em objects. `pom_cluster_profiles.csv` on disk right now is the contaminated 3-soil version and should not be trusted for any soil. **Fix: fit any shared normalization only across the specific soils/branches being compared in a given output — never let one branch's data leak into another's clustering.**

**Replace the failed branch with two ablations on the already-trusted `mishmar_native` sample** (same physical core the 08-15 and 08-23 native-Mishmar numbers came from), instead of a second physical sample + fresh inference:

1. **`mishmar_label_downsample`** — downsample the existing, validated Mishmar segmentation (5.85 µm, pore=5/POM=2 labels) directly to ~15.0 µm.
2. **`mishmar_image_then_predict`** — downsample the raw Mishmar CT image (5.85 µm) to ~15.0 µm, then run `i2_loess` fresh on the downsampled image to get a new native segmentation at 15 µm.

Comparing these two against each other, plus against `mishmar_native` (5.85 µm) and `bnei_reem` (15.00 µm), gives a real 4-way comparison on genuinely matched samples, and tells us something extra: if branch 1 and branch 2 agree, the resolution effect lives mainly in the geometry/statistics of the POM metrics; if they diverge, the segmentation model itself behaves differently at coarse input resolution — that's a distinct finding worth its own sentence in the draft.

## Conventions (unchanged)

- Labels: pore = 5, POM = 2; verify with `np.unique()` on every new volume before anything else, including the downsampled ones.
- 26-connectivity for object labeling; 1-voxel border trim for voxel-wise stats.
- Re-derive the elbow cutoff (`find_elbow`) separately for each of the two new branches — don't reuse `mishmar_native`'s or `bnei_reem`'s cutoff.
- Everything under `pom_analysis_<date>/<branch>/`. Don't overwrite `pom_analysis_20260815_light/` or the valid parts of `pom_analysis_20260823_resolution/` (native Mishmar and Bnei Re'em results there are still good — only the `mishmar_15um` subfolder and the 3-soil clustering outputs are invalid).

## Part A — Label downsample (`mishmar_label_downsample`)

1. Take the existing Mishmar segmentation volume (5.85 µm, `mishmar_hanegev_maoz_3_5p85um.nii.gz`) and downsample the *label array* to ~15.0 µm voxel size using **majority vote (mode) per block** — e.g. reshape into non-overlapping ~2.56×2.56×2.56-voxel blocks (15.0/5.85 ≈ 2.564; round the block shape sensibly and report the achieved voxel size) and assign each output voxel the most common input label in its block. **Do not use linear/cubic interpolation on the label array** — that produces nonsense intermediate label values on a categorical array. Verify `np.unique()` on the result still shows only `[0, 1, 2, 5]` (or a subset).
2. Report the resulting voxel size, shape, and the pore/POM voxel fractions immediately — **stop and flag before proceeding if POM fraction has collapsed relative to native Mishmar's 1.613%** (this is the exact check that would have caught the 08-23 failure early). A drop toward native Bnei Re'em's ballpark (~0.8%) from resolution alone is plausible; a drop to <0.3% is not.
3. Run the full existing POM pipeline (A1 cutoff, A2 conditioned distance maps, A3 accessibility, B size distribution) on this downsampled-label volume, output to `pom_analysis_<date>/mishmar_label_downsample/`.

## Part B — Image downsample then predict (`mishmar_image_then_predict`)

1. Downsample the raw Mishmar CT image (5.85 µm) to ~15.0 µm using standard image resampling (block-averaging or another appropriately anti-aliased method — not nearest-neighbor, this is a continuous-valued image, not labels). Report the achieved voxel size.
2. Run the `i2_loess` nnU-Net model fresh on this downsampled raw image to produce a new segmentation at ~15 µm. Report pore/POM voxel fractions immediately — same stop-and-flag check as Part A: if POM fraction collapses implausibly (as it did in the failed `mishmar_15um` branch) while pore fraction stays reasonable, **stop and report the failure rather than running the full pipeline on a broken segmentation.**
3. If the sanity check passes, run the full POM pipeline on this volume, output to `pom_analysis_<date>/mishmar_image_then_predict/`.

## Part C — 4-way comparison + branch agreement

1. Build a 4-column table (same format as `part_a_3way_comparison.md`): `bnei_reem` (15.00 µm), `mishmar_native` (5.85 µm), `mishmar_label_downsample` (~15 µm), `mishmar_image_then_predict` (~15 µm) — distance-to-POM (all three conditions), count-median and volume-weighted-median diameter, POM volume fraction, POM-pore contact fraction, largest-object share, n objects, elbow cutoff.
2. Explicitly compare `mishmar_label_downsample` vs. `mishmar_image_then_predict` against each other, not just against the other two: if their numbers are close, say so and treat that as evidence the resolution effect is mostly geometric; if they diverge noticeably, say so and flag it as evidence the segmentation model's behavior itself changes with input resolution — that's a separate, reportable finding.
3. Interpret directionally against `bnei_reem` and `mishmar_native`, same logic as the original prompt: do the ~15 µm Mishmar variants move toward Bnei Re'em (supporting a resolution-driven original gap) or stay with native Mishmar (supporting a genuine soil-type effect)? This time there is no "different physical sample" caveat for Part A — Part A of this prompt is a clean ablation on the same sample. (Part B/image-downsample technically reprocesses the same raw data through inference again, so it's also same-sample; only the model's behavior at a new resolution is the added variable there.)

## Part D — Re-derive clean clustering (fixes the contamination bug)

1. Fix the clustering script so any shared normalization (StandardScaler or equivalent) is fit **only** on the soils/branches included in that specific comparison — never pooled across a run that also includes an excluded/failed branch.
2. Re-run shape + spatial clustering for exactly `bnei_reem` + `mishmar_native` (2-soil, clean) and save its `pom_cluster_profiles.csv` under a name that won't be overwritten by a later run (e.g. `pom_cluster_profiles_2soil_clean.csv`) — this recovers the per-archetype shape profile (mean elongation, flatness, sphericity, pore-contact fraction per cluster) that was lost when the 3-soil run overwrote it.
3. Then run a separate 4-soil clustering (`bnei_reem`, `mishmar_native`, `mishmar_label_downsample`, `mishmar_image_then_predict`) under its own output filenames, with the fixed per-comparison scaler — this is the version relevant to the resolution question, since it lets the two new Mishmar branches be compared for shape/spatial archetype membership alongside the size/distance numbers from Part C.

## Output checklist

- `pom_analysis_<date>/mishmar_label_downsample/summary_pom_metrics.json` and `mishmar_image_then_predict/summary_pom_metrics.json` (A2+A3+B, existing schema).
- Part C 4-way comparison table, Markdown, with the branch-agreement discussion.
- `pom_cluster_profiles_2soil_clean.csv` (recovered clean Bnei Re'em vs. native-Mishmar profiles) and a separate 4-soil clustering output set.
- In chat: both sanity-check results (POM fraction after downsampling, before running the rest of the pipeline) reported explicitly even if they pass; the 4-way table with interpretation; the branch-agreement finding; the re-derived clean 2-soil archetype/cluster summary; and 2–3 sentences of draft caption text updating the ones from the previous (failed) attempt.

## Sanity checks

- POM voxel fraction for both new Mishmar branches should be in the same order of magnitude as native Mishmar's 1.613% (allowing a real reduction toward Bnei Re'em's ~0.8% from resolution loss, but not a collapse below ~0.3%) — **check this before running the full pipeline on either branch**, exactly the check the 08-23 run skipped.
- Pore voxel fraction for both new Mishmar branches should stay close to native Mishmar's 27.0% (resolution shouldn't affect pore detection nearly as much as it affects small POM fragments).
- `np.unique()` on `mishmar_label_downsample` must show only valid labels ([0,1,2,5] or subset) — a majority-vote downsample can't introduce new label values; if it does, the block-reduction implementation is wrong.
- Ordering within each branch: denoised ≤ pore-adjacent ≤ connected-pore-adjacent mean distance (same check as all prior runs).
- The 2-soil clean clustering result should reproduce `run_log_shape_clustering_2soil.txt`'s numbers (Bnei Re'em best_k=2, silhouette≈0.811; Mishmar native best_k=5, silhouette≈0.418; archetype k=2, χ²≈12.52, p≈0.0004) — if it doesn't, the scaler fix introduced a regression, stop and check.
