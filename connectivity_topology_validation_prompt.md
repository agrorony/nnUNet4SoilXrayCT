# Prompt — Connectivity/topology metrics validation (Euler χ, connectivity density, Γ, tortuosity) — Track E

> Paste this into Claude Code, in the PSD/topology pipeline repo (`run_psd_diagnostics.py`, `napari_view_full_volume.py`, `run_psd_batch.py`). Track E — validate the connectivity metrics that already exist in `Topology_Metrics_Aug2026V2/raw/psd_diag_*/summary.json` for Bnei Re'em and Mishmar HaNegev, fill the missing Rehovot values, and produce a resolution-matched cross-soil comparison. Not part of Track B (POM) — this track is pore-topology only.

---

## Why this task exists

`Topology_Metrics_Aug2026V2/raw/psd_diag_*/summary.json` has connectivity numbers for two soils that have never been checked before use in the draft:

| Metric | Bnei Re'em (15.00 µm) | Mishmar native (5.85 µm) |
|---|---|---|
| `euler_number` (χ) | 10,318 | −65,340 |
| `connectivity_density_per_mm3` | −11.10 | 326.37 |
| `connectivity_probability_gamma` (Γ) | 0.859 | 0.927 |
| `degree_of_anisotropy` (DA) | 0.098 | 0.123 |
| `tortuosity_axis0/1/2` | NaN / 5.77 / 4.21 | NaN / NaN / NaN |

Four open questions before any of this can go in the results section:

1. **Sign-convention check.** Bnei Re'em has a *positive* χ but a *negative* connectivity density, while Mishmar has the opposite pattern. Per `reading_masks_and_metrics.md`, `connectivity_density_per_mm3 = -euler_number / volume_mm3` (Herring et al. 2015 convention, sign-flipped so higher = more connected) — so a positive χ mechanically produces a negative density and vice versa. **This is very likely not a bug, just χ's sign doing what it's defined to do** — but it has never been arithmetically verified against the actual sample volumes, and it still needs to be reconciled in words with Γ=0.86–0.93 (both soils read as "mostly one connected cluster" by Γ) for the same soil that also reads as "χ-dominated by isolated components" by connectivity density. Those two readings are not automatically contradictory (see Part A), but the draft needs a clean sentence explaining why, not just the raw numbers.
2. **`tortuosity_axis0` is NaN in both runs**, and Mishmar's other two axes are also NaN. Root cause not yet investigated — most likely explanation, per `reading_masks_and_metrics.md`, is that `get_percolating_mask(pore_mask, axis=0)` finds no path spanning the volume along axis 0 for these samples, and porespy's tortuosity computation returns NaN rather than erroring when that happens. Needs confirming, not assuming.
3. **No Rehovot values exist.** Rehovot has never had an `extended`-mode topology run. It's also the odd one out — binary pore/solid, no POM class — so its label convention needs re-verifying before reusing the `--pore-label 5` default from the other two soils.
4. **Resolution confound.** Mishmar's numbers are at 5.85 µm while Bnei Re'em is at 15.00 µm — χ and connectivity density are strongly voxel-size-dependent (small pores/throats disappear as voxels coarsen), so as they stand the two are not a fair cross-soil comparison. Per `PROJECT_STATUS.md`'s "Scans note," a native 15 µm Mishmar scan exists (`Cu011_samp_2`, segmented with `i2_loess` on 2026-08-23) whose **pore channel is valid** (26.4% fraction, consistent with native Mishmar's 27.0%) even though its POM channel failed segmentation. That scan has never had topology metrics computed on it — doing so gives a genuine 15-µm-vs-15-µm comparison for Rehovot/Bnei Re'em/Mishmar, independent of the POM failure (Track A/B territory, not this one).

## Conventions

- Verify label convention with `np.unique()` on every volume before running anything, including Rehovot — do not assume `--pore-label 5` carries over from the deployed 4-class scheme (`{0,1,2,5}`, pore=5) documented in `reading_masks_and_metrics.md`. Rehovot is binary (pore/solid only, no POM/matrix distinction) and may use a different label for pore.
- Use `run_psd_diagnostics.py` in **`extended`** mode for every new run (needed for the topology block; `real` mode omits it) with the same settings used for the existing Bnei Re'em/Mishmar runs (26-connectivity, 1-voxel border trim) so results are comparable.
- Output every new run under `Topology_Metrics_Aug2026V2/raw/psd_diag_<timestamp>_<run_name>/`, matching the existing naming pattern, so `summary.json` files stay collected in one place.
- Don't touch or re-run the existing Bnei Re'em (`nlm_volume_fresh_bnei_reem_i4`) or Mishmar-native (`mishmar_hanegev_maoz_3_5p85um_scratch_i2`) runs — Part A works from their existing `summary.json` files as-is.

