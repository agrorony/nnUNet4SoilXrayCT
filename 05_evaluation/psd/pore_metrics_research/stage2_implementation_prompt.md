# Prompt: Stage 2 — Implement PSD module extension (research decisions pre-resolved)

## Context

This repo already contains a Python module that computes pore-size distribution (PSD) from segmented soil X-ray CT volumes (matrix / pore / POM, 3-phase labels — same pipeline family as `nnUNet4SoilXrayCT` / `microsam_3d`). PSD is currently computed via a local-thickness / maximal-inscribed-sphere algorithm (BoneJ-equivalent), binned into pore-diameter size classes, following the method in Dor et al. (2025), *Agriculture, Ecosystems and Environment* 387, 109633.

All open research/methodological questions for this task were already resolved in Stage 1 and are recorded in `pore_metrics_research/decisions.md`. **This stage is implementation only — do not re-derive or second-guess those decisions; implement exactly what's specified in the blocks below.** If a block below still contains an unfilled `<!-- STAGE1-DECISION -->` marker (Stage 1 did not run or did not finish), stop and report that rather than guessing the missing specification yourself.

This task extends the existing PSD module — do not build a parallel pipeline.

## Task 0 — Locate and report before changing anything

1. Find the existing PSD-computing module in this repo (likely named something with `psd`, `pore_size`, `local_thickness`, or referencing BoneJ/`porespy`). Search imports/filenames across the repo.
2. Read it and report back, in a short summary before writing any code:
   - Its current function signatures (inputs: segmented volume array, voxel size, labels convention — which integer = matrix/pore/POM; outputs: what table/object it returns).
   - What library it currently uses for local thickness (custom, `porespy.filters.local_thickness`, or other).
   - What its current pore-size bins are.
   - What output format it currently produces (CSV row per sample? in-memory dataframe? plots already?).
3. Only after this reconnaissance, proceed to implementation. If the module does not exist / cannot be found, stop and ask rather than guessing its interface.

## Inputs (for all new functions below)

