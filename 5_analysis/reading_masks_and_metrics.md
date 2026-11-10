# Reading the masks and metrics from a full-volume PSD/topology run

This is a reference for interpreting the layers opened by
`napari_view_full_volume.py` (and `napari_view_connectivity_validation.py`,
its crop-only predecessor) alongside the numeric output of an `extended`-mode
`run_psd_diagnostics.py` run. It answers two questions: *what am I looking
at*, and *which number in `summary.json` / `psd_table.csv` does it feed*.

## Opening the viewer

```
python napari_view_full_volume.py \
    --run-dir   <psd_outputs>/psd_diag_<timestamp>_<run_name> \
    --segmentation <...>/inference_concatenated/<sample>.nii.gz \
    --raw-source   <...>/nifti_predict/<sample>_0000.nii.gz
```

`--run-dir` must be a run produced with `extended` mode (it needs the
`distance_to_*.tif` files, which `real` mode doesn't write). `--segmentation`
and `--raw-source` must be shape-identical — the script refuses to open
layers whose shapes don't match rather than silently rendering something
misaligned.

## Layer quick-reference

| Layer (napari name) | What it is | Source file | Feeds |
|---|---|---|---|
| `volume` | Raw grayscale CT | `nifti_predict/<sample>_0000.nii.gz` | Visual context only — not a metric input |
| `segmentation (matrix/pore/POM)` | Per-voxel class label | `inference_concatenated/<sample>.nii.gz` | `pore_mask` (label 5) and `pom_mask` (label 2) below, which everything else derives from |
| `connected pore mask (percolating, axis=0)` | Subset of `pore_mask` that spans the full volume top-to-bottom | computed live via `get_percolating_mask(pore_mask, axis=0)` | Connectivity density, Gamma, anisotropy, tortuosity (see below) |
| `distance-to-pore (unconditioned, um)` | Distance from every voxel to the nearest pore voxel | `distance_to_pore_unconditioned.tif` | Diagnostic/visual only (not currently a scalar metric) |
| `distance-to-pore (connected/percolating, um)` | Distance to the nearest *connected* pore voxel | `distance_to_pore_connected.tif` | Diagnostic/visual only |
| `distance-to-POM (unconditioned, um)` | Distance to the nearest POM voxel | `distance_to_pom_unconditioned.tif` | Diagnostic/visual only |
| `distance-to-POM (connected/percolating, um)` | Distance to the nearest *connected* POM voxel | `distance_to_pom_connected.tif` | Diagnostic/visual only |

The four distance maps are **not themselves reduced to a scalar** anywhere in
the current pipeline — they exist for visual/spatial inspection (e.g. "how
far is any point in the matrix from the nearest connected pore, and does
that pattern look physically reasonable"). The scalar topology metrics all
come from the segmentation and the connected-pore mask directly, listed below.

## Label convention (important caveat)

`dataset_info.json` documents a 7-class scheme (0=ToPredict, 1=Matrix,
2=Stones, 3=POM_type1, 4=POM_type2, 5=unused, 6=Pore). **The actual deployed
segmentation outputs do not use that scheme.** Verified via `np.unique()` on
both the `nlm_volume` and `mishmar_hanegev_maoz_3_5p85um` full-volume
outputs: only labels `{0, 1, 2, 5}` are ever present.

- `0` — background/matrix majority class
- `1` — a minor class (~1–2% of volume); **not independently confirmed**,
  treated as not-pore/not-POM by every metric below
- `2` — POM (particulate organic matter) — matches the pore/POM convention
  used in every validated run to date (crop200, zcenter200, and both full
  runs)
- `5` — pore — the dominant non-matrix class (~20–40% of volume, consistent
  with expected soil porosity)

Always pass `--pore-label 5 --pom-label 2` (the viewer's and
`run_psd_batch.py`'s defaults) for these models, not the `dataset_info.json`
numbers.

## Metrics reference (`summary.json` / `result_psd.json` / `psd_table.csv`)

### Pore-size distribution (base, every run)

| Field | Meaning |
|---|---|
| `total_pore_voxels` | Count of voxels with `label == pore_label`, after 1-voxel border exclusion |
| `bin_centers_um` / `bin_edges_um` | Pore-diameter bins (log-spaced by default, plus a forced 30–150 µm bin) |
| `volume_counts` | Voxel count per diameter bin, from the local-thickness/opening-map computation (this is what the EDT + chunking pipeline produces) |
| `cumulative_volume` / `differential_volume` | Cumulative and differential PSD curves (the two histogram-style PNGs) |
| `psd_30_150um_volume_fraction` | Fraction of total pore volume in the 30–150 µm class — the "microbial active domain" range from Dor et al. 2025 |

### Topology/connectivity (extended mode only)

| Field | Computed from | Meaning |
|---|---|---|
| `euler_number` | full `pore_mask` (label 5), 26-connectivity | Euler characteristic χ = b0 − b1 + b2 (components − loops + cavities) |
| `connectivity_density_per_mm3` | full `pore_mask` | `-euler_number` normalized by sample volume in mm³, sign-flipped so **higher = more connected** (Herring et al. 2015 convention) |
| `connectivity_probability_gamma` | full `pore_mask` | Probability two random pore voxels are in the same 26-connected cluster (Jarvis, Larsbo & Koestel 2017). Ranges 0–1; closer to 1 means the pore space is dominated by one giant connected cluster rather than fragmented into many small ones |
| `degree_of_anisotropy` | **connected pore mask only** (falls back to full `pore_mask` if the connected mask is empty) | Mean-intercept-length fabric tensor (Odgaard 1997). 0 = isotropic, 1 = maximally anisotropic (all pore space aligned along one direction) |
| `anisotropy_eigenvalues` / `anisotropy_fabric_tensor` | same | The 3 eigenvalues and full 3×3 tensor behind `degree_of_anisotropy` — eigenvalue ordering (Z,Y,X) tells you *which* axis the pore space favors, not just how strongly |
| `tortuosity_axis0/1/2` | full `pore_mask` (porespy internally derives its own connectivity-conditioned subset per axis) | Diffusive tortuosity τ_d = (⟨L_d⟩/L_s)², per axis. 1 = straight-line diffusion path, higher = more tortuous |
| `Surface_Area_um2` (per PSD bin, in `psd_table.csv` only) | `diameter_map` (from the opening-map step) restricted to each diameter bin | Pore/solid interface area contributed by that size class specifically |

### Why the connected-mask distinction matters

Notice `euler_number`, `connectivity_density_per_mm3`, and
`connectivity_probability_gamma` are computed on the **full** pore mask,
while `degree_of_anisotropy` and (indirectly, via porespy) the tortuosity
values are computed on the **connected/percolating** subset. This is
intentional, not an inconsistency: the first three metrics are *about*
fragmentation (they need the full mask, including dead-end and isolated
pores, to measure it), while anisotropy and tortuosity are about the
*shape* of the transport-relevant pathway, which only makes sense for pore
space that actually spans the sample. The `connected pore mask` layer in the
viewer is a strict subset of `segmentation`'s pore voxels — seeing pore
voxels in the segmentation that don't light up in the connected-mask layer
is expected (isolated/dead-end pores), not a bug.

## Known limitations

- The four distance-map `.tif` files are the same physical size as the
  volume itself (~1.1 GB for a 650×650×652 volume, ~4 GB for 1000³) — expect
  several GB of RAM once all layers are toggled on.
- Topology metrics (everything in the second table above except the base
  PSD) are **not spatially chunked** — they run on the full in-memory mask
  regardless of `--use-chunking` (that flag only chunks the EDT/PSD step).
  On very large volumes this can be the slowest part of a run.
- GPU EDT currently falls back to CPU in this environment (CUDA<12 cupy
  compile failure) — this doesn't affect correctness, only runtime.
