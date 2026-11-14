# Figure 4 subvolume-replicate inference — stats summary

Generated 2026-08-15. Replaces the chi-square-on-45M-voxels test (χ²=22,624,522,
df=58) with subvolume replication as advised: voxels are spatially autocorrelated
and there was no replication in the original test, so any difference was
"significant" at that n. This analysis uses 8 non-overlapping cubic subvolumes
per soil as physical replicates.

## Data sources

| Soil | Segmented volume | Shape | Voxel size | Segmentation method |
|---|---|---|---|---|
| Bnei Re'em (Vertisol) | `bnei_reem_fresh_bnei_reem_i4/inference_concatenated/nlm_volume.nii.gz` | 650×650×652 | 15.000149 µm | nnU-Net 3-class (pore=5, POM=2) |
| Mishmar HaNegev (Loess) | `mishmar_hanegev_maoz_3_5p85um/inference_output_concat_loess_i2/mishmar_hanegev_maoz_3_5p85um.nii.gz` | 1000×1000×1000 | 5.85 µm | nnU-Net 3-class (pore=5, POM=2) |
| Rehovot (Sand) | `10.5/rehovot_samp_2.npy` | 650×650×650 | 15.0 µm | **Binary pore/solid mask** (no POM class) |

**Caveats carried from discovery (Step 0), still relevant:**
- **Voxel size differs 2.56× between Mishmar (5.85 µm) and the other two soils (15.0/15.000149 µm).** Not a resolution artifact for the metrics used here (all soils' pore populations are well above the voxel scale), but relevant to cross-soil comparability of very small pores.
- **Rehovot's segmentation is a binary pore/solid mask, not a 3-class nnU-Net segmentation.** There is no POM class for Rehovot, and the "pore" definition may come from a different method (thresholding vs. deep learning) than the other two soils. This is a genuine methodological asymmetry, not just a labeling quirk — treat Rehovot's absolute porosity/pore-size numbers as less directly comparable to the other two soils' nnU-Net-derived numbers than they are to each other.
- **Mishmar's exact source file required reconciliation.** The original full-volume-batch checkpoint recorded a path (`inference_output_concat_scratch_i2`) that no longer exists on disk. Cross-checking pore-voxel counts against the completed run's recorded `total_pore_voxels` (268,974,742, post 1-voxel border trim) identified `inference_output_concat_loess_i2` as the matching file (raw pore count 270,384,653; implied trim 0.52%, consistent with the trim ratio independently verified on Bnei Re'em). `inference_output_concat_scratch`'s raw count (262,032,573) is already below the target and is ruled out. High but not 100% confidence.

## Subvolume scheme (Step 1)

- Bnei Re'em & Rehovot: 300³-voxel cubes → 4.50 mm edge, 2×2×2 = 8 subvolumes/soil.
- Mishmar: 430³-voxel cubes → 2.52 mm edge, 2×2×2 = 8 subvolumes/soil.
- Different voxel-count size per soil (user decision 2026-08-15): Bnei Re'em's physical
  sample (9.75mm) is much larger than Mishmar's (5.85mm) despite Mishmar having more
  voxels/axis (finer resolution), so no single physical or voxel-count size could hit
  8–12 subvolumes ≥300³ voxels for both simultaneously. Physical subvolume size therefore
  differs between soils — noted in the caption.
- Placement: each axis split into 2 halves, cube centered within each half (margin
  12–35 voxels from outer volume boundary on all sides) to reduce the chance of
  sampling the cylindrical-core scan boundary/corner artifacts.
- **Exclusion check**: porosity extremity (<0.02 or >0.85) and, for labeled volumes,
  anomalous label-0 ("unclassified") fraction vs. the global mean. **0 of 24 candidate
  subvolumes were excluded** — all porosities and label-0 fractions were within normal
  range (see `subvolume_extraction_manifest.json` for full per-subvolume values).
  Caveat: this is a coarse statistical heuristic, not a geometric corner-artifact
  detector; no subvolume showed the near-0/near-1 porosity signature of a true
  air-gap or container-wall region.

### REV check (Bnei Re'em, nested cubes centered at volume center)

| Edge (mm) | Porosity |
|---|---|
| 1.125 | 0.3463 |
| 2.250 | 0.3146 |
| 3.375 | 0.2895 |
| **4.500 (chosen size)** | **0.2887** |
| 6.000 | 0.2858 |
| 7.500 | 0.2581 |

Porosity is essentially flat (≤2% relative change) from 3.375–6.0 mm, bracketing the
chosen 4.50 mm subvolume edge — **REV appears satisfied at the chosen size**. The
drop at 7.5 mm (0.258) is most likely a boundary-proximity effect (7.5mm cube occupies
77% of the 9.75mm full sample axis, leaving little margin) rather than genuine
non-stabilization at larger scale, but this wasn't independently confirmed with a
larger sample. See `rev_check_bnei_reem.png`.

## Step 2: per-subvolume metrics

See `subvolume_metrics.csv` (24 rows: soil, subvolume id, origin, porosity, mean/median
diameter, 30–150µm fraction of pore volume and of total volume, full binned PSD vector).
Computed via the repo's existing local-thickness/PSD pipeline
(`run_psd_diagnostics.py real` mode — binary pore mask, no re-implementation), with a
fixed 32-edge bin set (2–1000 µm, log-spaced, 30/150 µm edges merged in) applied
identically across all subvolumes and both full-volume runs, so PSD vectors are
directly comparable soil-to-soil for Part B.

## Step 3A: univariate tests (subvolumes as replicates, n=8/soil)

All three metrics failed the ANOVA assumption check (Shapiro on residuals and/or
Levene, p≤0.05) — **Kruskal-Wallis + Dunn (Holm-corrected)** used throughout. No
ANOVA/KW conflict to report (KW was triggered for all three metrics, consistently).

| Metric | Test | Statistic | df | p | Effect size | Bnei Re'em | Mishmar | Rehovot |
|---|---|---|---|---|---|---|---|---|
| Porosity | Kruskal-Wallis | H | 2 | 0.0108 | ε²=0.336 | 0.221±0.032 **b** | 0.277±0.016 **ab** | 0.309±0.007 **a** |
| Median diameter (µm) | Kruskal-Wallis | H | 2 | 0.00026 | ε²=0.690 | 173.7±38.3 **a** | 52.8±3.4 **b** | 106.3±1.4 **a** |
| 30–150µm frac. (of pore vol.) | Kruskal-Wallis | H | 2 | 0.0064 | ε²=0.386 | 0.475±0.060 **b** | 0.729±0.034 **a** | 0.703±0.016 **a** |

(mean ± SE, n=8 per soil; letters = Dunn post-hoc, Holm-corrected, shared letter = not
significantly different)

Full pairwise Dunn p-values are in `stats_results.json` (`A_univariate.<metric>.pairwise`).

## Step 3B: PERMANOVA (Bray-Curtis, binned PSD vectors, 9999 permutations)

**Omnibus**: pseudo-F(2,21) = 56.11, R² = 0.842, p = 0.0001 (minimum resolvable at
9999 permutations). Soil identity explains 84% of the variance in subvolume PSD-shape
dissimilarity.

**Pairwise (Holm-corrected)**:

| Pair | pseudo-F | R² | p | p (Holm) |
|---|---|---|---|---|
| Bnei Re'em vs Mishmar | 45.58 | 0.765 | 0.0002 | 0.0006 |
| Bnei Re'em vs Rehovot | 12.73 | 0.476 | 0.0003 | 0.0006 |
| Mishmar vs Rehovot | 249.91 | 0.947 | 0.0004 | 0.0006 |

All three pairs remain significant after Holm correction. Mishmar vs. Rehovot shows
the largest separation (R²=0.947); Bnei Re'em vs. Rehovot the smallest (R²=0.476),
consistent with Part A's median-diameter result (Bnei Re'em and Rehovot share letter
"a").

## Step 3C: pore-object KS tests (26-connectivity, full volumes, objects ≥2 voxels)

| Soil | n objects (raw) | n objects (≥2 vox) | excluded | median diam (µm) |
|---|---|---|---|---|
| Bnei Re'em | 25,279 | 23,423 | 7.3% | 59.7 |
| Mishmar | 56,187 | 52,542 | 6.5% | 23.5 |
| Rehovot | 2,695 | 2,529 | 6.2% | 66.7 |

Rehovot's much lower object count for a comparable/larger pore-voxel volume (83.8M
pore voxels in only 2,695 objects, vs. Bnei Re'em's 59.6M voxels in 25,279 objects)
indicates Rehovot's pore space is dominated by a small number of large, well-connected
percolating structures rather than many discrete pores — expected for sand, and worth
keeping in mind when interpreting its object-diameter distribution (likely strongly
bimodal: many small isolated pores + one or few enormous connected networks).

