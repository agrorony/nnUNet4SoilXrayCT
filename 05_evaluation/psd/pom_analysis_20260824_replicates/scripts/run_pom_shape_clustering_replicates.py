"""Part 5 -- POM object shape + spatial clustering for the replicate-comparison
run (pom_replicate_comparison_prompt.md).

Same script version/methodology as pom_analysis_20260824_ablation/scripts/
run_pom_shape_clustering_v2.py (marching-cubes sphericity, eigenvalue-floored
elongation/flatness, per-run StandardScaler, per-run output filenames) --
duplicated rather than imported per project convention of self-contained
scripts, and explicitly noted here so future runs know which version this is.

Adds GROUP-level archetype matching on top of v2's per-soil-key clustering:
this run has two Mishmar REPLICATES of the same soil (mishmar_label_downsample_1
= native 5.85um sample, mishmar_label_downsample_2 = second physical 8.8um
sample), both downsampled to ~15um. Part 5.3 of the prompt asks for the
cross-soil archetype comparison at the soil-GROUP level (Bnei Re'em pooled
vs. Mishmar pooled, i.e. collapsing the two Mishmar replicates into one
group), plus a separate look at whether the two Mishmar replicates resemble
each other (internal consistency check). Per-soil-key (i.e. per-replicate)
clustering/archetype counts are still computed and reported, exactly as v2
did, so the internal-consistency comparison is possible.

Only volumes from this run's DATASETS are ever loaded -- no reference to
mishmar_image_then_predict or the discarded Cu011_samp_2 branch anywhere.

Usage:
    python run_pom_shape_clustering_replicates.py --run-name replicates \
        bnei_reem mishmar_label_downsample_1 mishmar_label_downsample_2
"""
from __future__ import annotations

import argparse
import json
import sys
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
OLD_20260815_ROOT = OUT_ROOT.parent / "pom_analysis_20260815"
STRUCT_26 = np.ones((3, 3, 3), dtype=np.uint8)
STRUCT_FACE = ndi.generate_binary_structure(3, 1)
FEATURE_NAMES = ["elongation", "flatness", "sphericity", "pore_contact_fraction"]
CLUSTER_FEATURE_NAMES = ["log_elongation", "log_flatness", "sphericity", "pore_contact_fraction"]

# Maps each soil_key in this run to its physical-soil GROUP, for the
# group-level archetype contingency table (Part 5.3).
SOIL_GROUP = {
    "bnei_reem": "bnei_reem",
    "mishmar_label_downsample_1": "mishmar",
    "mishmar_label_downsample_2": "mishmar",
}

