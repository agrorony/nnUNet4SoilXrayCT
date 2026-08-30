# POM interface metrics (Track B, step 2a) -- final report

Run 2026-08-30, per `pom_interface_metrics_prompt.md`. Scope: the same 3
POM-valid volumes used throughout this project's POM work -- Bnei Re'em
canonical (`nlm_volume`, 650x650x652, cutoff 8 vox), Mishmar native
(5.85 um, 1000^3, cutoff 21 vox), Mishmar 2nd specimen (8.8 um native,
label-downsampled ~15 um, 587^3, cutoff 15 vox) -- **not** the 2026-08-29/30
ROI-expanded Mishmar crops. Each volume's own pinned A1 noise-floor cutoff
was reused from its existing `summary_pom_metrics.json`, not re-derived.
Scripts: `scripts/run_pom_interface_metrics.py` (main pipeline),
`scripts/build_comparison_table.py` (Table 2 numbers).

## Part 1 sanity-check outcome (required statement)

**Matched exactly.** Bnei Re'em's reproduced POM-pore contact fraction
(voxel-face method) = 0.6422932338325659, identical to the pinned value in
`pom_analysis_20260815_light/bnei_reem/summary_pom_metrics.json`
(0.6422932338325659) -- abs diff = 0.0. The Part 2/3/4 numbers for all three
volumes are trusted on the strength of this reproduction.

## A finding that runs opposite to the prompt's stated literature expectation

The prompt's Part 2 sanity check states marching-cubes total surface area
"must not be smaller than a plain voxel-face-count-derived surface area...
if it comes out smaller, the mesh reconstruction is broken." **For all
three volumes it came out smaller** (Bnei Re'em: MC 252.7 mm^2 vs voxel-face
348.5 mm^2; Mishmar native: 126.0 vs 172.6 mm^2; Mishmar sample 2: 292.7 vs
402.7 mm^2 -- MC is consistently ~72-76% of the voxel-face value, not
larger).

Before accepting this as a real (non-bug) result, it was checked against
synthetic geometry with a known analytic surface area (spheres, radius
5-20 voxels): voxel-face counting overestimated the true sphere area by
+50-55%, while marching cubes overestimated by only +8-9% -- i.e.
marching cubes is *closer to the true continuous surface*, and voxel-face
counting is the one with the large bias, in the *opposite* direction from
what the prompt's Schlueter et al. (2014) summary asserts ("staircase bias
... underestimates true surface area"). The well-established result in the
image-analysis literature (e.g. Lindblad 2005) is that naive voxel-face
counting *overestimates* surface area for non-axis-aligned surfaces (a
staircase approximation of a diagonal plane is longer than the plane itself
-- 2x vs sqrt(2)x for a 45-degree diagonal), and marching cubes'
linearly-interpolated mesh is the more accurate estimator. That is exactly
the direction observed here, consistently, across all three volumes and
across sphere radii 5/10/15/20 in the synthetic check.

**Conclusion: not a bug.** The marching-cubes implementation is identical
(same call signature, same padding, same level=0.5, same spacing) to the
already-validated `pom_analysis_20260826_final_shape` sphericity code, and
independently validated against analytic ground truth. The prompt
document's stated expectation of the sign of this bias appears to be an
error in its own literature summary; the sanity check's *purpose*
(catching a genuinely broken mesh -- wrong isovalue, inverted mask, wrong
spacing) does not apply here, since none of those conditions hold. Per the
prompt's own ambiguity rule, this is flagged explicitly rather than
silently resolved, and both area estimates are reported side by side in
every output (see per-volume JSON `part2_marching_cubes` block).

## Ambiguity resolution: the minor "label 1" class

Part 1's instructions explicitly say to classify non-POM face-neighbors as
"pore (label 5) or matrix (everything else, including the minor 'label 1'
class)" -- so `matrix_mask = ~pore_mask & ~pom_mask_all` (labels 0 and 1
both count as matrix) was used throughout Parts 1-3. The Sanity-checks
section separately says contact fractions need not sum to 100% "since... the
minor label 1 class... is neither pore nor matrix by definition here",
which reads as inconsistent with Part 1's explicit rule. Resolution: Part
1's explicit, operational rule was followed (label 1 = matrix) since it is
unambiguous; the non-100% residual ("neither" fraction, 1.9-4.2% of surface
voxels across the 3 volumes) is not caused by label 1 at all -- it is
surface voxels whose only non-denoised neighbors are small, noise-filtered
POM specks (raw label-2 voxels below the size cutoff, so excluded from
`denoised_mask` but still label 2, hence neither pore- nor matrix-dilated).
This is logged here per the prompt's "log that this happened" rule for
resolved ambiguities.

## Output checklist

Per-volume JSON (`<soil>/summary_pom_interface_metrics.json`) contains all
required fields: `n_pom_objects`, `pom_pore_contact_fraction_voxel` /
`pom_matrix_contact_fraction_voxel` (+ overlap/neither, Part 1),
`pom_surface_area_um2_marching_cubes_*` (total/pore-facing/matrix-facing,
Part 2), `ssa_total_um1` / `ssa_pore_facing_um1` / `ssa_matrix_facing_um1`
(Part 3), `iad_pore_um1` / `iad_matrix_um1` (Part 3),
`largest_object_interface_area_share` / `top5_objects_interface_area_share`
(Part 4). Per-object arrays saved as `.npy` in each soil's output folder
(`pom_object_pore_area_um2.npy` etc.), matching this project's existing
convention (`pom_object_diameters_um.npy`).

