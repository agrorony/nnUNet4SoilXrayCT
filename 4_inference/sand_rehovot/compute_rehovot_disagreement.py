"""Compute A/B model disagreement maps for the Rehovot predictions and
export the 10 largest disagreement regions as ROI bounding boxes in the
format micro-SAM 3D Proofreader's 'Load' ROI mode expects
({z0,z1,y0,y1,x0,x1} per napari_plugin.py's load_rois_from_file()).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import tifffile
from scipy import ndimage

OUT_ROOT = Path(r"c:\Users\rony.schwartz\Documents\nnUNet4SoilXrayCT\predictions_rehovot_20260815")
LABELS = {0: "background", 1: "Stones", 2: "POM_type1", 3: "POM_type2", 4: "unused", 5: "Pore", 6: "ignore"}
VOLUMES = ["Rehovot_samp3_highkV_Cu0.11_15um", "rehovot_samp_2"]
MODEL_A = "loess_i2"       # newer model -> primary editable layer in Step 3
MODEL_B = "bnei_reem_i4"   # older-lineage-of-different-sample model -> read-only overlay

TOP_N = 10


def main() -> None:
    summary = {}
    for sample_id in VOLUMES:
        vol_dir = OUT_ROOT / sample_id
        predA = tifffile.imread(str(vol_dir / f"{sample_id}_{MODEL_A}.tif"))
        predB = tifffile.imread(str(vol_dir / f"{sample_id}_{MODEL_B}.tif"))
        assert predA.shape == predB.shape

        disagree = predA != predB
        total = disagree.size
        pct_overall = 100 * disagree.sum() / total

        per_phase = {}
        all_labels = sorted(set(np.unique(predA).tolist()) | set(np.unique(predB).tolist()))
        for lbl in all_labels:
            xor_mask = (predA == lbl) != (predB == lbl)
            per_phase[LABELS.get(int(lbl), str(lbl))] = round(100 * xor_mask.sum() / total, 4)

        # Connected components of the disagreement mask (6-connectivity default structure).
        labeled, n_components = ndimage.label(disagree)
        if n_components == 0:
            bboxes = []
        else:
            sizes = ndimage.sum(disagree, labeled, index=np.arange(1, n_components + 1))
            order = np.argsort(sizes)[::-1][:TOP_N]
            slices = ndimage.find_objects(labeled)
            bboxes = []
            for comp_idx in order:
                comp_label = comp_idx + 1
                sl = slices[comp_label - 1]
                z0, z1 = sl[0].start, sl[0].stop
                y0, y1 = sl[1].start, sl[1].stop
                x0, x1 = sl[2].start, sl[2].stop
                bboxes.append({
                    "z0": int(z0), "z1": int(z1),
                    "y0": int(y0), "y1": int(y1),
                    "x0": int(x0), "x1": int(x1),
                    "voxel_count": int(sizes[comp_idx]),
                })

        bbox_path = vol_dir / f"disagreement_bboxes_{sample_id}.json"
        # micro-SAM's Load mode expects z0..x1 keys; keep voxel_count as extra info (harmless extra key)
        bbox_path.write_text(json.dumps(bboxes, indent=2), encoding="utf-8")

        summary[sample_id] = {
            "pct_disagreement_overall": round(pct_overall, 4),
            "pct_disagreement_per_phase": per_phase,
            "n_disagreement_components": int(n_components),
            "top_bboxes_file": str(bbox_path),
            "top_bboxes": bboxes,
        }
        print(f"=== {sample_id} ===")
        print(f"Overall disagreement: {pct_overall:.3f}%")
        print(f"Per-phase (XOR) disagreement %: {per_phase}")
        print(f"Connected disagreement components: {n_components}")
        print(f"Top {len(bboxes)} bboxes written to {bbox_path}")
        for b in bboxes[:3]:
            print(f"  {b}")

    (OUT_ROOT / "disagreement_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nSummary: {OUT_ROOT / 'disagreement_summary.json'}")


if __name__ == "__main__":
    main()
