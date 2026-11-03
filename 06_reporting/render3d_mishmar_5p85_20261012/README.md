# 3D render of the Mishmar HaNegev 5.85 µm segmentation (2026-10-12, HIVE3065)

Visualization only: no new metrics, no retraining, no inference, nothing existing modified. Target look: Dor et al. 2025 Fig. 1a (`dor2025_fig1a_reference.png`). Large intermediates are on the share in `E:\PROJECTS\Yael_Mishael\Rony\remote_computer backup\render3d_mishmar_5p85_20261012\` (meshes, volumes, diameter map, raw frames — regenerable with `scripts/`; note the HIVE3065 60-day retention banner). Not committed.

Note on location: written into the repo at `E:\...\nnUNet4SoilXrayCT` (current, contains the prompt and `make_fig7.py`), not `C:\Users\rony.schwartz\Documents\nnUNet4SoilXrayCT`, which is a stale older checkout.

## Step 0 results
- File: `...\nnUNet_resources\mishmar_hanegev_maoz_3_5p85um\inference_output_concat_loess_i2\mishmar_hanegev_maoz_3_5p85um.nii.gz`, 52,131,807 bytes, **mtime 2026-07-16 00:28:11** (prompt expected 00:27 — one minute off; content checks below pass, so treated as the same file).
- Shape 1000³, uint8, header zooms **1.0 × 1.0 × 1.0** (wrong; 5.85 µm used), axcodes RAS. Labels exactly {0, 1, 2, 5}. Pore (5) 27.0385 %, POM (2) 1.6147 % (DATA_CATALOG 27.038 / 1.615: pass). Label 1 = 1.1177 %, not drawn.
- Axis convention: vertical = nibabel axis 2 (slice stack), shown vertical; `np.flip(seg, 1)` applied as in `make_fig7.py`.
- GPU: `OpenGL renderer: NVIDIA RTX A6000/PCIe/SSE2`, `version 4.5.0 NVIDIA 572.61` (RDP session, but hardware GL). 1 TB RAM, 46 GB per GPU, so no block meshing was needed (whole-volume meshes, no seams to check).
- New env `C:\Users\rony.schwartz\venv-render3d` (venv-napari and Anaconda base untouched): pyvista 0.49.1, vtk 9.7.1, nibabel 5.4.2, scipy 1.18.1, scikit-image 0.26.0, matplotlib 3.11.2, porespy 3.1.1, numpy 2.5.4, numba 0.68.0, pillow 12.3.0, tifffile 2026.9.20.

## Common settings (all options)
- Native 5.85 µm grid, no downsampling. Surfaces: Gaussian σ = 0.8 voxel on each binary mask, contour at 0.5 (vtk flying edges), point normals, Phong shading.
- Specks < 27 voxels (6-connectivity) hidden: **POM 0.147 %** of POM volume (4,966 of 6,533 components); **pores 0.104 %** (37,005 of 68,652 components). Both well under 1 %.
- No decimation (full 9.1 M-triangle POM mesh, 258.9 M-triangle open pore mesh, 261.8 M-triangle closed pore mesh). Mesh points: POM 4.59 M, pore 129.6 M (open) / 130.8 M (closed).
- Colors: pores `#4F9A98`, POM `#B3A23F` opaque, specular 0.45 (power 30); white background; `#555555` cube outline, 2 px. VTK light kit (three lights), parallel projection, SSAA, SSAO radius 45 µm / bias 5 µm / kernel 256 / blur (Options 1, 3; not used for Option 2, whose volume layer is not SSAO-compatible).
- Camera (`camera.json`): z-up, azimuth 40°, elevation 28°, cube fills 80 % of frame. Identical for all options.
- Output 3000 × 3000 px: PNG on white, PNG transparent, TIFF (LZW; white and transparent). Legend in English, added in matplotlib after rendering. Scale: dimension arrow along a cube edge labeled `5.85 mm` (close-ups: `1.2 mm`); no flat 2D bar.
- Close-ups: same scene and camera angle, clipped to a **1.20 mm** box (shifted inward so it lies fully inside the volume; centre 585→600, 600, 4095 µm, around the POM-richest 1.17 mm window). Surfaces are clipped to the box (otherwise the 5.85 mm depth column would swamp the view); no resampling. **Updated 2026-10-13:** POM mesh Taubin-smoothed in close-ups only (30 iterations, pass band 0.1; display-only; mean displacement 1.53 µm, max 5.29 µm = 0.26 / 0.9 voxel) to remove specular triangle speckle and terracing; labels state the true box (arrow `1.20 mm` + "Box 1.20 × 1.20 × 1.20 mm"); full views carry "Box 5.85 × 5.85 × 5.85 mm". The whole set was re-rendered with the updated `render.py` (raw frames now saved in the share folder).
- Tuning: 300³ full-resolution crop (POM-rich, [0,0,550]) for look, then full volume; roughly 2–3 rounds per option.

