import argparse
import sys
import time
from pathlib import Path
import math
import re
import csv
from datetime import datetime

import cv2
import numpy as np
import pandas as pd
import torch

# Add current directory to sys.path for importing check_confidence
sys.path.append(str(Path(__file__).resolve().parent))
import check_confidence

DEFAULT_MODEL_DIR = Path(__file__).resolve().parent

# --- HANG SO & REGEX ---
IOU_THRES = 0.5
ANGLE_PATTERN = re.compile(r"^Leanbot_(?:(?P<sign>[pm])(?P<value>\d+)|(?P<plain>\d+))$")
CLASS_ANGLE_MAP = {}

def parse_angle_from_class_name(class_name: str) -> float | None:
    match = ANGLE_PATTERN.match(class_name)
    if not match: return None
    if match.group("plain") is not None: return float(match.group("plain"))
    value = float(match.group("value"))
    return value if match.group("sign") == "p" else -value

def get_vector_from_scores(class_scores, names) -> tuple[float, float]:
    sum_x = 0.0
    sum_y = 0.0
    for cls_id, score in enumerate(class_scores):
        cls_name = names[cls_id]
        angle = CLASS_ANGLE_MAP.get(cls_name)
        if angle is None: continue
        theta = math.radians(angle)
        sum_x += score * math.cos(theta)
        sum_y += score * math.sin(theta)
    mag = math.hypot(sum_x, sum_y)
    if mag <= 1e-9: return 0.0, 0.0
    return mag, math.degrees(math.atan2(sum_y, sum_x))

def box_iou_numpy(box, boxes):
    if len(boxes) == 0: return np.array([])
    x1 = np.maximum(box[0], boxes[:, 0])
    y1 = np.maximum(box[1], boxes[:, 1])
    x2 = np.minimum(box[2], boxes[:, 2])
    y2 = np.minimum(box[3], boxes[:, 3])
    inter = np.maximum(0, x2 - x1) * np.maximum(0, y2 - y1)
    area_box = max(0, box[2] - box[0]) * max(0, box[3] - box[1])
    area_boxes = np.maximum(0, boxes[:, 2] - boxes[:, 0]) * np.maximum(0, boxes[:, 3] - boxes[:, 1])
    return inter / (area_box + area_boxes - inter + 1e-9)

def compute_weighted_bbox(group_df):
    w = group_df["vector_magnitude"].values
    total = w.sum()
    if total <= 1e-9:
        return float(group_df["x_center"].mean()), float(group_df["y_center"].mean()), float(group_df["width"].mean()), float(group_df["height"].mean())
    return (
        float(np.dot(w, group_df["x_center"].values) / total),
        float(np.dot(w, group_df["y_center"].values) / total),
        float(np.dot(w, group_df["width"].values) / total),
        float(np.dot(w, group_df["height"].values) / total)
    )

def group_anchors(df, iou_thres=IOU_THRES):
    if len(df) == 0: return []
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
        n = len(gdf)
        
        best_row = gdf.loc[gdf["vector_magnitude"].idxmax()]
        gx = float(best_row.get("group_x_center", best_row["x_center"]))
        gy = float(best_row.get("group_y_center", best_row["y_center"]))
        gw = float(best_row.get("group_width", best_row["width"]))
        gh = float(best_row.get("group_height", best_row["height"]))
        
        rows.append({
            "group_id": gid,
            "number_of_anchors": n,
            "vector_magnitude": round(group_mag, 2),
            "x_center": round(gx, 2),
            "y_center": round(gy, 2),
            "width": round(gw, 2),
            "height": round(gh, 2),
            "angle": round(group_ang, 2)
        })
    df_out = pd.DataFrame(rows)
    if not df_out.empty:
        df_out = df_out.sort_values("vector_magnitude", ascending=False).reset_index(drop=True)
    return df_out

def find_default_model() -> Path | None:
    preferred_candidates = [
        DEFAULT_MODEL_DIR / "best_24Class_Soft_Angular_BCE.pt",
        DEFAULT_MODEL_DIR / "best_24Class_Default_BCE.pt",
        DEFAULT_MODEL_DIR / "best.pt",
    ]
    for candidate in preferred_candidates:
        if candidate.exists():
            return candidate
    pt_files = sorted(DEFAULT_MODEL_DIR.glob("*.pt"), key=lambda path: path.stat().st_mtime)
    return pt_files[-1] if pt_files else None