- `volume`: 3D integer-labeled array (matrix / pore / POM), same convention as the existing PSD module.
- `voxel_size_um`: physical voxel edge length in µm (isotropic, as in the paper's 5 µm scans) — must be used everywhere so results are in real physical units, not voxel counts.

## New functionality to add

### 1. Connectivity-conditioned distance maps

<!-- STAGE1-DECISION: D1 -->
**Resolved (decisions.md D1, High confidence):** A pore voxel is "connected/percolating" iff it belongs to a **26-connected** (`skimage.measure.label(pore_mask, connectivity=3)`) 3D component whose voxel set touches **both** the top Z-face (`z==0`) and the bottom Z-face (`z==Z_max`) of the volume:
```python
labels = skimage.measure.label(pore_mask, connectivity=3)
top_labels = set(labels[0, :, :].ravel()) - {0}
bottom_labels = set(labels[-1, :, :].ravel()) - {0}
percolating_labels = top_labels & bottom_labels
connected_mask = np.isin(labels, list(percolating_labels))
```
Per Jarvis, Larsbo & Koestel (2017, Geoderma 287:71-79): percolating pore space F_p is defined as "connected to both the top and bottom of the sample"; 26- vs 6-connectivity was shown to have "little effect" on percolating fraction for structured soil, so the more permissive/standard 26-connectivity was adopted.
<!-- END-DECISION -->

Implementation using the above definition:
- Label connected components of the **pore phase** in 3D per the connectivity order specified above.
- Identify the "connected" subset per the definition above.
- Build the Euclidean distance transform (`scipy.ndimage.distance_transform_edt`, with `sampling=(voxel_size_um,)*3` so output is in µm) using **only the connected pore subset** as the target/foreground. Keep the existing unconditioned version (all pores) alongside it for comparison — do not replace it.
- Apply the same conditioned/unconditioned pair to distance-to-POM as a secondary variant (lower priority than the pore-side conditioning if time-constrained).
- Function signature: `distance_map(volume, target_label, voxel_size_um, connected_only=False) -> np.ndarray` (returns the full distance map, not just its mean — see Output requirements below).

### 2. Add 30–150 µm pore-size bin

- In the existing PSD binning step, add a `30–150 µm` bin edge exactly matching Dor et al. (2025), alongside whatever bins the module already has.
- No new algorithm needed — reuses the same local-thickness output already computed by the module; purely a binning/reporting change.

### 3. Euler characteristic / connectivity density

<!-- STAGE1-DECISION: D2 -->
**Resolved (decisions.md D2, Medium confidence; edge-correction detail flagged Low):** Compute raw Euler number via `skimage.measure.euler_number(pore_mask, connectivity=3)` — this uses the same χ = b0 − b1 + b2 alternating-sum convention as Renard & Allard (2013) Eq.(2) and Herring et al. (2015) Eq.(5), so **no sign correction is needed at the raw-χ level**. To report a "more-connected-is-higher" **connectivity density**, apply a sign flip and normalize by physical sample volume (not voxel counts, not BoneJ's edge-corrected "Connectivity"):
```python
connectivity_density = -euler_number / sample_volume_mm3   # units: mm^-3
# sample_volume_mm3 = n_voxels_total * (voxel_size_um / 1000) ** 3
```
Justification: Herring et al. (2015) state explicitly "as Euler number becomes more and more negative, the NW phase fluid is becoming better connected" (χ<0 = more connected, χ>0 = more disconnected) — hence the sign flip to make the reported metric increase with connectivity. Herring's own saturation-series normalization (χ/χ_100%sat) does not apply to a single-snapshot volume, so plain volume-normalization is used instead. **Low confidence caveat:** Doube et al. (2010), the actual BoneJ paper Dor et al. (2025) used, was not available in the papers folder, so BoneJ's specific edge-voxel correction algorithm (applied before computing "Connectivity"/"Connectivity Density" in BoneJ) is NOT reproduced here — only the general Euler-characteristic/volume-normalization relationship from the available papers.
<!-- END-DECISION -->

Implementation using the above: compute the topological Euler number of the pore phase and normalize per the specification above.

### 4. Connectivity probability (Γ)

<!-- STAGE1-DECISION: D3 -->
**Resolved (decisions.md D3, High confidence):** Label the full pore phase with 26-connectivity, let `s_i` = voxel count of cluster `i` (over ALL clusters, not just the percolating subset). Then, per Jarvis, Larsbo & Koestel (2017) Eq.(1):
```
Γ = Σ_i [s_i*(s_i-1)] / [(Σ_i s_i)*(Σ_i s_i - 1)]  ≈  Σ_i s_i^2 / (Σ_i s_i)^2
```
Γ is "the probability that two randomly chosen pore voxels in the ROI are connected (i.e. they belong to the same cluster)."
<!-- END-DECISION -->

Implementation using the above: will very likely reuse the connected-component labeling from step 1.

### 5. Degree of anisotropy

<!-- STAGE1-DECISION: D4 -->
**Resolved (decisions.md D4, Medium confidence; direction-count/fit-weight specifics flagged Low):** No existing Python/porespy implementation found — **write from scratch**:
1. Sample N=100 unit directions via Fibonacci-sphere sampling over a hemisphere.
2. For each direction, cast parallel physical-length (`voxel_size_um`-scaled) sampling lines through the connectivity-conditioned pore mask (from D1) and count pore/non-pore interface crossings; `MIL(ω) = total_line_length / n_intersections` (Odgaard 1997 Eq. 6).
3. Least-squares fit a symmetric 3x3 fabric tensor `M` to the MIL(ω) samples (ellipsoid quadratic form `ω^T M ω`, per Odgaard 1997 / Harrigan & Mann 1984 tensor-fit approach).
4. Eigen-decompose `M` (`numpy.linalg.eigh`) → λ1≥λ2≥λ3.
5. `DA = 1 - (λ3/λ1)` (0=isotropic, 1=max anisotropic) — matches the BoneJ/Jarvis-reported anisotropy index convention.
<!-- END-DECISION -->

Implementation using the above specification. Report which library/implementation was used.

### 6. Tortuosity

<!-- STAGE1-DECISION: D5 -->
**Resolved (decisions.md D5, High confidence):** Use **diffusive tortuosity**, `τ_d = (⟨L_d⟩/L_s)²` (Ghanbarian et al. 2013 Eq. 4) — the type that directly matches "how much longer is the real diffusive path vs straight-line distance." Installed `porespy==3.0.4` provides `porespy.simulations.tortuosity_fd(im, axis, solver=None)`, which runs a finite-difference steady-state diffusion solve and returns `tortuosity = (D_AB/D_eff) * effective_porosity`. This function internally calls `trim_nonpercolating_paths` (it derives its own percolating subset along the chosen axis), so pass it the boolean pore mask (pore==True) directly; iterate `axis=0,1,2` to get tortuosity along Z/Y/X. No custom fallback needed — the function exists and matches in the installed version.
<!-- END-DECISION -->

Implementation using the above specification. If `porespy` is not already a dependency, add it as a normal dependency addition (update `environment.yml`).

### 7. Surface area by pore-size class

- Extend the existing whole-image pore surface area calculation (likely via `skimage.measure.marching_cubes` + `mesh_surface_area`, matching the paper's "3D triangle mesh" method) to be computed **per pore-size bin** (mask the pore phase by its local-thickness bin, including the new 30–150 µm bin, before running marching cubes on each masked subset) instead of only once for the whole pore phase.

## Output requirements

For each processed sample/volume, produce:

1. **Graphs**, consistent in style with the paper's own figures (bar charts with means ± SE/CI across replicates/land-uses if multiple samples are batched, similar to Figs. 2–4 and S2–S5): one plot per new metric (PSD with the new 30–150 µm bin, Euler/connectivity density, Γ, tortuosity, anisotropy, surface area by size class). Use `matplotlib`.
2. **A saved distance-from-POM map**: not just the scalar mean, but the actual 3D (or a representative 2D mid-slice, matching Fig. 1b's style in the paper) distance map written to disk (e.g., `.tif`), for both the unconditioned and connectivity-conditioned variants.
3. Append the new scalar metrics (Euler/connectivity density, Γ, tortuosity, anisotropy, per-class surface area, new 30–150 µm PSD bin value) as **new columns to whatever output table the existing PSD module already produces** — do not create a second, separate results table.

## Constraints

- Do not rewrite or replace the existing PSD/local-thickness computation — extend it.
- Every new physical-unit metric must use `voxel_size_um`, not raw voxel counts.
- Do not re-derive or alter the resolved decisions above — if one is still an unfilled placeholder, stop and report rather than guessing.
- Implement full logic, not scaffolding.

## Done when

- Task 0's reconnaissance summary has been reported back before any new code was written.
- All 7 new pieces of functionality are implemented and integrated into the existing module (not a parallel pipeline).
- Running the module end-to-end on a real or synthetic 3-phase segmented test volume produces: the extended results table (existing columns + new ones), the full set of graphs, and both distance-from-POM map variants (unconditioned + connectivity-conditioned) written to disk, with no errors.
- A short final summary confirms which Stage 1 decisions were used and their confidence flags (from `decisions.md`), so anything flagged Low confidence can be double-checked later.
