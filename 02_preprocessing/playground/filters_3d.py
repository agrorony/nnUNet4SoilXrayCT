"""
3D preprocessing filters for µCT volumes.

Each filter accepts a 3-D float32 array in [0, 1] and returns the same.
Add new filters here so they are available from run_napari_filters.py.
"""

import numpy as np
from scipy.ndimage import gaussian_filter, median_filter
from skimage.restoration import denoise_nl_means


def _estimate_sigma(volume: np.ndarray) -> float:
    """Robust noise-sigma estimate using the MAD of the finest wavelet scale.

    Uses a 3×3×3 Laplacian-like kernel approximation (sum of absolute
    differences) which is fast and does not require skimage.restoration.
    """
    # Median absolute deviation of the volume (quick proxy)
    med = np.median(volume)
    mad = np.median(np.abs(volume - med))
    # MAD-to-sigma conversion (Gaussian assumption)
    return float(mad * 1.4826)


def gaussian_filter_3d(volume: np.ndarray, sigma: float = 1.0) -> np.ndarray:
    """Apply a 3-D Gaussian blur.

    :param volume: 3-D float32 array in [0, 1].
    :param sigma: standard deviation of the Gaussian kernel.
    :return: filtered volume, same shape and dtype.
    """
    return gaussian_filter(volume, sigma=sigma).astype(np.float32)


def median_filter_3d(volume: np.ndarray, size: int = 3) -> np.ndarray:
    """Apply a 3-D median filter.

    :param volume: 3-D float32 array in [0, 1].
    :param size: side length of the cubic structuring element.
    :return: filtered volume, same shape and dtype.
    """
    return median_filter(volume, size=size).astype(np.float32)


def non_local_means_3d(
    volume: np.ndarray,
    patch_size: int = 5,
    patch_distance: int = 6,
    h: float | None = None,
) -> np.ndarray:
    """Apply 3-D non-local means denoising (fast mode).

    If *h* is ``None`` the noise standard deviation is estimated automatically
    from the volume and used as *h*.

    :param volume: 3-D float32 array in [0, 1].
    :param patch_size: size of patches used for denoising.
    :param patch_distance: maximal distance (in pixels) to search for patches.
    :param h: cut-off distance (denoising strength). ``None`` → auto-estimate.
    :return: denoised volume, same shape and dtype.
    """
    if h is None:
        sigma_est = _estimate_sigma(volume)
        h = float(0.6 * sigma_est)
        print(f"NLM: estimated sigma = {sigma_est:.4f}, using h = {h:.4f}")

    return denoise_nl_means(
        volume,
        patch_size=patch_size,
        patch_distance=patch_distance,
        h=h,
        fast_mode=True,
        channel_axis=None,
    ).astype(np.float32)
