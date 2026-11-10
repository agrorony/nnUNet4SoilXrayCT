"""Step 1 - build surfaces on the native grid. usage: step1_mesh.py [crop|full]
Smoothing: Gaussian sigma=0.8 voxel on each binary mask, contour at 0.5 (flying edges). Specks <27 voxels hidden (6-conn).
Pore mesh is built padded (closed at cube faces, for Option 3) and also open (Options 1/2, no caps)."""
import sys, time, json, numpy as np, pyvista as pv, vtk
from scipy import ndimage as ndi
from common import *
mode = sys.argv[1] if len(sys.argv) > 1 else 'crop'
SIG, MINV = 0.8, 27
crop = pom_rich_crop() if mode == 'crop' else None
tag = 'crop' if crop else 'full'
seg = load_seg(crop); print(tag, seg.shape, flush=True)
stats = {}
def clean(mask, name):
    t = time.time(); lab, n = ndi.label(mask)                       # 6-connectivity
    sz = np.bincount(lab.ravel()); sz[0] = 0
    keep = sz >= MINV; keep[0] = False
    out = keep[lab]; hid = int(mask.sum() - out.sum())
    stats[name] = dict(components=int(n), hidden_vox=hid, hidden_pct=100*hid/max(1, int(mask.sum())), n_hidden_components=int((~keep[1:]).sum()))
    print(name, stats[name], round(time.time()-t), 's', flush=True); return out
def surf(mask, pad):
    if pad: mask = np.pad(mask, 1)
    f = ndi.gaussian_filter(mask.astype(np.float32), SIG)
    return f
def contour(f, pad, name, save_vol=False):
    t = time.time()
    img = pv.ImageData(dimensions=f.shape, spacing=(VOX,)*3, origin=((-VOX) if pad else 0.,)*3)
    img.point_data['v'] = f.ravel(order='F')
    m = img.contour([0.5], scalars='v', method='flying_edges')
    m = m.compute_normals(split_vertices=False, auto_orient_normals=False, consistent_normals=True, point_normals=True, cell_normals=False)
    m.save(os.path.join(CACHE, f'{name}_{tag}.vtp')); print(name, 'pts', m.n_points, 'cells', m.n_cells, round(time.time()-t), 's', flush=True)
    stats[name+'_mesh'] = dict(points=int(m.n_points), triangles=int(m.n_cells))
pom = clean(seg == POM, 'pom'); contour(surf(pom, False), False, 'pom')
pore = clean(seg == PORE, 'pore')
np.save(os.path.join(CACHE, f'pore_clean_{tag}.npy'), pore)
f = surf(pore, False)
np.save(os.path.join(CACHE, f'pore_smooth_u8_{tag}.npy'), np.clip(f*255+.5, 0, 255).astype(np.uint8))   # Option 2 volume
contour(f, False, 'pore_open'); del f
contour(surf(pore, True), True, 'pore_closed')
json.dump(dict(sigma_vox=SIG, min_voxels=MINV, crop=crop, stats=stats), open(os.path.join(CACHE, f'mesh_stats_{tag}.json'), 'w'), indent=1)
