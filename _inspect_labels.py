import numpy as np
import nibabel as nib

HIVE_BASE = r'\\hive3065\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources'
GT_PATH  = rf'{HIVE_BASE}\fresh_train_annotations_bnei_reem\annotations_i2.nii.gz'
NEW_PATH = rf'{HIVE_BASE}\bnei_reem_fresh_bnei_reem_i2\inference_concatenated\nlm_volume.nii.gz'
OLD_PATH = rf'{HIVE_BASE}\bnei_reem_fresh_bnei_reem\inference_concatenated\nlm_volume.nii.gz'

for tag, path in [('GT', GT_PATH), ('NEW', NEW_PATH), ('OLD', OLD_PATH)]:
    arr = np.asarray(nib.load(path).dataobj).astype(np.int32)
    unique, counts = np.unique(arr, return_counts=True)
    print(f'--- {tag} ---  shape={arr.shape}')
    for u, c in zip(unique, counts):
        print(f'  label {u:3d}: {c:>12,} voxels')
    if tag == 'GT':
        # Check all three axes for annotated slices
        for axis, name in [(0, 'x'), (1, 'y'), (2, 'z')]:
            nz = [i for i in range(arr.shape[axis]) if np.take(arr, i, axis=axis).any()]
            print(f'  Non-zero slices ({name}-axis): {len(nz)} / {arr.shape[axis]}')
            if nz:
                print(f'    indices: {nz}')
    print()
