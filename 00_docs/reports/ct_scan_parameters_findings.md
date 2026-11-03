# CT scan acquisition & preprocessing parameter findings

Read-only discovery pass for Methods §2.3. Every value below is cited to a specific file. Where a `.log`/`.txt` file does not exist on the share, or exists but lacks the field, this is stated explicitly rather than guessed.

## Constant across every specimen for which an acquisition log exists

Source: SkyScan1272 `.log` files (NRecon/SkyScan-style headers, `[System]`/`[Acquisition]`/`[Reconstruction]` sections) found alongside each raw slice-stack folder.

| Parameter | Value | Evidence |
|---|---|---|
| Scanner make/model | Bruker/SkyScan **SkyScan1272**, Instrument S/N `19M09225` | `[System]` block, e.g. `\\hive3065\Yael_Mishael\Rony\10.12.25_Rehovot_samp_2\Rehovot_samp2_highkV_Cu0.11_15um.log` line 2 |
| X-ray source | HAMAMATSU_L10101-67 | Same file, `Source Type=HAMAMATSU_L10101-67` |
| Detector | XIMEA xiRAY11, camera pixel size 9.0 µm, binning 3×3 | Same file, `Camera Type`/`Camera Pixel Size (um)`/`Camera binning` |
| Reconstruction software | **NRecon**, Program Version 2.1.0.2, engine GPUReconServer/NReconServer v2.1.0 | `[Reconstruction]` section, e.g. `29.3.26 mishmar_hanegev_samp_2\mishmar_hanegev_Cu011_samp_2_Rec\mishmar_hanegev_Cu011_samp_2_rec.log` lines 58-62; also present in the Rehovot and Mishmar Cu011 `_rec.log` files |
| Source current | **100 µA** | `Source Current (uA)= 100`, every acquisition log listed below |
| Exposure time per projection | **1408 ms** | `Exposure (ms)=1408`, every acquisition log listed below |
| Rotation step | **0.200°** | `Rotation Step (deg)=0.200`, every acquisition log listed below (matches `Angular Step (deg)=0.2000` in the reconstruction section) |
| Frame averaging | **ON, 2 frames** | `Frame Averaging=ON (2)`, every acquisition log listed below |
| Filter | **Cu 0.11 mm** (0.11 mm copper filter) — confirms the `highkV_Cu0.11` naming convention refers to this filter, not an arbitrary label | `Filter=Cu 0.11mm`, every acquisition log listed below |
| Reconstruction filter kernel | Hamming, Alpha=0.54; Ring Artifact Correction 2 or 3; Beam Hardening Correction 10-15% (varies per reconstruction) | `[Reconstruction]` sections, e.g. same Mishmar log lines 94-98 |
| Rotation range | 360° (`Use 360 Rotation=YES`) | Every acquisition log |

**On "highkV":** the logs confirm the filter reading (Cu 0.11 mm) but do not themselves state what kV value the "high" qualifier is relative to — no lower-kV comparison scan/log exists on the share for the same specimens. The actual source voltage used **does vary by specimen** (see table below); it is not a single constant "highkV" value. Treat "highkV" as a folder-naming label whose absolute meaning (relative to what baseline) is **NOT FOUND** — only the measured kV per scan (below) is confirmed.

## Per-specimen acquisition/reconstruction table

All voxel sizes below are read directly from the `.log` files' `Image Pixel Size (um)` / `Pixel Size (um)` fields and match `DATA_CATALOG.md`'s recorded values exactly (cross-check, not re-derivation).

