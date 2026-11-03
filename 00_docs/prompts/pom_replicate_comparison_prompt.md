# Prompt — POM comparison redone with replicates (all Bnei Re'em scans + 2 label-downsampled Mishmar volumes)

> Paste this into Claude Code, in the PSD/topology pipeline repo, with access to the `nnUNet_resources` share. Restarts the Bnei Re'em vs. Mishmar POM comparison from scratch, this time as a proper multi-replicate comparison instead of a single scan per soil — and deliberately excludes any fresh model inference on non-native-resolution input, per the finding in `pom_analysis_20260824_ablation/` that the segmentation model is not robust to that.

---

## Why this task exists

The 2026-08-24 ablation run found that comparing Bnei Re'em against Mishmar-at-~15µm gives wildly different answers depending on *how* the 15 µm Mishmar volume is produced: label-downsampling the existing segmentation gave 347 µm mean distance-to-POM, while downsampling the raw image and re-running `i2_loess` gave 762 µm — a 54% disagreement on the same physical sample. The conclusion was that fresh model inference on non-training-resolution input is itself an unreliable confound. **This rerun avoids that entirely**: no branch here asks the model to predict on a downsampled or otherwise resolution-shifted image. The only new model inference allowed is on a genuinely new native-resolution scan (segmenting it at its own native voxel size, the same kind of input the model was trained on) — everything else is either an existing validated segmentation or a label-space downsample (majority vote on already-correct labels, no new prediction).

**Second motivation: replace n=1-per-soil with real replicates.** Every comparison so far has been one Bnei Re'em volume vs. one Mishmar volume — a single physical sample per soil, so nothing has ever been a proper group comparison with variance across samples (per the advisor's standard, mean ± SE requires more than one observation). This run fixes that two ways:

1. **Use every available Bnei Re'em scan** (not just `bnei_reem_fresh_bnei_reem_i4`) as independent Bnei Re'em replicates.
2. **Add a second physical Mishmar volume** — a different Mishmar scan that exists at a voxel size a bit larger than the native 5.85 µm (not the 15 µm `Cu011_samp_2` scan already ruled out for POM) — segment it (if not already segmented) at its own native resolution, then label-downsample it to ~15 µm the same way `mishmar_native` was, giving a second independent Mishmar-at-15µm replicate.

**Clustering scope: restrict strictly to these scans.** Do not include `mishmar_image_then_predict` (or any other fresh-inference-on-shifted-resolution branch) in the shape/spatial clustering at all — not as a comparison group, not pooled into the scaler. Clustering in this run runs only on: all Bnei Re'em replicates + the two Mishmar label-downsample replicates.

## Part 0 — Discovery (do this first, report before proceeding)

1. Search the `nnUNet_resources` share for every Bnei Re'em volume/segmentation available (pattern `bnei_reem*` or similar — check both raw scans and existing inference outputs). For each, report: path, voxel size (`np.unique()` + header), shape, and whether a valid `i2`-family segmentation already exists for it (pore=5/POM=2 convention) or whether it would need fresh inference. **List all candidates before running anything** — if any candidate's existing segmentation looks questionable (e.g. an implausible POM fraction like the `Cu011_samp_2` failure), flag it and exclude it rather than silently using it.
2. Search the same share for Mishmar HaNegev volumes with a native voxel size a bit larger than 5.85 µm (i.e. not `mishmar_hanegev_maoz_3_5p85um` itself, and not the 15 µm `Cu011_samp_2`) — report every candidate found with its voxel size. If more than one plausible candidate exists, list them all and pick the one Rony's naming/context makes clearest, or pause and ask which one he means before proceeding — don't guess silently between multiple real candidates.
3. Report the final replicate plan (which Bnei Re'em volumes, which second Mishmar volume) before running Part 1 — this is a cheap step, get it right before spending time on inference/EDT.

## Part 1 — Segmentation (only where genuinely missing)

- For any Bnei Re'em volume from Part 0 that doesn't already have a valid `i2`-family (or equivalent) segmentation, run inference **at that volume's own native resolution** — no resolution shifting. Sanity-check immediately (pore/POM voxel fractions in a plausible range relative to the existing Bnei Re'em replicate(s) — flag and stop on anything that looks like the `Cu011_samp_2` collapse pattern) before using it further.
- For the second Mishmar volume identified in Part 0, if it doesn't already have a valid segmentation, run `i2_loess` inference at *its own native resolution* (not downsampled — this is a different physical scan at its own native voxel size, so this is normal in-distribution-ish inference, not the resolution-shift case that failed before). Same immediate sanity check: POM/pore fractions should land in the same ballpark as `mishmar_native`'s (POM ≈1.6%, pore ≈27%) adjusted for its own voxel size — stop and report if it collapses.

## Part 2 — Label-downsample both Mishmar volumes to ~15 µm

For `mishmar_native` (5.85 µm): reuse the existing result from `pom_analysis_20260824_ablation/mishmar_label_downsample/` if it's still valid (re-verify the sanity check numbers match what's on record — POM fraction 1.614%, pore 26.108%) rather than recomputing from scratch.

