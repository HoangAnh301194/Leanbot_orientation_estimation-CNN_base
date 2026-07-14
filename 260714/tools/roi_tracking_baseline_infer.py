import cv2
import numpy as np
import time
import psutil
import argparse
import csv
import os
import sys
import math
import re
from pathlib import Path
from datetime import datetime
from ultralytics import YOLO
import openvino as ov

# Add tools directory to import check_confidence


sys.path.append(str(Path(__file__).resolve().parent))
import check_confidence


ANGLE_PATTERN = re.compile(r"^Leanbot_(?:(?P<sign>[pm])(?P<value>\d+)|(?P<plain>\d+))$")

def parse_angle_from_class_name(class_name: str):
    match = ANGLE_PATTERN.match(class_name)
    if not match:
        return 0.0
    if match.group("plain") is not None:
        return float(match.group("plain"))
    value = float(match.group("value"))
    return value if match.group("sign") == "p" else -value

def angle_from_detection_class(model, cls_id):
    try:
        return parse_angle_from_class_name(model.names[int(cls_id)])
    except Exception:
        return 0.0

def get_vector_from_scores(class_scores, names):
    sum_x = 0.0
    sum_y = 0.0
    for cls_id, score in enumerate(class_scores):
        class_name = names[int(cls_id)]
        angle = parse_angle_from_class_name(class_name)
        theta_rad = math.radians(angle)
        sum_x += float(score) * math.cos(theta_rad)
        sum_y += float(score) * math.sin(theta_rad)
    magnitude = math.hypot(sum_x, sum_y)
    if magnitude <= 1e-9:
        return 0.0, 0.0
    angle = math.degrees(math.atan2(sum_y, sum_x))
    return magnitude, angle

def infer_openvino_raw(compiled_model, image):
    input_tensor = image[:, :, ::-1].transpose(2, 0, 1)
    input_tensor = np.ascontiguousarray(input_tensor, dtype=np.float32) / 255.0
    input_tensor = input_tensor[None, ...]
    output = compiled_model([input_tensor])[compiled_model.output(0)]
    pred = np.asarray(output)[0]
    if pred.shape[0] < pred.shape[1]:
        pred = pred.T
    return pred

def select_best_vector_detection(compiled_model, image, names):
    pred = infer_openvino_raw(compiled_model, image)
    boxes_xywh = pred[:, :4]
    class_scores = pred[:, 4:4 + len(names)]
    best_scores = class_scores.max(axis=1)
    best_idx = int(np.argmax(best_scores))
    best_conf = float(best_scores[best_idx])
    x_center, y_center, width, height = boxes_xywh[best_idx]
    box_xyxy = np.array([
        x_center - width / 2.0,
        y_center - height / 2.0,
        x_center + width / 2.0,
        y_center + height / 2.0,
    ], dtype=np.float32)
    vector_magnitude, vector_angle = get_vector_from_scores(class_scores[best_idx], names)
    return box_xyxy, best_conf, vector_angle, vector_magnitude

def safe_timestamp_for_filename(text: str):
    return text.replace(":", "-").replace(".", "-")

def make_multiple_of_32(val):
    return int(np.ceil(val / 32.0) * 32)