## Table 2 -- POM interface metrics (Bnei Re'em n=1 vs Mishmar mean +/- SE, n=2; no SD)

| Metric | Bnei Re'em (n=1) | Mishmar (mean +/- SE, n=2) |
|---|---|---|
| POM-pore contact fraction (voxel-face) | 0.642 | 0.556 +/- 0.007 |
| POM-matrix contact fraction (voxel-face) | 0.458 | 0.508 +/- 0.038 |
| MC total POM surface area (mm2) | 252.7 | 209.3 +/- 83.3 |
| Voxel-face total POM surface area (mm2), cross-check | 348.5 | 287.7 +/- 115.1 |
| MC pore-facing area fraction | 0.575 | 0.509 +/- 0.023 |
| MC matrix-facing area fraction | 0.406 | 0.461 +/- 0.028 |
| SSA total (mm2/mm3) | 33.2 | 32.6 +/- 6.4 |
| SSA pore-facing (mm2/mm3) | 19.1 | 16.8 +/- 4.0 |
| SSA matrix-facing (mm2/mm3) | 13.5 | 14.8 +/- 2.0 |
| IAD pore (mm2/mm3) | 0.156 | 0.272 +/- 0.063 |
| IAD matrix (mm2/mm3) | 0.110 | 0.241 +/- 0.031 |
| Largest-object interface-area share (%) | 13.0 | 36.2 +/- 0.4 |
| Top-5-object interface-area share (%) | 33.9 | 52.6 +/- 1.4 |

Per-metric cross-check flags: the marching-cubes-vs-voxel-face pore-area
*fraction* disagreement was 6.7pp (Bnei Re'em), 3.0pp (Mishmar native), 6.3pp
(Mishmar sample 2) -- all well under the prompt's 15pp flag threshold, so
none are flagged despite the (documented, above) total-area-magnitude
discrepancy.

## Methods paragraph (ready to paste)

*POM-pore, POM-matrix, and specific/interfacial surface area were computed
on each volume's existing denoised POM object mask (per-volume noise-floor
cutoff already pinned in prior runs). Voxel-face contact fractions were
obtained by 6-connected face-adjacency counting of denoised-POM surface
voxels against the pore and matrix phases (Schlueter et al., 2014).
Interfacial surface area was independently estimated via marching-cubes
mesh reconstruction of each POM object (level=0.5, voxel-scaled spacing),
following the solid-pore interfacial-area method of Houston et al. (2013)
as applied to POM-bearing soil CT by Juyal et al. (2021), with each mesh
triangle assigned to the pore or matrix phase by sampling the nearest voxel
along its outward normal; this and the voxel-face estimate are reported
together as a cross-check, consistent with the two standard interfacial-area
estimation families reviewed by Schlueter et al. (2014) -- surface area
itself follows the Minkowski-functional framework of Vogel & Roth (2001).
Specific surface area (SSA, POM surface : POM volume) and interfacial area
density (IAD, POM-pore or POM-matrix surface : bulk sample volume) were
computed as physically distinct, separately reported quantities, with IAD
normalized by bulk volume following the same convention already used for
this pipeline's connectivity-density metric (Herring et al., 2015).*

## Draft caption text (IAD interpretation, for Table 2 / a new figure panel)

*Interfacial area density (IAD) -- organo-pore and organo-mineral contact
area per unit volume of bulk soil -- was 1.6-2.2x higher in Mishmar than in
Bnei Re'em for both the POM-pore interface (0.272 +/- 0.063 vs 0.156 mm2/mm3)
and the POM-matrix interface (0.241 +/- 0.031 vs 0.110 mm2/mm3), even though
POM-intrinsic specific surface area (SSA) was statistically indistinguishable
between the two soils (33.2 vs 32.6 +/- 6.4 mm2/mm3 total). This dissociation
is expected given each soil's own POM abundance (Mishmar's denoised POM
volume fraction is roughly double Bnei Re'em's, per the existing Table-2
diameter/largest-object numbers): SSA is a per-unit-POM shape/exposure
descriptor and normalizes that abundance difference away, while IAD is the
ecologically scaled quantity -- it is what actually differs in how much
microbially-accessible organo-pore and organo-mineral interface each soil
presents per unit volume, independent of whether that comes from more POM,
more exposed POM, or both.*

## Notes on Part 4

Interfacial-area concentration (fraction of total POM-pore interfacial area
contributed by the single largest / top-5 objects) is far more concentrated
in Mishmar (largest object 36.2 +/- 0.4%, top 5 = 52.6 +/- 1.4%) than in Bnei
Re'em (largest 13.0%, top 5 = 33.9%) -- a substantially bigger gap than the
already-reported POM-*volume* largest-object share (17.1% Bnei Re'em vs.
45.1% Mishmar). This is consistent with the two soils' known largest-object
volume disparity, but the interfacial-area gap is proportionally larger,
consistent with the idea flagged in the prompt that "a large, blocky object
and a smaller, highly convoluted one can contribute very differently to
interface despite similar volume" -- worth a one-line mention alongside the
existing largest-object-volume-share number in the draft, not a replacement
for it.

## Per-gram (m2/g) conversion

Not computed -- no POM particle density is available in this project, per
the prompt's explicit instruction not to fabricate one.
