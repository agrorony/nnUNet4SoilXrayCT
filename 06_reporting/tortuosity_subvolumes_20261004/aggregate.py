"""Aggregate raw per-size CSVs -> deliverable CSVs + figure + stats json."""
import json
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

H = Path(__file__).resolve().parent
ORDER = ["Vertisol", "Loess", "Sand"]
COL = {"Loess": "#C8A24B", "Vertisol": "#6B4F35", "Sand": "#D97B4F"}
LAB = {"Loess": "Loess\n(Mishmar HaNegev)", "Vertisol": "Vertisol\n(Bnei Re'em)", "Sand": "Sand\n(Rehovot)"}

df = pd.concat([pd.read_csv(f) for f in sorted((H / "work").glob("raw_full_s*.csv"))], ignore_index=True)
df["flow_mismatch"] = df.message.fillna("").str.contains("FLOW_MISMATCH")
df = df[["soil", "specimen", "cube_index", "origin_xyz", "cube_size", "axis", "porosity", "spanning", "phase",
         "status", "tortuosity", "runtime_s", "solver_settings", "flow_mismatch", "message", "input_path", "pore_label"]]
df.to_csv(H / "tortuosity_subvolumes.csv", index=False)
orig = df[df.phase == "original"]; retry = df[df.phase == "retry"]

# convergence summary (share of all cube x axis rows)
cats = ["ok", "no_spanning_path", "nonconvergence", "timeout", "error"]
def conv(d, label):
    out = []
    for (soil, size), g in d.groupby(["soil", "cube_size"]):
        r = dict(phase=label, soil=soil, cube_size=size, n_rows=len(g))
        for c in cats:
            r[f"n_{c}"] = int((g.status == c).sum()); r[f"share_{c}"] = round((g.status == c).mean(), 4)
        sp = g[g.spanning == "y"]
        r["n_ok_flow_mismatch"] = int(g[g.status == "ok"].flow_mismatch.sum()); r["n_spanning"] = len(sp); r["share_ok_of_spanning"] = round((sp.status == "ok").mean(), 4) if len(sp) else np.nan
        out.append(r)
    return out
cs = pd.DataFrame(conv(orig, "original") + (conv(retry, "retry_of_nonconvergence_only") if len(retry) else []))
cs["soil"] = pd.Categorical(cs.soil, ORDER); cs = cs.sort_values(["phase", "cube_size", "soil"], ascending=[False, False, True])
cs.to_csv(H / "convergence_summary.csv", index=False)

# sensitivity: timeouts re-solved at 900 s
tr = pd.read_csv(H / "work/timeout_rerun_900s.csv"); tr["cube_size"] = 200
tr = tr.merge(orig[["specimen", "cube_index", "axis", "soil", "porosity"]].drop_duplicates(), on=["specimen", "cube_index", "axis"])
# tortuosity summary (original-phase ok values; retry reported separately)
def summarize(d, tag):
    ok = d[d.status == "ok"]
    sp = ok.groupby(["soil", "specimen", "cube_size"]).tortuosity.agg(n_ok="count", median="median", mean="mean").reset_index()
    sp["level"] = "specimen"; sp["basis"] = tag
    so = []
    for (soil, size), g in sp.groupby(["soil", "cube_size"]):
        n = len(g); m = g["mean"].mean(); se = g["mean"].std(ddof=1) / np.sqrt(n) if n > 1 else np.nan
        so.append(dict(soil=soil, cube_size=size, specimen="(across specimens)", n_ok=int(g.n_ok.sum()), n_specimens=n,
                       mean=m, se=se, median=g["mean"].median(), level="soil", basis=tag))
    return pd.concat([sp, pd.DataFrame(so)], ignore_index=True)
ts = summarize(orig, "original")
if len(retry):
    ts = pd.concat([ts, summarize(pd.concat([orig[orig.status == "ok"], retry]), "original_ok_plus_retry_ok")], ignore_index=True)
orig_ok = orig[orig.status == "ok"]
ts = pd.concat([ts, summarize(orig_ok[~orig_ok.flow_mismatch], "original_ok_excluding_flow_mismatch"),
                summarize(pd.concat([orig_ok, tr[tr.status == "ok"]]), "original_ok_plus_900s_timeout_rerun")], ignore_index=True)
ts.to_csv(H / "tortuosity_summary.csv", index=False)

