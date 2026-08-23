"""Chunked, checkpointed batch runner for run_psd_diagnostics.py over full volumes.

Loops over the volumes listed in a manifest JSON (one entry per already-segmented
full volume, no cropping), and for each one not yet completed, invokes
``run_psd_diagnostics.py extended --use-chunking`` as a subprocess. Progress is
checkpointed after every volume, so re-running this script after a crash or
interruption skips volumes already marked "done" and resumes at the next one.

This script does NOT chunk *within* a volume — that spatial EDT chunking
(_BlockProcessor, ported from legacy/pores_analysis/block_processor.py) already
lives in psd_diagnostics_core.py and is reached via run_psd_diagnostics.py's own
--use-chunking/--chunk-size/--halo-width flags, which this script simply passes
through. "Chunked" here means the volumes in the manifest are processed one at a
time as isolated subprocesses; "checkpointed" means the batch remembers which
volumes are already done.

Usage
-----
::

    python run_psd_batch.py                          # run all enabled, non-done volumes
    python run_psd_batch.py --dry-run                 # print commands, do nothing
    python run_psd_batch.py --only nlm_volume_fresh_bnei_reem_i4
    python run_psd_batch.py --force                   # re-run even if marked done
    python run_psd_batch.py --retry-failed             # re-run only failed volumes
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

BATCH_DIR = Path(__file__).resolve().parent / "full_volume_batch"
DEFAULT_MANIFEST = BATCH_DIR / "manifest.json"
DEFAULT_CHECKPOINT = BATCH_DIR / "checkpoint.json"
DEFAULT_LOGS_DIR = BATCH_DIR / "logs"
DEFAULT_OUTPUT_ROOT = (
    r"\\hive3065\Yael_Mishael\Rony\remote_computer backup\10.5\psd_outputs"
)
RUN_PSD_SCRIPT = Path(__file__).resolve().parent / "run_psd_diagnostics.py"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _save_json_atomic(path: Path, data: Dict[str, Any]) -> None:
    """Write via temp file + rename so a crash mid-write can't corrupt checkpoint.json."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with open(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def _build_command(
    entry: Dict[str, Any],
    args: argparse.Namespace,
) -> List[str]:
    spacing = entry["voxel_spacing_um"]
    cmd = [
        sys.executable,
        str(RUN_PSD_SCRIPT),
        "extended",
        "--input", entry["input"],
        "--pore-label", str(args.pore_label),
        "--pom-label", *[str(v) for v in args.pom_label],
        "--voxel-spacing", *[str(v) for v in spacing],
        "--output-root", args.output_root,
        "--run-name", entry["name"],
        "--n-anisotropy-directions", str(args.n_anisotropy_directions),
    ]
    if args.use_chunking:
        cmd += [
            "--use-chunking",
            "--chunk-size", *[str(v) for v in args.chunk_size],
            "--halo-width", str(args.halo_width),
        ]
    if args.no_gpu:
        cmd.append("--no-gpu")
    return cmd


def _parse_run_dir(log_lines: List[str]) -> Optional[str]:
    for line in log_lines:
        if line.startswith("Run directory:"):
            return line.split("Run directory:", 1)[1].strip()
    return None


def _run_one(entry: Dict[str, Any], args: argparse.Namespace, log_path: Path) -> Dict[str, Any]:
    cmd = _build_command(entry, args)
    started_at = _now_iso()
    t0 = time.monotonic()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n{'=' * 70}")
    print(f"[{entry['name']}] starting")
    print(f"  input: {entry['input']}")
    print(f"  log:   {log_path}")
    print(f"  cmd:   {' '.join(cmd)}")
    print("=" * 70)

    child_env = dict(os.environ)
    child_env["PYTHONUNBUFFERED"] = "1"  # child's own stdout is fully-buffered when piped otherwise

    lines: List[str] = []
    with log_path.open("w", encoding="utf-8", buffering=1) as log_fh:
        log_fh.write(f"command: {' '.join(cmd)}\nstarted_at: {started_at}\n\n")
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1, env=child_env,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            lines.append(line.rstrip("\n"))
            log_fh.write(line)
            print(f"  [{entry['name']}] {line.rstrip()}", flush=True)
        returncode = proc.wait()

    elapsed_s = time.monotonic() - t0
    finished_at = _now_iso()

    result: Dict[str, Any] = {
        "status": "done" if returncode == 0 else "failed",
        "returncode": returncode,
        "started_at": started_at,
        "finished_at": finished_at,
        "elapsed_s": round(elapsed_s, 1),
        "log_path": str(log_path),
        "run_dir": _parse_run_dir(lines),
    }
    if returncode != 0:
        result["error_tail"] = "\n".join(lines[-20:])

    print(f"[{entry['name']}] {'DONE' if returncode == 0 else 'FAILED'} "
          f"in {elapsed_s / 60:.1f} min (returncode={returncode})")
    return result


