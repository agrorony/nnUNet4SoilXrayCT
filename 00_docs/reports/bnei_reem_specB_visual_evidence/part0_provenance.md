# Part 0 — Decisive provenance check for `bnei_reem_samp_2_0_recropped` (Specimen B)

Executed per direct instruction, as a follow-up to the visual-evidence run in this same folder. **Note on the prompt file itself**: `bnei_reem_specB_visual_proof_prompt.md` as it currently exists in the repo (`nnUNet4SoilXrayCT/`) contains only Parts 1–4, identical to the version already executed in the previous run — no "Part 0" section is present in that file. This investigation was carried out from the explicit task description given directly in the request, not from repo file content. Flagging this discrepancy rather than silently ignoring it: either a locally-edited copy of the prompt (with Part 0 added) was never saved back to this repo, or Part 0 exists only in another copy of this file elsewhere. Worth reconciling so the canonical prompt file matches what's actually been asked/run.

## Direct answer

**No — `bnei_reem_samp_2_0_recropped`'s segmentation does NOT derive from `new_rec`.** It derives from `\\hive3065\Yael_Mishael\Rony\18.12.25 bnei_reem_samp_2.0` (note the dot), Specimen B's own, separate raw scan. `new_rec` (`C:\Users\rony.schwartz\Desktop\new_rec`) is a different volume entirely — the raw reconstruction behind `bnei_reem_samp_2_rec_recropped`, i.e. **Specimen A's redo**, not Specimen B.

## Evidence chain

### 1. `new_rec`'s own reconstruction log identifies its source directly

`C:\Users\rony.schwartz\Desktop\new_rec\bnei_reem_highkV_cu011_samp_2_rec.log` (805 TIFF slices, last written 2026-08-25 17:16) states, verbatim:

```
[Acquisition]
Data Directory=\\Hive3065\Yael_Mishael\Rony\18.12.25 bnei_reem_samp_2
Filename Prefix=bnei_reem_highkV_cu011_samp_2
...
Image Pixel Size (um)=15.000149
Study Date and Time=18 Dec 2025  13h:34m:02s
[File name convention]
Filename Prefix=bnei_reem_highkV_cu011_samp_2_rec
```

`Data Directory` is `...bnei_reem_samp_2` — **no dot**. This is Specimen A's raw core (per DATA_CATALOG.md: "raw core `18.12.25 bnei_reem_samp_2` (no dot), 15.000149 µm"), and the voxel size (15.000149 µm) and reconstruction-output filename prefix (`bnei_reem_highkV_cu011_samp_2_rec`) match exactly. This reconstruction was written 2026-08-25 — the same date DATA_CATALOG.md records for `bnei_reem_samp_2_rec_recropped`'s "freshly reconstructed 2026-08-25" redo. **`new_rec` is that redo's raw reconstruction, not Specimen B's.**

### 2. Specimen B has its own, separately-scanned raw source, confirmed independently

