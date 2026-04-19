"""Observability helpers for the PSD pipeline."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

DEFAULT_HIST_BINS = 64
DEFAULT_LOW_COUNT_THRESHOLD = 5
DEFAULT_SPIKE_MULTIPLIER = 5.0
DEFAULT_INTEGER_TOLERANCE = 1e-6
DEFAULT_OUTPUT_STEM = "psd_diagnostics"


def _to_scalar(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    return value


def _flatten_numeric(values: Sequence[float]) -> np.ndarray:
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


def _format_head_tail(values: Sequence[float], limit: int = 3) -> Tuple[List[float], List[float]]:
    arr = list(values)
    head = arr[:limit]
    tail = arr[-limit:]
    return head, tail


def _flatten_dict(data: Dict[str, Any]) -> Iterable[Tuple[str, str]]:
    for key, value in data.items():
        if isinstance(value, dict):
            for sub_key, sub_value in _flatten_dict(value):
                yield f"{key}.{sub_key}", sub_value
        else:
            yield key, value


class DiagnosticsCollector:
    def __init__(self, config: Optional[Dict[str, Any]] = None, default_tag: Optional[str] = None):
        cfg = config or {}
        self.enabled = bool(cfg.get("enabled"))
        if not self.enabled:
            self.hist_bins = DEFAULT_HIST_BINS
            self.low_count_threshold = DEFAULT_LOW_COUNT_THRESHOLD
            self.spike_multiplier = DEFAULT_SPIKE_MULTIPLIER
            self.save_json = False
            self.save_csv = False
            self.output_dir = None
            self.run_tag = default_tag or "psd"
            self.data: Dict[str, Any] = {}
            return

        self.hist_bins = int(cfg.get("hist_bins", DEFAULT_HIST_BINS))
        self.low_count_threshold = int(cfg.get("low_count_threshold", DEFAULT_LOW_COUNT_THRESHOLD))
        self.spike_multiplier = float(cfg.get("spike_multiplier", DEFAULT_SPIKE_MULTIPLIER))
        self.save_json = bool(cfg.get("save_json", True))
        self.save_csv = bool(cfg.get("save_csv", False))
        output_dir = cfg.get("output_dir")
        self.output_dir = Path(output_dir) if output_dir else None
        tag = cfg.get("run_tag") or default_tag
        if tag:
            safe_tag = ''.join(c if c.isalnum() or c in "_-" else "_" for c in tag)
        else:
            safe_tag = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
        self.run_tag = safe_tag
        self.data = {
            "run_tag": self.run_tag,
            "created": datetime.utcnow().isoformat(),
            "config": {
                "hist_bins": self.hist_bins,
                "low_count_threshold": self.low_count_threshold,
                "spike_multiplier": self.spike_multiplier,
            },
            "stages": {},
        }

    def record_metadata(self, **meta: Any) -> None:
        if not self.enabled:
            return
        meta = {k: _to_scalar(v) for k, v in meta.items()}
        self.data.setdefault("metadata", {}).update(meta)

    def record_stage(self, stage: str, payload: Dict[str, Any]) -> None:
        if not self.enabled:
            return
        self.data["stages"][stage] = payload

    def log_edt_map(self, edt_map: np.ndarray, voxel_spacing: Tuple[float, float, float]) -> None:
        if not self.enabled:
            return
        values = _flatten_numeric(edt_map)
        hist = _histogram(values, self.hist_bins)
        unique_count = int(np.unique(values).size) if values.size else 0
        integer_like = bool(np.max(np.abs(values - np.round(values))) < DEFAULT_INTEGER_TOLERANCE) if values.size else True
        stats = _array_stats(values)
        payload = {
            "stats": stats,
            "unique_count": unique_count,
            "integer_like": integer_like,
            "voxel_spacing": tuple(float(v) for v in voxel_spacing),
            "histogram": hist,
        }
        print("\n[Diagnostics] EDT map")
        print(f"  Range: {stats['min']:.4f} - {stats['max']:.4f}")
        print(f"  Unique values: {unique_count}, integer-like: {integer_like}")
        print(f"  Histogram bins: {self.hist_bins}, counts head {hist['counts_head']}, tail {hist['counts_tail']}")
        self.record_stage("edt", payload)

    def log_opening_map(self, opening_map: np.ndarray) -> None:
        if not self.enabled:
            return
        values = _flatten_numeric(opening_map)
        hist = _histogram(values, self.hist_bins)
        unique_values, counts = np.unique(values, return_counts=True)
        total = float(counts.sum()) if counts.size else 0.0
        fractions = (counts / total) if total else np.zeros_like(counts, dtype=float)
        top_idx = np.argsort(counts)[::-1][:5]
        top_values = [
            {
                "diameter": float(unique_values[idx]),
                "count": int(counts[idx]),
                "fraction": float(fractions[idx]) if total else 0.0,
            }
            for idx in top_idx
            if counts[idx]
        ]
        payload = {
            "unique_diameter_count": int(unique_values.size),
            "top_diameter_fractions": top_values,
            "histogram": hist,
        }
        print("\n[Diagnostics] Opening map")
        print(f"  Unique diameters: {payload['unique_diameter_count']}")
        print(f"  Top diameter fractions: {top_values}")
        print(f"  Histogram bins: {self.hist_bins}, counts head {hist['counts_head']}")
        self.record_stage("opening", payload)

    def log_raw_diameters(self, pore_diameters: np.ndarray) -> None:
        if not self.enabled:
            return
        values = _flatten_numeric(pore_diameters)
        stats = _array_stats(values)
        unique_values, counts = np.unique(values, return_counts=True)
        repeat_bins = int(np.sum(counts > 1))
        repeat_details = [
            {"diameter": float(unique_values[idx]), "count": int(counts[idx])}
            for idx in np.argsort(counts)[::-1][:5]
            if counts[idx] > 1
        ]
        hist = _histogram(values, self.hist_bins)
        payload = {
            "stats": stats,
            "repeat_bin_count": repeat_bins,
            "repeat_summary": repeat_details,
            "histogram": hist,
        }
        print("\n[Diagnostics] Raw pore diameters")
        print(f"  Count: {int(stats['count'])}, range: {stats['min']:.4f} - {stats['max']:.4f}")
        print(f"  Repeated diameters (>1): {repeat_bins}, samples: {repeat_details}")
        print(f"  Histogram bins: {self.hist_bins}, counts head {hist['counts_head']}")
        self.record_stage("raw_diameters", payload)

    def log_binning(
        self,
        volume_counts: np.ndarray,
        bin_edges_px: np.ndarray,
        bin_edges_um: np.ndarray,
    ) -> None:
        if not self.enabled:
            return
        counts = np.asarray(volume_counts, dtype=np.int64)
        empty_bins = int(np.sum(counts == 0))
        low_count_bins = int(np.sum(counts < self.low_count_threshold))
        bin_widths = np.diff(bin_edges_um)
        zero_width_bins = int(np.sum(bin_widths <= 0))
        highlights = {
            "bins": [],
        }
        payload = {
            "bin_edges_px": bin_edges_px.tolist(),
            "bin_edges_um": bin_edges_um.tolist(),
            "bin_widths_um": bin_widths.tolist(),
            "bin_counts": counts.tolist(),
            "empty_bins": empty_bins,
            "low_count_bins": low_count_bins,
            "zero_width_bins": zero_width_bins,
            "low_count_threshold": self.low_count_threshold,
        }
        print("\n[Diagnostics] Bin edges")
        head_px, tail_px = _format_head_tail(bin_edges_px)
        head_um, tail_um = _format_head_tail(bin_edges_um)
        print(f"  Bin edges (px): {head_px} ... {tail_px}")
        print(f"  Bin edges (um): {head_um} ... {tail_um}")
        print(f"  Bin width (um): min {bin_widths.min():.4e}, max {bin_widths.max():.4e}, zero-width bins: {zero_width_bins}")
        print(f"  Empty bins: {empty_bins}, low-count bins (< {self.low_count_threshold}): {low_count_bins}")
        if zero_width_bins:
            widths = np.where(bin_widths <= 0)[0].tolist()
            print(f"    Zero-width indices: {widths}")
        self.record_stage("binning", payload)

    def log_post_psd(self, differential_volume: np.ndarray, bin_centers_um: np.ndarray) -> None:
        if not self.enabled:
            return
        values = np.asarray(differential_volume, dtype=np.float64)
        nan_mask = np.isnan(values)
        inf_mask = np.isinf(values)
        finite_mask = np.isfinite(values)
        finite_values = values[finite_mask]
        stats = _array_stats(finite_values)
        median = float(np.median(finite_values)) if finite_values.size else 0.0
        mad = float(np.median(np.abs(finite_values - median))) if finite_values.size else 0.0
        threshold = median + self.spike_multiplier * (mad or 1.0)
        spike_indices = [int(idx) for idx in np.where(values > threshold)[0]]
        spike_details = [
            {
                "bin_index": idx,
                "bin_center_um": float(bin_centers_um[idx]) if idx < len(bin_centers_um) else None,
                "value": float(values[idx]),
            }
            for idx in spike_indices
        ]
        payload = {
            "stats": stats,
            "nan_count": int(np.sum(nan_mask)),
            "inf_count": int(np.sum(inf_mask)),
            "spike_threshold": threshold,
            "spikes": spike_details,
        }
        print("\n[Diagnostics] Differential PSD")
        print(f"  Finite bins: {int(finite_values.size)}, NaNs: {payload['nan_count']}, Infs: {payload['inf_count']}")
        print(f"  Median: {median:.4e}, MAD: {mad:.4e}, Spike threshold: {threshold:.4e}")
        if spike_details:
            print(f"  Spikes detected at indices: {[item['bin_index'] for item in spike_details]}")
        self.record_stage("post_psd", payload)

    def flush(self) -> None:
        if not self.enabled or not self.output_dir or not (self.save_json or self.save_csv):
            return
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if self.save_json:
            json_path = self.output_dir / f"{self.run_tag}_diagnostics.json"
            with json_path.open("w", encoding="utf-8") as fh:
                json.dump(self.data, fh, indent=2)
            print(f"Diagnostics JSON saved: {json_path}")
        if self.save_csv:
            csv_dir = self.output_dir / "csv"
            csv_dir.mkdir(parents=True, exist_ok=True)
            for stage, payload in self.data.get("stages", {}).items():
                csv_path = csv_dir / f"{self.run_tag}_{stage}.csv"
                with csv_path.open("w", newline="", encoding="utf-8") as fh:
                    writer = csv.writer(fh)
                    writer.writerow(["key", "value"])
                    for key, value in _flatten_dict(payload):
                        writer.writerow([key, json.dumps(value)])
            print(f"Diagnostics CSV saved to: {csv_dir}")