def main() -> None:
    sys.stdout.reconfigure(line_buffering=True)  # visible progress when stdout is redirected to a file

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--checkpoint", default=str(DEFAULT_CHECKPOINT))
    parser.add_argument("--logs-dir", default=str(DEFAULT_LOGS_DIR))
    parser.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT,
                         help="Parent directory for run_psd_diagnostics.py run folders.")
    parser.add_argument("--only", action="append", default=None,
                         help="Restrict to this volume name (repeatable).")
    parser.add_argument("--force", action="store_true",
                         help="Re-run volumes even if checkpointed as done.")
    parser.add_argument("--retry-failed", action="store_true",
                         help="Re-run volumes checkpointed as failed (in addition to pending ones).")
    parser.add_argument("--dry-run", action="store_true",
                         help="Print what would run without executing anything.")

    parser.add_argument("--pore-label", type=int, default=5,
                         help="Default: 5. NOTE: dataset_info.json documents pore=6, but the "
                              "actual deployed segmentation outputs (verified via np.unique on "
                              "nlm_volume.nii.gz and mishmar_hanegev_maoz_3_5p85um.nii.gz) only "
                              "ever contain labels {0,1,2,5}; 5 is the large (~27-38%) porosity-"
                              "matching class, matching the prior validated crop200/zcenter200 runs.")
    parser.add_argument("--pom-label", type=int, nargs="+", default=[2],
                         help="Default: 2. See --pore-label note: there is only one minor "
                              "candidate POM class in these outputs, not two.")
    parser.add_argument("--use-chunking", dest="use_chunking", action="store_true", default=True)
    parser.add_argument("--no-chunking", dest="use_chunking", action="store_false")
    parser.add_argument("--chunk-size", type=int, nargs=3, default=[128, 128, 128])
    parser.add_argument("--halo-width", type=int, default=50)
    parser.add_argument("--n-anisotropy-directions", type=int, default=800)
    parser.add_argument("--no-gpu", action="store_true")

    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    checkpoint_path = Path(args.checkpoint)
    logs_dir = Path(args.logs_dir)

    manifest = _load_json(manifest_path)
    volumes: List[Dict[str, Any]] = manifest.get("volumes", [])
    if not volumes:
        print(f"No volumes found in manifest: {manifest_path}", file=sys.stderr)
        sys.exit(1)

    checkpoint = _load_json(checkpoint_path)

    if args.only:
        volumes = [v for v in volumes if v["name"] in args.only]
        missing = set(args.only) - {v["name"] for v in volumes}
        if missing:
            print(f"WARNING: --only name(s) not found in manifest: {sorted(missing)}", file=sys.stderr)

    print(f"Manifest: {manifest_path} ({len(volumes)} volume(s) selected)")
    print(f"Checkpoint: {checkpoint_path}")
    print(f"Output root: {args.output_root}")

    for entry in volumes:
        name = entry["name"]
        prior = checkpoint.get(name)

        if not entry.get("enabled", True):
            print(f"\n[{name}] SKIPPED (disabled in manifest)")
            continue

        if prior and prior.get("status") == "done" and not args.force:
            print(f"\n[{name}] SKIPPED (already done at {prior.get('finished_at')}; "
                  f"use --force to re-run)")
            continue

        if prior and prior.get("status") == "failed" and not (args.retry_failed or args.force):
            print(f"\n[{name}] SKIPPED (previously failed; use --retry-failed or --force to re-run)")
            continue

        input_path = Path(entry["input"])
        if not input_path.exists():
            print(f"\n[{name}] SKIPPED (input not found: {input_path})")
            checkpoint[name] = {
                "status": "skipped_missing_input",
                "input": str(input_path),
                "checked_at": _now_iso(),
            }
            _save_json_atomic(checkpoint_path, checkpoint)
            continue

        cmd = _build_command(entry, args)
        if args.dry_run:
            print(f"\n[{name}] DRY RUN: {' '.join(cmd)}")
            continue

        checkpoint[name] = {"status": "running", "started_at": _now_iso()}
        _save_json_atomic(checkpoint_path, checkpoint)

        log_path = logs_dir / f"{name}.log"
        result = _run_one(entry, args, log_path)
        checkpoint[name] = result
        _save_json_atomic(checkpoint_path, checkpoint)

    print(f"\n{'=' * 70}")
    print("Batch summary:")
    for entry in volumes:
        status = checkpoint.get(entry["name"], {}).get("status", "not_run")
        print(f"  {entry['name']}: {status}")
    print("=" * 70)


if __name__ == "__main__":
    main()
