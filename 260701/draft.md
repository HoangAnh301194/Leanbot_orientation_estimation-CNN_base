# Báo cáo công việc ngày 20/06/2026

## A. Công việc đã làm

### 1. Tổng quan về bài toán hiện tại.
Vì đã một tháng em xin nghỉ nên trong khoảng thời gian đó có thể đã mất mạch làm việc, nghiên cứu với Thầy nên em xin phép tổng quan lại bài toán hiện tại để Thầy nắm được tình hình và định hướng tiếp theo ạ.

- Công việc trước đó em đang thực hiện bao gồm : 
    - Chỉnh sửa hàm Mất mát ( Loss Function) từ BCE defaut thành Soft Angular BCE Loss. Phương pháp này là thử nghiệm trước mắt. Vẫn còn các phương pháp có thể thử nghiệm tiếp theo:  
        - Label Smoothing
        - Focal Cross Entropy Loss
        - Cross Entropy Loss (BCE) + sai số góc ( Angle-aware Loss)
    - Sử dụng kết quả Model train bằng Soft Angular BCE Loss để đánh giá kết quả. Hiện tại dự án đang sử dụng các tools đánh giá chính:
        - Tools xuất báo cáo dạng bảng Markdown: [export_markdown_report.py](tools/export_markdown_report.py) 
            + Báo cáo trình bày ảnh có vẽ BBox trực quan. 
            + Bảng phân tích chi tiết từng Leanbot: Tọa độ BBox, điểm confidence của các class góc, góc dự đoán truyền thống (Best class) và góc nội suy mềm.
            + Kỹ thuật tính góc: Góc ước lượng được tính bằng phương pháp **Top-K Vector Sum** (chỉ lấy trung bình vector của 2 class có điểm cao nhất để lọc nhiễu, thay vì cộng dồn cả 24 class).
        - Tools xuất file CSV lọc top 200 Anchor tốt nhất: [check_confidence.py](tools/check_confidence.py) 
            + Lưu lại tối đa 200 khung dự đoán thô (anchor) có điểm số tự tin cao nhất.
            + Nội dung : Tọa độ khung (x, y, w, h), điểm confidence lớn nhất, và chi tiết 24 cột điểm của 24 class góc.
        - Tools gom nhóm các Anchor chồng lặp: [group_anchors.py](tools/group_anchors.py) 
            + Sử dụng thuật toán IoU để gom các khung hình bị chồng chéo (cùng chỉ vào 1 Leanbot) thành từng nhóm (group_id).
            + Xuất ra file CSV tổng hợp và làm gọn dữ liệu (đại diện mỗi Leanbot là một nhóm dự đoán).
    

### 2. Công việc cần thực hiện. 
- Chỉnh sửa lại file CSV đánh giá kết quả các confidence theo Soft Angular BCE loss : 
    + Biểu diễn vector tổng của 24 confidence của 24 class
    + Tính góc tương ứng với vector tổng

- Chỉnh sửa bảng CSV góp nhóm các Anchors overlap:
    + Bỏ cột best class, max confidence
    + Thêm cột vector tổng 24 class và góc tương ứng
- Tính toán vector tổng sau khi gom nhóm các Anchor overlap với nhau. 
    + Thêm tools phân tích file **grouped.csv**, tính toán Vector tổng , góc tương ứng, tạo bảng tổng quan. 

### 2.1 Chỉnh sửa lại file tạo bảng đánh giá Maskdown
**File code:** [`export_markdown_report.py`](tools/export_markdown_report.py)

**Nội dung thay đổi:**
- Loại bỏ hoàn toàn cơ chế lọc Top-K (chỉ lấy 2 class cao nhất) khi tính góc.
- Áp dụng công thức cộng Vector cho **toàn bộ 24 class**, từ đó tính ra được "Độ lớn Vector" (Magnitude) và "Góc ước lượng" (Estimated Angle) đại diện cho sức ảnh hưởng của tất cả các class cộng lại.
- Dịch chuyển 3 cột quan trọng: `Best Class`, `Độ lớn Vector`, `Góc ước lượng` lên đầu bảng (ngay sau cột BBox) để dễ quan sát hơn trước khi xem chi tiết 24 class. ( Phần này em vẫn giữ lại Best class để dễ so sánh xem góc ước lượng lệch thế nào so với nhãn có confidence cao nhất của đối tượng)

