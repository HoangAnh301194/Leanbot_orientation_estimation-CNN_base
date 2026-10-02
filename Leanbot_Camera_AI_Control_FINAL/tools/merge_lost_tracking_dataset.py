"""Merge the base YOLO dataset with validated lost-tracking samples.

Expected inputs
---------------
Base dataset:
    datasets/
    ├── images/
    ├── labels/
    └── manifest.json          # optional

Lost-tracking dataset:
    lost_tracking_dataset/
    └── session_*/
        ├── images/
        ├── labels/
        ├── metadata/
        └── check_labels/

The script never modifies the base dataset. It creates a new dataset directory,
renames all samples sequentially, validates YOLO labels, and writes a manifest
that records the source of every output image.
"""

from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BASE = PROJECT_ROOT / "datasets"
DEFAULT_LOST_ROOT = PROJECT_ROOT / "lost_tracking_dataset"
DEFAULT_OUTPUT = PROJECT_ROOT / "datasets_with_lost_tracking"

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}


def image_files(images_dir: Path) -> list[Path]:
    if not images_dir.exists():
        return []
    return sorted(
        p for p in images_dir.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES
    )


def validate_yolo_label(label_path: Path, num_classes: int = 24) -> tuple[bool, int, str]:
    """Validate a YOLO detection label and return (valid, bbox_count, reason)."""
    if not label_path.exists():
        return False, 0, "missing label"

    text = label_path.read_text(encoding="utf-8").strip()
    if not text:
        return False, 0, "empty label"

    bbox_count = 0
    for line_no, line in enumerate(text.splitlines(), start=1):
        parts = line.split()
        if len(parts) != 5:
            return False, bbox_count, f"line {line_no}: expected 5 fields"

        try:
            class_id = int(float(parts[0]))
            x, y, w, h = map(float, parts[1:])
        except ValueError:
            return False, bbox_count, f"line {line_no}: non-numeric value"

        if not 0 <= class_id < num_classes:
            return False, bbox_count, f"line {line_no}: class_id={class_id} outside [0,{num_classes - 1}]"

        if not all(0.0 <= value <= 1.0 for value in (x, y, w, h)):
            return False, bbox_count, f"line {line_no}: normalized bbox outside [0,1]"

        if w <= 0.0 or h <= 0.0:
            return False, bbox_count, f"line {line_no}: width/height must be > 0"

        bbox_count += 1

    return True, bbox_count, ""


def load_manifest(dataset_dir: Path) -> dict[str, dict]:
    manifest_path = dataset_dir / "manifest.json"
    if not manifest_path.exists():
        return {}

    try:
        records = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    return {
        str(item.get("filename")): item
        for item in records
        if isinstance(item, dict) and item.get("filename")
    }


def collect_base_samples(base_dir: Path, num_classes: int):
    images_dir = base_dir / "images"
    labels_dir = base_dir / "labels"
    old_manifest = load_manifest(base_dir)

    samples = []
    skipped = []
    for img in image_files(images_dir):
        label = labels_dir / f"{img.stem}.txt"
        valid, bbox_count, reason = validate_yolo_label(label, num_classes=num_classes)

        # Base dataset may intentionally include negative-background samples.
        # A present empty label is therefore accepted for the base dataset.
        if label.exists() and not label.read_text(encoding="utf-8").strip():
            valid, bbox_count, reason = True, 0, ""

        if not valid:
            skipped.append((img, reason))
            continue

        info = old_manifest.get(img.name, {})
        samples.append({
            "image": img,
            "label": label,
            "bbox_count": bbox_count,
            "source_type": "base_dataset",
            "source_session": info.get("source_session", ""),
            "source_image": info.get("source_image", img.name),
            "source_group": info.get("source_group", "base_dataset"),
        })

    return samples, skipped


def collect_lost_samples(lost_root: Path, num_classes: int):
    samples = []
    skipped = []

    if not lost_root.exists():
        return samples, skipped

    sessions = sorted(p for p in lost_root.iterdir() if p.is_dir())
    for session in sessions:
        images_dir = session / "images"
        labels_dir = session / "labels"

        for img in image_files(images_dir):
            label = labels_dir / f"{img.stem}.txt"
            valid, bbox_count, reason = validate_yolo_label(label, num_classes=num_classes)
            if not valid:
                skipped.append((img, reason))
                continue

            samples.append({
                "image": img,
                "label": label,
                "bbox_count": bbox_count,
                "source_type": "lost_tracking",
                "source_session": session.name,
                "source_image": img.name,
                "source_group": "lost_tracking",
            })

    return samples, skipped


