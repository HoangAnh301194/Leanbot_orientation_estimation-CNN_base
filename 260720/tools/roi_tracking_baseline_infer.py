import cv2
import numpy as np
import pandas as pd
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


IOU_THRES = 0.5
CLASS_ANGLE_MAP = {}
ANGLE_PATTERN = re.compile(r"^Leanbot_(?:(?P<sign>[pm])(?P<value>\d+)|(?P<plain>\d+))$")

def parse_angle_from_class_name(class_name: str):
    """Returns the angle (float) encoded in the class name, or None if not an angle class."""
    match = ANGLE_PATTERN.match(class_name)
    if not match:
        return None  # Not an angle class — caller decides fallback
    if match.group("plain") is not None:
        return float(match.group("plain"))
    value = float(match.group("value"))
    return value if match.group("sign") == "p" else -value

def angle_from_detection_class(model, cls_id):
    try:
        result = parse_angle_from_class_name(model.names[int(cls_id)])
        return result if result is not None else 0.0
    except Exception:
        return 0.0

def get_vector_from_scores(class_scores, names):
    """Tổng hợp vector từ toàn bộ class scores, dùng CLASS_ANGLE_MAP cache.
    Các class không phải angle class sẽ bị bỏ qua (giống webcam_vector_infer).
    """
    if not CLASS_ANGLE_MAP:
        for cid, cname in names.items():
            a = parse_angle_from_class_name(cname)
            if a is not None:
                CLASS_ANGLE_MAP[cname] = a
    sum_x = 0.0
    sum_y = 0.0
    for cls_id, score in enumerate(class_scores):
        cls_name = names[int(cls_id)]
        angle = CLASS_ANGLE_MAP.get(cls_name)
        if angle is None:
            continue  # Bỏ qua class không có angle
        theta_rad = math.radians(angle)
        sum_x += float(score) * math.cos(theta_rad)
        sum_y += float(score) * math.sin(theta_rad)
    magnitude = math.hypot(sum_x, sum_y)
    if magnitude <= 1e-9:
        return 0.0, 0.0
    angle_out = math.degrees(math.atan2(sum_y, sum_x))
    return magnitude, angle_out

# ---------------------------------------------------------------------------
# Helper functions cho no-NMS pipeline (ported từ webcam_vector_infer.py)
# ---------------------------------------------------------------------------

def box_iou_numpy(box, boxes):
    """Tính IoU giữa 1 box và mảng boxes (xyxy format)."""
    if len(boxes) == 0:
        return np.array([])
    x1 = np.maximum(box[0], boxes[:, 0])
    y1 = np.maximum(box[1], boxes[:, 1])
    x2 = np.minimum(box[2], boxes[:, 2])
    y2 = np.minimum(box[3], boxes[:, 3])
    inter = np.maximum(0, x2 - x1) * np.maximum(0, y2 - y1)
    area_box = max(0, box[2] - box[0]) * max(0, box[3] - box[1])
    area_boxes = np.maximum(0, boxes[:, 2] - boxes[:, 0]) * np.maximum(0, boxes[:, 3] - boxes[:, 1])
    return inter / (area_box + area_boxes - inter + 1e-9)

def compute_weighted_bbox(group_df):
    """Tính bounding box trung bình có trọng số theo vector_magnitude."""
    w = group_df["vector_magnitude"].values
    total = w.sum()
    if total <= 1e-9:
        return (float(group_df["x_center"].mean()), float(group_df["y_center"].mean()),
                float(group_df["width"].mean()), float(group_df["height"].mean()))
    return (
        float(np.dot(w, group_df["x_center"].values) / total),
        float(np.dot(w, group_df["y_center"].values) / total),
        float(np.dot(w, group_df["width"].values) / total),
        float(np.dot(w, group_df["height"].values) / total),
    )