def run_realtime_inference(model, frame, args, csv_writer, frame_id, timestamp):
    names = model.names
    nc = len(names)
    
    # Initialize CLASS_ANGLE_MAP if empty
    if not CLASS_ANGLE_MAP:
        for cid, cname in names.items():
            a = parse_angle_from_class_name(cname)
            if a is not None:
                CLASS_ANGLE_MAP[cname] = a

    if args.mirror:
        frame = cv2.flip(frame, 1)
        
    # Preprocess (Full Frame Letterbox)
    from ultralytics.data.augment import LetterBox
    letterbox = LetterBox(new_shape=(640, 640), auto=False, stride=32)
    img640 = letterbox(image=frame)
    img_tensor = img640[:, :, ::-1].transpose(2, 0, 1)
    img_tensor = torch.from_numpy(np.ascontiguousarray(img_tensor)).to(model.device).float() / 255.0
    img_tensor = img_tensor.unsqueeze(0)
    
    # Inference without NMS
    t0 = time.time()
    with torch.no_grad():
        raw_pred = model.model(img_tensor)
        
    raw_pred = raw_pred[0] if isinstance(raw_pred, (tuple, list)) else raw_pred
    if raw_pred.shape[1] != 4 + nc and raw_pred.shape[2] == 4 + nc:
        raw_pred = raw_pred.permute(0, 2, 1)
        
    raw_boxes_xywh = raw_pred[0, :4, :].T
    raw_class_scores = raw_pred[0, 4:4+nc, :].T
    
    annotated = frame.copy()
    
    # 1. Confidence Filter & Top-K Selection
    max_scores, _ = raw_class_scores.max(dim=1)
    
    conf_mask = max_scores > args.conf
    filtered_idx = torch.nonzero(conf_mask).view(-1)
    filtered_scores = max_scores[filtered_idx]
    
    total_anchors = len(filtered_scores)
    
    if total_anchors == 0:
        t1 = time.time()
        print(f"\n--- Frame {frame_id} | Time: {timestamp} | Calc Time: {(t1 - t0) * 1000:.1f}ms ---")
        print(" No objects detected (filtered by conf).")
        return annotated
        
    topk_actual = min(args.topk, total_anchors)
    _, topk_relative_idx = torch.topk(filtered_scores, topk_actual)
    topk_idx = filtered_idx[topk_relative_idx]
    
    top_boxes = raw_boxes_xywh[topk_idx].cpu().numpy()
    top_scores = raw_class_scores[topk_idx].cpu().numpy()
    
    # 2. Map boxes back to original image coordinates
    from ultralytics.utils.ops import xywh2xyxy, xyxy2xywh, scale_boxes
    top_boxes_xyxy = xywh2xyxy(top_boxes)
    orig_boxes_xyxy = scale_boxes(img640.shape[:2], top_boxes_xyxy, frame.shape[:2])
    orig_boxes_xywh = xyxy2xywh(orig_boxes_xyxy)
    
    # 3. Compute vector per anchor
    raw_rows = []
    for i in range(topk_actual):
        mag, ang = get_vector_from_scores(top_scores[i], names)
        row = [float(mag), float(ang)] + orig_boxes_xywh[i].tolist()
        raw_rows.append(row)
        
    col_names = ["vector_magnitude", "estimated_angle", "x_center", "y_center", "width", "height"]
    raw_df = pd.DataFrame(raw_rows, columns=col_names)
    
    # 4. Group anchors (IoU Greedy)
    groups = group_anchors(raw_df, iou_thres=args.iou)
    
    # 5. Compute vector for each group
    summary_df = pd.DataFrame()
    if groups:
        summary_df = compute_group_vectors(groups)
        if not summary_df.empty:
            summary_df = summary_df[summary_df["vector_magnitude"] >= args.min_mag]
        
    t1 = time.time()
    calc_time_ms = (t1 - t0) * 1000
    
    # In ra terminal
    print(f"\n--- Frame {frame_id} | Time: {timestamp} | Calc Time: {calc_time_ms:.1f}ms ---")
    
    colors = [(0,255,0),(255,80,0),(0,80,255),(0,220,220),(220,0,220),(220,220,0),(128,255,0),(0,128,255)]
    
    if not summary_df.empty:
        for _, row in summary_df.iterrows():
            gid = int(row["group_id"])
            n_anch = int(row["number_of_anchors"])
            mag = float(row["vector_magnitude"])
            ang = float(row["angle"])
            xc, yc, bw, bh = row["x_center"], row["y_center"], row["width"], row["height"]
            
            print(f" Group {gid:>2} | Anchors: {n_anch:>2} | Mag: {mag:>6.2f} | Angle: {ang:>7.2f}°")
            
            if csv_writer:
                csv_writer.writerow([timestamp, frame_id, gid, n_anch, f"{mag:.2f}", f"{xc:.1f}", f"{yc:.1f}", f"{bw:.1f}", f"{bh:.1f}", f"{ang:.2f}"])
                
            # Draw bbox
            x1, y1 = int(xc - bw / 2), int(yc - bh / 2)
            x2, y2 = int(xc + bw / 2), int(yc + bh / 2)
            c = colors[(gid - 1) % len(colors)]
            cv2.rectangle(annotated, (x1, y1), (x2, y2), c, 2)
            
            label = f"Leanbot {gid} {ang:.1f}deg m={mag:.2f}"
            font, scale, thick = cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1
            (tw, th), _ = cv2.getTextSize(label, font, scale, thick)
            lx = max(0, x1)
            ly = max(th + 4, y1 - 4)
            cv2.rectangle(annotated, (lx, ly - th - 4), (lx + tw + 4, ly), c, -1)
            cv2.putText(annotated, label, (lx + 2, ly - 2), font, scale, (0, 0, 0), thick, cv2.LINE_AA)
    else:
        print(" No objects detected.")
        
    return annotated

