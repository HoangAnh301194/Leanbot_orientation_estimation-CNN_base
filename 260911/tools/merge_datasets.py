"""
merge_datasets.py
Hợp nhất datasets_0 và datasets_24class_640 vào một thư mục datasets/ duy nhất.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
from collections import defaultdict
from pathlib import Path
import sys

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DEFAULT_DATASETS_0 = PROJECT_ROOT / "datasets_0"
DEFAULT_DATASETS_NEW = PROJECT_ROOT / "datasets_24class_640"
DEFAULT_OUTPUT = PROJECT_ROOT / "datasets"


def merge_datasets(
    datasets_0_dir: Path,
    datasets_new_dir: Path,
    output_dir: Path,
    dry_run: bool = False,
):
    print("=" * 60)
    print("[*] BẮT ĐẦU HỢP NHẤT DATASET")
    print(f"    Dataset cũ (datasets_0)  : {datasets_0_dir}")
    print(f"    Dataset mới (24class_640): {datasets_new_dir}")
    print(f"    Thư mục đầu ra           : {output_dir}")
    print("=" * 60)

    if not datasets_0_dir.exists():
        raise SystemExit(f"[ERROR] Không tìm thấy datasets_0: {datasets_0_dir}")
    if not datasets_new_dir.exists():
        raise SystemExit(f"[ERROR] Không tìm thấy datasets_new: {datasets_new_dir}")

    out_images_dir = output_dir / "images"
    out_labels_dir = output_dir / "labels"

    if not dry_run:
        if out_images_dir.exists():
            shutil.rmtree(out_images_dir)
        if out_labels_dir.exists():
            shutil.rmtree(out_labels_dir)
        out_images_dir.mkdir(parents=True, exist_ok=True)
        out_labels_dir.mkdir(parents=True, exist_ok=True)

    # 1. Đọc manifest cũ
    manifest_0_path = datasets_0_dir / "manifest.json"
    manifest_0 = []
    if manifest_0_path.exists():
        with open(manifest_0_path, "r", encoding="utf-8") as f:
            manifest_0 = json.load(f)
    manifest_0_by_fn = {item["filename"]: item for item in manifest_0}

    # 2. Đọc manifest mới
    manifest_new_path = datasets_new_dir / "manifest.json"
    manifest_new = []
    if manifest_new_path.exists():
        with open(manifest_new_path, "r", encoding="utf-8") as f:
            manifest_new = json.load(f)
    manifest_new_by_fn = {item["filename"]: item for item in manifest_new}

    unified_manifest = []
    current_idx = 0
    class_counts = defaultdict(int)
    group_counts = defaultdict(int)
    total_bboxes = 0

    # 3. Xử lý phần 1: datasets_0
    images_0 = sorted((datasets_0_dir / "images").glob("*.jpg"))
    print(f"\n[1/2] Đang xử lý {len(images_0)} ảnh từ datasets_0...")
    for img_p in images_0:
        fn = img_p.name
        lbl_p = datasets_0_dir / "labels" / f"{img_p.stem}.txt"
        
        new_name = f"{current_idx:06d}"
        dst_img = out_images_dir / f"{new_name}.jpg"
        dst_lbl = out_labels_dir / f"{new_name}.txt"

        if not dry_run:
            shutil.copy2(img_p, dst_img)
            if lbl_p.exists():
                shutil.copy2(lbl_p, dst_lbl)
            else:
                dst_lbl.touch()

        # Đọc nhãn thống kê
        if lbl_p.exists():
            with open(lbl_p, "r", encoding="utf-8") as lf:
                for line in lf:
                    p = line.strip().split()
                    if p:
                        cid = int(p[0])
                        class_counts[cid] += 1
                        total_bboxes += 1

        info_0 = manifest_0_by_fn.get(fn, {})
        grp = info_0.get("source_group", "datasets_0_unknown")
        group_counts[grp] += 1

        unified_manifest.append({
            "index": current_idx,
            "filename": f"{new_name}.jpg",
            "source_dataset": "datasets_0",
            "source_session": info_0.get("source_session", "unknown"),
            "source_image": info_0.get("source_image", fn),
            "source_group": grp,
        })
        current_idx += 1

    # 4. Xử lý phần 2: datasets_24class_640
    images_new = sorted((datasets_new_dir / "images").glob("*.jpg"))
    print(f"[2/2] Đang xử lý {len(images_new)} ảnh từ datasets_24class_640...")
    for img_p in images_new:
        fn = img_p.name
        lbl_p = datasets_new_dir / "labels" / f"{img_p.stem}.txt"

        new_name = f"{current_idx:06d}"
        dst_img = out_images_dir / f"{new_name}.jpg"
        dst_lbl = out_labels_dir / f"{new_name}.txt"

        if not dry_run:
            shutil.copy2(img_p, dst_img)
            if lbl_p.exists():
                shutil.copy2(lbl_p, dst_lbl)
            else:
                dst_lbl.touch()

        # Đọc nhãn thống kê
        if lbl_p.exists():
            with open(lbl_p, "r", encoding="utf-8") as lf:
                for line in lf:
                    p = line.strip().split()
                    if p:
                        cid = int(p[0])
                        class_counts[cid] += 1
                        total_bboxes += 1

        info_new = manifest_new_by_fn.get(fn, {})
        grp = "new_setup_24class_260911"
        group_counts[grp] += 1

        unified_manifest.append({
            "index": current_idx,
            "filename": f"{new_name}.jpg",
            "source_dataset": "datasets_24class_640",
            "source_session": info_new.get("source_session", "unknown"),
            "source_image": info_new.get("source_image", fn),
            "source_group": grp,
        })
        current_idx += 1

    # 5. Lưu manifest tổng hợp
    if not dry_run:
        out_manifest_p = output_dir / "manifest.json"
        with open(out_manifest_p, "w", encoding="utf-8") as mf:
            json.dump(unified_manifest, mf, ensure_ascii=False, indent=2)
            mf.write("\n")

    print("\n" + "=" * 60)
    print(f"[DONE] Hoàn tất hợp nhất vào {output_dir}")
    print(f"       Tổng số ảnh        : {current_idx}")
    print(f"       Tổng bounding box  : {total_bboxes}")
    print(f"       Số class duy nhất  : {len(class_counts)}")
    print("\n[PHÂN BỐ THEO NHÓM NGUỒN]:")
    for grp, cnt in sorted(group_counts.items()):
        print(f"  - {grp:26s}: {cnt:3d} ảnh")

    print("\n[PHÂN BỐ BOUNDING BOX THEO CLASS]:")
    for cid in range(24):
        print(f"  - Class {cid:2d}: {class_counts.get(cid, 0):3d} bboxes")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge datasets_0 and datasets_24class_640")
    parser.add_argument("--base", type=str, default=str(DEFAULT_DATASETS_0), help="Path to datasets_0")
    parser.add_argument("--new", type=str, default=str(DEFAULT_DATASETS_NEW), help="Path to datasets_24class_640")
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT), help="Path to output datasets")
    parser.add_argument("--dry_run", action="store_true", help="Dry run without copying")
    args = parser.parse_args()

    merge_datasets(
        datasets_0_dir=Path(args.base),
        datasets_new_dir=Path(args.new),
        output_dir=Path(args.output),
        dry_run=args.dry_run,
    )
