import sys
import subprocess

python = sys.executable
script = r"C:\Users\rony.schwartz\Documents\nnUNet4SoilXrayCT\inspect_predictions.py"
pred   = r"\\hive3065\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources\bnei_reem_iter04\inference_concatenated\nlm_volume.nii.gz"
orig   = r"\\hive3065\Yael_Mishael\Rony\remote_computer backup\10.5\nlm_volume.tif"
dsinfo = r"C:\Users\rony.schwartz\Documents\nnUNet4SoilXrayCT\dataset_info.json"

subprocess.run([
    python, script,
    "--prediction_volume", pred,
    "--original_volume",   orig,
    "--dataset_info",      dsinfo,
    "--reverse_label_map",
    "--original_layer_name",   "nlm_volume (iter04)",
    "--prediction_layer_name", "iter04 prediction",
], check=True)
