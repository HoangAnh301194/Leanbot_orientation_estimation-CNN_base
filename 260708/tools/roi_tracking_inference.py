import cv2
import numpy as np
import time
import psutil
import argparse
import csv
import os
import sys
from pathlib import Path
from datetime import datetime
from ultralytics import YOLO

# Thêm đường dẫn để import check_confidence
sys.path.append(str(Path(__file__).resolve().parent))
import check_confidence

def make_multiple_of_32(val):
    return int(np.ceil(val / 32.0) * 32)

def calculate_roi(bbox, img_w, img_h):
    x1, y1, x2, y2 = bbox
    w = x2 - x1
    h = y2 - y1
    cx = x1 + w / 2.0
    cy = y1 + h / 2.0

    roi_w = w * 2.0
    roi_h = h * 2.0

    roi_w_32 = make_multiple_of_32(roi_w)
    roi_h_32 = make_multiple_of_32(roi_h)

    roi_w_32 = min(roi_w_32, img_w)
    roi_h_32 = min(roi_h_32, img_h)

    x_min = int(cx - roi_w_32 / 2.0)
    y_min = int(cy - roi_h_32 / 2.0)

    if x_min < 0:
        x_min = 0
    elif x_min + roi_w_32 > img_w:
        x_min = img_w - roi_w_32

    if y_min < 0:
        y_min = 0
    elif y_min + roi_h_32 > img_h:
        y_min = img_h - roi_h_32

    return x_min, y_min, roi_w_32, roi_h_32

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="0", help="Camera index or video path")
    parser.add_argument("--mode", default="roi", choices=["roi", "baseline"], help="Chế độ chạy: roi hoặc baseline")
    parser.add_argument("--log", default="", help="Tên file csv để lưu log (mặc định tự tạo theo mode)")
    parser.add_argument("--no-show", action="store_true", help="Không hiển thị cửa sổ OpenCV (tránh lỗi treo GUI)")
    args = parser.parse_args()

    model_path = r'models\best_24Class_Soft_Angular_BCE_dynamic_openvino_model'
    source = args.source
    
    print("[INFO] Loading OpenVINO Model...")
    model = YOLO(model_path, task='detect')
    
    if source.isdigit():
        source = int(source)
    
    cap = cv2.VideoCapture(source)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 2560)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1440)
    
    if not cap.isOpened():
        print(f"[ERROR] Không thể mở nguồn video: {source}")
        return

    prev_roi = None
    frame_id = 0
    lost_tracking_count = 0
    
    out_dir = "benchmark"
    os.makedirs(out_dir, exist_ok=True)
    
    if args.log:
        # Nếu user truyền đường dẫn có chứa thư mục rồi thì giữ nguyên, ngược lại nhét vào benchmark/
        log_file = args.log if os.path.dirname(args.log) else os.path.join(out_dir, args.log)
    else:
        log_file = os.path.join(out_dir, f"log_{args.mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    
    # Khởi tạo Process object để đo riêng CPU của script này (tránh nhiễu từ app khác)
    current_process = psutil.Process()
    current_process.cpu_percent() # Lần gọi đầu tiên để khởi tạo mốc thời gian
    
    # Mở file CSV để ghi
    with open(log_file, mode='w', newline='') as f:
        writer = csv.writer(f)
        # Ghi header
        writer.writerow([
            "frame_id", "timestamp", "mode", "input_width", "input_height",
            "inf_time_ms", "total_proc_time_ms", "cpu_load_pct", "fps",
            "center_x", "center_y", "width", "height", "angle", "lost_count"
        ])

        print(f"[INFO] Bắt đầu Inference ({args.mode.upper()} mode). Log lưu tại: {log_file}")
        
        start_benchmark_time = time.time()
        max_duration = 30.0  # Tự động thoát sau 30 giây
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            frame_id += 1
            timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            img_h, img_w = frame.shape[:2]
            
            t0 = time.time()
            # Đo % CPU CỦA RIÊNG TIẾN TRÌNH NÀY, chia cho số nhân CPU để ra hệ quy chiếu 100%
            cpu_load = current_process.cpu_percent() / psutil.cpu_count()
            
            inference_mode = "FULL"
            offset_x, offset_y = 0, 0

            if args.mode == "roi" and prev_roi is not None:
                inference_mode = "ROI"
                rx, ry, rw, rh = prev_roi
                offset_x, offset_y = rx, ry
                inference_input = frame[ry:ry+rh, rx:rx+rw]
                input_w, input_h = rw, rh
            else:
                inference_input, params = check_confidence.training_style_crop_pad(frame)
                input_w, input_h = 640, 640
                
            results = model.predict(source=inference_input, imgsz=(input_w, input_h), verbose=False)
            result = results[0]
            
            speed = result.speed if hasattr(result, 'speed') else {'preprocess': 0, 'inference': 0, 'postprocess': 0}
            total_inf_time = speed.get('preprocess', 0) + speed.get('inference', 0) + speed.get('postprocess', 0)
            
            boxes = result.boxes.xyxy.cpu().numpy()
            confs = result.boxes.conf.cpu().numpy()
            
            if inference_mode == "FULL" and len(boxes) > 0:
                boxes = check_confidence.restore_boxes_from_training_style(boxes, params)
            
            # Trích xuất obb nếu có (để lấy góc)
            angle = 0.0
            if hasattr(result, 'obb') and result.obb is not None:
                obbs = result.obb.xywhr.cpu().numpy()
            else:
                obbs = None

            cx, cy, bw, bh = 0.0, 0.0, 0.0, 0.0
            
            if len(boxes) > 0:
                best_idx = np.argmax(confs)
                box = boxes[best_idx]
                
                orig_x1 = box[0] + offset_x
                orig_y1 = box[1] + offset_y
                orig_x2 = box[2] + offset_x
                orig_y2 = box[3] + offset_y
                best_box = [orig_x1, orig_y1, orig_x2, orig_y2]
                
                bw = orig_x2 - orig_x1
                bh = orig_y2 - orig_y1
                cx = orig_x1 + bw / 2.0
                cy = orig_y1 + bh / 2.0
                
                if obbs is not None and len(obbs) > best_idx:
                    angle = obbs[best_idx][4]

                if args.mode == "roi":
                    # Chỉ cập nhật lại vùng crop ROI sau mỗi 5 frame để giữ nguyên kích thước input cho OpenVINO,
                    # giảm tối đa chi phí recompile dynamic shape.
                    if prev_roi is None or getattr(model, 'frames_since_roi_update', 5) >= 5:
                        prev_roi = calculate_roi(best_box, img_w, img_h)
                        model.frames_since_roi_update = 1
                    else:
                        model.frames_since_roi_update += 1
                
                cv2.rectangle(frame, (int(orig_x1), int(orig_y1)), (int(orig_x2), int(orig_y2)), (0, 255, 0), 6)
            else:
                if inference_mode == "ROI":
                    lost_tracking_count += 1
                prev_roi = None
                model.frames_since_roi_update = 5  # Reset để lấy ngay ROI mới khi detect lại được

            total_proc_time = (time.time() - t0) * 1000  # ms
            fps = 1000.0 / total_proc_time if total_proc_time > 0 else 0

            # Ghi Log vào CSV
            writer.writerow([
                frame_id, timestamp, inference_mode, input_w, input_h,
                f"{total_inf_time:.2f}", f"{total_proc_time:.2f}", cpu_load, f"{fps:.2f}",
                f"{cx:.2f}", f"{cy:.2f}", f"{bw:.2f}", f"{bh:.2f}", f"{angle:.4f}", lost_tracking_count
            ])
            f.flush()  # Đảm bảo dữ liệu được ghi ngay xuống ổ cứng (chống mất data khi force close)

            if not args.no_show:
                if inference_mode == "ROI" and prev_roi is not None:
                    rx, ry, rw, rh = offset_x, offset_y, input_w, input_h
                    cv2.rectangle(frame, (rx, ry), (rx+rw, ry+rh), (0, 255, 255), 6)

                # Resize xuống 640x360 (tỷ lệ 1/4 giống hệt code gốc) để gọn gàng
                display_frame = cv2.resize(frame, (640, 360))
                
                # Hiển thị HUD trên display_frame để chữ không bị scale mờ
                cv2.putText(display_frame, f"Mode: {inference_mode} | Input: {input_w}x{input_h}", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                cv2.putText(display_frame, f"FPS: {fps:.1f} | CPU: {cpu_load}%", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                cv2.putText(display_frame, f"Lost Count: {lost_tracking_count}", (10, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

                cv2.imshow("Tracking", display_frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
            else:
                # Chế độ No-show: In log ra màn hình console thay vì bật cửa sổ GUI
                if frame_id % 10 == 0:
                    print(f"[LOG] Frame {frame_id} | Mode: {inference_mode} | FPS: {fps:.1f} | CPU: {cpu_load}%")
            
            # Tự động kết thúc sau 30 giây
            elapsed_time = time.time() - start_benchmark_time
            if elapsed_time >= max_duration:
                print(f"[INFO] Đã thu thập đủ {max_duration} giây log. Tự động kết thúc!")
                break

    cap.release()
    if not args.no_show:
        cv2.destroyAllWindows()
    print(f"[INFO] Hoàn tất. Đã lưu log vào file {log_file}")

if __name__ == "__main__":
    main()
