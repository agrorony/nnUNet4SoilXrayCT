"""Figures 4-6 (pore-size classes, distances and connectivity, POM), revised Nov 2026.

Fig 4 replaces draft graphs 8-9. Draft graph 8 (per-soil PSD histograms) came from the 2026-08-04
150-slice slab runs (Topology_Metrics_Aug2026V2/raw/*_150z), which disagree with the subvolume data
behind graph 9 and the text (e.g. Loess 30-150 um share of pore volume: 0.31 in the slab vs 0.73 in the
subvolumes). Both panels here therefore use only the subvolume data (psd_A2_reanalysis_20260822,
class_metrics.csv / class_stats_results.json; 8 non-overlapping subvolumes from one scan per soil).
Fig 5 replaces draft graphs 10-12: distances (graph 10), Gamma against visible porosity (the R2 = 0.91
relation stated in the text but not shown in the draft), crossover radius r* (graph 12b).
Draft graph 11 (chi(r) curves) is not redrawn: its curves for Vertisol and Loess are only on the share.
Fig 6 replaces draft graphs 13-14 with the four metrics the text uses.
"""
import json
import numpy as np
import pandas as pd
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
from common import *

D = None  # inputs are read from the repo below
KEY = {'L': 'mishmar', 'V': 'bnei_reem', 'S': 'rehovot'}
MARK = {'L': 'o', 'V': 's', 'S': '^'}

# ============================== Figure 4 ==============================
cm = pd.read_csv(os.path.join(REPO, '5_analysis', 'pore_size_distribution', 'class_metrics.csv'))
st = json.load(open(os.path.join(REPO, '5_analysis', 'pore_size_distribution', 'class_stats_results.json')))['A_univariate']
classes = [('frac31_150_of_total', '30–150'), ('frac150_290_of_total', '150–300'), ('fracGE290_of_total', '> 300')]

fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.27, 3.15), gridspec_kw=dict(width_ratios=[2.0, 1]))
w = 0.26
for k, (col, lab) in enumerate(classes):
    groups = [cm[cm.soil == KEY[s]][col].values for s in ORDER]
    # compact letters from the stored (Holm-adjusted) pairwise p-values, lowest mean = 'a'
    idx = {KEY[s]: i for i, s in enumerate(ORDER)}
    P = np.ones((3, 3))
    for pr in st[col]['pairwise']:
        i, j = idx[pr['group1']], idx[pr['group2']]
        P[i, j] = P[j, i] = pr['p_adj']
    lets = cld(groups, P)
    for i, s in enumerate(ORDER):
        x = k + (i - 1) * w
        m, se = groups[i].mean(), stats.sem(groups[i])
        a1.bar(x, m, width=w * 0.92, color=COLORS[s], edgecolor='k', lw=0.5)
        a1.errorbar(x, m, yerr=se, fmt='none', ecolor='k', capsize=2.5, lw=0.9)
        a1.text(x, m + se + 0.006, lets[i], ha='center', va='bottom', fontsize=9.5, fontweight='bold')
    t = st[col]
    eff = 'ε²' if 'epsilon' in t['effect_size_name'] else 'η²'
    name = 'KW H' if t['test'].startswith('Kruskal') else 'F'
    name = 'H' if t['test'].startswith('Kruskal') else 'F'
    a1.text(k, -0.15, f"{name} = {t['statistic']:.1f}\n{ptxt(t['p'])}\n{eff} = {t['effect_size']:.2f}",
            transform=a1.get_xaxis_transform(), ha='center', va='top', fontsize=6.6, color='0.25')
a1.set_xticks(range(3))
a1.set_xticklabels([f'{lab} µm' for _, lab in classes], fontsize=8.5)
a1.set_xlabel('Pore diameter class', labelpad=30)
a1.set_ylabel('Fraction of total volume')
a1.set_ylim(0, 0.27)
a1.legend(handles=[Patch(facecolor=COLORS[s], edgecolor='k', lw=0.5, label=SHORT[s]) for s in ORDER],
          frameon=False, fontsize=8, loc='upper right')
despine(a1)
panel_label(a1, 0, x=-0.15, y=1.02)

