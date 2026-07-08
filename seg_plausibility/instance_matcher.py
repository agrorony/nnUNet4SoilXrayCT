"""Per-slice instance labeling, cross-slice IoU matching, and persistent id assignment.

Matching is vectorized: for a pair of labeled slices it builds the full
label-x-label overlap (confusion) matrix in one shot via a bincount, instead
of looping over every (region_z, region_z1) pair in Python. This is what
makes classes with hundreds of small regions per slice (e.g. a fragmented
pore network) tractable. The bincount runs on GPU via torch when available
(CUDA), and transparently falls back to numpy on CPU otherwise.
"""
import numpy as np
from skimage.measure import label as sk_label, regionprops

try:
    import torch
    _HAS_TORCH = True
except ImportError:
    _HAS_TORCH = False


def default_device():
    """'cuda' if a CUDA-capable torch is installed, else 'cpu'."""
    if _HAS_TORCH and torch.cuda.is_available():
        return 'cuda'
    return 'cpu'


def label_slices(volume):
    """For each z slice and each foreground class value, connected-component
    label the 2D slice and compute region props.

    Returns
    -------
    props_by_zc : dict[(z, cls)] -> list of dicts, each:
        {'local_id': int, 'bbox': (minr, minc, maxr, maxc), 'area': int,
         'centroid': (row, col), 'eccentricity': float}
        local_id is 1-based and contiguous (skimage.measure.label always
        assigns sequential ids), matching row/col index (local_id - 1) in
        the overlap matrix built by match_slices.
    lbl_by_zc : dict[(z, cls)] -> labeled 2D array (int32) or None if the
        class is absent from that slice. Kept around so match_slices and
        the caller don't have to re-run connected-component labeling.
    """
    nz = volume.shape[0]
    classes = sorted(int(c) for c in np.unique(volume) if c != 0)
    props_by_zc = {}
    lbl_by_zc = {}
    for z in range(nz):
        sl = volume[z]
        for cls in classes:
            mask = sl == cls
            if not mask.any():
                props_by_zc[(z, cls)] = []
                lbl_by_zc[(z, cls)] = None
                continue
            lbl = sk_label(mask, connectivity=2).astype(np.int32)
            lbl_by_zc[(z, cls)] = lbl
            regions = regionprops(lbl)
            entries = []
            for r in regions:
                entries.append({
                    'local_id': int(r.label),
                    'bbox': r.bbox,
                    'area': int(r.area),
                    'centroid': tuple(float(v) for v in r.centroid),
                    'eccentricity': float(r.eccentricity),
                })
            props_by_zc[(z, cls)] = entries
    return props_by_zc, lbl_by_zc


def _overlap_matrix(lbl_z, lbl_z1, n1, n2, device):
    """Full (n1 x n2) pixel-overlap confusion matrix between two label
    images, computed via a single bincount (GPU-accelerated when
    device == 'cuda')."""
    if device == 'cuda' and _HAS_TORCH and torch.cuda.is_available():
        tz = torch.as_tensor(lbl_z.ravel().astype(np.int64), device='cuda')
        tz1 = torch.as_tensor(lbl_z1.ravel().astype(np.int64), device='cuda')
        combined = tz * (n2 + 1) + tz1
        counts = torch.bincount(combined, minlength=(n1 + 1) * (n2 + 1))
        counts = counts.reshape(n1 + 1, n2 + 1)[1:, 1:]
        return counts.to('cpu').numpy()
    combined = lbl_z.ravel().astype(np.int64) * (n2 + 1) + lbl_z1.ravel().astype(np.int64)
    counts = np.bincount(combined, minlength=(n1 + 1) * (n2 + 1)).reshape(n1 + 1, n2 + 1)
    return counts[1:, 1:]


def match_slices(lbl_z, lbl_z1, props_z, props_z1, iou_threshold=0.1, device='cpu'):
    """Match instances at z to z+1 by 2D footprint IoU (same class only,
    since props_z/props_z1/lbl_z/lbl_z1 are already filtered to a single
    class by the caller). Every pair whose IoU clears `iou_threshold` is
    kept — matching is deliberately not constrained to 1-to-1, since a
    single parent instance legitimately matching multiple z+1 instances (or
    vice versa) is exactly the split/merge topology the graph needs to
    represent.

    Parameters
    ----------
    lbl_z, lbl_z1 : labeled 2D arrays for slice z and z+1 (from label_slices).
    device : 'cpu' or 'cuda' — where to compute the overlap matrix.

    Returns
    -------
    list of (local_id_z, local_id_z1, iou), sorted by descending iou.
    """
    if not props_z or not props_z1 or lbl_z is None or lbl_z1 is None:
        return []

    n1 = max(p['local_id'] for p in props_z)
    n2 = max(p['local_id'] for p in props_z1)
    overlap = _overlap_matrix(lbl_z, lbl_z1, n1, n2, device)

    areas_z = np.zeros(n1, dtype=np.float64)
    for p in props_z:
        areas_z[p['local_id'] - 1] = p['area']
    areas_z1 = np.zeros(n2, dtype=np.float64)
    for p in props_z1:
        areas_z1[p['local_id'] - 1] = p['area']

    union = areas_z[:, None] + areas_z1[None, :] - overlap
    with np.errstate(divide='ignore', invalid='ignore'):
        iou = np.where(union > 0, overlap / union, 0.0)

    ii, jj = np.nonzero((overlap > 0) & (iou >= iou_threshold))
    matches = [(int(i) + 1, int(j) + 1, float(iou[i, j])) for i, j in zip(ii, jj)]
    matches.sort(key=lambda t: t[2], reverse=True)
    return matches


