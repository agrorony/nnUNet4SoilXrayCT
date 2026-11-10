# Literature used for this analysis

These are the papers used to design, implement and interpret the analysis in this repository and the write-up (Schwartz, 2026). The PDFs are not in git because they are third-party copyright. They are kept locally in this folder (`docs/literature/`, which `.gitignore` excludes except for this file), and each PDF is named by the key shown in front of its entry (e.g. `Jarvis_2017.pdf`).

- **[W]** = cited in the submitted write-up.
- **Used for** says where the paper fed into the analysis or the text.
- DOIs come from the papers themselves, the write-up's reference list, the project's reading notes, or a bibliographic record checked on 2026-11-10. Entries without a DOI have not had one checked.

## 1. Segmentation and image processing

- `Phalempin_2025` **[W]** Phalempin, M., Krämer, L., Geers-Lucas, M., Isensee, F., & Schlüter, S. (2025). Deep learning segmentation of soil constituents in 3D X-ray CT images. *Geoderma*, 458, 117321. https://doi.org/10.1016/j.geoderma.2025.117321 (preprint: https://doi.org/10.22541/essoar.173395846.68597189/v1)
  **Used for:** the UFZ pipeline this fork builds on: preprocessing, the sparse-annotation strategy, and the ignore-label trainer.
- `Isensee_2021` Isensee, F., Jaeger, P. F., Kohl, S. A. A., Petersen, J., & Maier-Hein, K. H. (2021). nnU-Net: a self-configuring method for deep learning-based biomedical image segmentation. *Nature Methods*, 18(2), 203–211. https://doi.org/10.1038/s41592-020-01008-z
  **Used for:** the segmentation framework behind every nnU-Net model (Vertisol `fresh_bnei_reem_i4`, Loess `loess_i2`).
- `Otsu_1979` Otsu, N. (1979). A threshold selection method from gray-level histograms. *IEEE Transactions on Systems, Man, and Cybernetics*, 9(1), 62–66.
  **Used for:** the global-threshold binary masks of the Rehovot sand, and the model-free cross-check in the Vertisol identity investigation.
- `Buades_2005` Buades, A., Coll, B., & Morel, J.-M. (2005). A non-local algorithm for image denoising. *Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition (CVPR 2005)*, 2, 60–65.
  **Used for:** the non-local-means (NLM) denoising step before inference (`2_preprocessing/denoise_normalize/`).
- `Schluter_2014` Schlüter, S., Sheppard, A., Brown, K., & Wildenschild, D. (2014). Image processing of multiphase images obtained via X-ray microtomography: A review. *Water Resources Research*, 50(4), 3615–3639. https://doi.org/10.1002/2014WR015256
  **Used for:** the voxel-face interfacial-area estimate and its known bias (POM interface metrics). Also background on multiclass segmentation.
- `Houston_2013` Houston, A. N., Otten, W., Baveye, P. C., & Hapca, S. (2013). Adaptive-window indicator kriging: A thresholding method for computed tomography images of porous media. *Computers & Geosciences*, 54, 239–248.
  **Used for:** solid–pore interfacial area from 3D Minkowski functionals, the method behind the POM interface precedent (`Juyal_2021`).
- micro-SAM: Archit, A., et al. Segment Anything for Microscopy. *Nature Methods*. https://doi.org/10.1038/s41592-024-02580-4
  **Used for:** explored in `1_annotation/napari_review_tool/`. Not used for any reported result.

## 2. Pore-size distribution and pore classes

- `Hildebrand_Ruegsegger_1997` Hildebrand, T., & Rüegsegger, P. (1997). A new method for the model-independent assessment of thickness in three-dimensional images. *Journal of Microscopy*, 185(1), 67–75. https://doi.org/10.1046/j.1365-2818.1997.1340694.x
  **Used for:** local thickness, i.e. the pore-size distribution (`psd_diagnostics_core.py`).
- `Vogel_2010` **[W]** Vogel, H.-J., Weller, U., & Schlüter, S. (2010). Quantification of soil structure based on Minkowski functions. *Computers & Geosciences*, 36(10), 1236–1245. https://doi.org/10.1016/j.cageo.2010.03.007
  **Used for:** the Minkowski-function framework, and the rule that objects below about 5 voxels are unreliable.
