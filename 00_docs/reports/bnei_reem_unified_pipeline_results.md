# Bnei Re'em — unified two-specimen pipeline results

Generated 2026-09-07 17:16:24 by `04_inference/scripts/run_bnei_reem_unified_pipeline.py`.

Both specimens were put through **one script, one code path**: raw reconstruction → center 650³ crop → norm200 + CUDA NLM → global-mean/std z-score → 4-way split → nnU-Net inference (`multi_sample_fresh_bnei_reem_i4`, trainer `nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss_lowlr`) → PSD/topology diagnostics → χ(r) sweep. The only per-volume differences are input folder, slice regex, output sample ID, and voxel spacing; every other step, order and parameter is identical.

## 1. Input verification

### Specimen A — `bnei_reem_specA_unified`

- Folder read: `C:\Users\rony.schwartz\Desktop\new_rec`
- This is the folder specified in the task (no substitution).
- Slice regex: `^bnei_reem_highkV_cu011_samp_2_rec\d{8}\.tif$`
- **Slice count: 804** matching slices (822 .tif in the folder, 18 excluded as preview/parameter-tuning/aux files)
- Index range 49–852, **contiguous: True** (zero gaps)
- Shape **1344×1344**, dtype **uint16**, dynamic range reaches **65535**: real reconstruction stack ✔
- Voxel spacing: **15.000149 µm** (isotropic)

| probe | file | min | max | mean |
|---|---|---|---|---|
| first | `bnei_reem_highkV_cu011_samp_2_rec00000049.tif` | 0 | 65535 | 14929.2 |
| mid | `bnei_reem_highkV_cu011_samp_2_rec00000451.tif` | 0 | 65535 | 16063.4 |
| last | `bnei_reem_highkV_cu011_samp_2_rec00000852.tif` | 0 | 65535 | 16360.2 |

- Center crop: Z positions 77–727 (original indices 126–775), XY offset [347, 347] → 650³
- NLM volume MD5 `0fe47a94f092ec08643173f9fb5a9908` (mean 0.73416, std 0.17616)

### Specimen B — `bnei_reem_specB_unified`

- Folder read: `\\HIVE3065\Yael_Mishael\Rony\18.12.25 bnei_reem_samp_2.0\bnei_reem_highkV_cu011_samp_2.0_Rec`
- This is the folder specified in the task (no substitution).
- Slice regex: `^bnei_reem_highkV_cu011_samp_2\.0_rec\d{8}\.tif$`
- **Slice count: 804** matching slices (828 .tif in the folder, 24 excluded as preview/parameter-tuning/aux files)
- Index range 49–852, **contiguous: True** (zero gaps)
- Shape **1344×1344**, dtype **uint16**, dynamic range reaches **65535**: real reconstruction stack ✔
- Voxel spacing: **15.034357 µm** (isotropic)

| probe | file | min | max | mean |
|---|---|---|---|---|
| first | `bnei_reem_highkV_cu011_samp_2.0_rec00000049.tif` | 4420 | 65535 | 16713.1 |
| mid | `bnei_reem_highkV_cu011_samp_2.0_rec00000451.tif` | 3632 | 65535 | 16978.7 |
| last | `bnei_reem_highkV_cu011_samp_2.0_rec00000852.tif` | 5141 | 65535 | 17655.4 |

- Center crop: Z positions 77–727 (original indices 126–775), XY offset [347, 347] → 650³
- NLM volume MD5 `b30891fcf769e5b30834902b5d118ec8` (mean 0.68435, std 0.21817)

**Shared-scratch-slot hazard**: `02_preprocessing/filters/nlm_output/nlm_volume.tif` is overwritten by every `run_preprocess.py` call. The two volumes were processed strictly sequentially, both scratch slots were deleted before each call, each NLM result was copied out to a per-specimen path before the next specimen started, and the two copied-out volumes were MD5-compared: **DISTINCT ✔**.

## 2. Identity check — the reason for this rerun

