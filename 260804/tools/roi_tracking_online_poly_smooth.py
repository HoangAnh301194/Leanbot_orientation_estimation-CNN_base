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
import matplotlib.pyplot as plt
from ultralytics import YOLO
import openvino as ov

# Add tools directory to sys.path to import check_confidence
sys.path.append(str(Path(__file__).resolve().parent))
import check_confidence

IOU_THRES = 0.5
CLASS_ANGLE_MAP = {}
ANGLE_PATTERN = re.compile(r"^Leanbot_(?:(?P<sign>[pm])(?P<value>\d+)|(?P<plain>\d+))$")

SMOOTH_LENGTH = 30
SMOOTH_ORDER = 3

def parse_angle_from_class_name(class_name: str):
    """Returns the angle (float) encoded in the class name, or None if not an angle class."""
    match = ANGLE_PATTERN.match(class_name)
    if not match:
        return None
    if match.group("plain") is not None:
        return float(match.group("plain"))
    value = float(match.group("value"))
    return value if match.group("sign") == "p" else -value

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
                                  iou_thres=IOU_THRES, mag_threshold=2.0):
    pred = infer_openvino_raw(compiled_model, image)
    if pred.shape[1] == 6:
        valid_pred = pred[pred[:, 4] > 0.0]
        if len(valid_pred) == 0:
            return np.zeros(4, dtype=np.float32), 0.0, 0.0, 0.0, 0.0, 0.0
        best_detection = valid_pred[int(np.argmax(valid_pred[:, 4]))]
        box_xyxy = best_detection[:4].astype(np.float32)
        best_conf = float(best_detection[4])
        cls_id = int(best_detection[5])
        angle = parse_angle_from_class_name(names[cls_id])
        if angle is None:
            angle = 0.0
        return box_xyxy, best_conf, angle, best_conf, 0.0, 0.0

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
        return np.zeros(4, dtype=np.float32), 0.0, 0.0, 0.0, 0.0, 0.0

    # 2. Top-K selection
    filtered_scores = best_scores_per_anchor[filtered_indices]
    topk_actual = min(topk, len(filtered_indices))
    topk_relative = np.argsort(filtered_scores)[-topk_actual:][::-1]
    topk_idx = filtered_indices[topk_relative]

    top_boxes = boxes_xywh[topk_idx]
    top_class_scores = class_scores[topk_idx]
    best_conf = float(best_scores_per_anchor[topk_idx[0]])

    # 3. Tính vector cho từng anchor
    rows = []
    for i in range(topk_actual):
        mag, ang = get_vector_from_scores(top_class_scores[i], names)
        if mag > 0:
            cx, cy, w, h = top_boxes[i]
            rows.append({
                "x_center": cx, "y_center": cy, "width": w, "height": h,
                "confidence": float(best_scores_per_anchor[topk_idx[i]]),
                "vector_magnitude": mag, "estimated_angle": ang
            })

    if not rows:
        return np.zeros(4, dtype=np.float32), 0.0, 0.0, 0.0, 0.0, 0.0

    df_anchors = pd.DataFrame(rows)
    groups = group_anchors(df_anchors, iou_thres=iou_thres)
    df_groups = compute_group_vectors(groups)

    if df_groups.empty:
        return np.zeros(4, dtype=np.float32), 0.0, 0.0, 0.0, 0.0, 0.0

    group1 = df_groups.iloc[0]
    mag1 = float(group1["vector_magnitude"])
    if mag1 < mag_threshold:
        return np.zeros(4, dtype=np.float32), 0.0, 0.0, 0.0, 0.0, 0.0

    cx1, cy1 = float(group1["x_center"]), float(group1["y_center"])
    w1, h1 = float(group1["width"]), float(group1["height"])
    ang1 = float(group1["angle"])
    box1 = np.array([cx1 - w1 / 2.0, cy1 - h1 / 2.0, cx1 + w1 / 2.0, cy1 + h1 / 2.0], dtype=np.float32)

    mag2, ang2 = 0.0, 0.0
    if len(df_groups) > 1:
        group2 = df_groups.iloc[1]
        mag2 = float(group2["vector_magnitude"])
        ang2 = float(group2["angle"])

    return box1, best_conf, ang1, mag1, ang2, mag2