DATASETS = {
    "bnei_reem": dict(
        label="Bnei Re'em (Vertisol) -- n=1 (only plausible replicate; see Part 0)",
        path=r"\\hive3065\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources\bnei_reem_fresh_bnei_reem_i4\inference_concatenated\nlm_volume.nii.gz",
        voxel_um=15.000149, pore_label=5, pom_label=2,
        summary_json=OLD_20260815_ROOT / "bnei_reem" / "summary_pom_metrics.json",
    ),
    "mishmar_label_downsample_1": dict(
        label="Mishmar HaNegev (Loess) -- sample 1 (native 5.85um), label-downsampled ~15um",
        path=str(ABLATION_ROOT / "mishmar_label_downsample" / "mishmar_label_downsample.nii.gz"),
        voxel_um=15.000149, pore_label=5, pom_label=2,
        summary_json=ABLATION_ROOT / "mishmar_label_downsample" / "summary_pom_metrics.json",
    ),
    "mishmar_label_downsample_2": dict(
        label="Mishmar HaNegev (Loess) -- sample 2 (native 8.8um), label-downsampled ~15um",
        path=str(OUT_ROOT / "mishmar_label_downsample_2" / "mishmar_label_downsample_2.nii.gz"),
        voxel_um=15.000149, pore_label=5, pom_label=2,
        summary_json=OUT_ROOT / "mishmar_label_downsample_2" / "summary_pom_metrics.json",
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

    if not Path(cfg["summary_json"]).is_file():
        raise FileNotFoundError(f"{soil_key}: missing {cfg['summary_json']} -- run its A1-A3/B pipeline first")
    prior = json.loads(Path(cfg["summary_json"]).read_text())
    cutoff = prior["A1_noise_floor"]["proposed_default_cutoff"]["cutoff_voxels"]
    log(f"=== {soil_key} ({cfg['label']}) -- cutoff={cutoff} vox (from prior run) ===")

    log(f"Loading {cfg['path']}")
    vol = np.asarray(nib.load(cfg["path"]).dataobj)
    pore_mask = (vol == cfg["pore_label"])
    pom_mask_all = (vol == cfg["pom_label"])
    n_total = int(vol.size)
    del vol

    log("Labeling POM objects (26-connectivity)...")
    labels, n_objects_raw = ndi.label(pom_mask_all, structure=STRUCT_26)
    counts_all = np.bincount(labels.ravel())[1:]
    keep_default = np.zeros(n_objects_raw + 1, dtype=bool)
    keep_default[1:] = counts_all >= cutoff
    denoised_mask = keep_default[labels]
    n_kept = int(keep_default.sum())
    log(f"  n_objects_raw={n_objects_raw:,}  n_kept(>= {cutoff} vox)={n_kept:,}")

    pore_dilated = ndi.binary_dilation(pore_mask, structure=STRUCT_FACE)
    surface_mask = denoised_mask & ~ndi.binary_erosion(denoised_mask, structure=STRUCT_FACE, border_value=0)

    log("Computing per-object voxel-position moments (vectorized bincount)...")
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

    log("Computing sphericity (marching cubes per object, voxel-proxy fallback)...")
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
    log(f"  features computed for {len(df):,} objects (dropped {n_kept_obj - len(df)} with undefined contact fraction)")
    return df


def spatial_pattern(df: pd.DataFrame) -> Dict:
    coords = df[["centroid_z_um", "centroid_y_um", "centroid_x_um"]].to_numpy()
    n_total_voxels = df.attrs["n_total_voxels"]
    voxel_um = df.attrs["voxel_um"]
    sample_volume_um3 = n_total_voxels * voxel_um ** 3

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
    df["cluster_id"] = best_labels
    df.attrs["silhouette_scores"] = scores
    df.attrs["best_k"] = best_k
    df.attrs["best_silhouette"] = best_score
    return df


def plot_diagnostics(soil_key: str, df: pd.DataFrame, run_name: str) -> None:
    out_dir = OUT_ROOT / soil_key
    out_dir.mkdir(parents=True, exist_ok=True)
    scores = df.attrs["silhouette_scores"]

    fig, ax = plt.subplots(figsize=(5, 4), dpi=150)
    ax.plot(list(scores.keys()), list(scores.values()), "o-")
    ax.axvline(df.attrs["best_k"], color="red", linestyle="--", alpha=0.6, label=f"chosen k={df.attrs['best_k']}")
    ax.set_xlabel("k")
    ax.set_ylabel("Silhouette score")
    ax.set_title(f"{df.attrs['label']} [{run_name}]\nKMeans silhouette vs k")
    ax.legend()
    fig.tight_layout()
    fig.savefig(str(out_dir / f"clustering_silhouette_vs_k_{run_name}.png"), dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(5.5, 5), dpi=150)
    sc = ax.scatter(df["elongation"], df["sphericity"], c=df["cluster_id"], cmap="tab10", s=10, alpha=0.7)
    ax.set_xlabel("Elongation (largest/smallest principal axis)")
    ax.set_ylabel("Sphericity")
    ax.set_title(f"{df.attrs['label']} [{run_name}]\nk={df.attrs['best_k']} clusters")
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


def main(soil_keys: List[str], run_name: str) -> None:
    log(f"=== Run '{run_name}': {soil_keys} ===")
    log(f"Groups: { {sk: SOIL_GROUP[sk] for sk in soil_keys} }")
    dfs = {}
    for sk in soil_keys:
        dfs[sk] = compute_soil_features(sk, DATASETS[sk])

    log(f"Fitting StandardScaler across ONLY this run's soils ({soil_keys}) -- no pooling with excluded branches...")
    pooled = np.concatenate([_cluster_feature_matrix(dfs[sk]) for sk in soil_keys], axis=0)
    scaler = StandardScaler().fit(pooled)

    spatial_results = {}
    profile_tables = []
    for sk in soil_keys:
        log(f"=== {sk}: spatial pattern ===")
        spatial_results[sk] = spatial_pattern(dfs[sk])
        log(f"  n={spatial_results[sk]['n_objects']}  mean NN={spatial_results[sk]['mean_nn_distance_um']:.2f}um  "
            f"R={spatial_results[sk]['clark_evans_r_index']:.3f} ({spatial_results[sk]['verdict']})")

        log(f"=== {sk}: clustering ===")
        dfs[sk] = cluster_dataset(dfs[sk], scaler)
        log(f"  best_k={dfs[sk].attrs['best_k']}  silhouette={dfs[sk].attrs['best_silhouette']:.3f}")
        plot_diagnostics(sk, dfs[sk], run_name)
        profile_tables.append(cluster_profile_table(dfs[sk]))

    with (OUT_ROOT / f"pom_spatial_pattern_summary_{run_name}.json").open("w", encoding="utf-8") as fh:
        json.dump(spatial_results, fh, indent=2)
    log(f"Wrote pom_spatial_pattern_summary_{run_name}.json")

    profile_df = pd.concat(profile_tables, axis=0, ignore_index=True)
    profile_df.to_csv(OUT_ROOT / f"pom_cluster_profiles_{run_name}.csv", index=False)
    log(f"Wrote pom_cluster_profiles_{run_name}.csv")

    log("=== Cross-soil archetype matching (per-replicate centroids) ===")
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

    for r, a in zip(centroid_rows, best_alabels):
        r["archetype_id"] = int(a)

    archetype_map = {(r["soil"], r["cluster_id"]): r["archetype_id"] for r in centroid_rows}
    for sk in soil_keys:
        dfs[sk]["archetype_id"] = dfs[sk]["cluster_id"].map(lambda c, sk=sk: archetype_map[(sk, c)])

    combined = pd.concat([dfs[sk] for sk in soil_keys], axis=0, ignore_index=True)

    # Per-replicate (soil_key) contingency table -- internal-consistency view.
    contingency_per_replicate = pd.crosstab(combined["soil"], combined["archetype_id"])
    chi2_r, p_r, dof_r, _ = sstats.chi2_contingency(contingency_per_replicate)

    # Group-level contingency table -- the Part 5.3 primary result
    # (bnei_reem pooled vs. mishmar pooled, collapsing the two Mishmar
    # replicates into one row).
    contingency_group = pd.crosstab(combined["group"], combined["archetype_id"])
    chi2_g, p_g, dof_g, _ = sstats.chi2_contingency(contingency_group)

    # Mishmar-internal-consistency: compare the two Mishmar replicates'
    # archetype composition to each other directly (2-row contingency).
    mishmar_only = combined[combined["group"] == "mishmar"]
    mishmar_replicates = sorted(mishmar_only["soil"].unique())
    mishmar_internal = None
    if len(mishmar_replicates) == 2:
        cont_mishmar = pd.crosstab(mishmar_only["soil"], mishmar_only["archetype_id"])
        chi2_m, p_m, dof_m, _ = sstats.chi2_contingency(cont_mishmar)
        mishmar_internal = {
            "contingency_table": cont_mishmar.to_dict(),
            "chi2": float(chi2_m), "dof": int(dof_m), "p": float(p_m),
            "interpretation": (
                "Low p means the two Mishmar replicates differ in archetype composition "
                "(physical-sample variability comparable to or larger than the group's "
                "internal spread); high p means they look similar (consistent with a real, "
                "reproducible Mishmar signature rather than single-sample noise)."
            ),
        }

    archetype_result = {
        "n_archetypes": int(best_ak),
        "archetype_silhouette": float(best_ascore),
        "centroids": [
            {"soil": r["soil"], "group": r["group"], "cluster_id": r["cluster_id"], "archetype_id": r["archetype_id"], "n": r["n"]}
            for r in centroid_rows
        ],
        "per_replicate": {
            "contingency_table": contingency_per_replicate.to_dict(),
            "chi2": float(chi2_r), "dof": int(dof_r), "p": float(p_r),
        },
        "group_level": {
            "contingency_table": contingency_group.to_dict(),
            "chi2": float(chi2_g), "dof": int(dof_g), "p": float(p_g),
        },
        "mishmar_internal_consistency": mishmar_internal,
    }
    with (OUT_ROOT / f"pom_archetype_crosssoil_comparison_{run_name}.json").open("w", encoding="utf-8") as fh:
        json.dump(archetype_result, fh, indent=2)
    log(f"Archetypes: k={best_ak} (silhouette={best_ascore:.3f})")
    log(f"  per-replicate: chi2={chi2_r:.2f} dof={dof_r} p={p_r:.4g}")
    log(f"  GROUP-level (bnei_reem vs mishmar pooled): chi2={chi2_g:.2f} dof={dof_g} p={p_g:.4g}")
    if mishmar_internal:
        log(f"  Mishmar-internal (replicate 1 vs 2): chi2={mishmar_internal['chi2']:.2f} dof={mishmar_internal['dof']} p={mishmar_internal['p']:.4g}")
    print("\nPer-replicate contingency table (soil x archetype):")
    print(contingency_per_replicate)
    print("\nGROUP-level contingency table (group x archetype):")
    print(contingency_group)
    if mishmar_internal:
        print("\nMishmar-internal contingency table (replicate x archetype):")
        print(pd.DataFrame(mishmar_internal["contingency_table"]))

    combined.to_csv(OUT_ROOT / f"pom_object_features_{run_name}.csv", index=False)
    log(f"Wrote pom_object_features_{run_name}.csv ({len(combined):,} rows)")

    log(f"DONE ({run_name})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-name", required=True, help="Distinct tag for output filenames, e.g. replicates")
    parser.add_argument("soil_keys", nargs="+", choices=list(DATASETS.keys()))
    args = parser.parse_args()
    main(args.soil_keys, args.run_name)
