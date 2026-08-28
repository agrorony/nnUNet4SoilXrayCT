"""
05_evaluation/labels_debug/check_data.py
Diagnostic tool for nnU-Net training data: value audit, metadata check,
label integrity, intensity stats, napari visualization, and self-check.

Usage:
    # Auto-select first matching pair:
    python 05_evaluation/labels_debug/check_data.py

    # Explicit case name (without suffix):
    python 05_evaluation/labels_debug/check_data.py --case bnei_reem_001
"""

import argparse
import json
import sys
from pathlib import Path

import nibabel as nib
import numpy as np

# ──────────────────────────── Paths ───────────────────────────────────────────
IMAGES_TR = Path(
    r"G:\האחסון שלי\soil_microCT_images\nnUNet_resources\bnei_reem"
    r"\nnUNet_raw\Dataset777_GCEF\imagesTr"
)
LABELS_TR = Path(
    r"G:\האחסון שלי\soil_microCT_images\nnUNet_resources\bnei_reem"
    r"\nnUNet_raw\Dataset777_GCEF\labelsTr"
)


# ──────────────────────────── Pair resolution ─────────────────────────────────
def find_case_pairs() -> list[tuple[Path, Path]]:
    """Return (image_path, label_path) pairs matched by case name."""
    if not LABELS_TR.exists():
        sys.exit(f"[ERROR] labelsTr not found: {LABELS_TR}")
    if not IMAGES_TR.exists():
        sys.exit(f"[ERROR] imagesTr not found: {IMAGES_TR}")

    pairs = []
    for label_path in sorted(LABELS_TR.glob("*.nii.gz")):
        case = label_path.name.replace(".nii.gz", "")
        # imagesTr files use _0000 channel suffix
        img_path = IMAGES_TR / f"{case}_0000.nii.gz"
        if img_path.exists():
            pairs.append((img_path, label_path))
    return pairs


def resolve_pair(case: str | None) -> tuple[Path, Path]:
    pairs = find_case_pairs()
    if not pairs:
        sys.exit("[ERROR] No matching image/label pairs found.")

    if case:
        matched = [(i, l) for i, l in pairs if case in l.stem]
        if not matched:
            sys.exit(f"[ERROR] Case '{case}' not found. Available:\n"
                     + "\n".join(str(l) for _, l in pairs))
        return matched[0]

    return pairs[0]  # default: first pair


# ──────────────────────────── Label name lookup ──────────────────────────────
def _build_nnunet_label_names(dataset_info_path: Path) -> dict:
    """Map nnUNet output label ID → class name, derived from dataset_info.json.

    mask_to_nnUNet semantics applied here:
      JSON label 0 (ToPredict) → num_classes-1  (ignore)
      JSON label k (k >= 1)   → k-1             (real classes, 0-indexed)
    """
    if not dataset_info_path.exists():
        return {}
    try:
        with open(dataset_info_path, encoding="utf-8") as f:
            info = json.load(f)
    except Exception:
        return {}
    raw_labels = info.get("labels", {})
    num_classes = len(raw_labels)  # includes ToPredict (id=0)
    mapping = {}
    for k_str, name in raw_labels.items():
        orig_id = int(k_str)
        if orig_id == 0:
            mapping[num_classes - 1] = f"{name} [ignore]"
        else:
            mapping[orig_id - 1] = name
    return mapping


# ──────────────────────────── Audit functions ─────────────────────────────────
def metadata_check(img_nib: nib.Nifti1Image, lbl_nib: nib.Nifti1Image) -> None:
    print("\n" + "=" * 60)
    print("METADATA CHECK")
    print("=" * 60)

    img_shape = img_nib.shape
    lbl_shape = lbl_nib.shape
    print(f"  Image shape : {img_shape}")
    print(f"  Label shape : {lbl_shape}")
    shape_ok = img_shape == lbl_shape
    print(f"  Shapes match: {'YES' if shape_ok else '*** NO — MISMATCH ***'}")

    img_spacing = tuple(float(v) for v in img_nib.header.get_zooms()[:3])
    lbl_spacing = tuple(float(v) for v in lbl_nib.header.get_zooms()[:3])
    print(f"\n  Image spacing (mm): {img_spacing}")
    print(f"  Label spacing (mm): {lbl_spacing}")
    spacing_ok = np.allclose(img_spacing, lbl_spacing, atol=1e-3)
    print(f"  Spacing match     : {'YES' if spacing_ok else '*** NO — MISMATCH ***'}")

    img_aff = img_nib.affine
    lbl_aff = lbl_nib.affine
    aff_ok = np.allclose(img_aff, lbl_aff, atol=1e-3)
    print(f"\n  Affine match      : {'YES' if aff_ok else '*** NO — MISMATCH ***'}")
    if not aff_ok:
        print("  Image affine:\n", img_aff)
        print("  Label affine:\n", lbl_aff)
        print("  Diff (abs max):", np.abs(img_aff - lbl_aff).max())


