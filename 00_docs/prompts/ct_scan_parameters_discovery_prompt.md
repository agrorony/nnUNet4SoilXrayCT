# CT scan acquisition & preprocessing parameter discovery prompt

**Purpose:** fill the acquisition-hardware and preprocessing-definition gaps in Methods §2.3 (X-ray micro-CT imaging and preprocessing) of the research exercise write-up. This is a read-only discovery task — do not edit DATA_CATALOG.md, PROJECT_STATUS.md, or any pipeline script.

## Context to read first

- `PROJECT_STATUS.md` — project overview, soils, master document location.
- `DATA_CATALOG.md` — canonical inventory of every specimen/scan (Bnei Re'em Specimen A/B, Mishmar `mishmar_native`/`mishmar_hanegev_maoz_2_8p8um`/`Cu011_samp_1`/`Cu011_samp_2`/`Cu011_samp_3`, Rehovot `samp1`/`samp2`/`samp3`), their raw-source paths on the share, and voxel sizes.
- `methods_section_planning.md` (project docs) and the draft Methods text already written for §2.3, for what's already covered and what's missing.

## What's missing and needs a sourced answer

1. **Scanner hardware/acquisition settings**, per specimen where they differ, or "constant across all scans" where they don't:
   - Scanner make and model, and reconstruction software (e.g. NRecon/SkyScan or equivalent).
   - X-ray source voltage (kV) and current (µA).
   - Filter material and thickness (some raw folder/sample names encode "highkV_Cu0.11" — confirm what this actually means: kV value, and 0.11 mm Cu filter or a different reading).
   - Exposure time per projection, rotation step (degrees), frame averaging.
   - Reconstructed voxel size (already known per specimen from DATA_CATALOG.md — confirm it against the scan log rather than re-deriving it).

   Look for `.log`/`.txt` files that sit alongside each specimen's raw slice-stack folder on the share (the same kind of log DATA_CATALOG.md already cites for slice counts and voxel sizes) — these formats typically record the full acquisition header. Check each specimen's raw source path as listed in DATA_CATALOG.md.

2. **The exact "norm200" preprocessing step.** This name appears repeatedly in pipeline logs (e.g. `track_e_correction_summary.md`, `DATA_CATALOG.md`) as a step between raw crop and NLM denoising, but its actual operation is never spelled out. Find the script or function that performs it (search for "norm200" or "normalize" in preprocessing scripts on the share and in the project folder's `scripts/` subfolders) and report the literal operation (e.g. percentile clipping + rescale to a fixed range, min-max to a target value of 200, etc.), quoting the relevant code and its file path as evidence.

3. **NLM (non-local means) denoising parameters.** `track_e_correction_summary.md` references a "CUDA NLM denoise" step (`preprocess_samp_2_0.log` shows it in the pipeline order). Find the implementation (library/module used, e.g. a custom CUDA kernel vs. a package function) and its parameters — patch size, search window, h/sigma (or equivalent noise-strength parameter) — with file path evidence.

4. **The 650³ crop step.** Confirm whether the crop is always exactly 650³ voxels for every specimen, or varies (DATA_CATALOG.md's ROI-expansion note mentions some Mishmar crops growing to 1216³/1614³ — clarify whether that supersedes the "650³ standard" for those specimens specifically, and what the crop size actually was for every specimen used in the reported results).

## Ground rules

- Every value must be traceable to a specific file path (and ideally a quoted line/snippet). If a parameter cannot be found anywhere on the share, report it explicitly as **NOT FOUND** — do not guess, infer from naming conventions alone, or fill in a "typical" instrument value. This is going directly into a Methods section that will be read by a statistics-minded advisor; a fabricated number is worse than an acknowledged gap.
- If you find something DATA_CATALOG.md *should* have recorded (e.g. scanner model) but doesn't, note it in your final report as a suggested addition — don't edit the file yourself.
- Where a parameter is genuinely constant across all specimens (e.g. the same scanner for every scan), say so once rather than repeating it per row.

## Output

Produce a markdown report, `ct_scan_parameters_findings.md`, saved in the project folder, structured as:

- A table: one row per specimen (or "all specimens" where a parameter is shared), columns = scanner model, kV, µA, filter, exposure time, rotation step, frame averaging, voxel size, crop size, each with a file-path citation or "NOT FOUND".
- A short paragraph giving the confirmed norm200 definition, with citation.
- A short paragraph giving the confirmed NLM parameters, with citation.
- A "Suggested DATA_CATALOG.md additions" section listing anything worth adding there, for Rony to review and apply himself.
