"""Checkpointed sequential batch runner for run_psd_diagnostics.py 'real' mode
over a fixed job list, pinned to one CUDA device. Two instances of this script
are launched in parallel (one per GPU) to split the 24 subvolume jobs + 1
full-volume Rehovot job across both A6000s.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT_ROOT = HERE.parent
RUN_PSD = OUT_ROOT.parent / "run_psd_diagnostics.py"
BIN_EDGES = (OUT_ROOT / "bin_edges_um.json").read_text().strip()
PYTHON = r"C:\Users\rony.schwartz\.conda\envs\venv-napari\python.exe"

MANIFEST = json.loads((OUT_ROOT / "subvolume_extraction_manifest.json").read_text())

VOXEL_UM = {"bnei_reem": 15.000149, "mishmar": 5.85, "rehovot": 15.0}


def build_jobs(soils: list[str]) -> list[dict]:
    jobs = []
    for soil in soils:
        for entry in MANIFEST[soil]:
            if entry["excluded"]:
                continue
            jobs.append({
                "name": f"{soil}_{entry['subvolume_id']}",
                "input": entry["npy_path"],
                "voxel_spacing": [VOXEL_UM[soil]] * 3,
                "chunking": False,
            })
    return jobs


FULL_REHOVOT_JOB = {
    "name": "rehovot_full_volume",
    "input": r"\\hive3065\Yael_Mishael\Rony\remote_computer backup\10.5\rehovot_samp_2.npy",
    "voxel_spacing": [15.0, 15.0, 15.0],
    "chunking": True,
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gpu", type=int, required=True)
    ap.add_argument("--soils", nargs="+", default=[])
    ap.add_argument("--include-rehovot-full", action="store_true")
    ap.add_argument("--checkpoint", required=True)
    args = ap.parse_args()

    jobs = build_jobs(args.soils)
    if args.include_rehovot_full:
        jobs.append(FULL_REHOVOT_JOB)

    ckpt_path = Path(args.checkpoint)
    ckpt = json.loads(ckpt_path.read_text()) if ckpt_path.exists() else {}

    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = str(args.gpu)

    for job in jobs:
        if ckpt.get(job["name"], {}).get("status") == "done":
            print(f"[skip] {job['name']} already done")
            continue

        cmd = [
            PYTHON, str(RUN_PSD), "real",
            "--input", job["input"],
            "--voxel-spacing", *[str(v) for v in job["voxel_spacing"]],
            "--output-root", str(OUT_ROOT / "psd_runs"),
            "--run-name", job["name"],
            "--bin-edges-json", BIN_EDGES,
        ]
        if job["chunking"]:
            cmd += ["--use-chunking", "--chunk-size", "128", "128", "128", "--halo-width", "50"]

        print(f"[run] {job['name']} on GPU {args.gpu}: {' '.join(cmd[:4])} ...")
        t0 = time.time()
        log_path = OUT_ROOT / "logs" / f"{job['name']}.log"
        with log_path.open("w", encoding="utf-8") as lf:
            proc = subprocess.run(cmd, env=env, stdout=lf, stderr=subprocess.STDOUT)
        elapsed = time.time() - t0

        ckpt[job["name"]] = {
            "status": "done" if proc.returncode == 0 else "failed",
            "returncode": proc.returncode,
            "elapsed_s": elapsed,
            "log": str(log_path),
        }
        ckpt_path.write_text(json.dumps(ckpt, indent=2))
        print(f"[{'ok' if proc.returncode == 0 else 'FAIL'}] {job['name']} in {elapsed:.1f}s")

    print("Batch complete.")


if __name__ == "__main__":
    main()
