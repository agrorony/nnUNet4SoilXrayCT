#!/usr/bin/env python
"""
Global Otsu thresholding on 3D TIFF volumes.

Loads a full 3D `.tif` volume, applies global Otsu thresholding across the entire volume,
converts to binary, and saves as `.npy` file.

Thresholding logic controlled by --pore-is-dark flag (default: True):
  - If True (default):  volume < threshold → True (pore)
  - If False:           volume > threshold → True (pore)

Dependencies:
  - numpy
  - tifffile
  - scikit-image (threshold_otsu)
  - argparse (stdlib)
  - pathlib (stdlib)
"""

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import tifffile
from skimage.filters import threshold_otsu


def validate_input(input_path):
    """
    Validate that input file exists and has `.tif` extension.
    
    Args:
        input_path (str): Path to input TIFF file.
        
    Raises:
        FileNotFoundError: If file does not exist.
        ValueError: If file does not end in `.tif`.
    """
    p = Path(input_path)
    if not p.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    if p.suffix.lower() != ".tif":
        raise ValueError(f"Input file must be `.tif`, got: {p.suffix}")


def load_volume(input_path):
    """
    Load 3D TIFF volume.
    
    Args:
        input_path (str): Path to TIFF file.
        
    Returns:
        np.ndarray: 3D volume array.
        
    Raises:
        ValueError: If volume is not 3D.
    """
    volume = tifffile.imread(input_path)
    
    if volume.ndim != 3:
        raise ValueError(
            f"Expected 3D volume, got {volume.ndim}D volume with shape {volume.shape}"
        )
    
    return volume


def otsu_threshold_3d(volume, pore_is_dark=True):
    """
    Apply global Otsu thresholding to 3D volume.
    
    Args:
        volume (np.ndarray): 3D grayscale volume.
        pore_is_dark (bool): If True, pores are dark (volume < threshold).
                             If False, pores are bright (volume > threshold).
                             Default: True.
    
    Returns:
        tuple: (binary_mask, threshold_value)
            binary_mask (np.ndarray, dtype=bool): Binary 3D mask.
            threshold_value (float): Otsu threshold computed globally on entire volume.
    """
    # Compute global Otsu threshold on entire volume
    threshold_value = threshold_otsu(volume)
    
    # Apply threshold based on pore-is-dark flag
    if pore_is_dark:
        binary_mask = volume < threshold_value
    else:
        binary_mask = volume > threshold_value
    
    return binary_mask, threshold_value


def get_output_path(input_path, output_path=None):
    """
    Derive output `.npy` path from input TIFF path.
    
    Args:
        input_path (str): Path to input TIFF file.
        output_path (str, optional): Explicit output path. If provided, used as-is.
    
    Returns:
        str: Path to output `.npy` file.
    """
    if output_path is not None:
        return output_path
    
    p = Path(input_path)
    return str(p.with_suffix(".npy"))


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Apply global Otsu thresholding to 3D TIFF volumes and save as `.npy`."
    )
    parser.add_argument(
        "input",
        type=str,
        help="Path to input 3D `.tif` volume.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Path to output `.npy` file. If not provided, derived from input filename.",
    )
    parser.add_argument(
        "--pore-is-dark",
        action="store_true",
        default=True,
        help="If set, pores are dark (volume < threshold). Default: True.",
    )
    parser.add_argument(
        "--no-pore-is-dark",
        action="store_false",
        dest="pore_is_dark",
        help="If set, pores are bright (volume > threshold).",
    )
    
    args = parser.parse_args()
    
    try:
        # Validate input
        validate_input(args.input)
        
        # Load volume
        print(f"Loading volume from: {args.input}")
        volume = load_volume(args.input)
        
        print(f"  Input shape: {volume.shape}")
        print(f"  Input dtype: {volume.dtype}")
        
        # Apply Otsu thresholding
        binary_mask, threshold_value = otsu_threshold_3d(
            volume, pore_is_dark=args.pore_is_dark
        )
        
        # Determine output path
        output_path = get_output_path(args.input, args.output)
        
        # Save binary mask
        np.save(output_path, binary_mask, allow_pickle=False)
        
        # Print summary
        print(f"\nThresholding Summary:")
        print(f"  Threshold value: {threshold_value}")
        print(f"  Pore is dark: {args.pore_is_dark}")
        print(f"  Output shape: {binary_mask.shape}")
        print(f"  Output dtype: {binary_mask.dtype}")
        print(f"  Output saved to: {output_path}")
        
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
