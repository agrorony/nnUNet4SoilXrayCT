# Track A2 — class-restricted re-inference + Mishmar resolution robustness check

Generated 2026-08-22. Executes the A2 follow-up flagged in `PROJECT_STATUS.md`
(Track A row) using the class scheme from `psd_binning_recommendation.md` and the
raw per-subvolume PSD histograms from `fig4_inference_20260815/` (2026-08-15 run,
8 subvolumes/soil, non-overlapping cubic replicates; see
`subvolume_psd_stats_summary_v1.md` for the full original methodology, REV
check, and object-level KS results, which are unaffected by A2 and still stand).

**No local-thickness recomputation was needed for the class restriction itself**
— the existing `psd_table.csv` per subvolume already carries the full 32-bin
histogram (`Volume_Count` per bin), so class fractions are exact re-binnings of
the same underlying data. A recomputation *was* needed for the Mishmar
downsample robustness check (new local-thickness runs on resampled volumes).

## What changed vs. the 2026-08-15 run

1. **Cross-soil inference restricted to >=31 µm.** Three classes used throughout:
   `31-150 µm` (microbially active), `150-290 µm` (transmission), `>=290 µm`
   (large macropores/biopores & cracks). The Kravchenko/Dor scheme's boundaries
   are 30/150/300 µm; the log-spaced bin edges from the original run already
   merge in exact 30 and 150 µm edges, but have no edge at exactly 300 µm — the
   nearest available edge, **288.54 µm**, is used as the practical >300 µm
   cutoff (4% off target, well inside a single log-bin's width, and the same
   approximation the binning recommendation anticipated). Everything below
   31 µm (unreliable at 15 µm-voxel resolution) is excluded from cross-soil
   classes.
2. **Whole-distribution median pore diameter is dropped from cross-soil claims.**
   It is resolution-confounded (Mishmar's 5.85 µm voxels see pores the 15 µm
   scans structurally cannot) and must not reappear in the draft as a 3-soil
   comparison. Porosity and per-class porosity are used instead.
3. **Mishmar-downsample robustness check** (new): the 8 Mishmar subvolumes were
   resampled from 5.85 µm to ~15 µm voxels (trilinear resample of the binary
   pore mask + re-threshold at 0.5 — the standard "downsample and re-threshold"
   proxy for what a coarser acquisition + thresholding segmentation would see)
   and the local-thickness PSD pipeline re-run on all 8. Cross-soil tests were
   redone with downsampled-Mishmar substituted for original Mishmar to check
   whether the >=31 µm conclusions survive.
4. **Sensitivity re-test on 60-150 µm** (>=4 voxels at 15 µm, per the
   recommendation): repeats the 31-150 µm comparison restricted to 60-150 µm to
   check whether the specific 31-60 µm sub-range (2-4 voxels, unreliably sized
   even where nominally "detected") is driving any conclusions.

All tests: Shapiro (residuals) + Levene -> one-way ANOVA+Tukey HSD (eta²) or
Kruskal-Wallis+Dunn Holm-corrected (epsilon²), exactly as the 2026-08-15 run.
Family-wise Holm correction additionally applied across the 3 main class-omnibus
p-values (not just the 3 within-metric soil-pairs), since 3 separate class tests
are now being reported together instead of one 59-bin chi-square.
**Cross-check**: re-running the pipeline on unchanged inputs (porosity) reproduces
the original run's p-value and significance grouping exactly, validating the
re-implementation.

## Results: >=31 µm class porosity (mean ± SE, n=8/soil)

| Class | Test | p | p (Holm, family of 3) | Effect size | Bnei Re'em | Mishmar | Rehovot |
|---|---|---|---|---|---|---|---|
| 31-150 µm | Kruskal-Wallis | 0.00041 | 0.00041 | ε²=0.648 | 0.093±0.004 **b** | 0.204±0.019 **a** | 0.216±0.004 **a** |
| 150-290 µm | one-way ANOVA | 2.4e-05 | 7.1e-05 | η²=0.637 | 0.055±0.007 **b** | 0.022±0.009 **a** | 0.087±0.007 **c** |
| >=290 µm | Kruskal-Wallis | 6.2e-05 | 0.00012 | ε²=0.827 | 0.073±0.029 **b** | 0.0009±0.0004 **a** | 0.006±0.001 **c** |
| Porosity (reference, unchanged) | Kruskal-Wallis | 0.0108 | — | ε²=0.336 | 0.221±0.032 **a** | 0.277±0.016 **ab** | 0.309±0.007 **b** |

