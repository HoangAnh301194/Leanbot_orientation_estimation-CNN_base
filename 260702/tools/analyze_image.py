"""
analyze_image.py — Pipeline nhận diện góc Leanbot (chạy một lần).

Quy trình:
    Đọc ảnh → crop vuông (center crop) → resize 640×640
    → YOLOv8 inference (lấy ~200 raw anchors tốt nhất, KHÔNG qua NMS)
    → tính vector góc từ 24 class score (mỗi anchor)
    → tính vector_magnitude + estimated_angle
    → gom các anchor overlap thành group (IoU greedy)
    → tính bounding box đại diện (weighted average theo vector_magnitude)
    → tính vector tổng của từng group
    → sắp xếp group theo vector_magnitude giảm dần
    → xuất CSV / vẽ ảnh / tạo báo cáo debug / ghi log

Lệnh mẫu:
    python analyze_image.py --input 24class_test_images/002.jpg \\
                            --output runs/002 \\
                            --model tools/best_24Class_Soft_Angular_BCE.pt
"""

import argparse
import logging
import math
import os
import re
import sys
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import pandas as pd
import torch

# ── Hằng số mặc định ──────────────────────────────────────────────────────────
IMG_SIZE    = 640
TOP_K       = 200        # Số anchor lấy trước NMS
IOU_THRES   = 0.5        # Ngưỡng IoU để gom nhóm
CONF_THRES  = 0.05       # Chỉ dùng khi vẽ ảnh NMS (không ảnh hưởng raw anchors)
SCRIPT_DIR  = Path(__file__).resolve().parent

# ── Regex parse tên class → góc (độ) ─────────────────────────────────────────
ANGLE_PATTERN = re.compile(
    r"^Leanbot_(?:(?P<sign>[pm])(?P<value>\d+)|(?P<plain>\d+))$"
)

CLASS_ANGLE_MAP: dict[str, float] = {}  # Sẽ được điền sau khi load model


def parse_angle_from_class_name(class_name: str) -> Optional[float]:
    """Chuyển tên class Leanbot_p30 → +30, Leanbot_m15 → -15, Leanbot_0 → 0."""
    match = ANGLE_PATTERN.match(class_name)
    if not match:
        return None
    if match.group("plain") is not None:
        return float(match.group("plain"))
    value = float(match.group("value"))
    return value if match.group("sign") == "p" else -value


def get_vector_from_scores(
    class_scores: np.ndarray, names: dict[int, str]
) -> tuple[float, float]:
    """
    Tính vector tổng từ 24 class score theo công thức:
        Vx = Σ score_i * cos(θ_i)
        Vy = Σ score_i * sin(θ_i)
    Trả về (magnitude, angle_degrees).
    """
    sum_x = 0.0
    sum_y = 0.0
    for cls_id, score in enumerate(class_scores):
        cls_name = names[cls_id]
        angle = CLASS_ANGLE_MAP.get(cls_name)
        if angle is None:
            continue
        theta = math.radians(angle)
        sum_x += score * math.cos(theta)
        sum_y += score * math.sin(theta)
    mag = math.hypot(sum_x, sum_y)
    if mag <= 1e-9:
        return 0.0, 0.0
    return mag, math.degrees(math.atan2(sum_y, sum_x))


# ── Hàm xử lý ảnh ─────────────────────────────────────────────────────────────

def center_crop_square(img_bgr: np.ndarray) -> tuple[np.ndarray, dict]:
    """Crop vuông tại trung tâm, giữ tỉ lệ X/Y."""
    h, w = img_bgr.shape[:2]
    size   = min(h, w)
    crop_y = (h - size) // 2
    crop_x = (w - size) // 2
    cropped = img_bgr[crop_y:crop_y + size, crop_x:crop_x + size]
    return cropped, {"orig_w": w, "orig_h": h, "size": size, "crop_x": crop_x, "crop_y": crop_y}


def preprocess_image(img_bgr: np.ndarray, imgsz: int = IMG_SIZE) -> torch.Tensor:
    """BGR → RGB → CHW → Tensor (float32, normalized)."""
    try:
        from ultralytics.data.augment import LetterBox
        img = LetterBox(new_shape=(imgsz, imgsz), auto=False, stride=32)(image=img_bgr)
    except Exception:
        img = cv2.resize(img_bgr, (imgsz, imgsz))

    img = img[:, :, ::-1].transpose(2, 0, 1)
    tensor = torch.from_numpy(np.ascontiguousarray(img)).float() / 255.0
    return tensor.unsqueeze(0)


