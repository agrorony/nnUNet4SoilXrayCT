# Bnei Re'em "i3" retrain pipeline — prompts for Claude Code (rony-pc)

Context for whoever runs these (Claude Code has no memory of the cowork session that produced this file): Rony is rebuilding the Bnei Re'em POM/pore segmentation model using a newer 5-class scheme (`1=Matrix, 2=Stones, 3=POM_type1, 4=POM_type2, 6=Pore`) discovered in `G:\האחסון שלי\soil_microCT_segmentation_review`. A seed annotation volume (`bnei_reem_i3_seed_annotations.nii.gz`, ignore-label = 255) was auto-built from that folder's QC images and now lives next to the source data. Rony will hand-correct it in napari before anything trains. This project has a long history of axis/orientation mistakes and of specimen-naming collisions (samp1/samp2/samp3 vs samp_2/samp_2.0 vs "Spec A/Spec B") — every prompt below says explicitly not to guess and to surface conflicts to Rony instead of silently resolving them.

Each prompt is meant to be run **as its own Claude Code session/turn**, in order. Do not skip the verification step (Prompt 1) or the training step (Prompt 3) into the same run as anything else — each is a checkpoint Rony wants to see before the next thing happens.

---

## Prompt 1 — Verify the seed mask is actually aligned

```
Read C:\Users\ronys\soil_and_water\research_exercise\nnUNet4SoilXrayCT\DATA_CATALOG.md and any project docs on preprocessing/orientation conventions before touching anything (search for prior axis/orientation bugs — this project has a documented history of them).

Files to check:
- G:\האחסון שלי\soil_microCT_segmentation_review\nlm_volume.nii.gz  (raw denoised volume, shape ~650x650x652)
- G:\האחסון שלי\soil_microCT_segmentation_review\bnei_reem_i3_seed_annotations.nii.gz  (auto-built seed labels, ignore label = 255, same shape)
- G:\האחסון שלי\soil_microCT_segmentation_review\seed_annotations_qc.json  (lists which of the 652 z-slices have real seed labels, and how many pixels came from true GT vs. model-prediction fill)
- G:\האחסון שלי\soil_microCT_segmentation_review\synopsis_i3\slice_*.png  (the original 3-panel QC images: Raw CT | GT Annotations (i3) | Prediction (fresh_bnei_reem_i3), each 1431x696, panels at x=[18,471]/[488,941]/[959,1412], y=[107,559])

Task: for every z-slice listed in seed_annotations_qc.json, render a side-by-side comparison of (a) the raw CT slice from nlm_volume.nii.gz, (b) the corresponding label slice from bnei_reem_i3_seed_annotations.nii.gz color-mapped with the same legend (Matrix=#6D0B62, Stones=#E3E30B, POM_type1=#B8E3E3, POM_type2=#140BE3, Pore=#36B80B), and (c) the original synopsis_i3 PNG's Prediction panel for that z. Save all of these into a new folder G:\האחסון שלי\soil_microCT_segmentation_review\alignment_qc\.

Explicitly test whether the label array's axis order/orientation matches the raw volume: try at least the identity mapping and the transposed (swap X/Y) mapping, and state in your report which one visually matches the synopsis panels and which does not — do not assume the identity mapping is correct just because the file already exists. Report any flips or transposes needed as a concrete, stated finding, not a silent fix. Do not modify the seed_annotations file yet — output your findings and the comparison images, then stop and report back with the alignment_qc folder path and a clear yes/no on "is bnei_reem_i3_seed_annotations.nii.gz already correctly aligned to nlm_volume.nii.gz."
```

---

## Prompt 2 — Preprocessing for all existing raw volumes

