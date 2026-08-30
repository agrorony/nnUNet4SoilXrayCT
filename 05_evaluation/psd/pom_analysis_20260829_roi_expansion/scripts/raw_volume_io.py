"""Shared helpers for reading raw (post-reconstruction, pre-crop) slice
stacks for the ROI-expansion prompt. Kept in one place so Part 1's slice
listing logic and Part 2's shell-scan / crop-export logic can't drift apart.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List

import numpy as np
import tifffile

REC_PATTERN = re.compile(r"_rec(\d+)\.tif$", re.IGNORECASE)


def list_zslices(slice_dir: Path) -> List[Path]:
    """Return the reconstructed cross-section slice files, Z-ordered.

    Handles the Bnei Re'em raw folder, which mixes raw radiographic
    projection images (plain sequential naming) in with the actual
    reconstructed slices ("*_rec#####.tif") at a different resolution --
    only the "_rec" files are real cross-sections there. Mishmar raw
    folders contain only "slice#####.tif" reconstructed slices already, so
    the plain-name fallback covers them.
    """
    all_files = sorted(slice_dir.glob("*.tif"))
    rec_files = [f for f in all_files if REC_PATTERN.search(f.name)]
    if rec_files:
        rec_files.sort(key=lambda f: int(REC_PATTERN.search(f.name).group(1)))
        return rec_files
    return all_files


def center_range(n: int, size: int) -> tuple[int, int]:
    start = (n // 2) - (size // 2)
    return start, start + size


def read_centered_cube(slice_dir: Path, size: int) -> np.ndarray:
    """Read a symmetric, center-aligned cubic crop of edge length `size`
    directly from the raw slice stack into memory as a single array."""
    files = list_zslices(slice_dir)
    n_z = len(files)
    z0, z1 = center_range(n_z, size)
    if z0 < 0 or z1 > n_z:
        raise ValueError(f"crop size {size} exceeds Z extent {n_z} in {slice_dir}")

    first = tifffile.imread(str(files[z0]))
    h, w = first.shape[:2]
    y0, y1 = center_range(h, size)
    x0, x1 = center_range(w, size)
    if y0 < 0 or y1 > h or x0 < 0 or x1 > w:
        raise ValueError(f"crop size {size} exceeds XY extent {(h, w)} in {slice_dir}")

    out = np.empty((size, size, size), dtype=first.dtype)
    out[0] = first[y0:y1, x0:x1]
    for i in range(1, size):
        img = tifffile.imread(str(files[z0 + i]))
        out[i] = img[y0:y1, x0:x1]
    return out
