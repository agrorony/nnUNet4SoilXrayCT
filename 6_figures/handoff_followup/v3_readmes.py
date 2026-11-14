"""Package v3, step 2: write every README in the v3 staging folder.

Scan, model, annotation, code and lab READMEs are the v2 READMEs with package paths changed to the v3 layout
(share paths keep their original folder names) and the "Used in the write-up for" sections rewritten from the traced
run inputs. The top-level, 05_results and 06_figures READMEs are new. Every replacement must match.

Usage: python v3_readmes.py <v2_package_dir> <v3_package_dir>
"""
import csv
import re
import sys
from pathlib import Path

SCANS = {
    'bnei_reem_specA_unified': '01_scans/vertisol_A',
    'bnei_reem_specB_unified': '01_scans/vertisol_B',
    'bnei_reem_fresh_bnei_reem_i4': '01_scans/vertisol_B/april_processing',
    'mishmar_hanegev_maoz_3_5p85um': '01_scans/loess_5p85um_maoz',
    'mishmar_hanegev_maoz_2_8p8um': '01_scans/loess_8p8um_maoz',
    'Cu011_samp_2': '01_scans/loess_samp2',
    'Rehovot_samp2_highkV_Cu0.11_15um': '01_scans/sand_samp2',
    'Rehovot_samp3_highkV_Cu0.11_15um': '01_scans/sand_samp3',
}
CODE_COMMIT = '87f2de4df66d1c1b569c8e1887690ebaaade89f7'   # main after PR #5 (2026-11-14)
CODE_ROW = ("| `nnUNet4SoilXrayCT_" + CODE_COMMIT[:7] + ".zip` | `git archive` of this project's repository at commit `" + CODE_COMMIT +
            "`, branch `main` (the merge of PR #5, 2026-11-14), made for v3 of this package (on GitHub: https://github.com/agrorony/nnUNet4SoilXrayCT/tree/" + CODE_COMMIT +
            "). The paths this package's READMEs cite follow this commit's layout (2026-11 restructure; its `archive/PATH_MAP_2026-11.csv` maps the older paths). "
            "v2 of the package shipped `nnUNet4SoilXrayCT_a01686e.zip` (commit `a01686ea9852742328a9fec07854d1ba7f5489ae`), v1 `nnUNet4SoilXrayCT_198c5b5.zip` "
            "(commit `198c5b5dc3da729954e9a5efc20aec6d208d3bad`, older layout) | `" + CODE_COMMIT + "` |")
TE = '05_results/connectivity/track_e'
CR = '05_results/connectivity/chi_r'
V2 = 'v2 package'

GENERIC = [  # applied to every README edited from v2 (package paths only)
    ('`03_models/bnei_reem_i4/`', '`03_models/vertisol_i4/`'),
    ('`03_models/mishmar_loess_i2/`', '`03_models/loess_i2/`'),
    ('"03_models/bnei_reem_i4/', '"03_models/vertisol_i4/'),
    ('"03_models/mishmar_loess_i2/', '"03_models/loess_i2/'),
    ('`01_volumes/bnei_reem_fresh_bnei_reem_i4/`', '`01_scans/vertisol_B/april_processing/`'),
    ('`01_volumes/mishmar_hanegev_maoz_3_5p85um/`', '`01_scans/loess_5p85um_maoz/`'),
    ('`01_volumes/*/README.md`', '`01_scans/*/README.md`'),
    ('`01_volumes/`', '`01_scans/`'),
    ('segmentation_nnunet_bnei_reem_i4', 'segmentation_nnunet_reference_bnei_reem_i4'),
    ('segmentation_nnunet_loess_i2', 'segmentation_nnunet_reference_loess_i2'),
    ('`missing_data_20261004/REPORT.md`', '`docs/missing_data_20261004_REPORT.md` (repo)'),
]

