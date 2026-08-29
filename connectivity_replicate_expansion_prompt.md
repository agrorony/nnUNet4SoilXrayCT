# Prompt — Track E replicate expansion: run connectivity metrics on every usable binary/pore volume, not just the canonical 4

> Paste into Claude Code, PSD/topology pipeline repo, with access to the scan share (`nnUNet_resources`) and the network drive `Z:\Rony\remote_computer backup\Topology_Metrics_Aug2026\`. **Fully autonomous — do not stop for Rony's input mid-run.** Where a genuine judgment call would normally need his sign-off (see "What to skip, not guess" below), skip that item, flag it clearly in the output, and continue with everything else. Read `PROJECT_STATUS.md` and `DATA_CATALOG.md` first for full context; this prompt is self-contained but assumes both are on disk as of 2026-08-29. **`DATA_CATALOG.md` is current and complete as of 2026-08-29 (full share sweep + specimen-identity corrections done) — do not re-sweep the share or edit `DATA_CATALOG.md` in this prompt; treat it as read-only ground truth.**

## Why

Track E's connectivity metrics (χ, connectivity density, Γ, DA, tortuosity, χ(r)/crossover radius) currently exist for exactly 4 runs — Bnei Re'em canonical, Mishmar native, Mishmar `Cu011_samp_2`, Rehovot canonical — i.e. **n=1 physical specimen per soil** (Mishmar's 2 runs are two different processing branches of soils that, resolution aside, still trace to only 1–2 physical cores actually topology-processed so far). This is the exact problem flagged in the draft's comment 4: Koestel, Larsbo & Jarvis (2020, *Geoderma*) found no REV for connectivity measures, so sub-volume splitting of a single scan (the trick already used for PSD stats, Fig 4b) is not a defensible way to get statistical replication for these metrics specifically.

**The fix is real physical replicates, not sub-volume splitting — and Track E can get more of them than Track A/B can.** Track A/B (POM shape/spacing metrics) need a valid 3-class segmentation (matrix/POM/pore), and several known volumes fail that gate (`Cu011_samp_2`'s POM channel collapsed; `bnei_reem_samp_2_0_recropped` is stuck pending a visual POM review). **Track E only needs a valid binary pore/solid mask** — it never touches the POM class. A volume disqualified for POM work can still be perfectly usable here. `Cu011_samp_2` is already proof of this (its pore channel was explicitly marked valid and reused for Track E while its POM channel was discarded). This prompt finds every other volume in the same position and runs the established Track E pipeline on all of them.

## What already exists — don't rediscover, reuse

Read these before starting; they define the pipeline exactly and it must not drift between runs:
- `connectivity_topology_validation_prompt.md` + `connectivity_validation_summary.md` — the extended-mode topology run (χ, connectivity density, Γ, DA, tortuosity), sign convention, sanity checks.
- `connectivity_crossover_radius_prompt.md` + `crossover_radius_summary.md` — the χ(r)/crossover-radius sweep, **including the local-thickness masking bug and its fix (below) — do not reintroduce the bug.**
- `DATA_CATALOG.md` — current, complete inventory (2026-08-29). Its **"Analysis-tier policy"** section already states the rule this prompt relies on: every reconstruction with a valid pore channel is in scope for structural/topology metrics (Track E) regardless of POM status — this includes volumes excluded from POM work. Read it as given; Part 1 below just lists the concrete candidates it already identifies.

### The pipeline, consolidated (apply identically to every volume in this prompt)

1. **Segmentation → binary pore mask.** Reuse each volume's existing valid segmentation (deployed label convention pore=5; for binary Rehovot-style segmentations, pore is the foreground class directly). Do **not** run new model inference unless a volume has no segmentation at all yet — see "What to skip, not guess" for the rule on when that's allowed.
2. **Topology metrics (extended mode).** 1-voxel border trim, 26-connectivity. `euler_number` (χ) via the established function; `connectivity_density_per_mm3 = -euler_number / volume_mm3` (Herring et al. 2015 sign convention — higher = more connected); `connectivity_probability_gamma` (Γ, Jarvis/Larsbo/Koestel 2017); degree of anisotropy `DA` via fabric-tensor eigenvalues (Odgaard 1997) on the connected/percolating pore mask; per-axis diffusive tortuosity via `porespy.simulations.tortuosity_fd`. **Tortuosity caveat, already root-caused — apply it up front, don't rediscover:** this solver can raise `Exception: Solver failed to converge, exit code: 1000` on a genuine non-convergence, which a broad `except → NaN` will silently misreport as "no percolating path." Catch and log the actual exception text per axis; report a NaN only with its cause attached (solver non-convergence vs. genuine disconnection), never bare.
3. **Local-thickness / diameter map.** `porespy.filters.local_thickness(method='imj')` on the pore mask. **Known bug — mask it every time:** this leaks nonzero thickness into a ~22%-larger shell outside the true pore mask. Always compute `pore_mask_true = raw_pore_mask & (diameter_map_px > 0)` before using the diameter map for anything (PSD binning or χ(r)).
4. **χ(r) connectivity function + crossover radius.** Sweep r over the run's own `bin_edges_um` (from its `result_psd.json`, so the curve overlays that volume's own PSD). At each r: `pore_mask_r = raw_pore_mask & (diameter_map_px >= r_px)`, recompute χ on `pore_mask_r`. **Required sanity check, per volume:** χ at the smallest r must equal the volume's own recorded full-mask `euler_number` exactly — if it doesn't, stop processing *that volume* (log it, move to the next one, don't abort the whole run). Interpolate the sign-change crossover r* in log-diameter space; if none exists in range, report the trend (all-positive / all-negative) instead of extrapolating. Flag any r* within ~2–3 voxel widths of that volume's voxel size as resolution-limited.
5. **Volume back-calc sanity check** (used successfully in the prior two runs): recompute physical volume from voxel count × voxel size³ and confirm it matches the run's recorded sample volume exactly, before trusting connectivity_density.

## Part 1 — Candidate volumes (already established in `DATA_CATALOG.md` — no sweep, no catalog edits)

The share sweep and specimen-identity work is done; these are the concrete candidates as of the 2026-08-29 catalog. Existing Track E runs (already under `Topology_Metrics_Aug2026/raw/` — do not re-run): Bnei Re'em canonical (Specimen A, old reconstruction), Mishmar native (`mishmar_native`, 5.85 µm), Rehovot `samp2` (canonical), Mishmar `Cu011_samp_2`.

**Ready to run now (valid pore channel, existing segmentation, no new inference needed):**
- Bnei Re'em Specimen B (`bnei_reem_samp_2_0_recropped`) — genuine second physical Bnei Re'em specimen. Pore-only, valid. **This is the headline new replicate.**
- Bnei Re'em Specimen A's redo (`bnei_reem_samp_2_rec_recropped`) — a fresh reconstruction of the *same* physical core as canonical (not a second specimen — see the reconstruction-vs-specimen note in Part 3). Valid pore channel. Worth running as a processing-robustness check, but do not count it as a second Bnei Re'em replicate when consolidating.
- Mishmar `mishmar_hanegev_maoz_2_8p8um` (2nd physical Mishmar specimen, 8.8 µm native) — valid, plausible pore fraction. Prefer running topology at native 8.8 µm resolution if that segmentation exists on the share; otherwise use the already-produced ~15 µm label-downsampled version and note the resolution.
- Rehovot `Rehovot_samp3_highkV_Cu0.11_15um` — fully processed (both models run, same setup as `samp2`), valid, genuine second physical Rehovot specimen, simply never run through Track E yet.

**Excluded — same physical core as an existing run, not a new replicate:** `mishmar_label_downsample`, `mishmar_image_then_predict` (both derived from `mishmar_native`); `bnei_reem_samp_2_0` original uncropped (superseded by `_recropped`).

**Needs Rony, skip for now (see "What to skip, not guess"):** Mishmar `Cu011_samp_1` and `Cu011_samp_3` — raw scans exist but are only partially preprocessed (no full-height crop/norm200/NLM, no inference), and the catalog itself flags `⚠ NEEDS RONY` on whether to run them through the full pipeline. Rehovot `samp1` — raw only, never preprocessed at all, no catalog note that this is authorized yet.

## Part 2 — Run the pipeline on every ready-to-run volume from Part 1

1. If it has no segmentation yet: run inference **only** if the correct model/checkpoint for that soil is unambiguous per `DATA_CATALOG.md`'s "Known model branches" section (already confirmed for Bnei Re'em and Mishmar; confirm Rehovot's while sweeping in Part 1). If ambiguous, **skip and flag** — do not guess a model.
2. Run the full pipeline from "The pipeline, consolidated" above: topology metrics → `summary.json`, PSD/local-thickness → `result_psd.json` + `psd_table.csv`, χ(r) sweep → `chi_r_<run>.csv`.
3. Write outputs to `Topology_Metrics_Aug2026/raw/<run_id>/` and `Topology_Metrics_Aug2026/connectivity_function/` on the network drive (the canonical, non-`V2` location — confirmed repeatedly that no `V2` folder exists; do not create one).

## Part 3 — Consolidate into a real multi-replicate connectivity dataset

Build a master table, one row per completed run, columns: soil, sample ID, voxel size, χ, connectivity density, Γ, DA, tortuosity (per axis + convergence caveat), r*, resolution-limited flag. Then, **grouped by soil, distinguishing genuine physical replicates from a) derived/resampled versions and b) re-reconstructions of the same physical core** (per Part 1 — never mix any of these into one mean):

- Bnei Re'em specifically: canonical and Specimen A's redo (`bnei_reem_samp_2_rec_recropped`) are the **same physical core**, reconstructed twice — report both numbers (useful as a processing-robustness check, same idea as the Mishmar downsample ablation) but treat them as **one** physical replicate, not two. Specimen B (`bnei_reem_samp_2_0_recropped`) is the genuine second physical replicate. So Bnei Re'em goes from n=1 to n=2 physical specimens (up to 3 reconstructions reported).
- For any soil now at n≥2 genuine physical replicates: report mean ± SE per metric alongside the per-replicate values, and say explicitly that this is now a legitimate physical-replicate SE — not the sub-volume pseudoreplication comment 4 warns about.
- For any soil still at n=1: say so plainly, don't compute an SE from n=1.
- Note which soils gained replicates from this run and which didn't.

## Output

- New runs under `Topology_Metrics_Aug2026/raw/<run_id>/` and `connectivity_function/` on the network drive, same structure as the existing 4.
- `connectivity_replicate_expansion_summary.md`: what was run and why (per Part 1's candidate list), what was skipped and why (per "What to skip, not guess"), the consolidated multi-replicate table per soil, and updated mean±SE where n≥2 now holds.
- Chat: short version of the same — replicate counts before/after per soil, headline new mean±SE numbers, anything skipped and why.

## What to skip, not guess (autonomy boundaries)

Skip and flag, don't block on or guess, any of:
- Mishmar `Cu011_samp_1` / `Cu011_samp_3` — the catalog itself flags these `⚠ NEEDS RONY` (whether to run the full preprocessing pipeline on them at all). Do not preprocess or infer on these; leave for Rony to decide.
- Rehovot `samp1` — raw only, no preprocessing done, not authorized in the catalog.
- Anything that would require new POM/3-class segmentation work — out of scope for this track entirely, even incidentally.
- Any volume whose pore fraction looks implausible (near-zero or near-100%) even if a segmentation exists — flag as a possible channel-collapse candidate rather than including it uncritically.

None of these should stop the rest of the run — process everything in Part 1's "ready to run now" list and report the skipped items clearly.

## Sanity checks (do not skip)

- Per volume: χ(r=smallest r) must equal the volume's own recorded full-mask `euler_number` exactly, and back-calculated volume must match recorded sample volume exactly — both required before that volume's numbers are trusted.
- `pore_mask_true = raw_pore_mask & (diameter_map_px > 0)` applied at every step that touches the diameter map (never the unmasked thickness map directly).
- No physical volume is double-counted as two replicates via a resampled/reprocessed derivative, or a second reconstruction, of itself (see the Bnei Re'em redo and `mishmar_label_downsample`/`mishmar_image_then_predict` notes).
- No pooling of raw metrics across soils or across resolutions — report per-soil, per-resolution, exactly like the existing 4-run table already does.
