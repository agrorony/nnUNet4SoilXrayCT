# Resources

External citations, institutional links, and tooling documentation for
this repository, consolidated out of `README.md` during the 2026-07
reorganization (per `REORG_PLAN.md` §7/§9 Q6 — resolved toward "move
everything out", per the maintainer's amendment E). If you used this
repository and associated code for your own work, please cite the
references below.

## 1. Citations

If you used this repository and associated code, please cite:

```
Isensee, F., Jaeger, P. F., Kohl, S. A., Petersen, J., & Maier-Hein, K. H. (2021).
nnU-Net: a self-configuring method for deep learning-based biomedical image segmentation.
Nature methods, 18(2), 203-211. https://doi.org/10.1038/s41592-020-01008-z
```

```
Phalempin, M., Krämer, L., Geers-Lucas, M., Isensee, F., & Schlüter, S. (2025).
Deep learning segmentation of soil constituents in 3D X-ray CT images.
Geoderma. 458, 117321. https://doi.org/10.1016/j.geoderma.2025.117321
```

(Previously `README.md` lines 9 and 12.)

## 2. Institutional links

- [Helmholtz Center for Environmental Research (UFZ)](https://www.ufz.de/) — Department of Soil System Sciences.
- [Helmholtz Imaging](https://www.helmholtz-imaging.de/) — Applied Computer Vision Lab.
- EVE HPC cluster — referenced throughout the training/inference sections of `README.md` for SLURM job submission.

(Previously `README.md` lines 2 and ~56.)

## 3. Tooling install docs

- [Miniforge](https://github.com/conda-forge/miniforge#miniforge3) — lightweight Conda/mamba distribution used for environment management.
- [devbio-napari](https://github.com/haesleinhuepf/devbio-napari) — napari distribution bundling common bio-image-analysis plugins.
- [nnU-Net installation instructions](https://github.com/MIC-DKFZ/nnUNet/blob/master/documentation/installation_instructions.md#installation-instructions) and [repository](https://github.com/MIC-DKFZ/nnUNet).
- [Fiji / ImageJ downloads](https://imagej.net/software/fiji/downloads#other-downloads) — used for `.tif`/`.mha` <-> `.hdr/.img` conversion via `07_utilities/Fiji_macros/`.

(Previously `README.md` lines ~96, ~114, ~155, ~157, ~169.)

## 4. PyTorch wheel indices

- CUDA 11.7: `pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu117` (previously `README.md` L247; used by the core nnUNet train/predict environment).
- CUDA 12.4: used by the GPU preprocessing branch — `02_preprocessing/filters/run_preprocess.py` and `02_preprocessing/filters/gpu_nlm_torch.py` (previously `preprocess/run_preprocess.py:24`, `preprocess/gpu_nlm_torch.py:24`), and referenced in `setup_prompt.md`.

## 5. micro-SAM background reading

Background reading for `05_evaluation/microsam_3d/` (previously `microsam_3d/README.md` lines 39, 43, 47, 51, 55):

- Archit, A. et al. — Segment Anything for Microscopy (micro-SAM).
- See `05_evaluation/microsam_3d/README.md` for the full annotated reading list and links.

## 6. Footnote

nnU-Net's own auto-emitted doc link (`resenc_presets.md`) that appears in
training log stdout is **not** included here — it is tool-generated log
noise, not an authored reference. See `logs_archive/` for raw training
logs.
