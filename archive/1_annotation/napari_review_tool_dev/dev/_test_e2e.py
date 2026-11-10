"""
End-to-end headless test.
Step 1: SAM vit_b weights download + model load
Step 2: VolumeEmbedder computes embedding on a synthetic slice
Step 3: MaskPredictor3D.predict_region returns a correctly shaped patch
"""
import sys, time
import numpy as np

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

# ── Step 1: SAM model download / load ─────────────────────────────────────
print("=" * 60)
print("Step 1: SAM model load (downloads weights on first run)")
t0 = time.time()
from micro_sam.util import get_sam_model
predictor = get_sam_model(model_type="vit_b")
device = next(predictor.model.parameters()).device
print(f"  SAM loaded in {time.time()-t0:.1f}s | device: {device}")
print(f"  predictor type: {type(predictor).__name__}")

# ── Step 2: VolumeEmbedder on a synthetic volume ───────────────────────────
print()
print("Step 2: VolumeEmbedder — on-demand embedding for one Z-slice")
from embedder import VolumeEmbedder

rng = np.random.default_rng(42)
volume = rng.random((10, 128, 128), dtype=np.float32)
emb = VolumeEmbedder(volume, model_type="vit_b")

t0 = time.time()
feat = emb.get_embedding(5)
t_first = time.time() - t0
print(f"  First call (z=5):  {t_first:.2f}s | features shape: {feat['features'].shape}")

t0 = time.time()
emb.get_embedding(5)           # should be instant (cached)
t_cached = time.time() - t0
print(f"  Cached call (z=5): {t_cached:.4f}s  ← should be ~0")
assert t_cached < 0.1, "Cache miss on second call!"

# ── Step 3: MaskPredictor3D.predict_region ─────────────────────────────────
print()
print("Step 3: MaskPredictor3D.predict_region on small bbox")
from predictor import MaskPredictor3D

pred3d = MaskPredictor3D(emb)
bbox = (3, 6, 20, 80, 20, 80)          # z=3..6, y=20..80, x=20..80
point_coords = np.array([[50, 50]])     # (y, x) global
point_labels = np.array([1])

t0 = time.time()
patch = pred3d.predict_region(bbox, point_coords, point_labels)
print(f"  predict_region took {time.time()-t0:.2f}s")
print(f"  patch shape: {patch.shape}  (expected (3, 60, 60))")
assert patch.shape == (3, 60, 60), f"Wrong shape: {patch.shape}"
assert patch.dtype == np.uint8, f"Wrong dtype: {patch.dtype}"
assert patch.max() <= 1, f"Values out of range: {patch.max()}"
print(f"  patch unique values: {np.unique(patch).tolist()}")

# ── Step 4: CorrectionStore round-trip ─────────────────────────────────────
print()
print("Step 4: CorrectionStore add + export")
from correction_store import CorrectionStore
import tempfile, tifffile
from pathlib import Path

pred_vol = rng.integers(0, 2, size=(10, 128, 128), dtype=np.uint8)
store = CorrectionStore(pred_vol.shape)
store.add(bbox, patch)
assert len(store.corrections) == 1

with tempfile.TemporaryDirectory() as td:
    store.export(td, volume, pred_vol)
    files = list(Path(td).iterdir())
    names = {f.name for f in files}
    assert "corrected_labels.tiff" in names, f"Missing corrected_labels.tiff in {names}"
    assert "pair_0000.npz" in names, f"Missing pair_0000.npz in {names}"
    corr = tifffile.imread(str(Path(td) / "corrected_labels.tiff"))
    assert corr.shape == pred_vol.shape
    with np.load(str(Path(td) / "pair_0000.npz")) as pair:
        vol_shape = pair["volume"].shape
        gt_shape  = pair["gt"].shape
    assert vol_shape == (3, 60, 60)
    assert gt_shape  == (3, 60, 60)
    print(f"  corrected_labels.tiff shape: {corr.shape}")
    print(f"  pair_0000.npz — volume: {vol_shape}, gt: {gt_shape}")

print()
print("ALL STEPS PASSED")
