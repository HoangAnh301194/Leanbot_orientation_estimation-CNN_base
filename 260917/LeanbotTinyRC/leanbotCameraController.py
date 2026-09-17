import cv2
import numpy as np
from collections import deque
import pandas as pd
import time
import psutil
import argparse
import csv
import os
import sys
import math
import re
import json
from pathlib import Path
from datetime import datetime
from ultralytics import YOLO
import openvino as ov
from PID_controller import create_position_pid
from LeanbotController import LeanbotController
from logs import logs_init, logs_shutdown
import asyncio
import threading
import queue


# Add directories to sys.path
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
sys.path.append(str(current_dir))
sys.path.append(str(parent_dir / "tools"))
sys.path.append(str(parent_dir))

import check_confidence
from angle_smoothing import AngleSmoothingEngine


IOU_THRES = 0.5
CLASS_ANGLE_MAP = {}
ANGLE_PATTERN = re.compile(r"^Leanbot_(?:(?P<sign>[pm])(?P<value>\d+)|(?P<plain>\d+))$")


def parse_angle_from_class_name(class_name: str):
    """Returns the angle (float) encoded in the class name, or None if not an angle class."""
    match = ANGLE_PATTERN.match(class_name)
    if not match:
        return None  # Not an angle class - caller decides fallback
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
    """Aggregate vector from all class scores using CLASS_ANGLE_MAP cache.
    Non-angle classes are ignored (same as webcam_vector_infer).
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
            continue  # Skip classes without angle
        theta_rad = math.radians(angle)
        sum_x += float(score) * math.cos(theta_rad)
        sum_y += float(score) * math.sin(theta_rad)
    magnitude = math.hypot(sum_x, sum_y)
    if magnitude <= 1e-9:
        return 0.0, 0.0
    angle_out = math.degrees(math.atan2(sum_y, sum_x))
    return magnitude, angle_out


# ---------------------------------------------------------------------------
# Helper functions for no-NMS pipeline (ported from webcam_vector_infer.py)
# ---------------------------------------------------------------------------

def box_iou_numpy(box, boxes):
    """Compute IoU between 1 box and an array of boxes (xyxy format)."""
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
    """Compute weighted average bounding box based on vector_magnitude."""
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
    """Greedy IoU grouping - group overlapping anchors into clusters."""
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
    """Compute combined vector for each anchor group."""
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

    # ------------------------------------------------------------------
    # NMS branch: 6-column output [x1, y1, x2, y2, conf, cls_id]
    # ------------------------------------------------------------------
    if pred.shape[1] == 6:
        valid_pred = pred[pred[:, 4] > 0.0]
        if len(valid_pred) == 0:
            return np.zeros(4, dtype=np.float32), 0.0, 0.0, 0.0, 0.0, 0.0
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
        return box_xyxy, best_conf, vector_angle, best_conf, 0.0, 0.0

    # ------------------------------------------------------------------
    # No-NMS branch: full vector pipeline (same as webcam_vector_infer.py)
    # Raw output: [x_c, y_c, w, h, score_cls0, ..., score_clsN]
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
    # Representative conf = highest score of the top anchor
    best_conf = float(best_scores_per_anchor[topk_idx[0]])

    # 3. Compute vector for each anchor
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

    # 4. Group anchors by IoU
    groups = group_anchors(raw_df, iou_thres=iou_thres)
    if not groups:
        return np.zeros(4, dtype=np.float32), 0.0, 0.0, 0.0, 0.0, 0.0

    # 5. Compute combined vector for each group
    summary_df = compute_group_vectors(groups)
    summary_df = summary_df[summary_df["vector_magnitude"] >= mag_threshold]
    if summary_df.empty:
        return np.zeros(4, dtype=np.float32), 0.0, 0.0, 0.0, 0.0, 0.0

    # Best group (highest magnitude - already sorted)
    best = summary_df.iloc[0]
    xc = float(best["x_center"])
    yc = float(best["y_center"])
    bw = float(best["width"])
    bh = float(best["height"])
    box_xyxy = np.array(
        [xc - bw / 2, yc - bh / 2, xc + bw / 2, yc + bh / 2],
        dtype=np.float32,
    )
    angle2 = 0.0
    mag2 = 0.0
    if len(summary_df) > 1:
        second_best = summary_df.iloc[1]
        angle2 = float(second_best["angle"])
        mag2 = float(second_best["vector_magnitude"])
    return box_xyxy, best_conf, float(best["angle"]), float(best["vector_magnitude"]), angle2, mag2


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
    max_side_32 = (min(img_w, img_h) // 32) * 32
    side_32 = min(side_32, max_side_32)
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


class BLEMotorWorker:
    """Runs BLE Leanbot communication on a dedicated background thread to avoid COM STA / Windows GUI conflicts with OpenCV."""
    def __init__(self, leanbot_id: int):
        self.leanbot_id = leanbot_id
        self.cmd_queue = queue.Queue(maxsize=1)
        self.running = True
        self.connected = False
        self.leanbot = None
        self.thread = threading.Thread(target=self._worker_thread, daemon=True)
        self.thread.start()

    def _worker_thread(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._async_loop())

    async def _async_loop(self):
        await logs_init()
        self.leanbot = LeanbotController(self.leanbot_id)
        try:
            print(f"[INFO] Connecting to Leanbot {self.leanbot_id} via BLE...")
            await self.leanbot.find()
            await self.leanbot.connect()
            self.connected = True
            print(f"[INFO] BLE connected to Leanbot {self.leanbot_id}! Navigation [READY]")
            
            while self.running:
                cmd = None
                try:
                    while not self.cmd_queue.empty():
                        cmd = self.cmd_queue.get_nowait()
                except Exception:
                    pass
                
                if cmd is not None:
                    try:
                        await self.leanbot.send(cmd, response=False)
                    except Exception as e:
                        print(f"[WARN] BLE send error: {e}")
                
                await asyncio.sleep(0.02)
        except Exception as e:
            print(f"[ERROR] Failed to connect BLE to Leanbot {self.leanbot_id}: {e}")
        finally:
            if self.leanbot is not None:
                try:
                    await self.leanbot.send("r/0/0\n", response=False)
                    await self.leanbot.disconnect()
                except Exception:
                    pass
            self.connected = False

    def send_speed(self, speed_l: int, speed_r: int):
        if not self.connected:
            return
        cmd = f"r/{speed_l}/{speed_r}\n"
        try:
            if self.cmd_queue.full():
                _ = self.cmd_queue.get_nowait()
            self.cmd_queue.put_nowait(cmd)
        except Exception:
            pass

    def stop(self):
        self.send_speed(0, 0)
        self.running = False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="0", help="Camera index or video path")
    parser.add_argument("--video", default="", help="Path to video file (takes priority over --source if provided)")
    parser.add_argument("--mode", default="roi", choices=["roi", "baseline"], help="Inference mode: roi or baseline")
    parser.add_argument("--log", default="", help="CSV log filename (auto-generated by mode if omitted)")
    parser.add_argument("--width", type=int, default=1280, help="Desired camera width (default 1280)")
    parser.add_argument("--height", type=int, default=720, help="Desired camera height (default 720)")
    parser.add_argument("--no-show", action="store_true", help="Disable OpenCV display windows")
    parser.add_argument("--show", action="store_true", help="Enable OpenCV windows if GUI is available")
    parser.add_argument("--device", default="CPU", choices=["CPU", "GPU", "AUTO"], help="OpenVINO inference device (default CPU)")
    parser.add_argument("--full-model", default=r"models\YOLO11n_versions\FP16_NO_NMS\best_fp16_no_nms_imgsz640_openvino_model", help="Path to full detection model directory")
    parser.add_argument("--tracking-model", default=r"models\YOLO11n_versions\FP16_NO_NMS\best_fp16_no_nms_imgsz160_openvino_model", help="Path to ROI tracking model directory")
    # --- Vector pipeline parameters (only used when model has no-NMS / raw output) ---
    parser.add_argument("--topk", type=int, default=100, help="Top-K anchors for no-NMS pipeline (default 100)")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold for FULL 640 anchor filter (default 0.25)")
    parser.add_argument("--roi_conf", type=float, default=0.15, help="Confidence threshold for ROI 160 anchor filter (default 0.15)")
    parser.add_argument("--iou", type=float, default=IOU_THRES, help="IoU threshold for anchor grouping (default 0.5)")
    parser.add_argument("--mag-threshold", type=float, default=2.0, help="Minimum vector magnitude to accept a group (default 2.0)")
    parser.add_argument("--debug-imgsz", action="store_true", help="Save debug images of resize/padding steps to benchmark/imgszdebug/")
    parser.add_argument("--fps", type=float, default=30.0, help="Maximum FPS limit (default 30.0)")
    # --- Angle smoothing pipeline parameters ---
    parser.add_argument("--smooth-window", type=int, default=18, help="Sliding window size for smoothing (default 18)")
    parser.add_argument("--smooth-index", type=int, default=0, help="Delayed tangent eval index (default 0)")
    parser.add_argument("--smooth-K", type=float, default=1.0, help="K constant for fused angle weighting (default 1.0)")
    # --- PID controller parameters ---
    parser.add_argument("--kp-angle", type=float, default=15.0, help="PID Phase 1 heading gain (default 15.0)")
    parser.add_argument("--kd-angle", type=float, default=0.0, help="PID Phase 1 derivative gain (default 0.0)")
    parser.add_argument("--kp-angle2", type=float, default=0.02, help="PID Phase 2 heading gain (default 0.02)")
    parser.add_argument("--kd-angle2", type=float, default=0.0, help="PID Phase 2 derivative gain (default 0.0)")
    parser.add_argument("--heading-tol", type=float, default=20.0, help="Heading tolerance in degrees (default 20.0)")
    parser.add_argument("--target-heading", type=float, default=None, help="Target heading in degrees for Phase 3 final alignment (default: None)")
    parser.add_argument("--heading-tol3", type=float, default=10.0, help="Phase 3 final heading tolerance in degrees (default 10.0)")
    parser.add_argument("--settle-time-ms", type=float, default=200.0, help="Hold time in ms to settle target heading before complete (default 200.0)")
    parser.add_argument("--fwd-bwd-time", type=float, default=3.0, help="Forward/backward test duration in seconds after Phase 3 (default 3.0, 0 to disable)")
    parser.add_argument("--fwd-bwd-speed", type=int, default=400, help="Wheel speed during forward/backward test (default 400)")
    # --- Set Target parameters (phím T / file JSON) ---
    parser.add_argument("--target-config", type=str, default="target_config.json", help="Path to target config JSON file (default: target_config.json)")
    parser.add_argument("--set-target-time", type=float, default=5.0, help="Set Target: duration (s) for fwd/bwd drive to fit heading (default 5.0)")
    parser.add_argument("--set-target-speed", type=int, default=800, help="Set Target: wheel speed during fwd/bwd drive (default 800)")
    parser.add_argument("--ble", type=int, default=0, help="Leanbot BLE ID to connect (e.g. --ble 123456, default 0: disabled)")
    args = parser.parse_args()
    if not args.show:
        args.no_show = True

    def resolve_path(p: str) -> str:
        if not p:
            return p
        if os.path.isabs(p) and os.path.exists(p):
            return p
        if os.path.exists(p):
            return p
        alt1 = os.path.join(str(parent_dir), p)
        if os.path.exists(alt1):
            return alt1
        alt2 = os.path.join(str(current_dir), p)
        if os.path.exists(alt2):
            return alt2
        return p

    full_model_path = resolve_path(args.full_model)
    tracking_model_path = resolve_path(args.tracking_model)

    source = args.video if args.video else args.source
    if isinstance(source, str) and not source.isdigit() and not os.path.exists(source):
        source = resolve_path(source)

    print("[INFO] Loading OpenVINO Models...")
    print(f"[INFO] Full detection model: {full_model_path}")
    print(f"[INFO] ROI tracking model: {tracking_model_path}")
    full_model = YOLO(full_model_path, task='detect')
    names = full_model.names
    ov_core = ov.Core()
    full_xml = [f for f in os.listdir(full_model_path) if f.endswith('.xml')][0]
    full_compiled_model = ov_core.compile_model(
        os.path.join(full_model_path, full_xml),
        args.device,
        {"PERFORMANCE_HINT": "LATENCY"}
    )
    print(f"[INFO] Full model execution device: {full_compiled_model.get_property('EXECUTION_DEVICES')}")

    if args.mode == "roi":
        tracking_model = YOLO(tracking_model_path, task='detect')
        tracking_xml = [f for f in os.listdir(tracking_model_path) if f.endswith('.xml')][0]
        tracking_compiled_model = ov_core.compile_model(
            os.path.join(tracking_model_path, tracking_xml),
            args.device,
            {"PERFORMANCE_HINT": "LATENCY"}
        )
        print(f"[INFO] ROI model execution device: {tracking_compiled_model.get_property('EXECUTION_DEVICES')}")
    else:
        tracking_compiled_model = None

    if source.isdigit():
        source = int(source)

    cap = cv2.VideoCapture(source)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    cap.set(cv2.CAP_PROP_FPS, 15)

    if not cap.isOpened():
        print(f"[ERROR] Failed to open video source: {source}")
        return

    prev_roi = None
    prev_bbox_xyxy = None
    frame_id = 0
    debug_full_saved = False
    debug_roi_saved = False
    benchmark_base = os.path.join(str(current_dir), "benchmark_logs")
    os.makedirs(benchmark_base, exist_ok=True)
    if args.debug_imgsz:
        debug_imgsz_dir = os.path.join(benchmark_base, "imgszdebug")
        os.makedirs(debug_imgsz_dir, exist_ok=True)
        print(f"[INFO] Debug imgsz: images will be saved to {debug_imgsz_dir}")

    lost_capture_dir = os.path.join(benchmark_base, "lost_tracking_captures")
    os.makedirs(lost_capture_dir, exist_ok=True)

    manual_capture_dir = os.path.join(benchmark_base, "manual_captures")
    os.makedirs(manual_capture_dir, exist_ok=True)

    # Initialize Process object to measure CPU usage of this script only
    current_process = psutil.Process()
    current_process.cpu_percent()  # First call initializes the measurement baseline

    csv_header = [
        "frame_id", "timestamp", "mode", "input_width", "input_height", "roi_w", "roi_h",
        "inf_time_ms", "end_to_end_time_ms", "cpu_load_pct", "end_to_end_cpu_load_pct", "fps",
        "x_center", "y_center", "width", "height", "iou_prev_bbox",
        "group1_magnitude", "group1_angle", "group2_magnitude", "group2_angle", "best_conf", "tracking_lost",
        "raw_angle", "model_angle_smooth", "trajectory_angle_smooth",
        "estimated_speed", "fused_angle", "fused_weight_x",
        "pid_mode", "target_angle", "angle_error",
        "target_x", "target_y", "distance_error",
        "ble_speed_left", "ble_speed_right"
    ]

    log_handle = None
    writer = None
    recording = False
    current_log_file = ""

    def start_recording():
        nonlocal log_handle, writer, recording, current_log_file
        if log_handle is not None:
            log_handle.close()
        
        if args.log:
            current_log_file = args.log if (os.path.isabs(args.log) or os.path.dirname(args.log)) else os.path.join(benchmark_base, args.log)
        else:
            current_log_file = os.path.join(benchmark_base, f"log_{args.mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
            
        os.makedirs(os.path.dirname(current_log_file) or ".", exist_ok=True)
        log_handle = open(current_log_file, mode='w', newline='')
        writer = csv.writer(log_handle)
        writer.writerow(csv_header)
        log_handle.flush()
        recording = True

        # Tự động ghi chỉ mục vào benchmark_logs/experiment_index.csv
        index_csv_path = os.path.join(benchmark_base, "experiment_index.csv")
        idx_exists = os.path.exists(index_csv_path)
        try:
            with open(index_csv_path, 'a', newline='') as idxf:
                idx_writer = csv.writer(idxf)
                if not idx_exists:
                    idx_writer.writerow([
                        "timestamp", "log_file", "target_heading_deg", "target_x", "target_y",
                        "kp_angle", "kd_angle", "kp_angle2", "kd_angle2",
                        "heading_tol3_deg", "settle_time_ms", "fwd_bwd_time_s", "fwd_bwd_speed"
                    ])
                th_val = f"{pos_pid.target_heading:.1f}" if pos_pid.target_heading is not None else "None"
                tx_val = f"{target_pos[0]:.1f}" if target_pos is not None else "None"
                ty_val = f"{target_pos[1]:.1f}" if target_pos is not None else "None"
                idx_writer.writerow([
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    os.path.basename(current_log_file),
                    th_val, tx_val, ty_val,
                    args.kp_angle, args.kd_angle, args.kp_angle2, args.kd_angle2,
                    args.heading_tol3, args.settle_time_ms, args.fwd_bwd_time, args.fwd_bwd_speed
                ])
                idxf.flush()
        except Exception as e:
            print(f"[WARN] Failed to write experiment index: {e}")

        th_str = f"{pos_pid.target_heading:.1f} deg" if pos_pid.target_heading is not None else "None"
        print(f"\n[INFO] >>> REC ON. Started recording: {os.path.basename(current_log_file)} | Target: {target_pos} @ {th_str} <<<\n")

    def stop_recording():
        nonlocal log_handle, writer, recording, current_log_file
        if log_handle is not None:
            log_handle.flush()
            log_handle.close()
        log_handle = None
        writer = None
        recording = False
        th_str = f"{pos_pid.target_heading:.1f} deg" if pos_pid.target_heading is not None else "None"
        print(f"\n[INFO] >>> REC OFF. Log saved: {os.path.basename(current_log_file)} | Target: {target_pos} @ {th_str} <<<\n")

    print(f"[INFO] Starting Inference ({args.mode.upper()} mode).")
    if args.no_show:
        print(f"[INFO] No-show mode: auto-recording log to {benchmark_base}")
        start_recording()
    elif args.video:
        print(f"[INFO] Video mode: auto-recording log to {benchmark_base}")
        start_recording()
        print("[INFO] Key controls: T = set target, S = start + record log, P = pause, C = cancel run, Q = quit.")
    else:
        print("[INFO] Key controls: T = set target, S = start + record log, P = pause, C = cancel run, Q = quit.")

    # Timeout feature has been removed

    pos_pid = create_position_pid(
        Kp_angle=args.kp_angle,
        Kd_angle=args.kd_angle,
        Kp_angle2=args.kp_angle2,
        Kd_angle2=args.kd_angle2,
        heading_tolerance_deg=args.heading_tol,
        target_heading=args.target_heading,
        heading_tolerance3_deg=args.heading_tol3,
        settle_time_ms=args.settle_time_ms,
        fwd_bwd_time_s=args.fwd_bwd_time,
        fwd_bwd_speed=args.fwd_bwd_speed,
    )
    ble_worker = BLEMotorWorker(args.ble) if args.ble > 0 else None
    is_auto_pid_enabled = False
    is_pid_completed = False
    target_pos = None

    # =====================================================================
    # SET TARGET STATE MACHINE (Phím T)
    # Giai đoạn 1: SET_TARGET_MEASURING_POS - Đo center x,y trung bình 3s
    # Giai đoạn 2: SET_TARGET_DRIVING - Chạy tiến lùi, thu thập quỹ đạo
    # Giai đoạn 3: SET_TARGET_DONE - Fit heading, lưu config, chuyển READY
    # =====================================================================
    SET_TARGET_IDLE = "IDLE"
    SET_TARGET_MEASURING_POS = "MEASURING_POS"
    SET_TARGET_DRIVING_FWD = "DRIVING_FWD"
    SET_TARGET_DRIVING_BWD = "DRIVING_BWD"
    SET_TARGET_DONE = "DONE"

    set_target_state = SET_TARGET_IDLE
    set_target_start_time = None
    set_target_pos_samples_x = []
    set_target_pos_samples_y = []
    set_target_traj_samples_x = []
    set_target_traj_samples_y = []
    set_target_measure_duration = 3.0  # seconds
    set_target_fwd_start_time = None
    set_target_bwd_start_time = None
    set_target_fwd_bwd_time = args.set_target_time
    set_target_fwd_bwd_speed = args.set_target_speed
    target_config_path = resolve_path(args.target_config)
    if not target_config_path or not os.path.exists(target_config_path):
        alt_cfg = os.path.join(str(current_dir), "target_config.json")
        if os.path.exists(alt_cfg):
            target_config_path = alt_cfg
        elif not target_config_path:
            target_config_path = alt_cfg

    # Auto-load target configuration from JSON if available
    target_pos = None
    loaded_from_json = False
    if os.path.exists(target_config_path):
        try:
            with open(target_config_path, 'r') as f:
                saved_cfg = json.load(f)
            if "target_x" in saved_cfg and "target_y" in saved_cfg:
                target_pos = (float(saved_cfg["target_x"]), float(saved_cfg["target_y"]))
                loaded_from_json = True
            if "target_heading" in saved_cfg and args.target_heading is None:
                pos_pid.target_heading = float(saved_cfg["target_heading"])
        except Exception as e:
            print(f"[WARN] Failed to load target config from {target_config_path}: {e}")

    # --- Initialize angle smoothing engine ---
    smoothing_engine = AngleSmoothingEngine(
        window_size=args.smooth_window,
        eval_index=args.smooth_index,
        K=args.smooth_K,
    )
    print("=" * 65)
    print(" [DEBUG CONFIGURATION ON STARTUP]")
    if loaded_from_json:
        print(f"  * Target Config    : {target_config_path} [LOADED]")
        print(f"  * Target Position  : ({target_pos[0]}, {target_pos[1]}) [FROM JSON]")
    else:
        print(f"  * Target Config    : {target_config_path} [NOT FOUND]")
        print(f"  * Target Position  : Center of frame (fallback)")
    print(f"  * Smoothing Engine : Window={args.smooth_window}, EvalIndex={args.smooth_index}, K={args.smooth_K}")
    print(f"  * PID Angle (Ph1)  : Kp={pos_pid.Kp_angle}, Ki={pos_pid.Ki_angle}, Kd={pos_pid.Kd_angle}")
    print(f"  * PID Dist  (Ph2)  : Kp={pos_pid.Kp_dist}, Ki={pos_pid.Ki_dist}, Kd={pos_pid.Kd_dist}")
    print(f"  * PID Angle2(Ph2)  : Kp={pos_pid.Kp_angle2}, Ki={pos_pid.Ki_angle2}, Kd={pos_pid.Kd_angle2}")
    print(f"  * Tolerances       : HeadingTol={pos_pid.heading_tolerance} deg, DistTol={pos_pid.dist_tolerance} px")
    if pos_pid.target_heading is not None:
        source_h = "FROM JSON" if (loaded_from_json and args.target_heading is None) else "FROM CLI"
        print(f"  * Phase 3 Target   : Heading={pos_pid.target_heading} deg [{source_h}], Tol3={pos_pid.heading_tolerance3} deg, Settle={pos_pid.settle_time_ms} ms")
    else:
        print("  * Phase 3 Target   : DISABLED (No target heading provided)")
    if pos_pid.fwd_bwd_time_s > 0:
        print(f"  * Phase 4 Test     : Fwd/Bwd {pos_pid.fwd_bwd_time_s}s each at Speed {pos_pid.fwd_bwd_speed}")
    else:
        print("  * Phase 4 Test     : DISABLED")
    print(f"  * Max Velocity     : {pos_pid.max_velocity} runLR units")
    print(f"  * BLE Target       : {args.ble if args.ble > 0 else 'OFF'}")
    print(f"  * Camera Mode      : {args.mode.upper()} ({args.width}x{args.height})")
    print("=" * 65)
    print("[INFO] Press T to calibrate target (position + heading), then S to start navigation.")

    # --- Realtime angle graph ---
    GRAPH_W, GRAPH_H = 600, 300
    GRAPH_MAX_POINTS = 200  # number of frames shown on the graph
    angle_history_model = deque(maxlen=GRAPH_MAX_POINTS)
    angle_history_traj = deque(maxlen=GRAPH_MAX_POINTS)
    angle_history_fused = deque(maxlen=GRAPH_MAX_POINTS)

    # Colors (BGR)
    COLOR_MODEL = (255, 120, 0)    # Blue
    COLOR_TRAJ  = (0, 140, 255)    # Orange
    COLOR_FUSED = (0, 220, 0)      # Green

    # Pre-allocated canvas to reduce CPU overhead
    graph_canvas = np.zeros((GRAPH_H, GRAPH_W, 3), dtype=np.uint8)

    def draw_angle_graph():
        """Draw 3 realtime angle lines on an OpenCV canvas (memory reuse)."""
        graph_canvas.fill(30)  # dark gray background

        margin_left, margin_right = 60, 20
        margin_top, margin_bottom = 30, 40
        plot_w = GRAPH_W - margin_left - margin_right
        plot_h = GRAPH_H - margin_top - margin_bottom

        # Drawing area
        cv2.rectangle(graph_canvas, (margin_left, margin_top),
                      (margin_left + plot_w, margin_top + plot_h), (50, 50, 50), -1)

        # Collect data values
        all_vals = []
        for v in list(angle_history_model) + list(angle_history_traj) + list(angle_history_fused):
            if v is not None:
                all_vals.append(v)

        if len(all_vals) < 2:
            cv2.putText(graph_canvas, "Waiting for data...", (GRAPH_W // 3, GRAPH_H // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (150, 150, 150), 1)
            return graph_canvas

        y_min = min(all_vals) - 5
        y_max = max(all_vals) + 5
        if y_max - y_min < 10:
            mid = (y_max + y_min) / 2
            y_min = mid - 5
            y_max = mid + 5

        n_points = max(len(angle_history_model), len(angle_history_traj), len(angle_history_fused))

        def val_to_pixel(idx, val):
            px = margin_left + int(idx / max(1, n_points - 1) * plot_w)
            py = margin_top + plot_h - int((val - y_min) / (y_max - y_min) * plot_h)
            py = max(margin_top, min(margin_top + plot_h, py))
            return px, py

        # Draw horizontal grid + Y-axis labels
        n_grid = 5
        for gi in range(n_grid + 1):
            gy = y_min + gi * (y_max - y_min) / n_grid
            _, py = val_to_pixel(0, gy)
            cv2.line(graph_canvas, (margin_left, py), (margin_left + plot_w, py), (70, 70, 70), 1)
            cv2.putText(graph_canvas, f"{gy:.0f}", (5, py + 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1)

        # Draw 3 angle lines
        def draw_line(history, color, thickness=2):
            pts = []
            for i, v in enumerate(history):
                if v is not None:
                    pts.append(val_to_pixel(i, v))
                else:
                    if len(pts) >= 2:
                        cv2.polylines(graph_canvas, [np.array(pts, dtype=np.int32)], False, color, thickness, cv2.LINE_AA)
                    pts = []
            if len(pts) >= 2:
                cv2.polylines(graph_canvas, [np.array(pts, dtype=np.int32)], False, color, thickness, cv2.LINE_AA)

        draw_line(angle_history_model, COLOR_MODEL, 2)
        draw_line(angle_history_traj, COLOR_TRAJ, 2)
        draw_line(angle_history_fused, COLOR_FUSED, 2)

        # Legend
        lx = margin_left + 10
        ly = margin_top + 15
        for label, color in [("Model Smooth", COLOR_MODEL), ("Traj Smooth", COLOR_TRAJ), ("Fused Angle", COLOR_FUSED)]:
            cv2.line(graph_canvas, (lx, ly), (lx + 25, ly), color, 2)
            cv2.putText(graph_canvas, label, (lx + 30, ly + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
            lx += 150

        # Axis labels
        cv2.putText(graph_canvas, "Angle (deg)", (5, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        cv2.putText(graph_canvas, f"Frames (last {GRAPH_MAX_POINTS})", (GRAPH_W // 2 - 60, GRAPH_H - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

        return graph_canvas

    windows_positioned = False
    fps_history = deque(maxlen=20)
    prev_frame_time = time.perf_counter()
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            t_now = time.perf_counter()
            dt = t_now - prev_frame_time
            prev_frame_time = t_now
            if dt > 0:
                fps_history.append(1.0 / dt)
            real_fps = (sum(fps_history) / len(fps_history)) if fps_history else 0.0

            orig_frame = frame.copy()

            frame_id += 1
            timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            img_h, img_w = frame.shape[:2]
            if target_pos is None:
                target_pos = (img_w // 2, img_h // 2)
                print(f"[INFO] Fixed target at frame center: {target_pos}. Press S to start.")

            t0 = time.time()
            # Measure CPU % of this process only, divided by core count to normalize to 100%
            cpu_load = current_process.cpu_percent() / psutil.cpu_count()

            inference_mode = "FULL"
            offset_x, offset_y = 0, 0
            roi_scale_x, roi_scale_y = 1.0, 1.0
            tracking_lost = 0
            lost_roi_input = None
            roi_w, roi_h = 0, 0
            display_bbox = None

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
                infer_model = tracking_compiled_model
                # --- Debug imgsz: ROI mode ---
                if args.debug_imgsz and not debug_roi_saved:
                    cv2.imwrite(os.path.join(debug_imgsz_dir, "roi_01_raw_frame.png"), frame)
                    cv2.imwrite(os.path.join(debug_imgsz_dir, "roi_02_cropped_roi.png"), roi_input)
                    cv2.imwrite(os.path.join(debug_imgsz_dir, "roi_03_resized_160.png"), inference_input)
                    debug_roi_saved = True
                    print(f"[DEBUG] Saved ROI debug images (frame {frame_id}): roi_input {roi_input.shape[1]}x{roi_input.shape[0]} -> 160x160")
            else:
                # --- Separate steps for debug ---
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
                # --- Debug imgsz: FULL mode ---
                if args.debug_imgsz and not debug_full_saved:
                    cv2.imwrite(os.path.join(debug_imgsz_dir, "full_01_raw_frame.png"), frame)
                    cv2.imwrite(os.path.join(debug_imgsz_dir, "full_02_cropped.png"), cropped)
                    cv2.imwrite(os.path.join(debug_imgsz_dir, "full_03_padded.png"), padded)
                    cv2.imwrite(os.path.join(debug_imgsz_dir, "full_04_resized_640.png"), inference_input)
                    debug_full_saved = True
                    print(f"[DEBUG] Saved FULL debug images (frame {frame_id}): {img_w_orig}x{img_h_orig} -> crop {crop_w}x{crop_h} -> pad {square_size}x{square_size} -> 640x640")

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
                    iou_prev = 1.0  # First frame: 100% overlap by convention
                prev_bbox_xyxy = current_box_xyxy.copy()

                bw = orig_x2 - orig_x1
                bh = orig_y2 - orig_y1
                cx = orig_x1 + bw / 2.0
                cy = orig_y1 + bh / 2.0

                if args.mode == "roi":
                    # Update ROI immediately after every successful detection frame
                    prev_roi = calculate_roi(best_box, img_w, img_h)

                display_bbox = (int(orig_x1), int(orig_y1), int(orig_x2), int(orig_y2))
            else:
                # Detection lost: both ROI mode (lost tracking) and FULL/baseline mode (no detection)
                tracking_lost = 1
                prev_roi = None
                prev_bbox_xyxy = None
                iou_prev = 0.0

            # --- Angle smoothing pipeline ---
            smooth_result = smoothing_engine.update(
                raw_angle=angle,
                x_center=cx,
                y_center=cy,
                detected=detected,
            )
            sm_model   = smooth_result["model_angle_smooth"]
            sm_traj    = smooth_result["trajectory_angle_smooth"]
            sm_speed   = smooth_result["estimated_speed"]
            sm_fused   = smooth_result["fused_angle"]
            sm_weight  = smooth_result["fused_weight_x"]

            end_to_end_time_ms = (time.time() - t0) * 1000  # ms
            end_to_end_cpu_load_pct = current_process.cpu_percent() / psutil.cpu_count()
            fps = 1000.0 / end_to_end_time_ms if end_to_end_time_ms > 0 else 0

            # Format smoothed values (None -> "NaN")
            def _fmt(v, fmt=".4f"):
                return f"{v:{fmt}}" if v is not None else "NaN"

            speed_l, speed_r = 0, 0
            dist_err = 0.0
            ang_err = 0.0
            target_heading = 0.0
            pos_state = "READY"

            # =================================================================
            # SET TARGET STATE MACHINE - Xử lý trước PID chính
            # =================================================================
            if set_target_state == SET_TARGET_MEASURING_POS:
                # Giai đoạn 1: Đo tọa độ trung bình trong 3 giây
                elapsed_measure = time.perf_counter() - set_target_start_time
                if detected:
                    set_target_pos_samples_x.append(cx)
                    set_target_pos_samples_y.append(cy)
                # Giữ xe đứng yên
                if ble_worker is not None:
                    ble_worker.send_speed(0, 0)
                remaining = max(0, set_target_measure_duration - elapsed_measure)
                n_samples = len(set_target_pos_samples_x)
                pid_status_txt = f"[SET TARGET] Measuring position... {remaining:.1f}s left ({n_samples} samples)"
                nav_sub_txt = "Hold still - collecting center samples"
                pid_color_type = "AUTO"
                pos_state = "SET_TARGET_MEASURING"

                if elapsed_measure >= set_target_measure_duration:
                    if n_samples >= 5:
                        avg_x = round(sum(set_target_pos_samples_x) / n_samples, 1)
                        avg_y = round(sum(set_target_pos_samples_y) / n_samples, 1)
                        target_pos = (avg_x, avg_y)
                        print(f"\n[SET TARGET] Phase 1 DONE: target_pos = ({avg_x}, {avg_y}) from {n_samples} samples.")
                        print(f"[SET TARGET] Phase 2 START: Driving forward for {set_target_fwd_bwd_time}s at speed {set_target_fwd_bwd_speed}...")
                        set_target_state = SET_TARGET_DRIVING_FWD
                        set_target_fwd_start_time = time.perf_counter()
                        set_target_traj_samples_x = []
                        set_target_traj_samples_y = []
                    else:
                        print(f"\n[SET TARGET] FAILED: Only {n_samples} samples detected in 3s (need >= 5). Aborting.")
                        set_target_state = SET_TARGET_IDLE

            elif set_target_state == SET_TARGET_DRIVING_FWD:
                # Giai đoạn 2A: Chạy tiến thẳng, thu thập quỹ đạo
                elapsed_fwd = time.perf_counter() - set_target_fwd_start_time
                if detected:
                    set_target_traj_samples_x.append(cx)
                    set_target_traj_samples_y.append(cy)
                speed_l = set_target_fwd_bwd_speed
                speed_r = set_target_fwd_bwd_speed
                if ble_worker is not None:
                    ble_worker.send_speed(speed_l, speed_r)
                remaining = max(0, set_target_fwd_bwd_time - elapsed_fwd)
                pid_status_txt = f"[SET TARGET] Driving FWD... {remaining:.1f}s left ({len(set_target_traj_samples_x)} pts)"
                nav_sub_txt = f"FWD: L={speed_l} R={speed_r}"
                pid_color_type = "AUTO"
                pos_state = "SET_TARGET_FWD"

                if elapsed_fwd >= set_target_fwd_bwd_time:
                    print(f"[SET TARGET] FWD done ({len(set_target_traj_samples_x)} pts). Now driving BWD...")
                    set_target_state = SET_TARGET_DRIVING_BWD
                    set_target_bwd_start_time = time.perf_counter()

            elif set_target_state == SET_TARGET_DRIVING_BWD:
                # Giai đoạn 2B: Chạy lùi thẳng, thu thập quỹ đạo
                elapsed_bwd = time.perf_counter() - set_target_bwd_start_time
                if detected:
                    set_target_traj_samples_x.append(cx)
                    set_target_traj_samples_y.append(cy)
                speed_l = -set_target_fwd_bwd_speed
                speed_r = -set_target_fwd_bwd_speed
                if ble_worker is not None:
                    ble_worker.send_speed(speed_l, speed_r)
                remaining = max(0, set_target_fwd_bwd_time - elapsed_bwd)
                pid_status_txt = f"[SET TARGET] Driving BWD... {remaining:.1f}s left ({len(set_target_traj_samples_x)} pts)"
                nav_sub_txt = f"BWD: L={speed_l} R={speed_r}"
                pid_color_type = "AUTO"
                pos_state = "SET_TARGET_BWD"

                if elapsed_bwd >= set_target_fwd_bwd_time:
                    # Dừng xe
                    if ble_worker is not None:
                        ble_worker.send_speed(0, 0)
                    # Giai đoạn 3: Linear fit heading từ quỹ đạo thu thập được
                    n_traj = len(set_target_traj_samples_x)
                    if n_traj >= 5:
                        t_norm = np.linspace(0.0, 1.0, n_traj)
                        px_fit = np.polyfit(t_norm, set_target_traj_samples_x, deg=1)
                        py_fit = np.polyfit(t_norm, set_target_traj_samples_y, deg=1)
                        dx_fit = float(px_fit[0])
                        dy_fit = float(py_fit[0])
                        theta_fit = float(np.degrees(np.arctan2(-dy_fit, dx_fit)))
                        target_heading_value = round(theta_fit, 2)

                        # Cập nhật PID controller
                        pos_pid.target_heading = target_heading_value
                        print(f"\n{'='*65}")
                        print(f" [SET TARGET] COMPLETED SUCCESSFULLY!")
                        print(f"   Target Position : ({target_pos[0]}, {target_pos[1]})")
                        print(f"   Target Heading  : {target_heading_value} deg")
                        print(f"   Trajectory pts  : {n_traj}")
                        print(f"   Linear fit      : dx={dx_fit:.2f}, dy={dy_fit:.2f}")
                        print(f"{'='*65}")

                        # 1. Lưu ra file target_config.json (ghi đè target mới nhất)
                        config_data = {
                            "target_x": round(float(target_pos[0]), 1),
                            "target_y": round(float(target_pos[1]), 1),
                            "target_heading": round(float(target_heading_value), 1),
                        }
                        try:
                            with open(target_config_path, 'w') as f:
                                json.dump(config_data, f, indent=2)
                            print(f"[SET TARGET] Latest config saved to: {target_config_path}")
                        except Exception as e:
                            print(f"[WARN] Failed to save target config: {e}")

                        # 2. Append vào file lịch sử target_history.json
                        target_history_path = os.path.join(str(current_dir), "target_history.json")
                        history_list = []
                        if os.path.exists(target_history_path):
                            try:
                                with open(target_history_path, 'r') as hf:
                                    history_list = json.load(hf)
                                if not isinstance(history_list, list):
                                    history_list = []
                            except Exception:
                                history_list = []

                        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        entry = {
                            "target_id": len(history_list) + 1,
                            "calibrated_at": now_str,
                            "target_x": round(float(target_pos[0]), 1),
                            "target_y": round(float(target_pos[1]), 1),
                            "target_heading": round(float(target_heading_value), 1),
                            "trajectory_points": int(n_traj),
                            "fit_dx": round(dx_fit, 2),
                            "fit_dy": round(dy_fit, 2),
                        }
                        history_list.append(entry)
                        try:
                            with open(target_history_path, 'w') as hf:
                                json.dump(history_list, hf, indent=2)
                            print(f"[SET TARGET] Appended to history JSON #{entry['target_id']}: ({entry['target_x']}, {entry['target_y']}) @ {entry['target_heading']} deg")
                        except Exception as e:
                            print(f"[WARN] Failed to append target history JSON: {e}")

                        # 3. Append vào file lịch sử target_history.csv dạng bảng
                        target_history_csv = os.path.join(str(current_dir), "target_history.csv")
                        th_csv_exists = os.path.exists(target_history_csv)
                        try:
                            with open(target_history_csv, 'a', newline='') as cf:
                                c_writer = csv.writer(cf)
                                if not th_csv_exists:
                                    c_writer.writerow(["target_id", "calibrated_at", "target_x", "target_y", "target_heading", "points", "fit_dx", "fit_dy"])
                                c_writer.writerow([
                                    entry["target_id"], entry["calibrated_at"],
                                    entry["target_x"], entry["target_y"], entry["target_heading"],
                                    entry["trajectory_points"], entry["fit_dx"], entry["fit_dy"]
                                ])
                        except Exception as e:
                            print(f"[WARN] Failed to append target history CSV: {e}")
                    else:
                        print(f"\n[SET TARGET] WARNING: Only {n_traj} trajectory points (need >= 5).")
                        print(f"[SET TARGET] Target position set but heading NOT updated.")

                    set_target_state = SET_TARGET_IDLE
                    is_auto_pid_enabled = False
                    is_pid_completed = False
                    pos_pid.reset()
                    print(f"[SET TARGET] Ready. Press S to start PID navigation to target.\n")

            # =================================================================
            # MAIN PID CONTROLLER (chỉ chạy khi KHÔNG đang trong Set Target)
            # =================================================================
            elif is_pid_completed:
                pos_state = "COMPLETED"
                pid_status_txt = f"Target: ({target_pos[0]}, {target_pos[1]}) [COMPLETED]"
                nav_sub_txt = "P-only: L=   0 R=   0 | No heading correction at target"
                pid_color_type = "COMPLETED"
            elif not is_auto_pid_enabled:
                pos_state = "READY"
                pid_status_txt = f"Target: ({target_pos[0]}, {target_pos[1]}) [READY - PRESS S]"
                nav_sub_txt = "P-only: waiting for start command"
                pid_color_type = "PAUSED"
            elif sm_fused is not None and detected:
                speed_l, speed_r, dbg_pos = pos_pid.compute(
                    current_x=cx,
                    current_y=cy,
                    current_angle=sm_fused,
                    target_x=target_pos[0],
                    target_y=target_pos[1],
                    current_time=time.perf_counter(),
                )
                dist_err = dbg_pos["distance"]
                ang_err = dbg_pos["angle_error"]
                target_heading = dbg_pos["target_heading"]
                pos_state = dbg_pos["state"]
                is_pid_completed = dbg_pos["is_completed"]
                if is_pid_completed:
                    is_auto_pid_enabled = False
                    # Auto-stop logging when Leanbot reaches target
                    if recording:
                        print("[INFO] Leanbot reached target -> Auto-stopping log recording.")
                        stop_recording()

                pid_status_txt = (
                    f"Target: ({target_pos[0]}, {target_pos[1]}) | "
                    f"DistErr: {dist_err:.1f}px | State: {pos_state}"
                )
                if pos_state == "PHASE_3_FINAL_ALIGNING":
                    nav_sub_txt = (
                        f"Ph3 Spin: L={speed_l:4d} R={speed_r:4d} | "
                        f"FinalAngErr={ang_err:5.1f}deg (Tgt={target_heading:.1f})"
                    )
                elif pos_state == "PHASE_4_FORWARD":
                    nav_sub_txt = (
                        f"Ph4 FWD: L={speed_l:4d} R={speed_r:4d} | "
                        f"Target={target_heading:.1f}deg"
                    )
                elif pos_state == "PHASE_4_BACKWARD":
                    nav_sub_txt = (
                        f"Ph4 BWD: L={speed_l:4d} R={speed_r:4d} | "
                        f"Target={target_heading:.1f}deg"
                    )
                else:
                    nav_sub_txt = (
                        f"P-only: L={speed_l:4d} R={speed_r:4d} | "
                        f"AngErr={ang_err:5.1f}deg"
                    )
                pid_color_type = "ALIGNED" if is_pid_completed else "AUTO"
            else:
                pos_state = "LOST_TRACKING"
                pid_status_txt = f"Target: ({target_pos[0]}, {target_pos[1]}) [LOST TRACKING]"
                nav_sub_txt = "P-only: L=   0 R=   0 | Holding current phase"
                pid_color_type = "LOST"

            # Send control command to Leanbot via BLE Worker (thread-safe, non-blocking)
            # Lưu ý: khi đang trong Set Target (FWD/BWD), tốc độ đã được gửi ở state machine phía trên
            if ble_worker is not None:
                if set_target_state in (SET_TARGET_MEASURING_POS, SET_TARGET_DRIVING_FWD, SET_TARGET_DRIVING_BWD):
                    pass  # Tốc độ đã được gửi trong state machine Set Target
                elif is_auto_pid_enabled and not is_pid_completed:
                    ble_worker.send_speed(speed_l, speed_r)
                else:
                    ble_worker.send_speed(0, 0)

            if recording and writer is not None:
                rec_pid_mode = pos_state
                rec_target_angle = float(target_heading)
                rec_angle_error = float(ang_err)
                rec_target_x = float(target_pos[0])
                rec_target_y = float(target_pos[1])
                rec_dist_error = float(dist_err)

                rec_speed_l = speed_l if (is_auto_pid_enabled and not is_pid_completed) else 0
                rec_speed_r = speed_r if (is_auto_pid_enabled and not is_pid_completed) else 0

                writer.writerow([
                    frame_id, timestamp, inference_mode, input_w, input_h, roi_w, roi_h,
                    f"{total_inf_time:.2f}", f"{end_to_end_time_ms:.2f}", cpu_load,
                    end_to_end_cpu_load_pct, f"{fps:.2f}",
                    f"{cx:.2f}", f"{cy:.2f}", f"{bw:.2f}", f"{bh:.2f}", f"{iou_prev:.4f}",
                    f"{vector_magnitude:.4f}", f"{angle:.4f}", f"{mag2:.4f}", f"{angle2:.4f}", f"{best_conf:.4f}", tracking_lost,
                    f"{angle:.4f}", _fmt(sm_model), _fmt(sm_traj),
                    _fmt(sm_speed), _fmt(sm_fused), _fmt(sm_weight),
                    rec_pid_mode, f"{rec_target_angle:.2f}", f"{rec_angle_error:.2f}",
                    f"{rec_target_x:.1f}", f"{rec_target_y:.1f}", f"{rec_dist_error:.2f}",
                    rec_speed_l, rec_speed_r,
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
                detection_frame = orig_frame.copy()

                target_roi_w = 360
                target_roi_h = 360

                if lost_roi_input is not None and lost_roi_input.size > 0:
                    roi_display = cv2.resize(lost_roi_input, (target_roi_w, target_roi_h))
                else:
                    roi_display = np.zeros((target_roi_h, target_roi_w, 3), dtype=np.uint8)

                if display_bbox is not None:
                    x1, y1, x2, y2 = display_bbox
                    cv2.rectangle(detection_frame, (x1, y1), (x2, y2), (0, 255, 0), 4)

                # Draw target pixel and yellow connecting line on detection_frame
                if target_pos is not None:
                    tx, ty = int(target_pos[0]), int(target_pos[1])
                    cv2.circle(detection_frame, (tx, ty), 10, (0, 0, 255), -1)
                    cv2.circle(detection_frame, (tx, ty), 18, (0, 255, 255), 2)
                    tgt_lbl = f"TARGET ({tx}, {ty})"
                    if pos_pid.target_heading is not None:
                        tgt_lbl += f" @ {pos_pid.target_heading:.1f} deg"
                        # Draw heading arrow from target (45 px)
                        rad_th = math.radians(pos_pid.target_heading)
                        hx = int(tx + 45 * math.cos(rad_th))
                        hy = int(ty - 45 * math.sin(rad_th))
                        cv2.arrowedLine(detection_frame, (tx, ty), (hx, hy), (0, 255, 255), 3, tipLength=0.35)
                    cv2.putText(detection_frame, tgt_lbl, (tx + 15, ty - 5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)
                    if detected:
                        cv2.line(detection_frame, (int(cx), int(cy)), (tx, ty), (0, 255, 255), 2)

                # Keep full 16:9 aspect ratio (no crop), scale down by 2x
                disp_w = max(320, int(img_w / 2))
                disp_h = max(180, int(img_h / 2))
                detection_display = cv2.resize(detection_frame, (disp_w, disp_h), interpolation=cv2.INTER_NEAREST)

                cv2.putText(roi_display, f"FPS: {real_fps:.1f} | Proc: {end_to_end_time_ms:.1f}ms", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                cv2.putText(roi_display, f"ROI: {roi_w}x{roi_h}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 0, 0), 2)

                cv2.putText(detection_display, f"FPS: {real_fps:.1f} | Proc: {end_to_end_time_ms:.1f}ms", (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                model_txt = f"{sm_model:.1f} deg" if sm_model is not None else "N/A"
                fused_txt = f"{sm_fused:.1f} deg" if sm_fused is not None else "N/A"
                cv2.putText(detection_display, f"Raw: {angle:.1f} deg | Smooth: {model_txt} | Fused: {fused_txt}", (10, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 2)

                # Display PID status / Target Pixel / Pixel Error
                if pid_color_type == "COMPLETED" or pid_color_type == "ALIGNED":
                    pid_color = (0, 255, 0)
                elif pid_color_type == "AUTO":
                    pid_color = (180, 50, 0)  # Navy Blue in BGR
                elif pid_color_type == "LOST" or pid_color_type == "STOPPED":
                    pid_color = (0, 0, 255)
                else:
                    pid_color = (150, 150, 150)

                cv2.putText(detection_display, pid_status_txt, (10, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.42, pid_color, 2)
                if nav_sub_txt:
                    cv2.putText(detection_display, nav_sub_txt, (10, 82), cv2.FONT_HERSHEY_SIMPLEX, 0.42, pid_color, 2)

                # --- Update angle graph ---
                angle_history_model.append(sm_model)
                angle_history_traj.append(sm_traj)
                angle_history_fused.append(sm_fused)
                graph_canvas = draw_angle_graph()
                if recording and tracking_lost:
                    save_lost_tracking_images()

                try:
                    cv2.imshow("Leanbot Detection", detection_display)
                    cv2.imshow("ROI View", roi_display)
                    cv2.imshow("Angle Graph", graph_canvas)
                    if not windows_positioned:
                        cv2.moveWindow("Leanbot Detection", 0, 0)
                        cv2.moveWindow("ROI View", disp_w + 15, 0)
                        cv2.moveWindow("Angle Graph", 0, disp_h + 35)
                        windows_positioned = True
                    key = cv2.waitKey(1) & 0xFF
                    if key in (ord('q'), ord('Q')):
                        break
                    if key in (ord('p'), ord('P')):
                        is_auto_pid_enabled = False
                        print("[INFO] PAUSED. Press S to restart from Phase 1.")
                        if ble_worker is not None:
                            ble_worker.send_speed(0, 0)
                    def do_manual_capture(tag="manual_cap"):
                        cap_time = datetime.now().strftime('%Y%m%d_%H%M%S')
                        roi_ui_path = os.path.join(manual_capture_dir, f"{tag}_{frame_id}_{cap_time}_roi_ui.png")
                        detection_ui_path = os.path.join(manual_capture_dir, f"{tag}_{frame_id}_{cap_time}_detection_ui.png")
                        orig_path = os.path.join(manual_capture_dir, f"{tag}_{frame_id}_{cap_time}_orig.png")
                        cv2.imwrite(roi_ui_path, roi_display)
                        cv2.imwrite(detection_ui_path, detection_display)
                        cv2.imwrite(orig_path, orig_frame)
                        print(f"\n[INFO] CAPTURE ({tag.upper()}, Frame {frame_id}):\n       - ROI UI: {roi_ui_path}\n       - Detection UI: {detection_ui_path}\n       - Original: {orig_path}\n")

                    if key in (ord('s'), ord('S')):
                        pos_pid.reset()
                        is_pid_completed = False
                        is_auto_pid_enabled = True
                        th_info = f"{pos_pid.target_heading:.1f} deg" if pos_pid.target_heading is not None else "None"
                        print(f"[INFO] START: target={target_pos}, target_heading={th_info}. Beginning Phase 1.")
                        if ble_worker is not None:
                            ble_worker.send_speed(0, 0)
                        # Auto-start log recording when S is pressed
                        if not recording:
                            start_recording()
                        # Auto-capture upon start
                        do_manual_capture(tag="manual_cap")
                    if key in (ord('c'), ord('C')):
                        is_pid_completed = False
                        is_auto_pid_enabled = False
                        pos_pid.reset()
                        # Reset Set Target state machine nếu đang chạy
                        if set_target_state != SET_TARGET_IDLE:
                            print(f"[SET TARGET] Cancelled (was in {set_target_state}).")
                            set_target_state = SET_TARGET_IDLE
                        if ble_worker is not None:
                            ble_worker.send_speed(0, 0)
                        if recording:
                            stop_recording()
                        print("\n[KEY 'c'] RUN CANCELLED -> Stopped and log file closed/saved.\n")
                    if key in (ord('k'), ord('K')):
                        do_manual_capture(tag="manual_cap")
                    if key in (ord('t'), ord('T')):
                        if set_target_state == SET_TARGET_IDLE:
                            # Bắt đầu quy trình Set Target
                            is_auto_pid_enabled = False
                            is_pid_completed = False
                            pos_pid.reset()
                            if ble_worker is not None:
                                ble_worker.send_speed(0, 0)
                            set_target_pos_samples_x = []
                            set_target_pos_samples_y = []
                            set_target_traj_samples_x = []
                            set_target_traj_samples_y = []
                            set_target_start_time = time.perf_counter()
                            set_target_state = SET_TARGET_MEASURING_POS
                            print(f"\n{'='*65}")
                            print(f" [SET TARGET] Started! Hold Leanbot still at target position.")
                            print(f" [SET TARGET] Measuring center (x,y) for {set_target_measure_duration}s...")
                            print(f"{'='*65}")
                        else:
                            print(f"[SET TARGET] Already in progress (state={set_target_state}). Wait or press C to cancel.")
                except cv2.error as exc:
                    print(f"[WARN] OpenCV GUI not available, switching to --no-show mode: {exc}")
                    args.no_show = True
                    if not recording:
                        start_recording()
            else:
                if recording and tracking_lost:
                    save_lost_tracking_images()
                if frame_id % 10 == 0:
                    print(f"[LOG] Frame {frame_id} | Mode: {inference_mode} | FPS: {real_fps:.1f} (Proc: {end_to_end_time_ms:.1f}ms) | CPU: {end_to_end_cpu_load_pct}% | REC: {recording}")

    finally:
        if ble_worker is not None:
            print("[INFO] Stopping Leanbot and disconnecting BLE Worker...")
            ble_worker.stop()
        if log_handle is not None:
            log_handle.close()

    cap.release()
    if not args.no_show:
        cv2.destroyAllWindows()
    print(f"[INFO] Done. Log directory: {benchmark_base}")


if __name__ == "__main__":
    main()
