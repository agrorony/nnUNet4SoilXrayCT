# Loess i2 model (`mishmar_hanegev_maoz_3_5p85um_loess_i2`), trained 2026-07-15

- **The training driver was not found.** No script, config or console log from 2026-07-14 to 07-16 survives on the lab computer.
- **The likely driver is `3_training/run_training.py`.** The evidence:
  - Its output folder `multi_sample_<iteration_name>` matches the folder recorded in the run's `debug.json`.
  - The trainer (`nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss`) matches.
  - The early-stopping settings match. The log has `patience=20 | min_delta=0.001`.
  - The run started from pretrained weights: epoch-0 train loss was −0.70, against +0.28 for the from-scratch parent run on 2026-07-12. That fits `base_checkpoint: mishmar_hanegev_maoz_3_5p85um_scratch`.
- **The run was renamed after training.** It was named `mishmar_hanegev_maoz_3_5p85um_scratch_i2` when it trained; the training log and `debug.json` record `multi_sample_..._scratch_i2`. It was renamed `loess_i2` afterwards, along with its inference folder.
- **`mishmar_hanegev_maoz_3_5p85um_loess_i2.yaml` here is a reconstruction** written on 2026-08-14, after the rename. It is not the config the run used. Run as it stands, it would write to `multi_sample_..._loess_i2`, not `..._scratch_i2`.
- **The reliable record of the run is `model_files/`:** `plans.json`, `dataset.json`, `splits_final.json` and `fold_0/training_log_2026_7_15_13_43_55.txt`.
