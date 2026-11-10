"""Step 4 - contact sheet: the three full views (same camera) + the Dor et al. 2025 Fig. 1a reference."""
import os
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
HERE = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(HERE, '..', 'renders')
REF = os.path.join(HERE, '..', '..', '..', 'dor2025_fig1a_reference.png')
items = [('Reference: Dor et al. 2025, Fig. 1a', Image.open(REF).convert('RGB')),
         ('Option 1: translucent pore surface', Image.open(os.path.join(R, 'option1_full_view_white.png')).convert('RGB')),
         ('Option 2: pore volume haze (GPU)', Image.open(os.path.join(R, 'option2_full_view_white.png')).convert('RGB')),
         ('Option 3: pores by diameter', Image.open(os.path.join(R, 'option3_full_view_white.png')).convert('RGB'))]
plt.rcParams['font.family'] = 'sans-serif'; plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans']
fig, axs = plt.subplots(1, 4, figsize=(24, 6.8), gridspec_kw=dict(width_ratios=[0.5, 1, 1, 1]))
for ax, (t, im) in zip(axs, items):
    im = im.copy(); im.thumbnail((1400, 1400), Image.LANCZOS)      # display-only thumbnail of the finished renders
    ax.imshow(im); ax.set_title(t, fontsize=13); ax.axis('off')
fig.tight_layout(rect=(0, 0, 1, 0.94)); fig.savefig(os.path.join(HERE, '..', 'contact_sheet.png'), dpi=150, facecolor='white')
