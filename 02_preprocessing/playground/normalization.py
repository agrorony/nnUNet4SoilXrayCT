"""
Slice stacking and norm200 normalization for 3D µCT volumes.

The norm200 pipeline is ported from legacy/preprocess_ct_images.py but adapted
to operate on the **full 3D volume** (global statistics) rather than per-slice.
"""

from pathlib import Path
import numpy as np
import tifffile

# ---------------------------------------------------------------------------
# norm200 constants (ported from legacy/preprocess_ct_images.py)
# ---------------------------------------------------------------------------
P_LOW: float = 0.5
P_HIGH: float = 99.5
MODE_LOW: int = 100
MODE_HIGH: int = 254
TARGET_MODE: float = 200.0


# ---------------------------------------------------------------------------
# Slice stacking
# ---------------------------------------------------------------------------

def stack_slices_to_volume(input_dir: Path) -> np.ndarray:
    """Read all slice images in *input_dir* and stack them into a 3D array.

    :param input_dir: directory containing 2-D slice images (.tif/.tiff/.png).
    :return: 3-D numpy array with shape (num_slices, H, W), original dtype.
    """
    input_dir = Path(input_dir)
    paths = sorted(
        list(input_dir.glob("*.tif"))
        + list(input_dir.glob("*.tiff"))
        + list(input_dir.glob("*.png"))
    )
    if not paths:
        raise FileNotFoundError(
            f"No .tif / .tiff / .png images found in {input_dir}"
        )

    slices = [tifffile.imread(str(p)) for p in paths]
    volume = np.stack(slices, axis=0)

    if volume.ndim != 3:
        raise ValueError(
            f"Expected 3-D stack (Z, H, W), got shape {volume.shape}"
        )

    print(f"Stacked {len(paths)} slices → volume {volume.shape}, dtype={volume.dtype}")
    return volume


# ---------------------------------------------------------------------------
# norm200 helpers (ported from legacy/preprocess_ct_images.py)
# ---------------------------------------------------------------------------

def _to_uint8(volume: np.ndarray) -> np.ndarray:
    """Percentile-based rescaling of a float32 [0, 1] volume to uint8.

    :param volume: 3-D float32 array in [0, 1].
    :return: 3-D uint8 array in [0, 255].
    """
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
    """Return the histogram mode in [low, high] for a uint8 volume.

    :param volume_u8: 3-D uint8 array.
    :param low: lower bound of the search window.
    :param high: upper bound of the search window.
    :return: intensity value of the mode, or 0 if none found.
    """
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
    """Scale a uint8 volume so that *mode* maps to *target*.

    :param volume_u8: 3-D uint8 array.
    :param mode: detected mode value.
    :param target: desired output value for that mode.
    :return: rescaled uint8 array.
    """
    if mode <= 0:
        return volume_u8

    factor = target / float(mode)
    out = volume_u8.astype(np.float32) * factor
    return np.clip(out, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------------------
# norm200 — public entry point
# ---------------------------------------------------------------------------

def norm200(volume: np.ndarray) -> np.ndarray:
    """Normalize a 3-D µCT volume using the norm200 pipeline.

    Pipeline (operates on the **full 3D volume**, not per-slice):
      1. Convert raw dtype → float32 [0, 1].
      2. Percentile-clip to uint8.
      3. Detect the mineral-peak mode in the bright region [100, 254].
      4. Rescale so that mode → 200.
      5. Return float32 [0, 1].

    :param volume: 3-D array (uint16, uint8, or float).
    :return: normalized 3-D float32 array in [0, 1].
    """
    # --- dtype dispatch → float32 [0, 1] ---
    if np.issubdtype(volume.dtype, np.uint16):
        float_vol = volume.astype(np.float32, copy=False) / 65535.0
    elif volume.dtype == np.uint8:
        float_vol = volume.astype(np.float32, copy=False) / 255.0
    elif np.issubdtype(volume.dtype, np.floating):
        float_vol = volume.astype(np.float32, copy=False)
    else:
        raise TypeError(f"Unsupported volume dtype: {volume.dtype}")

    float_vol = np.clip(float_vol, 0.0, 1.0)

    # --- norm200 core ---
    img255 = np.clip(float_vol * 255.0, 0, 255)
    vol_u8 = _to_uint8(img255)
    mode = _detect_mode_above_threshold(vol_u8)
    normed = _rescale_to_mode_200(vol_u8, mode)

    print(f"norm200: detected mode = {mode}, rescaled to target = {TARGET_MODE}")
    return normed.astype(np.float32) / 255.0