# ── IoU helper ────────────────────────────────────────────────────────────────

def box_iou_numpy(box: np.ndarray, boxes: np.ndarray) -> np.ndarray:
    if len(boxes) == 0:
        return np.array([])
    x1 = np.maximum(box[0], boxes[:, 0])
    y1 = np.maximum(box[1], boxes[:, 1])
    x2 = np.minimum(box[2], boxes[:, 2])
    y2 = np.minimum(box[3], boxes[:, 3])
    inter = np.maximum(0, x2 - x1) * np.maximum(0, y2 - y1)
    area_box   = max(0, box[2] - box[0]) * max(0, box[3] - box[1])
    area_boxes = np.maximum(0, boxes[:, 2] - boxes[:, 0]) * np.maximum(0, boxes[:, 3] - boxes[:, 1])
    return inter / (area_box + area_boxes - inter + 1e-9)


# ── Gom nhóm anchor ──────────────────────────────────────────────────────────

def compute_weighted_bbox(
    group_df: pd.DataFrame,
) -> tuple[float, float, float, float]:
    """
    Bounding box đại diện = trung bình có trọng số theo vector_magnitude.
    Fallback: trung bình cộng khi tổng trọng số ≈ 0.
    """
    w = group_df["vector_magnitude"].values
    total = w.sum()
    if total <= 1e-9:
        return (
            float(group_df["x_center"].mean()),
            float(group_df["y_center"].mean()),
            float(group_df["width"].mean()),
            float(group_df["height"].mean()),
        )
    return (
        float(np.dot(w, group_df["x_center"].values) / total),
        float(np.dot(w, group_df["y_center"].values) / total),
        float(np.dot(w, group_df["width"].values)    / total),
        float(np.dot(w, group_df["height"].values)   / total),
    )


def group_anchors(df: pd.DataFrame, iou_thres: float = IOU_THRES) -> list[pd.DataFrame]:
    """
    Gom anchor chồng lặp thành group bằng thuật toán IoU greedy.
    Seed mỗi vòng: anchor có vector_magnitude cao nhất trong danh sách còn lại.
    Ngưỡng: IoU > iou_thres → cùng group.
    """
    df = df.sort_values("vector_magnitude", ascending=False).reset_index(drop=True)
    df["x1"] = df["x_center"] - df["width"]  / 2
    df["y1"] = df["y_center"] - df["height"] / 2
    df["x2"] = df["x_center"] + df["width"]  / 2
    df["y2"] = df["y_center"] + df["height"] / 2
    boxes  = df[["x1", "y1", "x2", "y2"]].values
    remaining = list(range(len(df)))
    groups = []
    gid = 1

    while remaining:
        best = remaining[0]
        for idx in remaining:
            if df.loc[idx, "vector_magnitude"] > df.loc[best, "vector_magnitude"]:
                best = idx

        center_box = boxes[best]
        rem_boxes  = boxes[remaining]
        ious       = box_iou_numpy(center_box, rem_boxes)
        mask       = ious > iou_thres

        in_group  = [remaining[i] for i, m in enumerate(mask) if m]
        remaining = [remaining[i] for i, m in enumerate(mask) if not m]
        in_group  = sorted(in_group, key=lambda i: df.loc[i, "vector_magnitude"], reverse=True)

        gdf = df.iloc[in_group].copy()
        gdf["group_id"] = gid
        gx, gy, gw, gh = compute_weighted_bbox(gdf)
        gdf["group_x_center"] = round(gx, 2)
        gdf["group_y_center"] = round(gy, 2)
        gdf["group_width"]    = round(gw, 2)
        gdf["group_height"]   = round(gh, 2)
        groups.append(gdf)
        gid += 1

    return groups


# ── Tính vector tổng cho từng group ──────────────────────────────────────────

