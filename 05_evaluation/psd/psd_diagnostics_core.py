"""PSD diagnostics core — reusable compute and diagnostics module.

Public API
----------
run_psd_pipeline(volume, voxel_spacing, *, ...)  ->  dict
to_json_serializable(obj)  ->  JSON-native Python object
build_psd_table(result)  ->  list[dict]  (CSV rows, §4.6 columns)
build_summary(result, *, mode, run_name)  ->  dict  (§4.7 fields)

No CLI logic, no implicit paths, no global state.
All algorithmic behavior is preserved from legacy/pores_analysis.
"""

# =============================================================================
# Runtime dependencies and version constraints
# =============================================================================
# Package        Constraint               Reason
# -------------- ------------------------ ------------------------------------
# numpy          >= 1.22, <= 2.3          numba 0.63.x hard upper-bound;
#                                         pip install "numpy<2.4" to pin
# porespy        >= 3.0.4                 local_thickness(method='imj')
#                                         (BoneJ-equivalent EDT sphere algo)
# numba          >= 0.5x (0.63.1 tested)  JIT sphere-insertion kernels
#                                         used internally by porespy
# edt            >= 3.0.0                 fast float EDT (porespy dep)
# scikit-image   >= 0.26.0               0.25.x has broken segmentation DLL
#                                         on Windows — causes hard crash;
#                                         0.26.0 fixes it
# scipy          any modern               distance_transform_edt fallback
# =============================================================================
#
# NOTE: This file has a NARROWER numpy window than the rest of the project.
# All other project scripts are compatible with any modern numpy (1.22 - 2.x).
# If you upgrade numpy above 2.3, porespy/numba will raise ImportError.
# =============================================================================
#
# Tested environment (venv-napari, April 2026):
#   numpy==2.3.5   scikit-image==0.26.0   porespy==3.0.4
#   numba==0.63.1  edt==3.0.0             scipy==1.17.1
# =============================================================================

from __future__ import annotations

import warnings
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# Module-level constants  (values preserved from legacy psd_calculator.py /
#                          psd_diagnostics.py / block_processor.py)
# ---------------------------------------------------------------------------
_INTERNAL_VOXEL_SPACING: Tuple[float, float, float] = (1.0, 1.0, 1.0)
_DEFAULT_N_BINS: int = 50
_DEFAULT_BORDER_WIDTH: int = 1
_DEFAULT_HIST_BINS: int = 64
_DEFAULT_LOW_COUNT_THRESHOLD: int = 5
_DEFAULT_SPIKE_MULTIPLIER: float = 5.0
_INTEGER_TOLERANCE: float = 1e-6
_DEFAULT_CHUNK_SIZE: Tuple[int, int, int] = (128, 128, 128)
_DEFAULT_HALO_WIDTH: int = 50

# ---------------------------------------------------------------------------
# GPU availability
# ---------------------------------------------------------------------------

def _check_gpu_available() -> bool:
    """Return True if CuPy and a CUDA device are accessible."""
    try:
        import cupy as cp  # noqa: F401
        _ = cp.cuda.Device(0).compute_capability
        return True
    except (ImportError, RuntimeError):
        return False


# ---------------------------------------------------------------------------
# Euclidean Distance Transform
# ---------------------------------------------------------------------------

def _compute_edt_cpu(
    volume: np.ndarray,
    spacing: Tuple[float, float, float],
) -> np.ndarray:
    from scipy.ndimage import distance_transform_edt
    return distance_transform_edt(volume, sampling=spacing).astype(np.float32)


def _compute_edt_gpu(
    volume: np.ndarray,
    spacing: Tuple[float, float, float],
) -> np.ndarray:
    import cupy as cp
    from cupyx.scipy.ndimage import distance_transform_edt as _edt_gpu

    vol_gpu = cp.asarray(volume, dtype=cp.bool_)
    result = _edt_gpu(vol_gpu, sampling=spacing)
    out = cp.asnumpy(result).astype(np.float32)
    del vol_gpu, result
    cp.get_default_memory_pool().free_all_blocks()
    return out


def _compute_edt(
    volume: np.ndarray,
    spacing: Tuple[float, float, float],
    use_gpu: bool = True,
) -> np.ndarray:
    if use_gpu and _check_gpu_available():
        try:
            return _compute_edt_gpu(volume, spacing)
        except Exception as exc:
            warnings.warn(
                f"GPU EDT failed ({exc}), falling back to CPU",
                RuntimeWarning,
            )
    return _compute_edt_cpu(volume, spacing)


# ---------------------------------------------------------------------------
# Block Processor  (chunked EDT stitching)
# Preserved from legacy block_processor.BlockProcessor; checkpoint dependency
# removed (Colab-specific feature outside new design scope).
# ---------------------------------------------------------------------------

