# Bnei Re'em Specimen B — visual/quantitative evidence

Produced per `bnei_reem_specB_visual_proof_prompt.md`. This is evidence, not a verdict — see the per-check statements below rather than a single conclusion. Volumes compared: `bnei_reem_samp_2_0_recropped` (Specimen B, "specB") vs. `bnei_reem_fresh_bnei_reem_i4` (canonical, control).

## Context noticed while loading the data (not itself a motion-artifact check, but relevant)

The two raw sources use **different normalization conventions**:
- `specB` raw (`bnei_reem_samp_2_0_recropped_0000.nii.gz`): float32, range **[0.0021, 1.0]**, mean 0.640 — a min-max-to-[0,1] convention.
- `canonical` raw (`nlm_volume_0000.nii.gz`): float32, range **[-3.128, 1.529]**, mean ≈0 — a z-score (standardized) convention.

Because of this, a single shared display window (same absolute vmin/vmax) would be meaningless across the two files, so every image below uses each volume's own 1st–99th percentile as its display window (same *method*, not the same *numbers* — documented on each image). This convention difference is a genuine pipeline inconsistency between the two processing runs, but on its own it says nothing about whether either raw scan contains a motion/trajectory artifact — it is a display/normalization fact, not a structural one.

## Part 1 — midslice images (12 files)

| File | Caption |
|---|---|
| `specB_axis0_mid_raw.png` | Specimen B, axis 0, mid-slice: raw grayscale CT only. |
| `specB_axis0_mid_overlay.png` | Specimen B, axis 0, mid-slice: raw CT + segmentation overlay (red=pore, green=POM). |
| `specB_axis1_mid_raw.png` | Specimen B, axis 1, mid-slice: raw grayscale CT only. |
| `specB_axis1_mid_overlay.png` | Specimen B, axis 1, mid-slice: raw CT + overlay. |
| `specB_axis2_mid_raw.png` | Specimen B, axis 2, mid-slice: raw grayscale CT only. |
| `specB_axis2_mid_overlay.png` | Specimen B, axis 2, mid-slice: raw CT + overlay. |
| `canonical_axis0_mid_raw.png` | Canonical, axis 0, mid-slice: raw grayscale CT only. |
| `canonical_axis0_mid_overlay.png` | Canonical, axis 0, mid-slice: raw CT + overlay. |
| `canonical_axis1_mid_raw.png` | Canonical, axis 1, mid-slice: raw grayscale CT only. |
| `canonical_axis1_mid_overlay.png` | Canonical, axis 1, mid-slice: raw CT + overlay. |
| `canonical_axis2_mid_raw.png` | Canonical, axis 2, mid-slice: raw grayscale CT only. |
| `canonical_axis2_mid_overlay.png` | Canonical, axis 2, mid-slice: raw CT + overlay. |

**Per-check statement**: these are provided for direct visual inspection — deliberately not pre-judged here. Look at the raw-alone images first (streaking/banding/blur would show there independent of segmentation), then the overlay images.

## Part 2 — 3D rendered view

- **Napari live-window screenshot: attempted, failed.** `specB_napari_3d_screenshot.png` and `canonical_napari_3d_screenshot.png` are both saved files but are **fully blank** (pixel std = 0.0, confirmed programmatically) — this automation session has no accessible interactive desktop for GDI screen capture, even though both napari processes were confirmed alive and responding with the correct window titles. Kept on disk rather than deleted, so the failure itself is inspectable.
- **Fallback used instead** (explicitly permitted by the task spec): `specB_pore_3d_marching_cubes_fallback.png` and `canonical_pore_3d_marching_cubes_fallback.png` — marching-cubes surface of the pore label (5), identical method for both (block-OR downsample factor 5, `skimage.measure.marching_cubes` level 0.5, same fixed camera angle elev=25/azim=60, same rendering style).

