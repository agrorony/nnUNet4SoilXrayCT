# Data Catalog — CT scans, segmentations, and validity

> Single source of truth for what scans exist, where, and their processing/validity status. Update this whenever a new scan is found, processed, or its validity is reassessed. Prompts should read this before doing their own rediscovery.
>
> **2026-08-28 merge note:** Two versions of this file had diverged — a local-project-folder copy (rebuilt 2026-08-27/28 from scratch after a phantom-row problem) and this repo's own copy (a careful full-share inventory sweep from 2026-08-25, with `.log`-confirmed voxel sizes and raw-source paths). This version merges them: the 2026-08-25 sweep's Mishmar and Rehovot sections are the better evidence and are kept close to as-is; the Bnei Re'em section is corrected per Rony's direct confirmation (2026-08-28) that there are **2** physical specimens, not 3 — see the note under that section for the unresolved technical wrinkle this creates.
>
> **One file, one location going forward:** this repo (`nnUNet4SoilXrayCT`, local git clone) is the canonical location for this file. The local project folder (`resarch exercise\`) keeps a copy for quick reference but should be treated as a mirror, not a second source of truth — update this one first, then copy over. Per Rony (2026-08-29): the `Z:\Rony\...` network-share copy is **not in scope** and should be disregarded going forward — this repo location is the only one that matters.

## Analysis-tier policy (Rony, 2026-08-29)

- **Structural/topology metrics (pore-only: χ, connectivity density, Γ, DA, tortuosity, PSD, etc.):** every physical specimen listed below that has a valid pore channel is in scope, regardless of its POM status. This includes specimens excluded from POM work (e.g. `Cu011_samp_2`, Bnei Re'em Specimen 2) — POM invalidity does not disqualify pore/structure use.
- **POM-inclusive analysis (Track A/B, 3-class matrix/POM/pore work):** restricted to exactly 3 volumes — Bnei Re'em canonical (`bnei_reem_fresh_bnei_reem_i4`), Mishmar `mishmar_hanegev_maoz_3_5p85um` (5.85 µm), and Mishmar `mishmar_hanegev_maoz_2_8p8um` (8.8 µm). No other volume — regardless of future processing status — enters POM analysis unless Rony explicitly adds it here.

## Inclusion rule (unchanged, 2026-08-24)

A sample is **excluded** only for one of these concrete reasons:
1. **Channel collapse** — a phase's voxel fraction crashes toward zero (e.g. POM <0.3%) while the other phase(s) stay in a normal range. This is the fingerprint of the model failing to recognize a class, not a real soil difference (seen in `Cu011_samp_2`).
2. **Known unfixed preprocessing defect** — e.g. missing center-crop, wrong model/checkpoint — until corrected.
3. **Wrong model/checkpoint used** for the soil (verified against the driver script + inference log, not assumed).

A sample is **NOT** excluded merely for differing in magnitude from another sample of the same soil — different physical specimens can genuinely differ. Magnitude differences get a note, not an exclusion.

---

## Bnei Re'em (Vertisol) — 2 physical specimens (Rony confirmed 2026-08-28)

### Specimen 1 — canonical
| | |
|---|---|
| Sample ID | `bnei_reem_fresh_bnei_reem_i4` |
| Raw source | Not present on the share as a standalone acquisition folder — only the derived NLM volume (`10.5\nlm_volume.tif`) and annotation iterations survive |
| Voxel size | 15.000149 µm |
| Preprocessing | Full pipeline (stack → crop 650³ → norm200 → NLM) — confirmed complete |
| Model/checkpoint | `multi_sample_fresh_bnei_reem_i4`, `checkpoint_final.pth` |
| Pore % / POM % | 21.636 / 0.819 |
| Status | **VALID — canonical reference**, used in every comparison as "Bnei Re'em" |
| Location | `Z:\Rony\remote_computer backup\nnUNet_resources\bnei_reem_fresh_bnei_reem_i4\inference_concatenated\nlm_volume.nii.gz` |

### Specimen 2 — second physical core, three processing/naming passes of the *same* scan
Rony confirmed (2026-08-28) this is one specimen that got inconsistently named `samp_2` and `samp_2.0` across sessions — **not** two separate cores.

**Open technical wrinkle, not yet explained:** the 2026-08-25 share sweep found `18.12.25 bnei_reem_samp_2\` and `18.12.25 bnei_reem_samp_2.0\` as two separate raw folders on `Z:\Rony\`, each with a full ~1800-slice stack, but different instrument-logged voxel sizes (15.000149 µm vs 15.034357 µm) — and the two reconstructions show different POM failure modes (samp_2's redo: POM not recognized at all; samp_2.0's redo: POM elevated but not collapsed). Per Rony this is still one physical core, so the voxel-size/dual-raw-folder difference needs an explanation at some point (duplicate/backup raw folder? a `.log` typo? a re-scan of the same core logged slightly differently?) — flagged for whenever it's convenient to check, not blocking.

| | `bnei_reem_samp_2_0` | `bnei_reem_samp_2_0_recropped` | `bnei_reem_samp_2` (no dot) → `bnei_reem_samp_2_rec_recropped` |
|---|---|---|---|
| Raw source | `Z:\Rony\18.12.25 bnei_reem_samp_2.0\` | (same raw source, recropped) | `Z:\Rony\18.12.25 bnei_reem_samp_2\` |
| Processed file | `10.5\bnei_reem_samp_2_0.tif` (Aug 4) | `10.5\bnei_reem_samp_2_0_recropped.tif` (Aug 24) | `10.5\bnei_reem_samp_2_rec_recropped.tif` (Aug 25 — this week's reconstruction) |
| Preprocessing | Crop step skipped (driver bug) — raw→NLM→tif_direct | Full pipeline re-run correctly (drop 12 stray SkyScan preview TIFFs, crop 650³, norm200, NLM) | Full pipeline, freshly reconstructed |
| Pore % / POM % | ~39.4 / ~11.0 | 28.3 / 7.62 (elevated, not collapsed) | Not yet computed — no summary metrics on the share for this pass |
| Status | **SUPERSEDED** — kept for traceability | Prior "current" pass; 2026-08-26 Rony decided not to pursue this pass further for POM (settled on Bnei Re'em n=1 for POM) | **CURRENT reconstruction.** Model does not recognize POM here (per Rony) — **valid for structure/pore-only work; not usable for POM/3-class analysis** |
| Location | `Z:\Rony\remote_computer backup\nnUNet_resources\bnei_reem_samp_2_0\` | `...\bnei_reem_samp_2_0_recropped\` | `...\bnei_reem_samp_2_rec_recropped\` |

Bnei Re'em POM work remains **n=1** (canonical only). Specimen 2 (any pass) is usable for 2-class pore/solid work only (A2, Track E connectivity).

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