- `Dor_2025` **[W]** Dor, M., Fan, L., Zamanian, K., & Kravchenko, A. N. (2025). Long-term land use conversion influence on soil pore structure and organic carbon. *Agriculture, Ecosystems and Environment*, 387, 109633. https://doi.org/10.1016/j.agee.2025.109633
  **Used for:** the baseline methodology: the 30–150 µm pore class, distance-map definitions, connectivity density and anisotropy as reported with BoneJ. Its Fig. 1a was the style reference for the 3D renders.
- `Kravchenko_2019b` Kravchenko, A. N., et al. (2019). Microbial spatial footprint as a driver of soil carbon stabilization. *Nature Communications*. https://doi.org/10.1038/s41467-019-11057-4
  **Used for:** the origin of the 30–150 µm "microbially active" pore class (`5_analysis/pore_size_distribution/psd_binning_recommendation.md`).
- `Franco_2024` Franco, et al. (2024). Composition and metabolism of microbial communities in soil pores. *Nature Communications*, 15. https://doi.org/10.1038/s41467-024-47755-x
  **Used for:** the 4–10 µm vs 30–150 µm pore-habitat contrast (PSD class choice).
- `Kaur_2025` **[W]** Kaur, P., Lamba, J., Way, T. R., Balkcom, K. S., & Watts, D. B. (2025). Effect of image resolution and soil core diameter on soil pore characteristics quantified using X-ray computed tomography. *Journal of Soils and Sediments*, 25, 2611–2625. https://doi.org/10.1007/s11368-025-04105-8
  **Used for:** the resolution confound between the 5.85 µm Loess scan and the 15 µm scans (A2 re-analysis, label-downsampling to ~15 µm).
- Coarse pore-class precedents checked for the binning decision (`psd_binning_recommendation.md`). Only the details recorded there are given:
  - `Pires_2020` Pires, L. F., et al. (2020). *Geoderma*, 362, 114103 (wetting–drying cycles). https://pmc.ncbi.nlm.nih.gov/articles/PMC7043393/
  - `Munkholm_2012` Munkholm, L. J., et al. (2012). *Geoderma*, 181–182 (CT pore classes and soil friability). https://www.sciencedirect.com/science/article/abs/pii/S0016706112001024
  - `Kumari_2022` Kumari, et al. (2022). *Frontiers in Environmental Science*, 10, 898249 (tillage, Indo-Gangetic plain). https://doi.org/10.3389/fenvs.2022.898249
  - `Galdos_2019` Galdos, M. V., et al. (2019). *Scientific Reports* (zero tillage, macropore classes). https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6358041/

## 3. Connectivity, anisotropy and tortuosity

- `Vogel_1997` Vogel, H.-J. (1997). Morphological determination of pore connectivity as a function of pore size using serial sections. *European Journal of Soil Science*, 48, 365–377. https://doi.org/10.1111/j.1365-2389.1997.tb00203.x
  **Used for:** the connectivity function χ(r) (`compute_chi_r_sweep.py`).
- `Vogel_Roth_2001` **[W]** Vogel, H.-J., & Roth, K. (2001). Quantitative morphology and network representation of soil pore structure. *Advances in Water Resources*, 24(3–4), 233–242. https://doi.org/10.1016/S0309-1708(00)00055-5
  **Used for:** the connectivity function and the crossover radius r*.
- `Jarvis_2017` **[W]** Jarvis, N., Larsbo, M., & Koestel, J. (2017). Connectivity and percolation of structural pore networks in a cultivated silt loam soil quantified by X-ray tomography. *Geoderma*, 287, 71–79. https://doi.org/10.1016/j.geoderma.2016.06.026
  **Used for:** the connection probability Γ and the percolating-pore definition (26-connectivity). Also the porosity dependence of Γ used in the discussion.
- `Renard_Allard_2013` Renard, P., & Allard, D. (2013). Connectivity metrics for subsurface flow and transport. *Advances in Water Resources*, 51, 168–196. https://doi.org/10.1016/j.advwatres.2011.12.001
  **Used for:** the Euler characteristic convention χ = b0 − b1 + b2.
