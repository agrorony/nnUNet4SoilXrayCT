"""
Center-crop a raw slice stack to a cube, then run the norm200 -> CUDA NLM
pipeline (run_preprocess.py) and export the result into the canonical
10.5 data root.

Mirrors the manual steps in colab_cli_runner.ipynb (nested-folder detection,
center crop, run_preprocess.py subprocess call, copy to EXPORT_DIR).
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import tifffile

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_DIR = SCRIPT_DIR.parent.parent

SLICE_PATTERNS = ("*.tif", "*.tiff", "*.png")


def find_slice_dir(input_dir: Path) -> Path:
    def count_slices(folder: Path) -> int:
        return sum(len(list(folder.glob(p))) for p in SLICE_PATTERNS)

    if count_slices(input_dir) > 0:
        return input_dir

    candidates = [
        (sub, count_slices(sub))
        for sub in sorted(p for p in input_dir.rglob("*") if p.is_dir())
    ]
    candidates = [(sub, n) for sub, n in candidates if n > 0]
    if not candidates:
        raise FileNotFoundError(f"No slices found under {input_dir} (recursive).")
    return candidates[0][0]


def list_slice_files(slice_dir: Path) -> list[Path]:
    files: list[Path] = []
    for pattern in SLICE_PATTERNS:
        files.extend(sorted(slice_dir.glob(pattern)))
    return files


def center_crop_cube(slice_dir: Path, crop_size: int, out_dir: Path) -> None:
    files = list_slice_files(slice_dir)
    if len(files) < crop_size:
        raise ValueError(
            f"Not enough slices for Z crop: found {len(files)}, need at least {crop_size}"
        )

    z_start = (len(files) // 2) - (crop_size // 2)
    z_end = z_start + crop_size
    selected = files[z_start:z_end]

    first = tifffile.imread(str(selected[0]))
    if first.ndim != 2:
        raise ValueError(f"Expected 2D slices, got shape {first.shape}")
    h, w = first.shape
    if h < crop_size or w < crop_size:
        raise ValueError(
            f"Slice size too small for XY crop: got {(h, w)}, need at least ({crop_size}, {crop_size})"
        )

    y_start = (h - crop_size) // 2
    x_start = (w - crop_size) // 2

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for i, src in enumerate(selected):
        img = tifffile.imread(str(src))
        if img.shape != (h, w):
            raise ValueError(f"Unexpected shape change in {src.name}: {img.shape} vs {(h, w)}")
        cropped = img[y_start : y_start + crop_size, x_start : x_start + crop_size]
        tifffile.imwrite(str(out_dir / f"slice_{i:06d}.tif"), cropped)

    print(f"Cropped {crop_size}^3 volume written to {out_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Center-crop a slice stack to a cube, then run norm200 -> CUDA NLM and export."
    )
    parser.add_argument("--input_dir", required=True, type=Path)
    parser.add_argument("--export_basename", required=True)
    parser.add_argument(
        "--export_dir",
        type=Path,
        default=Path(r"\\HIVE3065\Yael_Mishael\Rony\remote_computer backup\10.5"),
    )
    parser.add_argument("--crop_size", type=int, default=1000)
    args = parser.parse_args()

    if not args.input_dir.exists():
        raise FileNotFoundError(f"Input folder not found: {args.input_dir}")
    if not args.export_dir.exists():
        raise FileNotFoundError(f"Export folder not found: {args.export_dir}")

    slice_dir = find_slice_dir(args.input_dir)
    print(f"Using slice folder: {slice_dir}")

    cropped_dir = SCRIPT_DIR / "_tmp_center_crop" / args.export_basename
    center_crop_cube(slice_dir, args.crop_size, cropped_dir)

    cmd = [sys.executable, "run_preprocess.py", "--input_dir", str(cropped_dir)]
    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=str(SCRIPT_DIR))
    if result.returncode != 0:
        raise RuntimeError("run_preprocess.py failed. See output above.")

    nlm_path = SCRIPT_DIR / "nlm_output" / "nlm_volume.tif"
    if not nlm_path.exists():
        raise FileNotFoundError(f"Expected NLM output not found: {nlm_path}")

    export_path = args.export_dir / f"{args.export_basename}.tif"
    shutil.copy2(nlm_path, export_path)
    print(f"Exported final TIF to: {export_path}")

    shutil.rmtree(cropped_dir)
    print(f"Cleaned up temp crop folder: {cropped_dir}")


if __name__ == "__main__":
    main()
