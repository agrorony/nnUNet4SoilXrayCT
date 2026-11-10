"""Open a single preprocessed (no prediction) volume in the micro-SAM napari viewer.

Usage:
    python view_preprocessed_volume_only.py --volume-path <path.tif> [--title TITLE]
"""
import argparse
import os
import sys

MICROSAM_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "05_evaluation", "microsam_3d")
sys.path.insert(0, MICROSAM_DIR)
os.chdir(MICROSAM_DIR)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--volume-path", required=True)
    parser.add_argument("--title", default=None)
    args = parser.parse_args()

    from run import main as microsam_main
    microsam_main(volume_path=args.volume_path, title=args.title, debug=True)


if __name__ == "__main__":
    main()
