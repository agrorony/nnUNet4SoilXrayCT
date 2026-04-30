"""PSD diagnostics runner — CLI entrypoint for two modes.

Usage
-----
real mode::

    python run_psd_diagnostics.py real \\
        --input /path/to/volume.npy \\
        --voxel-spacing 2.0 1.0 1.0 \\
        --output-root /path/to/results \\
        [--run-name scan_001] \\
        [--no-exclude-borders] \\
        [--bin-edges-json '[1,2,4,8,16]'] \\
        [--use-chunking] \\
        [--chunk-size 128 128 128] \\
        [--halo-width 50] \\
        [--no-gpu]

synthetic mode::

    python run_psd_diagnostics.py synthetic \\
        --output-root /path/to/results \\
        [--run-name my_test] \\
        [--shape 80 80 80] \\
        [--voxel-spacing 1.0 1.0 1.0] \\
        [--sphere-count 40] \\
        [--seed 42] \\
        [--min-radius-um 5.0] \\
        [--chunk-size 64 64 64] \\
        [--halo-width 32] \\
        [--no-gpu]

Output
------
One run folder per execution::

    <output-root>/psd_diag_<timestamp>_<run-name>/
        config.json
        result_psd.json
        diagnostics.json
        summary.json
        psd_table.csv
        comparison.json   (synthetic only)
        ground_truth.json (synthetic only)
"""

from __future__ import annotations

import argparse
# =============================================================================
# Runtime dependencies and version constraints
# =============================================================================
# This script calls psd_diagnostics_core, which uses porespy + numba.
# The numpy version constraint is INHERITED from that module.
#
# Package        Constraint               Reason
# -------------- ------------------------ ------------------------------------
# numpy          >= 1.22, <= 2.3          numba 0.63.x upper-bound (via
#                                         psd_diagnostics_core -> porespy)
# porespy        >= 3.0.4                 required by psd_diagnostics_core
# scikit-image   >= 0.26.0               0.25.x segmentation DLL crash on Win
# scipy          any modern               used by psd_diagnostics_core
# =============================================================================

import csv
import json
import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Non-interactive backend — must be set before any pyplot import.
# plot_psd_extras (in psd_diagnostics_core) imports pyplot lazily;
# this call ensures Agg is active before that happens.
import matplotlib
matplotlib.use("Agg")

# ---------------------------------------------------------------------------
# Import core; abort immediately if unavailable
# ---------------------------------------------------------------------------
try:
    from psd_diagnostics_core import (
        PSD_TABLE_COLUMNS,
        build_psd_table,
        build_summary,
        compare_runs,
        generate_synthetic_volume,
        plot_psd_extras,
        run_psd_pipeline,
        to_json_serializable,
    )