**Chi tiết code thay đổi:**
```python
# Tính vector tổng từ 24 class
def estimate_angle_from_scores(class_scores: list) -> tuple:
    sum_x, sum_y = 0.0, 0.0
    for idx, score in enumerate(class_scores):
        cls_name = CLASSES[idx]
        angle_deg = extract_angle_from_class(cls_name)
        if angle_deg is not None:
            rad = math.radians(angle_deg)
            sum_x += score * math.cos(rad)
            sum_y += score * math.sin(rad)
            
    magnitude = math.hypot(sum_x, sum_y)
    estimated_angle = math.degrees(math.atan2(sum_y, sum_x))
    return estimated_angle, magnitude
```

**Cấu trúc bảng Maskdown mới :**
[`report.md`](test_vector_results/report/report.md)

| Vị trí | BBox (Xc, Yc, W, H) | Best Class | Độ lớn Vector | Góc ước lượng | 0 | p15 | p30 | p45 | p60 | p75 | p90 | p105 | p120 | p135 | p150 | p165 | p180 | p195 | m150 | m135 | m120 | m105 | m90 | m75 | m60 | m45 | m30 | m15 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| #1 | (1043.5, 777, 221, 142) | `Leanbot_p195` (0.6074) | 0.2779 | -143.8° | 0.3406 | 0.0171 | 0.0021 | 0.0031 | 0.0001 | 0.0001 | 0.0000 | 0.0001 | 0.0001 | 0.0004 | 0.0001 | 0.0095 | 0.0014 | 0.6074 | 0.0004 | 0.0001 | 0.0012 | 0.0066 | 0.0040 | 0.0012 | 0.0005 | 0.0005 | 0.0006 | 0.0139 |
| #2 | (1415.5, 485.5, 185, 105) | `Leanbot_p195` (0.5686) | 0.4748 | -157.4° | 0.0000 | 0.0000 | 0.0003 | 0.0023 | 0.0023 | 0.0004 | 0.0001 | 0.0000 | 0.0001 | 0.0002 | 0.0010 | 0.0002 | 0.0099 | 0.5686 | 0.0013 | 0.0045 | 0.0003 | 0.0012 | 0.0001 | 0.0001 | 0.0021 | 0.0000 | 0.0005 | 0.1264 |
| #3 | (1753.5, 474, 203, 110) | `Leanbot_p195` (0.5568) | 0.4040 | -146.4° | 0.0000 | 0.0001 | 0.0005 | 0.0020 | 0.0034 | 0.0001 | 0.0001 | 0.0000 | 0.0001 | 0.0003 | 0.0038 | 0.0010 | 0.0917 | 0.5568 | 0.0017 | 0.0028 | 0.0001 | 0.0017 | 0.0003 | 0.0000 | 0.0023 | 0.0000 | 0.0008 | 0.3063 |
| #4 | (2007, 1108, 290, 214) | `Leanbot_p180` (0.4769) | 0.4542 | -175.2° | 0.0001 | 0.0000 | 0.0004 | 0.0002 | 0.0008 | 0.0003 | 0.0002 | 0.0000 | 0.0010 | 0.0024 | 0.0040 | 0.0000 | 0.4769 | 0.0059 | 0.0381 | 0.0017 | 0.0000 | 0.0003 | 0.0001 | 0.0029 | 0.0007 | 0.0000 | 0.0005 | 0.0697 |
| #5 | (1415.5, 485, 187, 108) | `Leanbot_p180` (0.4745) | 0.2943 | -165.4° | 0.0000 | 0.0001 | 0.0017 | 0.0003 | 0.0009 | 0.0001 | 0.0001 | 0.0000 | 0.0001 | 0.0001 | 0.0029 | 0.0248 | 0.4745 | 0.0342 | 0.0056 | 0.0014 | 0.0000 | 0.0018 | 0.0006 | 0.0002 | 0.0009 | 0.0000 | 0.0036 | 0.2586 |
| #6 | (1478, 1117, 268, 180) | `Leanbot_p195` (0.4225) | 0.3532 | -161.3° | 0.0758 | 0.0037 | 0.0003 | 0.0037 | 0.0002 | 0.0001 | 0.0002 | 0.0000 | 0.0001 | 0.0012 | 0.0001 | 0.0141 | 0.0007 | 0.4225 | 0.0003 | 0.0002 | 0.0008 | 0.0024 | 0.0010 | 0.0043 | 0.0017 | 0.0009 | 0.0021 | 0.0034 |
| #7 | (1415.5, 485.5, 185, 105) | `Leanbot_m15` (0.3868) | 0.3062 | -21.0° | 0.0000 | 0.0000 | 0.0003 | 0.0002 | 0.0017 | 0.0001 | 0.0000 | 0.0000 | 0.0002 | 0.0001 | 0.0059 | 0.0011 | 0.0362 | 0.0480 | 0.0002 | 0.0007 | 0.0002 | 0.0010 | 0.0004 | 0.0000 | 0.0003 | 0.0000 | 0.0007 | 0.3868 |
| #8 | (974.5, 1138.5, 257, 183) | `Leanbot_p195` (0.3859) | 0.2305 | -148.9° | 0.1653 | 0.0057 | 0.0044 | 0.0043 | 0.0001 | 0.0001 | 0.0002 | 0.0000 | 0.0002 | 0.0004 | 0.0001 | 0.0077 | 0.0009 | 0.3859 | 0.0003 | 0.0001 | 0.0025 | 0.0146 | 0.0063 | 0.0022 | 0.0005 | 0.0004 | 0.0007 | 0.0103 |
| #9 | (1044, 776, 218, 140) | `Leanbot_0` (0.3559) | 0.2528 | -9.7° | 0.3559 | 0.0063 | 0.0003 | 0.0010 | 0.0000 | 0.0001 | 0.0000 | 0.0000 | 0.0002 | 0.0002 | 0.0002 | 0.0023 | 0.0002 | 0.1287 | 0.0001 | 0.0002 | 0.0006 | 0.0016 | 0.0052 | 0.0007 | 0.0009 | 0.0003 | 0.0001 | 0.0138 |

