"""Preprocess-only run on the corrected bnei_reem_samp_2 reconstruction.

2026-08-25: Rony redid the CT reconstruction for the raw scan at
`18.12.25 bnei_reem_samp_2` (note: this is the folder WITHOUT the ".0"
suffix -- a separate raw scan from `bnei_reem_samp_2_0`, whose earlier
recrop still failed its POM sanity check). That folder mixes raw projection
radiographs (`bnei_reem_highkV_cu011_samp_2########.tif`, shape 896x1344,
one per rotation angle) together with the newly-generated reconstructed
cross-section slices (`bnei_reem_highkV_cu011_samp_2_rec########.tif`,
shape 1344x1344, mtime 2026-08-25 -- today). This script picks up ONLY the
`_rec` files by filename pattern, center-crops them to 650^3 (matching the
project's canonical Bnei Re'em convention), and runs norm200 + CUDA NLM.

Deliberately stops after preprocessing (no inference) -- Rony wants to look
at the preprocessed volume himself in napari before deciding whether it's
good enough to segment.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import tifffile

REPO_DIR = Path(__file__).resolve().parents[2]
FILTERS_DIR = REPO_DIR / "02_preprocessing" / "filters"

HIVE_BASE = r"\\hive3065\Yael_Mishael\Rony\remote_computer backup"
RAW_DIR = Path("C:/Users/rony.schwartz/Desktop/new_rec")
NEW_SAMPLE_ID = "bnei_reem_samp_2_rec"
CROP_SIZE = 650  # matches canonical Bnei Re'em nlm_volume.tif (650x650x652)

SLICE_RE = re.compile(r"^bnei_reem_highkV_cu011_samp_2_rec\d{8}\.tif$")

LOCAL_CROP_DIR = FILTERS_DIR / "_tmp_center_crop" / NEW_SAMPLE_ID
LOCAL_NLM_TIF = FILTERS_DIR / "nlm_output" / "nlm_volume.tif"
NETWORK_TIF = Path(HIVE_BASE) / "10.5" / f"{NEW_SAMPLE_ID}_recropped.tif"


def step1_crop() -> None:
    if LOCAL_CROP_DIR.exists() and len(list(LOCAL_CROP_DIR.glob("*.tif"))) == CROP_SIZE:
        print(f"[1/3] SKIP (already cropped): {LOCAL_CROP_DIR}", flush=True)
        return

    all_files = sorted(RAW_DIR.glob("*.tif"))
    rec_slices = [p for p in all_files if SLICE_RE.match(p.name)]
    print(f"[1/3] raw folder: {len(all_files)} .tif files total, {len(rec_slices)} reconstructed slices "
          f"matched by '_rec########.tif' pattern", flush=True)
    if len(rec_slices) < CROP_SIZE:
        raise RuntimeError(f"Only {len(rec_slices)} reconstructed slices available, need at least {CROP_SIZE}")

    z_start = (len(rec_slices) // 2) - (CROP_SIZE // 2)
    z_end = z_start + CROP_SIZE
    selected = rec_slices[z_start:z_end]
    print(f"[1/3] Z crop: slices [{z_start}:{z_end}] of {len(rec_slices)} reconstructed slices "
          f"(index range {rec_slices[0].name} .. {rec_slices[-1].name})", flush=True)

    first = tifffile.imread(str(selected[0]))
    h, w = first.shape
    y_start = (h - CROP_SIZE) // 2
    x_start = (w - CROP_SIZE) // 2
    print(f"[1/3] XY crop: raw ({h},{w}) -> [{y_start}:{y_start+CROP_SIZE}, {x_start}:{x_start+CROP_SIZE}]", flush=True)

    if LOCAL_CROP_DIR.exists():
        shutil.rmtree(LOCAL_CROP_DIR)
    LOCAL_CROP_DIR.mkdir(parents=True, exist_ok=True)

    for i, src in enumerate(selected):
        img = tifffile.imread(str(src))
        if img.shape != (h, w):
            raise ValueError(f"Unexpected shape change in {src.name}: {img.shape} vs {(h, w)}")
        cropped = img[y_start: y_start + CROP_SIZE, x_start: x_start + CROP_SIZE]
        tifffile.imwrite(str(LOCAL_CROP_DIR / f"slice_{i:06d}.tif"), cropped)
        if i % 200 == 0:
            print(f"[1/3]   wrote {i}/{CROP_SIZE}", flush=True)

    print(f"[1/3] Cropped {CROP_SIZE}^3 volume written to {LOCAL_CROP_DIR}", flush=True)


def step2_norm_nlm() -> None:
    # NOTE: nlm_output/nlm_volume.tif is a SHARED scratch slot reused by every
    # run_preprocess.py invocation regardless of sample -- a shape-only
    # existence check previously caused a silent skip against stale data from
    # an unrelated run (caught 2026-08-24). Always regenerate.
    print(f"\n{'=' * 70}\n[2/3] norm200 + CUDA NLM\n{'=' * 70}", flush=True)
    result = subprocess.run(
        [sys.executable, "run_preprocess.py", "--input_dir", str(LOCAL_CROP_DIR)],
        cwd=str(FILTERS_DIR),
    )
    if result.returncode != 0:
        raise RuntimeError(f"[2/3] run_preprocess.py failed with returncode {result.returncode}")


def step3_export() -> None:
    NETWORK_TIF.parent.mkdir(parents=True, exist_ok=True)
    print(f"[3/3] Copying {LOCAL_NLM_TIF} -> {NETWORK_TIF}", flush=True)
    shutil.copy2(LOCAL_NLM_TIF, NETWORK_TIF)
    print(f"\nDONE (preprocessing only, no inference): {NETWORK_TIF}", flush=True)


def main() -> None:
    step1_crop()
    step2_norm_nlm()
    step3_export()


if __name__ == "__main__":
    main()