| Specimen | kV | Raw slices / XY (log) | Voxel size (log-confirmed) | Crop size used in reported results | Citation |
|---|---|---|---|---|---|
| Bnei Re'em Specimen A (`bnei_reem_samp_2`, no dot — canonical) | **90 kV** | 1800 files, 896×1344 | 15.000149 µm | **652 × 650 × 650** (Z×H×W) — not a perfect cube | kV/voxel: `18.12.25 bnei_reem_samp_2\bnei_reem_highkV_cu011_samp_2.log` lines 28,30. Crop shape of the volume actually used (`nlm_volume.tif`/`nlm_volume.nii.gz`): `05_evaluation\psd\pom_analysis_20260829_roi_expansion\part1_margin_report.json`, `bnei_reem_canonical.current_crop_shape_zhw = [652, 650, 650]` |
| Bnei Re'em Specimen B (`bnei_reem_samp_2.0` / `_recropped`) | **90 kV** | 1800 files, 896×1344 | 15.034357 µm | Exact **650³** cube | kV/voxel: `18.12.25 bnei_reem_samp_2.0\bnei_reem_highkV_cu011_samp_2.0.log` lines 28,30. Crop: `04_inference\scripts\run_bnei_reem_samp_2_0_recrop_pipeline.py` line 49, `CROP_SIZE = 650  # matches canonical Bnei Re'em nlm_volume.tif (650x650x652)`, and lines 90-114 implementing a literal cubic crop |
| Mishmar `mishmar_hanegev_maoz_3_5p85um` (native, canonical POM) | **NOT FOUND** | — | 5.85 µm (per `DATA_CATALOG.md`) | **1000³** (baseline used in all reported POM/interface results) | No `.log`/`.txt` acquisition file exists in `\\hive3065\Yael_Mishael\Rony\mishmar_hanegev_maoz\3-16mm_diam_5.85um\` — directory contains only slice images, confirmed by directory listing. Crop: `part1_margin_report.json`, `mishmar_native_5p85um.current_crop_shape_zhw = [1000, 1000, 1000]` |
| Mishmar `mishmar_hanegev_maoz_2_8p8um` (2nd specimen) | **NOT FOUND** | — | 8.8 µm (per `DATA_CATALOG.md`) | **1000³** (baseline used in all reported POM/interface results) | No `.log`/`.txt` acquisition file exists in `\\hive3065\Yael_Mishael\Rony\mishmar_hanegev_maoz\2-16mm_diam_8.8um\` (only a `___All_Errors.txt` sync-error log, no acquisition header) — confirmed by directory listing. Crop: `part1_margin_report.json`, `mishmar_second_8p8um.current_crop_shape_zhw = [1000, 1000, 1000]` |
| Mishmar `Cu011_samp_1` (unprocessed, partial only) | **100 kV** | 1800 files, 896×1075 (Partial Width 80%) | 15.000149 µm | **N/A — never run through full crop/norm200/NLM.** Only a 328/822-slice partial NLM+crop subset exists (per `DATA_CATALOG.md`) | `29.3.26 mishmar_hanegev_samp_1\mishmar_hanegev_Cu011_samp_1.log` lines 28,30 |
| Mishmar `Cu011_samp_2` (Track E pore-only, POM invalid) | **100 kV** | 1800 files, 896×1075 (Partial Width 80%) | 15.000149 µm | XY confirmed **650×650** (Z not independently confirmed from available logs) | kV/voxel: `29.3.26 mishmar_hanegev_samp_2\mishmar_hanegev_Cu011_samp_2.log` lines 28,30. Crop XY: inference input-shape lines in `04_inference\scripts\cu011_loess_i2_inference_log.txt` (`torch.Size([1, ..., 650, 650])`, repeated chunks) |
| Mishmar `Cu011_samp_3` (unprocessed, partial only) | **100 kV** | 1800 files, 896×860 (Partial Width 64%) | 15.000149 µm | **N/A — never run through full crop/norm200/NLM.** Only a 623/837-slice partial subset exists | `29.3.26 mishmar_hanegev_samp_3\mishmar_hanegev_Cu011_samp_3.log` lines 28,30 |
| Rehovot `samp1` (raw only, unprocessed) | **100 kV** | 1800 files, 896×1276 (Partial Width 95%) | 15.034357 µm | **N/A — never cropped/preprocessed** (per `DATA_CATALOG.md`) | `10.12.25 Rehovot\Rehovot_samp1_highkV_Cu0.11_15um.log` lines 28,30 |
| Rehovot `samp2` (canonical/most-used) | **100 kV** | 1800 files, 896×1236 (Partial Width 92%) | 15.000149 µm | **650³** (pipeline comment states "center-crop 650^3") | kV/voxel: `10.12.25_Rehovot_samp_2\Rehovot_samp2_highkV_Cu0.11_15um.log` lines 28,30. Crop: `04_inference\scripts\run_rehovot_inference_pipeline.py` line 8, docstring "pipeline -- center-crop 650^3, norm200, CUDA NLM, 15um voxels" |
| Rehovot `samp3` (`_clean` reconstruction) | **100 kV** | 1800 files, 896×1236 (Partial Width 92%) | 15.034357 µm | **650³** (same pipeline as `samp2`) | kV/voxel: `10.12.25_Rehovot_samp_3_clean\Rehovot_samp3_highkV_Cu0.11_15um.log` lines 28,30. Crop: same pipeline docstring as above; `04_inference\scripts\run_rehovot_inference_pipeline.py` treats both Rehovot volumes identically |

### Notes on the crop-size question (item 4)

The "650³ standard" is **not universal**:
- **Bnei Re'em** (both specimens) and **Rehovot** (both processed specimens) were cropped to (approximately) 650³ and this is what the reported figures/results use.
- **Both POM-eligible Mishmar volumes** (`mishmar_native_5p85um`, `mishmar_second_8p8um`) were never cropped to 650³ at all — their baseline crop, used in every reported POM/interface-metrics result to date, is **1000³** (`part1_margin_report.json`, `current_crop_shape_zhw`).
- A separate, later **ROI-expansion experiment** (`05_evaluation\psd\pom_analysis_20260829_roi_expansion\final_report.md`, lines 45-49 and 121-125) tried enlarging all three POM volumes further: Bnei Re'em's enlargement to 722³ **failed** (POM channel collapsed) and fell back to its original 652×650×650 crop; Mishmar native grew 1000³→**1216³** and Mishmar second grew 1000³→**1614³**, both passing sanity checks. **However, this ROI-expanded set was used only for the (now-retired) shape/archetype clustering work.** The POM interface-metrics run that is actually in the v9 draft (`pom_analysis_20260831_interface_metrics_resmatched/scripts/run_pom_interface_metrics.py`, lines 42-74) explicitly loads the **original, non-ROI-expanded** volumes (`bnei_reem_fresh_bnei_reem_i4/inference_concatenated/nlm_volume.nii.gz` and the `mishmar_label_downsample*` volumes derived from the original 1000³ crops) — so the 1216³/1614³ crops do **not** supersede the numbers in the current draft; they exist only in the retired clustering analysis.
- Bnei Re'em Specimen B and the standalone `bnei_reem_samp_2_rec_recropped` re-crop (`05_evaluation\psd\full_volume_batch\logs\preprocess_only_samp_2_rec_v2.log`, line 8: `Cropped 650^3 volume written to ...`) both use an exact 650³ cube, distinct from canonical Specimen A's 652×650×650 shape.

## norm200 — confirmed definition

**File:** `02_preprocessing\filters\normalization.py` (module docstring: "Slice stacking and norm200 normalization for 3D µCT volumes... ported from legacy/preprocess_ct_images.py but adapted to operate on the full 3D volume").

The operation is **not** a simple percentile clip-and-rescale to a fixed range, and **not** literally "rescale to mode=200" in one step. It is a two-stage process:

1. Percentile-based rescale of the (0-1 normalized) float volume to uint8, using the 0.5th/99.5th percentiles as the stretch bounds (`P_LOW = 0.5`, `P_HIGH = 99.5`):
```python
def _to_uint8(volume: np.ndarray) -> np.ndarray:
    x = volume.astype(np.float32, copy=False)
    mn = float(np.percentile(x, P_LOW))
    mx = float(np.percentile(x, P_HIGH))
    scaled = (x - mn) * (255.0 / (mx - mn))
    return np.clip(scaled, 0, 255).astype(np.uint8)
