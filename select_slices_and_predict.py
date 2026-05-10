#!/usr/bin/env python
"""
Select representative slices from a 3D volume and run nnUNet prediction on them.

Main workflow:
1) Load a 3D volume (.tif or .nii/.nii.gz)
2) Compute per-slice metrics (variance + foreground fraction)
3) Select informative slices with spacing constraints
4) Optionally run nnUNetv2_predict on selected slices only
5) Save selected images, predictions, and metadata
"""

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import nibabel as nib
import numpy as np
import tifffile
from skimage.filters import threshold_otsu


@dataclass
class SliceMetric:
    slice_idx: int
    variance: float
    foreground_fraction: float
    score: float
    is_informative: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Select representative slices from a 3D volume and run nnUNet prediction."
    )
    parser.add_argument(
        "--input_volume",
        required=True,
        help="Path to 3D input volume (.tif, .nii, .nii.gz).",
    )
    parser.add_argument(
        "--model_or_checkpoint",
        required=True,
        help=(
            "Model path or identifier. Recommended: nnUNet model folder path like "
            ".../DatasetXXX_Name/Trainer__Plans__3d_fullres"
        ),
    )
    parser.add_argument(
        "--output_dir",
        required=True,
        help="Output directory for selected slices, predictions, and metadata.",
    )
    parser.add_argument(
        "--axis",
        type=int,
        default=0,
        help="Slice axis on internal (Z, Y, X) representation. Default: 0 (Z-axis).",
    )
    parser.add_argument(
        "--num_slices",
        type=int,
        default=3,
        help="Number of representative slices to select. Default: 3.",
    )
    parser.add_argument(
        "--min_slice_gap",
        type=int,
        default=10,
        help="Minimum index distance between selected slices. Default: 10.",
    )
    parser.add_argument(
        "--dry_run",
        action="store_true",
        help="If set, only select slices and save metadata; skip prediction.",
    )
    parser.add_argument(
        "--norm_type",
        default=None,
        choices=["noNorm", "zscore", "rescale_to_0_1", "rgb_to_0_1"],
        help="Normalization method for prediction inputs. Default: read from dataset_info.json.",
    )
    parser.add_argument(
        "--min_foreground_fraction",
        type=float,
        default=0.01,
        help="Minimum per-slice foreground fraction to be considered informative. Default: 0.01.",
    )
    parser.add_argument(
        "--dataset_id",
        default=None,
        help="Override dataset id for nnUNetv2_predict (-d), e.g. 777.",
    )
    parser.add_argument(
        "--trainer",
        default=None,
        help="Override trainer for nnUNetv2_predict (-tr).",
    )
    parser.add_argument(
        "--configuration",
        default=None,
        help="Override configuration for nnUNetv2_predict (-c), e.g. 3d_fullres.",
    )
    parser.add_argument(
        "--plans",
        default=None,
        help="Optional plans identifier for nnUNetv2_predict (-p).",
    )
    parser.add_argument(
        "--folds",
        nargs="+",
        default=["0"],
        help="Folds passed to nnUNetv2_predict (-f). Default: 0.",
    )
    parser.add_argument(
        "--checkpoint_name",
        default=None,
        help="Optional checkpoint name passed as -chk (e.g., checkpoint_final.pth).",
    )
    parser.add_argument(
        "--device",
        default=None,
        choices=["cpu", "cuda", "mps"],
        help="Optional nnUNetv2_predict device argument.",
    )
    return parser.parse_args()


def read_default_norm_type(dataset_info_path: Path) -> str:
    if not dataset_info_path.exists():
        return "noNorm"
    with dataset_info_path.open("r", encoding="utf-8") as f:
        metadata = json.load(f)
    return metadata.get("norm_type", "noNorm")


def normalize_image(img: np.ndarray, norm_type: str) -> np.ndarray:
    if norm_type == "noNorm":
        return img
    if norm_type == "zscore":
        mean_, std_ = float(np.mean(img)), float(np.std(img))
        return (img - mean_) / max(std_, 1e-8)
    if norm_type == "rescale_to_0_1":
        min_, max_ = float(np.min(img)), float(np.max(img))
        if max_ <= min_:
            return np.zeros_like(img, dtype=np.float32)
        return (img - min_) / (max_ - min_)
    if norm_type == "rgb_to_0_1":
        return img / 255.0
    raise NotImplementedError(f"Unknown normalization type: {norm_type}")


