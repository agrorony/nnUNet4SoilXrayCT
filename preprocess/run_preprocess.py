"""
Minimal preprocess pipeline:
    stack slices -> norm200 -> CUDA NLM -> write two 3D TIFF outputs
"""

from __future__ import annotations

import argparse
from importlib import import_module
from pathlib import Path
import sys

import numpy as np
import tifffile

# Local-only layout: run_preprocess.py, normalization.py, gpu_nlm_torch.py
# must all be in the same folder.
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

def _save_tif(path: Path, volume: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tifffile.imwrite(str(path), volume.astype(np.float32), bigtiff=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run stack -> norm200 -> CUDA NLM and save 3D TIFF outputs."
    )
    parser.add_argument(
        "--input_dir",
        required=True,
        type=Path,
        help="Path to folder containing 2-D slice images (.tif/.tiff/.png).",
    )
    args = parser.parse_args()

    norm_mod = import_module("normalization")
    stack_slices_to_volume = norm_mod.stack_slices_to_volume
    norm200 = norm_mod.norm200

    try:
        import torch
    except ImportError as exc:
        raise RuntimeError(
            "PyTorch is required for CUDA NLM. Install torch in your Colab runtime."
        ) from exc

    from gpu_nlm_torch import NLMConfig, non_local_means_3d_cuda_chunked

    if not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA is required for this pipeline. Use a GPU runtime (e.g., Google Colab T4)."
        )

    device_name = torch.cuda.get_device_name(0)
    print(f"CUDA device: {device_name}")

    norm_out_dir = SCRIPT_DIR / "norm200_output"
    nlm_out_dir = SCRIPT_DIR / "nlm_output"

    norm_out_path = norm_out_dir / "norm200_volume.tif"
    nlm_out_path = nlm_out_dir / "nlm_volume.tif"

    print(f"Input dir: {args.input_dir}")
    print("Step 1/3: stacking slices")
    raw_volume = stack_slices_to_volume(args.input_dir)

    print("Step 2/3: applying norm200")
    norm_volume = norm200(raw_volume).astype(np.float32)

    print("Saving norm200 output")
    _save_tif(norm_out_path, norm_volume)

    print("Step 3/3: applying CUDA NLM (chunked)")
    cfg = NLMConfig(
        patch_size=5,
        patch_distance=6,
        h=None,
        chunk_size=128,
        min_chunk_size=32,
    )
    nlm_volume = non_local_means_3d_cuda_chunked(norm_volume, config=cfg)

    print("Saving NLM output")
    _save_tif(nlm_out_path, nlm_volume)

    print("Done.")
    print(f"norm200 output: {norm_out_path}")
    print(f"nlm output: {nlm_out_path}")


if __name__ == "__main__":
    main()
