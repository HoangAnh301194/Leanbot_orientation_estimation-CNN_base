import argparse
import pandas as pd
import math
import os


def evaluate_group_vectors(csv_path: str, image_filename: str = "") -> None:
    """
    Đọc file grouped.csv, tính vector tổng cho từng group và xuất báo cáo.

    Các bước:
    1. Tính vector tổng bằng cách cộng dồn: Vx = Σ(mᵢ * cos(θᵢ)), Vy = Σ(mᵢ * sin(θᵢ))
    2. Góc tổng = atan2(Vy, Vx), Độ lớn tổng = hypot(Vx, Vy)
    3. Lấy bounding box đại diện từ cột group_x/y/w/h (nếu có), fallback về anchor top-1.
    4. Sắp xếp kết quả theo vector_magnitude giảm dần.
    5. Xuất file Markdown + CSV tổng hợp.
    """
    print(f"[INFO] Reading Grouped CSV: {csv_path}")
    df = pd.read_csv(csv_path)

    if 'group_id' not in df.columns:
        print("[ERROR] CSV file does not contain 'group_id' column.")
        return

    # Tên file ảnh (nếu không truyền vào thì tự suy từ tên CSV)
    if not image_filename:
        csv_base = os.path.basename(csv_path)
        image_filename = csv_base.replace("_grouped.csv", ".jpg")

    # Gom nhóm theo group_id
    grouped = df.groupby('group_id')

    # Kiểm tra xem có cột bbox đại diện của group không
    has_group_bbox = all(c in df.columns for c in ['group_x_center', 'group_y_center', 'group_width', 'group_height'])

    report_rows = []

    for group_id, group_df in grouped:
        sum_x = 0.0
        sum_y = 0.0

        # Tìm Best Anchor (Dựa trên Độ lớn Vector cao nhất)
        best_anchor_row = group_df.loc[group_df['vector_magnitude'].idxmax()]
        best_anchor_angle = best_anchor_row['estimated_angle']
        best_anchor_mag   = best_anchor_row['vector_magnitude']

        anchor_count = len(group_df)

        # Lặp qua tất cả anchor trong group để giải mã Vector và cộng dồn
        for _, row in group_df.iterrows():
            mag     = row['vector_magnitude']
            ang_deg = row['estimated_angle']
            ang_rad = math.radians(ang_deg)
            sum_x  += mag * math.cos(ang_rad)
            sum_y  += mag * math.sin(ang_rad)

        # Tính toán "Siêu Vector" của Group
        group_mag = math.hypot(sum_x, sum_y)
        group_ang = math.degrees(math.atan2(sum_y, sum_x))
        avg_mag   = group_mag / anchor_count if anchor_count > 0 else 0.0

        # Bounding box đại diện (lấy từ cột group_* nếu có, không thì từ anchor top-1)
        if has_group_bbox:
            gx = float(best_anchor_row['group_x_center'])
            gy = float(best_anchor_row['group_y_center'])
            gw = float(best_anchor_row['group_width'])
            gh = float(best_anchor_row['group_height'])
        else:
            gx = float(best_anchor_row['x_center'])
            gy = float(best_anchor_row['y_center'])
            gw = float(best_anchor_row['width'])
            gh = float(best_anchor_row['height'])

        report_rows.append({
            'group_id':             int(group_id),
            'number_of_anchors':    anchor_count,
            'vector_magnitude':     round(group_mag, 2),
            'x_center':             round(gx, 2),
            'y_center':             round(gy, 2),
            'width':                round(gw, 2),
            'height':               round(gh, 2),
            'angle':                round(group_ang, 2),
            'image_filename':       image_filename,
            # Cột bổ sung giữ nguyên để không mất dữ liệu debug
            'avg_magnitude':        round(avg_mag, 2),
            'best_anchor_angle':    round(best_anchor_angle, 2),
            'best_anchor_mag':      round(best_anchor_mag, 2),
        })

    # Sắp xếp theo vector_magnitude giảm dần (yêu cầu mục 2.1)
    report_rows.sort(key=lambda r: r['vector_magnitude'], reverse=True)

    # ── Tạo nội dung Markdown ──────────────────────────────────────────────────
    md_lines = []
    md_lines.append("# Báo Cáo Đánh Giá Vector Tổng (Group)")
    md_lines.append(f"- **File nguồn:** `{csv_path}`")
    md_lines.append(f"- **Ảnh phân tích:** `{image_filename}`")
    md_lines.append(f"- **Tổng số Group:** {len(grouped)}")
    md_lines.append("")
    md_lines.append(
        "> **Lưu ý:** Độ lớn Vector Tổng (vector_magnitude) thường lớn hơn 1.0 vì đây là tổng "
        "đại số cộng dồn sức mạnh của tất cả các anchors chồng lặp. Khi nhiều anchors cùng dự đoán "
        "về một hướng, vector tổng sẽ kéo dài ra, thể hiện sức mạnh đồng thuận của tập thể. "
        "Cột **avg_magnitude** được bổ sung để đưa giá trị về thang đo dưới 1.0 như thông thường."
    )
    md_lines.append("")

    header_cols = [
        "group_id", "Số Anchor", "vector_magnitude",
        "x_center", "y_center", "width", "height",
        "angle", "image_filename",
        "avg_magnitude", "Góc Best Anchor", "Mag Best Anchor",
    ]
    md_lines.append("| " + " | ".join(header_cols) + " |")
    md_lines.append("|" + "|".join([":---:"] * len(header_cols)) + "|")

    for row in report_rows:
        angle_str = f"**`{row['angle']:.2f}°`**"
        md_lines.append(
            f"| {row['group_id']} "
            f"| {row['number_of_anchors']} "
            f"| **{row['vector_magnitude']:.2f}** "
            f"| {row['x_center']:.2f} "
            f"| {row['y_center']:.2f} "
            f"| {row['width']:.2f} "
            f"| {row['height']:.2f} "
            f"| {angle_str} "
            f"| `{row['image_filename']}` "
            f"| {row['avg_magnitude']:.2f} "
            f"| `{row['best_anchor_angle']:.2f}°` "
            f"| {row['best_anchor_mag']:.2f} |"
        )

    md_content = "\n".join(md_lines)

    # ── Đường dẫn output ──────────────────────────────────────────────────────
    csv_dir      = os.path.dirname(csv_path)
    csv_basename = os.path.basename(csv_path)
    name_no_ext  = os.path.splitext(csv_basename)[0]

    out_md_path  = os.path.join(csv_dir, f"{name_no_ext}_evaluation.md")
    out_csv_path = os.path.join(csv_dir, f"{name_no_ext}_vector_summary.csv")

    # Lưu Markdown
    with open(out_md_path, 'w', encoding='utf-8') as f:
        f.write(md_content)

    # Lưu CSV tổng hợp (vector_summary) – thứ tự cột theo yêu cầu
    summary_cols = [
        'group_id', 'number_of_anchors', 'vector_magnitude',
        'x_center', 'y_center', 'width', 'height',
        'angle', 'image_filename',
        'avg_magnitude', 'best_anchor_angle', 'best_anchor_mag',
    ]
    summary_df = pd.DataFrame(report_rows)[summary_cols]
    summary_df.to_csv(out_csv_path, index=False, float_format="%.2f")

    print(f"[DONE] Evaluated {len(grouped)} groups, sorted by vector_magnitude descending.")
    print(f"[DONE] Markdown  -> {out_md_path}")
    print(f"[DONE] CSV       -> {out_csv_path}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Evaluate Grouped Vectors to calculate Group Super-Vector")
    parser.add_argument('--csv',   type=str, required=True,  help="Path to the grouped CSV file")
    parser.add_argument('--image', type=str, default="",     help="Tên file ảnh input (cho báo cáo)")

    args = parser.parse_args()
    evaluate_group_vectors(args.csv, image_filename=args.image)
