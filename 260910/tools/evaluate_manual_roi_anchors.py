import argparse
import colorsys
from pathlib import Path

import cv2
import numpy as np
import openvino as ov
import pandas as pd
from ultralytics import YOLO

import check_confidence
import roi_tracking_baseline_infer as pipeline


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIR = ROOT_DIR / "benchmark" / "manual_captures"
DEFAULT_OUTPUT_DIR = ROOT_DIR / "benchmark" / "manual_captures_anchor_analysis"
DEFAULT_FULL_MODEL = ROOT_DIR / "models" / "YOLO11n_versions" / "FP16_NO_NMS" / "best_640_openvino_model"
DEFAULT_TRACKING_MODEL = ROOT_DIR / "models" / "YOLO11n_versions" / "FP16_NO_NMS" / "best_160_openvino_model"


def resolve_path(value):
    path = Path(value)
    return path if path.is_absolute() else ROOT_DIR / path


def compile_model(core, model_dir, device):
    xml_files = sorted(model_dir.glob("*.xml"))
    if not xml_files:
        raise FileNotFoundError(f"No XML model in: {model_dir}")
    return core.compile_model(str(xml_files[0]), device)


def prepare_full_input(image):
    image_height, image_width = image.shape[:2]
    crop_width = int(image_width * 0.625)
    start_x = (image_width - crop_width) // 2
    cropped = image[:, start_x:start_x + crop_width]
    square_size = max(crop_width, image_height)
    padded = np.zeros((square_size, square_size, 3), dtype=np.uint8)
    pad_top = (square_size - image_height) // 2
    pad_left = (square_size - crop_width) // 2
    padded[pad_top:pad_top + image_height, pad_left:pad_left + crop_width] = cropped
    params = {
        "start_x": start_x,
        "pad_top": pad_top,
        "pad_left": pad_left,
        "crop_w": crop_width,
        "scale": 640.0 / square_size,
    }
    return cv2.resize(padded, (640, 640)), params


def class_items(names):
    if isinstance(names, dict):
        return [(int(class_id), names[class_id]) for class_id in sorted(names)]
    return list(enumerate(names))


def anchor_color(rank, count):
    hue = 0.0 if count <= 1 else (rank - 1) / count
    red, green, blue = colorsys.hsv_to_rgb(hue, 0.9, 1.0)
    return int(blue * 255), int(green * 255), int(red * 255)


def extract_roi_anchors(model, image, names, topk, conf, iou):
    prediction = pipeline.infer_openvino_raw(model, image)
    if prediction.shape[1] <= 6:
        raise ValueError(f"ROI model is not raw no-NMS: {prediction.shape}")
    items = class_items(names)
    boxes = prediction[:, :4]
    scores = prediction[:, 4:4 + len(items)]
    best_scores = scores.max(axis=1)
    filtered = np.where(best_scores > conf)[0]
    if len(filtered) == 0:
        return pd.DataFrame(), pd.DataFrame()
    actual_topk = min(topk, len(filtered))
    order = np.argsort(best_scores[filtered])[-actual_topk:][::-1]
    top_indices = filtered[order]
    rows = []
    for rank, anchor_index in enumerate(top_indices, start=1):
        class_scores = scores[anchor_index]
        best_class_id = int(np.argmax(class_scores))
        magnitude, angle = pipeline.get_vector_from_scores(class_scores, names)
        x_center, y_center, width, height = boxes[anchor_index]
        color_b, color_g, color_r = anchor_color(rank, actual_topk)
        row = {
            "anchor_rank": rank,
            "anchor_index": int(anchor_index),
            "best_class_id": best_class_id,
            "best_class": names[best_class_id],
            "best_conf": float(best_scores[anchor_index]),
            "vector_magnitude": float(magnitude),
            "estimated_angle": float(angle),
            "vector_x": float(magnitude * np.cos(np.radians(angle))),
            "vector_y": float(magnitude * np.sin(np.radians(angle))),
            "x_center": float(x_center),
            "y_center": float(y_center),
            "width": float(width),
            "height": float(height),
            "color_b": color_b,
            "color_g": color_g,
            "color_r": color_r,
            "color_hex": f"#{color_r:02X}{color_g:02X}{color_b:02X}",
        }
        for class_id, class_name in items:
            row[f"score_{class_name}"] = float(class_scores[class_id])
        rows.append(row)
    anchors = pd.DataFrame(rows)
    groups = pipeline.group_anchors(anchors.copy(), iou_thres=iou)
    grouped = pd.concat(groups, ignore_index=True)
    group_map = grouped.set_index("anchor_index")["group_id"].to_dict()
    group_ids = anchors["anchor_index"].map(group_map).astype("Int64")
    anchors.insert(2, "group_id", group_ids)
    summary = pipeline.compute_group_vectors(groups).rename(columns={
        "number_of_anchors": "group_anchor_count",
        "vector_magnitude": "group_vector_magnitude",
        "angle": "group_estimated_angle",
        "x_center": "group_x_center_160",
        "y_center": "group_y_center_160",
        "width": "group_width_160",
        "height": "group_height_160",
    })
    return anchors, summary


