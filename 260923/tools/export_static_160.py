from ultralytics import YOLO
import argparse
import os

def main():
    parser = argparse.ArgumentParser(description="Export YOLO model to OpenVINO static 160x160 FP16")
    parser.add_argument("--weights", default=r"models\YOLO11n_versions\Soft_Angular_BCE_yolo11n.pt", help="Path to the .pt model")
    args = parser.parse_args()

    if not os.path.exists(args.weights):
        print(f"[ERROR] Không tìm thấy file weights tại: {args.weights}")
        return

    print(f"[INFO] Đang tải mô hình: {args.weights}")
    model = YOLO(args.weights)

    print("[INFO] Đang export sang OpenVINO (FP16, imgsz=160, static)...")
    # Export với imgsz=160, half=True (FP16), và dynamic=False (mặc định)
    import shutil
    export_path = model.export(format="openvino", imgsz=160, half=True, dynamic=False)
    
    # Đổi tên thư mục để dễ nhận biết (thêm _static_160)
    new_export_path = export_path.replace("_openvino_model", "_static_160_openvino_model")
    if export_path != new_export_path:
        if os.path.exists(new_export_path):
            shutil.rmtree(new_export_path)
        os.rename(export_path, new_export_path)
        export_path = new_export_path
    
    print(f"\n[SUCCESS] Đã export thành công!")
    print(f"[INFO] Model lưu tại: {export_path}")

if __name__ == "__main__":
    main()
