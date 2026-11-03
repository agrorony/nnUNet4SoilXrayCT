# Prompt — Re-preprocess and re-segment `bnei_reem_samp_2_0` through the standard pipeline

> Paste this into Claude Code, in the PSD/topology pipeline repo. Follow-up to the root-cause finding that `bnei_reem_samp_2_0` was excluded from `pom_replicate_comparison_prompt.md` (implausible POM/pore fraction) because it skipped the center-crop step before inference. This prompt checks whether it also skipped other standard preprocessing steps, and produces a properly preprocessed replacement.

---

## Why this task exists

The prior diagnostic confirmed `bnei_reem_samp_2_0` was segmented with the correct model (`multi_sample_fresh_bnei_reem_i4`, `checkpoint_final.pth` — same as the canonical trusted volume), but its input was never center-cropped: shape 1344×896×1800 (the full raw scan) instead of the canonical ~650×650×652 crop. Its driver script (`run_bnei_reem_samp_2_0_pipeline.py`) goes straight from raw NLM output to `tif_direct`, skipping `crop_center_and_preprocess.py`.

**Open question this prompt resolves first:** the canonical Bnei Re'em volume's filename (`bnei_reem_fresh_bnei_reem_i4/inference_concatenated/nlm_volume.nii.gz`) implies non-local-means (NLM) denoising is a standard preprocessing step, and Rony also applies a "mod 200" step (his own preprocessing convention — likely a padding/reshaping step to make dimensions divisible by 200 for patch-based tiling, but confirm the actual purpose from the script itself rather than assuming). Given `bnei_reem_samp_2_0` skipped the crop step, it may well have skipped these too. **Don't assume — check directly**, the same way the crop-skip was confirmed: read `run_bnei_reem_samp_2_0_pipeline.py` line by line against whichever script(s) implement the canonical pipeline (the ones that produced `bnei_reem_fresh_bnei_reem_i4/inference_concatenated/nlm_volume.nii.gz` and every other successfully-used volume in this project), and list every preprocessing step present in the canonical pipeline but absent from `bnei_reem_samp_2_0`'s driver script — not just the crop.

## Part 1 — Audit (report before changing anything)

1. Identify the canonical preprocessing pipeline's full step sequence, in order (e.g. NLM denoise → mod-200 pad/reshape → center-crop → whatever else exists), by reading the scripts that produced the trusted `bnei_reem_fresh_bnei_reem_i4` volume and confirming the same sequence was used for the other trusted volumes in this project (Mishmar native, etc. — check at least one non-Bnei-Re'em volume too, to make sure this is a universal pipeline and not soil-specific).
2. Diff that sequence against what `run_bnei_reem_samp_2_0_pipeline.py` actually does, step by step. Report the full list of missing/skipped steps — the crop is already confirmed missing; explicitly confirm whether the NLM filter and the mod-200 step were applied or skipped for this volume, and report any other discrepancy found.
3. Check whether `bnei_reem_samp_2_0`'s raw input is already NLM-filtered from an earlier step (i.e. maybe NLM ran but crop+mod200 didn't) — don't assume all-or-nothing; report exactly which steps ran and which didn't.

## Part 2 — Re-run the full standard pipeline on `bnei_reem_samp_2_0`

1. Starting from `bnei_reem_samp_2_0`'s raw scan (not the partially-processed output that produced the excluded result), run it through the complete canonical preprocessing sequence identified in Part 1, in the correct order, using the same scripts/parameters as every other trusted volume in this project — no shortcuts, no reuse of the previous partial output.
2. Run inference with the correct Bnei Re'em model (`multi_sample_fresh_bnei_reem_i4`, `checkpoint_final.pth` — already confirmed correct) on the properly preprocessed volume.
3. Report the resulting shape and voxel size, and confirm it now matches the canonical convention (or explain if `bnei_reem_samp_2_0`'s native scan geometry legitimately differs and what the expected post-crop shape should be for this specific sample).

## Part 3 — Sanity check before reuse

1. Report pore/POM voxel fraction for the newly (properly) preprocessed `bnei_reem_samp_2_0`, compared against the canonical Bnei Re'em volume's fractions (pore/POM %) and against the implausible values that got it excluded the first time. It should land in a plausible range relative to the canonical volume — flag and stop (don't proceed to Part 4) if it still looks collapsed or otherwise implausible; that would mean the crop/preprocessing gap wasn't the whole story.
2. Save this as a new, clearly-named output (e.g. `bnei_reem_samp_2_0_recropped`) — don't overwrite the excluded first attempt, keep both on record with the outcome noted.

## Part 4 — Redo the group comparison and clustering with Bnei Re'em at n=2

If Part 3 passes:

1. Run the full POM pipeline (A1 cutoff, A2 conditioned distance maps, A3 accessibility, B size distribution — same methodology as `pom_replicate_comparison_prompt.md`) on the newly preprocessed `bnei_reem_samp_2_0`.
2. Redo Part 4 (group comparison) and Part 5 (clustering) from `pom_replicate_comparison_prompt.md`, this time with Bnei Re'em at n=2 (canonical + newly fixed `bnei_reem_samp_2_0`) and Mishmar still at n=2. Report the updated per-replicate table, group mean±SE for both soils now, and note how the Bnei Re'em group's own within-soil variability (n=2) compares in magnitude to what was found for Mishmar (44% difference between its two replicates on distance-to-POM) — this is directly comparable now that both soils have n=2.
3. Redo the cross-soil clustering/archetype comparison with all 4 volumes (2 Bnei Re'em + 2 Mishmar), same script version and scaler-pooling discipline as before (fit only across these 4 volumes, nothing else).

If Part 3 fails (still implausible after proper preprocessing): report that plainly, do not proceed to Part 4, and say what's left to investigate — at that point the sample itself, not the pipeline, becomes the more likely explanation.

## Output checklist

- Part 1 audit report (full list of skipped steps, not just the crop) — in chat, before any recomputation.
- Part 3 sanity-check result, explicit pass/fail against the canonical volume's fractions.
- If passed: updated Part 4 group table (both soils now potentially n=2) and Part 5 clustering, in the same format as `pom_replicate_comparison_prompt.md`'s output, so it's a direct drop-in replacement/update.
- If failed: a plain report of what's still wrong, with Bnei Re'em correctly remaining at n=1.

## Sanity checks

- The properly-preprocessed `bnei_reem_samp_2_0` should NOT still show the implausible fraction that got it excluded originally — if it does, the crop/preprocessing gap was not the (or not the only) cause, and that needs to be said explicitly rather than silently re-including a still-bad sample.
- Voxel size and shape after proper preprocessing should be internally consistent with the canonical Bnei Re'em convention.
- Do not overwrite or delete the original excluded `bnei_reem_samp_2_0` output — keep it on record with a note explaining why it was superseded, for traceability.
