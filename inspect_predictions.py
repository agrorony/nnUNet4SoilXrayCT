#!/usr/bin/env python
"""
Inspect a prediction volume alongside the original 3D volume in Napari.

Version 1 scope:
- Single prediction + single original volume
- Viewer-only workflow (no manifest export)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import nibabel as nib
import numpy as np
import tifffile


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Open Napari with original volume and prediction overlay."
    )
    parser.add_argument(
        "--prediction_volume",
        type=Path,
        required=True,
        help="Path to prediction volume (.nii/.nii.gz/.tif/.tiff/.mha).",
    )
    parser.add_argument(
        "--original_volume",
        type=Path,
        required=True,
        help="Path to original image volume (.nii/.nii.gz/.tif/.tiff/.mha).",
    )
    parser.add_argument(
        "--prediction_opacity",
        type=float,
        default=0.5,
        help="Prediction labels opacity in [0, 1]. Default: 0.5.",
    )
    parser.add_argument(
        "--hide_prediction",
        action="store_true",
        help="Start with prediction layer hidden.",
    )
    parser.add_argument(
        "--original_layer_name",
        default="Original",
        help="Napari layer name for original image. Default: Original.",
    )
    parser.add_argument(
        "--prediction_layer_name",
        default="Prediction",
        help="Napari layer name for prediction labels. Default: Prediction.",
    )
    parser.add_argument(
        "--flip_axes",
        type=str,
        default="",
        help="Comma-separated axis indices to flip prediction (0=Z, 1=Y, 2=X). E.g. '1' or '0,1'.",
    )
    parser.add_argument(
        "--dataset_info",
        type=Path,
        default=None,
        help="Path to dataset_info.json for reverse label mapping (to show original annotation labels).",
    )
    parser.add_argument(
        "--reverse_label_map",
        action="store_true",
        help="If set, reverse the nnUNet label shift to show original annotation labels.",
    )
    return parser.parse_args()


def _ensure_exists(path: Path, arg_name: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{arg_name} does not exist: {path}")


def _load_with_simpleitk(path: Path) -> np.ndarray:
    try:
        import SimpleITK as sitk
    except ImportError as exc:
        raise ImportError(
            "SimpleITK is required to load .mha files but is not installed."
        ) from exc

    image = sitk.ReadImage(str(path))
    vol = sitk.GetArrayFromImage(image)
    if vol.ndim != 3:
        raise ValueError(f"Expected 3D MHA volume, got shape={vol.shape}")
    return vol


def load_volume_as_zyx(input_volume: Path) -> np.ndarray:
    suffixes = "".join(input_volume.suffixes).lower()

    if suffixes.endswith(".tif") or suffixes.endswith(".tiff"):
        vol = tifffile.imread(str(input_volume))
        if vol.ndim != 3:
            raise ValueError(f"Expected 3D TIFF volume, got shape={vol.shape}")
        return vol

    if suffixes.endswith(".nii") or suffixes.endswith(".nii.gz"):
        vol = nib.load(str(input_volume)).get_fdata()
        if vol.ndim != 3:
            raise ValueError(f"Expected 3D NIfTI volume, got shape={vol.shape}")
        return vol.transpose(2, 1, 0)

    if suffixes.endswith(".mha"):
        return _load_with_simpleitk(input_volume)

    raise ValueError(
        f"Unsupported input format for {input_volume}. "
        "Supported: .nii/.nii.gz/.tif/.tiff/.mha"
    )


def _validate_inputs(original_zyx: np.ndarray, prediction_zyx: np.ndarray) -> None:
    if original_zyx.ndim != 3:
        raise ValueError(f"Original volume must be 3D. Got shape={original_zyx.shape}")
    if prediction_zyx.ndim != 3:
        raise ValueError(
            f"Prediction volume must be 3D. Got shape={prediction_zyx.shape}"
        )
    if original_zyx.shape != prediction_zyx.shape:
        raise ValueError(
            "Volume shape mismatch: "
            f"original={original_zyx.shape}, prediction={prediction_zyx.shape}."
        )


def _reverse_nnunet_label_shift(prediction: np.ndarray, num_annotated_classes: int) -> np.ndarray:
    """
    Reverse the nnUNet label shift to restore original annotation labels.

    nnUNet training applies: label 0 → num_classes (ignore), then all -= 1
    So nnUNet output labels are shifted -1 relative to original annotation.

    Reverse mapping:
    - nnUNet label 0 → annotation label 1
    - nnUNet label 2 → annotation label 3
    - nnUNet label num_classes-1 (ignore) → annotation label 0

    :param prediction: NIfTI prediction array with nnUNet labels
    :param num_annotated_classes: Number of originally annotated classes (excluding ToPredict/0)
    :return: Prediction array with original annotation labels
    """
    remapped = prediction.copy()
    ignore_label = num_annotated_classes  # nnUNet ignore label

    # Ignore label (nnUNet) → 0 (ToPredict in annotation)
    remapped[prediction == ignore_label] = 0

    # All other nnUNet labels (0 through num_classes-2): add 1 to restore original
    mask = prediction < ignore_label
    remapped[mask] = prediction[mask] + 1

    return remapped


def launch_napari(
    original_zyx: np.ndarray,
    prediction_zyx: np.ndarray,
    original_layer_name: str,
    prediction_layer_name: str,
    prediction_opacity: float,
    hide_prediction: bool,
    flip_axes: list[int] | None = None,
    reverse_label_map: bool = False,
    num_annotated_classes: int | None = None,
) -> None:
    try:
        import napari
    except ImportError as exc:
        raise ImportError(
            "Napari is not installed in the active environment. "
            "Install napari (or devbio-napari) in venv-napari."
        ) from exc

    if flip_axes:
        for ax in flip_axes:
            prediction_zyx = np.flip(prediction_zyx, axis=ax)

    if reverse_label_map and num_annotated_classes is not None:
        prediction_zyx = _reverse_nnunet_label_shift(prediction_zyx, num_annotated_classes)
        prediction_layer_name = f"{prediction_layer_name} (annotation labels)"

    viewer = napari.Viewer(title="Prediction Inspector")
    viewer.add_image(
        original_zyx,
        name=original_layer_name,
        colormap="gray",
        blending="translucent",
    )
    viewer.add_labels(
        prediction_zyx.astype(np.int32),
        name=prediction_layer_name,
        opacity=prediction_opacity,
        visible=not hide_prediction,
        blending="additive",
    )
    print("Napari viewer open. Close the window to exit.")
    napari.run()


def main() -> None:
    args = parse_args()

    if not (0.0 <= args.prediction_opacity <= 1.0):
        raise ValueError("--prediction_opacity must be between 0 and 1.")

    _ensure_exists(args.original_volume, "--original_volume")
    _ensure_exists(args.prediction_volume, "--prediction_volume")

    original_zyx = load_volume_as_zyx(args.original_volume)
    prediction_zyx = load_volume_as_zyx(args.prediction_volume)

    _validate_inputs(original_zyx, prediction_zyx)

    flip_axes = [int(a) for a in args.flip_axes.split(",") if a.strip()] if args.flip_axes else []

    num_annotated_classes = None
    if args.reverse_label_map:
        if args.dataset_info is None:
            # Try default location
            args.dataset_info = Path(__file__).parent / "dataset_info.json"
        if args.dataset_info.exists():
            with open(args.dataset_info) as f:
                metadata = json.load(f)
                labels = metadata.get("labels", {})
                # Number of annotated classes = total labels minus ToPredict (label 0)
                num_annotated_classes = len(labels) - 1
                print(f"Loaded {num_annotated_classes} annotated classes from {args.dataset_info}")
        else:
            print(f"Warning: --reverse_label_map requested but dataset_info not found at {args.dataset_info}")

    launch_napari(
        original_zyx=original_zyx,
        prediction_zyx=prediction_zyx,
        original_layer_name=args.original_layer_name,
        prediction_layer_name=args.prediction_layer_name,
        prediction_opacity=args.prediction_opacity,
        hide_prediction=args.hide_prediction,
        flip_axes=flip_axes,
        reverse_label_map=args.reverse_label_map,
        num_annotated_classes=num_annotated_classes,
    )


if __name__ == "__main__":
    main()
