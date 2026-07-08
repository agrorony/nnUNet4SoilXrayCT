# Prompt: Stage 1 — Resolve research decisions for PSD module extension (literature-only, no code)

## Goal

Before any implementation happens, resolve every open methodological decision required to extend the existing soil-CT PSD module with: connectivity-conditioned distance maps, Euler characteristic / connectivity density, connectivity probability (Γ), degree of anisotropy, and tortuosity. Do this purely from the literature placed in `pore_metrics_research/papers/` — **do not write, edit, or plan implementation code in this stage.**

## Input

Check `pore_metrics_research/papers/` for the PDFs listed in `pore_metrics_research_reading_list.md` (in the repo root). If any listed paper is missing, do not stop and wait — proceed per the Constraints section below (pick the most defensible convention available, flag it low-confidence) rather than blocking the pipeline.

## Decisions to resolve

For each decision below: read the cited paper(s), extract the precise definition/formula/convention needed, and write your resolution into `pore_metrics_research/decisions.md`.

### D1 — "Connected / percolating pore" definition
What exactly counts as a "connected" pore for the connectivity-conditioned distance maps (used for both distance-to-pores and distance-to-POM)? Options seen in the literature include: percolation across two opposite faces of the sample (along one specific axis, or any axis), largest connected component only, or another operational definition. Read: Jarvis, Larsbo & Koestel (2017); Renard & Allard (2013); Schlüter et al. (2022).
Required output: the exact operational definition to implement (e.g., "26-connectivity components that touch both the top and bottom Z-faces of the cuboid"), with the reasoning tied to a specific paper.

### D2 — Euler characteristic sign convention & normalization
How should the raw Euler number be converted into a "connectivity density" comparable to Dor et al. (2025) Fig. S5 — sign convention (some tools report the negative of the Euler number as more-connected-is-higher), and what exactly it's normalized by (pore-space volume vs. total sample volume, and in what units). Read: Vogel (1997); Herring et al. (2015); Doube et al. (2010, BoneJ — the tool the source paper actually used).
Required output: the exact sign convention and normalization formula to implement, and which library call (if any, e.g., `skimage.measure.euler_number`) matches that convention — flag if `skimage`'s convention differs from BoneJ's and what correction factor/sign flip is needed.

### D3 — Connectivity probability (Γ) formula
The precise definition and normalization of Γ as used in Dor et al. (2025) Fig. S5. Read: Jarvis, Larsbo & Koestel (2017) — the sole primary source.
Required output: the exact formula/procedure to implement, expressed in terms of quantities computable from a labeled 3D pore array (e.g., counts of percolating clusters, total pore volume, sample dimensions).

### D4 — Degree of anisotropy (MIL / fabric tensor) algorithm
Which specific algorithm to implement: mean-intercept-length (MIL) direction sampling → fabric tensor → eigenvalue-ratio anisotropy, as used by BoneJ's Anisotropy plugin. Read: Odgaard (1997) — original method; Doube et al. (2010) — BoneJ's specific implementation/parameters.
Required output: the exact algorithm steps (how many/which sampling directions, tensor construction, and the anisotropy index formula from the eigenvalues), plus any existing Python implementation found (BoneJ-equivalent, `porespy`, or other) vs. what must be written from scratch.

### D5 — Tortuosity: definition + computation method
Which tortuosity definition (geometric, hydraulic, electrical, or diffusive — per Ghanbarian et al. 2013's taxonomy) is appropriate for "how much longer is the real diffusive path vs. the straight-line distance already computed in the distance maps," and which specific `porespy` function (if the installed version has one) implements it. Read: Ghanbarian, Hunt, Ewing & Sahimi (2013); Gostick et al. (2019, the PoreSpy paper) — then check the actually-installed `porespy` version's API directly (`pip show porespy`, inspect `porespy.simulations`/`porespy.metrics`) since the API has changed across versions and the paper alone won't reflect the current function names.
Required output: which tortuosity type was chosen and why, the exact `porespy` function/class to call (or a fallback custom implementation plan if no suitable function exists in the installed version), and whether it needs the connectivity-conditioned pore mask from D1 as input.

## Deliverables

1. **`pore_metrics_research/decisions.md`** — one section per decision (D1–D5). Each section must contain:
   - The resolved decision, stated as an implementable specification (not just prose — include the actual formula/steps).
   - A justification paragraph citing the specific paper(s) and paraphrasing/quoting the relevant passage.
   - A confidence flag: **High** (directly and unambiguously stated in a paper found in the folder), **Medium** (inferred/synthesized from multiple sources), or **Low** (a required paper was missing or ambiguous, and a defensible default was chosen instead — state the default and why).

2. **Updated `stage2_implementation_prompt.md`** — open it and replace every block delimited by
   ```
   <!-- STAGE1-DECISION: Dx -->
   ...
   <!-- END-DECISION -->
   ```
   with the concrete resolved specification for that decision (formula, convention, library/function choice), drawn directly from `decisions.md`. Keep the surrounding prompt text intact — only fill in the marked blocks.

## Constraints

- No implementation code in this stage — this stage produces documentation (`decisions.md`) and edits one other prompt file, nothing else.
- Missing paper ≠ blocker: document the gap and the default chosen, flagged Low confidence, and move on.
- Do not ask the user for input mid-stage. Resolve everything from the available literature plus defensible defaults; confidence flags are how uncertainty gets communicated, not questions back to the user.

## Final step — proceed to Stage 2 automatically, no pause

Once `decisions.md` is written and `stage2_implementation_prompt.md` is fully updated, **immediately continue in this same session and execute every task in `stage2_implementation_prompt.md` in full.** Do not stop, summarize-and-wait, or ask for confirmation between the two stages — Stage 2 is a direct, automatic continuation of this task, not a separate step requiring approval.
