"""PSD diagnostics core — reusable compute and diagnostics module.

Public API
----------
run_psd_pipeline(volume, voxel_spacing, *, ...)  ->  dict
generate_synthetic_volume(*, shape, voxel_spacing, ...)  ->  dict
compare_runs(result_a, result_b, *, ...)  ->  dict
to_json_serializable(obj)  ->  JSON-native Python object
build_psd_table(result)  ->  list[dict]  (CSV rows, §4.6 columns)
build_summary(result, *, mode, run_name)  ->  dict  (§4.7 fields)
plot_psd_extras(pore_diameters_um, psd, run_dir, n_bins)  ->  list[str]

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
_MIN_RELIABLE_DIAMETER_VOXELS: int = 5
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

    def log_edt_grid_diagnostic(self, report: Dict[str, Any]) -> None:
        print("\n[EDT grid diagnostic]")
        if "error" in report:
            print(f"  Error: {report['error']}")
            self.data["stages"]["edt_grid_diagnostic"] = report
            return
        print(
            f"  Theoretical EDT levels  : {report['total_theoretical_levels']}"
        )
        print(
            f"  Natural bins (EDT-spaced): {report['total_bins']}  "
            f"| empty: {report['empty_bins']}  "
            f"| non-empty: {report['nonempty_bins']}  "
            f"(empty fraction: {report['empty_fraction']:.1%})"
        )
        print(
            f"  Main 50-bin PSD zero-count bins    : {report['main_psd_zero_count_bins']}"
        )
        print(
            f"  ... falling in structural EDT gaps : "
            f"{report['main_psd_zero_bins_in_structural_gaps']}"
            f"  → {'EDT discretization' if report['main_psd_zero_bins_in_structural_gaps'] > 0 else 'not structural gaps'}"
        )
        self.data["stages"]["edt_grid_diagnostic"] = report


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

    # ── EDT/binning gap diagnostic ───────────────────────────────────────
    # Determines whether empty PSD bins are caused by EDT discretization
    # (gaps in unique diameter values) or over-fine log binning.
    _vals_um = pore_diameters.astype(np.float64) * voxel_scale_um
    _u = np.unique(np.round(_vals_um, 3))
    print(f"\n[Diameter diagnostic] Unique diameter values: {len(_u)}")
    print(f"  First 50: {_u[:50]}")
    if len(_u) > 1:
        print(f"  Gaps between first 20 consecutive values: {np.diff(_u[:20])}")
    # ─────────────────────────────────────────────────────────────────────

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

    # ── EDT grid diagnostic ───────────────────────────────────────────────
    _grid_report = _edt_grid_diagnostic(
        pore_diameters.astype(np.float64) * voxel_scale_um,
        voxel_spacing,
        bin_centers_um,
        volume_counts,
    )
    collector.log_edt_grid_diagnostic(_grid_report)
    # ─────────────────────────────────────────────────────────────────────

    total_pore_voxels = int(pore_diameters.size)
    cumulative_volume = np.cumsum(volume_counts) / total_pore_voxels
    bin_widths = np.diff(_bin_edges_um)
    differential_volume = volume_counts / (total_pore_voxels * bin_widths)

    collector.log_post_psd(differential_volume, bin_centers_um)

    # Reliability flag: Vogel et al. constraint (diameter >= configured threshold)
    reliability_flag = bin_centers_px >= _MIN_RELIABLE_DIAMETER_VOXELS

    return {
        "bin_centers_px": bin_centers_px,
        "bin_centers_um": bin_centers_um,
        "bin_edges_um": _bin_edges_um,
        "volume_counts": volume_counts,
        "cumulative_volume": cumulative_volume,
        "differential_volume": differential_volume,
        "reliability_flag": reliability_flag,
        "total_pore_voxels": total_pore_voxels,
        "voxel_spacing": tuple(voxel_spacing),
        # Raw diameters for downstream plotting (popped by run_psd_pipeline;
        # not part of the serialised PSD schema).
        "pore_diameters_um": pore_diameters.astype(np.float64) * voxel_scale_um,
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
        "reliability_flag": np.array([], dtype=bool),
        "total_pore_voxels": 0,
        "voxel_spacing": tuple(voxel_spacing),
    }


# ---------------------------------------------------------------------------
# EDT grid diagnostic
# ---------------------------------------------------------------------------

def _edt_theoretical_levels_um(
    voxel_spacing: Tuple[float, float, float],
    max_d_um: float,
    cap: int = 300,
) -> np.ndarray:
    """Sorted array of all theoretically possible EDT diameters in µm.

    Enumerates D = 2·sqrt((dz·sz)²+(dy·sy)²+(dx·sx)²) for non-negative
    integer steps (sz, sy, sx) up to *max_d_um*.
    """
    dz = float(voxel_spacing[0])
    dy = float(voxel_spacing[1])
    dx = float(voxel_spacing[2])
    nz_max = min(int(np.ceil(max_d_um / (2.0 * dz))) + 1, cap)
    ny_max = min(int(np.ceil(max_d_um / (2.0 * dy))) + 1, cap)
    nx_max = min(int(np.ceil(max_d_um / (2.0 * dx))) + 1, cap)
    nz_g, ny_g, nx_g = np.meshgrid(
        np.arange(nz_max + 1, dtype=np.float64),
        np.arange(ny_max + 1, dtype=np.float64),
        np.arange(nx_max + 1, dtype=np.float64),
        indexing="ij",
    )
    d_all = 2.0 * np.sqrt((dz * nz_g) ** 2 + (dy * ny_g) ** 2 + (dx * nx_g) ** 2)
    d_mask = (d_all > 0.0) & (d_all <= max_d_um * 1.05)
    return np.unique(np.round(d_all[d_mask], 4))


def _edt_grid_diagnostic(
    pore_diameters_um: np.ndarray,
    voxel_spacing: Tuple[float, float, float],
    psd_bin_centers_um: np.ndarray,
    psd_volume_counts: np.ndarray,
) -> Dict[str, Any]:
    """Compute grid-aware EDT bin diagnostic.

    Enumerates all theoretically possible EDT diameters:
        D = 2 * sqrt((dz*sz)^2 + (dy*sy)^2 + (dx*sx)^2)  [µm]
    for non-negative integer steps (sz, sy, sx), up to the observed max
    diameter.  These are the only diameters the integer EDT grid can produce.

    Returns a dict with:
        total_theoretical_levels      -- distinct possible EDT diameters
        total_bins                    -- number of natural (EDT-spaced) bins
        empty_bins                    -- bins with no pore voxels
        nonempty_bins                 -- bins with at least one pore voxel
        empty_fraction                -- empty_bins / total_bins
        main_psd_zero_count_bins      -- zero-count bins in the main PSD
        main_psd_zero_bins_in_structural_gaps
                                      -- of those, how many fall strictly
                                         between two consecutive EDT levels
                                         (structural gap, not a binning artefact)
        structural_gap_details        -- list of per-bin detail dicts
    """
    dz, dy, dx = (float(voxel_spacing[0]),
                  float(voxel_spacing[1]),
                  float(voxel_spacing[2]))

    if pore_diameters_um.size == 0:
        return {"error": "no pore voxels"}

    max_d = float(pore_diameters_um.max())
    theoretical_um = _edt_theoretical_levels_um(voxel_spacing, max_d)

    n_theoretical = int(theoretical_um.size)
    if n_theoretical < 2:
        return {
            "total_theoretical_levels": n_theoretical,
            "error": "too few theoretical levels to form bins",
        }

    # Bin edges midway between consecutive theoretical levels
    half_gaps = np.diff(theoretical_um) * 0.5
    bin_edges = np.concatenate([
        [max(0.0, theoretical_um[0] - half_gaps[0])],
        theoretical_um[:-1] + half_gaps,
        [theoretical_um[-1] + half_gaps[-1]],
    ])

    counts, _ = np.histogram(pore_diameters_um.astype(np.float64), bins=bin_edges)
    n_total_bins = int(counts.size)
    n_empty = int(np.sum(counts == 0))
    n_nonempty = n_total_bins - n_empty

    # Cross-check: which main-PSD zero-count bins fall in structural gaps
    zero_mask = np.asarray(psd_volume_counts) == 0
    zero_centers = np.asarray(psd_bin_centers_um)[zero_mask]
    structural_hits = 0
    gap_details: List[Dict[str, Any]] = []
    for zc in zero_centers:
        zc_f = float(zc)
        idx = int(np.searchsorted(theoretical_um, zc_f))
        if 0 < idx < n_theoretical:
            lo = float(theoretical_um[idx - 1])
            hi = float(theoretical_um[idx])
            structural_hits += 1
            gap_details.append({
                "psd_bin_um": round(zc_f, 2),
                "between_edt_levels": [round(lo, 2), round(hi, 2)],
                "gap_width_um": round(hi - lo, 2),
            })

    return {
        "total_theoretical_levels": n_theoretical,
        "total_bins": n_total_bins,
        "empty_bins": n_empty,
        "nonempty_bins": n_nonempty,
        "empty_fraction": round(n_empty / n_total_bins, 4) if n_total_bins > 0 else 0.0,
        "main_psd_zero_count_bins": int(zero_mask.sum()),
        "main_psd_zero_bins_in_structural_gaps": structural_hits,
        "structural_gap_details": gap_details,
    }


# ---------------------------------------------------------------------------
# Optional diagnostic plots
# ---------------------------------------------------------------------------

def plot_psd_extras(
    pore_diameters_um: np.ndarray,
    psd: Dict[str, Any],
    run_dir: Any,
    n_bins: int = 30,
    voxel_spacing: Optional[Tuple[float, float, float]] = None,
) -> List[str]:
    """Generate two supplementary diagnostic plots and save them to *run_dir*.

    Plots produced
    --------------
    psd_hist_30bins.png
        Differential PSD histogram with ``n_bins`` log-spaced bins.
        Bins that contain no theoretically possible EDT diameter (structural
        gaps) are drawn in red with hatching when *voxel_spacing* is supplied.
        X-axis shows readable µm tick labels.

    psd_kde.png
        KDE-smoothed diameter distribution (log-space Scott bandwidth,
        Jacobian-corrected to µm).  X-axis uses the same readable tick labels.

    Parameters
    ----------
    pore_diameters_um:
        1-D array of valid pore diameters in µm.
    psd:
        The ``result["psd"]`` sub-dict (metadata only).
    run_dir:
        Output directory path (str or Path).
    n_bins:
        Number of log-spaced bins for the histogram plot (default 30).
    voxel_spacing:
        Physical voxel spacing (dz, dy, dx) in µm.  When provided, structural
        EDT gaps are computed and highlighted on the histogram.

    Returns
    -------
    list[str]
        Absolute paths of the files written.  Empty if no pore voxels.
    """
    from pathlib import Path as _Path
    import matplotlib.pyplot as plt
    import matplotlib.ticker as _mticker
    from matplotlib.patches import Patch as _Patch
    from scipy.stats import gaussian_kde

    run_dir = _Path(run_dir)
    written: List[str] = []

    if pore_diameters_um.size == 0:
        warnings.warn(
            "plot_psd_extras: no pore diameters — plots skipped", UserWarning
        )
        return written

    d = pore_diameters_um.astype(np.float64)
    total = int(d.size)
    d_min, d_max = float(d.min()), float(d.max())

    # ── EDT gap detection ─────────────────────────────────────────────────
    theoretical_um: Optional[np.ndarray] = None
    if voxel_spacing is not None:
        try:
            theoretical_um = _edt_theoretical_levels_um(voxel_spacing, d_max)
        except Exception:
            theoretical_um = None

    def _is_gap(lo: float, hi: float) -> bool:
        if theoretical_um is None or theoretical_um.size == 0:
            return False
        return (
            int(np.searchsorted(theoretical_um, lo, side="left"))
            == int(np.searchsorted(theoretical_um, hi, side="right"))
        )

    # ── Readable x-axis helper ────────────────────────────────────────────
    def _apply_ticks(ax: object, xmin: float, xmax: float) -> None:
        ticks = sorted({
            float(m) * 10.0 ** e
            for e in range(-2, 6)
            for m in (1, 2, 3, 5)
            if xmin * 0.7 <= float(m) * 10.0 ** e <= xmax * 1.4
        })
        ax.set_xscale("log")  # type: ignore[attr-defined]
        ax.xaxis.set_major_locator(_mticker.FixedLocator(ticks))  # type: ignore
        ax.xaxis.set_major_formatter(  # type: ignore
            _mticker.FuncFormatter(lambda x, _: f"{x:.0f}")
        )
        ax.xaxis.set_minor_formatter(_mticker.NullFormatter())  # type: ignore
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")  # type: ignore

    # ── Plot 1: n_bins log-spaced histogram ──────────────────────────────
    edges = np.logspace(np.log10(max(d_min, 1e-9)), np.log10(d_max * 1.1), n_bins + 1)
    counts, _ = np.histogram(d, bins=edges)
    widths = np.diff(edges)
    diff_psd = counts / (total * widths)

    fig1, ax1 = plt.subplots(figsize=(10, 5))
    gap_labelled = False
    for i in range(n_bins):
        is_gap = _is_gap(float(edges[i]), float(edges[i + 1]))
        kw: Dict[str, Any] = dict(
            x=edges[i], height=diff_psd[i], width=widths[i], align="edge",
            linewidth=0.4,
        )
        if is_gap:
            kw.update(color="tomato", hatch="///", edgecolor="darkred")
            if not gap_labelled:
                kw["label"] = "No EDT level in bin"
                gap_labelled = True
        else:
            kw.update(color="steelblue", edgecolor="white")
        ax1.bar(**kw)

    legend_handles = [_Patch(facecolor="steelblue", label=f"{n_bins} log-spaced bins")]
    if theoretical_um is not None:
        legend_handles.append(
            _Patch(facecolor="tomato", hatch="///", edgecolor="darkred",
                   label="No EDT level in bin")
        )
    ax1.legend(handles=legend_handles, fontsize=9)
    _apply_ticks(ax1, d_min, d_max)
    ax1.set_xlabel("Pore diameter (µm)", fontsize=11)
    ax1.set_ylabel("Differential PSD  [µm⁻¹]", fontsize=11)
    ax1.set_title(
        f"PSD — {n_bins} log-spaced bins\n"
        f"n = {total:,} voxels,  range {d_min:.1f}–{d_max:.1f} µm",
        fontsize=10,
    )
    ax1.grid(axis="y", linestyle="--", alpha=0.4)
    fig1.tight_layout()
    p1 = run_dir / "psd_hist_30bins.png"
    fig1.savefig(p1, dpi=150)
    plt.close(fig1)
    written.append(str(p1))

    # ── Plot 2: KDE-smoothed distribution (log-space KDE) ────────────────
    log_d = np.log10(d)
    kde = gaussian_kde(log_d)  # Scott's rule bandwidth
    bw_log = float(kde.factor) * float(np.std(log_d))
    x_log = np.linspace(float(log_d.min()), float(log_d.max()), 500)
    x_um = 10.0 ** x_log
    # Jacobian: p(d) = f(log₁₀ d) / (d · ln 10)
    y_kde = kde(x_log) / (x_um * np.log(10.0))

    fig2, ax2 = plt.subplots(figsize=(10, 5))
    ax2.plot(x_um, y_kde, color="firebrick", linewidth=2,
             label="KDE (log-space, Scott's rule)")
    ax2.fill_between(x_um, y_kde, alpha=0.15, color="firebrick")
    _apply_ticks(ax2, d_min, d_max)
    ax2.set_xlabel("Pore diameter (µm)", fontsize=11)
    ax2.set_ylabel("Density  [µm⁻¹]", fontsize=11)
    ax2.set_title(
        f"KDE — pore diameter distribution\n"
        f"Scott bandwidth h = {bw_log:.4f} (log₁₀ scale),  "
        f"n = {total:,} voxels",
        fontsize=10,
    )
    ax2.legend(fontsize=9)
    ax2.grid(axis="y", linestyle="--", alpha=0.4)
    fig2.tight_layout()
    p2 = run_dir / "psd_kde.png"
    fig2.savefig(p2, dpi=150)
    plt.close(fig2)
    written.append(str(p2))

    return written


# ---------------------------------------------------------------------------
# Synthetic volume generator
# Preserved from legacy synthetic_volume.generate_non_overlapping_spheres
# ---------------------------------------------------------------------------

def _generate_non_overlapping_spheres(
    volume_shape: Tuple[int, int, int],
    voxel_spacing: Tuple[float, float, float],
    n_spheres: int,
    min_radius_um: float,
    max_radius_um: Optional[float],
    seed: Optional[int],
    max_attempts: int = 6000,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Create a binary volume populated with non-overlapping spheres.

    Uses a log-normal radius distribution (same as legacy) so the ground-truth
    PSD is smooth and continuous in physical units.  Sphere placement is in
    physical coordinates to honour anisotropic voxel spacing.
    """
    rng = np.random.default_rng(seed)
    volume_shape = tuple(int(d) for d in volume_shape)
    spacing = np.array(voxel_spacing, dtype=float)
    physical_extents = np.array(volume_shape, dtype=float) * spacing
    default_max = float(np.min(physical_extents) / 3.0)
    max_r = float(max_radius_um) if max_radius_um is not None else default_max
    if max_r <= min_radius_um:
        raise ValueError("max_radius_um must be larger than min_radius_um")

    def _sample_radius() -> float:
        value = float(rng.lognormal(mean=np.log(6.0), sigma=0.35))
        return float(np.clip(value, min_radius_um, max_r))

    def _sample_center(radius: float) -> np.ndarray:
        coords = []
        for extent in physical_extents:
            lo = radius
            hi = extent - radius
            if hi <= lo:
                return np.array([])
            coords.append(rng.uniform(lo, hi))
        return np.array(coords, dtype=float)

    placed_centers: List[np.ndarray] = []
    placed_radii: List[float] = []
    attempts = 0

    while len(placed_centers) < n_spheres and attempts < max_attempts:
        attempts += 1
        radius = _sample_radius()
        center = _sample_center(radius)
        if center.size == 0:
            continue
        overlap = any(
            np.linalg.norm(center - oc) < (radius + orr)
            for oc, orr in zip(placed_centers, placed_radii)
        )
        if overlap:
            continue
        placed_centers.append(center)
        placed_radii.append(radius)

    if len(placed_centers) < n_spheres:
        warnings.warn(
            f"Only placed {len(placed_centers)} spheres out of "
            f"requested {n_spheres}",
            UserWarning,
        )

    volume = np.zeros(volume_shape, dtype=bool)
    centers_arr = (
        np.array(placed_centers, dtype=float)
        if placed_centers
        else np.zeros((0, 3))
    )
    radii_arr = np.array(placed_radii, dtype=float)

    for center, radius in zip(centers_arr, radii_arr):
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

    return volume, radii_arr, centers_arr


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
            cumulative_volume, differential_volume, reliability_flag,
            total_pore_voxels, voxel_spacing

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
    n_reliable = int(psd["reliability_flag"].sum())
    n_total = int(psd["reliability_flag"].size)
    print(
        f"Reliable bins (d >= {_MIN_RELIABLE_DIAMETER_VOXELS} voxels): "
        f"{n_reliable}/{n_total}"
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
        "min_reliable_diameter_voxels": _MIN_RELIABLE_DIAMETER_VOXELS,
        "default_n_bins": _DEFAULT_N_BINS,
    }

    # Expose raw diameters at the top level so callers can generate optional
    # plots without touching the serialised PSD schema.
    pore_diameters_um: np.ndarray = psd.pop(
        "pore_diameters_um", np.array([], dtype=np.float64)
    )

    return {
        "psd": psd,
        "diagnostics": collector.data,
        "meta": meta,
        "pore_diameters_um": pore_diameters_um,
    }


