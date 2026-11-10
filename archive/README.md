# archive

This folder holds files that did not produce a result in the write-up. They are kept for the record but should not be used:

- earlier training and annotation iterations (`legacy_per_iteration`, iteration configs and logs);
- Vertisol runs that were superseded or retracted (`4_inference/superseded_vertisol_runs/`: the `samp_2_0` runs built from raw projections, and the August specimen-A redo);
- the POM shape-clustering analyses dropped in August 2026 (`5_analysis/pom_clustering_retired/`);
- exploratory tools (`legacy_pores_analysis`, `seg_plausibility`, label debugging, microSAM development files);
- the agent registry files;
- old cluster (SLURM) and Colab helpers.

The subfolders follow the same numbering as the repository. Code here was **not** updated in the 2026-11 restructure, so its internal paths refer to the old layout. `PATH_MAP_2026-11.csv` maps every old path to its new location (or marks it as removed; removed files are still in git history).