def add_coordinates(anchors, roi, full_bbox, summary):
    roi_x, roi_y, roi_width, roi_height = roi
    scale_x = roi_width / 160.0
    scale_y = roi_height / 160.0
    result = anchors.rename(columns={
        "x_center": "x_center_160",
        "y_center": "y_center_160",
        "width": "width_160",
        "height": "height_160",
    }).copy()
    result["roi_x"] = roi_x
    result["roi_y"] = roi_y
    result["roi_width"] = roi_width
    result["roi_height"] = roi_height
    result["full_bbox_x1"] = float(full_bbox[0])
    result["full_bbox_y1"] = float(full_bbox[1])
    result["full_bbox_x2"] = float(full_bbox[2])
    result["full_bbox_y2"] = float(full_bbox[3])
    result["x1_160"] = result["x_center_160"] - result["width_160"] / 2
    result["y1_160"] = result["y_center_160"] - result["height_160"] / 2
    result["x2_160"] = result["x_center_160"] + result["width_160"] / 2
    result["y2_160"] = result["y_center_160"] + result["height_160"] / 2
    result["x_center_roi"] = result["x_center_160"] * scale_x
    result["y_center_roi"] = result["y_center_160"] * scale_y
    result["width_roi"] = result["width_160"] * scale_x
    result["height_roi"] = result["height_160"] * scale_y
    result["x1_origin"] = roi_x + result["x1_160"] * scale_x
    result["y1_origin"] = roi_y + result["y1_160"] * scale_y
    result["x2_origin"] = roi_x + result["x2_160"] * scale_x
    result["y2_origin"] = roi_y + result["y2_160"] * scale_y
    result["x_center_origin"] = roi_x + result["x_center_roi"]
    result["y_center_origin"] = roi_y + result["y_center_roi"]
    result["width_origin"] = result["width_roi"]
    result["height_origin"] = result["height_roi"]
    return result.merge(summary, on="group_id", how="left")


