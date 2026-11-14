"""A2 Step 5b: run the local-thickness PSD pipeline on the 8 downsampled
(~15um) Mishmar subvolumes, using the same bin edges as the original
2026-08-15 run for direct comparability.
"""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT_ROOT = HERE.parent / "mishmar_downsample"
RUN_PSD = Path(r"C:\Users\rony.schwartz\Documents\nnUNet4SoilXrayCT\05_evaluation\psd\run_psd_diagnostics.py")
BIN_EDGES = Path(r"C:\Users\rony.schwartz\Documents\nnUNet4SoilXrayCT\05_evaluation\psd\fig4_inference_20260815\bin_edges_um.json").read_text().strip()
PYTHON = r"C:\Users\rony.schwartz\.conda\envs\venv-napari\python.exe"

MANIFEST = json.loads((OUT_ROOT / "downsample_manifest.json").read_text())


def main() -> None:
    ckpt_path = OUT_ROOT / "checkpoint.json"
    ckpt = json.loads(ckpt_path.read_text()) if ckpt_path.exists() else {}

    for entry in MANIFEST:
        name = f"mishmar_downsampled_{entry['subvolume_id']}"
        if ckpt.get(name, {}).get("status") == "done":
            print(f"[skip] {name} already done")
            continue

        voxel = entry["actual_voxel_um"]
        cmd = [
            PYTHON, str(RUN_PSD), "real",
            "--input", entry["npy_path"],
            "--voxel-spacing", str(voxel), str(voxel), str(voxel),
            "--output-root", str(OUT_ROOT / "psd_runs"),
            "--run-name", name,
            "--bin-edges-json", BIN_EDGES,
        ]
        print(f"[run] {name}: {' '.join(cmd[:4])} ...")
        t0 = time.time()
        log_path = OUT_ROOT / "logs" / f"{name}.log"
        with log_path.open("w", encoding="utf-8") as lf:
            proc = subprocess.run(cmd, stdout=lf, stderr=subprocess.STDOUT)
        elapsed = time.time() - t0

        ckpt[name] = {
            "status": "done" if proc.returncode == 0 else "failed",
            "returncode": proc.returncode,
            "elapsed_s": elapsed,
            "log": str(log_path),
        }
        ckpt_path.write_text(json.dumps(ckpt, indent=2))
        print(f"[{'ok' if proc.returncode == 0 else 'FAIL'}] {name} in {elapsed:.1f}s")

    print("Batch complete.")


if __name__ == "__main__":
    main()
