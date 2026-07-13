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
    parser.add_argument("--show", action="store_true", help="Bật cửa sổ OpenCV nếu môi trường hỗ trợ GUI")
    args = parser.parse_args()
    if not args.show:
        args.no_show = True

    full_model_path = r'models\quantized_fp16\best_24Class_Soft_Angular_BCE_openvino_model'
    tracking_model_path = r'models\best_24Class_Soft_Angular_BCE_static_160_openvino_model'
    source = args.source
    
    print("[INFO] Loading OpenVINO Models...")
    print(f"[INFO] Full detection model: {full_model_path}")
    print(f"[INFO] ROI tracking model: {tracking_model_path}")
    full_model = YOLO(full_model_path, task='detect')
    tracking_model = YOLO(tracking_model_path, task='detect')
    
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
    
    csv_header = [
        "frame_id", "timestamp", "mode", "input_width", "input_height",
        "inf_time_ms", "total_proc_time_ms", "cpu_load_pct", "fps",
        "center_x", "center_y", "width", "height", "angle", "tracking_lost"
    ]

    log_handle = None
    writer = None
    recording = False

    def start_recording():
        nonlocal log_handle, writer, recording
        if log_handle is not None:
            log_handle.close()
        log_handle = open(log_file, mode='w', newline='')
        writer = csv.writer(log_handle)
        writer.writerow(csv_header)
        log_handle.flush()
        recording = True
        print(f"[INFO] REC ON. Ghi đè log tại: {log_file}")

    def stop_recording():
        nonlocal log_handle, writer, recording, start_benchmark_time
        if log_handle is not None:
            log_handle.flush()
            log_handle.close()
        log_handle = None
        writer = None
        recording = False
        start_benchmark_time = time.time()
        print("[INFO] REC OFF. Timeout 30 giây được reset.")

    print(f"[INFO] Bắt đầu Inference ({args.mode.upper()} mode).")
    if args.no_show:
        print(f"[INFO] No-show mode: tự ghi log tại {log_file}")
        start_recording()
    else:
        print("[INFO] Phím điều khiển: r = bật/tắt ghi log, q = thoát.")

    start_benchmark_time = time.time()
    max_duration = 30.0  # Tự động thoát sau 30 giây

    try:
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
            roi_scale_x, roi_scale_y = 1.0, 1.0
            display_roi = None
            tracking_lost = 0

            if args.mode == "roi" and prev_roi is not None:
                inference_mode = "ROI"
                rx, ry, rw, rh = prev_roi
                offset_x, offset_y = rx, ry
                roi_input = frame[ry:ry+rh, rx:rx+rw]
                inference_input = cv2.resize(roi_input, (160, 160))
                input_w, input_h = 160, 160
                roi_scale_x = rw / 160.0
                roi_scale_y = rh / 160.0
                display_roi = (rx, ry, rw, rh)
                infer_model = tracking_model
            else:
                inference_input, params = check_confidence.training_style_crop_pad(frame)
                input_w, input_h = 640, 640
                infer_model = full_model

            results = infer_model.predict(source=inference_input, imgsz=(input_w, input_h), verbose=False)
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
                if inference_mode == "ROI":
                    box = box.copy()
                    box[[0, 2]] *= roi_scale_x
                    box[[1, 3]] *= roi_scale_y

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
                    if prev_roi is None or getattr(tracking_model, 'frames_since_roi_update', 5) >= 5:
                        prev_roi = calculate_roi(best_box, img_w, img_h)
                        tracking_model.frames_since_roi_update = 1
                    else:
                        tracking_model.frames_since_roi_update += 1

                cv2.rectangle(frame, (int(orig_x1), int(orig_y1)), (int(orig_x2), int(orig_y2)), (0, 255, 0), 6)
            else:
                if inference_mode == "ROI":
                    tracking_lost = 1
                prev_roi = None
                tracking_model.frames_since_roi_update = 5  # Reset để lấy ngay ROI mới khi detect lại được

            total_proc_time = (time.time() - t0) * 1000  # ms
            fps = 1000.0 / total_proc_time if total_proc_time > 0 else 0

            if recording and writer is not None:
                writer.writerow([
                    frame_id, timestamp, inference_mode, input_w, input_h,
                    f"{total_inf_time:.2f}", f"{total_proc_time:.2f}", cpu_load, f"{fps:.2f}",
                    f"{cx:.2f}", f"{cy:.2f}", f"{bw:.2f}", f"{bh:.2f}", f"{angle:.4f}", tracking_lost
                ])
                log_handle.flush()

            if not args.no_show:
                if inference_mode == "ROI" and display_roi is not None:
                    rx, ry, rw, rh = display_roi
                    cv2.rectangle(frame, (rx, ry), (rx+rw, ry+rh), (0, 255, 255), 6)

                display_frame = cv2.resize(frame, (640, 360))

                rec_text = "REC" if recording else "IDLE"
                rec_color = (0, 0, 255) if recording else (180, 180, 180)
                cv2.putText(display_frame, f"Mode: {inference_mode} | Input: {input_w}x{input_h}", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                cv2.putText(display_frame, f"FPS: {fps:.1f} | CPU: {cpu_load}%", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                cv2.putText(display_frame, f"Tracking Lost: {tracking_lost}", (10, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                cv2.putText(display_frame, f"{rec_text} | r: record/reset | q: quit", (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, rec_color, 2)

                try:
                    cv2.imshow("Tracking", display_frame)
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        break
                    if key == ord('r'):
                        if recording:
                            stop_recording()
                        else:
                            start_recording()
                except cv2.error as exc:
                    print(f"[WARN] OpenCV GUI không khả dụng, tự chuyển sang --no-show: {exc}")
                    args.no_show = True
                    if not recording:
                        start_recording()
            else:
                if frame_id % 10 == 0:
                    print(f"[LOG] Frame {frame_id} | Mode: {inference_mode} | FPS: {fps:.1f} | CPU: {cpu_load}% | REC: {recording}")

            if not recording:
                elapsed_time = time.time() - start_benchmark_time
                if elapsed_time >= max_duration:
                    print(f"[INFO] Không ghi log trong {max_duration} giây. Tự động kết thúc!")
                    break
    finally:
        if log_handle is not None:
            log_handle.close()

    cap.release()
    if not args.no_show:
        cv2.destroyAllWindows()
    print(f"[INFO] Hoàn tất. Đã lưu log vào file {log_file}")

if __name__ == "__main__":
    main()
