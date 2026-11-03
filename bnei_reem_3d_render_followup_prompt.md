# Follow-up prompt — same 3D renders for Bnei Re'em (run on HIVE3065, after the Mishmar 5.85 µm render run)

Paste this into the same agent session that produced `06_reporting/render3d_mishmar_5p85_20261012/`. If it's a new session, give it the original prompt (`mishmar_5p85_3d_render_prompt.md`) and `dor2025_fig1a_reference.png` as well.

---

Good work on the Mishmar renders. Now do the same three options for the Bnei Re'em (Vertisol) scan Rony annotated and trained on: the legacy "canonical" volume. **Same job, same rules as the Mishmar prompt:** visualization only, no new metrics, no new inference, don't modify existing outputs, don't commit. Write into a new folder `06_reporting/render3d_bnei_reem_20261013/` in the **E: repo** (the C: copy is stale, as you found). Large intermediates go to `E:\PROJECTS\Yael_Mishael\Rony\remote_computer backup\render3d_bnei_reem_20261013\`.

## Input
- Segmentation: `E:\PROJECTS\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources\bnei_reem_fresh_bnei_reem_i4\inference_concatenated\nlm_volume.nii.gz` (model `multi_sample_fresh_bnei_reem_i4`).
- Voxel 15.000149 µm isotropic. **Force this value**, as you did for Mishmar; report what the header says.
- Shape 650 × 650 × 652 in nibabel order (652 = slice-stack / core vertical axis). It is **not a cube**: about 9.75 × 9.75 × 9.78 mm. Label the box with its real dimensions.
- Labels as before: 5 = pore, 2 = POM; don't draw 0 or 1.
- **Naming:** this volume is numerically identical to Specimen B and its specimen identity is unresolved. Call it only "Bnei Re'em (Vertisol)" in legends, titles, file names and the README, never "Specimen A" or "Specimen B". Don't confuse it with `bnei_reem_specA_unified` (the Figure 7 volume) or `bnei_reem_specB_unified`. Those are different files, and the specA one has almost no POM.

## Step 0 — checks (stop and report if any fails)
1. **File and fractions:** report path, size, mtime and `np.unique` (expect only {0, 1, 2, 5}). Pore must round to 21.64 % and POM to 0.82 % (DATA_CATALOG values). Use no cached or other copy.
2. **Mirror check:** don't assume the y-flip. Verify it for this volume against its raw/NLM input as was done on 2026-10-04: correlate the pore mask with the raw under the candidate flips; pores are dark. Apply whichever flip the evidence supports, and report the correlations.
3. **GPU:** same as before — the renderer must be the A6000.

## What to reuse and what to adjust
- **Reuse** the Mishmar scripts, colors, camera angles, lighting, legend style and output formats so the two soils look like one figure set. Keep voxel-relative settings the same: smoothing σ, speck threshold in voxels, and no downsampling.
- **Re-tune** physical-unit settings for the coarser 15 µm voxel and lower porosity: SSAO radius, `opacity_unit_distance` (option 2) and pore opacity (option 1). The goal is that a Bnei Re'em render and a Mishmar render look like siblings at a glance.
- **Close-up:** 1–1.5 mm is only ~70–100 voxels here. Use a ~2–2.5 mm POM-rich region instead.
- **Option 3 diameter map:**
  - Look for a saved map in the existing PSD run `E:\...\remote_computer backup\10.5\psd_outputs\psd_diag_20260802T104738_nlm_volume_fresh_bnei_reem_i4\`. If there is none, recompute it with the repo's PSD code configured as that run was.
  - Apply the `pore_mask & (diameter_map > 0)` guard.
  - Validate the result against that run's `psd_table.csv`, bin by bin.
  - Use this soil's own 2–98 % color range and state it. Cross-soil comparison by color isn't meaningful at different voxel sizes, so say that in the README.
- **Apply the lessons from the Mishmar run:**
  - Close-up and scale labels must state the actual size after clipping. Fix the Mishmar close-up label too: it says 1.2 mm but the box is about 1.185 mm. Re-composite only, no re-render.
  - Try to reduce the triangular specular speckle on POM close-ups, e.g. lower specular on POM in close-ups, or smoother normals. Apply the fix to Mishmar's close-ups too if it works.
  - Look at every regenerated image, including the contact sheets, before you finish.

## Deliverables
- **`render3d_bnei_reem_20261013/`:** the same structure as the Mishmar folder — `renders/`, `contact_sheet.png`, `scripts/`, `camera.json`, `render_params.json`, `README.md` (Step-0 results incl. flip evidence, per-option settings, what changed vs Mishmar and why, problems, your pick).
- **`06_reporting/render3d_pairs_20261013/`:** one image per option with Mishmar (left) and Bnei Re'em (right) side by side.
  - Same camera, colors and legend style for both.
  - Each panel titled in English: "Loess (Mishmar HaNegev), 5.85 µm" / "Vertisol (Bnei Re'em), 15 µm".
  - Each panel keeps its own scale label. Don't imply the two are at the same scale.
- A short note in your final message: which option you'd use for the pair figure, and anything that looks wrong.
