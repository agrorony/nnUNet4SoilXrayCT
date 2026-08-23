"""Read-only napari viewer for the PSD/connectivity-metrics validation run.

Loads the bnei_reem_i4_crop200 validation inputs/outputs as separate,
spatially-aligned layers so the connectivity-conditioned distance maps can be
inspected in 3D (rotate/scroll) rather than only via the static mid-slice
PNGs. Everything is loaded in the same raw array order the PSD pipeline
itself used (plain `nibabel`/`tifffile` arrays, no axis transpose/flip) —
this is deliberately NOT microsam_3d/run.py's (Z,Y,X) + Y-flip convention,
because that convention is only applied to its .nii.gz loader and not its
.tif loader, which would silently misalign the segmentation against the
distance-map .tif files if reused here.

Also loads the matching raw grayscale CT crop (same Z200:300/Y200:400/X200:400
window, cropped from the network-share nlm_volume_0000.nii.gz raw input, cached
locally as raw_volume_crop.npy) and docks the microSAM 3D proofreader's plugin
widgets (05_evaluation/microsam_3d/napari_plugin.py) on the same viewer, so the
image/label-layer dropdowns in those widgets can be pointed at any of the
layers loaded here.

The raw crop's Z/Y/X bounds (_DEFAULT_CROP_BOUNDS) are the single source of
truth for where raw_volume_crop.npy comes from. Previously that .npy was a
hand-built, disconnected cache file with no reproducible generator, which let
it silently drift out of sync with the segmentation crop (same shape, wrong
window -> masks rendered visibly shifted against the grayscale volume beneath
them). `_load_or_build_raw_crop()` below re-derives the crop from
--raw-source using --crop-bounds and cross-checks it against any cached .npy
byte-for-byte, rebuilding the cache instead of trusting a stale/mismatched one.

Usage:
    python napari_view_connectivity_validation.py
    python napari_view_connectivity_validation.py --run-dir <other_run_dir> --input <other_volume.nii.gz>
"""
import argparse
import os
import sys

import numpy as np
import tifffile

_HERE = os.path.dirname(os.path.abspath(__file__))
_PSD_DIR = os.path.dirname(_HERE)  # 05_evaluation/psd
_MICROSAM_DIR = os.path.join(os.path.dirname(_PSD_DIR), "microsam_3d")  # 05_evaluation/microsam_3d
_DEFAULT_RUN_DIR = os.path.join(
    _HERE, "validation_run", "out", "psd_diag_20260707T134721_bnei_reem_i4_crop200"
)
_DEFAULT_INPUT = os.path.join(_HERE, "validation_run", "sub_z200_300_crop200.nii.gz")
_DEFAULT_RAW_VOLUME = os.path.join(_HERE, "validation_run", "raw_volume_crop.npy")
_DEFAULT_RAW_SOURCE = (
    r"\\hive3065\Yael_Mishael\Rony\remote_computer backup"
    r"\nnUNet_resources\bnei_reem_iter04\nifti_predict\nlm_volume_0000.nii.gz"
)
_DEFAULT_CROP_BOUNDS = (200, 300, 200, 400, 200, 400)  # z0, z1, y0, y1, x0, x1

sys.path.insert(0, _PSD_DIR)
sys.path.insert(0, _MICROSAM_DIR)


