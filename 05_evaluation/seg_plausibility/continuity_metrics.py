"""Per-transition and per-track continuity metrics."""
import math


def compute_transition_metrics(props_z, props_z1, matches):
    """Per match: IoU (already known), centroid Euclidean distance,
    area_ratio = area(z+1)/area(z), eccentricity_delta.

    Returns
    -------
    list of dicts: {local_id_z, local_id_z1, iou, centroid_dist, area_ratio,
    eccentricity_delta}
    """
    by_id_z = {p['local_id']: p for p in props_z}
    by_id_z1 = {p['local_id']: p for p in props_z1}

    results = []
    for local_id_z, local_id_z1, iou in matches:
        pz = by_id_z[local_id_z]
        pz1 = by_id_z1[local_id_z1]
        cz = pz['centroid']
        cz1 = pz1['centroid']
        centroid_dist = math.hypot(cz1[0] - cz[0], cz1[1] - cz[1])
        area_ratio = pz1['area'] / pz['area'] if pz['area'] > 0 else float('inf')
        eccentricity_delta = pz1['eccentricity'] - pz['eccentricity']
        results.append({
            'local_id_z': local_id_z,
            'local_id_z1': local_id_z1,
            'iou': iou,
            'centroid_dist': centroid_dist,
            'area_ratio': area_ratio,
            'eccentricity_delta': eccentricity_delta,
        })
    return results


def aggregate_track_metrics(lineage, all_transition_metrics):
    """Per persistent id: worst IoU, max centroid jump, min/max area ratio
    across its lifespan.

    Parameters
    ----------
    lineage : list of dicts with 'label' (persistent id).
    all_transition_metrics : list of dicts, each must additionally carry
        'label_z' and 'label_z1' (persistent ids on either side of the
        transition) alongside the compute_transition_metrics fields.

    Returns
    -------
    dict[persistent_id] -> {worst_iou, max_centroid_jump, min_area_ratio, max_area_ratio}
    """
    agg = {
        entry['label']: {
            'worst_iou': None,
            'max_centroid_jump': None,
            'min_area_ratio': None,
            'max_area_ratio': None,
        }
        for entry in lineage
    }

    for tm in all_transition_metrics:
        for pid in {tm.get('label_z'), tm.get('label_z1')}:
            if pid is None or pid not in agg:
                continue
            a = agg[pid]
            a['worst_iou'] = tm['iou'] if a['worst_iou'] is None else min(a['worst_iou'], tm['iou'])
            a['max_centroid_jump'] = tm['centroid_dist'] if a['max_centroid_jump'] is None else max(a['max_centroid_jump'], tm['centroid_dist'])
            a['min_area_ratio'] = tm['area_ratio'] if a['min_area_ratio'] is None else min(a['min_area_ratio'], tm['area_ratio'])
            a['max_area_ratio'] = tm['area_ratio'] if a['max_area_ratio'] is None else max(a['max_area_ratio'], tm['area_ratio'])

    return agg
