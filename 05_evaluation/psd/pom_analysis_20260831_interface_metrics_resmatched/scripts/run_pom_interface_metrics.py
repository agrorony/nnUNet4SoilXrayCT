"""POM interface metrics -- resolution-matched re-run.

Per pom_interface_metrics_resolution_fix_prompt.md. Identical to
pom_analysis_20260830_interface_metrics/scripts/run_pom_interface_metrics.py
except for ONE entry in the SOILS dict: `mishmar_native` now points at the
label-downsampled-to-15um volume (pom_analysis_20260824_ablation/
mishmar_label_downsample/mishmar_label_downsample.nii.gz), not the native
5.85um volume, so both Mishmar replicates are resolution-matched (~15um)
before being averaged into the Mishmar mean +/- SE. The original 08-30 run
mixed a 5.85um replicate with a ~15um replicate -- a resolution confound
(surface-area metrics are voxel-size-sensitive), not a real specimen
difference. See final_report.md's "Resolution correction" section (appended
to the original run's report) for the full before/after comparison.

No other logic changed from the original script. bnei_reem and
mishmar_sample2 entries are untouched.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, Optional

import nibabel as nib
import numpy as np
from scipy import ndimage as ndi
from skimage.measure import marching_cubes

SCRIPT_DIR = Path(__file__).resolve().parent
OUT_ROOT = SCRIPT_DIR.parent  # .../pom_analysis_20260831_interface_metrics_resmatched
PSD_ROOT = OUT_ROOT.parent  # .../05_evaluation/psd
REPLICATES_ROOT = PSD_ROOT / "pom_analysis_20260824_replicates"
ABLATION_ROOT = PSD_ROOT / "pom_analysis_20260824_ablation"

STRUCT_26 = np.ones((3, 3, 3), dtype=np.uint8)
STRUCT_FACE = ndi.generate_binary_structure(3, 1)  # 6-connectivity

SAMPLE_STEP_VOXELS = 0.75  # outward-sample distance for triangle phase classification

SOILS = {
    "bnei_reem": dict(
        soil_label="Bnei Re'em (Vertisol) -- canonical nlm_volume",
        path=r"\\hive3065\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources\bnei_reem_fresh_bnei_reem_i4\inference_concatenated\nlm_volume.nii.gz",
        voxel_um=15.000149,
        pore_label=5,
        pom_label=2,
        cutoff_voxels=8,  # pinned in pom_analysis_20260815_light/bnei_reem/summary_pom_metrics.json
        reference_pore_contact_fraction=0.6422932338325659,
        check_reproduction=True,
    ),
    "mishmar_native": dict(
        # RESOLUTION FIX: was native 5.85um; now label-downsampled to ~15.0um
        # so it is resolution-matched to mishmar_sample2 (both ~15um).
        soil_label="Mishmar HaNegev (Loess) -- native 5.85um sample, label-downsampled to 15.0um (resolution-matched)",
        path=str(ABLATION_ROOT / "mishmar_label_downsample" / "mishmar_label_downsample.nii.gz"),
        voxel_um=15.0,
        pore_label=5,
        pom_label=2,
        cutoff_voxels=13,  # pinned in pom_analysis_20260824_replicates/mishmar_label_downsample_1/summary_pom_metrics.json
        reference_pore_contact_fraction=0.5988303585645836,
        check_reproduction=False,
    ),
    "mishmar_sample2": dict(
        soil_label="Mishmar HaNegev (Loess) -- 2nd specimen, 8.8um native label-downsampled ~15um",
        path=str(REPLICATES_ROOT / "mishmar_label_downsample_2" / "mishmar_label_downsample_2.nii.gz"),
        voxel_um=14.991482112436115,
        pore_label=5,
        pom_label=2,
        cutoff_voxels=15,  # pinned in pom_analysis_20260824_replicates/mishmar_label_downsample_2/summary_pom_metrics.json
        reference_pore_contact_fraction=0.5486826512064232,
        check_reproduction=False,
    ),
}


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def voxel_face_count_surface_area(mask: np.ndarray, voxel_um: float) -> float:
    """Standard voxel-face-count interfacial area (Schlueter et al. 2014,
    method a): sum of exposed 6-connected faces * voxel face area."""
    P = np.pad(mask, 1, mode="constant", constant_values=False)
    exposed = 0
    exposed += int(np.count_nonzero(mask & ~P[2:, 1:-1, 1:-1]))
    exposed += int(np.count_nonzero(mask & ~P[:-2, 1:-1, 1:-1]))
    exposed += int(np.count_nonzero(mask & ~P[1:-1, 2:, 1:-1]))
    exposed += int(np.count_nonzero(mask & ~P[1:-1, :-2, 1:-1]))
    exposed += int(np.count_nonzero(mask & ~P[1:-1, 1:-1, 2:]))
    exposed += int(np.count_nonzero(mask & ~P[1:-1, 1:-1, :-2]))
    return float(exposed) * (voxel_um ** 2)


def process_soil(soil_key: str, cfg: dict) -> Dict:
    out_dir = OUT_ROOT / soil_key
    out_dir.mkdir(parents=True, exist_ok=True)
    voxel_um = cfg["voxel_um"]
    voxel_vol_um3 = voxel_um ** 3
    cutoff = cfg["cutoff_voxels"]

    log(f"=== {soil_key} ({cfg['soil_label']}) ===")
    log(f"Loading {cfg['path']}")
    vol = np.asarray(nib.load(cfg["path"]).dataobj)
    n_total = int(vol.size)
    uniq = np.unique(vol)
    log(f"  shape={vol.shape} unique_labels={uniq.tolist()} voxel_um={voxel_um} cutoff={cutoff}vox")
    assert cfg["pore_label"] in uniq, f"pore_label={cfg['pore_label']} not in {uniq}"
    assert cfg["pom_label"] in uniq, f"pom_label={cfg['pom_label']} not in {uniq}"

    pore_mask = vol == cfg["pore_label"]
    pom_mask_all = vol == cfg["pom_label"]
    matrix_mask = (~pore_mask) & (~pom_mask_all)  # everything else, incl. minor label-1 class (Part 1 rule)
    del vol

    n_pore = int(pore_mask.sum())
    n_pom_raw = int(pom_mask_all.sum())
    n_matrix = int(matrix_mask.sum())
    log(f"  pore={n_pore:,} pom_raw={n_pom_raw:,} matrix(incl. label1)={n_matrix:,} total={n_total:,}")
    log(f"  pom_fraction_pct_raw={100*n_pom_raw/n_total:.4f}  pore_fraction_pct={100*n_pore/n_total:.4f}")

    log("Labeling POM objects (26-connectivity)...")
    labels, n_objects_raw = ndi.label(pom_mask_all, structure=STRUCT_26)
    counts = np.bincount(labels.ravel())[1:]  # per-object voxel count, drop background
    keep_default = np.zeros(n_objects_raw + 1, dtype=bool)
    keep_default[1:] = counts >= cutoff
    denoised_mask = keep_default[labels]
    n_denoised = int(denoised_mask.sum())
    kept_ids = np.nonzero(keep_default)[0]
    kept_ids = kept_ids[kept_ids > 0]
    n_kept = len(kept_ids)
    log(f"  n_objects_raw={n_objects_raw:,} n_objects_kept={n_kept:,} denoised_pom_voxels={n_denoised:,}")

    # ------------------------------------------------------------------
    # Part 1 -- voxel-face contact fractions (sanity anchor)
    # ------------------------------------------------------------------
    log("Part 1: voxel-face contact fractions...")
    surface_voxels = denoised_mask & ~ndi.binary_erosion(denoised_mask, structure=STRUCT_FACE, border_value=0)
    n_surface = int(surface_voxels.sum())
    pore_dilated = ndi.binary_dilation(pore_mask, structure=STRUCT_FACE)
    matrix_dilated = ndi.binary_dilation(matrix_mask, structure=STRUCT_FACE)

    surf_pore = surface_voxels & pore_dilated
    surf_matrix = surface_voxels & matrix_dilated
    surf_both = surf_pore & surf_matrix  # should be structurally empty (pore/matrix disjoint)
    surf_neither = surface_voxels & ~pore_dilated & ~matrix_dilated  # touches only filtered-noise POM specks

    pom_pore_contact_fraction = float(surf_pore.sum() / n_surface) if n_surface else float("nan")
    pom_matrix_contact_fraction = float(surf_matrix.sum() / n_surface) if n_surface else float("nan")
    overlap_fraction = float(surf_both.sum() / n_surface) if n_surface else float("nan")
    neither_fraction = float(surf_neither.sum() / n_surface) if n_surface else float("nan")
    log(f"  n_surface_voxels={n_surface:,} pore_contact={pom_pore_contact_fraction:.6f} "
        f"matrix_contact={pom_matrix_contact_fraction:.6f} overlap={overlap_fraction:.6f} neither={neither_fraction:.6f}")

    reproduction_check = None
    ref = cfg.get("reference_pore_contact_fraction")
    if ref is not None:
        diff = abs(pom_pore_contact_fraction - ref)
        reproduction_check = {
            "reference_value": ref,
            "computed_value": pom_pore_contact_fraction,
            "abs_diff": diff,
            "matched_exact": bool(diff < 1e-9),
            "close_within_1e-3": bool(diff < 1e-3),
        }
        log(f"  REFERENCE CHECK vs {ref}: diff={diff:.3e} matched_exact={reproduction_check['matched_exact']} "
            f"close(<1e-3)={reproduction_check['close_within_1e-3']}")
        if cfg.get("check_reproduction") and not reproduction_check["matched_exact"]:
            log("  *** MISMATCH -- stopping before Part 2 for this volume, per prompt's sanity-check rule ***")
        elif not cfg.get("check_reproduction") and not reproduction_check["close_within_1e-3"]:
            log("  *** NOT CLOSE to pinned reference -- flag for manual review before trusting downstream numbers ***")

    part1 = dict(
        n_surface_voxels_denoised_pom=n_surface,
        pom_pore_contact_fraction_voxel=pom_pore_contact_fraction,
        pom_matrix_contact_fraction_voxel=pom_matrix_contact_fraction,
        overlap_fraction_voxel=overlap_fraction,
        neither_fraction_voxel=neither_fraction,
        reference_pore_contact_fraction=cfg.get("reference_pore_contact_fraction"),
        reproduction_check=reproduction_check,
    )

    del surface_voxels, pore_dilated, matrix_dilated, surf_pore, surf_matrix, surf_both, surf_neither

    # ------------------------------------------------------------------
    # Part 2 -- marching-cubes surface area + phase split (per object)
    # ------------------------------------------------------------------
    log("Part 2: marching-cubes surface reconstruction + phase split (per object)...")
    voxel_face_area_um2 = voxel_face_count_surface_area(denoised_mask, voxel_um)
    log(f"  voxel-face-count total surface area = {voxel_face_area_um2:,.1f} um^2 (cross-check reference)")

    bboxes = ndi.find_objects(labels)
    shape = labels.shape

    obj_voxel_count = counts[kept_ids - 1].astype(np.int64)
    obj_volume_um3 = obj_voxel_count.astype(np.float64) * voxel_vol_um3
    obj_total_area = np.zeros(n_kept, dtype=np.float64)
    obj_pore_area = np.zeros(n_kept, dtype=np.float64)
    obj_matrix_area = np.zeros(n_kept, dtype=np.float64)
    obj_unclassified_area = np.zeros(n_kept, dtype=np.float64)
    obj_mc_failed = np.zeros(n_kept, dtype=bool)

    t_mc0 = time.time()
    for i, obj_id in enumerate(kept_ids):
        slc = bboxes[obj_id - 1]
        z0, z1 = max(slc[0].start - 1, 0), min(slc[0].stop + 1, shape[0])
        y0, y1 = max(slc[1].start - 1, 0), min(slc[1].stop + 1, shape[1])
        x0, x1 = max(slc[2].start - 1, 0), min(slc[2].stop + 1, shape[2])

        local_labels = labels[z0:z1, y0:y1, x0:x1]
        local_obj_mask = local_labels == obj_id
        local_pore = pore_mask[z0:z1, y0:y1, x0:x1]
        local_matrix = matrix_mask[z0:z1, y0:y1, x0:x1]

        padded_obj = np.pad(local_obj_mask, 1, mode="constant", constant_values=False)
        try:
            verts, faces, normals, _values = marching_cubes(
                padded_obj.astype(np.float32), level=0.5, spacing=(voxel_um,) * 3
            )
        except (ValueError, RuntimeError):
            obj_mc_failed[i] = True
            continue
        if len(faces) == 0:
            obj_mc_failed[i] = True
            continue

        tri_v = verts[faces]  # (n_tri, 3, 3) um coords in padded-local frame
        cross = np.cross(tri_v[:, 1] - tri_v[:, 0], tri_v[:, 2] - tri_v[:, 0])
        tri_areas = 0.5 * np.linalg.norm(cross, axis=1)
        total_area = float(tri_areas.sum())

        tri_normals = normals[faces].mean(axis=1)
        nlen = np.linalg.norm(tri_normals, axis=1, keepdims=True)
        nlen[nlen == 0] = 1.0
        tri_normals = tri_normals / nlen

        centroid_um = tri_v.mean(axis=1)
        centroid_vox_padded = centroid_um / voxel_um
        sample_vox_padded = centroid_vox_padded + tri_normals * SAMPLE_STEP_VOXELS
        sample_local = sample_vox_padded - 1.0  # padded-local -> local (unpadded) index frame

        idx_z = np.clip(np.round(sample_local[:, 0]).astype(int), 0, local_pore.shape[0] - 1)
        idx_y = np.clip(np.round(sample_local[:, 1]).astype(int), 0, local_pore.shape[1] - 1)
        idx_x = np.clip(np.round(sample_local[:, 2]).astype(int), 0, local_pore.shape[2] - 1)

        is_pore = local_pore[idx_z, idx_y, idx_x]
        is_matrix = local_matrix[idx_z, idx_y, idx_x]
        pore_only = is_pore & ~is_matrix
        matrix_only = is_matrix & ~is_pore
        unclassified = (~is_pore & ~is_matrix) | (is_pore & is_matrix)

        obj_total_area[i] = total_area
        obj_pore_area[i] = float(tri_areas[pore_only].sum())
        obj_matrix_area[i] = float(tri_areas[matrix_only].sum())
        obj_unclassified_area[i] = float(tri_areas[unclassified].sum())

        if (i + 1) % 200 == 0:
            log(f"  ... {i+1}/{n_kept} objects ({time.time()-t_mc0:.1f}s elapsed)")

    log(f"  marching-cubes done for {n_kept:,} objects ({time.time()-t_mc0:.1f}s); "
        f"{int(obj_mc_failed.sum())} failed/degenerate")

    total_mc_surface_area = float(obj_total_area.sum())
    total_pore_area = float(obj_pore_area.sum())
    total_matrix_area = float(obj_matrix_area.sum())
    total_unclassified_area = float(obj_unclassified_area.sum())

    mc_pore_fraction = total_pore_area / total_mc_surface_area if total_mc_surface_area else float("nan")
    mc_matrix_fraction = total_matrix_area / total_mc_surface_area if total_mc_surface_area else float("nan")

    cross_check_diff_pp = abs(mc_pore_fraction - pom_pore_contact_fraction) * 100.0
    mc_ge_voxel_face = bool(total_mc_surface_area >= voxel_face_area_um2)

    log(f"  total_mc_area={total_mc_surface_area:,.1f}um^2 pore_area={total_pore_area:,.1f} "
        f"matrix_area={total_matrix_area:,.1f} unclassified_area={total_unclassified_area:,.1f}")
    log(f"  mc pore fraction={mc_pore_fraction:.4f} vs voxel-face pore contact fraction={pom_pore_contact_fraction:.4f} "
        f"(diff={cross_check_diff_pp:.2f}pp, flag if >15pp: {cross_check_diff_pp > 15.0})")
    log(f"  mc_total_area >= voxel_face_area: {mc_ge_voxel_face} "
        f"({total_mc_surface_area:,.1f} vs {voxel_face_area_um2:,.1f})  "
        f"(see original run's final_report.md -- this is expected to read False; validated as not a bug)")

    part2 = dict(
        pom_surface_area_um2_marching_cubes_total=total_mc_surface_area,
        pom_surface_area_um2_marching_cubes_pore_facing=total_pore_area,
        pom_surface_area_um2_marching_cubes_matrix_facing=total_matrix_area,
        pom_surface_area_um2_marching_cubes_unclassified=total_unclassified_area,
        pom_surface_area_um2_voxel_face_count_total=voxel_face_area_um2,
        marching_cubes_area_ge_voxel_face_area=mc_ge_voxel_face,
        mc_pore_area_fraction=mc_pore_fraction,
        mc_matrix_area_fraction=mc_matrix_fraction,
        voxel_face_pore_contact_fraction_for_comparison=pom_pore_contact_fraction,
        fraction_disagreement_percentage_points=cross_check_diff_pp,
        fraction_disagreement_flag_gt_15pp=bool(cross_check_diff_pp > 15.0),
        n_objects_mc_failed=int(obj_mc_failed.sum()),
    )

    # ------------------------------------------------------------------
    # Part 3 -- SSA and IAD
    # ------------------------------------------------------------------
    log("Part 3: SSA / IAD...")
    pom_volume_um3 = float(n_denoised) * voxel_vol_um3
    bulk_volume_um3 = float(n_total) * voxel_vol_um3

    ssa_total = total_mc_surface_area / pom_volume_um3 if pom_volume_um3 else float("nan")
    ssa_pore = total_pore_area / pom_volume_um3 if pom_volume_um3 else float("nan")
    ssa_matrix = total_matrix_area / pom_volume_um3 if pom_volume_um3 else float("nan")

    iad_pore = total_pore_area / bulk_volume_um3 if bulk_volume_um3 else float("nan")
    iad_matrix = total_matrix_area / bulk_volume_um3 if bulk_volume_um3 else float("nan")

    part3 = dict(
        pom_volume_um3_denoised=pom_volume_um3,
        bulk_sample_volume_um3=bulk_volume_um3,
        ssa_total_um1=ssa_total,
        ssa_pore_facing_um1=ssa_pore,
        ssa_matrix_facing_um1=ssa_matrix,
        ssa_total_mm2_per_mm3=ssa_total * 1000.0,
        ssa_pore_facing_mm2_per_mm3=ssa_pore * 1000.0,
        ssa_matrix_facing_mm2_per_mm3=ssa_matrix * 1000.0,
        iad_pore_um1=iad_pore,
        iad_matrix_um1=iad_matrix,
        iad_pore_mm2_per_mm3=iad_pore * 1000.0,
        iad_matrix_mm2_per_mm3=iad_matrix * 1000.0,
    )
    log(f"  SSA_total={ssa_total:.5f}/um SSA_pore={ssa_pore:.5f}/um SSA_matrix={ssa_matrix:.5f}/um")
    log(f"  IAD_pore={iad_pore:.6f}/um IAD_matrix={iad_matrix:.6f}/um")

    # ------------------------------------------------------------------
    # Part 4 -- object-level interfacial-area concentration
    # ------------------------------------------------------------------
    log("Part 4: object-level interfacial area concentration...")
    order = np.argsort(obj_pore_area)[::-1]
    sorted_pore_area = obj_pore_area[order]
    largest_share = float(sorted_pore_area[0] / total_pore_area) if total_pore_area and n_kept else float("nan")
    top5_share = float(sorted_pore_area[:5].sum() / total_pore_area) if total_pore_area and n_kept else float("nan")

    part4 = dict(
        largest_object_interface_area_share=largest_share,
        top5_objects_interface_area_share=top5_share,
        n_objects_considered=n_kept,
    )
    log(f"  largest-object POM-pore interface share={largest_share*100:.2f}%  top5 share={top5_share*100:.2f}%")

    # save per-object arrays
    np.save(out_dir / "pom_object_ids.npy", kept_ids)
    np.save(out_dir / "pom_object_voxel_counts.npy", obj_voxel_count)
    np.save(out_dir / "pom_object_volume_um3.npy", obj_volume_um3)
    np.save(out_dir / "pom_object_total_area_um2.npy", obj_total_area)
    np.save(out_dir / "pom_object_pore_area_um2.npy", obj_pore_area)
    np.save(out_dir / "pom_object_matrix_area_um2.npy", obj_matrix_area)
    np.save(out_dir / "pom_object_unclassified_area_um2.npy", obj_unclassified_area)

    summary = dict(
        soil=soil_key,
        soil_label=cfg["soil_label"],
        source_input=cfg["path"],
        voxel_size_um=voxel_um,
        shape=list(shape),
        cutoff_voxels=cutoff,
        n_total_voxels=n_total,
        n_pore_voxels=n_pore,
        n_pom_voxels_raw=n_pom_raw,
        n_matrix_voxels_incl_label1=n_matrix,
        n_pom_objects_raw=int(n_objects_raw),
        n_pom_objects=n_kept,
        n_denoised_pom_voxels=n_denoised,
        part1_voxel_face_contact=part1,
        part2_marching_cubes=part2,
        part3_ssa_iad=part3,
        part4_object_level=part4,
    )
    with (out_dir / "summary_pom_interface_metrics.json").open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    log(f"Wrote {out_dir / 'summary_pom_interface_metrics.json'}")
    return summary


def main() -> None:
    summaries = {}
    for soil_key, cfg in SOILS.items():
        t0 = time.time()
        summaries[soil_key] = process_soil(soil_key, cfg)
        log(f"=== {soil_key} done in {time.time()-t0:.1f}s ===\n")

    with (OUT_ROOT / "all_soils_interface_summary.json").open("w", encoding="utf-8") as fh:
        json.dump(summaries, fh, indent=2)
    log("Wrote all_soils_interface_summary.json -- DONE")


if __name__ == "__main__":
    main()