## Option 1 — translucent pore surface + solid POM
Pore opacity **0.025** (0.10 and 0.04 were too dense at full scale; 260 M translucent triangles accumulate), depth peeling 20 peels, occlusion ratio 0. Full view render 381 s, close-up 1605 s. No problems besides slow close-up. Fine haze, POM clearly visible through it.

## Option 2 — GPU volume haze + solid POM
Pore mask smoothed (σ 0.8), stored as uint8 0–255 (1 GB), `mapper='gpu'`, constant teal, opacity ramp 0 at ≤100 → 0.2 at ≥200 (of 255), `opacity_unit_distance` 500 µm. First tries (0.6 / 150 µm; 0.15 / 400 µm) were a fog wall / too faint. Render 213 s full, 58 s close-up. Problems: PyVista silently draws nothing for a 256-length opacity list; a 65-point ramp is used. The POM mesh is opaque and in the same scene (correct depth compositing observed).

## Option 3 — pores colored by diameter + solid POM
- **Diameter source: recomputed** (no saved map exists in `psd_diag_20260803T010446_..._scratch_i2`, which holds only `distance_to_*` maps and per-block summaries). Used the repo's `psd_diagnostics_core.run_psd_pipeline` (porespy `local_thickness`, method `imj`) on `loess_i2` with that run's config: chunked EDT 128³ / halo 50, `exclude_borders`, extended bin edges, CPU; 12,772 s. Applied the pipeline guard `pore_mask & (diameter_map > 0)`.
- **Validation: the recomputed bin counts equal that run's `psd_table.csv` exactly (all 32 bins, total 268,974,742 voxels, max difference 0).** This also confirms that `scratch_i2` and `loess_i2` are the same segmentation.
- Vertex coloring: nearest pore voxel (diameter > 0) per vertex via EDT indices, in µm (diameter voxels × 5.85); no zero-valued vertices. Pore surface is the closed (face-capped) mesh.
- **Color range 11.7–105.9 µm = 2nd–98th percentile of vertex values**, with an "≥" arrow. (The voxel-based 2–98 % range, 16.5–226 µm, was tried first; surfaces sit on small pores, so most of the picture was one dark purple.) Colormap is viridis **truncated at 0.65** (ends green) because the top of viridis is yellow and reads as POM.
- Render 297 s full, 1112 s close-up. Opaque pores occlude POM, so far less POM is visible than in Options 1–2 (inherent to this view, also in Dor Fig. 1c).

## Deliverables
`renders/option{1,2,3}_{full_view,closeup}_{white,transparent}.{png,tiff}`, `contact_sheet.png` (Dor reference crop + 3 full views), `scripts/` (step0a/0b checks, step1 mesh, step2 diameter map, step3 vertex coloring, render, step4 contact sheet, run_final shell wrappers), `camera.json`, `render_params.json`, `mesh_stats_full.json`, `diameter_map_check.json`.

## Known issues
- Transparent PNG/TIFF: alpha comes from the VTK framebuffer; check edges against your final background before publication.
- NIfTI header spacing is 1.0 (wrong); 5.85 µm was forced.
- (Fixed 2026-10-13: the close-up speckle and the 1.2 mm vs 1.185 mm label.)

## Which looks most professional
**Option 2 (GPU volume haze)**: the lightest, most Dragonfly-like haze, POM pops, and it reads best at the 5.85 mm scale; Option 1 is the robust close second; Option 3 is the most informative (size structure) but hides POM and is darker.
