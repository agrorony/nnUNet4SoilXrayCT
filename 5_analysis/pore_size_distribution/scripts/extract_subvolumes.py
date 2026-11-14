"""Extract non-overlapping cubic subvolumes for the Figure 4 subvolume-replication
inference redo. Also runs the REV (representative elementary volume) porosity check.

Soils / sources
----------------
bnei_reem (Vertisol): nnUNet 3-class labeled volume, pore label = 5.
mishmar   (Loess):    nnUNet 3-class labeled volume, pore label = 5.
rehovot   (Sand):     binary pore/solid mask (bool), no POM class -- different
                       segmentation method than the other two soils (flagged
                       explicitly in stats_summary.md).

Subvolume placement
--------------------
Each soil's volume is split into 2 halves per axis; a cube of edge S voxels is
centered within each half (equal margin on both sides), giving a fixed 2x2x2=8
grid of non-overlapping subvolumes per soil. S differs per soil (same voxel-count
target achieving 8 subvolumes >=300**3, per user decision 2026-08-15) because the
physical sample sizes differ:
  bnei_reem / rehovot: S=300 vox (~15.0um voxel) -> 4.50mm edge
  mishmar:             S=430 vox (5.85um voxel)  -> 2.52mm edge

Artifact/wall exclusion heuristic
----------------------------------
1. Porosity extremity: subvolume porosity < 0.02 or > 0.85 (suspicious of hitting
   an air gap / fully solid container-wall region, not real soil heterogeneity).
2. For labeled volumes only: fraction of label 0 ("ToPredict"/unclassified,
   dataset_info.json) far above the full-volume mean (> 2x global mean AND > 0.15
   absolute) -- indicates the subvolume overlaps unclassified/background voxels,
   which in these center-cropped cylindrical-core scans typically means it's
   touching the corner regions outside the physical core or a scan artifact.
"""

from __future__ import annotations

import json
from pathlib import Path

import nibabel as nib
import numpy as np

OUT_ROOT = Path(__file__).resolve().parents[1]
SUBVOL_DIR = OUT_ROOT / "subvolumes"

SOILS = {
    "bnei_reem": {
        "label": "Bnei Re'em (Vertisol)",
        "path": r"\\hive3065\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources\bnei_reem_fresh_bnei_reem_i4\inference_concatenated\nlm_volume.nii.gz",
        "kind": "labeled",
        "pore_label": 5,
        "voxel_um": 15.000149,
        "S": 300,
    },
    "mishmar": {
        "label": "Mishmar HaNegev (Loess)",
        "path": r"\\hive3065\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources\mishmar_hanegev_maoz_3_5p85um\inference_output_concat_loess_i2\mishmar_hanegev_maoz_3_5p85um.nii.gz",
        "kind": "labeled",
        "pore_label": 5,
        "voxel_um": 5.85,
        "S": 430,
    },
    "rehovot": {
        "label": "Rehovot (Sand)",
        "path": r"\\hive3065\Yael_Mishael\Rony\remote_computer backup\10.5\rehovot_samp_2.npy",
        "kind": "binary",
        "pore_label": None,
        "voxel_um": 15.0,
        "S": 300,
    },
}


def load_volume(cfg: dict) -> np.ndarray:
    path = cfg["path"]
    if path.lower().endswith((".nii", ".nii.gz")):
        return np.asarray(nib.load(path).dataobj)
    return np.load(path)


def grid_origins(dim: int, s: int) -> list[int]:
    half = dim // 2
    margin = (half - s) // 2
    if margin < 0:
        raise ValueError(f"S={s} does not fit in half-dim={half} (dim={dim})")
    o0 = margin
    o1 = half + margin
    return [o0, o1]


def main() -> None:
    manifest: dict[str, list[dict]] = {}

    for soil_key, cfg in SOILS.items():
        print(f"=== {soil_key} ({cfg['label']}) ===")
        vol = load_volume(cfg)
        print(f"  shape={vol.shape} dtype={vol.dtype}")

        if cfg["kind"] == "labeled":
            pore_full = vol == cfg["pore_label"]
            bg_full_frac = float(np.mean(vol == 0))
            print(f"  global label-0 (unclassified) fraction: {bg_full_frac:.4f}")
        else:
            pore_full = vol.astype(bool)
            bg_full_frac = None

        s = cfg["S"]
        oz = grid_origins(vol.shape[0], s)
        oy = grid_origins(vol.shape[1], s)
        ox = grid_origins(vol.shape[2], s)

        soil_dir = SUBVOL_DIR / soil_key
        soil_dir.mkdir(parents=True, exist_ok=True)

        entries = []
        idx = 0
        for z0 in oz:
            for y0 in oy:
                for x0 in ox:
                    sub_labeled = vol[z0:z0 + s, y0:y0 + s, x0:x0 + s]
                    sub_pore = pore_full[z0:z0 + s, y0:y0 + s, x0:x0 + s]
                    porosity = float(np.mean(sub_pore))

                    excluded = False
                    reasons = []
                    if porosity < 0.02 or porosity > 0.85:
                        excluded = True
                        reasons.append(f"porosity extremity ({porosity:.4f})")

                    if cfg["kind"] == "labeled":
                        sub_bg_frac = float(np.mean(sub_labeled == 0))
                        if sub_bg_frac > max(0.15, 2 * bg_full_frac):
                            excluded = True
                            reasons.append(
                                f"label-0/unclassified fraction {sub_bg_frac:.4f} "
                                f"(global mean {bg_full_frac:.4f})"
                            )
                    else:
                        sub_bg_frac = None

                    name = f"sub_{idx:02d}_z{z0}_y{y0}_x{x0}"
                    out_path = soil_dir / f"{name}.npy"
                    np.save(out_path, sub_pore)

                    entries.append({
                        "soil": soil_key,
                        "subvolume_id": name,
                        "origin_z": z0, "origin_y": y0, "origin_x": x0,
                        "edge_voxels": s,
                        "edge_mm": round(s * cfg["voxel_um"] / 1000.0, 4),
                        "porosity": porosity,
                        "label0_fraction": sub_bg_frac,
                        "excluded": excluded,
                        "exclude_reasons": reasons,
                        "npy_path": str(out_path),
                    })
                    status = "EXCLUDED" if excluded else "ok"
                    print(f"  [{idx}] z{z0} y{y0} x{x0} porosity={porosity:.4f} "
                          f"label0={sub_bg_frac} -> {status} {reasons}")
                    idx += 1

        manifest[soil_key] = entries
        del vol, pore_full

    manifest_path = OUT_ROOT / "subvolume_extraction_manifest.json"
    with manifest_path.open("w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    print(f"\nWrote manifest: {manifest_path}")

    n_excluded = sum(e["excluded"] for soil in manifest.values() for e in soil)
    n_total = sum(len(v) for v in manifest.values())
    print(f"Total subvolumes: {n_total}, excluded: {n_excluded}")


if __name__ == "__main__":
    main()
