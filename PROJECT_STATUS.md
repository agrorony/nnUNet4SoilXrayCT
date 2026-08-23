# Research Exercise — Mission Control

> Read this first in any new chat about the figures draft. It replaces re-deriving context from the long August conversation. Update the status tables here at the end of each working session.

## The project in one paragraph

Research exercise: impact of soil structure on microbial aspects. Three soils — Rehovot (brown-red sand), Bnei Re'em (Vertisol), Mishmar HaNegev (Loess). Lab side: respiration (NaOH traps, 15-day incubation, jar L4 excluded as outlier), fumigation-extraction Cmic (paired to respiration jars), bulk density (two methods), texture/CaCO₃ pending. Imaging side: microCT + nnUNet segmentation (deployed label convention: pore=5, POM=2 — NOT dataset_info.json; Rehovot is binary pore/solid, no POM), PSD via local thickness, distance-to-target topology metrics. Master document: **`figures draft - updated v5.docx`** (latest; v4 and older are history — edit from v5 only).

## Non-negotiable standards (mentor: dr. Maoz Dor)

1. **No SD anywhere. SE only.** Where SE is meaningless (voxel-wise metrics, n≈10⁸), report **mean (median)** instead. Already applied in v5 Tables 1–2.
2. A graph is not finished without statistics: omnibus p (+ effect size η²) printed on the figure, Tukey/LSD compact letters, plot EMM ± SE. Full text: `Maoz_Figure_Standard.md`.
3. Figure style: use the **`soil-figures-style`** skill (saved in Cowork) — fixed soil colors, ordering, and stats-annotation conventions.

## Work split (decided 2026-08-22)

