

## Remote Desktop Setup — nnUNet4SoilXrayCT Dependencies

### Context

You are setting up a **Windows machine with GPU (CUDA)** to run the full `nnUNet4SoilXrayCT` pipeline — preprocessing, annotation, nnUNet training/inference, postprocessing, and analysis. **Fiji is not required** — the codebase already uses Python-native conversion paths.

### Step 1 — Create conda environment

```powershell
conda create -n venv-napari python=3.11 -y
conda activate venv-napari
```

### Step 2 — Install PyTorch with CUDA

Install PyTorch **with CUDA support** first (before nnUNet). Check your CUDA driver version with `nvidia-smi` and pick the matching CUDA toolkit from https://pytorch.org/get-started/locally/. Example for CUDA 12.4:

```powershell
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
```

Verify GPU is visible:
```powershell
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

### Step 3 — Install nnUNet v2

```powershell
pip install nnunetv2
```

This pulls many transitive dependencies (numpy, scipy, scikit-image, tqdm, etc.).

### Step 4 — Install remaining project dependencies

```powershell
pip install nibabel tifffile SimpleITK pandas matplotlib seaborn napari[all] pyyaml porespy
```

| Package | Used by |
|---|---|
| `nibabel` | NIfTI I/O (preprocessing_nnUNet_train.py, `preprocessing_nnUNet_predict*.py`, check_data.py) |
| `tifffile` | TIFF volume I/O (make_annotations.py, preprocessing_nnUNet_train.py, run_preprocess.py, run_psd_diagnostics.py) |
| `SimpleITK` | Volume split/concatenate (preprocessing_nnUNet_predict_split.py, postprocessing_nnUNet_predict_concatenate.py) |
| `pandas` | Metrics aggregation (extract_trainlog.py) |
| `matplotlib` | Plotting (extract_trainlog.py) |
| `seaborn` | Plotting (extract_trainlog.py) |
| `napari[all]` | 3D annotation GUI (make_annotations.py); also installs `qtpy` |
| `pyyaml` | Config loading (legacy pore analysis) |
| `porespy` | Local thickness via EDT sphere reconstruction (analysis/psd_diagnostics_core.py) |

### Step 5 — (Optional) Install CuPy for GPU-accelerated PSD analysis

```powershell
pip install cupy-cuda12x
```

Match `12x` to your CUDA version. Only needed for psd_diagnostics_core.py GPU path.

### Step 6 — Set nnUNet environment variables

Set as **persistent environment variables** (System → Advanced → Environment Variables), or in your PowerShell profile:

```powershell
$env:nnUNet_raw = "C:\nnUNet_workspace\nnUNet_raw"
$env:nnUNet_preprocessed = "C:\nnUNet_workspace\nnUNet_preprocessed"
$env:nnUNet_results = "C:\nnUNet_workspace\nnUNet_results"
```

Create the directories:
```powershell
New-Item -ItemType Directory -Force -Path $env:nnUNet_raw, $env:nnUNet_preprocessed, $env:nnUNet_results
```

### Step 7 — Update __path__.py

Adapt all paths in __path__.py to match the remote machine's directory structure:
- `PATH_nnUNet_raw` — must match `$env:nnUNet_raw`
- `input_dir_images` / `input_dir_masks` — local data directories
- `PATH_ImageJ` — can be left as-is or set to empty string (Fiji is not used)

### Step 8 — Verify installation

```powershell
python -c "
import numpy, nibabel, tifffile, SimpleITK, pandas, matplotlib, seaborn, scipy, skimage, tqdm, napari, torch, yaml
from nnunetv2.dataset_conversion.generate_dataset_json import generate_dataset_json
print('All imports OK')
print(f'torch CUDA: {torch.cuda.is_available()}')
"
```

### Summary — all pip packages

```
torch torchvision torchaudio    # with --index-url for CUDA
nnunetv2
nibabel
tifffile
SimpleITK
pandas
matplotlib
seaborn
napari[all]
pyyaml
porespy
cupy-cuda12x                    # optional, for GPU PSD analysis
```

Standard-library modules used (no install needed): `glob`, `os`, `shutil`, `json`, `subprocess`, `pathlib`, `typing`, `re`, `argparse`, `csv`, `sys`, `warnings`, `datetime`, `pickle`, `gzip`, `copy`, `logging`, `dataclasses`, `importlib`.

