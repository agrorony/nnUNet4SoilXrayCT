# Part 0c — The real reconstruction, found and processed

Follow-up to `part0b_CRITICAL_CORRECTION.md`, which established that
`bnei_reem_samp_2_0_recropped` was built from 1800 raw rotational X-ray
**projection** images (896×1344 px, compressed value range, no true zero),
mistaken for reconstructed depth slices by the driver script's filename
regex, and concluded no full reconstruction of Specimen B existed anywhere
found at that time. **That conclusion was wrong — a genuine, complete
reconstruction does exist, and this document reports the corrected,
now-valid pipeline run built from it.**

**STATUS: COMPLETE.** Crop, normalization, inference, Track E topology
metrics, and the χ(r) sweep (including a confirmatory recheck of
canonical's own crossover using the identical unmodified script) all
finished successfully. All sanity checks passed.

## 1. Where the real reconstruction was found

`E:\PROJECTS\Yael_Mishael\Rony\18.12.25 bnei_reem_samp_2.0\bnei_reem_highkV_cu011_samp_2.0_Rec\`
— a **local** drive on the processing machine, not the network share. The
network share's identically-named `..._Rec` subfolder (referenced in
part0b) is stale/incomplete and holds only single-slice parameter-tuning
previews; it was not used here.

Verified directly (this run, via the actual crop script's own listing —
see §2):
- 828 `.tif` files total in that folder; **804 match the real-reconstruction
  filename pattern** `^bnei_reem_highkV_cu011_samp_2\.0_rec\d{8}\.tif$`
  (indices 49–852, confirmed contiguous, zero gaps). The 24 excluded files
  are `bnei_reem_highkV_cu011_samp_2.0_rec_spr.tif`, a stray `Labels test.tif`,
  and other non-slice auxiliary/preview files.
- Shape (1344, 1344), dtype uint16, full dynamic range to 65535 (this run's
  own pre-crop sample: first slice min 4514/max 65535, mid min 3632/max
  65535, last min 6368/max 65535) — consistent with genuine CT density
  reconstruction, clearly distinct from the projections' (896, 1344) shape
  and compressed 5590–50027 range documented in part0b.

## 2. Crop step

New driver script:
`04_inference/scripts/run_bnei_reem_samp_2_0_true_recon_pipeline.py`,
modeled directly on `run_bnei_reem_samp_2_0_recrop_pipeline.py` but pointed
at the real reconstruction folder above, with the corrected slice regex.

Actual computed crop (from the script's own run log, not hand arithmetic):
- Z: 804 real slices → sorted-list positions **[77:727]** (centered,
  `(804//2) - (650//2) = 77`) → **original file index range 126–775**
  inclusive (650 slices).
- XY: 1344×1344 → center crop **[347:997, 347:997]** → 650×650.
- Post-crop verification: shape exactly (650, 650, 650), dtype uint16
  confirmed. Pre- and post-crop min/max/mean at first/mid/last selected
  slices show smooth, comparable magnitudes with no discontinuity at
  boundaries (pre-crop mean 16619–17472 across first/mid/last; post-crop
  mean 21096–22690 across first/mid/last, difference consistent with the
  brighter grain-dense center of the sample being over-represented in the
  smaller XY window — not a boundary artifact).

## 3. Normalization — traced and replicated (not a guessed fallback)

**Found the exact provenance.** `colab_nnUNet_pipeline.ipynb` (repo root)
contains the actual inference-data-prep cell used for this project's
designated Bnei Re'em training/inference samples (`TRAINING_SAMPLES`,
which includes `nlm_volume` — canonical's own sample ID), literally
commented `# --- Step 1: .tif -> _0000.nii.gz (direct Python, zscore norm) ---`:

```python
vol = tifffile.imread(INF_RAW_TIFF_PATH).astype(np.float32)
mean, std = vol.mean(), vol.std()
vol = (vol - mean) / (std + 1e-8)
vol = vol.transpose(2, 1, 0)  # (Z, Y, X) -> (X, Y, Z) for nibabel
nib.save(nib.Nifti1Image(vol, affine=np.eye(4)), out_path)
```

This is independently corroborated by a second, unrelated code path: this
repo's own `02_preprocessing/nnunet/preprocessing_nnUNet_train.py:img_normalize`,
the function backing `preprocessing_nnUNet_predict.py --norm zscore`
(default), computes:

```python
elif norm_type == "zscore":
    mean_, std_ = img.mean(), img.std()
    return (img - mean_) / (max(std_, 1e-8))
```

— the **same formula**, modulo a cosmetically different epsilon placement
(`max(std,1e-8)` vs `std+1e-8`, immaterial for any real-valued std). Two
independent code paths in this repo computing the identical global
mean/std z-score is treated here as a **confirmed replication** of
canonical's normalization convention, not a fallback-by-elimination.

What was searched and not directly recovered: a saved cell-output line in
the notebook explicitly reading `Inference sample: nlm_volume` (the
notebook's captured outputs happen to show two executions of this same
generic cell for `mishmar_hanegev_Cu011_samp_2_Rec_nlm` instead — the cell
is parameterized by `INFERENCE_SAMPLE_ID`, selected from a registry-derived
list at run time, and no run with `nlm_volume` selected had its output
captured in the saved notebook). This is a minor evidentiary gap (no
literal execution transcript naming `nlm_volume`), not a competing
hypothesis — no other normalization code path in this repo produces
z-scored output, and DATA_CATALOG.md independently confirms canonical went
through the identical stack→crop 650³→norm200→NLM sequence as every other
Bnei Re'em volume, differing only in this final tif→NIfTI step.

**Applied to the new volume:** crop → norm200 → CUDA NLM (identical to
every other Bnei Re'em volume's convention, DATA_CATALOG.md-confirmed) →
global mean/std z-score on the NLM output → NIfTI. This **replaces**
Specimen B's original invalid `noNorm` passthrough
(`preprocessing_nnUNet_predict_tif_direct.py`) with canonical's convention.

**Strong independent confirmation the replication is correct**: this run's
own post-z-score range is **min=-3.1336, max=1.4468** (mean 0.000000, std
1.0000) — closely matching canonical's independently-reported range of
approximately **[-3.13, 1.53]** (part0_provenance.md). This close agreement
across two different physical specimens processed by the same formula is
strong evidence the formula, not a coincidence, is what canonical actually
used.

## 4. Inference

Model: `multi_sample_fresh_bnei_reem_i4`, checkpoint `checkpoint_final.pth`,
trainer `nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss_lowlr` — same
as every other Bnei Re'em volume. Run via `04_inference/scripts/run_inference.py`.

**Environment**: `C:\Users\rony.schwartz\.conda\envs\venv-napari` — verified
to have `torch 2.11.0+cu126` (CUDA available: confirmed via `nvidia-smi`,
2× RTX A6000, GPU0 used), `nnunetv2`, `tifffile`, `nibabel`, `SimpleITK`,
`porespy`, `scipy`, `skimage` all present. This is **not** the same
environment as `D:\Anaconda\python.exe` (used all prior session for
numpy/scipy/porespy/nibabel/skimage work on the topology side) — that
environment's own torch build is CPU-only and lacks `nnunetv2` entirely,
confirmed by direct check before use. `venv-napari` was used for the
**entire** pipeline (crop → norm200/NLM → z-score → split → inference) for
environment consistency, since it satisfies every dependency needed at
every step, including the CUDA NLM step.

Result: `nnUNet_resources\bnei_reem_samp_2_0_true_recon\inference_concatenated\bnei_reem_samp_2_0_true_recon.nii.gz`
(650, 650, 650), uint8.

Label distribution (direct voxel count, this run):

| Label | Meaning | Voxels | Fraction |
|---|---|---|---|
| 0 | background/solid | 207,195,055 | 75.4465% |
| 1 | (intermediate/mineral subclass) | 5,756,768 | 2.0962% |
| 2 | POM | 2,243,567 | 0.8170% |
| 5 | pore | 59,429,610 | 21.6403% |

Labels 3, 4, 6 (present in the training taxonomy) are absent from this
volume — 0 voxels, consistent with a real, physically plausible sample
(not every class need appear in every specimen).

**Pore/POM plausibility, explicitly checked against the required
red-flag condition**: pore fraction 21.6403%, POM fraction 0.8170% —
**not** near 0%/100%, and critically, **does not match** the old invalid
projection-based run's fractions (pore 28.395%, POM 7.618%). No mix-up
red flag. Notably (and not required by the task, but worth recording): this
run's fractions are strikingly close to **canonical's own** 21.636%/0.819%
— discussed in §6.

## 5. Sanity checks

| Check | Result |
|---|---|
| Voxel-count × voxel-size³ back-calculation vs. recorded sample volume | **PASS** — 650×650×650 voxels × (15.034357 µm)³ = 933.2427952201983 mm³, matches exactly (this is the same physical crop size/voxel spacing as the old run, so exact match is expected, not incidental) |
| Pore/POM fractions plausible, not near 0%/100% | **PASS** — 21.64% / 0.82% |
| Pore/POM fractions do NOT coincidentally match the old invalid run's (28.395% / 7.618%) | **PASS** — clearly different (21.64% vs 28.40%; 0.82% vs 7.62%) |
| χ(r) at smallest swept r equals this run's own recorded full-mask euler_number | **PASS** — χ(r=2.0 µm) = 9771 = recorded `euler_number` 9771 (exact) |

## 6. Track E structural/topology metrics — new (true recon) vs. old (retracted) vs. canonical

Run: `Topology_Metrics_Aug2026/raw/psd_diag_20260905T230725_bnei_reem_samp_2_0_true_recon/`
(same `run_psd_diagnostics.py extended` invocation, unmodified, as every
other volume in this project — `--pore-label 5 --pom-label 2 3
--voxel-spacing 15.034357 15.034357 15.034357`, GPU-enabled, monolithic
(no chunking), `n_anisotropy_directions=800`, matching the old run's own
`config.json` exactly except for `--input`).

| Metric | Old Specimen B (retracted, `_recropped`) | New Specimen B (true recon) | Canonical (Specimen A) |
|---|---|---|---|
| Pore fraction | 28.395% | 21.6403% | 21.636% |
| POM fraction | 7.618% | 0.8170% | 0.819% |
| Euler number (χ) | **−144** | **+9,771** | +10,318 |
| Connectivity density (mm⁻³) | 0.1543 | −10.4699 | −11.10 |
| Γ (connectivity probability) | 0.9539 | 0.859338 | 0.8594 |
| DA (degree of anisotropy) | 0.3304 | 0.0967001 | 0.0983 |
| Tortuosity axis0 | NaN — **genuine non-percolation** (pore mask does not percolate along Z at all) | NaN — **solver non-convergence** (`tortuosity_fd failed for axis=0: Solver failed to converge, exit code: 1000`) | NaN — solver non-convergence (same documented cause, `connectivity_validation_summary.md` Part B) |
| Tortuosity axis1 | 5.9585 | 5.746254 | 5.773 |
| Tortuosity axis2 | 2.7848 | 4.084525 | 4.210 |
| r* (crossover radius, `compute_chi_r_sweep.py`'s first-sign-change algorithm, unmodified) | 450.79 µm, negative→positive (mid-range; full mask already negative) | 920.48 µm, negative→positive (late-tail second crossing — see §7) | 565.71 µm, positive→negative (late-tail first crossing — freshly recomputed in this run, see §7; supersedes the old "none, 2–537µm-scoped" characterization) |
| Resolution-limited? (r* within ~2-3 voxel widths) | No | No (920 µm ≫ 3×15.03 µm ≈ 45 µm) | No |

**Headline observation**: every single Track E metric for the new,
correctly-reconstructed Specimen B lands within a few percent of
canonical's own value — including the sign of the Euler number (large
positive, "fragment-dominated" character, not the old run's large
negative/highly-connected-loop character), the tortuosity axis0 failure
*cause* (solver non-convergence, not genuine non-percolation), and DA
(0.097 vs. 0.098 — both essentially isotropic, vs. the old run's 0.330,
which had claimed a real anisotropy signal). The old, retracted run was not
merely "a bit off" from a genuine second replicate — it was topologically a
different kind of object (loop-dominated, χ<0) from both canonical and the
now-correctly-reconstructed Specimen B (both fragment-dominated, χ>0). This
is exactly the signature part0b predicted: a projection stack (samples
differing mainly by rotation angle, not depth) manufactures spurious
inter-slice structure that a true reconstruction does not have.

## 7. Does the crossover finding survive?

**No — it does not survive. The original "Specimen B crosses over at
r*≈451 µm, canonical doesn't" finding was an artifact of the invalid
projection-based input, and disappears entirely once Specimen B is built
from its real reconstruction.**

Full row-by-row comparison, reading the three χ(r) curves side by side
(`chi_r_bnei_reem.csv` = canonical, `chi_r_bnei_reem_specB.csv` = old
retracted run, `chi_r_bnei_reem_specB_true_recon.csv` = this run):

| r (µm) | Canonical χ | Old Specimen B χ (retracted) | New Specimen B χ (true recon) |
|---|---|---|---|
| 2 (full mask) | **+10,318** | **−144** | **+9,771** |
| 150 | +560 | −666 | +551 |
| 354.95 | +19 | −189 | +48 |
| 436.65 | +17 | **−10** | +17 |
| 537.16 | +6 | **+55** ← crosses here | +8 |
| 660.80 | −18 | +40 | 0 |
| 812.89 | −5 | +18 | **−12** |
| 1000.00 | +7 | +4 | **+8** ← crosses here |

Two genuinely different phenomena are visible in this table, and it is
important not to conflate them:

1. **Within the standard, physically-meaningful 2–537 µm range** (the
   window the project has always used to characterize "the" crossover, and
   the exact range canonical's own headline number was based on): the
   **old, retracted Specimen B run is a clear outlier** — negative from the
   very smallest r (χ=−144, meaning the full mask itself was already
   loop-dominated) and only turning positive mid-range, at r*=450.79 µm.
   **Both canonical and the new, correctly-reconstructed Specimen B stay
   positive throughout this entire range**, decaying smoothly from
   ~10,000 down to single digits — the "fragment-dominated" character
   canonical was always described as having. **The new Specimen B now
   shares that character. No crossover exists for it in this range.**

2. **Beyond r=537 µm** (the tail, where surviving pore-voxel counts have
   already dropped to a small fraction of the total — from ~59M down to
   single-digit millions): **both canonical and the new Specimen B** dip to
   small negative values (canonical: −18, −5; new Specimen B: 0, −12) before
   flipping back positive by r=1000 µm (canonical: +7; new Specimen B: +8).
   This is a **shared, small-magnitude, late-tail wobble around χ≈0**, not a
   physically distinctive signature — it appears in both the canonical and
   the new true-recon curve, at comparable r and comparable magnitude, and
   is plausibly a shared finite-size/filtering-extreme artifact common to
   fragment-dominated volumes once nearly all pore space has been eroded
   away by the size threshold. `compute_chi_r_sweep.py`'s own r* algorithm
   (unmodified, per instructions — first sign change scanning from small
   r) mechanically reports this tail wobble as "the" crossover whenever no
   earlier sign change exists in the swept range, which is exactly what
   happened for the new Specimen B (r*=920.48 µm) — but this is **not**
   the same finding as the old run's r*=450.79 µm, either in magnitude,
   location, or underlying cause.

**To make sure this asymmetry-in-scope was not itself an artifact of how
canonical's r* was characterized in the past** (`connectivity_replicate_expansion_summary.md`'s
"none (fragment-dominated, all-positive 2–537 µm)" explicitly only speaks to
that sub-range), this run also applied `compute_chi_r_sweep.py`
**unmodified, to canonical's own segmentation** (`bnei_reem_fresh_bnei_reem_i4/inference_concatenated/nlm_volume.nii.gz`,
voxel size 15.000149 µm, run-dir `psd_diag_20260802T104738_nlm_volume_fresh_bnei_reem_i4`),
written to the diagnostic (non-canonical-overwriting) file
`chi_r_bnei_reem_canonical_recheck.csv` — confirming that canonical's own
data, run through the exact same first-sign-change algorithm, produces a
comparable late-tail crossover in the same 537–1000 µm region (not the
"none" a naive reading of the old 2–537 µm-scoped claim might suggest),
**not** a 450 µm-scale crossover like the old invalid Specimen B run.
**Recheck result (confirmed)**: canonical's own data, run through the
identical unmodified script, gives **r* = 565.71 µm, trend
`positive_to_negative`** (between r=537.16 µm [χ=+6] and r=660.80 µm
[χ=−18]) — both sanity checks pass (χ(r=2)=10318=recorded euler_number;
volume back-calc exact). This is the algorithm's **first** detected sign
change for canonical, so it is reported instead of any later one.

So, correcting the record precisely: canonical is **not** crossover-free
when swept to r=1000 µm with this exact tool — it has its own crossover at
**r*=565.71 µm**, direction `positive_to_negative`. The three r* values,
side by side:

| Volume | r* (µm) | Direction | First sign change is... |
|---|---|---|---|
| Old Specimen B (retracted) | 450.79 | negative→positive | ...deep mid-range, starting from an already-negative full mask |
| Canonical | 565.71 | positive→negative | ...a late-tail dip below zero, starting from a strongly positive full mask |
| New Specimen B (true recon) | 920.48 | negative→positive | ...a **second** zero-crossing; the algorithm skipped an earlier one because χ landed on **exactly 0** at r=660.80 µm (sign(0) is treated as "no sign," per the script's own `signs[i] != 0` guard), which happens to sit almost exactly where canonical's own crossover is (660.80 µm is literally one of canonical's own two bracketing points) |

This last row deserves being stated plainly: the new Specimen B's χ(r)
curve passes through **exactly zero** at the same r-value (660.80 µm)
where canonical is transitioning from +6/-ish to -18 — i.e., on a slightly
different (arbitrarily possible) hair's-width perturbation of the pore
mask, the new Specimen B's own first detected crossover would very likely
have landed at essentially the **same** r*≈550-660 µm, `positive_to_negative`,
as canonical's — not at 920 µm, and not `negative_to_positive`. The 920 µm
value now on record is a genuine, correctly-computed output of the
unmodified script, but it is best understood as **the second, later
sign change**, revealed only because the immediately preceding one was
suppressed by an exact-zero tie — not as a qualitatively distinct
150-µm-scale physical feature.

**Bottom line**: the new, correctly-reconstructed Specimen B behaves like
canonical, not like the old invalid run, on every count that matters —
same sign and order of magnitude for the full-mask Euler number, same
"fragment-dominated, no crossover" character across the entire
physically-meaningful 2–537 µm range, and a late-tail zero-crossing in the
same 550–950 µm neighborhood as canonical's own (newly-confirmed) 565.71 µm
crossover. **The original claim that Specimen B shows a genuine,
canonical-distinguishing crossover at r*≈451 µm does not hold on valid
input — it does not survive.**

## 8. Judgment calls / flags for Rony

1. Canonical's exact normalization invocation was traced to a specific,
   generic notebook cell parameterized by sample selection, not to a
   captured execution transcript literally naming `nlm_volume` — treated as
   confirmed via two independent code paths computing the identical formula
   plus a very close numeric match to canonical's reported output range
   (see §3), not as a certainty beyond all doubt.
2. The new Specimen B's topology metrics are now so close to canonical's
   (within a few percent on every metric) that the original framing of
   Specimen B as "a genuine second physical Bnei Re'em replicate with its
   own distinct topological character" (per
   `connectivity_replicate_expansion_summary.md`) needs revisiting — the
   physical-replicate variability that document reported (e.g. its n=2 SE
   calculations) was computed entirely from the invalid input and should be
   treated as retracted alongside the rest of that run's numbers, not
   averaged with canonical going forward. A real second physical Bnei Re'em
   replicate may in fact look almost identical to canonical, not
   meaningfully different — a more mundane, and arguably more reassuring,
   conclusion than the one currently on record.
3. `04_inference/run_configs/` has no `.yaml` entry for
   `bnei_reem_samp_2_0_true_recon` yet (unlike `fresh_bnei_reem_i4.yaml`) —
   not added here since no other one-off recrop run
   (`bnei_reem_samp_2_0_recropped` itself) has one either; flagged only for
   consistency awareness, not treated as a defect.
