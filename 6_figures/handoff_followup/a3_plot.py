"""Plot the A3 strict matrices (images: Pearson r; segmentations: pore Dice) as heatmaps; n/c = grey.
Usage: python a3_plot.py <A3_content_level.json> <out.png>
"""
import json
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

d = json.load(open(sys.argv[1]))
fig, axes = plt.subplots(1, 2, figsize=(24, 11), gridspec_kw=dict(width_ratios=[1, 2.2]))
for ax, k, lab, vmin in ((axes[0], 'image', 'Images: Pearson r (stride 2)', -1), (axes[1], 'seg', 'Segmentations: pore Dice (stride 2)', 0)):
    names = [l.split(': ', 1)[1] for l in d[k]['legend']]
    rels = sorted({s['a'] for s in d[k]['strict']} | {s['b'] for s in d[k]['strict']})
    n = len(names)
    M = np.full((n, n), np.nan)
    # legend order == entry order; map rel -> index via the strict list order of first appearance
    order = [l.split('`')[1] for l in d[k]['legend']]
    from a3_content_matrices import short  # noqa: E402
    idx = {}
    for s in d[k]['strict']:
        for r in (s['a'], s['b']):
            idx[r] = order.index(short(r))
    for s in d[k]['strict']:
        i, j = idx[s['a']], idx[s['b']]
        M[i, j] = M[j, i] = s['score']
    cmap = plt.get_cmap('RdBu_r' if k == 'image' else 'viridis').copy(); cmap.set_bad('#d0d0d0')
    im = ax.imshow(M, cmap=cmap, vmin=vmin, vmax=1)
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            ax.text(j, i, 'n/c' if np.isnan(M[i, j]) else f'{M[i, j]:.2f}', ha='center', va='center', fontsize=6 if k == 'seg' else 8,
                    color='k' if np.isnan(M[i, j]) or (k == 'image' and abs(M[i, j]) < 0.6) or (k == 'seg' and M[i, j] > 0.6) else 'w')
    ax.set_xticks(range(n)); ax.set_yticks(range(n))
    ax.set_xticklabels([str(i) for i in range(n)], fontsize=7)
    ax.set_yticklabels([f'{i}: {nm}' for i, nm in enumerate(names)], fontsize=7)
    ax.set_title(lab); plt.colorbar(im, ax=ax, fraction=0.03)
fig.suptitle('Part A3 - content-level duplicate check (identity orientation; grey = different shape, n/c)\n'
             'Transform-searched extras: canonical img.tif vs specB img r=0.9999 (TIF z,y,x -> NIfTI x,y,z); all other image pairs |r| < 0.07')
fig.tight_layout()
fig.savefig(sys.argv[2], dpi=110)
