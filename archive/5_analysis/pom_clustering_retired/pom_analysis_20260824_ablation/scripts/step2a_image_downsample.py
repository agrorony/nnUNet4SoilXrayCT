"""Part B step 1 -- block-average downsample the raw, already-preprocessed
Mishmar CT image (norm200 + NLM, 5.85um, the same file that was chunk-split
and fed to loess_i2 to produce the mishmar_native segmentation) to ~15.0um.

Output is written as a single *_0000.nii.gz ready for
02_preprocessing/nnunet/preprocessing_nnUNet_predict_split.py (run with
-s 1 in step2b, since the downsampled volume is small enough not to need
real chunking -- using the split script with s=1 rather than skipping it
keeps the exact same axis-flip/orientation convention the concatenation
script expects).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import nibabel as nib
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from downsample_common import block_mean_image, compute_block_edges, achieved_voxel_um  # noqa: E402

SOURCE_PATH = (
    r"\\hive3065\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources"
    r"\mishmar_hanegev_maoz_3_5p85um\nifti_predict\mishmar_hanegev_maoz_3_5p85um_0000.nii.gz"
)
SOURCE_VOXEL_UM = 5.85
TARGET_VOXEL_UM = 15.000149

HIVE = r"\\hive3065\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources"
SID = "mishmar_image_then_predict"
SAMPLE_BASE = fr"{HIVE}\mishmar_hanegev_maoz_3_5p85um\ablation_image_downsample"
NIFTI_PREDICT_DIR = fr"{SAMPLE_BASE}\nifti_predict_ds15um"


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def main() -> None:
    Path(NIFTI_PREDICT_DIR).mkdir(parents=True, exist_ok=True)

    log(f"Loading {SOURCE_PATH}")
    vol = np.asarray(nib.load(SOURCE_PATH).dataobj).astype(np.float32)
    n = vol.shape[0]
    assert vol.shape == (n, n, n), f"expected a cube, got {vol.shape}"
    log(f"  source shape={vol.shape} dtype={vol.dtype} voxel_um={SOURCE_VOXEL_UM} "
        f"min={vol.min():.4f} max={vol.max():.4f} mean={vol.mean():.4f}")

    edges = compute_block_edges(n, TARGET_VOXEL_UM, SOURCE_VOXEL_UM)
    m = len(edges) - 1
    v_um = achieved_voxel_um(n, edges, SOURCE_VOXEL_UM)
    log(f"  block partition: n={n} -> m={m} blocks/axis, mean block size={n/m:.4f} vox, "
        f"achieved voxel size={v_um:.4f}um (target {TARGET_VOXEL_UM}um)")

    t0 = time.time()
    ds = block_mean_image(vol, edges)
    log(f"  block-mean downsample done ({time.time()-t0:.1f}s) -> shape={ds.shape} "
        f"min={ds.min():.4f} max={ds.max():.4f} mean={ds.mean():.4f}")
    del vol

    out_path = Path(NIFTI_PREDICT_DIR) / f"{SID}_0000.nii.gz"
    nib.save(nib.Nifti1Image(ds, affine=np.eye(4)), str(out_path))
    log(f"  wrote {out_path}")

    print("\n" + "=" * 70)
    print(f"achieved_voxel_um={v_um:.6f}  shape={list(ds.shape)}  output={out_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