## Part A — Sign-convention and Γ-vs-χ reconciliation (no new runs)

1. Using the existing `summary.json` files, back out the sample volume each run must have used: `volume_mm3 = -euler_number / connectivity_density_per_mm3`. Confirm it's a plausible physical volume for these samples (order of magnitude check against known volume dimensions in the pipeline config/logs) and confirm both soils give a self-consistent, physically sane number — not just that the arithmetic closes (it will close by construction; the point is whether the resulting volume is sane).
2. Write 3–5 sentences, for the draft/notes, reconciling positive-χ-with-negative-density (Bnei Re'em) and negative-χ-with-positive-density (Mishmar) as expected behavior of the Herring et al. 2015 sign convention, **not** an inconsistency between the two soils.
3. Reconcile Γ with χ conceptually: χ = b0 − b1 + b2 counts isolated components (b0) against loops (b1) and cavities (b2), unweighted by size, while Γ is the probability two *randomly chosen pore voxels* land in the same 26-connected cluster — heavily weighted toward whichever cluster has the most volume. A pore space can simultaneously have many small isolated fragments (pushing b0, and therefore χ, up) *and* have Γ close to 1, if one giant cluster still contains the large majority of pore volume. Check this directly rather than just asserting it: run `scipy.ndimage.label` (or equivalent, 26-connectivity) on each soil's `pore_mask` and report the **number of connected components** and the **volume fraction held by the single largest component**. If the largest component holds the bulk of the pore volume despite a large component count, that confirms the "many small fragments coexist with one dominant giant cluster" explanation for both soils; if not, say so plainly instead of forcing the explanation.

## Part B — Tortuosity NaN root cause

1. For each existing run (Bnei Re'em, Mishmar native), compute `get_percolating_mask(pore_mask, axis=0)`, `axis=1`, `axis=2` directly and report whether each is empty (no voxels) or non-empty.
2. Cross-check against which `tortuosity_axis*` values are NaN. If NaN lines up exactly with an empty percolating mask for that axis, that confirms "no spanning path along that axis" as the cause (expected behavior, not a bug — flag it as a modeling note: these samples do not percolate top-to-bottom along axis 0 at the imaged resolution/orientation) — document this per soil. If any NaN does **not** line up with an empty mask (e.g. Mishmar's axis1/axis2 are NaN despite Bnei Re'em having real values there), treat that as a genuine bug in the tortuosity call and investigate the porespy invocation (are the args identical between the two runs? Same porespy version?) rather than writing it off.
3. Report which physical axis is `axis0` in this pipeline's orientation convention (check `run_psd_diagnostics.py` / the CT acquisition axis order) so the draft can say something more informative than "axis 0" — e.g. "no percolating path along the vertical (scan) axis."

## Part C — Rehovot topology run (fills the missing soil)

1. Locate Rehovot's segmentation volume (used already for `rehovot_distance_metrics_binary/` and/or `rehovot_inference_microsam_prompt.md` — reuse the same volume, don't re-infer). Confirm with `np.unique()`: binary pore/solid means two labels total (background/matrix and pore) — identify which numeric label is pore.
2. Run `run_psd_diagnostics.py` in extended mode with the correct `--pore-label` for Rehovot (no `--pom-label` needed — Rehovot has no POM class; check the script doesn't require one, or pass a value that safely no-ops). Same 26-connectivity / 1-voxel border convention as the other soils.
3. Report Rehovot's voxel size (should be 15 µm range, per `rehovot_150z` naming elsewhere in the project — confirm rather than assume) and porosity, sanity-checked against the pore fraction already used for Rehovot elsewhere in the draft/Table 2.
4. Output the full `summary.json` (χ, connectivity density, Γ, DA, tortuosity, anisotropy tensor) to `Topology_Metrics_Aug2026V2/raw/psd_diag_<timestamp>_rehovot_<model>/`.

## Part D — Resolution-matched Mishmar run (native 15 µm scan, pore channel)

1. Use the native 15 µm Mishmar scan `Cu011_samp_2` (segmented with `i2_loess`, 2026-08-23) — same volume already confirmed valid for pore metrics in `PROJECT_STATUS.md`'s Scans note (26.4% pore fraction, in line with native 5.85 µm Mishmar's 27.0%). Do **not** rely on or report anything from its POM channel (failed segmentation — out of scope here).
2. Run `run_psd_diagnostics.py` in extended mode on this volume's pore channel only, same convention as Parts A–C. Report the achieved voxel size.
3. Output to `Topology_Metrics_Aug2026V2/raw/psd_diag_<timestamp>_mishmar_15um_cu011samp2/`.

## Part E — Consolidated comparison + draft-ready summary

1. Build one table with all soils/resolutions now available: Rehovot (~15 µm), Bnei Re'em (15.00 µm), Mishmar native (5.85 µm), Mishmar `Cu011_samp_2` (~15 µm) — columns: voxel size, χ, connectivity density, Γ, DA, tortuosity axis0/1/2 (flag NaNs per Part B's finding), `psd_30_150um_volume_fraction`, largest-component volume fraction (from Part A).
2. **Primary cross-soil comparison** — do this at matched resolution: Rehovot / Bnei Re'em / Mishmar-15µm, all ~15 µm. This is the set safe to report as a genuine soil-type comparison.
3. **Resolution-sensitivity check** — Mishmar 5.85 µm vs. Mishmar 15 µm (Cu011_samp_2), same soil. Report how much χ, connectivity density, and Γ shift with voxel size alone. This quantifies how much of the original 5.85-vs-15-µm Bnei Re'em/Mishmar gap (documented as unvalidated in `PROJECT_STATUS.md`) was resolution rather than soil type — directly informs whether the resolution caveat needs to stay attached to any earlier Track A/A2 pore-metric claims that used both voxel sizes together.
4. Draft 3–4 sentences suitable for the results text and figure caption, covering: the matched-resolution soil comparison, the sign-convention/Γ reconciliation from Part A stated plainly (not left as a raw-numbers table), and the tortuosity-NaN finding from Part B stated as a modeling note rather than a gap.
5. Flag anything from this run that should feed Track D (figures) — e.g., which metrics are now trustworthy enough to plot, and whether Rehovot's binary (no-POM) status needs a footnote wherever POM-adjacent metrics appear alongside these.