except ImportError as _exc:  # pragma: no cover
    print(
        f"ERROR: cannot import psd_diagnostics_core: {_exc}",
        file=sys.stderr,
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# Output file names (single source of truth — §4.1 / §4.2)
# ---------------------------------------------------------------------------
_F_CONFIG = "config.json"
_F_RESULT = "result_psd.json"
_F_DIAG = "diagnostics.json"
_F_SUMMARY = "summary.json"
_F_TABLE = "psd_table.csv"
_F_COMPARISON = "comparison.json"          # synthetic only
_F_GROUND_TRUTH = "ground_truth.json"      # synthetic only
_F_PLOT_HIST = "psd_hist_30bins.png"       # supplementary diagnostic plot
_F_PLOT_KDE = "psd_kde.png"               # supplementary diagnostic plot


# ===========================================================================
# Volume I/O helpers
# ===========================================================================

def _load_volume(path: Path) -> np.ndarray:
    """Load a 3-D binary volume from .npy or .tif/.tiff.

    Raises SystemExit(1) on error; writes structured message to stderr.
    """
    suffix = path.suffix.lower()
    try:
        if suffix == ".npy":
            vol = np.load(str(path))
        elif suffix in (".tif", ".tiff"):
            try:
                import tifffile
                vol = tifffile.imread(str(path))
            except ImportError:
                _fail(
                    f"tifffile is required to load .tif volumes: "
                    f"pip install tifffile"
                )
        else:
            _fail(
                f"Unsupported volume format '{suffix}'. "
                f"Supported: .npy, .tif, .tiff"
            )
    except FileNotFoundError:
        _fail(f"Input volume not found: {path}")
    except Exception as exc:
        _fail(f"Failed to load volume from {path}: {exc}")

    if vol.ndim != 3:
        _fail(
            f"Volume must be 3-D, got shape {vol.shape} from {path}"
        )
    return vol


# ===========================================================================
# Fail-fast error handler  (§3.4)
# ===========================================================================

def _fail(msg: str) -> None:
    """Write structured error to stderr and exit non-zero immediately."""
    print(json.dumps({"error": msg}), file=sys.stderr)
    sys.exit(1)


# ===========================================================================
# Run-folder creation  (§4 naming)
# ===========================================================================

def _make_run_dir(output_root: Path, run_name: str, ts: str) -> Path:
    """Create and return <output_root>/psd_diag_<ts>_<run_name>/."""
    folder_name = f"psd_diag_{ts}_{run_name}"
    run_dir = output_root / folder_name
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _safe_name(raw: str) -> str:
    """Sanitise run_name to filesystem-safe characters."""
    return "".join(c if c.isalnum() or c in "_-" else "_" for c in raw)


# ===========================================================================
# Writers  (§4 output contract)
# ===========================================================================

def _write_json(run_dir: Path, filename: str, data: Any) -> None:
    path = run_dir / filename
    with path.open("w", encoding="utf-8") as fh:
        json.dump(to_json_serializable(data), fh, indent=2)


def _write_plots(run_dir: Path, result: Dict[str, Any]) -> List[str]:
    """Generate psd_hist_30bins.png and psd_kde.png into *run_dir*."""
    pore_diameters_um = result.get("pore_diameters_um", np.array([], dtype=np.float64))
    voxel_spacing = result["psd"].get("voxel_spacing")
    return plot_psd_extras(
        pore_diameters_um, result["psd"], run_dir, voxel_spacing=voxel_spacing
    )


def _write_csv(run_dir: Path, rows: List[Dict[str, Any]]) -> None:
    """Write psd_table.csv with columns in §4.6 order."""
    path = run_dir / _F_TABLE
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(PSD_TABLE_COLUMNS))
        writer.writeheader()
        writer.writerows(rows)


def _write_all_outputs(
    run_dir: Path,
    *,
    config: Dict[str, Any],
    result: Dict[str, Any],
    mode: str,
    run_name: str,
    timestamp: str,
) -> None:
    """Write the 5 files required for every run (§4.1)."""

    # config.json
    _write_json(run_dir, _F_CONFIG, config)

    # result_psd.json  — add §4.3 scalar fields
    psd_payload = dict(result["psd"])
    psd_payload["mode"] = mode
    psd_payload["run_name"] = run_name
    psd_payload["timestamp"] = timestamp
    _write_json(run_dir, _F_RESULT, psd_payload)

    # diagnostics.json  (§4.4 keys already present from core)
    _write_json(run_dir, _F_DIAG, result["diagnostics"])

    # summary.json  (§4.7)
    summary = build_summary(result, mode=mode, run_name=run_name)
    _write_json(run_dir, _F_SUMMARY, summary)

    # psd_table.csv  (§4.6)
    _write_csv(run_dir, build_psd_table(result))

    # supplementary diagnostic plots
    _write_plots(run_dir, result)


# ===========================================================================
# Real mode  (§3.5 / §4 / §7)
# ===========================================================================