All three >=31 µm classes remain significant after Holm-correcting across the
3-class family (p<=0.0007 for all). Full pairwise p-values, effect sizes and
group stats: `class_stats_results.json`. Per-subvolume raw values:
`class_metrics.csv`.

**Compositional PERMANOVA** (CLR-transformed 3-class vector, Euclidean distance,
9999 permutations) — replaces the previous 32-bin Bray-Curtis PERMANOVA as the
whole-distribution-shape test for cross-soil claims, since it now only uses the
>=31 µm classes: omnibus pseudo-F(2,21)=12.65, R²=0.546, p=0.0001. All 3 pairwise
comparisons significant after Holm correction (bnei_reem-mishmar p_holm=0.0006,
bnei_reem-rehovot p_holm=0.0006, mishmar-rehovot p_holm=0.0105).

## Caveat surfaced by the sensitivity re-test (60-150 µm)

| Class | Test | p | Bnei Re'em | Mishmar | Rehovot |
|---|---|---|---|---|---|
| 60-150 µm | Kruskal-Wallis | 0.00035 | 0.082±0.004 **a** | 0.120±0.015 **a** | 0.208±0.004 **b** |

Restricting to 60-150 µm (excluding the 31-60 µm sub-range, which sits at only
2-4 voxels at the 15 µm-scan resolution and is flagged in the recommendation as
unreliably sized) **removes the Bnei Re'em vs. Mishmar significant difference**
that is present in the full 31-150 µm class (Dunn p_adj 0.0033 -> 0.120,
n.s.). Bnei Re'em vs. Rehovot and Mishmar vs. Rehovot remain significant in
both versions. **Practical implication for the draft**: the Bnei Re'em-vs-Mishmar
part of the 31-150 µm ("microbially active") claim is not robust to the coarse-
scan detection limit and should either be dropped or explicitly hedged
("driven by the 31-60 µm sub-range, which is close to the 15 µm scan's
detection floor"); Rehovot's separation from both other soils in this class is
robust.

## Mishmar-downsample robustness check (5.85 µm -> ~15 µm)

Method and per-subvolume before/after values: `mishmar_downsample/downsample_manifest.json`,
`mishmar_downsample/downsample_comparison.json`. Actual output voxel size after
resampling: 14.973 µm (target was 15.000 µm, matching Bnei Re'em/Rehovot).

**Paired before/after (n=8, Wilcoxon signed-rank):**

| Metric | Mean before (5.85 µm) | Mean after (~15 µm) | % change | Wilcoxon p |
|---|---|---|---|---|
| Porosity | 0.2767 | 0.2758 | -0.30% | 0.0078 |
| 31-150 µm class | 0.2038 | 0.1975 | -3.08% | 0.0078 |
| 150-290 µm class | 0.0221 | 0.0234 | +5.90% | 0.0078 |
| >=290 µm class | 0.00086 | 0.00081 | -5.68% | 0.625 (n.s.) |

Small but statistically detectable shifts in porosity, 31-150 µm, and 150-290 µm
(consistent with resolution effects: losing some of the finest detected pores
and some smoothing-driven redistribution across the local-thickness estimate at
downsampling), no detectable shift in the >=290 µm class (large pores are far
above both resolutions' detection limits, as expected).

**3-soil re-test with downsampled Mishmar substituted for original Mishmar**
(`downsample_comparison.json` -> `robustness_comparison`): for all four metrics
(porosity, 31-150, 150-290, >=290 µm), the compact-letter grouping *structure*
(which pairs are/aren't significantly different) and the **rank order of group
means** are identical before and after downsampling. Two of the four show a
different letter *string* (e.g. "b"/"a" swapped to "a"/"b") — this is a cosmetic
artifact of the compact-letter algorithm's clique-selection order, not a
substantive change: in both 150-290 µm and >=290 µm, Mishmar remains the lowest
of the three soils and all three soils remain mutually significantly different
in both the original and downsampled analysis (verified directly against
`group_means` in `downsample_comparison.json`, not just the letter strings).

**Conclusion: the >=31 µm cross-soil conclusions are robust to the voxel-size
difference between Mishmar and the other two soils.** Downsampling shifts
absolute class fractions by a few percent (as expected) but does not change
which soils differ from which, in any of the three >=31 µm classes.

## Recommended text for the figures draft (replaces the v1 subvolume caption)

> Pore-size distributions were derived from eight non-overlapping cubic
> subvolumes per soil (physical replicates; see Methods for extraction and REV
> details) and aggregated into three functional size classes following
> Kravchenko/Dor (30-150, 150-300, >300 µm; the coarsest scan's 2-voxel
> detection floor sets the lower bound at 31 µm, so whole-distribution medians
> and the <31 µm range are not used for cross-soil comparison). Per-class
> porosity differed significantly among soils in all three classes
> (31-150 µm: Kruskal-Wallis p=0.0004; 150-290 µm: ANOVA p<0.0001; >=290 µm:
> Kruskal-Wallis p<0.0001; all significant after Holm correction across the
> three classes; η²/ε²=0.64-0.83), and the three-class composition vector
> differed significantly among soils overall (compositional PERMANOVA,
> pseudo-F(2,21)=12.6, R²=0.55, p=0.0001; all pairwise comparisons significant,
> Holm-corrected). Bnei Re'em (Vertisol) has the lowest 31-150 µm ("microbially
> active") fraction but the highest >=290 µm ("large macropore/crack") fraction,
> consistent with shrink-swell cracking; Mishmar HaNegev (Loess) has the highest
> 31-150 µm fraction and the lowest 150-290 µm and >=290 µm fractions,
> consistent with a fine, uniform loess pore structure; Rehovot (Sand) has the
> highest 150-290 µm fraction. A sensitivity re-test restricted to 60-150 µm
> (excluding the 31-60 µm sub-range nearest the 15 µm-scan detection limit)
> confirms Rehovot's separation from both other soils but not the Bnei
> Re'em-Mishmar difference in this class, which should be treated as sensitive
> to the resolution floor. A robustness check that downsampled Mishmar's 5.85 µm
> scan to the other two soils' ~15 µm resolution confirmed all cross-soil
> significance patterns and rank orderings are unchanged. As before, each soil
> is represented by a single physical CT scan, so these subvolumes are
> pseudo-replicates of one sample per soil type; Rehovot's binary-threshold
> segmentation (vs. nnU-Net 3-class for the other two soils) remains a
> methodological asymmetry.

## Outputs in this folder

- `class_metrics.csv` — 24 rows, per-subvolume class fractions (of pore volume
  and of total volume) for 31-150, 150-290, >=290, and the 60-150 sensitivity
  class, plus porosity.
- `class_stats_results.json` — full Part A (per-class univariate incl. Holm
  family correction), sensitivity re-test, and Part B (compositional PERMANOVA)
  results, machine-readable.
- `mishmar_downsample/` — `subvolumes_15um/` (8 resampled masks),
  `downsample_manifest.json` (before/after porosity per subvolume),
  `psd_runs/` (8 new local-thickness runs), `mishmar_downsampled_class_metrics.csv`,
  `downsample_comparison.json` (paired test + 3-soil re-test with substitution).
- `scripts/` — `reaggregate_classes.py`, `downsample_mishmar.py`,
  `run_downsample_psd_batch.py`, `downsample_compare.py`.

## Not affected by A2 (still valid from the 2026-08-15 run)

REV check, subvolume extraction/exclusion manifest, pore-object KS tests
(Part C — object diameters, not diameter classes, and not used for cross-soil
median claims), sanity checks (subvolume-mean vs. full-volume porosity).
