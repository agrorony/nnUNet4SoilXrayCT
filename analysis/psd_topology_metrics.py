"""Topology & Connectivity Metrics Extension for PSD diagnostics.
=================================================================

Extends `analysis/psd_diagnostics_core.py` (the live, maintained PSD
implementation) with connectivity-conditioned distance maps, Euler
characteristic / connectivity density, connectivity probability (Gamma),
degree of anisotropy (MIL fabric tensor), diffusive tortuosity, and
per-pore-size-class surface area.

All research decisions implemented here are resolved in
`analysis/pore_metrics_research/decisions.md` (Stage 1, D1-D5). See that
file for full justification/citations and confidence flags.

This is a corrected-target re-implementation. An earlier agent run ported
this same functionality into `legacy/pores_analysis/topology_metrics.py`,
which extends dead code (`legacy/pores_analysis/psd_calculator.py`) that
nothing in the live pipeline imports. This module is functionally
equivalent (same algorithms, same decisions.md specs) but lives alongside,
and is designed to be called from, the actually-used
`analysis/psd_diagnostics_core.py` / `analysis/run_psd_diagnostics.py`.

This module does NOT replace or duplicate the existing PSD/local-thickness
pipeline; it only adds new analyses that consume its outputs (pore masks,
diameter maps) or run alongside it. It depends only on numpy/scipy/skimage
(and, lazily, porespy for tortuosity) — no dependency on legacy/pores_analysis.
"""

from __future__ import annotations

import warnings
from typing import Dict, Optional, Sequence, Tuple

import numpy as np
from scipy.ndimage import distance_transform_edt, map_coordinates
from skimage.measure import label as sk_label
from skimage.measure import euler_number as sk_euler_number
from skimage.measure import marching_cubes, mesh_surface_area


# ---------------------------------------------------------------------------
# D1 - Connected / percolating pore definition
# ---------------------------------------------------------------------------

def get_percolating_mask(
    phase_mask: np.ndarray,
    axis: int = 0,
    connectivity: int = 3,
) -> np.ndarray:
    """Return the subset of ``phase_mask`` that percolates across the volume
    along ``axis`` (default: Z), per decisions.md D1.

    Definition (Jarvis, Larsbo & Koestel, 2017): a voxel is "connected" if it
    belongs to a 26-connected (connectivity=3) 3D component that touches both
    faces perpendicular to ``axis``.

    Args:
        phase_mask: boolean 3D array (True = phase of interest, e.g. pore or POM).
        axis: axis along which percolation is required (0=Z, 1=Y, 2=X).
        connectivity: skimage labeling connectivity (3 = 26-connectivity in 3D).

    Returns:
        Boolean array, same shape as ``phase_mask``, True only for voxels
        belonging to a component that spans both faces along ``axis``.
    """
    if phase_mask.ndim != 3:
        raise ValueError(f"Expected 3D mask, got shape {phase_mask.shape}")
    if not np.any(phase_mask):
        return np.zeros_like(phase_mask, dtype=bool)

    labels = sk_label(phase_mask, connectivity=connectivity)

    first_slc = [slice(None)] * 3
    first_slc[axis] = 0
    last_slc = [slice(None)] * 3
    last_slc[axis] = -1

    top_labels = set(np.unique(labels[tuple(first_slc)])) - {0}
    bottom_labels = set(np.unique(labels[tuple(last_slc)])) - {0}
    percolating_labels = top_labels & bottom_labels

    if not percolating_labels:
        return np.zeros_like(phase_mask, dtype=bool)

    return np.isin(labels, list(percolating_labels))


# ---------------------------------------------------------------------------
# New functionality 1 - Connectivity-conditioned distance maps
# ---------------------------------------------------------------------------

