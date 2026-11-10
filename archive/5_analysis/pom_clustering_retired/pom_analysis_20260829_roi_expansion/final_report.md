# ROI Expansion + Final POM Clustering — Bnei Re'em (n=1) vs Mishmar (n=2)

Run: `roi_expansion`, 2026-08-29/30. Per `pom_roi_expansion_and_final_clustering_prompt.md`. Same 3 volumes as
`pom_final_clustering_prompt.md`'s prior "final" run (`pom_analysis_20260826_final_shape/`): Bnei Re'em canonical
(`nlm_volume`), Mishmar native (5.85µm), Mishmar second sample (~8.8µm). No other volumes added.

## TL;DR

ROI expansion worked for 2 of 3 volumes — both Mishmar crops grew substantially (1000³→1216³ and 1000³→1614³) and
passed every sanity check. It **failed** for Bnei Re'em: the enlarged 722³ crop's POM channel collapsed
(0.819%→0.254%, below the 0.3% floor) while pore stayed roughly normal, so Bnei Re'em automatically fell back to
its existing, already-trusted 650³ crop per the prompt's rule. This is not a surprise in hindsight — `DATA_CATALOG.md`
already records that a *separate* fresh reconstruction of this same physical core failed POM recognition entirely,
so this model appears to be specifically brittle to field-of-view changes on this one specimen.