def compute_group_vectors(
    groups: list[pd.DataFrame], image_filename: str
) -> pd.DataFrame:
    """
    Tính vector tổng (sum of individual anchor vectors) cho mỗi group.
    Sắp xếp kết quả theo vector_magnitude giảm dần.
    """
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
        n         = len(gdf)
        avg_mag   = group_mag / n if n > 0 else 0.0

        best_row  = gdf.loc[gdf["vector_magnitude"].idxmax()]
        gx = float(best_row.get("group_x_center", best_row["x_center"]))
        gy = float(best_row.get("group_y_center", best_row["y_center"]))
        gw = float(best_row.get("group_width",    best_row["width"]))
        gh = float(best_row.get("group_height",   best_row["height"]))

        rows.append({
            "group_id":          gid,
            "number_of_anchors": n,
            "vector_magnitude":  round(group_mag, 2),
            "x_center":          round(gx, 2),
            "y_center":          round(gy, 2),
            "width":             round(gw, 2),
            "height":            round(gh, 2),
            "angle":             round(group_ang, 2),
            "image_filename":    image_filename,
            "avg_magnitude":     round(avg_mag, 2),
            "best_anchor_angle": round(float(best_row["estimated_angle"]), 2),
            "best_anchor_mag":   round(float(best_row["vector_magnitude"]), 2),
            # Các thành phần vector tổng – hữu ích khi debug
            "sum_vx":            round(sum_x, 4),
            "sum_vy":            round(sum_y, 4),
        })

    df_out = pd.DataFrame(rows)
    return df_out.sort_values("vector_magnitude", ascending=False).reset_index(drop=True)


# ── Vẽ ảnh kết quả ───────────────────────────────────────────────────────────

def draw_groups(img: np.ndarray, summary_df: pd.DataFrame) -> np.ndarray:
    """
    Vẽ bounding box đại diện, group ID, góc và magnitude lên ảnh.
    BBox được tính từ group_x/y/w/h (weighted average).
    """
    out = img.copy()
    colors = [
        (0,255,0),(255,80,0),(0,80,255),(0,220,220),
        (220,0,220),(220,220,0),(128,255,0),(0,128,255),
    ]
    for _, row in summary_df.iterrows():
        gid  = int(row["group_id"])
        xc   = float(row["x_center"])
        yc   = float(row["y_center"])
        w    = float(row["width"])
        h    = float(row["height"])
        ang  = float(row["angle"])
        mag  = float(row["vector_magnitude"])

        x1 = int(xc - w / 2); y1 = int(yc - h / 2)
        x2 = int(xc + w / 2); y2 = int(yc + h / 2)
        color = colors[(gid - 1) % len(colors)]

        cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)

        label = f"G{gid} {ang:.1f}deg m={mag:.2f}"
        font, scale, thick = cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1
        (tw, th), _ = cv2.getTextSize(label, font, scale, thick)
        lx = max(0, x1)
        ly = max(th + 4, y1 - 4)
        cv2.rectangle(out, (lx, ly - th - 4), (lx + tw + 4, ly), color, -1)
        cv2.putText(out, label, (lx + 2, ly - 2), font, scale, (0, 0, 0), thick, cv2.LINE_AA)

    return out


# ── Debug CSV cho Group 6 và Group 9 ─────────────────────────────────────────

def build_debug_csv(groups: list[pd.DataFrame], names: dict[int, str]) -> pd.DataFrame:
    """
    Tạo bảng debug chi tiết: mỗi anchor có anchor_id, confidence, vector_magnitude,
    predicted_angle, bbox, top_class, top_class_score, vector_x, vector_y.
    """
    rows = []
    for gdf in groups:
        gid = int(gdf["group_id"].iloc[0])
        # Tính vector tổng của group để tính đóng góp
        sum_x_g, sum_y_g = 0.0, 0.0
        for _, r in gdf.iterrows():
            mg = r["vector_magnitude"]
            ag = math.radians(r["estimated_angle"])
            sum_x_g += mg * math.cos(ag)
            sum_y_g += mg * math.sin(ag)
        group_mag = math.hypot(sum_x_g, sum_y_g)

        class_cols = [c for c in gdf.columns if c.startswith("Leanbot_")]

        for aid, (_, r) in enumerate(gdf.iterrows()):
            mag = float(r["vector_magnitude"])
            ang = float(r["estimated_angle"])
            ang_rad = math.radians(ang)
            vx = mag * math.cos(ang_rad)
            vy = mag * math.sin(ang_rad)

            # Top class theo score cao nhất
            if class_cols:
                scores = r[class_cols].values.astype(float)
                top_i  = int(np.argmax(scores))
                top_cls = class_cols[top_i]
                top_cls_score = float(scores[top_i])
            else:
                top_cls, top_cls_score = "", 0.0

            # Tỉ lệ đóng góp magnitude vào group
            contribution = (mag / group_mag * 100) if group_mag > 1e-9 else 0.0

            rows.append({
                "group_id":          gid,
                "anchor_id":         aid,
                "vector_magnitude":  round(mag, 4),
                "predicted_angle":   round(ang, 2),
                "x_center":          round(float(r["x_center"]), 2),
                "y_center":          round(float(r["y_center"]), 2),
                "width":             round(float(r["width"]), 2),
                "height":            round(float(r["height"]), 2),
                "top_class":         top_cls,
                "top_class_score":   round(top_cls_score, 4),
                "vector_x":          round(vx, 4),
                "vector_y":          round(vy, 4),
                "contribution_pct":  round(contribution, 2),
            })
    return pd.DataFrame(rows)


