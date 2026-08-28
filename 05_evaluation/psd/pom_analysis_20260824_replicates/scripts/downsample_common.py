"""Shared block-reduce downsampling helpers for the Mishmar 5.85um -> ~15um
computational ablation (mishmar_downsample_ablation_prompt.md).

The 5.85um -> 15.000149um factor (2.5641...) is not an integer, so a plain
reshape-into-blocks approach doesn't work. Instead we partition each axis
into M non-overlapping blocks of *nearly* equal size (2 or 3 input voxels
each, averaging 2.5641) using rounded linspace edges -- a standard
generalized block-reduce for non-integer downsample factors. Because the
partition is a Cartesian grid of axis-aligned blocks, both majority-vote
(label downsample) and mean (image downsample) are separable and can be
computed with three sequential 1D reductions (np.add.reduceat per axis)
instead of materializing the full (N,N,N) block-id array -- keeps peak
memory to a couple of GB instead of tens of GB for a 1000^3 volume.
"""
from __future__ import annotations

import numpy as np


def compute_block_edges(n: int, target_voxel_um: float, source_voxel_um: float) -> np.ndarray:
    """Return M+1 integer edges partitioning [0, n) into M blocks whose mean
    size is as close as possible to target_voxel_um / source_voxel_um."""
    factor = target_voxel_um / source_voxel_um
    m = int(round(n / factor))
    edges = np.round(np.linspace(0, n, m + 1)).astype(np.int64)
    assert edges[0] == 0 and edges[-1] == n
    assert np.all(np.diff(edges) >= 1), "degenerate block (zero-width) -- factor too aggressive for this n"
    return edges


def achieved_voxel_um(n: int, edges: np.ndarray, source_voxel_um: float) -> float:
    m = len(edges) - 1
    return float(source_voxel_um * n / m)


def block_reduce_sum_3d(arr: np.ndarray, edges: np.ndarray, out_dtype) -> np.ndarray:
    """Separable block-sum over a 3D array using the same edge partition on
    all three axes (only valid when all three axes share the same length,
    true here since inputs are cropped cubes)."""
    starts = edges[:-1]
    a = np.add.reduceat(arr.astype(out_dtype), starts, axis=0)
    a = np.add.reduceat(a, starts, axis=1)
    a = np.add.reduceat(a, starts, axis=2)
    return a


def block_majority_labels(vol: np.ndarray, edges: np.ndarray, label_values) -> np.ndarray:
    """Per-block majority vote over a small categorical alphabet. Vectorized
    as: for each label value, block-sum its indicator array (separable,
    see block_reduce_sum_3d), then argmax across labels per block."""
    m = len(edges) - 1
    label_values = list(label_values)
    stacked = np.empty((len(label_values), m, m, m), dtype=np.uint16)
    for i, lv in enumerate(label_values):
        indicator = (vol == lv)
        stacked[i] = block_reduce_sum_3d(indicator, edges, np.uint16)
    idx = np.argmax(stacked, axis=0)
    lut = np.array(label_values, dtype=vol.dtype)
    return lut[idx]


def block_mean_image(vol: np.ndarray, edges: np.ndarray) -> np.ndarray:
    """Anti-aliased block-average downsample of a continuous-valued image."""
    sizes = np.diff(edges).astype(np.float64)
    block_vol = sizes[:, None, None] * sizes[None, :, None] * sizes[None, None, :]
    s = block_reduce_sum_3d(vol, edges, np.float64)
    return (s / block_vol).astype(np.float32)
