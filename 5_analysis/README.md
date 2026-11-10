# 5_analysis: which script produces which result

Every structural result in the write-up comes from one of the folders below. All of them work on the final segmentations listed in the root `README.md` (pore = 5, POM = 2; Rehovot = boolean Otsu mask).

The input volumes are not in git; the root README says where they live. Figures are drawn from these outputs by `6_figures/write_up_figures/` (graph numbers below are the write-up's).

| Result | Graph | Script | Output |
|---|---|---|---|
| **Pore-size classes**: 30–150, 150–300 and > 300 µm shares of pore volume, 8 subvolumes per soil; ANOVA or Kruskal–Wallis depending on the assumption checks, Holm-corrected pairwise tests | 4 | Local thickness via `shared_code/run_psd_diagnostics.py` on each subvolume. Driver scripts: `pore_size_distribution/scripts/` ⚠ still being brought from the lab computer | `pore_size_distribution/class_metrics.csv`, `class_stats_results.json` (what graph 4 reads); `A2_summary.md` (method and results) |
| Resolution check for the 5.85 µm Loess scan (downsampled to 15 µm) | text | same pipeline | `pore_size_distribution/mishmar_downsample_check/` |
| **Connectivity**: Euler χ, connectivity density, connection probability Γ, degree of anisotropy | 5b | `shared_code/run_psd_diagnostics.py extended` (functions in `shared_code/psd_topology_metrics.py`) | per-scan runs on the share (`Topology_Metrics_Aug2026\raw\psd_diag_*\summary.json`); all values in `connectivity/figures_data_export.md`; Rehovot samp3 in `connectivity/rehovot_samp3/` |
| **Crossover radius r\*** from the connectivity function χ(r) | 5c | `connectivity/compute_chi_r_sweep.py` | `chi_r_*.csv` on the share (`Topology_Metrics_Aug2026\connectivity_function\`); Rehovot in `connectivity/rehovot_samp3/` |
| Per-block variability of the same metrics (2×2×2 blocks) | — | `connectivity/compute_block_metrics.py` | written next to each run |
| **Distance to the nearest pore** (and to connected pores) | 5a | `distance_maps/compute_distance_map_stats.py`; Rehovot: `distance_maps/compute_rehovot_distance_metrics.py` | `distance_maps/comparison_mean_distances.json`, plus `summary_distance_metrics.json` per run |
| **Tortuosity** (diffusive, 200³ subvolumes, 3 axes) | text | `tortuosity/run_tortuosity_subvolumes.py`, then `aggregate.py` (`rerun_timeouts.py` for runs that timed out) | `tortuosity/tortuosity_subvolumes.csv`, `tortuosity_summary.csv`, `stats.json`, `REPORT.md` |
| **POM interface metrics**: POM–pore and POM–matrix contact, specific surface area, interface area density, at matched ~15 µm resolution | 6 | `pom/interface_metrics/scripts/run_pom_interface_metrics.py`, then `build_comparison_table.py` and `make_interface_figure.py` | `pom/interface_metrics/all_soils_interface_summary.json` (what graph 6 reads) |
| **POM size and spatial pattern**: per-object size, Clark–Evans R | 6 | `pom/size_and_spatial_pattern/scripts/run_pom_shape_clustering_v2.py --run-name 2soil_clean` | `pom_object_features_2soil_clean.csv`, `pom_spatial_pattern_summary_2soil_clean.json` |

## Other files here

- `shared_code/`: the library that every analysis uses.
  - `psd_diagnostics_core.py` holds local thickness and the PSD tables.
  - `psd_topology_metrics.py` holds χ, Γ, DA and tortuosity.
  - `run_psd_diagnostics.py` is the command-line entry point; `run_psd_batch.py` runs it over many volumes.
- `decisions.md`: how each metric is defined and why (D1 connected pores, D2 Euler and connectivity density, D3 Γ, D4 anisotropy, D5 tortuosity).
- `reading_masks_and_metrics.md`: how to read the masks and the output files.
- `pore_size_distribution/psd_binning_recommendation.md`: why these three pore classes.
- `pore_size_distribution/subvolume_psd_stats_summary_v1.md`: the original subvolume method and the REV check.
- `pore_size_distribution/make_psd_plot.py`: plots one run's `psd_table.csv`.

The POM shape clustering ("archetypes") was dropped in August 2026 as not robust. Its runs are in `archive/5_analysis/pom_clustering_retired/`. The `size_and_spatial_pattern` script still computes clusters, but only the per-object sizes and Clark–Evans R are reported.