def load_volume_as_zyx(input_volume: Path) -> np.ndarray:
    suffixes = "".join(input_volume.suffixes).lower()
    if suffixes.endswith(".tif") or suffixes.endswith(".tiff"):
        vol = tifffile.imread(str(input_volume))
        if vol.ndim != 3:
            raise ValueError(f"Expected 3D TIFF volume, got shape={vol.shape}")
        return vol

    if suffixes.endswith(".nii") or suffixes.endswith(".nii.gz"):
        vol = nib.load(str(input_volume)).get_fdata()
        if vol.ndim != 3:
            raise ValueError(f"Expected 3D NIfTI volume, got shape={vol.shape}")
        # NIfTI is typically (X, Y, Z) -> internal (Z, Y, X)
        return vol.transpose(2, 1, 0)

    raise ValueError(
        f"Unsupported input format for {input_volume}. Supported: .tif/.tiff/.nii/.nii.gz"
    )


def make_dirs(base_dir: Path) -> Dict[str, Path]:
    selected_dir = base_dir / "selected_slices"
    predictions_dir = base_dir / "predictions"
    metadata_dir = base_dir / "metadata"
    temp_dir = base_dir / "_temp_nnunet"
    temp_input_dir = temp_dir / "input"
    temp_pred_dir = temp_dir / "pred"
    for p in [selected_dir, predictions_dir, metadata_dir, temp_input_dir, temp_pred_dir]:
        p.mkdir(parents=True, exist_ok=True)
    return {
        "selected": selected_dir,
        "predictions": predictions_dir,
        "metadata": metadata_dir,
        "temp": temp_dir,
        "temp_input": temp_input_dir,
        "temp_pred": temp_pred_dir,
    }


def min_max_scale(arr: np.ndarray) -> np.ndarray:
    arr = arr.astype(np.float64)
    amin, amax = float(np.min(arr)), float(np.max(arr))
    if amax <= amin:
        return np.zeros_like(arr, dtype=np.float64)
    return (arr - amin) / (amax - amin)


def compute_slice_metrics(
    volume_axis_first: np.ndarray,
    min_foreground_fraction: float,
) -> Tuple[List[SliceMetric], float]:
    # Global Otsu is robust against local noise spikes and provides consistent foreground estimate.
    otsu_thr = float(threshold_otsu(volume_axis_first))

    variances: List[float] = []
    foregrounds: List[float] = []
    slices = volume_axis_first.shape[0]
    for idx in range(slices):
        sl = volume_axis_first[idx]
        variances.append(float(np.var(sl)))
        fg = float(np.count_nonzero(sl > otsu_thr)) / float(sl.size)
        foregrounds.append(fg)

    var_arr = min_max_scale(np.asarray(variances, dtype=np.float64))
    fg_arr = min_max_scale(np.asarray(foregrounds, dtype=np.float64))
    score_arr = 0.5 * var_arr + 0.5 * fg_arr

    metrics: List[SliceMetric] = []
    for idx in range(slices):
        is_informative = foregrounds[idx] >= min_foreground_fraction
        metrics.append(
            SliceMetric(
                slice_idx=idx,
                variance=variances[idx],
                foreground_fraction=foregrounds[idx],
                score=float(score_arr[idx]),
                is_informative=is_informative,
            )
        )
    return metrics, otsu_thr


def respects_gap(idx: int, selected: Sequence[int], min_gap: int) -> bool:
    return all(abs(idx - s) >= min_gap for s in selected)


def closest_to_value(candidates: Sequence[SliceMetric], target: float) -> SliceMetric:
    return min(candidates, key=lambda x: abs(x.score - target))


def choose_with_gap(
    ordered_candidates: Sequence[SliceMetric],
    selected: List[int],
    min_gap: int,
) -> Optional[SliceMetric]:
    for c in ordered_candidates:
        if c.slice_idx not in selected and respects_gap(c.slice_idx, selected, min_gap):
            return c
    return None


