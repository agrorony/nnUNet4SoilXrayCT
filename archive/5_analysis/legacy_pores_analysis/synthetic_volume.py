"""Synthetic binary pore volume generator for controlled PSD tests."""

from __future__ import annotations

import warnings
from typing import Callable, Optional, Tuple
import numpy as np

RadiusSampler = Callable[[np.random.Generator], float]


def generate_non_overlapping_spheres(
    volume_shape: Tuple[int, int, int],
    voxel_spacing: Tuple[float, float, float] = (1.0, 1.0, 1.0),
    n_spheres: int = 40,
    min_radius_um: float = 5.0,
    max_radius_um: Optional[float] = None,
    radius_sampler: Optional[RadiusSampler] = None,
    seed: Optional[int] = None,
    max_attempts: int = 6000
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Create a binary volume populated with non-overlapping spheres.

    The radius sampler defaults to a log-normal distribution so the ground truth
    PSD is smooth and continuous in physical units. Spheres are placed using
    physical coordinates to honor anisotropic voxel spacing.

    Args:
        volume_shape: Volume dimensions (Z, Y, X) in voxels.
        voxel_spacing: Physical voxel dimensions (dz, dy, dx) in micrometers.
        n_spheres: Target number of spheres to place.
        min_radius_um: Minimum physical radius for each sphere.
        max_radius_um: Maximum physical radius. Defaults to one third of the
            smallest physical dimension.
        radius_sampler: Callable receiving a random generator and returning a
            radius in micrometers.
        seed: Optional RNG seed for reproducible volumes.
        max_attempts: Maximum placement attempts before giving up.

    Returns:
        Tuple containing the binary volume, the radii (μm) used, and the
        corresponding centers (μm).
    """
    rng = np.random.default_rng(seed)
    volume_shape = tuple(int(dim) for dim in volume_shape)
    spacing = np.array(voxel_spacing, dtype=float)

    physical_extents = np.array(volume_shape, dtype=float) * spacing
    default_max_radius = float(np.min(physical_extents) / 3.0)
    max_radius = float(max_radius_um) if max_radius_um is not None else default_max_radius
    if max_radius <= min_radius_um:
        raise ValueError("max_radius_um must be larger than min_radius_um")

    def _sample_radius() -> float:
        if radius_sampler is None:
            value = float(rng.lognormal(mean=np.log(6.0), sigma=0.35))
        else:
            value = float(radius_sampler(rng))
        return float(np.clip(value, min_radius_um, max_radius))

    def _sample_center(radius: float) -> np.ndarray:
        coords = []
        for extent, dim in zip(physical_extents, spacing):
            min_bound = radius
            max_bound = extent - radius
            if max_bound <= min_bound:
                return np.array([])
            coords.append(rng.uniform(min_bound, max_bound))
        return np.array(coords, dtype=float)

    placed_centers: list[np.ndarray] = []
    placed_radii: list[float] = []
    attempts = 0

    while len(placed_centers) < n_spheres and attempts < max_attempts:
        attempts += 1
        radius = _sample_radius()
        center = _sample_center(radius)
        if center.size == 0:
            continue

        overlap = False
        for other_center, other_radius in zip(placed_centers, placed_radii):
            distance = np.linalg.norm(center - other_center)
            if distance < (radius + other_radius):
                overlap = True
                break
        if overlap:
            continue

        placed_centers.append(center)
        placed_radii.append(radius)

    if len(placed_centers) < n_spheres:
        warnings.warn(
            f"Only placed {len(placed_centers)} spheres out of requested {n_spheres}",
            UserWarning
        )

    volume = np.zeros(volume_shape, dtype=bool)
    centers_array = np.array(placed_centers, dtype=float) if placed_centers else np.zeros((0, 3))
    radii_array = np.array(placed_radii, dtype=float)

    for center, radius in zip(centers_array, radii_array):
        z_phys, y_phys, x_phys = center
        r = radius
        z_min = max(0, int(np.floor((z_phys - r) / spacing[0])))
        z_max = min(volume_shape[0], int(np.ceil((z_phys + r) / spacing[0])))
        y_min = max(0, int(np.floor((y_phys - r) / spacing[1])))
        y_max = min(volume_shape[1], int(np.ceil((y_phys + r) / spacing[1])))
        x_min = max(0, int(np.floor((x_phys - r) / spacing[2])))
        x_max = min(volume_shape[2], int(np.ceil((x_phys + r) / spacing[2])))

        if z_min >= z_max or y_min >= y_max or x_min >= x_max:
            continue

        z_lin = (np.arange(z_min, z_max) + 0.5) * spacing[0]
        y_lin = (np.arange(y_min, y_max) + 0.5) * spacing[1]
        x_lin = (np.arange(x_min, x_max) + 0.5) * spacing[2]

        dz2 = (z_lin[:, None, None] - z_phys) ** 2
        dy2 = (y_lin[None, :, None] - y_phys) ** 2
        dx2 = (x_lin[None, None, :] - x_phys) ** 2
        mask = (dz2 + dy2 + dx2) <= (r ** 2)

        volume[z_min:z_max, y_min:y_max, x_min:x_max] |= mask

    return volume, radii_array, centers_array
