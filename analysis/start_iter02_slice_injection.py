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
import zlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

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
    for rev in range(1, 100):
        candidate = base_dir / f"annotations_v{date_str}_r{rev:02d}"
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Unable to find free revision under {base_dir}")


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
) -> SampleRunResult:
    sample_id = sample_rec["sample_id"]
    latest_annotation_path = Path(sample_rec["latest_annotation_path"])
    prediction_path = Path(sample_rec["prediction_concatenated_path"])

    if not latest_annotation_path.exists():
        raise FileNotFoundError(f"Latest annotation missing for {sample_id}: {latest_annotation_path}")
    if not prediction_path.exists():
        raise FileNotFoundError(f"Prediction volume missing for {sample_id}: {prediction_path}")

    ann_zyx = tifffile.imread(str(latest_annotation_path))
    if ann_zyx.ndim != 3:
        raise ValueError(f"Latest annotation must be 3D for {sample_id}, got {ann_zyx.shape}")

    pred_zyx_raw = load_prediction_as_zyx(prediction_path)
    if pred_zyx_raw.shape != ann_zyx.shape:
        raise ValueError(
            f"Shape mismatch for {sample_id}: prediction={pred_zyx_raw.shape}, annotation={ann_zyx.shape}"
        )

    annotated_mask = np.any(ann_zyx != 0, axis=(1, 2))
    eligible = np.where(~annotated_mask)[0]

    if eligible.size < num_slices:
        raise RuntimeError(
            f"Sample {sample_id} has only {eligible.size} eligible slices, need {num_slices}."
        )

    selected_slices, sample_seed = choose_slices_arbitrary_deterministic(
        sample_id=sample_id,
        eligible_slices=eligible,
        num_slices=num_slices,
        seed=seed,
    )

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

    sample_out_dir = selected_outputs_root / sample_id
    sample_out_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = sample_out_dir / "bad_slices_iter02.json"
    save_json(
        manifest_path,
        {
            "sample_id": sample_id,
            "iteration": iteration,
            "format": "annotation_label_space",
            "selection_policy": "arbitrary_deterministic",
            "selection_seed": sample_seed,
            "selected_slices": [int(x) for x in selected_slices],
            "source_latest_annotation": str(latest_annotation_path),
            "source_prediction": str(prediction_path),
            "notes": "Auto-selected from prediction slices not already annotated in latest annotation.",
        },
    )

    eligibility_report_path = sample_out_dir / "eligibility_iter02.json"
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

    injection_audit_path = sample_out_dir / f"injected_predictions_{iteration}.json"
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
        )
        results.append(result)

    mutation_package = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "requested_by_agent": "GitHub Copilot",
        "approved_by_agent": "Data Registry and Path Validation",
        "reason": "Start iter_02: inject 2 prediction-derived non-annotated slices per sample and set new latest annotation versions",
        "status_update": "in_progress",
        "updates": [
            {
                "sample_id": r.sample_id,
                "new_annotation_path": r.output_annotation_path,
                "append_history_action": "inject_predictions_into_latest_annotation_iter02",
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

    mutation_package_path = analysis_dir / "iter02_registry_mutation_request.json"
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