def select_representative_slices(
    metrics: List[SliceMetric],
    num_slices: int,
    min_slice_gap: int,
) -> Tuple[List[int], Dict[int, str], bool]:
    if num_slices < 1:
        raise ValueError("num_slices must be >= 1")

    informative = [m for m in metrics if m.is_informative]
    used_fallback = False
    if len(informative) < num_slices:
        informative = metrics
        used_fallback = True

    selected: List[int] = []
    reasons: Dict[int, str] = {}

    # 1) Typical / median-content slice
    median_score = float(np.median([m.score for m in informative]))
    typical = closest_to_value(informative, median_score)
    selected.append(typical.slice_idx)
    reasons[typical.slice_idx] = "typical_median_score"

    if num_slices == 1:
        return selected, reasons, used_fallback

    # 2) High-structure / high-contrast slice
    by_score_desc = sorted(informative, key=lambda x: x.score, reverse=True)
    high = choose_with_gap(by_score_desc, selected, min_slice_gap)
    if high is None:
        high = next((c for c in by_score_desc if c.slice_idx not in selected), typical)
        used_fallback = True
    if high.slice_idx not in selected:
        selected.append(high.slice_idx)
        reasons[high.slice_idx] = "high_structure_high_score"

    # 3+) Diverse/challenging slices: maximize distance in (score, foreground_fraction)
    metric_lookup = {m.slice_idx: m for m in informative}
    while len(selected) < min(num_slices, len(informative)):
        best = None
        best_dist = -1.0
        for c in informative:
            if c.slice_idx in selected:
                continue
            if not respects_gap(c.slice_idx, selected, min_slice_gap):
                continue
            min_dist = min(
                (
                    (c.score - metric_lookup[s].score) ** 2
                    + (c.foreground_fraction - metric_lookup[s].foreground_fraction) ** 2
                )
                ** 0.5
                for s in selected
            )
            if min_dist > best_dist:
                best_dist = min_dist
                best = c

        if best is None:
            # Relax gap only if no valid candidate remains.
            remaining = [c for c in informative if c.slice_idx not in selected]
            if not remaining:
                break
            # Still prefer slices most different from selected set.
            def diversity_no_gap(candidate: SliceMetric) -> float:
                return min(
                    (
                        (candidate.score - metric_lookup[s].score) ** 2
                        + (candidate.foreground_fraction - metric_lookup[s].foreground_fraction)
                        ** 2
                    )
                    ** 0.5
                    for s in selected
                )

            best = max(remaining, key=diversity_no_gap)
            used_fallback = True

        selected.append(best.slice_idx)
        reason = "challenging_diverse"
        if len(selected) > 3:
            reason = "diverse_extension"
        reasons[best.slice_idx] = reason

    # If request exceeds informative count, top up from all slices.
    all_lookup = {m.slice_idx: m for m in metrics}
    while len(selected) < min(num_slices, len(metrics)):
        remaining = [m for m in metrics if m.slice_idx not in selected]
        if not remaining:
            break
        pick = max(remaining, key=lambda m: all_lookup[m.slice_idx].score)
        selected.append(pick.slice_idx)
        reasons[pick.slice_idx] = "fallback_top_score"
        used_fallback = True

    return sorted(selected), reasons, used_fallback


def save_selected_images(
    volume_axis_first: np.ndarray,
    selected_indices: Sequence[int],
    selected_dir: Path,
) -> None:
    for idx in selected_indices:
        img2d = volume_axis_first[idx]
        out_path = selected_dir / f"slice_{idx:04d}_image.tif"
        tifffile.imwrite(str(out_path), img2d)


def build_nnunet_2d_volume_from_slice(img2d: np.ndarray) -> np.ndarray:
    # Internal slice is (Y, X). Build single-slice 3D as (Z=1, Y, X), then transpose to (X, Y, Z).
    vol_zyx = img2d[np.newaxis, ...]
    return vol_zyx.transpose(2, 1, 0)