```
Read C:\Users\ronys\soil_and_water\research_exercise\nnUNet4SoilXrayCT\DATA_CATALOG.md in full first, plus any existing preprocessing scripts in that repo (search for norm200/NLM/crop steps already used for Bnei Re'em's April "Dataset777_GCEF" run) — match their exact parameters and code style rather than inventing a new pipeline. Do not proceed until you have found and read the prior preprocessing script(s); if you can't find one, stop and ask Rony rather than guessing normalization/denoise parameters.

Raw volumes needing this pipeline (verify each path exists before processing; do not assume specimen identity beyond the literal folder name — if a folder name is ambiguous relative to DATA_CATALOG.md's specimen IDs, stop and ask rather than pick one):
- G:\האחסון שלי\soil_microCT_images\10.12.25 Rehovot\Rehovot_samp1_highkV_Cu0.11_15um_Rec  (and _Rec_2, _Rec_3 — pick the one that matches how the other Rehovot specimen was reconstructed, and say which you picked and why)
- G:\האחסון שלי\soil_microCT_images\10.12.25_Rehovot_samp_2\Rehovot_samp2_highkV_Cu0.11_15um_Rec  (and _Rec_2)
- Bnei Re'em Specimen A (raw core `18.12.25 bnei_reem_samp_2`, no dot, 15.000149 µm): DATA_CATALOG.md records its operative reconstruction as `C:\Users\rony.schwartz\Desktop\new_rec` (804 slices, 1344x1344, uint16) — NOT the Drive copy at `G:\האחסון שלי\soil_microCT_images\18.12.25 bnei_reem_samp_2\bnei_reem_highkV_cu011_samp_2_Rec`, which only has 2 preview slices, not a full stack. Use `new_rec` if that machine/path is reachable from rony-pc; if it isn't, stop and ask Rony rather than substituting the incomplete Drive copy.
- Bnei Re'em Specimen B (raw core `18.12.25 bnei_reem_samp_2.0`, 15.034357 µm): reconstruction at `G:\האחסון שלי\soil_microCT_images\18.12.25 bnei_reem_samp_2.0\bnei_reem_highkV_cu011_samp_2.0_Rec` per DATA_CATALOG.md (also referenced there via the `\\HIVE3065\Yael_Mishael\...` share path — use whichever is actually reachable).
- G:\האחסון שלי\soil_microCT_images\mishmar_hanegev_Cu011_samp_1_Rec
- G:\האחסון שלי\soil_microCT_images\mishmar_hanegev_Cu011_samp_2_Rec
- G:\האחסון שלי\soil_microCT_images\mishmar_hanegev_Cu011_samp_3_Rec
- G:\האחסון שלי\soil_microCT_images\29.3.26 mishmar_hanegev_samp_3  (check whether this is the same physical specimen as Cu011_samp_3 above or a different one — if unclear, ask Rony, do not assume)

For each: run the established norm200 → NLM denoise → crop steps, and write outputs to a new, explicitly-named folder structure under C:\Users\ronys\soil_and_water\research_exercise\nnUNet4SoilXrayCT\03_preprocessed\<soil>_<specimen-id-exactly-as-in-DATA_CATALOG>_<voxel-size>um\ (e.g. 03_preprocessed\bnei_reem_specB_15um\). Do not use ad hoc or abbreviated names — every folder name should be traceable to a DATA_CATALOG.md row without guessing. Write a manifest CSV (03_preprocessed\preprocessing_manifest.csv) listing: source path, output path, voxel size, processing steps applied with exact parameters, timestamp.

Update DATA_CATALOG.md (both this repo copy and the mirror at C:\Users\ronys\Documents\Claude\Projects\resarch exercise\05_analysis_notes\DATA_CATALOG.md — keep them identical) with a dated changelog entry listing what was preprocessed. Do not touch anything else in DATA_CATALOG.md. Report back the manifest and flag anything you skipped or couldn't resolve.
```

---

## Prompt 3 — Train from scratch (run only after Rony has corrected the mask in napari)

```
Read C:\Users\ronys\soil_and_water\research_exercise\nnUNet4SoilXrayCT\DATA_CATALOG.md and the existing nnUNet_resources\bnei_reem\ folder structure from the "Dataset777_GCEF" run (checkpoint dated 2026-04-20, under G:\האחסון שלי\soil_microCT_images\ROI\nnUNet_resources\bnei_reem\) to match its exact folder layout and nnUNet dataset conventions — do not invent a new structure. Note: this April checkpoint's relationship to the documented `fresh_bnei_reem_i4` "canonical" run (the 3-class model DATA_CATALOG.md treats as the current source of Bnei Re'em POM results) is NOT confirmed — the dates don't obviously line up and this hasn't been checked. Don't assume they're the same model; if it matters for how you set up training, ask Rony rather than assume.

Inputs (confirm both exist and Rony has told you the mask is corrected before proceeding — if you have no confirmation the mask was reviewed, stop and ask):
- G:\האחסון שלי\soil_microCT_segmentation_review\nlm_volume.nii.gz
- G:\האחסון שלי\soil_microCT_segmentation_review\bnei_reem_i3_seed_annotations.nii.gz  (Rony's corrected version — confirm the file's modification time is recent / after his review before using it)

This is a 5-class scheme (1=Matrix, 2=Stones, 3=POM_type1, 4=POM_type2, 6=Pore) with ignore label 255 for unannotated slices — use the same sparse-annotation ignore-label training approach as the prior nnUNetTrainer_betterIgnoreSampling run (check its trainer config/plans.json under nnUNet_resources\bnei_reem\nnUNet_results\ and reuse the same trainer/settings unless there's a clear reason not to — state any deviation explicitly).

Set up a new nnUNet dataset (e.g. Dataset778 or the next free ID — check what's already used and do not collide with Dataset777_GCEF), preprocess, and train from scratch (do not initialize from the April checkpoint — Rony wants a from-scratch run given the new class scheme). Log training curves the same way as training_metrics_lowlr.png was produced previously (same plot style/naming convention if you can find the script that made it).

Save the new checkpoint under a clearly new-dated results folder (do not overwrite Dataset777_GCEF's April results). Update DATA_CATALOG.md and PROJECT_STATUS.md (both copies) with a dated entry describing the new model: dataset ID, class scheme, training date, final validation Dice, and where the checkpoint lives. Report back with the checkpoint path and final metrics.
```

