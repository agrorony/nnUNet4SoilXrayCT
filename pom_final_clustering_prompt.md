# Prompt — Final POM shape/spatial clustering: Bnei Re'em (n=1) vs Mishmar (n=2)

> Paste into Claude Code. Bnei Re'em stays at n=1 (Rony has confirmed no further replicate is coming) — use the canonical, already-trusted volume (segmentation output `nlm_volume` — the one Rony has been annotating against, do NOT use `bnei_reem_samp_2_0` or `bnei_reem_samp_2_0_recropped`). Mishmar is n=2: native 5.85 µm sample + the second ~8.8 µm sample, both label-downsampled to ~15 µm (from `pom_replicate_comparison_prompt.md`).

## Why this task exists

Two bugs undermined every prior clustering attempt: (1) a pooled `StandardScaler` fit across all soils/branches in a run let a bad branch's features corrupt the others' results, and (2) two script versions computed sphericity differently (marching-cubes mesh vs. a voxel-face-counting proxy), giving non-comparable archetype results on the same two soils. This prompt fixes both by pinning one script version and one volume set, end to end.

## Part 1 — Pin the pipeline

1. Confirm which script version computes sphericity via marching-cubes mesh reconstruction (the 08-24 `run_pom_shape_clustering_v2.py` or its current equivalent). Use only this version for everything below — do not fall back to the older voxel-proxy method for any volume.
2. Before extracting shape features on any volume, apply a minimum-resolvability cutoff: drop POM objects that don't span enough voxels across their diameter to be trusted after downsampling (use ~20 voxels across the diameter as the threshold unless you have a better-justified number). Apply this identically to all 3 volumes below.

## Part 2 — Extract features for exactly these 3 volumes

1. Bnei Re'em canonical (`nlm_volume` — the trusted, already-annotated volume; confirm the exact path/folder before running, and report it back so Rony can verify it's the right one).
2. Mishmar native, label-downsampled to ~15 µm.
3. Mishmar second sample (~8.8 µm native), label-downsampled to ~15 µm.

Use the pinned script version and cutoff from Part 1 for all three. Do not include any other volume (no `bnei_reem_samp_2_0`, no `mishmar_image_then_predict`, no `Cu011_samp_2`).

## Part 3 — Cluster and compare

1. Fit the clustering/archetype model with a scaler fit only on these 3 volumes' objects — nothing pooled in from outside this comparison.
2. Compute each volume's own cluster/archetype proportion vector (3 vectors total: 1 Bnei Re'em, 2 Mishmar).
3. Report Bnei Re'em's vector as a single descriptive point (n=1 — no variance, no inferential test on this side). Report Mishmar's two vectors individually plus mean ± SE (n=2). Show where Bnei Re'em's single point falls relative to Mishmar's mean ± SE, described plainly, not as a hypothesis test.

## Output checklist

- Confirmed path/volume used for "Bnei Re'em canonical" (`nlm_volume`), stated explicitly.
- Confirmed script version used for shape features, stated explicitly.
- Object counts before/after the resolvability cutoff, per volume.
- Final cluster/archetype table: Bnei Re'em (n=1, single vector) vs. Mishmar (n=2, both vectors + mean ± SE).
- Explicit statement that this is descriptive given n=1 on the Bnei Re'em side — no p-value or test implying otherwise.

## Sanity checks

- Do not silently substitute `bnei_reem_samp_2_0` or any recropped variant if the canonical volume has any issue — flag it and stop, don't swap volumes without saying so.
- Do not reuse any previously-fitted scaler from an earlier run — fit fresh, scoped to only these 3 volumes.
- Do not mix sphericity values computed by different script versions into the same table.
