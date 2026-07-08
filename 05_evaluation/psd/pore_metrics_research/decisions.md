# Stage 1 Research Decisions — PSD module extension

**Implementation-target correction (Stage 2, 2026-07-07):** the metrics below were
originally (wrongly) implemented against `legacy/pores_analysis/` (dead code, not
imported anywhere live). They have since been re-implemented against the actual
live pipeline: `analysis/psd_topology_metrics.py` (new module) +
`analysis/psd_diagnostics_core.py` + `analysis/run_psd_diagnostics.py`'s new
`extended` CLI subcommand. The `legacy/pores_analysis/topology_metrics.py` /
`extended_pipeline.py` files were left in place but are unused dead code.

Papers physically present in `analysis/pore_metrics_research/papers/` (6 PDFs, identified by opening each and reading title/authors — filenames are DOI suffixes and do not match the reading-list names):

| File | Actual paper |
|---|---|
| `1-s2.0-S0016706116302737-main.pdf` | Jarvis, Larsbo & Koestel (2017), *Geoderma* 287:71-79, "Connectivity and percolation of structural pore networks in a cultivated silt loam soil quantified by X-ray tomography" |
| `1-s2.0-S0309170811002223-main.pdf` | Renard & Allard (2013), *Advances in Water Resources* 51:168-196, "Connectivity metrics for subsurface flow and transport" |
| `1-s2.0-S0309170815000317-main.pdf` | Herring, Andersson, Schlüter, Sheppard & Wildenschild (2015), *Advances in Water Resources* 79:91-102, "Efficiently engineering pore-scale processes: the role of force dominance and topology during nonwetting phase trapping" |
| `1-s2.0-S8756328297000070-main.pdf` | Odgaard (1997), *Bone* 20(4):315-328, "Three-Dimensional Methods for Quantification of Cancellous Bone Architecture" |
| `European J Soil Science ... VOGEL ...pdf` (filename says 2008, content is the original 1997 article) | Vogel (1997), *European Journal of Soil Science* 48:365-377, "Morphological determination of pore connectivity as a function of pore size using serial sections" |
| `Soil Science Soc of Amer J - 2013 - Ghanbarian ...pdf` | Ghanbarian, Hunt, Ewing & Sahimi (2013), *Soil Sci. Soc. Am. J.* 77:1461-1477, "Tortuosity in Porous Media: A Critical Review" |

**Not physically present** (cited in the Stage 1 prompt but absent from the folder): Jarvis is present so D1/D3 are fully covered; **Renard & Allard (2013) is present**; **Herring et al. (2015) is present**; **Odgaard (1997) is present**; **Ghanbarian et al. (2013) is present**. The one genuinely missing primary source is **Doube et al. (2010), the BoneJ paper** — not in the folder. Schlüter et al. (2022) and Gostick et al. (2019, the PoreSpy paper) are also not in the folder, but their functional content is superseded by directly inspecting the installed `porespy==3.0.4` API, per the prompt's own instruction for D5.

---

## D1 — "Connected / percolating pore" definition

**Resolved specification:** A pore voxel belongs to the "connected"/percolating subset if and only if it is part of a **26-connected** 3D connected component of the pore phase that contains at least one voxel touching the **top** Z-face (`z == 0`) **and** at least one voxel touching the **bottom** Z-face (`z == Z_max`) of the volume. Operationally:

```
labels = skimage.measure.label(pore_mask, connectivity=3)  # 26-connectivity in 3D
top_labels = set(labels[0, :, :].ravel()) - {0}
bottom_labels = set(labels[-1, :, :].ravel()) - {0}
percolating_labels = top_labels & bottom_labels
connected_mask = np.isin(labels, list(percolating_labels))
```