class _BlockProcessor:
    """Processes large 3-D volumes in overlapping chunks with halo overlap."""

    def __init__(
        self,
        volume_shape: Tuple[int, int, int],
        chunk_size: Tuple[int, int, int] = (128, 128, 128),
        halo_width: int = 50,
    ) -> None:
        self.volume_shape = volume_shape
        self.chunk_size = chunk_size
        self.halo_width = halo_width

        if halo_width < 10:
            warnings.warn(
                f"halo_width={halo_width} may be too small. "
                "Recommend >= 2 × max_pore_diameter",
                UserWarning,
            )
        if any(cs < 2 * halo_width for cs in chunk_size):
            raise ValueError(
                f"chunk_size {chunk_size} must be >= 2×halo_width "
                f"({2 * halo_width}) in all dimensions"
            )

        self.blocks = self._compute_block_grid()

    def _compute_block_grid(self) -> List[Tuple[int, int, int, int, int, int]]:
        Z, Y, X = self.volume_shape
        cz, cy, cx = self.chunk_size
        blocks: List[Tuple[int, int, int, int, int, int]] = []
        for z0 in range(0, Z, cz):
            z1 = min(z0 + cz, Z)
            for y0 in range(0, Y, cy):
                y1 = min(y0 + cy, Y)
                for x0 in range(0, X, cx):
                    x1 = min(x0 + cx, X)
                    blocks.append((z0, z1, y0, y1, x0, x1))
        return blocks

    def _get_padded_slice(
        self,
        block_coords: Tuple[int, int, int, int, int, int],
    ) -> Tuple[slice, slice, slice, Tuple[int, int, int, int, int, int]]:
        z0, z1, y0, y1, x0, x1 = block_coords
        H = self.halo_width
        Z, Y, X = self.volume_shape
        z0p = max(0, z0 - H)
        z1p = min(Z, z1 + H)
        y0p = max(0, y0 - H)
        y1p = min(Y, y1 + H)
        x0p = max(0, x0 - H)
        x1p = min(X, x1 + H)
        return (
            slice(z0p, z1p),
            slice(y0p, y1p),
            slice(x0p, x1p),
            (z0p, z1p, y0p, y1p, x0p, x1p),
        )

    def _crop_halo(
        self,
        padded_result: np.ndarray,
        block_coords: Tuple[int, int, int, int, int, int],
        actual_padded_coords: Tuple[int, int, int, int, int, int],
    ) -> np.ndarray:
        z0, z1, y0, y1, x0, x1 = block_coords
        z0p, _, y0p, _, x0p, _ = actual_padded_coords
        zs = z0 - z0p
        ys = y0 - y0p
        xs = x0 - x0p
        return padded_result[
            zs : zs + (z1 - z0),
            ys : ys + (y1 - y0),
            xs : xs + (x1 - x0),
        ]

    def get_memory_estimate(self, dtype: np.dtype = np.float32) -> Dict[str, float]:
        H = self.halo_width
        cz, cy, cx = self.chunk_size
        padded = (cz + 2 * H, cy + 2 * H, cx + 2 * H)
        bpv = np.dtype(dtype).itemsize
        input_mb = float(np.prod(padded)) / (1024 ** 2)
        output_mb = float(np.prod(padded)) * bpv / (1024 ** 2)
        full_mb = float(np.prod(self.volume_shape)) * bpv / (1024 ** 2)
        return {
            "input_block_mb": input_mb,
            "output_block_mb": output_mb,
            "total_per_block_mb": input_mb + output_mb,
            "full_output_mb": full_mb,
        }

    def process_volume(
        self,
        volume: np.ndarray,
        process_func: Callable[[np.ndarray], np.ndarray],
    ) -> np.ndarray:
        if volume.shape != self.volume_shape:
            raise ValueError(
                f"Volume shape {volume.shape} doesn't match processor "
                f"shape {self.volume_shape}"
            )
        output = np.zeros(self.volume_shape, dtype=np.float32)
        total = len(self.blocks)
        for idx, block_coords in enumerate(self.blocks):
            print(f"Processing block {idx + 1}/{total}: {block_coords}")
            z_sl, y_sl, x_sl, actual = self._get_padded_slice(block_coords)
            padded_block = volume[z_sl, y_sl, x_sl]
            try:
                processed = process_func(padded_block)
            except Exception as exc:
                raise RuntimeError(
                    f"Processing failed for block {idx}: {exc}"
                ) from exc
            cropped = self._crop_halo(processed, block_coords, actual)
            z0, z1, y0, y1, x0, x1 = block_coords
            output[z0:z1, y0:y1, x0:x1] = cropped
        return output


# ---------------------------------------------------------------------------
# Local thickness  (EDT-based maximum inscribed sphere reconstruction)
# Replaces the previous integer-radius morphological-opening loop that
# quantised pore diameters to even integers and produced a sparse PSD.
# Uses porespy.filters.local_thickness (method='imj') which implements the
# Hildebrand & Rüegsegger (1997) / BoneJ equivalent: for every pore voxel,
# the float radius of the maximally-inscribed sphere covering it is recorded
# via Numba-JIT per-voxel sphere insertion.
# ---------------------------------------------------------------------------

def _compute_opening_map(edt_map: np.ndarray, use_gpu: bool = True) -> np.ndarray:
    """Compute per-voxel local thickness (diameter) via EDT sphere reconstruction.

    Calls ``porespy.filters.local_thickness(method='imj')``, passing the
    pre-computed ``edt_map`` directly to avoid redundant EDT computation.
    The binary pore mask is derived as ``edt_map > 0``.

    Returns diameter values (radius × 2) as float32, preserving the
    downstream API contract of the previous implementation.

    ``use_gpu`` is accepted for API compatibility; PoreSpy uses Numba JIT
    (parallel CPU) for the sphere-insertion pass regardless.
    """
    from porespy.filters import local_thickness as _ps_local_thickness

    if edt_map.dtype not in (np.float32, np.float64):
        warnings.warn(
            f"EDT map dtype {edt_map.dtype} not float32/64, converting",
            UserWarning,
        )
        edt_map = edt_map.astype(np.float32)

    im = edt_map > 0  # binary pore mask derived from EDT
    print(
        f"  Computing Local Thickness (PoreSpy imj, "
        f"max EDT radius: {edt_map.max():.2f})..."
    )
    # local_thickness returns radius per voxel; multiply by 2 for diameter
    lt = _ps_local_thickness(
        im, dt=edt_map.astype(np.float64), method="imj", smooth=False
    )
    return (np.asarray(lt) * 2).astype(np.float32)


# ---------------------------------------------------------------------------
# Border masking
# Preserved from legacy psd_calculator.mask_border_voxels
# ---------------------------------------------------------------------------

