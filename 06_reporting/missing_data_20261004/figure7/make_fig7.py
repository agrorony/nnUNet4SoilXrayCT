"""Figure 7 panels: raw slice | segmentation overlay, per soil. Reads existing outputs only (read-only)."""
import numpy as np, nibabel as nib, itertools, json, os
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
R = r'E:\PROJECTS\Yael_Mishael\Rony\remote_computer backup'
N = R + r'\nnUNet_resources'
OUT = os.path.dirname(os.path.abspath(__file__))
PORE, POM = '#1f77b4', '#d62728'          # deployed labels: pore=5, POM=2 (dataset_info.json differs)
SOIL = {'V': ('#6B4F35', 'Vertisol (Bnei Re\'em)'), 'L': ('#C8A24B', 'Loess (Mishmar HaNegev)'), 'S': ('#D97B4F', 'Sand (Rehovot)')}
def load(p): return np.asarray(nib.load(p).dataobj)
def slice_ax2(a): k = a.shape[2] // 2; return k, a[:, :, k].T
specs = []
raw = load(N + r'\bnei_reem_specA_unified\nifti_predict\bnei_reem_specA_unified_0000.nii.gz')
seg = np.flip(load(N + r'\bnei_reem_specA_unified\inference_concatenated\bnei_reem_specA_unified.nii.gz'), 1)  # nnU-Net output is y-flipped vs raw nifti (corr-verified); display only
k, r = slice_ax2(raw); specs.append(('V', 'bnei_reem_specA_unified', 15.000149, k, r, seg[:, :, k].T, True))
raw = load(N + r'\mishmar_hanegev_maoz_3_5p85um\nifti_predict\mishmar_hanegev_maoz_3_5p85um_0000.nii.gz')
seg = np.flip(load(N + r'\mishmar_hanegev_maoz_3_5p85um\inference_output_concat_loess_i2\mishmar_hanegev_maoz_3_5p85um.nii.gz'), 1)  # nnU-Net output is y-flipped vs raw nifti (corr-verified); display only
k, r = slice_ax2(raw); specs.append(('L', 'mishmar_hanegev_maoz_3_5p85um', 5.85, k, r, seg[:, :, k].T, True))
raw = load(N + r'\rehovot_inference_rehovot_samp_2\nifti_predict\rehovot_samp_2_0000.nii.gz')
msk = np.load(R + r'\10.5\rehovot_samp_2.npy').astype(np.uint8)     # Otsu binary pore mask used for Rehovot Track E
# determine axis order of the npy relative to the nifti by correlating with raw (pore = dark)
best = None
for perm in itertools.permutations(range(3)):
    m = msk.transpose(perm)[:, :, 325].astype(float); c = np.corrcoef(m.ravel(), raw[:, :, 325].ravel())[0, 1]
    if best is None or abs(c) > abs(best[0]): best = (c, perm)
print('rehovot mask axis match', best)
mk = msk.transpose(best[1])
k, r = slice_ax2(raw); s = np.where(mk[:, :, k].T > 0, 5, 0)
specs.append(('S', 'Rehovot_samp2_highkV_Cu0.11_15um', 15.000149, k, r, s, False))
fig, axes = plt.subplots(3, 2, figsize=(7, 10.5)); info = {}
cm = ListedColormap([(0, 0, 0, 0), PORE, POM]); 
for i, (key, name, vox, k, r, s, has_pom) in enumerate(specs):
    col, lab = SOIL[key]
    lo, hi = np.percentile(r, [1, 99])
    ov = np.zeros(s.shape, np.uint8); ov[s == 5] = 1; ov[s == 2] = 2
    for j in range(2):
        ax = axes[i, j]; ax.imshow(r, cmap='gray', vmin=lo, vmax=hi, interpolation='nearest'); ax.set_axis_off()
        if j == 1: ax.imshow(ov, cmap=cm, vmin=0, vmax=2, alpha=0.6, interpolation='nearest')
    bar_mm = 1.0 if vox < 10 else 2.0; px = bar_mm * 1000 / vox
    ax = axes[i, 1]; h, w = r.shape
    ax.plot([w * 0.05, w * 0.05 + px], [h * 0.95] * 2, color='w', lw=3); ax.text(w * 0.05 + px / 2, h * 0.90, f'{bar_mm:g} mm', color='w', ha='center', fontsize=9, fontweight='bold', bbox=dict(fc='k', ec='none', alpha=0.5, pad=1.5))
    axes[i, 0].set_title(f'{lab} - raw (z={k})', color=col, fontsize=9, fontweight='bold', loc='left')
    axes[i, 1].set_title('segmentation' + ('' if has_pom else ' (Otsu, binary)'), fontsize=9, loc='left')
    info[name] = dict(z_slice=int(k), voxel_um=vox, scale_bar_mm=bar_mm, shape=list(r.shape))
fig.legend(handles=[Patch(color=PORE, label='Pore (label 5)'), Patch(color=POM, label='POM (label 2)')], loc='lower center', ncol=2, frameon=False)
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(OUT + r'\figure7_prediction_panels.png', dpi=300); fig.savefig(OUT + r'\figure7_prediction_panels.svg')
json.dump(info, open(OUT + r'\figure7_slice_info.json', 'w'), indent=1)