def infer_predict_settings(
    model_or_checkpoint: str,
    dataset_id: Optional[str],
    trainer: Optional[str],
    configuration: Optional[str],
    plans: Optional[str],
) -> Tuple[str, str, str, Optional[str], Dict[str, str]]:
    model_path = Path(model_or_checkpoint)
    extra_env: Dict[str, str] = {}

    if model_path.exists() and model_path.is_dir():
        # Typical model folder format: Trainer__Plans__3d_fullres
        if "__" in model_path.name:
            parts = model_path.name.split("__")
            if len(parts) == 3:
                trainer = trainer or parts[0]
                plans = plans or parts[1]
                configuration = configuration or parts[2]

            parent = model_path.parent
            m = re.match(r"Dataset(\d+)_.*", parent.name)
            if m:
                dataset_id = dataset_id or m.group(1)
                extra_env["nnUNet_results"] = str(parent.parent)

        # If user passed nnUNet_results root, we cannot infer unambiguously.
        if dataset_id is None:
            dataset_dirs = sorted(model_path.glob("Dataset*_*"))
            if len(dataset_dirs) == 1:
                m = re.match(r"Dataset(\d+)_.*", dataset_dirs[0].name)
                if m:
                    dataset_id = m.group(1)
                model_cfgs = [d for d in dataset_dirs[0].iterdir() if d.is_dir() and "__" in d.name]
                if len(model_cfgs) == 1:
                    parts = model_cfgs[0].name.split("__")
                    if len(parts) == 3:
                        trainer = trainer or parts[0]
                        plans = plans or parts[1]
                        configuration = configuration or parts[2]
                extra_env["nnUNet_results"] = str(model_path)

    # Allow direct dataset id as model_or_checkpoint if path does not exist.
    if dataset_id is None and re.fullmatch(r"\d+", model_or_checkpoint):
        dataset_id = model_or_checkpoint

    if dataset_id is None or trainer is None or configuration is None:
        raise ValueError(
            "Could not infer nnUNet settings. Provide --dataset_id, --trainer, and --configuration "
            "or pass a model folder path formatted as Trainer__Plans__Configuration under DatasetXXX_*."
        )

    return dataset_id, trainer, configuration, plans, extra_env


def write_prediction_inputs(
    volume_axis_first: np.ndarray,
    selected_indices: Sequence[int],
    temp_input_dir: Path,
    norm_type: str,
) -> List[str]:
    case_ids: List[str] = []
    for idx in selected_indices:
        img2d = volume_axis_first[idx].astype(np.float32)
        img2d = normalize_image(img2d, norm_type).astype(np.float32)
        vol_xyz = build_nnunet_2d_volume_from_slice(img2d)
        case_id = f"slice_{idx:04d}"
        case_ids.append(case_id)
        out_nii = temp_input_dir / f"{case_id}_0000.nii.gz"
        nib.save(nib.Nifti1Image(vol_xyz, np.eye(4)), str(out_nii))
    return case_ids


def run_nnunet_predict(
    input_dir: Path,
    output_dir: Path,
    dataset_id: str,
    trainer: str,
    configuration: str,
    folds: Sequence[str],
    plans: Optional[str],
    checkpoint_name: Optional[str],
    device: Optional[str],
    extra_env: Dict[str, str],
) -> Tuple[int, str, str, List[str]]:
    cmd: List[str] = [
        "nnUNetv2_predict",
        "-i",
        str(input_dir),
        "-o",
        str(output_dir),
        "-d",
        str(dataset_id),
        "-tr",
        trainer,
        "-c",
        configuration,
        "-f",
    ]
    cmd.extend([str(f) for f in folds])
    if plans:
        cmd.extend(["-p", plans])
    if checkpoint_name:
        cmd.extend(["-chk", checkpoint_name])
    if device:
        cmd.extend(["-device", device])

    env = os.environ.copy()
    env.update(extra_env)

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr, cmd


def convert_predictions_to_tif(
    temp_pred_dir: Path,
    selected_indices: Sequence[int],
    predictions_dir: Path,
) -> List[str]:
    saved: List[str] = []
    for idx in selected_indices:
        case_id = f"slice_{idx:04d}"
        nii_path = temp_pred_dir / f"{case_id}.nii.gz"
        if not nii_path.exists():
            continue
        pred_xyz = nib.load(str(nii_path)).get_fdata()
        if pred_xyz.ndim != 3:
            raise ValueError(f"Unexpected prediction shape for {nii_path}: {pred_xyz.shape}")

        # Back to (Z, Y, X), then squeeze Z=1 for 2D output.
        pred_zyx = pred_xyz.transpose(2, 1, 0)
        pred2d = np.squeeze(pred_zyx, axis=0)
        pred2d = pred2d.astype(np.uint8)

        out_tif = predictions_dir / f"slice_{idx:04d}_pred.tif"
        tifffile.imwrite(str(out_tif), pred2d)
        saved.append(str(out_tif))
    return saved


def write_metrics_csv(metrics: Sequence[SliceMetric], out_csv: Path) -> None:
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "slice_idx",
            "variance",
            "foreground_fraction",
            "score",
            "is_informative",
        ])
        for m in metrics:
            writer.writerow(
                [
                    m.slice_idx,
                    f"{m.variance:.8f}",
                    f"{m.foreground_fraction:.8f}",
                    f"{m.score:.8f}",
                    int(m.is_informative),
                ]
            )