def draw_image(image, anchors, roi, full_bbox):
    output = image.copy()
    image_height, image_width = output.shape[:2]
    full_x1, full_y1, full_x2, full_y2 = np.rint(full_bbox).astype(int)
    cv2.rectangle(output, (full_x1, full_y1), (full_x2, full_y2), (0, 255, 0), 3)
    cv2.putText(output, "FULL BEST", (full_x1, max(18, full_y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2, cv2.LINE_AA)
    roi_x, roi_y, roi_width, roi_height = roi
    cv2.rectangle(output, (roi_x, roi_y),
                  (roi_x + roi_width, roi_y + roi_height), (0, 255, 255), 3)
    cv2.putText(output, "ROI 160", (roi_x, max(18, roi_y - 8)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2, cv2.LINE_AA)
    for row in anchors.sort_values("anchor_rank", ascending=False).itertuples(index=False):
        x1 = int(np.clip(round(row.x1_origin), 0, image_width - 1))
        y1 = int(np.clip(round(row.y1_origin), 0, image_height - 1))
        x2 = int(np.clip(round(row.x2_origin), 0, image_width - 1))
        y2 = int(np.clip(round(row.y2_origin), 0, image_height - 1))
        color = int(row.color_b), int(row.color_g), int(row.color_r)
        cv2.rectangle(output, (x1, y1), (x2, y2), color, 2)
        cv2.putText(output, f"A{int(row.anchor_rank):03d}",
                    (x1, max(12, y1 - 3)), cv2.FONT_HERSHEY_SIMPLEX,
                    0.35, color, 1, cv2.LINE_AA)
    return output


def process_image(image_path, full_model, tracking_model, names, args):
    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"Cannot read image: {image_path}")
    full_input, params = prepare_full_input(image)
    full_box, full_conf, full_angle, full_magnitude, _, _ = (
        pipeline.select_best_vector_detection(
            full_model,
            full_input,
            names,
            conf_thres=args.conf,
            topk=args.topk,
            iou_thres=args.iou,
            mag_threshold=args.mag_threshold,
        )
    )
    if full_magnitude <= 0:
        raise RuntimeError("FULL 640 produced no valid grouped detection")
    full_bbox = check_confidence.restore_boxes_from_training_style(
        full_box.reshape(1, 4), params
    )[0]
    image_height, image_width = image.shape[:2]
    roi = pipeline.calculate_roi(full_bbox, image_width, image_height)
    roi_x, roi_y, roi_width, roi_height = roi
    roi_crop = image[roi_y:roi_y + roi_height, roi_x:roi_x + roi_width]
    roi_input = cv2.resize(roi_crop, (160, 160))
    anchors, summary = extract_roi_anchors(
        tracking_model, roi_input, names, args.topk, args.roi_conf, args.iou
    )
    if anchors.empty:
        raise RuntimeError("ROI 160 produced no anchor after filtering")
    anchors = add_coordinates(anchors, roi, full_bbox, summary)
    anchors["full_best_conf"] = float(full_conf)
    anchors["full_group_angle"] = float(full_angle)
    anchors["full_group_vector_magnitude"] = float(full_magnitude)
    return anchors, draw_image(image, anchors, roi, full_bbox)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run FULL 640, static ROI 160, export Top-K ROI anchors."
    )
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--pattern", default="*_orig.png")
    parser.add_argument("--full-model", default=str(DEFAULT_FULL_MODEL))
    parser.add_argument("--tracking-model", default=str(DEFAULT_TRACKING_MODEL))
    parser.add_argument("--topk", type=int, default=100)
    parser.add_argument("--conf", type=float, default=0.0)
    parser.add_argument("--roi-conf", type=float, default=0.0)
    parser.add_argument("--iou", type=float, default=pipeline.IOU_THRES)
    parser.add_argument("--mag-threshold", type=float, default=0.0)
    parser.add_argument("--device", default="AUTO")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.topk <= 0:
        raise ValueError("--topk must be greater than zero")
    input_dir = resolve_path(args.input_dir)
    output_dir = resolve_path(args.output_dir)
    full_model_dir = resolve_path(args.full_model)
    tracking_model_dir = resolve_path(args.tracking_model)
    image_paths = sorted(input_dir.glob(args.pattern))
    if not image_paths:
        raise FileNotFoundError(
            f"No images matching '{args.pattern}' in: {input_dir}"
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    full_yolo = YOLO(str(full_model_dir), task="detect")
    tracking_yolo = YOLO(str(tracking_model_dir), task="detect")
    names = full_yolo.names
    if tracking_yolo.names != names:
        raise ValueError("FULL and ROI models have different class names")
    core = ov.Core()
    full_model = compile_model(core, full_model_dir, args.device)
    tracking_model = compile_model(core, tracking_model_dir, args.device)
    for image_number, image_path in enumerate(image_paths, start=1):
        print(f"[INFO] [{image_number}/{len(image_paths)}] {image_path.name}")
        anchors, annotated = process_image(
            image_path, full_model, tracking_model, names, args
        )
        image_name = (
            f"{image_path.stem}_roi160_top{len(anchors)}_anchors.png"
        )
        output_image = output_dir / image_name
        if not cv2.imwrite(str(output_image), annotated):
            raise OSError(f"Cannot write image: {output_image}")
        csv_name = f"{image_path.stem}_roi160_top{len(anchors)}_anchors.csv"
        csv_path = output_dir / csv_name
        anchors.to_csv(
            csv_path,
            index=False,
            encoding="utf-8",
            float_format="%.6f",
        )
        print(
            f"[INFO] Saved {len(anchors)} anchors: "
            f"{output_image.name} | {csv_path.name}"
        )
    print(
        f"[INFO] Images: {len(image_paths)} | "
        f"CSV files: {len(image_paths)} | Rows per CSV: {args.topk}"
    )


if __name__ == "__main__":
    main()
