import os
import glob
import pandas as pd
import numpy as np
import argparse
import sys

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

def box_iou_numpy(box, boxes):
    """Tính IoU giữa một bounding box và một mảng các bounding box."""
    if len(boxes) == 0: return np.array([])
    x1 = np.maximum(box[0], boxes[:, 0])
    y1 = np.maximum(box[1], boxes[:, 1])
    x2 = np.minimum(box[2], boxes[:, 2])
    y2 = np.minimum(box[3], boxes[:, 3])
    inter = np.maximum(0, x2 - x1) * np.maximum(0, y2 - y1)
    area_box = max(0, box[2] - box[0]) * max(0, box[3] - box[1])
    area_boxes = np.maximum(0, boxes[:, 2] - boxes[:, 0]) * np.maximum(0, boxes[:, 3] - boxes[:, 1])
    return inter / (area_box + area_boxes - inter + 1e-9)


def compute_weighted_bbox(group_df: pd.DataFrame) -> tuple[float, float, float, float]:
    """
    Tính bounding box đại diện cho group bằng trung bình có trọng số.
    Trọng số = vector_magnitude của từng anchor.
    
    Công thức: x̄ = Σ(mᵢ * xᵢ) / Σmᵢ
    
    Trả về: (x_center, y_center, width, height)
    """
    weights = group_df['vector_magnitude'].values
    total_weight = weights.sum()

    if total_weight <= 1e-9:
        # Fallback: dùng trung bình cộng thông thường nếu tổng trọng số = 0
        return (
            float(group_df['x_center'].mean()),
            float(group_df['y_center'].mean()),
            float(group_df['width'].mean()),
            float(group_df['height'].mean()),
        )

    x_c = float(np.dot(weights, group_df['x_center'].values) / total_weight)
    y_c = float(np.dot(weights, group_df['y_center'].values) / total_weight)
    w   = float(np.dot(weights, group_df['width'].values)    / total_weight)
    h   = float(np.dot(weights, group_df['height'].values)   / total_weight)
    return x_c, y_c, w, h


def process_csv(csv_path: str, iou_thres: float = 0.5) -> list[pd.DataFrame]:
    """
    Đọc file top200.csv, gom các anchor chồng lặp thành group theo thuật toán IoU greedy.
    Sau khi gom, tính bounding box đại diện (weighted average) và lưu vào cột group_x/y/w/h.

    Ngưỡng overlap: IoU > iou_thres thì hai anchor thuộc cùng group.
    Anchor trung tâm (seed) của mỗi vòng: anchor có vector_magnitude cao nhất trong số còn lại.
    """
    df = pd.read_csv(csv_path)
    if df.empty:
        return []
    
    # Tìm các cột là class confidence (chứa chữ Leanbot_)
    class_cols = np.array([c for c in df.columns if c.startswith("Leanbot_")])
    
    # Tính x1, y1, x2, y2 để tính IoU
    df['x1'] = df['x_center'] - df['width'] / 2
    df['y1'] = df['y_center'] - df['height'] / 2
    df['x2'] = df['x_center'] + df['width'] / 2
    df['y2'] = df['y_center'] + df['height'] / 2
    
    # Sắp xếp danh sách giảm dần theo vector_magnitude
    df = df.sort_values(by='vector_magnitude', ascending=False).reset_index(drop=True)
    
    groups = []
    remaining_indices = list(range(len(df)))
    boxes = df[['x1', 'y1', 'x2', 'y2']].values
    
    group_id = 1
    while remaining_indices:
        # Trong số các hộp còn lại, tìm hộp có vector_magnitude cao nhất (luôn là phần tử đầu vì đã sort)
        best_idx = remaining_indices[0]
        for idx in remaining_indices:
            if df.loc[idx, 'vector_magnitude'] > df.loc[best_idx, 'vector_magnitude']:
                best_idx = idx
                
        center_box = boxes[best_idx]
        
        # Tính IoU của hộp tốt nhất với tất cả các hộp CÒN LẠI
        remaining_boxes = boxes[remaining_indices]
        ious = box_iou_numpy(center_box, remaining_boxes)
        
        # Tìm các hộp có độ chồng lấp (IoU) vượt ngưỡng
        overlapping_mask = ious > iou_thres
        
        current_group_indices = []
        next_remaining = []
        
        for i, idx in enumerate(remaining_indices):
            if overlapping_mask[i]:
                current_group_indices.append(idx)
            else:
                next_remaining.append(idx)
                
        # Sắp xếp các hộp TRONG CÙNG NHÓM theo vector_magnitude từ cao xuống thấp
        current_group_indices = sorted(current_group_indices, key=lambda i: df.loc[i, 'vector_magnitude'], reverse=True)
        
        group_data = df.iloc[current_group_indices].copy()
        group_data['group_id'] = group_id

        # --- TÍNH BOUNDING BOX ĐẠI DIỆN (WEIGHTED AVERAGE) ---
        gx, gy, gw, gh = compute_weighted_bbox(group_data)
        group_data['group_x_center'] = round(gx, 2)
        group_data['group_y_center'] = round(gy, 2)
        group_data['group_width']    = round(gw, 2)
        group_data['group_height']   = round(gh, 2)

        groups.append(group_data)
        
        group_id += 1
        remaining_indices = next_remaining  # Các hộp chưa được gom sẽ vào vòng lặp sau
        
    return groups

