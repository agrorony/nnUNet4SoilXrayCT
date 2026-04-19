# Implementation Contract for PSD Diagnostics

## Source of Truth
The old implementation files will be provided by the user in chat context and must be treated as the authoritative behavior reference.

If any implementation decision conflicts with this document versus the provided old implementation behavior, preserve parity with the provided old implementation behavior while keeping this contract constraints.

## 1. Non-Negotiable Constraints
1. Implement exactly 2 Python files and no more.
2. Do not add any other Python modules, helper files, or package folders.
3. Do not change algorithmic behavior relative to current PSD workflow.
4. Do not refactor in any way that changes numerical outputs.
5. Do not create notebooks.
6. Do not create or modify environment configuration.
7. Do not introduce hidden state, implicit caches, or side-effect writes outside run output folder.
8. Expose behavior only through explicit function calls and a CLI entrypoint.

## 2. Source of Truth (Behavioral)
All behavior below must be identical in effect to current implementation semantics.

1. EDT stage
- Compute Euclidean distance transform on binary pore volume.
- Preserve current pore/solid convention: `True` means pore.
- Preserve current spacing semantics used by pipeline execution and output scaling.

2. Opening/local-thickness stage
- Preserve iterative morphological granulometry behavior.
- Preserve discrete integer-radius processing in voxel space.
- Preserve spherical structuring element logic.
- Preserve maximal assignment behavior across radii.

3. Diameter definition
- Preserve diameter assignment convention as `diameter = 2 * r` at opening/local-thickness stage.
- Preserve downstream assumption that opening-map values represent diameters.

4. Raw diameter extraction
- Preserve pore-mask-based extraction behavior from diameter map.
- Preserve border exclusion semantics currently used by workflow.

5. Binning
- Preserve current bin construction strategy and default bin count behavior.
- Preserve current conversion path between voxel-domain and physical-domain bins.
- Preserve histogram counting semantics.

6. PSD normalization
- Preserve cumulative and differential PSD definitions.
- Preserve denominator and bin-width normalization behavior exactly.

7. Reliability logic
- Preserve reliability threshold semantics and output flag behavior.

8. Diagnostics payload
- Preserve stage structure and metric semantics currently emitted.
- Preserve key names and interpretation used by current diagnostics consumers.

## 3. Input Contract
1. Volume input
- Accept exactly one 3D volume per run.
- Required shape rank: 3.
- Required meaning: boolean pore mask where `True = pore`, `False = solid`.

2. Type handling
- Accept boolean input directly.
- If non-boolean input is provided, convert to boolean using existing behavior parity and record this in metadata.

3. Voxel spacing
- Require 3 values in order `(dz, dy, dx)`.
- Require numeric positive values.
- Reject invalid spacing length or non-positive values.

4. Invalid input handling
- Fail fast with non-zero exit code for invalid shape/spacing/path.
- Do not continue with partial execution.
- Write a structured error message to stderr.

5. CLI mode contract
- `real` mode requires input volume path, voxel spacing, and output root.
- `synthetic` mode requires generator parameters and output root.

## 4. Output Contract (Strict)
For every run, create exactly one run folder:
- `<output-root>/psd_diag_<timestamp>_<run-name>/`

### 4.1 Required files (all runs)
1. `config.json`
2. `result_psd.json`
3. `diagnostics.json`
4. `summary.json`
5. `psd_table.csv`

`SUMMARY.md` is not part of the required output contract.

### 4.2 Required files (synthetic mode only)
1. `comparison.json`
2. `ground_truth.json`

### 4.3 result_psd.json required fields
1. `bin_centers_px`
2. `bin_centers_um`
3. `bin_edges_um`
4. `volume_counts`
5. `cumulative_volume`
6. `differential_volume`
7. `reliability_flag`
8. `total_pore_voxels`
9. `voxel_spacing`
10. `mode`
11. `run_name`
12. `timestamp`

### 4.4 diagnostics.json required top-level keys
1. `run_tag`
2. `created`
3. `config`
4. `stages`

### 4.5 diagnostics.json required stages keys
1. `edt`
2. `opening`
3. `raw_diameters`
4. `binning`
5. `post_psd`

### 4.6 psd_table.csv required columns
1. `Diameter_px`
2. `Diameter_um`
3. `Volume_Count`
4. `Cumulative_Porosity`
5. `Differential_PSD`
6. `is_reliable`

### 4.7 summary.json required fields
1. `range`
2. `repeat_bins`
3. `low_count_bins`
4. `spikes`
5. `mode`
6. `run_name`

