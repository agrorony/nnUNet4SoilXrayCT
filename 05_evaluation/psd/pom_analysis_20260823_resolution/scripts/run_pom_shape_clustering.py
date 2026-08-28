"""Part B -- POM object shape + spatial clustering, cross-soil archetypes.

For each dataset (bnei_reem 15um, mishmar_native 5.85um, mishmar_15um new
15um sample), on the denoised POM objects (>= that dataset's own elbow
cutoff, per its summary_pom_metrics.json):

  B1. Per-object shape: elongation (sqrt(lambda1/lambda2)), flatness
      (sqrt(lambda2/lambda3)) from the voxel-coordinate covariance matrix
      (lambda1>=lambda2>=lambda3, eigenvalues of the covariance of the
      object's voxel positions -- principal-axis LENGTHS are proportional
      to sqrt(eigenvalue), so this ratio is literally "largest principal
      axis / smallest principal axis"); sphericity via a voxel-surface-count
      proxy (cheaper than marching_cubes for ~1500-1750 objects/soil,
      explicitly allowed by the prompt); per-object POM-pore contact
      fraction (same voxel-surface proxy, restricted to face-adjacency with
      the pore phase).

  B2. Spatial pattern: nearest-neighbor distance between object centroids
      (um), plus a 3D Clark-Evans-analog index R = observed mean NN / expected
      mean NN under a homogeneous 3D Poisson process at the same object
      density (R<1 aggregated, R~1 random, R>1 dispersed/regular). Cheaper
      than 3D Ripley's K per the prompt's own "pick whichever is cheaper"
      allowance, and gives the same aggregated/random/dispersed verdict.

  B3. Clustering: KMeans (k=2..6, silhouette-selected) on
      {elongation, flatness, sphericity, pore_contact_fraction} (size
      deliberately excluded, reported post-hoc only), STANDARDIZED WITH A
      SINGLE SCALER FITTED ACROSS ALL SOILS POOLED -- so per-soil cluster
      centroids live in the same space and are directly comparable for the
      cross-soil archetype match afterward (a per-soil-only scaler would
      make "similar" clusters in different soils land at different
      coordinates purely from differing per-soil feature ranges).

Cross-soil archetype matching: cluster the pooled set of per-soil cluster
centroids themselves (k chosen by silhouette) to find shared archetypes,
then chi-square test of independence on archetype-membership x soil.

All per-object feature computation is fully vectorized via np.bincount over
(z,y,x) covariance/moment sums -- no per-object Python loop, since each soil
has 1500-1750 kept objects and looping marching_cubes/covariance per object
would be the slow path.
"""
from __future__ import annotations

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
STRUCT_26 = np.ones((3, 3, 3), dtype=np.uint8)
STRUCT_FACE = ndi.generate_binary_structure(3, 1)
FEATURE_NAMES = ["elongation", "flatness", "sphericity", "pore_contact_fraction"]
# elongation/flatness are ratio (multiplicative, long-right-tail) quantities;
# log-transforming just for the clustering feature space keeps a handful of
# very-high-aspect-ratio real objects from dominating Euclidean-distance
# KMeans purely by scale. Raw elongation/flatness are still reported as-is
# in every output table -- only the clustering input uses the log.
CLUSTER_FEATURE_NAMES = ["log_elongation", "log_flatness", "sphericity", "pore_contact_fraction"]


def _cluster_feature_matrix(df: pd.DataFrame) -> np.ndarray:
    return np.column_stack([
        np.log(df["elongation"].to_numpy()),
        np.log(df["flatness"].to_numpy()),
        df["sphericity"].to_numpy(),
        df["pore_contact_fraction"].to_numpy(),
    ])

