"""
build_dataset.py
Gộp toàn bộ ảnh (aligned_images) và label (labels) từ tool1_output/session_X
vào một thư mục datasets/ duy nhất, đánh số lại tên file liên tục.

Cấu trúc output:
    datasets/
    ├── images/
    │   ├── 000000.jpg
    │   ├── 000001.jpg
    │   └── ...
    └── labels/
        ├── 000000.txt
        ├── 000001.txt
        └── ...

Lưu ý:
- Không xóa tool1_output gốc, chỉ copy và rename.
- Thứ tự: session được sắp xếp theo tên (thời gian), ảnh trong mỗi session theo tên file gốc.
- Bỏ qua các file label rỗng (0 byte) hoặc ảnh không có label tương ứng.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
TOOL1_OUTPUT = PROJECT_ROOT / "crop_images"
DATASET_ROOT = PROJECT_ROOT / "datasets"


def collect_pairs(tool1_dir: Path, skip_empty: bool = True):
    """
    Thu thập tất cả cặp (image_path, label_path) từ tool1_output.
    Sắp xếp theo tên session rồi theo tên file.
    """
    pairs = []
    sessions = sorted([d for d in tool1_dir.iterdir() if d.is_dir()])

    for session_dir in sessions:
        images_dir = session_dir / "aligned_images"
        labels_dir = session_dir / "labels"

        if not images_dir.exists() or not labels_dir.exists():
            continue

        image_files = sorted(images_dir.glob("*.jpg"))
        for img_path in image_files:
            label_path = labels_dir / f"{img_path.stem}.txt"

            if not label_path.exists():
                continue

            # Bỏ qua label rỗng nếu được yêu cầu
            if skip_empty and label_path.stat().st_size == 0:
                continue

            pairs.append((img_path, label_path, session_dir.name))

    return pairs


def build_dataset(
    tool1_dir: Path = TOOL1_OUTPUT,
    dataset_dir: Path = DATASET_ROOT,
    skip_empty: bool = True,
    dry_run: bool = False,
):
    """Copy ảnh và label vào datasets/, đánh số lại từ 000000."""
    pairs = collect_pairs(tool1_dir, skip_empty=skip_empty)

    if not pairs:
        print("[WARN] No image-label pairs found in tool1_output.")
        return

    images_dir = dataset_dir / "images"
    labels_dir = dataset_dir / "labels"

    if not dry_run:
        # Clear existing directories to avoid polluting with old data
        if images_dir.exists():
            shutil.rmtree(images_dir)
        if labels_dir.exists():
            shutil.rmtree(labels_dir)
            
        images_dir.mkdir(parents=True, exist_ok=True)
        labels_dir.mkdir(parents=True, exist_ok=True)

    manifest = []
    class_counts = {}
    total_bboxes = 0

    for idx, (img_src, lbl_src, session_name) in enumerate(pairs):
        new_name = f"{idx:06d}"
        img_dst = images_dir / f"{new_name}.jpg"
        lbl_dst = labels_dir / f"{new_name}.txt"

        if dry_run:
            print(f"  [{idx:4d}] {session_name}/{img_src.name} -> {new_name}.jpg")
            label_to_parse = lbl_src
        else:
            shutil.copy2(img_src, img_dst)
            shutil.copy2(lbl_src, lbl_dst)
            label_to_parse = lbl_dst

        try:
            with open(label_to_parse, 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split()
                    if parts:
                        cls_id = int(parts[0])
                        class_counts[cls_id] = class_counts.get(cls_id, 0) + 1
                        total_bboxes += 1
        except Exception as e:
            pass

        manifest.append({
            "index": idx,
            "filename": f"{new_name}.jpg",
            "source_session": session_name,
            "source_image": img_src.name,
        })

    # Lưu manifest để truy vết nguồn gốc
    if not dry_run:
        manifest_path = dataset_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    print(f"\n[DONE] Merged {len(pairs)} image-label pairs into {dataset_dir}")
    print(f"       Images : {images_dir}")
    print(f"       Labels : {labels_dir}")

    # Stats per session
    session_counts = {}
    for _, _, sn in pairs:
        session_counts[sn] = session_counts.get(sn, 0) + 1

    print(f"\n[STATS] Distribution by session:")
    for sn in sorted(session_counts):
        print(f"  {sn}: {session_counts[sn]} images")

    print(f"\n[DATASET INFO]")
    print(f"  Total images        : {len(pairs)}")
    print(f"  Total bounding boxes: {total_bboxes}")
    print(f"  Total unique classes: {len(class_counts)}")
    print(f"  Class breakdown:")
    for cls_id in sorted(class_counts.keys()):
        print(f"    - Class {cls_id}: {class_counts[cls_id]} bounding boxes")


def main():
    parser = argparse.ArgumentParser(
        description="Gộp ảnh và label từ tool1_output vào datasets/."
    )
    parser.add_argument(
        "--input", default=str(TOOL1_OUTPUT),
        help=f"Thư mục tool1_output (mặc định: {TOOL1_OUTPUT})",
    )
    parser.add_argument(
        "--output", default=str(DATASET_ROOT),
        help=f"Thư mục output (mặc định: {DATASET_ROOT})",
    )
    parser.add_argument(
        "--include_empty", action="store_true",
        help="Bao gồm cả ảnh có label rỗng (không có Leanbot).",
    )
    parser.add_argument(
        "--dry_run", action="store_true",
        help="Chỉ in danh sách, không copy file.",
    )
    args = parser.parse_args()

    build_dataset(
        tool1_dir=Path(args.input),
        dataset_dir=Path(args.output),
        skip_empty=not args.include_empty,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
