"""Build a small synthetic 3D label volume (40, 100, 100), single class,
containing: a clean continuous object, a disappearing object, a splitting
object, and an object that jumps position implausibly between two slices.
"""
import os
import numpy as np
import tifffile

NZ, NY, NX = 40, 100, 100
OUT_PATH = os.path.join(os.path.dirname(__file__), 'synthetic_labels.tif')


def _disk_mask(cy, cx, r):
    yy, xx = np.ogrid[:NY, :NX]
    return (yy - cy) ** 2 + (xx - cx) ** 2 <= r ** 2


def build_synthetic_volume():
    vol = np.zeros((NZ, NY, NX), dtype=np.uint8)

    # A: clean continuation, identical disk every slice -> should have zero flags.
    a_mask = _disk_mask(15, 15, 6)
    for z in range(NZ):
        vol[z][a_mask] = 1

    # B: disappears after z=19 (present z=0..19, absent afterwards).
    b_mask = _disk_mask(15, 85, 6)
    for z in range(20):
        vol[z][b_mask] = 1

    # C: single disk z=0..14, splits into two smaller disks z=15..39.
    c_parent = _disk_mask(85, 15, 8)
    for z in range(15):
        vol[z][c_parent] = 1
    c_child1 = _disk_mask(85, 9, 5)
    c_child2 = _disk_mask(85, 21, 5)
    for z in range(15, NZ):
        vol[z][c_child1] = 1
        vol[z][c_child2] = 1

    # D: jumps position by more than plausible per-slice motion at z=19->20.
    # radius/shift chosen so footprints still overlap enough to be matched
    # (iou ~0.17, above the graph-building iou_threshold) while the ~18px
    # centroid jump still clears max_centroid_jump.
    d_before = _disk_mask(60, 70, 15)
    d_after = _disk_mask(78, 70, 15)
    for z in range(20):
        vol[z][d_before] = 1
    for z in range(20, NZ):
        vol[z][d_after] = 1

    return vol


if __name__ == '__main__':
    vol = build_synthetic_volume()
    tifffile.imwrite(OUT_PATH, vol)
    print(f'[OK] wrote synthetic volume {vol.shape} -> {OUT_PATH}')
