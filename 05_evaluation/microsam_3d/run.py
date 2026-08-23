"""CLI: python run.py volume.tif pred.tif [gt.tif]"""
import sys
import os
import argparse
import time
import logging
from pathlib import Path

import numpy as np
import napari

_logger = logging.getLogger(__name__)


# ── Debug logging ─────────────────────────────────────────────────────────────

def _setup_debug_logging() -> None:
    log_path = Path(__file__).parent / "debug.log"
    fmt = "%(message)s"
    fh = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(fmt))
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(logging.Formatter(fmt))
    _logger.addHandler(fh)
    _logger.addHandler(ch)
    _logger.setLevel(logging.DEBUG)


def _log(msg: str, t0: float, debug: bool) -> None:
    if debug:
        elapsed = time.time() - t0
        try:
            import psutil
            ram_gb = psutil.Process(os.getpid()).memory_info().rss / 1e9
            line = f"[{elapsed:05.1f}s] {msg} | RAM: {ram_gb:.2f} GB"
        except ImportError:
            line = f"[{elapsed:05.1f}s] {msg}"
        _logger.info(line)
    else:
        print(msg)


# ── Dask lazy loaders ─────────────────────────────────────────────────────────

def _nii_to_zyx(arr: np.ndarray, x_flip: bool = False) -> np.ndarray:
    """Convert NIfTI array (X, Y, Z) to napari-friendly (Z, Y, X).

    nibabel returns voxel data as (X, Y, Z).  arr.T = np.transpose(arr, (2,1,0))
    maps that to (Z, Y, X) correctly.  np.flip on axis 1 corrects the Y-axis
    scan direction; x_flip (axis 2) corrects X when affine[0,0] < 0.
    """
    arr = np.transpose(arr, (2, 1, 0))   # (X, Y, Z) → (Z, Y, X)
    arr = np.flip(arr, axis=1)            # correct Y-axis scan direction
    if x_flip:
        arr = np.flip(arr, axis=2)        # correct X-axis scan direction
    return arr


def _load_volume_dask(path: str):
    """Lazy-load volume → dask array (Z, Y, X) float32, un-normalized.

    napari detects dask arrays and reads slices on demand — no pyramid
    precomputation, RAM stays near 0 until a slice is actually rendered.
    """
    import dask
    import dask.array as da

    path = str(path)
    if path.endswith(".nii.gz") or path.endswith(".nii"):
        import nibabel as nib
        img = nib.load(path)
        # NIfTI shape is (X, Y, Z); after _nii_to_zyx → (Z, Y, X)
        nx, ny, nz = img.shape
        shape_zyx = (nz, ny, nx)
        x_flip = float(img.affine[0, 0]) < 0

        def _load(_p=path, _x_flip=x_flip):
            arr = np.asarray(nib.load(_p).dataobj)
            if arr.ndim == 3:
                arr = _nii_to_zyx(arr, x_flip=_x_flip)
            return arr.astype(np.float32)

        return da.from_delayed(
            dask.delayed(_load)(), shape=shape_zyx, dtype=np.float32
        )
    else:
        import tifffile
        with tifffile.TiffFile(path) as tf:
            nz = len(tf.pages)
            shape_yx = tf.pages[0].shape

        def _read_z(z, _p=path):
            with tifffile.TiffFile(_p) as tf:
                return tf.pages[z].asarray().astype(np.float32)

        slices = [
            da.from_delayed(dask.delayed(_read_z)(z), shape=shape_yx, dtype=np.float32)
            for z in range(nz)
        ]
        return da.stack(slices, axis=0)


def _load_labels_dask(path: str):
    """Lazy-load integer label map → dask array (Z, Y, X)."""
    import dask
    import dask.array as da

    path = str(path)
    if path.endswith(".nii.gz") or path.endswith(".nii"):
        import nibabel as nib
        img = nib.load(path)
        # NIfTI shape is (X, Y, Z); after _nii_to_zyx → (Z, Y, X)
        nx, ny, nz = img.shape
        shape_zyx = (nz, ny, nx)
        x_flip = float(img.affine[0, 0]) < 0

        def _load(_p=path, _x_flip=x_flip):
            import nibabel as nib
            arr = np.asarray(nib.load(_p).dataobj)
            if arr.ndim == 3:
                arr = _nii_to_zyx(arr, x_flip=_x_flip)
            return arr.astype(np.uint8)

        return da.from_delayed(
            dask.delayed(_load)(), shape=shape_zyx, dtype=np.uint8
        )
    else:
        import tifffile
        with tifffile.TiffFile(path) as tf:
            nz = len(tf.pages)
            shape_yx = tf.pages[0].shape
            page_dtype = tf.pages[0].dtype

        def _read_z(z, _p=path):
            with tifffile.TiffFile(_p) as tf:
                return tf.pages[z].asarray()

        slices = [
            da.from_delayed(dask.delayed(_read_z)(z), shape=shape_yx, dtype=page_dtype)
            for z in range(nz)
        ]
        return da.stack(slices, axis=0)


