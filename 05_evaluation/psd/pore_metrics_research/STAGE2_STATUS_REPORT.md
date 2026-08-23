# PSD module extension — status report (reconstructed 2026-07-22)

Session that ran this work was lost, but everything is committed on `main`
(reorg commit `d90e0bd` and later — nothing uncommitted, no side branch).
Reconstructed from the recovered planning docs and the actual code/output on disk.

**Bottom line: all 7 items are implemented and wired into the live pipeline
(not a parallel one), and were run end-to-end on a real cropped CT subvolume
with no crashes.** Two of the seven have flagged confidence issues from
Stage 1 (unresolved without the BoneJ/Doube et al. 2010 paper), and one
diffusion solver logged a convergence warning worth double-checking.

## Where things live

- Plan docs: [`stage1_research_prompt.md`](stage1_research_prompt.md), [`decisions.md`](decisions.md), [`stage2_implementation_prompt.md`](stage2_implementation_prompt.md) (all in this folder).
- Implementation: [`../psd_topology_metrics.py`](../psd_topology_metrics.py) (new module, pure numpy/scipy/skimage + lazy porespy).
- Integration: [`../psd_diagnostics_core.py`](../psd_diagnostics_core.py) (`build_extended_psd_table`, extended plotting) and [`../run_psd_diagnostics.py`](../run_psd_diagnostics.py) (new `extended` CLI subcommand, `_run_extended`).
- **Dead-end to ignore:** `05_evaluation/legacy_pores_analysis/topology_metrics.py` + `extended_pipeline.py`. An earlier agent run built the same functionality against this dead module first (nothing live imports it); it was superseded by the version above and left in place unused. Its `environment.yml`, however, is real and is the one declaring the new `porespy`/`openpnm` deps.
- Validation run output (real data, not synthetic): [`validation_run/out/psd_diag_20260707T134721_bnei_reem_i4_crop200/`](validation_run/out/psd_diag_20260707T134721_bnei_reem_i4_crop200/) — a 100×200×200 voxel crop (`sub_z200_300_crop200.nii.gz`) of bnei_reem iter4 predictions, 5 µm voxels, porosity 0.3565. Log: [`validation_run/run_crop200.log`](validation_run/run_crop200.log).

## Status by item

### 1. Connectivity-conditioned distance maps — ✅ Implemented, integrated, run
`get_percolating_mask()` + `distance_map_from_mask()` / `distance_map()` in `psd_topology_metrics.py`. Wired into `_run_extended()`, produces 4 `.tif` variants (pore unconditioned/conditioned, POM unconditioned/conditioned) plus mid-slice `.tif`s and a combined `extended_distance_maps_midslice.png`. All 8 files present in the validation output. **D1 definition:** High confidence — 26-connectivity, top/bottom Z-face percolation, directly stated in Jarvis, Larsbo & Koestel (2017).

### 2. 30–150 µm PSD bin — ✅ Implemented, integrated, run
`add_pore_size_bin()` merges the 30/150 µm edges into whatever bin set already existed; no new algorithm, pure binning change as specified. Validation run's `psd_20bins_30_150um.png` and `PSD_30_150um_Volume_Fraction` column (= 0.571 in the crop) confirm it ran. No open question here — this item had no Stage-1 ambiguity.

### 3. Euler characteristic / connectivity density — ✅ Implemented, integrated, run — ⚠️ Medium/Low confidence
`connectivity_density()` uses `skimage.measure.euler_number(pore_mask, connectivity=3)`, sign-flipped and normalized by total sample volume (mm⁻³). Validation run: Euler number 56, connectivity density −112 mm⁻³.
**Open/unverified (D2):** the *general* Euler/sign-convention (Renard & Allard 2013, Herring et al. 2015) is High confidence, but **BoneJ's specific edge-voxel correction** (which Dor et al. 2025 actually used, via Doube et al. 2010) was never verified — that paper wasn't in the papers folder. Current numbers are **not guaranteed to match Dor et al.'s absolute values**, only its sign/scaling convention. Flagged Low confidence in `decisions.md` D2.

### 4. Connectivity probability (Γ) — ✅ Implemented, integrated, run — High confidence, fully resolved
`connectivity_probability()` implements Jarvis, Larsbo & Koestel (2017) Eq. 1 verbatim (Σsᵢ(sᵢ−1) / Σsᵢ(Σsᵢ−1), full pore phase, not just percolating subset). Validation run: Γ = 0.881. No open questions — formula was quoted directly from the sole cited source.

