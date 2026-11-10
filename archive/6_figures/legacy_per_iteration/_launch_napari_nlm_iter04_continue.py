import sys
import subprocess
import os

python = sys.executable
script = r"C:\Users\rony.schwartz\Documents\nnUNet4SoilXrayCT\microsam_3d\run.py"
vol    = r"\\hive3065\Yael_Mishael\Rony\remote_computer backup\10.5\nlm_volume.tif"
pred   = r"\\hive3065\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources\bnei_reem_iter04_continue\inference_concatenated\nlm_volume.nii.gz"
gt     = r"\\hive3065\Yael_Mishael\Rony\remote_computer backup\microSAM_inputs\merged_GT.nii.gz"

subprocess.run(
    [python, script, vol, pred, gt, "--zrange", "50", "70", "--debug"],
    cwd=r"C:\Users\rony.schwartz\Documents\nnUNet4SoilXrayCT\microsam_3d",
    check=True,
)
