# Final POM shape/spatial clustering — Bnei Re'em (n=1) vs Mishmar (n=2)

Run: `final`, 2026-08-26. Script: `scripts/run_pom_shape_clustering_final.py`.

## Pinned methodology (Part 1)

- **Sphericity**: marching-cubes mesh reconstruction per object (`skimage.measure.marching_cubes` + `mesh_surface_area`), same as `pom_analysis_20260824_ablation/scripts/run_pom_shape_clustering_v2.py` and `pom_analysis_20260824_replicates/scripts/run_pom_shape_clustering_replicates.py`. 0 objects fell back to the voxel-proxy method in this run (all objects were large enough for a valid mesh, unsurprising given the size cutoff below).
- **Elongation/flatness**: eigenvalue-floored PCA on voxel positions, identical formula to both prior versions.
- **New in this run — minimum-resolvability cutoff** (replaces the old "A1 noise floor" cutoff): drop POM objects whose equivalent-sphere diameter is under **20 voxels** (`n_voxels >= (pi/6) * 20^3 = 4188.8` at this project's 15.000149 µm/voxel convention, i.e. diameter ≥ 300.0 µm). Computed directly per volume, not read from any prior run's JSON.

## Volumes used (Part 2)

| Volume | Path | Voxel size |
|---|---|---|
| Bnei Re'em (canonical) | `\\hive3065\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources\bnei_reem_fresh_bnei_reem_i4\inference_concatenated\nlm_volume.nii.gz` | 15.000149 µm |
| Mishmar replicate 1 (native 5.85µm → label-downsampled ~15µm) | `pom_analysis_20260824_ablation/mishmar_label_downsample/mishmar_label_downsample.nii.gz` | 15.000149 µm |
| Mishmar replicate 2 (native 8.8µm → label-downsampled ~15µm) | `pom_analysis_20260824_replicates/mishmar_label_downsample_2/mishmar_label_downsample_2.nii.gz` | 15.000149 µm |

**Object counts before/after the resolvability cutoff:**

| Volume | n_objects_raw | n_kept (diam ≥ 300µm) | % kept |
|---|---:|---:|---:|
| Bnei Re'em | 2,709 | 76 | 2.8% |
| Mishmar rep 1 (5.85µm) | 1,902 | 19 | 1.0% |
| Mishmar rep 2 (8.8µm) | 3,479 | 60 | 1.7% |

**This is a drastic reduction** compared to every prior POM object-shape run on these same volumes, which used a much looser "segmentation noise floor" cutoff (8–15 voxels, i.e. only ~2.5–3 voxels across the equivalent diameter — not enough to trust a mesh-based sphericity or a PCA-based elongation/flatness). At the 20-voxel-diameter resolvability standard, only the largest few percent of POM objects in each volume survive. Mishmar replicate 1 in particular has only **19 objects** total.

## Clustering / archetypes (Part 3)

StandardScaler fit fresh, only on these 155 pooled objects (76 + 19 + 60) — no reuse of any earlier scaler, no pooling with `mishmar_image_then_predict` or `Cu011_samp_2`.

Per-volume clustering (KMeans, k chosen by silhouette, k∈[2,6]):
- Bnei Re'em: best_k=4, silhouette=0.258
- Mishmar rep 1: best_k=6, silhouette=0.390 (**~3.2 objects/cluster on average — treat cluster assignments here as noisy**)
- Mishmar rep 2: best_k=6, silhouette=0.278

Cross-volume archetype matching on cluster centroids found **6 archetypes** (silhouette on centroids = 0.319). Mean shape per archetype (pooled across all 3 volumes):

| Archetype | n | elongation | flatness | sphericity | pore_contact_fraction | diameter_um | rough description |
|---|---:|---:|---:|---:|---:|---:|---|
| 0 | 47 | 1.53 | 1.80 | 0.39 | 0.68 | 542 | flattened, large, high pore contact |
| 1 | 9  | 2.94 | 1.28 | 0.53 | 0.48 | 407 | rod-like/elongated, moderate |
| 2 | 26 | 1.84 | 2.75 | 0.38 | 0.50 | 444 | strongly platy/flattened |
| 3 | 18 | 1.34 | 1.60 | 0.65 | 0.33 | 370 | most equant/blocky, smallest, low pore contact |
| 4 | 37 | 1.67 | 1.57 | 0.48 | 0.43 | 404 | moderate all-around |
| 5 | 18 | 2.64 | 1.45 | 0.35 | 0.70 | 543 | elongated, large, high pore contact |

**Archetype proportion vectors** (fraction of each volume's kept objects in archetypes [0,1,2,3,4,5]):

| | 0 | 1 | 2 | 3 | 4 | 5 | n |
|---|---:|---:|---:|---:|---:|---:|---:|
| **Bnei Re'em (n=1)** | 0.250 | 0.000 | 0.145 | 0.000 | 0.421 | 0.184 | 76 |
| Mishmar rep 1 | 0.263 | 0.105 | 0.000 | 0.158 | 0.263 | 0.211 | 19 |
| Mishmar rep 2 | 0.383 | 0.117 | 0.250 | 0.250 | 0.000 | 0.000 | 60 |
| **Mishmar mean ± SE (n=2)** | 0.323 ± 0.060 | 0.111 ± 0.006 | 0.125 ± 0.125 | 0.204 ± 0.046 | 0.132 ± 0.132 | 0.105 ± 0.105 |  |

Bnei Re'em's single point relative to Mishmar's mean ± SE (descriptive, in SE units — **not a p-value**):

- Archetype 0: −1.2 SE — within range.
- Archetype 1: Bnei Re'em = 0.0 vs Mishmar 0.111 ± 0.006 — Bnei Re'em has **no** objects in this rod-like archetype; both Mishmar replicates agree it's present (~10–12%), so this looks like a real qualitative absence, not sampling noise.
- Archetype 2: +0.16 SE — essentially on the Mishmar mean, but that mean is the average of 0% (rep 2... wait rep2=0.250, rep1=0.000) — i.e. the two Mishmar replicates strongly disagree on this archetype themselves.
- Archetype 3: Bnei Re'em = 0.0 vs Mishmar 0.204 ± 0.046 — Bnei Re'em has **no** objects in this most-equant/blocky/low-pore-contact archetype; both Mishmar replicates have some (16%, 25%). Looks like a real absence.
- Archetype 4: +2.2 SE — Bnei Re'em's largest archetype (42%), elevated vs Mishmar mean, but the Mishmar SE here is huge (±0.132) because rep 1 = 26% and rep 2 = 0% — the two Mishmar replicates disagree with each other as much as either disagrees with Bnei Re'em.
- Archetype 5: +0.75 SE — within range.

**Honest read**: the two Mishmar replicates disagree with each other substantially on archetypes 2, 4, and 5 (one has ~25%, the other 0%, for each) — within-Mishmar physical-sample variability at this object count is comparable to, or larger than, the Bnei-Re'em-vs-Mishmar difference for those archetypes. The clearest, most reproducible signal is archetypes 1 and 3 (small elongated / small equant objects, respectively): **both** Mishmar replicates have some objects there and Bnei Re'em has **none** — that's the one part of this comparison that isn't just an artifact of n=2 Mishmar noise.

## Caveats (stated explicitly, per the prompt)

- **n=1 on the Bnei Re'em side** — every Bnei Re'em number above is a single descriptive point, not a distribution. No inferential test is reported for it, deliberately.
- **n=19 for Mishmar replicate 1** post-cutoff is very small for a 6-cluster split (~3 objects/cluster) — individual cluster/archetype assignments for that volume should be treated as noisy, not authoritative.
- The resolvability cutoff (20 voxels across diameter) removed **97–99%** of POM objects in every volume. This is a much stricter, much more defensible standard for trusting mesh-based sphericity/elongation/flatness than any prior POM run used — but it means this analysis characterizes only the largest few percent of POM objects, not the whole POM population (that's what the earlier, size-distribution-focused runs with the looser cutoff already covered).