def main():
    parser = argparse.ArgumentParser(description="Webcam real-time vector inference")
    parser.add_argument("--model", default=None, help="Path to .pt model")
    parser.add_argument("--source", default="0", help="Camera source (0 for default webcam)")
    parser.add_argument("--topk", type=int, default=100, help="Top-K anchors (default 100)")
    parser.add_argument("--iou", type=float, default=IOU_THRES, help="IoU threshold for grouping")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold to filter anchors")
    parser.add_argument("--min-mag", type=float, default=2.0, help="Minimum vector magnitude to keep a group")
    parser.add_argument("--mirror", action="store_true", help="Flip image horizontally")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    args = parser.parse_args()
    
    try:
        from ultralytics import YOLO
    except ImportError:
        sys.exit("Chua cai ultralytics. pip install ultralytics")
        
    model_path = Path(args.model) if args.model else find_default_model()
    if model_path is None or not model_path.exists():
        sys.exit("Khong tim thay model .pt")
        
    print(f"Dang dung model: {model_path}")
    model = YOLO(str(model_path))
    
    source = int(args.source) if args.source.isdigit() else args.source
    cap = cv2.VideoCapture(source)
    if isinstance(source, int):
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
        
    if not cap.isOpened():
        sys.exit(f"Khong the mo camera source {source}")

    # Setup CSV
    run_dir = DEFAULT_MODEL_DIR.parent / "runs"
    run_dir.mkdir(exist_ok=True)
    
    print("Nhan 'q' de thoat.")
    print("Nhan 'r' hoac 'R' de BAT / TAT luu log (Record).")
    
    is_recording = False
    f_csv = None
    writer = None
    
    frame_id = 0
    fps_time = time.time()
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Khong doc duoc frame tu camera. Thoat...")
                break
                
            frame_id += 1
            current_timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            
            # Tính toán và chú thích
            annotated = run_realtime_inference(model, frame, args, writer, frame_id, current_timestamp)
            
            # Tính FPS toàn trình (bao gồm cả inference, pandas, cv2 drawing)
            t_end = time.time()
            fps = 1.0 / (t_end - fps_time + 1e-9)
            fps_time = t_end
            cv2.putText(annotated, f"FPS: {fps:.1f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            if is_recording:
                cv2.putText(annotated, "REC", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            
            cv2.imshow("Real-time Vector Infer", annotated)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key in [ord('r'), ord('R')]:
                if not is_recording:
                    # Bắt đầu record
                    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                    csv_path = run_dir / f"webcam_vector_log_{timestamp_str}.csv"
                    img_path = run_dir / f"webcam_vector_log_{timestamp_str}.jpg"
                    cv2.imwrite(str(img_path), annotated) # Lưu ảnh mẫu đầu tiên
                    f_csv = open(csv_path, mode="w", newline="", encoding="utf-8")
                    writer = csv.writer(f_csv)
                    writer.writerow(["timestamp", "frame_id", "group_id", "num_anchors", "magnitude", "x_center", "y_center", "width", "height", "angle"])
                    is_recording = True
                    print(f"\n[RECORDING START] Dang luu log vao: {csv_path}")
                    print(f"[CAPTURE] Da luu anh mau vao: {img_path}")
                else:
                    # Dừng record
                    is_recording = False
                    if f_csv is not None:
                        f_csv.close()
                        f_csv = None
                        writer = None
                    print("\n[RECORDING STOP] Da dung luu log.")
    finally:
        if f_csv is not None:
            f_csv.close()
        cap.release()
        cv2.destroyAllWindows()
        print("Da dong camera.")

if __name__ == "__main__":
    main()
