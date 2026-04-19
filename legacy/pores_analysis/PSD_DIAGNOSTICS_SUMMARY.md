# PSD Diagnostics Summary

## 1. Setup
- Script used:
  experiments/synthetic_psd_diagnostics.py
- Environment:
  C:\Users\ronys\miniconda3\envs\venv-napari
- Runs:
  - monolithic (no chunking)
  - chunked

## 2. Key Findings (Short)
- PSD is sparse rather than smooth: 5 nonzero bins out of 50, with 45 empty bins.
- Chunking has no numerical effect on PSD outputs in this run (monolithic vs chunked arrays are identical).
- Binning is not the root cause: zero-width bins = 0 and near-zero-width bins = 0.
- Distortion originates earlier, where diameters collapse to a small discrete set before binning.

## 3. Quantitative Evidence

### EDT
- min / max: 0.0 / 6.0
- unique values: 30
- integer-like: False

### Opening Map
- unique diameters: 7
- dominant diameters + fractions:
  - 0.0 -> 0.961351
  - 2.0 -> 0.011102
  - 6.0 -> 0.010608
  - 4.0 -> 0.006263
  - 8.0 -> 0.005861
- explicit note: dominant nonzero diameters are multiples of 2

### Raw Diameters
- total count: 52,305
- unique values: 6
- top-5 concentration: 97.4687%

### Binning
- number of bins: 50
- empty bins: 45
- zero-width bins: 0

### PSD Output
- nonzero bins: 5
- NaN / Inf: 0 / 0
- amplitudes (nonzero bins): 1.219408, 0.931163, 0.561969, 0.269711, 0.088243

## 4. Run Comparison
- Are monolithic and chunked identical? True for all PSD numeric outputs.
- Exact statement: PSD arrays are identical (bin_centers_um, bin_edges_um, differential_volume, volume_counts all max absolute difference = 0); diagnostics JSON differs only by run metadata (run tag / timestamp).

## 5. Ground Truth vs Measured
- Ground-truth diameter distribution: continuous-like (63 unique values; range 10.000000 to 24.137399 um).
- Raw diameters: discrete (6 unique values in diagnostics output).
- PSD: sparse (5 nonzero bins out of 50).

## 6. Root Cause (Critical Section)
- Dominant issue: Quantization
- Stage: Opening / Local Thickness
- Explanation:
  - integer radii produce discrete diameter levels
  - the distribution collapses from continuous ground truth to a few diameter values before PSD binning

## 7. Conclusion
Distortion is introduced at the Opening/Local Thickness stage where diameter quantization collapses a continuous ground-truth distribution into a small discrete set; chunking is not responsible, and binning is not the root cause because bin definitions are valid (no zero-width bins) while sparsity is inherited from earlier quantization.
