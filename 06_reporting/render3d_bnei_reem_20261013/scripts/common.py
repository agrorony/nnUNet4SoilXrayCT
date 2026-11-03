import numpy as np, os, json
VOX = 15.000149  # um (Bnei Re'em, Vertisol; NIfTI header says 1.0, forced)
CACHE = r'E:\PROJECTS\Yael_Mishael\Rony\remote_computer backup\render3d_bnei_reem_20261013'
SEGNPY = os.path.join(CACHE, 'seg_flipped_uint8.npy')   # flipped on nibabel axis 1 (correlation-verified in step0a)
PORE, POM = 5, 2
CROP = 200   # tuning crop edge in voxels (full-resolution crop, not a downsample)


def load_seg(crop=None):
    s = np.load(SEGNPY, mmap_mode='r')
    return np.ascontiguousarray(s if crop is None else s[crop[0]:crop[0]+crop[3], crop[1]:crop[1]+crop[3], crop[2]:crop[2]+crop[3]])


def full_shape(): return tuple(np.load(SEGNPY, mmap_mode='r').shape)


def pom_rich_crop(size=CROP):
    p = os.path.join(CACHE, 'crop_tune.json')
    if os.path.exists(p): return json.load(open(p))
    s = np.load(SEGNPY, mmap_mode='r'); best = None; st = size // 4
    for x in range(0, s.shape[0]-size+1, st):
        for y in range(0, s.shape[1]-size+1, st):
            for z in range(0, s.shape[2]-size+1, st):
                v = (np.asarray(s[x:x+size:3, y:y+size:3, z:z+size:3]) == POM).mean()   # selection heuristic only (not for rendering)
                if best is None or v > best[0]: best = (v, [x, y, z, size])
    json.dump(best[1], open(p, 'w')); print('crop', best); return best[1]