def _run_real(args: argparse.Namespace) -> None:
    input_path = Path(args.input)
    if not input_path.exists():
        _fail(f"Input path does not exist: {input_path}")

    # Parse and validate voxel spacing
    try:
        spacing: Tuple[float, float, float] = tuple(
            float(v) for v in args.voxel_spacing
        )
    except (TypeError, ValueError) as exc:
        _fail(f"Invalid --voxel-spacing: {exc}")

    if len(spacing) != 3:
        _fail(
            f"--voxel-spacing requires exactly 3 values, got {len(spacing)}"
        )
    if any(v <= 0 for v in spacing):
        _fail(f"All voxel-spacing values must be positive, got {spacing}")

    # Parse optional bin edges
    bin_edges_um: Optional[np.ndarray] = None
    if args.bin_edges_json:
        try:
            raw_edges = json.loads(args.bin_edges_json)
            bin_edges_um = np.array(raw_edges, dtype=np.float64)
        except (json.JSONDecodeError, ValueError) as exc:
            _fail(f"Invalid --bin-edges-json: {exc}")

    # Load volume
    vol = _load_volume(input_path)

    # Chunking params
    chunk_size: Tuple[int, int, int] = tuple(int(c) for c in args.chunk_size)
    halo_width: int = int(args.halo_width)

    # Identify run
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    run_name = _safe_name(args.run_name) if args.run_name else "real"
    output_root = Path(args.output_root)

    config: Dict[str, Any] = {
        "mode": "real",
        "run_name": run_name,
        "timestamp": ts,
        "input": str(input_path.resolve()),
        "voxel_spacing": list(spacing),
        "exclude_borders": not args.no_exclude_borders,
        "use_chunking": args.use_chunking,
        "chunk_size": list(chunk_size),
        "halo_width": halo_width,
        "bin_edges_um_input": bin_edges_um.tolist() if bin_edges_um is not None else None,
        "use_gpu": not args.no_gpu,
    }

    # Run pipeline
    with warnings.catch_warnings(record=True) as caught_warnings:
        warnings.simplefilter("always")
        result = run_psd_pipeline(
            vol,
            spacing,
            use_chunking=args.use_chunking,
            chunk_size=chunk_size,
            halo_width=halo_width,
            exclude_borders=not args.no_exclude_borders,
            bin_edges_um=bin_edges_um,
            use_gpu=not args.no_gpu,
            diagnostics_cfg={"run_tag": run_name},
        )

    if caught_warnings:
        config["warnings"] = [str(w.message) for w in caught_warnings]

    # Write outputs
    run_dir = _make_run_dir(output_root, run_name, ts)
    _write_all_outputs(
        run_dir,
        config=config,
        result=result,
        mode="real",
        run_name=run_name,
        timestamp=ts,
    )

    # Console summary
    psd = result["psd"]
    print(f"\nRun directory: {run_dir}")
    print(f"Total pore voxels: {psd['total_pore_voxels']:,}")
    if psd["bin_centers_um"].size > 0:
        print(
            f"Diameter range: {float(psd['bin_centers_um'].min()):.2f}"
            f" – {float(psd['bin_centers_um'].max()):.2f} µm"
        )
    n_reliable = int(psd["reliability_flag"].sum())
    print(f"Reliable bins: {n_reliable}/{len(psd['reliability_flag'])}")
    print("Files written:")
    for f in (_F_CONFIG, _F_RESULT, _F_DIAG, _F_SUMMARY, _F_TABLE,
              _F_PLOT_HIST, _F_PLOT_KDE):
        print(f"  {f}")


# ===========================================================================
# Synthetic mode  (§7 / §8 — both paths mandatory)
# ===========================================================================

