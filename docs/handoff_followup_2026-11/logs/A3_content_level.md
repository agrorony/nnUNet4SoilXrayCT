## A3 images: Pearson r (z-scored, stride 2, identity orientation)

0: `Cu011_samp_2/img` (650, 650, 822)
1: `Rehovot_samp2_highkV_Cu0.11_15um/img` (650, 650, 650)
2: `Rehovot_samp3_highkV_Cu0.11_15um/img` (650, 650, 650)
3: `bnei_reem_fresh_bnei_reem_i4/img.tif` (652, 650, 650)
4: `bnei_reem_specA_unified/img` (650, 650, 650)
5: `bnei_reem_specB_unified/img` (650, 650, 650)
6: `mishmar_hanegev_maoz_2_8p8um/img` (1000, 1000, 1000)
7: `mishmar_hanegev_maoz_3_5p85um/img` (1000, 1000, 1000)
8: `bnei_reem_i4/imagesTr/nlm_volume_0000` (650, 650, 99)
9: `mishmar_loess_i2/imagesTr/mishmar_hanegev_maoz_3_5p85um_0000` (1000, 1000, 98)

| | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | — | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c |
| 1 | n/c | — | 0.0122 | n/c | 0.0022 | 0.0205 | n/c | n/c | n/c | n/c |
| 2 | n/c | 0.0122 | — | n/c | 0.0009 | 0.0051 | n/c | n/c | n/c | n/c |
| 3 | n/c | n/c | n/c | — | n/c | n/c | n/c | n/c | n/c | n/c |
| 4 | n/c | 0.0022 | 0.0009 | n/c | — | -0.0120 | n/c | n/c | n/c | n/c |
| 5 | n/c | 0.0205 | 0.0051 | n/c | -0.0120 | — | n/c | n/c | n/c | n/c |
| 6 | n/c | n/c | n/c | n/c | n/c | n/c | — | 0.0638 | n/c | n/c |
| 7 | n/c | n/c | n/c | n/c | n/c | n/c | 0.0638 | — | n/c | n/c |
| 8 | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | — | n/c |
| 9 | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | — |

### A3 images: best over 48 signed axis permutations x crop offsets (stride 4), compatible pairs

| a | b | identity | best | perm | flips | offset a | offset b |
|---|---|---|---|---|---|---|---|
| `bnei_reem_fresh_bnei_reem_i4/img.tif` | `bnei_reem_specB_unified/img` | 0.1334 | 0.9999 | [2, 1, 0] | [False, False, False] | [0, 0, 0] | [0, 0, 0] |
| `mishmar_hanegev_maoz_2_8p8um/img` | `mishmar_hanegev_maoz_3_5p85um/img` | 0.0641 | 0.0641 | [0, 1, 2] | [False, False, False] | [0, 0, 0] | [0, 0, 0] |
| `bnei_reem_fresh_bnei_reem_i4/img.tif` | `bnei_reem_specA_unified/img` | -0.0305 | -0.0564 | [1, 0, 2] | [True, True, True] | [2, 0, 0] | [0, 0, 0] |
| `bnei_reem_specA_unified/img` | `bnei_reem_specB_unified/img` | -0.0119 | -0.0557 | [1, 2, 0] | [True, True, True] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp2_highkV_Cu0.11_15um/img` | `bnei_reem_fresh_bnei_reem_i4/img.tif` | 0.0069 | 0.0434 | [1, 2, 0] | [True, True, True] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp2_highkV_Cu0.11_15um/img` | `bnei_reem_specB_unified/img` | 0.0207 | 0.0433 | [1, 0, 2] | [True, True, True] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp3_highkV_Cu0.11_15um/img` | `bnei_reem_fresh_bnei_reem_i4/img.tif` | 0.0012 | 0.0388 | [2, 1, 0] | [False, True, True] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp3_highkV_Cu0.11_15um/img` | `bnei_reem_specB_unified/img` | 0.0054 | 0.0385 | [0, 1, 2] | [False, True, True] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp3_highkV_Cu0.11_15um/img` | `bnei_reem_specA_unified/img` | 0.0011 | -0.0202 | [0, 2, 1] | [True, True, True] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp2_highkV_Cu0.11_15um/img` | `Rehovot_samp3_highkV_Cu0.11_15um/img` | 0.0123 | 0.0167 | [1, 0, 2] | [True, True, False] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp2_highkV_Cu0.11_15um/img` | `bnei_reem_specA_unified/img` | 0.0023 | -0.0133 | [0, 2, 1] | [True, True, False] | [0, 0, 0] | [0, 0, 0] |

## A3 segs: pore Dice (stride 2, identity orientation)

0: `Cu011_samp_2/segmentation` (650, 650, 822) pore=5
1: `Rehovot_samp2_highkV_Cu0.11_15um/segmentation_nnunet_bnei_reem_i4` (650, 650, 650) pore=5
2: `Rehovot_samp2_highkV_Cu0.11_15um/segmentation_nnunet_loess_i2` (650, 650, 650) pore=5
3: `Rehovot_samp2_highkV_Cu0.11_15um/segmentation_otsu.npy` (650, 650, 650) pore=1
4: `Rehovot_samp3_highkV_Cu0.11_15um/segmentation_nnunet_bnei_reem_i4` (650, 650, 650) pore=5
5: `Rehovot_samp3_highkV_Cu0.11_15um/segmentation_nnunet_loess_i2` (650, 650, 650) pore=5
6: `Rehovot_samp3_highkV_Cu0.11_15um/segmentation_otsu.npy` (650, 650, 650) pore=1
7: `bnei_reem_fresh_bnei_reem_i4/segmentation` (650, 650, 652) pore=5
8: `bnei_reem_specA_unified/segmentation` (650, 650, 650) pore=5
9: `bnei_reem_specB_unified/segmentation` (650, 650, 650) pore=5
10: `mishmar_hanegev_maoz_2_8p8um/segmentation` (1000, 1000, 1000) pore=5
11: `mishmar_hanegev_maoz_2_8p8um/segmentation_15um_pom` (587, 587, 587) pore=5
12: `mishmar_hanegev_maoz_2_8p8um/segmentation_15um_trackE` (947, 947, 947) pore=5
13: `mishmar_hanegev_maoz_3_5p85um/segmentation` (1000, 1000, 1000) pore=5
14: `mishmar_hanegev_maoz_3_5p85um/segmentation_15um_pom` (390, 390, 390) pore=5
15: `mishmar_hanegev_maoz_3_5p85um/segmentation_15um_trackE` (474, 474, 474) pore=5
16: `bnei_reem_i4/labelsTr/nlm_volume` (650, 650, 99) pore=5
17: `bnei_reem_i4//annotations_i2` (650, 650, 652) pore=6
18: `bnei_reem_i4//annotations_i3` (650, 650, 652) pore=6
19: `bnei_reem_i4//fine_tuning_annotations` (650, 650, 652) pore=6
20: `bnei_reem_i4//POM_GT` (650, 650, 652) pore=6
21: `bnei_reem_i4//less_reliable_solid_pores_GT` (650, 650, 652) pore=6
22: `bnei_reem_i4//merged_GT` (650, 650, 652) pore=6
23: `mishmar_loess_i2/labelsTr/mishmar_hanegev_maoz_3_5p85um` (1000, 1000, 98) pore=5
24: `mishmar_loess_i2//mishmar_hanegev_maoz_3_5p85um-1` (1000, 1000, 1000) pore=6
25: `mishmar_loess_i2//mishmar_hanegev_maoz_3_5p85um` (1000, 1000, 1000) pore=6
26: `bnei_reem_i4/validation/nlm_volume` (650, 650, 99) pore=5
27: `mishmar_loess_i2/validation/mishmar_hanegev_maoz_3_5p85um` (1000, 1000, 98) pore=5

| | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 | 22 | 23 | 24 | 25 | 26 | 27 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | — | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c |
| 1 | n/c | — | 0.9581 | 0.2897 | 0.3198 | 0.3237 | 0.3278 | n/c | 0.1935 | 0.2464 | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c |
| 2 | n/c | 0.9581 | — | 0.2907 | 0.3213 | 0.3253 | 0.3292 | n/c | 0.1946 | 0.2468 | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c |
| 3 | n/c | 0.2897 | 0.2907 | — | 0.3397 | 0.3443 | 0.3529 | n/c | 0.2033 | 0.2610 | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c |
| 4 | n/c | 0.3198 | 0.3213 | 0.3397 | — | 0.9703 | 0.3968 | n/c | 0.2153 | 0.2783 | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c |
| 5 | n/c | 0.3237 | 0.3253 | 0.3443 | 0.9703 | — | 0.4025 | n/c | 0.2174 | 0.2812 | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c |
| 6 | n/c | 0.3278 | 0.3292 | 0.3529 | 0.3968 | 0.4025 | — | n/c | 0.2243 | 0.2889 | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c |
| 7 | n/c | n/c | n/c | n/c | n/c | n/c | n/c | — | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | 0.0076 | 0.0104 | 0.0015 | 0.0000 | 0.0054 | 0.0054 | n/c | n/c | n/c | n/c | n/c |
| 8 | n/c | 0.1935 | 0.1946 | 0.2033 | 0.2153 | 0.2174 | 0.2243 | n/c | — | 0.1678 | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c |
| 9 | n/c | 0.2464 | 0.2468 | 0.2610 | 0.2783 | 0.2812 | 0.2889 | n/c | 0.1678 | — | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c |
| 10 | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | — | n/c | n/c | 0.2635 | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | 0.0002 | 0.0010 | n/c | n/c |
| 11 | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | — | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c |
| 12 | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | — | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c |
| 13 | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | 0.2635 | n/c | n/c | — | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | 0.0004 | 0.0009 | n/c | n/c |
| 14 | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | — | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c |
| 15 | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | — | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c |
| 16 | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | — | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | 0.0368 | n/c |
| 17 | n/c | n/c | n/c | n/c | n/c | n/c | n/c | 0.0076 | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | — | 0.8777 | 0.0000 | 0.0000 | 0.8263 | 0.8320 | n/c | n/c | n/c | n/c | n/c |
| 18 | n/c | n/c | n/c | n/c | n/c | n/c | n/c | 0.0104 | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | 0.8777 | — | 0.2079 | 0.0000 | 0.7102 | 0.7155 | n/c | n/c | n/c | n/c | n/c |
| 19 | n/c | n/c | n/c | n/c | n/c | n/c | n/c | 0.0015 | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | 0.0000 | 0.2079 | — | 0.0000 | 0.0000 | 0.0000 | n/c | n/c | n/c | n/c | n/c |
| 20 | n/c | n/c | n/c | n/c | n/c | n/c | n/c | 0.0000 | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | 0.0000 | 0.0000 | 0.0000 | — | 0.0000 | 0.0000 | n/c | n/c | n/c | n/c | n/c |
| 21 | n/c | n/c | n/c | n/c | n/c | n/c | n/c | 0.0054 | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | 0.8263 | 0.7102 | 0.0000 | 0.0000 | — | 0.9941 | n/c | n/c | n/c | n/c | n/c |
| 22 | n/c | n/c | n/c | n/c | n/c | n/c | n/c | 0.0054 | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | 0.8320 | 0.7155 | 0.0000 | 0.0000 | 0.9941 | — | n/c | n/c | n/c | n/c | n/c |
| 23 | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | — | n/c | n/c | n/c | 0.0368 |
| 24 | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | 0.0002 | n/c | n/c | 0.0004 | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | — | 0.0000 | n/c | n/c |
| 25 | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | 0.0010 | n/c | n/c | 0.0009 | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | 0.0000 | — | n/c | n/c |
| 26 | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | 0.0368 | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | — | n/c |
| 27 | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | n/c | 0.0368 | n/c | n/c | n/c | — |