```
2. Detect the histogram mode within the range `[MODE_LOW=100, MODE_HIGH=254]` of that uint8 volume, then multiplicatively rescale the whole uint8 volume so that mode maps to a fixed target value of **200.0** (`TARGET_MODE = 200.0`):
```python
def _rescale_to_mode_200(volume_u8, mode, target=TARGET_MODE):
    factor = target / float(mode)
    out = volume_u8.astype(np.float32) * factor
    return np.clip(out, 0, 255).astype(np.uint8)
```
So "norm200" = **percentile[0.5,99.5]-stretch to uint8, then linear rescale so the dominant grayscale mode (detected in [100,254]) is mapped to 200**. Confirmed live in a run log: `05_evaluation\psd\full_volume_batch\logs\preprocess_samp_2_0.log` line 6, `norm200: detected mode = 244, rescaled to target = 200.0`, and `run_preprocess.py` line 94 (`norm_volume = norm200(raw_volume).astype(np.float32)`) shows it runs immediately after slice-stacking and before NLM.

## NLM (non-local means) denoising — confirmed parameters

**Implementation:** custom **PyTorch CUDA kernel** (not skimage/scipy), file `02_preprocessing\filters\gpu_nlm_torch.py` (module docstring: "This module is intentionally self-contained and avoids skimage/scipy denoisers"). Hard-fails if `torch.cuda.is_available()` is False.

Parameters, from the `NLMConfig` dataclass (lines 38-44) as actually invoked in `run_preprocess.py` lines 100-106:
```python
cfg = NLMConfig(
    patch_size=5,
    patch_distance=6,
    h=None,
    chunk_size=128,
    min_chunk_size=32,
)
```
- **Patch size = 5** (5×5×5 voxel comparison patch, via `F.avg_pool3d(..., kernel_size=patch_size, ...)`).
- **Search window / patch distance = 6** — this is a search *radius* in voxels (`_build_offsets(radius=patch_distance)` iterates `dz,dy,dx` from -6 to +6 in each axis, i.e. a 13×13×13 = 2,197-offset search neighborhood, excluding the center).
- **h (filtering parameter) is not fixed** — it is derived per-volume from a robust noise estimate: `h = max(0.6 * sigma, 1e-4)`, where `sigma` is a median/MAD-based robust estimator (`_estimate_sigma_torch`, lines 47-62: `sigma = 1.4826 * median(|x - median(x)|)`, subsampled to 200M voxels for volumes too large for `torch.median` on CUDA). Example live values: `preprocess_samp_2_0.log` line 9, `NLM CUDA: estimated sigma=0.122096, h=0.073258`; the Bnei Re'em canonical-style re-crop run shows a different value per volume (`preprocess_only_samp_2_rec_v2.log` line 21, `sigma=0.191866, h=0.115120`) — confirming h is volume-specific, not a fixed constant.
- **Chunking:** the volume is processed in non-overlapping 128³ tiles with a halo of `patch_distance + patch_size//2 = 8` voxels for correctness at tile boundaries (`_tile_halo`, line 125-126), purely a memory/engineering detail, not a filtering-strength parameter.