def _run_synthetic(args: argparse.Namespace) -> None:
    # Parse spacing
    try:
        spacing: Tuple[float, float, float] = tuple(
            float(v) for v in args.voxel_spacing
        )
    except (TypeError, ValueError) as exc:
        _fail(f"Invalid --voxel-spacing: {exc}")

    if len(spacing) != 3:
        _fail(
            f"--voxel-spacing requires exactly 3 values, got {len(spacing)}"
        )
    if any(v <= 0 for v in spacing):
        _fail(f"All voxel-spacing values must be positive, got {spacing}")

    # Parse shape
    try:
        shape: Tuple[int, int, int] = tuple(int(d) for d in args.shape)
    except (TypeError, ValueError) as exc:
        _fail(f"Invalid --shape: {exc}")
    if len(shape) != 3 or any(d <= 0 for d in shape):
        _fail(f"--shape requires 3 positive integers, got {args.shape}")

    sphere_count = int(args.sphere_count)
    seed: Optional[int] = int(args.seed) if args.seed is not None else None
    min_radius_um = float(args.min_radius_um)

    chunk_size: Tuple[int, int, int] = tuple(int(c) for c in args.chunk_size)
    halo_width: int = int(args.halo_width)

    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    run_name = _safe_name(args.run_name) if args.run_name else "synthetic"
    output_root = Path(args.output_root)
    use_gpu = not args.no_gpu

    config: Dict[str, Any] = {
        "mode": "synthetic",
        "run_name": run_name,
        "timestamp": ts,
        "shape": list(shape),
        "voxel_spacing": list(spacing),
        "sphere_count": sphere_count,
        "seed": seed,
        "min_radius_um": min_radius_um,
        "use_chunking_chunked_run": True,
        "chunk_size": list(chunk_size),
        "halo_width": halo_width,
        "use_gpu": use_gpu,
    }

    # Generate synthetic volume (deterministic)
    synth = generate_synthetic_volume(
        shape=shape,
        voxel_spacing=spacing,
        sphere_count=sphere_count,
        seed=seed,
        min_radius_um=min_radius_um,
    )
    vol: np.ndarray = synth["volume"]
    ground_truth: Dict[str, Any] = synth["ground_truth"]

    # §7.3 — both monolithic and chunked paths are mandatory
    print("\n[Synthetic] Running monolithic pipeline...")
    result_mono = run_psd_pipeline(
        vol,
        spacing,
        use_chunking=False,
        use_gpu=use_gpu,
        diagnostics_cfg={"run_tag": f"{run_name}_monolithic"},
    )

    print("\n[Synthetic] Running chunked pipeline...")
    result_chunked = run_psd_pipeline(
        vol,
        spacing,
        use_chunking=True,
        chunk_size=chunk_size,
        halo_width=halo_width,
        use_gpu=use_gpu,
        diagnostics_cfg={"run_tag": f"{run_name}_chunked"},
    )

    # §8 — mandatory comparison
    comparison = compare_runs(
        result_mono,
        result_chunked,
        label_a="monolithic",
        label_b="chunked",
    )

    # Write outputs
    run_dir = _make_run_dir(output_root, run_name, ts)

    # 5 common files (using monolithic result as the canonical result)
    _write_all_outputs(
        run_dir,
        config=config,
        result=result_mono,
        mode="synthetic",
        run_name=run_name,
        timestamp=ts,
    )

    # ground_truth.json  (§4.2 / §7.2)
    _write_json(run_dir, _F_GROUND_TRUTH, ground_truth)

    # comparison.json  (§4.2 / §4.8)
    _write_json(run_dir, _F_COMPARISON, comparison)

    # Console summary
    psd = result_mono["psd"]
    print(f"\nRun directory: {run_dir}")
    print(f"Placed spheres: {ground_truth['placed_count']}")
    print(f"Total pore voxels: {psd['total_pore_voxels']:,}")
    if psd["bin_centers_um"].size > 0:
        print(
            f"Diameter range: {float(psd['bin_centers_um'].min()):.2f}"
            f" – {float(psd['bin_centers_um'].max()):.2f} µm"
        )
    print(
        f"Mono vs chunked: {comparison['status']} "
        f"(exact_equal={comparison['exact_equal']})"
    )
    print("Files written:")
    for f in (_F_CONFIG, _F_RESULT, _F_DIAG, _F_SUMMARY, _F_TABLE,
              _F_GROUND_TRUTH, _F_COMPARISON,
              _F_PLOT_HIST, _F_PLOT_KDE):
        print(f"  {f}")


