"""Napari review viewer for seg_plausibility output.

Loads instance_map.tif as a Labels layer and errors.json as a navigable list
of flagged objects/events. A small widget lets you step through flagged
entries (sorted by severity); each step jumps the Z slider to the entry's
slice and highlights the corresponding persistent object id.

Usage:
    python napari_review.py --results-dir <dir with instance_map.tif/errors.json/track_table.csv>
        [--original <raw grayscale volume for context>]
        [--prediction <raw class-prediction volume (nnUNet label space)>]
        [--dataset-info <dataset_info.json, for --prediction color mapping>]
        [--exclude-classes 5]     # default: hide the noisy Pore class
        [--min-severity 0.0]
"""
import argparse
import json
import os

import numpy as np
import pandas as pd
import tifffile


def load_zyx(path):
    lower = path.lower()
    if lower.endswith(('.tif', '.tiff')):
        return tifffile.imread(path)
    if lower.endswith(('.nii', '.nii.gz')):
        import nibabel as nib
        data = np.asarray(nib.load(path).dataobj)
        return np.transpose(data, (2, 1, 0))
    raise ValueError(f'Unsupported file type: {path}')


def reverse_nnunet_labels(prediction, ignore_label):
    """nnUNet training shifts original annotation label 0 -> ignore_label,
    then subtracts 1 from everything. Reverse it: ignore_label -> 0 (ToPredict),
    everything else += 1, to recover the original dataset_info.json label values."""
    remapped = prediction.copy()
    remapped[prediction == ignore_label] = 0
    mask = prediction < ignore_label
    remapped[mask] = prediction[mask] + 1
    return remapped


def build_color_dict(dataset_info_path):
    """Build a napari Labels `color` dict (label value -> RGBA 0-1) from
    dataset_info.json's colors, so classes render with the same colors used
    everywhere else in this project. Label 0 (ToPredict/background) is
    transparent."""
    with open(dataset_info_path) as fh:
        meta = json.load(fh)
    colors = meta['colors']
    color_dict = {None: np.array([0, 0, 0, 0], dtype=float)}
    for k, rgb in colors.items():
        label = int(k)
        if label == 0:
            color_dict[label] = np.array([0, 0, 0, 0], dtype=float)
        else:
            color_dict[label] = np.array([*(c / 255.0 for c in rgb), 1.0], dtype=float)
    return color_dict, {int(k): v for k, v in meta['labels'].items()}


def create_adjust_widget(viewer):
    """Per-layer flip and value-shift panel (same as microsam_3d's proofreader)."""
    from magicgui.widgets import Container, PushButton, ComboBox

    adj_combo = ComboBox(label='Layer', choices=lambda w: [l.name for l in viewer.layers] or [''])
    flip_z_btn = PushButton(text='Flip Z')
    flip_y_btn = PushButton(text='Flip Y')
    flip_x_btn = PushButton(text='Flip X')
    shift_p1_btn = PushButton(text='+1')
    shift_m1_btn = PushButton(text='-1')

    def _get_layer():
        name = adj_combo.value
        return viewer.layers[name] if name and name in viewer.layers else None

    @flip_z_btn.changed.connect
    def _on_flip_z(value=None):
        lyr = _get_layer()
        if lyr is None:
            return
        lyr.data = np.flip(lyr.data, axis=0)
        lyr.refresh()

    @flip_y_btn.changed.connect
    def _on_flip_y(value=None):
        lyr = _get_layer()
        if lyr is None:
            return
        lyr.data = np.flip(lyr.data, axis=1)
        lyr.refresh()

    @flip_x_btn.changed.connect
    def _on_flip_x(value=None):
        lyr = _get_layer()
        if lyr is None:
            return
        lyr.data = np.flip(lyr.data, axis=2)
        lyr.refresh()

    @shift_p1_btn.changed.connect
    def _on_shift_p1(value=None):
        lyr = _get_layer()
        if lyr is None:
            return
        lyr.data = lyr.data + 1
        lyr.refresh()

    @shift_m1_btn.changed.connect
    def _on_shift_m1(value=None):
        lyr = _get_layer()
        if lyr is None:
            return
        lyr.data = lyr.data - 1
        lyr.refresh()

    return Container(widgets=[adj_combo, flip_z_btn, flip_y_btn, flip_x_btn, shift_p1_btn, shift_m1_btn])


def load_entries(results_dir, exclude_classes, min_severity):
    with open(os.path.join(results_dir, 'errors.json')) as fh:
        errors = json.load(fh)
    track_df = pd.read_csv(os.path.join(results_dir, 'track_table.csv'))
    id_to_class = dict(zip(track_df['label'], track_df['class']))

    entries = []
    for e in errors:
        cls = id_to_class.get(e['object_id'])
        if cls in exclude_classes:
            continue
        if e['severity'] < min_severity:
            continue
        e = dict(e)
        e['class'] = cls
        entries.append(e)
    entries.sort(key=lambda e: e['severity'], reverse=True)
    return entries


