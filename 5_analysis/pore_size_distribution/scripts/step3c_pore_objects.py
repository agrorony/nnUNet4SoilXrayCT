"""Step 3C: pore-object KS test prep. 26-connectivity connected-component
labeling of the full pore phase per soil, equivalent spherical diameter per
object, objects <2 voxels excluded (segmentation noise). Saves per-soil object
diameter arrays (.npy) + a summary JSON (n objects before/after cutoff, exclusion
impact). The actual pairwise KS tests run later once all three soils are done
(see run_stats.py).
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import nibabel as nib
import numpy as np
from scipy import ndimage as ndi

OUT_ROOT = Path(__file__).resolve().parents[1]
OBJ_DIR = OUT_ROOT / "pore_objects"
OBJ_DIR.mkdir(exist_ok=True)

SOILS = {
    "bnei_reem": {
        "path": r"\\hive3065\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources\bnei_reem_fresh_bnei_reem_i4\inference_concatenated\nlm_volume.nii.gz",
        "kind": "labeled", "pore_label": 5, "voxel_um": 15.000149,
    },
    "mishmar": {
        "path": r"\\hive3065\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources\mishmar_hanegev_maoz_3_5p85um\inference_output_concat_loess_i2\mishmar_hanegev_maoz_3_5p85um.nii.gz",
        "kind": "labeled", "pore_label": 5, "voxel_um": 5.85,
    },
    "rehovot": {
        "path": r"\\hive3065\Yael_Mishael\Rony\remote_computer backup\10.5\rehovot_samp_2.npy",
        "kind": "binary", "pore_label": None, "voxel_um": 15.0,
    },
}

STRUCT_26 = np.ones((3, 3, 3), dtype=np.uint8)  # full 26-connectivity structuring element


def load_volume(cfg: dict) -> np.ndarray:
    path = cfg["path"]
    if path.lower().endswith((".nii", ".nii.gz")):
        return np.asarray(nib.load(path).dataobj)
    return np.load(path)


def main() -> None:
    summary = {}
    for soil_key, cfg in SOILS.items():
        t0 = time.time()
        print(f"=== {soil_key} ===", flush=True)
        vol = load_volume(cfg)
        pore = (vol == cfg["pore_label"]) if cfg["kind"] == "labeled" else vol.astype(bool)
        del vol
        print(f"  loaded, pore voxels = {int(pore.sum()):,}", flush=True)

        labels, n_objects_raw = ndi.label(pore, structure=STRUCT_26)
        print(f"  labeled: {n_objects_raw:,} raw objects ({time.time()-t0:.1f}s)", flush=True)
        del pore

        counts = np.bincount(labels.ravel())
        counts = counts[1:]  # drop background (label 0)
        del labels

        voxel_um = cfg["voxel_um"]
        voxel_vol_um3 = voxel_um ** 3
        obj_vol_um3 = counts.astype(np.float64) * voxel_vol_um3
        eq_diam_um = (6.0 * obj_vol_um3 / np.pi) ** (1.0 / 3.0)

        n_before = counts.size
        keep = counts >= 2
        n_after = int(keep.sum())
        eq_diam_kept = eq_diam_um[keep]

        np.save(OBJ_DIR / f"{soil_key}_object_diameters_um.npy", eq_diam_kept)

        summary[soil_key] = {
            "n_objects_before_cutoff": n_before,
            "n_objects_after_cutoff": n_after,
            "n_excluded_lt2vox": n_before - n_after,
            "frac_excluded": (n_before - n_after) / n_before if n_before else None,
            "median_diameter_um": float(np.median(eq_diam_kept)) if n_after else None,
            "mean_diameter_um": float(np.mean(eq_diam_kept)) if n_after else None,
            "elapsed_s": time.time() - t0,
        }
        print(f"  before cutoff: {n_before:,}, after (>=2 vox): {n_after:,} "
              f"({100*(n_before-n_after)/n_before:.2f}% excluded)", flush=True)
        print(f"  median diam {summary[soil_key]['median_diameter_um']:.2f} um, "
              f"elapsed {summary[soil_key]['elapsed_s']:.1f}s", flush=True)

    with (OUT_ROOT / "pore_objects_summary.json").open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    print("\nWrote pore_objects_summary.json")


if __name__ == "__main__":
    main()
