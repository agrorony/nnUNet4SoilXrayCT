# Claude Code task: PSD + bulk density of 3 soils (Otsu-based)

Compute the **pore-size distribution (PSD)** and **bulk density** of my three
soils from their segmented images, building on the Otsu-segmentation and image
analyses that ALREADY EXIST in this project. The headline deliverable is a
**bulk-density report** using a fixed particle density of **2.65 g/cm³** for
every solid pixel/voxel.

## 0. Working-folder contract (important)

- Create ONE dedicated scratch folder for this task, e.g. `./_psd_bd_task/`.
- Put ALL scripts, intermediate arrays, crops, and debug output there.
- At the END of the task, **delete that folder entirely.** The only thing that
  persists is the final report (+ its figures) written to the project's normal
  results/reports location.
- Because the scratch folder is deleted, the report must be **self-contained and
  reproducible**: embed the exact method, parameters, and the key code snippets
  in a methods/appendix section so nothing essential is lost when the folder goes.

## 1. Explore and reuse what's already here (do this first — do not reinvent)

Inspect the project and find:
- The **image data for all three soils** (A/B/C, or whatever they're named here).
  Detect whether they are 2D images or 3D CT volumes, and handle accordingly.
- The **existing Otsu segmentation** code and/or already-segmented outputs, and my
  **recent deeper analyses**. Reuse them — same threshold method, same
  phase definitions, same region/crop conventions — so results stay consistent
  with prior work. Do not introduce a different segmentation pipeline.
- The **voxel/pixel physical resolution** (µm or mm per voxel) from the data or
  metadata. Needed for PSD in real units. (Not needed for bulk density — see §3.)
- How "solid" vs "pore" is defined in the existing segmentation. If the
  segmentation has more than two classes (e.g. pore / organic / mineral), state
  explicitly which classes you count as "solid," and note it as an assumption.

Report what you found (paths, data type, resolution, phase definitions) before
computing, so the basis is auditable.

## 2. Binary solid/pore masks

Using the existing 3dOtsu script, produce a clean binary mask per soil:
solid = 1, pore = 0 (matching my existing solid definition from §1). Reuse any
existing cleanup (fill/despeckle) my prior analyses already apply, so the masks
match what I've been using.

## 3. Bulk density (the headline output — 2.65 g/cm³ rule)

Assign every **solid** voxel a density of **2.65 g/cm³** and every pore voxel 0.
Then:

```
porosity        phi   = N_pore  / N_total
solid fraction        = N_solid / N_total = 1 - phi
bulk density    rho_b = (1 - phi) * 2.65   [g/cm^3]
```

(Equivalently: total solid mass = N_solid * voxel_volume * 2.65, divided by
total bulk volume = N_total * voxel_volume — the voxel volume cancels, so bulk
density does not depend on the resolution, only on the solid fraction.)

Report `phi`, solid fraction, and `rho_b` per soil. State the 2.65 g/cm³
assumption clearly (it is the standard mineral particle density; if some solid
voxels are organic matter, treating them as 2.65 is a deliberate simplification —
say so).

## 4. Pore-size distribution (PSD)

Compute PSD from the binary pore mask in **physical units** (using the §1 resolution) — **extend the existing PSD/local-thickness code in this repo rather than writing a new implementation.**

- First locate the existing PSD-computing code (local-thickness / maximal-inscribed-sphere logic — likely `porespy.filters.local_thickness` or an equivalent skimage-based implementation) and read its current interface: inputs, voxel-size handling, output format.
- This binary solid/void case is simpler than whatever segmentation it currently supports (e.g. multi-phase matrix/pore/POM) — the void mask should just work as its pore/foreground input as-is. Reuse it directly; don't reimplement local thickness or granulometry from scratch.
- Only add what the existing code doesn't already produce:
  - volume-weighted PSD (histogram + cumulative curve)
  - median/mode pore diameter and D10/D50/D90 percentiles
- If the existing output already includes any of the above, extend/match it in place rather than duplicating.
- Report which existing function/module you extended, and flag any behavioral differences from building it fresh.

## 5. The report (the only persisted deliverable)

Write ONE report to the project's results/reports location (Markdown or PDF),
containing:
- **Method & assumptions**: data type + resolution, Otsu/phase definitions reused,
  the 2.65 g/cm³ particle-density assumption, the PSD method.
- **Per-soil results table**: porosity, solid fraction, bulk density (g/cm³), and
  PSD summary stats (D10/D50/D90, median, mode).
- **Figures**: PSD histogram + cumulative curve per soil, plus one overlaid PSD
  comparing all three; a bulk-density / porosity bar comparison.
- **Cross-soil comparison**: a short interpretation of how the three soils differ
  in porosity, bulk density, and pore-size character.
- **Appendix**: the key code and exact parameters used, so the run is reproducible
  after the scratch folder is deleted.

## 6. Cleanup

Delete `./_psd_bd_task/` and all intermediates. Confirm in your final message what
was persisted (the report + figures) and what was removed (the scratch folder).

## Notes

- Keep the three soils' naming consistent with how they appear in this project.
- These outputs (per-soil porosity, bulk density, and PSD) are intended to later
  parameterize a separate pore-based simulation, so precise, clearly-labeled
  per-soil numbers matter more than polish.