- `Herring_2015` Herring, A. L., Andersson, L., Schlüter, S., Sheppard, A., & Wildenschild, D. (2015). Efficiently engineering pore-scale processes: The role of force dominance and topology during nonwetting phase trapping in porous media. *Advances in Water Resources*, 79, 91–102. https://doi.org/10.1016/j.advwatres.2015.02.005
  **Used for:** the sign and volume normalisation of connectivity density (higher = more connected).
- `Doube_2010` Doube, M., et al. (2010). BoneJ: Free and extensible bone image analysis in ImageJ. *Bone*, 47(6), 1076–1079. https://doi.org/10.1016/j.bone.2010.08.023
  **Used for:** the reference for how BoneJ (the tool used by `Dor_2025`) computes Euler number and anisotropy. Its edge-correction details were never checked, so absolute values may differ from Dor et al.
- `Odgaard_1997` Odgaard, A. (1997). Three-dimensional methods for quantification of cancellous bone architecture. *Bone*, 20(4), 315–328. https://doi.org/10.1016/S8756-3282(97)00007-0
  **Used for:** the mean-intercept-length fabric tensor behind the degree of anisotropy (DA).
- `Harrigan_Mann_1984` Harrigan, T. P., & Mann, R. W. (1984). *Journal of Materials Science*.
  **Used for:** the fabric-tensor fit. Cited through `Odgaard_1997` and not read directly.
- `Ghanbarian_2013` Ghanbarian, B., Hunt, A. G., Ewing, R. P., & Sahimi, M. (2013). Tortuosity in porous media: A critical review. *Soil Science Society of America Journal*, 77, 1461–1477. https://doi.org/10.2136/sssaj2012.0435
  **Used for:** the choice of diffusive tortuosity and its definition.
- `Gostick_2019` Gostick, J., et al. (2019). PoreSpy: A Python toolkit for quantitative analysis of porous media images. *Journal of Open Source Software*, 4(37), 1296. https://doi.org/10.21105/joss.01296
  **Used for:** the finite-difference tortuosity solver (`tortuosity_fd`).
- `Koestel_2020` **[W]** Koestel, J., Larsbo, M., & Jarvis, N. (2020). Scale and REV analyses for porosity and pore connectivity measures in undisturbed soil. *Geoderma*, 366, 114206. https://doi.org/10.1016/j.geoderma.2020.114206
  **Used for:** the caveat that the 200³ tortuosity subvolumes may be below the REV for connectivity measures.
- `Lucas_2021` **[W]** Lucas, M., Vetterlein, D., Vogel, H.-J., & Schlüter, S. (2021). Revealing pore connectivity across scales and resolutions with X-ray CT. *European Journal of Soil Science*. https://doi.org/10.1111/ejss.12961
  **Used for:** the meaning of the sign of the Euler characteristic, and the resolution dependence of connectivity.

## 4. Particulate organic matter (POM)

- `Juyal_2021` Juyal, A., Guber, A., Oerther, M., Quigley, M., & Kravchenko, A. (2021). Pore architecture and particulate organic matter in soils under monoculture switchgrass and restored prairie in contrasting topography. *Scientific Reports*, 11, 21998. https://doi.org/10.1038/s41598-021-01533-7
  **Used for:** the direct precedent for POM–pore and POM–matrix interface metrics.
- `Schluter_2022` **[W]** Schlüter, S., Leuther, F., Albrecht, L., Hoeschen, C., Kilian, R., Surey, R., Mikutta, R., Kaiser, K., Mueller, C. W., & Vogel, H.-J. (2022). Microscale carbon distribution around pores and particulate organic matter varies with soil moisture regime. *Nature Communications*, 13, 2098. https://doi.org/10.1038/s41467-022-29605-w
  **Used for:** distances between POM and connected or air-filled pores.
- `Clark_Evans_1954` Clark, P. J., & Evans, F. C. (1954). Distance to nearest neighbor as a measure of spatial relationships in populations. *Ecology*, 35(4), 445–453.
  **Used for:** the Clark–Evans R index of POM spatial clustering.
