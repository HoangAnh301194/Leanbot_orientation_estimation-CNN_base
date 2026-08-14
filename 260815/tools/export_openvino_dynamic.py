import os
import shutil
from ultralytics import YOLO

def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    models_dir = os.path.join(current_dir, '..', 'models')
    model_path = os.path.join(models_dir, 'best_24Class_Soft_Angular_BCE.pt')
    
    dynamic_model_path = os.path.join(models_dir, 'best_24Class_Soft_Angular_BCE_dynamic.pt')
    shutil.copy(model_path, dynamic_model_path)
    
    model = YOLO(dynamic_model_path)
    
    print("[INFO] Đang export model sang định dạng OpenVINO (Dynamic Input & FP16)...")
    openvino_path = model.export(
        format="openvino",
        imgsz=640,
        dynamic=True,
        half=True
    )
    
    # Xoá file .pt phụ
    if os.path.exists(dynamic_model_path):
        os.remove(dynamic_model_path)
        
    print(f"[SUCCESS] Export hoàn tất. Model lưu tại: {openvino_path}")

if __name__ == "__main__":
    main()