# ── Main pipeline ─────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Leanbot Angle Detection – single image pipeline")
    p.add_argument("--input",  required=True, help="Đường dẫn file ảnh JPG đầu vào")
    p.add_argument("--output", default=None,  help="Thư mục lưu kết quả (mặc định: runs/<stem>)")
    p.add_argument("--model",  default=None,  help="Đường dẫn model .pt (mặc định: tìm trong tools/)")
    p.add_argument("--iou",    type=float, default=IOU_THRES, help=f"Ngưỡng IoU grouping (mặc định {IOU_THRES})")
    p.add_argument("--topk",   type=int,   default=TOP_K,    help=f"Số anchor lấy trước NMS (mặc định {TOP_K})")
    return p.parse_args()


def find_default_model() -> Optional[Path]:
    preferred = [
        SCRIPT_DIR / "tools" / "best_24Class_Soft_Angular_BCE.pt",
        SCRIPT_DIR / "tools" / "best_24Class_Default_BCE.pt",
        SCRIPT_DIR / "tools" / "best.pt",
    ]
    for p in preferred:
        if p.exists():
            return p
    pts = sorted(SCRIPT_DIR.glob("tools/*.pt"), key=lambda f: f.stat().st_mtime, reverse=True)
    return pts[0] if pts else None


