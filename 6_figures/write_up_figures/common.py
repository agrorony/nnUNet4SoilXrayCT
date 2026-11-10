"""Shared style, data loading and statistics for the revised figures (Nov 2026).

Style: soil-figures-style skill (fixed soil colours, SE only, omnibus statistic on the figure,
compact letters, despined axes). Change from the October figures, per Maoz's review:
no figure titles inside the images, larger fonts, related panels merged into one figure.
"""
import os
import numpy as np
import openpyxl
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import stats

COLORS = {"L": "#C8A24B", "V": "#6B4F35", "S": "#D97B4F"}
LABELS = {"L": "Loess (Mishmar HaNegev)", "V": "Vertisol (Bnei Re'em)", "S": "Sand (Rehovot)"}
SHORT = {"L": "Loess", "V": "Vertisol", "S": "Sand"}
ORDER = ["L", "V", "S"]
PANEL = list("abcdefgh")        # switch to list("אבגדהוזח") for Hebrew panel letters
C_FROM_CO2 = 12.0 / 44.0
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
# Lab workbooks are not in the repo: point LAB_DATA_DIR at 07_lab_data_and_writeup/raw_workbooks from the hand-off ZIP.
DATA = os.environ.get('LAB_DATA_DIR', os.path.join(HERE, 'lab_data')) + os.sep
OUT = os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)

plt.rcParams.update({
    'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.labelsize': 10.5, 'axes.titlesize': 10.5,
    'xtick.labelsize': 9.5, 'ytick.labelsize': 9.5, 'legend.fontsize': 9, 'axes.linewidth': 0.8,
    'svg.fonttype': 'none',
})
BOX = dict(boxstyle='round,pad=0.35', fc='white', ec='0.6', lw=0.7)


def despine(ax):
    ax.spines[['top', 'right']].set_visible(False)


def panel_label(ax, i, x=-0.16, y=1.04):
    ax.text(x, y, f'({PANEL[i]})', transform=ax.transAxes, fontsize=12, fontweight='bold', va='bottom')


def ptxt(p):
    return 'p < 0.001' if p < 0.001 else f'p = {p:.3f}'


# ---------------------------------------------------------------- data
def respiration():
    """Per-jar CO2-C (mg C kg-1 dry soil) per period, rates per period, cumulative; L4 kept, flagged."""
    wb = openpyxl.load_workbook(DATA + 'Soil_CO2_Respiration_v4.xlsx', data_only=True)
    ws = wb['Results']
    jars = {}
    for row in ws.iter_rows(min_row=9, max_row=20, values_only=True):
        jid = row[0]
        if not jid or not isinstance(row[3], (int, float)):
            continue
        jars[jid] = dict(co2=np.array([row[3], row[6], row[9], row[12]]) * C_FROM_CO2,
                         rate=np.array([row[4], row[7], row[10], row[13]]) * C_FROM_CO2,
                         cum=row[14] * C_FROM_CO2, avg=row[15] * C_FROM_CO2)
    return jars


def soil_jars(jars, s, include_outlier=False):
    return [j for j in sorted(jars) if j[0] == s and (include_outlier or j != 'L4')]


def cmic():
    """Cmic (ug C g-1 dry soil) per replicate, from the Calculations sheet."""
    wb = openpyxl.load_workbook(DATA + 'Fumigation_Extraction_Experiment.xlsx', data_only=True)
    ws = wb['Calculations']
    out = {s: {} for s in ORDER}
    for row in ws.iter_rows(min_row=1, values_only=True):
        if row[0] in out and isinstance(row[1], (int, float)) and isinstance(row[4], (int, float)):
            out[row[0]][int(row[1])] = row[4]
    return out


def corg_percent():
    """Total organic C (%) per soil = mean SOM (LOI 400 C) / 1.724, from the FE Summary sheet."""
    wb = openpyxl.load_workbook(DATA + 'Fumigation_Extraction_Experiment.xlsx', data_only=True)
    ws = wb['Summary']
    out = {}
    for row in ws.iter_rows(min_row=1, values_only=True):
        if row[0] in ORDER and isinstance(row[5], (int, float)):
            out[row[0]] = row[5]
    return out


# ---------------------------------------------------------------- statistics
def anova(groups):
    groups = [np.asarray(g, float) for g in groups]
    f, p = stats.f_oneway(*groups)
    allv = np.concatenate(groups)
    gm = allv.mean()
    eta2 = sum(len(g) * (g.mean() - gm) ** 2 for g in groups) / ((allv - gm) ** 2).sum()
    return dict(F=f, p=p, eta2=eta2, df1=len(groups) - 1, df2=len(allv) - len(groups))


def assumptions(groups):
    groups = [np.asarray(g, float) for g in groups]
    resid = np.concatenate([g - g.mean() for g in groups])
    sw = stats.shapiro(resid)
    lev = stats.levene(*groups, center='median')   # Brown-Forsythe
    return dict(shapiro_W=sw.statistic, shapiro_p=sw.pvalue, bf_stat=lev.statistic, bf_p=lev.pvalue)


def lsd_pvalues(groups):
    """Fisher's LSD: pairwise t-tests using the pooled within-group MSE of the one-way ANOVA."""
    groups = [np.asarray(g, float) for g in groups]
    k = len(groups)
    n = np.array([len(g) for g in groups])
    dfe = n.sum() - k
    mse = sum(((g - g.mean()) ** 2).sum() for g in groups) / dfe
    P = np.ones((k, k))
    for i in range(k):
        for j in range(i + 1, k):
            t = (groups[i].mean() - groups[j].mean()) / np.sqrt(mse * (1 / n[i] + 1 / n[j]))
            P[i, j] = P[j, i] = 2 * stats.t.sf(abs(t), dfe)
    return P


def tukey_pvalues(groups):
    return stats.tukey_hsd(*[np.asarray(g, float) for g in groups]).pvalue


def cld(groups, pmat, alpha=0.05):
    """Compact letter display (insert-and-absorb); the lowest mean gets 'a'."""
    n = len(groups)
    means = [np.mean(g) for g in groups]
    sets = [set(range(n))]
    for i in range(n):
        for j in range(i + 1, n):
            if pmat[i, j] < alpha:
                new = []
                for st in sets:
                    if i in st and j in st:
                        new += [st - {i}, st - {j}]
                    else:
                        new.append(st)
                new = [set(t) for t in {frozenset(a) for a in new}]
                sets = [a for a in new if not any(a < b for b in new)]
    sets.sort(key=lambda st: min(means[k] for k in st))
    letters = ['' for _ in range(n)]
    for li, st in enumerate(sets):
        for k in sorted(st):
            letters[k] += 'abcdef'[li]
    return letters


def letters(groups, method='lsd'):
    """Protected post-hoc letters: only if the omnibus F is significant."""
    a = anova(groups)
    if a['p'] >= 0.05:
        return ['a'] * len(groups), a
    P = lsd_pvalues(groups) if method == 'lsd' else tukey_pvalues(groups)
    return cld(groups, P), a


def save(fig, name):
    fig.savefig(os.path.join(OUT, f'{name}.png'), dpi=200)
    fig.savefig(os.path.join(OUT, f'{name}.svg'))
    plt.close(fig)