## Output checklist

- `Topology_Metrics_Aug2026V2/raw/psd_diag_<timestamp>_rehovot_<model>/summary.json` (+ `psd_table.csv`, `result_psd.json`, matching the existing schema).
- `Topology_Metrics_Aug2026V2/raw/psd_diag_<timestamp>_mishmar_15um_cu011samp2/summary.json` (same schema).
- A markdown file, e.g. `Topology_Metrics_Aug2026V2/connectivity_validation_summary.md`, containing: the Part A volume back-calculation and Γ-vs-χ reconciliation (with the connected-component check), the Part B percolating-mask/NaN table, the Part C Rehovot run details, the Part D Mishmar-15µm run details, the Part E consolidated comparison table, both named comparisons (matched-resolution and resolution-sensitivity), and the draft-ready paragraph.
- In chat: the same consolidated table and paragraph, plus an explicit call-out of anything that came back genuinely inconsistent (not just "different") and needs a second look before Track D.

## Sanity checks

- Volume back-calculated in Part A (`-euler_number / connectivity_density_per_mm3`) should match a plausible physical sample volume for both existing runs — if it's off by orders of magnitude, the two fields aren't actually using consistent units/definitions and that's a real bug, not just a sign quirk.
- Rehovot's pore fraction from this run should be consistent with whatever pore-fraction number is already used for Rehovot in the current draft (Table 2 / `rehovot_distance_metrics_binary/`) — if it disagrees noticeably, stop and check the label convention before trusting the topology numbers.
- Mishmar `Cu011_samp_2` pore fraction should reproduce the 26.4% already confirmed in the Scans note — if this run gives something different, something changed (wrong volume, wrong label) and needs to be caught before the topology numbers are used.
- `get_percolating_mask` emptiness should agree with NaN placement 1:1 for the two existing runs (Part B) — any mismatch is a flagged bug, not explained away.