def calculate_roi(bbox, img_w, img_h):

    x1, y1, x2, y2 = bbox
    w = x2 - x1
    h = y2 - y1
    cx = x1 + w / 2.0
    cy = y1 + h / 2.0

    # ROI hinh vuong: canh dua tren max(w, h) * he so
    side = max(w, h) * 2.0
    side_32 = make_multiple_of_32(side)
    side_32 = min(side_32, img_w, img_h)  # Khong vuot qua kich thuoc anh

    x_min = int(cx - side_32 / 2.0)
    y_min = int(cy - side_32 / 2.0)

    # Clamp de ROI nam trong khung hinh
    if x_min < 0:
        x_min = 0
    elif x_min + side_32 > img_w:
        x_min = img_w - side_32

    if y_min < 0:
        y_min = 0
    elif y_min + side_32 > img_h:
        y_min = img_h - side_32

    return x_min, y_min, side_32, side_32

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="0", help="Camera index or video path")
    parser.add_argument("--video", default="", help="Path to video file (neu co se uu tien dung thay cho source)")
    parser.add_argument("--mode", default="roi", choices=["roi", "baseline"], help="Che do chay: roi hoac baseline")
    parser.add_argument("--log", default="", help="Ten file csv de luu log (mac dinh tu tao theo mode)")
    parser.add_argument("--width", type=int, default=1280, help="Chieu rong camera mong muon")
    parser.add_argument("--height", type=int, default=720, help="Chieu cao camera mong muon")
    parser.add_argument("--no-show", action="store_true", help="Khong hien thi cua so OpenCV")
    parser.add_argument("--show", action="store_true", help="Bat cua so OpenCV neu moi truong ho tro GUI")
    parser.add_argument("--full-model", default=r"models\YOLOv8n_versions\quantized_fp16\best_24Class_Soft_Angular_BCE_openvino_model", help="Path to full detection model directory")
    parser.add_argument("--tracking-model", default=r"models\YOLOv8n_versions\best_24Class_Soft_Angular_BCE_static_160_openvino_model", help="Path to ROI tracking model directory")
    args = parser.parse_args()
    if not args.show:
        args.no_show = True

    full_model_path = args.full_model
    tracking_model_path = args.tracking_model
    
    source = args.video if args.video else args.source
    
    print("[INFO] Loading OpenVINO Models...")
    print(f"[INFO] Full detection model: {full_model_path}")
    print(f"[INFO] ROI tracking model: {tracking_model_path}")
    full_model = YOLO(full_model_path, task='detect')
    tracking_model = YOLO(tracking_model_path, task='detect')
    names = full_model.names
    ov_core = ov.Core()
    full_xml = [f for f in os.listdir(full_model_path) if f.endswith('.xml')][0]
    full_compiled_model = ov_core.compile_model(
        os.path.join(full_model_path, full_xml),
        'AUTO'
    )
    tracking_xml = [f for f in os.listdir(tracking_model_path) if f.endswith('.xml')][0]
    tracking_compiled_model = ov_core.compile_model(
        os.path.join(tracking_model_path, tracking_xml),
        'AUTO'
    )
    
    if source.isdigit():
        source = int(source)
    
    cap = cv2.VideoCapture(source)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    
    if not cap.isOpened():
        print(f"[ERROR] Khong the mo nguon video: {source}")
        return

    prev_roi = None
    frame_id = 0
    
    out_dir = "benchmark"
    os.makedirs(out_dir, exist_ok=True)
    lost_capture_dir = os.path.join(out_dir, "lost_tracking_captures")
    os.makedirs(lost_capture_dir, exist_ok=True)
    
    if args.log:
        # Neu user truyen duong dan co thu muc thi giu nguyen, nguoc lai dat vao benchmark/
        log_file = args.log if os.path.dirname(args.log) else os.path.join(out_dir, args.log)
    else:
        log_file = os.path.join(out_dir, f"log_{args.mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    
    # Khoi tao Process object de do CPU cua rieng script nay
    current_process = psutil.Process()
    current_process.cpu_percent() # Goi lan dau de khoi tao moc thoi gian
    
    csv_header = [
        "frame_id", "timestamp", "mode", "input_width", "input_height", "roi_w", "roi_h",
        "inf_time_ms", "end_to_end_time_ms", "cpu_load_pct", "end_to_end_cpu_load_pct", "fps",
        "x_center", "y_center", "width", "height", "vector_magnitude", "angle", "best_conf", "tracking_lost"
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
        print(f"[INFO] REC ON. Ghi de log tai: {log_file}")

    def stop_recording():
        nonlocal log_handle, writer, recording
        if log_handle is not None:
            log_handle.flush()
            log_handle.close()
        log_handle = None
        writer = None
        recording = False
        print("[INFO] REC OFF.")

    print(f"[INFO] Bat dau Inference ({args.mode.upper()} mode).")
    if args.no_show:
        print(f"[INFO] No-show mode: tu ghi log tai {log_file}")
        start_recording()
    else:
        print("[INFO] Phim dieu khien: r = bat/tat ghi log, q = thoat.")

    # Da bo tinh nang timeout


    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_id += 1
            timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            img_h, img_w = frame.shape[:2]

            t0 = time.time()
            # Do % CPU cua rieng tien trinh nay, chia cho so nhan CPU de quy ve moc 100%
            cpu_load = current_process.cpu_percent() / psutil.cpu_count()

            inference_mode = "FULL"
            offset_x, offset_y = 0, 0
            roi_scale_x, roi_scale_y = 1.0, 1.0
            display_roi = None
            tracking_lost = 0
            lost_roi_input = None
            roi_w, roi_h = 0, 0

            if args.mode == "roi" and prev_roi is not None:
                inference_mode = "ROI"
                rx, ry, rw, rh = prev_roi
                roi_w, roi_h = rw, rh
                offset_x, offset_y = rx, ry
                roi_input = frame[ry:ry+rh, rx:rx+rw]
                lost_roi_input = roi_input.copy()
                inference_input = cv2.resize(roi_input, (160, 160))
                input_w, input_h = 160, 160
                roi_scale_x = rw / 160.0
                roi_scale_y = rh / 160.0
                display_roi = (rx, ry, rw, rh)
                infer_model = tracking_compiled_model
            else:
                inference_input, params = check_confidence.training_style_crop_pad(frame)
                input_w, input_h = 640, 640
                infer_model = full_compiled_model

            infer_start = time.time()
            box, best_conf, angle, vector_magnitude = select_best_vector_detection(infer_model, inference_input, names)
            total_inf_time = (time.time() - infer_start) * 1000

            if inference_mode == "FULL":
                box = check_confidence.restore_boxes_from_training_style(box.reshape(1, 4), params)[0]

            detected = best_conf >= 0.25

            cx, cy, bw, bh = 0.0, 0.0, 0.0, 0.0

            if detected:
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

                if args.mode == "roi":
                    # Cap nhat ROI ngay sau moi frame detect thanh cong
                    prev_roi = calculate_roi(best_box, img_w, img_h)

                cv2.rectangle(frame, (int(orig_x1), int(orig_y1)), (int(orig_x2), int(orig_y2)), (0, 255, 0), 6)
            else:
                if inference_mode == "ROI":
                    tracking_lost = 1
                prev_roi = None

            end_to_end_time_ms = (time.time() - t0) * 1000  # ms
            end_to_end_cpu_load_pct = current_process.cpu_percent() / psutil.cpu_count()
            fps = 1000.0 / end_to_end_time_ms if end_to_end_time_ms > 0 else 0

            if recording and writer is not None:
                writer.writerow([
                    frame_id, timestamp, inference_mode, input_w, input_h, roi_w, roi_h,
                    f"{total_inf_time:.2f}", f"{end_to_end_time_ms:.2f}", cpu_load,
                    end_to_end_cpu_load_pct, f"{fps:.2f}",
                    f"{cx:.2f}", f"{cy:.2f}", f"{bw:.2f}", f"{bh:.2f}",
                    f"{vector_magnitude:.4f}", f"{angle:.4f}", f"{best_conf:.4f}", tracking_lost
                ])
                log_handle.flush()

            def save_lost_tracking_images():
                capture_prefix = f"lost_frame_{frame_id}_{safe_timestamp_for_filename(timestamp)}_{inference_mode}"
                frame_path = os.path.join(lost_capture_dir, f"{capture_prefix}_frame.png")
                cv2.imwrite(frame_path, frame)
                print(f"[INFO] Saved lost tracking frame: {frame_path}")

                if lost_roi_input is not None:
                    roi_path = os.path.join(lost_capture_dir, f"{capture_prefix}_roi.png")
                    cv2.imwrite(roi_path, lost_roi_input)
                    print(f"[INFO] Saved lost tracking ROI crop: {roi_path}")

            if not args.no_show:
                if inference_mode == "ROI" and display_roi is not None:
                    rx, ry, rw, rh = display_roi
                    cv2.rectangle(frame, (rx, ry), (rx+rw, ry+rh), (0, 255, 255), 6)

                display_frame = cv2.resize(frame, (640, 360))

                rec_text = "REC" if recording else "IDLE"
                rec_color = (0, 0, 255) if recording else (180, 180, 180)
                cv2.putText(display_frame, f"Mode: {inference_mode} | Input: {input_w}x{input_h}", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                cv2.putText(display_frame, f"FPS: {fps:.1f} | CPU: {cpu_load}%", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                cv2.putText(display_frame, f"Tracking Lost: {tracking_lost} | Vector Angle: {angle:.1f} | Conf: {best_conf:.2f}", (10, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                cv2.putText(display_frame, f"{rec_text} | r: record/reset | q: quit", (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, rec_color, 2)
                if recording and tracking_lost:
                    save_lost_tracking_images()

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
                    print(f"[WARN] OpenCV GUI khong kha dung, tu chuyen sang --no-show: {exc}")
                    args.no_show = True
                    if not recording:
                        start_recording()
            else:
                if recording and tracking_lost:
                    save_lost_tracking_images()
                if frame_id % 10 == 0:
                    print(f"[LOG] Frame {frame_id} | Mode: {inference_mode} | FPS: {fps:.1f} | CPU: {end_to_end_cpu_load_pct}% | REC: {recording}")

            # if not recording:
            #     elapsed_time = time.time() - start_benchmark_time
            #     if elapsed_time >= max_duration:
            #         print(f"[INFO] Khong ghi log trong {max_duration} giay. Tu dong ket thuc!")
            #         break
    finally:
        if log_handle is not None:
            log_handle.close()

    cap.release()
    if not args.no_show:
        cv2.destroyAllWindows()
    print(f"[INFO] Hoan tat. Da luu log vao file {log_file}")

if __name__ == "__main__":
    main()