def main():
    parser = argparse.ArgumentParser(description="Tool gom nhóm các anchor dự đoán trùng lặp")
    parser.add_argument("--input", default="yolo_class_bbox_results", help="Thư mục chứa các file *_top200.csv")
    parser.add_argument("--iou", type=float, default=0.5, help="Ngưỡng IoU để gom nhóm (mặc định 0.5)")
    args = parser.parse_args()
    
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    ROOT_DIR = os.path.dirname(SCRIPT_DIR)
    
    input_dir = args.input if os.path.isabs(args.input) else os.path.join(ROOT_DIR, args.input)
    
    # Tìm tất cả file csv được tạo ra từ check_confidence
    csv_files = glob.glob(os.path.join(input_dir, "**", "*_top200.csv"), recursive=True)
    
    if not csv_files:
        print(f"Không tìm thấy file CSV nào trong {input_dir}")
        return
        
    print(f"Tìm thấy {len(csv_files)} file CSV. Đang xử lý gom nhóm với ngưỡng IoU = {args.iou}...")
    
    for csv_path in csv_files:
        groups = process_csv(csv_path, iou_thres=args.iou)
        if not groups:
            continue
            
        output_txt_path = csv_path.replace("_top200.csv", "_grouped_report.txt")
        output_csv_path = csv_path.replace("_top200.csv", "_grouped.csv")
        
        # --- LƯU RA FILE CSV MỚI ---
        final_df = pd.concat(groups)
        # Chỉ lưu lại những cột quan trọng (bao gồm các cột bbox đại diện của group)
        class_cols_to_save = [c for c in final_df.columns if c.startswith("Leanbot_")]
        cols_to_save = (
            ['group_id', 'vector_magnitude', 'estimated_angle',
             'x_center', 'y_center', 'width', 'height',
             'group_x_center', 'group_y_center', 'group_width', 'group_height']
            + class_cols_to_save
        )
        final_df[cols_to_save].to_csv(output_csv_path, index=False, float_format="%.2f")
        
        # --- LƯU BÁO CÁO DẠNG TEXT DỄ ĐỌC ---
        with open(output_txt_path, "w", encoding="utf-8") as f:
            f.write(f"BÁO CÁO GOM NHÓM ANCHOR (IoU > {args.iou})\n")
            f.write(f"File nguồn: {os.path.basename(csv_path)}\n")
            f.write("="*60 + "\n\n")
            
            for g_id, group_df in enumerate(groups, 1):
                f.write(f"--- NHÓM {g_id} (Gồm {len(group_df)} anchors chồng lặp lên nhau) ---\n")
                
                # Hộp tự tin nhất trong nhóm
                center_row = group_df.iloc[0]
                f.write(f"  [Top 1] Anchor trung tâm (Góc {center_row['estimated_angle']:.1f}° | Độ lớn: {center_row['vector_magnitude']:.2f})\n")
                
                # Bounding box đại diện
                f.write(f"  [BBox]  Weighted BBox: x={center_row['group_x_center']:.1f}, y={center_row['group_y_center']:.1f}, w={center_row['group_width']:.1f}, h={center_row['group_height']:.1f}\n")

                if len(group_df) > 1:
                    f.write(f"  [Phụ] Các anchor khác trong cùng nhóm:\n")
                    for _, row in group_df.iloc[1:].iterrows():
                        f.write(f"      - Góc {row['estimated_angle']:.1f}° (Độ lớn: {row['vector_magnitude']:.2f})\n")
                f.write("\n")
                
        print(f"[+] Đã xử lý xong: {os.path.basename(csv_path)} -> Tạo được {len(groups)} nhóm vật thể.")
        print(f"    - Báo cáo text: {os.path.basename(output_txt_path)}")
        print(f"    - File CSV mới: {os.path.basename(output_csv_path)}")

if __name__ == "__main__":
    main()