def write_selected_csv(
    selected_indices: Sequence[int],
    metric_by_idx: Dict[int, SliceMetric],
    reasons: Dict[int, str],
    out_csv: Path,
) -> None:
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "slice_idx",
            "variance",
            "foreground_fraction",
            "score",
            "reason",
        ])
        for idx in selected_indices:
            m = metric_by_idx[idx]
            writer.writerow(
                [
                    idx,
                    f"{m.variance:.8f}",
                    f"{m.foreground_fraction:.8f}",
                    f"{m.score:.8f}",
                    reasons.get(idx, "selected"),
                ]
            )


def write_json_metadata(
    out_json: Path,
    input_volume: Path,
    model_or_checkpoint: str,
    norm_type: str,
    axis: int,
    otsu_threshold: float,
    selected_indices: Sequence[int],
    reasons: Dict[int, str],
    metrics: Sequence[SliceMetric],
    used_fallback: bool,
    prediction_cmd: Optional[Sequence[str]],
    predicted_files: Sequence[str],
) -> None:
    metric_by_idx = {m.slice_idx: m for m in metrics}
    payload = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "input_volume": str(input_volume),
        "model_or_checkpoint": model_or_checkpoint,
        "axis": axis,
        "norm_type": norm_type,
        "otsu_threshold": otsu_threshold,
        "used_fallback": used_fallback,
        "selected": [
            {
                "slice_idx": idx,
                "reason": reasons.get(idx, "selected"),
                "variance": metric_by_idx[idx].variance,
                "foreground_fraction": metric_by_idx[idx].foreground_fraction,
                "score": metric_by_idx[idx].score,
            }
            for idx in selected_indices
        ],
        "prediction_command": list(prediction_cmd) if prediction_cmd else None,
        "predicted_files": list(predicted_files),
    }
    with out_json.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def write_run_log(out_log: Path, lines: Sequence[str]) -> None:
    with out_log.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main() -> int:
    args = parse_args()
    input_volume = Path(args.input_volume)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_volume.exists():
        print(f"ERROR: Input volume does not exist: {input_volume}")
        return 1

    norm_type = args.norm_type
    if norm_type is None:
        norm_type = read_default_norm_type(Path.cwd() / "dataset_info.json")

    run_log_lines: List[str] = [
        f"[{datetime.now().isoformat(timespec='seconds')}] start",
        f"input_volume={input_volume}",
        f"model_or_checkpoint={args.model_or_checkpoint}",
        f"output_dir={output_dir}",
        f"axis={args.axis}",
        f"num_slices={args.num_slices}",
        f"min_slice_gap={args.min_slice_gap}",
        f"norm_type={norm_type}",
        f"dry_run={args.dry_run}",
    ]

    dirs = make_dirs(output_dir)

    # 1) Load volume as (Z, Y, X)
    vol_zyx = load_volume_as_zyx(input_volume)
    if args.axis < 0 or args.axis >= vol_zyx.ndim:
        print(f"ERROR: axis out of range for volume shape {vol_zyx.shape}: axis={args.axis}")
        return 1

    volume_axis_first = np.moveaxis(vol_zyx, args.axis, 0)
    run_log_lines.append(f"loaded_shape_zyx={tuple(vol_zyx.shape)}")
    run_log_lines.append(f"analysis_shape_axis_first={tuple(volume_axis_first.shape)}")

    # 2) Compute metrics and select slices
    metrics, otsu_thr = compute_slice_metrics(
        volume_axis_first,
        min_foreground_fraction=args.min_foreground_fraction,
    )
    selected, reasons, used_fallback = select_representative_slices(
        metrics,
        num_slices=args.num_slices,
        min_slice_gap=args.min_slice_gap,
    )
    metric_by_idx = {m.slice_idx: m for m in metrics}

    print("Selected slices:")
    for idx in selected:
        m = metric_by_idx[idx]
        why = reasons.get(idx, "selected")
        print(
            f"  slice={idx:04d} variance={m.variance:.6f} "
            f"foreground_fraction={m.foreground_fraction:.6f} score={m.score:.6f} reason={why}"
        )

    # 3) Save selected raw slices + metadata
    save_selected_images(volume_axis_first, selected, dirs["selected"])
    write_metrics_csv(metrics, dirs["metadata"] / "all_slice_metrics.csv")
    write_selected_csv(selected, metric_by_idx, reasons, dirs["metadata"] / "selected_slices.csv")

    prediction_cmd: Optional[List[str]] = None
    predicted_files: List[str] = []

    if not args.dry_run:
        # 4) Build prediction inputs and run nnUNet CLI
        case_ids = write_prediction_inputs(
            volume_axis_first,
            selected,
            dirs["temp_input"],
            norm_type,
        )
        run_log_lines.append(f"temp_cases={case_ids}")

        try:
            dataset_id, trainer, configuration, plans, extra_env = infer_predict_settings(
                model_or_checkpoint=args.model_or_checkpoint,
                dataset_id=args.dataset_id,
                trainer=args.trainer,
                configuration=args.configuration,
                plans=args.plans,
            )
        except ValueError as e:
            run_log_lines.append(f"ERROR infer settings: {e}")
            write_run_log(dirs["metadata"] / "run_log.txt", run_log_lines)
            write_json_metadata(
                dirs["metadata"] / "selected_slices.json",
                input_volume=input_volume,
                model_or_checkpoint=args.model_or_checkpoint,
                norm_type=norm_type,
                axis=args.axis,
                otsu_threshold=otsu_thr,
                selected_indices=selected,
                reasons=reasons,
                metrics=metrics,
                used_fallback=used_fallback,
                prediction_cmd=None,
                predicted_files=[],
            )
            print(f"ERROR: {e}")
            return 2

        run_log_lines.append(
            f"predict_settings=dataset:{dataset_id},trainer:{trainer},configuration:{configuration},plans:{plans}"
        )
        if extra_env:
            run_log_lines.append(f"predict_env_overrides={extra_env}")

        code, stdout, stderr, cmd = run_nnunet_predict(
            input_dir=dirs["temp_input"],
            output_dir=dirs["temp_pred"],
            dataset_id=dataset_id,
            trainer=trainer,
            configuration=configuration,
            folds=args.folds,
            plans=plans,
            checkpoint_name=args.checkpoint_name,
            device=args.device,
            extra_env=extra_env,
        )
        prediction_cmd = cmd

        run_log_lines.append("nnUNet command: " + " ".join(cmd))
        run_log_lines.append(f"nnUNet returncode={code}")
        run_log_lines.append("nnUNet stdout:")
        run_log_lines.append(stdout.strip())
        run_log_lines.append("nnUNet stderr:")
        run_log_lines.append(stderr.strip())

        if code != 0:
            write_run_log(dirs["metadata"] / "run_log.txt", run_log_lines)
            write_json_metadata(
                dirs["metadata"] / "selected_slices.json",
                input_volume=input_volume,
                model_or_checkpoint=args.model_or_checkpoint,
                norm_type=norm_type,
                axis=args.axis,
                otsu_threshold=otsu_thr,
                selected_indices=selected,
                reasons=reasons,
                metrics=metrics,
                used_fallback=used_fallback,
                prediction_cmd=prediction_cmd,
                predicted_files=[],
            )
            print("ERROR: nnUNetv2_predict failed. Check run_log.txt for details.")
            return 3

        predicted_files = convert_predictions_to_tif(dirs["temp_pred"], selected, dirs["predictions"])
        run_log_lines.append(f"saved_predictions={predicted_files}")

    # 5) Save metadata and cleanup
    write_json_metadata(
        dirs["metadata"] / "selected_slices.json",
        input_volume=input_volume,
        model_or_checkpoint=args.model_or_checkpoint,
        norm_type=norm_type,
        axis=args.axis,
        otsu_threshold=otsu_thr,
        selected_indices=selected,
        reasons=reasons,
        metrics=metrics,
        used_fallback=used_fallback,
        prediction_cmd=prediction_cmd,
        predicted_files=predicted_files,
    )

    run_log_lines.append(f"used_fallback={used_fallback}")
    run_log_lines.append(f"selected={selected}")
    run_log_lines.append(f"[{datetime.now().isoformat(timespec='seconds')}] finished")
    write_run_log(dirs["metadata"] / "run_log.txt", run_log_lines)

    shutil.rmtree(dirs["temp"], ignore_errors=True)
    print(f"Done. Output written to: {output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
