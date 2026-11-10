"""A2 Step 1-2: re-aggregate the 2026-08-15 subvolume PSD runs into functional
size classes restricted to >=31um (per psd_binning_recommendation.md), and drop
whole-distribution median diameter from cross-soil claims.

Reuses the existing 24 psd_table.csv outputs from
fig4_inference_20260815/psd_runs/ (no re-computation of local thickness needed --
class fractions are just re-binnings of the same underlying histogram).

Classes (bin edges from fig4_inference_20260815/bin_edges_um.json, which already
merges in 30 and 150um edges; no exact 300um edge exists in that log-spaced
scheme -- the nearest available edge, 288.54um, is used as the practical >300um
boundary, ~4% off target and well within one log-bin width):

  31-150   : 30.0 <= D < 150.0    ("microbially active", Kravchenko/Dor)
  150-290  : 150.0 <= D < 288.54  ("transmission")
  >=290    : D >= 288.54          ("large macropores / biopores & cracks")

Sensitivity re-test (per recommendation, section c): 60-150um, i.e. D >= 61.346
(the psd_table bin center closest to the 4-voxel-at-15um-voxel limit) < 150,
compared against the full 31-150 class to check the coarse-scan under-detection
concern doesn't flip conclusions.
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
import scikit_posthocs as sp
from statsmodels.stats.multicomp import pairwise_tukeyhsd

ORIG_ROOT = Path(r"C:\Users\rony.schwartz\Documents\nnUNet4SoilXrayCT\05_evaluation\psd\fig4_inference_20260815")
OUT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ORIG_ROOT / "subvolume_extraction_manifest.json").read_text())

EDGE_300_APPROX = 288.53997802734375
RNG = np.random.default_rng(20260822)
N_PERM = 9999

SOIL_LABELS = {
    "bnei_reem": "Bnei Re'em (Vertisol)",
    "mishmar": "Mishmar HaNegev (Loess)",
    "rehovot": "Rehovot (Sand)",
}
SOIL_ORDER = ["bnei_reem", "mishmar", "rehovot"]


def find_run_dir(run_name: str) -> Path:
    matches = sorted((ORIG_ROOT / "psd_runs").glob(f"psd_diag_*_{run_name}"))
    if not matches:
        raise FileNotFoundError(f"No psd_diag run dir found for {run_name}")
    return matches[-1]


def class_fraction(df: pd.DataFrame, lo: float, hi: float, total_pore_voxels: int) -> float:
    mask = (df["Diameter_um"] >= lo) & (df["Diameter_um"] < hi)
    return float(df.loc[mask, "Volume_Count"].sum() / total_pore_voxels)


def build_class_metrics() -> pd.DataFrame:
    rows = []
    for soil, entries in MANIFEST.items():
        for entry in entries:
            if entry["excluded"]:
                continue
            run_name = f"{soil}_{entry['subvolume_id']}"
            run_dir = find_run_dir(run_name)
            df = pd.read_csv(run_dir / "psd_table.csv")
            total_pore_voxels = int(df["Volume_Count"].sum())
            porosity = entry["porosity"]

            f31_150_pore = class_fraction(df, 30.0, 150.0, total_pore_voxels)
            f150_290_pore = class_fraction(df, 150.0, EDGE_300_APPROX, total_pore_voxels)
            fge290_pore = class_fraction(df, EDGE_300_APPROX, 1e9, total_pore_voxels)
            f60_150_pore = class_fraction(df, 61.34638023376465, 150.0, total_pore_voxels)

            rows.append({
                "soil": soil,
                "subvolume_id": entry["subvolume_id"],
                "porosity": porosity,
                "frac31_150_of_pore": f31_150_pore,
                "frac31_150_of_total": f31_150_pore * porosity,
                "frac150_290_of_pore": f150_290_pore,
                "frac150_290_of_total": f150_290_pore * porosity,
                "fracGE290_of_pore": fge290_pore,
                "fracGE290_of_total": fge290_pore * porosity,
                "frac60_150_of_pore": f60_150_pore,
                "frac60_150_of_total": f60_150_pore * porosity,
                "psd_run_dir": str(run_dir),
            })
    return pd.DataFrame(rows)


# --- stats machinery (same approach as the 2026-08-15 run_stats.py) --------
def compact_letters(groups: list[str], sig_pairs: set[frozenset]) -> dict[str, str]:
    ns_edges = {frozenset(p) for p in itertools.combinations(groups, 2)} - sig_pairs
    import networkx as nx
    G = nx.Graph()
    G.add_nodes_from(groups)
    G.add_edges_from([tuple(e) for e in ns_edges])
    cliques = sorted(nx.find_cliques(G), key=len, reverse=True)
    covered_edges, covered_nodes, selected = set(), set(), []
    for c in cliques:
        edges_here = {frozenset(p) for p in itertools.combinations(c, 2)}
        if not edges_here.issubset(covered_edges) or not set(c).issubset(covered_nodes):
            selected.append(c)
            covered_edges |= edges_here
            covered_nodes |= set(c)
        if covered_nodes == set(groups) and (ns_edges <= covered_edges or not ns_edges):
            break
    letters = {g: "" for g in groups}
    for i, c in enumerate(selected):
        letter = chr(ord("a") + i)
        for g in c:
            letters[g] += letter
    return letters


def holm_correct(pvals: list[float]) -> list[float]:
    pvals = np.asarray(pvals, dtype=float)
    order = np.argsort(pvals)
    m = len(pvals)
    adj = np.empty(m)
    running_max = 0.0
    for rank, idx in enumerate(order):
        val = (m - rank) * pvals[idx]
        running_max = max(running_max, val)
        adj[idx] = min(running_max, 1.0)
    return adj.tolist()


def univariate_test(df: pd.DataFrame, metric: str, label: str) -> dict:
    groups = {s: df.loc[df.soil == s, metric].to_numpy() for s in SOIL_ORDER}
    all_vals = df[metric].to_numpy()
    group_means = {s: v.mean() for s, v in groups.items()}
    residuals = np.concatenate([v - group_means[s] for s, v in groups.items()])

    shapiro_stat, shapiro_p = stats.shapiro(residuals)
    levene_stat, levene_p = stats.levene(*groups.values())
    assumptions_ok = shapiro_p > 0.05 and levene_p > 0.05

    result = {
        "metric": metric, "label": label,
        "shapiro_W": shapiro_stat, "shapiro_p": shapiro_p,
        "levene_W": levene_stat, "levene_p": levene_p,
        "assumptions_ok": assumptions_ok,
    }

    n = len(all_vals)
    k = len(groups)
    grand_mean = all_vals.mean()
    ss_total = float(np.sum((all_vals - grand_mean) ** 2))
    ss_between = float(sum(len(v) * (group_means[s] - grand_mean) ** 2 for s, v in groups.items()))

    if assumptions_ok:
        f_stat, p_val = stats.f_oneway(*groups.values())
        eta2 = ss_between / ss_total
        result.update({
            "test": "one-way ANOVA", "statistic": float(f_stat),
            "df_between": k - 1, "df_within": n - k, "p": float(p_val),
            "effect_size_name": "eta^2", "effect_size": eta2,
        })
        tukey_df_long = pd.DataFrame({"value": all_vals, "group": df["soil"].to_numpy()})
        tukey = pairwise_tukeyhsd(tukey_df_long["value"], tukey_df_long["group"])
        sig_pairs = set()
        pairwise_rows = []
        for row in tukey.summary().data[1:]:
            g1, g2, meandiff, p_adj, lo, hi, reject = row
            pairwise_rows.append({"group1": g1, "group2": g2, "p_adj": float(p_adj), "reject": bool(reject)})
            if reject:
                sig_pairs.add(frozenset((g1, g2)))
        result["posthoc"] = "Tukey HSD"
    else:
        h_stat, p_val = stats.kruskal(*groups.values())
        eps2 = (h_stat - k + 1) / (n - k)
        result.update({
            "test": "Kruskal-Wallis", "statistic": float(h_stat),
            "df_between": k - 1, "df_within": None, "p": float(p_val),
            "effect_size_name": "epsilon^2", "effect_size": float(eps2),
        })
        dunn = sp.posthoc_dunn(df, val_col=metric, group_col="soil", p_adjust="holm")
        sig_pairs = set()
        pairwise_rows = []
        for g1, g2 in itertools.combinations(SOIL_ORDER, 2):
            p_adj = float(dunn.loc[g1, g2])
            reject = p_adj < 0.05
            pairwise_rows.append({"group1": g1, "group2": g2, "p_adj": p_adj, "reject": reject})
            if reject:
                sig_pairs.add(frozenset((g1, g2)))
        result["posthoc"] = "Dunn (Holm-corrected)"

    result["pairwise"] = pairwise_rows
    result["letters"] = compact_letters(SOIL_ORDER, sig_pairs)
    result["group_stats"] = {
        s: {"mean": float(np.mean(v)), "se": float(np.std(v, ddof=1) / np.sqrt(len(v))), "n": len(v)}
        for s, v in groups.items()
    }
    return result


def permanova(dist: np.ndarray, group_labels: np.ndarray, n_perm: int, rng) -> dict:
    N = dist.shape[0]
    groups = np.unique(group_labels)
    a = len(groups)
    d2 = dist ** 2

    def pseudo_f(labels):
        ss_total = d2.sum() / N
        ss_within = 0.0
        for g in groups:
            idx = np.where(labels == g)[0]
            ng = len(idx)
            if ng <= 1:
                continue
            sub = d2[np.ix_(idx, idx)]
            ss_within += sub.sum() / ng
        ss_among = ss_total - ss_within
        f = (ss_among / (a - 1)) / (ss_within / (N - a))
        r2 = ss_among / ss_total
        return f, r2

    f_obs, r2_obs = pseudo_f(group_labels)
    count_ge = 1
    for _ in range(n_perm):
        perm_labels = rng.permutation(group_labels)
        f_perm, _ = pseudo_f(perm_labels)
        if f_perm >= f_obs:
            count_ge += 1
    p = count_ge / (n_perm + 1)
    return {"pseudo_F": float(f_obs), "R2": float(r2_obs), "p": float(p), "df_among": a - 1, "df_within": N - a, "n_perm": n_perm}


def permanova_pairwise(dist_full, labels_full, n_perm, rng) -> list[dict]:
    rows = []
    for g1, g2 in itertools.combinations(SOIL_ORDER, 2):
        idx = np.where((labels_full == g1) | (labels_full == g2))[0]
        sub_dist = dist_full[np.ix_(idx, idx)]
        sub_labels = labels_full[idx]
        res = permanova(sub_dist, sub_labels, n_perm, rng)
        rows.append({"group1": g1, "group2": g2, **res})
    p_adj = holm_correct([r["p"] for r in rows])
    for r, p in zip(rows, p_adj):
        r["p_adj_holm"] = p
    return rows


def clr(x: np.ndarray) -> np.ndarray:
    """Centered log-ratio, with a small pseudo-count for zeros."""
    x = x + 1e-8
    logx = np.log(x)
    return logx - logx.mean(axis=1, keepdims=True)


def part_b_permanova_3class(df: pd.DataFrame) -> dict:
    from scipy.spatial.distance import pdist, squareform
    cols = ["frac31_150_of_total", "frac150_290_of_total", "fracGE290_of_total"]
    X = clr(df[cols].to_numpy())
    dist = squareform(pdist(X, metric="euclidean"))
    labels = df["soil"].to_numpy()
    omnibus = permanova(dist, labels, N_PERM, RNG)
    pairwise = permanova_pairwise(dist, labels, N_PERM, RNG)
    return {"omnibus": omnibus, "pairwise": pairwise, "cols": cols, "transform": "CLR + Euclidean (compositional)"}


def main() -> None:
    class_df = build_class_metrics()
    class_df.to_csv(OUT_ROOT / "class_metrics.csv", index=False)
    print(f"Wrote class_metrics.csv ({len(class_df)} rows)")

    metrics = [
        ("porosity", "Porosity"),
        ("frac31_150_of_total", "31-150um class porosity (microbially active)"),
        ("frac150_290_of_total", "150-290um class porosity (transmission)"),
        ("fracGE290_of_total", ">=290um class porosity (large macropores/biopores/cracks)"),
    ]
    part_a = {m: univariate_test(class_df, m, label) for m, label in metrics}

    # family-wise Holm correction across the 3 SIZE-CLASS omnibus tests
    # (porosity itself is not a size-class comparison, excluded from this family)
    class_metric_keys = ["frac31_150_of_total", "frac150_290_of_total", "fracGE290_of_total"]
    omni_p = [part_a[k]["p"] for k in class_metric_keys]
    omni_p_holm = holm_correct(omni_p)
    for k, p_holm in zip(class_metric_keys, omni_p_holm):
        part_a[k]["omnibus_p_holm_family"] = p_holm

    # sensitivity re-test: 60-150 vs 31-150
    sens = univariate_test(class_df, "frac60_150_of_total", "60-150um class porosity (sensitivity re-test, >=4 voxels @15um)")

    part_b = part_b_permanova_3class(class_df)

    results = {
        "note": "Cross-soil inference restricted to >=31um functional classes per psd_binning_recommendation.md. "
                "Whole-distribution median diameter is DROPPED from cross-soil claims (resolution-confounded). "
                ">=290um used as practical >300um boundary (nearest available log-bin edge, 288.54um).",
        "A_univariate": part_a,
        "A_sensitivity_60_150": sens,
        "B_permanova_3class": part_b,
    }
    with (OUT_ROOT / "class_stats_results.json").open("w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, default=lambda o: float(o) if isinstance(o, np.floating) else str(o))

    print(json.dumps({
        "A": {m: {"test": v["test"], "p": v["p"], "p_holm_family": v.get("omnibus_p_holm_family"),
                   "effect_size": v["effect_size"], "letters": v["letters"]} for m, v in part_a.items()},
        "sensitivity_60_150": {"test": sens["test"], "p": sens["p"], "letters": sens["letters"]},
        "B_omnibus": part_b["omnibus"],
    }, indent=2))
    print("\nWrote class_stats_results.json")


if __name__ == "__main__":
    main()
