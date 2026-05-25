import torch
import cv2
import numpy as np
# import pandas removed
import glob
import os
import sys

from ultralytics import YOLO
from ultralytics.data.augment import LetterBox

try:
    from ultralytics.utils.nms import non_max_suppression
except ImportError:
    from ultralytics.utils.ops import non_max_suppression

from ultralytics.utils.ops import scale_boxes, xywh2xyxy

# =====================
# Config & Environment (Moved to main/args if needed)
# =====================
# CSV functionality removed
def cv2_imshow(img): pass # Prevent UI blocking locally

IMG_SIZE = 640
CONF_THRES = 0.05
IOU_THRES = 0.7
MAX_DET = 300
CLASS_DRAW_THRES = 0.05
DRAW_MAIN_NMS_BBOX = False

device = "cuda" if torch.cuda.is_available() else "cpu"

CLASS_COLOR_PALETTE = [
    (0, 255, 0), (255, 0, 0), (0, 0, 255), (0, 255, 255), (255, 0, 255), (255, 255, 0),
    (128, 128, 0), (0, 128, 128) # Added 2 more for 8 classes
]
CLASS_LABEL_TEXT_COLOR = (0, 0, 0)

# =====================
# Helper Functions
# =====================
def preprocess_image(img_bgr, imgsz=640):
    img = LetterBox(new_shape=(imgsz, imgsz), auto=False, stride=32)(image=img_bgr)
    img = img[:, :, ::-1].transpose(2, 0, 1)  # BGR -> RGB, HWC -> CHW
    img_tensor = torch.from_numpy(np.ascontiguousarray(img)).to(device).float() / 255.0
    return img_tensor.unsqueeze(0)

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

def normalize_raw_pred_shape(raw_pred, nc):
    raw_pred = raw_pred[0] if isinstance(raw_pred, (tuple, list)) else raw_pred
    if raw_pred.shape[1] == 4 + nc: return raw_pred
    if raw_pred.shape[2] == 4 + nc: return raw_pred.permute(0, 2, 1)
    raise ValueError(f"Unexpected shape: {raw_pred.shape}")

def run_nms(raw_pred, nc):
    try:
        out = non_max_suppression(raw_pred.clone(), conf_thres=CONF_THRES, iou_thres=IOU_THRES, max_det=MAX_DET, nc=nc, return_idxs=True)
        if isinstance(out, tuple) and len(out) == 2:
            return out[0][0], out[1][0]
        return out[0], None
    except TypeError:
        out = non_max_suppression(raw_pred.clone(), conf_thres=CONF_THRES, iou_thres=IOU_THRES, max_det=MAX_DET, nc=nc)
        return out[0][0] if isinstance(out, tuple) else out[0], None

def draw_label(img, text, x, y, bg_color):
    font, scale, thick, pad = cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1, 4
    (tw, th), _ = cv2.getTextSize(text, font, scale, thick)
    img_h, img_w = img.shape[:2]
    x = int(max(0, min(x, img_w - tw - pad * 2 - 1)))
    y = int(max(th + pad * 2, min(y, img_h - 1)))
    cv2.rectangle(img, (x, y - th - pad * 2), (x + tw + pad * 2, y), bg_color, -1)
    cv2.putText(img, text, (x + pad, y - pad), font, scale, CLASS_LABEL_TEXT_COLOR, thick, cv2.LINE_AA)

def draw_bboxes(img, x1, y1, x2, y2, class_scores, obj_id, names):
    img_h, img_w = img.shape[:2]
    for cls_id, score in enumerate(map(float, class_scores)):
        if score < CLASS_DRAW_THRES: continue
        color = CLASS_COLOR_PALETTE[cls_id % len(CLASS_COLOR_PALETTE)]
        offset = 0 # cls_id * 6 (Removed offset to let bboxes overlap)
        xc1, yc1 = max(0, int(x1) + offset), max(0, int(y1) + offset)
        xc2, yc2 = min(img_w - 1, int(x2) - offset), min(img_h - 1, int(y2) - offset)
        
        if xc2 > xc1 + 5 and yc2 > yc1 + 5:
            cv2.rectangle(img, (xc1, yc1), (xc2, yc2), color, 2)
            label_y = yc1 - 6 - cls_id * 20
            label_y = min(img_h - 1, yc1 + 20 + cls_id * 20) if label_y < 20 else label_y
            draw_label(img, f"Obj{obj_id} {names[cls_id]}: {score:.3f}", xc1, label_y, color)

import argparse

