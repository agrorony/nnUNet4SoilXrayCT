import numpy as np
from embedder import VolumeEmbedder


class MaskPredictor3D:
    """Runs SAM on each Z-slice within a 3-D bbox, using on-demand embeddings."""

    def __init__(self, embedder: VolumeEmbedder):
        self.embedder = embedder

    def predict_region(
        self,
        bbox: tuple[int, int, int, int, int, int],
        point_coords: np.ndarray = None,
        point_labels: np.ndarray = None,
    ) -> np.ndarray:
        """Predict a corrected label patch for the bbox.

        bbox: (z0, z1, y0, y1, x0, x1) in global voxel coords.
        point_coords: (N, 2) array in (y, x) global coords.
        point_labels: (N,) array, 1=foreground 0=background.

        Returns: uint8 (z1-z0, y1-y0, x1-x0) patch, values 0/1.
        """
        z0, z1, y0, y1, x0, x1 = bbox
        # SAM expects box as (x0, y0, x1, y1)
        box = np.array([[x0, y0, x1, y1]], dtype=np.float32)

        predict_kwargs: dict = {"box": box, "multimask_output": False}
        if point_coords is not None:
            # convert (y,x) → (x,y) for SAM
            pc_xy = point_coords[:, ::-1].copy().astype(np.float32)
            predict_kwargs["point_coords"] = pc_xy
            predict_kwargs["point_labels"] = point_labels.astype(np.int32)

        patches = []
        for z in range(z0, z1):
            self.embedder.set_to_slice(z)
            mask, _, _ = self.embedder.predictor.predict(**predict_kwargs)
            # mask: (1, H, W) bool → crop to bbox region
            patches.append(mask[0, y0:y1, x0:x1].astype(np.uint8))

        return np.stack(patches, axis=0)  # (Z, Y, X)