# ===========================================================================
# Argument parser
# ===========================================================================

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_psd_diagnostics",
        description="PSD diagnostics runner (real and synthetic modes).",
    )
    sub = parser.add_subparsers(dest="mode", required=True)

    # ------------------------------------------------------------------ real
    p_real = sub.add_parser("real", help="Run diagnostics on a real binary volume.")
    p_real.add_argument(
        "--input", required=True,
        help="Path to 3-D binary volume (.npy or .tif).",
    )
    p_real.add_argument(
        "--voxel-spacing", nargs=3, type=float, required=True,
        metavar=("DZ", "DY", "DX"),
        help="Physical voxel spacing in µm, order: dz dy dx.",
    )
    p_real.add_argument(
        "--output-root", required=True,
        help="Parent directory for run-folder output.",
    )
    p_real.add_argument("--run-name", default=None, help="Optional run identifier.")
    p_real.add_argument(
        "--no-exclude-borders", action="store_true",
        help="Disable 1-voxel border exclusion (default: borders excluded).",
    )
    p_real.add_argument(
        "--bin-edges-json", default=None,
        help="JSON array of custom bin edges in µm, e.g. '[2,4,8,16,32]'.",
    )
    p_real.add_argument(
        "--use-chunking", action="store_true",
        help="Use block-chunked EDT (default: monolithic).",
    )
    p_real.add_argument(
        "--chunk-size", nargs=3, type=int, default=[128, 128, 128],
        metavar=("CZ", "CY", "CX"),
        help="Core chunk size before halo padding (default: 128 128 128).",
    )
    p_real.add_argument(
        "--halo-width", type=int, default=50,
        help="Halo padding in voxels for chunked EDT (default: 50).",
    )
    p_real.add_argument(
        "--no-gpu", action="store_true",
        help="Disable GPU acceleration (force CPU).",
    )

    # ------------------------------------------------------------ synthetic
    p_syn = sub.add_parser(
        "synthetic",
        help="Generate a synthetic volume and run monolithic + chunked pipelines.",
    )
    p_syn.add_argument(
        "--output-root", required=True,
        help="Parent directory for run-folder output.",
    )
    p_syn.add_argument("--run-name", default=None, help="Optional run identifier.")
    p_syn.add_argument(
        "--shape", nargs=3, type=int, default=[80, 80, 80],
        metavar=("Z", "Y", "X"),
        help="Volume dimensions in voxels (default: 80 80 80).",
    )
    p_syn.add_argument(
        "--voxel-spacing", nargs=3, type=float, default=[1.0, 1.0, 1.0],
        metavar=("DZ", "DY", "DX"),
        help="Physical voxel spacing in µm (default: 1.0 1.0 1.0).",
    )
    p_syn.add_argument(
        "--sphere-count", type=int, default=40,
        help="Target number of non-overlapping spheres (default: 40).",
    )
    p_syn.add_argument(
        "--seed", type=int, default=None,
        help="RNG seed for reproducibility.",
    )
    p_syn.add_argument(
        "--min-radius-um", type=float, default=5.0,
        help="Minimum sphere radius in µm (default: 5.0).",
    )
    p_syn.add_argument(
        "--chunk-size", nargs=3, type=int, default=[64, 64, 64],
        metavar=("CZ", "CY", "CX"),
        help="Core chunk size for chunked pipeline run (default: 64 64 64).",
    )
    p_syn.add_argument(
        "--halo-width", type=int, default=32,
        help="Halo width in voxels for chunked pipeline run (default: 32).",
    )
    p_syn.add_argument(
        "--no-gpu", action="store_true",
        help="Disable GPU acceleration (force CPU).",
    )

    return parser


# ===========================================================================
# Entrypoint
# ===========================================================================

def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.mode == "real":
        _run_real(args)
    elif args.mode == "synthetic":
        _run_synthetic(args)
    else:
        _fail(f"Unknown mode: {args.mode}")


if __name__ == "__main__":
    main()
