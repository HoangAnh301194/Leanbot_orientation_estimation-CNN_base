import os
import cv2
import shutil
from ultralytics import YOLO

def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    original_pt_path = os.path.join(current_dir, '..', 'models', 'best_24Class_Soft_Angular_BCE.pt')
    test_dir = os.path.join(current_dir, '..', '24class_test_images')
    
    # THƯ MỤC CHỨA CÁC ĐỊNH DẠNG MODEL LƯỢNG TỬ
    quantized_dir = os.path.join(current_dir, '..', 'models', 'quantized_models_full')
    os.makedirs(quantized_dir, exist_ok=True)
    
    # Copy model gốc thành 3 bản để export không bị trùng tên (ghi đè)
    pt_fp32_path = os.path.join(quantized_dir, 'model_fp32.pt')
    pt_fp16_path = os.path.join(quantized_dir, 'model_fp16.pt')
    pt_int8_path = os.path.join(quantized_dir, 'model_int8.pt')
    
    shutil.copy(original_pt_path, pt_fp32_path)
    shutil.copy(original_pt_path, pt_fp16_path)
    shutil.copy(original_pt_path, pt_int8_path)
    
    # 1. Tìm toàn bộ ảnh test
    image_files = []
    if os.path.exists(test_dir):
        for f in os.listdir(test_dir):
            if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                image_files.append(os.path.join(test_dir, f))
    if not image_files:
        print("[ERROR] Không tìm thấy ảnh test trong thư mục.")
        return
        
    print("="*110)
    print(" BƯỚC 1: TIẾN HÀNH EXPORT CÁC ĐỊNH DẠNG MODEL (FP32, FP16, INT8)")
    print(f" (Models lưu tại: {quantized_dir})")
    print("="*110)
    
    # Export FP32
    print("\n[INFO] Đang Export ONNX và OpenVINO (FP32)...")
    model_fp32 = YOLO(pt_fp32_path)
    onnx_fp32_path = model_fp32.export(format="onnx", imgsz=640, half=False)
    openvino_fp32_path = model_fp32.export(format="openvino", imgsz=640, half=False)
    
    # Export FP16
    print("\n[INFO] Đang Export ONNX và OpenVINO (FP16)...")
    model_fp16 = YOLO(pt_fp16_path)
    onnx_fp16_path = model_fp16.export(format="onnx", imgsz=640, half=True)
    openvino_fp16_path = model_fp16.export(format="openvino", imgsz=640, half=True)
    
    # Export INT8
    print("\n[INFO] Đang Export OpenVINO (INT8)...")
    print("Lưu ý: OpenVINO INT8 Export sẽ sinh ra dữ liệu calibration mặc định nếu không truyền data!")
    model_int8 = YOLO(pt_int8_path)
    openvino_int8_path = model_int8.export(format="openvino", imgsz=640, int8=True)
    
    # ONNX INT8 Dynamic Quantization
    print("\n[INFO] Đang lượng tử hóa thủ công ONNX (INT8) bằng ONNX Runtime...")
    onnx_int8_path = os.path.join(quantized_dir, 'model_int8.onnx')
    try:
        from onnxruntime.quantization import quantize_dynamic, QuantType
        quantize_dynamic(
            model_input=onnx_fp32_path,
            model_output=onnx_int8_path,
            weight_type=QuantType.QUInt8
        )
        print("[INFO] Lượng tử hóa ONNX INT8 thành công!")
    except ImportError:
        print("[WARNING] Thiếu onnxruntime. Bỏ qua ONNX INT8. (Cài bằng: pip install onnxruntime)")
        onnx_int8_path = None
    except Exception as e:
        print(f"[ERROR] Lỗi khi lượng tử ONNX INT8: {e}")
        onnx_int8_path = None
    
    print("\n" + "="*110)
    print(f" BƯỚC 2: TIẾN HÀNH BENCHMARK TRÊN {len(image_files)} ẢNH TEST (Độ phân giải 640x640)")
    print("="*110)
    
    formats = {
        "PyTorch (Gốc FP32)": original_pt_path,
        "ONNX (FP32)": onnx_fp32_path,
        "OpenVINO (FP32)": openvino_fp32_path,
        "ONNX (FP16)": onnx_fp16_path,
        "OpenVINO (FP16)": openvino_fp16_path,
        "OpenVINO (INT8)": openvino_int8_path
    }
    if onnx_int8_path and os.path.exists(onnx_int8_path):
        formats["ONNX (INT8)"] = onnx_int8_path
    
    overall_stats = {fmt: [0.0, 0.0, 0.0] for fmt in formats.keys()}
    num_runs_per_img = 30
    
    for fmt_name, path in formats.items():
        print(f"[INFO] Đang chạy vòng lặp đánh giá mô hình: {fmt_name} ...")
        # Load model for current format
        try:
            model = YOLO(path)
        except Exception as e:
            print(f"[ERROR] Không thể load model {fmt_name} tại {path}: {e}")
            continue

        sum_pre, sum_inf, sum_post = 0.0, 0.0, 0.0
        
        for img_path in image_files:
            test_frame = cv2.imread(img_path)
            
            is_half = ("FP16" in fmt_name)
            
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
                
        total_runs = len(image_files) * num_runs_per_img
        overall_stats[fmt_name][0] = sum_pre / total_runs
        overall_stats[fmt_name][1] = sum_inf / total_runs
        overall_stats[fmt_name][2] = sum_post / total_runs
        
    print("\n" + "="*110)
    print(" BẢNG SO SÁNH TỐC ĐỘ (FP32 vs FP16 vs INT8) (IMGSZ = 640x640)")
    print("="*110)
    print(f"| {'Định dạng Model':<20} | {'Tiền xử lý (ms)':<15} | {'Suy luận (ms)':<15} | {'Hậu xử lý (ms)':<15} | {'Ước tính FPS':<12} |")
    print("|" + "-"*22 + "|" + "-"*17 + "|" + "-"*17 + "|" + "-"*17 + "|" + "-"*14 + "|")
    
    for fmt_name, stats in overall_stats.items():
        if sum(stats) == 0:
            print(f"| {fmt_name:<20} | {'FAILED':<15} | {'FAILED':<15} | {'FAILED':<15} | {'FAILED':<12} |")
            continue
        avg_pre, avg_inf, avg_post = stats
        total_time = avg_pre + avg_inf + avg_post
        fps = 1000.0 / total_time if total_time > 0 else 0
        print(f"| {fmt_name:<20} | {avg_pre:>11.2f} ms | {avg_inf:>11.2f} ms | {avg_post:>11.2f} ms | {fps:>9.2f} FPS |")
    print("="*110)

if __name__ == '__main__':
    main()
