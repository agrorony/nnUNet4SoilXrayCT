"""Step 2 (Option 3) - local-thickness diameter map with the repo's own PSD code (psd_diagnostics_core.run_psd_pipeline),
configured exactly like psd_diag_20260802T104738_nlm_volume_fresh_bnei_reem_i4 (chunked EDT 128^3, halo 50,
exclude_borders, extended bin edges, CPU). No saved map existed in that run, so it is recomputed here and validated
against its psd_table.csv. Runs on the ORIGINAL (unflipped) volume, then flips axis 1 to match the rendered orientation."""
import sys, json, csv, time, numpy as np, nibabel as nib
sys.path.insert(0, r'E:\PROJECTS\Yael_Mishael\Rony\remote_computer backup\nnUNet4SoilXrayCT\05_evaluation\psd')
from psd_diagnostics_core import run_psd_pipeline
from common import *
RUN = r'E:\PROJECTS\Yael_Mishael\Rony\remote_computer backup\10.5\psd_outputs\psd_diag_20260802T104738_nlm_volume_fresh_bnei_reem_i4'
SEG = json.load(open(os.path.join(CACHE, 'step0_input.json')))['path']
cfg = json.load(open(os.path.join(RUN, 'config.json')))
edges = np.array(cfg['extended_bin_edges_um'])
pore = np.asarray(nib.load(SEG).dataobj) == PORE
t = time.time()
res = run_psd_pipeline(pore, (VOX, VOX, VOX), use_chunking=True, chunk_size=tuple(cfg['chunk_size']), halo_width=cfg['halo_width'],
                       exclude_borders=cfg['exclude_borders'], bin_edges_um=edges, use_gpu=False)
print('elapsed s', round(time.time() - t), flush=True)
psd = res['psd']
mine = np.asarray(psd['volume_counts'], dtype=np.int64)
ref = np.array([int(float(r['Volume_Count'])) for r in csv.DictReader(open(os.path.join(RUN, 'psd_table.csv')))])
print('counts match psd_table.csv exactly:', bool(np.array_equal(mine, ref)), '| max abs diff', int(np.abs(mine - ref).max()), '| total', int(mine.sum()), int(ref.sum()), flush=True)
d = psd['diameter_map'] * np.asarray(pore, dtype=np.float32)          # pipeline guard: pore_mask & (diameter_map > 0); porespy leaks nonzero values outside the pore
d[~(d > 0)] = 0
np.save(os.path.join(CACHE, 'diameter_map_flipped_f32.npy'), np.flip(d, 1).astype(np.float32))
v = d[psd['masked_pore_mask']]
print('diameter um (2,50,98 pct, max):', np.percentile(v * VOX, [2, 50, 98]), v.max() * VOX)
json.dump(dict(match_psd_table=bool(np.array_equal(mine, ref)), max_abs_count_diff=int(np.abs(mine - ref).max()),
               pct_um=dict(zip(['p2', 'p50', 'p98'], (np.percentile(v, [2, 50, 98]) * VOX).tolist())), max_um=float(v.max() * VOX),
               unit_note='diameter_map values are in voxels; x5.85 = um'), open(os.path.join(CACHE, 'diameter_map_check.json'), 'w'), indent=1)
