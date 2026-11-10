import numpy as np
from scipy import ndimage


def compute_error_map(
    pred: np.ndarray,
    gt: np.ndarray = None,
    target_class: int = None,
) -> np.ndarray:
    """Return float (Z,Y,X) error map.

    If gt is provided:
      - With target_class: XOR of binary masks (pred==c) and (gt==c).
        Catches both false positives and false negatives for that class.
      - Without target_class: raw voxel-wise disagreement (pred != gt).
    Without gt: gradient-magnitude boundary-uncertainty proxy, computed on
      the binary mask for target_class if given, else on the full pred array.
    """
    if gt is not None:
        if target_class is not None:
            valid     = gt != 0          # 0 means "unlabeled" — exclude from error map
            pred_mask = pred == target_class
            gt_mask   = gt == target_class
            return ((pred_mask != gt_mask) & valid).astype(np.float32)
        return (pred != gt).astype(np.float32)
    base = (pred == target_class).astype(np.float32) if target_class is not None else pred.astype(np.float32)
    grads = np.gradient(base)
    return np.sqrt(sum(g ** 2 for g in grads)).astype(np.float32)


def get_error_regions(error_map: np.ndarray, min_size: int = 100) -> list[dict]:
    """Connected components of error_map > 0, sorted largest-first.

    Each entry: {"id": int, "size": int, "bbox": (z0,z1,y0,y1,x0,x1)}.
    """
    binary = error_map > 0
    labeled, num = ndimage.label(binary)
    regions = []
    for i in range(1, num + 1):
        coords = np.where(labeled == i)
        size = len(coords[0])
        if size < min_size:
            continue
        bbox = (
            int(coords[0].min()), int(coords[0].max()) + 1,
            int(coords[1].min()), int(coords[1].max()) + 1,
            int(coords[2].min()), int(coords[2].max()) + 1,
        )
        regions.append({"id": i, "size": size, "bbox": bbox})
    regions.sort(key=lambda r: r["size"], reverse=True)
    return regions
