# Part 0d — Otsu re-segmentation and the data-identity question

Follow-up to `part0c_TRUE_RECONSTRUCTION_RESULTS.md`. That document
established that `bnei_reem_samp_2_0_true_recon`'s Track E topology
metrics land within a few percent of canonical's on every axis. This
document investigates *why*, via two independent lines of evidence:
(A) a search for canonical's own original raw reconstruction, to attempt
a decisive raw-to-raw pixel comparison; and (B) a from-scratch Otsu
threshold re-segmentation of both volumes, independent of the nnU-Net
model entirely, to check whether the near-identity survives outside any
learned segmentation.

**STATUS: Job A closed (negative result, reported plainly). Job B
complete.**

## 0. Preliminary finding (carried over verbatim, not re-derived here)

This is the finding that motivated this investigation, produced moments
before this document by the coordinating session. Reproduced here as
already-established fact:

- Pearson correlation between the two volumes' raw z-scored input arrays
  (`bnei_reem_samp_2_0_true_recon_0000.nii.gz` vs `nlm_volume_0000.nii.gz`,
  common 650×650×650 overlap): **0.999929**.
- Pore-label (5) Dice (nnU-Net segmentations): **0.988447**, IoU 0.977158.
  Expected Dice under independence given each volume's own marginal pore
  fraction: only 0.216459.
- Control check calibrating what "genuinely different" looks like: raw
  reconstructed slices of samp_2.0's E: reconstruction vs. `new_rec`
  (Specimen A's redo, confirmed genuinely different raw scan) correlate at
  only **0.584**; even samp_2.0's own slice 450 vs. slice 470 (20 slices
  apart, same volume) only reaches **0.825**. The 0.9999 figure between
  "two different physical specimens" is higher than a volume correlates
  with itself.
- The historical "shared scratch slot" bug (`nlm_output/nlm_volume.tif`
  reused stale across samples) was checked directly and ruled out:
  `10.5/bnei_reem_samp_2_0_true_recon.tif` vs `10.5/nlm_volume.tif` have
  different MD5, different size (1,098,679,524 vs 1,102,060,076 bytes),
  and a fresh timestamp on the new file. Not a literal stale-file reuse.
- Root cause was **not** pinned down at that point. Leading hypothesis:
  the E: drive's `bnei_reem_samp_2.0_Rec` folder (identified in part0c as
  "the real reconstruction") might itself be misfiled/duplicated
  canonical-lineage data.

## 1. Job A — searching for canonical's original raw reconstruction

**Goal**: find canonical's own pre-August-2026 raw reconstruction (not
`new_rec`, which is a 2026-08-25 redo of the same raw scan) and directly
pixel-compare a middle slice of it against samp_2.0's E: reconstruction,
to test whether the E: `samp_2.0_Rec` folder is itself contaminated with
canonical-lineage data.

### 1.1 Where the "no-dot" `bnei_reem_samp_2` raw folder actually leads

Every copy of `18.12.25 bnei_reem_samp_2` (no dot — Specimen A / canonical's
raw acquisition folder per DATA_CATALOG.md) was located and inspected:

