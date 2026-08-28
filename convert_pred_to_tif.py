import nibabel as nib
import numpy as np
import tifffile
import argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("input", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()

nii = nib.load(args.input)
data = nii.get_fdata(dtype=np.float32).astype(np.uint8)
print(f"NIfTI shape: {data.shape}, unique labels: {np.unique(data)}")

# NIfTI is (X,Y,Z), TIF expects (Z,Y,X)
data = np.transpose(data, (2, 1, 0))
print(f"After transpose: {data.shape}")

tifffile.imwrite(args.output, data)
print(f"Saved to {args.output}")
