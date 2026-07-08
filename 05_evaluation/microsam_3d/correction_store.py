from pathlib import Path
import numpy as np
import tifffile


class CorrectionStore:
    """Accumulates accepted corrections and exports them as retraining pairs."""

    def __init__(self, pred_shape: tuple):
        self.pred_shape = pred_shape
        self.corrections: list[dict] = []  # [{bbox, patch}]

    def add(self, bbox: tuple, corrected_patch: np.ndarray) -> None:
        self.corrections.append({"bbox": bbox, "patch": corrected_patch.copy()})

    def apply_to(self, label_map: np.ndarray) -> np.ndarray:
        out = label_map.copy()
        for c in self.corrections:
            z0, z1, y0, y1, x0, x1 = c["bbox"]
            out[z0:z1, y0:y1, x0:x1] = c["patch"]
        return out

    def export(self, path: str | Path, volume: np.ndarray, pred: np.ndarray) -> None:
        """Save corrected label map as TIFF + (volume_crop, gt_crop) .npz pairs."""
        out_dir = Path(path)
        out_dir.mkdir(parents=True, exist_ok=True)

        corrected = self.apply_to(pred)
        tifffile.imwrite(str(out_dir / "corrected_labels.tiff"), corrected)

        for i, c in enumerate(self.corrections):
            z0, z1, y0, y1, x0, x1 = c["bbox"]
            np.savez(
                str(out_dir / f"pair_{i:04d}.npz"),
                volume=volume[z0:z1, y0:y1, x0:x1],
                gt=c["patch"],
            )

        print(f"Exported {len(self.corrections)} corrections -> {out_dir}")