def group_anchors(df, iou_thres=IOU_THRES):
    """Greedy IoU grouping — gom các anchors chồng lấp thành nhóm."""
    if len(df) == 0:
        return []
    df = df.sort_values("vector_magnitude", ascending=False).reset_index(drop=True)
    df["x1"] = df["x_center"] - df["width"] / 2
    df["y1"] = df["y_center"] - df["height"] / 2
    df["x2"] = df["x_center"] + df["width"] / 2
    df["y2"] = df["y_center"] + df["height"] / 2
    boxes = df[["x1", "y1", "x2", "y2"]].values
    remaining = list(range(len(df)))
    groups = []
    gid = 1
    while remaining:
        best = remaining[0]
        for idx in remaining:
            if df.loc[idx, "vector_magnitude"] > df.loc[best, "vector_magnitude"]:
                best = idx
        center_box = boxes[best]
        rem_boxes = boxes[remaining]
        ious = box_iou_numpy(center_box, rem_boxes)
        mask = ious > iou_thres
        in_group = [remaining[i] for i, m in enumerate(mask) if m]
        remaining = [remaining[i] for i, m in enumerate(mask) if not m]
        gdf = df.iloc[in_group].copy()
        gdf["group_id"] = gid
        gx, gy, gw, gh = compute_weighted_bbox(gdf)
        gdf["group_x_center"] = gx
        gdf["group_y_center"] = gy
        gdf["group_width"] = gw
        gdf["group_height"] = gh
        groups.append(gdf)
        gid += 1
    return groups

def compute_group_vectors(groups):
    """Tính vector tổng hợp cho mỗi nhóm anchor."""
    rows = []
    for gdf in groups:
        gid = int(gdf["group_id"].iloc[0])
        sum_x, sum_y = 0.0, 0.0
        for _, r in gdf.iterrows():
            mag = r["vector_magnitude"]
            ang = math.radians(r["estimated_angle"])
            sum_x += mag * math.cos(ang)
            sum_y += mag * math.sin(ang)
        group_mag = math.hypot(sum_x, sum_y)
        group_ang = math.degrees(math.atan2(sum_y, sum_x))
        best_row = gdf.loc[gdf["vector_magnitude"].idxmax()]
        gx = float(best_row.get("group_x_center", best_row["x_center"]))
        gy = float(best_row.get("group_y_center", best_row["y_center"]))
        gw = float(best_row.get("group_width", best_row["width"]))
        gh = float(best_row.get("group_height", best_row["height"]))
        rows.append({
            "group_id": gid,
            "number_of_anchors": len(gdf),
            "vector_magnitude": round(group_mag, 2),
            "x_center": round(gx, 2),
            "y_center": round(gy, 2),
            "width": round(gw, 2),
            "height": round(gh, 2),
            "angle": round(group_ang, 2),
        })
    df_out = pd.DataFrame(rows)
    if not df_out.empty:
        df_out = df_out.sort_values("vector_magnitude", ascending=False).reset_index(drop=True)
    return df_out

def infer_openvino_raw(compiled_model, image):
    input_tensor = image[:, :, ::-1].transpose(2, 0, 1)
    input_tensor = np.ascontiguousarray(input_tensor, dtype=np.float32) / 255.0
    input_tensor = input_tensor[None, ...]
    output = compiled_model([input_tensor])[compiled_model.output(0)]
    pred = np.asarray(output)[0]
    if pred.shape[0] < pred.shape[1]:
        pred = pred.T
    return pred

