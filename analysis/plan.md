# PSD Diagnostics Reimplementation Plan

## Source of Truth
The old implementation files will be provided by the user in chat context and must be treated as the authoritative behavioral reference during implementation.

Implementation must preserve behavior parity with that provided reference.

## 1. Objective
Create a minimal, reproducible PSD diagnostics subsystem that can run on real binary pore volumes and synthetic volumes, while preserving the current conceptual pipeline:
- EDT
- opening/local-thickness
- raw diameter extraction
- binning
- PSD computation
- stage-wise diagnostics

The subsystem must be production-style, deterministic, and easy to transplant into a new nnUNet-style repository version with only 2 Python files.

## 2. Scope
Includes:
- A reusable PSD diagnostics module that encapsulates core computation and diagnostics collection.
- A single CLI runner for two modes: real-data diagnostics and synthetic diagnostics.
- Structured run-folder outputs with explicit metadata and fixed output contract.
- Monolithic execution and a controlled chunking path policy (see Section 9).

Explicitly excludes:
- Notebooks.
- Ad hoc experiment scripts spread across folders.
- Multi-module utility sprawl.
- GUI/interactive tooling.
- Training/inference integration beyond diagnostics input/output contract.

## 3. Proposed File Layout
Two-file design:

1. `psd_diagnostics_core.py`
- Responsibility:
  - Reusable compute and diagnostics logic only.
  - No CLI parsing.
  - No implicit global paths.
- Contains:
  - PSD pipeline stages.
  - Diagnostics aggregation.
  - Synthetic volume generation utility (small, integrated, deterministic).
  - Serialization helpers for output payloads.

2. `run_psd_diagnostics.py`
- Responsibility:
  - Single entrypoint/CLI.
  - Input validation, run-folder creation, mode dispatch.
  - Calls `psd_diagnostics_core.py` APIs and writes outputs.
- Modes:
  - `real`: run diagnostics on one provided binary volume.
  - `synthetic`: generate synthetic data and run monolithic vs chunked comparison.

## 4. Data Flow
1. Input acquisition
- Real mode: load binary 3D pore volume from explicit path.
- Synthetic mode: generate deterministic synthetic 3D pore volume from CLI parameters and seed.

2. PSD stages (core)
- Compute EDT (with explicit voxel spacing).
- Compute opening/local-thickness map using the current project’s Vogel-style discrete-radius logic.
- Extract raw pore diameters from opening map and pore mask.
- Build bins and compute PSD outputs (counts, cumulative, differential).

3. Diagnostics collection (core)
- EDT stats + histogram.
- Opening-map stats + histogram.
- Raw-diameter stats + concentration summary.
- Binning diagnostics (bin widths, empty bins, zero-width bins).
- PSD sanity checks (NaN/Inf/spike detection summary).

4. Optional synthetic comparison branch
- Run same core pipeline twice (monolithic and chunked policy path).
- Compare stage and PSD outputs.
- Produce explicit equality/diff summary.

5. Output writing (runner)
- Write all artifacts into one structured run folder.
- No writes outside run folder except optional explicit user-requested output root.

## 5. Public Interfaces
### File 1: `psd_diagnostics_core.py`
Primary interfaces:
- `run_psd_pipeline(volume, voxel_spacing, *, use_chunking=False, chunk_size=None, halo_width=None, exclude_borders=True, bin_edges_um=None, diagnostics_cfg=None) -> dict`
  - Input:
    - `volume`: 3D bool array (True=pore).
    - `voxel_spacing`: `(dz, dy, dx)` tuple.
    - explicit processing options.
  - Output dict (single canonical structure):
    - `psd`: centers, edges, counts, cumulative, differential, reliability flags.
    - `stages`: per-stage diagnostics payloads.
    - `meta`: runtime/config metadata.

- `generate_synthetic_volume(*, shape, voxel_spacing, sphere_count, seed, profile='default') -> dict`
  - Output:
    - `volume` (bool array)
    - `ground_truth` (synthetic generator metadata for validation)

- `compare_runs(result_a, result_b, *, label_a='monolithic', label_b='chunked') -> dict`
  - Output:
    - exact-equality checks, max-abs-diff summaries, divergence locations.

### File 2: `run_psd_diagnostics.py`
CLI interface:
- Command style:
  - `python run_psd_diagnostics.py real --input <path> --voxel-spacing dz dy dx --output-root <path> [options]`
  - `python run_psd_diagnostics.py synthetic --output-root <path> [options]`

Core CLI arguments:
- common:
  - `--output-root`
  - `--run-name` (optional)
