"""Figure 1 (respiration) and Figure 2 (biomass and quotients), revised Nov 2026.

Fig 1 merges draft graphs 1-4: graph 1 (mean rate) is dropped because it carries the same
statistics as the day-15 cumulative endpoint (rate = cumulative / 15); graph 3 (jar-level points)
is overlaid on graph 2 as Maoz suggested.
Fig 2 merges draft graphs 5-6.

Post-hoc: Fisher's protected LSD (only after a significant omnibus F). With three groups the
protected LSD keeps the family-wise error rate at alpha. POSTHOC = 'tukey' restores the draft letters.
QCO2_WINDOW: 'd11-15' follows Methods 2.2.7 (last period, after the wetting flush);
'mean15' reproduces the draft figure (15-day mean rate).
"""
import sys
import numpy as np
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
from common import *

POSTHOC = 'lsd'
QCO2_WINDOW = 'd11-15'
for a in sys.argv[1:]:
    k, v = a.split('=')
    globals()[k] = v
TEST_NAME = {'lsd': "Fisher's LSD", 'tukey': 'Tukey HSD'}[POSTHOC]
SUFFIX = '' if (POSTHOC == 'lsd' and QCO2_WINDOW == 'd11-15') else f'_{POSTHOC}_{QCO2_WINDOW}'

jars = respiration()
cm = cmic()
corg = corg_percent()
PERIODS = ['1–3', '4–7', '8–10', '11–15']
DAY_END = [3, 7, 10, 15]
YRATE = 'Respiration rate, CO$_2$-C\n(mg C kg$^{-1}$ day$^{-1}$)'
log = []

# ============================== Figure 1 ==============================
fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.27, 3.25), gridspec_kw=dict(width_ratios=[1, 1.35]))

# (a) cumulative CO2-C
gend = [[jars[j]['cum'] for j in soil_jars(jars, s)] for s in ORDER]
lets, st = letters(gend, POSTHOC)
for s, l in zip(ORDER, lets):
    cum = np.array([[0] + list(np.cumsum(jars[j]['co2'])) for j in soil_jars(jars, s)])
    m, se = cum.mean(0), stats.sem(cum, axis=0)
    a1.errorbar([0] + DAY_END, m, yerr=se, color=COLORS[s], marker='o', ms=4, mec='k', mew=0.5,
                capsize=2.5, lw=1.6, label=SHORT[s], zorder=3)
    a1.text(15.6, m[-1], l, color=COLORS[s], fontsize=11, fontweight='bold', va='center')
a1.set_xlim(-0.5, 17)
a1.set_ylim(0, 700)
a1.set_xticks([0, 3, 7, 10, 15])
a1.set_xlabel('Incubation day')
a1.set_ylabel('Cumulative CO$_2$-C\n(mg C kg$^{-1}$ dry soil)')
a1.text(0.03, 0.97, f"Day 15: F({st['df1']},{st['df2']}) = {st['F']:.1f}\n{ptxt(st['p'])}, η² = {st['eta2']:.2f}",
        transform=a1.transAxes, ha='left', va='top', fontsize=8, bbox=BOX)
despine(a1)
panel_label(a1, 0, x=-0.3, y=1.03)
log.append(f"Fig1a cumulative day15 means {[round(float(np.mean(g)),1) for g in gend]} F({st['df1']},{st['df2']})={st['F']:.2f} {ptxt(st['p'])} eta2={st['eta2']:.2f} letters {lets}")

# (b) rate per period with jar points
w = 0.26
ymax = 62
for k in range(4):
    gk = [[jars[j]['rate'][k] for j in soil_jars(jars, s)] for s in ORDER]
    lk, sk = letters(gk, POSTHOC)
    for i, s in enumerate(ORDER):
        x = k + (i - 1) * w
        m, se = np.mean(gk[i]), stats.sem(gk[i])
        a2.bar(x, m, width=w * 0.92, color=COLORS[s], edgecolor='k', lw=0.5, alpha=0.9, zorder=1)
        a2.errorbar(x, m, yerr=se, fmt='none', ecolor='k', capsize=2.5, lw=0.9, zorder=2)
        a2.scatter(x + np.linspace(-0.06, 0.06, len(gk[i])), gk[i], s=9, facecolor='white', edgecolor='k',
                   lw=0.6, zorder=4)
        if s == 'L':
            a2.scatter([x], [jars['L4']['rate'][k]], marker='x', s=16, color='0.35', lw=0.9, zorder=4)
        top = max(m + se, max(gk[i]))
        a2.text(x, top + 1.3, lk[i], ha='center', va='bottom', fontsize=9, fontweight='bold')
    sig = '' if sk['p'] < 0.05 else ' (n.s.)'
    a2.text(k, -0.13, f"F = {sk['F']:.1f}\n{ptxt(sk['p'])}{sig}", transform=a2.get_xaxis_transform(),
            ha='center', va='top', fontsize=6.8, color='0.25')
    log.append(f"Fig1b days {PERIODS[k]} means {[round(float(np.mean(g)),1) for g in gk]} F({sk['df1']},{sk['df2']})={sk['F']:.2f} {ptxt(sk['p'])} letters {lk}")
