# 4_inference/loess

- **`predict_from_raw_data_args.json`** is from the inference of the Loess 5.85 µm scan (`mishmar_hanegev_maoz_3_5p85um`) with the loess_i2 model, on 2026-07-16.
  - The driver script for this run was not found. This file, written by nnU-Net itself, is the only record of the run.
  - It records the input folder `.../mishmar_hanegev_maoz_3_5p85um/inference_input` and the output folder `.../inference_output_scratch_i2`. That folder was later renamed `inference_output_loess_i2`; see `3_training/loess_i2/README.md`.
- **`resolution_matching_15um/`** makes the ~15 µm Loess volumes for cross-soil comparison; see its own README.
