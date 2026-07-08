import numpy as np
import torch
from micro_sam.util import get_sam_model


class VolumeEmbedder:
    """Lazy, per-Z-slice SAM embedding cache for a 3-D grayscale volume."""

    def __init__(self, volume: np.ndarray, model_type: str = "vit_b", device: str = None):
        self.volume = volume  # (Z, Y, X) float32, values in [0, 1]
        self.model_type = model_type
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._predictor = None
        self._cache: dict[int, dict] = {}

    @property
    def predictor(self):
        if self._predictor is None:
            self._predictor = get_sam_model(model_type=self.model_type, device=self.device)
        return self._predictor

    def _slice_to_rgb(self, z: int) -> np.ndarray:
        s = self.volume[z]
        img = (np.clip(s, 0, 1) * 255).astype(np.uint8)
        return np.stack([img, img, img], axis=-1)

    def get_embedding(self, z: int) -> dict:
        if z not in self._cache:
            self.predictor.set_image(self._slice_to_rgb(z))
            self._cache[z] = {
                "features": self.predictor.features.clone().detach(),
                "original_size": self.predictor.original_size,
                "input_size": self.predictor.input_size,
            }
        return self._cache[z]

    def set_to_slice(self, z: int) -> None:
        """Restore the predictor's state to the cached embedding for slice z."""
        emb = self.get_embedding(z)
        self.predictor.features = emb["features"]
        self.predictor.original_size = emb["original_size"]
        self.predictor.input_size = emb["input_size"]
        self.predictor.is_image_set = True

    def clear_cache(self) -> None:
        self._cache.clear()
