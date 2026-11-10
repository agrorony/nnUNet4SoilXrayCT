"""Final POM shape/spatial clustering -- Bnei Re'em (n=1) vs Mishmar (n=2),
per bnei_reem_samp_2_0_repreprocess_prompt.md's follow-up final prompt
(2026-08-26).

Same core algorithm/version as pom_analysis_20260824_ablation/scripts/
run_pom_shape_clustering_v2.py and pom_analysis_20260824_replicates/scripts/
run_pom_shape_clustering_replicates.py (marching-cubes sphericity with
voxel-proxy fallback, eigenvalue-floored elongation/flatness, per-run-only
StandardScaler, KMeans + silhouette per-volume clustering, then cross-volume
archetype matching on cluster centroids). Duplicated rather than imported,
per this project's convention of self-contained dated scripts.

ONE CHANGE from both prior versions: the per-object minimum-size cutoff.
Both prior versions used an ad hoc "A1 noise floor" cutoff (a statistically
-derived floor against segmentation noise, read from a prior run's
summary_pom_metrics.json -- typically only 8-15 voxels, i.e. ~2.5-3 voxels
across the equivalent-sphere diameter). That is a reasonable cutoff for
*counting/size-distribution* work, but it is NOT enough voxels to trust a
marching-cubes-derived sphericity or a PCA-eigenvalue-derived elongation/
flatness -- those need the object to actually be shaped like something in
voxel space. This run instead applies a minimum-resolvability cutoff:
diameter (voxel-equivalent sphere) >= 20 voxels across, i.e.
n_voxels >= (pi/6) * 20^3 ~= 4188.8 voxels for a 15.000149um volume
(diameter ~= 300.0um). This is computed directly from each volume's own
voxel size -- no dependency on any prior run's noise-floor JSON.

This drastically reduces n_objects_kept relative to prior runs (from
hundreds-to-low-thousands down to double digits per volume -- see
resolvability_cutoff_check.json in this directory for the pre-check that
established this). That is reported prominently, not hidden.

Datasets (exactly 3, matching the prompt -- do not substitute):
  - bnei_reem: canonical, already-trusted nlm_volume
    (bnei_reem_fresh_bnei_reem_i4/inference_concatenated/nlm_volume.nii.gz)
    -- NOT bnei_reem_samp_2_0 or any recropped variant.
  - mishmar_label_downsample_1: Mishmar native 5.85um, label-downsampled ~15um
    (reused from pom_analysis_20260824_ablation/mishmar_label_downsample/)
  - mishmar_label_downsample_2: Mishmar second sample ~8.8um native,
    label-downsampled ~15um
    (reused from pom_analysis_20260824_replicates/mishmar_label_downsample_2/)

Usage:
    python run_pom_shape_clustering_final.py --run-name final
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Dict, List

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import nibabel as nib
import numpy as np
import pandas as pd
from scipy import ndimage as ndi
from scipy import stats as sstats
from scipy.spatial import cKDTree
from scipy.special import gamma as gamma_fn
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

OUT_ROOT = Path(__file__).resolve().parents[1]
ABLATION_ROOT = OUT_ROOT.parent / "pom_analysis_20260824_ablation"
REPLICATES_ROOT = OUT_ROOT.parent / "pom_analysis_20260824_replicates"
STRUCT_26 = np.ones((3, 3, 3), dtype=np.uint8)
STRUCT_FACE = ndi.generate_binary_structure(3, 1)
FEATURE_NAMES = ["elongation", "flatness", "sphericity", "pore_contact_fraction"]
CLUSTER_FEATURE_NAMES = ["log_elongation", "log_flatness", "sphericity", "pore_contact_fraction"]

MIN_VOXELS_ACROSS_DIAMETER = 20.0

SOIL_GROUP = {
    "bnei_reem": "bnei_reem",
    "mishmar_label_downsample_1": "mishmar",
    "mishmar_label_downsample_2": "mishmar",
}

DATASETS = {
    "bnei_reem": dict(
        label="Bnei Re'em (Vertisol) -- canonical nlm_volume, n=1",
        path=r"\\hive3065\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources\bnei_reem_fresh_bnei_reem_i4\inference_concatenated\nlm_volume.nii.gz",
        voxel_um=15.000149, pore_label=5, pom_label=2,
    ),
    "mishmar_label_downsample_1": dict(
        label="Mishmar HaNegev (Loess) -- sample 1 (native 5.85um), label-downsampled ~15um",
        path=str(ABLATION_ROOT / "mishmar_label_downsample" / "mishmar_label_downsample.nii.gz"),
        voxel_um=15.000149, pore_label=5, pom_label=2,
    ),
    "mishmar_label_downsample_2": dict(
        label="Mishmar HaNegev (Loess) -- sample 2 (native 8.8um), label-downsampled ~15um",
        path=str(REPLICATES_ROOT / "mishmar_label_downsample_2" / "mishmar_label_downsample_2.nii.gz"),
        voxel_um=15.000149, pore_label=5, pom_label=2,
    ),
}


def _cluster_feature_matrix(df: pd.DataFrame) -> np.ndarray:
    return np.column_stack([
        np.log(df["elongation"].to_numpy()),
        np.log(df["flatness"].to_numpy()),
        df["sphericity"].to_numpy(),
        df["pore_contact_fraction"].to_numpy(),
    ])


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def compute_soil_features(soil_key: str, cfg: dict) -> pd.DataFrame:
    voxel_um = cfg["voxel_um"]
    voxel_vol_um3 = voxel_um ** 3
    min_voxels_cutoff = (np.pi / 6.0) * (MIN_VOXELS_ACROSS_DIAMETER ** 3)
    min_diameter_um = MIN_VOXELS_ACROSS_DIAMETER * voxel_um

    log(f"=== {soil_key} ({cfg['label']}) ===")
    log(f"  resolvability cutoff: diam>={MIN_VOXELS_ACROSS_DIAMETER:.0f} vox "
        f"({min_diameter_um:.1f}um) -> n_voxels>={min_voxels_cutoff:.1f}")

    p = Path(cfg["path"])
    if not p.exists():
        raise FileNotFoundError(f"{soil_key}: volume not found: {p}")
    log(f"  Loading {p}")
    vol = np.asarray(nib.load(str(p)).dataobj)
    pore_mask = (vol == cfg["pore_label"])
    pom_mask_all = (vol == cfg["pom_label"])
    n_total = int(vol.size)
    del vol

    log("  Labeling POM objects (26-connectivity)...")
    labels, n_objects_raw = ndi.label(pom_mask_all, structure=STRUCT_26)
    counts_all = np.bincount(labels.ravel())[1:]
    keep_default = np.zeros(n_objects_raw + 1, dtype=bool)
    keep_default[1:] = counts_all >= min_voxels_cutoff
    denoised_mask = keep_default[labels]
    n_kept = int(keep_default.sum())
    log(f"  n_objects_raw={n_objects_raw:,}  n_kept(diam>={MIN_VOXELS_ACROSS_DIAMETER:.0f}vox)={n_kept:,}")

    pore_dilated = ndi.binary_dilation(pore_mask, structure=STRUCT_FACE)
    surface_mask = denoised_mask & ~ndi.binary_erosion(denoised_mask, structure=STRUCT_FACE, border_value=0)

    log("  Computing per-object voxel-position moments (vectorized bincount)...")
    zz, yy, xx = np.nonzero(denoised_mask)
    lbl = labels[(zz, yy, xx)]
    minlen = n_objects_raw + 1

    n = np.bincount(lbl, minlength=minlen).astype(np.float64)
    sum_z = np.bincount(lbl, weights=zz.astype(np.float64), minlength=minlen)
    sum_y = np.bincount(lbl, weights=yy.astype(np.float64), minlength=minlen)
    sum_x = np.bincount(lbl, weights=xx.astype(np.float64), minlength=minlen)
    sum_zz = np.bincount(lbl, weights=(zz.astype(np.float64)) ** 2, minlength=minlen)
    sum_yy = np.bincount(lbl, weights=(yy.astype(np.float64)) ** 2, minlength=minlen)
    sum_xx = np.bincount(lbl, weights=(xx.astype(np.float64)) ** 2, minlength=minlen)
    sum_zy = np.bincount(lbl, weights=zz.astype(np.float64) * yy.astype(np.float64), minlength=minlen)
    sum_zx = np.bincount(lbl, weights=zz.astype(np.float64) * xx.astype(np.float64), minlength=minlen)
    sum_yx = np.bincount(lbl, weights=yy.astype(np.float64) * xx.astype(np.float64), minlength=minlen)

    kept_ids = np.nonzero(keep_default)[0]
    kept_ids = kept_ids[kept_ids > 0]
    nk = n[kept_ids]

    mean_z, mean_y, mean_x = sum_z[kept_ids] / nk, sum_y[kept_ids] / nk, sum_x[kept_ids] / nk
    cov_zz = sum_zz[kept_ids] / nk - mean_z ** 2
    cov_yy = sum_yy[kept_ids] / nk - mean_y ** 2
    cov_xx = sum_xx[kept_ids] / nk - mean_x ** 2
    cov_zy = sum_zy[kept_ids] / nk - mean_z * mean_y
    cov_zx = sum_zx[kept_ids] / nk - mean_z * mean_x
    cov_yx = sum_yx[kept_ids] / nk - mean_y * mean_x

    n_kept_obj = len(kept_ids)
    cov_mats = np.zeros((n_kept_obj, 3, 3), dtype=np.float64)
    cov_mats[:, 0, 0], cov_mats[:, 1, 1], cov_mats[:, 2, 2] = cov_zz, cov_yy, cov_xx
    cov_mats[:, 0, 1] = cov_mats[:, 1, 0] = cov_zy
    cov_mats[:, 0, 2] = cov_mats[:, 2, 0] = cov_zx
    cov_mats[:, 1, 2] = cov_mats[:, 2, 1] = cov_yx

    log(f"  batched eigendecomposition of {n_kept_obj:,} 3x3 covariance matrices...")
    eigvals = np.linalg.eigvalsh(cov_mats)
    eigvals = np.clip(eigvals, a_min=0.0, a_max=None)
    lam3, lam2, lam1 = eigvals[:, 0], eigvals[:, 1], eigvals[:, 2]
    voxel_var_floor = 1.0 / 12.0
    near_planar = lam3 < voxel_var_floor
    near_linear = lam2 < voxel_var_floor
    lam2_floored = np.maximum(lam2, voxel_var_floor)
    lam3_floored = np.maximum(lam3, voxel_var_floor)
    elongation = np.sqrt(lam1 / lam2_floored)
    flatness = np.sqrt(lam2_floored / lam3_floored)
    elongation = np.clip(elongation, 1.0, None)
    flatness = np.clip(flatness, 1.0, None)

    log("  Computing sphericity (marching cubes per object, voxel-proxy fallback)...")
    surf_lbl = labels[surface_mask]
    surf_counts = np.bincount(surf_lbl, minlength=minlen).astype(np.float64)
    pore_adj_surf_lbl = labels[surface_mask & pore_dilated]
    pore_adj_surf_counts = np.bincount(pore_adj_surf_lbl, minlength=minlen).astype(np.float64)

    surf_n = surf_counts[kept_ids]
    surf_pore_n = pore_adj_surf_counts[kept_ids]
    eps = 1e-9
    volume_um3 = nk * voxel_vol_um3
    pore_contact_fraction = np.where(surf_n > 0, surf_pore_n / np.maximum(surf_n, eps), np.nan)

    from skimage.measure import marching_cubes, mesh_surface_area
    bboxes = ndi.find_objects(labels)
    sphericity = np.empty(n_kept_obj, dtype=np.float64)
    sphericity_method = np.empty(n_kept_obj, dtype=object)
    t_mc = time.time()
    for i, obj_id in enumerate(kept_ids):
        slc = bboxes[obj_id - 1]
        local_mask = labels[slc] == obj_id
        area_mc = None
        try:
            padded = np.pad(local_mask, 1, mode="constant", constant_values=False)
            verts, faces, _, _ = marching_cubes(padded.astype(np.float32), level=0.5, spacing=(voxel_um,) * 3)
            area_mc = mesh_surface_area(verts, faces)
        except (ValueError, RuntimeError):
            area_mc = None
        if area_mc is not None and area_mc > 0:
            area_um2 = area_mc
            sphericity_method[i] = "marching_cubes"
        else:
            area_um2 = max(surf_n[i], 1.0) * (voxel_um ** 2)
            sphericity_method[i] = "voxel_proxy_fallback"
        sphericity[i] = (np.pi ** (1 / 3) * (6 * volume_um3[i]) ** (2 / 3)) / max(area_um2, eps)
    log(f"  sphericity for {n_kept_obj:,} objects done ({time.time()-t_mc:.1f}s); "
        f"{int((sphericity_method == 'voxel_proxy_fallback').sum())} used the voxel-proxy fallback")
    n_over_1 = int((sphericity > 1.0).sum())
    if n_over_1:
        log(f"  {n_over_1} objects had raw sphericity > 1.0 -- clipped to 1.0 per spec")
    sphericity = np.clip(sphericity, 0.0, 1.0)

    diameter_um = (6.0 * volume_um3 / np.pi) ** (1.0 / 3.0)

    df = pd.DataFrame({
        "soil": soil_key,
        "group": SOIL_GROUP[soil_key],
        "object_id": kept_ids,
        "n_voxels": nk.astype(int),
        "diameter_um": diameter_um,
        "elongation": elongation,
        "flatness": flatness,
        "near_planar": near_planar,
        "near_linear": near_linear,
        "sphericity": sphericity,
        "sphericity_method": sphericity_method,
        "pore_contact_fraction": pore_contact_fraction,
        "centroid_z_um": mean_z * voxel_um,
        "centroid_y_um": mean_y * voxel_um,
        "centroid_x_um": mean_x * voxel_um,
    })
    df = df.dropna(subset=FEATURE_NAMES)

    df.attrs["n_total_voxels"] = n_total
    df.attrs["voxel_um"] = voxel_um
    df.attrs["label"] = cfg["label"]
    df.attrs["n_objects_raw"] = int(n_objects_raw)
    df.attrs["n_objects_kept_by_cutoff"] = n_kept
    df.attrs["min_voxels_cutoff"] = float(min_voxels_cutoff)
    df.attrs["min_diameter_um"] = float(min_diameter_um)
    log(f"  features computed for {len(df):,} objects (dropped {n_kept_obj - len(df)} with undefined contact fraction)")
    return df


def spatial_pattern(df: pd.DataFrame) -> Dict:
    coords = df[["centroid_z_um", "centroid_y_um", "centroid_x_um"]].to_numpy()
    n_total_voxels = df.attrs["n_total_voxels"]
    voxel_um = df.attrs["voxel_um"]
    sample_volume_um3 = n_total_voxels * voxel_um ** 3

    if len(coords) < 2:
        return {
            "n_objects": int(len(coords)),
            "mean_nn_distance_um": None,
            "median_nn_distance_um": None,
            "expected_nn_distance_um_csr": None,
            "clark_evans_r_index": None,
            "verdict": "too few objects (n<2) for nearest-neighbor spatial statistics",
            "object_density_per_um3": len(coords) / sample_volume_um3,
        }

    tree = cKDTree(coords)
    dist, _ = tree.query(coords, k=2)
    nn_dist = dist[:, 1]

    density = len(coords) / sample_volume_um3
    expected_nn = float(gamma_fn(4 / 3) * (3 / (4 * np.pi * density)) ** (1 / 3))
    observed_nn = float(np.mean(nn_dist))
    r_index = observed_nn / expected_nn if expected_nn > 0 else float("nan")
    verdict = "aggregated/clustered" if r_index < 0.9 else ("dispersed/regular" if r_index > 1.1 else "close to random (CSR)")

    return {
        "n_objects": int(len(coords)),
        "mean_nn_distance_um": observed_nn,
        "median_nn_distance_um": float(np.median(nn_dist)),
        "expected_nn_distance_um_csr": expected_nn,
        "clark_evans_r_index": r_index,
        "verdict": verdict,
        "object_density_per_um3": density,
    }


def cluster_dataset(df: pd.DataFrame, scaler: StandardScaler) -> pd.DataFrame:
    X = scaler.transform(_cluster_feature_matrix(df))
    best_k, best_score, best_labels = None, -2.0, None
    scores = {}
    for k in range(2, 7):
        if k >= len(df):
            continue
        km = KMeans(n_clusters=k, n_init=10, random_state=0)
        cl = km.fit_predict(X)
        if len(np.unique(cl)) < 2:
            continue
        score = silhouette_score(X, cl)
        scores[k] = score
        if score > best_score:
            best_k, best_score, best_labels = k, score, cl
    df = df.copy()
    if best_labels is None:
        # Too few objects to form >=2 clusters -- everything is archetype/cluster 0.
        df["cluster_id"] = 0
        df.attrs["silhouette_scores"] = {}
        df.attrs["best_k"] = 1
        df.attrs["best_silhouette"] = float("nan")
    else:
        df["cluster_id"] = best_labels
        df.attrs["silhouette_scores"] = scores
        df.attrs["best_k"] = best_k
        df.attrs["best_silhouette"] = best_score
    return df


def plot_diagnostics(soil_key: str, df: pd.DataFrame, run_name: str) -> None:
    out_dir = OUT_ROOT / soil_key
    out_dir.mkdir(parents=True, exist_ok=True)
    scores = df.attrs["silhouette_scores"]

    if scores:
        fig, ax = plt.subplots(figsize=(5, 4), dpi=150)
        ax.plot(list(scores.keys()), list(scores.values()), "o-")
        ax.axvline(df.attrs["best_k"], color="red", linestyle="--", alpha=0.6, label=f"chosen k={df.attrs['best_k']}")
        ax.set_xlabel("k")
        ax.set_ylabel("Silhouette score")
        ax.set_title(f"{df.attrs['label']} [{run_name}]\nKMeans silhouette vs k (n={len(df)})")
        ax.legend()
        fig.tight_layout()
        fig.savefig(str(out_dir / f"clustering_silhouette_vs_k_{run_name}.png"), dpi=150)
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(5.5, 5), dpi=150)
    sc = ax.scatter(df["elongation"], df["sphericity"], c=df["cluster_id"], cmap="tab10", s=30, alpha=0.8)
    ax.set_xlabel("Elongation (largest/smallest principal axis)")
    ax.set_ylabel("Sphericity")
    ax.set_title(f"{df.attrs['label']} [{run_name}]\nk={df.attrs['best_k']} clusters, n={len(df)}")
    fig.colorbar(sc, ax=ax, label="cluster_id")
    fig.tight_layout()
    fig.savefig(str(out_dir / f"clustering_elongation_vs_sphericity_{run_name}.png"), dpi=150)
    plt.close(fig)


def cluster_profile_table(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    n_total = len(df)
    for cid, g in df.groupby("cluster_id"):
        rows.append({
            "soil": df.attrs["label"],
            "cluster_id": int(cid),
            "n_objects": len(g),
            "pct_of_soil_objects": 100 * len(g) / n_total,
            "mean_elongation": g["elongation"].mean(),
            "median_elongation": g["elongation"].median(),
            "mean_flatness": g["flatness"].mean(),
            "median_flatness": g["flatness"].median(),
            "mean_sphericity": g["sphericity"].mean(),
            "median_sphericity": g["sphericity"].median(),
            "mean_pore_contact_fraction": g["pore_contact_fraction"].mean(),
            "median_pore_contact_fraction": g["pore_contact_fraction"].median(),
            "mean_diameter_um": g["diameter_um"].mean(),
            "median_diameter_um": g["diameter_um"].median(),
        })
    return pd.DataFrame(rows)


def main(run_name: str) -> None:
    soil_keys = list(DATASETS.keys())
    log(f"=== Run '{run_name}': {soil_keys} ===")
    log(f"Groups: { {sk: SOIL_GROUP[sk] for sk in soil_keys} }")
    log(f"Resolvability cutoff: >= {MIN_VOXELS_ACROSS_DIAMETER:.0f} voxels across equivalent-sphere diameter "
        f"(same threshold applied identically to all 3 volumes)")

    dfs = {}
    cutoff_report = {}
    for sk in soil_keys:
        dfs[sk] = compute_soil_features(sk, DATASETS[sk])
        cutoff_report[sk] = {
            "path": DATASETS[sk]["path"],
            "voxel_um": DATASETS[sk]["voxel_um"],
            "n_objects_raw": dfs[sk].attrs["n_objects_raw"],
            "n_objects_kept_by_resolvability_cutoff": dfs[sk].attrs["n_objects_kept_by_cutoff"],
            "n_objects_used_after_contact_fraction_dropna": len(dfs[sk]),
            "min_voxels_cutoff": dfs[sk].attrs["min_voxels_cutoff"],
            "min_diameter_um": dfs[sk].attrs["min_diameter_um"],
        }

    with (OUT_ROOT / f"object_counts_before_after_cutoff_{run_name}.json").open("w", encoding="utf-8") as fh:
        json.dump(cutoff_report, fh, indent=2)
    log(f"Wrote object_counts_before_after_cutoff_{run_name}.json")

    log(f"Fitting StandardScaler across ONLY this run's 3 volumes -- no pooling with any other branch/soil...")
    pooled = np.concatenate([_cluster_feature_matrix(dfs[sk]) for sk in soil_keys], axis=0)
    scaler = StandardScaler().fit(pooled)

    spatial_results = {}
    profile_tables = []
    for sk in soil_keys:
        log(f"=== {sk}: spatial pattern ===")
        spatial_results[sk] = spatial_pattern(dfs[sk])
        log(f"  n={spatial_results[sk]['n_objects']}  "
            f"R={spatial_results[sk]['clark_evans_r_index']}  ({spatial_results[sk]['verdict']})")

        log(f"=== {sk}: clustering ===")
        dfs[sk] = cluster_dataset(dfs[sk], scaler)
        log(f"  best_k={dfs[sk].attrs['best_k']}  silhouette={dfs[sk].attrs['best_silhouette']}")
        plot_diagnostics(sk, dfs[sk], run_name)
        profile_tables.append(cluster_profile_table(dfs[sk]))

    with (OUT_ROOT / f"pom_spatial_pattern_summary_{run_name}.json").open("w", encoding="utf-8") as fh:
        json.dump(spatial_results, fh, indent=2)
    log(f"Wrote pom_spatial_pattern_summary_{run_name}.json")

    profile_df = pd.concat(profile_tables, axis=0, ignore_index=True)
    profile_df.to_csv(OUT_ROOT / f"pom_cluster_profiles_{run_name}.csv", index=False)
    log(f"Wrote pom_cluster_profiles_{run_name}.csv")

    log("=== Cross-volume archetype matching (per-volume cluster centroids) ===")
    centroid_rows = []
    for sk in soil_keys:
        df = dfs[sk]
        Xs = scaler.transform(_cluster_feature_matrix(df))
        for cid in sorted(df["cluster_id"].unique()):
            mask = (df["cluster_id"] == cid).to_numpy()
            centroid_rows.append({
                "soil": sk, "group": SOIL_GROUP[sk], "cluster_id": int(cid),
                "centroid": Xs[mask].mean(axis=0), "n": int(mask.sum()),
            })

    centroid_matrix = np.stack([r["centroid"] for r in centroid_rows])
    n_centroids = len(centroid_rows)
    max_k = min(n_centroids - 1, max(df["cluster_id"].nunique() for df in dfs.values()))
    max_k = max(max_k, 2)

    best_ak, best_ascore, best_alabels = None, -2.0, None
    for ak in range(2, max_k + 1):
        if ak >= n_centroids:
            continue
        km = KMeans(n_clusters=ak, n_init=10, random_state=0)
        al = km.fit_predict(centroid_matrix)
        if len(np.unique(al)) < 2:
            continue
        score = silhouette_score(centroid_matrix, al)
        if score > best_ascore:
            best_ak, best_ascore, best_alabels = ak, score, al

    if best_alabels is None:
        best_ak = 1
        best_alabels = np.zeros(n_centroids, dtype=int)
        best_ascore = float("nan")

    for r, a in zip(centroid_rows, best_alabels):
        r["archetype_id"] = int(a)

    archetype_map = {(r["soil"], r["cluster_id"]): r["archetype_id"] for r in centroid_rows}
    for sk in soil_keys:
        dfs[sk]["archetype_id"] = dfs[sk]["cluster_id"].map(lambda c, sk=sk: archetype_map[(sk, c)])

    combined = pd.concat([dfs[sk] for sk in soil_keys], axis=0, ignore_index=True)

    n_archetypes = int(combined["archetype_id"].max()) + 1

    # --- Part 3: per-volume archetype PROPORTION VECTORS ---
    proportion_vectors = {}
    for sk in soil_keys:
        df = dfs[sk]
        n_total = len(df)
        vec = np.zeros(n_archetypes, dtype=np.float64)
        counts = df["archetype_id"].value_counts()
        for aid, c in counts.items():
            vec[int(aid)] = c / n_total
        proportion_vectors[sk] = vec.tolist()

    mishmar_keys = [sk for sk in soil_keys if SOIL_GROUP[sk] == "mishmar"]
    mishmar_matrix = np.stack([proportion_vectors[sk] for sk in mishmar_keys])
    mishmar_mean = mishmar_matrix.mean(axis=0)
    mishmar_se = mishmar_matrix.std(axis=0, ddof=1) / np.sqrt(len(mishmar_keys)) if len(mishmar_keys) > 1 else np.full(n_archetypes, np.nan)
    bnei_reem_vec = np.array(proportion_vectors["bnei_reem"])
    diff_from_mishmar_mean = bnei_reem_vec - mishmar_mean
    se_multiples = np.where(mishmar_se > 0, diff_from_mishmar_mean / mishmar_se, np.nan)

    proportion_report = {
        "n_archetypes": n_archetypes,
        "archetype_silhouette_on_centroids": float(best_ascore) if best_ascore == best_ascore else None,
        "note": "n=1 on the Bnei Re'em side -- this is a descriptive comparison, not an inferential test.",
        "bnei_reem": {
            "vector": bnei_reem_vec.tolist(),
            "n_objects": int(len(dfs["bnei_reem"])),
        },
        "mishmar_replicate_1_label_downsample": {
            "soil_key": mishmar_keys[0],
            "vector": proportion_vectors[mishmar_keys[0]],
            "n_objects": int(len(dfs[mishmar_keys[0]])),
        },
        "mishmar_replicate_2_label_downsample": {
            "soil_key": mishmar_keys[1] if len(mishmar_keys) > 1 else None,
            "vector": proportion_vectors[mishmar_keys[1]] if len(mishmar_keys) > 1 else None,
            "n_objects": int(len(dfs[mishmar_keys[1]])) if len(mishmar_keys) > 1 else None,
        },
        "mishmar_mean": mishmar_mean.tolist(),
        "mishmar_se": mishmar_se.tolist(),
        "bnei_reem_minus_mishmar_mean": diff_from_mishmar_mean.tolist(),
        "bnei_reem_deviation_in_mishmar_se_units": se_multiples.tolist(),
    }
    with (OUT_ROOT / f"pom_archetype_proportion_vectors_{run_name}.json").open("w", encoding="utf-8") as fh:
        json.dump(proportion_report, fh, indent=2)
    log(f"Wrote pom_archetype_proportion_vectors_{run_name}.json")
    print("\nArchetype proportion vectors (index = archetype_id):")
    for sk in soil_keys:
        print(f"  {sk:35s} n={len(dfs[sk]):3d}  {np.round(proportion_vectors[sk], 3)}")
    print(f"  {'mishmar mean':35s}      {np.round(mishmar_mean, 3)}")
    print(f"  {'mishmar SE':35s}      {np.round(mishmar_se, 3)}")

    # --- contingency tables (same structure as replicates run) ---
    contingency_per_replicate = pd.crosstab(combined["soil"], combined["archetype_id"])
    contingency_group = pd.crosstab(combined["group"], combined["archetype_id"])

    mishmar_only = combined[combined["group"] == "mishmar"]
    mishmar_internal = None
    if sorted(mishmar_only["soil"].unique()).__len__() == 2:
        cont_mishmar = pd.crosstab(mishmar_only["soil"], mishmar_only["archetype_id"])
        mishmar_internal = {"contingency_table": cont_mishmar.to_dict()}

    archetype_result = {
        "n_archetypes": n_archetypes,
        "archetype_silhouette": float(best_ascore) if best_ascore == best_ascore else None,
        "centroids": [
            {"soil": r["soil"], "group": r["group"], "cluster_id": r["cluster_id"], "archetype_id": r["archetype_id"], "n": r["n"]}
            for r in centroid_rows
        ],
        "per_replicate_contingency_table": contingency_per_replicate.to_dict(),
        "group_level_contingency_table": contingency_group.to_dict(),
        "mishmar_internal_consistency": mishmar_internal,
    }
    with (OUT_ROOT / f"pom_archetype_crosssoil_comparison_{run_name}.json").open("w", encoding="utf-8") as fh:
        json.dump(archetype_result, fh, indent=2)
    log(f"Wrote pom_archetype_crosssoil_comparison_{run_name}.json")
    print("\nPer-volume contingency table (soil x archetype):")
    print(contingency_per_replicate)
    print("\nGROUP-level contingency table (group x archetype):")
    print(contingency_group)

    combined.to_csv(OUT_ROOT / f"pom_object_features_{run_name}.csv", index=False)
    log(f"Wrote pom_object_features_{run_name}.csv ({len(combined):,} rows)")

    log(f"DONE ({run_name})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-name", required=True)
    args = parser.parse_args()
    main(args.run_name)