---

### 2.2 Chỉnh sửa lại file CSV đánh giá kết quả các confidence theo Soft Angular BCE loss
**File code:** [`check_confidence_640.py`](tools/check_confidence_640.py) và [`check_confidence.py`](tools/check_confidence.py)

**Nội dung thay đổi:**
- Loại bỏ cột `best_class` và `confidence` (max_conf) cũ.
- Tích hợp hàm dùng Regex để tự động tách giá trị góc từ tên class (ví dụ: biến đổi `Leanbot_m15` thành góc `-15`, `Leanbot_p30` thành góc `30`, `Leanbot_0` thành `0`).
- Trích xuất ra hai thông số `vector_magnitude` và `estimated_angle`, đẩy lên 2 cột đầu tiên của file CSV.
- Format định dạng số thực chỉ giữ lại 2 chữ số thập phân bằng `float_format="%.2f"`.

**Chi tiết code thay đổi:**
```python
# Cập nhật thứ tự các cột vào CSV
# Tính toán xong mag (magnitude) và ang (angle) từ sum_x, sum_y
mag = math.hypot(sum_x, sum_y)
ang = math.degrees(math.atan2(sum_y, sum_x))

# Đẩy mag và ang lên đầu mỗi row
row = [float(mag), float(ang)] + top_boxes[i].tolist() + top_scores[i].tolist()
all_data.append(row)

```

**Cấu trúc bảng CSV mới :**
[test_vector_results/002_top200.csv](test_vector_results/002_top200.csv)

```csv
vector_magnitude,estimated_angle,x_center,y_center,width,height,Leanbot_0,Leanbot_p15,Leanbot_p30,Leanbot_p45,Leanbot_p60,Leanbot_p75,Leanbot_p90,Leanbot_p105,Leanbot_p120,Leanbot_p135,Leanbot_p150,Leanbot_p165,Leanbot_p180,Leanbot_p195,Leanbot_m150,Leanbot_m135,Leanbot_m120,Leanbot_m105,Leanbot_m90,Leanbot_m75,Leanbot_m60,Leanbot_m45,Leanbot_m30,Leanbot_m15
0.83,-168.84,184.38,504.50,113.36,80.45,0.12,0.00,0.00,0.00,0.00,0.00,0.01,0.00,0.00,0.00,0.00,0.00,0.42,0.59,0.00,0.00,0.00,0.00,0.01,0.00,0.00,0.00,0.00,0.06
0.42,-163.79,381.56,215.70,82.02,48.72,0.06,0.02,0.00,0.01,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.02,0.00,0.49,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00
0.59,-166.83,184.70,503.84,113.13,78.78,0.27,0.00,0.00,0.00,0.00,0.00,0.01,0.00,0.00,0.01,0.00,0.00,0.42,0.48,0.00,0.00,0.00,0.00,0.02,0.00,0.00,0.00,0.00,0.05
0.40,-166.83,184.47,504.24,113.26,80.24,0.09,0.00,0.00,0.00,0.00,0.00,0.01,0.00,0.00,0.01,0.00,0.00,0.14,0.39,0.00,0.00,0.00,0.00,0.01,0.00,0.00,0.00,0.00,0.05
0.33,-167.63,224.91,220.49,79.00,47.78,0.05,0.02,0.00,0.01,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.06,0.00,0.36,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00
0.26,-158.48,216.27,345.67,92.81,64.71,0.24,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.01,0.00,0.00,0.16,0.35,0.00,0.00,0.00,0.00,0.01,0.00,0.00,0.00,0.00,0.02
0.40,-168.15,408.94,496.05,116.92,83.89,0.03,0.00,0.00,0.00,0.00,0.00,0.02,0.00,0.00,0.01,0.01,0.00,0.15,0.34,0.00,0.00,0.00,0.00,0.01,0.00,0.00,0.00,0.00,0.08
0.28,-163.46,381.47,215.61,81.70,48.28,0.04,0.01,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.02,0.00,0.31,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00
0.32,-166.71,216.61,345.40,92.55,65.00,0.10,0.00,0.00,0.00,0.00,0.00,0.01,0.00,0.00,0.00,0.00,0.00,0.16,0.29,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.04
0.23,-161.53,184.97,504.44,112.92,78.93,0.11,0.01,0.00,0.00,0.00,0.00,0.01,0.00,0.00,0.01,0.00,0.00,0.08,0.27,0.00,0.00,0.00,0.00,0.01,0.00,0.00,0.00,0.00,0.02
```

