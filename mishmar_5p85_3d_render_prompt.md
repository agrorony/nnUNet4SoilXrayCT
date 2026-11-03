# Prompt — 3D render of the Mishmar HaNegev 5.85 µm segmentation (run on the remote lab computer, HIVE3065)

Paste this into an agent session on the lab computer that has the `nnUNet4SoilXrayCT` repo, the `Yael_Mishael` share and the NVIDIA GPU. Hand the agent `dor2025_fig1a_reference.png` (saved next to this prompt) together with the prompt.

---

You are making a publication-quality 3D image of one soil µCT segmentation for Rony's research exercise. **This is a visualization job only:** no new metrics, no retraining, no new inference, and do not modify or overwrite any existing output. Write everything into `06_reporting/render3d_mishmar_5p85_20261012/` in the repo (on this host: `C:\Users\rony.schwartz\Documents\nnUNet4SoilXrayCT`). Large intermediates (meshes, diameter map) go to `E:\PROJECTS\Yael_Mishael\Rony\remote_computer backup\render3d_mishmar_5p85_20261012\` on the share, not into git. Don't commit — Rony does that.

The target look is Fig. 1a of Dor et al. 2025 (Agric. Ecosyst. Environ. 387:109633, rendered in Dragonfly): pores as a light, see-through teal haze; particulate organic matter (POM) as solid, shaded olive-gold objects; white background; no axes. Try three ways of rendering it (Options 1–3), all in Python, all at full resolution, and deliver each as a finished, figure-ready image so Rony can choose.

## Input
- Segmentation: `E:\PROJECTS\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources\mishmar_hanegev_maoz_3_5p85um\inference_output_concat_loess_i2\mishmar_hanegev_maoz_3_5p85um.nii.gz` (same file as under `\\HIVE3065\Yael_Mishael\Rony\remote_computer backup\...`). 1000 × 1000 × 1000 voxels, 5.85 µm isotropic → a 5.85 mm cube. Use 5.85 µm even if the NIfTI header says otherwise (report the header value).
- Labels actually deployed (not the scheme in `dataset_info.json`): **5 = pore, 2 = POM**, 0 = matrix, 1 = an unconfirmed minor class. Render only 5 and 2; matrix and label 1 are not drawn.
- Orientation: the core's vertical axis is the reconstruction slice-stack axis — axis 2 when loaded with nibabel (axis 0 with SimpleITK). Confirm this and show that axis vertical. The nnU-Net output is mirrored on nibabel axis 1 relative to the raw scan (correlation-verified 2026-10-04); apply `np.flip(seg, 1)` exactly as `make_fig7.py` does (`06_reporting/missing_data_20261004/figure7/`) so the render is not a mirror image of the real sample.

## Step 0 — checks (stop and report if any fails)
1. **Right file, fresh.** Report path, size, modification time (expected 2026-07-16 00:27) and `np.unique` of the labels (expect only {0, 1, 2, 5}). Pore fraction must be 27.038 % and POM 1.615 % (± 0.01 percentage points) — the DATA_CATALOG values. Use no other or cached copy of this volume. (This project has a documented failure where agents reused stale outputs.)
2. **Real GPU rendering.** Create a new Python environment — do not change `venv-napari` or the Anaconda base env the pipeline uses. Install `pyvista` (≥ 0.44), `vtk`, `nibabel`, `scipy`, `scikit-image`, `matplotlib` (`porespy` only if Option 3 needs it). Run a tiny off-screen PyVista render and print the OpenGL renderer/version string. It must name the NVIDIA GPU. If it reports a software renderer ("GDI Generic", "Microsoft Basic Render Driver", llvmpipe — common in Remote Desktop sessions), stop and report; do not fall back to software rendering.
3. Report RAM and GPU memory and use them to decide whether meshing needs blocks (below).

