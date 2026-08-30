# Prompt — Expand ROI where it helps, then finalize the POM clustering (fully autonomous, no check-ins)

> Paste into Claude Code. Every decision point below has an explicit rule — follow it and proceed, don't pause to ask Rony anything. Log every decision and its reasoning in the final report instead.

## Scope

Only these 3 volumes, same as `pom_final_clustering_prompt.md`'s run: Bnei Re'em canonical (`nlm_volume`), Mishmar native (5.85 µm), Mishmar second sample (~8.8 µm). Do not add `bnei_reem_samp_2_0`, `samp_2_0_recropped`, or any other volume.

## Part 1 — Check how much raw volume exists beyond the current crop

For each of the 3 volumes: find its raw (post-reconstruction, pre-crop) scan and compare its full dimensions to the crop actually used (currently 650³ for Bnei Re'em / equivalent for Mishmar). Compute the extra linear margin available beyond the current crop on each axis.

**Decision rule:** if the raw scan offers less than 15% more linear extent beyond the current crop on every axis, skip re-cropping for that volume — log "insufficient extra volume, kept existing crop" and move to Part 3 for it. Otherwise proceed to Part 2 for that volume.

## Part 2 — Enlarge the crop safely, per volume that qualifies

1. Determine the largest symmetric, center-aligned cubic crop possible without exceeding the raw scan's own dimensions, capped at 90% of the raw scan's shortest axis (never crop all the way to the raw edges).
2. Safety check for the sample holder: scan the intensity histogram in thin shells moving outward from the current (known-good) crop boundary toward the proposed new boundary. The sample holder/mount produces a distinct, sharply different intensity signature from soil (either a very high-density ring or a sharp air gap) — if such a signature appears before reaching the proposed new boundary, stop the crop at the shell just before it appears, not at the originally proposed size. Log the final crop size chosen and why.
3. Re-run the full standard pipeline on the newly cropped raw volume: norm200 → NLM → inference with the correct model for that soil (Bnei Re'em: `multi_sample_fresh_bnei_reem_i4`; Mishmar: `i2_loess`). Save as a new output, don't overwrite the existing crop's output.
4. Sanity check: pore/POM voxel fractions should not show the channel-collapse pattern (a phase crashing toward zero while others stay normal). **This is the only disqualifying criterion** — do not reject an enlarged crop merely because its fractions differ in magnitude from the original crop's. If it fails this check, discard the enlarged version, log why, and fall back to the volume's existing (already-trusted) crop for the rest of this prompt.

## Part 3 — Final feature extraction and clustering

Using whichever crop each volume ended up with (enlarged-and-passed, or existing-because-insufficient-margin, or existing-because-enlarged-failed-sanity):

1. Use the same pinned methodology as `pom_final_clustering_prompt.md`: marching-cubes sphericity, PCA elongation/flatness, minimum-resolvability cutoff of 20 voxels across equivalent diameter (~300 µm at this project's voxel size).
2. Extract shape/spatial features, fit a scaler on only these 3 volumes' objects, cluster, match archetypes across volumes — same procedure as the prior "final" run.
3. Report Bnei Re'em (n=1, descriptive point) vs. Mishmar (n=2, mean ± SE), same table format as the prior "final" report.
4. **Comparison table**: object counts before/after the resolvability cutoff, this run vs. the prior "final" run, per volume — so the effect of any ROI expansion on object count is visible directly.

## Part 4 — Cutoff sensitivity check (secondary)

Repeat the Part 3 feature extraction and per-volume object counts (not full clustering) at resolvability cutoffs of 15, 20, and 25 voxels, using whatever crop each volume ended up with from Parts 1-2. Report object counts per volume per cutoff, and re-run the archetype clustering at 15 and 25 in addition to 20. State plainly whether the one notable finding from the prior run (Bnei Re'em having zero objects in the two archetypes both Mishmar replicates have some objects in) holds at all three cutoffs or only some.

## Output checklist

- Part 1: raw-vs-crop margin per volume, and the re-crop decision (with reasoning) for each.
- Part 2: for each volume that got a larger crop — final crop size chosen, holder-safety check result, sanity-check pass/fail, and if failed, confirmation the original crop was used instead.
- Part 3: final clustering table (same format as the prior "final" report) plus the object-count comparison table (this run vs. prior run).
- Part 4: cutoff-sensitivity table (object counts + archetype results at 15/20/25 voxels) and an explicit statement on whether the main finding is cutoff-robust.
- A one-paragraph plain-language summary at the top of the report: did ROI expansion help, and is the main finding from the prior run still standing.

## Sanity checks

- Never crop all the way to the raw scan's physical edge — always leave the 10% safety margin described in Part 2.
- Never disqualify an enlarged crop for a magnitude difference alone — only for channel collapse.
- Never overwrite the prior "final" run's outputs — this is a new, separately labeled run.
- If any step is ambiguous and no rule above resolves it, make the most conservative choice (keep the existing, already-trusted crop/volume) and log that this happened — do not stop and wait for input.