- real mode:
  - `--input`
  - `--voxel-spacing dz dy dx`
  - `--exclude-borders`
  - `--bin-edges-json` (optional explicit bins)
  - `--use-chunking` and chunk params (policy-gated, default off)
- synthetic mode:
  - generator args (`--shape`, `--sphere-count`, `--seed`, spacing)
  - always run both monolithic and chunked paths
  - always emit comparison output between monolithic and chunked

Runner return behavior:
- process exit code only.
- all structured results persisted to disk.

## 6. Output Contract
Per run, write exactly one run directory:
- `<output-root>/psd_diag_<timestamp>_<run-name>/`

Inside run folder:
1. `config.json`
- full resolved configuration used for this run.

2. `result_psd.json`
- canonical PSD arrays and scalar metadata.

3. `diagnostics.json`
- stage-by-stage diagnostics payload.

4. `summary.json`
- concise scalar summary for quick comparisons.

5. `comparison.json` (synthetic mode only)
- monolithic vs chunked equivalence/diff report.

6. `psd_table.csv` (required)
- tabular PSD bins.

Naming scheme constraints:
- fixed filenames above.
- no extra sidecar files.
- no nested ad hoc subfolders except optional `artifacts/` for future plots (empty unless explicitly requested).

## 7. Synthetic Test Design
Integrate synthetic diagnostics inside the same two-file system by embedding synthetic generation in `psd_diagnostics_core.py` and invoking it via `synthetic` mode in `run_psd_diagnostics.py`.

Design details:
- one deterministic generator path with fixed seed support.
- synthetic mode always emits:
  - monolithic result payload,
  - chunked result payload,
  - one comparison payload.
- no separate experiment scripts, no additional experiment directories.

## 8. Real-Data Diagnostic Path
Real-data execution should require only:
- explicit input volume path,
- explicit voxel spacing,
- explicit output root.

Path behavior:
- resolve input path once,
- validate binary shape/dtype contract,
- run single pipeline path,
- persist outputs in one run folder,
- print minimal terminal summary with run directory location and key scalar stats.

## 9. Chunking Strategy
Status for reimplementation:
- Keep chunking policy-gated and explicit in API/CLI.
- Real mode: chunking is optional and off by default.
- Synthetic mode: run both monolithic and chunked every time; comparison is mandatory.

Rationale:
- Needed for comparability with current workflow and synthetic monolithic-vs-chunked diagnostics.
- Must remain explicit as an implementation artifact, not hidden behavior.
- Preserve reproducibility by forcing all chunk parameters to be recorded in `config.json`.

Behavioral constraint:
- same diagnostics schema for monolithic and chunked results to enable strict direct comparison.
- synthetic mode is incomplete if either monolithic or chunked run is missing.

## 10. Migration Notes
Preserve from current logic:
- Stage sequence and definitions from current PSD pipeline.
- Opening/local-thickness discrete radius workflow used for current comparability.
- Diagnostics categories currently in use (EDT/opening/raw/binning/PSD checks).
- Synthetic comparability pattern (monolithic vs chunked artifact inspection).

Drop from current structure:
- scattered diagnostics scripts and ad hoc experiment file layout.
- multiple single-purpose modules whose responsibilities can be merged into the core module.
- implicit path behavior and mixed output locations.

Behaviors that must remain identical for comparability:
- pore-mask semantics used for raw diameter extraction.
- diameter assignment convention in opening/local-thickness stage.
- PSD normalization convention currently used in outputs.
- diagnostics field meanings and key scalar computations.

## 11. Implementation Order
1. First
- Define canonical data contracts (result dict schema, diagnostics schema, output filenames).
- Freeze CLI contract and resolved config format.

2. Second
- Implement `psd_diagnostics_core.py` end-to-end (pipeline + diagnostics + synthetic generator + comparison utility) using current logic parity.

3. Third
- Implement `run_psd_diagnostics.py` (mode dispatch, path validation, run-folder writing, minimal console summary), then parity-check outputs against current workflow on one synthetic and one real case.

## 12. Risks / Open Questions
- Contract risk: if current field semantics are not copied exactly, historical comparability may break despite numerically similar outputs.
- Geometry risk: spacing/unit handling must be explicitly standardized in the new contract to avoid hidden interpretation drift.
- Chunking parity risk: chunked equivalence depends on clearly fixed halo/chunk policies and recorded parameters.
- Input contract risk: real-data binarization assumptions must be explicit (already-binary vs thresholded upstream), otherwise reproducibility varies across datasets.
