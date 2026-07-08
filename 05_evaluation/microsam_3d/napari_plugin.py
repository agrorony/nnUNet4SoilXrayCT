"""napari dock widget for interactive micro-SAM proofreading of 3-D label maps."""
from __future__ import annotations


def load_rois_from_file(path) -> list[dict]:
    """Load ROI bboxes from a JSON or CSV file.

    JSON: array of objects with keys z0, z1, y0, y1, x0, x1.
    CSV:  header row z0,z1,y0,y1,x0,x1.

    Returns a list of dicts with those six int keys.
    """
    import json, csv
    from pathlib import Path
    p = Path(path)
    if p.suffix == ".json":
        with open(p) as f:
            return json.load(f)
    if p.suffix == ".csv":
        with open(p, newline="") as f:
            return [{k: int(v) for k, v in row.items()} for row in csv.DictReader(f)]
    raise ValueError(f"Unsupported ROI file format: {p.suffix}")

import json
import csv
from pathlib import Path

import numpy as np
import napari
from magicgui.widgets import (
    Container, PushButton, ComboBox, RadioButtons, Label, SpinBox,
)

from embedder import VolumeEmbedder
from error_map import compute_error_map, get_error_regions
from predictor import MaskPredictor3D
from correction_store import CorrectionStore


def create_widget(viewer: napari.Viewer) -> tuple:
    """Build and return two proofreading dock widgets as (panel1, panel2).

    Register both with napari:
        panel1, panel2 = create_widget(viewer)
        viewer.window.add_dock_widget(panel1, area="right", name="MicroSAM — Error Search")
        viewer.window.add_dock_widget(panel2, area="right", name="MicroSAM — Corrections")
    """

    # ── Shared mutable state ───────────────────────────────────────────────────
    ctx: dict = {
        "embedder": None,
        "predictor": None,
        "store": None,
        "error_regions": [],
        "region_idx": 0,
        "roi_queue": [],
        "roi_queue_idx": 0,
        "current_bbox": None,
        "volume": None,
        "pred": None,
        "pred_snap": None,   # unedited snapshot for slice-diff baseline
        "proposal_patch": None,
        "roi_z0": 0,
        "roi_z1": None,      # None = full volume until Change ROI is clicked
    }

    # ── Widget definitions ─────────────────────────────────────────────────────
    def _label_names(klass):
        return [l.name for l in viewer.layers if isinstance(l, klass)] or [""]

    # Panel 1 — Error Search
    img_combo   = ComboBox(label="Image layer",      choices=lambda w: _label_names(napari.layers.Image))
    pred_combo  = ComboBox(label="Prediction layer", choices=lambda w: _label_names(napari.layers.Labels))
    gt_combo    = ComboBox(label="GT layer (opt.)",  choices=lambda w: ["None"] + _label_names(napari.layers.Labels))
    model_combo = ComboBox(label="SAM model",        choices=["vit_b", "vit_l", "vit_h"])

    error_class_spin = SpinBox(label="Error-search class", value=1, min=1, max=255)
    start_slice_spin = SpinBox(label="Start slice",        value=0, min=0, max=9999)
    change_roi_btn   = PushButton(text="Change ROI")
    compute_btn      = PushButton(text="Compute errors")
    mode_radio       = RadioButtons(label="Region input", choices=["Auto", "Draw", "Load"])
    next_btn         = PushButton(text="Next error")
    load_roi_btn     = PushButton(text="Load ROIs (JSON/CSV)")
    status_lbl_a     = Label(value="Set ROI → Compute errors, or go straight to Propagate.")

    # Panel 2 — Corrections
    correction_class_spin = SpinBox(label="Correction class",   value=1, min=1, max=255)
    propose_btn           = PushButton(text="Propose fix")
    accept_btn            = PushButton(text="Accept (Y)")
    reject_btn            = PushButton(text="Reject (N)")
    propagate_n_spin      = SpinBox(label="Propagate N slices", value=2, min=1, max=20)
    propagate_btn         = PushButton(text="Propagate to neighbors")
    slice_diff_btn        = PushButton(text="Slice diff → SAM")
    export_btn            = PushButton(text="Export")
    status_lbl_b          = Label(value="Set ROI → Compute errors, or go straight to Propagate.")

    # ── Internal helpers ───────────────────────────────────────────────────────
    def _status(msg: str) -> None:
        status_lbl_a.value = msg
        status_lbl_b.value = msg

    def _layer(name: str):
        return viewer.layers[name] if name and name in viewer.layers else None

    def _roi_z_range() -> tuple:
        """Return (z0, z1_inclusive) of the active ROI, clamped to volume bounds."""
        z0 = ctx["roi_z0"]
        z1 = ctx["roi_z1"]
        if z1 is None:
            Z = ctx["volume"].shape[0] if ctx["volume"] is not None else 9999
            return z0, Z - 1
        return z0, z1

    def _make_adjacent_mask(pred: np.ndarray, z: int) -> np.ndarray:
        out = np.zeros_like(pred)
        Z = pred.shape[0]
        if z > 0:
            out[z - 1] = pred[z - 1]
        if z < Z - 1:
            out[z + 1] = pred[z + 1]
        return out

    def _jump_to_bbox(bbox: tuple) -> None:
        z0, z1, y0, y1, x0, x1 = bbox
        viewer.dims.set_current_step(0, (z0 + z1) // 2)
        viewer.camera.center = (0, (y0 + y1) / 2, (x0 + x1) / 2)

    def _get_active_bbox() -> tuple | None:
        mode = mode_radio.value
        if mode == "Auto":
            regions = ctx["error_regions"]
            i = ctx["region_idx"]
            return regions[i]["bbox"] if i < len(regions) else None
        elif mode == "Draw":
            roi_lyr = _layer("roi")
            if roi_lyr is None or len(roi_lyr.data) == 0:
                return None
            rect = roi_lyr.data[-1]  # (4, ndim) napari rectangle vertices
            ndim = rect.shape[1]
            if ndim == 3:
                yx = rect[:, 1:]
            else:
                yx = rect
            y0, x0 = yx.min(axis=0).astype(int)
            y1, x1 = yx.max(axis=0).astype(int)
            z = int(viewer.dims.current_step[0])
            return (z, z + 1, y0, y1, x0, x1)
        elif mode == "Load":
            q = ctx["roi_queue"]
            i = ctx["roi_queue_idx"]
            if i < len(q):
                r = q[i]
                return (r["z0"], r["z1"], r["y0"], r["y1"], r["x0"], r["x1"])
        return None

    def _advance_region() -> None:
        mode = mode_radio.value
        if mode == "Auto":
            ctx["region_idx"] += 1
        elif mode == "Load":
            ctx["roi_queue_idx"] += 1

    def _accept_current() -> None:
        if ctx["current_bbox"] is None:
            _status("No pending proposal.")
            return
        z0, z1, y0, y1, x0, x1 = ctx["current_bbox"]
        class_val = np.uint8(correction_class_spin.value)
        if "sam_proposal" in viewer.layers:
            raw = np.array(viewer.layers["sam_proposal"].data[z0:z1, y0:y1, x0:x1])
        elif ctx["proposal_patch"] is not None:
            raw = ctx["proposal_patch"]
        else:
            _status("No pending proposal.")
            return
        patch = (raw > 0).astype(np.uint8) * class_val
        ctx["store"].add(ctx["current_bbox"], patch)
        if "corrections" in viewer.layers:
            lyr = viewer.layers["corrections"]
            lyr.data[z0:z1, y0:y1, x0:x1] = patch
            lyr.refresh()
        ctx["proposal_patch"] = None
        ctx["current_bbox"] = None
        _advance_region()
        n = len(ctx["store"].corrections)
        _status(f"Accepted (class={class_val}). {n} correction(s) stored.")
        _try_jump_next()

    def _reject_current() -> None:
        ctx["proposal_patch"] = None
        ctx["current_bbox"] = None
        _advance_region()
        _status("Rejected. Moving to next region.")
        _try_jump_next()

    def _try_jump_next() -> None:
        bbox = _get_active_bbox()
        if bbox is not None:
            _jump_to_bbox(bbox)

    # ── Lazy initialisation ────────────────────────────────────────────────────
    def _ensure_initialized() -> bool:
        """Load volume+pred, set up predictor, create working layers.

        Safe to call multiple times — exits immediately if already done.
        Returns False (with a status message) if the required combos are unset.
        """
        if ctx["predictor"] is not None:
            return True

        img_name  = img_combo.value
        pred_name = pred_combo.value
        if not img_name or img_name == "" or not pred_name or pred_name == "":
            _status("Select Image and Prediction layers first.")
            return False

        _status("Loading volume and prediction into RAM …")
        volume = np.array(viewer.layers[img_name].data, dtype=np.float32)
        pred   = np.array(viewer.layers[pred_name].data)

        vmin, vmax = volume.min(), volume.max()
        if vmax > vmin:
            volume = (volume - vmin) / (vmax - vmin)

        ctx["volume"]    = volume
        ctx["pred"]      = pred
        ctx["pred_snap"] = pred.copy()
        ctx["store"]     = CorrectionStore(pred.shape)

        # Auto-commit ROI to centre if the user hasn't set one yet
        if ctx["roi_z1"] is None:
            Z     = pred.shape[0]
            start = max(0, min(Z // 2 - 9, Z - 20))
            ctx["roi_z0"]          = start
            ctx["roi_z1"]          = start + 19
            start_slice_spin.max   = max(0, Z - 20)
            start_slice_spin.value = start
            viewer.dims.set_current_step(0, start)

        # Auto-select GT layer if present and not yet chosen
        if (not gt_combo.value or gt_combo.value == "None") and "gt" in viewer.layers:
            gt_combo.value = "gt"

        ctx["embedder"]  = VolumeEmbedder(volume, model_type=model_combo.value)
        ctx["predictor"] = MaskPredictor3D(ctx["embedder"])

        # Adjacent-mask layer
        z = int(viewer.dims.current_step[0])
        adj = _make_adjacent_mask(pred, z)
        if "adjacent_mask" in viewer.layers:
            viewer.layers["adjacent_mask"].data = adj
        else:
            viewer.add_labels(adj, name="adjacent_mask", opacity=0.3)

        # ROI shapes layer (Draw mode)
        if "roi" not in viewer.layers:
            viewer.add_shapes(name="roi", edge_color="yellow",
                              face_color="transparent", opacity=0.8)

        # Corrections accumulation layer
        corr_blank = np.zeros(pred.shape, dtype=np.uint8)
        if "corrections" in viewer.layers:
            viewer.layers["corrections"].data = corr_blank
        else:
            viewer.add_labels(corr_blank, name="corrections", opacity=0.7)

        roi_z0, roi_z1 = _roi_z_range()
        _status(f"Initialized. ROI: slices {roi_z0}–{roi_z1}. "
                f"Click 'Compute errors' to find error regions, or use Propagate directly.")
        return True

    # ── Error-map recomputation (ROI-only — avoids OOM on large volumes) ───────
    def _recompute_errors() -> None:
        """Compute error map restricted to the active ROI slice range.

        Running ndimage.label on the full volume (e.g. 652×650×650) allocates
        a 1 GB int32 array.  Computing only on the 20-slice ROI window reduces
        that to ~33 MB.
        """
        if ctx["pred"] is None:
            return
        gt_name = gt_combo.value
        if not gt_name or gt_name == "None" or gt_name not in viewer.layers:
            _status("Select a GT layer to compute errors.")
            return

        roi_z0, roi_z1 = _roi_z_range()
        pred_roi = ctx["pred"][roi_z0:roi_z1 + 1]
        gt_roi   = np.array(viewer.layers[gt_name].data)[roi_z0:roi_z1 + 1]

        target  = error_class_spin.value
        em_roi  = compute_error_map(pred_roi, gt_roi, target_class=target)
        regions = get_error_regions(em_roi, min_size=100)

        # Shift local bbox z-coords to global volume space
        for r in regions:
            b = r["bbox"]
            r["bbox"] = (b[0] + roi_z0, b[1] + roi_z0, b[2], b[3], b[4], b[5])

        # Build full-volume error map (zeros outside ROI) for display
        em_full = np.zeros(ctx["pred"].shape, dtype=np.float32)
        em_full[roi_z0:roi_z1 + 1] = em_roi

        ctx["error_map"]     = em_full
        ctx["error_regions"] = regions
        ctx["region_idx"]    = 0

        if "error_map" in viewer.layers:
            viewer.layers["error_map"].data = em_full
        else:
            viewer.add_image(em_full, name="error_map", colormap="inferno", opacity=0.5)

        n = len(regions)
        _status(f"Found {n} error regions (class {target}, slices {roi_z0}–{roi_z1}). Ready.")
        if regions:
            _jump_to_bbox(regions[0]["bbox"])

    @gt_combo.changed.connect
    def _on_gt_changed(value) -> None:
        _recompute_errors()

    @error_class_spin.changed.connect
    def _on_error_class_changed(value) -> None:
        _recompute_errors()

    # ── Button handlers ────────────────────────────────────────────────────────
    @change_roi_btn.changed.connect
    def _on_change_roi() -> None:
        if ctx["volume"] is None:
            _status("Click 'Compute errors' first to load the volume.")
            return
        Z     = ctx["volume"].shape[0]
        start = int(start_slice_spin.value)
        start = max(0, min(start, Z - 20))
        ctx["roi_z0"] = start
        ctx["roi_z1"] = start + 19
        start_slice_spin.value = start  # snap back if clamped
        viewer.dims.set_current_step(0, start)
        _status(f"ROI set: slices {start}–{start + 19}.")
        _recompute_errors()

    @compute_btn.changed.connect
    def _on_compute() -> None:
        if not _ensure_initialized():
            return
        _recompute_errors()

    @viewer.dims.events.current_step.connect
    def _on_z_change(event) -> None:
        if ctx["pred"] is None:
            return
        z = int(viewer.dims.current_step[0])
        adj = _make_adjacent_mask(ctx["pred"], z)
        if "adjacent_mask" in viewer.layers:
            viewer.layers["adjacent_mask"].data = adj

    @next_btn.changed.connect
    def _on_next() -> None:
        regions = ctx["error_regions"]
        i = ctx["region_idx"]
        if i >= len(regions):
            _status("All error regions reviewed.")
            return
        ctx["region_idx"] = i + 1
        i2 = ctx["region_idx"]
        if i2 < len(regions):
            _jump_to_bbox(regions[i2]["bbox"])
            _status(f"Region {i2 + 1} / {len(regions)}")
        else:
            _status("All error regions reviewed.")

    @load_roi_btn.changed.connect
    def _on_load_rois() -> None:
        try:
            from qtpy.QtWidgets import QFileDialog
            path, _ = QFileDialog.getOpenFileName(
                None, "Load ROIs", "", "JSON/CSV files (*.json *.csv)"
            )
        except Exception:
            _status("Qt dialog unavailable — set roi_queue manually.")
            return
        if not path:
            return
        p = Path(path)
        rois = []
        if p.suffix == ".json":
            with open(p) as f:
                rois = json.load(f)
        elif p.suffix == ".csv":
            with open(p, newline="") as f:
                for row in csv.DictReader(f):
                    rois.append({k: int(v) for k, v in row.items()})
        ctx["roi_queue"]     = rois
        ctx["roi_queue_idx"] = 0
        _status(f"Loaded {len(rois)} ROIs.")
        if rois:
            r = rois[0]
            _jump_to_bbox((r["z0"], r["z1"], r["y0"], r["y1"], r["x0"], r["x1"]))

    @propose_btn.changed.connect
    def _on_propose() -> None:
        if not _ensure_initialized():
            return
        bbox = _get_active_bbox()
        if bbox is None:
            _status("No active region — select via Auto / Draw / Load.")
            return
        ctx["current_bbox"] = bbox
        z0, z1, y0, y1, x0, x1 = bbox
        em = ctx.get("error_map")
        if em is not None:
            err_yx = np.argwhere(em[z0:z1, y0:y1, x0:x1] > 0)
            if len(err_yx) > 0:
                cy = int(err_yx[:, 1].mean()) + y0
                cx = int(err_yx[:, 2].mean()) + x0
            else:
                cy, cx = (y0 + y1) // 2, (x0 + x1) // 2
        else:
            cy, cx = (y0 + y1) // 2, (x0 + x1) // 2
        point_coords = np.array([[cy, cx]])
        point_labels = np.array([1])
        _status(f"Running SAM on bbox {bbox} …")
        patch = ctx["predictor"].predict_region(bbox, point_coords, point_labels)
        ctx["proposal_patch"] = patch
        full = np.zeros_like(ctx["pred"])
        full[z0:z1, y0:y1, x0:x1] = patch
        if "sam_proposal" in viewer.layers:
            viewer.layers["sam_proposal"].data = full
        else:
            viewer.add_labels(full, name="sam_proposal", opacity=0.6)
        _status("Proposal ready — Accept (Y) or Reject (N).")

    @accept_btn.changed.connect
    def _on_accept_btn() -> None:
        _accept_current()

    @reject_btn.changed.connect
    def _on_reject_btn() -> None:
        _reject_current()

    viewer.bind_key("y", lambda v: _accept_current(), overwrite=True)
    viewer.bind_key("n", lambda v: _reject_current(), overwrite=True)

    @export_btn.changed.connect
    def _on_export() -> None:
        if ctx["store"] is None or not ctx["store"].corrections:
            _status("No corrections to export.")
            return
        try:
            from qtpy.QtWidgets import QFileDialog
            path = QFileDialog.getExistingDirectory(None, "Choose export directory")
        except Exception:
            path = ""
        if not path:
            _status("Export cancelled.")
            return
        ctx["store"].export(path, ctx["volume"], ctx["pred"])
        _status(f"Exported {len(ctx['store'].corrections)} pairs → {path}")

    @propagate_btn.changed.connect
    def _on_propagate() -> None:
        """Propagate GT annotation from current slice to N neighboring slices within the ROI."""
        if not _ensure_initialized():
            return
        gt_name = gt_combo.value
        if not gt_name or gt_name == "None" or gt_name not in viewer.layers:
            _status("Select a GT layer before propagating.")
            return
        if "corrections" not in viewer.layers:
            _status("Corrections layer missing — click 'Compute errors' once to initialise.")
            return

        from scipy import ndimage

        z         = int(viewer.dims.current_step[0])
        N         = propagate_n_spin.value
        class_val = np.uint8(correction_class_spin.value)
        roi_z0, roi_z1 = _roi_z_range()

        gt_vol   = np.array(viewer.layers[gt_name].data)
        gt_slice = gt_vol[z]

        labeled, n_obj = ndimage.label(gt_slice > 0)
        if n_obj == 0:
            _status(f"No labeled objects on slice {z}.")
            return

        objects = []
        for i in range(1, n_obj + 1):
            coords = np.argwhere(labeled == i)
            cy = int(coords[:, 0].mean())
            cx = int(coords[:, 1].mean())
            y0 = int(coords[:, 0].min())
            y1 = int(coords[:, 0].max()) + 1
            x0 = int(coords[:, 1].min())
            x1 = int(coords[:, 1].max()) + 1
            objects.append((cy, cx, y0, y1, x0, x1))

        corr_lyr    = viewer.layers["corrections"]
        z_neighbors = [
            zp for zp in range(max(roi_z0, z - N), min(roi_z1 + 1, z + N + 1))
            if zp != z
        ]
        total = 0
        for zp in z_neighbors:
            _status(f"Propagating to slice {zp} …")
            for cy, cx, y0, y1, x0, x1 in objects:
                bbox  = (zp, zp + 1, y0, y1, x0, x1)
                patch = ctx["predictor"].predict_region(
                    bbox, np.array([[cy, cx]]), np.array([1])
                )
                seg = (patch > 0).astype(np.uint8) * class_val
                corr_lyr.data[zp:zp + 1, y0:y1, x0:x1] = np.maximum(
                    corr_lyr.data[zp:zp + 1, y0:y1, x0:x1], seg
                )
            total += 1
        corr_lyr.refresh()
        _status(
            f"Propagated {n_obj} object(s) to {total} slice(s) "
            f"within ROI {roi_z0}–{roi_z1} (class {class_val})."
        )

    @slice_diff_btn.changed.connect
    def _on_slice_diff() -> None:
        """Propagate the diff on the current slice to all other slices in the ROI via SAM."""
        if not _ensure_initialized():
            return
        if ctx["pred_snap"] is None:
            _status("No prediction snapshot — click 'Compute errors' first.")
            return
        if "corrections" not in viewer.layers:
            _status("Corrections layer missing — click 'Compute errors' once to initialise.")
            return

        pred_name = pred_combo.value
        if not pred_name or pred_name not in viewer.layers:
            _status("No prediction layer selected.")
            return

        from scipy import ndimage

        z         = int(viewer.dims.current_step[0])
        class_val = np.uint8(correction_class_spin.value)
        roi_z0, roi_z1 = _roi_z_range()

        live = np.array(viewer.layers[pred_name].data[z])
        orig = ctx["pred_snap"][z]
        diff = (live != orig)

        if not diff.any():
            _status(f"No changes detected on slice {z} — edit the prediction layer first.")
            return

        labeled, n_obj = ndimage.label(diff)
        if n_obj == 0:
            _status(f"No diff regions on slice {z}.")
            return

        objects = []
        for i in range(1, n_obj + 1):
            coords = np.argwhere(labeled == i)
            cy = int(coords[:, 0].mean())
            cx = int(coords[:, 1].mean())
            y0 = int(coords[:, 0].min())
            y1 = int(coords[:, 0].max()) + 1
            x0 = int(coords[:, 1].min())
            x1 = int(coords[:, 1].max()) + 1
            objects.append((cy, cx, y0, y1, x0, x1))

        corr_lyr = viewer.layers["corrections"]
        z_others = [zp for zp in range(roi_z0, roi_z1 + 1) if zp != z]
        total    = 0
        for zp in z_others:
            _status(f"Slice diff: applying to slice {zp} …")
            for cy, cx, y0, y1, x0, x1 in objects:
                bbox  = (zp, zp + 1, y0, y1, x0, x1)
                patch = ctx["predictor"].predict_region(
                    bbox, np.array([[cy, cx]]), np.array([1])
                )
                seg = (patch > 0).astype(np.uint8) * class_val
                corr_lyr.data[zp:zp + 1, y0:y1, x0:x1] = np.maximum(
                    corr_lyr.data[zp:zp + 1, y0:y1, x0:x1], seg
                )
            total += 1
        corr_lyr.refresh()
        _status(
            f"Slice diff done: {n_obj} region(s) from slice {z} "
            f"propagated to {total} slice(s) within ROI {roi_z0}–{roi_z1} (class {class_val})."
        )

    # ── Assemble panels ────────────────────────────────────────────────────────
    panel1 = Container(widgets=[
        img_combo,
        pred_combo,
        gt_combo,
        model_combo,
        error_class_spin,
        start_slice_spin,
        change_roi_btn,
        compute_btn,
        mode_radio,
        next_btn,
        load_roi_btn,
        status_lbl_a,
    ])

    panel2 = Container(widgets=[
        correction_class_spin,
        propose_btn,
        accept_btn,
        reject_btn,
        propagate_n_spin,
        propagate_btn,
        slice_diff_btn,
        export_btn,
        status_lbl_b,
    ])

    return panel1, panel2


def create_adjust_widget(viewer: napari.Viewer) -> Container:
    """Standalone dock widget for per-layer flip and class-shift operations."""

    adj_combo    = ComboBox(label="Layer", choices=lambda w: [l.name for l in viewer.layers] or [""])
    flip_z_btn   = PushButton(text="Flip Z")
    flip_y_btn   = PushButton(text="Flip Y")
    flip_x_btn   = PushButton(text="Flip X")
    shift_p1_btn = PushButton(text="+1")
    shift_m1_btn = PushButton(text="-1")

    def _get_layer():
        name = adj_combo.value
        return viewer.layers[name] if name and name in viewer.layers else None

    @flip_z_btn.changed.connect
    def _on_flip_z():
        lyr = _get_layer()
        if lyr is None: return
        lyr.data = np.flip(lyr.data, axis=0)
        lyr.refresh()

    @flip_y_btn.changed.connect
    def _on_flip_y():
        lyr = _get_layer()
        if lyr is None: return
        lyr.data = np.flip(lyr.data, axis=1)
        lyr.refresh()

    @flip_x_btn.changed.connect
    def _on_flip_x():
        lyr = _get_layer()
        if lyr is None: return
        lyr.data = np.flip(lyr.data, axis=2)
        lyr.refresh()

    @shift_p1_btn.changed.connect
    def _on_shift_p1():
        lyr = _get_layer()
        if lyr is None: return
        lyr.data = lyr.data + 1
        lyr.refresh()

    @shift_m1_btn.changed.connect
    def _on_shift_m1():
        lyr = _get_layer()
        if lyr is None: return
        lyr.data = lyr.data - 1
        lyr.refresh()

    return Container(widgets=[
        adj_combo,
        flip_z_btn,
        flip_y_btn,
        flip_x_btn,
        shift_p1_btn,
        shift_m1_btn,
    ])