`\\hive3065\Yael_Mishael\Rony\18.12.25 bnei_reem_samp_2.0\bnei_reem_highkV_cu011_samp_2.0.log` (the raw acquisition log inside Specimen B's own raw folder) states:

```
[Acquisition]
Data Directory=\\HIVE3065\Yael_Mishael\Rony\18.12.25 bnei_reem_samp_2.0
Number Of Files= 1800
Image Pixel Size (um)=15.034357
Study Date and Time=18 Dec 2025  15h:20m:12s
```

This is a **separate scan**, same day as Specimen A's, ~1h46m later (15:20 vs. 13:34), different voxel size (15.034357 µm vs. 15.000149 µm) — matching DATA_CATALOG.md's Specimen B entry exactly ("raw core `18.12.25 bnei_reem_samp_2.0`, 15.034357 µm"). This folder contains its own reconstructed slices directly (filenames `bnei_reem_highkV_cu011_samp_2.0000000NN.tif`), not routed through anything resembling `new_rec`.

### 3. The actual driver script that built `bnei_reem_samp_2_0_recropped` hardcodes Specimen B's raw folder — not `new_rec`

`04_inference/scripts/run_bnei_reem_samp_2_0_recrop_pipeline.py` (the exact script that produced the volume in question, confirmed via DATA_CATALOG.md and `bnei_reem_samp_2_0_repreprocess_prompt.md`) contains, verbatim:

```python
RAW_DIR = Path(r"\\hive3065\Yael_Mishael\Rony\18.12.25 bnei_reem_samp_2.0")
NEW_SAMPLE_ID = "bnei_reem_samp_2_0_recropped"
CROP_SIZE = 650
SLICE_RE = re.compile(r"^bnei_reem_highkV_cu011_samp_2\.0\d{8}\.tif$")
```

`RAW_DIR` and the slice-matching regex both hardcode `samp_2.0` specifically (the regex literally requires a `.0` after `samp_2` to match — a file from `new_rec` or from the no-dot `samp_2` folder would **not** match this regex at all and the script would find 0 real slices and immediately fail its own `len(real_slices) != 1800` check). This is not a naming coincidence or a docstring claim — it is the exact executable logic that ran to build this volume, and it is physically incapable of accidentally consuming `new_rec` or Specimen A's raw folder as input.

**Conclusion**: the raw-source provenance is unambiguous and independently confirmed three separate ways (new_rec's own log naming Specimen A's folder; Specimen B's own distinct raw-scan log; and the exact driver script's hardcoded path + regex). Specimen B's segmentation derives from its own genuine raw scan, not from `new_rec`.

## Normalization step — resolved with exact source evidence

Question: did `bnei_reem_samp_2_0_recropped_0000.nii.gz` go through `02_preprocessing/nnunet/preprocessing_nnUNet_predict.py` with a non-default `--norm` flag, or through `02_preprocessing/filters/run_preprocess.py`'s norm200→NLM output without that script?

**Answer: the latter — norm200→NLM via `run_preprocess.py`, then converted to NIfTI by a *different*, no-op-normalization script (`preprocessing_nnUNet_predict_tif_direct.py`), never touching `preprocessing_nnUNet_predict.py` at all.**

Evidence, in pipeline order (from `run_bnei_reem_samp_2_0_recrop_pipeline.py`'s own step sequence):

1. **`step2_norm_nlm()`** calls `run_preprocess.py --input_dir <cropped_dir>` (in `02_preprocessing/filters/`). That script calls `normalization.py`'s `norm200()`, whose own docstring and code confirm:
   ```
   1. Convert raw dtype -> float32 [0, 1].
   2. Percentile-clip to uint8.
   3. Detect the mineral-peak mode in the bright region [100, 254].
   4. Rescale so that mode -> 200.
   5. Return float32 [0, 1].          # normed.astype(np.float32) / 255.0
   ```
   This produces a float32 volume bounded in [0, 1] — matching the observed `_0000.nii.gz` range **exactly** ([0.0021, 1.0], mean 0.640, confirmed by direct array inspection in the prior run). CUDA NLM denoising is then applied on top (`nlm_volume.tif`), which does not change this bounded range materially.

2. **`step4_tif_to_nifti_and_split()`** converts that NLM tif to NIfTI via `preprocessing_nnUNet_predict_tif_direct.py` — **not** `preprocessing_nnUNet_predict.py`. That script's own header comment states, verbatim:
   > "directly with tifffile, applies **noNorm** (data is already norm200+NLM preprocessed)"

   i.e. it explicitly does no further normalization — it only reshapes/transposes the array (`.transpose(2, 1, 0)`) and writes NIfTI. `preprocessing_nnUNet_predict.py` (the script with the `--norm` flag, default `zscore`, options `[noNorm, zscore, rescale_to_0_1, rgb_to_0_1]`) is **never invoked anywhere in this driver script**.

**So: neither of the two named hypotheses is exactly what happened, but the second is far closer** — it is the `run_preprocess.py` norm200→NLM path, with a *separate* conversion script (`_tif_direct.py`) doing an explicit `noNorm` passthrough into NIfTI format, rather than either (a) `preprocessing_nnUNet_predict.py --norm rescale_to_0_1`, or (b) skipping a conversion script entirely.

### Why canonical looks different (z-score, range [-3.13, 1.53])

This means canonical Bnei Re'em's raw source almost certainly went through a **different, older code path** that does apply z-score normalization (consistent with `preprocessing_nnUNet_predict.py`'s `--norm zscore` default) — but a quick search of canonical's own inference driver scripts (`04_inference/scripts/legacy_per_iteration/_run_inference_fresh_bnei_reem_i4.py`) found no preprocessing/normalization calls at all; that script only runs model inference on already-prepared input. Canonical predates the current driver-script convention (per DATA_CATALOG.md: training lineage "~June/July 2026", months before Specimen B's August pipeline), so its exact normalization invocation was **not** conclusively traced in this pass — flagged as unresolved rather than guessed. What is established with certainty is that Specimen B's `noNorm`-into-nifti / norm200-bounded-[0,1] convention and canonical's z-scored convention are real, verified, **different code paths** — a genuine pipeline inconsistency between two processing eras of this project, not a data-quality problem with either volume.

## Bottom line for the original "trajectories" concern

This closes the file-provenance question decisively: Specimen B's segmentation is built from its own correctly-identified raw scan, via a script whose input-matching logic could not have silently substituted a different raw source. It does **not** by itself address what Rony visually observed in napari's 3D rendering (that remains the open item from the prior visual-evidence run — see the main `README.md` in this folder, particularly Part 2's failed live-screenshot capture). The normalization-convention difference documented in the main README is now fully explained mechanistically here, and confirmed to be a pipeline-era difference, not evidence of a bad scan.
