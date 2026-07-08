import sys
from pathlib import Path
import cv2
from ultralytics import YOLO
from collections import defaultdict

# Import hàm run_low_level_inference từ script có sẵn
from export_markdown_report import run_low_level_inference

class DummyArgs:
    conf = 0.01  # Để ngưỡng thấp để lấy được hết các object
    imgsz = 640
    max_objects = 1  # Chỉ lấy object bự nhất (chính là cái crop)

def main():
    model_path = Path(__file__).resolve().parents[1] / "models" / "best_24Class_Soft_Angular_BCE.pt"
    if not model_path.exists():
        print("Không tìm thấy model best.pt")
        return
        
    obj_dir = Path(__file__).resolve().parent.parent / "detect_crop_output" / "objects" / "Leanbot_p180_001"
    if not obj_dir.exists():
        print(f"Không tìm thấy thư mục: {obj_dir}")
        return

    print("Loading model...")
    model = YOLO(str(model_path))
    
    args = DummyArgs()
    results_by_exp = {}
    
    # Tập hợp tất cả các class có score > 0.05 ở bất kỳ mức expansion nào để hiện lên bảng
    top_classes = set()

    for exp in [0, 1, 2, 3]:
        img_file = obj_dir / f"expand_{exp}.jpg"
        if not img_file.exists():
            continue
            
        frame = cv2.imread(str(img_file))
        detections = run_low_level_inference(model, frame, args)
        
        if not detections:
            results_by_exp[exp] = None
            continue
            
        det = detections[0] # Lấy detection tự tin nhất
        results_by_exp[exp] = det
        
        for cls_name, score in det["class_scores"].items():
            if score > 0.02:
                top_classes.add(cls_name)

    # Sắp xếp top_classes theo tên để in cho đẹp
    top_classes = sorted(list(top_classes))
    
    # In bảng Markdown
    header = ["Expansion", "Best Class", "Best Conf"] + top_classes
    print("\nBảng Confidence qua các mức cắt mở rộng (Expansion):")
    print("| " + " | ".join(header) + " |")
    print("|" + "|".join(["---"] * len(header)) + "|")
    
    for exp in [0, 1, 2, 3]:
        if exp not in results_by_exp:
            continue
            
        det = results_by_exp[exp]
        if det is None:
            row = [f"expand_{exp}", "No detection", "-"] + ["-"] * len(top_classes)
        else:
            row = [
                f"expand_{exp}", 
                f"`{det['best_cls']}`", 
                f"{det['best_conf']:.4f}"
            ]
            for cls_name in top_classes:
                score = det["class_scores"].get(cls_name, 0.0)
                # In đậm nếu score lớn nhất
                if cls_name == det['best_cls']:
                    row.append(f"**{score:.4f}**")
                else:
                    row.append(f"{score:.4f}")
        
        print("| " + " | ".join(row) + " |")

if __name__ == "__main__":
    main()