def _mask_border_voxels(
    volume: np.ndarray,
    border_width: int = _DEFAULT_BORDER_WIDTH,
) -> np.ndarray:
    masked = volume.copy()
    bw = border_width
    masked[:bw, :, :] = False
    masked[-bw:, :, :] = False
    masked[:, :bw, :] = False
    masked[:, -bw:, :] = False
    masked[:, :, :bw] = False
    masked[:, :, -bw:] = False
    return masked


# ---------------------------------------------------------------------------
# Diagnostics internal helpers
# Preserved from legacy psd_diagnostics.py
# ---------------------------------------------------------------------------

def _to_scalar(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    return value


def _flatten_numeric(values: Any) -> np.ndarray:
    arr = np.asarray(values, dtype=np.float64).ravel()
    if arr.size == 0:
        return arr
    finite = np.isfinite(arr)
    if not finite.all():
        arr = arr[finite]
    return arr


def _histogram(values: np.ndarray, bins: int) -> Dict[str, Any]:
    counts, edges = np.histogram(values, bins=bins)
    return {
        "bins": bins,
        "counts": counts.tolist(),
        "edges": edges.tolist(),
        "counts_head": counts[:3].tolist(),
        "counts_tail": counts[-3:].tolist(),
    }


def _array_stats(values: np.ndarray) -> Dict[str, float]:
    if values.size == 0:
        return {
            "count": 0,
            "min": 0.0,
            "max": 0.0,
            "mean": 0.0,
            "median": 0.0,
            "std": 0.0,
            "q25": 0.0,
            "q75": 0.0,
        }
    return {
        "count": float(values.size),
        "min": float(np.min(values)),
        "max": float(np.max(values)),
        "mean": float(np.mean(values)),
        "median": float(np.median(values)),
        "std": float(np.std(values)),
        "q25": float(np.quantile(values, 0.25)),
        "q75": float(np.quantile(values, 0.75)),
    }


# ---------------------------------------------------------------------------
# Diagnostics collector
# Preserved from legacy psd_diagnostics.DiagnosticsCollector (enabled=True).
# File I/O removed — the runner module is responsible for writing outputs.
# ---------------------------------------------------------------------------

class _DiagnosticsCollector:
    """Collects per-stage diagnostics; always enabled, no file I/O."""

    def __init__(
        self,
        run_tag: str = "psd",
        cfg: Optional[Dict[str, Any]] = None,
    ) -> None:
        cfg = cfg or {}
        self.hist_bins = int(cfg.get("hist_bins", _DEFAULT_HIST_BINS))
        self.low_count_threshold = int(
            cfg.get("low_count_threshold", _DEFAULT_LOW_COUNT_THRESHOLD)
        )
        self.spike_multiplier = float(
            cfg.get("spike_multiplier", _DEFAULT_SPIKE_MULTIPLIER)
        )
        # Sanitise run_tag the same way as the legacy code
        safe_tag = "".join(
            c if c.isalnum() or c in "_-" else "_" for c in run_tag
        )
        self.run_tag = safe_tag
        self.data: Dict[str, Any] = {
            "run_tag": safe_tag,
            "created": datetime.utcnow().isoformat(),
            "config": {
                "hist_bins": self.hist_bins,
                "low_count_threshold": self.low_count_threshold,
                "spike_multiplier": self.spike_multiplier,
            },
            "stages": {},
        }

    # ---------------------------------------------------------------- stages

    def log_edt_map(
        self,
        edt_map: np.ndarray,
        voxel_spacing: Tuple[float, float, float],
    ) -> None:
        values = _flatten_numeric(edt_map)
        hist = _histogram(values, self.hist_bins)
        unique_count = int(np.unique(values).size) if values.size else 0
        integer_like = (
            bool(
                np.max(np.abs(values - np.round(values))) < _INTEGER_TOLERANCE
            )
            if values.size
            else True
        )
        stats = _array_stats(values)
        payload: Dict[str, Any] = {
            "stats": stats,
            "unique_count": unique_count,
            "integer_like": integer_like,
            "voxel_spacing": tuple(float(v) for v in voxel_spacing),
            "histogram": hist,
        }
        print("\n[Diagnostics] EDT map")
        print(f"  Range: {stats['min']:.4f} - {stats['max']:.4f}")
        print(
            f"  Unique values: {unique_count}, integer-like: {integer_like}"
        )
        print(
            f"  Histogram bins: {self.hist_bins}, "
            f"counts head {hist['counts_head']}, tail {hist['counts_tail']}"
        )
        self.data["stages"]["edt"] = payload

    def log_opening_map(self, opening_map: np.ndarray) -> None:
        values = _flatten_numeric(opening_map)
        hist = _histogram(values, self.hist_bins)
        unique_values, counts = np.unique(values, return_counts=True)
        total = float(counts.sum()) if counts.size else 0.0
        fractions = (counts / total) if total else np.zeros_like(counts, dtype=float)
        top_idx = np.argsort(counts)[::-1][:5]
        top_values = [
            {
                "diameter": float(unique_values[i]),
                "count": int(counts[i]),
                "fraction": float(fractions[i]) if total else 0.0,
            }
            for i in top_idx
            if counts[i]
        ]
        payload: Dict[str, Any] = {
            "unique_diameter_count": int(unique_values.size),
            "top_diameter_fractions": top_values,
            "histogram": hist,
        }
        print("\n[Diagnostics] Opening map")
        print(f"  Unique diameters: {payload['unique_diameter_count']}")
        print(f"  Top diameter fractions: {top_values}")
        print(
            f"  Histogram bins: {self.hist_bins}, "
            f"counts head {hist['counts_head']}"
        )
        self.data["stages"]["opening"] = payload

    def log_raw_diameters(self, pore_diameters: np.ndarray) -> None:
        values = _flatten_numeric(pore_diameters)
        stats = _array_stats(values)
        unique_values, counts = np.unique(values, return_counts=True)
        repeat_bins = int(np.sum(counts > 1))
        repeat_details = [
            {"diameter": float(unique_values[i]), "count": int(counts[i])}
            for i in np.argsort(counts)[::-1][:5]
            if counts[i] > 1
        ]
        hist = _histogram(values, self.hist_bins)
        payload: Dict[str, Any] = {
            "stats": stats,
            "repeat_bin_count": repeat_bins,
            "repeat_summary": repeat_details,
            "histogram": hist,
        }
        print("\n[Diagnostics] Raw pore diameters")
        print(
            f"  Count: {int(stats['count'])}, "
            f"range: {stats['min']:.4f} - {stats['max']:.4f}"
        )
        print(
            f"  Repeated diameters (>1): {repeat_bins}, "
            f"samples: {repeat_details}"
        )
        print(
            f"  Histogram bins: {self.hist_bins}, "
            f"counts head {hist['counts_head']}"
        )
        self.data["stages"]["raw_diameters"] = payload

    def log_binning(
        self,
        volume_counts: np.ndarray,
        bin_edges_px: np.ndarray,
        bin_edges_um: np.ndarray,
    ) -> None:
        counts = np.asarray(volume_counts, dtype=np.int64)
        empty_bins = int(np.sum(counts == 0))
        low_count_bins = int(np.sum(counts < self.low_count_threshold))
        bin_widths = np.diff(bin_edges_um)
        zero_width_bins = int(np.sum(bin_widths <= 0))
        payload: Dict[str, Any] = {
            "bin_edges_px": bin_edges_px.tolist(),
            "bin_edges_um": bin_edges_um.tolist(),
            "bin_widths_um": bin_widths.tolist(),
            "bin_width_stats": {
                "min": float(bin_widths.min()),
                "max": float(bin_widths.max()),
            },
            "bin_counts": counts.tolist(),
            "empty_bins": empty_bins,
            "low_count_bins": low_count_bins,
            "zero_width_bins": zero_width_bins,
            "low_count_threshold": self.low_count_threshold,
        }
        print("\n[Diagnostics] Bin edges")
        head_px = bin_edges_px[:3].tolist()
        tail_px = bin_edges_px[-3:].tolist()
        head_um = bin_edges_um[:3].tolist()
        tail_um = bin_edges_um[-3:].tolist()
        print(f"  Bin edges (px): {head_px} ... {tail_px}")
        print(f"  Bin edges (um): {head_um} ... {tail_um}")
        print(
            f"  Bin width (um): min {bin_widths.min():.4e}, "
            f"max {bin_widths.max():.4e}, zero-width bins: {zero_width_bins}"
        )
        print(
            f"  Empty bins: {empty_bins}, "
            f"low-count bins (< {self.low_count_threshold}): {low_count_bins}"
        )
        if zero_width_bins:
            widths_idx = np.where(bin_widths <= 0)[0].tolist()
            print(f"    Zero-width indices: {widths_idx}")
        self.data["stages"]["binning"] = payload

    def log_post_psd(
        self,
        differential_volume: np.ndarray,
        bin_centers_um: np.ndarray,
    ) -> None:
        values = np.asarray(differential_volume, dtype=np.float64)
        nan_mask = np.isnan(values)
        inf_mask = np.isinf(values)
        finite_mask = np.isfinite(values)
        finite_values = values[finite_mask]
        stats = _array_stats(finite_values)
        median = float(np.median(finite_values)) if finite_values.size else 0.0
        mad = (
            float(np.median(np.abs(finite_values - median)))
            if finite_values.size
            else 0.0
        )
        threshold = median + self.spike_multiplier * (mad or 1.0)
        spike_indices = [int(i) for i in np.where(values > threshold)[0]]
        spike_details = [
            {
                "bin_index": i,
                "bin_center_um": (
                    float(bin_centers_um[i])
                    if i < len(bin_centers_um)
                    else None
                ),
                "value": float(values[i]),
            }
            for i in spike_indices
        ]
        payload: Dict[str, Any] = {
            "stats": stats,
            "nan_count": int(np.sum(nan_mask)),
            "inf_count": int(np.sum(inf_mask)),
            "spike_threshold": threshold,
            "spikes": spike_details,
        }
        print("\n[Diagnostics] Differential PSD")
        print(
            f"  Finite bins: {int(finite_values.size)}, "
            f"NaNs: {payload['nan_count']}, Infs: {payload['inf_count']}"
        )
        print(
            f"  Median: {median:.4e}, MAD: {mad:.4e}, "
            f"Spike threshold: {threshold:.4e}"
        )
        if spike_details:
            print(
                f"  Spikes detected at indices: "
                f"{[item['bin_index'] for item in spike_details]}"
            )
        self.data["stages"]["post_psd"] = payload


# ---------------------------------------------------------------------------
# PSD computation
# Preserved from legacy psd_calculator.compute_psd_from_opening_map
# ---------------------------------------------------------------------------

def _compute_psd_from_opening_map(
    opening_map: np.ndarray,
    binary_volume: np.ndarray,
    voxel_spacing: Tuple[float, float, float],
    bin_edges_um: Optional[np.ndarray],
    exclude_borders: bool,
    collector: _DiagnosticsCollector,
) -> Dict[str, Any]:
    """Extract PSD from opening map.

    The opening map already contains diameters (2*r) after the iterative
    granulometry step, so opening_to_diameter is a no-op (legacy behaviour
    preserved verbatim).
    """
    # opening_to_diameter is a no-op in legacy: opening map already has diameters
    diameter_map = opening_map

    if exclude_borders:
        masked_volume = _mask_border_voxels(binary_volume)
    else:
        masked_volume = binary_volume

    pore_mask = masked_volume & (diameter_map > 0)
    pore_diameters = diameter_map[pore_mask]

    if pore_diameters.size == 0:
        warnings.warn("No pore voxels found after masking", UserWarning)
        return _empty_psd_result(voxel_spacing)

    collector.log_raw_diameters(pore_diameters)

    # Voxel-to-physical scale: isotropic mean of spacing (legacy behaviour)
    voxel_scale_um = float(np.mean(voxel_spacing))

    if bin_edges_um is None:
        min_d = float(pore_diameters.min())
        max_d = float(pore_diameters.max())
        bin_edges_px = np.logspace(
            np.log10(max(min_d, 0.1)),
            np.log10(max_d * 1.1),
            _DEFAULT_N_BINS + 1,
        )
        _bin_edges_um = bin_edges_px * voxel_scale_um
    else:
        # Keep bin edges in float64 to avoid precision loss; pore diameters stay float32.
        bin_edges_px = np.asarray(bin_edges_um, dtype=np.float64) / voxel_scale_um
        _bin_edges_um = bin_edges_px * voxel_scale_um

    volume_counts, _ = np.histogram(pore_diameters, bins=bin_edges_px)
    bin_centers_px = (bin_edges_px[:-1] + bin_edges_px[1:]) / 2
    bin_centers_um = bin_centers_px * voxel_scale_um

    collector.log_binning(volume_counts, bin_edges_px, _bin_edges_um)

    total_pore_voxels = int(pore_diameters.size)
    cumulative_volume = np.cumsum(volume_counts) / total_pore_voxels
    bin_widths = np.diff(_bin_edges_um)
    differential_volume = volume_counts / (total_pore_voxels * bin_widths)

    collector.log_post_psd(differential_volume, bin_centers_um)

    return {
        "bin_centers_px": bin_centers_px,
        "bin_centers_um": bin_centers_um,
        "bin_edges_um": _bin_edges_um,
        "volume_counts": volume_counts,
        "cumulative_volume": cumulative_volume,
        "differential_volume": differential_volume,
        "total_pore_voxels": total_pore_voxels,
        "voxel_spacing": tuple(voxel_spacing),
        # Additive fields (not consumed by any existing caller — added for
        # analysis/psd_topology_metrics.py's per-bin surface-area metric,
        # which needs the full per-voxel diameter map, not just the
        # histogram). Named-key access only; safe to add.
        "diameter_map": diameter_map,
        "masked_pore_mask": pore_mask,
    }


def _empty_psd_result(
    voxel_spacing: Tuple[float, float, float],
) -> Dict[str, Any]:
    return {
        "bin_centers_px": np.array([], dtype=np.float64),
        "bin_centers_um": np.array([], dtype=np.float64),
        "bin_edges_um": np.array([], dtype=np.float64),
        "volume_counts": np.array([], dtype=np.int64),
        "cumulative_volume": np.array([], dtype=np.float64),
        "differential_volume": np.array([], dtype=np.float64),
        "total_pore_voxels": 0,
        "voxel_spacing": tuple(voxel_spacing),
        "diameter_map": None,
        "masked_pore_mask": None,
    }


# ===========================================================================
# Public API
# ===========================================================================

def run_psd_pipeline(
    volume: np.ndarray,
    voxel_spacing: Tuple[float, float, float],
    *,
    use_chunking: bool = False,
    chunk_size: Tuple[int, int, int] = _DEFAULT_CHUNK_SIZE,
    halo_width: int = _DEFAULT_HALO_WIDTH,
    exclude_borders: bool = True,
    bin_edges_um: Optional[np.ndarray] = None,
    diagnostics_cfg: Optional[Dict[str, Any]] = None,
    use_gpu: bool = True,
) -> Dict[str, Any]:
    """Run the full PSD pipeline on a 3-D binary pore volume.

    Parameters
    ----------
    volume : 3-D bool ndarray  (True = pore, False = solid)
    voxel_spacing : (dz, dy, dx) physical spacing in micrometers
    use_chunking : if True, EDT is computed in overlapping chunks
    chunk_size : core chunk dimensions (before halo) used when chunking
    halo_width : halo padding per side for chunked EDT
    exclude_borders : mask 1-voxel border before pore extraction
    bin_edges_um : custom bin edges in μm; auto-generated when None
    diagnostics_cfg : optional dict with diagnostics collector settings
        accepted keys: hist_bins, low_count_threshold, spike_multiplier,
                       run_tag
    use_gpu : attempt CuPy-accelerated EDT and opening steps

    Returns
    -------
    dict with three top-level keys:

    ``psd``
        PSD arrays and scalars::

            bin_centers_px, bin_centers_um, bin_edges_um, volume_counts,
            cumulative_volume, differential_volume, total_pore_voxels,
            voxel_spacing

    ``diagnostics``
        Full diagnostics payload (run_tag, created, config, stages) ready
        for direct serialisation as ``diagnostics.json``.

    ``meta``
        Resolved configuration for this run (for ``config.json``).
    """
    # ── Input validation ──────────────────────────────────────────────────
    if volume.ndim != 3:
        raise ValueError(f"Expected 3D volume, got shape {volume.shape}")
    if len(voxel_spacing) != 3:
        raise ValueError(
            f"voxel_spacing must have 3 elements, got {len(voxel_spacing)}"
        )
    if any(v <= 0 for v in voxel_spacing):
        raise ValueError(
            f"All voxel_spacing values must be positive, got {voxel_spacing}"
        )
    input_dtype_converted = False
    if volume.dtype != bool:
        warnings.warn(
            f"Converting volume from {volume.dtype} to bool", UserWarning
        )
        volume = volume.astype(bool)
        input_dtype_converted = True

    physical_voxel_spacing: Tuple[float, float, float] = tuple(
        float(v) for v in voxel_spacing
    )
    cfg = diagnostics_cfg or {}
    run_tag = str(cfg.get("run_tag", "psd"))
    collector = _DiagnosticsCollector(run_tag=run_tag, cfg=cfg)

    print("=" * 60)
    print("PSD Pipeline Execution")
    print("=" * 60)
    print(f"Volume shape: {volume.shape}")
    print(f"Voxel spacing (physical): {physical_voxel_spacing} um")
    print(f"Porosity: {volume.mean():.4f}")
    print(f"GPU: {use_gpu}, Chunking: {use_chunking}")

    # ── Step 1: EDT  (always with isotropic unit spacing — legacy behaviour) ─
    print("\n[1/3] Computing Euclidean Distance Transform...")
    internal_spacing = _INTERNAL_VOXEL_SPACING

    if use_chunking:
        def _edt_func(block: np.ndarray) -> np.ndarray:
            return _compute_edt(block, internal_spacing, use_gpu=use_gpu)

        processor = _BlockProcessor(
            volume_shape=volume.shape,
            chunk_size=chunk_size,
            halo_width=halo_width,
        )
        mem = processor.get_memory_estimate()
        print(f"  Memory per block: {mem['total_per_block_mb']:.2f} MB")
        print(f"  Total blocks: {len(processor.blocks)}")
        edt_map = processor.process_volume(volume, _edt_func)
    else:
        edt_map = _compute_edt(volume, internal_spacing, use_gpu=use_gpu)

    print(f"  EDT complete. Max distance: {edt_map.max():.2f} voxels")
    collector.log_edt_map(edt_map, voxel_spacing=physical_voxel_spacing)

    # ── Step 2: Opening map ──────────────────────────────────────────────
    print("\n[2/3] Computing Opening Map (Morphological Reconstruction)...")
    opening_map = _compute_opening_map(edt_map, use_gpu=use_gpu)
    print(f"  Opening complete. Max diameter: {opening_map.max():.2f} voxels")
    collector.log_opening_map(opening_map)

    # ── Step 3: PSD ──────────────────────────────────────────────────────
    print("\n[3/3] Extracting Pore Size Distribution...")
    psd = _compute_psd_from_opening_map(
        opening_map,
        volume,
        physical_voxel_spacing,
        bin_edges_um,
        exclude_borders,
        collector,
    )

    print("\n" + "=" * 60)
    print("PSD Calculation Complete")
    print("=" * 60)
    print(f"Total pore voxels analyzed: {psd['total_pore_voxels']:,}")
    if psd["bin_centers_um"].size > 0:
        print(
            f"Diameter range: {psd['bin_centers_um'].min():.2f} - "
            f"{psd['bin_centers_um'].max():.2f} um"
        )

    meta: Dict[str, Any] = {
        "volume_shape": list(volume.shape),
        "voxel_spacing": list(physical_voxel_spacing),
        "internal_voxel_spacing": list(internal_spacing),
        "input_dtype_converted": input_dtype_converted,
        "use_chunking": use_chunking,
        "use_gpu": use_gpu,
        "exclude_borders": exclude_borders,
        "bin_edges_um_input": (
            bin_edges_um.tolist() if bin_edges_um is not None else None
        ),
        "chunk_size": list(chunk_size) if use_chunking else None,
        "halo_width": halo_width if use_chunking else None,
        "default_n_bins": _DEFAULT_N_BINS,
    }

    return {
        "psd": psd,
        "diagnostics": collector.data,
        "meta": meta,
    }


# ---------------------------------------------------------------------------
# Serialization helpers  (plan §5: "Serialization helpers for output payloads")
# ---------------------------------------------------------------------------

def to_json_serializable(obj: Any) -> Any:
    """Recursively convert numpy arrays and scalars to JSON-native Python types.

    Use this before ``json.dump`` on any run result dict or sub-dict.

    Parameters
    ----------
    obj : any value — dict, list, tuple, numpy array/scalar, or scalar

    Returns
    -------
    JSON-serializable equivalent
    """
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.generic):
        return obj.item()
    if isinstance(obj, dict):
        return {k: to_json_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        converted = [to_json_serializable(v) for v in obj]
        return converted if isinstance(obj, list) else tuple(converted)
    return obj


# Required CSV column names (§4.6) — single source of truth
PSD_TABLE_COLUMNS: Tuple[str, ...] = (
    "Diameter_px",
    "Diameter_um",
    "Volume_Count",
    "Cumulative_Porosity",
    "Differential_PSD",
)


def build_psd_table(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build the tabular PSD data required for ``psd_table.csv`` (§4.6).

    Parameters
    ----------
    result : dict returned by ``run_psd_pipeline``

    Returns
    -------
    list of row dicts with keys matching ``PSD_TABLE_COLUMNS``
    """
    psd = result["psd"]
    n = len(psd["bin_centers_px"])
    rows: List[Dict[str, Any]] = []
    for i in range(n):
        rows.append(
            {
                "Diameter_px": float(psd["bin_centers_px"][i]),
                "Diameter_um": float(psd["bin_centers_um"][i]),
                "Volume_Count": int(psd["volume_counts"][i]),
                "Cumulative_Porosity": float(psd["cumulative_volume"][i]),
                "Differential_PSD": float(psd["differential_volume"][i]),
            }
        )
    return rows


# Extended CSV columns (base PSD_TABLE_COLUMNS + topology/connectivity
# metrics from analysis/pore_metrics_research/decisions.md D1-D5). Sample-
# level scalars are broadcast across every bin row; Surface_Area_um2 is a
# genuine per-bin value.
EXTENDED_PSD_TABLE_COLUMNS: Tuple[str, ...] = PSD_TABLE_COLUMNS + (
    "Surface_Area_um2",
    "Euler_Number",
    "Connectivity_Density_per_mm3",
    "Connectivity_Probability_Gamma",
    "Degree_of_Anisotropy",
    "Tortuosity_Axis0",
    "Tortuosity_Axis1",
    "Tortuosity_Axis2",
    "PSD_30_150um_Volume_Fraction",
)


def build_extended_psd_table(
    result: Dict[str, Any],
    surface_areas: "np.ndarray",
    scalars: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Build the extended PSD table: base PSD_TABLE_COLUMNS rows (via
    ``build_psd_table``) plus the new topology/connectivity columns.

    Parameters
    ----------
    result : dict returned by ``run_psd_pipeline``
    surface_areas : per-bin surface area (um^2), same length as the PSD
        bin arrays; NaN where a bin had too few voxels to mesh.
    scalars : sample-level scalar metrics dict (broadcast across all rows),
        expected keys: euler_number, connectivity_density_per_mm3,
        connectivity_probability_gamma, degree_of_anisotropy,
        tortuosity_axis0/1/2, psd_30_150um_volume_fraction.

    Returns
    -------
    list of row dicts with keys matching ``EXTENDED_PSD_TABLE_COLUMNS``
    """
    base_rows = build_psd_table(result)
    n = len(base_rows)
    sa = np.asarray(surface_areas, dtype=np.float64) if len(surface_areas) else np.full(n, np.nan)

    rows: List[Dict[str, Any]] = []
    for i, row in enumerate(base_rows):
        extended_row = dict(row)
        extended_row["Surface_Area_um2"] = float(sa[i]) if i < len(sa) else float("nan")
        extended_row["Euler_Number"] = scalars.get("euler_number")
        extended_row["Connectivity_Density_per_mm3"] = scalars.get("connectivity_density_per_mm3")
        extended_row["Connectivity_Probability_Gamma"] = scalars.get("connectivity_probability_gamma")
        extended_row["Degree_of_Anisotropy"] = scalars.get("degree_of_anisotropy")
        extended_row["Tortuosity_Axis0"] = scalars.get("tortuosity_axis0")
        extended_row["Tortuosity_Axis1"] = scalars.get("tortuosity_axis1")
        extended_row["Tortuosity_Axis2"] = scalars.get("tortuosity_axis2")
        extended_row["PSD_30_150um_Volume_Fraction"] = scalars.get("psd_30_150um_volume_fraction")
        rows.append(extended_row)
    return rows


def build_summary(
    result: Dict[str, Any],
    *,
    mode: str,
    run_name: str,
) -> Dict[str, Any]:
    """Build the concise scalar summary for ``summary.json`` (§4.7).

    Parameters
    ----------
    result   : dict returned by ``run_psd_pipeline``
    mode     : execution mode string, e.g. ``'real'``
    run_name : run identifier string

    Returns
    -------
    dict with keys: range, repeat_bins, low_count_bins, spikes, mode,
    run_name  (all §4.7 required fields)
    """
    psd = result["psd"]
    stages = result.get("diagnostics", {}).get("stages", {})

    bcu = psd["bin_centers_um"]
    if bcu.size > 0:
        diam_range: Optional[Dict[str, float]] = {
            "min": float(bcu.min()),
            "max": float(bcu.max()),
        }
    else:
        diam_range = None

    repeat_bins = int(
        stages.get("raw_diameters", {}).get("repeat_bin_count", 0)
    )
    low_count_bins = int(
        stages.get("binning", {}).get("low_count_bins", 0)
    )
    spikes = len(stages.get("post_psd", {}).get("spikes", []))

    return {
        "range": diam_range,
        "repeat_bins": repeat_bins,
        "low_count_bins": low_count_bins,
        "spikes": spikes,
        "mode": mode,
        "run_name": run_name,
    }


# ---------------------------------------------------------------------------
# Plot generation  (§4.5 graphical diagnostics)
# ---------------------------------------------------------------------------

def plot_psd_extras(
    psd_dict: Dict[str, Any],
    run_dir: str | Path,
) -> List[str]:
    """Generate diagnostic PSD plots from binned data.

    Generates two plots:

    - ``psd_30bins_microbial_active_domain.png``: 30-bin histogram (full diameter
      range, log-scale x), y-axis = per-bin pore volume fraction
      (Volume_Count / total_pore_voxels), cumulative on right axis, with the
      30–150 µm microbial active domain highlighted.
    - ``psd_kde.png``: kernel density estimate (log-space, Jacobian-corrected).

    Parameters
    ----------
    psd_dict : dict
        Pipeline output dict with keys: bin_centers_um, bin_edges_um,
        volume_counts, total_pore_voxels, voxel_spacing
    run_dir : str or Path
        Directory to save PNG files

    Returns
    -------
    list[str]
        Filenames written (psd_30bins_microbial_active_domain.png, psd_kde.png)
    """
    import matplotlib.pyplot as plt
    from pathlib import Path

    _MICROBIAL_LO = 30.0
    _MICROBIAL_HI = 150.0

    run_dir = Path(run_dir)
    written_files = []

    # Extract binned data — convert lists to numpy arrays (JSON compat)
    bin_centers_um = np.asarray(psd_dict.get("bin_centers_um", np.array([])))
    volume_counts  = np.asarray(psd_dict.get("volume_counts",  np.array([])))
    total_pore_voxels = int(
        psd_dict.get("total_pore_voxels", max(int(volume_counts.sum()), 1))
    )

    if bin_centers_um.size == 0:
        return written_files

    # ── Re-bin into exactly 30 log-spaced bins across the FULL diameter range ──
    _N_PLOT_BINS = 30
    d_min = float(bin_centers_um.min())
    d_max = float(bin_centers_um.max())
    plot_edges   = np.logspace(np.log10(d_min), np.log10(d_max), _N_PLOT_BINS + 1)
    plot_centers = np.sqrt(plot_edges[:-1] * plot_edges[1:])  # geometric mean

    rebinned, _ = np.histogram(bin_centers_um, bins=plot_edges, weights=volume_counts)

    # Per-bin pore volume fraction (y-axis)
    volume_fraction    = rebinned / total_pore_voxels
    cumulative_fraction = np.cumsum(volume_fraction)
    bar_widths = np.diff(plot_edges)

    # Bar colours: orange for microbial active domain, blue elsewhere
    bar_colors = [
        "#e67300" if _MICROBIAL_LO <= d <= _MICROBIAL_HI else "#4878cf"
        for d in plot_centers
    ]

    # --- Plot 1: full-range PSD (30 bins) with microbial domain highlight ----
    fig1, ax1_l = plt.subplots(figsize=(11, 6), dpi=100)
    ax1_r = ax1_l.twinx()

    ax1_l.bar(
        plot_centers,
        volume_fraction,
        width=bar_widths,
        color=bar_colors,
        edgecolor="white",
        linewidth=0.5,
        alpha=0.85,
        label="Pore volume fraction per bin",
    )

    # Cumulative line
    ax1_r.plot(
        plot_centers,
        cumulative_fraction,
        color="black",
        linewidth=2,
        label="Cumulative",
    )
    ax1_r.set_ylim(0, 1.05)
    ax1_r.set_ylabel("Cumulative pore volume fraction", fontsize=11)

    # Microbial active domain shading + annotation
    x_lo = max(_MICROBIAL_LO, d_min)
    x_hi = min(_MICROBIAL_HI, d_max)
    if x_lo < x_hi:
        ax1_l.axvspan(x_lo, x_hi, alpha=0.10, color="orange", zorder=0)
        ax1_l.axvline(x_lo, color="orange", linestyle="--", linewidth=1.2, alpha=0.8)
        ax1_l.axvline(x_hi, color="orange", linestyle="--", linewidth=1.2, alpha=0.8)
        mid_x = float(np.sqrt(x_lo * x_hi))
        y_top = float(volume_fraction.max()) if volume_fraction.max() > 0 else 1.0
        ax1_l.text(
            mid_x, y_top * 0.97,
            "Microbial\nactive domain\n30–150 µm",
            ha="center", va="top", fontsize=9, color="darkorange",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                      edgecolor="orange", alpha=0.85),
        )

    ax1_l.set_xlabel("Pore Diameter (µm)", fontsize=11)
    ax1_l.set_ylabel("Pore volume fraction", fontsize=11)
    ax1_l.set_xscale("log")
    ax1_l.set_title(
        f"Pore Size Distribution — {_N_PLOT_BINS} bins (full range)",
        fontsize=12, fontweight="bold",
    )
    ax1_l.grid(True, which="both", alpha=0.3)

    # Combined legend
    h1, l1 = ax1_l.get_legend_handles_labels()
    h2, l2 = ax1_r.get_legend_handles_labels()
    ax1_l.legend(h1 + h2, l1 + l2, loc="upper right", fontsize=10)

    f1 = run_dir / "psd_30bins_microbial_active_domain.png"
    fig1.savefig(str(f1), dpi=100, bbox_inches="tight")
    plt.close(fig1)
    written_files.append("psd_30bins_microbial_active_domain.png")
    
    # --- Plot 2: KDE (log-space, Jacobian-corrected) ---
    fig2, ax2 = plt.subplots(figsize=(10, 6), dpi=100)
    
    # Build smooth KDE from the binned data
    # Treat each bin center as a sample, weighted by volume_counts
    if volume_counts.sum() > 0:
        # Create weighted samples for KDE
        samples_for_kde = []
        for center, count in zip(bin_centers_um, volume_counts):
            # Use count as sample multiplicity (rounded)
            samples_for_kde.extend([center] * max(1, int(round(count / volume_counts.max() * 1000))))
        
        if len(samples_for_kde) > 1:
            from scipy.stats import gaussian_kde
            
            # KDE in log-space
            log_samples = np.log10(np.array(samples_for_kde))
            try:
                kde = gaussian_kde(log_samples)
                
                # Evaluate on a fine log-scale grid
                x_eval = np.logspace(np.log10(bin_centers_um.min()), 
                                     np.log10(bin_centers_um.max()), 200)
                x_log = np.log10(x_eval)
                y_log_space = kde(x_log)
                
                # Jacobian correction: dy_linear = dy_log * d(log x)/dx = dy_log / x
                y_linear_space = y_log_space / x_eval
                
                ax2.plot(x_eval, y_linear_space, color="blue", linewidth=2, label="KDE (Jacobian-corrected)")
                ax2.fill_between(x_eval, y_linear_space, alpha=0.3, color="blue")
            except Exception:
                # If KDE fails, fall back to bar chart using the 30 re-binned data
                ax2.bar(
                    plot_centers,
                    volume_fraction,
                    width=bar_widths,
                    edgecolor="black",
                    alpha=0.7,
                    label="Pore volume fraction (fallback)",
                )
    
    ax2.set_xlabel("Pore Diameter (µm)", fontsize=11)
    ax2.set_ylabel("Density", fontsize=11)
    ax2.set_title("PSD KDE (log-space, Jacobian-corrected)", fontsize=12, fontweight="bold")
    ax2.set_xscale("log")
    ax2.grid(True, which="both", alpha=0.3)
    ax2.legend()
    
    f2 = run_dir / "psd_kde.png"
    fig2.savefig(str(f2), dpi=100, bbox_inches="tight")
    plt.close(fig2)
    written_files.append("psd_kde.png")
    
    return written_files