### 4.8 comparison.json required fields (synthetic mode)
1. `labels`
2. `exact_equal`
3. `array_comparisons`
4. `diagnostics_equal`
5. `max_abs_diff`
6. `nonzero_diff_counts`
7. `status`

## 5. Numerical Fidelity Requirements
1. Exact-match required
- `volume_counts`
- `bin_edges_um`
- `bin_centers_um`
- `reliability_flag`
- `total_pore_voxels`
- diagnostics integer counts and bin occupancy counts

2. Tolerance-allowed values
- floating metrics in diagnostics summaries and differential PSD values.
- absolute tolerance: `1e-12` for scalar comparisons.
- array tolerance: `max_abs_diff <= 1e-12`.

3. Equality evaluation rules
- Arrays: compare length first, then elementwise.
- Boolean arrays: exact equality only.
- NaN handling: NaN positions must match exactly.
- JSON field names: exact string equality.

4. Determinism
- Synthetic mode must be deterministic under fixed seed.
- Repeated run with same seed and same parameters must produce numerically identical outputs under same backend and mode.

## 6. Diagnostics Requirements
The diagnostics payload must include the following minimum metrics per stage.

1. `stages.edt`
- `stats`: count, min, max, mean, median, std, q25, q75
- `unique_count`
- `integer_like`
- `voxel_spacing`
- `histogram`: bins, counts, edges, counts_head, counts_tail

2. `stages.opening`
- `unique_diameter_count`
- `top_diameter_fractions` with diameter/count/fraction entries
- `histogram`: bins, counts, edges, counts_head, counts_tail

3. `stages.raw_diameters`
- `stats`: count, min, max, mean, median, std, q25, q75
- `repeat_bin_count`
- `repeat_summary`
- `histogram`: bins, counts, edges, counts_head, counts_tail

4. `stages.binning`
- `bin_edges_px`
- `bin_edges_um`
- `bin_width_stats`: min, max
- `zero_width_bins`
- `empty_bins`
- `low_count_bins`

5. `stages.post_psd`
- finite-bin counts
- NaN and Inf counts
- spike threshold metadata
- spike list with bin index and diameter range for each spike

## 7. Synthetic Test Requirements
1. Generator guarantees
- Produce 3D binary pore volume.
- Use deterministic RNG controlled by seed.
- Return ground-truth descriptors sufficient for downstream validation.

2. Ground truth output
- `ground_truth.json` must include at least:
  - generator parameters
  - seed
  - placed-object count
  - ground-truth diameter summary statistics

3. Required synthetic execution paths
- Always run monolithic pipeline.
- Always run chunked pipeline.
- Always run monolithic-vs-chunked comparison.
- Synthetic mode is invalid if either path is missing.

4. Reproducibility
- Fixed seed and fixed parameters must reproduce identical synthetic volume and identical monolithic outputs.

## 8. Comparison Mode Requirements
1. Comparison target
- Compare monolithic vs chunked results for:
  - `bin_centers_um`
  - `bin_edges_um`
  - `differential_volume`
  - `volume_counts`
  - key diagnostics stage summaries

2. Comparison outputs
- Persist `comparison.json` with required fields in Section 4.8.
- Include per-array:
  - shape match result
  - exact equality result
  - max absolute difference
  - nonzero difference count

3. Identity definition
- `identical = True` only if all required arrays are exact-equal and diagnostics equality policy passes.
- `identical = False` otherwise.

4. Execution policy
- Comparison is mandatory in synthetic mode.
- Comparison is not required in real mode.

## 9. Forbidden Changes
1. Do not add smoothing at any stage.
2. Do not add interpolation of EDT, opening map, diameters, or PSD arrays.
3. Do not change discrete-radius opening logic.
4. Do not change diameter definition (`2*r`).
5. Do not change border exclusion semantics.
6. Do not change binning strategy defaults.
7. Do not change PSD normalization equations.
8. Do not change diagnostics key names or stage structure.
9. Do not change CSV column names.
10. Do not change run-folder naming pattern.

## 10. Definition of Done
Implementation is complete only if all conditions are met.

1. Structure
- Exactly 2 Python files exist for this subsystem.

2. CLI
- `real` and `synthetic` commands run from CLI and terminate with correct exit code.

3. Outputs
- All required files are created with required names and required fields.
- No unexpected extra output files are created.

4. Numerical behavior
- Behavioral contracts in Sections 2 and 5 are satisfied.
- Synthetic determinism constraints are satisfied.

5. Diagnostics completeness
- `diagnostics.json` contains all required stages and metrics in Section 6.

6. Comparison mode
- Monolithic vs chunked comparison runs and writes `comparison.json` with required schema.

7. Drift prevention
- No prohibited changes from Section 9 are present.
