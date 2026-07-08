"""
Extended PSD Pipeline
=====================

Orchestrates the existing PSD/local-thickness pipeline (psd_calculator.py)
together with the new topology/connectivity metrics (topology_metrics.py) on
a single 3-phase (matrix/pore/POM) labeled soil-CT volume, following
Dor et al. (2025), *Agriculture, Ecosystems and Environment* 387, 109633, and
the Stage 1 research decisions in
`analysis/pore_metrics_research/decisions.md`.

This module does NOT replace compute_psd() / compute_local_thickness(); it
calls them and appends new columns/outputs to their results.
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd

try:
    from .psd_calculator import compute_psd
    from .psd_output import psd_to_dataframe
    from .topology_metrics import (
        add_pore_size_bin,
        connectivity_density,
        connectivity_probability,
        degree_of_anisotropy,
        distance_map,
        get_percolating_mask,
        surface_area_by_size_class,
        tortuosity_diffusive,
    )
except ImportError:  # pragma: no cover - fallback for direct script execution
    from psd_calculator import compute_psd
    from psd_output import psd_to_dataframe
    from topology_metrics import (
        add_pore_size_bin,
        connectivity_density,
        connectivity_probability,
        degree_of_anisotropy,
        distance_map,
        get_percolating_mask,
        surface_area_by_size_class,
        tortuosity_diffusive,
    )


def compute_psd_extended(
    volume: np.ndarray,
    voxel_size_um: float,
    pore_label: int = 1,
    pom_label: int = 2,
    matrix_label: int = 0,
    bin_edges_um: Optional[np.ndarray] = None,
    output_dir: Optional[str] = None,
    sample_id: str = "sample",
    n_anisotropy_directions: int = 100,
    use_gpu: bool = False,
    make_plots: bool = True,
    save_distance_maps: bool = True,
) -> Dict[str, Any]:
    """Full extended PSD pipeline for a 3-phase labeled volume.

    Args:
        volume: 3D integer-labeled array. Convention: matrix=matrix_label,
            pore=pore_label, POM(particulate organic matter)=pom_label.
        voxel_size_um: isotropic physical voxel edge length (um).
        pore_label / pom_label / matrix_label: integer label convention.
        bin_edges_um: optional custom PSD bin edges (um); the 30-150 um bin
            (Dor et al. 2025) is always added on top of these.
        output_dir: if given, graphs and distance-map .tif files are written
            here.
        sample_id: identifier used in output filenames / dataframe metadata.
        n_anisotropy_directions: number of MIL sampling directions (D4).
        use_gpu: forwarded to compute_psd()'s EDT/opening computation.
        make_plots: if True, save one PNG per new metric (+ PSD).
        save_distance_maps: if True, save unconditioned + connectivity-
            conditioned distance-to-pore and distance-to-POM maps as .tif.

    Returns:
        Dict with:
            - 'dataframe': extended results table (existing PSD columns +
              new scalar/per-bin columns).
            - 'scalars': dict of the new sample-level scalar metrics.
            - 'distance_maps': dict of the four distance map arrays.
            - 'output_paths': dict of paths written to disk (if any).
    """
    if volume.ndim != 3:
        raise ValueError(f"Expected 3D volume, got shape {volume.shape}")

    voxel_spacing = (float(voxel_size_um),) * 3

    pore_mask = (volume == pore_label)
    pom_mask = (volume == pom_label)

    if not np.any(pore_mask):
        raise ValueError(f"No voxels found with pore_label={pore_label} in volume")

    # ------------------------------------------------------------------
    # Task 2: extend PSD bin edges with the Dor et al. (2025) 30-150 um bin.
    # ------------------------------------------------------------------
    extended_bin_edges_um = add_pore_size_bin(bin_edges_um, low=30.0, high=150.0)

    # ------------------------------------------------------------------
    # Existing PSD pipeline (unchanged) - EDT -> opening map -> binning.
    # ------------------------------------------------------------------
    psd = compute_psd(
        pore_mask,
        voxel_spacing=voxel_spacing,
        bin_edges=extended_bin_edges_um,
        use_gpu=use_gpu,
        use_chunking=False,
    )
    df = psd_to_dataframe(psd)

    diameter_map = psd.get("diameter_map")
    masked_pore_mask = psd.get("masked_pore_mask")
    if masked_pore_mask is None:
        masked_pore_mask = pore_mask

    # ------------------------------------------------------------------
    # New functionality 1: connectivity-conditioned distance maps.
    # ------------------------------------------------------------------
    dist_pore_unconditioned = distance_map(volume, pore_label, voxel_size_um, connected_only=False)
    dist_pore_conditioned = distance_map(volume, pore_label, voxel_size_um, connected_only=True)
    dist_pom_unconditioned = None
    dist_pom_conditioned = None
    if np.any(pom_mask):
        dist_pom_unconditioned = distance_map(volume, pom_label, voxel_size_um, connected_only=False)
        dist_pom_conditioned = distance_map(volume, pom_label, voxel_size_um, connected_only=True)
    else:
        warnings.warn(
            f"No voxels found with pom_label={pom_label}; skipping distance-to-POM maps.",
            UserWarning,
        )

    connected_pore_mask = get_percolating_mask(pore_mask, axis=0)

    # ------------------------------------------------------------------
    # New functionality 3 & 4: Euler/connectivity density and Gamma.
    # ------------------------------------------------------------------
    conn_density = connectivity_density(pore_mask, voxel_size_um)
    gamma = connectivity_probability(pore_mask)

    # ------------------------------------------------------------------
    # New functionality 5: degree of anisotropy (MIL fabric tensor).
    # ------------------------------------------------------------------
    anisotropy_source_mask = connected_pore_mask if np.any(connected_pore_mask) else pore_mask
    anisotropy = degree_of_anisotropy(
        anisotropy_source_mask, voxel_size_um, n_directions=n_anisotropy_directions
    )

    # ------------------------------------------------------------------
    # New functionality 6: diffusive tortuosity (porespy).
    # ------------------------------------------------------------------
    tortuosity = tortuosity_diffusive(pore_mask, axes=(0, 1, 2))

    # ------------------------------------------------------------------
    # New functionality 7: surface area per pore-size class.
    # ------------------------------------------------------------------
    if diameter_map is not None:
        surface_areas = surface_area_by_size_class(
            diameter_map, masked_pore_mask, psd["bin_edges_um"], voxel_size_um
        )
    else:
        surface_areas = np.full(len(psd["bin_edges_um"]) - 1, np.nan)

    # ------------------------------------------------------------------
    # Extra scalar: fraction of pore volume within the Dor et al. 30-150 um bin.
    # ------------------------------------------------------------------
    bin_centers = psd["bin_centers_um"]
    in_30_150 = (bin_centers >= 30.0) & (bin_centers < 150.0)
    if psd["total_pore_voxels"] > 0 and len(psd["volume_counts"]) > 0:
        frac_30_150 = float(psd["volume_counts"][in_30_150].sum() / psd["total_pore_voxels"])
    else:
        frac_30_150 = float("nan")

    scalars: Dict[str, Any] = {
        "sample_id": sample_id,
        "voxel_size_um": voxel_size_um,
        "euler_number": conn_density["euler_number"],
        "connectivity_density_per_mm3": conn_density["connectivity_density_per_mm3"],
        "connectivity_probability_gamma": gamma,
        "degree_of_anisotropy": anisotropy["degree_of_anisotropy"],
        "psd_30_150um_volume_fraction": frac_30_150,
        **tortuosity,
    }

    # ------------------------------------------------------------------
    # Append new columns to the EXISTING results table (not a new table).
    # ------------------------------------------------------------------
    df = df.copy()
    df["Surface_Area_um2"] = surface_areas
    for key, value in scalars.items():
        if key == "sample_id":
            df["sample_id"] = value
        else:
            df[key] = value  # broadcast sample-level scalar across all bin rows

    df.attrs.update(scalars)
    df.attrs["anisotropy_eigenvalues"] = anisotropy["eigenvalues"]
    df.attrs["fabric_tensor"] = anisotropy["fabric_tensor"]

    distance_maps = {
        "distance_to_pore_unconditioned": dist_pore_unconditioned,
        "distance_to_pore_connected": dist_pore_conditioned,
        "distance_to_pom_unconditioned": dist_pom_unconditioned,
        "distance_to_pom_connected": dist_pom_conditioned,
    }

    output_paths: Dict[str, str] = {}
    if output_dir is not None:
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        table_path = out_dir / f"{sample_id}_extended_psd.csv"
        df.to_csv(table_path, index=False, float_format="%.6f")
        output_paths["extended_table_csv"] = str(table_path)

        if save_distance_maps:
            output_paths.update(
                _save_distance_maps(distance_maps, out_dir, sample_id)
            )

        if make_plots:
            output_paths.update(
                _make_plots(df, psd, scalars, surface_areas, out_dir, sample_id)
            )

    return {
        "dataframe": df,
        "scalars": scalars,
        "distance_maps": distance_maps,
        "output_paths": output_paths,
        "psd": psd,
    }


def _save_distance_maps(
    distance_maps: Dict[str, Optional[np.ndarray]],
    out_dir: Path,
    sample_id: str,
) -> Dict[str, str]:
    """Write each distance map (3D volume + representative 2D mid-slice) to
    .tif, per the 'Output requirements' section of the Stage 2 prompt."""
    try:
        import tifffile
    except ImportError:
        warnings.warn(
            "tifffile is not installed; distance maps will not be saved to disk.",
            UserWarning,
        )
        return {}

    paths: Dict[str, str] = {}
    for name, dmap in distance_maps.items():
        if dmap is None:
            continue
        finite = np.where(np.isfinite(dmap), dmap, 0.0).astype(np.float32)

        vol_path = out_dir / f"{sample_id}_{name}.tif"
        tifffile.imwrite(str(vol_path), finite)
        paths[f"{name}_tif"] = str(vol_path)

        mid_z = finite.shape[0] // 2
        slice_path = out_dir / f"{sample_id}_{name}_midslice.tif"
        tifffile.imwrite(str(slice_path), finite[mid_z])
        paths[f"{name}_midslice_tif"] = str(slice_path)

    return paths


def _make_plots(
    df: pd.DataFrame,
    psd: Dict[str, Any],
    scalars: Dict[str, Any],
    surface_areas: np.ndarray,
    out_dir: Path,
    sample_id: str,
) -> Dict[str, str]:
    """One matplotlib PNG per new metric (+ PSD), consistent in style with
    Dor et al. (2025) Figs. 2-4 / S2-S5 (bar charts with error bars would be
    used across replicates; for a single sample, values are plotted as single
    bars so the multi-sample/batch case is a drop-in extension)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    paths: Dict[str, str] = {}

    # --- PSD (differential), highlighting the 30-150 um bin ------------
    fig, ax = plt.subplots(figsize=(7, 5))
    diam = psd["bin_centers_um"]
    diff = psd["differential_volume"]
    if len(diam) > 0:
        colors = np.where((diam >= 30.0) & (diam < 150.0), "tab:orange", "tab:blue")
        ax.bar(diam, diff, width=np.gradient(diam) if len(diam) > 1 else diam, color=colors)
        ax.set_xscale("log")
    ax.set_xlabel("Pore diameter (um)")
    ax.set_ylabel("dV/dd (um^-1)")
    ax.set_title(f"{sample_id}: Pore Size Distribution (30-150um bin highlighted)")
    fig.tight_layout()
    p = out_dir / f"{sample_id}_psd.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    paths["plot_psd"] = str(p)

    # --- Scalar connectivity/topology metrics (bar chart) ---------------
    fig, ax = plt.subplots(figsize=(7, 5))
    metric_names = [
        "connectivity_density_per_mm3",
        "connectivity_probability_gamma",
        "degree_of_anisotropy",
    ]
    values = [scalars.get(m, np.nan) for m in metric_names]
    ax.bar(metric_names, values, color="tab:green")
    ax.set_ylabel("Value")
    ax.set_title(f"{sample_id}: Connectivity / Topology metrics")
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    fig.tight_layout()
    p = out_dir / f"{sample_id}_connectivity_metrics.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    paths["plot_connectivity"] = str(p)

    # --- Tortuosity per axis --------------------------------------------
    fig, ax = plt.subplots(figsize=(6, 5))
    tort_keys = [k for k in scalars if k.startswith("tortuosity_axis")]
    tort_vals = [scalars[k] for k in tort_keys]
    ax.bar(tort_keys, tort_vals, color="tab:purple")
    ax.set_ylabel("Diffusive tortuosity (tau_d)")
    ax.set_title(f"{sample_id}: Tortuosity by axis")
    fig.tight_layout()
    p = out_dir / f"{sample_id}_tortuosity.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    paths["plot_tortuosity"] = str(p)

    # --- Surface area by pore-size class ---------------------------------
    fig, ax = plt.subplots(figsize=(7, 5))
    bin_centers = psd["bin_centers_um"]
    if len(bin_centers) == len(surface_areas):
        ax.bar(bin_centers, surface_areas, width=np.gradient(bin_centers) if len(bin_centers) > 1 else bin_centers, color="tab:red")
        ax.set_xscale("log")
    ax.set_xlabel("Pore diameter (um)")
    ax.set_ylabel("Surface area (um^2)")
    ax.set_title(f"{sample_id}: Surface area by pore-size class")
    fig.tight_layout()
    p = out_dir / f"{sample_id}_surface_area_by_class.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    paths["plot_surface_area"] = str(p)

    return paths
