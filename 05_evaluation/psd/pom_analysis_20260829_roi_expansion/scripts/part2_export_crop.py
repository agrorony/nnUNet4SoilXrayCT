"""Part 2 step 3 (prep) -- export the final decided crop for one volume as
a slice-stack folder, ready for run_preprocess.py (norm200 -> CUDA NLM).

Reads final_crop_size for --volume-key from part2_holder_safety_report.json
(falling back to part1_margin_report.json if that volume was skipped in
Part 2 for insufficient margin) and writes centered-crop TIFF slices to
raw_crops/<volume-key>/slice_NNNNNN.tif under this run directory.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import tifffile

from raw_volume_io import list_zslices, center_range

HERE = Path(__file__).resolve().parent
RUN_DIR = HERE.parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--volume-key", required=True)
    args = parser.parse_args()
    key = args.volume_key

    with (RUN_DIR / "part1_margin_report.json").open(encoding="utf-8") as fh:
        part1 = json.load(fh)
    with (RUN_DIR / "part2_holder_safety_report.json").open(encoding="utf-8") as fh:
        part2 = json.load(fh)

    final_size = part2[key]["final_crop_size"]
    raw_slice_dir = Path(part1[key]["raw_slice_dir"])
    print(f"[{key}] final_crop_size={final_size}  raw_slice_dir={raw_slice_dir}")

    out_dir = RUN_DIR / "raw_crops" / key
    out_dir.mkdir(parents=True, exist_ok=True)
    existing = list(out_dir.glob("*.tif"))
    if len(existing) == final_size:
        print(f"[{key}] {len(existing)} slices already exported at this size -- skipping re-export.")
        return
    for f in existing:
        f.unlink()

    files = list_zslices(raw_slice_dir)
    n_z = len(files)
    z0, z1 = center_range(n_z, final_size)

    first = tifffile.imread(str(files[z0]))
    h, w = first.shape[:2]
    y0, y1 = center_range(h, final_size)
    x0, x1 = center_range(w, final_size)

    print(f"[{key}] cropping Z[{z0}:{z1}] Y[{y0}:{y1}] X[{x0}:{x1}] from raw shape Z={n_z} H={h} W={w}")
    for i in range(final_size):
        img = tifffile.imread(str(files[z0 + i]))
        cropped = img[y0:y1, x0:x1]
        tifffile.imwrite(str(out_dir / f"slice_{i:06d}.tif"), cropped)
        if i % 100 == 0:
            print(f"[{key}]   {i}/{final_size}")
    print(f"[{key}] DONE -- wrote {final_size} slices to {out_dir}")


if __name__ == "__main__":
    main()
