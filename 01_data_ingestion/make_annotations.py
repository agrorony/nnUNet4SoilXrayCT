import numpy as np
import tifffile as tiff
from skimage.filters import threshold_otsu
from skimage.draw import polygon2mask
import napari
import argparse
import json
from pathlib import Path
from qtpy.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton

def load_metadata(metadata_path):
    with open(metadata_path, "r") as f:
        metadata = json.load(f)
    return metadata

def load_image(input_path, sample_id):
    image_path = input_path / f'{sample_id}.tif'
    print(f"Loading {sample_id} from {image_path} ...")
    grayscale_data = tiff.imread(image_path)
    print(f"Loaded {sample_id}, shape: {grayscale_data.shape}")
    return grayscale_data

def load_annotations_from_file(annotation_file):
    print(f"Loading annotations from {annotation_file} ...")
    saved_annotations = tiff.imread(annotation_file)
    print(f"Loaded previously saved annotations from {annotation_file}")
    return saved_annotations

def load_annotations(output_path, sample_id):
    image_path_annotations = output_path / f'{sample_id}.tif'
    return load_annotations_from_file(image_path_annotations)

def apply_threshold(grayscale_data):
    middle_index = grayscale_data.shape[0] // 2 - 1
    middle_slice = grayscale_data[middle_index]
    otsu_thresh = threshold_otsu(grayscale_data)
    binary_middle_slice = ((middle_slice < 220) & (middle_slice > otsu_thresh)).astype(np.uint8)
    annotations = np.zeros_like(grayscale_data, dtype=np.uint8)
    annotations[middle_index] = binary_middle_slice
    return annotations

def normalize_colors(metadata):
    color_dict = {int(k): tuple(v) for k, v in metadata["colors"].items()}
    return {k: np.array(v) / 255 for k, v in color_dict.items()}

def apply_polygons_to_labels(labels_data, polygons_data, target_label):
    if target_label <= 0:
        print("Warning: selected label is 0. Label 0 is usually reserved for ignore/unannotated.")

    applied_count = 0
    z_dim, y_dim, x_dim = labels_data.shape

    for vertices in polygons_data:
        vertices = np.asarray(vertices, dtype=float)
        if vertices.ndim != 2 or vertices.shape[1] != 3:
            print("Skipping polygon: unsupported dimensionality. Draw polygons on 2D slices of the 3D volume.")
            continue

        z_coords = vertices[:, 0]
        z_index = int(np.rint(np.mean(z_coords)))

        if not np.allclose(z_coords, z_index, atol=1e-3):
            print("Skipping polygon: vertices are not on a single z-slice.")
            continue
        if z_index < 0 or z_index >= z_dim:
            print(f"Skipping polygon: z-index {z_index} is out of bounds for volume depth {z_dim}.")
            continue

        yx = vertices[:, 1:]
        mask = polygon2mask((y_dim, x_dim), yx)
        labels_data[z_index][mask] = np.uint8(target_label)
        applied_count += 1

    return applied_count

def build_polygon_controls(viewer, labels_layer, polygons_layer):
    container = QWidget()
    layout = QVBoxLayout(container)

    instructions = QLabel(
        "Draw polygons on a slice in 'Polygon tool',\n"
        "set the target class with Labels selected label,\n"
        "then click Apply."
    )
    status = QLabel("Ready")

    apply_button = QPushButton("Apply polygons to selected label")
    clear_button = QPushButton("Clear polygon layer")

    def _apply_polygons():
        target_label = int(labels_layer.selected_label)
        polygon_data = [np.array(p) for p in polygons_layer.data]
        count = apply_polygons_to_labels(labels_layer.data, polygon_data, target_label)

        if count == 0:
            status.setText("No polygons were applied.")
            return

        labels_layer.refresh()
        polygons_layer.data = []
        status.setText(f"Applied {count} polygon(s) as label {target_label}.")

    def _clear_polygons():
        polygons_layer.data = []
        status.setText("Polygon layer cleared.")

    apply_button.clicked.connect(_apply_polygons)
    clear_button.clicked.connect(_clear_polygons)

    layout.addWidget(instructions)
    layout.addWidget(apply_button)
    layout.addWidget(clear_button)
    layout.addWidget(status)

    viewer.window.add_dock_widget(container, area='right', name='Polygon annotation controls')

def visualize_data(grayscale_data, annotations, color_dict):
    viewer = napari.Viewer()
    viewer.add_image(grayscale_data, name='Grayscale data')
    labels_layer = viewer.add_labels(annotations, name="Annotations", opacity=1, blending='additive')
    # Set label colors after layer creation (napari 0.5.3 compatibility)
    labels_layer.color = color_dict
    polygons_layer = viewer.add_shapes(
        name='Polygon tool',
        ndim=3,
        shape_type='polygon',
        edge_color='yellow',
        face_color=[1.0, 1.0, 0.0, 0.2],
        opacity=1.0,
    )
    polygons_layer.mode = 'add_polygon'
    build_polygon_controls(viewer, labels_layer, polygons_layer)
    napari.run()
    return np.asarray(labels_layer.data, dtype=np.uint8)

def save_annotations(output_path, sample_id, annotations):
    output_path.mkdir(parents=True, exist_ok=True)
    output_file = output_path / f'{sample_id}.tif'
    tiff.imwrite(output_file, annotations.astype(np.uint8))
    print(f"Annotations saved to {output_file}")

def main():

    # Parsing arguments from command line
    parser = argparse.ArgumentParser(description='This is script to prepare ground truth annotations using Napari.')
    parser.add_argument('-i', type=Path, required=True, help='Path to the input directory')
    parser.add_argument('-o', type=Path, required=True, help='Path to save the output')
    parser.add_argument('-id', type=str, required=True, help='Sample ID')
    parser.add_argument('-a', '--annotations', type=Path, default=None, required=False, help='Optional explicit annotation file to preload')
    parser.add_argument('-write', type=str, default= 'yes', required=False, help='Whether to save annotations or not - Possible answers: yes, no - /!\ yes overwrites previous annotations - Default is yes')
    parser.add_argument('-v', action='store_true', help='Increase output verbosity')
    args = parser.parse_args()

    # loading grayscale data
    grayscale_data = load_image(args.i, args.id)

    # loading annotations: explicit file if provided, otherwise existing default behavior
    if args.annotations is not None:
        if not args.annotations.exists():
            raise FileNotFoundError(f'Explicit annotations file not found: {args.annotations}')
        annotations = load_annotations_from_file(args.annotations)
    elif (args.o / f'{args.id}.tif').exists():
        annotations = load_annotations(args.o, args.id)
    else:
        annotations = apply_threshold(grayscale_data)
    metadata = load_metadata(Path.cwd() / 'dataset_info.json')
    color_dict = normalize_colors(metadata)
    annotations = visualize_data(grayscale_data, annotations, color_dict)

    # saving annotations if user wants to
    if args.write == 'yes':
        save_annotations(args.o, args.id, annotations)
    elif args.write == 'no':   
        print("Newly made annotations (if they were any) were not saved")
    
if __name__ == "__main__":
    main()
