# nnUNet4SoilXrayCT: soil structure and organic matter in three Israeli soils (HUJI, 2026)

This repository holds the code and results for a research exercise at the Hebrew University of Jerusalem (Rony Schwartz, 2026; advisors Prof. Yael Mishael and Dr. Maoz Dor). X-ray µCT scans of three Israeli soils were segmented with nnU-Net v2 into pore, solid matrix and particulate organic matter (POM):

- **Loess** from Mishmar HaNegev;
- **Vertisol** from Bnei Re'em;
- **Sand** from Rehovot.

Structural metrics were then computed from the segmentations: pore-size classes, connectivity (Γ, Euler χ, crossover radius r*), distances to pores, tortuosity, and POM metrics.

The work builds on the UFZ pipeline by Phalempin et al. ([upstream repo](https://github.com/MaxPhal/nnUNet4SoilXrayCT); tutorial kept in [`docs/UPSTREAM_README_UFZ.md`](docs/UPSTREAM_README_UFZ.md)). The write-up has been submitted, and this repository is in its final hand-off state (2026-11).

## Where things are

The folders follow the pipeline in order. Each one holds only what produced a result in the write-up. Everything else is in `archive/`.

| Folder | What is in it |
|---|---|
| `1_annotation/` | `make_annotations.py`: the napari annotation tool. `merge_annotations.py`, `select_slices_and_predict.py` and `chunk_extractor.py`: the annotation loop. `napari_review_tool/`: the prediction-review viewer. `data_registry.json`: which volume and annotation file each training run used |
| `2_preprocessing/` | `denoise_normalize/`: crop, norm200 and GPU non-local-means. `nnunet_dataset/`: turns volumes and annotations into nnU-Net datasets (with the Fiji macros it calls). `otsu_threshold_3d.py`: binary pore masks (used for the Rehovot sand) |
| `3_training/` | The custom trainer `nnUNetTrainer_betterIgnoreSampling.py`, the generic driver `run_training.py`, and one folder per final model (`vertisol_i4/`, `loess_i2/`). Each model folder holds its config, `dataset.json`, `plans.json`, the training log and the training curves |
| `4_inference/` | `run_inference.py` and the chunk concatenation, then one folder per soil: `vertisol/` (specimen A/B rebuild pipeline; canonical inference), `loess/` (Cu011 and 8.8 µm drivers and logs), `sand_rehovot/` |
| `5_analysis/` | One folder per analysis: `pore_size_distribution/`, `connectivity/`, `distance_maps/`, `tortuosity/`, `pom/`, plus `shared_code/`. **See [`5_analysis/README.md`](5_analysis/README.md)** for which script produces which result |
| `6_figures/` | `write_up_figures/`: the scripts behind the 7 figures in the write-up. Also `segmentation_examples/`, `renders_3d/` and `napari_viewers/` |
| `docs/` | `HANDOFF_REPORT.md`, the Vertisol specimen investigation, the CT scan parameters, `literature/REFERENCES.md` (every paper behind the analysis), and the upstream tutorial and citations (`RESOURCES.md`) |
| `archive/` | Earlier iterations, retracted runs, the retired POM-clustering analyses and exploratory tools. Code there still has its old paths; `archive/PATH_MAP_2026-11.csv` maps old paths to new ones |
| `DATA_CATALOG.md` | The specimen inventory: every scan, where it is, and whether it is valid |
| `dataset_info.json` | The annotation label scheme (scripts read it from the repo root) |

## Specimens and models

The specimen inventory is in [`DATA_CATALOG.md`](DATA_CATALOG.md). Distinct names there are not distinct specimens.

| Specimen ID | Soil | Voxel (µm) | Segmentation | Used for |
|---|---|---|---|---|
| `bnei_reem_specA_unified` | Vertisol, specimen A | 15.000149 | nnU-Net `fresh_bnei_reem_i4` | structure |
| `bnei_reem_specB_unified` | Vertisol, specimen B | 15.034357 | nnU-Net `fresh_bnei_reem_i4` | structure |
| `bnei_reem_fresh_bnei_reem_i4` ("canonical") | Vertisol: an older processing of a scan numerically identical to specimen B (see `DATA_CATALOG.md`) | see catalog | nnU-Net `fresh_bnei_reem_i4` | source of all Vertisol POM results |
| `mishmar_hanegev_maoz_3_5p85um` | Loess (external scan) | 5.85, plus a ~15 µm label-downsample | nnU-Net `..._loess_i2` | structure + POM |
| `mishmar_hanegev_maoz_2_8p8um` | Loess (external scan) | 8.8, plus a ~15 µm label-downsample | nnU-Net `..._loess_i2` | structure + POM |
| `Cu011_samp_2` | Loess | 15.000149 | nnU-Net `..._loess_i2` | pore only (POM channel collapsed) |
| `Rehovot_samp2_highkV_Cu0.11_15um` | Sand | 15.000149 | global Otsu (binary) | structure |
| `Rehovot_samp3_highkV_Cu0.11_15um` | Sand | 15.034357 | global Otsu (binary) | structure |

Both models are `3d_fullres`, fold 0, `checkpoint_final.pth`:

- **Vertisol:** `multi_sample_fresh_bnei_reem_i4`, trainer `nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss_lowlr`.
- **Loess:** `multi_sample_mishmar_hanegev_maoz_3_5p85um_loess_i2`, trainer `nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss`.

Both trainers are defined in `3_training/nnUNetTrainer_betterIgnoreSampling.py`, and that file must be on nnU-Net's trainer path to load the checkpoints.

## Where the data lives

Volumes, checkpoints and annotations are **not in git**. They are on the lab share `\\hive3065\Yael_Mishael\Rony\` (on the host itself: `E:\PROJECTS\Yael_Mishael\Rony\`; older docs say `Z:\Rony\`):

- **Raw reconstructions and scan logs:** `<share>\<date> <sample>\`.
- **Preprocessed volumes:** `<share>\remote_computer backup\10.5\`.
- **Models, training data, inference inputs and predictions:** `<share>\remote_computer backup\nnUNet_resources\`.
- **Topology and connectivity run outputs, χ(r) tables:** `<share>\remote_computer backup\Topology_Metrics_Aug2026\`.

Some analysis scripts read input volumes from run folders that were never in git. On the lab computer those folders stay at their old paths under `05_evaluation/psd/`, and the scripts point there (marked in the code).

A packaged copy of the data is in the hand-off ZIP: every analysed volume with its segmentation, the annotations, both models and the analysis outputs. See [`docs/HANDOFF_REPORT.md`](docs/HANDOFF_REPORT.md).

## Label convention

Predictions use **pore = 5, POM = 2** (also 0 = solid matrix, 1 = stones). This comes from each model's `dataset.json`.

`dataset_info.json` is the *annotation* label space, where every class is one higher: annotation 0 means "not annotated" and becomes nnU-Net's ignore label. Do not read predictions with `dataset_info.json`.

The Rehovot Otsu masks are boolean arrays, True = pore. NIfTI headers store a voxel size of 1.0, so take the physical voxel size from the table above.

## Known limitations

- **Tiny training set.** Each model was trained on one volume with sparse annotations, and nnU-Net's training and validation split is that same volume. The Dice of ~0.97 therefore says nothing about generalisation.
- **Vertisol "canonical" volume.** It is numerically identical to specimen B, and every Vertisol POM result comes from it.
- **Rehovot (sand).** Metrics come from a global-Otsu binary mask, not nnU-Net, and no POM was detected.
- **`Cu011_samp_2`.** The POM channel collapsed (0.12 % vs 1.6 % in the 5.85 µm scan), so it is used for pore metrics only.

## Related repository

The respiration simulation model (appendix A of the write-up): <https://github.com/agrorony/resp_model>.

## How to cite

Schwartz, R. (2026). *Research exercise, Hebrew University of Jerusalem.* Advisors: Prof. Y. Mishael and Dr. M. Dor.

Please also cite nnU-Net (Isensee et al., 2021) and the UFZ pipeline (Phalempin et al., 2025). The full list of papers behind the analysis is in [`docs/literature/REFERENCES.md`](docs/literature/REFERENCES.md).
