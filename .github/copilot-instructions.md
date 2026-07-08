# Copilot Instructions for nnUNet4SoilXrayCT

## 1) Project Mental Model

This repository implements a soil X-ray CT segmentation workflow around nnUNet v2, with extra conversion, splitting, annotation, and analysis utilities.

Primary end-to-end flow:

1. Dataset metadata definition:
- `dataset_info.json` (repo root, canonical single location) defines `TaskID`, `DatasetName`, `norm_type`, class labels, and annotation colors.

2. Ground-truth annotation:
- `01_data_ingestion/make_annotations.py` loads one 3D `.tif` volume, initializes the middle slice with Otsu-based mask, opens Napari for manual edits, and saves label volume as `.tif` (`uint8`).

3. Training data preparation:
- `02_preprocessing/nnunet/preprocessing_nnUNet_train.py` converts `.tif`/`.mha` -> `.hdr/.img` using Fiji macros, then `.hdr` -> `.nii.gz`, remaps labels for nnUNet ignore-label semantics, crops along Z around annotated slices, normalizes image volume, and writes nnUNet layout:
  - `imagesTr/*_0000.nii.gz`
  - `labelsTr/*.nii.gz`
  - generated `dataset.json`

4. nnUNet planning and preprocessing:
- Native `nnUNetv2_plan_and_preprocess` consumes `nnUNet_raw` dataset output from step 3.

5. Training:
- Native `nnUNetv2_train` with custom trainer `nnUNetTrainer_betterIgnoreSampling`.
- `03_training/nnUNetTrainer_betterIgnoreSampling.py` customizes patch sampling to handle ignore regions better.

6. Inference preprocessing:
- `02_preprocessing/nnunet/preprocessing_nnUNet_predict.py` for `.mha` input.
- `02_preprocessing/nnunet/preprocessing_nnUNet_predict_tif.py` for `.tif` input.
- Both convert to `*_0000.nii.gz` and apply configured normalization.

7. Split for parallel GPU inference:
- `02_preprocessing/nnunet/preprocessing_nnUNet_predict_split.py` reads model `plans.json`, computes overlap from patch size/spacing, and writes overlapped chunks with encoded filenames:
  - `sample__axis__min__max__0000.nii.gz`

8. Inference:
- Native `nnUNetv2_predict` (typically via SLURM array job).

9. Postprocessing:
- `04_inference/postprocessing_nnUNet_predict_concatenate.py` reassembles split predictions and trims overlap.
- `04_inference/postprocessing_nnUNet_predict.py` converts final `.nii.gz` predictions to `.mha` via Fiji macro.

10. Result analysis:
- `06_reporting/scripts/extract_trainlog.py` parses training logs and plots aggregated train/val loss.
- `05_evaluation/labels_debug/retrieve_dice_score.py` aggregates fold-level metrics JSON to CSV.

Auxiliary preprocessing branch:
- `02_preprocessing/filters/run_preprocess.py` performs `stack slices -> norm200 -> CUDA chunked NLM` to produce 3D TIFF outputs.
- `02_preprocessing/filters/colab_cli_runner.ipynb` is a Colab runner for that GPU preprocessing branch.
- `02_preprocessing/playground/*` is an interactive local experimentation area (Napari + CPU filters).

## 2) Environment & Execution Rules (STRICT)

### Canonical environment for this workspace

Primary environment (authoritative for local execution):
- `venv-napari` (mamba/conda environment)

Detected interpreter details:
- Name: `venv-napari`
- Python: `3.11`
- Interpreter path: `C:/Users/rony.schwartz/.conda/envs/venv-napari/python.exe`

Activation (PowerShell):

```powershell
conda activate venv-napari
```

### Environment Rules (STRICT)

- ALWAYS use `venv-napari` for local execution.
- NEVER create a new environment.
- NEVER switch environments automatically.
- ALL Python execution must use `C:/Users/rony.schwartz/.conda/envs/venv-napari/python.exe`.

### Execution Context Mapping

- `local`:
  - MUST use `venv-napari`.
- `remote-gpu`:
  - external environment (NOT managed here).
  - do NOT assume the same environment as local.
- `colab`:
  - Colab runtime only.
  - ignore local environment.

Rules:
- Code must not mix assumptions between `local`, `remote-gpu`, and `colab`.
- If execution context is unclear, ask the user before proceeding.

### Interpreter Enforcement

- All Python commands for local execution must use: `C:/Users/rony.schwartz/.conda/envs/venv-napari/python.exe`.
- Do NOT use system Python.
- Do NOT rely on PATH resolution.
- Do NOT call `python` without explicit environment clarity.

ALWAYS:
- Use `venv-napari` for all local Python work.
- Use `pip install ...` only inside activated `venv-napari` when needed.

NEVER:
- Never create a new environment (`conda create`, `mamba create`, `python -m venv`).
- Never suggest virtualenv/plain venv workflows.
- Never switch environments automatically.

