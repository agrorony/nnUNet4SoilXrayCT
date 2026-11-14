"""A2 Step 5a: downsample the 8 Mishmar subvolumes from 5.85um to ~15um voxels
as a robustness check (psd_binning_recommendation.md section (d)).

Method: trilinear resample of the binary pore mask (as float) to the target
grid size, re-thresholded at 0.5. This approximates what a coarser-resolution
acquisition + thresholding segmentation would see (majority-in-neighborhood),
which is the standard "downsample and re-threshold" resolution-robustness check
-- it does not model CT point-spread-function physics, but is the defensible
proxy given only the segmented mask (not raw radiographs) is available.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.ndimage import zoom

ORIG_ROOT = Path(r"C:\Users\rony.schwartz\Documents\nnUNet4SoilXrayCT\05_evaluation\psd\fig4_inference_20260815")
OUT_ROOT = Path(__file__).resolve().parents[1] / "mishmar_downsample"
SRC_VOXEL_UM = 5.85
TARGET_VOXEL_UM = 15.000149  # match bnei_reem exactly for direct 3-soil comparability

MANIFEST = json.loads((ORIG_ROOT / "subvolume_extraction_manifest.json").read_text())


def main() -> None:
    factor = SRC_VOXEL_UM / TARGET_VOXEL_UM
    out_dir = OUT_ROOT / "subvolumes_15um"
    out_dir.mkdir(parents=True, exist_ok=True)

    records = []
    for entry in MANIFEST["mishmar"]:
        if entry["excluded"]:
            continue
        sub_id = entry["subvolume_id"]
        mask = np.load(entry["npy_path"])
        edge_in = mask.shape[0]

        mask_f = mask.astype(np.float32)
        down = zoom(mask_f, zoom=factor, order=1, mode="nearest")
        down_bool = down >= 0.5

        edge_out = down_bool.shape[0]
        actual_voxel_um = edge_in * SRC_VOXEL_UM / edge_out
        porosity_before = float(mask.mean())
        porosity_after = float(down_bool.mean())

        out_path = out_dir / f"{sub_id}_15um.npy"
        np.save(out_path, down_bool)

        rec = {
            "subvolume_id": sub_id,
            "npy_path": str(out_path),
            "edge_voxels_in": int(edge_in),
            "edge_voxels_out": int(edge_out),
            "actual_voxel_um": actual_voxel_um,
            "porosity_before_5p85um": porosity_before,
            "porosity_after_15um": porosity_after,
            "porosity_delta": porosity_after - porosity_before,
        }
        records.append(rec)
        print(f"{sub_id}: {edge_in}^3 @5.85um (poro={porosity_before:.4f}) -> "
              f"{edge_out}^3 @{actual_voxel_um:.3f}um (poro={porosity_after:.4f}, "
              f"delta={rec['porosity_delta']:+.4f})")

    manifest_path = OUT_ROOT / "downsample_manifest.json"
    manifest_path.write_text(json.dumps(records, indent=2))
    print(f"\nWrote {manifest_path}")


if __name__ == "__main__":
    main()