USED = {
'01_scans/vertisol_A': f"""Traced from each run's recorded input path (`config.json`, `input_path`), not from run names.
- **Graph 5b** (Γ vs visible porosity) and the Γ–porosity fit (R² = 0.91): Vertisol A point, porosity 15.17 %, Γ = 0.7549. Track E run `psd_diag_20260907T103058_bnei_reem_specA_unified` (input `nnUNet_resources\\bnei_reem_specA_unified\\inference_concatenated\\bnei_reem_specA_unified.nii.gz`): `{TE}/psd_diag_20260907T103058_bnei_reem_specA_unified/`.
- **Graph 5c** (r*): one of the two Vertisol scans shown as "no crossover in measured range"; χ(r) stays positive up to 1000 µm (`{CR}/chi_r_bnei_reem_specA_unified.csv`).
- **Tortuosity** (text): 23 of the Vertisol 200³ subvolumes (`05_results/tortuosity/tortuosity_subvolumes.csv`, `input_path` = this segmentation).
- **Graph 3** (segmentation examples): the Vertisol panel, slice z = 325 (`figure7_slice_info.json` in the repo's `6_figures/segmentation_examples/`).
- Not used for POM, pore-size classes or distances (those use `../vertisol_B/april_processing/`).""",
'01_scans/vertisol_B': "See *Which reported result used which processing* above.",
'01_scans/vertisol_B/april_processing': "This is the April 2026 processing of the Vertisol B scan. The table *Which reported result used which processing* in `../README.md` lists every reported result and the processing it used. From this processing: pore-size classes (graph 4), distances (graph 5a), POM interface metrics, POM sizes and Clark–Evans R (graph 6), and the 3D renders. It was also the training volume of the i4 model.",
'01_scans/loess_5p85um_maoz': f"""Traced from each run's recorded input path, not from run names.
- **Graph 4** (pore-size classes): the 8 Loess subvolumes come from `segmentation.nii.gz` (native 5.85 µm). `05_results/pore_size_classes/fig4_subvolumes/stats_summary.md`, *Data sources*: `mishmar_hanegev_maoz_3_5p85um/inference_output_concat_loess_i2/mishmar_hanegev_maoz_3_5p85um.nii.gz`; the path was reconciled by pore-voxel count, "high but not 100 % confidence". Resolution check (text): the same 8 subvolumes downsampled to 15 µm (`05_results/pore_size_classes/downsample_comparison.json`, `A2_summary.md`).
- **Graph 5a** (distances): run `psd_diag_20260803T010446_mishmar_hanegev_maoz_3_5p85um_scratch_i2` (`05_results/distances/…/summary_distance_metrics.json`). The run kept no `config.json`. Its name says `scratch_i2`, but the same full-volume batch is the one `stats_summary.md` reconciles to the `loess_i2` segmentation (this file) by pore-voxel count. **Not fully certain.**
- **Graph 5b/5c** (5.85→15 µm point: porosity 26.57 %, Γ = 0.9361, r* = 67.66 µm): `segmentation_15um_trackE.nii.gz`. Track E run `psd_diag_20260902T160041_mishmar_native_label_downsample_15um` (input `…\\pipeline_work\\mishmar_native_5p85um\\mishmar_native_5p85um_label_downsample.nii.gz`); χ(r) `{CR}/chi_r_mishmar_native_label_downsample_15um.csv`.
- **Tortuosity** (text): 21 Loess 200³ subvolumes of `segmentation_15um_trackE.nii.gz` (`input_path` in `tortuosity_subvolumes.csv`).
- **Graph 6** (POM interface metrics at ~15 µm): `segmentation_15um_pom.nii.gz` (input `…\\pom_analysis_20260824_ablation\\mishmar_label_downsample\\mishmar_label_downsample.nii.gz` in `05_results/pom/all_soils_interface_summary.json`; that file = this mask, see *Segmentation*).
- **Graph 6** (POM object sizes, Clark–Evans R = 0.818): `segmentation.nii.gz` (run log of `run_pom_shape_clustering_v2.py --run-name 2soil_clean`: "Loading …\\mishmar_hanegev_maoz_3_5p85um\\inference_output_concat_loess_i2\\mishmar_hanegev_maoz_3_5p85um.nii.gz").
- **Graph 3**: the Loess panel, slice z = 500. 3D renders: `06_figures/renders_3d/loess_5p85um_maoz/`.""",
'01_scans/loess_8p8um_maoz': f"""Traced from each run's recorded input path, not from run names.
- **Graph 5b/5c** (8.8→15 µm point: porosity 20.34 %, Γ = 0.9313, r* = 119.51 µm): `segmentation_15um_trackE.nii.gz`. Track E run `psd_diag_20260902T215639_mishmar_second_8p8um_label_downsample_15um` (input `…\\pipeline_work\\mishmar_second_8p8um\\mishmar_second_8p8um_label_downsample.nii.gz`); χ(r) `{CR}/chi_r_mishmar_second_8p8um_label_downsample_15um.csv`. These are pore metrics; see the holder warning under *Known issues*.
- **Tortuosity** (text): 23 Loess 200³ subvolumes of `segmentation_15um_trackE.nii.gz`.
- **Graph 6** (POM interface metrics at ~15 µm): `segmentation_15um_pom.nii.gz` (input `…\\pom_analysis_20260824_replicates\\mishmar_label_downsample_2\\mishmar_label_downsample_2.nii.gz` in `05_results/pom/all_soils_interface_summary.json`; that file = this mask, see *Segmentation*). This mask is the 1000³ crop, not the ROI-expanded one, so the holder problem below does not apply to it.
- `segmentation.nii.gz` (native 8.8 µm) is the source of `segmentation_15um_pom.nii.gz`; no reported number is computed on it directly.""",
'01_scans/loess_samp2': f"""Traced from each run's recorded input path.
- **Graph 5b/5c** (porosity 26.18 %, Γ = 0.9300, r* = 212.6 µm): Track E run `psd_diag_20260824T135838_mishmar_15um_cu011samp2` (input `nnUNet_resources\\mishmar_hanegev_Cu011_samp_2_Rec_nlm\\inference_output_concat_loess_i2\\mishmar_hanegev_Cu011_samp_2_Rec_nlm.nii.gz`); χ(r) `{CR}/chi_r_mishmar_15um.csv`.
- **Tortuosity** (text): 24 Loess 200³ subvolumes.
- **POM is invalid** (channel collapse): never used for POM.""",
'01_scans/sand_samp2': f"""Traced from each run's recorded input path. All from the **Otsu** mask (the share's `10.5\\rehovot_samp_2.npy`, re-oriented here as `segmentation_otsu.npy`). The nnU-Net reference predictions are not behind any reported number.
- **Graph 4** (pore-size classes): the 8 Sand subvolumes (`stats_summary.md`, *Data sources*: `10.5/rehovot_samp_2.npy`).
- **Graph 5a** (distances to pore / connected pore): `05_results/distances/rehovot_distance_metrics_20260815/summary_distance_metrics.json` (`source_input` = `10.5\\rehovot_samp_2.npy`).
- **Graph 5b/5c** (porosity 30.50 %, Γ = 0.9889, r* = 100.8 µm): Track E run `psd_diag_20260824T135738_rehovot_samp_2_full_volume` (input `10.5\\rehovot_samp_2.npy`); χ(r) `{CR}/chi_r_rehovot.csv`.
- **Tortuosity** (text): 24 Sand 200³ subvolumes.
- **Graph 3**: the Sand panel, slice z = 325.""",
'01_scans/sand_samp3': f"""Traced from each run's recorded input path. All from the **Otsu** mask (the share's `10.5\\Rehovot_samp3_highkV_Cu0.11_15um.npy`, re-oriented here as `segmentation_otsu.npy`). The nnU-Net reference predictions are not behind any reported number.
- **Graph 5b/5c** (porosity 40.85 %, Γ = 0.9974, r* = 147.0 µm): Track E run `psd_diag_20260829T164636_rehovot_samp3_full_volume` (input `10.5\\Rehovot_samp3_highkV_Cu0.11_15um.npy`); χ(r) `{CR}/chi_r_rehovot_samp3.csv`. Sand mean ± SE of the two scans: `05_results/connectivity/rehovot_track_e_samp2_samp3_mean_se.csv`.
- **Tortuosity** (text): 24 Sand 200³ subvolumes.""",
}

