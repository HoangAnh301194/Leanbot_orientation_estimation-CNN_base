import argparse
import pandas as pd
import math
import os

def evaluate_group_vectors(csv_path):
    print(f"[INFO] Reading Grouped CSV: {csv_path}")
    df = pd.read_csv(csv_path)

    if 'group_id' not in df.columns:
        print("[ERROR] CSV file does not contain 'group_id' column.")
        return

    # Chuẩn bị dữ liệu báo cáo
    report_rows = []
    
    # Gom nhóm theo group_id
    grouped = df.groupby('group_id')
    
    for group_id, group_df in grouped:
        sum_x = 0.0
        sum_y = 0.0
        
        # Tìm Best Anchor (Dựa trên Độ lớn Vector cao nhất)
        # Bảng group đã được sort giảm dần trong tool group_anchors, nhưng ta cứ check lại cho chắc chắn.
        best_anchor_row = group_df.loc[group_df['vector_magnitude'].idxmax()]
        best_anchor_angle = best_anchor_row['estimated_angle']
        best_anchor_mag = best_anchor_row['vector_magnitude']
        
        anchor_count = len(group_df)
        
        # Lặp qua tất cả anchor trong group để giải mã Vector và cộng dồn
        for _, row in group_df.iterrows():
            mag = row['vector_magnitude']
            ang_deg = row['estimated_angle']
            
            ang_rad = math.radians(ang_deg)
            sum_x += mag * math.cos(ang_rad)
            sum_y += mag * math.sin(ang_rad)
            
        # Tính toán "Siêu Vector" của Group
        group_mag = math.hypot(sum_x, sum_y)
        group_ang = math.degrees(math.atan2(sum_y, sum_x))
        avg_mag = group_mag / anchor_count
        
        report_rows.append({
            'Group ID': int(group_id),
            'Số lượng Anchor': anchor_count,
            'Group Angle': f"{group_ang:.2f}°",
            'Group Magnitude': f"{group_mag:.2f}",
            'Average Magnitude': f"{avg_mag:.2f}",
            'Best Anchor Angle': f"{best_anchor_angle:.2f}°",
            'Best Anchor Mag': f"{best_anchor_mag:.2f}"
        })

    # Tạo nội dung Markdown
    md_lines = []
    md_lines.append(f"# Báo Cáo Đánh Giá Vector Tổng (Group)")
    md_lines.append(f"- **File nguồn:** `{csv_path}`")
    md_lines.append(f"- **Tổng số Group:** {len(grouped)}")
    md_lines.append("")
    md_lines.append("> **Lưu ý:** Độ lớn Vector Tổng (Group Magnitude) thường lớn hơn 1.0 vì đây là tổng đại số cộng dồn sức mạnh của tất cả các anchors chồng lặp. Khi nhiều anchors cùng dự đoán về một hướng, vector tổng sẽ kéo dài ra, thể hiện sức mạnh đồng thuận của tập thể. Cột **Độ lớn Trung Bình** được bổ sung để đưa giá trị về thang đo dưới 1.0 như thông thường.")
    md_lines.append("")
    
    md_lines.append("| Group ID | Số Anchor | Góc Tổng (Group) | Độ lớn Vector Tổng | Độ lớn Trung Bình | Góc Anchor Tốt Nhất | Độ lớn Anchor Tốt Nhất |")
    md_lines.append("|:---:|:---:|:---:|:---:|:---:|:---:|:---:|")
    
    for row in report_rows:
        md_lines.append(f"| {row['Group ID']} | {row['Số lượng Anchor']} | **`{row['Group Angle']}`** | **{row['Group Magnitude']}** | {row['Average Magnitude']} | `{row['Best Anchor Angle']}` | {row['Best Anchor Mag']} |")
        
    md_content = "\n".join(md_lines)
    
    # Tạo đường dẫn output
    csv_dir = os.path.dirname(csv_path)
    csv_basename = os.path.basename(csv_path)
    name_without_ext = os.path.splitext(csv_basename)[0]
    out_md_path = os.path.join(csv_dir, f"{name_without_ext}_evaluation.md")
    
    with open(out_md_path, 'w', encoding='utf-8') as f:
        f.write(md_content)
        
    print(f"[DONE] Successfully evaluated {len(grouped)} groups.")
    print(f"[DONE] Saved Markdown report to: {out_md_path}")
    
    # Bỏ qua in ra màn hình vì có thể gây lỗi Unicode trên Windows
    pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Evaluate Grouped Vectors to calculate Group Super-Vector")
    parser.add_argument('--csv', type=str, required=True, help="Path to the grouped CSV file")
    
    args = parser.parse_args()
    evaluate_group_vectors(args.csv)