# ---------------------------------------------------------------------------


def generate_synthetic_volume(
    *,
    shape: Tuple[int, int, int],
    voxel_spacing: Tuple[float, float, float],
    sphere_count: int = 40,
    seed: Optional[int] = None,
    min_radius_um: float = 5.0,
    max_radius_um: Optional[float] = None,
) -> Dict[str, Any]:
    """Generate a deterministic synthetic binary pore volume of non-overlapping
    spheres.

    Parameters
    ----------
    shape : (Z, Y, X) volume dimensions in voxels
    voxel_spacing : (dz, dy, dx) physical spacing in micrometers
    sphere_count : target number of spheres to place
    seed : RNG seed for reproducibility (None = non-deterministic)
    min_radius_um : minimum physical radius in micrometers
    max_radius_um : maximum physical radius; defaults to min_physical_dim / 3

    Returns
    -------
    dict with keys:

    ``volume``
        3-D bool ndarray (True = pore)

    ``ground_truth``
        Generator parameters and diameter statistics for downstream
        validation::

            shape, voxel_spacing, sphere_count_requested, seed,
            placed_count, radii_um, centers_um, diameter_stats
    """
    volume, radii_arr, centers_arr = _generate_non_overlapping_spheres(
        volume_shape=shape,
        voxel_spacing=voxel_spacing,
        n_spheres=sphere_count,
        min_radius_um=min_radius_um,
        max_radius_um=max_radius_um,
        seed=seed,
    )

    placed_count = int(radii_arr.size)
    if placed_count > 0:
        diameters = 2.0 * radii_arr
        diam_stats: Dict[str, Any] = {
            "count": placed_count,
            "min": float(diameters.min()),
            "max": float(diameters.max()),
            "mean": float(diameters.mean()),
            "median": float(np.median(diameters)),
            "std": float(diameters.std()),
        }
    else:
        diam_stats = {
            "count": 0,
            "min": 0.0,
            "max": 0.0,
            "mean": 0.0,
            "median": 0.0,
            "std": 0.0,
        }

    # Resolve the effective max_radius that was actually used
    _spacing_arr = np.array(voxel_spacing, dtype=float)
    _phys_extents = np.array(list(shape), dtype=float) * _spacing_arr
    _effective_max_radius = (
        float(max_radius_um)
        if max_radius_um is not None
        else float(np.min(_phys_extents) / 3.0)
    )

    ground_truth: Dict[str, Any] = {
        "shape": list(shape),
        "voxel_spacing": [float(v) for v in voxel_spacing],
        "sphere_count_requested": sphere_count,
        "seed": seed,
        "min_radius_um": float(min_radius_um),
        "max_radius_um": _effective_max_radius,
        "placed_count": placed_count,
        "radii_um": radii_arr.tolist(),
        "centers_um": centers_arr.tolist(),
        "diameter_stats": diam_stats,
    }

    return {"volume": volume, "ground_truth": ground_truth}


