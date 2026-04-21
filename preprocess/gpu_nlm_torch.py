"""
GPU-backed 3D non-local means filtering using PyTorch CUDA.

This module is intentionally self-contained and avoids skimage/scipy denoisers.
It operates on float32 volumes in [0, 1] and supports chunked processing for
large 3D volumes that do not fit on GPU memory in one pass.
"""

# =============================================================================
# Runtime dependencies and version constraints
# =============================================================================
# Execution context: GPU machine or Google Colab (CUDA required — hard fail
# if torch.cuda.is_available() is False).
#
# Package        Constraint               Reason
# -------------- ------------------------ ------------------------------------
# torch          >= 2.0, CUDA build       GPU NLM convolution kernels;
#                                         CPU-only torch will fail at runtime
# numpy          any modern (no upper     no numba; torch handles GPU ops
#                bound)                   directly
# =============================================================================
#
# Install torch with CUDA (example for CUDA 12.4):
#   pip install torch --index-url https://download.pytorch.org/whl/cu124
# Verify: python -c "import torch; print(torch.cuda.is_available())"
# =============================================================================

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import torch
import torch.nn.functional as F


@dataclass(frozen=True)
class NLMConfig:
    patch_size: int = 5
    patch_distance: int = 6
    h: float | None = None
    chunk_size: int = 128
    min_chunk_size: int = 32


def _estimate_sigma_torch(volume_3d: torch.Tensor) -> float:
    med = torch.median(volume_3d)
    mad = torch.median(torch.abs(volume_3d - med))
    return float((mad * 1.4826).item())


def _build_offsets(radius: int) -> Iterable[tuple[int, int, int]]:
    for dz in range(-radius, radius + 1):
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if dz == 0 and dy == 0 and dx == 0:
                    continue
                yield dz, dy, dx


def _nlm_single_tile_cuda(
    tile: torch.Tensor,
    patch_size: int,
    patch_distance: int,
    h: float,
) -> torch.Tensor:
    """Apply NLM to one tile tensor on CUDA.

    :param tile: 3-D CUDA tensor [Z, Y, X], float32 in [0, 1].
    :return: denoised tile, same shape.
    """
    if tile.ndim != 3:
        raise ValueError(f"Expected 3-D tile, got shape {tuple(tile.shape)}")

    vol = tile.unsqueeze(0).unsqueeze(0)
    accum = torch.zeros_like(vol)
    wsum = torch.zeros_like(vol)

    h2 = h * h + 1e-12
    pad = patch_size // 2

    for dz, dy, dx in _build_offsets(patch_distance):
        shifted = torch.roll(vol, shifts=(dz, dy, dx), dims=(2, 3, 4))
        sq_diff = (vol - shifted) * (vol - shifted)
        patch_dist = F.avg_pool3d(
            sq_diff,
            kernel_size=patch_size,
            stride=1,
            padding=pad,
        )
        w = torch.exp(-patch_dist / h2)
        accum = accum + w * shifted
        wsum = wsum + w

    accum = accum + vol
    wsum = wsum + 1.0

    out = accum / torch.clamp(wsum, min=1e-12)
    return out.squeeze(0).squeeze(0).clamp(0.0, 1.0)


def _iter_non_overlapping_starts(length: int, block: int) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    s = 0
    while s < length:
        e = min(s + block, length)
        spans.append((s, e))
        s = e
    return spans


def _tile_halo(patch_size: int, patch_distance: int) -> int:
    return patch_distance + (patch_size // 2)


def non_local_means_3d_cuda_chunked(
    volume: np.ndarray,
    config: NLMConfig | None = None,
) -> np.ndarray:
    """Denoise a 3D volume using CUDA NLM with mandatory chunked processing.

    :param volume: 3-D numpy array float32 in [0, 1].
    :param config: NLMConfig for search/patch/chunk params.
    :return: 3-D float32 numpy array in [0, 1].
    """
    cfg = config or NLMConfig()

    if not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA device not available. This NLM pipeline requires a real GPU backend (PyTorch CUDA)."
        )

    if volume.ndim != 3:
        raise ValueError(f"Expected 3-D volume, got shape {volume.shape}")

    if cfg.patch_size % 2 == 0:
        raise ValueError("patch_size must be odd")

    vol = np.asarray(volume, dtype=np.float32)
    vol = np.clip(vol, 0.0, 1.0)

    device = torch.device("cuda")

    # Derive h from the full normalized volume for consistency across chunks.
    if cfg.h is None:
        vol_t = torch.from_numpy(vol).to(device=device, dtype=torch.float32)
        sigma = _estimate_sigma_torch(vol_t)
        h = max(0.6 * sigma, 1e-4)
        del vol_t
        torch.cuda.empty_cache()
        print(f"NLM CUDA: estimated sigma={sigma:.6f}, h={h:.6f}")
    else:
        h = float(cfg.h)

    z_max, y_max, x_max = vol.shape
    output = np.empty_like(vol, dtype=np.float32)

    z_spans = _iter_non_overlapping_starts(z_max, cfg.chunk_size)
    y_spans = _iter_non_overlapping_starts(y_max, cfg.chunk_size)
    x_spans = _iter_non_overlapping_starts(x_max, cfg.chunk_size)

    halo = _tile_halo(cfg.patch_size, cfg.patch_distance)
    total_tiles = len(z_spans) * len(y_spans) * len(x_spans)
    tile_idx = 0

    for z0, z1 in z_spans:
        for y0, y1 in y_spans:
            for x0, x1 in x_spans:
                tile_idx += 1
                print(
                    f"NLM CUDA: tile {tile_idx}/{total_tiles} core="
                    f"[{z0}:{z1}, {y0}:{y1}, {x0}:{x1}]"
                )

                pz0 = max(0, z0 - halo)
                pz1 = min(z_max, z1 + halo)
                py0 = max(0, y0 - halo)
                py1 = min(y_max, y1 + halo)
                px0 = max(0, x0 - halo)
                px1 = min(x_max, x1 + halo)

                tile_np = vol[pz0:pz1, py0:py1, px0:px1]
                try:
                    tile_t = torch.from_numpy(tile_np).to(device=device, dtype=torch.float32)
                    den_t = _nlm_single_tile_cuda(
                        tile=tile_t,
                        patch_size=cfg.patch_size,
                        patch_distance=cfg.patch_distance,
                        h=h,
                    )

                    cz0 = z0 - pz0
                    cz1 = cz0 + (z1 - z0)
                    cy0 = y0 - py0
                    cy1 = cy0 + (y1 - y0)
                    cx0 = x0 - px0
                    cx1 = cx0 + (x1 - x0)

                    core = den_t[cz0:cz1, cy0:cy1, cx0:cx1]
                    output[z0:z1, y0:y1, x0:x1] = core.detach().cpu().numpy()

                    del tile_t
                    del den_t
                    del core
                    torch.cuda.empty_cache()
                except RuntimeError as exc:
                    msg = str(exc).lower()
                    if "out of memory" not in msg:
                        raise
                    torch.cuda.empty_cache()
                    raise RuntimeError(
                        "CUDA OOM occurred while processing a tile. "
                        "Reduce NLMConfig.chunk_size and rerun."
                    ) from exc

    return output
