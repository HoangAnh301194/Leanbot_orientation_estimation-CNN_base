import os
import cv2
import numpy as np
from ultralytics import YOLO

def run_benchmark():
    # Lấy thư mục chứa script hiện tại để làm đường dẫn động
    current_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(current_dir, 'best_24Class_Soft_Angular_BCE.pt')
    
    # Đường dẫn thư mục chứa ảnh test
    test_dir = os.path.join(current_dir, '..', '24class_test_images')
    
    # Quét toàn bộ file ảnh trong thư mục
    image_files = []
    if os.path.exists(test_dir):
        for f in os.listdir(test_dir):
            if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                image_files.append(f)
                
    if not image_files:
        print(f"[LỖI] Không tìm thấy ảnh (.jpg/.png) nào trong thư mục: {test_dir}")
        return
        
    print(f"[INFO] Đã tìm thấy {len(image_files)} ảnh test trong thư mục.")
    print(f"[INFO] Đang tải mô hình: {model_path} ...\n")
    model = YOLO(model_path)
    
    # Các kích thước cần kiểm tra từ 640 xuống 320
    test_sizes = [640, 512, 416, 320]
    
    # Từ điển lưu trữ kết quả để tính TRUNG BÌNH TỔNG CỦA MỌI ẢNH
    overall_stats = {size: [0.0, 0.0, 0.0] for size in test_sizes}
    # Chạy 30 lần mỗi ảnh để tiết kiệm thời gian (Do có nhiều ảnh)
    num_runs_per_img = 30 
    
    # Lặp qua từng ảnh một
    for img_name in image_files:
        img_path = os.path.join(test_dir, img_name)
        test_frame = cv2.imread(img_path)
        
        print("="*85)
        print(f" KẾT QUẢ CHO ẢNH: {img_name}")
        print("="*85)
        print(f"{'Kích thước (imgsz)':<20} | {'Tiền xử lý (ms)':<15} | {'Suy luận (ms)':<15} | {'Hậu xử lý (ms)':<15} | {'Ước tính FPS':<10}")
        print("-" * 85)
        
        for size in test_sizes:
            # 1. Warm-up
            for _ in range(5):
                _ = model.predict(source=test_frame, imgsz=size, verbose=False)
                
            # 2. Benchmark thực tế
            sum_pre, sum_inf, sum_post = 0.0, 0.0, 0.0
            for _ in range(num_runs_per_img):
                results = model.predict(source=test_frame, imgsz=size, verbose=False)
                speed_dict = results[0].speed
                sum_pre += speed_dict['preprocess']
                sum_inf += speed_dict['inference']
                sum_post += speed_dict['postprocess']
                
            # 3. Tính toán kết quả cho ảnh này
            avg_pre = sum_pre / num_runs_per_img
            avg_inf = sum_inf / num_runs_per_img
            avg_post = sum_post / num_runs_per_img
            
            # Cộng dồn vào bảng tổng
            overall_stats[size][0] += avg_pre
            overall_stats[size][1] += avg_inf
            overall_stats[size][2] += avg_post
            
            total_time_ms = avg_pre + avg_inf + avg_post
            est_fps = 1000.0 / total_time_ms if total_time_ms > 0 else 0
            
            size_str = f"{size}x{size}"
            print(f"{size_str:<20} | {avg_pre:>11.2f} ms | {avg_inf:>11.2f} ms | {avg_post:>11.2f} ms | {est_fps:>8.2f} FPS")
        print("\n")
        
    # IN RA BẢNG TRUNG BÌNH TỔNG KẾT
    print("="*85)
    print(f" BẢNG TRUNG BÌNH CHUNG CỦA TẤT CẢ {len(image_files)} ẢNH TEST")
    print("="*85)
    print(f"{'Kích thước (imgsz)':<20} | {'Tiền xử lý (ms)':<15} | {'Suy luận (ms)':<15} | {'Hậu xử lý (ms)':<15} | {'Ước tính FPS':<10}")
    print("-" * 85)
    
    for size in test_sizes:
        avg_pre = overall_stats[size][0] / len(image_files)
        avg_inf = overall_stats[size][1] / len(image_files)
        avg_post = overall_stats[size][2] / len(image_files)
        
        total_time_ms = avg_pre + avg_inf + avg_post
        est_fps = 1000.0 / total_time_ms if total_time_ms > 0 else 0
        
        size_str = f"{size}x{size}"
        print(f"{size_str:<20} | {avg_pre:>11.2f} ms | {avg_inf:>11.2f} ms | {avg_post:>11.2f} ms | {est_fps:>8.2f} FPS")
    print("="*85)

if __name__ == '__main__':
    run_benchmark()
