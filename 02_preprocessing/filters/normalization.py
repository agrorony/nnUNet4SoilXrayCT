"""
Slice stacking and norm200 normalization for 3D µCT volumes.

The norm200 pipeline is ported from legacy/preprocess_ct_images.py but adapted
to operate on the full 3D volume (global statistics) rather than per-slice.
"""

from pathlib import Path

import numpy as np
import tifffile

P_LOW: float = 0.5
P_HIGH: float = 99.5
MODE_LOW: int = 100
MODE_HIGH: int = 254
TARGET_MODE: float = 200.0


def stack_slices_to_volume(input_dir: Path) -> np.ndarray:
    """Read all slice images in *input_dir* and stack them into a 3D array."""
    input_dir = Path(input_dir)
    paths = sorted(
        list(input_dir.glob("*.tif"))
        + list(input_dir.glob("*.tiff"))
        + list(input_dir.glob("*.png"))
    )
    if not paths:
        raise FileNotFoundError(f"No .tif / .tiff / .png images found in {input_dir}")

    slices = [tifffile.imread(str(p)) for p in paths]
    volume = np.stack(slices, axis=0)

    if volume.ndim != 3:
        raise ValueError(f"Expected 3-D stack (Z, H, W), got shape {volume.shape}")

    print(f"Stacked {len(paths)} slices -> volume {volume.shape}, dtype={volume.dtype}")
    return volume


def _to_uint8(volume: np.ndarray) -> np.ndarray:
    """Percentile-based rescaling of a float32 [0, 1] volume to uint8."""
    if volume.dtype == np.uint8:
        return volume

    x = volume.astype(np.float32, copy=False)
    mn = float(np.percentile(x, P_LOW))
    mx = float(np.percentile(x, P_HIGH))

    if mx <= mn:
        return np.zeros_like(x, dtype=np.uint8)

    scaled = (x - mn) * (255.0 / (mx - mn))
    return np.clip(scaled, 0, 255).astype(np.uint8)


def _detect_mode_above_threshold(
    volume_u8: np.ndarray,
    low: int = MODE_LOW,
    high: int = MODE_HIGH,
) -> int:
    """Return the histogram mode in [low, high] for a uint8 volume."""
    if volume_u8.dtype != np.uint8:
        raise ValueError("Expected uint8 volume for mode detection")

    flat = volume_u8.ravel()
    mask = (flat >= low) & (flat <= high)
    if not np.any(mask):
        return 0

    counts = np.bincount(flat[mask], minlength=256)
    return int(np.argmax(counts[low : high + 1]) + low)


def _rescale_to_mode_200(
    volume_u8: np.ndarray,
    mode: int,
    target: float = TARGET_MODE,
) -> np.ndarray:
    """Scale a uint8 volume so that *mode* maps to *target*."""
    if mode <= 0:
        return volume_u8

    factor = target / float(mode)
    out = volume_u8.astype(np.float32) * factor
    return np.clip(out, 0, 255).astype(np.uint8)


def norm200(volume: np.ndarray) -> np.ndarray:
    """Normalize a 3-D µCT volume using the norm200 pipeline."""
    if np.issubdtype(volume.dtype, np.uint16):
        float_vol = volume.astype(np.float32, copy=False) / 65535.0
    elif volume.dtype == np.uint8:
        float_vol = volume.astype(np.float32, copy=False) / 255.0
    elif np.issubdtype(volume.dtype, np.floating):
        float_vol = volume.astype(np.float32, copy=False)
    else:
        raise TypeError(f"Unsupported volume dtype: {volume.dtype}")

    float_vol = np.clip(float_vol, 0.0, 1.0)

    img255 = np.clip(float_vol * 255.0, 0, 255)
    vol_u8 = _to_uint8(img255)
    mode = _detect_mode_above_threshold(vol_u8)
    normed = _rescale_to_mode_200(vol_u8, mode)

    print(f"norm200: detected mode = {mode}, rescaled to target = {TARGET_MODE}")
    return normed.astype(np.float32) / 255.0