def distance_map_from_mask(
    target_mask: np.ndarray,
    voxel_size_um: float,
    connected_only: bool = False,
    axis: int = 0,
) -> np.ndarray:
    """Euclidean distance transform (in physical units, um) to the nearest
    True voxel of ``target_mask``, optionally restricted to the
    connectivity-conditioned (percolating) subset per D1.

    Args:
        target_mask: boolean 3D array, True = phase of interest.
        voxel_size_um: isotropic physical voxel edge length (um).
        connected_only: if True, use only the percolating subset of
            ``target_mask`` (D1) as the foreground for the distance
            transform; if False, use the full (unconditioned) mask.
        axis: percolation axis used when connected_only=True (default Z).

    Returns:
        Float32 array, same shape as ``target_mask``, distance in um from
        every voxel to the nearest qualifying target voxel (0 at target
        voxels themselves).
    """
    mask = target_mask
    if connected_only:
        mask = get_percolating_mask(mask, axis=axis)

    if not np.any(mask):
        warnings.warn(
            f"No voxels found for target mask (connected_only={connected_only}); "
            "returning all-inf distance map.",
            UserWarning,
        )
        return np.full(target_mask.shape, np.inf, dtype=np.float32)

    # distance_transform_edt(input): for each nonzero (foreground) voxel of
    # `input`, computes distance to nearest zero-valued voxel. Passing
    # ~mask makes non-target voxels foreground, and their distance is
    # computed to the nearest target (True) voxel, which is what we want.
    dmap = distance_transform_edt(~mask, sampling=(voxel_size_um,) * 3)
    return dmap.astype(np.float32)


def distance_map(
    volume: np.ndarray,
    target_label: int,
    voxel_size_um: float,
    connected_only: bool = False,
    axis: int = 0,
) -> np.ndarray:
    """Same as ``distance_map_from_mask`` but takes an integer-labeled
    ``volume`` + ``target_label`` instead of a pre-computed boolean mask."""
    target_mask = (volume == target_label)
    return distance_map_from_mask(
        target_mask, voxel_size_um, connected_only=connected_only, axis=axis
    )


# ---------------------------------------------------------------------------
# New functionality 3 - Euler characteristic / connectivity density
# ---------------------------------------------------------------------------

def connectivity_density(
    pore_mask: np.ndarray,
    voxel_size_um: float,
    connectivity: int = 3,
) -> Dict[str, float]:
    """Euler characteristic and sign-flipped, volume-normalized connectivity
    density of the pore phase, per decisions.md D2.

    Returns a dict with:
        - 'euler_number': raw chi = b0 - b1 + b2 (skimage convention, same
          alternating-sum convention as Renard & Allard 2013 / Herring et
          al. 2015).
        - 'connectivity_density_per_mm3': -euler_number / sample_volume_mm3,
          sign-flipped so that HIGHER values = MORE connected (per Herring
          et al. 2015's established sign convention), normalized by total
          sample volume in mm^3 (voxel_size_um used, not raw voxel counts).
    """
    euler = int(sk_euler_number(pore_mask, connectivity=connectivity))
    n_voxels_total = pore_mask.size
    sample_volume_mm3 = n_voxels_total * (voxel_size_um / 1000.0) ** 3
    if sample_volume_mm3 <= 0:
        conn_density = np.nan
    else:
        conn_density = -euler / sample_volume_mm3
    return {
        "euler_number": euler,
        "connectivity_density_per_mm3": float(conn_density),
    }


# ---------------------------------------------------------------------------
# New functionality 4 - Connectivity probability (Gamma)
# ---------------------------------------------------------------------------

def connectivity_probability(
    pore_mask: np.ndarray,
    connectivity: int = 3,
) -> float:
    """Connectivity probability Gamma (Jarvis, Larsbo & Koestel, 2017, Eq.1),
    per decisions.md D3: the probability that two randomly chosen pore voxels
    belong to the same (26-connected) cluster.

    Gamma = sum_i[s_i*(s_i-1)] / [(sum_i s_i)*(sum_i s_i - 1)]
    """
    if not np.any(pore_mask):
        return float("nan")

    labels = sk_label(pore_mask, connectivity=connectivity)
    sizes = np.bincount(labels.ravel())
    sizes = sizes[1:]  # drop background (label 0)
    sizes = sizes[sizes > 0]

    total = sizes.sum()
    if total < 2:
        return float("nan")

    numerator = np.sum(sizes.astype(np.float64) * (sizes.astype(np.float64) - 1))
    denominator = total.astype(np.float64) * (total.astype(np.float64) - 1)
    return float(numerator / denominator)


