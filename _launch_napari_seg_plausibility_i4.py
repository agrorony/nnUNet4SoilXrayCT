import sys
import subprocess

python = sys.executable
script = r"C:\Users\rony.schwartz\Documents\nnUNet4SoilXrayCT\seg_plausibility\napari_review.py"
results_dir = r"C:\Users\rony.schwartz\Documents\nnUNet4SoilXrayCT\analysis\selected_outputs\bnei_reem\seg_plausibility_i4"
original = r"\\hive3065\Yael_Mishael\Rony\remote_computer backup\10.5\nlm_volume.tif"
prediction = r"\\hive3065\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources\bnei_reem_fresh_bnei_reem_i4\inference_concatenated\nlm_volume.nii.gz"
dataset_info = r"C:\Users\rony.schwartz\Documents\nnUNet4SoilXrayCT\dataset_info.json"

subprocess.run([
    python, script,
    "--results-dir", results_dir,
    "--original", original,
    "--prediction", prediction,
    "--dataset-info", dataset_info,
    "--exclude-classes", "5",  # hide the fragmented Pore class noise by default
], check=True)