def main() -> None:
    args = parse_args()

    # Giải quyết đường dẫn – relative paths từ cwd (thư mục làm việc hiện tại)
    input_path = Path(args.input)
    if not input_path.is_absolute():
        input_path = (Path.cwd() / args.input).resolve()
    if not input_path.exists():
        sys.exit(f"[ERROR] Không tìm thấy ảnh: {input_path}")

    stem       = input_path.stem
    output_dir = Path(args.output) if args.output else root / "runs" / stem
    output_dir.mkdir(parents=True, exist_ok=True)

    # Tìm model
    model_path = Path(args.model).resolve() if args.model else find_default_model()
    if model_path is None or not model_path.exists():
        sys.exit(f"[ERROR] Không tìm thấy model .pt. Truyền --model <path>")

    # Logging
    log_path = output_dir / "analysis.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(log_path, encoding="utf-8"), logging.StreamHandler(sys.stdout)],
    )
    log = logging.getLogger(__name__)
    log.info(f"=== analyze_image.py ===")
    log.info(f"Input  : {input_path}")
    log.info(f"Output : {output_dir}")
    log.info(f"Model  : {model_path}")
    log.info(f"IoU threshold (grouping): {args.iou}")
    log.info(f"Top-K anchors           : {args.topk}")

    # ── 1. Đọc & crop ảnh ────────────────────────────────────────────────────
    img_bgr = cv2.imread(str(input_path))
    if img_bgr is None:
        sys.exit(f"[ERROR] cv2.imread thất bại: {input_path}")

    cropped, crop_info = center_crop_square(img_bgr)
    resized = cv2.resize(cropped, (IMG_SIZE, IMG_SIZE))
    cv2.imwrite(str(output_dir / "processed_640x640.jpg"), resized)
    log.info(f"Ảnh gốc: {crop_info['orig_w']}×{crop_info['orig_h']} → crop {crop_info['size']}×{crop_info['size']} → resize 640×640")

    # ── 2. Load model & inference ─────────────────────────────────────────────
    try:
        from ultralytics import YOLO
    except ImportError:
        sys.exit("[ERROR] Chưa cài ultralytics. Chạy: pip install ultralytics")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    log.info(f"Device: {device}")

    model = YOLO(str(model_path)).to(device)
    model.model.eval()
    names: dict[int, str] = model.names
    nc = len(names)

    # Điền CLASS_ANGLE_MAP
    for cid, cname in names.items():
        a = parse_angle_from_class_name(cname)
        if a is not None:
            CLASS_ANGLE_MAP[cname] = a

    log.info(f"Model: {model_path.name}  |  Classes: {nc}")
    log.info(f"Class→Angle mapping: {CLASS_ANGLE_MAP}")

    img_tensor = preprocess_image(resized, IMG_SIZE).to(device)

    with torch.no_grad():
        raw_pred = model.model(img_tensor)

    # Normalize shape: (1, 4+nc, N) hoặc (1, N, 4+nc)
    raw_pred = raw_pred[0] if isinstance(raw_pred, (tuple, list)) else raw_pred
    if raw_pred.shape[1] != 4 + nc and raw_pred.shape[2] == 4 + nc:
        raw_pred = raw_pred.permute(0, 2, 1)

    raw_boxes_xywh  = raw_pred[0, :4, :].T          # (N, 4)
    raw_class_scores = raw_pred[0, 4:4 + nc, :].T   # (N, nc)

    total_anchors = raw_class_scores.shape[0]
    log.info(f"Tổng số anchor thô: {total_anchors}")

    # ── 3. Lấy Top-K anchor ───────────────────────────────────────────────────
    max_scores, _ = raw_class_scores.max(dim=1)
    topk_actual   = min(args.topk, total_anchors)
    _, topk_idx   = torch.topk(max_scores, topk_actual)

    top_boxes  = raw_boxes_xywh[topk_idx].cpu().numpy()   # (K, 4)
    top_scores = raw_class_scores[topk_idx].cpu().numpy() # (K, nc)
    log.info(f"Top-{topk_actual} anchors được chọn")

    # ── 4. Tính vector góc cho từng anchor ────────────────────────────────────
    raw_rows = []
    for i in range(topk_actual):
        mag, ang = get_vector_from_scores(top_scores[i], names)
        row = [float(mag), float(ang)] + top_boxes[i].tolist() + top_scores[i].tolist()
        raw_rows.append(row)

    col_names = (
        ["vector_magnitude", "estimated_angle", "x_center", "y_center", "width", "height"]
        + [names[j] for j in range(nc)]
    )
    raw_df = pd.DataFrame(raw_rows, columns=col_names)
    raw_csv = output_dir / "raw_anchors.csv"
    raw_df.to_csv(raw_csv, index=False, float_format="%.4f")
    log.info(f"raw_anchors.csv đã lưu ({len(raw_df)} dòng)")

    # ── 5. Gom nhóm anchor overlap ────────────────────────────────────────────
    groups = group_anchors(raw_df.copy(), iou_thres=args.iou)
    log.info(f"Số group sau khi gom (IoU>{args.iou}): {len(groups)}")

    grouped_df = pd.concat(groups).reset_index(drop=True)
    grouped_csv = output_dir / "grouped_anchors.csv"
    grouped_df.to_csv(grouped_csv, index=False, float_format="%.4f")
    log.info(f"grouped_anchors.csv đã lưu ({len(grouped_df)} dòng)")

    # ── 6. Tính vector tổng cho từng group ────────────────────────────────────
    summary_df = compute_group_vectors(groups, image_filename=input_path.name)
    summary_csv = output_dir / "vector_summary.csv"
    summary_df.to_csv(summary_csv, index=False, float_format="%.2f")
    log.info(f"vector_summary.csv đã lưu ({len(summary_df)} nhóm)")

    # ── 7. Vẽ ảnh kết quả ────────────────────────────────────────────────────
    result_img = draw_groups(resized, summary_df)
    detected_jpg = output_dir / "detected_groups.jpg"
    cv2.imwrite(str(detected_jpg), result_img)
    log.info(f"detected_groups.jpg đã lưu")

    # ── 8. Debug CSV chi tiết ─────────────────────────────────────────────────
    debug_df = build_debug_csv(groups, names)
    debug_csv = output_dir / "debug_groups.csv"
    debug_df.to_csv(debug_csv, index=False, float_format="%.4f")
    log.info(f"debug_groups.csv đã lưu ({len(debug_df)} dòng)")

    # ── 9. In bảng tổng kết ──────────────────────────────────────────────────
    log.info("\n=== KẾT QUẢ PHÂN TÍCH ===")
    log.info(f"{'group_id':>8} {'anchors':>7} {'magnitude':>10} {'angle':>9} {'x_c':>7} {'y_c':>7} {'w':>7} {'h':>7}  image")
    log.info("-" * 80)
    for _, row in summary_df.iterrows():
        log.info(
            f"{int(row['group_id']):>8} {int(row['number_of_anchors']):>7} "
            f"{row['vector_magnitude']:>10.2f} {row['angle']:>8.2f}° "
            f"{row['x_center']:>7.1f} {row['y_center']:>7.1f} "
            f"{row['width']:>7.1f} {row['height']:>7.1f}  {row['image_filename']}"
        )
    log.info("=" * 80)
    log.info(f"\nOutput directory: {output_dir}")
    log.info("Hoàn thành.")


if __name__ == "__main__":
    main()
