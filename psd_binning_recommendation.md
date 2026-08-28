# PSD binning recommendation for the three-soil microCT comparison

Prepared 2026-08-22. Question: how to aggregate ~59 fine log-spaced local-thickness bins into a defensible set of pore-size classes for per-class statistics (Vertisol, Loess, brown-red Sand).

## (a) Verified Dor et al. 2025 scheme

**Dor, M., Fan, L., Zamanian, K., Kravchenko, A.N. (2025). Long-term land use conversion influence on soil pore structure and organic carbon. *Agriculture, Ecosystems & Environment* 387, 109633.** https://doi.org/10.1016/j.agee.2025.109633 (preprint: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4859802, doi:10.2139/ssrn.4859802).

- The published abstract explicitly reports results by pore class, e.g. "lower volume of pores in the **30–150 μm** range (10–20%)" in agricultural vs. undisturbed soils — the 30–150 µm class is verified from the abstract itself.
- The full class scheme (10–30, 30–150, 150–300, >300 µm) is consistent with the Kravchenko-group convention (Dor's postdoc group at MSU); secondary search snippets of the paper confirm "pore size categories of 10–30 µm, 30–150 µm, and 150–300 µm" are used, with >300 µm as the top class. I could not open the ScienceDirect full text (paywall), so confirm the exact table in the PDF, but the scheme you cited matches everything accessible.
- The 30–150 µm "microbially active" domain originates in Kravchenko et al. (2019, *Nat. Commun.*) and is reaffirmed in Franco et al./Kravchenko (2024, *Nat. Commun.*): pores of 30–150 µm host the most active, fast-responding microbial communities (vs. 4–10 µm pores), are root/detritus-derived "biopores", and are linked to C processing and accrual.
- Note: earlier "Maoz Dor + Mishael" HUJI papers (PhD work with Yael Mishael, e.g. root-exudate/mucilage effects on soil structure, EGUsphere 2023 preprint) use microCT but not this fixed class scheme; the functional classes come from the Kravchenko collaboration.

## (b) Survey: how soil microCT papers bin PSDs for statistics

| Paper | Classes / boundaries | Rationale | Test per class |
|---|---|---|---|
| Dor et al. 2025, AGEE 387:109633 | 10–30, **30–150**, 150–300, >300 µm | Functional/biological domains (Kravchenko scheme); 30–150 = microbially active | Class-wise comparison among 4 land uses (ANOVA-type, mixed model) |
| Kravchenko et al. 2019, *Nat. Commun.* 10:3121 ("Microbial spatial footprint") | Contrasts centered on 30–150 µm vs. smaller/larger pores | Biological: enzyme activity and C protection differ by pore habitat | Mixed-model ANOVA across cropping systems |
| Franco et al. 2024, *Nat. Commun.* 15 ("Composition and metabolism of microbial communities in soil pores") | Two functional classes: 4–10 vs. 30–150 µm | Biological: distinct microbial life strategies per pore habitat | Pairwise class contrasts (ANOVA) |
| Kumari et al. 2022, *Front. Environ. Sci.* 10:898249 (Indo-Gangetic tillage) | Macropores >60 µm plus a few size sub-classes over 54–2250 µm | Detection limit + agronomic macropore function | ANOVA (RBD, n=3) + Duncan's test, p<0.05 |
| Pires et al. 2020, *Geoderma* 362:114103 (wetting–drying cycles) | Log size classes collapsed to a handful of size and 4 shape classes (equant/prolate/oblate/triaxial) | Morphological; imaged-porosity partition | ANOVA + Tukey, p<0.05 |
| Munkholm et al. 2012, *Geoderma* 181–182 (friability) | Few CT macropore classes above resolution limit (~60 µm range upward) | Detection limit + structural function | ANOVA with post-hoc mean separation |
| Lucas et al. 2021, *Eur. J. Soil Sci.* 72:546 (connectivity across resolutions) | Continuous PSD, but interpretation restricted to pores >~4 voxels (excluded <25 µm at 6 µm voxel) | Methodological: resolution bias | Descriptive across-scale comparison (key caveat source) |
| Galdos et al. 2019, *Sci. Rep.* (zero-tillage Brazil) | Macroporosity split into 2–3 broad classes (0.06/0.1–1, >1 mm) | Hydrological (fast-flow macropores) | ANOVA between tillage systems |

**Pattern:** nobody tests 59 bins. Papers making inference use **2–5 classes**, justified either (i) functionally — Brewer-type/capillary classes (micropores <30, mesopores 30–75, macropores >75 µm; or storage <~50 vs. transmission >~50 µm, Greenland 1977) or biological domains (Kravchenko 30–150 µm), or (ii) by the detection limit (everything above ~2–4 voxels lumped into a few macropore classes). Classical univariate tests per class (ANOVA/Tukey or Duncan; Kruskal-Wallis when n is small/non-normal) with p<0.05; a whole-distribution test (PERMANOVA/multivariate) is a sensible complement and matches your plan.

## (c) Recommended scheme

Adopt the mentor-group scheme, truncated to what all scans can see. **Four classes, three of them comparable across all three soils:**

| Class (µm) | Compared across | Justification |
|---|---|---|
| **31–150** "microbially active" | All 3 soils, **with caveat** | Lower bound = capillary drainage at ~ -10 kPa (field capacity; d[µm] ≈ 3000/\|h\|[hPa]), the classic storage/transmission divide, and the Kravchenko/Dor microbially-active lower bound; also coincides with the coarse scan's first bin (~31 µm ≈ 2 voxels at 15 µm). Caveat: the 15 µm-voxel scan under-detects the 31–60 µm portion (2–4 voxels), so run a **sensitivity re-test on 60–150 µm** (≥4 voxels in the coarse scan); conclusions should agree. |
| **150–300** "transmission" | All 3 soils | Kravchenko-scheme boundary; separates the microbially active domain from root-channel/inter-aggregate transmission pores (~fine-root diameter scale; drained at ~ -2 kPa). Well above 4 voxels in every scan. |
| **>300** "large macropores / biopores & cracks" | All 3 soils | Kravchenko-scheme boundary; faunal/root biopores and desiccation cracks, gravity-driven fast flow and aeration. Especially relevant for Vertisol cracking. |
| **10/12–31** (fine-scan floor to 31) | Fine scans only (5.85 µm voxels), reported as supplementary | Matches Dor et al.'s 10–30 µm class (plant-available-water storage domain). Cannot be seen by the 15 µm scan, so it must never enter the three-soil test; report descriptively (mean ± SE) for the soils that have it, clearly labeled. |

Statistics: per-class one-way ANOVA (Welch if variances differ) or Kruskal-Wallis on subvolume replicates, **Holm correction over the 3 comparable classes** (not 59 bins — power is preserved), post-hoc pairwise with letters; PERMANOVA on the 3-class (or full fine-bin, fine-scans-only) composition vector as the global test. Because class volume fractions are compositional, either analyze absolute per-class porosity (class volume / total volume) or CLR-transform fractions before PERMANOVA. Report mean ± SE throughout.

## (d) Voxel-size caveat

PSDs from local thickness are resolution-dependent in three ways. (1) **Detection:** pores narrower than ~2 voxels are missed entirely and pores below ~4 voxels are unreliably sized (partial-volume and segmentation sensitivity); Lucas et al. (2021) explicitly excluded pores <25 µm at a 6 µm voxel size (~4.2 voxels) for this reason. For the 15 µm scan this means nothing below ~31 µm exists in the data and the 31–60 µm range is systematically under-estimated, while the 5.85 µm scans resolve it — so any apparent deficit of fine pores in the coarse-scanned soil is partly instrumental, not pedological. (2) **Quantization:** maximal-inscribed-sphere diameters come in voxel-size steps, so fine log bins near the limit are artifacts of the grid, another reason to aggregate. (3) **Segmentation interaction:** thresholding at different resolutions shifts the pore/solid boundary differently, biasing total imaged porosity, so compare class *fractions of imaged porosity* cautiously and per-class porosity of the common size range (>~31 µm, sensitivity >60 µm) preferentially. A clean robustness check is to downsample the 5.85 µm volumes to 15 µm voxels, re-segment and recompute the PSD, and verify that between-soil conclusions for the shared classes are unchanged. State the per-scan lower detection limit in Methods and never interpret cross-soil differences below the coarsest scan's limit.

## (e) Sources

- Dor et al. 2025 (published): https://doi.org/10.1016/j.agee.2025.109633 ; https://www.sciencedirect.com/science/article/abs/pii/S0167880925001653
- Dor et al. preprint (SSRN, full abstract verified): https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4859802
- Franco/Kravchenko 2024, Nat. Commun. (30–150 vs 4–10 µm microbial pore habitats): https://www.nature.com/articles/s41467-024-47755-x ; https://pmc.ncbi.nlm.nih.gov/articles/PMC11055953/
- Kravchenko et al. 2019, Nat. Commun. (microbial spatial footprint, 30–150 µm): https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6635512/
- Kravchenko land-use/enzyme exchange (30–150 µm enzymatic activity): https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7755900/ ; https://www.nature.com/articles/s41467-020-19901-8
- Kumari et al. 2022, Front. Environ. Sci. (ANOVA + Duncan per class): https://www.frontiersin.org/journals/environmental-science/articles/10.3389/fenvs.2022.898249/full
- Pires et al. 2020, Geoderma (size/shape classes, ANOVA+Tukey): https://pmc.ncbi.nlm.nih.gov/articles/PMC7043393/ ; https://www.sciencedirect.com/science/article/pii/S0016706119307037
- Lucas et al. 2021, EJSS (resolution/4-voxel rule): https://bsssjournals.onlinelibrary.wiley.com/doi/full/10.1111/ejss.12961
- Munkholm et al. 2012, Geoderma (CT pore classes vs friability): https://www.sciencedirect.com/science/article/abs/pii/S0016706112001024
- Galdos et al. 2019, Sci. Rep. (zero-tillage macropore classes): https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6358041/
- Maoz Dor profile / HUJI Mishael group context: https://www.researchgate.net/profile/Maoz-Dor ; https://soilandwater.agri.huji.ac.il/book/export/html/67660 ; https://egusphere.copernicus.org/preprints/2023/egusphere-2023-2501/egusphere-2023-2501.pdf
