"""Render one option. usage: render.py <1|2|3> <crop|full> <full|close> [size_px] [outdir]
Options: 1 translucent pore surface + solid POM; 2 GPU volume-rendered pore haze + solid POM;
3 opaque pores colored by diameter + solid POM.
Shared by the Mishmar and Bnei Re'em runs: the project is defined by common.py next to this file (VOX, CACHE, SEGNPY)."""
import sys, time, json, numpy as np, pyvista as pv
from common import *
HERE = os.path.dirname(os.path.abspath(__file__))
opt, tag, view = int(sys.argv[1]), sys.argv[2], sys.argv[3]
SIZE = int(sys.argv[4]) if len(sys.argv) > 4 else 3000
OUT = sys.argv[5] if len(sys.argv) > 5 else os.path.join(HERE, '..', 'renders')
P = json.load(open(os.environ.get('RENDER_PARAMS', os.path.join(HERE, 'render_params.json'))))
TEAL, GOLD = P['pore_color'], P['pom_color']
SHAPE = (CROP,)*3 if tag == 'crop' else full_shape()
DIMS = tuple(s * VOX for s in SHAPE)          # box edge lengths in um
NMAX = max(DIMS)
CLOSE = float(P.get('close_um', 1200.0))      # close-up cube edge, um


def trunc_viridis(hi=0.65):
    # viridis truncated at 0.65 so the top of the scale is green, not yellow/olive (POM is olive-gold)
    from matplotlib.colors import ListedColormap
    import matplotlib
    return ListedColormap(matplotlib.colormaps['viridis'](np.linspace(0, hi, 256)))


