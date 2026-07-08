import numpy as np
from pathlib import Path

# Define volumes and output paths
volumes = [
    ("\\\\hive3065\\Yael_Mishael\\Rony\\remote_computer backup\\10.5\\mishmar_hanegev_Cu011_samp_2_Rec_nlm.npy", "mishmar_hanegev_Cu011_samp_2_Rec_nlm_150z"),
    ("\\\\hive3065\\Yael_Mishael\\Rony\\remote_computer backup\\10.5\\rehovot_samp_2.npy", "rehovot_samp_2_150z"),
    ("\\\\hive3065\\Yael_Mishael\\Rony\\remote_computer backup\\10.5\\nlm_volume.npy", "nlm_volume_150z"),
]

output_root = "\\\\hive3065\\Yael_Mishael\\Rony\\remote_computer backup\\10.5"

for vol_path, name in volumes:
    vol = np.load(vol_path)
    # Extract first 150 slices in Z
    chunk = vol[:150, :, :]
    output_path = Path(output_root) / f"{name}.npy"
    np.save(str(output_path), chunk, allow_pickle=False)
    print(f"Saved {name}: {chunk.shape}")
