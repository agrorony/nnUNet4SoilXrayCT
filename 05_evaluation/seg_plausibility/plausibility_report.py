"""Event detection, threshold-based flagging, and report export."""
import json
import pandas as pd


def detect_events(graph, id_map):
    """Classify each node's transition behavior from graph in/out-degree.

    Returns
    -------
    list of dicts: {z, object_id, event, children (split/merge only)}
    event in {'appear', 'disappear', 'split', 'merge'}.
    """
    all_nodes = set(graph.keys())
    for edges in graph.values():
        all_nodes.update(edges.keys())
    if not all_nodes:
        return []

    in_degree = {n: 0 for n in all_nodes}
    parents_of = {n: [] for n in all_nodes}
    for n, edges in graph.items():
        for m in edges:
            in_degree[m] += 1
            parents_of[m].append(n)
    out_degree = {n: len(graph.get(n, {})) for n in all_nodes}

    zs_by_class = {}
    for (z, cls, _) in all_nodes:
        lo, hi = zs_by_class.get(cls, (z, z))
        zs_by_class[cls] = (min(lo, z), max(hi, z))

    events = []
    for n in sorted(all_nodes):
        z, cls, _local_id = n
        pid = id_map[n]
        indeg = in_degree.get(n, 0)
        outdeg = out_degree.get(n, 0)
        z_lo, z_hi = zs_by_class[cls]

        if indeg == 0 and z > z_lo:
            events.append({'z': z, 'object_id': pid, 'event': 'appear'})
        if outdeg == 0 and z < z_hi:
            events.append({'z': z, 'object_id': pid, 'event': 'disappear'})
        if outdeg >= 2:
            children = sorted(id_map[m] for m in graph[n])
            events.append({'z': z, 'object_id': pid, 'event': 'split', 'children': children})
        if indeg >= 2:
            parents = sorted(id_map[p] for p in parents_of[n])
            events.append({'z': z, 'object_id': pid, 'event': 'merge', 'children': parents})
    return events


def _thresholds_for_class(thresholds, cls):
    if cls in thresholds:
        return thresholds[cls]
    if 'default' in thresholds:
        return thresholds['default']
    return thresholds


def flag_transitions(all_transition_metrics, thresholds):
    """Flag transitions violating thresholds (min_iou, min_area_ratio,
    max_area_ratio, max_centroid_jump). `thresholds` may be a flat dict or
    nested per class ({cls: {...}} with optional 'default' fallback).

    Each transition dict must carry: z, class, label_z, label_z1, iou,
    centroid_dist, area_ratio, eccentricity_delta.

    Returns
    -------
    list of dicts: {z, object_id, event, severity, detail}
    """
    is_nested = any(isinstance(v, dict) for v in thresholds.values())
    flagged = []

    for tm in all_transition_metrics:
        th = _thresholds_for_class(thresholds, tm.get('class')) if is_nested else thresholds

        min_iou = th.get('min_iou')
        min_ar = th.get('min_area_ratio')
        max_ar = th.get('max_area_ratio')
        max_jump = th.get('max_centroid_jump')

        if min_iou is not None and tm['iou'] < min_iou:
            severity = min(1.0, max(0.0, (min_iou - tm['iou']) / min_iou)) if min_iou > 0 else 1.0
            flagged.append({
                'z': tm['z'], 'object_id': tm['label_z'], 'event': 'low_iou',
                'severity': severity,
                'detail': f"IoU {tm['iou']:.2f} below min {min_iou:.2f}",
            })
        if min_ar is not None and tm['area_ratio'] < min_ar:
            severity = min(1.0, max(0.0, (min_ar - tm['area_ratio']) / min_ar)) if min_ar > 0 else 1.0
            flagged.append({
                'z': tm['z'], 'object_id': tm['label_z'], 'event': 'area_shrink',
                'severity': severity,
                'detail': f"area_ratio {tm['area_ratio']:.2f} below min {min_ar:.2f}",
            })
        if max_ar is not None and tm['area_ratio'] > max_ar:
            severity = min(1.0, max(0.0, (tm['area_ratio'] - max_ar) / max_ar)) if max_ar > 0 else 1.0
            flagged.append({
                'z': tm['z'], 'object_id': tm['label_z'], 'event': 'area_growth',
                'severity': severity,
                'detail': f"area_ratio {tm['area_ratio']:.2f} above max {max_ar:.2f}",
            })
        if max_jump is not None and tm['centroid_dist'] > max_jump:
            severity = min(1.0, max(0.0, (tm['centroid_dist'] - max_jump) / max_jump)) if max_jump > 0 else 1.0
            flagged.append({
                'z': tm['z'], 'object_id': tm['label_z'], 'event': 'centroid_jump',
                'severity': severity,
                'detail': f"centroid moved {tm['centroid_dist']:.1f}px, max {max_jump:.1f}",
            })
    return flagged


def build_track_table(lineage, aggregated_metrics):
    """Return a pandas.DataFrame: label, class, z_start, z_end, parent_label,
    worst_iou, max_centroid_jump, min_area_ratio, max_area_ratio."""
    rows = []
    for entry in lineage:
        pid = entry['label']
        agg = aggregated_metrics.get(pid, {})
        rows.append({
            'label': pid,
            'class': entry['class'],
            'z_start': entry['z_start'],
            'z_end': entry['z_end'],
            'parent_label': entry['parent_label'],
            'worst_iou': agg.get('worst_iou'),
            'max_centroid_jump': agg.get('max_centroid_jump'),
            'min_area_ratio': agg.get('min_area_ratio'),
            'max_area_ratio': agg.get('max_area_ratio'),
        })
    df = pd.DataFrame(rows, columns=[
        'label', 'class', 'z_start', 'z_end', 'parent_label',
        'worst_iou', 'max_centroid_jump', 'min_area_ratio', 'max_area_ratio',
    ])
    return df.sort_values('label').reset_index(drop=True)


def export_errors_json(events, flagged_transitions, path):
    """Merge events + flags into one list, sorted by severity descending,
    written to `path` as JSON matching the errors.json schema."""
    merged = []
    for e in events:
        merged.append({
            'object_id': e['object_id'],
            'z': e['z'],
            'event': e['event'],
            'severity': 1.0,
            'detail': _default_detail(e),
            'children': e.get('children'),
        })
    for f in flagged_transitions:
        merged.append({
            'object_id': f['object_id'],
            'z': f['z'],
            'event': f['event'],
            'severity': f['severity'],
            'detail': f['detail'],
            'children': None,
        })

    merged.sort(key=lambda d: d['severity'], reverse=True)

    out = []
    for i, m in enumerate(merged, start=1):
        entry = {
            'id': i,
            'z': m['z'],
            'object_id': m['object_id'],
            'event': m['event'],
            'severity': round(m['severity'], 4),
            'detail': m['detail'],
            'status': 'pending',
        }
        if m['children'] is not None:
            entry['children'] = m['children']
        out.append(entry)

    with open(path, 'w') as fh:
        json.dump(out, fh, indent=2)
    return out


def _default_detail(event):
    ev = event['event']
    if ev == 'appear':
        return f"object {event['object_id']} appears with no predecessor at z={event['z']}"
    if ev == 'disappear':
        return f"object {event['object_id']} disappears with no successor at z={event['z']}"
    if ev == 'split':
        return f"object {event['object_id']} splits into {event['children']} at z={event['z']}"
    if ev == 'merge':
        return f"objects {event['children']} merge into {event['object_id']} at z={event['z']}"
    return ev


def export_track_table_csv(df, path):
    df.to_csv(path, index=False)