### A3 segs: best over 48 signed axis permutations x crop offsets (stride 4), compatible pairs

| a | b | identity | best | perm | flips | offset a | offset b |
|---|---|---|---|---|---|---|---|
| `bnei_reem_i4//less_reliable_solid_pores_GT` | `bnei_reem_i4//merged_GT` | 0.9948 | 0.9948 | [0, 1, 2] | [False, False, False] | [0, 0, 0] | [0, 0, 0] |
| `bnei_reem_fresh_bnei_reem_i4/segmentation` | `bnei_reem_specB_unified/segmentation` | 0.9883 | 0.9883 | [0, 1, 2] | [False, False, False] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp3_highkV_Cu0.11_15um/segmentation_nnunet_bnei_reem_i4` | `Rehovot_samp3_highkV_Cu0.11_15um/segmentation_nnunet_loess_i2` | 0.9699 | 0.9699 | [0, 1, 2] | [False, False, False] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp3_highkV_Cu0.11_15um/segmentation_nnunet_loess_i2` | `Rehovot_samp3_highkV_Cu0.11_15um/segmentation_otsu.npy` | 0.4019 | 0.9622 | [2, 1, 0] | [False, True, False] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp2_highkV_Cu0.11_15um/segmentation_nnunet_bnei_reem_i4` | `Rehovot_samp2_highkV_Cu0.11_15um/segmentation_nnunet_loess_i2` | 0.9577 | 0.9577 | [0, 1, 2] | [False, False, False] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp3_highkV_Cu0.11_15um/segmentation_nnunet_bnei_reem_i4` | `Rehovot_samp3_highkV_Cu0.11_15um/segmentation_otsu.npy` | 0.3963 | 0.9521 | [2, 1, 0] | [False, True, False] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp2_highkV_Cu0.11_15um/segmentation_nnunet_loess_i2` | `Rehovot_samp2_highkV_Cu0.11_15um/segmentation_otsu.npy` | 0.2906 | 0.9288 | [2, 1, 0] | [False, True, False] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp2_highkV_Cu0.11_15um/segmentation_nnunet_bnei_reem_i4` | `Rehovot_samp2_highkV_Cu0.11_15um/segmentation_otsu.npy` | 0.2894 | 0.9178 | [2, 1, 0] | [False, True, False] | [0, 0, 0] | [0, 0, 0] |
| `bnei_reem_i4//annotations_i2` | `bnei_reem_i4//annotations_i3` | 0.7444 | 0.7444 | [0, 1, 2] | [False, False, False] | [0, 0, 0] | [0, 0, 0] |
| `bnei_reem_i4//annotations_i2` | `bnei_reem_i4//merged_GT` | 0.7403 | 0.7403 | [0, 1, 2] | [False, False, False] | [0, 0, 0] | [0, 0, 0] |
| `bnei_reem_i4//annotations_i2` | `bnei_reem_i4//less_reliable_solid_pores_GT` | 0.7355 | 0.7355 | [0, 1, 2] | [False, False, False] | [0, 0, 0] | [0, 0, 0] |
| `bnei_reem_i4//annotations_i3` | `bnei_reem_i4//merged_GT` | 0.5168 | 0.5168 | [0, 1, 2] | [False, False, False] | [0, 0, 0] | [0, 0, 0] |
| `bnei_reem_i4//annotations_i3` | `bnei_reem_i4//less_reliable_solid_pores_GT` | 0.5129 | 0.5129 | [0, 1, 2] | [False, False, False] | [0, 0, 0] | [0, 0, 0] |
| `bnei_reem_i4//annotations_i3` | `bnei_reem_i4//fine_tuning_annotations` | 0.3568 | 0.3568 | [0, 1, 2] | [False, False, False] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp2_highkV_Cu0.11_15um/segmentation_otsu.npy` | `Rehovot_samp3_highkV_Cu0.11_15um/segmentation_otsu.npy` | 0.3524 | 0.3537 | [0, 1, 2] | [False, False, True] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp2_highkV_Cu0.11_15um/segmentation_otsu.npy` | `Rehovot_samp3_highkV_Cu0.11_15um/segmentation_nnunet_loess_i2` | 0.3438 | 0.3468 | [2, 0, 1] | [True, True, False] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp2_highkV_Cu0.11_15um/segmentation_otsu.npy` | `Rehovot_samp3_highkV_Cu0.11_15um/segmentation_nnunet_bnei_reem_i4` | 0.3394 | 0.3428 | [2, 0, 1] | [False, True, False] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp2_highkV_Cu0.11_15um/segmentation_nnunet_loess_i2` | `Rehovot_samp3_highkV_Cu0.11_15um/segmentation_otsu.npy` | 0.3286 | 0.3321 | [2, 1, 0] | [True, True, False] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp2_highkV_Cu0.11_15um/segmentation_nnunet_bnei_reem_i4` | `Rehovot_samp3_highkV_Cu0.11_15um/segmentation_otsu.npy` | 0.3273 | 0.3300 | [1, 2, 0] | [True, False, False] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp2_highkV_Cu0.11_15um/segmentation_nnunet_loess_i2` | `Rehovot_samp3_highkV_Cu0.11_15um/segmentation_nnunet_loess_i2` | 0.3252 | 0.3264 | [1, 0, 2] | [False, False, True] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp2_highkV_Cu0.11_15um/segmentation_nnunet_bnei_reem_i4` | `Rehovot_samp3_highkV_Cu0.11_15um/segmentation_nnunet_loess_i2` | 0.3235 | 0.3246 | [1, 0, 2] | [False, False, False] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp2_highkV_Cu0.11_15um/segmentation_nnunet_loess_i2` | `Rehovot_samp3_highkV_Cu0.11_15um/segmentation_nnunet_bnei_reem_i4` | 0.3212 | 0.3226 | [1, 0, 2] | [False, False, True] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp2_highkV_Cu0.11_15um/segmentation_nnunet_bnei_reem_i4` | `Rehovot_samp3_highkV_Cu0.11_15um/segmentation_nnunet_bnei_reem_i4` | 0.3198 | 0.3210 | [1, 0, 2] | [False, False, False] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp3_highkV_Cu0.11_15um/segmentation_otsu.npy` | `bnei_reem_fresh_bnei_reem_i4/segmentation` | 0.2885 | 0.2942 | [2, 0, 1] | [False, True, False] | [0, 0, 0] | [2, 0, 0] |
| `Rehovot_samp3_highkV_Cu0.11_15um/segmentation_otsu.npy` | `bnei_reem_specB_unified/segmentation` | 0.2886 | 0.2939 | [2, 0, 1] | [False, True, False] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp3_highkV_Cu0.11_15um/segmentation_nnunet_loess_i2` | `bnei_reem_specB_unified/segmentation` | 0.2812 | 0.2876 | [2, 0, 1] | [True, True, False] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp3_highkV_Cu0.11_15um/segmentation_nnunet_loess_i2` | `bnei_reem_fresh_bnei_reem_i4/segmentation` | 0.2812 | 0.2875 | [2, 0, 1] | [True, True, False] | [0, 0, 0] | [1, 0, 0] |
| `Rehovot_samp3_highkV_Cu0.11_15um/segmentation_nnunet_bnei_reem_i4` | `bnei_reem_specB_unified/segmentation` | 0.2783 | 0.2852 | [2, 0, 1] | [True, True, False] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp3_highkV_Cu0.11_15um/segmentation_nnunet_bnei_reem_i4` | `bnei_reem_fresh_bnei_reem_i4/segmentation` | 0.2783 | 0.2851 | [2, 0, 1] | [True, True, False] | [0, 0, 0] | [1, 0, 0] |
| `Rehovot_samp2_highkV_Cu0.11_15um/segmentation_otsu.npy` | `bnei_reem_fresh_bnei_reem_i4/segmentation` | 0.2604 | 0.2688 | [2, 0, 1] | [True, True, False] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp2_highkV_Cu0.11_15um/segmentation_otsu.npy` | `bnei_reem_specB_unified/segmentation` | 0.2604 | 0.2684 | [2, 0, 1] | [True, True, False] | [0, 0, 0] | [0, 0, 0] |
| `mishmar_hanegev_maoz_2_8p8um/segmentation` | `mishmar_hanegev_maoz_3_5p85um/segmentation` | 0.2634 | 0.2634 | [0, 1, 2] | [False, False, False] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp2_highkV_Cu0.11_15um/segmentation_nnunet_loess_i2` | `bnei_reem_fresh_bnei_reem_i4/segmentation` | 0.2467 | 0.2517 | [1, 0, 2] | [False, False, True] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp2_highkV_Cu0.11_15um/segmentation_nnunet_loess_i2` | `bnei_reem_specB_unified/segmentation` | 0.2467 | 0.2514 | [1, 0, 2] | [False, False, True] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp2_highkV_Cu0.11_15um/segmentation_nnunet_bnei_reem_i4` | `bnei_reem_fresh_bnei_reem_i4/segmentation` | 0.2463 | 0.2502 | [1, 0, 2] | [False, False, True] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp2_highkV_Cu0.11_15um/segmentation_nnunet_bnei_reem_i4` | `bnei_reem_specB_unified/segmentation` | 0.2463 | 0.2499 | [1, 0, 2] | [False, False, True] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp3_highkV_Cu0.11_15um/segmentation_otsu.npy` | `bnei_reem_specA_unified/segmentation` | 0.2248 | 0.2248 | [0, 1, 2] | [False, False, False] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp3_highkV_Cu0.11_15um/segmentation_nnunet_loess_i2` | `bnei_reem_specA_unified/segmentation` | 0.2176 | 0.2220 | [2, 1, 0] | [False, True, False] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp3_highkV_Cu0.11_15um/segmentation_nnunet_bnei_reem_i4` | `bnei_reem_specA_unified/segmentation` | 0.2156 | 0.2203 | [2, 1, 0] | [False, True, False] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp2_highkV_Cu0.11_15um/segmentation_otsu.npy` | `bnei_reem_specA_unified/segmentation` | 0.2039 | 0.2058 | [0, 1, 2] | [True, True, True] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp2_highkV_Cu0.11_15um/segmentation_nnunet_loess_i2` | `bnei_reem_specA_unified/segmentation` | 0.1950 | 0.1992 | [2, 1, 0] | [True, False, True] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp2_highkV_Cu0.11_15um/segmentation_nnunet_bnei_reem_i4` | `bnei_reem_specA_unified/segmentation` | 0.1941 | 0.1990 | [2, 1, 0] | [True, False, True] | [0, 0, 0] | [0, 0, 0] |
| `bnei_reem_fresh_bnei_reem_i4/segmentation` | `bnei_reem_specA_unified/segmentation` | 0.1683 | 0.1939 | [1, 2, 0] | [True, True, False] | [0, 0, 0] | [0, 0, 0] |
| `bnei_reem_specA_unified/segmentation` | `bnei_reem_specB_unified/segmentation` | 0.1683 | 0.1934 | [2, 0, 1] | [False, True, True] | [0, 0, 0] | [0, 0, 0] |
| `mishmar_loess_i2/labelsTr/mishmar_hanegev_maoz_3_5p85um` | `mishmar_loess_i2/validation/mishmar_hanegev_maoz_3_5p85um` | 0.0708 | 0.0708 | [0, 1, 2] | [False, False, False] | [0, 0, 0] | [0, 0, 0] |
| `bnei_reem_fresh_bnei_reem_i4/segmentation` | `bnei_reem_i4//annotations_i3` | 0.0118 | 0.0545 | [0, 1, 2] | [False, True, False] | [0, 0, 0] | [0, 0, 0] |
| `bnei_reem_specB_unified/segmentation` | `bnei_reem_i4//annotations_i3` | 0.0118 | 0.0545 | [0, 1, 2] | [False, True, False] | [0, 0, 0] | [0, 0, 0] |
| `bnei_reem_specB_unified/segmentation` | `bnei_reem_i4//annotations_i2` | 0.0062 | 0.0459 | [0, 1, 2] | [False, True, False] | [0, 0, 0] | [0, 0, 2] |
| `bnei_reem_specB_unified/segmentation` | `bnei_reem_i4//merged_GT` | 0.0037 | 0.0374 | [0, 1, 2] | [False, True, False] | [0, 0, 0] | [0, 0, 2] |
| `bnei_reem_specB_unified/segmentation` | `bnei_reem_i4//less_reliable_solid_pores_GT` | 0.0036 | 0.0369 | [0, 1, 2] | [False, True, False] | [0, 0, 0] | [0, 0, 2] |
| `bnei_reem_fresh_bnei_reem_i4/segmentation` | `bnei_reem_i4//annotations_i2` | 0.0062 | 0.0326 | [0, 1, 2] | [False, True, False] | [0, 0, 0] | [0, 0, 0] |
| `bnei_reem_fresh_bnei_reem_i4/segmentation` | `bnei_reem_i4//merged_GT` | 0.0036 | 0.0195 | [0, 1, 2] | [False, True, False] | [0, 0, 0] | [0, 0, 0] |
| `bnei_reem_fresh_bnei_reem_i4/segmentation` | `bnei_reem_i4//less_reliable_solid_pores_GT` | 0.0036 | 0.0194 | [0, 1, 2] | [False, True, False] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp2_highkV_Cu0.11_15um/segmentation_otsu.npy` | `bnei_reem_i4//annotations_i3` | 0.0122 | 0.0135 | [2, 1, 0] | [False, True, True] | [0, 0, 0] | [0, 0, 0] |
| `bnei_reem_specA_unified/segmentation` | `bnei_reem_i4//annotations_i3` | 0.0118 | 0.0135 | [2, 0, 1] | [False, True, True] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp3_highkV_Cu0.11_15um/segmentation_nnunet_bnei_reem_i4` | `bnei_reem_i4//annotations_i3` | 0.0129 | 0.0133 | [1, 2, 0] | [False, False, True] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp3_highkV_Cu0.11_15um/segmentation_nnunet_loess_i2` | `bnei_reem_i4//annotations_i3` | 0.0128 | 0.0133 | [0, 2, 1] | [True, False, True] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp3_highkV_Cu0.11_15um/segmentation_otsu.npy` | `bnei_reem_i4//annotations_i3` | 0.0122 | 0.0132 | [1, 2, 0] | [True, False, True] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp2_highkV_Cu0.11_15um/segmentation_nnunet_loess_i2` | `bnei_reem_i4//annotations_i3` | 0.0122 | 0.0129 | [0, 1, 2] | [True, False, False] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp2_highkV_Cu0.11_15um/segmentation_nnunet_bnei_reem_i4` | `bnei_reem_i4//annotations_i3` | 0.0123 | 0.0129 | [2, 1, 0] | [True, False, False] | [0, 0, 0] | [2, 0, 0] |
| `bnei_reem_specA_unified/segmentation` | `bnei_reem_i4//annotations_i2` | 0.0068 | 0.0125 | [2, 1, 0] | [True, True, True] | [0, 0, 0] | [1, 0, 0] |
| `bnei_reem_fresh_bnei_reem_i4/segmentation` | `bnei_reem_i4//fine_tuning_annotations` | 0.0030 | 0.0123 | [0, 1, 2] | [False, True, False] | [0, 0, 0] | [0, 0, 0] |
| `bnei_reem_specB_unified/segmentation` | `bnei_reem_i4//fine_tuning_annotations` | 0.0030 | 0.0123 | [0, 1, 2] | [False, True, False] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp3_highkV_Cu0.11_15um/segmentation_otsu.npy` | `bnei_reem_i4//annotations_i2` | 0.0070 | 0.0117 | [2, 1, 0] | [True, False, True] | [0, 0, 0] | [1, 0, 0] |
| `Rehovot_samp2_highkV_Cu0.11_15um/segmentation_otsu.npy` | `bnei_reem_i4//annotations_i2` | 0.0071 | 0.0117 | [2, 1, 0] | [False, True, True] | [0, 0, 0] | [2, 0, 0] |
| `Rehovot_samp3_highkV_Cu0.11_15um/segmentation_nnunet_bnei_reem_i4` | `bnei_reem_i4//annotations_i2` | 0.0076 | 0.0114 | [0, 1, 2] | [True, True, True] | [0, 0, 0] | [0, 0, 1] |
| `Rehovot_samp3_highkV_Cu0.11_15um/segmentation_nnunet_loess_i2` | `bnei_reem_i4//annotations_i2` | 0.0076 | 0.0114 | [0, 1, 2] | [True, True, True] | [0, 0, 0] | [0, 0, 1] |
| `Rehovot_samp2_highkV_Cu0.11_15um/segmentation_nnunet_bnei_reem_i4` | `bnei_reem_i4//annotations_i2` | 0.0073 | 0.0113 | [2, 1, 0] | [True, False, False] | [0, 0, 0] | [1, 0, 0] |
| `Rehovot_samp2_highkV_Cu0.11_15um/segmentation_nnunet_loess_i2` | `bnei_reem_i4//annotations_i2` | 0.0073 | 0.0113 | [1, 0, 2] | [False, True, True] | [0, 0, 0] | [0, 0, 1] |
| `bnei_reem_specA_unified/segmentation` | `bnei_reem_i4//merged_GT` | 0.0037 | 0.0102 | [2, 0, 1] | [False, True, False] | [0, 0, 0] | [2, 0, 0] |
| `bnei_reem_specA_unified/segmentation` | `bnei_reem_i4//less_reliable_solid_pores_GT` | 0.0037 | 0.0101 | [2, 0, 1] | [False, True, False] | [0, 0, 0] | [2, 0, 0] |
| `Rehovot_samp2_highkV_Cu0.11_15um/segmentation_otsu.npy` | `bnei_reem_i4//merged_GT` | 0.0046 | 0.0096 | [2, 0, 1] | [True, True, True] | [0, 0, 0] | [1, 0, 0] |
| `Rehovot_samp2_highkV_Cu0.11_15um/segmentation_otsu.npy` | `bnei_reem_i4//less_reliable_solid_pores_GT` | 0.0045 | 0.0096 | [0, 1, 2] | [False, True, True] | [0, 0, 0] | [0, 0, 1] |
| `Rehovot_samp3_highkV_Cu0.11_15um/segmentation_otsu.npy` | `bnei_reem_i4//merged_GT` | 0.0041 | 0.0096 | [2, 1, 0] | [True, False, True] | [0, 0, 0] | [1, 0, 0] |
| `bnei_reem_i4//fine_tuning_annotations` | `bnei_reem_i4//less_reliable_solid_pores_GT` | 0.0000 | 0.0095 | [1, 2, 0] | [False, False, False] | [0, 0, 0] | [0, 1, 0] |
| `Rehovot_samp3_highkV_Cu0.11_15um/segmentation_otsu.npy` | `bnei_reem_i4//less_reliable_solid_pores_GT` | 0.0041 | 0.0095 | [2, 1, 0] | [True, False, True] | [0, 0, 0] | [1, 0, 0] |
| `bnei_reem_i4//fine_tuning_annotations` | `bnei_reem_i4//merged_GT` | 0.0000 | 0.0094 | [1, 2, 0] | [False, False, False] | [0, 0, 0] | [0, 1, 0] |
| `Rehovot_samp2_highkV_Cu0.11_15um/segmentation_nnunet_bnei_reem_i4` | `bnei_reem_i4//merged_GT` | 0.0043 | 0.0094 | [2, 1, 0] | [True, False, False] | [0, 0, 0] | [1, 0, 0] |
| `Rehovot_samp3_highkV_Cu0.11_15um/segmentation_nnunet_bnei_reem_i4` | `bnei_reem_i4//merged_GT` | 0.0046 | 0.0094 | [0, 1, 2] | [True, True, True] | [0, 0, 0] | [0, 0, 1] |
| `Rehovot_samp2_highkV_Cu0.11_15um/segmentation_nnunet_loess_i2` | `bnei_reem_i4//merged_GT` | 0.0042 | 0.0093 | [2, 1, 0] | [True, False, False] | [0, 0, 0] | [1, 0, 0] |
| `Rehovot_samp2_highkV_Cu0.11_15um/segmentation_nnunet_bnei_reem_i4` | `bnei_reem_i4//less_reliable_solid_pores_GT` | 0.0042 | 0.0093 | [2, 1, 0] | [True, False, False] | [0, 0, 0] | [1, 0, 0] |
| `Rehovot_samp3_highkV_Cu0.11_15um/segmentation_nnunet_bnei_reem_i4` | `bnei_reem_i4//less_reliable_solid_pores_GT` | 0.0046 | 0.0093 | [0, 1, 2] | [True, True, True] | [0, 0, 0] | [0, 0, 1] |
| `Rehovot_samp3_highkV_Cu0.11_15um/segmentation_nnunet_loess_i2` | `bnei_reem_i4//merged_GT` | 0.0046 | 0.0093 | [0, 1, 2] | [True, True, True] | [0, 0, 0] | [0, 0, 1] |
| `Rehovot_samp2_highkV_Cu0.11_15um/segmentation_nnunet_loess_i2` | `bnei_reem_i4//less_reliable_solid_pores_GT` | 0.0042 | 0.0092 | [2, 1, 0] | [True, False, False] | [0, 0, 0] | [1, 0, 0] |
| `Rehovot_samp3_highkV_Cu0.11_15um/segmentation_nnunet_loess_i2` | `bnei_reem_i4//less_reliable_solid_pores_GT` | 0.0045 | 0.0092 | [0, 1, 2] | [True, True, True] | [0, 0, 0] | [0, 0, 1] |
| `bnei_reem_i4//annotations_i2` | `bnei_reem_i4//fine_tuning_annotations` | 0.0000 | 0.0070 | [2, 0, 1] | [False, False, False] | [0, 0, 1] | [0, 0, 0] |
| `mishmar_hanegev_maoz_3_5p85um/segmentation` | `mishmar_loess_i2//mishmar_hanegev_maoz_3_5p85um` | 0.0018 | 0.0069 | [0, 1, 2] | [False, True, False] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp3_highkV_Cu0.11_15um/segmentation_nnunet_bnei_reem_i4` | `bnei_reem_i4//fine_tuning_annotations` | 0.0030 | 0.0041 | [1, 2, 0] | [True, False, True] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp3_highkV_Cu0.11_15um/segmentation_nnunet_loess_i2` | `bnei_reem_i4//fine_tuning_annotations` | 0.0029 | 0.0041 | [1, 2, 0] | [True, False, True] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp3_highkV_Cu0.11_15um/segmentation_otsu.npy` | `bnei_reem_i4//fine_tuning_annotations` | 0.0029 | 0.0040 | [0, 2, 1] | [True, True, True] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp2_highkV_Cu0.11_15um/segmentation_otsu.npy` | `bnei_reem_i4//fine_tuning_annotations` | 0.0028 | 0.0033 | [1, 0, 2] | [True, False, False] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp2_highkV_Cu0.11_15um/segmentation_nnunet_bnei_reem_i4` | `bnei_reem_i4//fine_tuning_annotations` | 0.0025 | 0.0032 | [2, 0, 1] | [False, True, True] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp2_highkV_Cu0.11_15um/segmentation_nnunet_loess_i2` | `bnei_reem_i4//fine_tuning_annotations` | 0.0025 | 0.0032 | [2, 0, 1] | [False, True, True] | [0, 0, 0] | [0, 0, 0] |
| `bnei_reem_specA_unified/segmentation` | `bnei_reem_i4//fine_tuning_annotations` | 0.0027 | 0.0029 | [0, 2, 1] | [False, False, False] | [0, 0, 0] | [0, 0, 0] |
| `mishmar_loess_i2//mishmar_hanegev_maoz_3_5p85um-1` | `mishmar_loess_i2//mishmar_hanegev_maoz_3_5p85um` | 0.0000 | 0.0026 | [2, 0, 1] | [True, True, True] | [0, 0, 0] | [0, 0, 0] |
| `mishmar_hanegev_maoz_2_8p8um/segmentation` | `mishmar_loess_i2//mishmar_hanegev_maoz_3_5p85um` | 0.0020 | 0.0023 | [2, 1, 0] | [True, True, False] | [0, 0, 0] | [0, 0, 0] |
| `mishmar_hanegev_maoz_3_5p85um/segmentation` | `mishmar_loess_i2//mishmar_hanegev_maoz_3_5p85um-1` | 0.0008 | 0.0022 | [0, 1, 2] | [False, True, False] | [0, 0, 0] | [0, 0, 0] |
| `mishmar_hanegev_maoz_2_8p8um/segmentation` | `mishmar_loess_i2//mishmar_hanegev_maoz_3_5p85um-1` | 0.0005 | 0.0007 | [2, 1, 0] | [False, True, True] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp2_highkV_Cu0.11_15um/segmentation_nnunet_bnei_reem_i4` | `bnei_reem_i4//POM_GT` | 0.0000 | 0.0000 | [0, 1, 2] | [False, False, False] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp2_highkV_Cu0.11_15um/segmentation_nnunet_loess_i2` | `bnei_reem_i4//POM_GT` | 0.0000 | 0.0000 | [0, 1, 2] | [False, False, False] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp2_highkV_Cu0.11_15um/segmentation_otsu.npy` | `bnei_reem_i4//POM_GT` | 0.0000 | 0.0000 | [0, 1, 2] | [False, False, False] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp3_highkV_Cu0.11_15um/segmentation_nnunet_bnei_reem_i4` | `bnei_reem_i4//POM_GT` | 0.0000 | 0.0000 | [0, 1, 2] | [False, False, False] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp3_highkV_Cu0.11_15um/segmentation_nnunet_loess_i2` | `bnei_reem_i4//POM_GT` | 0.0000 | 0.0000 | [0, 1, 2] | [False, False, False] | [0, 0, 0] | [0, 0, 0] |
| `Rehovot_samp3_highkV_Cu0.11_15um/segmentation_otsu.npy` | `bnei_reem_i4//POM_GT` | 0.0000 | 0.0000 | [0, 1, 2] | [False, False, False] | [0, 0, 0] | [0, 0, 0] |
| `bnei_reem_fresh_bnei_reem_i4/segmentation` | `bnei_reem_i4//POM_GT` | 0.0000 | 0.0000 | [0, 1, 2] | [False, False, False] | [0, 0, 0] | [0, 0, 0] |
| `bnei_reem_specA_unified/segmentation` | `bnei_reem_i4//POM_GT` | 0.0000 | 0.0000 | [0, 1, 2] | [False, False, False] | [0, 0, 0] | [0, 0, 0] |
| `bnei_reem_specB_unified/segmentation` | `bnei_reem_i4//POM_GT` | 0.0000 | 0.0000 | [0, 1, 2] | [False, False, False] | [0, 0, 0] | [0, 0, 0] |
| `bnei_reem_i4/labelsTr/nlm_volume` | `bnei_reem_i4/validation/nlm_volume` | 0.0000 | 0.0000 | [0, 1, 2] | [False, False, False] | [0, 0, 0] | [0, 0, 0] |
| `bnei_reem_i4//annotations_i2` | `bnei_reem_i4//POM_GT` | 0.0000 | 0.0000 | [0, 1, 2] | [False, False, False] | [0, 0, 0] | [0, 0, 0] |
| `bnei_reem_i4//annotations_i3` | `bnei_reem_i4//POM_GT` | 0.0000 | 0.0000 | [0, 1, 2] | [False, False, False] | [0, 0, 0] | [0, 0, 0] |
| `bnei_reem_i4//fine_tuning_annotations` | `bnei_reem_i4//POM_GT` | 0.0000 | 0.0000 | [0, 1, 2] | [False, False, False] | [0, 0, 0] | [0, 0, 0] |
| `bnei_reem_i4//POM_GT` | `bnei_reem_i4//less_reliable_solid_pores_GT` | 0.0000 | 0.0000 | [0, 1, 2] | [False, False, False] | [0, 0, 0] | [0, 0, 0] |
| `bnei_reem_i4//POM_GT` | `bnei_reem_i4//merged_GT` | 0.0000 | 0.0000 | [0, 1, 2] | [False, False, False] | [0, 0, 0] | [0, 0, 0] |
