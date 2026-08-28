# Superseded 2026-08-24

The `mishmar_15um/` branch in this folder (a *different physical Mishmar
sample*, `Cu011_samp_2`, scanned natively at ~15um) produced an implausible
POM-fraction collapse (0.120% vs. 1.613% for native Mishmar) while pore
detection stayed normal -- the segmentation model failed to recognize POM on
that input. Do not cite `mishmar_15um/summary_pom_metrics.json` or
`part_a_3way_comparison.md` (its 3-way table includes this branch).

The 3-soil clustering outputs in this folder (`run_log_shape_clustering_3soil.txt`,
`pom_cluster_profiles.csv`, `pom_object_features_all_soils.csv`,
`pom_archetype_crosssoil_comparison.json`, `pom_spatial_pattern_summary.json`)
also included this bad branch pooled into the StandardScaler and are likewise
superseded. `pom_cluster_profiles.csv` on disk here is the 3-soil (bad)
version, NOT the earlier clean 2-soil run it silently overwrote.

**Replacement:** `../pom_analysis_20260824_ablation/` -- two clean
computational ablations on the SAME physical sample as `mishmar_native`
(majority-vote label downsample + block-mean image downsample -> fresh
predict), a 4-way comparison table (`part_c_4way_comparison.md`), and
per-run-named clustering outputs (`pom_cluster_profiles_2soil_clean.csv`,
`pom_cluster_profiles_4soil.csv`) that can never overwrite each other.

The `bnei_reem/` and `mishmar/` (native) results elsewhere in THIS folder's
sibling `pom_analysis_20260815/` are unaffected and still valid -- only this
folder's `mishmar_15um/` branch and its downstream 3-soil clustering outputs
are invalid.
