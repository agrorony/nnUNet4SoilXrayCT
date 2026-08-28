"""Read-only napari viewer for a completed FULL-volume PSD/topology run.

Generalizes napari_view_connectivity_validation.py (which is hardcoded to the
100x200x200 bnei_reem_i4_crop200 validation crop) to any full-volume
extended-mode run directory produced by run_psd_batch.py / run_psd_diagnostics.py,
and additionally loads the POM distance maps (the crop-validation script only
loaded the two pore ones).

Everything is loaded via plain nibabel/tifffile arrays in their native storage
order -- deliberately NOT microsam_3d/run.py's (Z,Y,X)+Y-flip .nii.gz
convention. The segmentation and the distance-map .tif files were produced by
the same PSD pipeline from the same np.asarray(nib.load(...).dataobj) call
(see run_psd_diagnostics.py::_load_labeled_volume), so they are already in a
mutually consistent order; the raw grayscale volume is loaded the same way
from the exact nifti_predict input the segmentation model consumed, which is
shape-identical to the segmentation. No transpose/flip is applied to any of
them here -- this script only adds display layers, it does not touch
alignment logic.

Usage:
    python napari_view_full_volume.py \\
        --run-dir "<psd_outputs>/psd_diag_20260802T104738_nlm_volume_fresh_bnei_reem_i4" \\
        --segmentation "<...>/bnei_reem_fresh_bnei_reem_i4/inference_concatenated/nlm_volume.nii.gz" \\
        --raw-source "<...>/bnei_reem_iter04/nifti_predict/nlm_volume_0000.nii.gz"
"""
import argparse
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_PSD_DIR = os.path.dirname(_HERE)  # 05_evaluation/psd
_MICROSAM_DIR = os.path.join(os.path.dirname(_PSD_DIR), "microsam_3d")  # 05_evaluation/microsam_3d

sys.path.insert(0, _PSD_DIR)
sys.path.insert(0, _MICROSAM_DIR)

_DIST_FILES = {
    "distance-to-pore (unconditioned, um)": "distance_to_pore_unconditioned.tif",
    "distance-to-pore (connected/percolating, um)": "distance_to_pore_connected.tif",
    "distance-to-POM (unconditioned, um)": "distance_to_pom_unconditioned.tif",
    "distance-to-POM (connected/percolating, um)": "distance_to_pom_connected.tif",
}


def main(
    run_dir: str,
    segmentation_path: str,
    raw_source_path: str,
    pore_label: int,
    pom_label: int,
    axis: int,
    title: str,
) -> None:
    import nibabel as nib
    import tifffile
    import napari
    from psd_topology_metrics import get_percolating_mask

    print(f"Loading segmentation: {segmentation_path}")
    labeled_vol = np.asarray(nib.load(segmentation_path).dataobj)
    print(f"  shape={labeled_vol.shape} dtype={labeled_vol.dtype} labels={np.unique(labeled_vol)}")

    print(f"Loading raw volume: {raw_source_path}")
    raw_volume = np.asarray(nib.load(raw_source_path).dataobj)
    print(f"  shape={raw_volume.shape} dtype={raw_volume.dtype}")

    pore_mask = labeled_vol == pore_label
    print(f"Computing connected/percolating pore mask (axis={axis}) ...")
    connected_mask = get_percolating_mask(pore_mask, axis=axis)
    print(f"  pore voxels: {pore_mask.sum():,}  connected voxels: {connected_mask.sum():,}")

    dist_maps = {}
    for layer_name, fname in _DIST_FILES.items():
        path = os.path.join(run_dir, fname)
        if not os.path.isfile(path):
            print(f"  [SKIP] missing: {path}")
            continue
        print(f"Loading {fname} ...")
        dist_maps[layer_name] = tifffile.imread(path)

    shapes = {
        "segmentation": labeled_vol.shape,
        "connected_mask": connected_mask.shape,
        "raw_volume": raw_volume.shape,
        **{name: arr.shape for name, arr in dist_maps.items()},
    }
    if len(set(shapes.values())) != 1:
        raise ValueError(f"Layer shape mismatch, refusing to load misaligned layers: {shapes}")

    viewer = napari.Viewer(title=title)

    # Only volume + segmentation visible by default -- an opaque heatmap
    # layer added on top by default hides the volume beneath it and looks
    # like a misalignment bug even when everything is pixel-aligned (see
    # napari_view_connectivity_validation.py's note on this). Toggle other
    # layers on in the layer list once alignment looks right.
    viewer.add_image(raw_volume, name="volume", colormap="gray")
    viewer.add_labels(labeled_vol.astype(np.uint8), name="segmentation (matrix/pore/POM)")
    viewer.add_labels(
        connected_mask.astype(np.uint8),
        name=f"connected pore mask (percolating, axis={axis})",
        visible=False,
    )

    pore_dist_max = max(
        (dist_maps[k].max() for k in dist_maps if k.startswith("distance-to-pore") and np.isfinite(dist_maps[k]).any()),
        default=1.0,
    )
    pom_dist_max = max(
        (dist_maps[k].max() for k in dist_maps if k.startswith("distance-to-POM") and np.isfinite(dist_maps[k]).any()),
        default=1.0,
    )
    for layer_name, arr in dist_maps.items():
        cmax = float(pore_dist_max if layer_name.startswith("distance-to-pore") else pom_dist_max)
        viewer.add_image(
            arr, name=layer_name, colormap="magma",
            contrast_limits=(0.0, cmax), visible=False,
        )

    print("Docking microSAM plugin widgets ...")
    from napari_plugin import create_widget, create_adjust_widget
    panel1, panel2 = create_widget(viewer)
    viewer.window.add_dock_widget(panel1, area="right", name="MicroSAM — Error Search")
    viewer.window.add_dock_widget(panel2, area="right", name="MicroSAM — Corrections")
    adjust_widget = create_adjust_widget(viewer)
    viewer.window.add_dock_widget(adjust_widget, area="right", name="Adjust layer")

    print("\nLayer legend (bottom-left panel):")
    print("  volume                                        raw grayscale CT")
    print(f"  segmentation (matrix/pore/POM)                 labels 0/1/2/5; pore=={pore_label}, POM=={pom_label}")
    print(f"  connected pore mask (percolating, axis={axis})          subset of pore feeding connectivity/anisotropy/tortuosity metrics")
    for layer_name in dist_maps:
        print(f"  {layer_name}")
    print("Only 'volume' + 'segmentation' are visible by default; toggle others on in the layer list.\n")

    print("Layers and widgets ready. Entering napari event loop ...")
    napari.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run-dir", required=True,
                         help="PSD run output directory containing the distance-map .tif files.")
    parser.add_argument("--segmentation", required=True,
                         help="Segmented (matrix/pore/POM) .nii.gz volume the run was computed from.")
    parser.add_argument("--raw-source", required=True,
                         help="Raw grayscale .nii.gz, shape-identical to --segmentation (the nifti_predict "
                              "input the segmentation model consumed).")
    parser.add_argument("--pore-label", type=int, default=5)
    parser.add_argument("--pom-label", type=int, default=2)
    parser.add_argument("--axis", type=int, default=0, help="Percolation axis (0=Z), matches the pipeline default.")
    parser.add_argument("--title", default="PSD/connectivity full-volume viewer")
    args = parser.parse_args()
    main(
        args.run_dir, args.segmentation, args.raw_source,
        args.pore_label, args.pom_label, args.axis, args.title,
    )