a2.set_xticks(range(4))
a2.set_xticklabels(PERIODS, fontsize=8.5)
a2.set_xlabel('Incubation period (days)', labelpad=24)
a2.set_ylim(0, ymax)
a2.set_ylabel(YRATE)
h = [Line2D([], [], color=COLORS[s], marker='s', ms=7, mec='k', mew=0.5, lw=1.6, label=LABELS[s]) for s in ORDER]
h += [Line2D([], [], marker='o', ls='', mfc='white', mec='k', ms=4, label='single jar'),
      Line2D([], [], marker='x', ls='', color='0.35', ms=4, label='jar L4 (outlier, excluded)')]
fig.legend(handles=h, loc='upper center', ncol=3, frameon=False, fontsize=7.5, handlelength=1.8,
           columnspacing=1.2, bbox_to_anchor=(0.5, 1.0))
despine(a2)
panel_label(a2, 1, x=-0.2, y=1.03)
fig.subplots_adjust(left=0.125, right=0.985, top=0.80, bottom=0.21, wspace=0.42)
save(fig, f'fig1_respiration{SUFFIX}')

# ============================== Figure 2 ==============================
cm_g = [[cm[s][r] for r in sorted(cm[s])] for s in ORDER]
if QCO2_WINDOW == 'd11-15':
    q = {s: [jars[j]['rate'][3] / cm[s][int(j[1])] * 1000 / 24 for j in soil_jars(jars, s)] for s in ORDER}
    qlab = 'qCO$_2$, days 11–15\n(µg CO$_2$-C mg$^{-1}$ C$_{mic}$ h$^{-1}$)'
else:
    q = {s: [jars[j]['avg'] / cm[s][int(j[1])] * 1000 / 24 for j in soil_jars(jars, s)] for s in ORDER}
    qlab = 'qCO$_2$, 15-day mean\n(µg CO$_2$-C mg$^{-1}$ C$_{mic}$ h$^{-1}$)'
q_g = [q[s] for s in ORDER]
cc_g = [[cm[s][r] / (corg[s] * 1e4) * 100 for r in sorted(cm[s])] for s in ORDER]

fig, axes = plt.subplots(1, 3, figsize=(6.27, 2.7))
panels = [(cm_g, 'C$_{mic}$ (µg C g$^{-1}$ dry soil)', 570), (q_g, qlab, 8.4), (cc_g, 'C$_{mic}$/C$_{org}$ (%)', 2.9)]
for i, (ax, (g, ylab, ymax)) in enumerate(zip(axes, panels)):
    lets, st = letters(g, POSTHOC)
    xs = np.arange(3)
    m = [np.mean(v) for v in g]
    se = [stats.sem(v) for v in g]
    ax.bar(xs, m, width=0.6, color=[COLORS[s] for s in ORDER], edgecolor='k', lw=0.5)
    ax.errorbar(xs, m, yerr=se, fmt='none', ecolor='k', capsize=4, lw=1)
    for x, v, l in zip(xs, g, lets):
        ax.scatter(x + np.linspace(-0.1, 0.1, len(v)), v, s=10, facecolor='white', edgecolor='k', lw=0.6, zorder=3)
        ax.text(x, max(np.mean(v) + stats.sem(v), max(v)) + 0.035 * ymax, l, ha='center', va='bottom',
                fontsize=10.5, fontweight='bold')
    ax.set_ylim(0, ymax)
    ax.set_xticks(xs)
    ax.set_xticklabels([SHORT[s] for s in ORDER], fontsize=8.5)
    ax.set_ylabel(ylab, fontsize=9)
    ax.set_title(f"F({st['df1']},{st['df2']}) = {st['F']:.1f}, {ptxt(st['p'])}\nη² = {st['eta2']:.2f}", fontsize=7.5, pad=3, color='0.25')
    despine(ax)
    panel_label(ax, i, x=-0.38, y=1.12)
    name = ['Cmic', f'qCO2 {QCO2_WINDOW}', 'Cmic/Corg'][i]
    log.append(f"Fig2 {name} means {[round(float(x),3) for x in m]} SE {[round(float(x),3) for x in se]} F({st['df1']},{st['df2']})={st['F']:.2f} {ptxt(st['p'])} eta2={st['eta2']:.2f} letters {lets}")
fig.subplots_adjust(left=0.1, right=0.99, top=0.82, bottom=0.1, wspace=0.62)
save(fig, f'fig2_biomass_quotients{SUFFIX}')

log.insert(0, f'post-hoc: {TEST_NAME}; qCO2 window: {QCO2_WINDOW}')
open(os.path.join(OUT, f'fig_biology_stats{SUFFIX}.txt'), 'w').write('\n'.join(log) + '\n')
print('\n'.join(log))