---

### 2.3 Chỉnh sửa lại file gom nhóm Anchors chồng lặp (Group Anchors)
**File code:** [`group_anchors.py`](tools/group_anchors.py)

**Nội dung thay đổi:**
- Thay đổi tiêu chí khi chọn Anchor trung tâm (đại diện cho một nhóm bị chồng chéo). Trước đây hệ thống chọn anchor có Best Class tự tin nhất (`max_conf`), hiện tại đã chuyển sang chọn anchor có **Độ lớn Vector (Magnitude)** cao nhất làm trung tâm.
- Chỉnh sửa nội dung file báo cáo text (`*_grouped_report.txt`) để in ra chỉ số `Góc` và `Độ lớn` thay cho `Max Conf`.

**Chi tiết code thay đổi:**
```python
# Sắp xếp các anchor trong nhóm theo Độ lớn Vector (vector_magnitude) giảm dần để chọn ra Top 1
group_df = group_df.sort_values(by='vector_magnitude', ascending=False)
```

**Cấu trúc bảng CSV sau khi gom nhóm (chỉ còn các anchor trung tâm):**
[test_vector_results/002_grouped.csv](test_vector_results/002_grouped.csv)

```csv
group_id,vector_magnitude,estimated_angle,x_center,y_center,width,height,Leanbot_0,Leanbot_p15,Leanbot_p30,Leanbot_p45,Leanbot_p60,Leanbot_p75,Leanbot_p90,Leanbot_p105,Leanbot_p120,Leanbot_p135,Leanbot_p150,Leanbot_p165,Leanbot_p180,Leanbot_p195,Leanbot_m150,Leanbot_m135,Leanbot_m120,Leanbot_m105,Leanbot_m90,Leanbot_m75,Leanbot_m60,Leanbot_m45,Leanbot_m30,Leanbot_m15
1,0.83,-168.84,184.38,504.50,113.36,80.45,0.12,0.00,0.00,0.00,0.00,0.00,0.01,0.00,0.00,0.00,0.00,0.00,0.42,0.59,0.00,0.00,0.00,0.00,0.01,0.00,0.00,0.00,0.00,0.06
2,0.42,-163.79,381.56,215.70,82.02,48.72,0.06,0.02,0.00,0.01,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.02,0.00,0.49,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00
```

**Báo cáo Debug Gom Nhóm :**
[002_grouped_report.txt](test_vector_results/002_grouped_report.txt)

```text
--- NHÓM 1 (Gồm 14 anchors chồng lặp lên nhau) ---
  [Top 1] Anchor trung tâm (Góc -168.8° | Độ lớn: 0.83)
  [Phụ] Các anchor khác trong cùng nhóm:
      - Góc -166.8° (Độ lớn: 0.59)
      - Góc -166.8° (Độ lớn: 0.40)
      - Góc -161.5° (Độ lớn: 0.23)
      - Góc -164.7° (Độ lớn: 0.12)
      - Góc -166.8° (Độ lớn: 0.08)
      - Góc -3.3° (Độ lớn: 0.03)

      ...
      

--- NHÓM 2 (Gồm 29 anchors chồng lặp lên nhau) ---
  [Top 1] Anchor trung tâm (Góc -163.8° | Độ lớn: 0.42)
  [Phụ] Các anchor khác trong cùng nhóm:
      - Góc -163.5° (Độ lớn: 0.28)
      - Góc -164.6° (Độ lớn: 0.15)
      - Góc -156.0° (Độ lớn: 0.14)
      - Góc -163.1° (Độ lớn: 0.13)
      - Góc -24.4° (Độ lớn: 0.09)

      ...
```