| Track | What | Where | Status |
|---|---|---|---|
| A | PSD bin coarsening for multiple comparison — literature check | Subagent | **Done** — `psd_binning_recommendation.md`; bins merged into `fig4_psd_inference_prompt.md`. Note: Dor et al. 2025 is a Kravchenko-group (MSU) paper; 30–150 µm class verified from abstract, full table worth checking against the PDF. **Open follow-up (A2):** the subvolume run (see below) compared mean/median pore diameters across scans with different voxel sizes (Mishmar 5.85 µm vs. others 15 µm) — those medians are resolution-confounded (the fine scan sees small pores the coarse scans cannot; Mishmar's low medians, e.g. 52.8 µm subvolume / 23.5 µm object, are partly an artifact of this). Per the binning recommendation: restrict cross-soil inference to the ≥31 µm functional classes, and use the **native 15 µm Mishmar scan** (see "Scans note" below) — preferable to computational downsampling — as the robustness check. The per-class and PERMANOVA results need re-examination under this lens; whole-distribution medians should be dropped from cross-soil claims. **Extended 2026-08-22 (from the Track B chat, applies to POM not pore-PSD):** same voxel-size confound (Mishmar 5.85 µm vs. Bnei Re'em 15.00 µm) affects the POM distance/size numbers from `pom_analysis_20260815_light/`. Rony has a second, independently scanned Mishmar sample at ~15 µm (different location/core, already segmented) — running the POM pipeline on it and comparing 3-way (Bnei Re'em 15 µm / Mishmar native 5.85 µm / Mishmar new 15 µm) checks whether the gap is resolution-driven or a real soil-type effect. Paired with this: shape (elongation, flatness, sphericity) + spatial (nearest-neighbor / clustering) feature extraction and per-soil clustering of POM objects, to test whether POM has real resolution-independent morphological/spatial differences across soils. Prompt drafted: `pom_resolution_and_clustering_prompt.md` — **path to the new Mishmar 15 µm segmented volume still TBD, fill in before running** |
| B | OM interface-ratio metrics + differentiating POM metrics (deep dive) | New dedicated chat | **In progress.** Step 1 done — `pom_analysis_20260815_light/` explained back to Rony, confirmed understood. Note on what "light" skipped vs. the spec (`pom_conditioning_and_psd_prompt.md`): full-volume `distance_to_pom_*.tif` maps not kept (only midslice variants present), and the draft caption text the spec asked for was never produced. Conversation then pivoted to the A2-style resolution-confound question for POM specifically (see Track A row above and `pom_resolution_and_clustering_prompt.md`) before finishing steps 2–3 of the original Track B starter prompt (interface-ratio metrics, connectivity Γ/Euler) |
| C | Unified graphic language | Cowork skill `soil-figures-style` | Skill saved; apply when rebuilding figures |
| D | All image-derived metrics as graphs instead of tables | Final step, after A+B+E outputs and remote runs | Blocked by A, B, E, remote runs |
| E | Validate connectivity metrics (Euler χ, connectivity density, Γ) and add to results | Separate chat / remote session (NOT part of Track B) | Not started. Values exist but unvalidated — see "Connectivity metrics" note below |

## Remote Claude Code prompts (ready to paste, in project folder)

| File | Purpose | Status |
|---|---|---|
| `rehovot_inference_microsam_prompt.md` | 2 latest models × all Rehovot volumes + micro-SAM proofreading with disagreement queue | Not yet run |
| `fig4_psd_inference_prompt.md` | Replace Fig 4 voxel-χ² with subvolume ANOVA/KW + PERMANOVA + KS | **Run 2026-08-15** — results in `subvolume_psd_stats_summary_v1.md` (8 subvolumes/soil, KW+Dunn, PERMANOVA R²=0.842, KS object counts). BUT run predates the Track A binning recommendation: fine ~32-bin vectors and resolution-confounded medians were used → needs the A2 re-examination (≥31 µm classes only, possible Mishmar downsample) before the numbers go in the draft |
| `pom_conditioning_and_psd_prompt.md` | POM accessibility conditioning (denoised / pore-adjacent / connected-pore-adjacent) + POM size distribution | **Run 2026-08-15 in a "light" version** — outputs in `pom_analysis_20260815_light/` (Bnei Re'em + Mishmar: summary_pom_metrics.json, size distribution CSV/PNG, KS, midslice kept/removed PNGs, scripts/). Explained back to Rony in the Track B chat 2026-08-22; "light" skipped full-volume tifs and draft captions (see Track B row) |
| `pom_resolution_and_clustering_prompt.md` | **New 2026-08-22.** Extends the POM run: (A) 3-way Bnei Re'em / Mishmar-native / Mishmar-15µm comparison to test the resolution confound, (B) per-object shape + spatial clustering of POM within each soil, cross-soil archetype comparison | Not yet run — needs the Mishmar 15 µm scan's path filled in first |
| `rehovot_table2_distance_metrics_prompt.md` | Rehovot pore-distance metrics | **Done** — results in `rehovot_distance_metrics_binary/`, already in v5 Table 2 |

## Document state (v5)

Done: Fig 1d cumulative respiration (endpoint ANOVA, a/b/c letters); Fig 2b quotients qCO₂ + Cmic/Corg (paired per-jar; Loess lowest qCO₂ p=0.008; Vertisol lowest Cmic/Corg p=0.028); Table 1 dual bulk density mean ± SE; Table 2 mean (median) incl. Rehovot row.

Open comments in v5: (0) explain/resolve core-vs-bottle bulk density gap (Vertisol 1.35 vs 0.81 — candidate arbiter: CT-derived BD); (1) days 1–3 groups — two groups only if jar L2 excluded (Grubbs borderline G=1.151 vs 1.154; **check lab records for L2's day-3 titration**); (2) Fig 4 χ² replacement (Track A + remote prompt); (3) POM conditioning + connectivity Γ/Euler (Track B + remote prompt; connectivity metrics not yet in any prompt).

**Connectivity metrics (Euler χ, connectivity density, Γ) — exist but unvalidated, not yet in the draft.** Computed in the full extended runs (`Topology_Metrics_Aug2026V2/raw/psd_diag_*/summary.json`): Bnei Re'em χ=10,318, conn. density=−11.1 mm⁻³, Γ=0.859, DA=0.098; Mishmar χ=−65,340, conn. density=326.4 mm⁻³, Γ=0.927, DA=0.123. Reliability concerns before these enter results: (a) Bnei Re'em's *negative* connectivity density alongside a *positive* Euler number needs a sign-convention check (conn. density is usually derived from χ — the two rows may not use a consistent definition, or Bnei Re'em's pore network is genuinely dominated by isolated objects, which contradicts Γ=0.86); (b) tortuosity_axis0 is NaN in both runs; (c) no Rehovot values; (d) resolution gap (5.85 vs 15 µm) affects χ and conn. density strongly (small pores/connections) — use the native 15 µm Mishmar scan (see below) for the cross-soil comparison. Validation = Track E; presentation as figures = Track D.

Also open: Table 1 "Pending" cells (texture % — `Soil_Texture_Analysis.xlsx`, CaCO₃ — `Lime_CaCO3_Calcimeter_Experiment.xlsx`); Figure 5 (structure vs. activity — needs everything above); qCO₂ basal-window choice and days 1–3 post-hoc choice to confirm with Maoz.

## Starter prompt for Track B (paste into a new chat)

> Read PROJECT_STATUS.md in the project folder first. Track B deep dive, in this order:
> 1. **Explain last week's POM run to me first.** Go through `pom_analysis_20260815_light/` (all_soils_summary.json, per-soil summary_pom_metrics.json, pom_size_distribution.csv/png, KS json, midslice kept/removed PNGs, run_log.txt, scripts/) and the spec that produced it (`pom_conditioning_and_psd_prompt.md`). Walk me through: what conditioning was applied (denoised / pore-adjacent / connected-pore-adjacent), what cutoff was chosen and why, what the distance and size-distribution results say, and what "light" apparently skipped relative to the spec. I don't remember what happened there — assume nothing. **[Done 2026-08-22]**
> 2. Only after I confirm I understand: deepen — (a) metrics around ratios between organic-matter interfaces (POM–pore, POM–matrix, specific surface, interface density), (b) additional POM metrics that differentiate the soils (shape, occlusion, spacing…). Connectivity metrics (Γ, Euler) are NOT part of this track — they're Track E. **[Partially covered via the resolution/clustering side-quest — shape/spatial features drafted in `pom_resolution_and_clustering_prompt.md`; interface-ratio metrics (a) and connectivity Γ/Euler (c) still open]**
> 3. End goal: an updated remote-run prompt + planned figures per the soil-figures-style skill. Remember: POM exists only for Bnei Re'em and Mishmar (Rehovot is binary); Mishmar is 5.85 µm voxels vs. 15 µm — mind resolution comparability (see Track A2 note).

## Kickoff prompts per track (paste into a new chat)

- **A2:** "Read `PROJECT_STATUS.md` — Track A row, 'Open follow-up (A2)' note, and the matching remote-prompts entry. Also read `psd_binning_recommendation.md` and `subvolume_psd_stats_summary_v1.md`. Execute A2: cross-soil inference restricted to ≥31 µm classes, drop resolution-confounded medians from cross-soil claims, robustness check with the native 15 µm Mishmar scan (see 'Scans note')."
- **A2 (POM resolution + clustering):** "Read `PROJECT_STATUS.md` — Track A row, 2026-08-22 extension note. Fill in the Mishmar 15 µm scan path in `pom_resolution_and_clustering_prompt.md`, then execute it: 3-way POM distance/size comparison plus shape+spatial clustering."
- **B:** "Read `PROJECT_STATUS.md` and follow the 'Starter prompt for Track B' section — step 1 is done, continue with step 2 (interface-ratio metrics, connectivity Γ/Euler)."
- **D** (after A2+B): "Read `PROJECT_STATUS.md` — Track D row and 'Document state (v5)'. Execute Track D: rebuild all image-derived metrics as figures instead of tables, using the soil-figures-style skill, and insert into the latest figures draft."
- **Bulk density side item:** "Read `PROJECT_STATUS.md` — open comment (0): core-vs-bottle bulk density gap. Help me resolve it (CT-derived BD as arbiter) and draft the answer for the document."
- **E:** "Read `PROJECT_STATUS.md` — Track E row and the 'Connectivity metrics' note. Validate the Euler/connectivity-density/Γ values (sign conventions, the Bnei Re'em χ>0 vs. Γ=0.86 contradiction, NaN tortuosity), define the correct computation, produce a remote-run prompt that recomputes them consistently for all three soils — using the native 15 µm Mishmar scan for cross-soil comparability — and prepare the results for Track D."
- **C** needs no prompt — the `soil-figures-style` skill triggers automatically on any figure work.

## Scans note

**A native 15 µm Mishmar HaNegev scan exists** (scanned by Rony himself; the remote computer has it — it is not yet referenced in any analysis here, which so far used only the 5.85 µm Mishmar scan). For any cross-soil comparison affected by resolution (A2 medians, Track E connectivity, KS object stats), prefer this native 15 µm scan over computational downsampling of the 5.85 µm one. It may need segmentation (check on the remote machine whether an nnU-Net inference exists for it — if not, add it to the inference run in `rehovot_inference_microsam_prompt.md` or a similar prompt).

## Key data files

Respiration: `Soil_CO2_Respiration_v4.xlsx` (Results sheet, per-jar). Cmic: `Fumigation_Extraction_Experiment.xlsx` (Calculations; replicates 1–4 pair with jars 1–4; Summary has Corg via LOI/1.724). Bulk density: `Bulk_Density_Experiment.xlsx` (core), `Organic carbon(2).xlsx` sheet "bulk density" (bottle). Topology summaries: `Topology_Metrics_Aug2026V2/raw/`, `rehovot_distance_metrics_binary/`. Analysis plan: `comments_insights_and_implementation_plan.md`.
