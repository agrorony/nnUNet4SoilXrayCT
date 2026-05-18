"""Merge sparse 3D annotation stacks from two folders into one output folder.

The script is designed for the nnUNet workflow in this repository:
- input annotations are 3D TIFF stacks with shape (Z, Y, X)
- label 0 means ignore / unannotated
- non-zero labels from the two sources are combined voxel-wise

If both inputs annotate the same voxel with different non-zero labels, the
default behavior is to keep the value from the second input folder and report a
warning. This keeps the merge predictable while still allowing you to inspect
conflicts before training.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Sequence, Tuple

import numpy as np
import tifffile


TIFF_SUFFIXES = {".tif", ".tiff"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge 3D TIFF annotation stacks from two folders into one output folder."
    )
    parser.add_argument(
        "--input_a",
        type=Path,
        required=True,
        help="Folder containing the first set of annotations.",
    )
    parser.add_argument(
        "--input_b",
        type=Path,
        required=True,
        help="Folder containing the second set of annotations.",
    )
    parser.add_argument(
        "--output_dir",
        type=Path,
        required=True,
        help="Folder where merged annotation stacks will be written.",
    )
    parser.add_argument(
        "--volume_name",
        action="append",
        default=None,
        help=(
            "Optional explicit TIFF filename to merge. Repeat this flag to merge multiple volumes. "
            "If omitted, the script merges all common TIFF filenames between both folders."
        ),
    )
    parser.add_argument(
        "--conflict_policy",
        choices=["prefer_second", "prefer_first", "max", "error"],
        default="prefer_second",
        help=(
            "How to resolve voxels where both inputs contain different non-zero labels. "
            "Default: prefer_second."
        ),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing merged files in the output folder.",
    )
    return parser.parse_args()


def list_tiff_files(folder: Path) -> List[Path]:
    return sorted(
        [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in TIFF_SUFFIXES]
    )


def load_annotation_stack(path: Path) -> np.ndarray:
    stack = tifffile.imread(str(path))
    if stack.ndim != 3:
        raise ValueError(f"Expected a 3D TIFF stack in {path}, got shape {stack.shape}")
    return np.asarray(stack)


def merge_two_stacks(
    stack_a: np.ndarray,
    stack_b: np.ndarray,
    conflict_policy: str,
) -> Tuple[np.ndarray, int, int, int, int]:
    if stack_a.shape != stack_b.shape:
        raise ValueError(
            f"Annotation volumes must have the same shape, got {stack_a.shape} and {stack_b.shape}"
        )

    merged = np.array(stack_a, copy=True)

    a_nonzero = stack_a != 0
    b_nonzero = stack_b != 0
    b_only = b_nonzero & ~a_nonzero
    merged[b_only] = stack_b[b_only]

    overlap = a_nonzero & b_nonzero
    same_label = overlap & (stack_a == stack_b)
    conflicts = overlap & (stack_a != stack_b)

    if np.any(conflicts):
        if conflict_policy == "error":
            conflict_count = int(np.count_nonzero(conflicts))
            example_indices = np.argwhere(conflicts)[:5].tolist()
            raise ValueError(
                "Conflicting non-zero labels found while merging annotations: "
                f"{conflict_count} voxel(s) differ. Examples: {example_indices}"
            )
        if conflict_policy == "prefer_second":
            merged[conflicts] = stack_b[conflicts]
        elif conflict_policy == "prefer_first":
            pass
        elif conflict_policy == "max":
            merged[conflicts] = np.maximum(stack_a[conflicts], stack_b[conflicts])
        else:
            raise ValueError(f"Unknown conflict policy: {conflict_policy}")

    zero_a = int(np.count_nonzero(stack_a == 0))
    zero_b = int(np.count_nonzero(stack_b == 0))
    return (
        merged.astype(np.uint8, copy=False),
        zero_a,
        zero_b,
        int(np.count_nonzero(conflicts)),
        int(np.count_nonzero(same_label)),
    )


def resolve_volumes_to_merge(input_a: Path, input_b: Path, requested: Sequence[str] | None) -> List[str]:
    files_a = {p.name for p in list_tiff_files(input_a)}
    files_b = {p.name for p in list_tiff_files(input_b)}

    if requested:
        missing = [name for name in requested if name not in files_a or name not in files_b]
        if missing:
            raise FileNotFoundError(
                f"Requested volume(s) not found in both folders: {', '.join(missing)}"
            )
        return list(requested)

    common = sorted(files_a & files_b)
    if not common:
        raise FileNotFoundError(
            f"No common TIFF filenames found between {input_a} and {input_b}"
        )
    return common


def merge_folders(
    input_a: Path,
    input_b: Path,
    output_dir: Path,
    volume_names: Sequence[str] | None,
    conflict_policy: str,
    overwrite: bool,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    volumes_to_merge = resolve_volumes_to_merge(input_a, input_b, volume_names)

    for volume_name in volumes_to_merge:
        path_a = input_a / volume_name
        path_b = input_b / volume_name
        output_path = output_dir / volume_name

        if output_path.exists() and not overwrite:
            raise FileExistsError(
                f"Output file already exists: {output_path}. Use --overwrite to replace it."
            )

        stack_a = load_annotation_stack(path_a)
        stack_b = load_annotation_stack(path_b)
        merged, zero_a, zero_b, conflict_count, same_label_count = merge_two_stacks(
            stack_a, stack_b, conflict_policy
        )

        tifffile.imwrite(str(output_path), merged)
        print(
            f"Merged {volume_name}: shape={merged.shape}, "
            f"zeros_a={zero_a}, zeros_b={zero_b}, same_label_overlap={same_label_count}, "
            f"conflicts={conflict_count}, written={output_path}"
        )


def main() -> None:
    args = parse_args()
    merge_folders(
        input_a=args.input_a,
        input_b=args.input_b,
        output_dir=args.output_dir,
        volume_names=args.volume_name,
        conflict_policy=args.conflict_policy,
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    main()