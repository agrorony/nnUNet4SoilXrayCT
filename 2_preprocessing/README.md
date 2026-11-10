# 2_preprocessing

- **`otsu_threshold_3d.py`** made both Rehovot (Sand) pore masks.
  - It applies a global Otsu threshold to a 3D TIFF (`volume < t`, pore = dark) and saves a boolean `.npy` next to the TIFF.
  - Its outputs are `10.5/rehovot_samp_2.npy` and `10.5/Rehovot_samp3_highkV_Cu0.11_15um.npy`.
  - Recomputing global Otsu from each TIFF gives 0 voxels different from the saved masks (checked 2026-11-10).