**The prior run's headline finding does not hold up.** At the pinned 20-voxel cutoff, the much larger Mishmar object
counts (driven mostly by Mishmar rep 2's crop growing from 1000³→1614³, tripling its POM volume fraction) caused the
archetype clustering to collapse from 6 archetypes down to just **2**. In that simpler structure, Bnei Re'em's
proportion vector became numerically **identical** to Mishmar replicate 1's (`[1.0, 0.0]` for both) — it is now
Mishmar replicate 2 that stands apart from the other two, not Bnei Re'em. That is the opposite of the story that
supported the prior run's "Bnei Re'em lacks these archetypes, both Mishmar replicates agree it's present" conclusion.
This holds at cutoff=15 too. At cutoff=25 (much smaller n, back to 6 archetypes) one archetype shows a partial echo
of the original pattern, but it's the exception, not the rule — see Part 4. **Bottom line: treat the prior run's
"Bnei Re'em is missing archetypes 1 and 3" finding as not robust.** It was likely an artifact of small-n clustering
noise at the old, smaller Mishmar crop sizes, not a real compositional difference between the soils.

## Part 1 — Raw-vs-crop margin check

| Volume | Raw shape (Z×H×W) | Current crop (Z/Y/X) | Margin (Z / Y / X) | Decision |
|---|---|---|---|---|
| Bnei Re'em canonical | 804×1344×1344 | 652 / 650 / 650 | +23.3% / +106.8% / +106.8% | proceed to Part 2 |
| Mishmar native (5.85µm) | 1353×1845×1845 | 1000 / 1000 / 1000 | +35.3% / +84.5% / +84.5% | proceed to Part 2 |
| Mishmar second (8.8µm) | 3311×1794×1807 | 1000 / 1000 / 1000 | +231.1% / +79.4% / +80.7% | proceed to Part 2 |

All three volumes cleared the ≥15%-on-every-axis threshold. Note: the Bnei Re'em raw folder mixes raw radiographic
*projection* images (896×1344, sequential naming) in with the actual reconstructed cross-sections
(`*_rec#####.tif`, 1344×1344, only 804 of the 2613 total `.tif` files) — the margin check filters to the
reconstructed-slice pattern only; using the naive file count would have overstated Bnei Re'em's raw Z-extent by
~3.2×. Also cross-checked the Bnei Re'em raw-source folder identity (`18.12.25 bnei_reem_samp_2`, an "inferred, not
confirmed" flag from initial discovery) against `DATA_CATALOG.md` — confirmed correct.

## Part 2 — Enlarged crops, holder-safety check, and pipeline sanity checks

| Volume | Proposed max (90% cap) | Holder signature found | Final crop | Pipeline sanity check |
|---|---:|---|---:|---|
| Bnei Re'em canonical | 723 (90% of 804) | none before boundary | 722 | **FAILED** — channel collapse |
| Mishmar native (5.85µm) | 1217 (90% of 1353) | none before boundary | 1216 | PASSED |
| Mishmar second (8.8µm) | 1614 (90% of 1794) | none before boundary | 1614 | PASSED |

Holder-safety shell scan: intensity was tracked outward from each current crop boundary to the proposed boundary in
10-voxel shells, watching for a sharp saturated (dense/metal mount) or near-zero-with-collapsed-variance (air gap)
signature. None triggered for any volume, so all three got the full 90%-cap enlargement. One thing worth flagging:
Mishmar second's shell mean intensity declined *gradually* (15,677→9,053) approaching the boundary — a smooth trend,
not a sharp jump, so it didn't meet the disqualifying criterion, but it's consistent with slowly approaching the
physical edge of the cylindrical core. The downstream sanity check (below) is what actually caught any resulting
segmentation problems, and it passed clean for this volume.

**Channel-collapse sanity check** (pore/POM voxel fraction vs. the existing crop's baseline; floor = 0.3%, and
either phase crashing toward zero while the other stays normal is disqualifying — magnitude differences alone are
not):

| Volume | New pore % | Baseline pore % | New POM % | Baseline POM % | Verdict |
|---|---:|---:|---:|---:|---|
| Bnei Re'em canonical | 14.69 | 21.64 | **0.254** | 0.819 | **COLLAPSED** (POM < 0.3% floor) |
| Mishmar native (5.85µm) | 27.56 | 27.04 | 2.04 | 1.62 | passed |
| Mishmar second (8.8µm) | 21.68 | 22.98 | 7.96 | 1.64 | passed (POM ~5× higher, not disqualifying per spec) |

Bnei Re'em: discarded, fell back to the existing 650³ crop (`bnei_reem_fresh_bnei_reem_i4/inference_concatenated/nlm_volume.nii.gz`) for everything below.

Mishmar volumes were then label-downsampled from native resolution to ~15µm (majority-vote block downsample,
matching the pinned methodology) and re-checked:

| Volume | Downsampled shape | Achieved voxel size | Pore % | POM % | Verdict |
|---|---|---:|---:|---:|---|
| Mishmar native | 474³ | 15.008µm | 26.57 | 2.03 | passed, used |
| Mishmar second | 947³ | 14.998µm | 20.34 | 7.86 | passed, used |

Both downsampled volumes confirmed no collapse and were used directly in Part 3/4.

## Part 3 — Final clustering (cutoff = 20 voxels, this run's crops)

Volumes used: Bnei Re'em **existing crop** (fallback), Mishmar native and Mishmar second **ROI-expanded crops**.
StandardScaler fit fresh on only these 3 volumes' 423 pooled objects — no reuse of any earlier scaler.

**Object counts before/after the resolvability cutoff (diam ≥ 300µm, 20 voxels):**

| Volume | n_objects_raw | n_kept | % kept |
|---|---:|---:|---:|
| Bnei Re'em (existing crop) | 2,709 | 76 | 2.8% |
| Mishmar rep 1 (ROI-expanded, 5.85µm) | 6,959 | 53 | 0.8% |
| Mishmar rep 2 (ROI-expanded, 8.8µm) | 25,358 | 294 | 1.2% |

Per-volume clustering (KMeans, k chosen by silhouette, k∈[2,6]): Bnei Re'em best_k=2, Mishmar rep 1 best_k=3,
Mishmar rep 2 best_k=2. Cross-volume archetype matching on centroids found only **2 archetypes**
(silhouette on centroids = 0.301) — a sharp simplification from the prior run's 6.

**Archetype proportion vectors** (fraction of each volume's kept objects in archetypes [0, 1]):

| | 0 | 1 | n |
|---|---:|---:|---:|
| **Bnei Re'em (n=1, existing crop)** | 1.000 | 0.000 | 76 |
| Mishmar rep 1 (ROI-expanded) | 1.000 | 0.000 | 53 |
| Mishmar rep 2 (ROI-expanded) | 0.793 | 0.207 | 294 |
| **Mishmar mean ± SE (n=2)** | 0.896 ± 0.104 | 0.104 ± 0.104 |  |

Bnei Re'em's single point relative to Mishmar's mean ± SE: **+1.00 SE** (archetype 0) / **−1.00 SE** (archetype 1) —
well within one Mishmar-replicate SE both ways. **Bnei Re'em is numerically identical to Mishmar rep 1** on this
axis; the only volume that differs from the other two is Mishmar rep 2. Contingency table confirms this directly:
archetype 1 has 0 Bnei Re'em objects, 0 Mishmar-rep-1 objects, and 61 Mishmar-rep-2 objects — i.e. this archetype is
specific to one Mishmar replicate, not something that separates Bnei Re'em from Mishmar as a group.

Archetype character (from per-cluster shape means): archetype 0 objects are moderate elongation/flatness with
sphericity ~0.3–0.7 and pore-contact fraction ~0.4–0.7; archetype 1 (Mishmar rep 2 only, 61 objects) is more
elongated/flattened on average, lower sphericity (~0.38), much lower pore-contact fraction (~0.12) and larger mean
diameter (~728µm) — plausibly the larger raw crop capturing bigger, more irregular POM aggregates near the newly
included periphery of that sample.

## Object-count comparison: this run vs. the prior "final" run

| Volume | Prior crop (vox) | This run's crop (vox) | Prior n_raw | Prior n_kept | This n_raw | This n_kept | Δn_kept |
|---|---:|---:|---:|---:|---:|---:|---:|
| Bnei Re'em canonical | 652 | 722 (discarded → 652 used) | 2,709 | 76 | 2,709 | 76 | +0 |
| Mishmar native (5.85µm) | 1000 | 1216 | 1,902 | 19 | 6,959 | 53 | +34 |
| Mishmar second (8.8µm) | 1000 | 1614 | 3,479 | 60 | 25,358 | 294 | +234 |

Bnei Re'em is unchanged (fallback preserved the exact prior crop and its exact object counts). Both Mishmar volumes
gained substantially more kept objects — rep 2 especially (60→294, +234, a ~5× increase), driven by both the larger
crop volume and the POM voxel-fraction increase noted in Part 2.

## Part 4 — Cutoff sensitivity check (15 / 20 / 25 voxels)

**Object counts per volume per cutoff** (same crops as Part 3 throughout):

| Cutoff (vox) | Bnei Re'em raw→kept | Mishmar rep 1 raw→kept | Mishmar rep 2 raw→kept | n_archetypes | Archetype silhouette |
|---:|---|---|---|---:|---:|
| 15 | 2,709 → 125 | 6,959 → 114 | 25,358 → 610 | 2 | 0.370 |
| 20 | 2,709 → 76 | 6,959 → 53 | 25,358 → 294 | 2 | 0.301 |
| 25 | 2,709 → 41 | 6,959 → 24 | 25,358 → 158 | 6 | 0.384 |

**Archetype proportion vectors per cutoff:**

- **cutoff=15** (2 archetypes): Bnei Re'em `[1.000, 0.000]` (n=125); Mishmar rep 1 `[1.000, 0.000]` (n=114);
  Mishmar rep 2 `[0.807, 0.193]` (n=610). Mishmar mean±SE `[0.903±0.097, 0.097±0.097]`. Bnei Re'em deviation:
  +1.00 SE / −1.00 SE. **Same pattern as cutoff=20**: Bnei Re'em = Mishmar rep 1, Mishmar rep 2 is the outlier.
- **cutoff=20** (2 archetypes): as above in Part 3.
- **cutoff=25** (6 archetypes, back to the prior run's structure size): Bnei Re'em `[0.195, 0.220, 0.000, 0.195,
  0.244, 0.146]` (n=41); Mishmar rep 1 `[0.167, 0.042, 0.167, 0.250, 0.250, 0.125]` (n=24); Mishmar rep 2
  `[0.000, 0.000, 0.228, 0.000, 0.772, 0.000]` (n=158). Here archetype 2 shows a partial echo of the prior run's
  finding — Bnei Re'em = 0.000, both Mishmar replicates > 0 (0.167, 0.228) — but no other archetype shows that
  pattern; e.g. archetype 1 has Bnei Re'em (0.220) *higher* than both Mishmar replicates (0.042, 0.000), the reverse
  shape of the "finding."

**Is the prior run's main finding cutoff-robust? No.** It appears, partially and in only one archetype out of six,
at cutoff=25 — but is absent at cutoffs 15 and 20, where the archetype structure itself simplifies to 2 clusters and
Bnei Re'em becomes indistinguishable from Mishmar rep 1. The number of archetypes recovered is itself unstable
across cutoffs (2, 2, then 6), which is a second-order robustness concern independent of the specific finding: with
this much sensitivity to the cutoff choice, no single archetype-membership pattern here should be treated as a
confirmed compositional difference between the two soils without a great deal more replication.

## Caveats

- **Mixed crop provenance in this run's final comparison**: Bnei Re'em uses its old, smaller crop while both Mishmar
  volumes use much larger new crops. This was the correct, prompt-mandated response to Bnei Re'em's channel
  collapse, not a methodology error — but it means the "Bnei Re'em vs Mishmar" comparison in this run is no longer
  an apples-to-apples ROI-size comparison, on top of the pre-existing n=1-vs-n=2 asymmetry.
- **n=1 on the Bnei Re'em side** — every Bnei Re'em number above is a single descriptive point, not a distribution.
- **n=24 for Mishmar rep 1 at cutoff=25** and **n=41 for Bnei Re'em at cutoff=25** are small for a 6-archetype split
  (~4-7 objects/archetype on average) — treat cutoff=25's per-archetype assignments as noisy.
- Sphericity was computed via marching-cubes mesh reconstruction throughout (same pinned method as the prior run);
  no volume in this run needed the voxel-proxy fallback.
- Bnei Re'em's channel-collapse result on the enlarged crop, together with the pre-existing note in
  `DATA_CATALOG.md` that a separate fresh reconstruction of the same physical core failed POM recognition entirely,
  suggests the `multi_sample_fresh_bnei_reem_i4` model's POM channel may be more generally sensitive to
  out-of-training-distribution field-of-view/context than the pore/solid channels are for this specimen — worth
  keeping in mind for any future work that touches this model or this raw core.

## Where everything lives

- Part 1: `part1_margin_report.json`
- Part 2: `part2_holder_safety_report.json`, `sanity_check_<volume>.json`, `pipeline_work/<volume>/downsample_sanity_check.json`, `crop_decisions_final.json`, `datasets_this_run.json`
- Part 3 (cutoff=20): `object_counts_before_after_cutoff_roi_expansion_cutoff20.json`, `pom_archetype_proportion_vectors_roi_expansion_cutoff20.json`, `pom_archetype_crosssoil_comparison_roi_expansion_cutoff20.json`, `pom_cluster_profiles_roi_expansion_cutoff20.csv`, `pom_object_features_roi_expansion_cutoff20.csv`, diagnostic plots under `bnei_reem/`, `mishmar_label_downsample_1/`, `mishmar_label_downsample_2/`
- Object-count comparison: `object_count_comparison_this_run_vs_prior_final.json`
- Part 4 (cutoffs 15/25): `object_counts_before_after_cutoff_roi_expansion_cutoff{15,25}.json`, `pom_archetype_proportion_vectors_roi_expansion_cutoff{15,25}.json`, `pom_archetype_crosssoil_comparison_roi_expansion_cutoff{15,25}.json`
- Scripts: `scripts/` (all self-contained, none overwrite the prior "final" run's outputs)