TWO_PROC = f"""## Two processings of the same scan

This folder holds **two processings of one physical scan**: raw core `18.12.25 bnei_reem_samp_2.0`, reconstruction `bnei_reem_highkV_cu011_samp_2.0_Rec` (804 slices), voxel size **15.034357 µm** (`scan_log/`).

| | September 2026 processing (this folder) | April 2026 processing (`april_processing/`) |
|---|---|---|
| Name in v1/v2 and on the share | `bnei_reem_specB_unified` | `bnei_reem_fresh_bnei_reem_i4` ("canonical", `nlm_volume`) |
| Made | 2026-09-07 by `run_bnei_reem_unified_pipeline.py` (log in `provenance/`) | image `10.5\\nlm_volume.tif` dated 2026-04-20, segmented 2026-07-06; preprocessing log NOT FOUND |
| Image | 650³ NIfTI, z-scored | 652×650×650 TIFF |
| Pore / POM % | 21.6403 / 0.8170 | 21.6364 / 0.8189 |
| Voxel size given to the analysis runs | 15.034357 µm | 15.000149 µm (recorded before the identity was resolved; the 0.23 % difference is negligible and nothing was recomputed) |

**Same scan.** The two model inputs correlate at r = 0.9999 (0.999929 at zero crop offset, the best of 48 axis transforms; the next best reaches 0.357), and the two segmentations agree with pore Dice 0.988. Against `../vertisol_A/` the best r over all transforms and offsets is 0.140. The evidence is in Part D of the hand-off follow-up report (`docs/HANDOFF_FOLLOWUP_2026-11.md` in the repo).

### Which reported result used which processing

Each row comes from the input path the run itself recorded (`config.json`, `source_input`, the `input_path` column or the run log), not from run names.

| Result (graph) | Processing | Recorded input | File in this package |
|---|---|---|---|
| Γ and visible porosity, the Vertisol B point (5b), and the Γ–porosity fit (R² = 0.91) | September | `nnUNet_resources\\bnei_reem_specB_unified\\inference_concatenated\\bnei_reem_specB_unified.nii.gz` (`config.json`) | `{TE}/psd_diag_20260907T122221_bnei_reem_specB_unified/` |
| χ(r): the Vertisol panel "no crossover in measured range" (5c), together with vertisol_A | September | `chi_r_bnei_reem_specB_unified.meta.json` | `{CR}/chi_r_bnei_reem_specB_unified.csv` (note: this curve does cross zero, at about 920 µm; `figures_data_export.md` gives r* = 920.48 µm) |
| Tortuosity: 24 of the Vertisol 200³ subvolumes (text) | September | `input_path` column of `tortuosity_subvolumes.csv` | `05_results/tortuosity/` |
| Pore-size classes, Vertisol (4) | April | `stats_summary.md`, *Data sources*: `bnei_reem_fresh_bnei_reem_i4/inference_concatenated/nlm_volume.nii.gz` | `05_results/pore_size_classes/` |
| Distances to the nearest pore, connected pore and POM (5a) | April | run `psd_diag_20260802T104738_nlm_volume_fresh_bnei_reem_i4`. It kept no `config.json`, but its PSD table was reproduced bin for bin from this segmentation for the 3D render ({V2}: `06_figures/render3d_bnei_reem_20261013/README.md`, Option 3) | `05_results/distances/psd_diag_20260802T104738_nlm_volume_fresh_bnei_reem_i4/` |
| POM interface metrics (6) | April | `all_soils_interface_summary.json`: `…\\bnei_reem_fresh_bnei_reem_i4\\inference_concatenated\\nlm_volume.nii.gz` | `05_results/pom/all_soils_interface_summary.json` |
| POM object sizes and Clark–Evans R = 0.640 (6) | April | run log of `run_pom_shape_clustering_v2.py --run-name 2soil_clean` ({V2}: `05_analysis_outputs/pom/pom_analysis_20260824_ablation/scripts/run_log_shape_clustering_2soil_clean.txt`): "Loading …\\bnei_reem_fresh_bnei_reem_i4\\inference_concatenated\\nlm_volume.nii.gz" | `05_results/pom/pom_spatial_pattern_summary_2soil_clean.json` |
| Lab vs CT at the soil level (7) | both | values typed into `fig_correlation.py`: visible porosity and Γ = mean of vertisol_A and the September processing; 30–150 µm share and distance to pore from April; POM fraction 0.82 (both processings round to 0.82) | — |
| 3D renders | April | `step0_input.json` of the render | `06_figures/renders_3d/vertisol_B_april_processing/` |

The graph-3 segmentation example for Vertisol is from `../vertisol_A/`.

"""