DATASETS = {
    "bnei_reem": dict(
        label="Bnei Re'em (Vertisol)",
        path=r"\\hive3065\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources\bnei_reem_fresh_bnei_reem_i4\inference_concatenated\nlm_volume.nii.gz",
        voxel_um=15.000149, pore_label=5, pom_label=2,
        summary_json=OUT_ROOT.parent / "pom_analysis_20260815" / "bnei_reem" / "summary_pom_metrics.json",
    ),
    "mishmar_native": dict(
        label="Mishmar HaNegev (Loess) -- native 5.85um",
        path=r"\\hive3065\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources\mishmar_hanegev_maoz_3_5p85um\inference_output_concat_loess_i2\mishmar_hanegev_maoz_3_5p85um.nii.gz",
        voxel_um=5.85, pore_label=5, pom_label=2,
        summary_json=OUT_ROOT.parent / "pom_analysis_20260815" / "mishmar" / "summary_pom_metrics.json",
    ),
    "mishmar_15um": dict(
        label="Mishmar HaNegev (Loess) -- new 15um sample",
        path=r"\\hive3065\Yael_Mishael\Rony\remote_computer backup\nnUNet_resources\mishmar_hanegev_Cu011_samp_2_Rec_nlm\inference_output_concat_loess_i2\mishmar_hanegev_Cu011_samp_2_Rec_nlm.nii.gz",
        voxel_um=15.000149, pore_label=5, pom_label=2,
        summary_json=OUT_ROOT / "mishmar_15um" / "summary_pom_metrics.json",
    ),
}


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def compute_soil_features(soil_key: str, cfg: dict) -> pd.DataFrame:
    out_dir = OUT_ROOT / soil_key
    out_dir.mkdir(parents=True, exist_ok=True)
    voxel_um = cfg["voxel_um"]
    voxel_vol_um3 = voxel_um ** 3

    if not cfg["summary_json"].is_file():
        raise FileNotFoundError(f"{soil_key}: missing {cfg['summary_json']} -- run its A1-A3/B pipeline first")
    prior = json.loads(cfg["summary_json"].read_text())
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
    eigvals = np.linalg.eigvalsh(cov_mats)  # ascending: (n_kept_obj, 3) -> [l3,l2,l1]
    eigvals = np.clip(eigvals, a_min=0.0, a_max=None)
    lam3, lam2, lam1 = eigvals[:, 0], eigvals[:, 1], eigvals[:, 2]
    # Physically-motivated floor: a coordinate sample of integer voxel indices
    # that all share the same value has *exactly* zero variance -- that is a
    # real "no extent along this axis" object (a 1-voxel-thick flake/rod), not
    # numerical noise. A near-zero float epsilon (e.g. 1e-9) turns that into a
    # meaningless elongation/flatness value in the thousands that then
    # dominates any Euclidean-distance clustering. Floor eigenvalues at
    # 1/12 voxel^2 (variance of a voxel-wide uniform distribution -- the
    # smallest physically resolvable extent at this grid spacing) instead,
    # and flag objects that hit the floor explicitly rather than silently
    # clipping their ratio to an arbitrary huge number.
    voxel_var_floor = 1.0 / 12.0
    near_planar = lam3 < voxel_var_floor  # zero/near-zero extent along shortest axis
    near_linear = lam2 < voxel_var_floor  # zero/near-zero extent along middle axis too
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
            area_um2 = max(surf_n[i], 1.0) * (voxel_um ** 2)  # voxel-face proxy fallback
            sphericity_method[i] = "voxel_proxy_fallback"
        sphericity[i] = (np.pi ** (1 / 3) * (6 * volume_um3[i]) ** (2 / 3)) / max(area_um2, eps)
    log(f"  sphericity for {n_kept_obj:,} objects done ({time.time()-t_mc:.1f}s); "
        f"{int((sphericity_method == 'voxel_proxy_fallback').sum())} used the voxel-proxy fallback")
    n_over_1 = int((sphericity > 1.0).sum())
    if n_over_1:
        log(f"  {n_over_1} objects had raw sphericity > 1.0 (marching-cubes mesh smoothing "
            f"slightly underestimates area for small near-convex objects) -- clipped to 1.0 per spec")
    sphericity = np.clip(sphericity, 0.0, 1.0)

    diameter_um = (6.0 * volume_um3 / np.pi) ** (1.0 / 3.0)

    df = pd.DataFrame({
        "soil": soil_key,
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

    log(f"  n_voxels_total={n_total:,}")
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

    density = len(coords) / sample_volume_um3  # objects per um^3
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


def plot_diagnostics(soil_key: str, df: pd.DataFrame) -> None:
    out_dir = OUT_ROOT / soil_key
    scores = df.attrs["silhouette_scores"]

    fig, ax = plt.subplots(figsize=(5, 4), dpi=150)
    ax.plot(list(scores.keys()), list(scores.values()), "o-")
    ax.axvline(df.attrs["best_k"], color="red", linestyle="--", alpha=0.6, label=f"chosen k={df.attrs['best_k']}")
    ax.set_xlabel("k")
    ax.set_ylabel("Silhouette score")
    ax.set_title(f"{df.attrs['label']}\nKMeans silhouette vs k")
    ax.legend()
    fig.tight_layout()
    fig.savefig(str(out_dir / "clustering_silhouette_vs_k.png"), dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(5.5, 5), dpi=150)
    sc = ax.scatter(df["elongation"], df["sphericity"], c=df["cluster_id"], cmap="tab10", s=10, alpha=0.7)
    ax.set_xlabel("Elongation (largest/smallest principal axis)")
    ax.set_ylabel("Sphericity")
    ax.set_title(f"{df.attrs['label']}\nk={df.attrs['best_k']} clusters")
    fig.colorbar(sc, ax=ax, label="cluster_id")
    fig.tight_layout()
    fig.savefig(str(out_dir / "clustering_elongation_vs_sphericity.png"), dpi=150)
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


def main(soil_keys: List[str]) -> None:
    dfs = {}
    for sk in soil_keys:
        dfs[sk] = compute_soil_features(sk, DATASETS[sk])

    log("Fitting global StandardScaler across all soils (pooled) for comparable cluster centroids...")
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
        plot_diagnostics(sk, dfs[sk])
        profile_tables.append(cluster_profile_table(dfs[sk]))

    # -------------------- combined per-object CSV --------------------
    combined = pd.concat([dfs[sk] for sk in soil_keys], axis=0, ignore_index=True)
    combined.to_csv(OUT_ROOT / "pom_object_features_all_soils.csv", index=False)
    log(f"Wrote pom_object_features_all_soils.csv ({len(combined):,} rows)")

    # -------------------- spatial pattern summary --------------------
    with (OUT_ROOT / "pom_spatial_pattern_summary.json").open("w", encoding="utf-8") as fh:
        json.dump(spatial_results, fh, indent=2)
    log("Wrote pom_spatial_pattern_summary.json")

    # -------------------- cluster profile table --------------------
    profile_df = pd.concat(profile_tables, axis=0, ignore_index=True)
    profile_df.to_csv(OUT_ROOT / "pom_cluster_profiles.csv", index=False)
    log("Wrote pom_cluster_profiles.csv")

    # -------------------- cross-soil archetype matching --------------------
    if len(soil_keys) >= 2:
        log("=== Cross-soil archetype matching ===")
        centroid_rows = []
        for sk in soil_keys:
            df = dfs[sk]
            Xs = scaler.transform(_cluster_feature_matrix(df))
            for cid in sorted(df["cluster_id"].unique()):
                mask = (df["cluster_id"] == cid).to_numpy()
                centroid_rows.append({"soil": sk, "cluster_id": int(cid), "centroid": Xs[mask].mean(axis=0), "n": int(mask.sum())})

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

        combined2 = pd.concat([dfs[sk] for sk in soil_keys], axis=0, ignore_index=True)
        combined2.to_csv(OUT_ROOT / "pom_object_features_all_soils.csv", index=False)

        contingency = pd.crosstab(combined2["soil"], combined2["archetype_id"])
        chi2, p, dof, expected = sstats.chi2_contingency(contingency)

        archetype_result = {
            "n_archetypes": int(best_ak),
            "archetype_silhouette": float(best_ascore),
            "centroids": [
                {"soil": r["soil"], "cluster_id": r["cluster_id"], "archetype_id": r["archetype_id"], "n": r["n"]}
                for r in centroid_rows
            ],
            "contingency_table": contingency.to_dict(),
            "chi2": float(chi2),
            "dof": int(dof),
            "p": float(p),
        }
        with (OUT_ROOT / "pom_archetype_crosssoil_comparison.json").open("w", encoding="utf-8") as fh:
            json.dump(archetype_result, fh, indent=2)
        log(f"Archetypes: k={best_ak} (silhouette={best_ascore:.3f})  chi2={chi2:.2f} dof={dof} p={p:.4g}")
        print("\nContingency table (soil x archetype):")
        print(contingency)

    log("DONE")


if __name__ == "__main__":
    keys = sys.argv[1:] if len(sys.argv) > 1 else ["bnei_reem", "mishmar_native"]
    main(keys)
