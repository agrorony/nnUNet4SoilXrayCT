# Part 0b — CRITICAL CORRECTION to Part 0's provenance finding

**This corrects and partially reverses `part0_provenance.md` in this same folder — read that file's finding as superseded by this one, not confirmed by it.** Prompted directly by Rony noticing that the raw folder for `samp_2.0` contains both projection images and reconstructed images, and asking whether the driver script's filename filter actually selected the reconstructed ones. It did not.

## The file-identity finding in `part0_provenance.md` still stands: wrong-source-folder is ruled out

`bnei_reem_samp_2_0_recropped` genuinely derives from `18.12.25 bnei_reem_samp_2.0` (Specimen B's own raw acquisition), not from `new_rec` (Specimen A's redo). That part of the investigation was correct and is not in question here.

## What was missed: the script selected raw ROTATIONAL PROJECTIONS, not reconstructed depth slices

`18.12.25 bnei_reem_samp_2.0\` contains (confirmed by direct listing):
- **1800 files** named `bnei_reem_highkV_cu011_samp_2.0<8-digit-index>.tif` at the top level — no `_rec` in the name.
- A **separate subfolder**, `bnei_reem_highkV_cu011_samp_2.0_Rec\`, containing 831 files — but these are all parameter-tuning preview renders of a single slice (index 478) at many different beam-hardening-correction (`_BHC_*`) and post-alignment-correction (`_PAC_*`) settings, i.e. SkyScan/NRecon's parameter-sweep preview output, **not a full reconstructed volume**.
- No full reconstruction of `samp_2.0` (a complete z-stack of actual cross-sectional slices, analogous to what `new_rec` is for Specimen A) exists anywhere found — checked the raw folder itself, its `_Rec` subfolder, and the local machine's `Desktop` (where `new_rec` itself lives) with no match.

`run_bnei_reem_samp_2_0_recrop_pipeline.py`'s regex —
```python
SLICE_RE = re.compile(r"^bnei_reem_highkV_cu011_samp_2\.0\d{8}\.tif$")
```
— matches **exactly the 1800 top-level files**, confirmed by direct count. The script's own comment claims these are "1800 real numbered slices (matching the scanner log's 'Number Of Files=1800')" — but `Number Of Files=1800` in a SkyScan acquisition log is the **projection count** (360°/0.2° rotation step = 1800), not a reconstructed-slice count. The script's author cross-checked the count against the wrong log field's meaning.

## Decisive image-content evidence (not just filenames)

| File | Shape | Value range | Mean | Interpretation |
|---|---|---|---|---|
| Top-level file matched by the script (`...samp_2.000000900.tif`) | **(896, 1344)** | 5,590–50,027 | 19,436 | Matches the acquisition log's **camera/detector geometry exactly** (`Number Of Rows=896`, `Number Of Columns=1344`) — this is a raw X-ray transmission **projection**, not a reconstructed slice. Compressed dynamic range, no true zero — typical of transmission projection data. |
| `new_rec` (confirmed real reconstruction, Specimen A's redo) | **(1344, 1344)** | 0–65,535 | 14,929 | Square, matching the reconstructed field-of-view convention. Full dynamic range including true zero — typical of a real CT density reconstruction. |
| `_Rec` subfolder preview slice (samp_2.0's own parameter-tuning output) | **(1344, 1344)** | 0–65,535 | 4,553 | Square, full range — this IS what a genuine samp_2.0 reconstruction looks like when one exists (a single-slice preview of it), and it looks nothing like the projection files the pipeline actually used. |

The shape mismatch alone (896×1344 vs. 1344×1344) is unambiguous: **projections and reconstructed slices have different pixel dimensions on this scanner, and the pipeline used the projection dimensions.**

## What this means

**`bnei_reem_samp_2_0_recropped`'s entire pipeline — the 650³ center-crop, norm200, NLM denoising, and nnU-Net segmentation — was built from a stack of 650 consecutive raw rotational X-ray projection images (shadowgrams at sequential ~0.2° rotation angles), not from a tomographically reconstructed 3D density volume.** Stacking projections along their acquisition order and treating that stack as a Z-axis is not a valid soil volume by any definition — each "slice" differs from its neighbor primarily by rotation angle around the sample, not by physical depth. This is a strong, concrete, mechanistic explanation for napari looking like "acquisition trajectories" — because the data essentially *is* a trajectory (rotation-angle) sequence, not a spatial one.

**This reverses the practical conclusion of every prior Track E / visual-evidence pass on this volume**, including:
- The `track_e_correction_prompt.md` correction run's Part 1 finding ("Specimen B's input file is fine, nothing retracted") — that investigation checked file *identity* (right sample, right folder) and got that right, but never checked whether the files inside that folder were the *right kind of image* (projection vs. reconstruction). This correction shows they were not.
- Every one of Specimen B's Track E numbers (χ=−144, connectivity density 0.1543 mm⁻³, Γ=0.9539, DA=0.3304, r*≈451 µm, tortuosity per axis, pore fraction 28.395%) in `connectivity_replicate_expansion_summary.md` and `track_e_correction_summary.md` — all computed from this same invalid volume. **These should be treated as unreliable pending a proper reconstruction**, not as a genuine second physical Bnei Re'em replicate.
- The earlier `bnei_reem_specB_visual_evidence` Part 3 finding that specB was "more slice-to-slice self-consistent than canonical" — that finding is very likely an artifact of this same root cause (consecutive rotational projections of a rigid object are naturally highly self-similar, since the sample itself barely moves between 0.2° steps — this would produce artificially high slice-to-slice correlation, not evidence of clean data).

## What is NOT lost

The underlying raw data is intact and complete: all 1800 real projection images exist, with a full, valid acquisition log (rotation step, geometry, exposure, etc.) — everything needed to run a proper tomographic reconstruction. **This is a missing/skipped processing step, not lost or corrupted source data.** The fix is to actually reconstruct `samp_2.0`'s projections into a real 3D volume (e.g. via SkyScan's NRecon, the same tool that presumably produced `new_rec` for Specimen A and the existing `_Rec` preview for samp_2.0 itself) before repeating the crop → norm200 → NLM → inference pipeline — this is outside what this investigation can do directly (NRecon is external, licensed SkyScan software, not a script in this repo), so it is reported here as the necessary next step rather than attempted.

## Recommendation

- Do not use any existing `bnei_reem_samp_2_0_recropped` Track E or POM numbers as a genuine Bnei Re'em Specimen B result until a real reconstruction exists and the pipeline is rerun on it.
- `bnei_reem_samp_2_0` (the original, pre-recrop attempt) almost certainly has the identical problem, since it's an earlier attempt on the same raw folder — worth checking with the same shape test before assuming it's any more valid.
- The same shape check (896×1344 = projection vs. 1344×1344 = reconstruction) is cheap and mechanical enough that it is worth applying retroactively to any other volume in this project whose raw-folder provenance was assumed rather than verified at the pixel-content level.
