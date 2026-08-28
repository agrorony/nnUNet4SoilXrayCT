"""Convert Rehovot nnUNet predictions (nii.gz) to .tif label maps and sanity-check them.

Orientation: nnUNet nifti predictions come back as (X, Y, Z) with an
identity affine here. Empirically verified against raw intensity (Stones
should be bright/dense, Pore should be dark) that the correct conversion to
match the raw (Z, Y, X) tif volume is transpose(2,1,0) + flip(axis=1) --
i.e. exactly matching 05_evaluation/microsam_3d/run.py's `_nii_to_zyx()`.
See pipeline_log / conversation for the empirical check (mean intensity in
predicted Stones = 0.895 vs Pore = 0.159 under this orientation, vs
0.464/0.459 -- indistinguishable from background -- under a naive
transpose-only conversion).
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import nibabel as nib
import numpy as np
import tifffile

HIVE_BASE = Path(r"\\hive3065\Yael_Mishael\Rony\remote_computer backup")
OUT_ROOT = Path(r"c:\Users\rony.schwartz\Documents\nnUNet4SoilXrayCT\predictions_rehovot_20260815")

LABELS = {0: "background", 1: "Stones", 2: "POM_type1", 3: "POM_type2", 4: "unused", 5: "Pore", 6: "ignore"}

VOLUMES = {
    "Rehovot_samp3_highkV_Cu0.11_15um": HIVE_BASE / "10.5" / "Rehovot_samp3_highkV_Cu0.11_15um.tif",
    "rehovot_samp_2": HIVE_BASE / "10.5" / "rehovot_samp_2.tif",
}

MODELS = ["loess_i2", "bnei_reem_i4"]


def nii_to_zyx(pred_xyz: np.ndarray, x_flip: bool) -> np.ndarray:
    arr = np.transpose(pred_xyz, (2, 1, 0))
    arr = np.flip(arr, axis=1)
    if x_flip:
        arr = np.flip(arr, axis=2)
    return arr


def main() -> None:
    report_lines = []
    for sample_id, raw_tif_path in VOLUMES.items():
        vol_dir = OUT_ROOT / sample_id
        vol_dir.mkdir(parents=True, exist_ok=True)
        raw = tifffile.imread(str(raw_tif_path))
        report_lines.append(f"\n=== {sample_id} (raw shape {raw.shape}, dtype {raw.dtype}) ===")

        preds_zyx = {}
        for model_key in MODELS:
            nii_path = (
                HIVE_BASE / "nnUNet_resources" / f"rehovot_inference_{sample_id}"
                / f"inference_concatenated_{model_key}" / f"{sample_id}.nii.gz"
            )
            img = nib.load(str(nii_path))
            x_flip = float(img.affine[0, 0]) < 0
            pred_xyz = np.asarray(img.dataobj).astype(np.uint8)
            pred_zyx = nii_to_zyx(pred_xyz, x_flip)

            shape_ok = pred_zyx.shape == raw.shape
            report_lines.append(f"[{model_key}] pred shape {pred_zyx.shape} vs raw {raw.shape} -> {'OK' if shape_ok else 'MISMATCH'}")
            if not shape_ok:
                report_lines.append(f"  !!! SHAPE MISMATCH for {sample_id}/{model_key} -- NOT resampling, flagging only.")
                continue

            out_tif = vol_dir / f"{sample_id}_{model_key}.tif"
            tifffile.imwrite(str(out_tif), pred_zyx, dtype=np.uint8)
            preds_zyx[model_key] = pred_zyx

            vals, counts = np.unique(pred_zyx, return_counts=True)
            total = pred_zyx.size
            report_lines.append(f"  Wrote {out_tif}")
            report_lines.append(f"  Label set present: {[LABELS.get(int(v), v) for v in vals]}")
            for v, c in zip(vals, counts):
                report_lines.append(f"    {LABELS.get(int(v), v):12s} (id={v}): {c:>10d} voxels ({100*c/total:5.2f}%)")

        # Middle-slice snapshot: volume | predA | predB
        if preds_zyx:
            mid = raw.shape[0] // 2
            fig, axes = plt.subplots(1, 1 + len(preds_zyx), figsize=(6 * (1 + len(preds_zyx)), 6))
            if len(preds_zyx) == 0:
                axes = [axes]
            axes[0].imshow(raw[mid], cmap="gray")
            axes[0].set_title(f"{sample_id}\nvolume z={mid}")
            axes[0].axis("off")
            for i, (model_key, pred_zyx) in enumerate(preds_zyx.items(), start=1):
                axes[i].imshow(pred_zyx[mid], cmap="tab10", vmin=0, vmax=6)
                axes[i].set_title(model_key)
                axes[i].axis("off")
            fig.tight_layout()
            snap_path = vol_dir / f"{sample_id}_snapshot_mid.png"
            fig.savefig(str(snap_path), dpi=120)
            plt.close(fig)
            report_lines.append(f"  Snapshot: {snap_path}")

            # two more snapshots at 25% and 75% depth
            for frac, tag in [(0.25, "q1"), (0.75, "q3")]:
                z = int(raw.shape[0] * frac)
                fig, axes = plt.subplots(1, 1 + len(preds_zyx), figsize=(6 * (1 + len(preds_zyx)), 6))
                axes[0].imshow(raw[z], cmap="gray")
                axes[0].set_title(f"{sample_id}\nvolume z={z}")
                axes[0].axis("off")
                for i, (model_key, pred_zyx) in enumerate(preds_zyx.items(), start=1):
                    axes[i].imshow(pred_zyx[z], cmap="tab10", vmin=0, vmax=6)
                    axes[i].set_title(model_key)
                    axes[i].axis("off")
                fig.tight_layout()
                snap_path = vol_dir / f"{sample_id}_snapshot_{tag}.png"
                fig.savefig(str(snap_path), dpi=120)
                plt.close(fig)
                report_lines.append(f"  Snapshot: {snap_path}")

        (vol_dir / "inference_log.txt").write_text("\n".join(report_lines[-40:]), encoding="utf-8")

    print("\n".join(report_lines))
    (OUT_ROOT / "sanity_check_report.txt").write_text("\n".join(report_lines), encoding="utf-8")
    print(f"\nFull report: {OUT_ROOT / 'sanity_check_report.txt'}")


if __name__ == "__main__":
    main()