# ---------------------------------------------------------------------------
# New functionality 5 - Degree of anisotropy (MIL / fabric tensor)
# ---------------------------------------------------------------------------

def _fibonacci_hemisphere_directions(n_directions: int) -> np.ndarray:
    """Generate n_directions roughly-uniformly-distributed unit vectors on a
    hemisphere using a Fibonacci-sphere sampling scheme."""
    indices = np.arange(0, n_directions, dtype=np.float64) + 0.5
    phi = np.arccos(1 - indices / n_directions)  # polar angle in [0, pi/2] (hemisphere)
    golden_angle = np.pi * (1 + 5 ** 0.5)
    theta = golden_angle * indices

    x = np.sin(phi) * np.cos(theta)
    y = np.sin(phi) * np.sin(theta)
    z = np.cos(phi)
    directions = np.stack([z, y, x], axis=1)  # (Z, Y, X) order to match volume axes
    norms = np.linalg.norm(directions, axis=1, keepdims=True)
    return directions / norms


def _mean_intercept_length(
    mask: np.ndarray,
    direction: np.ndarray,
    voxel_size_um: float,
    n_lines: int = 400,
    rng: Optional[np.random.Generator] = None,
) -> float:
    """Estimate MIL(direction) = total line length / number of interface
    crossings, per Odgaard (1997) Eq.6, using vectorized ray sampling
    (map_coordinates) rather than rotating the whole volume."""
    if rng is None:
        rng = np.random.default_rng(0)

    shape = np.array(mask.shape, dtype=np.float64)
    diag_len = np.linalg.norm(shape)
    step = 1.0  # voxel-index-space step; volume assumed isotropic
    n_steps = int(np.ceil(diag_len / step)) + 2

    center = shape / 2.0
    # Two vectors orthogonal to `direction`, spanning the sampling plane.
    arbitrary = np.array([1.0, 0.0, 0.0])
    if np.allclose(np.abs(direction), arbitrary, atol=1e-6):
        arbitrary = np.array([0.0, 1.0, 0.0])
    u = np.cross(direction, arbitrary)
    u /= np.linalg.norm(u)
    v = np.cross(direction, u)
    v /= np.linalg.norm(v)

    # Sample start offsets on the (u, v) plane, scaled to comfortably cover
    # the volume's bounding sphere.
    max_offset = diag_len / 2.0
    offsets_u = rng.uniform(-max_offset, max_offset, size=n_lines)
    offsets_v = rng.uniform(-max_offset, max_offset, size=n_lines)

    starts = center[None, :] + offsets_u[:, None] * u[None, :] + offsets_v[:, None] * v[None, :]
    starts = starts - (n_steps / 2.0) * step * direction[None, :]

    t = np.arange(n_steps, dtype=np.float64) * step
    # coords shape: (n_lines, n_steps, 3)
    coords = starts[:, None, :] + t[None, :, None] * direction[None, None, :]

    z = coords[..., 0].ravel()
    y = coords[..., 1].ravel()
    x = coords[..., 2].ravel()

    in_bounds = (
        (z >= 0) & (z <= shape[0] - 1) &
        (y >= 0) & (y <= shape[1] - 1) &
        (x >= 0) & (x <= shape[2] - 1)
    )

    samples = np.zeros(z.shape, dtype=np.uint8)
    if np.any(in_bounds):
        sampled = map_coordinates(
            mask.astype(np.uint8),
            [z[in_bounds], y[in_bounds], x[in_bounds]],
            order=0,
            mode="constant",
            cval=0,
        )
        samples[in_bounds] = sampled

    samples = samples.reshape(n_lines, n_steps)
    valid = in_bounds.reshape(n_lines, n_steps)

    # Count interface crossings only where both neighboring samples are valid.
    both_valid = valid[:, :-1] & valid[:, 1:]
    transitions = (samples[:, :-1] != samples[:, 1:]) & both_valid
    n_intersections = int(transitions.sum())
    total_line_length_um = float(both_valid.sum()) * step * voxel_size_um

    if n_intersections == 0:
        return float("nan")
    return total_line_length_um / n_intersections