**Justification:** Jarvis, Larsbo & Koestel (2017) define the percolating pore fraction `F_p` explicitly as "the percolating pore space (i.e. connected to both the top and bottom of the sample)" and computed it "with the 'Open and closed porosity' algorithm in the Porodict module of GeoDict." They tested both 6-nearest-neighbour (face-only) and 26-nearest-neighbour (face+edge+corner) connectivity definitions and found the choice "has little effect on the fraction of the pore space that percolates for our samples" for real structured soils, with only marginal sensitivity in a random-medium comparison. Because the difference is small for structured soil pore networks and 26-connectivity is the more permissive/inclusive convention (matching `skimage.measure.label(connectivity=3)`'s standard default for full 3D connectivity and Renard & Allard's discussion of connectivity order choices), 26-connectivity spanning the Z-axis (top-to-bottom) was adopted as the operational definition, matching Jarvis's `F_p` metric.

**Confidence: High** — the core definition ("connected to both top and bottom of sample") is stated verbatim in the primary source; the specific choice of 26- over 6-connectivity is a defensible convention selection informed by the same paper's own sensitivity analysis (difference is negligible), not an ambiguous gap.

---

## D2 — Euler characteristic sign convention & normalization

**Resolved specification:**

1. Compute the raw Euler characteristic of the (unconditioned) pore phase using `skimage.measure.euler_number(pore_mask, connectivity=3)`. This computes χ = b0 − b1 + b2 (Betti numbers: number of components − number of independent loops/handles + number of enclosed cavities), the same alternating-sum convention as Renard & Allard's Eq. (2) and Herring et al.'s Eq. (5) — **no sign correction is needed relative to these two papers' convention.**
2. Apply a **sign flip** to obtain a "more-connected-is-higher" connectivity density, because both sources establish that a more negative raw χ indicates *more* connectivity (redundant loops/handles dominate as pores merge), while positive χ indicates a dominantly disconnected/isolated-cluster regime:
   `connectivity_density = -euler_number / sample_volume_mm3`
   where `sample_volume_mm3 = (n_voxels_total or n_pore_voxels) * (voxel_size_um / 1000)**3`. Normalize by **total sample volume** (not just pore volume) so the metric is comparable across samples of different porosity, matching the "connectivity density" naming convention (Euler number per unit volume) used in BoneJ-style bone-morphometry literature that Dor et al. (2025) draws its terminology from.
3. Units: connectivity density is reported in **mm⁻³** (loops per cubic millimeter of sample), computed via `voxel_size_um`, never raw voxel counts.

**Justification:** Renard & Allard (2013) define the Euler characteristic formally (Eq. 2, `φ(X) = Σ(-1)^i #e_i(X)`) as a topological invariant equal to (number of clusters − number of handles + number of holes) in 3D, and state explicitly that it becomes more negative as clusters merge and holes/handles proliferate near and above the percolation threshold. Herring et al. (2015) make the sign convention completely explicit for a pore-scale phase: "as Euler number becomes more and more negative, the NW phase fluid is becoming better connected" and "the transition from dominantly disconnected (χ > 0) to dominantly connected (χ < 0)." `skimage.measure.euler_number` implements the same b0 − b1 + b2 alternating-sum definition, so it is directly compatible with both papers without a sign correction at the raw-χ level — the sign flip we apply is purely to turn χ into a "bigger number = more connected" *reporting* convention, matching how connectivity density is conventionally presented in figures (e.g., Dor et al. 2025 Fig. S5, where higher bars mean more connected).

Herring et al.'s own normalization (Eq. 6, χ̂ = χ / χ at 100% saturation) is designed for a multi-saturation drainage/imbibition series and does not apply to our single-snapshot 3-phase segmentation (there is no saturation series here) — so it was **not** adopted directly; we substitute the standard bone-morphometry convention of normalizing by physical sample volume instead.

