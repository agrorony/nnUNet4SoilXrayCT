# 3D render of Bnei Re'em (Vertisol), 15 µm — 2026-10-13, HIVE3065

Same three options and the same rules as `../render3d_mishmar_5p85_20261012/` (visualization only; no new metrics/inference; nothing existing modified; not committed). Named only "Bnei Re'em (Vertisol)" everywhere; not Specimen A/B. Large intermediates: `E:\PROJECTS\Yael_Mishael\Rony\remote_computer backup\render3d_bnei_reem_20261013\` (meshes, volumes, diameter map, raw frames; regenerable with `scripts/`; HIVE3065 60-day retention applies). Pair figures: `../render3d_pairs_20261013/`.

## Step 0 results
- File: `...\nnUNet_resources\bnei_reem_fresh_bnei_reem_i4\inference_concatenated\nlm_volume.nii.gz` (model `multi_sample_fresh_bnei_reem_i4`), 11,871,558 bytes, mtime 2026-07-06 13:19:47. Shape **650 × 650 × 652** (nibabel order; 652 = slice stack = vertical), uint8, header zooms **1.0 × 1.0 × 1.0** (wrong; **15.000149 µm** forced). Box = 9.75 × 9.75 × 9.78 mm.
- Labels exactly {0, 1, 2, 5}. Pore 21.6364 % (rounds to 21.64), POM 0.8189 % (0.82), label 1 = 2.1039 % (not drawn). Pass.
- **Mirror check (not assumed).** Raw/NLM input: `10.5\nlm_volume.tif` (652,650,650) transposed to (650,650,652). (The `bnei_reem_specB_unified` raw NIfTI is 650³ and could not be compared voxel-wise, so it was not used.) corr(pore mask, raw) under flips of the segmentation (pores are dark → strongly negative = aligned):

| flip axes | none | 0 | **1** | 2 | 0,1 | 0,2 | 1,2 | 0,1,2 |
|---|---|---|---|---|---|---|---|---|
| corr | −0.019 | −0.045 | **−0.857** | +0.015 | −0.037 | −0.002 | −0.042 | −0.019 |

  Flip nibabel axis 1 (same as Mishmar and Fig. 7). Slice-stack axis 2 is vertical (confirmed by the transposed raw matching in shape and correlation).
- GPU: NVIDIA RTX A6000 (OpenGL 4.5), same environment as Mishmar (`venv-render3d`).

## Settings: reused, and what changed vs Mishmar (and why)
Reused unchanged: colors (`#4F9A98` pores, `#B3A23F` POM), camera (z-up, azimuth 40°, elevation 28°, 80 % fill, `camera.json`), light kit, SSAA, parallel projection, legend style, outputs (3000×3000 px; PNG white + transparent + TIFF), smoothing σ = 0.8 voxel, speck threshold 27 voxels, no downsampling.