HOLDER = ("- ⚠ **About 80 % of the POM voxels in `segmentation_15um_trackE.nii.gz` are the sample holder, not soil.** "
          "This mask comes from the ROI-expanded 1614³ crop, which includes the holder wall, and the model labelled the wall as POM. "
          "Inside the core, POM is about 1.2–4 %, like the other masks. So its 7.86 % POM, and the \"tripled POM fraction\" noted for the 8.8 µm ROI expansion, are mostly holder. "
          "Its pore metrics (Γ, r*, tortuosity) are not affected in the same way, but any POM number from this mask should not be used. "
          "Found in the hand-off follow-up, Part B (`docs/HANDOFF_FOLLOWUP_2026-11.md` in the repo); nothing was changed. "
          "The 5.85 µm equivalent does not show this.\n")


def rd(p):
    with open(p, encoding='utf-8', newline='') as f:
        return f.read()


def wr(p, s):
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(s)


def rep(s, old, new, rel, count=1):
    c = s.count(old)
    assert c == count, f'{rel}: {c}x {old[:90]!r}'
    return s.replace(old, new)


def generic(s):
    for o, n in GENERIC:
        s = s.replace(o, n)
    return s


def set_section(s, head, body, rel):
    m = re.search(rf'^## {re.escape(head)}\r?\n(.*?)(?=^## )', s, flags=re.S | re.M)
    assert m, f'{rel}: no section {head}'
    nl = '\r\n' if '\r\n' in s else '\n'
    return s[:m.start(1)] + body.replace('\n', nl) + nl + nl + s[m.end(1):]


