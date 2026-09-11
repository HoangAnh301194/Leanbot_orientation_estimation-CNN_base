import os
import cv2
import shutil
from ultralytics import YOLO

def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    original_pt_path = os.path.join(current_dir, '..', 'models', 'YOLO11n_versions', 'Soft_Angular_BCE_yolo11n.pt')
    test_dir = os.path.join(current_dir, '..', '24class_test_images')
    
    # TẠO THƯ MỤC CHỨA MODEL LƯỢNG TỬ HÓA
    quantized_dir = os.path.join(current_dir, '..', 'models', 'YOLO11n_versions','quantized_fp16')
    os.makedirs(quantized_dir, exist_ok=True)
    
    # Mẹo: Copy model gốc sang thư mục quantized_fp16 để Ultralytics tự động xuất file vào chung folder này
    pt_model_path = os.path.join(quantized_dir, 'Soft_Angular_BCE_yolo11n.pt')
    if not os.path.exists(pt_model_path):
        shutil.copy(original_pt_path, pt_model_path)
    
    # 1. Tìm toàn bộ ảnh test
    image_files = []
    if os.path.exists(test_dir):
        for f in os.listdir(test_dir):
            if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                image_files.append(os.path.join(test_dir, f))
    if not image_files:
        print("[LỖI] Không tìm thấy ảnh test trong thư mục.")
        return
        
    # 2. Export Model sang chuẩn FP16
    print("="*85)
    print(" BƯỚC 1: TIẾN HÀNH EXPORT MODEL SANG ONNX VÀ OPENVINO (LƯỢNG TỬ HÓA FP16)")
    print(f" (Tất cả file Model sẽ được gom chung tại: {quantized_dir})")
    print("="*85)
    
    model_pt = YOLO(pt_model_path)
    
    # Export OpenVINO FP16
    print("\n[INFO] Đang Export sang định dạng OpenVINO (Quantize FP16)...")
    openvino_fp16_path = model_pt.export(format="openvino", imgsz=640, half=True)
    
    # 3. Chuẩn bị Benchmark
    print("\n" + "="*85)
    print(f" BƯỚC 2: TIẾN HÀNH BENCHMARK TRÊN {len(image_files)} ẢNH TEST (Độ phân giải 640x640)")
    print("="*85)
    
    # Định nghĩa danh sách các định dạng cần so sánh
    formats = {
        "PyTorch (FP32 Gốc)": original_pt_path,
        "OpenVINO (FP16)": openvino_fp16_path
    }
    
    overall_stats = {fmt: [0.0, 0.0, 0.0] for fmt in formats.keys()}
    num_runs_per_img = 30 # Chạy 30 vòng mỗi ảnh cho từng format
    
    for fmt_name, path in formats.items():
        print(f"[INFO] Đang chạy vòng lặp đánh giá mô hình: {fmt_name} ...")
        model = YOLO(path)
        sum_pre, sum_inf, sum_post = 0.0, 0.0, 0.0
        
        for img_path in image_files:
            test_frame = cv2.imread(img_path)
            
            is_half = (fmt_name == "PyTorch (FP16)")
            # Warmup engine
            for _ in range(3):
                _ = model.predict(source=test_frame, imgsz=640, verbose=False, half=is_half)
                
            # Bắt đầu đo
            for _ in range(num_runs_per_img):
                results = model.predict(source=test_frame, imgsz=640, verbose=False, half=is_half)
                speed = results[0].speed
                sum_pre += speed['preprocess']
                sum_inf += speed['inference']
                sum_post += speed['postprocess']
                
        # Tính trung bình cộng của TOÀN BỘ ảnh test x 30 vòng lặp
        total_runs = len(image_files) * num_runs_per_img
        overall_stats[fmt_name][0] = sum_pre / total_runs
        overall_stats[fmt_name][1] = sum_inf / total_runs
        overall_stats[fmt_name][2] = sum_post / total_runs
        
    # 4. In bảng kết quả
    print("\n" + "="*85)
    print(" BẢNG SO SÁNH TỐC ĐỘ (AVERAGE 4 ẢNH) - QUANTIZATION FP16 (IMGSZ = 640x640)")
    print("="*85)
    print(f"{'Định dạng Model':<20} | {'Tiền xử lý (ms)':<15} | {'Suy luận (ms)':<15} | {'Hậu xử lý (ms)':<15} | {'Ước tính FPS':<10}")
    print("-" * 85)
    
    for fmt_name, stats in overall_stats.items():
        avg_pre, avg_inf, avg_post = stats
        total_time = avg_pre + avg_inf + avg_post
        fps = 1000.0 / total_time if total_time > 0 else 0
        print(f"{fmt_name:<20} | {avg_pre:>11.2f} ms | {avg_inf:>11.2f} ms | {avg_post:>11.2f} ms | {fps:>8.2f} FPS")
    print("="*85)

if __name__ == '__main__':
    main()