def _load_or_build_raw_crop(cache_path, raw_source_path, crop_bounds):
    """Return the raw grayscale crop, verified against --raw-source at
    --crop-bounds rather than trusted blindly from a cached .npy.

    Rebuilds (and overwrites) the cache whenever it's missing or its content
    doesn't match a fresh crop of the same window from raw_source_path --
    this is what protects against the exact bug this viewer previously hit:
    a cached crop, correct in shape, taken from the wrong offset/source.
    """
    import nibabel as nib

    z0, z1, y0, y1, x0, x1 = crop_bounds
    cached = None
    if os.path.isfile(cache_path):
        cached = np.load(cache_path)
        print(f"  Found cached raw crop: {cache_path}  shape={cached.shape}")

    if not os.path.isfile(raw_source_path):
        if cached is None:
            raise FileNotFoundError(
                f"No cached raw crop at {cache_path} and --raw-source is unreachable: {raw_source_path}"
            )
        print(f"  [WARN] --raw-source unreachable ({raw_source_path}); using cached crop unverified.")
        return cached

    print(f"  Deriving raw crop from source: {raw_source_path}  bounds=Z{z0}:{z1}/Y{y0}:{y1}/X{x0}:{x1}")
    source_vol = np.asarray(nib.load(raw_source_path).dataobj)
    fresh = source_vol[z0:z1, y0:y1, x0:x1]

    if cached is not None and cached.shape == fresh.shape and np.array_equal(cached, fresh):
        print("  Cached raw crop matches source crop exactly — using cache.")
        return cached

    if cached is not None:
        print("  [FIX] Cached raw crop did NOT match a fresh crop from --raw-source at the "
              "expected bounds (stale/misaligned cache) — rebuilding and overwriting it.")
    np.save(cache_path, fresh)
    return fresh


