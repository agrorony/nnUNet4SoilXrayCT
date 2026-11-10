# nnUNet4SoilXrayCT: soil structure and organic matter in three Israeli soils (HUJI, 2026)

This fork holds the code and records for a research exercise at the Hebrew University of Jerusalem (Rony Schwartz, 2026; advisors Prof. Yael Mishael and Dr. Maoz Dor). X-ray µCT scans of three Israeli soils (**Loess** from Mishmar HaNegev, **Vertisol** from Bnei Re'em, **Sand** from Rehovot) were segmented with nnU-Net v2 into pore, solid matrix and particulate organic matter (POM). Structural metrics were then computed: pore-size classes, connectivity (Γ, Euler χ, χ(r) and crossover radius r*), tortuosity, and POM interface metrics. It builds on the UFZ pipeline by Phalempin et al. ([upstream repo](https://github.com/MaxPhal/nnUNet4SoilXrayCT); its tutorial is kept in [`00_docs/UPSTREAM_README_UFZ.md`](00_docs/UPSTREAM_README_UFZ.md); citations are in [`RESOURCES.md`](RESOURCES.md)).

The write-up has been submitted. This repository is in its final hand-off state (2026-11) and is no longer maintained.

## Repository map

| Folder | Contents |
|---|---|
| `00_docs/` | Project records: [`prompts/`](00_docs/prompts) (agent prompts that drove each analysis step), [`reports/`](00_docs/reports) (findings and results write-ups, incl. the hand-off report), [`reorg_2026-07/`](00_docs/reorg_2026-07) (repo reorganisation records), [`literature/REFERENCES.md`](00_docs/literature/REFERENCES.md) (every paper used for the analysis; PDFs kept locally, not in git), the upstream UFZ tutorial, figures |
| `01_data_ingestion/` | Annotation tool (`make_annotations.py`, napari) and the data registry (`registry/data_registry.json`) |
| `02_preprocessing/` | nnU-Net dataset preparation, split-for-inference, and the norm200 + CUDA non-local-means (NLM) filter branch (`filters/`) |
| `03_training/` | Custom trainer `nnUNetTrainer_betterIgnoreSampling.py`, training run configs (`run_configs/*.yaml`) and drivers |
| `04_inference/` | Inference drivers (`scripts/`), chunk concatenation, run configs, and the inference logs that survived |
| `05_evaluation/` | PSD / topology / tortuosity code (`psd/`), POM analyses (`psd/pom_analysis_*`), segmentation checks |
| `06_reporting/` | Figure scripts, training-curve diagnostics, 3D renders, tortuosity and missing-data reports |
| `07_utilities/` | Fiji macros, SLURM helpers, small one-off scripts |
| `logs_archive/` | Training/inference logs archived during the 2026-07 reorganisation |

## Specimens and models

From [`DATA_CATALOG.md`](DATA_CATALOG.md) (the specimen inventory; distinct names there are not distinct specimens).

| Specimen ID | Soil | Voxel (µm) | Segmentation | Used for |
|---|---|---|---|---|
| `bnei_reem_specA_unified` | Vertisol, specimen A | 15.000149 | nnU-Net `fresh_bnei_reem_i4` | structure |
| `bnei_reem_specB_unified` | Vertisol, specimen B | 15.034357 | nnU-Net `fresh_bnei_reem_i4` | structure |
| `bnei_reem_fresh_bnei_reem_i4` ("canonical") | Vertisol; which specimen is unresolved (numerically identical to specimen B) | 15.000149 | nnU-Net `fresh_bnei_reem_i4` | source of all Vertisol POM results |
| `mishmar_hanegev_maoz_3_5p85um` | Loess (external scan) | 5.85, plus a ~15 µm label-downsample | nnU-Net `mishmar_hanegev_maoz_3_5p85um_loess_i2` | structure + POM |
| `mishmar_hanegev_maoz_2_8p8um` | Loess (external scan) | 8.8, plus a ~15 µm label-downsample | nnU-Net `..._loess_i2` | structure + POM |
| `Cu011_samp_2` | Loess | 15.000149 | nnU-Net `..._loess_i2` | pore only (POM channel collapsed) |
| `Rehovot_samp2_highkV_Cu0.11_15um` | Sand | 15.000149 | global Otsu (binary) for metrics; nnU-Net outputs kept for reference | structure |
| `Rehovot_samp3_highkV_Cu0.11_15um` | Sand | 15.034357 | same as samp2 | structure |

Not analysed: `Cu011_samp_1`, `Cu011_samp_3` (raw scans only). Retracted (do not use): `bnei_reem_samp_2_0`, `bnei_reem_samp_2_0_recropped` (built from raw projections, not reconstructed slices) and `Rehovot_samp1` (not a real specimen).

Models used in the write-up (both 3d_fullres, fold 0, `checkpoint_final.pth`):

- Vertisol: `multi_sample_fresh_bnei_reem_i4`, trainer `nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss_lowlr`
- Loess (also applied to Rehovot for reference): `multi_sample_mishmar_hanegev_maoz_3_5p85um_loess_i2`, trainer `nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss`

Both trainers are defined in [`03_training/nnUNetTrainer_betterIgnoreSampling.py`](03_training/nnUNetTrainer_betterIgnoreSampling.py) and must be on nnU-Net's trainer path to load the checkpoints.

## Where the data lives

Volumes, checkpoints and annotations are **not in git**. They are on the lab share `\\hive3065\Yael_Mishael\Rony\` (on the host itself: `E:\PROJECTS\Yael_Mishael\Rony\`; older docs say `Z:\Rony\`, which is not mapped any more):

- Raw reconstructions and SkyScan/NRecon logs: `<share>\<date> <sample>\` (e.g. `18.12.25 bnei_reem_samp_2.0\`, `10.12.25_Rehovot_samp_2\`, `29.3.26 mishmar_hanegev_samp_2\`, `mishmar_hanegev_maoz\`).
- Preprocessed volumes: `<share>\remote_computer backup\10.5\`.
- nnU-Net models, training data, inference inputs and predictions: `<share>\remote_computer backup\nnUNet_resources\`.
- Topology / connectivity run outputs and χ(r) tables: `<share>\remote_computer backup\Topology_Metrics_Aug2026\`.

A packaged copy (every analysed volume with its segmentation and a README, the annotations, both models, the code and the analysis outputs) is in the hand-off ZIP `Schwartz_soil_uCT_handoff_2026-11.zip` (see [`00_docs/reports/HANDOFF_REPORT.md`](00_docs/reports/HANDOFF_REPORT.md)).

## Label convention

Values actually present in every packaged nnU-Net segmentation (`np.unique`, computed at hand-off): **0, 1, 2, 5**. Their meaning comes from each model's own `dataset.json` (identical for both models):

| Value | Model `dataset.json` name | Meaning |
|---|---|---|
| 0 | `background` | solid matrix |
| 1 | `Stones` | stones / dense mineral grains |
| 2 | `POM_type1` | **POM** |
| 3 | `POM_type2` | never predicted |
| 4 | `unused` | never predicted |
| 5 | `Pore` | **pore** |
| 6 | `ignore` | training only (unannotated voxels) |

So **pore = 5, POM = 2**, which is also what the analysis scripts were run with (`--pore-label 5 --pom-label 2`).

⚠ `dataset_info.json` at the repo root lists a different numbering (0 ToPredict, 1 Matrix, 2 Stones, 3 POM_type1, 4 POM_type2, 5 unused, 6 Pore). That is the **annotation** label space used when drawing in napari. `mask_to_nnUNet()` in `02_preprocessing/nnunet/preprocessing_nnUNet_train.py` turns annotation 0 into the ignore label and shifts every other class down by one. Do not read predictions with `dataset_info.json`. The Rehovot Otsu masks are boolean `.npy` arrays (True = pore; the Track E runs read them with `pore_label 1`).

The NIfTI headers of the volumes and predictions store a voxel size of 1.0 (no physical spacing). Take the physical voxel size from the table above (SkyScan logs; analysis configs).

## Reproducing the main metrics

| Metric | Script | Outputs |
|---|---|---|
| Pore-size distribution and PSD classes (8 subvolumes per soil, Fig. 4) | `05_evaluation/psd/run_psd_diagnostics.py` (core: `psd_diagnostics_core.py`); subvolume driver and stats in `05_evaluation/psd/fig4_inference_20260815/scripts/` (`extract_subvolumes.py`, `batch_run_psd.py`, `run_stats.py`, `make_figure4.py`); class re-analysis in `05_evaluation/psd/psd_A2_reanalysis_20260822/` | `05_evaluation/psd/fig4_inference_20260815/` (volumes there are not in git; tables and figures are), `psd_A2_reanalysis_20260822/` |
| Connectivity: Euler χ, connectivity density, Γ, degree of anisotropy | `05_evaluation/psd/run_psd_diagnostics.py extended` (functions in `psd_topology_metrics.py`) | share: `Topology_Metrics_Aug2026\raw\psd_diag_*\` (`summary.json`) and the summaries next to it |
| χ(r) sweep and crossover radius r* | `05_evaluation/psd/pore_metrics_research/compute_chi_r_sweep.py` | share: `Topology_Metrics_Aug2026\connectivity_function\chi_r_*.csv` (+ `.meta.json`) |
| Tortuosity (200³ subvolumes) | `06_reporting/tortuosity_subvolumes_20261004/run_tortuosity_subvolumes.py`, `aggregate.py` (solver: `tortuosity_diffusive()` in `psd_topology_metrics.py`) | `06_reporting/tortuosity_subvolumes_20261004/` |
| POM interface metrics (POM–pore, POM–matrix, SSA, IAD), resolution-matched | `05_evaluation/psd/pom_analysis_20260831_interface_metrics_resmatched/scripts/run_pom_interface_metrics.py` | same folder |
| Vertisol rebuild from raw (both specimens, one code path) | `04_inference/scripts/run_bnei_reem_unified_pipeline.py` | log `04_inference/scripts/bnei_reem_unified_pipeline_log.txt`; report `00_docs/reports/bnei_reem_unified_pipeline_results.md` |

Run all local Python with the project environment (`venv-napari`, see [`.github/copilot-instructions.md`](.github/copilot-instructions.md)). Scripts hard-code `\\hive3065\...` paths; on the host use the `E:\PROJECTS\...` equivalent.

## Known limitations

- **Tiny training set:** each model was trained on one volume with sparse annotations, and nnU-Net's train and validation split is the same single volume, so the reported Dice (~0.97) does not show generalisation.
- **Vertisol "canonical" volume:** its specimen label (A or B) is unresolved; it is numerically identical to specimen B, and every Vertisol POM result comes from it.
- **Rehovot (Sand):** metrics come from a global-Otsu binary mask, not nnU-Net; no POM was detected.
- **`Cu011_samp_2`:** POM channel collapsed (0.12 % vs 1.6 % in the 5.85 µm scan); used for pore metrics only.

## Related repository

The respiration simulation model (appendix A of the write-up): <https://github.com/agrorony/resp_model>.

## How to cite

Schwartz, R. (2026). *Research exercise, Hebrew University of Jerusalem.* Advisors: Prof. Y. Mishael and Dr. M. Dor.

Please also cite nnU-Net (Isensee et al., 2021) and the UFZ pipeline this fork builds on (Phalempin et al., 2025); the full references are in [`RESOURCES.md`](RESOURCES.md). The complete list of papers behind the analysis is in [`00_docs/literature/REFERENCES.md`](00_docs/literature/REFERENCES.md).
