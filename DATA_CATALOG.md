# Data Catalog — CT scans, segmentations, and validity

> Single source of truth for what scans exist, where, and their processing/validity status. Update this whenever a new scan is found, processed, or its validity is reassessed. Prompts should read this before doing their own rediscovery.
>
> **2026-08-28 merge note:** Two versions of this file had diverged — a local-project-folder copy (rebuilt 2026-08-27/28 from scratch after a phantom-row problem) and this repo's own copy (a careful full-share inventory sweep from 2026-08-25, with `.log`-confirmed voxel sizes and raw-source paths). This version merges them: the 2026-08-25 sweep's Mishmar and Rehovot sections are the better evidence and are kept close to as-is.
>
> **2026-08-29 correction (final):** Bnei Re'em is **2 physical specimens**. "Canonical" is not a third scan — it's just the long-standing name for the *older* reconstruction of one of the two specimens (the one used in every prior comparison). Confirmed by Rony plus two independent evidence points: canonical's `fresh_bnei_reem_i4` training lineage dates back to ~June/July 2026, far predating `samp_2_0` (Aug 4); and canonical's recorded voxel size (15.000149 µm) exactly matches the `samp_2` (no dot) raw folder's logged voxel size, not `samp_2.0`'s (15.034357 µm). So the `samp_2` (no dot) raw core was processed twice, years apart — once as "canonical," once as this week's redo — while `samp_2.0` is the other, separate physical core.
>
> **One file, one location going forward:** this repo (`nnUNet4SoilXrayCT`, local git clone) is the canonical location for this file. The local project folder (`resarch exercise\`) keeps a copy for quick reference but should be treated as a mirror, not a second source of truth — update this one first, then copy over. Per Rony (2026-08-29): the `Z:\Rony\...` network-share copy is **not in scope** and should be disregarded going forward — this repo location is the only one that matters.

## Analysis-tier policy (Rony, 2026-08-29)

- **Structural/topology metrics (pore-only: χ, connectivity density, Γ, DA, tortuosity, PSD, etc.):** every reconstruction listed below that has a valid pore channel is in scope, regardless of its POM status. This includes ones excluded from POM work (e.g. `Cu011_samp_2`, Bnei Re'em Specimen B) — POM invalidity does not disqualify pore/structure use.
- **POM-inclusive analysis (Track A/B, 3-class matrix/POM/pore work):** restricted to exactly 3 volumes — Bnei Re'em canonical (`bnei_reem_fresh_bnei_reem_i4`), Mishmar `mishmar_hanegev_maoz_3_5p85um` (5.85 µm), and Mishmar `mishmar_hanegev_maoz_2_8p8um` (8.8 µm). No other volume — regardless of future processing status — enters POM analysis unless Rony explicitly adds it here.

## Inclusion rule (unchanged, 2026-08-24)

A sample is **excluded** only for one of these concrete reasons:
1. **Channel collapse** — a phase's voxel fraction crashes toward zero (e.g. POM <0.3%) while the other phase(s) stay in a normal range. This is the fingerprint of the model failing to recognize a class, not a real soil difference (seen in `Cu011_samp_2`).
2. **Known unfixed preprocessing defect** — e.g. missing center-crop, wrong model/checkpoint — until corrected.
3. **Wrong model/checkpoint used** for the soil (verified against the driver script + inference log, not assumed).

A sample is **NOT** excluded merely for differing in magnitude from another sample of the same soil — different physical specimens can genuinely differ. Magnitude differences get a note, not an exclusion.

---

## Bnei Re'em (Vertisol) — 2 physical specimens (confirmed 2026-08-29 per Rony)

### Specimen A — raw core `18.12.25 bnei_reem_samp_2` (no dot), 15.000149 µm
| | |
|---|---|
| Raw source | `Z:\Rony\18.12.25 bnei_reem_samp_2\` — full ~1800-slice stack |
| Sample ID | `bnei_reem_fresh_bnei_reem_i4` |
| Preprocessing | Full pipeline (stack → crop 650³ → norm200 → NLM), trained through iterations i2→i4 (~June/July 2026) |
| Model/checkpoint | `multi_sample_fresh_bnei_reem_i4`, `checkpoint_final.pth` |
| Pore % / POM % | 21.636 / 0.819 |
| Status | **VALID — used in every prior comparison as "Bnei Re'em."** |
| Location | `Z:\Rony\remote_computer backup\nnUNet_resources\bnei_reem_fresh_bnei_reem_i4\inference_concatenated\nlm_volume.nii.gz` |

### Specimen B — raw core `18.12.25 bnei_reem_samp_2.0`, 15.034357 µm
| | |
|---|---|
| Raw source | `Z:\Rony\18.12.25 bnei_reem_samp_2.0\` — full ~1800-slice stack |
| Processed file | `10.5\bnei_reem_samp_2_0.tif` (Aug 4, crop step skipped — driver bug) → `10.5\bnei_reem_samp_2_0_recropped.tif` (Aug 24, full pipeline re-run correctly: drop 12 stray SkyScan preview TIFFs, crop 650³, norm200, NLM) |
| Pore % / POM % | ~39.4 / ~11.0 (original, superseded) → 28.3 / 7.62, elevated not collapsed (recropped, current) |
| Status | **VALID for 2-class (pore/solid) work only — not used for POM/3-class analysis.** 2026-08-26: Rony decided not to pursue this specimen further for POM (settled on Bnei Re'em n=1 for POM — canonical only) |
| Location | `Z:\Rony\remote_computer backup\nnUNet_resources\bnei_reem_samp_2_0_recropped\` |
| Track E correction check (2026-09-03) | Rony flagged the 2026-08-29 Track E run (`psd_diag_20260829T164631_bnei_reem_samp_2_0_recropped`) as possibly computed on scan trajectories/motion-metadata rather than this segmentation. Independent re-investigation (fresh reload + `np.unique()`, full preprocessing-log provenance trace, cross-check against a second script's voxel counts, both sanity checks re-verified) found **no evidence of a wrong input** — see `Topology_Metrics_Aug2026/track_e_correction_summary.md` Part 1 for full detail. χ=−144/Γ=0.9539/DA=0.330/r*≈451µm are NOT retracted. **Open item for Rony** — this discrepancy is unresolved, not confirmed as a false alarm. |

Bnei Re'em POM work remains **n=1** (canonical only). Specimen B is usable for 2-class pore/solid work only (A2, Track E connectivity) — that gives Bnei Re'em 2 *reconstructions* for structural/topology metrics, matching its 2 *physical specimens*.

**2026-09-02→05 — file-provenance bug ruled out; the underlying data-quality question is UNRESOLVED, not settled.** Rony flagged the `psd_diag_20260829T164631_bnei_reem_samp_2_0_recropped` run (PID 13048) as having used the scan's trajectories rather than the segmented volume. An independent re-investigation (`track_e_correction_prompt.md` Part 1) reloaded the exact input path recorded in the run's own `config.json`, reproduced the documented pore/POM fractions (28.395%/7.618%, matching this catalog's 28.3/7.62 to rounding), traced a complete preprocessing log, and found PID 13048 is a napari viewer process, not the compute pipeline — **this specific wrong-file bug is ruled out.** That is a narrower finding than "the data is fine": it does not address Rony's direct visual observation that this volume's pore network, loaded in napari, looks very different from every other scan in this project and reads as trajectory/motion-artifact-like — a log trail and a matching voxel fraction are consistent with a genuine CT acquisition artifact in the raw scan (correctly processed garbage is still garbage), not just with a pipeline bug. **Rony maintains, with 100% confidence in his own observation, that this scan is not good — a claim no one has yet independently verified or falsified with actual visual/quantitative evidence.** `bnei_reem_specB_visual_proof_prompt.md` (repo root, 2026-09-05) asks for real inspectable evidence — side-by-side midslice images, a reproduced napari-equivalent screenshot, and objective raw-scan motion-artifact screening (slice-to-slice consistency, FFT banding detection) — not another narrative report. **Until that runs, Specimen B's Track E numbers should be treated as of undetermined reliability, not as confirmed valid.**

---

## Mishmar HaNegev (Loess) — 5 physical scans (2026-08-25 share sweep)

| Sample ID | Raw source (share) | Voxel size | Preprocessing | Model/checkpoint | Pore % | POM % | Status |
|---|---|---|---|---|---|---|---|
| `mishmar_native` = `mishmar_hanegev_maoz_3_5p85um` (canonical) | `Z:\Rony\mishmar_hanegev_maoz\3-16mm_diam_5.85um\` | 5.85 µm | Full pipeline, confirmed | `i2_loess`, `checkpoint_final.pth` | 27.038 | 1.615 | **VALID — canonical reference** |
| `mishmar_hanegev_maoz_2_8p8um` (2nd specimen) | `Z:\Rony\mishmar_hanegev_maoz\2-16mm_diam_8.8um\` | 8.8 µm native → label-downsampled to ~15 µm | Full pipeline, confirmed | `i2_loess` (native-resolution) | plausible | plausible | **VALID** |
| `Cu011_samp_2` (3rd specimen) | `Z:\Rony\29.3.26 mishmar_hanegev_samp_2\` — `.log`-confirmed 822 slices, 1072×1072px | 15.000149 µm (log-confirmed) | Full pipeline confirmed via log | `i2_loess`, `checkpoint_final.pth` | 26.4 (plausible) | 0.120 (**collapsed**, 0.074× canonical) | **Pore VALID / POM INVALID** (channel collapse) — pore-only reuse OK (A2, Track E), never POM |
| `Cu011_samp_1` (4th specimen) | `Z:\Rony\29.3.26 mishmar_hanegev_samp_1\` — `.log`-confirmed 822 slices, 1072×1072px | 15.000149 µm (log-confirmed) | **Partial only** — NLM+crop exists for a 328/822-slice subset; full-height crop/norm200/NLM never run; only a 3-slice May-2026 bootstrap pseudo-annotation exists | — none run — | — | — | **UNPROCESSED for full-volume use.** Needs full-height crop → norm200 → NLM → `i2_loess`, same as `samp_2` |
| `Cu011_samp_3` (5th specimen) | `Z:\Rony\29.3.26 mishmar_hanegev_samp_3\` — `.log`-confirmed 837 slices, 860×860px | 15.000149 µm (log-confirmed) | **Partial only** — NLM+crop exists for a 623/837-slice subset; same bootstrap-only status as `samp_1` | — none run — | — | — | **UNPROCESSED for full-volume use.** Same pipeline needed as `samp_1` |

Derived from `mishmar_native` (same physical scan, nested here rather than as standalone rows):
- `mishmar_label_downsample` — majority-vote label downsample to ~15 µm. **VALID**, methodologically clean. Pore 26.108% / POM 1.614%. ("Mishmar sample 1" in `pom_replicate_comparison_prompt.md`.)
- ~~`mishmar_image_then_predict`~~ — image-downsample-then-fresh-inference branch. **Not a standalone catalog entry** per Rony's standing decision (Pore 25.632% / POM 0.856%, disagreed with `mishmar_label_downsample` by 54% — kept elsewhere only as a model-robustness finding).

`⚠ NEEDS RONY`: confirm whether `Cu011_samp_1`/`samp_3` should be run through the full pipeline (same treatment as `samp_2`) as the next step toward real Mishmar POM/pore replicates.

**2026-09-02/03 — Track E resolution-matching DONE.** The 3 valid Mishmar Track E specimens sat at 3 different voxel sizes, so no mean±SE could be computed across them. `track_e_correction_prompt.md` Part 2 downsampled `mishmar_native` (5.85→15.008µm) and `mishmar_hanegev_maoz_2_8p8um` (8.8→14.998µm) via the same majority-vote label downsample already validated for POM, reusing the existing ROI-expanded segmentations; `Cu011_samp_2` was already natively ~15.000µm. Both new downsampled runs passed both required sanity checks (χ-at-min-r match, volume back-calc). **Mean ± SE (n=3, matched ~15µm, physical replicates):** connectivity density 151.2±110.7 mm⁻³, Γ 0.9324±0.0018, DA 0.148±0.023, r* 133.3±42.4µm — full table in `track_e_correction_summary.md` (network drive). Voxel sizes are close but not bit-identical (15.008/14.998/15.000µm), flagged not hidden. Native-resolution numbers (5.85µm, 8.8µm) are kept on record separately as the resolution-sensitivity comparison, not folded into this mean. One new open item: the 8.8→15µm branch's tortuosity failed on all 3 axes with an AMG-solver library crash, now shown to be resolution-independent (also failed at the smaller downsampled node count) — a real upstream library issue worth a version check, not a scale problem.

---

## Rehovot (sand — binary pore/solid, no POM class) — 3 physical scans (2026-08-25 share sweep)

| Sample ID | Raw source (share) | Voxel size | Preprocessing | Model/checkpoint | Status |
|---|---|---|---|---|---|
| `Rehovot_samp1_highkV_Cu0.11_15um` (1st specimen) | `Z:\Rony\10.12.25 Rehovot\` — `.log`-confirmed 808 slices, 1276×1276px | 15.034357 µm (log-confirmed) | **None** — no crop/norm200/NLM/inference found anywhere on the share | — none run — | **UNPROCESSED — raw only.** An orphaned duplicate of the same raw slices also sits in `Z:\Rony\test\` — same physical sample, not a 4th scan |
| `Rehovot_samp2_highkV_Cu0.11_15um` (2nd specimen — canonical/most-used) | `Z:\Rony\10.12.25_Rehovot_samp_2\` — `.log`-confirmed 811 slices, 1236×1236px | 15.000149 µm (log-confirmed) | Full pipeline, cropped to 650³ | Both `multi_sample_fresh_bnei_reem_i4` and `i2_loess` run, cross-soil comparison | **VALID.** Used in A2 pore-PSD and Track E connectivity |
| `Rehovot_samp3_highkV_Cu0.11_15um` (3rd specimen) | `Z:\Rony\10.12.25_Rehovot_samp_3\` (original) superseded by `10.12.25_Rehovot_samp_3_clean\` (corrected re-reconstruction, 2026-08-04) — `.log`-confirmed 811 slices, 1236×1236px | 15.034357 µm (log-confirmed) | Full pipeline, cropped to 650³, built from the "clean" reconstruction | Both `multi_sample_fresh_bnei_reem_i4` and `i2_loess` run | **VALID.** Same dual-model setup as `samp2` |

This matches Rony's "2 active samples" — `samp1` is real but was never put through the pipeline, so it isn't one of the 2 in active use. `rehovot_inference_microsam_prompt.md` ("all Rehovot volumes") currently only covers `samp2`/`samp3`; `samp1` would need the full pipeline first.

---

## Known model branches (soil → training lineage)

- Bnei Re'em: `multi_sample_fresh_bnei_reem_i4` (trainer `nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss_lowlr`, `checkpoint_final.pth`)
- Mishmar HaNegev / Loess: `i2_loess` (same trainer family — confirm exact folder name when next touching this)
- Rehovot: no dedicated model found on the share — both Rehovot samples were run through the Bnei Re'em (`..._i4`) and Mishmar (`i2_loess`) branches for cross-soil comparison

## Change log

- 2026-08-24: catalog created.
- 2026-08-25: full-share inventory sweep (this repo's copy) — found `Cu011_samp_1`/`samp_3` (Mishmar, raw/bootstrap-only) and a third Rehovot specimen (`samp1`, never processed); flagged `bnei_reem_samp_2` (no dot) as a possible 3rd Bnei Re'em specimen or a misfiled copy of canonical's missing raw folder — left unresolved.
- 2026-08-25 → 08-27 (local-project-folder copy, separately): that copy accumulated a phantom-looking `bnei_reem_samp_2` row with contradictory notes across sessions, lost the Mishmar/Rehovot detail this sweep had, and never recorded storage locations — diverged from this file rather than building on it.
- **2026-08-28: merged.** Reconnected this repo, compared both copies. Rony confirmed directly: exactly 2 Bnei Re'em physical specimens (not 3) — `bnei_reem_samp_2` (no dot) and `bnei_reem_samp_2.0` are the same core under two names, despite the sweep finding them as separate raw folders with different voxel sizes (flagged above, unresolved technically, not blocking). `bnei_reem_samp_2`'s reconstruction (dated 2026-08-25 on the share) is the "this week" redo Rony mentioned — POM not recognized by the model there, pore/structure-only. Kept this file's superior Mishmar/Rehovot sections as the base. Going forward: this repo copy is canonical; the local project-folder copy is a mirror, updated to match.
- **2026-08-29:** added the analysis-tier policy — all valid-pore specimens are in scope for structural/topology metrics; only the Bnei Re'em canonical + both native Mishmar scans (5.85/8.8 µm) are in scope for POM-inclusive analysis. Per Rony, the `Z:\Rony\...` network-share copy of this file is out of scope and no longer tracked here.
- **2026-08-29 (corrections, same day, in order):** first wrongly collapsed `samp_2`/`samp_2.0` into one specimen (Bnei Re'em "2 total"). Rony corrected: they're two different physical cores (different voxel sizes because different scans) — so briefly went to "3 physical specimens" (canonical + samp_2.0 + samp_2, treating canonical as a third scan). Rony corrected again: canonical isn't a third scan at all, it's just the older of two reconstructions of the `samp_2` (no dot) core — confirmed via voxel-size match (canonical = 15.000149 µm = `samp_2`'s raw log; `samp_2.0`'s raw log is 15.034357 µm, different) and via canonical's `fresh_bnei_reem_i4` training lineage predating both Aug reconstructions by ~2 months. **Final: 2 physical specimens** — Specimen A (`samp_2` raw core, reconstructed twice: canonical + this week's redo) and Specimen B (`samp_2.0` raw core). Lesson: don't treat a working label like "canonical" as implying a distinct entity — verify what it actually refers to before building structure around it, and when a verbal count conflicts with sweep evidence, surface the conflict and ask rather than picking a side.