# =====================
# Main Execution
# =====================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="degree_45_test", help="Input directory")
    parser.add_argument("--output", default="yolo_class_bbox_results", help="Output directory")
    args = parser.parse_args()

    # Get the directory of the current script
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    # Get the root directory (parent of tools/)
    ROOT_DIR = os.path.dirname(SCRIPT_DIR)

    model_path = os.path.join(SCRIPT_DIR, 'best.pt')
    
    # Resolve input dir
    if os.path.isabs(args.input):
        test_image_dir = args.input
    else:
        test_image_dir = os.path.join(ROOT_DIR, args.input)
        
    # Resolve output dir
    if os.path.isabs(args.output):
        OUTPUT_DIR = args.output
    else:
        OUTPUT_DIR = os.path.join(ROOT_DIR, args.output)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    model = YOLO(model_path).to(device)
    model.model.eval()
    names, nc = model.names, len(model.names)

    print(f"Device: {device} | Classes: {names}")
    
    exts = ("*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG")
    image_paths = sorted([p for ext in exts for p in glob.glob(os.path.join(test_image_dir, "**", ext), recursive=True)])
    
    if not image_paths:
        print(f"Không tìm thấy ảnh nào trong {test_image_dir}.")
        return

    # CSV rows initialization removed

    for img_path in image_paths:
        img_name = os.path.basename(img_path)
        img0 = cv2.imread(img_path)
        if img0 is None: continue
        
        print(f"\n{'='*80}\nIMAGE: {img_path}\n{'='*80}")

        rel_dir = os.path.dirname(os.path.relpath(img_path, test_image_dir))
        out_subdir = os.path.join(OUTPUT_DIR, rel_dir)
        os.makedirs(out_subdir, exist_ok=True)

        img_tensor = preprocess_image(img0, IMG_SIZE)
        with torch.no_grad():
            raw_pred = normalize_raw_pred_shape(model.model(img_tensor), nc)

        raw_boxes_xywh = raw_pred[0, :4, :].T
        raw_class_scores = raw_pred[0, 4:4 + nc, :].T
        detections, kept_idxs = run_nms(raw_pred, nc)

        debug_lines = [f"Image: {img_name}", f"Path: {img_path}", f"Relative dir: {rel_dir}", "-" * 60]
        
        if detections is None or len(detections) == 0:
            print("Không phát hiện object nào.")
            debug_lines.append("Không phát hiện object nào.")
        else:
            print(f"Number of detections after NMS: {len(detections)}")
            detections_scaled = detections.clone()
            detections_scaled[:, :4] = scale_boxes(img_tensor.shape[2:], detections_scaled[:, :4], img0.shape).round()
            
            raw_boxes_xyxy_scaled = scale_boxes(img_tensor.shape[2:], xywh2xyxy(raw_boxes_xywh.clone()), img0.shape).cpu().numpy()

            for obj_id, det in enumerate(detections_scaled):
                x1, y1, x2, y2, best_conf, best_cls = map(float, det.cpu().numpy())
                best_cls = int(best_cls)

                if kept_idxs is not None:
                    raw_idx, match_method, match_iou = int(kept_idxs[obj_id]), "return_idxs", None
                else:
                    ious = box_iou_numpy(np.array([x1, y1, x2, y2]), raw_boxes_xyxy_scaled)
                    raw_idx, match_method, match_iou = int(np.argmax(ious)), "iou_fallback", float(np.max(ious))

                class_scores = raw_class_scores[raw_idx].cpu().numpy()

                # base_info and row_wide removed

                debug_lines.extend([
                    f"\nObject {obj_id} | Best: {names[best_cls]} (Conf: {best_conf:.4f})",
                    f"Bbox (xyxy): ({x1:.1f}, {y1:.1f}, {x2:.1f}, {y2:.1f}) | Match: {match_method}"
                ])
                if match_iou is not None: debug_lines.append(f"Fallback IoU: {match_iou:.4f}")

                for cls_id, score in enumerate(map(float, class_scores)):
                    debug_lines.append(f"  {cls_id} - {names[cls_id]}: {score:.4f} {'<-- BEST' if cls_id == best_cls else ''}")
                
                if DRAW_MAIN_NMS_BBOX:
                    cv2.rectangle(img0, (int(x1), int(y1)), (int(x2), int(y2)), (255, 255, 255), 3)
                
                draw_bboxes(img0, x1, y1, x2, y2, class_scores, obj_id, names)

        cv2.imwrite(os.path.join(out_subdir, f"debug_{img_name}"), img0)
        with open(os.path.join(out_subdir, f"{os.path.splitext(img_name)[0]}_debug.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(debug_lines))

        cv2_imshow(img0)

    print(f"\nĐã lưu ảnh debug và text log vào folder:\n- {OUTPUT_DIR}")

if __name__ == "__main__":
    main()