import os
import torch
import pandas as pd
from ultralytics import YOLO
from ultralytics.utils.ops import scale_boxes, xywh2xyxy, xyxy2xywh
import cv2

# Import các hàm tiện ích có sẵn
from check_confidence import preprocess_image, normalize_raw_pred_shape

def export_top_anchors(img_path, output_csv, top_k=200):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    # Load model
    model = YOLO("best.pt").to(device)
    model.model.eval()
    nc = len(model.names) # 24 classes
    
    # Đọc và preprocess ảnh
    img0 = cv2.imread(img_path)
    if img0 is None:
        print(f"Lỗi: Không thể đọc ảnh {img_path}")
        return
        
    img_tensor = preprocess_image(img0, 640)
    
    # Forward pass lấy raw_pred
    with torch.no_grad():
        raw_pred = model.model(img_tensor)
        raw_pred = normalize_raw_pred_shape(raw_pred, nc)
        
    # raw_pred có shape (1, 28, 8400)
    # 28 = 4 (x_center, y_center, w, h) + 24 (class scores)
    raw_pred = raw_pred[0] # Bỏ batch dimension -> (28, 8400)
    
    raw_boxes_xywh = raw_pred[:4, :].T # (8400, 4)
    raw_class_scores = raw_pred[4:4 + nc, :].T # (8400, 24)
    
    # Tính điểm confidence cao nhất cho mỗi anchor (trong 24 class)
    max_scores, best_class_indices = torch.max(raw_class_scores, dim=1)
    
    # Sắp xếp anchors theo điểm giảm dần và lấy top_k
    sorted_indices = torch.argsort(max_scores, descending=True)
    top_indices = sorted_indices[:top_k]
    
    # Scale boxes từ hệ tọa độ 640x640 về gốc (2560x1440)
    boxes_scaled = raw_boxes_xywh[top_indices].clone()
    boxes_xyxy = xywh2xyxy(boxes_scaled)
    boxes_xyxy_scaled = scale_boxes(img_tensor.shape[2:], boxes_xyxy, img0.shape)
    boxes_xywh_scaled = xyxy2xywh(boxes_xyxy_scaled).cpu().numpy()
    
    top_scores = raw_class_scores[top_indices].cpu().numpy()
    
    # Tạo danh sách dữ liệu cho DataFrame
    rows = []
    for i in range(top_k):
        idx = top_indices[i].item()
        x_c, y_c, w, h = boxes_xywh_scaled[i]
        
        row = {
            "Anchor_Index": idx,
            "x_center": round(x_c, 2),
            "y_center": round(y_c, 2),
            "width": round(w, 2),
            "height": round(h, 2),
            "Best_Conf": round(max_scores[idx].item(), 4),
            "Best_Class": model.names[best_class_indices[idx].item()]
        }
        
        # Thêm 24 class scores
        for class_id in range(nc):
            class_name = model.names[class_id]
            row[class_name] = round(top_scores[i, class_id], 4)
            
        rows.append(row)
        
    # Lưu vào CSV
    df = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    df.to_csv(output_csv, index=False)
    print(f"Đã xuất thành công {top_k} anchors tốt nhất vào {output_csv}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--img", type=str, default="../24class_test_images/002.jpg")
    parser.add_argument("--out", type=str, default="../evaluate_crop_results/top_200_anchors.csv")
    parser.add_argument("--topk", type=int, default=200)
    args = parser.parse_args()
    
    export_top_anchors(args.img, args.out, top_k=args.topk)
