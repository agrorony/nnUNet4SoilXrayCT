"""Appendix figure A1: the respiration simulation model (resp_model, github.com/agrorony/resp_model).

(a) 2D model, stages 10-12: mean +- SE of 40 random pore structures per soil (results/appendix_figure/pinned/curve_*.npy, om_mode as in stage12_run.main;
    per-soil OM amount and availability; same data as the October appendix figure).
(b, c) 3D packing structures of stage 21 (central slices, from results/stage21/step1_slices.png).
(d) Stage 21 respiration, equal per-voxel OM and biomass, no per-soil rules: 3 packing seeds per soil
    (results/stage21/runs/{S,V}_s{0,1,2}_om1_T1500_Dstd_n256.npz), R normalised to the maintenance floor m0*B0.
No measured data is used anywhere in the model.
"""
import numpy as np
from PIL import Image
from matplotlib.patches import Patch
from common import *

# Simulation outputs come from github.com/agrorony/resp_model (results/): set RESP_MODEL_SIM_DIR.
D = os.environ.get('RESP_MODEL_SIM_DIR', os.path.join(HERE, 'sim')) + os.sep
fig = plt.figure(figsize=(6.27, 5.0))
gs = fig.add_gridspec(2, 4, height_ratios=[0.85, 1.05], hspace=0.6, wspace=0.75)
a = fig.add_subplot(gs[0, 0:4])
b = fig.add_subplot(gs[1, 0])
c = fig.add_subplot(gs[1, 1])
d = fig.add_subplot(gs[1, 2:4])

x = np.linspace(0, 1, 500)
for s, key in [('V', 'vertisol'), ('S', 'sand')]:
    cur = np.load(D + f'pinned_curves_{key}.npy')
    m, se = cur.mean(0), cur.std(0, ddof=1) / np.sqrt(cur.shape[0])
    a.plot(x, m, color=COLORS[s], lw=1.8, label=f'{SHORT[s]} (n = {cur.shape[0]})')
    a.fill_between(x, m - se, m + se, color=COLORS[s], alpha=0.35, lw=0)
a.set_xlabel('Fraction of observation window')
a.set_ylabel('Respiration (a.u.)')
a.set_title('2D: soil-specific OM amount and availability', fontsize=7.5, color='0.25', pad=4, loc='right')
a.legend(frameon=False, fontsize=7.5, loc='upper right')
a.text(0.97, 0.55, 'Peak position differs:\nMann–Whitney r = 1.0,\np < 10$^{-14}$', transform=a.transAxes, ha='right',
       va='top', fontsize=7, bbox=BOX)
despine(a)
panel_label(a, 0, x=-0.075, y=1.06)

N = 256 ** 3
floor = 0.02 * 0.0125 * N
t = np.arange(1500) / 1500
for s in ['V', 'S']:
    for seed in range(3):
        z = np.load(D + f'{s}_s{seed}_om1_T1500_Dstd_n256.npz')
        d.plot(t, z['R'] / floor, color=COLORS[s], lw=1.4 if seed == 0 else 0.9, alpha=1 if seed == 0 else 0.7,
               label=f'{SHORT[s]} (3 packing seeds)' if seed == 0 else None)
d.set_xlabel('Fraction of simulated time')
d.set_ylabel('R / maintenance floor')
d.set_title('3D packing: shared rules, OM, biomass', fontsize=7.5, color='0.25', pad=4, loc='right')
d.legend(frameon=False, fontsize=7, loc='upper right', bbox_to_anchor=(1.02, 1.0))
d.text(0.97, 0.62, 'S–V distance 1.21–1.24\nseed noise ≤ 0.11', transform=d.transAxes, ha='right', va='top', fontsize=6.8, bbox=BOX)
despine(d)
panel_label(d, 3, x=-0.26, y=1.06)

im = np.array(Image.open(D + 'step1_slices.png').convert('RGB'))
for ax, (x0, x1), s, i in [(b, (221, 455), 'S', 1), (c, (503, 737), 'V', 2)]:
    ax.imshow(im[98:332, x0:x1])
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_title({'S': 'Sand: grains\n+ fines', 'V': 'Vertisol: porous\nplates'}[s], fontsize=7.5, pad=3)
    ax.set_xlabel('1.28 mm', fontsize=7, labelpad=2)
    panel_label(ax, i, x=-0.08, y=1.3)
fig.legend(handles=[Patch(facecolor='#3a3a3a', label='inert grains'),
                    Patch(facecolor='#c8a46a', label='porous matrix (fines / clay)'),
                    Patch(facecolor='white', edgecolor='0.5', label='resolved pores')],
           loc='lower left', bbox_to_anchor=(0.06, 0.0), frameon=False, fontsize=7, ncol=3, handlelength=1.2, columnspacing=1.0)
fig.subplots_adjust(left=0.1, right=0.98, top=0.94, bottom=0.13)
save(fig, 'figA1_simulation')