def degree_of_anisotropy(
    pore_mask: np.ndarray,
    voxel_size_um: float,
    n_directions: int = 100,
    n_lines_per_direction: int = 400,
    seed: int = 0,
) -> Dict[str, object]:
    """Degree of anisotropy via the mean-intercept-length (MIL) fabric-tensor
    method (Odgaard, 1997; Harrigan & Mann, 1984), per decisions.md D4.

    No existing Python/porespy implementation was found - this is written
    from scratch: sample directions -> per-direction MIL -> least-squares
    fabric tensor fit -> eigen-decomposition -> DA = 1 - lambda_min/lambda_max.

    Returns dict with 'degree_of_anisotropy' (0=isotropic, 1=max anisotropic),
    'eigenvalues' (sorted descending), and 'fabric_tensor'.
    """
    if not np.any(pore_mask):
        return {
            "degree_of_anisotropy": float("nan"),
            "eigenvalues": [float("nan")] * 3,
            "fabric_tensor": np.full((3, 3), np.nan).tolist(),
        }

    rng = np.random.default_rng(seed)
    directions = _fibonacci_hemisphere_directions(n_directions)

    mil_values = np.empty(n_directions, dtype=np.float64)
    for i, d in enumerate(directions):
        mil_values[i] = _mean_intercept_length(
            pore_mask, d, voxel_size_um, n_lines=n_lines_per_direction, rng=rng
        )

    valid = np.isfinite(mil_values) & (mil_values > 0)
    if valid.sum() < 6:
        warnings.warn(
            "Too few valid MIL samples to fit a fabric tensor reliably.",
            UserWarning,
        )
        return {
            "degree_of_anisotropy": float("nan"),
            "eigenvalues": [float("nan")] * 3,
            "fabric_tensor": np.full((3, 3), np.nan).tolist(),
        }

    directions_v = directions[valid]
    mil_v = mil_values[valid]
    # Polar plot of 1/MIL^2 approximates the ellipsoid quadratic form
    # omega^T M omega (Whitehouse 1974 / Odgaard 1997).
    r = 1.0 / (mil_v ** 2)

    dz, dy, dx = directions_v[:, 0], directions_v[:, 1], directions_v[:, 2]
    # Design matrix for the 6 independent entries of a symmetric 3x3 tensor.
    design = np.stack(
        [dz * dz, dy * dy, dx * dx, 2 * dz * dy, 2 * dz * dx, 2 * dy * dx],
        axis=1,
    )
    coeffs, *_ = np.linalg.lstsq(design, r, rcond=None)
    Mzz, Myy, Mxx, Mzy, Mzx, Myx = coeffs
    M = np.array(
        [
            [Mzz, Mzy, Mzx],
            [Mzy, Myy, Myx],
            [Mzx, Myx, Mxx],
        ]
    )

    eigvals = np.linalg.eigvalsh(M)
    eigvals = np.sort(eigvals)[::-1]  # descending
    eigvals_clipped = np.clip(eigvals, a_min=1e-12, a_max=None)
    lambda_max, lambda_min = eigvals_clipped[0], eigvals_clipped[-1]
    da = 1.0 - (lambda_min / lambda_max) if lambda_max > 0 else float("nan")

    return {
        "degree_of_anisotropy": float(da),
        "eigenvalues": eigvals.tolist(),
        "fabric_tensor": M.tolist(),
    }


# ---------------------------------------------------------------------------
# New functionality 6 - Tortuosity (diffusive, via porespy)
# ---------------------------------------------------------------------------

