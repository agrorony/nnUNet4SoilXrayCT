"""
Direct .tif -> nnUNet _0000.nii.gz conversion for prediction, without ImageJ.

preprocessing_nnUNet_predict_tif.py requires ImageJ (PATH_ImageJ in __path__.py),
which is unconfigured on this machine. This script reads a single 3D .tif volume
directly with tifffile, applies noNorm (data is already norm200+NLM preprocessed),
and writes it out in nnUNet's (X, Y, Z) NIfTI convention with an identity affine
(matches the convention used by existing nifti_predict inputs in this project).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import nibabel as nib
import numpy as np
import tifffile


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input_tif", required=True, type=Path)
    parser.add_argument("--output_dir", required=True, type=Path)
    parser.add_argument("--sample_id", required=True)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    vol_zyx = tifffile.imread(str(args.input_tif))
    if vol_zyx.ndim != 3:
        raise ValueError(f"Expected 3D volume, got shape={vol_zyx.shape}")

    vol_xyz = vol_zyx.astype(np.float32).transpose(2, 1, 0)
    out_path = args.output_dir / f"{args.sample_id}_0000.nii.gz"
    nib.save(nib.Nifti1Image(vol_xyz, np.eye(4)), str(out_path))
    print(f"Wrote {out_path}, shape={vol_xyz.shape}")


if __name__ == "__main__":
    main()