## Suggested `DATA_CATALOG.md` additions (for Rony to review/apply)

1. **Scanner make/model, source, and detector** are never recorded in `DATA_CATALOG.md` today. Worth adding as a one-line "Acquisition hardware" note near the top (it is constant: SkyScan1272 / HAMAMATSU_L10101-67 source / XIMEA xiRAY11 camera / NRecon 2.1.0.2 reconstruction), since Methods §2.3 needs this and it is currently undocumented anywhere in the repo outside the raw `.log` files.
2. **Per-specimen kV** is not recorded anywhere in `DATA_CATALOG.md` and it is **not** constant (90 kV for both Bnei Re'em specimens, 100 kV for every Mishmar Cu011 and Rehovot specimen) — worth a column, especially since the "highkV" naming convention could otherwise mislead a reader into assuming one fixed high-kV setting across all soils.
3. **No acquisition `.log` exists for either of the two POM-critical Mishmar volumes** (`mishmar_hanegev_maoz_3_5p85um` native and `mishmar_hanegev_maoz_2_8p8um`) — only image slices are present in their raw folders on the share. This is a real gap (not just an oversight in this discovery task): DATA_CATALOG.md currently states these volumes' voxel sizes without a `.log` citation (unlike every other entry, which is explicitly marked "log-confirmed"). Worth flagging this distinction explicitly in the catalog, since these two volumes underpin the headline POM comparison in the draft.
4. **Crop size per specimen** is not recorded in `DATA_CATALOG.md` at all, and (per this investigation) it genuinely varies — 650³-ish for Bnei Re'em/Rehovot vs. 1000³ baseline for both POM-eligible Mishmar volumes (with a since-retired 1216³/1614³ ROI-expansion experiment for the latter two that does not affect the current draft's numbers). Worth adding a "crop shape (Z×H×W)" column so a future reader doesn't assume a single "650³ standard" applies everywhere.
5. Consider recording the norm200/NLM parameter provenance (file paths above) directly in `DATA_CATALOG.md` or `ARCHITECTURE.md` once, rather than only in scattered run logs — several prompts/summaries reference "norm200" and "CUDA NLM denoise" by name without ever linking to `02_preprocessing\filters\normalization.py` / `gpu_nlm_torch.py`.