## Ground rules (all options)
- **No downsampling.** Every surface is built on the native 5.85 µm grid; never resample, zoom, bin or stride the label volume. Allowed, display-only, and each reported in the README:
  - light surface smoothing to remove voxel staircase — Gaussian σ ≤ 1 voxel on each binary mask before contouring at 0.5, or `contour_labels` (SurfaceNets) with light smoothing;
  - hiding specks < 27 voxels (report the % of each class's volume hidden — should be well under 1 %);
  - mesh decimation, only if a mesh is too large to render — then report the reduction and the mean/max surface deviation in µm (target mean < 3 µm, i.e. ½ voxel).
- If memory forces meshing in blocks, overlap blocks by ≥ 3σ, clip each block back to its own region, and check the joined mesh for seams.
- **Tune fast, render once:** tune appearance on a 300³ full-resolution sub-cube (a crop, not a downsample), then render the full 1000³ with the same settings. Cache meshes to disk so re-renders don't re-mesh. Run long steps in the background with a log.
- **Colors** (sampled from Dor 2025 Fig. 1):
  - Pores: teal `#4F9A98`, opacity ~0.08–0.15 (brighter alternative `#2FB3B0`).
  - POM: olive-gold `#B3A23F`, opaque, specular ~0.4–0.5.
  - Reference only: Dor's 2D panels use `#0EF6F2` (pores) and `#C47F04` (POM).
  - Background white; thin dark-gray cube outline (`#555555`, ~1.5 px). Nothing else in the scene.
  - Compare renders side-by-side with `dor2025_fig1a_reference.png` and adjust until the look is close: pores a fine haze, darker where dense; POM is what the eye lands on.
- **Quality:** smooth shading with normals, three-light kit, SSAO (radius ~30–60 µm, kernel 256), supersampling anti-aliasing (SSAA), parallel projection. Depth peeling for every translucent mesh.
- **Camera:** identical for all options — core axis vertical, elevation ~25–30°, azimuth ~35–45°, cube filling ~80 % of the frame. Save it to `camera.json`.
- **Every final image:** ≥ 3000 × 3000 px; PNG (white and transparent background) + TIFF; with
  - an **English** legend (`Pores`, `POM`; Option 3 adds a colorbar `Pore diameter (µm)`), added in matplotlib after rendering, sans-serif font;
  - scale: label a cube edge `5.85 mm`, or draw a labeled 1 mm segment along a cube edge in 3D. No flat 2D scale bar — it is wrong on a tilted view;
  - one close-up per option: same scene, camera zoomed onto a ~1–1.5 mm region rich in POM, to show the full-resolution detail.
- **Self-review:** open and look at every render before moving on — no seams, no staircase, no flicker/z-fighting, POM visible through the pores, nothing cut off by the frame. At most ~3 tuning rounds per option.

## Option 1 — translucent pore surfaces + solid POM (PyVista)
Pore surface mesh in translucent teal with depth peeling (increase the number of peels until the image stops changing); POM surface mesh opaque olive-gold. This is the baseline: closest to Dor in color and the most robust.

## Option 2 — pores as GPU volume-rendered haze + solid POM
Pores as a GPU ray-cast volume (`add_volume(..., mapper='gpu')`) — the closest match to Dragonfly's look. Feed it the pore mask lightly smoothed (σ ≈ 0.7–1 voxel) and stored as uint8 0–255 to save memory. Constant teal color; opacity ramps up around the 0.5 boundary; tune `opacity_unit_distance` (physical units) until it reads as a haze, not a fog wall. POM: the same opaque mesh as Option 1, in the same scene. Keep everything except the volume opaque (VTK does not composite translucent meshes with volumes correctly). If GPU volume rendering fails or looks broken, document it with a screenshot and move on.

## Option 3 — pores colored by pore diameter (as in Dor 2025 Fig. 1c)
Opaque pore surface colored by local pore diameter (viridis, continuous colorbar in µm) plus opaque olive-gold POM in the same scene. Close the surfaces at the cube faces so cut pores show as flat caps.
- **Diameter source:** first look for a saved local-thickness/diameter map in the existing full-volume PSD run `E:\PROJECTS\Yael_Mishael\Rony\remote_computer backup\10.5\psd_outputs\psd_diag_20260803T010446_mishmar_hanegev_maoz_3_5p85um_scratch_i2\` (`scratch_i2` is the old name of `loess_i2`; confirm from its config that it ran on this same segmentation). If no map was saved, compute it with the repo's own PSD code (`psd_diagnostics_core`, the same local-thickness method the pipeline uses) and save it to the share. Either way, apply the pipeline's guard `pore_mask & (diameter_map > 0)` (porespy's local thickness leaks nonzero values into a shell outside the pore mask), and check that the resulting pore-size distribution matches that run's `psd_table.csv`.
- **Coloring:** give each vertex the diameter of the pore voxel it bounds — e.g. sample ~1 voxel inside the pore along the normal, or take the nearest pore voxel. Sampling exactly on the surface gives near-zero or shell-artifact values.
- **Color range:** 2nd–98th percentile, or a fixed range matching the PSD figure in the write-up; state which.

## Deliverables (in the output folder)
- `renders/option1_*`, `option2_*`, `option3_*` — full view + close-up for each, PNG (white + transparent) and TIFF.
- `contact_sheet.png` — the three full views side-by-side (same camera) next to the Dor reference crop.
- `scripts/` — one rerunnable script per step; `camera.json`; `render_params.json`.
- `README.md`, short:
  - Step-0 results: file, mtime, label fractions, header spacing, axis convention, GPU/OpenGL string, package versions.
  - Per option: smoothing σ, speck threshold + % hidden, decimation + deviation (if any), colors, opacities, SSAO settings, mesh sizes, render times, problems.
  - The diameter-map source used for Option 3.
  - One line: which option looks most professional, and why.