**Confidence: Medium.** The sign convention and the general Euler-characteristic definition are High confidence (directly stated in Renard & Allard and Herring et al.). However, **Doube et al. (2010), the BoneJ paper that Dor et al. (2025) actually used**, was not present in the papers folder, so BoneJ's exact edge-correction algorithm for computing a boundary-adjusted "Connectivity" (BoneJ assumes the sample is a single bounded connected solid and applies a specific edge-voxel correction before computing Connectivity Density) could not be verified directly. We used the general Euler-characteristic/volume-normalization relationship from the papers that ARE present as a defensible substitute for BoneJ's specific edge-correction step; **this substitution (no edge correction) is flagged Low confidence** and should be checked against BoneJ's actual `Connectivity.java` if exact reproduction of Dor et al.'s absolute values is later required.

---

## D3 — Connectivity probability (Γ) formula

**Resolved specification:**

```
Γ = Σ_i [ s_i * (s_i - 1) ] / [ (Σ_i s_i) * (Σ_i s_i - 1) ]
  ≈ Σ_i s_i^2 / (Σ_i s_i)^2      (large-domain approximation used in the paper)
```

where `s_i` is the size (voxel count) of pore cluster `i`, obtained from 26-connected labeling of the **full** pore phase (not just the percolating subset — Γ is defined over all clusters, matching Jarvis's Eq. 1). Γ is the probability that two randomly chosen pore voxels in the volume belong to the same connected cluster.

**Justification:** This is Jarvis, Larsbo & Koestel (2017) Eq. (1) verbatim: "the connection probability, Γ_p, ... is defined as the probability that two randomly chosen pore voxels in the ROI are connected (i.e. they belong to the same cluster)," given by `Γ_p = [Σ_i s_i(s_i−1)] / [(Σ_i s_i)(Σ_i s_i − 1)] ≈ Σ_i s_i² / (Σ_i s_i)²`. The paper is the sole primary source specified for D3 and gives the formula explicitly and unambiguously.

**Confidence: High** — formula is quoted directly and unambiguously from the primary source named in the prompt.

---

## D4 — Degree of anisotropy (MIL / fabric tensor) algorithm

**Resolved specification:**

1. Sample `N` (default N=100) roughly uniformly-distributed unit directions `ω_k` over a hemisphere using a Fibonacci-sphere sampling scheme.
2. For each direction `ω_k`, cast parallel sampling lines through the **connected** pore mask (D1's percolating subset — using the connected mask reduces edge/noise artifacts, consistent with Odgaard's requirement that the interface be well-defined) along that direction, scaled by `voxel_size_um` so line lengths are physical. Count the number of pore↔non-pore interface crossings along each line and accumulate total line length `L` and total intersection count over all lines for that direction.
3. Compute `MIL(ω_k) = L / (number of intersections)` per Odgaard's Eq. (6): "The mean intercept length (the mean length between two intersections) is simply the total line length divided by the number of intersections."
4. Fit a symmetric second-rank **fabric tensor** `M` (3×3) to the MIL data by least-squares, exploiting that a polar plot of 1/MIL(ω)² (or MIL(ω) itself, per convention) approximates an ellipsoid whose quadratic form is `ω^T M ω` (Odgaard, citing Whitehouse 1974 and the Harrigan & Mann 1984 tensor-fit method, also used by Jarvis et al. 2017's own anisotropy index via BoneJ).
5. Eigen-decompose `M` to get eigenvalues `λ1 ≥ λ2 ≥ λ3` (radii of the fitted ellipsoid).
6. Degree of anisotropy: `DA = 1 - (λ3 / λ1)`, ranging 0 (perfectly isotropic) to 1 (maximally anisotropic) — matching the BoneJ/Jarvis-reported anisotropy index convention ("varies between zero and one, where zero represents a perfectly isotropic structure").

**Library/implementation:** No existing Python or `porespy` implementation of full 3D MIL-based fabric-tensor anisotropy was found (porespy has no `anisotropy`/`fabric_tensor`/`MIL` function in the installed 3.0.4 API). **This must be implemented from scratch** — a Fibonacci-sphere direction sampler + ray-based intercept counter + least-squares ellipsoid/tensor fit + eigendecomposition (`numpy.linalg.eigh`).

**Justification:** Odgaard (1997) is the primary methodological source and directly describes: the MIL measurement principle (Eq. 6, Fig. 2a), the observation that a polar plot of MIL approximates an ellipsoid, and that this ellipsoid is the quadratic form of a second-rank "fabric tensor" (attributing the tensor-fit approach to Harrigan & Mann 1984 and Whitehouse). Jarvis et al. (2017) independently confirm this is the standard soil-CT practice: "the degree of anisotropy of the pore space was therefore computed in BoneJ using the mean intercept length method (Harrigan and Mann, 1984; Doube et al., 2010). This method gives an index of anisotropy which varies between zero and one, where zero represents a perfectly isotropic structure" — directly corroborating the `DA = 1 − λmin/λmax` formula chosen here.

**Confidence: Medium.** The overall MIL → fabric tensor → eigenvalue-ratio anisotropy pipeline structure is High confidence (stated directly in Odgaard 1997 and corroborated by Jarvis et al. 2017). However, **Doube et al. (2010)**, which would specify BoneJ's exact number/pattern of sampling directions and the precise least-squares fitting weights, **was not present in the papers folder**; the direction count (N=100, Fibonacci sampling) and the exact tensor-fit numerics are a defensible standard choice from general knowledge of MIL implementations, not verified against BoneJ's source — **this specific parameterization is flagged Low confidence**.

---

## D5 — Tortuosity: definition + computation method

**Resolved specification:** Use **diffusive tortuosity**, `τ_d = (⟨L_d⟩ / L_s)²` (Ghanbarian et al. 2013, Eq. 4), computed via the installed `porespy` (version 3.0.4, verified directly via `pip show porespy` / API inspection) function:

```python
porespy.simulations.tortuosity_fd(im, axis, solver=None)
```

which runs a finite-difference steady-state diffusion simulation along the specified axis and returns `tortuosity = (D_AB/D_eff) * effective_porosity`, i.e. the formation-factor-based diffusive tortuosity. This function **internally calls `trim_nonpercolating_paths`** before solving, meaning it **requires (and automatically derives) a connectivity-conditioned percolating pore mask along the chosen axis** — i.e. it consumes exactly the kind of connected/percolating subset defined in D1, though it computes its own trimming rather than requiring D1's mask to be passed in explicitly. We pass the same 3-phase-derived pore mask used for D1 (matrix/pore/POM → boolean pore==True) and iterate over `axis=0,1,2` (Z, Y, X) to report tortuosity in all three physical directions, in case of anisotropy.

**Justification:** Ghanbarian, Hunt, Ewing & Sahimi (2013) is the primary taxonomy source and defines exactly four tortuosity types — geometric, hydraulic, electrical, diffusive — and gives diffusive tortuosity explicitly as `τ_d = (⟨L_d⟩/L_s)²` (Eq. 4), i.e., precisely "how much longer is the real diffusive path vs. the straight-line distance," which is the quantity requested in the Stage 1 prompt. The paper also notes diffusive and electrical tortuosity are frequently equivalent under steady-state conditions, but diffusive tortuosity is the more directly applicable type here since the distance maps already computed by the existing PSD module are themselves diffusion/geometric-distance-based quantities, and porespy's actual installed function performs a genuine diffusion PDE solve (not a geometric shortest-path estimate), making it the closest available implementation to Ghanbarian's diffusive definition. The Gostick et al. (2019) PoreSpy paper itself was not found in the folder, but per the prompt's own instruction, the installed API was inspected directly (`porespy==3.0.4`, `porespy.simulations.tortuosity_fd`) rather than relying on the paper's (possibly outdated) description of the API.

**Confidence: High** — the tortuosity-type choice and formula are directly and unambiguously stated in Ghanbarian et al. (2013), and the specific porespy function was confirmed to exist and match by directly inspecting the installed package rather than guessing from the (absent) Gostick et al. paper.
