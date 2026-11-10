"""Figure 3: one CT slice and its segmentation per soil, re-laid out as 2 rows x 3 columns.

Source: 6_figures/segmentation_examples/figure7_prediction_panels.png,
made by make_fig7.py from the final model outputs: Vertisol bnei_reem_specA_unified z=325 (15 um),
Loess mishmar_hanegev_maoz_3_5p85um z=500 (5.85 um), Sand Rehovot_samp2 z=325 (15 um, Otsu binary).
The tiles are cropped from that panel unchanged (scale bars included); only the layout, panel letters
and legend are new (legend without internal label codes).
"""
import numpy as np
from PIL import Image
from matplotlib.patches import Patch
from common import *

src = np.array(Image.open(os.path.join(REPO, '6_figures', 'segmentation_examples', 'figure7_prediction_panels.png')).convert('RGB'))
ROWS = [(100, 1004), (1104, 2007), (2107, 3011)]   # Vertisol, Loess, Sand
COLS = [(91, 995), (1105, 2009)]                   # raw, segmentation
tiles = {s: [src[r0:r1, c0:c1] for c0, c1 in COLS] for s, (r0, r1) in zip(['V', 'L', 'S'], ROWS)}

fig, axes = plt.subplots(2, 3, figsize=(6.27, 4.55))
for j, s in enumerate(ORDER):
    for i in range(2):
        ax = axes[i, j]
        ax.imshow(tiles[s][i])
        ax.set_xticks([]); ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_visible(False)
        panel_label(ax, i * 3 + j, x=0.0, y=1.02)
    axes[0, j].set_title(f'{LABELS[s]}\n' + {'L': '5.85 µm voxel', 'V': '15 µm voxel', 'S': '15 µm voxel'}[s],
                         fontsize=8.5, color='k', pad=14)
axes[0, 0].text(-0.06, 0.5, 'CT slice', transform=axes[0, 0].transAxes, rotation=90, ha='right', va='center', fontsize=9)
axes[1, 0].text(-0.06, 0.5, 'Segmentation', transform=axes[1, 0].transAxes, rotation=90, ha='right', va='center', fontsize=9)
axes[1, 2].text(0.5, -0.04, 'Otsu threshold (pore / solid only)', transform=axes[1, 2].transAxes, ha='center', va='top', fontsize=7.5, color='0.25')
axes[1, 0].text(0.5, -0.04, 'nnU-Net', transform=axes[1, 0].transAxes, ha='center', va='top', fontsize=7.5, color='0.25')
axes[1, 1].text(0.5, -0.04, 'nnU-Net', transform=axes[1, 1].transAxes, ha='center', va='top', fontsize=7.5, color='0.25')
fig.legend(handles=[Patch(color='#1f5f8b', label='Pore'), Patch(color='#d62728', label='Particulate organic matter (POM)'),
                    Patch(facecolor='#dcdcdc', edgecolor='0.6', label='Solid (unlabelled background)')],
           loc='lower center', ncol=3, frameon=False, fontsize=8)
fig.subplots_adjust(left=0.05, right=0.99, top=0.88, bottom=0.1, wspace=0.06, hspace=0.18)
save(fig, 'fig3_segmentation')