---

## Prompt 4 — Inference on the remaining volumes

```
Read DATA_CATALOG.md first. Using the newly trained checkpoint from Prompt 3 (confirm its path with Rony if it's not obvious which run is "the" current one), run inference on:
1. Confirm which Bnei Re'em specimen `soil_microCT_segmentation_review\nlm_volume.nii.gz` actually is (Specimen A or B per DATA_CATALOG.md) before picking "the other one" to run inference on — do not assume; if the file's provenance isn't stated anywhere, stop and ask Rony rather than guess, given this project's history of specimen mislabeling (see the unresolved canonical-vs-Specimen-A/B identity flag already in DATA_CATALOG.md).
2. Both Mishmar HaNegev "Maoz" scans (the 5.85µm native run and the second, 8.8µm-downsampled-to-15µm run — confirm exact preprocessed paths from Prompt 2's manifest, do not re-derive them from scratch).

Apply the same preprocessing pipeline used for training (norm200 → NLM → crop, matching voxel size expectations of the trained model — flag if a resolution mismatch requires resampling, per this project's A2 resolution-matching policy, and say explicitly what you did about it rather than silently resampling).

Save each prediction volume as a NIfTI file under a new dated folder (e.g. 07_analysis_runs\bnei_reem_i3_inference_<date>\) with explicit names identifying soil, specimen ID (matching DATA_CATALOG.md exactly), and model/checkpoint used. Do not overwrite any existing prediction files. Update DATA_CATALOG.md and PROJECT_STATUS.md (both copies) with a dated entry noting new predictions exist and are pending Rony's napari review — do not report any POM metrics from these predictions as final/trusted yet, since Rony reviews them next. Report back the output paths.
```

---

## (Manual step — not a Claude Code prompt)

Rony reviews all new predictions in napari himself. No prompt needed for this step; it happens between Prompt 4 and Prompt 5/6.

---

## Prompt 5 — Recompute any missing non-POM structural metrics

```
Read DATA_CATALOG.md and PROJECT_STATUS.md in full first. Before recomputing anything, produce a clear table of exactly which structural metrics (porosity, PSD 30-150um fraction, Euler characteristic χ, connectivity density, connectivity probability Γ, degree of anisotropy, tortuosity, crossover radius r*) are missing for which specimen/resolution combinations, based on what's actually recorded in DATA_CATALOG.md right now (including any specimens newly preprocessed in Prompt 2 or newly predicted in Prompt 4, once Rony has confirmed those predictions are usable post-review). Show this table to Rony implicitly by writing it into your report before computing anything, so gaps are confirmed rather than assumed.

These are structural (pore-network) metrics, independent of the POM segmentation model — use the project's existing Track E scripts/pipeline (locate them under nnUNet4SoilXrayCT and reuse them exactly; do not reimplement the metrics from scratch). Follow the project's A2 policy: only compute cross-soil-comparable connectivity/porosity metrics at resolution-matched (~15um) volumes; note native-resolution results separately and do not pool them with resolution-matched ones.

Save results into a new dated folder under 07_analysis_runs\, following the same file-naming and summary-markdown pattern as prior runs (e.g. connectivity_validation_summary.md, crossover_radius_summary.md). Update DATA_CATALOG.md and PROJECT_STATUS.md (both copies, identical) with a dated changelog entry. Report back exactly what was computed, what's still missing (e.g. any specimen still lacking a valid pore-only volume), and remind Rony that he still needs to git commit/push the nnUNet4SoilXrayCT repo copy himself.
```
