#!/usr/bin/env python
"""
Start iter_02 by selecting 2 prediction slices per sample that are not already
annotated in the latest annotation, then inject them into new annotation versions.

This script intentionally does not mutate analysis/data_registry.json directly.
It writes a mutation package for the Data Registry and Path Validation agent.
"""

from __future__ import annotations

import argparse
import json
import os
import zlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import nibabel as nib
import numpy as np
import tifffile


@dataclass
class SampleRunResult:
    sample_id: str
    latest_annotation_path: str
    prediction_path: str
    selected_slices: List[int]
    output_annotation_path: str
    manifest_path: str
    injection_audit_path: str
    eligibility_report_path: str
    sample_seed: int
    total_slices: int
    annotated_slices: int
    eligible_slices: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start iter_02 slice injection workflow.")
    parser.add_argument(
        "--repo_dir",
        type=Path,
        default=Path.cwd(),
        help="Repository root containing analysis/data_registry.json.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=20260602,
        help="Base deterministic seed for arbitrary slice selection.",
    )
    parser.add_argument(
        "--num_slices",
        type=int,
        default=2,
        help="Number of slices to select per sample.",
    )
    parser.add_argument(
        "--iteration",
        type=str,
        default="iter_02",
        help="Iteration label to write in output manifests.",
    )
    parser.add_argument(
        "--reuse_existing_selection",
        action="store_true",
        help="Reuse selected_slices from an existing bad_slices_<iteration>.json manifest if present.",
    )
    parser.add_argument(
        "--output_tag",
        type=str,
        default="",
        help="Optional suffix for corrected output artifacts, for example corrected_latest_predictions.",
    )
    parser.add_argument(
        "--flip_y_samples",
        type=str,
        default="nlm_volume",
        help="Comma-separated sample IDs whose prediction volumes should be flipped on axis 1 (Y) before injection.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def load_prediction_as_zyx(path: Path) -> np.ndarray:
    suffix = "".join(path.suffixes).lower()
    if suffix.endswith(".nii") or suffix.endswith(".nii.gz"):
        arr = nib.load(str(path)).get_fdata()
        if arr.ndim != 3:
            raise ValueError(f"Prediction must be 3D, got {arr.shape} for {path}")
        return np.asarray(arr.transpose(2, 1, 0), dtype=np.int32)

    if suffix.endswith(".tif") or suffix.endswith(".tiff"):
        arr = tifffile.imread(str(path))
        if arr.ndim != 3:
            raise ValueError(f"Prediction must be 3D, got {arr.shape} for {path}")
        return np.asarray(arr, dtype=np.int32)

    raise ValueError(f"Unsupported prediction format: {path}")


def remap_prediction_to_annotation_labels(pred_zyx: np.ndarray, num_annotation_labels: int) -> np.ndarray:
    ignore_label = num_annotation_labels - 1
    ann = pred_zyx + 1
    ann[pred_zyx == ignore_label] = 0
    ann = np.clip(ann, 0, num_annotation_labels - 1)
    return ann.astype(np.uint8)


def next_version_dir(base_dir: Path, date_str: str) -> Path:
    prefix = f"annotations_v{date_str}_r"
    max_rev = 0
    if base_dir.exists():
        for child in base_dir.iterdir():
            if not child.is_dir() or not child.name.startswith(prefix):
                continue
            suffix = child.name[len(prefix):]
            if suffix.isdigit():
                max_rev = max(max_rev, int(suffix))

    next_rev = max_rev + 1
    if next_rev > 99:
        raise RuntimeError(f"Unable to allocate revision under {base_dir}: next_rev={next_rev}")
    return base_dir / f"annotations_v{date_str}_r{next_rev:02d}"


def resolve_freshest_prediction_path(configured_prediction_path: Path, sample_id: str) -> Path:
    prediction_name = configured_prediction_path.name
    configured_parent = configured_prediction_path.parent
    base_dir_name = configured_parent.name
    sibling_root = configured_parent.parent

    candidates: List[Path] = []
    direct_candidate = configured_parent / prediction_name
    if direct_candidate.exists():
        candidates.append(direct_candidate)

    for sibling in sibling_root.iterdir():
        if not sibling.is_dir():
            continue
        if sibling.name == base_dir_name or sibling.name.startswith(f"{base_dir_name}_"):
            candidate = sibling / prediction_name
            if candidate.exists():
                candidates.append(candidate)

    if not candidates:
        raise FileNotFoundError(
            f"No prediction volume found for {sample_id} near {configured_prediction_path}"
        )

    return max(candidates, key=lambda path: path.stat().st_mtime)


def build_artifact_name(prefix: str, iteration: str, output_tag: str, extension: str) -> str:
    tag_suffix = f"_{output_tag}" if output_tag else ""
    return f"{prefix}_{iteration}{tag_suffix}.{extension}"


def build_legacy_artifact_name(prefix: str, iteration: str, extension: str) -> str:
    normalized_iteration = iteration.replace("_", "")
    return f"{prefix}_{normalized_iteration}.{extension}"


def load_existing_selected_slices(
    sample_out_dir: Path,
    iteration: str,
    expected_num_slices: int,
    output_tag: str,
) -> Optional[List[int]]:
    candidate_names = [
        build_artifact_name("bad_slices", iteration, "", "json"),
        build_legacy_artifact_name("bad_slices", iteration, "json"),
        build_artifact_name("bad_slices", iteration, output_tag, "json"),
    ]
    for name in candidate_names:
        manifest_path = sample_out_dir / name
        if not manifest_path.exists():
            continue
        payload = load_json(manifest_path)
        selected_slices = payload.get("selected_slices", [])
        if len(selected_slices) != expected_num_slices:
            raise ValueError(
                f"Existing manifest {manifest_path} does not contain exactly {expected_num_slices} slices"
            )
        return [int(x) for x in selected_slices]
    return None


def choose_slices_arbitrary_deterministic(sample_id: str, eligible_slices: np.ndarray, num_slices: int, seed: int) -> Tuple[List[int], int]:
    sample_seed = (zlib.crc32(sample_id.encode("utf-8")) + int(seed)) % (2**32)
    rng = np.random.default_rng(sample_seed)
    selected = np.sort(rng.choice(eligible_slices, size=num_slices, replace=False)).astype(int).tolist()
    return selected, int(sample_seed)


def process_sample(
    sample_rec: dict,
    selected_outputs_root: Path,
    date_str: str,
    iteration: str,
    seed: int,
    num_slices: int,
    num_annotation_labels: int,
    reuse_existing_selection: bool,
    output_tag: str,
    flip_y_samples: set[str],
) -> SampleRunResult:
    sample_id = sample_rec["sample_id"]
    latest_annotation_path = Path(sample_rec["latest_annotation_path"])
    configured_prediction_path = Path(sample_rec["prediction_concatenated_path"])
    prediction_path = resolve_freshest_prediction_path(configured_prediction_path, sample_id)

    if not latest_annotation_path.exists():
        raise FileNotFoundError(f"Latest annotation missing for {sample_id}: {latest_annotation_path}")
    if not prediction_path.exists():
        raise FileNotFoundError(f"Prediction volume missing for {sample_id}: {prediction_path}")

    ann_zyx = tifffile.imread(str(latest_annotation_path))
    if ann_zyx.ndim != 3:
        raise ValueError(f"Latest annotation must be 3D for {sample_id}, got {ann_zyx.shape}")

    pred_zyx_raw = load_prediction_as_zyx(prediction_path)
    if sample_id in flip_y_samples:
        pred_zyx_raw = np.flip(pred_zyx_raw, axis=1)
    if pred_zyx_raw.shape != ann_zyx.shape:
        raise ValueError(
            f"Shape mismatch for {sample_id}: prediction={pred_zyx_raw.shape}, annotation={ann_zyx.shape}"
        )

    annotated_mask = np.any(ann_zyx != 0, axis=(1, 2))
    eligible = np.where(~annotated_mask)[0]

    sample_out_dir = selected_outputs_root / sample_id
    sample_out_dir.mkdir(parents=True, exist_ok=True)

    selected_slices: Optional[List[int]] = None
    sample_seed = (zlib.crc32(sample_id.encode("utf-8")) + int(seed)) % (2**32)
    if reuse_existing_selection:
        selected_slices = load_existing_selected_slices(
            sample_out_dir=sample_out_dir,
            iteration=iteration,
            expected_num_slices=num_slices,
            output_tag=output_tag,
        )

    if selected_slices is None and eligible.size < num_slices:
        raise RuntimeError(
            f"Sample {sample_id} has only {eligible.size} eligible slices, need {num_slices}."
        )

    if selected_slices is None:
        selected_slices, sample_seed = choose_slices_arbitrary_deterministic(
            sample_id=sample_id,
            eligible_slices=eligible,
            num_slices=num_slices,
            seed=seed,
        )

    if any(z < 0 or z >= ann_zyx.shape[0] for z in selected_slices):
        raise ValueError(f"Selected slices out of bounds for {sample_id}: {selected_slices}")

    pred_zyx_ann = remap_prediction_to_annotation_labels(pred_zyx_raw, num_annotation_labels)
    output_zyx = ann_zyx.astype(np.uint8).copy()

    injected_slices = []
    for z in selected_slices:
        pred_slice = pred_zyx_raw[z].astype(np.int32)
        mapped_slice = pred_zyx_ann[z].astype(np.uint8)
        output_zyx[z] = mapped_slice
        injected_slices.append(
            {
                "slice_index": int(z),
                "pred_unique": sorted(np.unique(pred_slice).astype(int).tolist()),
                "converted_unique": sorted(np.unique(mapped_slice).astype(int).tolist()),
            }
        )

    latest_parent = latest_annotation_path.parent
    base_dir = latest_parent.parent
    out_version_dir = next_version_dir(base_dir, date_str)
    out_version_dir.mkdir(parents=True, exist_ok=True)
    out_annotation_path = out_version_dir / f"{sample_id}.tif"

    tifffile.imwrite(str(out_annotation_path), output_zyx.astype(np.uint8))

    manifest_path = sample_out_dir / build_artifact_name("bad_slices", iteration, output_tag, "json")
    save_json(
        manifest_path,
        {
            "sample_id": sample_id,
            "iteration": iteration,
            "format": "annotation_label_space",
            "selection_policy": "reuse_existing_selection" if reuse_existing_selection else "arbitrary_deterministic",
            "selection_seed": sample_seed,
            "selected_slices": [int(x) for x in selected_slices],
            "source_latest_annotation": str(latest_annotation_path),
            "source_prediction": str(prediction_path),
            "notes": (
                "Reused existing slice indices and refreshed them from the newest available concatenated prediction."
                if reuse_existing_selection
                else "Auto-selected from prediction slices not already annotated in latest annotation."
            ),
        },
    )

    eligibility_report_path = sample_out_dir / build_artifact_name("eligibility", iteration, output_tag, "json")
    save_json(
        eligibility_report_path,
        {
            "sample_id": sample_id,
            "total_slices": int(ann_zyx.shape[0]),
            "annotated_slices": int(np.count_nonzero(annotated_mask)),
            "eligible_slices": int(eligible.size),
            "exclusion_rule": "exclude any Z with at least one non-zero voxel in latest annotation",
            "selected_slices": [int(x) for x in selected_slices],
        },
    )

    injection_audit_path = sample_out_dir / build_artifact_name("injected_predictions", iteration, output_tag, "json")
    save_json(
        injection_audit_path,
        {
            "sample_id": sample_id,
            "source_annotation": str(latest_annotation_path),
            "source_prediction": str(prediction_path),
            "output_annotation": str(out_annotation_path),
            "injected_slices": injected_slices,
            "num_injected_slices": len(injected_slices),
        },
    )

    return SampleRunResult(
        sample_id=sample_id,
        latest_annotation_path=str(latest_annotation_path),
        prediction_path=str(prediction_path),
        selected_slices=[int(x) for x in selected_slices],
        output_annotation_path=str(out_annotation_path),
        manifest_path=str(manifest_path),
        injection_audit_path=str(injection_audit_path),
        eligibility_report_path=str(eligibility_report_path),
        sample_seed=sample_seed,
        total_slices=int(ann_zyx.shape[0]),
        annotated_slices=int(np.count_nonzero(annotated_mask)),
        eligible_slices=int(eligible.size),
    )


def main() -> int:
    args = parse_args()

    repo_dir = args.repo_dir.resolve()
    analysis_dir = repo_dir / "analysis"
    registry_path = analysis_dir / "data_registry.json"
    dataset_info_path = repo_dir / "dataset_info.json"
    selected_outputs_root = analysis_dir / "selected_outputs"

    if not registry_path.exists():
        raise FileNotFoundError(f"Missing registry: {registry_path}")
    if not dataset_info_path.exists():
        raise FileNotFoundError(f"Missing dataset info: {dataset_info_path}")

    registry = load_json(registry_path)
    dataset_info = load_json(dataset_info_path)

    labels = dataset_info.get("labels", {})
    if not isinstance(labels, dict) or len(labels) < 2:
        raise ValueError("dataset_info.json labels must be a non-empty dict")
    num_annotation_labels = len(labels)

    samples = registry.get("samples", [])
    if not isinstance(samples, list) or not samples:
        raise ValueError("No samples found in data_registry.json")

    flip_y_samples = {
        item.strip()
        for item in args.flip_y_samples.split(",")
        if item.strip()
    }

    date_str = datetime.now().strftime("%Y%m%d")
    results: List[SampleRunResult] = []

    for sample_rec in samples:
        sample_id = sample_rec.get("sample_id", "")
        if not sample_id:
            continue
        result = process_sample(
            sample_rec=sample_rec,
            selected_outputs_root=selected_outputs_root,
            date_str=date_str,
            iteration=args.iteration,
            seed=args.seed,
            num_slices=args.num_slices,
            num_annotation_labels=num_annotation_labels,
            reuse_existing_selection=args.reuse_existing_selection,
            output_tag=args.output_tag,
            flip_y_samples=flip_y_samples,
        )
        results.append(result)

    mutation_package = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "requested_by_agent": "GitHub Copilot",
        "approved_by_agent": "Data Registry and Path Validation",
        "reason": (
            "Correct iter_02 by refreshing injected slices from the newest available concatenated predictions"
            if args.reuse_existing_selection and args.output_tag
            else "Start iter_02: inject 2 prediction-derived non-annotated slices per sample and set new latest annotation versions"
        ),
        "status_update": "in_progress",
        "updates": [
            {
                "sample_id": r.sample_id,
                "new_annotation_path": r.output_annotation_path,
                "append_history_action": (
                    f"inject_predictions_into_latest_annotation_{args.iteration}_{args.output_tag}"
                    if args.output_tag
                    else "inject_predictions_into_latest_annotation_iter02"
                ),
                "decision": "GREEN",
                "paths_touched": [
                    r.latest_annotation_path,
                    r.prediction_path,
                    r.output_annotation_path,
                    r.manifest_path,
                    r.injection_audit_path,
                ],
                "bad_slice_manifest_path": r.manifest_path,
            }
            for r in results
        ],
        "summary": [
            {
                "sample_id": r.sample_id,
                "selected_slices": r.selected_slices,
                "selection_seed": r.sample_seed,
                "total_slices": r.total_slices,
                "annotated_slices": r.annotated_slices,
                "eligible_slices": r.eligible_slices,
                "output_annotation_path": r.output_annotation_path,
            }
            for r in results
        ],
    }

    mutation_package_name = (
        f"{args.iteration}_registry_mutation_request_{args.output_tag}.json"
        if args.output_tag
        else f"{args.iteration}_registry_mutation_request.json"
    )
    mutation_package_path = analysis_dir / mutation_package_name
    save_json(mutation_package_path, mutation_package)

    print("Iter_02 slice injection prepared.")
    print(f"Mutation package: {mutation_package_path}")
    for r in results:
        print(
            f"- {r.sample_id}: selected={r.selected_slices}, "
            f"output={r.output_annotation_path}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
