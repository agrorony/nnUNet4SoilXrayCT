# Prompt — produce actual, inspectable proof about Bnei Re'em Specimen B's data quality

> Paste into Claude Code, in the PSD/topology pipeline repo. This is NOT a request to re-argue whether the prior "trajectories" claim was right or wrong — Rony has directly observed something visually abnormal in napari and that observation stands on its own regardless of what any log says. The goal here is to produce concrete artifacts (images, numbers) that a human can look at and judge for themselves — not another narrative conclusion. Do not write a summary that asserts "everything is fine" or "the claim is confirmed" without the actual images/numbers attached for independent inspection. Fully autonomous — don't stop for input, flag and continue instead.

## Why this exists

A prior investigation checked file paths, voxel fractions, and preprocessing logs for `bnei_reem_samp_2_0_recropped` and found nothing wrong — but that only rules out a *wrong-file* bug. It does NOT address what Rony actually observed: loading this segmentation in napari looks visually very different from every other scan in this project, and looks more like acquisition trajectories/motion artifact than a normal pore structure. A clean log and a matching pore fraction are consistent with a genuine CT motion artifact in the raw scan itself (garbage in, correctly processed, still garbage) — they don't rule it out. This prompt produces the actual evidence needed to judge that directly.

## Part 0 — Decisive provenance check: does the catalogued segmentation actually trace back to Rony's chosen raw reconstruction? (do this FIRST — it may settle the question on its own)

Rony has identified the specific raw reconstruction he decided to work with for this Bnei Re'em scan: **`C:\Users\rony.schwartz\Desktop\new_rec`** (on the remote/reconstruction computer — a different machine from the one this repo normally runs on, so locate it there, e.g. via a network path, remote session, or however that machine is normally reached). His own framing, verbatim: if the segmentation `DATA_CATALOG.md` points to for Specimen B was produced from this exact raw data, the r*≈451µm finding is legitimate; if it was not, then the mistake he originally flagged did happen — just not in the form first described.

1. Identify the raw slice stack in `new_rec` — file count, per-slice dimensions, bit depth, and (if available) file timestamps/creation dates.
2. Trace `bnei_reem_samp_2_0_recropped`'s full preprocessing chain backward from the catalogued segmentation (`nnUNet_resources\bnei_reem_samp_2_0_recropped\inference_concatenated\...`) to whatever raw input it actually started from — the same preprocessing log already used in the prior investigation (`05_evaluation/psd/full_volume_batch/logs/preprocess_samp_2_0.log` / `recrop_samp_2_0_retry.log`) should name or imply the raw source directory it read from first.
3. **Compare the two directly**: slice count, per-slice pixel dimensions, and file timestamps between `new_rec` and whatever the preprocessing log shows as its actual raw input. If a byte-level or hash comparison of a few slices is feasible (e.g. the raw TIFFs are accessible from both references), do that too — it's more conclusive than metadata matching alone.
4. Report a direct yes/no: **does the segmentation used for Specimen B's Track E numbers derive from `new_rec`, or from a different raw source?** If it's a different source, name exactly which directory/scan it actually came from, and say so plainly — this would mean Rony's original concern was correct in substance, even though the specific "trajectories file" mechanism wasn't confirmed by the earlier check.
5. If this check is decisive either way, the remaining parts (1–3 below) become confirmatory rather than essential — still worth doing for the record, but say up front in the report which way Part 0 already points.

## Part 1 — Side-by-side 2D image evidence (must produce actual PNG files, not descriptions)

For **`bnei_reem_samp_2_0_recropped`** (the volume in question) and **canonical Bnei Re'em** (`bnei_reem_fresh_bnei_reem_i4`), as a control:

