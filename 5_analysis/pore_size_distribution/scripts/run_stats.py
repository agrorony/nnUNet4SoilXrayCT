"""Step 3: inference on subvolume_metrics.csv.

A. Univariate (porosity, median diameter, 30-150um fraction of pore volume):
   Shapiro (residuals) + Levene -> ANOVA+Tukey HSD (eta^2) or Kruskal-Wallis+Dunn
   Holm (epsilon^2), with compact letter display.
B. PERMANOVA (Bray-Curtis, 9999 perms) on binned PSD vectors: omnibus + pairwise
   (Holm-corrected). Implemented manually (McArdle & Anderson 2001 formulation)
   to avoid the scikit-bio dependency.
C. Pairwise KS tests on pore-object equivalent-spherical-diameters (from
   step3c_pore_objects.py output).

Writes stats_summary.md and prints the final soil x metric table.
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from scipy.spatial.distance import pdist, squareform
from statsmodels.stats.multicomp import pairwise_tukeyhsd
import scikit_posthocs as sp

OUT_ROOT = Path(__file__).resolve().parents[1]
RNG = np.random.default_rng(12345)
N_PERM = 9999

SOIL_LABELS = {
    "bnei_reem": "Bnei Re'em (Vertisol)",
    "mishmar": "Mishmar HaNegev (Loess)",
    "rehovot": "Rehovot (Sand)",
}
SOIL_ORDER = ["bnei_reem", "mishmar", "rehovot"]


# ---------------------------------------------------------------------------
# Compact letter display (maximal-clique cover of the "not significantly
# different" graph) -- exact for small group counts (here: 3 soils).
# ---------------------------------------------------------------------------
def compact_letters(groups: list[str], sig_pairs: set[frozenset]) -> dict[str, str]:
    ns_edges = {frozenset(p) for p in itertools.combinations(groups, 2)} - sig_pairs
    import networkx as nx  # small, commonly available; fallback below if missing
    G = nx.Graph()
    G.add_nodes_from(groups)
    G.add_edges_from([tuple(e) for e in ns_edges])
    cliques = list(nx.find_cliques(G))
    # greedy cover: pick cliques (largest first) until every node and every
    # ns-edge is covered
    cliques = sorted(cliques, key=len, reverse=True)
    covered_edges = set()
    covered_nodes = set()
    selected = []
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


# ---------------------------------------------------------------------------
# Part A: univariate tests
# ---------------------------------------------------------------------------
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
    ss_between = float(sum(len(v) * (m - grand_mean) ** 2 for s, v, m in
                            [(s, v, group_means[s]) for s, v in groups.items()]))

    if assumptions_ok:
        f_stat, p_val = stats.f_oneway(*groups.values())
        eta2 = ss_between / ss_total
        result.update({
            "test": "one-way ANOVA", "statistic": float(f_stat),
            "df_between": k - 1, "df_within": n - k, "p": float(p_val),
            "effect_size_name": "eta^2", "effect_size": eta2,
        })
        tukey_df_long = pd.DataFrame({"value": all_vals,
                                       "group": df["soil"].to_numpy()})
        tukey = pairwise_tukeyhsd(tukey_df_long["value"], tukey_df_long["group"])
        sig_pairs = set()
        pairwise_rows = []
        for row in tukey.summary().data[1:]:
            g1, g2, meandiff, p_adj, lo, hi, reject = row
            pairwise_rows.append({"group1": g1, "group2": g2, "p_adj": float(p_adj),
                                   "reject": bool(reject)})
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
        s: {"mean": float(np.mean(v)), "se": float(np.std(v, ddof=1) / np.sqrt(len(v))),
            "n": len(v)}
        for s, v in groups.items()
    }
    return result


# ---------------------------------------------------------------------------
# Part B: PERMANOVA (McArdle & Anderson 2001), manual implementation
# ---------------------------------------------------------------------------
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
    return {"pseudo_F": float(f_obs), "R2": float(r2_obs), "p": float(p),
            "df_among": a - 1, "df_within": N - a, "n_perm": n_perm}


def permanova_pairwise(dist_full: np.ndarray, labels_full: np.ndarray, subvol_ids,
                        n_perm: int, rng) -> list[dict]:
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


def part_b_permanova(df: pd.DataFrame) -> dict:
    psd_cols = [c for c in df.columns if c.startswith("PSD_bin_")]
    X = df[psd_cols].to_numpy()
    dist = squareform(pdist(X, metric="braycurtis"))
    labels = df["soil"].to_numpy()

    omnibus = permanova(dist, labels, N_PERM, RNG)
    pairwise = permanova_pairwise(dist, labels, df["subvolume_id"].to_numpy(), N_PERM, RNG)
    return {"omnibus": omnibus, "pairwise": pairwise, "n_bins": len(psd_cols)}


# ---------------------------------------------------------------------------
# Part C: pairwise KS tests on pore-object diameters
# ---------------------------------------------------------------------------
def part_c_ks() -> dict:
    obj_dir = OUT_ROOT / "pore_objects"
    diam = {s: np.load(obj_dir / f"{s}_object_diameters_um.npy") for s in SOIL_ORDER}
    summary = json.loads((OUT_ROOT / "pore_objects_summary.json").read_text())

    rows = []
    for g1, g2 in itertools.combinations(SOIL_ORDER, 2):
        d_stat, p_val = stats.ks_2samp(diam[g1], diam[g2])
        rows.append({
            "group1": g1, "group2": g2,
            "n1": len(diam[g1]), "n2": len(diam[g2]),
            "D": float(d_stat), "p": float(p_val),
        })
    return {"pairwise": rows, "object_summary": summary}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    df = pd.read_csv(OUT_ROOT / "subvolume_metrics.csv")

    metrics = [
        ("porosity", "Porosity"),
        ("median_diameter_um", "Median pore diameter (um)"),
        ("frac_30_150um_of_pore_volume", "30-150um fraction of pore volume"),
    ]
    part_a = {m: univariate_test(df, m, label) for m, label in metrics}
    part_b = part_b_permanova(df)
    part_c = part_c_ks()

    results = {"A_univariate": part_a, "B_permanova": part_b, "C_ks": part_c}
    with (OUT_ROOT / "stats_results.json").open("w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, default=lambda o: float(o) if isinstance(o, np.floating) else str(o))

    print(json.dumps({
        "A": {m: {"test": v["test"], "p": v["p"], "effect_size": v["effect_size"],
                   "letters": v["letters"]} for m, v in part_a.items()},
        "B_omnibus": part_b["omnibus"],
        "C": part_c["pairwise"],
    }, indent=2))
    print("\nWrote stats_results.json")


if __name__ == "__main__":
    main()