### 5. Degree of anisotropy (MIL/fabric tensor) — ✅ Implemented, integrated, run — ⚠️ Medium/Low confidence
Written from scratch (no existing Python/porespy implementation exists) in `psd_topology_metrics.py`: Fibonacci-hemisphere direction sampling (N=100) → vectorized ray-cast MIL per direction (`_mean_intercept_length`, via `map_coordinates`) → least-squares fabric-tensor fit → eigendecomposition → `DA = 1 − λmin/λmax`. Validation run: DA = 0.271.
**Open/unverified (D4):** the overall MIL→tensor→eigenvalue-ratio pipeline is High confidence (Odgaard 1997, corroborated by Jarvis et al. 2017), but the specific parameterization (N=100 directions, 400 lines/direction, least-squares fit weights) is a defensible default, **not verified against BoneJ's actual `Anisotropy` plugin** (Doube et al. 2010 unavailable). If exact reproduction of a BoneJ-computed DA is later needed, this is the piece to check first.

### 6. Tortuosity — ✅ Implemented, integrated, run — ⚠️ ran with a solver warning
`tortuosity_diffusive()` calls `porespy.simulations.tortuosity_fd(im, axis)` per axis (0/1/2), diffusive tortuosity per Ghanbarian et al. (2013) Eq. 4. `porespy`/`openpnm` were added as real dependencies (see `05_evaluation/legacy_pores_analysis/environment.yml:27-28`, with a documented numpy-version pin conflict resolution: `numpy<=2.4.6` needed to satisfy both openpnm/scipy and numba/porespy simultaneously).
Validation run produced values (axis0=1.65, axis1=6.07, axis2=3.01) but the log shows:
```
WARNING  Found non-percolating regions, were filled to percolate   (x3)
ERROR    Inlet/outlet rates don't match: 1.1155e+01 vs. -1.1154e+01
```
This is porespy's own internal diffusion-solver sanity check (`porespy/simulations/_dns.py:108`), not a bug in our code — but it did **not** abort the run, and axis1's much larger value (6.07 vs 1.65/3.01) alongside that mismatched-rate error suggests **axis1's tortuosity result should be treated as suspect/unverified** rather than trusted at face value. Worth rerunning on a larger/less axis1-constrained crop before citing this number.

### 7. Surface area by pore-size class — ✅ Implemented, integrated, run
`surface_area_by_size_class()` extends the existing whole-volume marching-cubes surface-area calc to run per size-bin (masks pore phase by local-thickness bin first, pads by 1 voxel, skips bins with <8 voxels). Produces a `Surface_Area_um2` column per bin row in the extended table and `extended_surface_area_by_class.png`. No Stage-1 ambiguity flagged for this item — straightforward extension as specified.

## Output integration (per the "done when" checklist)

- Extended results table: **same** `psd_table.csv`/`psd_raw_data.csv` files as the existing pipeline, with new columns appended (`Surface_Area_um2`, `Euler_Number`, `Connectivity_Density_per_mm3`, `Connectivity_Probability_Gamma`, `Degree_of_Anisotropy`, `Tortuosity_Axis0/1/2`, `PSD_30_150um_Volume_Fraction`) — confirmed no second/parallel table was created (`build_extended_psd_table()` in `psd_diagnostics_core.py`).
- Plots: `psd_20bins_30_150um.png`, `psd_kde.png`, `extended_distance_maps_midslice.png`, `extended_connectivity_topology_metrics.png`, `extended_tortuosity.png`, `extended_surface_area_by_class.png` — all present in the validation run.
- Distance-to-POM maps: both unconditioned and connected variants written as full-volume `.tif` + mid-slice `.tif`, matching the spec.
- Ran via the pipeline's own CLI (`run_psd_diagnostics.py ... extended`), not a bespoke script — genuinely integrated, not a side pipeline.

## What to prioritize next (suggested, for advisor discussion)

1. **Axis-1 tortuosity solver mismatch** — rerun on a bigger/less-constrained volume and check whether the "inlet/outlet rate mismatch" error recurs; if so this metric isn't trustworthy yet.
2. **BoneJ cross-check (items 3 & 5)** — both open confidence flags trace back to the same missing source, Doube et al. (2010). If reproducing Dor et al. (2025)'s absolute connectivity-density/anisotropy numbers matters, that paper needs to be sourced and D2/D4 revisited.
3. Everything else (items 1, 2, 4, 7, and the overall integration) is on solid footing and has run cleanly on real data — safe to treat as done.
