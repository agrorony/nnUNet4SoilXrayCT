# Prompt — fix two Track E (connectivity/topology) errors: wrong input for Bnei Re'em Specimen B, unmatched Mishmar resolutions

> Paste into Claude Code, in the PSD/topology pipeline repo (`nnUNet4SoilXrayCT`). Fully autonomous — don't stop for input, flag and continue instead. Two independent fixes; do both.

## Background

Rony has confirmed two problems with the Track E replicate-expansion results (the ones in `connectivity_function/` and `Topology_Metrics_Aug2026/raw/psd_diag_20260829T*`):

1. **Bnei Re'em Specimen B's run used the wrong input file.** The `psd_diag_20260829T164631_bnei_reem_samp_2_0_recropped` run (PID 13048) and its associated `chi_r_bnei_reem_specB.csv` were computed on what turned out to be the scan's **trajectories** (a reconstruction/motion metadata artifact), not the actual segmented pore/POM volume. This invalidates every metric from that run: `euler_number=-144`, `connectivity_density=0.154`, `Γ=0.9539`, `DA=0.330`, and — critically — the headline finding that Specimen B has a loop-to-fragment crossover at r*≈451µm (unlike canonical, which never crosses over). **That finding must be treated as retracted until redone on the correct volume.**
2. **Mishmar has no matched-resolution mean±SE.** The 3 Mishmar physical specimens currently sit at 3 different voxel sizes (native 5.85µm, 2nd specimen 8.8µm, `Cu011_samp_2` ~15.0µm), so no honest mean±SE can be computed across them for Track E — only the existing "resolution-sensitivity check" framing. Rony wants the same **majority-vote label downsample to ~15µm** already validated for POM work (see `mishmar_downsample_ablation_prompt.md` Part A — `mishmar_label_downsample`, proven clean, no interpolation artifacts) applied here too, so all 3 Mishmar specimens can be compared/averaged at a matched ~15µm voxel size for Track E.

## Part 1 — Bnei Re'em Specimen B: find the correct input, rerun clean

1. **Root-cause first, don't just rerun blind.** Find whatever script/command actually produced `psd_diag_20260829T164631_bnei_reem_samp_2_0_recropped` (check shell history, the driver script used for the 4-volume Track E batch from `connectivity_replicate_expansion_prompt.md`, or any wrapper that assembled `--input` paths from a shared naming pattern). Confirm exactly which file was fed in and why it resolved to a trajectories file instead of the segmented volume — report this plainly (one paragraph) so the same bug doesn't recur for future batch runs.
2. **Identify the correct input.** Per `DATA_CATALOG.md`, Specimen B's valid segmented volume lives at `Z:\Rony\remote_computer backup\nnUNet_resources\bnei_reem_samp_2_0_recropped\` (the fully-preprocessed, correctly-cropped Aug 24 reconstruction — pore 28.3% / POM 7.62%, per the catalog). Before running anything: sanity-check this file directly — load it, run `np.unique()` on the label array, confirm the pore-label voxel fraction lands near 28.3% (not near-zero, not the ~39.4% original-uncropped number, and nothing consistent with a trajectories/metadata file, which would not look like a 3D labeled volume at all — e.g. wrong dtype, wrong shape, or absurd value range). Report this check's result explicitly before proceeding.
3. **Rerun the full Track E pipeline** on this confirmed-correct volume: the same full-volume topology summary (`euler_number`, `connectivity_density_per_mm3`, `Γ`, `DA`, tortuosity per axis — same script/method as the other 4 original + 4 replicate-expansion runs) **and** the χ(r) sweep (`compute_chi_r_sweep.py`, applying the known local-thickness-outside-pore-mask fix at every r).
4. **Required sanity checks, report pass/fail explicitly:**
   - χ at the smallest swept r must exactly equal this run's own recorded `euler_number`.
   - Voxel-count × voxel-size³ back-calculation must match the recorded sample volume.
5. Report the corrected numbers (χ, connectivity density, Γ, DA, r* or trend) side by side with the old, invalidated ones, and state plainly whether the "Specimen B crosses over, canonical doesn't" finding still holds on the corrected input — it may or may not; report whatever the corrected data actually shows, don't assume the qualitative conclusion survives.
6. Save outputs alongside the existing Track E outputs under clearly-superseding names (e.g. `psd_diag_<newtimestamp>_bnei_reem_samp_2_0_recropped_CORRECTED`, `chi_r_bnei_reem_specB_corrected.csv`) — do not silently overwrite the invalidated run; keep it on disk with a note that it's superseded and why, for traceability.

## Part 2 — Mishmar: downsample all 3 specimens to matched ~15µm for Track E, compute mean±SE

1. **`mishmar_native` (5.85µm → ~15µm):** apply the same majority-vote label downsample already validated in `mishmar_downsample_ablation_prompt.md` Part A (non-overlapping ~2.56×2.56×2.56-voxel blocks, most-common-label per block, no interpolation) to the native Mishmar segmentation. Verify `np.unique()` still shows only valid labels, report achieved voxel size and pore-fraction sanity check (should stay close to native's 27.038% — resolution loss shouldn't move pore fraction much).
2. **`mishmar_hanegev_maoz_2_8p8um` (8.8µm → ~15µm):** same majority-vote downsample method, from 8.8µm to ~15µm (8.8/15 ≈ block factor 1.70 — round sensibly and report the achieved voxel size). Same pore-fraction sanity check against this specimen's existing pore%.
3. **`Cu011_samp_2`** is already natively ~15.000149µm — no downsampling needed, use as-is (this is the specimen already in the current Table 3 as "Mishmar Cu011_samp_2").
4. **Run the full Track E pipeline** (topology summary + χ(r) sweep, same method as Part 1) on the two newly-downsampled volumes. Apply the same two required sanity checks (χ-at-min-r match, volume back-calc) and report pass/fail explicitly for each.
5. **Compute mean±SE across all 3 Mishmar specimens at matched ~15µm** for each Track E metric (connectivity density, Γ, DA, r*) — same format as the Rehovot mean±SE already in the draft (`124 ± 23 µm` for r*, `0.993 ± 0.004` for Γ). Report n=3.
6. Keep the native-resolution numbers (5.85µm, 8.8µm as originally run) on record too, clearly labeled as the resolution-sensitivity comparison — they're still useful for that purpose, just not for the mean±SE.

## Output checklist

- Part 1: root-cause paragraph (what went wrong and why), input-file sanity check result, corrected Track E numbers vs. the retracted ones, both required sanity checks pass/fail, explicit statement of whether the crossover finding survives on the corrected input.
- Part 2: downsample achieved voxel sizes + pore-fraction sanity checks for both new Mishmar branches, both required sanity checks pass/fail for each, the matched-15µm 3-way Mishmar table, and the Mishmar mean±SE (n=3).
- A short consolidated `track_e_correction_summary.md` with both parts, suitable for directly updating `DATA_CATALOG.md`, `PROJECT_STATUS.md`, and Table 3 of the draft figures document.
- In chat: a short version of the same — the corrected Bnei Re'em Specimen B numbers and whether the heterogeneity finding holds, plus the Mishmar matched-resolution mean±SE.

## Sanity checks (both parts)

- χ at the smallest swept r must equal the run's own recorded `euler_number`, exactly, for every new/rerun volume.
- Voxel-count-based volume back-calculation must match the recorded sample volume, for every new/rerun volume.
- Downsampled label arrays must show only valid labels via `np.unique()` — a majority-vote block downsample cannot introduce new values.
- Pore-fraction sanity checks (against each specimen's own native-resolution baseline) must be reported explicitly, not skipped, before trusting any downstream number.
