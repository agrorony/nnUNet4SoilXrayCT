# seg_plausibility

Standalone, fully-automatic checker for whether a 3D label volume (e.g. an
nnUNet prediction) is physically plausible across Z: objects shouldn't
appear, vanish, jump, or change shape faster than physically possible
between adjacent slices.

CPU-only. No GPU, no SAM, no napari, no human interaction — this module only
produces files. A separate napari review plugin (not part of this module)
consumes its output.

## Pipeline

1. `instance_matcher.label_slices` — per Z slice, per class, connected-component
   label + region props (bbox, area, centroid, eccentricity).
2. `instance_matcher.build_track_graph` — greedy IoU-matches instances between
   every consecutive slice pair (same class only) into a directed graph.
3. `instance_matcher.assign_persistent_ids` — walks the graph; a clean 1-to-1
   chain keeps one persistent id. At a split or merge, the incoming segment
   keeps its id and each outgoing branch gets a new id (ISBI Cell Tracking
   Challenge `res_track.txt` convention).
4. `instance_matcher.rasterize_instance_map` — paints persistent ids back into
   a volume.
5. `continuity_metrics` — per-transition IoU/centroid-distance/area-ratio/
   eccentricity-delta, aggregated to per-track worst-case stats.
6. `plausibility_report` — classifies topological events (appear/disappear/
   split/merge) from graph degree, flags transitions that violate
   `thresholds.yaml`, and exports `track_table.csv` + `errors.json`.

## Usage

```bash
conda env create -f environment.yml
conda activate segplaus

# optional: derive thresholds from known-good volumes
python calibrate.py trusted1.tif trusted2.tif --out thresholds.yaml

# run the checker
python run.py labels.tif --thresholds thresholds.yaml --out-dir results/
```

If `--thresholds` is omitted, built-in defaults are used (a warning is
printed). Input may be `.tif`/`.tiff` or `.nii`/`.nii.gz` (NIfTI volumes are
assumed stored as X,Y,Z and are transposed to Z,Y,X internally, since the
pipeline iterates slices along axis 0).

## Output files

### `instance_map.tif`

Same shape as the input volume, dtype `uint16` (or `uint32` if more than
65535 persistent ids exist). Voxel value = persistent instance id (0 =
background). Intended to be loaded as a **napari Labels layer** by the
downstream review plugin.

### `track_table.csv`

One row per persistent track:

| column            | meaning                                              |
|-------------------|-------------------------------------------------------|
| `label`           | persistent id                                          |
| `class`           | class value                                            |
| `z_start`         | first Z slice the track appears in                     |
| `z_end`           | last Z slice the track appears in                      |
| `parent_label`    | id of the track it split from, or empty if none        |
| `worst_iou`       | minimum IoU across the track's transitions             |
| `max_centroid_jump` | maximum centroid displacement (px) across transitions |
| `min_area_ratio`  | minimum area(z+1)/area(z) across transitions           |
| `max_area_ratio`  | maximum area(z+1)/area(z) across transitions           |

### `errors.json`

A list of flagged issues, sorted by `severity` descending. Schema (must match
exactly):

```json
[
  {
    "id": 1,
    "z": 132,
    "object_id": 47,
    "event": "split",
    "children": [48, 49],
    "severity": 0.82,
    "detail": "IoU 0.31 at split boundary",
    "status": "pending"
  }
]
```

- `event` is one of the topological events `appear`, `disappear`, `split`,
  `merge`, or a threshold-violation flag `low_iou`, `area_shrink`,
  `area_growth`, `centroid_jump`.
- `children` is present only for `split` (new branch ids) and `merge`
  (ids of the tracks that merged in); continue-type flags (bad IoU / area
  ratio / centroid jump on an ordinary 1-to-1 transition) omit it.
- `status` starts as `"pending"` for every entry — the downstream napari
  review plugin is expected to update it in place as issues are triaged.

The downstream napari plugin (not built here) is expected to load
`instance_map.tif` as a Labels layer and use each `errors.json` entry to jump
the viewer to `z` and set `selected_label = object_id` (with
`show_selected_label = True`).

## Thresholds

`thresholds.yaml` may be flat:

```yaml
min_iou: 0.3
min_area_ratio: 0.5
max_area_ratio: 2.0
max_centroid_jump: 15.0
```

or nested per class (with optional `default` fallback for classes not
listed):

```yaml
default:
  min_iou: 0.3
  min_area_ratio: 0.5
  max_area_ratio: 2.0
  max_centroid_jump: 15.0
1:
  min_iou: 0.4
  max_centroid_jump: 10.0
```

`calibrate.py` writes the nested-per-class form using the 5th/95th
percentiles pooled from the trusted volumes you pass it.

## Self-test

```bash
python dev/_make_synthetic.py
python dev/_test_pipeline.py
```

`_make_synthetic.py` builds a small synthetic label volume with a clean
continuous object, a disappearing object, a splitting object, and an object
that jumps position implausibly. `_test_pipeline.py` runs the full `run.py`
pipeline on it and asserts each of those shows up correctly in the outputs.
