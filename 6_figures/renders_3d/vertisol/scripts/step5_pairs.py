"""Step 5 - side-by-side pair figures, one per option: Mishmar (left) | Bnei Re'em (right).
Uses the finished, identically-styled full-view renders (same camera, colors, legend style). Each panel keeps its own scale arrow and
box-dimension label baked in by render.py, so the two panels are never implied to share a scale."""
import os
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
HERE = os.path.dirname(os.path.abspath(__file__))
REP = os.path.abspath(os.path.join(HERE, '..', '..'))
L = os.path.join(REP, 'loess_5p85um', 'renders')
R = os.path.join(REP, 'vertisol', 'renders')
OUT = os.path.join(REP, 'pairs'); os.makedirs(OUT, exist_ok=True)
plt.rcParams['font.family'] = 'sans-serif'; plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans']
names = {1: 'option1_translucent_pores', 2: 'option2_pore_haze', 3: 'option3_pore_diameter'}
for o, n in names.items():
    a = Image.open(os.path.join(L, f'option{o}_full_view_white.png')).convert('RGB')
    b = Image.open(os.path.join(R, f'option{o}_full_view_white.png')).convert('RGB')
    assert a.size == b.size
    w, h = a.size
    fig = plt.figure(figsize=(2*w/300, (h + 260)/300), dpi=300)
    for i, (im, t) in enumerate(((a, 'Loess (Mishmar HaNegev), 5.85 µm'), (b, 'Vertisol (Bnei Re’em), 15 µm'))):
        ax = fig.add_axes([i/2, 0, 0.5, h/(h + 260)]); ax.imshow(im); ax.axis('off')
        fig.text(i/2 + 0.25, 1 - 130/(h + 260), t, ha='center', va='center', fontsize=30, color='#222222')
    fig.savefig(os.path.join(OUT, f'pair_{n}.png'), dpi=300, facecolor='white'); plt.close(fig)
    print('wrote', n)