For the newly identified second Mishmar volume: apply the same majority-vote label-downsample method (`downsample_common.py` / `step1_label_downsample.py` from the 08-24 run, generalized to this volume's own native voxel size rather than assuming 5.85 µm) to bring it to ~15.000 µm. Run the same immediate sanity check (POM fraction shouldn't collapse relative to its own native-resolution segmentation) before running the full pipeline on it.

Run the full POM pipeline (A1 cutoff, A2 conditioned distance maps, A3 accessibility, B size distribution — same methodology as all prior runs) on both label-downsampled Mishmar volumes independently, output to `pom_analysis_<date>/mishmar_label_downsample_1/` (native sample) and `pom_analysis_<date>/mishmar_label_downsample_2/` (new sample).

## Part 3 — Bnei Re'em replicates

For every Bnei Re'em volume from Part 0 (with a valid segmentation, whether pre-existing or freshly run in Part 1), run the full POM pipeline independently, output to `pom_analysis_<date>/bnei_reem_<n>/`. Reuse the existing `bnei_reem` result from `pom_analysis_20260824_ablation/bnei_reem/` for the original volume rather than recomputing.

## Part 4 — Group comparison (Bnei Re'em group vs. Mishmar-label-downsample group)

1. For every metric used in the prior 3-way/4-way tables (distance-to-POM mean, all three conditions; count-median and volume-weighted-median diameter; POM volume fraction; POM-pore contact fraction; largest-object share), report each replicate's value individually (a small table, one row per volume) — don't just report group means, since with this few replicates the individual values matter for judging homogeneity.
2. Then report group mean ± SE (per soil, across its replicates) for each metric. **State the actual n for each group plainly** — this is likely still small (however many Bnei Re'em volumes and exactly 2 Mishmar volumes turn out to exist), so frame any group comparison honestly: with n this small, mean ± SE is descriptive, not a basis for strong inferential claims. If n ≥ 3 for both groups, an appropriate test (Welch's t-test if roughly normal, Mann-Whitney U otherwise) can be reported; if either group has n=2, report the values and the difference plainly without dressing it up as a hypothesis test.
3. Compare this group-level result to the single-point figures from `pom_analysis_20260815_light/` (Bnei Re'em 597.9 µm vs. native Mishmar 268.1 µm, distance-to-POM denoised mean) and from the 08-24 ablation's label-downsample branch (347.3 µm) — does adding the second Mishmar replicate keep the Mishmar group close to that number, or shift it meaningfully? That tells us something about within-Mishmar physical-sample variability, separate from the resolution question.

## Part 5 — Clustering (Bnei Re'em replicates + both Mishmar label-downsample replicates ONLY)

1. Extract the same per-object shape (elongation, flatness, sphericity, pore-contact fraction) and spatial (nearest-neighbor / Clark-Evans) features as the 08-24 run, using the **same script version** for every volume in this run (state which version/commit is used, so future runs can reproduce it — this run found that switching sphericity computation methods between runs makes cluster/archetype results silently incomparable).
2. Fit any shared normalization (StandardScaler or equivalent) **only** across the volumes included in this run — Bnei Re'em replicates + the two Mishmar label-downsample replicates. Do not pool in, reference, or compare against `mishmar_image_then_predict` or the discarded `Cu011_samp_2` branch anywhere in this step.
3. Cluster each volume individually first (per-volume best-k via silhouette), then do the cross-soil archetype matching at the **group** level: Bnei Re'em (pooling all its replicates) vs. Mishmar (pooling both label-downsample replicates) — report the contingency table and chi-square test as before, plus, if useful, whether the two Mishmar replicates individually look similar to each other in cluster composition (a rough internal-consistency check for the Mishmar group).

## Output checklist

- Part 0 discovery report (candidate lists + chosen replicate plan) — in chat, before anything else runs.
- `pom_analysis_<date>/bnei_reem_<n>/summary_pom_metrics.json` for each Bnei Re'em replicate; `mishmar_label_downsample_1/` and `_2/summary_pom_metrics.json` for both Mishmar replicates.
- Part 4 per-replicate table + group mean±SE table, with n stated explicitly for each group and appropriately hedged language given the sample size.
- Part 5 clustering outputs (features CSV, cluster profiles, archetype contingency table + chi-square), restricted to exactly this run's volumes, with the script version noted.
- 2–3 sentences of draft caption text summarizing the group comparison, suitable for the figures draft, explicitly noting n per group.

## Sanity checks

- Every fresh segmentation (Part 1) checked immediately against a plausible POM/pore fraction range before being used further — stop on collapse, same as before.
- Both label-downsample sanity checks (Part 2) should show POM fraction close to their own native-resolution segmentation's POM fraction (no collapse toward the 0.3% floor used previously).
- No file, path, or result from `mishmar_image_then_predict` or the discarded `Cu011_samp_2` POM branch should appear anywhere in this run's outputs — a quick grep/check for those names in the final output directory before declaring done is a reasonable final check.
- If Part 0 finds only one Bnei Re'em volume and/or fails to find a plausible second Mishmar volume, say so plainly rather than proceeding as if the replicate upgrade succeeded — a single-replicate group is still worth analyzing, just report it as such.