def scan_readmes(v2, v3):
    for old, new in SCANS.items():
        s = rd(v2 / f'01_volumes/{old}/README.md')
        rel = f'{new}/README.md'
        nl = '\r\n' if '\r\n' in s else '\n'
        label = new.replace('01_scans/', '')
        s = rep(s, f'# {old}', f'# {label}{nl}{nl}Named `{old}` in v1/v2 of this package and on the share.', rel)
        s = set_section(s, 'Used in the write-up for', USED[new], rel)
        s = generic(s)
        if old == 'bnei_reem_specB_unified':
            s = rep(s, '## Specimen', TWO_PROC.replace('\n', nl) + '## Specimen', rel)
            s = rep(s, 'Numerically identical to the "canonical" volume `bnei_reem_fresh_bnei_reem_i4` (`DATA_CATALOG.md`: r = 0.999929, pore Dice 0.988), because the canonical volume is a legacy (April 2026) processing of this same specimen B scan (resolved 2026-11-14, hand-off follow-up Part D).',
                    'Same physical scan as `april_processing/` (r = 0.999929, pore Dice 0.988; see *Two processings of the same scan*).', rel)
        if old == 'bnei_reem_fresh_bnei_reem_i4':
            s = rep(s, '`../bnei_reem_specB_unified/scan_log/`', '`../scan_log/`', rel)
            s = rep(s, "canonical's model input vs `bnei_reem_specB_unified`'s", "canonical's model input vs `bnei_reem_specB_unified`'s (`../`, the September processing)", rel)
            s = rep(s, "vs `bnei_reem_specA_unified`'s", "vs `bnei_reem_specA_unified`'s (`../../vertisol_A/`)", rel)
        if old == 'mishmar_hanegev_maoz_2_8p8um':
            s = rep(s, '## Known issues' + nl, '## Known issues' + nl + HOLDER.replace('\n', nl), rel)
        if old == 'bnei_reem_specA_unified':
            s = rep(s, 'Not used for POM results (those come from the "canonical" volume).', 'Not used for POM results.', rel, count=0)
        wr(v3 / rel, s)


def other_readmes(v2, v3, manifest):
    # annotations
    for d in ('bnei_reem_i4', 'mishmar_loess_i2'):
        wr(v3 / f'02_annotations/{d}/README.md', generic(rd(v2 / f'02_annotations/{d}/README.md')))
    # models
    for old, new, yaml in (('bnei_reem_i4', 'vertisol_i4', 'fresh_bnei_reem_i4.yaml'),
                           ('mishmar_loess_i2', 'loess_i2', 'mishmar_hanegev_maoz_3_5p85um_loess_i2.yaml')):
        rel = f'03_models/{new}/README.md'
        s = rd(v2 / f'03_models/{old}/README.md')
        nl = '\r\n' if '\r\n' in s else '\n'
        best = next(r['source'] for p, r in manifest.items() if p.startswith(f'03_models/{old}/') and p.endswith('checkpoint_best.pth'))
        s = rep(s, f'# Model `{old}`', f'# Model `{new}`{nl}{nl}Named `{old}` in v1/v2 of this package.', rel)
        s = rep(s, '| `checkpoint_best.pth` | nnU-Net default rule', f'| `checkpoint_best.pth` (**not in this package**; on the share: `{best}`) | nnU-Net default rule', rel)
        s = rep(s, f'Training config (`run_configs/{yaml}`,', f'Training config (`{yaml}` in this folder,', rel)
        s = rep(s, 'Other files: `progress.png` (nnU-Net\'s training curves), `debug.json`, `analytics/` (training-metric exports), `validation/` (prediction on the validation case = the training volume, and its `summary.json`), `dataset.json` (label names), `dataset_fingerprint.json`.',
                'Other files: `fold_0/progress.png` (nnU-Net\'s training curves), `fold_0/training_log_*.txt`, `plans.json`, `dataset.json` (label names), `splits_final.json`. '
                'Not in this package (they are in v2 and on the share): `checkpoint_best.pth`, `debug.json`, `analytics/`, `validation/`, `dataset_fingerprint.json`.', rel)
        wr(v3 / rel, generic(s))
    # code
    s = rd(v2 / '04_code/README.md')
    s = rep(s, '`01_volumes/`', '`01_scans/`', '04_code/README.md')
    s = re.sub(r'^\| `nnUNet4SoilXrayCT_a01686e\.zip` \|.*$', CODE_ROW, s, count=1, flags=re.M)
    assert CODE_ROW in s and 'a01686e.zip' not in s.split('v2 of the package shipped')[0]
    wr(v3 / '04_code/README.md', s)
    # lab
    s = rd(v2 / '07_lab_data_and_writeup/README.md')
    s = rep(s, '# 07_lab_data_and_writeup:', '# 07_lab_data:', '07_lab_data/README.md')
    wr(v3 / '07_lab_data/README.md', s)