def get_vector_from_scores(class_scores, names):
    if not CLASS_ANGLE_MAP:
        for cid, cname in names.items():
            a = parse_angle_from_class_name(cname)
            if a is not None:
                CLASS_ANGLE_MAP[cname] = a
    sum_x, sum_y = 0.0, 0.0
    for cls_id, score in enumerate(class_scores):
        cls_name = names[int(cls_id)]
        angle = CLASS_ANGLE_MAP.get(cls_name)
        if angle is None:
            continue
        theta_rad = math.radians(angle)
        sum_x += float(score) * math.cos(theta_rad)
        sum_y += float(score) * math.sin(theta_rad)
    magnitude = math.hypot(sum_x, sum_y)
    if magnitude <= 1e-9:
        return 0.0, 0.0
    angle_out = math.degrees(math.atan2(sum_y, sum_x))
    return magnitude, angle_out

def calculate_roi(box_xyxy, img_w, img_h, target_size=160):
    x1, y1, x2, y2 = box_xyxy
    bw = x2 - x1
    bh = y2 - y1
    cx = x1 + bw / 2.0
    cy = y1 + bh / 2.0
    side = max(bw, bh)
    side_32 = math.ceil((side * 2.0) / 32.0) * 32
    if side_32 < target_size:
        side_32 = target_size

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


class OnlinePolySmoother:
    """Sliding Window Online Polynomial Smoother.
    Mỗi khi có 30 điểm raw (cx, cy) gần nhất, fit 2 đa thức bậc 3 x(t) và y(t),
    tính tọa độ smooth cho duy nhất điểm thứ 30.
    """
    def __init__(self, window_size=SMOOTH_LENGTH, poly_degree=SMOOTH_ORDER):
        self.window_size = window_size
        self.poly_degree = poly_degree
        self.raw_window = []  # Lớp chứa tối đa 30 điểm (cx, cy) gần nhất
        self.raw_trajectory = []     # Toàn bộ chuỗi raw (cx, cy)
        self.smooth_trajectory = []  # Toàn bộ chuỗi smooth (sx, sy)

    def add_point(self, cx, cy):
        self.raw_trajectory.append((cx, cy))
        self.raw_window.append((cx, cy))

        if len(self.raw_window) > self.window_size:
            self.raw_window.pop(0)

        if len(self.raw_window) == self.window_size:
            pts = np.array(self.raw_window, dtype=float)
            x_seg = pts[:, 0]
            y_seg = pts[:, 1]
            t_norm = np.arange(self.window_size, dtype=float) / float(self.window_size)

            coeffs_x = np.polyfit(t_norm, x_seg, deg=self.poly_degree)
            coeffs_y = np.polyfit(t_norm, y_seg, deg=self.poly_degree)

            # Tính duy nhất điểm cuối (tương ứng t = (N-1)/N = 29/30)
            t_last = (self.window_size - 1) / float(self.window_size)
            sx = float(np.polyval(coeffs_x, t_last))
            sy = float(np.polyval(coeffs_y, t_last))

            self.smooth_trajectory.append((sx, sy))
            return sx, sy
        else:
            # Chưa đủ 30 điểm thì dùng tạm giá trị raw
            self.smooth_trajectory.append((cx, cy))
            return cx, cy

    def reset_buffer(self):
        self.raw_window = []