1. Export midslice PNGs (raw grayscale CT slice with the segmentation labels overlaid as a semi-transparent mask) at the **center slice of all 3 axes** (not just axis 0) for both volumes — 6 images total. Use the same colormap, contrast/window settings, and overlay opacity for both, so they are visually comparable.
2. Additionally export the **raw CT slice alone** (no segmentation overlay) at the same 6 slice locations, so a raw acquisition artifact (streaking, banding, ring artifacts, motion blur) can be judged independently of the segmentation.
3. Save all 12 images with clear filenames (e.g. `specB_axis0_mid_raw.png`, `specB_axis0_mid_overlay.png`, `canonical_axis0_mid_raw.png`, etc.) into a new folder, `bnei_reem_specB_visual_evidence/`.

## Part 2 — Reproduce the actual napari view Rony saw, as a static image

1. Re-run the exact napari command already on record for this volume (`napari_view_full_volume.py --run-dir ...psd_diag_20260829T164631_bnei_reem_samp_2_0_recropped --segmentation ...bnei_reem_samp_2_0_recropped/inference_concatenated/bnei_reem_samp_2_0_recropped.nii.gz --raw-source .../bnei_reem_samp_2_0_recropped_0000.nii.gz --pore-label 5 --pom-label 2 --axis 0`), but headless — capture an actual screenshot of the 3D rendered view (napari supports off-screen screenshot capture; if that's not straightforward, use an equivalent volume-rendering tool — matplotlib's `voxels`, PyVista, or similar — rendering the same pore-label (5) volume from a fixed, documented camera angle).
2. Do the same for canonical Bnei Re'em's pore label, from the same camera angle/settings.
3. Save both screenshots into the same evidence folder. These should let Rony (and Claude, once retrieved) see the same thing he saw when he made the original observation — not a re-description of it.

## Part 3 — Objective motion-artifact screening on the RAW CT volume (before any segmentation)

CT motion artifacts have known objective signatures independent of anyone's visual impression — check for them quantitatively, on the raw preprocessed CT volume (`_0000.nii.gz`, the actual scanner-derived intensity data), not the segmentation:

1. **Slice-to-slice consistency**: compute the correlation (or SSIM) between each consecutive raw slice along each of the 3 axes, for both Specimen B and canonical. A genuine motion artifact typically shows abrupt discontinuities or periodic drops in slice-to-slice similarity that a normal scan doesn't.
2. **Periodic banding / streak detection**: compute the 1D power spectrum (FFT) of the mean intensity profile along each axis for both volumes. A periodic banding pattern (like acquisition trajectory artifacts) shows up as an anomalous peak in this spectrum that a clean scan won't have.
3. **Basic intensity statistics per slice** (mean, std, min, max) plotted as a line across all slices along each axis, for both volumes — plot them together so any abrupt jump, drift, or oscillation unique to Specimen B is visible on one chart.
4. Report all three checks as actual plots (PNG) saved into the evidence folder, not just pass/fail text.

## Part 4 — Report

Write `bnei_reem_specB_visual_evidence/README.md` that:
- Lists every image/plot produced with a one-line caption of what it shows.
- States plainly, for each of Parts 1–3, whether Specimen B looks different from canonical in that specific check — don't round this up or down to a single verdict; report per-check, since these are genuinely different questions (file correctness vs. raw scan quality).
- Does NOT conclude "the data is fine" or "Rony was right" — presents the evidence and lets a human judge it.

## Delivery — copy everything off the network drive too

Save `bnei_reem_specB_visual_evidence/` under the network drive location as usual, **and also copy the entire folder into the repo** (`nnUNet4SoilXrayCT/bnei_reem_specB_visual_evidence/`) — the network share has been unreliable for remote file access this project, and the repo copy is what Claude can actually retrieve to look at the images directly.

## Sanity checks

- Every image/plot must be an actual saved file, not a text description of what an image would show.
- Part 1's raw-slice images must use identical windowing/contrast settings across both volumes, or the comparison is meaningless.
- Part 3's checks must run on the raw CT intensity volume, not the segmentation — a motion artifact in acquisition would show up before segmentation, and segmentation could either mask or amplify it.
- If canonical Bnei Re'em's own raw scan isn't readily available in the same preprocessing stage (post-NLM, pre-crop) as Specimen B's, use whatever stage is available for both but use the *same* stage for both — never compare two different pipeline stages against each other.