# ---------------------------------------------------------------------------


def compare_runs(
    result_a: Dict[str, Any],
    result_b: Dict[str, Any],
    *,
    label_a: str = "monolithic",
    label_b: str = "chunked",
) -> Dict[str, Any]:
    """Compare two ``run_psd_pipeline`` outputs for array equality and
    numerical differences.

    Required comparison arrays (contract §8.1):
        bin_centers_um, bin_edges_um, differential_volume, volume_counts

    Parameters
    ----------
    result_a, result_b : dicts returned by ``run_psd_pipeline``
    label_a, label_b   : human-readable labels for each run

    Returns
    -------
    dict matching the ``comparison.json`` schema (contract §4.8)::

        labels, exact_equal, array_comparisons, diagnostics_equal,
        max_abs_diff, nonzero_diff_counts, status
    """
    _COMPARE_KEYS = [
        "bin_centers_um",
        "bin_edges_um",
        "differential_volume",
        "volume_counts",
    ]
    _ATOL = 1e-12

    psd_a = result_a["psd"]
    psd_b = result_b["psd"]

    array_comparisons: Dict[str, Any] = {}
    all_exact = True
    global_max_diff = 0.0
    nonzero_diff_counts: Dict[str, int] = {}

    for key in _COMPARE_KEYS:
        arr_a = np.asarray(psd_a[key])
        arr_b = np.asarray(psd_b[key])
        shapes_match = arr_a.shape == arr_b.shape

        if shapes_match:
            exact_eq = bool(np.array_equal(arr_a, arr_b))
            if np.issubdtype(arr_a.dtype, np.floating):
                diff = np.abs(
                    arr_a.astype(np.float64) - arr_b.astype(np.float64)
                )
                max_diff = float(diff.max()) if diff.size else 0.0
                nz = int(np.sum(diff > _ATOL))
            else:
                not_equal = arr_a != arr_b
                max_diff = float(np.sum(not_equal))
                nz = int(not_equal.sum())
        else:
            exact_eq = False
            max_diff = float("nan")
            nz = -1

        if not exact_eq:
            all_exact = False
        if np.isfinite(max_diff) and max_diff > global_max_diff:
            global_max_diff = max_diff
        nonzero_diff_counts[key] = nz

        array_comparisons[key] = {
            "shape_a": list(arr_a.shape),
            "shape_b": list(arr_b.shape),
            "shapes_match": shapes_match,
            "exact_equal": exact_eq,
            "max_abs_diff": max_diff,
            "nonzero_diff_count": nz,
        }

    # Diagnostics equality: stage keys present in both runs must match
    stages_a = result_a.get("diagnostics", {}).get("stages", {})
    stages_b = result_b.get("diagnostics", {}).get("stages", {})
    diagnostics_equal = set(stages_a.keys()) == set(stages_b.keys())

    status = "identical" if (all_exact and diagnostics_equal) else "differ"

    return {
        "labels": [label_a, label_b],
        "exact_equal": all_exact,
        "array_comparisons": array_comparisons,
        "diagnostics_equal": diagnostics_equal,
        "max_abs_diff": global_max_diff,
        "nonzero_diff_counts": nonzero_diff_counts,
        "status": status,
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
    "is_reliable",
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
                "is_reliable": bool(psd["reliability_flag"][i]),
            }
        )
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
    mode     : execution mode string, e.g. ``'real'`` or ``'synthetic'``
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