**Per-check statement**: this is a coarser, downsampled proxy for the live napari 3D view, not a reproduction of the exact rendering Rony saw (different renderer, different downsampling, different lighting/shading model) — treat it as a rough structural cross-check, not a substitute for the original observation.

## Part 3 — objective motion-artifact screening on RAW volumes

All three checks below ran on the raw preprocessed CT intensity volumes (`_0000.nii.gz`), not the segmentation, per the task spec.

### 3.1 — Slice-to-slice consistency (Pearson correlation between consecutive slices)

Note: the task spec suggested correlation *or* SSIM. `skimage`'s SSIM was tried first and was pathologically slow on these arrays (>90 minutes of CPU with not even one axis finished, killed before completion) — switched to fully-vectorized Pearson correlation, the spec's explicitly-named alternative, which completed in under a minute.

| Volume | Axis 0 mean (min) | Axis 1 mean (min) | Axis 2 mean (min) |
|---|---|---|---|
| specB | 0.99942 (0.99604) | 0.99947 (0.99760) | 0.99969 (0.99852) |
| canonical | 0.98726 (0.97765) | 0.98744 (0.97916) | 0.98930 (0.98063) |

Full per-slice-pair values: `motion_screen_raw_stats.json` (`consecutive_pearson_correlation` per volume/axis). Plots: `motion_screen_axis{0,1,2}_stats_and_corr.png` (bottom panel).

**Per-check statement**: on this specific metric, **specB is more slice-to-slice self-consistent than canonical, on all 3 axes** — the reverse of what "specB has a motion/trajectory artifact" would predict, if such an artifact typically manifests as abrupt slice-to-slice discontinuities. Neither volume's minimum correlation drops sharply (both stay ≥0.976), i.e. neither shows an abrupt single-slice discontinuity by this measure.

### 3.2 — Periodic banding / streak detection (FFT of per-slice mean-intensity profile)

Peak analysis (top power bins, excluding the DC/bin-0 term):

| Volume | Axis | Top-3 frequency bins | Top bin power vs. median non-DC power |
|---|---|---|---|
| specB | 0 | 1, 2, 3 | 1,537,802× |
| specB | 1 | 1, 2, 4 | 27,223× |
| specB | 2 | 1, 2, 3 | 108,886× |
| canonical | 0 | 1, 3, 2 | 347,958× |
| canonical | 1 | 1, 2, 5 | 1,074,063× |
| canonical | 2 | 1, 2, 3 | 82,427× |

Plots: `motion_screen_axis{0,1,2}_fft.png`.

**Per-check statement**: for **both** volumes, on all 3 axes, the dominant power sits at the lowest frequency bins (1–5) — consistent with smooth, large-scale density/intensity trends across the stack (e.g. sample tapering), not a periodic banding pattern at a specific mid/high frequency. **Neither volume shows an isolated anomalous peak away from the low-frequency end** — i.e. this specific check finds no periodic-trajectory signature in either scan.

### 3.3 — Per-slice intensity statistics (mean/std/min/max)

Plots: `motion_screen_axis{0,1,2}_stats_and_corr.png` (top panel, both volumes overlaid). Raw numeric arrays: `motion_screen_raw_stats.json`.

**Per-check statement**: presented for direct visual inspection of abrupt jumps, drift, or oscillation — deliberately not pre-judged here; look for any single-slice spike or step change unique to one volume.

## What this does NOT establish

- It does not confirm or rule out a genuine acquisition-level motion artifact in either raw scan — these are the specific, named objective checks from the task spec, not an exhaustive CT-artifact screen.
- It does not explain what Rony visually saw in napari's 3D rendering specifically, since that exact live view could not be captured (Part 2).
- The raw-value normalization-convention difference (see top) is real and worth fixing for pipeline consistency, but is a separate issue from whether either scan has a motion artifact.

Every image/plot listed above is an actual saved file in this folder (and its network-drive mirror) — none of the above is a substitute for looking at them directly.