| Quantity | This run | Previous failed run | Genuinely-different baseline |
|---|---|---|---|
| Pearson r between the two z-scored `_0000.nii.gz` arrays | **-0.011947** | 0.9999 | ~0.58 |
| Pore-label (5) Dice between the two segmentations | **0.167908** | 0.988 | — |
| Pore-label IoU | 0.091648 | — | — |
| Dice expected under independence (from marginals) | 0.178357 | — | — |
| Inputs byte-identical | False | — | — |
| Segmentations byte-identical | False | — | — |

**PASS.** r = -0.0119 and pore Dice = 0.1679 are both far below the previous run's 0.9999 / 0.988. The two volumes carry genuinely different data through the pipeline, so the metrics below are interpretable.

## 3. Structural metrics, side by side

| Metric | Specimen A (`bnei_reem_specA_unified`) | Specimen B (`bnei_reem_specB_unified`) | B vs A |
|---|---|---|---|
| Pore fraction (label 5) | 15.1688% | 21.6403% | +42.66% |
| POM fraction (labels 2+3) | 0.2403% | 0.8170% | +239.99% |
| Euler number χ | 26330 | 9771 | -62.89% |
| Connectivity density (mm⁻³) | -28.4069 | -10.4699 | +63.14% |
| Γ (connectivity probability) | 0.754887 | 0.859338 | +13.84% |
| DA (degree of anisotropy) | 0.188606 | 0.096700 | -48.73% |
| PSD 30–150 µm volume fraction | 0.698896 | 0.391276 | -44.02% |
| r* crossover radius (µm) | n/a | 920.48 | n/a |
| χ(r) trend | all_positive_in_range | negative_to_positive | — |
| r* resolution-limited? | None | False | — |
| Voxel spacing (µm) | 15.000149 | 15.034357 | — |

- Tortuosity was **not computed** (`--no-tortuosity`): ~15 h per volume, and axis0 returns NaN via solver non-convergence on these volumes anyway. Its keys are omitted from every output rather than filled with placeholders.
- PSD run dirs: `\\hive3065\Yael_Mishael\Rony\remote_computer backup\Topology_Metrics_Aug2026\raw\psd_diag_20260907T103058_bnei_reem_specA_unified` and `\\hive3065\Yael_Mishael\Rony\remote_computer backup\Topology_Metrics_Aug2026\raw\psd_diag_20260907T122221_bnei_reem_specB_unified`
- χ(r) CSVs: `\\hive3065\Yael_Mishael\Rony\remote_computer backup\Topology_Metrics_Aug2026\connectivity_function\chi_r_bnei_reem_specA_unified.csv` and `\\hive3065\Yael_Mishael\Rony\remote_computer backup\Topology_Metrics_Aug2026\connectivity_function\chi_r_bnei_reem_specB_unified.csv`

### χ(r) sanity checks

| Check | Specimen A | Specimen B |
|---|---|---|
| χ(r=min) == recorded full-mask Euler number | True | True |
| voxel-count × voxel-size³ back-calculation | True | True |

## 4. Do the two specimens actually differ?

**Yes.** Pearson r = -0.0119 between the two z-scored inputs and pore-label Dice = 0.1679 between the two segmentations — nowhere near the previous run's 0.9999 / 0.988. The two folders hold genuinely different reconstructions and the pipeline carried that difference through to the segmentations. The metrics in §3 are a real two-specimen comparison.

## 5. Provenance

| Item | Value |
|---|---|
| Driver | `04_inference/scripts/run_bnei_reem_unified_pipeline.py` |
| Model | `multi_sample_fresh_bnei_reem_i4` / `Dataset777_GCEF` |
| Trainer | `nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss_lowlr` |
| Labels | Pore=5, POM=2,3 (dataset.json) |
| Crop | center 650³ |
| Anisotropy directions | 800 |
| CUDA env | `C:\Users\rony.schwartz\.conda\envs\venv-napari\python.exe` |
| Topology env | `D:\Anaconda\python.exe` |
| State file | `\\hive3065\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources\_bnei_reem_unified_state.json` |
| Stage A wall time | A: 14.3 min, B: 13.4 min |
| Stage C wall time | A: PSD 53.8 min + χ(r) 57.6 min, B: PSD 98.3 min + χ(r) 75.9 min |