# (b) composition of the visible pore volume
comp_cols = [('frac31_150_of_pore', '30–150 µm'), ('frac150_290_of_pore', '150–300 µm'), ('fracGE290_of_pore', '> 300 µm')]
shades = ['#c9d9e6', '#7fa3c0', '#2f5d82']
xs = np.arange(3)
bottom = np.zeros(3)
small = np.array([1 - sum(cm[cm.soil == KEY[s]][c].mean() for c, _ in comp_cols) for s in ORDER])
small[small < 1e-6] = 0
a2.bar(xs, small, width=0.6, bottom=bottom, color='white', edgecolor='0.4', hatch='////', lw=0.5,
       label='< 30 µm (seen only\nin the 5.85 µm scan)')
bottom += small
for (c, lab), shade in zip(comp_cols, shades):
    v = np.array([cm[cm.soil == KEY[s]][c].mean() for s in ORDER])
    a2.bar(xs, v, width=0.6, bottom=bottom, color=shade, edgecolor='white', lw=1.0, label=lab)
    for x, b, h in zip(xs, bottom, v):
        if h > 0.08:
            a2.text(x, b + h / 2, f'{h:.2f}', ha='center', va='center', fontsize=7.5,
                    color='k' if shade != shades[-1] else 'white')
    bottom += v
a2.set_xticks(xs)
a2.set_xticklabels([SHORT[s] for s in ORDER], fontsize=8.5)
a2.set_ylim(0, 1)
a2.set_ylabel('Share of visible pore volume')
h, l = a2.get_legend_handles_labels()
a2.legend(h[::-1], l[::-1], frameon=False, fontsize=7, loc='upper left', bbox_to_anchor=(1.0, 1.0), handlelength=1.2)
despine(a2)
panel_label(a2, 1, x=-0.45, y=1.02)
fig.subplots_adjust(left=0.1, right=0.785, top=0.92, bottom=0.27, wspace=0.5)
save(fig, 'fig4_pore_classes')

# ============================== Figure 5 ==============================
dist = {  # mean (median), um; voxel-wise over the whole volume (summary_distance_metrics.json)
    'V': dict(pore=(64.5, 54.1), conn=(134.6, 82.2), pom=(543.4, 503.3)),   # canonical Vertisol, 15 um
    'L': dict(pore=(21.1, 14.3), conn=(36.8, 17.5), pom=(214.0, 207.2)),    # Loess 5.85 um native
    'S': dict(pore=(34.8, 26.0), conn=(37.6, 30.0), pom=None),               # Sand samp2, Otsu binary
}
spec = [  # soil, specimen, visible porosity (%), Gamma, r* (um) at ~15 um (merged_specimen_level_ct_only.csv + samp3)
    ('V', 'specA', 15.17, 0.7549, None), ('V', 'specB', 21.64, 0.8593, None),
    ('L', '5.85->15', 26.57, 0.9361, 67.66), ('L', '8.8->15', 20.34, 0.9313, 119.51), ('L', 'Cu011_samp_2', 26.18, 0.9300, 212.6),
    ('S', 'samp2', 30.50, 0.9889, 100.8), ('S', 'samp3', 40.85, 0.9974, 147.0)]

fig = plt.figure(figsize=(6.27, 4.9))
gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.05], width_ratios=[1.35, 1], hspace=0.55, wspace=0.38)
a1 = fig.add_subplot(gs[0, :])
a2 = fig.add_subplot(gs[1, 0])
a3 = fig.add_subplot(gs[1, 1])

# (a) distances
targets = [('pore', 'Nearest pore'), ('conn', 'Nearest connected pore'), ('pom', 'Nearest POM')]
w = 0.26
for k, (key, lab) in enumerate(targets):
    for i, s in enumerate(ORDER):
        x = k + (i - 1) * w
        v = dist[s][key]
        if v is None:
            a1.text(x, 6, 'no POM\nclass', ha='center', va='bottom', fontsize=6.5, color='0.35')
            continue
        a1.bar(x, v[0], width=w * 0.92, color=COLORS[s], edgecolor='k', lw=0.5)
        a1.text(x, v[0] * 1.08, f'{v[0]:.0f}\n({v[1]:.0f})', ha='center', va='bottom', fontsize=7)