def select_best_vector_detection(compiled_model, image, names,
                                  conf_thres=0.25, topk=100,
                                  iou_thres=IOU_THRES, min_mag=2.0):
    """Chọn detection tốt nhất từ output của model.

    - NMS output  (shape[1] == 6): lấy box có conf cao nhất, đọc angle từ class name.
    - Raw output  (shape[1] >  6): dùng full vector pipeline giống webcam_vector_infer
      (conf filter → Top-K → per-anchor vector → IoU grouping → group vector sum).

    Returns: (box_xyxy, best_conf, angle, vector_magnitude)
    """
    pred = infer_openvino_raw(compiled_model, image)

    # ------------------------------------------------------------------
    # Nhánh NMS: output 6 cột [x1, y1, x2, y2, conf, cls_id]
    # ------------------------------------------------------------------
    if pred.shape[1] == 6:
        valid_pred = pred[pred[:, 4] > 0.0]
        if len(valid_pred) == 0:
            return np.zeros(4, dtype=np.float32), 0.0, 0.0, 0.0
        best_detection = valid_pred[int(np.argmax(valid_pred[:, 4]))]
        box_xyxy = best_detection[:4].astype(np.float32)
        best_conf = float(best_detection[4])
        try:
            class_name = names[int(best_detection[5])]
            vector_angle = parse_angle_from_class_name(class_name)
            if vector_angle is None:
                vector_angle = 0.0
        except (IndexError, KeyError, TypeError, ValueError):
            vector_angle = 0.0
        return box_xyxy, best_conf, vector_angle, best_conf

    # ------------------------------------------------------------------
    # Nhánh No-NMS: full vector pipeline (giống webcam_vector_infer.py)
    # Output raw: [x_c, y_c, w, h, score_cls0, ..., score_clsN]
    # ------------------------------------------------------------------
    boxes_xywh = pred[:, :4]
    class_scores = pred[:, 4:4 + len(names)]

    # 1. Confidence filter
    best_scores_per_anchor = class_scores.max(axis=1)
    conf_mask = best_scores_per_anchor > conf_thres
    filtered_indices = np.where(conf_mask)[0]

    if len(filtered_indices) == 0:
        return np.zeros(4, dtype=np.float32), 0.0, 0.0, 0.0

    # 2. Top-K selection
    filtered_scores = best_scores_per_anchor[filtered_indices]
    topk_actual = min(topk, len(filtered_indices))
    topk_relative = np.argsort(filtered_scores)[-topk_actual:][::-1]
    topk_idx = filtered_indices[topk_relative]

    top_boxes = boxes_xywh[topk_idx]
    top_class_scores = class_scores[topk_idx]
    # Conf đại diện = score cao nhất của anchor đứng đầu
    best_conf = float(best_scores_per_anchor[topk_idx[0]])

    # 3. Tính vector cho từng anchor
    raw_rows = []
    for i in range(topk_actual):
        mag, ang = get_vector_from_scores(top_class_scores[i], names)
        x, y, w, h = top_boxes[i]
        raw_rows.append({
            "vector_magnitude": float(mag),
            "estimated_angle": float(ang),
            "x_center": float(x),
            "y_center": float(y),
            "width": float(w),
            "height": float(h),
        })

    raw_df = pd.DataFrame(raw_rows)

    # 4. Gom nhóm anchor theo IoU
    groups = group_anchors(raw_df, iou_thres=iou_thres)
    if not groups:
        return np.zeros(4, dtype=np.float32), 0.0, 0.0, 0.0

    # 5. Tính vector tổng hợp cho mỗi nhóm
    summary_df = compute_group_vectors(groups)
    summary_df = summary_df[summary_df["vector_magnitude"] >= min_mag]
    if summary_df.empty:
        return np.zeros(4, dtype=np.float32), 0.0, 0.0, 0.0

    # Nhóm tốt nhất (magnitude cao nhất — đã sort sẵn)
    best = summary_df.iloc[0]
    xc = float(best["x_center"])
    yc = float(best["y_center"])
    bw = float(best["width"])
    bh = float(best["height"])
    box_xyxy = np.array(
        [xc - bw / 2, yc - bh / 2, xc + bw / 2, yc + bh / 2],
        dtype=np.float32,
    )
    return box_xyxy, best_conf, float(best["angle"]), float(best["vector_magnitude"])


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
    side = max(w, h) * 2.0
    side_32 = make_multiple_of_32(side)
    side_32 = min(side_32, img_w, img_h)
    x_min = int(cx - side_32 / 2.0)
    y_min = int(cy - side_32 / 2.0)
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
    parser.add_argument("--full-model", default=r"models\YOLO11n_versions\quantized_fp16_nms\Soft_Angular_BCE_yolo11n_fp16_nms_imgsz640_openvino_model", help="Path to full detection model directory")
    parser.add_argument("--tracking-model", default=r"models\YOLO11n_versions\quantized_fp16_nms\Soft_Angular_BCE_yolo11n_fp16_nms_imgsz160_openvino_model", help="Path to ROI tracking model directory")
    # --- Tham so vector pipeline (chi dung khi model la no-NMS / raw output) ---
    parser.add_argument("--topk", type=int, default=100, help="Top-K anchors cho no-NMS pipeline (default 100)")
    parser.add_argument("--conf", type=float, default=0.25, help="Nguong confidence loc anchor FULL 640 (default 0.25)")
    parser.add_argument("--roi_conf", type=float, default=0.15, help="Nguong confidence loc anchor ROI 160 (default 0.15)")
    parser.add_argument("--iou", type=float, default=IOU_THRES, help="Nguong IoU gom nhom anchor (default 0.5)")
    parser.add_argument("--min-mag", type=float, default=2.0, help="Vector magnitude toi thieu de chap nhan nhom (default 2.0)")
    parser.add_argument("--debug-imgsz", action="store_true", help="Luu anh debug cac buoc resize/padding vao benchmark/imgszdebug/")
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
    names = full_model.names
    ov_core = ov.Core()
    full_xml = [f for f in os.listdir(full_model_path) if f.endswith('.xml')][0]
    full_compiled_model = ov_core.compile_model(
        os.path.join(full_model_path, full_xml),
        'AUTO'
    )
    
    if args.mode == "roi":
        tracking_model = YOLO(tracking_model_path, task='detect')
        tracking_xml = [f for f in os.listdir(tracking_model_path) if f.endswith('.xml')][0]
        tracking_compiled_model = ov_core.compile_model(
            os.path.join(tracking_model_path, tracking_xml),
            'AUTO'
        )
    else:
        tracking_compiled_model = None
    
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
    debug_full_saved = False
    debug_roi_saved = False
    if args.debug_imgsz:
        debug_imgsz_dir = os.path.join("benchmark", "imgszdebug")
        os.makedirs(debug_imgsz_dir, exist_ok=True)
        print(f"[INFO] Debug imgsz: se luu anh vao {debug_imgsz_dir}")
    
    if args.log:
        log_file = args.log if os.path.dirname(args.log) else os.path.join("benchmark", args.log)
    else:
        log_file = os.path.join("benchmark", f"log_{args.mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        
    out_dir = os.path.dirname(log_file)
    if not out_dir:
        out_dir = "."
    os.makedirs(out_dir, exist_ok=True)
    
    lost_capture_dir = os.path.join(out_dir, "lost_tracking_captures")
    os.makedirs(lost_capture_dir, exist_ok=True)
    
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
    elif args.video:
        print(f"[INFO] Video mode: tu dong ghi log tai {log_file}")
        start_recording()
        print("[INFO] Phim dieu khien: r = bat/tat ghi log, q = thoat.")
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
                # --- Debug imgsz ROI ---
                if args.debug_imgsz and not debug_roi_saved:
                    cv2.imwrite(os.path.join(debug_imgsz_dir, "roi_01_raw_frame.png"), frame)
                    cv2.imwrite(os.path.join(debug_imgsz_dir, "roi_02_cropped_roi.png"), roi_input)
                    cv2.imwrite(os.path.join(debug_imgsz_dir, "roi_03_resized_160.png"), inference_input)
                    debug_roi_saved = True
                    print(f"[DEBUG] Da luu anh debug ROI (frame {frame_id}): roi_input {roi_input.shape[1]}x{roi_input.shape[0]} -> 160x160")
            else:
                # --- Tach cac buoc de debug ---
                img_h_orig, img_w_orig = frame.shape[:2]
                crop_w = int(img_w_orig * 0.625)
                crop_h = img_h_orig
                start_x = (img_w_orig - crop_w) // 2
                cropped = frame[0:crop_h, start_x:start_x + crop_w]
                square_size = max(crop_w, crop_h)
                padded = np.zeros((square_size, square_size, 3), dtype=np.uint8)
                pad_top = (square_size - crop_h) // 2
                pad_left = (square_size - crop_w) // 2
                padded[pad_top:pad_top + crop_h, pad_left:pad_left + crop_w] = cropped
                inference_input = cv2.resize(padded, (640, 640))
                params = {
                    'start_x': start_x,
                    'pad_top': pad_top,
                    'pad_left': pad_left,
                    'crop_w': crop_w,
                    'scale': 640.0 / square_size
                }
                input_w, input_h = 640, 640
                infer_model = full_compiled_model
                # --- Debug imgsz FULL ---
                if args.debug_imgsz and not debug_full_saved:
                    cv2.imwrite(os.path.join(debug_imgsz_dir, "full_01_raw_frame.png"), frame)
                    cv2.imwrite(os.path.join(debug_imgsz_dir, "full_02_cropped.png"), cropped)
                    cv2.imwrite(os.path.join(debug_imgsz_dir, "full_03_padded.png"), padded)
                    cv2.imwrite(os.path.join(debug_imgsz_dir, "full_04_resized_640.png"), inference_input)
                    debug_full_saved = True
                    print(f"[DEBUG] Da luu anh debug FULL (frame {frame_id}): {img_w_orig}x{img_h_orig} -> crop {crop_w}x{crop_h} -> pad {square_size}x{square_size} -> 640x640")

            infer_start = time.time()
            current_conf = args.roi_conf if inference_mode == "ROI" else args.conf
            box, best_conf, angle, vector_magnitude = select_best_vector_detection(
                infer_model, inference_input, names,
                conf_thres=current_conf, topk=args.topk,
                iou_thres=args.iou, min_mag=args.min_mag,
            )
            total_inf_time = (time.time() - infer_start) * 1000

            if inference_mode == "FULL":
                box = check_confidence.restore_boxes_from_training_style(box.reshape(1, 4), params)[0]

            detected = vector_magnitude > 0

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
                # Mất detect: cả ROI mode (lost tracking) lẫn FULL/baseline mode (no detection)
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