def focus_center():
    p = os.path.join(CACHE, f'closeup_center_{tag}.json')
    if os.path.exists(p): return json.load(open(p))
    s = load_seg(pom_rich_crop() if tag == 'crop' else None); b = max(8, int(round(CLOSE / VOX / 30)))
    n = [(k // b) * b for k in s.shape]
    m = (s[:n[0], :n[1], :n[2]] == POM).reshape(n[0]//b, b, n[1]//b, b, n[2]//b, b).sum((1, 3, 5)).astype(np.float32)   # block counts, location choice only
    from scipy.ndimage import uniform_filter
    w = max(3, int(round(CLOSE / VOX / b)) | 1); f = uniform_filter(m, w, mode='constant')
    h = w // 2; f[:h] = 0; f[-h:] = 0; f[:, :h] = 0; f[:, -h:] = 0; f[:, :, :h] = 0; f[:, :, -h:] = 0
    i = np.unravel_index(np.argmax(f), f.shape); c = [float((k + .5) * b * VOX) for k in i]
    json.dump(c, open(p, 'w')); return c


def camera(bounds):
    az, el = np.radians(P['azimuth']), np.radians(P['elevation'])
    d = np.array([np.cos(el)*np.cos(az), np.cos(el)*np.sin(az), np.sin(el)])
    right = np.cross([0, 0, 1.], d); right /= np.linalg.norm(right); up = np.cross(d, right)
    c = np.array([(bounds[0]+bounds[1])/2, (bounds[2]+bounds[3])/2, (bounds[4]+bounds[5])/2])
    corners = np.array([[x, y, z] for x in bounds[:2] for y in bounds[2:4] for z in bounds[4:]])
    ext = max(np.ptp((corners-c)@right), np.ptp((corners-c)@up))
    return dict(center=c.tolist(), direction=d.tolist(), right=right.tolist(), up=up.tolist(),
                parallel_scale=float(ext / 2 / P['fill']), view_up=[0, 0, 1], distance=float(10*NMAX),
                azimuth_deg=P['azimuth'], elevation_deg=P['elevation'], box_um=[float(bounds[1]-bounds[0]), float(bounds[3]-bounds[2]), float(bounds[5]-bounds[4])])


def load_meshes(box):
    pom = pv.read(os.path.join(CACHE, f'pom_{tag}.vtp'))
    pore = {1: lambda: pv.read(os.path.join(CACHE, f'pore_open_{tag}.vtp')),
            3: lambda: pv.read(os.path.join(CACHE, f'pore3_{tag}.vtp'))}.get(opt, lambda: None)()
    if box is not None:
        pom = pom.clip_box(box, invert=False)
        if pore is not None: pore = pore.clip_box(box, invert=False)
        if P.get('pom_smooth_iter_close', 0):      # display-only smoothing of the POM mesh in close-ups (speckle fix); deviation is reported
            pts0 = np.asarray(pom.points).copy()
            pom = pom.smooth_taubin(n_iter=int(P['pom_smooth_iter_close']), pass_band=float(P.get('pom_smooth_passband', 0.1)), normalize_coordinates=True)
            pom = pom.compute_normals(split_vertices=False, auto_orient_normals=False, consistent_normals=True, point_normals=True, cell_normals=False)
            dev = np.linalg.norm(np.asarray(pom.points) - pts0, axis=1)
            print('POM taubin deviation um: mean %.3f max %.3f' % (dev.mean(), dev.max()), flush=True)
    return pom, pore


def build(cam, box):
    p = pv.Plotter(off_screen=True, window_size=(SIZE, SIZE))
    p.background_color = 'white'
    bounds = box if box is not None else (0, DIMS[0], 0, DIMS[1], 0, DIMS[2])
    pom, pore = load_meshes(box)
    spec = P.get('pom_specular_close', P['pom_specular']) if box is not None else P['pom_specular']
    if opt == 1:
        p.add_mesh(pore, color=TEAL, opacity=P['pore_opacity'], smooth_shading=False, specular=0.0, ambient=0.25, diffuse=0.75)
    elif opt == 2:
        v = np.load(os.path.join(CACHE, f'pore_smooth_u8_{tag}.npy'), mmap_mode='r')
        if box is not None:
            lo = [int(max(0, np.floor(box[2*i]/VOX))) for i in range(3)]; hi = [int(min(v.shape[i], np.ceil(box[2*i+1]/VOX))) for i in range(3)]
            v = v[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]]
        else: lo = [0, 0, 0]
        v = np.ascontiguousarray(v)
        img = pv.ImageData(dimensions=v.shape, spacing=(VOX,)*3, origin=tuple(l*VOX for l in lo)); img.point_data['v'] = v.ravel(order='F')
        from matplotlib.colors import ListedColormap
        ramp = np.clip((np.linspace(0, 255, 65) - 100) / 100.0, 0, 1) ** P['vol_gamma'] * P['vol_max_opacity']   # ~0 below 0.4, full above 0.8 (65 pts: pyvista breaks on 256-length lists)
        p.add_volume(img, scalars='v', cmap=ListedColormap([TEAL]), opacity=ramp.tolist(), clim=[0, 255], mapper='gpu',
                     opacity_unit_distance=P['vol_unit_um'], show_scalar_bar=False, shade=False)
    elif opt == 3:
        p.add_mesh(pore, scalars='diam', cmap=trunc_viridis(), clim=P['diam_clim'], smooth_shading=False, specular=0.1, show_scalar_bar=False)
    p.add_mesh(pom, color=GOLD, opacity=1.0, smooth_shading=False, specular=spec, specular_power=30, ambient=0.2, diffuse=0.8)
    p.add_mesh(pv.Box(bounds), style='wireframe', color='#555555', line_width=P['line_px'])
    p.enable_lightkit()
    p.enable_parallel_projection()
    c = np.array(cam['center']); d = np.array(cam['direction'])
    p.camera.focal_point = c; p.camera.position = c + d * cam['distance']; p.camera.up = (0, 0, 1)
    p.camera.parallel_scale = cam['parallel_scale']; p.camera.clipping_range = (cam['distance'] - 3*NMAX, cam['distance'] + 3*NMAX)
    if opt == 1: p.enable_depth_peeling(number_of_peels=P['peels'], occlusion_ratio=0.0)
    if P['ssao'] and opt != 2: p.enable_ssao(radius=P['ssao_radius_um'], bias=P['ssao_bias_um'], kernel_size=256, blur=True)
    p.enable_anti_aliasing('ssaa')
    return p


def shoot(cam, box):
    t = time.time(); p = build(cam, box)
    p.show(auto_close=False); rgb = p.screenshot(return_img=True)
    rgba = p.screenshot(return_img=True, transparent_background=True); p.close()
    print('render s', round(time.time() - t, 1), flush=True); return rgb, rgba


def to_px(pt, cam):
    c = np.array(cam['center']); r = np.array(cam['right']); u = np.array(cam['up']); s = cam['parallel_scale']
    q = np.array(pt) - c; return SIZE/2 + (q@r)/s*SIZE/2, SIZE/2 - (q@u)/s*SIZE/2


def fmt_mm(x_um): return f'{x_um/1000:.2f}'.rstrip('0').rstrip('.') if abs(x_um/1000 - round(x_um/1000, 1)) > 1e-9 else f'{x_um/1000:.1f}'


def compose(rgb, rgba, cam, box, name):
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    from matplotlib import cm as mcm
    plt.rcParams['font.family'] = 'sans-serif'; plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans']
    fs = 26 * SIZE / 3000
    b = box if box is not None else (0, DIMS[0], 0, DIMS[1], 0, DIMS[2]); d = np.array(cam['direction'])
    # scale: dimension line along a bottom cube edge nearest the viewer, offset below the cube
    near = np.array([b[0] if d[0] < 0 else b[1], b[2] if d[1] < 0 else b[3], b[4]])
    far = np.array([b[1] if d[0] < 0 else b[0], near[1], b[4]])
    off = np.array([0, 0, -0.04*(b[5]-b[4])])
    a0, a1 = to_px(near + off, cam), to_px(far + off, cam)
    ang = np.degrees(np.arctan2(-(a1[1]-a0[1]), a1[0]-a0[0])); ang = ang if abs(ang) <= 90 else ang - 180*np.sign(ang)
    Lx, Ly, Lz = b[1]-b[0], b[3]-b[2], b[5]-b[4]
    txt = f'{Lx/1000:.2f} mm'
    dims_txt = f'Box {Lx/1000:.2f} × {Ly/1000:.2f} × {Lz/1000:.2f} mm'
    for kind, img in (('white', rgb), ('transparent', rgba)):
        fig = plt.figure(figsize=(10, 10), dpi=SIZE/10); ax = fig.add_axes([0, 0, 1, 1])
        ax.imshow(img, interpolation='nearest'); ax.set_xlim(0, SIZE); ax.set_ylim(SIZE, 0); ax.axis('off')
        hs = [Patch(facecolor=TEAL, alpha=.6, edgecolor='none', label='Pores'), Patch(facecolor=GOLD, edgecolor='none', label='POM')]
        if opt == 3: hs = hs[1:]
        ax.legend(handles=hs, loc='upper left', bbox_to_anchor=(0.03, 0.97), frameon=False, fontsize=fs, handlelength=1.4, labelcolor='#222222')
        ax.annotate('', xy=a1, xytext=a0, arrowprops=dict(arrowstyle='<->', color='#222222', lw=2.2*SIZE/3000, shrinkA=0, shrinkB=0))
        ax.text((a0[0]+a1[0])/2, (a0[1]+a1[1])/2 + 45*SIZE/3000, txt, rotation=ang, rotation_mode='anchor', ha='center', va='top', fontsize=fs, color='#222222')
        ax.text(0.97, 0.03, dims_txt, transform=ax.transAxes, ha='right', va='bottom', fontsize=fs*0.75, color='#444444')
        if opt == 3:
            cax = fig.add_axes([0.05, 0.10, 0.30, 0.016]); sm = mcm.ScalarMappable(cmap=trunc_viridis(), norm=plt.Normalize(*P['diam_clim']))
            cb = fig.colorbar(sm, cax=cax, orientation='horizontal', extend='max'); cb.set_label('Pore diameter (µm)', fontsize=fs, color='#222222', labelpad=8)
            cb.ax.tick_params(labelsize=fs*.85, colors='#222222'); cb.outline.set_edgecolor('#555555')
        for ext, kw in (('png', {}), ('tiff', dict(pil_kwargs=dict(compression='tiff_lzw')))):
            fig.savefig(os.path.join(OUT, f'{name}_{kind}.{ext}'), dpi=SIZE/10, transparent=(kind == 'transparent'), **kw)
        plt.close(fig)


def recompose_only(name_suffix):
    """Re-do the matplotlib overlay from saved raw frames (no 3D re-render)."""
    from PIL import Image
    box, cam = scene_geometry()
    rawdir = os.path.join(CACHE, 'raw_frames')
    rgb = np.array(Image.open(os.path.join(rawdir, f'option{opt}_{view}_rgb.png'))); rgba = np.array(Image.open(os.path.join(rawdir, f'option{opt}_{view}_rgba.png')))
    compose(rgb, rgba, cam, box, f'option{opt}_' + name_suffix)


def scene_geometry():
    allb = (0, DIMS[0], 0, DIMS[1], 0, DIMS[2])
    if view == 'full': return None, camera(allb)
    c = np.array(focus_center()); h = CLOSE / 2
    c = np.array([min(max(c[i], h), DIMS[i] - h) for i in range(3)])      # keep the close-up box inside the volume -> label = true size
    box = (c[0]-h, c[0]+h, c[1]-h, c[1]+h, c[2]-h, c[2]+h); return box, camera(box)


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    suffix = 'full_view' if view == 'full' else 'closeup'
    if len(sys.argv) > 6 and sys.argv[6] == 'recompose':
        recompose_only(suffix); sys.exit(0)
    box, cam = scene_geometry()
    if view == 'full': json.dump(cam, open(os.path.join(HERE, '..', f'camera_{tag}.json'), 'w'), indent=1)
    rgb, rgba = shoot(cam, box)
    from PIL import Image
    rawdir = os.path.join(CACHE, 'raw_frames'); os.makedirs(rawdir, exist_ok=True)
    Image.fromarray(rgb).save(os.path.join(rawdir, f'option{opt}_{view}_rgb.png')); Image.fromarray(rgba).save(os.path.join(rawdir, f'option{opt}_{view}_rgba.png'))
    compose(rgb, rgba, cam, box, f'option{opt}_' + suffix)
