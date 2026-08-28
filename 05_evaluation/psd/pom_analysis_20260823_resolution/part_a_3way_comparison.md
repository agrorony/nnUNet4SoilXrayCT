## Part A -- 3-way resolution-matched comparison

| Metric | Bnei Re'em (15.00 um) | Mishmar native (5.85 um) | Mishmar new (15.00 um) |
|---|---|---|---|
| Distance-to-POM, denoised, mean (median) um | 597.9 (542.1) | 268.1 (258.1) | 652.8 (633.2) |
| Distance-to-POM, pore-adjacent, mean (median) um | 603.8 (548.9) | 269.4 (259.2) | 654.8 (635.5) |
| Distance-to-POM, connected-pore-adjacent, mean (median) um | 666.8 (586.5) | 284.5 (272.5) | 680.8 (659.5) |
| Count-median object diameter, um | 72.0 | 33.9 | 62.0 |
| Volume-weighted median diameter, um | 690.2 | 734.0 | 277.0 |
| Largest single object, % of denoised POM volume | 17.1 | 45.1 | 11.8 |
| POM volume fraction, % of total volume | 0.818 | 1.613 | 0.118 |
| POM-pore contact fraction | 0.642 | 0.562 | 0.672 |
| N POM objects (>= own elbow cutoff) | 1461 | 1726 | 1215 |
| Elbow cutoff (voxels / equiv um) | 8 vox / 37.2 um | 21 vox / 20.0 um | 12 vox / 42.6 um |

### Interpretation

**Distance-to-POM (all three conditions) and count-median object diameter: resolution-driven.**
Matching Mishmar to Bnei Re'em's resolution (15.00 um) moves its distance-to-POM mean from
268.1 um (native 5.85 um) to
652.8 um (new 15.00 um sample) --
landing closer to Bnei Re'em's 597.9 um
than to native-resolution Mishmar. Same pattern for count-median object diameter
(33.9 -> 62.0 um,
vs. Bnei Re'em's 72.0 um). This is consistent evidence that
a substantial part of the original Mishmar-vs-Bnei-Re'em distance/size gap in Table 2 was a **resolution artifact**
(the finer 5.85 um scan resolves smaller POM fragments and finer pore throats the coarser scans cannot), not a pure
soil-type effect.

**POM volume fraction, volume-weighted median diameter, and largest-object share: NOT cleanly resolution- or
soil-type-driven -- dominated by sample-to-sample variability.** The new 15 um Mishmar sample's POM volume fraction
(0.118%) is *lower* than both native Mishmar
(1.613%) and Bnei Re'em
(0.818%), and its volume-weighted median diameter
(277.0 um) is far below both
(734.0 and
690.2 um) -- neither "moves toward Bnei Re'em"
nor "stays with native Mishmar." The largest-single-object share is also wildly different between the two Mishmar
samples (native 45.1% vs. new
11.8%) despite being the same soil
type. These volume-dominated metrics are sensitive to whether a core happened to intersect one or two large POM
fragments -- a natural within-soil-type sampling variability, exactly the caveat this prompt asked to keep in view.

**Caveats (do not overclaim from n=1 additional sample):** this is a different physical core, not a controlled
resolution ablation of the same sample -- natural within-soil variability and the resolution change are riding
together, so this cannot cleanly attribute the distance/diameter shift to resolution alone versus a partly-real
soil-type difference that happens to point the same direction. The loess_i2 model was originally tuned on 5.85 um
patches; nnU-Net resamples internally to its training spacing, but applying it to a native-15um input is still a
secondary, smaller possible confound worth flagging. As already noted in the prompt itself, the clean ablation
(computationally downsampling native Mishmar to 15 um, same physical sample) is the recommended next step to
separate these explanations with more confidence -- not executed here.
