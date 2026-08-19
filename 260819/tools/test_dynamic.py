import cv2
import numpy as np
from ultralytics import YOLO

def main():
    model_path = r'models\best_24Class_Soft_Angular_BCE_openvino_model'
    
    # Sử dụng YOLO để load openvino model
    model = YOLO(model_path, task='detect')
    
    print(f"[INFO] Đã load model OpenVINO từ: {model_path}")
    
    # Tạo ảnh đen 320x320
    test_size = 320
    img = np.zeros((test_size, test_size, 3), dtype=np.uint8)
    
    print(f"[INFO] Bắt đầu inference với ảnh {test_size}x{test_size}...")
    try:
        results = model.predict(source=img, imgsz=test_size, verbose=False)
        print(f"[SUCCESS] Inference thành công! Shape đầu ra: {results[0].boxes.shape if len(results) > 0 else 'No boxes'}")
    except Exception as e:
        print("[ERROR] Inference thất bại:", e)

if __name__ == "__main__":
    main()
