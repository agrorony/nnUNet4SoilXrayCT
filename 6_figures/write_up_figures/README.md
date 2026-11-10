# Figures in the submitted write-up

These scripts produced the graphs in the final write-up (November 2026 revision). The PNG/SVG next to them are those figures. On 2026-11-10 every script was re-run from this repository and gave pixel-identical images.

| Graph | Script | Reads |
|---|---|---|
| 1 Respiration (cumulative, per period) | `fig_biology.py` | lab workbooks (`Soil_CO2_Respiration_v4.xlsx`) |
| 2 Microbial biomass C, qCO₂, MBC/Corg | `fig_biology.py` | lab workbooks (`Fumigation_Extraction_Experiment.xlsx`, `Organic carbon(2).xlsx`) |
| 3 Segmentation examples | `fig_segmentation.py` | `6_figures/segmentation_examples/figure7_prediction_panels.png` |
| 4 Pore-size classes | `fig_structure.py` | `5_analysis/pore_size_distribution/class_metrics.csv`, `class_stats_results.json` |
| 5 Distances, Γ vs visible porosity, r* | `fig_structure.py` | values written in the script, from `5_analysis/distance_maps` and the connectivity runs (see the comments) |
| 6 POM metrics | `fig_structure.py` | `5_analysis/pom/interface_metrics/all_soils_interface_summary.json`, plus the Clark–Evans R values from `5_analysis/pom/size_and_spatial_pattern/` |
| 7 Lab vs CT at the soil level | `fig_correlation.py` | lab workbooks + the CT values above |
| A1 Simulation model (appendix) | `fig_appendix.py` | outputs of <https://github.com/agrorony/resp_model> |

- `common.py` holds the shared style, data loading and statistics (ANOVA, Fisher's LSD or Tukey, compact letters).
- `fig_biology_stats.txt` holds every number printed on graphs 1–2. `stats_tukey_vs_lsd.txt` compares the two post-hoc choices, and `stats_check.py` checks the test assumptions.

## Rerun

The lab workbooks are not in this repository. They are in `07_lab_data_and_writeup/raw_workbooks/` of the hand-off ZIP.

```
set LAB_DATA_DIR=<path to raw_workbooks>
set RESP_MODEL_SIM_DIR=<resp_model simulation outputs>   (only for fig_appendix.py)
python fig_structure.py
python fig_biology.py
python fig_segmentation.py
python fig_correlation.py
```

Output goes to `out/`, which git ignores. `fig_biology.py` accepts `POSTHOC=tukey` and `QCO2_WINDOW=mean15` to redraw the alternative choices.
