"""
Interactive 3D µCT preprocessing viewer.

Pipeline:
    slice folder → stack → norm200 → 3D filter → Napari

Usage:
    python preprocess_playground/run_napari_filters.py \
        --input_dir path/to/slices \
        --filter gaussian
"""

import argparse
import sys
from pathlib import Path

import napari

# Allow sibling imports when run from the repo root.
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from normalization import stack_slices_to_volume, norm200
from filters_3d import gaussian_filter_3d, median_filter_3d, non_local_means_3d

# Mapping from CLI names to filter functions.
FILTERS = {
    "gaussian": gaussian_filter_3d,
    "median": median_filter_3d,
    "nlm": non_local_means_3d,
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Load a µCT slice stack, normalise (norm200), "
        "apply a 3-D filter, and visualise in Napari."
    )
    parser.add_argument(
        "--input_dir",
        required=True,
        type=Path,
        help="Directory containing 2-D slice images (.tif / .tiff / .png).",
    )
    parser.add_argument(
        "--filter",
        default="gaussian",
        choices=list(FILTERS.keys()),
        dest="filter_name",
        help="3-D filter to apply after norm200 (default: gaussian).",
    )
    args = parser.parse_args()

    # 1. Stack slices → 3D volume
    raw_volume = stack_slices_to_volume(args.input_dir)

    # 2. Normalise (norm200)
    norm_volume = norm200(raw_volume)

    # 3. Apply selected filter
    filter_fn = FILTERS[args.filter_name]
    print(f"Applying filter: {args.filter_name} …")
    filtered_volume = filter_fn(norm_volume)
    print("Done.")

    # 4. Visualise in Napari
    viewer = napari.Viewer(title="µCT preprocessing playground")
    viewer.add_image(raw_volume, name="raw", visible=False)
    viewer.add_image(norm_volume, name="norm200", visible=False)
    viewer.add_image(filtered_volume, name=f"filtered ({args.filter_name})")
    napari.run()


if __name__ == "__main__":
    main()
