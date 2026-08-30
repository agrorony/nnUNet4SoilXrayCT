"""Part 2 driver -- for each volume, export the decided crop then run the
full norm200 -> NLM -> inference -> sanity-check pipeline, sequentially.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
VOLUME_KEYS = ["bnei_reem_canonical", "mishmar_native_5p85um", "mishmar_second_8p8um"]
# run_preprocess.py (norm200->CUDA NLM) and nnUNet inference require torch
# with CUDA + nnunetv2, which live in the venv-napari conda env, not the
# default "python" on PATH (base Anaconda has tifffile/numpy but no torch).
PY_EXE = r"C:\Users\rony.schwartz\.conda\envs\venv-napari\python.exe"


def run(cmd: list[str]) -> None:
    print(f"\n{'#'*90}\n$ {' '.join(cmd)}\n{'#'*90}", flush=True)
    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed (exit {result.returncode}): {cmd}")


def main() -> None:
    for key in VOLUME_KEYS:
        print(f"\n\n{'='*100}\nVOLUME: {key}\n{'='*100}", flush=True)
        run([PY_EXE, "-u", str(HERE / "part2_export_crop.py"), "--volume-key", key])
        run([PY_EXE, "-u", str(HERE / "part2_run_pipeline.py"), "--volume-key", key])
    print("\n\nALL VOLUMES DONE.")


if __name__ == "__main__":
    main()