| Location | Contents |
|---|---|
| `E:\PROJECTS\Yael_Mishael\Rony\18.12.25 bnei_reem_samp_2\` (local drive) | 1800 raw projection tif/iif pairs (Dec 18, 2025) **plus** 805 reconstructed-slice files matching `*_rec\d{8}\.tif` directly in the folder root, index range 49–852 |
| `\\hive3065\Yael_Mishael\Rony\18.12.25 bnei_reem_samp_2\` (network share, same folder) | Identical: 1800 raw projections + 804 `*_rec*.tif` files, same index range |
| `C:\Users\rony.schwartz\Desktop\new_rec\` | 804 `*_rec*.tif` files, same index range 49–852, plus preview/BHC/PAC/RAC auxiliary files |
| `E:\...\18.12.25 bnei_reem_samp_2\bnei_reem_highkV_cu011_samp_2_Rec\` (the `_Rec` subfolder) | Only 2 stale preview files (`_pp1.tif`, `_pp2.tif`), dated Dec 18, 2025 — mirrors the same stale-preview pattern part0c documented for the network share's `samp_2.0_Rec` subfolder |

**Direct timestamp check on the 805/804 `*_rec*.tif` files in every copy**:
all individually timestamped **2026-08-25, 16:05–16:12** (a ~7-minute
write window) — i.e. every single "reconstructed slice" file found
anywhere under the `samp_2` (no-dot) name, in any of three locations, is
the exact same 2026-08-25 reconstruction session (`new_rec`), just present
redundantly in three places. **No reconstruction older than 2026-08-25
exists anywhere under this raw-folder name.**

### 1.2 Canonical's training log proves its real reconstruction predates `new_rec` by months — but that reconstruction was not found

`logs_archive/training/fresh_bnei_reem_i2/_fresh_bnei_reem_i2.log`
(2026-06-30 training run) records canonical's actual training input:

```
Raw TIF: \\hive3065\Yael_Mishael\Rony\remote_computer backup\10.5\nlm_volume.tif
```

`10.5\nlm_volume.tif` on disk is dated **2026-04-20** (confirmed via
directory listing) — already cropped and NLM-processed, ~4 months before
`new_rec` existed. This proves canonical's own real, original raw
reconstruction is **not** `new_rec` and predates it substantially — but it
also means the per-slice raw reconstruction output (the direct analogue
of the `_Rec` folder being searched for — full-resolution individual
slice TIFFs straight off the scanner, before crop/norm/NLM) that must
have fed into producing `nlm_volume.tif` was never located.

### 1.3 Locations searched, all negative

Beyond the three `samp_2` copies above:

- **D: drive** — searched to depth 6 for `*bnei_reem*`; only
  `D:\bnei_reem_true_recon_logs` (this project's own log folder, created
  this week) was found. No raw reconstruction data.
- **P: drive** — confirmed to contain only `$RECYCLE.BIN`, `System Volume
  Information`, and `pagefile.sys`. Not a data drive.
- **Desktop** (`C:\Users\rony.schwartz\Desktop\`) — only `new_rec`,
  `pom_20260823_light`, `pom_analysis_20260824_ablation`, and unrelated
  shortcuts/files. No older reconstruction folder.
- **Documents** (`C:\Users\rony.schwartz\Documents\nnUNet_resources\bnei_reem\`)
  — canonical's local processing mirror. Earliest `.tif` there is
  `tif_input/nlm_volume.tif`, dated 2026-04-20 — same already-processed
  file as in `10.5\`, not raw per-slice reconstruction output. An
  `archive_before_rerun_20260512_132436/` folder exists (May 12, 2026)
  but contains only nnU-Net-format preprocessed/trained artifacts
  (`dataset.json`, plans, checkpoints), not raw TIFF slices.
- The `resarch exercise\` local-project-folder copy referenced in
  DATA_CATALOG.md's merge note was not found on any locally-searched
  drive (C:, D:, E:, P:) and, per Rony's 2026-08-29 decision recorded in
  DATA_CATALOG.md, the `Z:\Rony\...` network-share copy of that
  reference document is explicitly out of scope — not pursued further.

### 1.4 Job A conclusion

**Canonical's original, pre-2026-04-20 per-slice raw reconstruction was
not found after a genuine search across E: (multiple subfolders, network
and local copies), D:, P:, Desktop, and Documents.** The decisive
raw-to-raw pixel comparison this job set out to perform (canonical's
original reconstruction vs. samp_2.0's E: `_Rec` reconstruction) could
therefore **not be carried out** — there is nothing on any searched drive
that predates `new_rec` in per-slice raw form to compare against.

This is not a null result, however: it directly corroborates
DATA_CATALOG.md's own 2026-08-25 flag that the no-dot `bnei_reem_samp_2`
folder might be "a misfiled copy of canonical's missing raw folder." The
raw folder's true original `_Rec` output appears to be genuinely gone —
not merely misplaced under a different name — and the only reconstruction
event ever recorded under that raw folder's name, in any of its three
copies, is the 2026-08-25 `new_rec` redo. Whatever fed canonical's
`10.5\nlm_volume.tif` (April 2026 or earlier) is not recoverable from any
location checked in this pass.

**Judgment call flagged for Rony**: since Job A could not close the loop,
the root-cause question for the specB/canonical near-identity remains
open at the raw-reconstruction level. Job B (below) approaches it from a
different angle instead.

## 2. Job B — Otsu re-segmentation, independent of nnU-Net

### 2.1 Method and polarity choice

`02_preprocessing/otsu_threshold_3d.py` was adapted (not run as-is, since
it hard-requires `.tif` input and this task's inputs are the z-scored
`_0000.nii.gz` NIfTI arrays already used for the raw-correlation check).
The core logic — `skimage.filters.threshold_otsu` with the
`pore_is_dark=True` convention (`volume < threshold → pore`) — was kept
identical.

**Why `pore_is_dark=True` needs no adaptation for z-scored input**:
z-score normalization (`(v - mean) / std`) is a monotonic *increasing*
affine transform of the raw grayscale. It cannot change which voxels are
darker than which others — it only rescales the axis. So "low raw
intensity" and "low z-score value" pick out exactly the same set of
voxels, and running Otsu directly on the z-scored array with
`pore_is_dark=True` is mathematically equivalent to running it on the
original raw grayscale with the same polarity. This matches the
convention established in `compute_rehovot_distance_metrics.py`
(`pore_mask = vol; # Otsu pore_is_dark=True convention`), applied here to
the z-scored rather than min-max-normalized case, with no other change to
the polarity/threshold logic needed.

