# Reused from pom_analysis_20260824_ablation/mishmar_label_downsample/

This replicate is `mishmar_native` (5.85um), the same physical sample used
throughout the project, label-downsampled to ~15um. Per
`pom_replicate_comparison_prompt.md` Part 2 instructions, the existing
2026-08-24 ablation result was re-verified (not recomputed) since it is
still valid:

- `sanity_check.json` / `summary_pom_metrics.json` here are copies of the
  originals in `../../pom_analysis_20260824_ablation/mishmar_label_downsample/`.
- Re-verified numbers match record exactly: POM 1.6141% (recorded 1.614%),
  pore 26.1083% (recorded 26.108%). No collapse, no drift.
- Full outputs (downsampled .nii.gz, distance-map tifs, object-diameter
  .npy files, diagnostic PNG) were NOT duplicated here to avoid copying
  multi-GB data -- they remain at
  `../../pom_analysis_20260824_ablation/mishmar_label_downsample/`.