def merge_datasets(
    base_dir: Path,
    lost_root: Path,
    output_dir: Path,
    *,
    num_classes: int = 24,
    overwrite: bool = False,
    dry_run: bool = False,
):
    base_dir = base_dir.resolve()
    lost_root = lost_root.resolve()
    output_dir = output_dir.resolve()

    if not base_dir.exists():
        raise SystemExit(f"[ERROR] Base dataset not found: {base_dir}")
    if not (base_dir / "images").exists() or not (base_dir / "labels").exists():
        raise SystemExit("[ERROR] Base dataset must contain images/ and labels/.")

    if output_dir == base_dir:
        raise SystemExit("[ERROR] Output must be different from the base dataset.")

    base_samples, base_skipped = collect_base_samples(base_dir, num_classes)
    lost_samples, lost_skipped = collect_lost_samples(lost_root, num_classes)

    all_samples = base_samples + lost_samples
    if not all_samples:
        raise SystemExit("[ERROR] No valid image-label pairs found.")

    print(f"[INFO] Base dataset          : {base_dir}")
    print(f"[INFO] Lost-tracking root    : {lost_root}")
    print(f"[INFO] Output dataset        : {output_dir}")
    print(f"[INFO] Valid base samples    : {len(base_samples)}")
    print(f"[INFO] Valid lost samples    : {len(lost_samples)}")
    print(f"[INFO] Skipped base samples  : {len(base_skipped)}")
    print(f"[INFO] Skipped lost samples  : {len(lost_skipped)}")

    for path, reason in base_skipped + lost_skipped:
        print(f"[SKIP] {path}: {reason}")

    if dry_run:
        print(f"[DRY RUN] Would write {len(all_samples)} samples.")
        return

    if output_dir.exists():
        if not overwrite:
            raise SystemExit(
                f"[ERROR] Output already exists: {output_dir}\n"
                "        Use --overwrite to replace it."
            )
        shutil.rmtree(output_dir)

    out_images = output_dir / "images"
    out_labels = output_dir / "labels"
    out_images.mkdir(parents=True, exist_ok=True)
    out_labels.mkdir(parents=True, exist_ok=True)

    manifest = []
    source_counts = Counter()
    total_bboxes = 0

    for index, sample in enumerate(all_samples):
        stem = f"{index:06d}"
        suffix = sample["image"].suffix.lower()
        out_image = out_images / f"{stem}{suffix}"
        out_label = out_labels / f"{stem}.txt"

        shutil.copy2(sample["image"], out_image)
        shutil.copy2(sample["label"], out_label)

        source_counts[sample["source_type"]] += 1
        total_bboxes += sample["bbox_count"]

        manifest.append({
            "index": index,
            "filename": out_image.name,
            "source_type": sample["source_type"],
            "source_session": sample["source_session"],
            "source_image": sample["source_image"],
            "source_group": sample["source_group"],
            "bbox_count": sample["bbox_count"],
        })

    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("\n[DONE] Dataset merge completed.")
    print(f"       Total images        : {len(all_samples)}")
    print(f"       Base images         : {source_counts['base_dataset']}")
    print(f"       Lost-tracking images: {source_counts['lost_tracking']}")
    print(f"       Total bounding boxes: {total_bboxes}")
    print(f"       Manifest            : {output_dir / 'manifest.json'}")


def main():
    parser = argparse.ArgumentParser(
        description="Merge a base YOLO dataset with lost-tracking samples."
    )
    parser.add_argument(
        "--base",
        default=str(DEFAULT_BASE),
        help=f"Base dataset containing images/ and labels/ (default: {DEFAULT_BASE})",
    )
    parser.add_argument(
        "--lost-root",
        default=str(DEFAULT_LOST_ROOT),
        help=f"Root containing lost-tracking session folders (default: {DEFAULT_LOST_ROOT})",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help=f"New merged dataset directory (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument("--num-classes", type=int, default=24)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace the output directory if it already exists.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and report samples without copying files.",
    )
    args = parser.parse_args()

    merge_datasets(
        base_dir=Path(args.base),
        lost_root=Path(args.lost_root),
        output_dir=Path(args.output),
        num_classes=args.num_classes,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