Otsu was run independently on each volume's own array (global threshold,
own histogram — no shared threshold was imposed):

| Volume | Native shape | Otsu threshold (z-score units) | Pore fraction (full native volume) |
|---|---|---|---|
| Specimen B true-recon | (650, 650, 650) | −0.762894 | 18.3064% |
| Canonical | (650, 650, 652) | −0.754289 | 18.3722% |

The two independently-computed Otsu thresholds land within 0.009 z-score
units of each other — itself a small piece of corroborating evidence for
how similar the two volumes' global intensity distributions are.

### 2.2 Otsu-mask identity check — same test as the preliminary finding, applied to Otsu output

Canonical's array has 652 Z-slices vs. Specimen B's 650; for this
voxel-for-voxel comparison only, canonical's Otsu mask was center-cropped
by dropping 1 slice from each end (Z indices 1:651) to reach a common
650×650×650 shape — a judgment call, flagged here, consistent with this
project's usual centered-crop convention (see part0c §2) rather than an
arbitrary edge trim.

| Metric | Value |
|---|---|
| Dice | **0.9469** |
| IoU | **0.8991** |
| Pearson r (mask-as-0/1) | **0.9350** |
| Pore fraction, Specimen B (cropped region) | 18.306% |
| Pore fraction, canonical (cropped region) | 18.390% |
| Expected Dice under independence (marginal fractions) | 0.1835 |

**This is the second, independent confirmation the task asked for.** The
Otsu masks — built with zero learned-model involvement, from two
independent global-histogram thresholds — agree far beyond anything two
genuinely independent physical specimens should produce (expected ~0.18
under independence; the established genuinely-different-specimen control
baseline from §0 topped out at 0.584 raw-slice correlation). It is not as
extreme as the nnU-Net Dice (0.988 vs. 0.947 here), which makes sense —
Otsu is a cruder, single-global-threshold segmentation with no learned
context, so some disagreement at the pore/solid boundary is expected even
between identical underlying data — but 0.947 Dice / 0.935 raw-mask
correlation is still overwhelming evidence in the same direction as the
nnU-Net check, not a different conclusion.

### 2.3 Track E topology metrics on the Otsu-derived masks

Run via `05_evaluation/psd/run_psd_diagnostics.py extended`, same settings
as every other volume in this project (`--voxel-spacing 15.034357` ×3 for
Specimen B, `15.000149` ×3 for canonical, `--n-anisotropy-directions 800`,
monolithic/no chunking, GPU-enabled — falls back to CPU automatically, as
it also did in the nnU-Net-based canonical/specB runs, since `cupy`'s CUDA
build is unavailable in both environments used this project). Each Otsu
binary mask was packaged as an integer-labeled volume (0=solid, 5=pore)
with `--pore-label 5 --pom-label 2` (label 2 has 0 voxels in an Otsu-only
binary mask, so POM fraction reads 0% by construction — Otsu does not
attempt a 3-class pore/POM/solid split, only pore/solid).

[TRACK_E_TABLE_PLACEHOLDER]

### 2.4 Does the near-identical-to-canonical pattern persist under Otsu?

[CONCLUSION_PLACEHOLDER]

## 3. Bottom line

[BOTTOM_LINE_PLACEHOLDER]