def tortuosity_diffusive(
    pore_mask: np.ndarray,
    axes: Sequence[int] = (0, 1, 2),
) -> Dict[str, float]:
    """Diffusive tortuosity (Ghanbarian et al., 2013, tau_d = (<L_d>/L_s)^2)
    computed via porespy.simulations.tortuosity_fd, per decisions.md D5.

    tortuosity_fd internally trims non-percolating paths along the requested
    axis (it derives its own connectivity-conditioned subset), so the raw
    boolean pore mask is passed directly.

    NOTE: as of porespy==3.0.4, tortuosity_fd requires the optional
    `openpnm` package (imported lazily inside porespy itself) to build/solve
    the diffusion network; if it is missing, results are NaN with a warning
    rather than a hard failure.

    Returns dict {'tortuosity_axis0': ..., 'tortuosity_axis1': ..., ...}
    with NaN for axes that fail (e.g. no percolating path / singular solve).
    """
    try:
        import porespy
    except ImportError:
        warnings.warn(
            "porespy is not installed; tortuosity cannot be computed. "
            "Add 'porespy' to the environment.",
            UserWarning,
        )
        return {f"tortuosity_axis{ax}": float("nan") for ax in axes}

    results: Dict[str, float] = {}
    for ax in axes:
        try:
            res = porespy.simulations.tortuosity_fd(im=pore_mask, axis=ax)
            results[f"tortuosity_axis{ax}"] = float(res.tortuosity)
        except Exception as exc:  # pragma: no cover - defensive: solver can fail on tiny/disconnected volumes
            warnings.warn(f"tortuosity_fd failed for axis={ax}: {exc}", UserWarning)
            results[f"tortuosity_axis{ax}"] = float("nan")
    return results


# ---------------------------------------------------------------------------
# New functionality 2 - Add 30-150 um pore-size bin
# ---------------------------------------------------------------------------

def add_pore_size_bin(
    bin_edges_um: Optional[np.ndarray],
    low: float = 30.0,
    high: float = 150.0,
    default_min: float = 2.0,
    default_max: float = 1000.0,
    n_default_bins: int = 30,
) -> np.ndarray:
    """Ensure ``low`` and ``high`` (default 30-150 um, matching Dor et al.
    2025) are present as bin edges, alongside whatever bins already exist.

    If bin_edges_um is None, a default log-spaced bin set is generated first.
    """
    if bin_edges_um is None:
        bin_edges_um = np.logspace(np.log10(default_min), np.log10(default_max), n_default_bins + 1)
    else:
        bin_edges_um = np.asarray(bin_edges_um, dtype=np.float64)

    merged = np.union1d(bin_edges_um, np.array([low, high], dtype=np.float64))
    return np.sort(merged).astype(np.float32)


# ---------------------------------------------------------------------------
# New functionality 7 - Surface area by pore-size class
# ---------------------------------------------------------------------------

def surface_area_by_size_class(
    diameter_map: np.ndarray,
    pore_mask: np.ndarray,
    bin_edges_um: np.ndarray,
    voxel_size_um: float,
) -> np.ndarray:
    """Surface area (um^2) of the pore/solid interface, computed separately
    per pore-diameter size class (extends the existing whole-image
    marching-cubes surface-area calculation to be per-bin).

    For each bin [edge_i, edge_i+1), the pore mask is restricted to voxels
    whose local-thickness diameter falls in that range, then marching_cubes
    + mesh_surface_area is run on that masked subset.

    Returns an array of length len(bin_edges_um)-1 (NaN where a bin has too
    few voxels to mesh).
    """
    n_bins = len(bin_edges_um) - 1
    areas = np.full(n_bins, np.nan, dtype=np.float64)
    spacing = (voxel_size_um,) * 3

    for i in range(n_bins):
        lo, hi = bin_edges_um[i], bin_edges_um[i + 1]
        class_mask = pore_mask & (diameter_map >= lo) & (diameter_map < hi)
        n_voxels = int(class_mask.sum())
        if n_voxels < 8:  # too small to mesh meaningfully
            continue
        # Pad by 1 voxel so surfaces at the array boundary are closed.
        padded = np.pad(class_mask, 1, mode="constant", constant_values=False)
        try:
            verts, faces, _, _ = marching_cubes(
                padded.astype(np.float32), level=0.5, spacing=spacing
            )
            areas[i] = mesh_surface_area(verts, faces)
        except (ValueError, RuntimeError) as exc:
            warnings.warn(f"marching_cubes failed for bin [{lo:.1f},{hi:.1f}) um: {exc}", UserWarning)
            areas[i] = np.nan

    return areas