- `Lavallee_2020` **[W]** Lavallee, J. M., Soong, J. L., & Cotrufo, M. F. (2020). Conceptualizing soil organic matter into particulate and mineral-associated forms to address global change in the 21st century. *Global Change Biology*, 26(1), 261–273. https://doi.org/10.1111/gcb.14859
- `Hassink_1997` **[W]** Hassink, J. (1997). The capacity of soils to preserve organic C and N by their association with clay and silt particles. *Plant and Soil*, 191, 77–87. https://doi.org/10.1023/A:1004213929699
- `Negassa_2015` **[W]** Negassa, W. C., Guber, A. K., Kravchenko, A. N., Marsh, T. L., Hildebrandt, B., & Rivers, M. L. (2015). Properties of soil pore space regulate pathways of plant residue decomposition and community structure of associated bacteria. *PLoS ONE*, 10(4), e0123999. https://doi.org/10.1371/journal.pone.0123999

## 5. Lab methods and microbial indices

- `Vance_1987` **[W]** Vance, E. D., Brookes, P. C., & Jenkinson, D. S. (1987). An extraction method for measuring soil microbial biomass C. *Soil Biology and Biochemistry*, 19(6), 703–707. https://doi.org/10.1016/0038-0717(87)90052-6
  **Used for:** the fumigation–extraction method for microbial biomass C (MBC).
- `Anderson_Domsch_1989` **[W]** Anderson, T.-H., & Domsch, K. H. (1989). Ratios of microbial biomass carbon to total organic carbon in arable soils. *Soil Biology and Biochemistry*, 21(4), 471–479. https://doi.org/10.1016/0038-0717(89)90117-X
  **Used for:** the MBC/Corg quotient.
- `Anderson_Domsch_1993` **[W]** Anderson, T.-H., & Domsch, K. H. (1993). The metabolic quotient for CO2 (qCO2) as a specific activity parameter to assess the effects of environmental conditions, such as pH, on the microbial biomass of forest soils. *Soil Biology and Biochemistry*, 25(3), 393–395. https://doi.org/10.1016/0038-0717(93)90140-7
  **Used for:** the metabolic quotient qCO2.
- `Blagodatskaya_2014` **[W]** Blagodatskaya, E., Blagodatsky, S., Anderson, T.-H., & Kuzyakov, Y. (2014). Microbial growth and carbon use efficiency in the rhizosphere and root-free soil. *PLoS ONE*, 9(4), e93282. https://doi.org/10.1371/journal.pone.0093282
- `Gao_2024` **[W]** Gao, D., Shi, W., Wang, H., Liu, Z., Jiang, Q., Lv, W., Wang, S., Zhang, Y.-L., Zhao, C., & Hagedorn, F. (2024). Contrasting global patterns of soil microbial quotients of carbon, nitrogen, and phosphorus in terrestrial ecosystems. *Catena*, 243, 108145. https://doi.org/10.1016/j.catena.2024.108145
  **Used for:** reference ranges for the microbial quotients.
- `Birch_1958` **[W]** Birch, H. F. (1958). The effect of soil drying on humus decomposition and nitrogen availability. *Plant and Soil*, 10(1), 9–31. https://doi.org/10.1007/BF01343734
- `Borken_Matzner_2009` **[W]** Borken, W., & Matzner, E. (2009). Reappraisal of drying and wetting effects on C and N mineralization and fluxes in soils. *Global Change Biology*, 15(4), 808–824. https://doi.org/10.1111/j.1365-2486.2008.01681.x
- `Linn_Doran_1984` **[W]** Linn, D. M., & Doran, J. W. (1984). Effect of water-filled pore space on carbon dioxide and nitrous oxide production in tilled and nontilled soils. *Soil Science Society of America Journal*, 48(6), 1267–1272. https://doi.org/10.2136/sssaj1984.03615995004800060013x
- `Dor_2026` **[W]** Dor, M., Guber, A. K., Tiemann, L., Kuzyakov, Y., & Kravchenko, A. N. (2026). Nitrogen availability decouples soil pore size-defined microhabitat control of microbial carbon use efficiency. *Soil Biology and Biochemistry*, 221, 110249. https://doi.org/10.1016/j.soilbio.2026.110249
- `Ritz_Young_2004` **[W]** Ritz, K., & Young, I. M. (2004). Interactions between soil structure and fungi. *Mycologist*, 18(2), 52–59. https://doi.org/10.1017/S0269915X04002010

