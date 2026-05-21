import argparse
import json
import shutil
from pathlib import Path
from datetime import datetime
import sys

# Force UTF-8 encoding for standard output to avoid charmap errors on Windows terminals
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def main():
    parser = argparse.ArgumentParser(description="Gom các thư mục góc thành một thư mục Class chuẩn để auto label.")
    parser.add_argument("--dataset_name", required=True, help="Tên dataset mới (ví dụ: 8class, 24class)")
    parser.add_argument("--folders", nargs="+", required=True, help="Danh sách các folder trong root_images (ví dụ: angle_0 angle_p15 angle_m15)")
    parser.add_argument("--class_name", required=True, help="Tên class để lưu file (ví dụ: Leanbot_0)")
    parser.add_argument("--class_id", type=int, required=True, help="ID của class (ví dụ: 0)")
    parser.add_argument("--bg_path", type=str, default=None, help="Đường dẫn đến file background (không bắt buộc)")
    parser.add_argument("--root_images_dir", type=str, default="root_images", help="Thư mục chứa ảnh gốc")
    parser.add_argument("--output_root", type=str, default="datasets", help="Thư mục gốc chứa dataset mới")

    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    root_images_dir = project_root / args.root_images_dir
    
    # Tạo cấu trúc thư mục giả lập session trong raw_image của dataset mới
    # VD: datasets/8class/raw_image/Leanbot_0/
    session_dir = project_root / args.output_root / args.dataset_name / "raw_image" / args.class_name
    raw_images_dir = session_dir / "raw_images"
    backgrounds_dir = session_dir / "backgrounds"

    # Xóa sạch thư mục cũ nếu đã tồn tại để tránh bị lẫn dữ liệu từ lần chạy trước
    if raw_images_dir.exists():
        shutil.rmtree(raw_images_dir)
    if backgrounds_dir.exists():
        shutil.rmtree(backgrounds_dir)

    raw_images_dir.mkdir(parents=True, exist_ok=True)
    backgrounds_dir.mkdir(parents=True, exist_ok=True)

    copied_images = []
    
    # Copy toàn bộ ảnh từ các thư mục góc đã chọn
    print(f"[*] Đang xử lý tạo class '{args.class_name}' (ID: {args.class_id})...")
    for folder_name in args.folders:
        src_folder = root_images_dir / folder_name
        if not src_folder.exists():
            print(f"    [CẢNH BÁO] Không tìm thấy thư mục: {src_folder}")
            continue
            
        for img_path in src_folder.glob("*.jpg"):
            dst_path = raw_images_dir / img_path.name
            shutil.copy2(img_path, dst_path)
            copied_images.append(img_path.name)
            
    copied_images.sort()

    background_files = []
    # Xử lý background nếu được truyền vào
    if args.bg_path and Path(args.bg_path).exists():
        bg_src = Path(args.bg_path)
        bg_dst = backgrounds_dir / bg_src.name
        shutil.copy2(bg_src, bg_dst)
        background_files.append(bg_src.name)

    # Sinh file cấu hình session_metadata.json
    metadata = {
        "session_name": args.class_name,
        "session_dir": str(session_dir.absolute()),
        "created_at": now_stamp(),
        "class_name": args.class_name,
        "class_id": args.class_id,
        "background_count": len(background_files),
        "raw_image_count": len(copied_images),
        "background_files": background_files,
        "raw_image_files": copied_images,
        "folder_description": {
            "backgrounds": "Reference background images captured in the session.",
            "raw_images": "Images containing Leanbot that will be processed by the labeling tool."
        }
    }

    metadata_path = session_dir / "session_metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"[THÀNH CÔNG] Dataset class lưu tại: {session_dir}")
    print(f"             Đã copy {len(copied_images)} ảnh từ {len(args.folders)} góc.")
    if not background_files:
        print(f"             [LƯU Ý] Thư mục backgrounds/ đang trống. Hãy copy 1 ảnh background vào đây để tool tự động gán nhãn có thể hoạt động!")

if __name__ == "__main__":
    main()
