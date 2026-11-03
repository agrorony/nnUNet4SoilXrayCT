# Prompt — POM cross-soil resolution check + shape/spatial clustering

> Paste this into Claude Code, running inside the PSD/topology pipeline repo (same repo as `run_pom_analysis.py`, `psd_topology_metrics.py`, etc.). Extends the 2026-08-15 "light" POM run (`pom_analysis_20260815_light/`) and follows up on Track A2's open note about the Mishmar (5.85 µm) vs. Bnei Re'em (15.00 µm) voxel-size confound.

---

## Why this task exists

The 2026-08-15 POM run found real numeric differences between Bnei Re'em and Mishmar HaNegev in distance-to-POM and POM size distribution — but Mishmar was scanned at 5.85 µm and Bnei Re'em at 15.00 µm, so part of that gap could be a resolution artifact (the finer scan resolves smaller POM fragments and pore throats the coarser one can't). Two follow-ups:

1. **A second, independently scanned Mishmar sample at ~15 µm** (a *different* location/core from the existing 5.85 µm scan, already nnUNet-segmented with the same pore=5/POM=2 convention) is available. Running the same POM pipeline on it and comparing to both the native Mishmar (5.85 µm) and Bnei Re'em (15.00 µm) tests whether matching resolution moves Mishmar's numbers toward Bnei Re'em's (supporting a resolution confound) or whether it still resembles native-resolution Mishmar (supporting a genuine soil-type effect). **Caveat to keep in the write-up: because this is a different physical sample, it is not a clean resolution ablation — natural within-soil variability is a second variable riding along with the resolution change.** Treat it as one additional data point, not a controlled twin.
2. **Shape + spatial clustering of POM objects within each soil**, to test whether there are real, resolution-independent morphological or spatial differences in how POM is structured across soils (as opposed to just size/distance differences that resolution alone could produce).

**Scope: three POM datasets, Bnei Re'em and Mishmar HaNegev only** (Rehovot has no POM class, still N/A):

| Dataset | Voxel size | Status |
|---|---|---|
| `bnei_reem` | 15.000149 µm | Existing — from `pom_analysis_20260815_light/bnei_reem/` |
| `mishmar_native` | 5.85 µm | Existing — from `pom_analysis_20260815_light/mishmar/` |
| `mishmar_15um` | ~15 µm | **New** — different sample, already segmented. **Path: TBD — Rony to fill in the segmented volume path (and confirm exact voxel size via header / `np.unique()`, same as existing convention) before this prompt is run.** |

## Conventions (unchanged from the 08-15 run)

- Labels: pore = 5, POM = 2 (deployed convention, NOT `dataset_info.json`); verify with `np.unique()` on the new volume before anything else.
- 26-connectivity for object labeling; 1-voxel border trim for voxel-wise stats.
- Physical units via voxel size everywhere; report voxel size per volume explicitly in every output.
- Reuse the elbow-detection cutoff method (`find_elbow`) from `run_pom_analysis.py` for `mishmar_15um` rather than reusing Bnei Re'em's or native Mishmar's cutoff — the noise floor should be re-derived per volume.
- Everything under `pom_analysis_<date>/<soil>/`. Don't overwrite the 08-15 outputs.

## Part A — Resolution-matched cross-soil check

1. Run the existing POM pipeline (A1 noise-floor cutoff, A2 conditioned distance maps, A3 accessibility metrics, B size distribution) on `mishmar_15um`, identical methodology to the 08-15 run, output to `pom_analysis_<date>/mishmar_15um/summary_pom_metrics.json`.
2. Produce a **3-way comparison table**: `bnei_reem` (15 µm) vs. `mishmar_native` (5.85 µm) vs. `mishmar_15um` (~15 µm), for:
   - Distance-to-POM mean (median) µm, all three conditions (denoised / pore-adjacent / connected-pore-adjacent)
   - Size distribution: count-median and volume-weighted-median diameter (µm)
   - A3 accessibility metrics: POM volume fraction, POM–pore contact fraction
3. Interpret directionally in the write-up: if `mishmar_15um` values sit closer to `bnei_reem` than to `mishmar_native`, that's evidence the original Mishmar-vs-Bnei-Re'em gap was resolution-driven; if `mishmar_15um` still tracks `mishmar_native` despite matched resolution, that's evidence of a genuine soil-type difference. State this plainly — don't overclaim statistical significance from a single additional sample per soil.
4. **Note as a follow-up (not required in this run):** a computational downsample of `mishmar_native` to 15 µm (already flagged in the Track A2 note) would be the clean resolution ablation — same physical sample, resolution as the only variable. Running both the empirical new-scan comparison (this prompt) and the downsample check, and seeing whether they agree, would be the strongest evidence either way. Flag this explicitly as a recommended next step in the output, don't execute it here.

## Part B — POM object shape + spatial clustering

Applied to all three datasets (`bnei_reem`, `mishmar_native`, `mishmar_15um`), objects ≥ each dataset's own denoised cutoff.

### B1. Per-object shape features

For every kept POM object, compute:
- **Elongation** — ratio of largest to smallest principal axis (eigenvalues of the object's inertia tensor / covariance matrix of voxel coordinates).
- **Flatness** — ratio of middle to smallest principal axis (distinguishes rod-like from plate-like fragments; elongation alone conflates the two).
- **Sphericity / surface-to-volume ratio** — object surface area (marching cubes on the object mask, or face-adjacent-voxel counting for a cheaper proxy) divided by volume, normalized so a sphere = 1.
- **Per-object pore-contact fraction** — fraction of the object's surface voxels face-adjacent to pore space (extends the existing whole-sample A3 contact-fraction metric to per-object resolution).
- Keep existing size fields (voxel count, equivalent diameter) alongside these for context — don't drop them.

### B2. Spatial pattern

Using object centroid coordinates (voxel space → µm via voxel size), per soil:
- Nearest-neighbor distance distribution between POM object centroids — report mean/median NN distance.
- A clustering-vs-dispersion indicator: either the NN-distance-based clustering index (observed mean NN distance ÷ expected mean NN distance under complete spatial randomness, given the sample's object density) or a 3D pair-correlation function / Ripley's K at a few representative radii — pick whichever is cheaper to implement correctly with the existing toolset. Report whether POM is spatially aggregated, dispersed, or close to random within each soil, and whether this differs between soils.

### B3. Clustering

Per soil, on the normalized feature vector {elongation, flatness, sphericity, pore-contact fraction} (size deliberately excluded from the clustering features themselves, to keep clusters about *shape/accessibility* rather than re-deriving the already-known size distribution — report size as a post-hoc cluster descriptor instead):
- Cluster with k-means (or GMM if cluster shapes look non-spherical in a quick pairwboth-plot check); select k by silhouette score, testing k = 2..6.
- Report per cluster: size (n objects, % of soil's POM objects), mean feature profile, and mean/median diameter (post-hoc, not a clustering input).
- Cross-soil comparison: do the soils produce similar cluster "archetypes" (e.g. a compact/rounded accessible cluster and an elongated/occluded cluster in both) just in different proportions, or does clustering surface soil-specific archetypes that don't appear in the other soil? A chi-square test of independence on cluster-membership-by-soil (after matching clusters across soils by nearest feature-profile centroid, if archetypes look shared) is the appropriate significance check — no SD anywhere, mean (median) or SE only for any continuous summary, per advisor's standard.

## Output checklist

- `pom_analysis_<date>/mishmar_15um/summary_pom_metrics.json` — same schema as existing (A1/A2/A3/B), voxel size clearly stated.
- 3-way comparison table (Part A) — Markdown, ready to paste into the draft, with a short interpretive note on resolution-confound vs. soil-type-effect per the logic above.
- `pom_object_features_<soil>.csv` per soil (or one combined CSV with a `soil` column): object_id, diameter_um, elongation, flatness, sphericity, pore_contact_fraction, cluster_id.
- Spatial pattern summary (NN-distance stats + clustering index or pair-correlation result) per soil, one CSV or JSON.
- Clustering diagnostic: silhouette-score-vs-k plot per soil (to justify chosen k), and a 2D feature-space scatter (e.g. elongation vs. sphericity) colored by cluster, per soil.
- In chat: the Part A comparison table with interpretation, the Part B cluster profile summary per soil, the cross-soil archetype comparison result (with the chi-square test if applicable), and 2–3 sentences of draft caption text for each of Part A and Part B that can drop directly into the figures draft.

## Sanity checks

- `mishmar_15um` voxel size must come out close to 15 µm — if `np.unique()` or the header disagrees, stop and flag before running anything else.
- Elongation ≥ 1 and flatness ≥ 1 by construction (largest ÷ smallest, middle ÷ smallest) — any object below 1 indicates a bug in the eigenvalue ordering.
- Sphericity should be in (0, 1] — values > 1 indicate a surface-area computation error.
- Chosen k for each soil's clustering should be > 1 and < n_objects / 20 or so (a k close to n_objects means the clustering degenerated into near-singleton clusters — reconsider the feature normalization or k range).
