import os
import sys
import torch
from ultralytics import YOLO

def main():
    model_path = r'D:\PTIT\DTT\Nguyen_Huu_Hoang_Anh\260403\Leanbot_detection\models\leanbot_colab.pt'
    if not os.path.exists(model_path):
        print(f"Không tìm thấy file: {model_path}")
        return

    print(f"==================================================")
    print(f"    ĐÁNH GIÁ THÔNG TIN CHI TIẾT MÔ HÌNH YOLO      ")
    print(f"==================================================")
    print(f"File path: {model_path}")
    
    # 1. Kích thước file
    size_mb = os.path.getsize(model_path) / (1024 * 1024)
    print(f"[1] Kích thước file: {size_mb:.2f} MB")

    # Load model
    model = YOLO(model_path)
    
    # 2. Thông tin cơ bản (Layers, Params, GFLOPs)
    print("\n[2] Kiến trúc cơ bản (YOLO Model Info):")
    model.info()

    # 3. Trích xuất Metadata nâng cao từ Checkpoint
    print("\n[3] Thông tin Metadata huấn luyện (Training Configs):")
    try:
        ckpt = torch.load(model_path, map_location='cpu', weights_only=False)
        train_args = ckpt.get('train_args', {})
        
        print(f" - Loại tác vụ (Task):        {model.task}")
        print(f" - Model nền tảng gốc:        {train_args.get('model', 'Unknown')}")
        print(f" - Kích thước ảnh (imgsz):    {train_args.get('imgsz', 'Unknown')}x{train_args.get('imgsz', 'Unknown')}")
        print(f" - Số vòng lặp (Epochs):      {train_args.get('epochs', 'Unknown')}")
        print(f" - Batch size:                {train_args.get('batch', 'Unknown')}")
        print(f" - File Dataset:              {train_args.get('data', 'Unknown')}")
        print(f" - Thiết bị train (Device):   {train_args.get('device', 'Unknown')}")
        print(f" - Bộ tối ưu (Optimizer):     {train_args.get('optimizer', 'Unknown')}")
        
        # 4. Data Augmentation
        print("\n[4] Tham số tăng cường dữ liệu (Data Augmentation):")
        print(f" - Mosaic:                    {train_args.get('mosaic', 'Unknown')}")
        print(f" - Độ xoay ảnh (degrees):     {train_args.get('degrees', 'Unknown')}")
        print(f" - Tịnh tiến (translate):     {train_args.get('translate', 'Unknown')}")
        print(f" - Scale (phóng to/thu nhỏ):  {train_args.get('scale', 'Unknown')}")
        print(f" - Xóa ngẫu nhiên (erasing):  {train_args.get('erasing', 'Unknown')}")
        
        # 5. Thông tin Classes
        print(f"\n[5] Thông tin nhãn dữ liệu (Classes):")
        print(f" - Tổng số nhãn (NC):         {len(model.names)}")
        print(f" - Danh sách các nhãn:        ")
        for idx, name in model.names.items():
            print(f"   + Class {idx:02d}: {name}")

    except Exception as e:
        print(f"Không thể đọc metadata chi tiết: {e}")

if __name__ == "__main__":
    main()