**Pairwise KS** (D emphasized over p, per instructions, given very large n):

| Pair | n1 | n2 | D | p |
|---|---|---|---|---|
| Bnei Re'em vs Mishmar | 23,423 | 52,542 | 0.582 | ~0 |
| Bnei Re'em vs Rehovot | 23,423 | 2,529 | 0.083 | 4.6e-14 |
| Mishmar vs Rehovot | 52,542 | 2,529 | 0.613 | ~0 |

Bnei Re'em and Rehovot have the most similar object-diameter distributions (D=0.083,
smallest of the three pairs) — consistent with Part A/B.

## Sanity checks

- **Subvolume-mean vs. full-volume porosity** (target: within 1–2 pp):
  - Bnei Re'em: 0.2209 (subvolume mean) vs. 0.2164 (full volume) — **0.45 pp**
  - Mishmar: 0.2767 vs. 0.2704 — **0.63 pp**
  - Rehovot: 0.3087 vs. 0.3050 — **0.37 pp**

  All well within tolerance.
- **30–150 µm fractions vs. existing curves**: plausible — Mishmar (fine loess) shows
  the highest 30–150µm fraction of pore volume (0.729), consistent with its PSD curve
  peaking sharply around 30µm; Rehovot (sand) peaks near 150–200µm (large interparticle
  pores) but still carries a substantial 30–150µm fraction (0.703); Bnei Re'em
  (Vertisol, shrink-swell cracks) has the lowest 30–150µm fraction (0.475) and by far
  the widest subvolume-to-subvolume spread, consistent with a bimodal fine-matrix +
  coarse-crack pore structure.