## 6. Statistics

- `Games_Howell_1976` **[W]** Games, P. A., & Howell, J. F. (1976). Pairwise multiple comparison procedures with unequal n's and/or variances: A Monte Carlo study. *Journal of Educational Statistics*, 1(2), 113–125. https://doi.org/10.3102/10769986001002113
- `Seaman_1991` **[W]** Seaman, M. A., Levin, J. R., & Serlin, R. C. (1991). New developments in pairwise multiple comparisons: Some powerful and practicable procedures. *Psychological Bulletin*, 110(3), 577–586. https://doi.org/10.1037/0033-2909.110.3.577

## 7. Background cited in the write-up

- `Young_Crawford_2004` **[W]** Young, I. M., & Crawford, J. W. (2004). Interactions and self-organization in the soil-microbe complex. *Science*, 304, 1634. https://doi.org/10.1126/science.1097394
- `Nunan_2017` **[W]** Nunan, N. (2017). The microbial habitat in soil: Scale, heterogeneity and functional consequences. *Journal of Plant Nutrition and Soil Science*, 180, 425–429. https://doi.org/10.1002/jpln.201700184
- `Kravchenko_Guber_2017` **[W]** Kravchenko, A. N., & Guber, A. K. (2017). Soil pores and their contributions to soil carbon processes. *Geoderma*, 287, 31–39. https://doi.org/10.1016/j.geoderma.2016.06.027
- `Kravchenko_2019a` **[W]** Kravchenko, A. N., Guber, A. K., Razavi, B. S., Koestel, J., Blagodatskaya, E. V., & Kuzyakov, Y. (2019). Spatial patterns of extracellular enzymes: Combining X-ray computed micro-tomography and 2D zymography. *Soil Biology and Biochemistry*, 135, 411–419. https://doi.org/10.1016/j.soilbio.2019.06.002
- `Chenu_2025` **[W]** Chenu, C., Pouteau, V., & Nunan, N. (2025). Pore scale microbial biogeography across different soil types. *Soil Biology and Biochemistry*, 209, 109896. https://doi.org/10.1016/j.soilbio.2025.109896
- `Leuther_2025` **[W]** Leuther, F., Fischer, D., Nunan, N., Meurer, K. H. E., & Herrmann, A. M. (2025). Soil structural indicators as predictors of biological activity under various soil management practices. *Geoderma*, 457, 117290. https://doi.org/10.1016/j.geoderma.2025.117290
- `Zhao_2020` **[W]** Zhao, Y., Hu, X., & Li, X. (2020). Analysis of the intra-aggregate pore structures in three soil types using X-ray computed tomography. *Catena*, 193, 104622. https://doi.org/10.1016/j.catena.2020.104622
- `Xia_2022` **[W]** Xia, Q., Zheng, N., Heitman, J. L., & Shi, W. (2022). Soil pore size distribution shaped not only compositions but also networks of the soil microbial community. *Applied Soil Ecology*, 170, 104273. https://doi.org/10.1016/j.apsoil.2021.104273
- `Watson_Wyatt_2025` **[W]** Watson, K. L., & Wyatt, B. M. (2025). Using X-ray computed tomography to quantify pore characteristics in a shrink-swell clay. *Agrosystems, Geosciences & Environment*, 8(3), e70196. https://doi.org/10.1002/agg2.70196

## 8. Read during the project, not cited in the final write-up

- `Yudina_Kuzyakov_2023` Yudina, A., & Kuzyakov, Y. (2023). Dual nature of soil structure: The unity of aggregates and pores. *Geoderma*. https://doi.org/10.1016/j.geoderma.2023.116478
- `Dinka_2013` Dinka, T. M., Morgan, C. L. S., McInnes, K. J., Kishné, A. Sz., & Harmel, R. D. (2013). Shrink–swell behavior of soil across a Vertisol catena. *Journal of Hydrology*. https://doi.org/10.1016/j.jhydrol.2012.11.002

## Software

nnU-Net v2, napari, scikit-image, SciPy, PoreSpy and OpenPNM. Upstream citations and tooling notes are in [`RESOURCES.md`](../RESOURCES.md).