TOP = ("""# Soil µCT hand-off package v3: Schwartz 2026 (HUJI)

Image-analysis material of Rony Schwartz's research exercise at the Hebrew University of Jerusalem (2026; advisors Prof. Yael Mishael and Dr. Maoz Dor): how the pore network and particulate organic matter (POM) differ between three Israeli soils, **Loess** (Mishmar HaNegev), **Vertisol** (Bnei Re'em) and **Sand** (Rehovot). Intact cores were scanned by X-ray µCT and segmented with nnU-Net v2 (Sand: global Otsu threshold).

v3 is the lean version: the scans, the models, the annotations, the code, the lab data, and only the result files behind numbers reported in the write-up. Every file is a copy of v1/v2 or of the project repository. Nothing was recomputed. `PACKAGE_MAP_v2_to_v3.csv`, kept next to the ZIP, maps every v2 path to its v3 path or says "not in v3".

## What is where

| Folder | Contents |
|---|---|
| `01_scans/<scan>/` | one folder per scan: the preprocessed image the model saw, the segmentation(s), `README.md`, `provenance/` (inference script, verification logs, nnU-Net records) and `scan_log/` (SkyScan/NRecon logs, where they exist). Loess 5.85/8.8 µm also hold the two ~15 µm masks; Sand holds the Otsu mask plus the nnU-Net predictions for reference |
| `02_annotations/` | the sparse manual annotations and the nnU-Net training pairs of both models |
| `03_models/` | `vertisol_i4/` and `loess_i2/`: `checkpoint_final.pth` (the checkpoint every result used), `plans.json`, `dataset.json`, `splits_final.json`, training log, `progress.png`, training config; the custom trainer `nnUNetTrainer_betterIgnoreSampling.py` |
| `04_code/` | `git archive` of the project repository and of `resp_model`, and the software environment |
| `05_results/` | the result files behind the reported numbers: `pore_size_classes/`, `connectivity/`, `distances/`, `tortuosity/`, `pom/` (see `05_results/README.md`) |
| `06_figures/` | `write_up/` (the 8 figures of the write-up, PNG + SVG), `segmentation_examples/`, `renders_3d/` |
| `07_lab_data/` | the 7 lab workbooks and the scripts and printed statistics for every biology-figure number |
| `MANIFEST.csv` | every file: relative path, bytes, sha256, source |

## Scans

| Folder in `01_scans/` | Name in v1/v2 and on the share | Soil | Voxel size (µm) | Segmentation | Used for (write-up graph) |
|---|---|---|---|---|---|
| `vertisol_A/` | `bnei_reem_specA_unified` | Vertisol, specimen A (raw core `18.12.25 bnei_reem_samp_2`) | 15.000149 | nnU-Net `vertisol_i4` | Γ/porosity (5b), r* "no crossover" (5c), tortuosity, segmentation example (3) |
| `vertisol_B/` | `bnei_reem_specB_unified` | Vertisol, specimen B (raw core `18.12.25 bnei_reem_samp_2.0`), September 2026 processing | 15.034357 | nnU-Net `vertisol_i4` | Γ/porosity (5b), r* "no crossover" (5c), tortuosity |
| `vertisol_B/april_processing/` | `bnei_reem_fresh_bnei_reem_i4` ("canonical") | the same specimen B scan, April 2026 processing | 15.034357 (runs used 15.000149) | nnU-Net `vertisol_i4` | pore-size classes (4), distances (5a), all Vertisol POM results (6), 3D renders |
| `loess_5p85um_maoz/` | `mishmar_hanegev_maoz_3_5p85um` | Loess (external scan) | 5.85; ~15 µm masks | nnU-Net `loess_i2` | pore-size classes (4), distances (5a), Γ and r* at 15 µm (5b/c), tortuosity, POM (6), segmentation example (3), 3D renders |
| `loess_8p8um_maoz/` | `mishmar_hanegev_maoz_2_8p8um` | Loess (external scan) | 8.8; ~15 µm masks | nnU-Net `loess_i2` | Γ and r* at 15 µm (5b/c), tortuosity, POM interface metrics (6) |
| `loess_samp2/` | `Cu011_samp_2` | Loess (raw `29.3.26 mishmar_hanegev_samp_2`) | 15.000149 | nnU-Net `loess_i2` | Γ, r* (5b/c), tortuosity; pore only (POM invalid) |
| `sand_samp2/` | `Rehovot_samp2_highkV_Cu0.11_15um` | Sand | 15.000149 | global-Otsu mask (nnU-Net predictions `segmentation_nnunet_reference_*` for reference only) | pore-size classes (4), distances (5a), Γ, r* (5b/c), tortuosity, segmentation example (3) |
| `sand_samp3/` | `Rehovot_samp3_highkV_Cu0.11_15um` | Sand | 15.034357 | global-Otsu mask (nnU-Net predictions for reference only) | Γ, r* (5b/c), tortuosity |

All scans' segmentations are VERIFIED: either an inference log names the model and checkpoint, or the segmentation was reproduced by re-inference or re-computation on 2026-11-10. The details are in each scan's README. Each scan README's *Used in the write-up for* section names the run and the file behind each number. `01_scans/vertisol_B/README.md` lists which results used which of its two processings.

**Loess `samp_1` and `samp_3`** were scanned but never processed. Their raw data are on the share at `E:\\PROJECTS\\Yael_Mishael\\Rony\\29.3.26 mishmar_hanegev_samp_1\\` and `E:\\PROJECTS\\Yael_Mishael\\Rony\\29.3.26 mishmar_hanegev_samp_3\\`.

Voxel sizes come from the SkyScan logs, or from `DATA_CATALOG.md` and the analysis configs for the two external Loess scans, which have no scan log. **All NIfTI headers say 1 × 1 × 1**; the physical voxel size is not stored in the files.

## Label convention

- **nnU-Net segmentations:** values 0, 1, 2, 5. 0 = matrix, 1 = stones, **2 = POM**, **5 = pore** (each model's `dataset.json`). The analyses ran with `--pore-label 5 --pom-label 2`.
- **Otsu masks** (`segmentation_otsu.npy`, Sand): boolean, **True = pore**.
- The repository's `dataset_info.json` and the annotation files use the annotation label space, where every class is one higher (6 = pore). That is nnU-Net's ignore-label shift, not a disagreement. Do not read predictions with it.
- **Orientation:** in this package every segmentation overlays its image as stored (re-oriented 2026-11-10). The copies on the share are still in the original orientation; each scan README gives the transform.

## Two flags

1. **Vertisol B has two processings of the same scan.** `01_scans/vertisol_B/` (September 2026) and `01_scans/vertisol_B/april_processing/` (April 2026, the former "canonical") are one physical scan: r = 0.9999 and pore Dice 0.988. Connectivity and tortuosity used the September processing; pore-size classes, distances and every POM result used the April one. The full list is in `01_scans/vertisol_B/README.md`.
2. **The 8.8 µm Loess ~15 µm Track E mask includes the sample holder.** About 80 % of the POM voxels in `01_scans/loess_8p8um_maoz/segmentation_15um_trackE.nii.gz` are the holder wall. Its POM numbers should not be used. The POM interface metrics for this scan use `segmentation_15um_pom.nii.gz`, a different crop.

## Quick start

```python
import nibabel as nib, numpy as np, napari
img = np.asarray(nib.load("01_scans/vertisol_A/image_preprocessed.nii.gz").dataobj)
seg = np.asarray(nib.load("01_scans/vertisol_A/segmentation.nii.gz").dataobj)
v = napari.Viewer(); v.add_image(img, name="CT"); v.add_labels(seg, name="labels"); napari.run()   # pore = 5, POM = 2
```

To run a model on a new scan, see `03_models/*/README.md`. The preprocessing and inference scripts are in the code archive.

## Repositories and code

- Project code: https://github.com/agrorony/nnUNet4SoilXrayCT (fork of https://github.com/MaxPhal/nnUNet4SoilXrayCT). The code archive `04_code/nnUNet4SoilXrayCT_""" + CODE_COMMIT[:7] + """.zip` is a `git archive` of commit `""" + CODE_COMMIT + """` on `main` (https://github.com/agrorony/nnUNet4SoilXrayCT/tree/""" + CODE_COMMIT + """). The analysis scripts behind each result are listed in its `5_analysis/README.md`, and the figure scripts in `6_figures/write_up_figures/README.md`.
- Respiration model (appendix A): https://github.com/agrorony/resp_model, commit `5a82e605e467eb4cc7b909168e0ddbce54a94750` (`04_code/resp_model_5a82e60.zip`).
- Software: nnU-Net v2 (nnunetv2 2.4.2), PyTorch 2.11 / CUDA 12.6, 2 × RTX A6000; see `04_code/environment/`.
- Not included: raw projections and reconstructions, intermediate volumes, per-chunk inference files, ROI-expanded volumes, distance maps, render meshes (all on the share `\\\\hive3065\\Yael_Mishael\\Rony\\`; see v2's README for the locations), and the write-up.
- Please cite the write-up (Schwartz, R., 2026, research exercise, Hebrew University of Jerusalem; advisors Y. Mishael and M. Dor), nnU-Net (Isensee et al., 2021) and Phalempin et al. (2025).
- Contact: Rony Schwartz, ronysc@on.huji.ac.il
""")

