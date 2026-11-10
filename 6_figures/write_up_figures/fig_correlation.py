"""Figure 7: lab vs CT metrics at the soil level (n = 3), the correlation matrix Maoz asked to see.

Replaces the 26 x 26 heatmap of correlation_matrix_20260921 with the metrics the text discusses,
recomputed from the same sources as Figs 1-6 (respiration in CO2-C; qCO2 per QCO2_WINDOW;
CT metrics at ~15 um where resolution-matched values exist; Sand Rehovot n = 2 incl. samp3).
With three soils Spearman rho can only be +-1 or +-0.5, so panel (a) shows the soil means themselves.
"""
import sys
import numpy as np
from matplotlib.colors import TwoSlopeNorm
from common import *

QCO2_WINDOW = 'd11-15'
for a in sys.argv[1:]:
    k, v = a.split('=')
    globals()[k] = v

jars = respiration()
cm = cmic()
corg = corg_percent()
bio = {
    'Respiration, 15 d': {s: np.mean([jars[j]['cum'] for j in soil_jars(jars, s)]) for s in ORDER},
    'C$_{mic}$': {s: np.mean(list(cm[s].values())) for s in ORDER},
    'qCO$_2$': {s: np.mean([(jars[j]['rate'][3] if QCO2_WINDOW == 'd11-15' else jars[j]['avg']) / cm[s][int(j[1])] * 1000 / 24
                             for j in soil_jars(jars, s)]) for s in ORDER},
    'C$_{mic}$/C$_{org}$': {s: np.mean([cm[s][r] / (corg[s] * 1e4) * 100 for r in cm[s]]) for s in ORDER},
    'Organic matter': {'L': 2.72, 'V': 4.86, 'S': 1.67},
}
ct = {
    'Visible porosity': {'L': np.mean([26.57, 20.34, 26.18]), 'V': np.mean([15.17, 21.64]), 'S': np.mean([30.50, 40.85])},
    '30–150 µm share': {'L': 0.729, 'V': 0.475, 'S': 0.703},
    'Connectivity Γ': {'L': np.mean([0.9361, 0.9313, 0.9300]), 'V': np.mean([0.7549, 0.8593]), 'S': np.mean([0.9889, 0.9974])},
    'Distance to pore': {'L': 21.1, 'V': 64.5, 'S': 34.8},
    'POM fraction': {'L': 1.62, 'V': 0.82, 'S': np.nan},
    'Crossover r*': {'L': 133.3, 'V': np.nan, 'S': 123.9},
}
rows = list(bio) + list(ct)
vals = {**bio, **ct}

fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.27, 3.6), gridspec_kw=dict(width_ratios=[0.75, 1]))
CT2 = [c for c in ct if all(not np.isnan(ct[c][s]) for s in ORDER)]
# (a) soil means, coloured by within-row z-score
Z = np.full((len(rows), 3), np.nan)
for i, r in enumerate(rows):
    v = np.array([vals[r][s] for s in ORDER], float)
    ok = ~np.isnan(v)
    if ok.sum() > 1:
        Z[i, ok] = (v[ok] - v[ok].mean()) / v[ok].std()
a1.imshow(Z, cmap='PuOr_r', norm=TwoSlopeNorm(0, -1.5, 1.5), aspect='auto')
for i, r in enumerate(rows):
    for j, s in enumerate(ORDER):
        v = vals[r][s]
        txt = '–' if np.isnan(v) else (f'{v:.0f}' if abs(v) >= 100 else f'{v:.2f}' if abs(v) < 10 else f'{v:.1f}')
        a1.text(j, i, txt, ha='center', va='center', fontsize=6.8,
                color='white' if (not np.isnan(Z[i, j]) and abs(Z[i, j]) > 1.1) else 'k')
a1.set_xticks(range(3)); a1.set_xticklabels([SHORT[s] for s in ORDER], fontsize=8)
a1.set_yticks(range(len(rows))); a1.set_yticklabels(rows, fontsize=7.5)
a1.axhline(len(bio) - 0.5, color='k', lw=1)
a1.tick_params(length=0)
a1.xaxis.tick_top()
for sp in a1.spines.values():
    sp.set_visible(False)
a1.text(2.72, (len(bio) - 1) / 2, 'lab', rotation=270, ha='center', va='center', fontsize=7.5, color='0.35')
a1.text(2.72, len(bio) + (len(ct) - 1) / 2, 'CT', rotation=270, ha='center', va='center', fontsize=7.5, color='0.35')
panel_label(a1, 0, x=-0.78, y=1.07)

# (b) Spearman rho, lab (rows) x CT (columns)
R = np.full((len(bio), len(CT2)), np.nan)
for i, b in enumerate(bio):
    for j, c in enumerate(CT2):
        x = np.array([vals[b][s] for s in ORDER]); y = np.array([vals[c][s] for s in ORDER])
        ok = ~np.isnan(x) & ~np.isnan(y)
        if ok.sum() == 3:
            R[i, j] = stats.spearmanr(x, y).statistic
a2.imshow(R, cmap='RdBu_r', vmin=-1, vmax=1, aspect='auto')
for i in range(R.shape[0]):
    for j in range(R.shape[1]):
        a2.text(j, i, '×' if np.isnan(R[i, j]) else f'{R[i, j]:+.1f}', ha='center', va='center', fontsize=7.5,
                color='0.4' if np.isnan(R[i, j]) else ('white' if abs(R[i, j]) > 0.75 else 'k'))
a2.set_xticks(range(len(CT2))); a2.set_xticklabels(CT2, fontsize=7.5, rotation=30, ha='right')
a2.set_yticks(range(len(bio))); a2.set_yticklabels(list(bio), fontsize=7.5)
a2.yaxis.tick_right()
a2.tick_params(length=0)
for sp in a2.spines.values():
    sp.set_visible(False)
a2.set_title('Spearman ρ, n = 3 soils (only ±1 or ±0.5)', fontsize=7.5, color='0.3', pad=6, loc='right')
panel_label(a2, 1, x=-0.1, y=1.07)
fig.subplots_adjust(left=0.2, right=0.82, top=0.84, bottom=0.17, wspace=0.42)
save(fig, 'fig7_correlation')