# ── Entry point ───────────────────────────────────────────────────────────────

def main(
    volume_path: str,
    pred_path: str = None,
    gt_path: str = None,
    extra_label_paths: dict = None,
    zrange: tuple = None,
    debug: bool = False,
    title: str = None,
) -> None:
    if debug:
        _setup_debug_logging()

    t0 = time.time()

    _log(f"Loading volume: {volume_path}", t0, debug)
    volume = _load_volume_dask(volume_path)
    if zrange is not None:
        volume = volume[zrange[0]:zrange[1]]
    _log(f"  shape={volume.shape}  dtype={volume.dtype}", t0, debug)

    pred = None
    if pred_path:
        _log(f"Loading prediction: {pred_path}", t0, debug)
        pred = _load_labels_dask(pred_path)
        if zrange is not None:
            pred = pred[zrange[0]:zrange[1]]
        _log(f"  shape={pred.shape}", t0, debug)

    gt = None
    if gt_path:
        _log(f"Loading GT: {gt_path}", t0, debug)
        gt = _load_labels_dask(gt_path)
        if zrange is not None:
            gt = gt[zrange[0]:zrange[1]]
        _log(f"  shape={gt.shape}", t0, debug)

    _log("Creating viewer ...", t0, debug)
    viewer = napari.Viewer(title=title or "micro-SAM 3D Proofreader")

    _log("Adding volume layer ...", t0, debug)
    viewer.add_image(volume, name="volume", colormap="gray")
    _log("Volume layer added.", t0, debug)

    if pred is not None:
        _log("Adding prediction layer (computing to numpy for paintability) ...", t0, debug)
        viewer.add_labels(pred.compute(), name="prediction")
        _log("Prediction layer added.", t0, debug)

    if gt is not None:
        _log("Adding GT layer (computing to numpy for paintability) ...", t0, debug)
        viewer.add_labels(gt.compute(), name="gt")
        _log("GT layer added.", t0, debug)

    if extra_label_paths:
        for layer_name, layer_path in extra_label_paths.items():
            _log(f"Loading extra layer '{layer_name}' (computing to numpy) ...", t0, debug)
            lyr = _load_labels_dask(layer_path)
            if zrange is not None:
                lyr = lyr[zrange[0]:zrange[1]]
            viewer.add_labels(lyr.compute(), name=layer_name)
            _log(f"  '{layer_name}' layer added.", t0, debug)

    from napari_plugin import create_widget, create_adjust_widget
    _log("Building dock widgets ...", t0, debug)
    panel1, panel2 = create_widget(viewer)
    viewer.window.add_dock_widget(panel1, area="right", name="MicroSAM — Error Search")
    viewer.window.add_dock_widget(panel2, area="right", name="MicroSAM — Corrections")
    adjust_widget = create_adjust_widget(viewer)
    viewer.window.add_dock_widget(adjust_widget, area="right", name="Adjust layer")
    _log("Widgets ready. Entering napari event loop ...", t0, debug)

    napari.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="run.py",
        description="micro-SAM 3D Proofreader — interactive napari tool for correcting "
                    "dense 3-D CNN segmentation outputs using SAM.",
    )
    parser.add_argument("volume", help="Raw volume TIFF file path")
    parser.add_argument("pred",   help="Prediction TIFF or NIfTI file path (nnUNet output)")
    parser.add_argument("gt",     nargs="?", default=None,
                        help="Ground-truth annotation TIFF (optional, enables GT diff error map)")
    parser.add_argument("--zrange", nargs=2, type=int, metavar=("Z0", "Z1"),
                        help="Crop to Z-slice range [Z0, Z1) — useful for fast testing")
    parser.add_argument("--extra-labels", nargs=2, action="append", metavar=("NAME", "PATH"),
                        help="Additional read-only labels layer: NAME PATH. Repeatable. "
                             "Shown at low opacity with a distinct color seed.")
    parser.add_argument("--debug", action="store_true",
                        help="Log timing and RAM to console + microsam_3d/debug.log")
    args = parser.parse_args()
    main(
        args.volume, args.pred, args.gt,
        extra_label_paths=dict(args.extra_labels) if args.extra_labels else None,
        zrange=tuple(args.zrange) if args.zrange else None,
        debug=args.debug,
    )
