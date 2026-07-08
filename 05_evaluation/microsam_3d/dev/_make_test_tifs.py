"""Write a tiny (20x128x128) synthetic volume + label pair for napari smoke-test."""
import numpy as np
import tifffile, pathlib

rng = np.random.default_rng(0)
vol  = (rng.random((20, 128, 128)) * 255).astype(np.uint16)
pred = rng.integers(0, 2, size=(20, 128, 128), dtype=np.uint8)

out = pathlib.Path(__file__).parent
tifffile.imwrite(str(out / "_test_vol.tif"),  vol)
tifffile.imwrite(str(out / "_test_pred.tif"), pred)
print("Written:", out / "_test_vol.tif", out / "_test_pred.tif")
