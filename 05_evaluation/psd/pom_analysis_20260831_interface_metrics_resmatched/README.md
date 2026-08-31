# POM interface metrics -- resolution-matched re-run (2026-08-31)

Fixes a resolution confound in `../pom_analysis_20260830_interface_metrics/`:
that run's Mishmar `mean +/- SE (n=2)` mixed a 5.85um replicate
(`mishmar_native`) with a ~15um replicate (`mishmar_sample2`). This run
replaces `mishmar_native` with the already-existing label-downsampled-to-15um
version of the same physical sample
(`../pom_analysis_20260824_ablation/mishmar_label_downsample/mishmar_label_downsample.nii.gz`,
pinned cutoff 13 vox) so both Mishmar replicates are resolution-matched.
`bnei_reem` and `mishmar_sample2` are unchanged from the original run.

**Full before/after comparison, per metric, with a verdict on whether each
conclusion survives:** see the "Resolution correction" section appended to
`../pom_analysis_20260830_interface_metrics/final_report.md`.

**Bottom line:** every directional conclusion from the original run
survives; the two headline claims (SSA indistinguishable between soils,
IAD 1.6-2.2x higher in Mishmar) hold after correction. Use this run's
numbers (`all_soils_interface_summary.json`, `comparison_table_raw.json`,
`pom_interface_metrics_figure.png`) going forward -- the 08-30 run is kept
only as the documented record of the bug and its fix.

Scripts: `scripts/run_pom_interface_metrics.py` (main pipeline, one SOILS
entry changed from the original), `scripts/build_comparison_table.py`,
`scripts/make_interface_figure.py`.
