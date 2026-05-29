import os
import glob
import pandas as pd
import numpy as np
import argparse
import sys

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

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

def process_csv(csv_path, iou_thres=0.5):
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
    
    # Tìm max_confidence và class dự đoán tốt nhất cho mỗi anchor
    class_probs = df[class_cols].values
    max_conf = np.max(class_probs, axis=1)
    best_class_idx = np.argmax(class_probs, axis=1)
    best_class = class_cols[best_class_idx]
    
    df['max_conf'] = max_conf
    df['best_class'] = best_class
    
    # Sắp xếp danh sách giảm dần theo max_conf
    df = df.sort_values(by='max_conf', ascending=False).reset_index(drop=True)
    
    groups = []
    remaining_indices = list(range(len(df)))
    boxes = df[['x1', 'y1', 'x2', 'y2']].values
    
    group_id = 1
    while remaining_indices:
        # Trong số các hộp còn lại, tìm hộp có max_conf cao nhất
        best_idx = remaining_indices[0]
        for idx in remaining_indices:
            if df.loc[idx, 'max_conf'] > df.loc[best_idx, 'max_conf']:
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
                
        # Sắp xếp các hộp TRONG CÙNG NHÓM theo confidence từ cao xuống thấp
        current_group_indices = sorted(current_group_indices, key=lambda i: df.loc[i, 'max_conf'], reverse=True)
        
        group_data = df.iloc[current_group_indices].copy()
        group_data['group_id'] = group_id
        groups.append(group_data)
        
        group_id += 1
        remaining_indices = next_remaining # Các hộp chưa được gom sẽ vào vòng lặp sau
        
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
        # Chỉ lưu lại những cột quan trọng
        class_cols_to_save = [c for c in final_df.columns if c.startswith("Leanbot_")]
        cols_to_save = ['group_id', 'best_class', 'max_conf', 'x_center', 'y_center', 'width', 'height'] + class_cols_to_save
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
                f.write(f"  [Top 1] Anchor trung tâm: {center_row['best_class']} (Conf: {center_row['max_conf']:.2f})\n")
                
                if len(group_df) > 1:
                    f.write(f"  [Phụ] Các anchor khác trong cùng nhóm:\n")
                    for _, row in group_df.iloc[1:].iterrows():
                        f.write(f"      - {row['best_class']} (Conf: {row['max_conf']:.2f})\n")
                f.write("\n")
                
        print(f"[+] Đã xử lý xong: {os.path.basename(csv_path)} -> Tạo được {len(groups)} nhóm vật thể.")
        print(f"    - Báo cáo text: {os.path.basename(output_txt_path)}")
        print(f"    - File CSV mới: {os.path.basename(output_csv_path)}")

if __name__ == "__main__":
    main()
