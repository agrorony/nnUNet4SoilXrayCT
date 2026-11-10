## Part 4 -- group comparison (Bnei Re'em vs. Mishmar label-downsample, n stated per group)

Group n: Bnei Re'em n=1, Mishmar n=2.

**Caveat:** Bnei Re'em is n=1 (Part 0 found only one plausible physical replicate -- `bnei_reem_samp_2_0` was excluded for an implausible POM/pore fraction, see Part 0 report). Its 'group' value below is a single observation, not a mean, and has no SE. Mishmar is n=2: mean +/- SE is descriptive only, not a basis for a hypothesis test at this sample size, per the prompt's own instruction.

### Per-replicate values

| Metric | Bnei Re'em (canonical, 15.00um) -- n=1 | Mishmar sample 1 (native 5.85um -> ~15um) | Mishmar sample 2 (native 8.8um -> ~15um) |
|---|---|---|---|
| Distance-to-POM, denoised, mean um | 597.862 | 347.267 | 500.622 |
| Distance-to-POM, pore-adjacent, mean um | 603.785 | 348.767 | 501.002 |
| Distance-to-POM, connected-pore-adjacent, mean um | 666.808 | 356.684 | 525.823 |
| Count-median object diameter, um | 72.040 | 89.841 | 83.967 |
| Volume-weighted median diameter, um | 690.219 | 735.569 | 1146.443 |
| POM volume fraction, % of total volume | 0.818 | 1.608 | 1.641 |
| POM-pore contact fraction | 0.642 | 0.599 | 0.549 |
| Largest object, % of denoised POM volume | 17.077 | 45.385 | 45.359 |

### Group mean +/- SE

| Metric | Bnei Re'em (n=1) | Mishmar (n=2, mean +/- SE) |
|---|---|---|
| Distance-to-POM, denoised, mean um | 597.862 | 423.945 +/- 76.677 |
| Distance-to-POM, pore-adjacent, mean um | 603.785 | 424.884 +/- 76.117 |
| Distance-to-POM, connected-pore-adjacent, mean um | 666.808 | 441.253 +/- 84.570 |
| Count-median object diameter, um | 72.040 | 86.904 +/- 2.937 |
| Volume-weighted median diameter, um | 690.219 | 941.006 +/- 205.437 |
| POM volume fraction, % of total volume | 0.818 | 1.624 +/- 0.016 |
| POM-pore contact fraction | 0.642 | 0.574 +/- 0.025 |
| Largest object, % of denoised POM volume | 17.077 | 45.372 +/- 0.013 |

### Comparison to prior single-point figures (distance-to-POM, denoised mean)

- `pom_analysis_20260815_light/`: Bnei Re'em 597.9 um vs. native Mishmar 268.1 um (both n=1, no downsampling).
- 2026-08-24 ablation (native sample only, label-downsampled): 347.3 um (n=1).
- This run's Mishmar group (n=2, both samples label-downsampled): individual values ['347.3', '500.6'] um, mean 423.9 um.

Adding the second Mishmar replicate shifts the group mean by 22.1% relative to the single-sample 08-24 ablation figure -- a non-trivial shift, indicating meaningful within-Mishmar physical-sample variability that the n=1 figure could not have revealed.