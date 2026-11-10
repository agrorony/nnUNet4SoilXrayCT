import numpy as np, os, json
VOX = 5.85  # um, forced (header says 1.0)
CACHE = r'E:\PROJECTS\Yael_Mishael\Rony\remote_computer backup\render3d_mishmar_5p85_20261012'
SEGNPY = os.path.join(CACHE, 'seg_flipped_uint8.npy')   # flipped on nibabel axis 1, as make_fig7.py
PORE, POM = 5, 2
def load_seg(crop=None):
    s = np.load(SEGNPY, mmap_mode='r')
    return np.ascontiguousarray(s if crop is None else s[crop[0]:crop[0]+crop[3], crop[1]:crop[1]+crop[3], crop[2]:crop[2]+crop[3]])
def pom_rich_crop(size=300, blk=100):
    p = os.path.join(CACHE, 'crop300.json')
    if os.path.exists(p): return json.load(open(p))
    s = np.load(SEGNPY, mmap_mode='r'); n = s.shape[0]; best = None
    for x in range(0, n-size+1, 50):
        for y in range(0, n-size+1, 50):
            for z in range(0, n-size+1, 50):
                v = (np.asarray(s[x:x+size:4, y:y+size:4, z:z+size:4]) == POM).mean()   # selection heuristic only (not for rendering)
                if best is None or v > best[0]: best = (v, [x, y, z, size])
    json.dump(best[1], open(p, 'w')); print('crop', best); return best[1]


CROP = 300   # tuning crop edge in voxels
def full_shape(): return tuple(np.load(SEGNPY, mmap_mode='r').shape)