- **ANOVA vs. KW conflict**: none — all three Part-A metrics failed the
  normality/homogeneity check and used Kruskal-Wallis consistently; no case where the
  parametric and non-parametric results disagreed.

## Draft caption (for the figures draft, replacing the χ² sentence)

> Pore-size distributions were derived from eight non-overlapping cubic subvolumes
> per soil (4.50 mm edge for Bnei Re'em and Rehovot; 2.52 mm for Mishmar HaNegev,
> sized to each soil's physical sample extent) rather than a single ~45-million-voxel
> slab, using subvolumes as physical replicates. Porosity, median pore diameter, and
> the 30–150 µm ("microbially active") pore-volume fraction each differed
> significantly among soils (Kruskal-Wallis, p=0.011, p=0.00026, and p=0.0064
> respectively; ε²=0.34–0.69), with Bnei Re'em (Vertisol) showing the coarsest and
> most variable pore structure and Mishmar HaNegev (Loess) the finest (Dunn post-hoc,
> Holm-corrected; compact letters in Fig. 4). The full binned pore-size-distribution
> vectors also differed significantly among soils (PERMANOVA, Bray-Curtis,
> pseudo-F(2,21)=56.1, R²=0.84, p=0.0001; all three pairwise comparisons significant
> after Holm correction). Because each soil is represented by a single physical CT
> scan, these subvolumes are pseudo-replicates of one sample per soil type: the
> inference describes differences between these three scanned volumes, not soil
> types in general. Rehovot's pore mask was produced by a different (binary
> thresholding) segmentation method than the nnU-Net 3-class segmentations used for
> the other two soils, a methodological asymmetry noted here for transparency.

## Outputs in this folder

- `subvolume_extraction_manifest.json` — per-subvolume origin, porosity, exclusion check
- `rev_check_bnei_reem.{json,png}` — REV check
- `subvolume_metrics.csv` — Step 2 per-subvolume metrics
- `stats_results.json` — full Step 3 A/B/C results (all numbers above, machine-readable)
- `figure4_replacement.{png,svg}` — Figure 4 replacement panel
- `pore_objects/`, `pore_objects_summary.json` — Step 3C object-diameter arrays
- `psd_runs/` — all 25 individual PSD run folders (24 subvolumes + full-volume Rehovot)
- `scripts/` — all analysis scripts (extraction, REV, batch runner, aggregation, stats, figure)
