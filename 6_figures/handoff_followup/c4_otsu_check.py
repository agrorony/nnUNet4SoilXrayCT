"""Part C4: reproduce the Rehovot global-Otsu pore masks (pore = below threshold) from their source images
and compare with the packaged masks (packaged = re-oriented to the NIfTI image in B4) and the pre-flip backups.

Usage: python c4_otsu_check.py <package_dir> <backup_dir> <tenfive_dir> <out_json>
"""
import json
import sys
from pathlib import Path

import nibabel as nib
import numpy as np
import tifffile
from skimage.filters import threshold_otsu

CASES = {
    'Rehovot_samp3_highkV_Cu0.11_15um': 'Rehovot_samp3_highkV_Cu0.11_15um.tif',
    'Rehovot_samp2_highkV_Cu0.11_15um': 'rehovot_samp_2.tif',
}


def dice(a, b):
    s = int(a.sum()) + int(b.sum())
    return float(2 * np.logical_and(a, b).sum() / s)


def main():
    pkg, bak, tenfive, out = map(Path, sys.argv[1:5])
    res = {}
    for case, tif in CASES.items():
        rel = f'01_volumes/{case}/segmentation_otsu.npy'
        packaged = np.load(pkg / rel)            # re-oriented (NIfTI image axis order)
        old = np.load(bak / rel)                 # as on the share
        tif_img = tifffile.imread(tenfive / tif)  # (Z, Y, X)
        nii_img = np.asanyarray(nib.load(str(pkg / f'01_volumes/{case}/image_preprocessed.nii.gz')).dataobj)
        r = dict(source_tif=str(tenfive / tif), tif_shape=list(tif_img.shape), tif_dtype=str(tif_img.dtype))
        r['tif_equals_packaged_image_transposed'] = bool(np.array_equal(tif_img.transpose(2, 1, 0), nii_img))
        t_tif = float(threshold_otsu(tif_img))
        t_nii = float(threshold_otsu(nii_img))
        m_tif = tif_img < t_tif
        m_nii = nii_img < t_nii
        r.update(threshold_tif=t_tif, threshold_nii=t_nii,
                 fresh_pore_pct=float(100 * m_nii.mean()), packaged_pore_pct=float(100 * packaged.mean()))
        r['fresh_from_nii_vs_packaged'] = dict(identical=bool(np.array_equal(m_nii, packaged)), dice=dice(m_nii, packaged),
                                               n_diff=int((m_nii != packaged).sum()))
        r['fresh_from_tif_vs_share_copy'] = dict(identical=bool(np.array_equal(m_tif, old)), dice=dice(m_tif, old),
                                                 n_diff=int((m_tif != old).sum()))
        # also "<=" convention, in case the original used it
        r['fresh_le_vs_packaged_identical'] = bool(np.array_equal(nii_img <= t_nii, packaged))
        res[case] = r
        print(case, json.dumps(r, indent=1))
    json.dump(res, open(out, 'w'), indent=1)


if __name__ == '__main__':
    main()