IF rules:
- If a dependency is missing, install it into `venv-napari`.
- If execution context is unclear, ask whether the task is `local`, `remote-gpu`, or `colab`.

Package management policy:
- Install all Python dependencies into `venv-napari`.
- Do not mix package installs across contexts.
- Do not assume system Python for local project commands.

Dependency baseline inferred from imports and installed envs:
- Core: `numpy`, `nibabel`, `SimpleITK`, `tifffile`, `tqdm`, `pandas`, `matplotlib`, `seaborn`.
- Annotation/playground: `napari`, `scikit-image`, `scipy`.
- nnUNet path: `nnunetv2`.
- GPU preprocessing path: `torch` (CUDA-enabled build required for `02_preprocessing/filters/*` NLM pipeline).

### Execution matrix

| script/module | environment | GPU required | where to run |
| --- | --- | --- | --- |
| `01_data_ingestion/make_annotations.py` | `venv-napari` | No (CPU-only) | Local workstation with GUI (Napari) |
| `02_preprocessing/nnunet/preprocessing_nnUNet_train.py` | `venv-napari` | No (CPU-only) | Local workstation |
| `02_preprocessing/nnunet/preprocessing_nnUNet_predict.py` | `venv-napari` | No (CPU-only) | Local workstation |
| `02_preprocessing/nnunet/preprocessing_nnUNet_predict_tif.py` | `venv-napari` | No (CPU-only) | Local workstation |
| `02_preprocessing/nnunet/preprocessing_nnUNet_predict_split.py` | `venv-napari` | No (CPU-only) | Local workstation |
| `04_inference/postprocessing_nnUNet_predict_concatenate.py` | `venv-napari` | No (CPU-only) | Local workstation |
| `04_inference/postprocessing_nnUNet_predict.py` | `venv-napari` | No (CPU-only, Fiji subprocess) | Local workstation |
| `03_training/nnUNetTrainer_betterIgnoreSampling.py` (used by `nnUNetv2_train`) | remote environment (external, not managed here) | Yes (practically GPU-required for 3D fullres training) | Remote GPU/HPC (SLURM) |
| `07_utilities/Utilities/submit_nnUNet_training` | remote environment (external, not managed here) | Yes | Remote GPU/HPC |
| `07_utilities/Utilities/submit_nnUNet_inference` | remote environment (external, not managed here) | Yes | Remote GPU/HPC |
| `07_utilities/Utilities/mkdir_movefiles.sh` | shell env | No | Remote or local shell |
| `06_reporting/scripts/extract_trainlog.py` | `venv-napari` | No | Local workstation |
| `05_evaluation/labels_debug/retrieve_dice_score.py` | `venv-napari` | No | Local workstation |
| `02_preprocessing/filters/run_preprocess.py` | `venv-napari` with torch+CUDA | Yes (hard-required) | GPU machine or Google Colab GPU |
| `02_preprocessing/filters/gpu_nlm_torch.py` | `venv-napari` with torch+CUDA | Yes (hard-required) | GPU machine or Google Colab GPU |
| `02_preprocessing/filters/normalization.py` | `venv-napari` | No | Local/GPU host |
| `02_preprocessing/filters/colab_cli_runner.ipynb` | existing Colab runtime env | Yes for NLM step | Google Colab |
| `02_preprocessing/playground/run_napari_filters.py` | `venv-napari` | No (CPU filter implementations) | Local workstation with GUI |
| `02_preprocessing/playground/filters_3d.py` | `venv-napari` | No (CPU-only) | Local workstation |
| `02_preprocessing/legacy/preprocess_ct_images.py` | `venv-napari` | No | Local workstation |

### Non-Production Code Guard

- `02_preprocessing/playground/*` is experimental.
- `02_preprocessing/legacy/*` and `05_evaluation/legacy_pores_analysis/*` are reference-only (the latter is archived, scheduled for deletion in a future cleanup cycle).
- Agents MUST NOT base implementations on these folders.
- Agents MUST NOT modify these folders unless explicitly requested.

## 3) Device Handling Policy

1. Default policy:
- Never assume CUDA availability.
- Select device explicitly from code path requirements.

2. GPU-allowed / required zones:
- `02_preprocessing/filters/run_preprocess.py` and `02_preprocessing/filters/gpu_nlm_torch.py` require CUDA; `run_preprocess.py` raises if `torch.cuda.is_available()` is false.
- nnUNet training/inference jobs (via SLURM scripts and `nnUNetv2_train`/`nnUNetv2_predict`) are intended for GPU nodes (A100 in provided scripts).

3. CPU-only zones:
- Annotation, conversion, splitting, concatenation, and metric extraction scripts are CPU pipelines and should not be rewritten to enforce GPU.

4. Torch rules:
- Keep torch/CUDA logic only where it already exists.
- Preserve explicit OOM handling and chunk-size control in `02_preprocessing/filters/gpu_nlm_torch.py`.
- Do not introduce torch device code into non-torch scripts.