a1.set_yscale('log')
a1.set_ylim(5, 3000)
a1.set_xlim(-0.55, 2.55)
a1.set_xticks(range(3))
a1.set_xticklabels([lab for _, lab in targets], fontsize=8.5)
a1.set_ylabel('Distance from matrix (µm)\nmean (median)')
a1.legend(handles=[Patch(facecolor=COLORS[s], edgecolor='k', lw=0.5, label=LABELS[s]) for s in ORDER],
          frameon=False, fontsize=7.5, loc='upper left', ncol=3, bbox_to_anchor=(0.0, 1.17))
despine(a1)
panel_label(a1, 0, x=-0.09, y=1.04)

# (b) Gamma vs visible porosity, logistic fit on all 7 scans
phi = np.array([p for _, _, p, _, _ in spec]) / 100
gam = np.array([g for _, _, _, g, _ in spec])
yl = np.log(gam / (1 - gam))
b, a0 = np.polyfit(phi, yl, 1)
r2 = 1 - ((yl - (a0 + b * phi)) ** 2).sum() / ((yl - yl.mean()) ** 2).sum()
xx = np.linspace(0.12, 0.44, 100)
a2.plot(xx * 100, 1 / (1 + np.exp(-(a0 + b * xx))), color='0.45', lw=1.2, ls='--', zorder=1)
for s in ORDER:
    pts = [(p, g) for ss, _, p, g, _ in spec if ss == s]
    a2.scatter([p for p, _ in pts], [g for _, g in pts], s=34, color=COLORS[s], marker=MARK[s], edgecolor='k',
               lw=0.6, zorder=3, label=SHORT[s])
a2.set_xlabel('Visible porosity (%)')
a2.set_ylabel('Connectivity probability Γ')
a2.set_xlim(12, 44)
a2.set_ylim(0.7, 1.01)
a2.text(0.97, 0.05, f'logit(Γ) ~ porosity\nR² = {r2:.2f}, n = 7 scans', transform=a2.transAxes, ha='right',
        va='bottom', fontsize=7.5, bbox=BOX)
a2.legend(frameon=False, fontsize=7.5, loc='upper left', handletextpad=0.3)
despine(a2)
panel_label(a2, 1, x=-0.25, y=1.1)

# (c) crossover radius
RST = {s: [r for ss, _, _, _, r in spec if ss == s and r is not None] for s in ORDER}
xs = np.arange(3)
for x, s in zip(xs, ORDER):
    if not RST[s]:
        a3.text(x, 30, 'no crossover\nin measured\nrange', ha='center', va='bottom', fontsize=6.8, style='italic', color='0.3')
        continue
    m, se = np.mean(RST[s]), stats.sem(RST[s])
    a3.bar(x, m, width=0.6, color=COLORS[s], edgecolor='k', lw=0.5)
    a3.errorbar(x, m, yerr=se, fmt='none', ecolor='k', capsize=4, lw=1)
    a3.scatter(x + np.linspace(-0.1, 0.1, len(RST[s])), RST[s], s=12, facecolor='white', edgecolor='k', lw=0.6, zorder=3)
fr = anova([RST['L'], RST['S']])
a3.set_xticks(xs)
a3.set_xticklabels([SHORT[s] for s in ORDER], fontsize=8.5)
a3.set_ylabel('Crossover radius r* (µm)')
a3.set_ylim(0, 260)
a3.set_title(f"Loess vs Sand: F({fr['df1']},{fr['df2']}) = {fr['F']:.2f}, p = {fr['p']:.2f}", fontsize=7.5, color='0.25', pad=3)
despine(a3)
panel_label(a3, 2, x=-0.3, y=1.1)
fig.subplots_adjust(left=0.12, right=0.98, top=0.9, bottom=0.1)
save(fig, 'fig5_distance_connectivity')
print(f'Gamma fit: logit(G) = {a0:.2f} + {b:.2f} * porosity, R2 = {r2:.2f}; r* Loess {np.mean(RST["L"]):.1f}+-{stats.sem(RST["L"]):.1f}, Sand {np.mean(RST["S"]):.1f}+-{stats.sem(RST["S"]):.1f}; F={fr["F"]:.3f} p={fr["p"]:.3f}')