RESULTS = """# 05_results: the files behind the reported numbers

Only files that a reported number can be traced to (`5_analysis/README.md` and `6_figures/write_up_figures/README.md` in the repo). Graph numbers are the write-up's. Run folders keep their original run names so they can be matched to the share (`\\\\hive3065\\Yael_Mishael\\Rony\\remote_computer backup\\Topology_Metrics_Aug2026\\raw\\`). Which scan and processing each file comes from is in the scan READMEs (`01_scans/*/README.md`, *Used in the write-up for*).

| Folder / file | Result (graph) | Scans |
|---|---|---|
| `pore_size_classes/class_metrics.csv`, `class_stats_results.json` | pore-size classes 30–150 / 150–300 / > 300 µm and their tests (4; what graph 4 reads) | Vertisol B April processing, Loess 5.85 µm, Sand samp2 (8 subvolumes each) |
| `pore_size_classes/A2_summary.md` | method and results of the class analysis and of the Loess resolution check | same |
| `pore_size_classes/fig4_subvolumes/stats_results.json`, `subvolume_metrics.csv`, `stats_summary.md` | per-subvolume porosity and PSD metrics behind graph 4; `stats_summary.md` lists the data sources | same |
| `pore_size_classes/downsample_comparison.json` | Loess 5.85 µm subvolumes downsampled to 15 µm (resolution check, text) | Loess 5.85 µm |
| `connectivity/track_e/<run>/summary.json`, `config.json` | Euler χ, connectivity density, Γ, anisotropy, visible porosity at ~15 µm (5b; the R² = 0.91 fit). `config.json` names the input segmentation | 7 runs: Vertisol A, Vertisol B (September), Loess 5.85→15, 8.8→15, Loess samp2, Sand samp2, Sand samp3 |
| `connectivity/chi_r/*.csv` (+ `.meta.json` where the run wrote one) | χ(r) curves and the crossover radius r* (5c) | Loess 5.85→15 (67.66 µm), 8.8→15 (119.51), Loess samp2 (212.6), Sand samp2 (100.8), Sand samp3 (147.0); Vertisol A and B (shown as "no crossover in measured range"; the B curve crosses at ~920 µm) |
| `connectivity/rehovot_track_e_samp2_samp3_mean_se.csv` | Sand mean ± SE over the two scans | Sand |
| `connectivity/figures_data_export.md` | all Track E values in one table, with the source paths | all |
| `connectivity/porosity_normalization_results.txt` | logit(Γ) vs visible porosity (R² = 0.91, 7 scans) and log tortuosity vs log porosity, with each soil's mean residual (text) | all |
| `distances/<run>/summary_distance_metrics.json` | mean and median distance to the nearest pore, connected pore and POM (5a) | Vertisol B April processing, Loess 5.85 µm (native), Sand samp2 |
| `tortuosity/` | diffusive tortuosity of 200³ subvolumes, 3 axes (text): `tortuosity_subvolumes.csv` (every subvolume, with its `input_path`), `tortuosity_summary.csv`, `convergence_summary.csv`, `stats.json`, `REPORT.md` | Vertisol A and B (September), the three Loess ~15 µm masks, both Sand scans |
| `pom/all_soils_interface_summary.json`, `comparison_table_raw.json` | POM–pore and POM–matrix contact, specific surface area, interface area density at matched ~15 µm (6) | Vertisol B April processing, Loess 5.85 and 8.8 µm (`segmentation_15um_pom`) |
| `pom/pom_object_features_2soil_clean.csv`, `pom_spatial_pattern_summary_2soil_clean.json` | POM object sizes and Clark–Evans R (6: Vertisol 0.640, Loess 0.818). The file also holds cluster columns from the dropped shape clustering; only sizes and R are reported | Vertisol B April processing, Loess 5.85 µm (native) |

Left out on purpose (still in v2 and on the share): the dropped POM shape-clustering runs, the earlier 2026-08-30 interface run, run logs, `diagnostics.json`, `psd_raw_data.csv` (the same content as `psd_table.csv`), per-subvolume PSD runs, block files, and the scripts (they are in the code archive, `5_analysis/`).
"""

