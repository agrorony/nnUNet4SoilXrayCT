# Preprocess Playground

Interactive workspace for testing 3D preprocessing filters on µCT slice stacks
before integrating them into the main segmentation pipeline.

## Pipeline

```
slice folder  →  stack slices  →  norm200  →  3D filter  →  Napari viewer
                                 (global)
```

**norm200** detects the mineral-intensity peak in the bright region of the
histogram and rescales the entire 3D volume so that this peak maps to intensity
value 200.  It operates on the full volume (global statistics), not per-slice.

## Environment

Activate the existing mamba environment:

```
mamba activate venv-napari
```

(Located at `C:\Users\ronys\miniconda3\envs\venv-napari`)

## Usage

Run from the **repository root**:

```
python preprocess_playground/run_napari_filters.py --input_dir path/to/slices --filter gaussian
```

### Available filters

| Name       | Description                         |
|------------|-------------------------------------|
| `gaussian` | 3D Gaussian blur (default)          |
| `median`   | 3D median filter                    |
| `nlm`      | 3D non-local means (fast mode)      |

### Examples

```bash
# Gaussian (default)
python preprocess_playground/run_napari_filters.py --input_dir D:\data\sample_stack

# Median filter
python preprocess_playground/run_napari_filters.py --input_dir D:\data\sample_stack --filter median

# Non-local means
python preprocess_playground/run_napari_filters.py --input_dir D:\data\sample_stack --filter nlm
```

The Napari viewer opens with three layers:

- **raw** — stacked volume before any processing
- **norm200** — volume after norm200 normalization
- **filtered (…)** — volume after the selected 3D filter

## Current Conclusion

**Non-Local Means (NLM)** was selected as the preferred preprocessing filter
for µCT volumes. It provides better noise reduction while preserving pore
boundaries compared to Gaussian and median filters.

Working pipeline:

```
slice folder → stack → norm200 → NLM → visualization
```

NLM parameters (defaults in `filters_3d.py`):

- `patch_size = 5`
- `patch_distance = 6`
- `h = 0.6 × estimated_sigma` (auto-estimated from the volume)
- `fast_mode = True`

## Adding new filters

1. Open `filters_3d.py`.
2. Add a function with the signature `my_filter(volume: np.ndarray, ...) -> np.ndarray`.
   Input and output should be float32 arrays in [0, 1].
3. Register the filter in `run_napari_filters.py` by adding an entry to the
   `FILTERS` dictionary.