## 4) Data Conventions

1. Core modalities and file formats:
- Input grayscale volumes: 3D `.tif` (and sometimes `.mha`).
- Intermediate conversion: `.hdr/.img` via Fiji macros.
- nnUNet training/prediction: `.nii.gz`.
- Optional export format: `.mha` after prediction.

2. Shape conventions in code:
- Annotation script treats TIFF volume as `(Z, Y, X)` and seeds middle slice.
- Nibabel conversion reads 4D HDR arrays and extracts `[:, :, :, 0]` before saving NIfTI.
- Split/concatenate code uses SimpleITK arrays with explicit transpose operations between SITK and NumPy axis order.

3. Naming conventions:
- nnUNet image channel suffix: `_0000.nii.gz`.
- Split inference chunks: `name__axis__min__max__0000.nii.gz`.
- Concatenation logic expects encoded axis/min/max in filename.

4. Label semantics:
- `dataset_info.json` label `0` is `ToPredict` (unannotated/ignore source).
- `mask_to_nnUNet` remaps label `0` to last class (ignore), shifts remaining class IDs by `-1`.
- Current annotation classes in this repository:
  - `0`: `ToPredict`
  - `1`: `Matrix`
  - `2`: `Stones`
  - `3`: `POM_type1`
  - `4`: `POM_type2`
  - `5`: `unused`
  - `6`: `Pore`
- Iteration rule: user-facing QA and slice-injection handoffs must use annotation label space.
- For `inspect_predictions.py`, run with `--reverse_label_map` so displayed prediction IDs match annotation IDs.

5. Dtype conventions observed:
- Annotation masks saved as `uint8` TIFF.
- HDR/NIfTI conversion often casts to `uint8`.
- `02_preprocessing/filters/*` normalization/NLM branch operates on float32 volumes in `[0, 1]` and writes float32 TIFF.

## 5) Architecture Rules

1. Top-level scripts are orchestration entry points:
- Keep single-purpose CLI behavior per file.
- Avoid embedding unrelated logic across stages.

2. Conversion boundary:
- Fiji macro invocation is centralized in conversion helpers (`convert_*_to_hdr`, `nii_to_mha`).
- Do not duplicate subprocess macro wrappers in unrelated modules.

3. nnUNet customization boundary:
- Training behavior modifications belong in `03_training/nnUNetTrainer_betterIgnoreSampling.py` only.
- Data-format preparation remains in `02_preprocessing/nnunet/preprocessing_nnUNet_train.py`.

4. Branch separation:
- `02_preprocessing/filters/*` is a dedicated norm200 + CUDA NLM branch.
- `02_preprocessing/playground/*` is experimental/interactive and should not be treated as production training pipeline code.
- `02_preprocessing/legacy/*` and `05_evaluation/legacy_pores_analysis/*` are historical reference; do not prioritize them for new workflow changes.

5. Path config boundary:
- Keep machine-specific paths in `02_preprocessing/nnunet/__path__.py` and job scripts, not hardcoded in new modules.

## 6) Performance Constraints

1. Memory-sensitive operations already present:
- `preprocessing_nnUNet_train.py` and predict preprocess scripts delete temporary arrays after each file.
- NLM GPU pipeline is explicitly chunked (`chunk_size`, `min_chunk_size`) with halo overlap and CUDA cache clears.

2. Chunking and overlap strategy:
- `preprocessing_nnUNet_predict_split.py` computes overlap from model patch size and spacing (from `plans.json`) to reduce seam artifacts.
- `postprocessing_nnUNet_predict_concatenate.py` trims/averages overlaps when reassembling.

3. HPC parallelism model:
- One fold per SLURM array index for training.
- One per-sample folder per SLURM array index for inference.
- Keep this coarse-grained parallelism model when editing automation scripts.

4. Constraints for code changes:
- Do not load whole datasets into memory when file-wise iteration exists.
- Preserve existing crop/split strategy before introducing heavier transforms.

## 7) Copilot Behavior Rules

MUST:
- Explain intended code changes before applying edits.
- Enforce existing-environment usage and provide activation command when relevant.
- Enforce the local interpreter path `C:/Users/rony.schwartz/.conda/envs/venv-napari/python.exe` for local Python execution.
- Respect device logic already encoded by the repository (CPU scripts stay CPU; GPU scripts keep CUDA guards).
- Keep stage boundaries intact (annotation, conversion, training prep, split, concat, analysis).
- Preserve nnUNet naming and label remapping semantics.

MUST NOT:
- Create new virtual environments.
- Suggest or introduce environment switching for local execution.
- Assume GPU availability for all scripts.
- Hardcode new absolute local paths inside source modules.
- Replace file-format bridges (Fiji macro steps) with incompatible ad hoc conversions unless explicitly requested.
- Break split filename conventions used by concatenation.
All command examples MUST use full interpreter path:
C:/Users/rony.schwartz/.conda/envs/venv-napari/python.exe script.py

Do NOT use:
python script.py