def build_track_graph(volume, iou_threshold=0.1, device='auto'):
    """Run label_slices + match_slices across every consecutive z pair.

    Parameters
    ----------
    device : 'auto' (use CUDA if available, else CPU), 'cpu', or 'cuda'.

    Returns
    -------
    graph : dict[(z, cls, local_id)] -> dict[(z+1, cls, local_id')] -> iou
    props_by_zc : dict[(z, cls)] -> list of region-prop dicts (from label_slices)
    all_matches : dict[(z, cls)] -> list of (local_id_z, local_id_z1, iou), matches
        from slice z to z+1 for that class
    """
    if device == 'auto':
        device = default_device()

    props_by_zc, lbl_by_zc = label_slices(volume)
    nz = volume.shape[0]
    classes = sorted(set(c for (_, c) in props_by_zc.keys()))

    graph = {}
    all_matches = {}
    for z in range(nz - 1):
        for cls in classes:
            props_z = props_by_zc.get((z, cls), [])
            props_z1 = props_by_zc.get((z + 1, cls), [])
            for p in props_z:
                graph.setdefault((z, cls, p['local_id']), {})
            for p in props_z1:
                graph.setdefault((z + 1, cls, p['local_id']), {})
            matches = match_slices(
                lbl_by_zc.get((z, cls)), lbl_by_zc.get((z + 1, cls)),
                props_z, props_z1, iou_threshold, device,
            )
            all_matches[(z, cls)] = matches
            for id_z, id_z1, iou in matches:
                graph[(z, cls, id_z)][(z + 1, cls, id_z1)] = iou
    return graph, props_by_zc, all_matches


def assign_persistent_ids(graph):
    """Assign persistent (lineage) ids to graph nodes.

    A maximal chain of clean 1-to-1 matches keeps one persistent id.
    At a split (out-degree >= 2) or merge (in-degree >= 2), the incoming
    segment keeps its id up to and including the branch node, and each
    outgoing branch is assigned a brand-new id starting at the next node.

    Returns
    -------
    id_map : dict[(z, cls, local_id)] -> persistent_id (int, 1-based)
    lineage : list of dicts {label, class, z_start, z_end, parent_label}
    """
    all_nodes = set(graph.keys())
    for edges in graph.values():
        all_nodes.update(edges.keys())
    nodes = sorted(all_nodes)

    in_degree = {n: 0 for n in nodes}
    for n, edges in graph.items():
        for m in edges:
            in_degree[m] = in_degree.get(m, 0) + 1
    out_degree = {n: len(graph.get(n, {})) for n in nodes}

    id_map = {}
    lineage = []
    next_id = [1]

    def start_new_track(start_node, parent_label):
        pid = next_id[0]
        next_id[0] += 1
        z_start, cls, _ = start_node
        cur = start_node
        z_end = z_start
        while True:
            id_map[cur] = pid
            z_end = cur[0]
            out_edges = graph.get(cur, {})
            if out_degree[cur] != 1:
                break
            (nxt,) = list(out_edges.keys())
            if in_degree.get(nxt, 0) != 1:
                break  # nxt is a merge target; it starts its own track
            cur = nxt
        lineage.append({
            'label': pid, 'class': cls, 'z_start': z_start,
            'z_end': z_end, 'parent_label': parent_label,
        })
        return cur

    # Track roots: in-degree 0 (new appearance) or in-degree >= 2 (merge target),
    # visited in deterministic (z, cls, local_id) order for reproducibility.
    roots = [n for n in nodes if in_degree.get(n, 0) != 1]
    for root in roots:
        if root in id_map:
            continue
        end_node = start_new_track(root, parent_label=None)
        if out_degree.get(end_node, 0) >= 2:
            parent_pid = id_map[end_node]
            for child in sorted(graph[end_node].keys()):
                if child not in id_map:
                    start_new_track(child, parent_label=parent_pid)

    for n in nodes:
        if n not in id_map:
            start_new_track(n, parent_label=None)

    return id_map, lineage


def rasterize_instance_map(volume, id_map):
    """Build a volume of persistent-id labels (0 = background)."""
    max_id = max(id_map.values()) if id_map else 0
    dtype = np.uint16 if max_id <= 65535 else np.uint32
    out = np.zeros(volume.shape, dtype=dtype)

    classes = sorted(set(c for (_, c, _) in id_map.keys()))
    nz = volume.shape[0]
    for z in range(nz):
        for cls in classes:
            mask = volume[z] == cls
            if not mask.any():
                continue
            lbl = sk_label(mask, connectivity=2)
            local_ids = set(int(v) for v in np.unique(lbl) if v != 0)
            for local_id in local_ids:
                pid = id_map.get((z, cls, local_id))
                if pid is not None:
                    out[z][lbl == local_id] = pid
    return out
