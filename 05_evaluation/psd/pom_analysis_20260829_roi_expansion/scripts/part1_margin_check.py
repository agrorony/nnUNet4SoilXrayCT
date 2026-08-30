"""Part 1 -- raw-vs-crop margin check for the ROI expansion prompt.

For each of the 3 in-scope volumes (Bnei Re'em canonical, Mishmar native
5.85um, Mishmar second sample ~8.8um): find the raw (post-reconstruction,
pre-crop) slice stack, count Z slices and read one slice's (H, W), compare
against the current crop actually used, and compute the extra linear
margin available beyond the current crop on each axis.

Decision rule (per pom_roi_expansion_and_final_clustering_prompt.md Part 1):
if the raw scan offers less than 15% more linear extent beyond the current
crop on EVERY axis, skip re-cropping for that volume.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import tifffile

# SkyScan-style reconstructed cross-section slices are named "*_rec#####.tif"
# (or plainly "slice#####.tif"). Some raw folders (Bnei Re'em) mix these in
# with raw radiographic *projection* images (sequential "...00000000.tif"
# naming, no "_rec") at a different, non-square resolution -- those must be
# excluded or the slice count and H/W come out wrong (confirmed by direct
# inspection: Bnei Re'em raw folder has 2613 total .tif files but only 804
# are actual reconstructed slices at 1344x1344; the rest are 896x1344
# projections / previews).
REC_PATTERN = re.compile(r"_rec(\d+)\.tif$", re.IGNORECASE)


def count_and_shape(slice_dir: Path) -> tuple[int, int, int]:
    all_files = sorted(slice_dir.glob("*.tif"))
    rec_files = [f for f in all_files if REC_PATTERN.search(f.name)]
    files = rec_files if rec_files else all_files
    n_z = len(files)
    if n_z == 0:
        raise FileNotFoundError(f"No .tif slices found in {slice_dir}")
    first = tifffile.imread(str(files[0]))
    last = tifffile.imread(str(files[-1]))
    assert first.shape == last.shape, (
        f"inconsistent slice shape in {slice_dir}: {first.shape} vs {last.shape}"
    )
    h, w = first.shape[:2]
    return n_z, h, w


def crop_shape(path: Path) -> tuple[int, int, int]:
    with tifffile.TiffFile(str(path)) as tf:
        n_pages = len(tf.pages)
        page0 = tf.pages[0].asarray()
    h, w = page0.shape[:2]
    return n_pages, h, w


def margin_pct(raw: int, crop: int) -> float:
    return 100.0 * (raw - crop) / crop


VOLUMES = {
    "bnei_reem_canonical": {
        "raw_slice_dir": Path(r"\\hive3065\Yael_Mishael\Rony\18.12.25 bnei_reem_samp_2"),
        "current_crop_tif": Path(
            r"\\hive3065\Yael_Mishael\Rony\remote_computer backup\10.5\nlm_volume.tif"
        ),
        "voxel_um": 15.000149,
    },
    "mishmar_native_5p85um": {
        "raw_slice_dir": Path(
            r"\\hive3065\Yael_Mishael\Rony\mishmar_hanegev_maoz\3-16mm_diam_5.85um"
        ),
        "current_crop_tif": Path(
            r"\\hive3065\Yael_Mishael\Rony\remote_computer backup\10.5\mishmar_hanegev_maoz_3_5p85um.tif"
        ),
        "voxel_um": 5.85,
    },
    "mishmar_second_8p8um": {
        "raw_slice_dir": Path(
            r"\\hive3065\Yael_Mishael\Rony\mishmar_hanegev_maoz\2-16mm_diam_8.8um\2-16mm_diam_8.8um"
        ),
        "current_crop_tif": Path(
            r"\\hive3065\Yael_Mishael\Rony\remote_computer backup\10.5\mishmar_hanegev_maoz_2_8p8um.tif"
        ),
        "voxel_um": 8.8,
    },
}


def main() -> None:
    report = {}
    for key, cfg in VOLUMES.items():
        print(f"=== {key} ===")
        raw_dir = cfg["raw_slice_dir"]
        crop_tif = cfg["current_crop_tif"]
        assert raw_dir.exists(), f"raw slice dir missing: {raw_dir}"
        assert crop_tif.exists(), f"current crop tif missing: {crop_tif}"

        n_z, h, w = count_and_shape(raw_dir)
        print(f"  raw: Z={n_z} H={h} W={w}")

        c_z, c_h, c_w = crop_shape(crop_tif)
        print(f"  current crop: Z={c_z} H={c_h} W={c_w}")

        margins = {
            "z_pct": margin_pct(n_z, c_z),
            "y_pct": margin_pct(h, c_h),
            "x_pct": margin_pct(w, c_w),
        }
        print(f"  margins: {margins}")

        qualifies = all(m >= 15.0 for m in margins.values())
        print(f"  qualifies for Part 2 (>=15% margin on every axis): {qualifies}")

        report[key] = {
            "raw_shape_zhw": [n_z, h, w],
            "current_crop_shape_zhw": [c_z, c_h, c_w],
            "margin_pct": margins,
            "qualifies_for_part2": qualifies,
            "voxel_um": cfg["voxel_um"],
            "raw_slice_dir": str(raw_dir),
            "current_crop_tif": str(crop_tif),
        }
        print()

    out_path = Path(__file__).resolve().parent.parent / "part1_margin_report.json"
    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
