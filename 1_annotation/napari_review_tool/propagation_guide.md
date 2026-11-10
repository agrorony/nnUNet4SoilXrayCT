# MicroSAM Propagation — User Guide

The plugin offers two propagation tools that let you correct one slice and have SAM automatically apply a matching mask to the remaining slices in the active ROI. Both tools write their results into the **corrections** layer using whatever **Correction class** is set in the Corrections panel.

---

## Prerequisites

Before using either propagation tool, complete these steps in order:

1. **Load layers** — open your image and prediction volumes in napari and select them in the *Error Search* panel (Image layer / Prediction layer).
2. **Set ROI** *(optional but recommended)* — enter a Start slice value and click **Change ROI** to restrict all operations to 20 consecutive slices. Without this, propagation targets every slice in the volume, which is slow.
3. **Click "Compute errors"** — this initialises the SAM embedder, the predictor, and the corrections layer. Neither propagation button works before this step.
4. **Set Correction class** *(Corrections panel)* — choose the integer label that will be written into the corrections layer. Default is 1.

---

## Tool 1 — Propagate to neighbors

**What it does:** reads the GT annotation on the *currently displayed* slice, finds each labeled object, and runs SAM on z−N … z+N (excluding the source slice) to produce a matching mask on each neighbor. Results are merged (max) into the corrections layer.

**When to use it:** you have a hand-annotated or clean GT slice and want to extend that annotation outward by a small number of slices — typically 2–5.

### Step-by-step

1. Navigate napari to the slice you want to propagate *from* (use the Z slider or keyboard arrow keys).
2. In the *Error Search* panel, make sure a **GT layer** is selected that has valid labels on this slice.
3. In the *Corrections* panel, set **Correction class** to the label value you want written.
4. Set **Propagate N slices** to the number of slices above and below the source to target (e.g. `3` targets slices z−3, z−2, z−1, z+1, z+2, z+3).
5. Click **Propagate to neighbors**.
6. Watch the status bar — it prints "Propagating to slice N …" for each slice. When done it reports the number of objects and slices processed.
7. Toggle the **corrections** layer on/off in the layer list to review the result.

### ROI interaction

Propagation is clamped to the active ROI. If your source slice is z=5 and N=4 but the ROI starts at z=3, the propagation range becomes z=3,4,6,7,8,9 — it will not go below z=3 even if z−4=1 would otherwise be in range.

### Parameters

| Parameter | Where | Effect |
|---|---|---|
| GT layer | Error Search panel | Source of the mask on the current slice |
| Correction class | Corrections panel | Label value written to corrections |
| Propagate N slices | Corrections panel | Half-width of the neighborhood (1–20) |
| Active ROI | set via Change ROI | Hard boundary — propagation never exits this range |

---

## Tool 2 — Slice diff → SAM

**What it does:** compares the *current state* of the prediction layer on the displayed slice against the unedited snapshot taken when you first selected that layer. Each connected component of changed voxels becomes a SAM prompt (centroid + bounding box), and SAM runs that prompt on every other slice in the active ROI. Results are merged into the corrections layer.

**When to use it:** you manually paint or erase a correction on one slice and want SAM to replicate it across all slices in the ROI — especially useful when the edit is topologically consistent across slices (a grain boundary, a pore, an aggregate).

### Step-by-step

1. In the *Error Search* panel, select the **Prediction layer**. The plugin snapshots it automatically at this moment — do not change the selection later or the baseline will be lost.
2. Set the active ROI via **Start slice + Change ROI** so propagation doesn't run over the entire volume.
3. Navigate to any slice where the prediction is clearly wrong.
4. In napari's layer list, select the prediction layer and use the **paint** or **erase** brush to draw the correct mask for that one slice.
5. In the *Corrections* panel, confirm **Correction class** is correct.
6. Click **Slice diff → SAM**.
7. The status bar prints "Slice diff: applying to slice N …" for each target slice. When done it reports the number of diff regions and slices.
8. Review the corrections layer. If the result is wrong on specific slices, you can repaint those slices and run Slice diff again — results are merged with max, so previously correct regions are preserved.

### How the baseline snapshot works

The snapshot is taken the moment you select the prediction layer in the combo box (or when "Compute errors" runs as a fallback). It represents the prediction *before any manual edits*. The diff is always `current_prediction_slice XOR snapshot_slice` — only voxels you changed since that moment are included. If you want to reset the baseline, re-select the prediction layer in the combo box.

### Parameters

| Parameter | Where | Effect |
|---|---|---|
| Prediction layer | Error Search panel | Source of both live state and baseline snapshot |
| Correction class | Corrections panel | Label value written to corrections |
| Active ROI | set via Change ROI | Only slices within the ROI are targeted |

---

## Setting the active ROI

Both propagation tools respect the 20-slice ROI defined by **Start slice + Change ROI** in the Error Search panel.

| Step | Action |
|---|---|
| 1 | Click "Compute errors" at least once (this loads the volume and sets the spinbox maximum). |
| 2 | Type a value in **Start slice** — this is the first slice of the 20-slice window. |
| 3 | Click **Change ROI**. The viewer snaps to the start slice and the ROI is committed. |
| 4 | The spinbox value is automatically clamped so start + 19 never exceeds the last slice. |

Until **Change ROI** is clicked, changing the spinbox value has no effect. After clicking, error regions are re-filtered to the new range and both propagation tools operate only within it.

To return to full-volume operation, click **Compute errors** again — this resets the ROI to the full volume.

---

## Corrections layer

Both tools write into a single **corrections** layer that is created when you click "Compute errors". The merge rule is `max(existing, new)` — a voxel already assigned a label will only be overwritten if the new label is larger.

When you are satisfied with the corrections:

1. Click **Export** in the Corrections panel.
2. Choose a directory. The store saves each accepted correction as a paired image/mask patch for downstream training.

---

## Troubleshooting

| Message | Cause | Fix |
|---|---|---|
| "Click 'Compute errors' first." | Predictor not initialised | Click Compute errors |
| "Select a GT layer before propagating." | gt_combo is set to None | Choose a GT layer in Error Search panel |
| "No labeled objects on slice N." | Current slice has no foreground in GT | Navigate to a slice with GT labels |
| "No changes detected on slice N." | Prediction layer matches snapshot exactly | Edit the prediction layer with the paint brush before clicking Slice diff |
| "No prediction snapshot." | Prediction layer was never selected | Re-select the prediction layer in the combo box |
| "Run 'Compute errors' first to initialise the corrections layer." | corrections layer missing | Click Compute errors |
| Propagation runs on too many slices | ROI not set | Set Start slice and click Change ROI |
| Propagation result looks wrong | SAM prompt is at the wrong location | The centroid of the GT object or diff region may not be representative; try painting a cleaner source region |
