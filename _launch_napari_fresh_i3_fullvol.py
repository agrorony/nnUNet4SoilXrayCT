import sys
import subprocess
import os

python = sys.executable
script = r"C:\Users\rony.schwartz\Documents\nnUNet4SoilXrayCT\microsam_3d\run.py"

HIVE_ROOT = r'\\hive3065\Yael_Mishael\Rony\remote_computer backup'
HIVE_BASE = os.path.join(HIVE_ROOT, 'nnUNet_resources')

vol  = os.path.join(HIVE_ROOT, '10.5', 'nlm_volume.tif')
pred = os.path.join(HIVE_BASE, 'bnei_reem_fresh_bnei_reem_i3', 'inference_concatenated', 'nlm_volume.nii.gz')
gt   = os.path.join(HIVE_BASE, 'fresh_train_annotations_bnei_reem', 'annotations_i3.nii.gz')

for name, path in [('vol', vol), ('pred', pred), ('gt', gt)]:
    assert os.path.isfile(path), f'Missing {name}: {path}'
    print(f'[OK] {name}: {path}')

subprocess.run(
    [python, script, vol, pred, gt, '--debug'],
    cwd=r'C:\Users\rony.schwartz\Documents\nnUNet4SoilXrayCT\microsam_3d',
    check=True,
)
