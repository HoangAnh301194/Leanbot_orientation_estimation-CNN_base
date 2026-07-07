import os
import glob
from pathlib import Path

base_dir = Path(__file__).resolve().parents[1] / "yolo_class_bbox_results"
txt_files = glob.glob(os.path.join(base_dir, "**", "*_debug.txt"), recursive=True)

md_lines = ["| Tên ảnh | Góc độ (Thư mục) | Số object | Nhận diện Top 1 (Class & Conf) |", "|---|---|---|---|"]

for txt in sorted(txt_files):
    with open(txt, "r", encoding="utf-8") as f:
        content = f.read()
    
    lines = content.strip().split("\n")
    if len(lines) < 3: continue
    
    img_name = lines[0].replace("Image:", "").strip()
    rel_dir = lines[2].replace("Relative dir:", "").strip()
    
    if "Không phát hiện object nào." in content:
        md_lines.append(f"| {img_name} | {rel_dir} | 0 | Không có |")
    else:
        # đếm số đối tượng
        obj_count = 0
        for line in lines:
            if line.startswith("Object "):
                obj_count += 1
                
        # Lấy info của Object đầu tiên làm đại diện
        best_info = ""
        for line in lines:
            if "| Best:" in line:
                best_info = line.split("| Best:")[1].strip()
                break
        
        # Nếu có nhiều object, ta chỉ hiển thị best của obj 0, và ghi chú
        if obj_count > 1:
            best_info += f" (+ {obj_count - 1} obj khác)"
            
        md_lines.append(f"| {img_name} | {rel_dir} | {obj_count} | {best_info} |")

print("\n".join(md_lines))
