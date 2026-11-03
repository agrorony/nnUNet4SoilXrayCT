"""Step 3 (Option 3) - give every vertex of the closed pore mesh the diameter (um) of the nearest pore voxel
(nearest voxel with diameter_map > 0; sampling exactly on the surface would give zero / shell-leak values).
usage: step3_color_mesh.py <crop|full>"""
import sys, json, time, numpy as np, pyvista as pv
from scipy import ndimage as ndi
from common import *
tag = sys.argv[1]
d = np.load(os.path.join(CACHE, 'diameter_map_flipped_f32.npy'), mmap_mode='r')
if tag == 'crop':
    c = pom_rich_crop(); d = np.ascontiguousarray(d[c[0]:c[0]+c[3], c[1]:c[1]+c[3], c[2]:c[2]+c[3]])
else: d = np.ascontiguousarray(d)
d = np.where(d > 0, d, 0).astype(np.float32)
pore = np.load(os.path.join(CACHE, f'pore_clean_{tag}.npy'))
d[~pore] = 0                                                       # pipeline guard (and hides the same specks as the mesh)
t = time.time()
inside = d > 0
idx = ndi.distance_transform_edt(~inside, return_distances=False, return_indices=True).astype(np.int32)   # nearest pore voxel
print('edt idx', round(time.time()-t), 's', flush=True)
m = pv.read(os.path.join(CACHE, f'pore_closed_{tag}.vtp'))
P = np.asarray(m.points); n = d.shape[0]
out = np.empty(len(P), np.float32); step = 20_000_000
for a in range(0, len(P), step):
    ijk = np.clip(np.rint(P[a:a+step] / VOX - 0.0).astype(np.int64), 0, n - 1)
    nn = idx[:, ijk[:, 0], ijk[:, 1], ijk[:, 2]]
    out[a:a+step] = d[nn[0], nn[1], nn[2]] * VOX                   # diameter voxels -> um
m.point_data['diam'] = out
m.save(os.path.join(CACHE, f'pore3_{tag}.vtp'))
print('vertices', len(P), 'diam um p2/p50/p98/max', np.percentile(out[out > 0], [2, 50, 98]), out.max(), 'zero-valued vertices', int((out == 0).sum()), round(time.time()-t), 's')
