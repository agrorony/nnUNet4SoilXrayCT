# Prompt — tortuosity on subvolumes of all valid scans (run on the remote lab computer, HIVE3065)

Paste this into a Claude Code session on the lab computer that has the `nnUNet4SoilXrayCT` repo and the restored `Yael_Mishael` share.

---

## Background
Rony's research exercise compares pore structure in three soils from µCT (nnU-Net segmentation). Tortuosity was computed for whole volumes during the connectivity work ("Track E"), but most runs failed:
- the porespy finite-difference solver did not converge (`Solver failed to converge`), not because no spanning path existed;
- one Mishmar branch crashed in the AMG solver library;
- runs took ~15 h per volume, so the latest Bnei Re'em pipeline skipped tortuosity (`--no-tortuosity` flag).

**Question for this run:** does tortuosity become computable on smaller subvolumes, and if so, do the soils differ? The result goes into the paper either as a short result or as a documented limitation. **Both outcomes are fine — report honestly.**

## Rule 1 — do not reinvent the wheel
A tortuosity implementation already exists in this repo. Before writing any code:
1. Search for it: `tortuosity`, `tortuosity_fd`, `porespy.simulations`, `--no-tortuosity`, and inside `04_inference/scripts/run_bnei_reem_unified_pipeline.py` and the Track E topology scripts (connectivity/topology validation, PSD/topology runner).
2. Report which function is called, the porespy version, solver and tolerance settings, the axis convention, and the input format (binary pore mask? which label value?).
3. Call that same function on subvolumes through a thin wrapper script. **The only new code allowed:** subvolume extraction, the spanning-path pre-check, batching, timeouts and output collection. Don't write a new tortuosity solver or change the existing one's internals.

## Inputs — volumes in scope
Use `DATA_CATALOG.md` (repo root). Every volume with a valid pore channel, at its **~15 µm resolution-matched version**:

| Soil | Volumes | n specimens |
|---|---|---|
| Vertisol (Bnei Re'em) | `bnei_reem_specA_unified`, `bnei_reem_specB_unified` | 2 |
| Loess (Mishmar) | `mishmar_hanegev_maoz_3_5p85um` label-downsampled to ~15 µm; `mishmar_hanegev_maoz_2_8p8um` downsampled to ~15 µm; `Cu011_samp_2` (native 15 µm, pore channel valid) | 3 |
| Sand (Rehovot) | `Rehovot_samp2_highkV_Cu0.11_15um`, `Rehovot_samp3_highkV_Cu0.11_15um` | 2 |

- Use the existing segmentations; no new inference.
- Binary mask = the pore label of the deployed convention (pore=5 in the 3-class volumes; check Rehovot's binary label value).
- Use the same segmentation files that the Track E runs used. Log every input path.
- Do not use the retracted `bnei_reem_samp_2_0*` runs or `Rehovot_samp1`.

## Subvolume design
- Non-overlapping cubes from inside each volume. Skip cubes that touch crop padding or outside-sample voxels (check for zero/constant regions).
- **Default cube size 200³ voxels (~3 mm at 15 µm).** Cut as many as fit, up to 8 per volume, chosen on a regular grid (not cherry-picked).
- If timing allows, repeat with 128³ cubes as a size-sensitivity check.
- Note in the report that cube sizes may be below the REV for connectivity measures (Koestel et al. 2020, Geoderma 366:114206). This is a caveat, not a reason to stop.

## Procedure
1. **Pilot.** Run one cube, all 3 axes, on one Vertisol and one Sand volume. Record runtime per solve, then estimate total runtime. If the total exceeds ~24 h, reduce cubes per volume (keep at least 4) and say so. Set a per-solve timeout of about 3× the pilot median.
2. **For every cube × axis, before solving:**
   - compute porosity;
   - check whether a pore cluster connects the two opposite faces along that axis (6-connectivity, the same as the solver uses).
   - If there is no spanning cluster, record `no_spanning_path` and skip the solve.
3. **Solve** with the existing function. Classify each result as `ok`, `nonconvergence` (captured exception), `timeout` or `error` (message kept).
4. **Retry, at most once:** if the existing function exposes a documented alternative (solver choice or tolerance), retry only the `nonconvergence` cases with it. Log the change, and report original and retry results separately.

## Outputs (new folder `06_reporting/tortuosity_subvolumes_20261004/`)
- **`tortuosity_subvolumes.csv`** — one row per volume × cube × axis: soil, specimen, cube index and origin, cube size, porosity, spanning (y/n), status, tortuosity, runtime_s, solver settings.
- **`convergence_summary.csv`** — share of `ok` / `no_spanning_path` / `nonconvergence` / `timeout` per soil and per cube size.
- **`tortuosity_summary.csv`:**
  - per specimen: median and mean of the `ok` values across cubes and axes;
  - per soil: mean ± **SE** across specimens (the physical specimen is the replicate; cubes are pseudo-replicates within a specimen, so never treat them as independent n across soils).
  - **Never report SD.**
- **One figure:** tortuosity by soil (points = specimen means, small grey points = individual cubes), soil order Vertisol / Loess / Sand. Mark how many cubes were `ok` out of the total.
- **Statistics:** report per-soil means ± SE descriptively. Run a Kruskal-Wallis test on specimen means only if every soil has at least 2 specimens with values, and state plainly that n=2–3 per soil gives almost no power.

## REPORT.md (short)
1. Which existing script/function was used (path, version, settings).
2. Did subvolumes fix the convergence problem? Give the numbers from `convergence_summary`.
3. Tortuosity per soil (mean ± SE), and whether the ranking matches the earlier partial whole-volume result (Vertisol ≈ 4.99 > Sand ≈ 3.40 > Loess ≈ 3.04).
4. Is tortuosity correlated with porosity across cubes? Report Spearman ρ, descriptive only.
5. Recommendation for the paper, one paragraph: report as a result, or as a limitation, and why.

Do not edit `DATA_CATALOG.md`, `PROJECT_STATUS.md` or any existing run output.
