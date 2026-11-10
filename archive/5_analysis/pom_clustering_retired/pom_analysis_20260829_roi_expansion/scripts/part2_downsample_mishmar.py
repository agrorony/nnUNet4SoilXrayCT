"""Part 2 step 3 (continued) -- label-downsample the two Mishmar ROI-expanded
crops from their native segmentation resolution (5.85um / 8.8um) to
~15.000149um, matching the pinned methodology (Mishmar volumes are always
compared to Bnei Re'em at the ~15um label-downsampled resolution -- see
pom_final_clustering_prompt.md Part 2 and pom_analysis_20260824_ablation /
pom_analysis_20260824_replicates for the original native-resolution runs
this mirrors). Bnei Re'em needs no downsampling -- it is natively ~15um.

Also re-applies the channel-collapse sanity check on the DOWNSAMPLED volume
(majority-vote block downsampling can in principle erase a rare class even
if the native-resolution segmentation itself didn't collapse), mirroring
step_mishmar2_label_downsample.py's own post-downsample check.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import nibabel as nib
import numpy as np

HERE = Path(__file__).resolve().parent
RUN_DIR = HERE.parent
sys.path.insert(0, str(RUN_DIR.parent / "pom_analysis_20260824_ablation" / "scripts"))
from downsample_common import compute_block_edges, block_majority_labels, achieved_voxel_um  # noqa: E402

PORE_LABEL, POM_LABEL = 5, 2
VALID_LABELS = [0, 1, 2, 5]
TARGET_VOXEL_UM = 15.000149
POM_COLLAPSE_FLOOR_PCT = 0.3

SOURCE_VOXEL_UM = {
    "mishmar_native_5p85um": 5.85,
    "mishmar_second_8p8um": 8.8,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--volume-key", required=True, choices=list(SOURCE_VOXEL_UM.keys()))
    args = parser.parse_args()
    key = args.volume_key
    source_voxel_um = SOURCE_VOXEL_UM[key]

    concat_path = RUN_DIR / "pipeline_work" / key / "inference_concatenated" / f"{key}.nii.gz"
    assert concat_path.exists(), f"Missing native-res segmentation: {concat_path}"
    print(f"[{key}] loading native-res segmentation: {concat_path}")
    vol = np.asarray(nib.load(str(concat_path)).dataobj)
    n = vol.shape[0]
    assert vol.shape == (n, n, n), f"expected a cube, got {vol.shape}"
    uniq_src = np.unique(vol)
    print(f"[{key}] native shape={vol.shape} unique_labels={uniq_src.tolist()} voxel_um={source_voxel_um}")
    assert set(uniq_src.tolist()) <= set(VALID_LABELS), f"unexpected labels {uniq_src}"

    edges = compute_block_edges(n, TARGET_VOXEL_UM, source_voxel_um)
    m = len(edges) - 1
    v_um = achieved_voxel_um(n, edges, source_voxel_um)
    print(f"[{key}] block partition: n={n} -> m={m} blocks/axis, achieved voxel size={v_um:.4f}um "
          f"(target {TARGET_VOXEL_UM}um)")

    ds = block_majority_labels(vol, edges, VALID_LABELS)
    del vol
    print(f"[{key}] downsampled shape={ds.shape}")

    n_total = int(ds.size)
    n_pore = int((ds == PORE_LABEL).sum())
    n_pom = int((ds == POM_LABEL).sum())
    pore_pct = 100 * n_pore / n_total
    pom_pct = 100 * n_pom / n_total
    print(f"[{key}] downsampled pore={n_pore:,} ({pore_pct:.3f}%)  pom={n_pom:,} ({pom_pct:.3f}%)")

    collapsed = pom_pct < POM_COLLAPSE_FLOOR_PCT or pore_pct < POM_COLLAPSE_FLOOR_PCT
    sanity = {
        "volume_key": key,
        "achieved_voxel_um": v_um,
        "target_voxel_um": TARGET_VOXEL_UM,
        "shape": list(ds.shape),
        "pore_voxel_fraction_pct": pore_pct,
        "pom_voxel_fraction_pct": pom_pct,
        "collapse_floor_pct": POM_COLLAPSE_FLOOR_PCT,
        "downsampled_collapse_detected": bool(collapsed),
    }
    out_dir = RUN_DIR / "pipeline_work" / key
    with (out_dir / "downsample_sanity_check.json").open("w", encoding="utf-8") as fh:
        json.dump(sanity, fh, indent=2)
    print(json.dumps(sanity, indent=2))

    if collapsed:
        print(f"[{key}] !!! DOWNSAMPLED CHANNEL COLLAPSE -- do not use this downsampled volume !!!")
        return

    out_path = out_dir / f"{key}_label_downsample.nii.gz"
    nib.save(nib.Nifti1Image(ds.astype(np.uint8), affine=np.eye(4)), str(out_path))
    print(f"[{key}] DONE -- wrote {out_path}")


if __name__ == "__main__":
    main()
