# micro-SAM 3D Proofreader

A napari-based interactive tool for correcting dense 3D voxel-wise label maps produced by CNNs (e.g. nnUNet). The user loads a volume and its prediction, navigates to error regions, inspects SAM-proposed corrections region by region, accepts or rejects them, and exports the corrected labels together with `(volume_crop, gt_crop)` training pairs ready for the next CNN iteration.

---

## Background & motivation

This tool was developed as part of an iterative nnUNet segmentation pipeline for soil X-ray CT volumes ([`nnUNet4SoilXrayCT`](../README.md)).

The core problem: a CNN produces "almost good" dense predictions, but boundary errors and missed phases need human correction before the next training iteration. Annotating from scratch is slow; what's needed is a way to *review and patch* the existing prediction at the regions where it is wrong.

micro-SAM was chosen because its GPU-cached image embeddings make interactive segmentation proposals fast enough for a fluid proofreading loop — sub-second response after the first request within a region. The tool propagates a point or box prompt through a Z-chunk using the same cached embeddings, avoiding full-volume precomputation entirely.

---

## Key design decisions

**On-demand embedding cache.** `VolumeEmbedder` runs the SAM image encoder on a Z-slice the first time it is requested, then stores the result in memory. All subsequent accesses to that slice cost ~0 ms. No embeddings are computed upfront; the user pays only for slices they actually visit.

**Chunk-based workflow.** SAM runs only within the active bounding box. The user defines a region of interest via one of three input modes, and `MaskPredictor3D` computes embeddings for only those Z-slices — keeping each interaction cycle to a few seconds on GPU even for large volumes.

**Three ROI input modes.**
- *Auto* — jumps to the next largest unreviewed error region, computed from `compute_error_map` (GT diff if GT is available, gradient-magnitude proxy otherwise).
- *Draw* — user draws a rectangle on a napari Shapes layer to define the active chunk manually.
- *Load* — reads a JSON or CSV file of `{z0, z1, y0, y1, x0, x1}` bounding boxes as a review queue, enabling pre-computed or pre-curated region lists.

**Adjacent-slice overlay.** A semi-transparent `adjacent_mask` layer always shows the current prediction at Z±1 as the user scrolls, making it easy to maintain boundary continuity across slices without switching layers.

**Export for retraining.** Accepted corrections are accumulated as sparse edits. On export, the tool writes:
- `corrected_labels.tiff` — the full label map with all accepted corrections applied in-place.
- `pair_NNNN.npz` — per-correction `(volume_crop, gt_crop)` pairs for direct use as nnUNet training patches.

---

## References

1. **micro-SAM** — Archit et al., "Segment Anything for Microscopy", *Nature Methods*, 2024.  
   https://www.nature.com/articles/s41592-024-02580-4  
   Foundation model used for interactive segmentation proposals; provides GPU-cached per-slice embeddings and the `SamPredictor` API used throughout this tool.

2. **nnInteractive** — MIC-DKFZ, "nnInteractive: Redefining 3D Promptable Segmentation", *arXiv*, 2025.  
   https://arxiv.org/abs/2503.08373  
   Alternative 3D interactive segmentation framework; informed the prompt-propagation design and the idea of propagating 2D prompts through Z-slices within a chunk.

3. **SuRVoS2** — Luengo et al., "SuRVoS 2: Accelerating Annotation and Segmentation for Large Volumetric Bioimage Workflows", *Frontiers in Cell and Developmental Biology*, 2022.  
   https://www.frontiersin.org/articles/10.3389/fcell.2022.842342/full  
   Informed the chunk-based annotation workflow design and the separation between error detection and targeted correction.

4. **WEBKNOSSOS** — Boergens et al., "webKnossos: efficient online 3D data annotation for connectomics", *Nature Methods*, 2017.  
   https://www.nature.com/articles/nmeth.4331  
   Informed the adjacent-slice overlay UX and the region-based proofreading workflow where a reviewer steps through a queue of flagged regions.

5. **Segment Anything Model (SAM)** — Kirillov et al., "Segment Anything", *ICCV*, 2023.  
   https://arxiv.org/abs/2304.02643  
   Underlying foundation model; defines the image encoder, prompt encoder, and mask decoder architecture used by micro-SAM.

---

## Setup

```bash
conda env create -f environment.yml
conda activate microsam3d
```

SAM `vit_b` weights (~375 MB) are downloaded automatically on first use and cached at `%LOCALAPPDATA%\micro_sam\micro_sam\Cache\models\`.

---

## Usage

```bash
# Minimum: volume + nnUNet prediction
python run.py volume.tif pred.tif

# With ground-truth annotation (error map shows real disagreement)
python run.py volume.tif pred.tif gt.tif

# Full argument reference
python run.py --help
```

### Workflow

1. **Load layers** — the CLI loads the volume and prediction automatically. Additional layers can be dragged into napari.
2. **Select SAM model** — choose `vit_b` (fast, default), `vit_l`, or `vit_h` (more accurate). First call downloads the checkpoint.
3. **Compute errors** — click the button. The `error_map` layer highlights disagreements; the `adjacent_mask` layer shows Z±1 context as you scroll.
4. **Pick an ROI mode** — toggle between Auto / Draw / Load (see above).
5. **Propose fix** — SAM embeds only the Z-slices inside the active chunk (on demand, cached after first use), then predicts a corrected mask shown in `sam_proposal`.
6. **Accept / Reject** — press **Y** to store the correction and advance, **N** to skip. Buttons also available in the panel.
7. **Export** — saves `corrected_labels.tiff` and per-correction `pair_NNNN.npz` patches.

### ROI file format

**JSON** — array of objects:
```json
[
  {"z0": 100, "z1": 120, "y0": 200, "y1": 280, "x0": 150, "x1": 230},
  {"z0": 300, "z1": 310, "y0": 50,  "y1": 100, "x0": 400, "x1": 450}
]
```

**CSV** — header row `z0,z1,y0,y1,x0,x1`:
```
z0,z1,y0,y1,x0,x1
100,120,200,280,150,230
```

---

## Module overview

| File | Purpose |
|---|---|
| `embedder.py` | `VolumeEmbedder` — lazy per-Z-slice SAM embedding cache |
| `error_map.py` | `compute_error_map`, `get_error_regions` |
| `predictor.py` | `MaskPredictor3D` — runs SAM decoder per Z-slice within a bbox |
| `correction_store.py` | `CorrectionStore` — accumulates edits, exports tiff + npz pairs |
| `napari_plugin.py` | `create_widget(viewer)` — magicgui dock widget; `load_rois_from_file()` |
| `run.py` | CLI entry point |
| `environment.yml` | `microsam3d` conda environment |
| `dev/` | Test scripts and synthetic fixtures (not part of the tool) |

---

## Development notes

- Tested on: Windows Server 2019, NVIDIA RTX A6000, CUDA 11.7, `venv-napari` (napari 0.7.0, micro-sam latest).
- `micro_sam.util.get_sam_model()` returns a `SamPredictor` directly — not a `(sam, predictor)` tuple as older documentation suggests. This was corrected during development.
- NIfTI predictions from nnUNet are stored as `(Y, X, Z)`; transpose with `.T` to get `(Z, Y, X)` before passing to this tool.
- Test suite: `dev/_test_suite.py` — 12 tests covering imports, GPU, SAM load, embedding cache, error map, region detection, SAM prediction, store export, ROI loading, CLI, and headless import. Run with:

```bash
python dev/_test_suite.py
```
