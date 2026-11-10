import os

HIVE_BASE = r'\\hive3065\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources'
HIVE_ROOT = r'\\hive3065\Yael_Mishael\Rony\remote_computer backup'

checks = {
    'annotation i2':       os.path.join(HIVE_BASE, 'fresh_train_annotations_bnei_reem', 'annotations_i2.nii.gz'),
    'raw tif':             os.path.join(HIVE_ROOT, '10.5', 'nlm_volume.tif'),
    'fresh checkpoint':    os.path.join(HIVE_BASE, 'bnei_reem_iter04', 'multi_sample_fresh_bnei_reem',
                               'nnUNet_results', 'Dataset777_GCEF',
                               'nnUNetTrainer_betterIgnoreSampling_earlyStopValLoss__nnUNetPlans__3d_fullres',
                               'fold_0', 'checkpoint_final.pth'),
    'inference input dir': os.path.join(HIVE_BASE, 'bnei_reem_iter04', 'inference_input'),
    'train wrapper':       r'C:\Users\rony.schwartz\Documents\nnUNet4SoilXrayCT\_train_wrapper.py',
    'inference script i2': r'C:\Users\rony.schwartz\Documents\nnUNet4SoilXrayCT\_run_inference_fresh_bnei_reem_i2.py',
}
all_ok = True
for name, path in checks.items():
    exists = os.path.isfile(path) or os.path.isdir(path)
    tag = "OK" if exists else "MISSING"
    print(tag + " " + name)
    if not exists:
        print("       -> " + path)
        all_ok = False
if all_ok:
    print("\nAll paths OK - ready to train.")
else:
    raise SystemExit("One or more paths are missing!")
