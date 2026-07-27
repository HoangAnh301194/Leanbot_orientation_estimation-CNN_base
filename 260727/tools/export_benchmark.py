import os
import cv2
from ultralytics import YOLO

def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    pt_model_path = os.path.join(current_dir, '..', 'models', 'best_24Class_Soft_Angular_BCE.pt')
    test_dir = os.path.join(current_dir, '..', '24class_test_images')
    
    # 1. Tìm toàn bộ ảnh test
    image_files = []
    if os.path.exists(test_dir):
        for f in os.listdir(test_dir):
            if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                image_files.append(os.path.join(test_dir, f))
    if not image_files:
        print("[LỖI] Không tìm thấy ảnh test trong thư mục.")
        return
        
    # 2. Export Model (Sử dụng imgsz=416 như đề xuất)
    print("="*85)
    print(" BƯỚC 1: TIẾN HÀNH EXPORT MODEL SANG ONNX VÀ OPENVINO")
    print("="*85)
    
    model_pt = YOLO(pt_model_path)
    
    # Export ONNX
    print("\n[INFO] Đang Export sang định dạng ONNX...")
    # Việc gọi hàm export có thể tốn vài phút và cần tải thư viện nếu máy chưa có
    onnx_path = model_pt.export(format="onnx", imgsz=640, half=False)
    
    # Export OpenVINO
    print("\n[INFO] Đang Export sang định dạng OpenVINO...")
    openvino_path = model_pt.export(format="openvino", imgsz=640, half=False)
    
    # 3. Chuẩn bị Benchmark
    print("\n" + "="*85)
    print(f" BƯỚC 2: TIẾN HÀNH BENCHMARK TRÊN {len(image_files)} ẢNH TEST (Cố định độ phân giải 640x640)")
    print("="*85)
    
    # Định nghĩa danh sách các định dạng cần so sánh
    formats = {
        "PyTorch Gốc (.pt)": pt_model_path,
        "ONNX Runtime": onnx_path,
        "OpenVINO (Intel)": openvino_path
    }
    
    overall_stats = {fmt: [0.0, 0.0, 0.0] for fmt in formats.keys()}
    num_runs_per_img = 30 # Chạy 30 vòng mỗi ảnh cho từng format
    
    for fmt_name, path in formats.items():
        print(f"[INFO] Đang chạy vòng lặp đánh giá mô hình: {fmt_name} ...")
        # Load model với format tương ứng
        model = YOLO(path)
        sum_pre, sum_inf, sum_post = 0.0, 0.0, 0.0
        
        for img_path in image_files:
            test_frame = cv2.imread(img_path)
            
            # Warmup engine
            for _ in range(3):
                _ = model.predict(source=test_frame, imgsz=640, verbose=False)
                
            # Bắt đầu đo
            for _ in range(num_runs_per_img):
                results = model.predict(source=test_frame, imgsz=640, verbose=False)
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
    print(" BẢNG SO SÁNH TỐC ĐỘ (AVERAGE 4 ẢNH) GIỮA CÁC RUNTIME PHẦN CỨNG (IMGSZ = 640x640)")
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