def label_integrity(lbl_data: np.ndarray,
                    label_names: dict | None = None) -> None:
    print("\n" + "=" * 60)
    print("LABEL INTEGRITY")
    print("=" * 60)
    unique_ints = [int(v) for v in np.unique(lbl_data)]
    print(f"  Unique label values : {unique_ints}")
    total_voxels = lbl_data.size
    for vi in unique_ints:
        count = int((lbl_data == vi).sum())
        pct = 100.0 * count / total_voxels
        name = f"  ({label_names[vi]})" if label_names and vi in label_names else ""
        print(f"    label={vi:3d}{name:<30}  count={count:>10,}  ({pct:.3f}%)")

    if len(unique_ints) == 1 and unique_ints[0] == 0:
        print("\n  *** WARNING: ALL LABELS ARE ZERO — mask may be blank! ***")
    elif set(unique_ints) == {0}:
        print("\n  *** WARNING: Only background label found. ***")
    else:
        print("\n  Label range looks populated.")


def intensity_stats(img_data: np.ndarray) -> None:
    print("\n" + "=" * 60)
    print("INTENSITY STATS (image)")
    print("=" * 60)
    print(f"  dtype : {img_data.dtype}")
    print(f"  min   : {img_data.min():.4f}")
    print(f"  max   : {img_data.max():.4f}")
    print(f"  mean  : {img_data.mean():.4f}")
    print(f"  std   : {img_data.std():.4f}")
    p1, p5, p50, p95, p99 = np.percentile(img_data, [1, 5, 50, 95, 99])
    print(f"  p1/p5 : {p1:.4f} / {p5:.4f}")
    print(f"  p50   : {p50:.4f}")
    print(f"  p95/p99: {p95:.4f} / {p99:.4f}")


# ──────────────────────────── Self-check ──────────────────────────────────────
def selfcheck_labels() -> None:
    """Scan all labelsTr .nii.gz files; report files that are all-zero or empty."""
    print("\n" + "=" * 60)
    print("SELF-CHECK: labelsTr all-zero / empty scan")
    print("=" * 60)
    if not LABELS_TR.exists():
        print(f"  [SKIP] labelsTr dir not found: {LABELS_TR}")
        return

    label_files = sorted(LABELS_TR.glob("*.nii.gz"))
    if not label_files:
        print("  [WARN] No .nii.gz files found in labelsTr.")
        return

    print(f"  Scanning {len(label_files)} file(s)...")
    flagged = []
    for f in label_files:
        size_bytes = f.stat().st_size
        if size_bytes == 0:
            flagged.append((f.name, "EMPTY FILE (0 bytes)"))
            continue
        try:
            data = nib.load(str(f)).get_fdata(dtype=np.float32)
            if data.max() == 0:
                flagged.append((f.name, f"ALL-ZERO array (shape={data.shape})"))
        except Exception as e:
            flagged.append((f.name, f"LOAD ERROR: {e}"))

    if flagged:
        print("\n  *** FLAGGED FILES ***")
        for name, reason in flagged:
            print(f"    {name}: {reason}")
    else:
        print("  All files OK — none are empty or all-zero.")


# ──────────────────────────── Napari visualization ────────────────────────────
def launch_napari(img_data: np.ndarray, lbl_data: np.ndarray,
                  img_path: Path, lbl_path: Path) -> None:
    try:
        import napari
    except ImportError:
        print("\n[SKIP] napari not installed — skipping visualization.")
        return

    print("\nLaunching napari viewer...")
    viewer = napari.Viewer(title="nnUNet Training Diagnostic")

    viewer.add_image(
        img_data,
        name=img_path.stem.replace(".nii", ""),
        colormap="gray",
        blending="translucent",
    )

    viewer.add_labels(
        lbl_data.astype(np.int32),
        name=lbl_path.stem.replace(".nii", "") + "_labels",
        opacity=0.5,
        blending="additive",
    )

    print("  Viewer open. Close the window to exit.")
    napari.run()


# ──────────────────────────── Main ────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Diagnostic check for nnU-Net imagesTr / labelsTr pair."
    )
    parser.add_argument(
        "--case", default=None,
        help="Case name substring (without _0000.nii.gz). Default: first pair found."
    )
    parser.add_argument(
        "--no-napari", action="store_true",
        help="Skip napari visualization (useful on headless servers)."
    )
    parser.add_argument(
        "--selfcheck-only", action="store_true",
        help="Only run the all-zero scan on labelsTr, then exit."
    )
    args = parser.parse_args()

    # ── Self-check only mode ──────────────────────────────────────────────────
    if args.selfcheck_only:
        selfcheck_labels()
        return

    # ── Resolve pair ─────────────────────────────────────────────────────────
    img_path, lbl_path = resolve_pair(args.case)
    print(f"\nDiagnosing pair:")
    print(f"  Image : {img_path}")
    print(f"  Label : {lbl_path}")

    # ── Load ─────────────────────────────────────────────────────────────────
    print("\nLoading files...")
    img_nib = nib.load(str(img_path))
    lbl_nib = nib.load(str(lbl_path))

    img_data = img_nib.get_fdata(dtype=np.float32)
    # Round-trip the NIfTI float storage back to integers for label analysis.
    lbl_data = np.round(lbl_nib.get_fdata(dtype=np.float32)).astype(np.int32)

    # ── Audits ───────────────────────────────────────────────────────────────
    dataset_info_path = Path(__file__).parent.parent / "dataset_info.json"
    label_names = _build_nnunet_label_names(dataset_info_path)
    metadata_check(img_nib, lbl_nib)
    label_integrity(lbl_data, label_names)
    intensity_stats(img_data)
    selfcheck_labels()

    # ── Napari ───────────────────────────────────────────────────────────────
    if not args.no_napari:
        launch_napari(img_data, lbl_data, img_path, lbl_path)

    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    main()