def main(
    run_dir: str, input_path: str, raw_volume_path: str,
    pore_label: int, pom_label: int, axis: int,
    raw_source_path: str = _DEFAULT_RAW_SOURCE,
    crop_bounds=_DEFAULT_CROP_BOUNDS,
) -> None:
    import nibabel as nib
    import napari
    from psd_topology_metrics import get_percolating_mask

    print(f"Loading segmented volume: {input_path}")
    labeled_vol = np.asarray(nib.load(input_path).dataobj)
    print(f"  shape={labeled_vol.shape} dtype={labeled_vol.dtype} labels={np.unique(labeled_vol)}")

    pore_mask = labeled_vol == pore_label
    print(f"Computing connected/percolating pore mask (axis={axis}, same call as the pipeline) ...")
    connected_mask = get_percolating_mask(pore_mask, axis=axis)
    print(f"  pore voxels: {pore_mask.sum():,}  connected voxels: {connected_mask.sum():,}")

    dist_unconditioned_path = os.path.join(run_dir, "distance_to_pore_unconditioned.tif")
    dist_connected_path = os.path.join(run_dir, "distance_to_pore_connected.tif")
    print(f"Loading distance maps:\n  {dist_unconditioned_path}\n  {dist_connected_path}")
    dist_unconditioned = tifffile.imread(dist_unconditioned_path)
    dist_connected = tifffile.imread(dist_connected_path)

    print(f"Loading raw grayscale CT crop (cache: {raw_volume_path}) ...")
    raw_volume = _load_or_build_raw_crop(raw_volume_path, raw_source_path, crop_bounds)

    shapes = {
        "segmentation": labeled_vol.shape,
        "connected_mask": connected_mask.shape,
        "dist_unconditioned": dist_unconditioned.shape,
        "dist_connected": dist_connected.shape,
        "raw_volume": raw_volume.shape,
    }
    if len(set(shapes.values())) != 1:
        raise ValueError(f"Layer shape mismatch, refusing to load misaligned layers: {shapes}")

    viewer = napari.Viewer(title="PSD/connectivity validation — bnei_reem_i4_crop200")

    # Only the raw volume + full segmentation are visible on open. The other
    # three layers are diagnostic overlays computed FROM the segmentation
    # (not independent alignment checks) — showing them all at once by
    # default (as this used to) stacks multiple opaque/translucent layers on
    # top of the grayscale volume, and the topmost one (an opaque magma
    # heatmap, added last -> rendered on top) fully hides the volume beneath
    # it. That looked exactly like a "the volume is shifted / I can't tell
    # what I'm looking at" bug even when the underlying arrays are pixel-
    # aligned (see _load_or_build_raw_crop above) — it was a default-
    # visibility/z-order issue, not a data offset. Toggle layers on in the
    # layer list (bottom-left panel) to cross-check any of them individually.
    viewer.add_image(
        raw_volume, name="volume", colormap="gray",
    )
    viewer.add_labels(
        labeled_vol.astype(np.uint8), name="segmentation (matrix/pore/POM)",
    )
    viewer.add_labels(
        connected_mask.astype(np.uint8), name=f"connected pore mask (percolating, axis={axis})",
        visible=False,
    )
    # Shared contrast limits so toggling between the two is a fair comparison.
    shared_max = float(max(dist_unconditioned.max(), dist_connected.max()))
    viewer.add_image(
        dist_unconditioned, name="distance-to-pore (unconditioned, um)",
        colormap="magma", contrast_limits=(0.0, shared_max), visible=False,
    )
    viewer.add_image(
        dist_connected, name="distance-to-pore (connected/percolating, um)",
        colormap="magma", contrast_limits=(0.0, shared_max), visible=False,
    )

    print("Docking microSAM plugin widgets ...")
    from napari_plugin import create_widget, create_adjust_widget
    panel1, panel2 = create_widget(viewer)
    viewer.window.add_dock_widget(panel1, area="right", name="MicroSAM — Error Search")
    viewer.window.add_dock_widget(panel2, area="right", name="MicroSAM — Corrections")
    adjust_widget = create_adjust_widget(viewer)
    viewer.window.add_dock_widget(adjust_widget, area="right", name="Adjust layer")

    print("\nLayer legend (bottom-left panel) -> what it is / which metrics it feeds:")
    print("  volume                                     raw grayscale CT crop (this run's --raw-source window)")
    print("  segmentation (matrix/pore/POM)              --input labels 0/1/2/5; pore==5 feeds ALL metrics below")
    print(f"  connected pore mask (percolating, axis={axis})       STRICT SUBSET of the pore label above (only the "
          f"top<->bottom-percolating cluster) -> Connectivity_Density, Connectivity_Probability_Gamma, "
          f"Degree_of_Anisotropy, Tortuosity_Axis0/1/2 columns in psd_table.csv. It will NOT cover every pore "
          f"voxel shown in 'segmentation' — dead-end/isolated pores are excluded by design, that is not misalignment.")
    print("  distance-to-pore (unconditioned, um)        distance_to_pore_unconditioned.tif -> base/legacy PSD")
    print("  distance-to-pore (connected/percolating, um) distance_to_pore_connected.tif -> Item-1 "
          "connectivity-conditioned distance metrics (D1 in decisions.md)")
    print("Only 'volume' + 'segmentation' are visible by default so you can sanity-check alignment first; "
          "toggle the others on in the layer list once that looks right.\n")

    print("Layers and widgets ready. Entering napari event loop ...")
    napari.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run-dir", default=_DEFAULT_RUN_DIR,
                         help="Validation-run output directory containing the distance-map .tif files.")
    parser.add_argument("--input", default=_DEFAULT_INPUT,
                         help="Segmented (matrix/pore/POM) .nii.gz volume the run was computed from.")
    parser.add_argument("--raw-volume", default=_DEFAULT_RAW_VOLUME,
                         help="Raw grayscale CT crop cache (.npy), same Z/Y/X window as --input. "
                              "Verified against --raw-source/--crop-bounds and rebuilt if stale/missing.")
    parser.add_argument("--raw-source", default=_DEFAULT_RAW_SOURCE,
                         help="Full-resolution raw grayscale .nii.gz that --raw-volume's crop must match "
                              "(network share; used to verify/rebuild the .npy cache).")
    parser.add_argument("--crop-bounds", type=int, nargs=6, default=list(_DEFAULT_CROP_BOUNDS),
                         metavar=("Z0", "Z1", "Y0", "Y1", "X0", "X1"),
                         help="Z/Y/X window --raw-volume was cropped from --raw-source at. Must match --input's "
                              "own crop (e.g. sub_z200_300_crop200.nii.gz encodes Z200:300/Y200:400/X200:400).")
    parser.add_argument("--pore-label", type=int, default=5, help="Integer label = pore phase (per config.json).")
    parser.add_argument("--pom-label", type=int, default=2, help="Integer label = POM phase (per config.json, unused here).")
    parser.add_argument("--axis", type=int, default=0, help="Percolation axis (0=Z), matches the pipeline's default.")
    args = parser.parse_args()
    main(args.run_dir, args.input, args.raw_volume, args.pore_label, args.pom_label, args.axis,
         raw_source_path=args.raw_source, crop_bounds=tuple(args.crop_bounds))
