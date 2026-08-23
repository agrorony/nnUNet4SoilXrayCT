"""
Make a clean copy of the Rehovot sample 3 scan folder, skipping files that
are actually corrupted (0-byte, or .tif/.iif that fail to decode).

The source folder is READ-ONLY here: nothing is deleted, modified, or
written under SOURCE. All output goes to DEST, a sibling folder.

Corruption check for .tif/.iif files does a real decode attempt (tifffile,
falling back to Pillow) rather than trusting the extension or file size
alone, since a truncated/garbage file can still have nonzero size.
"""

import os
import re
import shutil
import sys
from pathlib import Path

import tifffile
from PIL import Image

SOURCE = Path(r"\\hive3065\Yael_Mishael\Rony\10.12.25_Rehovot_samp_3")
DEST = Path(r"\\hive3065\Yael_Mishael\Rony\10.12.25_Rehovot_samp_3_clean")

IMAGE_EXTENSIONS = {".tif", ".iif"}

# Filenames/dirs that look like leftovers from earlier failed reconstruction
# attempts rather than original scan data. Flagged separately, still copied.
ARTIFACT_FILENAME_PATTERNS = [
    re.compile(r"_pp\d+\.tif$", re.IGNORECASE),
    re.compile(r"_prev_.*\.tif$", re.IGNORECASE),
    re.compile(r"_rectmp\.log$", re.IGNORECASE),
]
ARTIFACT_DIR_PATTERN = re.compile(r"_Rec$", re.IGNORECASE)

PROGRESS_EVERY = 200


def check_image_decodes(path: Path) -> tuple[bool, str]:
    """Actually attempt to decode pixel data. Returns (ok, error_message)."""
    try:
        with tifffile.TiffFile(str(path)) as tf:
            tf.asarray()
        return True, ""
    except Exception as e_tiff:
        try:
            with Image.open(path) as img:
                img.load()
            return True, ""
        except Exception as e_pil:
            return False, f"tifffile: {e_tiff}; PIL: {e_pil}"


def is_corrupted(path: Path) -> tuple[bool, str]:
    size = path.stat().st_size
    if size == 0:
        return True, "0-byte file"
    if path.suffix.lower() in IMAGE_EXTENSIONS:
        ok, err = check_image_decodes(path)
        if not ok:
            return True, f"failed to decode image ({err})"
    return False, ""


def is_artifact(rel_path: Path) -> bool:
    for part in rel_path.parts[:-1]:
        if ARTIFACT_DIR_PATTERN.search(part):
            return True
    return any(p.search(rel_path.name) for p in ARTIFACT_FILENAME_PATTERNS)


def main() -> None:
    if not SOURCE.is_dir():
        sys.exit(f"Source folder not found or not accessible: {SOURCE}")

    DEST.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    skipped: list[tuple[str, str]] = []
    flagged_artifacts: list[str] = []
    artifact_dirs_seen: set[str] = set()
    total_bytes = 0
    n_seen = 0

    for root, dirnames, filenames in os.walk(SOURCE):
        root_path = Path(root)

        for dname in dirnames:
            if ARTIFACT_DIR_PATTERN.search(dname):
                rel_dir = (root_path / dname).relative_to(SOURCE)
                artifact_dirs_seen.add(str(rel_dir))

        for fname in filenames:
            src_file = root_path / fname
            rel_path = src_file.relative_to(SOURCE)
            n_seen += 1

            corrupted, reason = is_corrupted(src_file)
            if corrupted:
                skipped.append((str(rel_path), reason))
            else:
                dest_file = DEST / rel_path
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, dest_file)

                size = src_file.stat().st_size
                total_bytes += size
                copied.append(str(rel_path))

                if is_artifact(rel_path):
                    flagged_artifacts.append(str(rel_path))

            if n_seen % PROGRESS_EVERY == 0:
                print(f"...processed {n_seen} files ({len(copied)} copied, {len(skipped)} skipped)")

    empty_artifact_dirs = [
        d for d in sorted(artifact_dirs_seen)
        if not any(c.startswith(d + os.sep) or c == d for c in copied)
        and not any(s.startswith(d + os.sep) or s == d for s, _ in skipped)
    ]

    print()
    print("=" * 70)
    print("COPY REPORT")
    print("=" * 70)
    print(f"Source:      {SOURCE}")
    print(f"Destination: {DEST}")
    print()
    print(f"Files copied:            {len(copied)}")
    print(f"Files skipped (corrupt): {len(skipped)}")
    print(f"Total bytes copied:      {total_bytes:,} bytes ({total_bytes / (1024**3):.3f} GiB)")
    print()

    if skipped:
        print("-" * 70)
        print("SKIPPED AS CORRUPTED:")
        for rel, reason in skipped:
            print(f"  {rel}  [{reason}]")
        print()

    if flagged_artifacts or empty_artifact_dirs:
        print("-" * 70)
        print("FLAGGED AS LIKELY LEFTOVER RECONSTRUCTION ARTIFACTS (copied by default, review if you want to exclude):")
        for rel in flagged_artifacts:
            print(f"  {rel}")
        for d in empty_artifact_dirs:
            print(f"  {d}  [empty artifact directory, nothing to copy]")
        print()
    else:
        print("No leftover-artifact-pattern files or folders detected.")

    print("Done.")


if __name__ == "__main__":
    main()