Re-tuned for the 15 µm voxel (voxel-relative equivalents of Mishmar's values):
| parameter | Mishmar (5.85 µm) | Bnei Re'em (15 µm) | reason |
|---|---|---|---|
| SSAO radius / bias | 45 / 5 µm | 115 / 12 µm | same radius in voxels (~7.7) |
| Option 1 pore opacity | 0.025 | 0.035 | fewer surface layers per ray (650 vs 1000 voxels, lower porosity) |
| Option 2 `opacity_unit_distance` | 500 µm | 1000 µm | same order in voxels; haze strength matched by eye |
| Close-up box | 1.2 mm (~205 vox) | 2.25 mm (150 vox), POM-rich, centre 7380, 4140, 5820 µm | 1–1.5 mm is only 70–100 voxels |
| Option 3 color range | 11.7–105.9 µm | **30.0–366.2 µm** | each soil's own 2–98 % of vertex values |

Tuning: 200³ full-resolution crop for look, then the full volume at 1000 px (1 round); finals rendered once.

## Meshes and hidden specks
Whole-volume meshes (no blocks needed). POM 1.25 M points / 2.49 M triangles; pores 25.1 M points / 50.1 M triangles (open) and 25.4 M / 50.8 M (closed, for Option 3). No decimation. Specks < 27 voxels hidden: **pores 0.20 %** of pore volume (14,914 of 28,562 components); **POM 0.71 %** (5,667 of 6,682 components). Both < 1 %, but the POM figure is larger than for Mishmar (0.15 %) because small POM fragments are a bigger share of this soil's POM.

## Per option
- **Option 1** — translucent pore surface, opacity 0.035, 20 depth-peeling passes. Render 61 s full, 226 s close-up.
- **Option 2** — GPU volume haze (σ 0.8, uint8, ramp 0→0.2 over 100–200/255, 65-point opacity list), solid POM mesh in the same scene. Render 48 s full, 14 s close-up.
- **Option 3** — opaque closed pore surface (flat caps at the box faces) colored by local pore diameter, viridis truncated at 0.65 (so the top is green, not POM-like yellow), color bar with "≥" arrow. **Diameter source: recomputed** — the run `psd_diag_20260802T104738_nlm_volume_fresh_bnei_reem_i4` saved no diameter map. Recomputed with the repo's `psd_diagnostics_core.run_psd_pipeline` configured as that run was (chunked EDT 128³ / halo 50, `exclude_borders`, extended bin edges, CPU; 3,788 s), guard `pore_mask & (diameter_map > 0)`. **Validated: bin counts equal that run's `psd_table.csv` exactly (all bins, total 52,648,772, max difference 0).** Per-vertex diameter = nearest pore voxel; no zero-valued vertices. **Color range 30.0–366.2 µm = 2nd–98th percentile of vertex values** (voxel-based range would be 42–1406 µm). **Colors are not comparable across soils**: different voxel size, different range (the Mishmar bar is 11.7–105.9 µm).
- Render 61 s full, 219 s close-up.

## Fixes carried over from the Mishmar run (applied to both soils)
- **True sizes in labels.** Close-up boxes are kept inside the volume and each image now shows the arrow length plus "Box X × Y × Z mm" computed from the actual rendered box. (The old Mishmar close-up said 1.2 mm for a box that was 1.185 mm on one side because it was clipped at the volume face; it is now shifted inward and truly 1.20 mm.) Full views state the real box (Mishmar 5.85 × 5.85 × 5.85, Bnei Re'em 9.75 × 9.75 × 9.78 mm).
- **POM specular speckle in close-ups.** Tested on a Mishmar close-up: lowering specular alone (0.12) reduced it only partly and left terracing; **Taubin smoothing of the POM mesh (30 iterations, pass band 0.1, close-ups only) removed both** and was adopted. It is display-only; measured displacement: **Mishmar mean 1.53 µm / max 5.29 µm (0.26 / 0.9 voxel); Bnei Re'em mean 4.30 µm / max 17.0 µm (0.29 / 1.1 voxel)**. Full views use the unsmoothed meshes.
- Because raw frames of Mishmar Options 1/2 had not been kept, the whole Mishmar set was **re-rendered** (not only re-composited) with the updated `render.py`; raw frames are now saved in the share folder so overlays can be redone without 3D rendering (`render.py ... recompose`).

## Known issues
- Option 3 close-up: some POM patches show dark speckle where POM and pore surfaces touch (the two separately smoothed surfaces interpenetrate slightly at their shared boundary). Cosmetic, close-up only.
- Opaque pores in Option 3 hide most POM (inherent to the view, as in Dor Fig. 1c).
- Transparent PNG/TIFF alpha comes from the VTK framebuffer; check edges on your final background.
- NIfTI header spacing is 1.0 (wrong) — 15.000149 µm was forced.

## Which option for the pair figure
**Option 2** (GPU volume haze): the same light, Dragonfly-like haze for both soils, POM reads first, and the two panels look like siblings. Option 1 is a close second; Option 3 is useful as a supplement (clearly different pore-size structure) but the color scales differ, so it shouldn't be read as a direct comparison.