# stats
info = {}
for size in sorted(orig.cube_size.unique()):
    sp = ts[(ts.level == "specimen") & (ts.basis == "original") & (ts.cube_size == size)]
    groups = {s: sp[sp.soil == s]["mean"].values for s in ORDER}
    info[f"kw_{size}"] = None
    if all(len(v) >= 2 for v in groups.values()):
        h, p = stats.kruskal(*groups.values()); info[f"kw_{size}"] = dict(H=h, p=p, n={k: len(v) for k, v in groups.items()})
    ok = orig[(orig.cube_size == size) & (orig.status == "ok")]
    sp2 = ts[(ts.level == "specimen") & (ts.basis == "original_ok_excluding_flow_mismatch") & (ts.cube_size == size)]
    g2 = {s_: sp2[sp2.soil == s_]["mean"].values for s_ in ORDER}
    info[f"kw_{size}_excl_flow_mismatch"] = dict(zip(["H", "p"], stats.kruskal(*g2.values()))) if all(len(v) >= 2 for v in g2.values()) else None
    ok_nm = ok[~ok.flow_mismatch]; r_, p_ = stats.spearmanr(ok_nm.porosity, ok_nm.tortuosity)
    info[f"spearman_{size}_excl_flow_mismatch"] = dict(rho=r_, p=p_, n=len(ok_nm))
    rho, p = stats.spearmanr(ok.porosity, ok.tortuosity) if len(ok) > 3 else (np.nan, np.nan)
    info[f"spearman_{size}"] = dict(rho=rho, p=p, n=len(ok))
    for s in ORDER:
        o = ok[ok.soil == s]
        if len(o) > 3:
            r, pp = stats.spearmanr(o.porosity, o.tortuosity); info[f"spearman_{size}_{s}"] = dict(rho=r, p=pp, n=len(o))
json.dump(info, open(H / "stats.json", "w"), indent=1, default=float)

# figure (main size = 200)
size = 200
fig, ax = plt.subplots(figsize=(6.2, 4.6))
rng = np.random.default_rng(0)
o200 = orig[orig.cube_size == size]; ok200 = o200[o200.status == "ok"]
spm = ts[(ts.level == "specimen") & (ts.basis == "original") & (ts.cube_size == size)]
for i, s in enumerate(ORDER):
    c = ok200[ok200.soil == s]
    ax.scatter(i + rng.uniform(-.25, .25, len(c)), c.tortuosity, s=10, color="0.65", zorder=2)
    m = spm[spm.soil == s]
    ax.scatter(i + np.linspace(-.08, .08, len(m)) if len(m) > 1 else [i], m["mean"], s=70, color=COL[s], edgecolor="k", lw=.6, zorder=4)
    so = ts[(ts.level == "soil") & (ts.basis == "original") & (ts.cube_size == size) & (ts.soil == s)]
    if len(so):
        r = so.iloc[0]
        ax.errorbar(i + .32, r["mean"], yerr=0 if np.isnan(r.se) else r.se, fmt="_", color="k", capsize=5, ms=14, zorder=5)
    tot = o200[o200.soil == s]
    nsp = (tot.spanning == "y").sum()
    ax.text(i, -0.2, f"{len(c)}/{len(tot)} cube×axis ok", ha="center", va="top", fontsize=8, transform=ax.get_xaxis_transform())
ax.set_xticks(range(3)); ax.set_xticklabels([LAB[s] for s in ORDER]); ax.set_yscale("log"); ax.set_yticks([1,2,3,5,10,20,50,100]); ax.set_yticklabels(["1","2","3","5","10","20","50","100"])
ax.set_xlim(-.5, 2.6); ax.set_ylabel("Diffusive tortuosity τ (–)  [200³ voxel cubes, ~3 mm]")
ax.set_ylim(1,200); ax.spines[["top", "right"]].set_visible(False)
kw = info.get(f"kw_{size}")
t = f"Kruskal–Wallis on specimen means: H={kw['H']:.2f}, p={kw['p']:.2f}" if kw else "Kruskal–Wallis not run (a soil has <2 specimens with values)"
ax.set_title(t + "\ncoloured = specimen means; black = soil mean ± SE across specimens; grey = cubes×axes", fontsize=8.5)
ax.scatter([], [], s=70, color="w", edgecolor="k", label="specimen mean"); ax.scatter([], [], s=10, color="0.65", label="individual cube × axis")
ax.legend(frameon=False, fontsize=8, loc="upper right")
fig.tight_layout(); fig.savefig(H / "tortuosity_by_soil.png", dpi=200); fig.savefig(H / "tortuosity_by_soil.svg")
print(cs.to_string()); print(ts[ts.level=="soil"].to_string()); print(ts[(ts.level=="specimen")&(ts.basis=="original")].to_string()); print(json.dumps(info, indent=1, default=float))
