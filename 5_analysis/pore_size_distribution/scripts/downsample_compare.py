"""A2 Step 5c: aggregate the downsampled-Mishmar PSD runs into the same
size classes as reaggregate_classes.py, then:
  (i) paired before/after comparison (5.85um subvolume vs its own downsampled
      ~15um twin) for the >=31um classes,
  (ii) re-run the 3-soil Kruskal-Wallis/ANOVA + Dunn/Tukey with the
      downsampled-Mishmar rows substituted for the original Mishmar rows,
      to check whether the soil ranking/compact letters for each >=31um class
      survive the resolution robustness check.
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

A2_ROOT = Path(__file__).resolve().parents[1]
DOWN_ROOT = A2_ROOT / "mishmar_downsample"
MANIFEST = json.loads((DOWN_ROOT / "downsample_manifest.json").read_text())
EDGE_300_APPROX = 288.53997802734375

SOIL_ORDER = ["bnei_reem", "mishmar", "rehovot"]


def find_run_dir(name: str) -> Path:
    matches = sorted((DOWN_ROOT / "psd_runs").glob(f"psd_diag_*_{name}"))
    if not matches:
        raise FileNotFoundError(f"No run dir for {name}")
    return matches[-1]


def class_fraction(df: pd.DataFrame, lo: float, hi: float, total: int) -> float:
    mask = (df["Diameter_um"] >= lo) & (df["Diameter_um"] < hi)
    return float(df.loc[mask, "Volume_Count"].sum() / total)


def build_downsampled_metrics() -> pd.DataFrame:
    rows = []
    for entry in MANIFEST:
        name = f"mishmar_downsampled_{entry['subvolume_id']}"
        run_dir = find_run_dir(name)
        df = pd.read_csv(run_dir / "psd_table.csv")
        total = int(df["Volume_Count"].sum())
        porosity = entry["porosity_after_15um"]

        f31_150 = class_fraction(df, 30.0, 150.0, total)
        f150_290 = class_fraction(df, 150.0, EDGE_300_APPROX, total)
        fge290 = class_fraction(df, EDGE_300_APPROX, 1e9, total)

        rows.append({
            "soil": "mishmar",
            "subvolume_id": entry["subvolume_id"],
            "porosity": porosity,
            "frac31_150_of_total": f31_150 * porosity,
            "frac150_290_of_total": f150_290 * porosity,
            "fracGE290_of_total": fge290 * porosity,
        })
    return pd.DataFrame(rows)


def paired_compare(orig: pd.DataFrame, down: pd.DataFrame) -> dict:
    orig_m = orig[orig.soil == "mishmar"].set_index("subvolume_id")
    down_m = down.set_index("subvolume_id")
    common = sorted(set(orig_m.index) & set(down_m.index))
    out = {}
    for col in ["porosity", "frac31_150_of_total", "frac150_290_of_total", "fracGE290_of_total"]:
        before = orig_m.loc[common, col].to_numpy()
        after = down_m.loc[common, col].to_numpy()
        diff = after - before
        w_stat, w_p = stats.wilcoxon(before, after)
        out[col] = {
            "n": len(common),
            "mean_before_5p85um": float(before.mean()),
            "mean_after_15um": float(after.mean()),
            "mean_diff": float(diff.mean()),
            "se_diff": float(diff.std(ddof=1) / np.sqrt(len(diff))),
            "pct_change": float(diff.mean() / before.mean() * 100),
            "wilcoxon_stat": float(w_stat),
            "wilcoxon_p": float(w_p),
        }
    return out


def compact_letters(groups, sig_pairs):
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


def univariate_3soil(df: pd.DataFrame, metric: str) -> dict:
    groups = {s: df.loc[df.soil == s, metric].to_numpy() for s in SOIL_ORDER}
    all_vals = df[metric].to_numpy()
    group_means = {s: v.mean() for s, v in groups.items()}
    residuals = np.concatenate([v - group_means[s] for s, v in groups.items()])
    shapiro_p = stats.shapiro(residuals).pvalue
    levene_p = stats.levene(*groups.values()).pvalue
    assumptions_ok = shapiro_p > 0.05 and levene_p > 0.05

    if assumptions_ok:
        f_stat, p_val = stats.f_oneway(*groups.values())
        tukey_df_long = pd.DataFrame({"value": all_vals, "group": df["soil"].to_numpy()})
        tukey = pairwise_tukeyhsd(tukey_df_long["value"], tukey_df_long["group"])
        sig_pairs = set()
        for row in tukey.summary().data[1:]:
            g1, g2, meandiff, p_adj, lo, hi, reject = row
            if reject:
                sig_pairs.add(frozenset((g1, g2)))
        test_name = "one-way ANOVA"
    else:
        h_stat, p_val = stats.kruskal(*groups.values())
        dunn = sp.posthoc_dunn(df, val_col=metric, group_col="soil", p_adjust="holm")
        sig_pairs = set()
        for g1, g2 in itertools.combinations(SOIL_ORDER, 2):
            if dunn.loc[g1, g2] < 0.05:
                sig_pairs.add(frozenset((g1, g2)))
        test_name = "Kruskal-Wallis"

    letters = compact_letters(SOIL_ORDER, sig_pairs)
    return {"test": test_name, "p": float(p_val), "letters": letters,
            "group_means": {s: float(np.mean(v)) for s, v in groups.items()}}


def main() -> None:
    orig_class = pd.read_csv(A2_ROOT / "class_metrics.csv")
    down_class = build_downsampled_metrics()
    down_class.to_csv(DOWN_ROOT / "mishmar_downsampled_class_metrics.csv", index=False)

    paired = paired_compare(orig_class, down_class)

    # Substitute downsampled Mishmar for original Mishmar in the 3-soil frame
    non_mishmar = orig_class[orig_class.soil != "mishmar"]
    swapped = pd.concat([non_mishmar, down_class], ignore_index=True)

    class_cols = ["porosity", "frac31_150_of_total", "frac150_290_of_total", "fracGE290_of_total"]
    swapped_results = {c: univariate_3soil(swapped, c) for c in class_cols}
    orig_class_stats = json.loads((A2_ROOT / "class_stats_results.json").read_text())

    comparison = {}
    for c in class_cols:
        key = c if c != "porosity" else "porosity"
        orig_letters = orig_class_stats["A_univariate"][key]["letters"]
        new_letters = swapped_results[c]["letters"]
        comparison[c] = {
            "original_mishmar_letters": orig_letters,
            "downsampled_mishmar_letters": new_letters,
            "letters_match": orig_letters == new_letters,
            "original_p": orig_class_stats["A_univariate"][key]["p"],
            "downsampled_p": swapped_results[c]["p"],
        }

    out = {
        "paired_before_after_mishmar_subvolumes": paired,
        "three_soil_with_downsampled_mishmar": swapped_results,
        "robustness_comparison": comparison,
    }
    (DOWN_ROOT / "downsample_comparison.json").write_text(
        json.dumps(out, indent=2, default=lambda o: float(o) if isinstance(o, np.floating) else str(o)))

    print(json.dumps(comparison, indent=2))
    print("\nWrote downsample_comparison.json")


if __name__ == "__main__":
    main()