---

### 2.4 Xây dựng Tool Đánh giá Vector Tổng cho toàn bộ Group
**File code:** [`evaluate_group_vectors.py`](tools/evaluate_group_vectors.py)

**Nội dung bổ sung:**
- Bổ sung công cụ phân tích file CSV đã gom nhóm (Grouped CSV).
- Dùng công thức lượng giác: `x = r * cos(θ)` và `y = r * sin(θ)` để biến đổi ngược Vector của từng anchor chồng lặp (dựa trên `vector_magnitude` và `estimated_angle`) về dạng hệ tọa độ Descartes (Vx và Vy).
- Cộng dồn tất cả các Vector Vx Vy trong cùng một nhóm lại với nhau, tạo thành Vector tổng đại diện. Từ đó tính ra **Góc của Vector tổng** và **Độ lớn Vector tổng** để đánh giá toàn bộ nhóm anchors overlap nhau.
- Tự động xuất kết quả đánh giá ra file Markdown trình bày dạng bảng.

**Chi tiết code thay đổi (Logic cộng dồn Vector):**
```python
# Lặp qua tất cả anchor trong group để giải mã Vector và cộng dồn
for _, row in group_df.iterrows():
    mag = row['vector_magnitude']
    ang_deg = row['estimated_angle']
    
    ang_rad = math.radians(ang_deg)
    sum_x += mag * math.cos(ang_rad)
    sum_y += mag * math.sin(ang_rad)
    
# Tính toán vector tổng của group bằng atan2()
group_mag = math.hypot(sum_x, sum_y)
group_ang = math.degrees(math.atan2(sum_y, sum_x))
```

**Bảng báo cáo Markdown sau khi đánh giá:**
[test_vector_results/002_grouped_evaluation.md](test_vector_results/002_grouped_evaluation.md)

> **Nhận xét:** Độ lớn Vector Tổng (Group Magnitude) lớn hơn 1.0 vì đây là tổng đại số cộng dồn của tất cả các anchors chồng lặp. Khi nhiều anchors cùng dự đoán về một hướng, vector tổng sẽ lớn hơn. 

- Cột `Độ lớn Trung Bình` được tính bằng cách lấy `Độ lớn Vector Tổng` chia cho `Số lượng Anchor`. Để đưa giá trị về thang đo dưới 1.0 như thông thường. 

| Group ID | Số Anchor | Góc Tổng (Group) | Độ lớn Vector Tổng | Độ lớn Trung Bình | Góc Anchor Tốt Nhất | Độ lớn Anchor Tốt Nhất |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | 14 | **`-166.37°`** | **2.15** | 0.15 | `-168.84°` | 0.83 |
| 2 | 29 | **`-158.27°`** | **1.36** | 0.05 | `-163.79°` | 0.42 |
| 3 | 19 | **`-165.52°`** | **1.14** | 0.06 | `-168.15°` | 0.40 |
| 4 | 22 | **`-165.12°`** | **1.68** | 0.08 | `-167.63°` | 0.33 |
| 5 | 13 | **`-157.93°`** | **0.98** | 0.08 | `-166.71°` | 0.32 |
| 6 | 22 | **`-60.37°`** | **1.07** | 0.05 | `-61.08°` | 0.29 |
| 7 | 28 | **`-177.03°`** | **0.99** | 0.04 | `-175.52°` | 0.21 |
| 8 | 31 | **`-179.60°`** | **1.32** | 0.04 | `176.29°` | 0.18 |
| 9 | 19 | **`174.47°`** | **0.36** | 0.02 | `-163.52°` | 0.14 |
| 10 | 2 | **`-80.08°`** | **0.06** | 0.03 | `-70.61°` | 0.06 |
| 11 | 1 | **`84.57°`** | **0.05** | 0.05 | `84.57°` | 0.05 |

## B. Khó khăn 
- Không

## C. Công việc tiếp theo 
- Em xin phép nhận hướng đi tiếp theo từ Thầy ạ. 