def main():
    parser = argparse.ArgumentParser(description='Review seg_plausibility flagged objects in napari')
    parser.add_argument('--results-dir', required=True,
                         help='Directory containing instance_map.tif, errors.json, track_table.csv')
    parser.add_argument('--original', default=None,
                         help='Optional raw grayscale volume (.tif/.nii.gz) to show for context')
    parser.add_argument('--prediction', default=None,
                         help='Optional raw class-prediction volume (nnUNet label space, .tif/.nii.gz) '
                              'to show colored by class, so you can judge/fix the underlying segmentation')
    parser.add_argument('--dataset-info', default=None,
                         help='Path to dataset_info.json (for --prediction class colors/names). '
                              'Required if --prediction is given.')
    parser.add_argument('--ignore-label', type=int, default=6,
                         help='nnUNet ignore-label value in --prediction, reverse-mapped to class 0. Default: 6.')
    parser.add_argument('--exclude-classes', default='',
                         help="Comma-separated class values to hide from the review list (e.g. '5' for Pore)")
    parser.add_argument('--min-severity', type=float, default=0.0)
    args = parser.parse_args()

    exclude_classes = {int(c) for c in args.exclude_classes.split(',') if c.strip() != ''}

    entries = load_entries(args.results_dir, exclude_classes, args.min_severity)
    print(f'{len(entries)} flagged entries loaded '
          f'(excluded classes: {sorted(exclude_classes) or "none"}, min_severity={args.min_severity})')
    if not entries:
        print('Nothing to review with these filters.')
        return

    instance_map = tifffile.imread(os.path.join(args.results_dir, 'instance_map.tif'))

    import napari
    viewer = napari.Viewer(title='seg_plausibility review')

    if args.original:
        original = load_zyx(args.original)
        viewer.add_image(original, name='volume', colormap='gray', blending='translucent')

    if args.prediction:
        if not args.dataset_info:
            raise ValueError('--dataset-info is required when --prediction is given')
        prediction = load_zyx(args.prediction).astype(np.int32)
        color_dict, label_names = build_color_dict(args.dataset_info)
        prediction = reverse_nnunet_labels(prediction, args.ignore_label)
        from napari.utils.colormaps import DirectLabelColormap
        viewer.add_labels(
            prediction, name='prediction (classes)',
            colormap=DirectLabelColormap(color_dict=color_dict),
            opacity=1.0, blending='translucent',
        )
        print('Prediction classes: ' + ', '.join(f'{v}={k}' for k, v in label_names.items() if k != 0))

    # Fully opaque so instance colors read clearly instead of washing out
    # against the grayscale volume; show_selected_label isolates the
    # currently-flagged object from the rest once navigation starts.
    labels_layer = viewer.add_labels(
        instance_map, name='instance_map', opacity=1.0, blending='translucent',
    )

    state = {'i': 0}

    def show_current():
        e = entries[state['i']]
        z = e['z']
        viewer.dims.set_current_step(0, z)
        labels_layer.selected_label = int(e['object_id'])
        labels_layer.show_selected_label = True
        children = f" children={e['children']}" if e.get('children') else ''
        print(f"[{state['i'] + 1}/{len(entries)}] id={e['id']} z={z} "
              f"object_id={e['object_id']} class={e['class']} event={e['event']} "
              f"severity={e['severity']:.3f}{children} — {e['detail']}")

    from magicgui import magicgui
    from magicgui.widgets import Label

    @magicgui(call_button='Next flagged')
    def next_entry():
        state['i'] = min(state['i'] + 1, len(entries) - 1)
        show_current()

    @magicgui(call_button='Previous flagged')
    def prev_entry():
        state['i'] = max(state['i'] - 1, 0)
        show_current()

    viewer.window.add_dock_widget(next_entry, area='right', name='Next')
    viewer.window.add_dock_widget(prev_entry, area='right', name='Previous')

    # Live "labels present in this slice" readout — no need to hover the
    # paint brush over each blob just to learn its id.
    slice_labels_widget = Label(value='')

    def _update_slice_labels():
        z = int(viewer.dims.current_step[0])
        ids = np.unique(labels_layer.data[z])
        ids = ids[ids != 0]
        if ids.size == 0:
            slice_labels_widget.value = f'z={z}: no instance_map labels'
        elif ids.size <= 40:
            slice_labels_widget.value = f'z={z} ({ids.size} labels): ' + ', '.join(str(int(v)) for v in ids)
        else:
            slice_labels_widget.value = f'z={z}: {ids.size} labels (too many to list)'

    viewer.dims.events.current_step.connect(lambda event: _update_slice_labels())
    viewer.window.add_dock_widget(slice_labels_widget, area='right', name='Labels in slice')

    viewer.window.add_dock_widget(create_adjust_widget(viewer), area='right', name='Adjust')

    show_current()
    _update_slice_labels()
    print('Napari viewer open. Use the Next/Previous flagged buttons to step through issues. Close the window to exit.')
    napari.run()


if __name__ == '__main__':
    main()