FIGS = """# 06_figures

| Folder | Contents |
|---|---|
| `write_up/` | the 8 figures of the submitted write-up (graphs 1–7 and appendix A1), PNG + SVG, copied from the repo's `6_figures/write_up_figures/`. The scripts that draw them are there too (re-run 2026-11-10, pixel-identical) |
| `segmentation_examples/` | `figure7_prediction_panels.png`, the panels behind graph 3 (Vertisol A slice 325, Loess 5.85 µm slice 500, Sand samp2 slice 325) |
| `renders_3d/` | 3D renders of the Vertisol B April processing and the Loess 5.85 µm scan (three options each, close-up and full view, white and transparent background) and the side-by-side pairs. PNGs only; the render scripts, parameters and logs are in the repo (`6_figures/renders_3d/`) |
"""


def main():
    v2, v3 = Path(sys.argv[1]), Path(sys.argv[2])
    manifest = {r['relative_path']: r for r in csv.DictReader(open(v2 / 'MANIFEST.csv', encoding='utf-8'))}
    scan_readmes(v2, v3)
    other_readmes(v2, v3, manifest)
    wr(v3 / 'README.md', TOP)
    wr(v3 / '05_results/README.md', RESULTS)
    wr(v3 / '06_figures/README.md', FIGS)
    print('READMEs:', len(list(v3.rglob('README.md'))))


if __name__ == '__main__':
    main()