def save_trajectory_plot(raw_traj, smooth_traj, output_path, title="Online Poly Smooth Trajectory"):
    """Vẽ và xuất đồ thị quỹ đạo (Đường smooth phía dưới, đường raw đè lên trên)."""
    if not raw_traj or not smooth_traj:
        return
    raw_pts = np.array(raw_traj)
    smooth_pts = np.array(smooth_traj)

    plt.figure(figsize=(10, 8), dpi=150)
    # 1. Đường smooth bên dưới (màu xanh dương)
    plt.plot(smooth_pts[:, 0], smooth_pts[:, 1], color='blue', linewidth=2.5, label='Smooth Trajectory (Poly deg=3)', zorder=1)
    plt.scatter(smooth_pts[:, 0], smooth_pts[:, 1], color='navy', s=12, alpha=0.6, zorder=2)

    # 2. Đường raw đè lên bên trên (màu đỏ)
    plt.plot(raw_pts[:, 0], raw_pts[:, 1], color='red', linewidth=1.0, linestyle='--', alpha=0.7, label='Raw Trajectory', zorder=3)
    plt.scatter(raw_pts[:, 0], raw_pts[:, 1], color='darkred', s=15, marker='o', label='Raw Points', zorder=4)

    plt.gca().invert_yaxis()  # Đảo ngược trục Y cho đúng hệ tọa độ ảnh OpenCV
    plt.title(title, fontsize=14, fontweight='bold')
    plt.xlabel('X (pixels)')
    plt.ylabel('Y (pixels)')
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.legend(loc='best')
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    print(f"[INFO] Đã lưu đồ thị quỹ đạo tại: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Leanbot ROI Tracking with Online Polynomial Smoothing (deg=3, length=30)")
    parser.add_argument("--source", default="0", help="Camera index or video path")
    parser.add_argument("--video", default="", help="Path to video file")
    parser.add_argument("--mode", default="roi", choices=["roi", "baseline"])
    parser.add_argument("--log", default="", help="Path file CSV luu log")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--no-show", action="store_true")
    parser.add_argument("--show", action="store_true")
    parser.add_argument("--device", default="CPU", choices=["CPU", "GPU", "AUTO"])
    parser.add_argument("--full-model", default=r"models\YOLO11n_versions\FP16_NO_NMS\best_fp16_no_nms_imgsz640_openvino_model")
    parser.add_argument("--tracking-model", default=r"models\YOLO11n_versions\FP16_NO_NMS\best_fp16_no_nms_imgsz160_openvino_model")
    parser.add_argument("--topk", type=int, default=100)
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--roi_conf", type=float, default=0.15)
    parser.add_argument("--iou", type=float, default=IOU_THRES)
    parser.add_argument("--mag-threshold", type=float, default=2.0)
    args = parser.parse_args()

    # Mặc định hiển thị cửa sổ OpenCV, chỉ ẩn khi truyền --no-show
    if args.no_show:
        args.no_show = True
    else:
        args.no_show = False

    full_model_path = args.full_model
    tracking_model_path = args.tracking_model
    source = args.video if args.video else args.source

    print(f"[INFO] Khoi tao Online Poly Smoother (SMOOTH_LENGTH={SMOOTH_LENGTH}, SMOOTH_ORDER={SMOOTH_ORDER})")
    smoother = OnlinePolySmoother(window_size=SMOOTH_LENGTH, poly_degree=SMOOTH_ORDER)

    print("[INFO] Loading OpenVINO Models...")
    full_model = YOLO(full_model_path, task='detect')
    names = full_model.names
    ov_core = ov.Core()
    full_xml = [f for f in os.listdir(full_model_path) if f.endswith('.xml')][0]
    full_compiled_model = ov_core.compile_model(
        os.path.join(full_model_path, full_xml),
        args.device,
        {"PERFORMANCE_HINT": "LATENCY"}
    )

    if args.mode == "roi":
        tracking_model = YOLO(tracking_model_path, task='detect')
        tracking_xml = [f for f in os.listdir(tracking_model_path) if f.endswith('.xml')][0]
        tracking_compiled_model = ov_core.compile_model(
            os.path.join(tracking_model_path, tracking_xml),
            args.device,
            {"PERFORMANCE_HINT": "LATENCY"}
        )
    else:
        tracking_compiled_model = None

    if str(source).isdigit():
        source = int(source)

    cap = cv2.VideoCapture(source)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    cap.set(cv2.CAP_PROP_FPS, 15)

    if not cap.isOpened():
        print(f"[ERROR] Khong the mo nguon video: {source}")
        return

    prev_roi = None
    prev_bbox_xyxy = None
    frame_id = 0
    current_process = psutil.Process()
    current_process.cpu_percent()

    if args.log:
        log_file = args.log if os.path.dirname(args.log) else os.path.join("benchmark", args.log)
    else:
        log_file = os.path.join("benchmark", f"log_online_poly_{args.mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")

    out_dir = os.path.dirname(log_file)
    if not out_dir:
        out_dir = "."
    os.makedirs(out_dir, exist_ok=True)

    csv_header = [
        "frame_id", "timestamp", "mode", "input_width", "input_height", "roi_w", "roi_h",
        "inf_time_ms", "end_to_end_time_ms", "cpu_load_pct", "end_to_end_cpu_load_pct", "fps",
        "x_center", "y_center", "smooth_x", "smooth_y", "width", "height", "iou_prev_bbox",
        "group1_magnitude", "group1_angle", "group2_magnitude", "group2_angle", "best_conf", "tracking_lost"
    ]

    log_handle = None
    writer = None
    recording = False
    has_recorded = False

    def start_recording():
        nonlocal log_handle, writer, recording, has_recorded
        if log_handle is not None:
            log_handle.close()
        log_handle = open(log_file, mode='w', newline='')
        writer = csv.writer(log_handle)
        writer.writerow(csv_header)
        log_handle.flush()
        recording = True
        has_recorded = True
        print(f"[INFO] REC ON. Ghi log tai: {log_file}")

    def stop_recording():
        nonlocal log_handle, writer, recording
        if log_handle is not None:
            log_handle.flush()
            log_handle.close()
        log_handle = None
        writer = None
        recording = False
        print("[INFO] REC OFF.")

    if args.no_show:
        start_recording()
    elif args.video:
        start_recording()
    else:
        print("[INFO] Phim dieu khien: r = bat/tat ghi log CSV, q = thoat.")

    print(f"[INFO] Running Online Tracking & Smooth. Saving log to: {log_file}")

    windows_positioned = False
    try:
        while True:
            t0 = time.time()
            ret, frame = cap.read()
            if not ret:
                break

            orig_frame = frame.copy()
            frame_id += 1
            timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            img_h, img_w = frame.shape[:2]

            cpu_load = current_process.cpu_percent() / psutil.cpu_count()

            inference_mode = "FULL"
            offset_x, offset_y = 0, 0
            roi_scale_x, roi_scale_y = 1.0, 1.0
            tracking_lost = 0
            roi_w, roi_h = 0, 0
            display_bbox = None

            current_roi_crop = None
            if args.mode == "roi" and prev_roi is not None:
                inference_mode = "ROI"
                rx, ry, rw, rh = prev_roi
                roi_w, roi_h = rw, rh
                offset_x, offset_y = rx, ry
                roi_input = frame[ry:ry+rh, rx:rx+rw]
                current_roi_crop = roi_input.copy()
                inference_input = cv2.resize(roi_input, (160, 160))
                input_w, input_h = 160, 160
                roi_scale_x = rw / 160.0
                roi_scale_y = rh / 160.0
                infer_model = tracking_compiled_model
            else:
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

            infer_start = time.time()
            current_conf = args.roi_conf if inference_mode == "ROI" else args.conf
            box, best_conf, angle, vector_magnitude, angle2, mag2 = select_best_vector_detection(
                infer_model, inference_input, names,
                conf_thres=current_conf, topk=args.topk,
                iou_thres=args.iou, mag_threshold=args.mag_threshold,
            )
            total_inf_time = (time.time() - infer_start) * 1000

            if inference_mode == "FULL":
                box = check_confidence.restore_boxes_from_training_style(box.reshape(1, 4), params)[0]

            detected = vector_magnitude > 0
            cx, cy, bw, bh = 0.0, 0.0, 0.0, 0.0
            sx, sy = 0.0, 0.0
            iou_prev = 0.0

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
                current_box_xyxy = np.array(best_box, dtype=np.float32)

                if prev_bbox_xyxy is not None:
                    iou_prev = float(box_iou_numpy(current_box_xyxy, np.array([prev_bbox_xyxy]))[0])
                else:
                    iou_prev = 1.0
                prev_bbox_xyxy = current_box_xyxy.copy()

                bw = orig_x2 - orig_x1
                bh = orig_y2 - orig_y1
                cx = orig_x1 + bw / 2.0
                cy = orig_y1 + bh / 2.0

                if args.mode == "roi":
                    prev_roi = calculate_roi(best_box, img_w, img_h)

                display_bbox = (int(orig_x1), int(orig_y1), int(orig_x2), int(orig_y2))

                # --- Tính Online Polynomial Smooth ---
                sx, sy = smoother.add_point(cx, cy)

            else:
                tracking_lost = 1
                prev_roi = None
                prev_bbox_xyxy = None
                iou_prev = 0.0
                # Bỏ qua frame bị lost, giữ nguyên các điểm hợp lệ trước đó trong bộ đệm

            end_to_end_time_ms = (time.time() - t0) * 1000
            end_to_end_cpu_load_pct = current_process.cpu_percent() / psutil.cpu_count()
            fps = 1000.0 / end_to_end_time_ms if end_to_end_time_ms > 0 else 0

            if recording and writer is not None:
                writer.writerow([
                    frame_id, timestamp, inference_mode, input_w, input_h, roi_w, roi_h,
                    f"{total_inf_time:.2f}", f"{end_to_end_time_ms:.2f}", cpu_load,
                    end_to_end_cpu_load_pct, f"{fps:.2f}",
                    f"{cx:.2f}", f"{cy:.2f}", f"{sx:.2f}", f"{sy:.2f}", f"{bw:.2f}", f"{bh:.2f}", f"{iou_prev:.4f}",
                    f"{vector_magnitude:.4f}", f"{angle:.4f}", f"{mag2:.4f}", f"{angle2:.4f}", f"{best_conf:.4f}", tracking_lost
                ])
                log_handle.flush()

            if not args.no_show:
                display_frame = orig_frame.copy()
                # 1. Vẽ toàn bộ đường smooth bên dưới (màu xanh lá/xanh dương)
                if len(smoother.smooth_trajectory) > 1:
                    s_pts = np.array(smoother.smooth_trajectory, dtype=np.int32)
                    cv2.polylines(display_frame, [s_pts], isClosed=False, color=(255, 120, 0), thickness=3)

                # 2. Vẽ toàn bộ đường raw đè lên trên (màu đỏ)
                if len(smoother.raw_trajectory) > 1:
                    r_pts = np.array(smoother.raw_trajectory, dtype=np.int32)
                    cv2.polylines(display_frame, [r_pts], isClosed=False, color=(0, 0, 255), thickness=1)

                # 3. Vẽ Bounding Box và điểm hiện tại
                if detected:
                    if display_bbox is not None:
                        bx1, by1, bx2, by2 = display_bbox
                        cv2.rectangle(display_frame, (bx1, by1), (bx2, by2), (0, 255, 0), 3) # Khung xanh lá quanh Leanbot
                    cv2.circle(display_frame, (int(cx), int(cy)), 4, (0, 0, 255), -1)  # raw point red
                    cv2.circle(display_frame, (int(sx), int(sy)), 5, (255, 255, 0), -1) # smooth point cyan

                rec_status_str = "[REC ON]" if recording else "[REC OFF]"
                rec_color = (0, 0, 255) if recording else (200, 200, 200)

                cv2.putText(display_frame, f"FPS: {fps:.1f} {rec_status_str}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, rec_color, 2)
                cv2.putText(display_frame, f"Raw: ({cx:.1f}, {cy:.1f})", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                cv2.putText(display_frame, f"Smooth: ({sx:.1f}, {sy:.1f})", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

                cv2.imshow("Leanbot Online Poly Smooth Tracking", display_frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('r'):
                    if recording:
                        stop_recording()
                    else:
                        start_recording()
                elif key == ord('s'):
                    # Lưu hình ảnh đồ thị quỹ đạo
                    plot_path = os.path.join(out_dir, f"trajectory_plot_frame_{frame_id}.png")
                    save_trajectory_plot(smoother.raw_trajectory, smoother.smooth_trajectory, plot_path)
            else:
                if frame_id % 30 == 0:
                    print(f"[LOG] Frame {frame_id} | FPS: {fps:.1f} | Raw: ({cx:.1f}, {cy:.1f}) -> Smooth: ({sx:.1f}, {sy:.1f}) | REC: {recording}")

    finally:
        if log_handle is not None:
            log_handle.close()
        cap.release()
        if not args.no_show:
            cv2.destroyAllWindows()

    # Tự động xuất đồ thị khi kết thúc luồng video / webcam
    if has_recorded and len(smoother.raw_trajectory) > 0:
        final_plot_path = os.path.join(out_dir, f"final_online_poly_smooth_trajectory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        save_trajectory_plot(smoother.raw_trajectory, smoother.smooth_trajectory, final_plot_path)

if __name__ == "__main__":
    main()
