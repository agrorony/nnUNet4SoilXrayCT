# Prompt — finish Track E replicate expansion (χ(r) sweep, tortuosity logging, consolidation)

> Paste into Claude Code. Follows `connectivity_replicate_expansion_prompt.md`, whose Part 2 (topology metrics) completed for 4 new volumes but stopped short of the required sanity check and consolidation. Fully autonomous — don't stop for input, flag and continue instead.

## What's done, what's missing

3 new runs exist on the network drive under `Topology_Metrics_Aug2026/raw/`: `bnei_reem_samp_2_0_recropped`, `rehovot_samp3_full_volume`, `mishmar_hanegev_maoz_2_8p8um_native` — each has a `summary.json` with topology metrics. Missing, and required before any of these numbers are trusted:

1. **χ(r) sweep + sanity check**, per `connectivity_crossover_radius_prompt.md`'s method, for all 3 new runs. Sweep `bin_edges_um` from each run's `result_psd.json`; at each r, `pore_mask_r = raw_pore_mask & (diameter_map_px >= r_px)` (apply the known local-thickness masking fix — AND the true pore mask in at every r, not just r=0). **Required:** χ at the smallest r must equal that run's own recorded `euler_number` exactly — report pass/fail per volume explicitly, don't just proceed silently. Output `chi_r_<run>.csv` per volume into `connectivity_function/`, plus crossover r* (or trend if none) same as the existing 4.
2. **Tortuosity NaNs need a real cause, not a bare NaN.** 2 of the 3 new runs have NaN axes (`bnei_reem_samp_2_0_recropped` axis0; `mishmar_hanegev_maoz_2_8p8um_native` all 3 axes). Re-run `tortuosity_fd` for just these axes with the actual exception caught and logged (not swallowed by a broad except) — confirm whether each is the known solver non-convergence bug or something else. Mishmar 8.8µm failing on *all three* axes is the one to look at most closely.
3. **Two numbers look surprising enough to investigate, not just report:**
   - `bnei_reem_samp_2_0_recropped`: χ=−144 (near-zero, sign-flipped vs. canonical Bnei Re'em's +10,318), DA jumped to 0.33 (canonical 0.098), and its `psd_30_150um_volume_fraction` is 0.047 — much lower than the other 3 new runs (0.56–0.81). Check whether this reflects the crop/mask genuinely differing from canonical, or a processing artifact (e.g. compare pore-mask visual/midslice against canonical's, re-check the border-trim and connectivity convention were applied identically). Re-confirm the recorded pore fraction (28.3%, from `DATA_CATALOG.md`) still matches this run's actual voxel counts.
4. **Volume back-calc sanity check** (voxel count × voxel size³ vs. recorded sample volume) for all 3 new runs — wasn't done yet either.

## Then consolidate

Once the above is done: build the multi-replicate table (all 7 runs now: original 4 + these 3), grouped by soil, distinguishing genuine physical replicates from same-core reconstructions (Specimen B = the real 2nd replicate). Report mean±SE where n≥2 physical replicates exist. Output `connectivity_replicate_expansion_summary.md` with: the sanity-check pass/fail table, tortuosity root-cause findings, the two flagged numbers' investigation results, and the consolidated table. Chat: short version of the same.