# ============================== Figure 6 ==============================
pom = json.load(open(os.path.join(REPO, '5_analysis', 'pom', 'interface_metrics', 'all_soils_interface_summary.json')))
vols = {'L': ['mishmar_native', 'mishmar_sample2'], 'V': ['bnei_reem']}
def metric(s, f):
    return [f(pom[v]) for v in vols[s]]
frac = lambda v: 100 * v['n_denoised_pom_voxels'] / v['n_total_voxels']
iadp = lambda v: v['part3_ssa_iad']['iad_pore_mm2_per_mm3']
iadm = lambda v: v['part3_ssa_iad']['iad_matrix_mm2_per_mm3']
lrg = lambda v: 100 * v['part4_object_level']['largest_object_interface_area_share']
clark = {'L': [0.818], 'V': [0.640]}   # one scan per soil (merged_soiltype_level.csv, ct_pom_clark_evans)
S2 = ['L', 'V']

fig, axes2 = plt.subplots(2, 2, figsize=(6.27, 4.3))
axes = axes2.ravel()
def bars(ax, vals, ylab, ymax):
    for x, s in enumerate(S2):
        v = vals[s]
        ax.bar(x, np.mean(v), width=0.6, color=COLORS[s], edgecolor='k', lw=0.5)
        if len(v) > 1:
            ax.errorbar(x, np.mean(v), yerr=stats.sem(v), fmt='none', ecolor='k', capsize=4, lw=1)
        ax.scatter(x + np.linspace(-0.08, 0.08, len(v)), v, s=12, facecolor='white', edgecolor='k', lw=0.6, zorder=3)
    ax.set_xticks(range(2)); ax.set_xticklabels([SHORT[s] for s in S2], fontsize=8.5)
    ax.set_xlim(-0.7, 1.7); ax.set_ylim(0, ymax); ax.set_ylabel(ylab, fontsize=8.5)
    despine(ax)
bars(axes[0], {s: metric(s, frac) for s in S2}, 'POM volume fraction (%)', 2.0)
# (b) interface area density, grouped
ax = axes[1]
for gi, (f, lab) in enumerate([(iadp, 'POM–pore'), (iadm, 'POM–matrix')]):
    for i, s in enumerate(S2):
        x = gi + (i - 0.5) * 0.36
        v = metric(s, f)
        ax.bar(x, np.mean(v), width=0.33, color=COLORS[s], edgecolor='k', lw=0.5)
        if len(v) > 1:
            ax.errorbar(x, np.mean(v), yerr=stats.sem(v), fmt='none', ecolor='k', capsize=3, lw=1)
        ax.scatter(x + np.linspace(-0.05, 0.05, len(v)), v, s=12, facecolor='white', edgecolor='k', lw=0.6, zorder=3)
ax.set_xticks([0, 1]); ax.set_xticklabels(['POM–pore', 'POM–matrix'], fontsize=8.5)
ax.set_ylim(0, 0.34); ax.set_ylabel('Interface area per soil volume\n(mm² mm⁻³)', fontsize=8.5)
despine(ax)
bars(axes[2], {s: metric(s, lrg) for s in S2}, 'Largest POM object, share\nof POM–pore interface (%)', 50)
bars(axes[3], clark, 'Clark–Evans R', 1.15)
axes[3].axhline(1, color='0.4', ls='--', lw=0.8)
axes[3].text(1.65, 1.01, 'random (R = 1)', ha='right', va='bottom', fontsize=6.8, color='0.35')
for i, ax in enumerate(axes):
    panel_label(ax, i, x=-0.22, y=1.03)
fig.text(0.5, 0.005, 'Descriptive only: Loess n = 2 scans (mean ± SE, points), Vertisol n = 1; Sand had no detectable POM. '
         '(d) one scan per soil.', ha='center', va='bottom', fontsize=7, color='0.3')
fig.subplots_adjust(left=0.11, right=0.98, top=0.94, bottom=0.1, wspace=0.42, hspace=0.42)
save(fig, 'fig6_pom')
for s in S2:
    print(s, 'POM%', np.round(metric(s, frac), 2), 'IADpore', np.round(metric(s, iadp), 3), 'IADmat', np.round(metric(s, iadm), 3), 'largest%', np.round(metric(s, lrg), 1))
