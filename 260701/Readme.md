# Báo cáo công việc ngày 01/07/2026

## A. Công việc đã làm

### 1. Tổng quan công việc cần làm

1. Bổ sung tính **Bbox đại diện (Weighted Average BBox)** cho mỗi group anchor.
    - Tính x_center,y_center,width,height chung của cả nhóm dựa trên trọng số là vector_magnitude của từng anchor
2. Chỉnh sửa **báo cáo đánh giá Vector Tổng** 
    - Xếp theo thứ tự  Độ lớn Vector Tổng
    - Thêm 4 cột  x_center,y_center,width,height (vào ngay sau cột Độ lớn Vector Tổng)
    - Thêm thông tin ảnh phần tích (tên file ảnh)
3. **Phân tích nguyên nhân** hai group dự đoán sai góc (Group 6: -60.37° và Group 9: 174.47° trong kết quả cũ).
4. **Chuẩn hóa scripts code Python** thành một script duy nhất chạy từ ảnh JPG đầu vào đến toàn bộ kết quả đầu ra ( Bảng đánh giá vector tổng , csv vector tổng,...).

---

### 1. Tính Bounding Box đại diện cho mỗi Group Anchor

**Link code:** [`group_anchors.py`](tools/group_anchors.py)

**Nội dung thay đổi:**
- Bổ sung hàm `compute_weighted_bbox()` tính tọa độ đại diện bằng **trung bình có trọng số** (weighted average), trọng số là `vector_magnitude` của từng anchor.
- Công thức áp dụng:

```
x̄ = Σ(mᵢ × xᵢ) / Σmᵢ
```

Tương tự cho `y_center`, `width`, `height`. Trường hợp tổng trọng số ≈ 0 sẽ fallback về trung bình cộng thông thường.

**Chi tiết code thay đổi:**
```python
def compute_weighted_bbox(group_df: pd.DataFrame) -> tuple[float, float, float, float]:
    """
    Tính bounding box đại diện bằng trung bình có trọng số.
    Trọng số = vector_magnitude của từng anchor.
    Fallback: trung bình cộng nếu tổng trọng số = 0.
    """
    weights = group_df['vector_magnitude'].values
    total_weight = weights.sum()

    if total_weight <= 1e-9:
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
```

**Kết quả CSV mới – các cột bbox đại diện được thêm vào `grouped_anchors.csv`:**

```csv
group_id,vector_magnitude,estimated_angle,x_center,y_center,width,height,group_x_center,group_y_center,group_width,group_height,...
1,2.21,-168.79,184.38,504.50,113.36,80.45,184.67,504.52,112.84,79.89,...
2,1.05,-163.40,381.56,215.70,82.02,48.72,381.60,215.65,81.98,48.59,...
```

> **Kết quả:** `group_x_center`, `group_y_center`, `group_width`, `group_height` là tọa độ đại diện của cả group sau khi cộng dồn sức ảnh hưởng từ tất cả các anchor (không chỉ lấy anchor trung tâm như trước). Những anchor có `vector_magnitude` cao hơn sẽ kéo bbox về phía mình nhiều hơn.

---

### 2. Chỉnh sửa Báo cáo Đánh giá Vector Tổng

**Link code:** [`evaluate_group_vectors.py`](tools/evaluate_group_vectors.py)

**Nội dung thay đổi:**
- **Sắp xếp** kết quả theo `vector_magnitude` giảm dần (group mạnh nhất lên đầu).
- **Thêm 4 cột** ngay sau `vector_magnitude`: `x_center`, `y_center`, `width`, `height` (lấy từ weighted bbox của group).
- **Thêm cột `image_filename`** để biết ảnh phân tích là ảnh nào.
- **Xuất thêm file CSV** `*_vector_summary.csv` song song với file Markdown, phục vụ debug.
- Thứ tự cột theo đề xuất: `group_id | number_of_anchors | vector_magnitude | x_center | y_center | width | height | angle | image_filename`.

**Bảng báo cáo Markdown sau khi chỉnh sửa code:**

| group_id | Số Anchor | vector_magnitude | x_center | y_center | width | height | angle | image_filename |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 2 | 22 | **15.34** | 569.02 | 328.25 | 101.05 | 60.62 | **`-169.34°`** | `002.jpg` |
| 3 | 18 | **14.09** | 389.13 | 321.32 | 94.60 | 61.04 | **`-171.94°`** | `002.jpg` |
| 7 | 18 | **13.90** | 215.25 | 344.95 | 97.66 | 64.57 | **`-173.33°`** | `002.jpg` |
| 8 | 21 | **12.66** | 183.93 | 506.07 | 113.83 | 82.18 | **`-170.27°`** | `002.jpg` |
| 5 | 25 | **12.15** | 407.55 | 498.46 | 123.35 | 82.72 | **`-173.81°`** | `002.jpg` |
| 1 | 24 | **11.91** | 531.60 | 211.09 | 87.88 | 51.38 | **`-171.14°`** | `002.jpg` |
| 6 | 18 | **11.85** | 224.42 | 220.81 | 79.93 | 49.60 | **`-176.04°`** | `002.jpg` |
| 9 | 19 | **9.74** | 611.56 | 493.01 | 56.81 | 95.68 | **`-166.83°`** | `002.jpg` |
| 4 | 24 | **8.93** | 381.71 | 215.92 | 80.71 | 49.45 | **`-174.33°`** | `002.jpg` |

> **Kết luận:** Sau khi chỉnh sửa code, **tất cả 9 group chính đều hội tụ về vùng -165° đến -176°**, phù hợp với quan sát ảnh. Hai kết quả bất thường trước đây đều có nguyên nhân từ **cách tính vector tổng của script cũ**: Group 6 (`-60.37°`) bị sai do anchor trung tâm top-1 đã có góc `-61.08°` nên kéo toàn group theo; Group 9 (`+174.47°`) bị lật hướng do anchor nhiễu chiếm tỉ trọng đủ lớn khi `vector_magnitude tổng` chỉ = 0.36 – phân tích chi tiết tại mục 3.

---

### 3. Phân tích Group 6 và Group 9 dự đoán sai góc


#### 3.1. Kết quả bất thường cần phân tích (script cũ `evaluate_group_vectors.py`)

| Group | Số Anchor | Góc script cũ | Góc script mới | Sai lệch |
|:---:|:---:|:---:|:---:|:---:|
| 6 | 22 | `-60.37°` | `-166.83°` | ~106° |
| 9 | 19 | `+174.47°` | `-176.04°` | ~350° (lật hướng) |

#### 3.2. Phân tích nguyên nhân từ dữ liệu thực tế khi chạy các script phân tích mới

**Dữ liệu debug tại vị trí Group 6 cũ – toàn bộ 19 anchors theo script mới (x≈611, y≈493):**

```
 #   magnitude   angle        x_center   y_center   top_class        contribution%
 1   1.6033      -164.18°     611.89     492.57     Leanbot_p195     16.47
 2   1.3567      -165.21°     611.53     492.88     Leanbot_p195     13.94
 3   1.3263      -169.20°     611.28     492.75     Leanbot_p180     13.62
 4   1.1615      -172.64°     611.72     492.78     Leanbot_p195     11.93
 5   1.1259      -169.54°     611.50     493.59     Leanbot_p180     11.56
 6   0.9493      -168.29°     611.48     492.79     Leanbot_p180      9.75
 7   0.7116      -169.69°     611.38     492.77     Leanbot_p195      7.31
 8   0.4748      -167.30°     611.20     493.44     Leanbot_p180      4.88
 9   0.3285      -163.20°     611.44     493.85     Leanbot_p180      3.37
10   0.2918      -154.28°     611.86     493.62     Leanbot_p195      3.00
11   0.1665      -160.80°     611.97     493.41     Leanbot_p195      1.71
12   0.1115      -153.68°     611.72     493.94     Leanbot_p195      1.14
13   0.0602      -167.54°     611.05     493.73     Leanbot_p180      0.62
14   0.0262      -127.26°     610.35     494.38     Leanbot_m15       0.27
15   0.0261      -139.55°     610.50     494.08     Leanbot_p180      0.27
16   0.0193      -157.94°     611.92     493.48     Leanbot_p180      0.20
17   0.0166       -87.29°     610.83     494.31     Leanbot_m15       0.17
18   0.0137      -164.79°     614.90     495.35     Leanbot_m150      0.14
19   0.0124      -156.49°     615.21     512.82     Leanbot_m150      0.13
```

**Kết luận Group 6 cũ:**
- Tất cả 19 anchor **tập trung tại một vị trí** (x≈611, y≈493) – không bị gom nhầm.
- Script mới tính vector tổng cho ra góc **`-166.83°`**, nhất quán với các group còn lại.
- **Nguyên nhân kết quả cũ bị `-60.37°`:** Script cũ đã tính `estimated_angle` của từng anchor bằng phương pháp **Top-K (chỉ lấy 2 class cao nhất)** → các anchor tại vị trí này cho `estimated_angle ≈ -60°` thay vì `-165°`. Khi cộng dồn vector tổng, toàn group bị kéo theo hướng `-60°`.

**So sánh hai cách tính tại Group 6 cũ (dữ liệu từ `002_grouped.csv` của 260620):**

| Cách tính | Input | Kết quả |
|:---|:---|:---:|
| **Script cũ** (260620) | `estimated_angle` của từng anchor (tính bằng Top-K 2 class) | **`-60.37°`** ❌ |
| **Script mới** (260701) | `score_i × cos(θ_i)` trực tiếp từ 24 class scores thô | **`-166.83°`** ✅ |

**Vết tính script cũ – 22 anchors tại Group 6 (trích từ `002_grouped.csv` / 260620):**

```
# Script cũ: sum_x = Σ mag_i × cos(estimated_angle_i)
#             sum_y = Σ mag_i × sin(estimated_angle_i)

Anchor  1: mag=0.2900, angle= -61.08° → Vx=+0.1402, Vy=-0.2538
Anchor  2: mag=0.2600, angle= -57.15° → Vx=+0.1410, Vy=-0.2184
Anchor  3: mag=0.1500, angle= -53.68° → Vx=+0.0888, Vy=-0.1209
Anchor  4: mag=0.1400, angle= -64.50° → Vx=+0.0603, Vy=-0.1264
Anchor  5: mag=0.0900, angle= -60.31° → Vx=+0.0446, Vy=-0.0782
Anchor  6: mag=0.0600, angle= -58.05° → Vx=+0.0318, Vy=-0.0509
Anchor  7: mag=0.0500, angle=+117.51° → Vx=-0.0231, Vy=+0.0443  ← nhiễu
Anchor  8: mag=0.0500, angle= -59.80° → Vx=+0.0252, Vy=-0.0432
...
Anchor 22: mag=0.0000, angle= +33.63° → Vx=+0.0000, Vy=+0.0000

--> sum_x = +0.5310,  sum_y = -0.9336
--> atan2(-0.9336, +0.5310) = -60.37°  --> Kết quả sai
```

**Vết tính script mới – cùng vị trí (Group 9 mới, từ `debug_groups.csv` / 260701):**

```
# Script mới: vector_x và vector_y tính trực tiếp từ 24 class scores
#   vx = Σ score_i × cos(θ_i)    vy = Σ score_i × sin(θ_i)
#   (24 class, không qua atan2 trung gian)

Anchor  1: vx=-1.5426, vy=-0.4371  (predicted_angle=-164.18°, mag=1.6033)
Anchor  2: vx=-1.3117, vy=-0.3463  (predicted_angle=-165.21°, mag=1.3567)
Anchor  3: vx=-1.3028, vy=-0.2485  (predicted_angle=-169.20°, mag=1.3263)
Anchor  4: vx=-1.1519, vy=-0.1488  (predicted_angle=-172.64°, mag=1.1615)
Anchor  5: vx=-1.1072, vy=-0.2044  (predicted_angle=-169.54°, mag=1.1259)
...

--> sum_x = -9.4797,  sum_y = -2.2181
--> atan2(-2.2181, -9.4797) = -166.83°  --> Kết quả đúng theo hướng dự đoán
```

> **Kết luận:** Script cũ dùng `estimated_angle` tính bằng Top-K 2 class → các anchor tại vị trí này bị phân loại thiên về `Leanbot_m75/-m60/-m45` (góc ~-60°) vì đây là class có confidence cao nhất trong Top-2. Script mới cộng đủ 24 class scores → contribution từ `Leanbot_p180/p195` (class thực sự mạnh nhất) được tính đúng → cho góc `-166.83°`.

**Dữ liệu debug tại vị trí Group 9 cũ – toàn bộ 18 anchors theo script mới (x≈224, y≈221):**

```
 #   magnitude   angle        x_center   y_center   top_class        contribution%
 1   1.9617      -175.33°     224.67     220.89     Leanbot_p180     16.55
 2   1.5860      -175.47°     224.85     220.59     Leanbot_p180     13.38
 3   1.4253      -176.87°     224.23     220.85     Leanbot_p180     12.03
 4   1.4055      -176.69°     223.87     220.68     Leanbot_p180     11.86
 5   1.2179      -175.48°     224.06     220.79     Leanbot_p195     10.28
 6   1.1292      -177.82°     224.48     220.90     Leanbot_p180      9.53
 7   1.0887      -176.05°     224.67     220.91     Leanbot_p180      9.19
 8   0.9410      -173.75°     224.26     220.87     Leanbot_p195      7.94
 9   0.7113      -176.43°     224.53     220.69     Leanbot_p180      6.00
10   0.1549      -179.21°     224.49     220.81     Leanbot_p180      1.31
11   0.0797      -174.63°     224.24     221.25     Leanbot_p180      0.67
12   0.0492      -176.24°     224.32     221.17     Leanbot_p180      0.42
13   0.0250      -178.86°     225.23     220.95     Leanbot_p195      0.21
14   0.0195       179.70°     225.51     221.48     Leanbot_p195      0.16
15   0.0184      -176.60°     224.64     220.76     Leanbot_p180      0.16
16   0.0180      -179.67°     225.38     221.63     Leanbot_p180      0.15
17   0.0120      -176.57°     224.46     220.91     Leanbot_p180      0.10
18   0.0096       176.32°     225.17     221.69     Leanbot_p180      0.08
```

**Kết luận Group 9 cũ:**
- Phần lớn anchor đều về hướng `-173°` đến `-179°` (đúng), tập trung tại (x≈224, y≈221).
- Script mới tính vector tổng cho ra góc **`-176.04°`**, đúng theo dự đoán chung.
- **Nguyên nhân kết quả cũ cho kết quả `+174.47°`:** Script cũ bị ảnh hưởng bởi anchor nhiễu có magnitude đủ lớn để lật vector tổng; `vector_magnitude tổng = 0.36` (rất thấp) khiến các anchor bù trừ nhau, script mới xử lý đúng.

#### 3.3. Tổng hợp nguyên nhân

| Group | Kết quả cũ | Kết quả mới | Loại lỗi | Nguyên nhân cụ thể |
|:---:|:---:|:---:|:---:|:---|
| 6 | `-60.37°` | `-166.83°` | **Lỗi cách tính vector tổng** | Script cũ tính vector tổng của group bằng cách **biến đổi ngược anchor trung tâm** (top-1 magnitude = `-61.08°`) thành `(Vx, Vy)` rồi cộng dồn tất cả anchors – anchor trung tâm đã bị dự đoán sai lệch nên kéo toàn group theo. Script mới cộng trực tiếp `(cos(θ), sin(θ))` từ từng anchor riêng biệt, cho góc đúng. |
| 9 | `+174.47°` | `-176.04°` | **Anchor nhiễu + vector_magnitude tổng thấp** | `vector_magnitude tổng = 0.36` (rất thấp), các anchor nhiễu có góc ngược `+25°`→`+55°` và `+140°`→`+161°` chiếm đủ tỉ trọng để lật vector tổng từ `-163°` sang `+174°`. Script mới với cách tính chuẩn và magnitude cao hơn cho kết quả ổn định. |

**Trích dẫn code tính góc từ báo cáo cũ [`260620/Readme.md`](../260620/Readme.md#L179-L196):**

Script cũ [`evaluate_group_vectors.py`](../260620/tools/evaluate_group_vectors.py) tính vector tổng của group bằng cách:

```python
# Báo cáo cũ 260620 – logic cộng dồn Vector (dòng 186–196)
for _, row in group_df.iterrows():
    mag = row['vector_magnitude']      # ← magnitude của anchor trung tâm (top-1)
    ang_deg = row['estimated_angle']   # ← góc của anchor trung tâm

    ang_rad = math.radians(ang_deg)
    sum_x += mag * math.cos(ang_rad)   # biến đổi ngược từ (mag, angle) → (Vx, Vy)
    sum_y += mag * math.sin(ang_rad)

group_mag = math.hypot(sum_x, sum_y)
group_ang = math.degrees(math.atan2(sum_y, sum_x))
```

> **Tổng kết vấn đề:** Script cũ dùng `estimated_angle` đã tính sẵn của **từng anchor riêng lẻ** (tức là `atan2` của vector con) để biến đổi ngược thành `(Vx, Vy)` rồi cộng dồn. Tuy nhiên, `estimated_angle` của anchor top-1 trong Group 6 cũ là **`-61.08°`** – khi toàn bộ anchors trong group dùng `mag × cos(angle_mỗi_anchor)`, nếu các anchor đều đang chỉ về `~-61°` thì kết quả vector tổng đương nhiên ra `-60.37°`. Script mới tính trực tiếp `sum_x = Σ score_i × cos(θ_i)` từ **24 class scores thô** của từng anchor, tránh hoàn toàn sai số tích lũy qua hai lần atan2.

> **Lưu ý:** Không có lỗi về class mapping. `Leanbot_p195` parse thành `+195°`, về lượng giác `cos(195°) = cos(-165°)` – vẫn chính xác.

---

### 4. Chuẩn hóa chạy 1 lần `analyze_image.py`

**Link code:** [`analyze_image.py`](tools/analyze_image.py)

**Lệnh chạy:**
```bash
python tools/analyze_image.py \
    --input 24class_test_images/002.jpg \
    --output runs/002 \
    --model tools/best_24Class_Soft_Angular_BCE.pt \
    --iou 0.5 \
    --topk 200
```

**Quy trình pipeline tự động:**
```
Đọc ảnh
- Center Crop vuông (giữ nguyên tỉ lệ X/Y)
- Resize 640×640
- YOLOv8 inference (lấy top-200 raw anchors trước NMS)
- Tính vector góc từ 24 class score (cos/sin weighted sum)
- Tính vector_magnitude + estimated_angle cho từng anchor
- Gom các anchor overlap thành group (IoU greedy, ngưỡng 0.5)
- Tính bounding box đại diện (weighted average theo magnitude)
- Tính vector tổng của từng group
- Sắp xếp group theo vector_magnitude giảm dần
- Xuất CSV (raw, grouped, summary, debug)
- Vẽ ảnh detected_groups.jpg

```

**Output mỗi lần chạy:**
```
runs/image_name/
├── processed_640x640.jpg   ← ảnh sau crop + resize
├── raw_anchors.csv          ← 200 anchor thô với vector, angle, 24 class score
├── grouped_anchors.csv      ← anchor đã gán group_id + group_bbox
├── vector_summary.csv       ← tổng hợp mỗi group (sorted by magnitude)
├── detected_groups.jpg      ← ảnh vẽ bbox đại diện + group ID + góc + magnitude
├── debug_groups.csv         ← chi tiết từng anchor: vx, vy, top_class, contribution
└── analysis.log             ← tham số, số anchor, số group, toàn bộ log
```

---

### 5. Kiểm thử trên 4 ảnh ( 1 ảnh ban đầu và 3 ảnh mới, các góc khác nhau)

> **Chú thích ảnh visualization `detected_groups.jpg`:**
> - **BBox** (bố viện các màu): vùng bao quanh từng Leanbot, tính theo **weighted average** của tất cả anchors trong group (anchor có `vector_magnitude` lớn hơn có ảnh hưởng nhiều hơn vị trí bbox).
> - **G{id}**: Group ID – số thứ tự của nhóm anchor sau khi gom.
> - **{angle}deg**: Góc dự đoán của vector tổng toàn group (tính bằng `atan2(sum_vy, sum_vx)`).
> - **m={mag}**: `vector_magnitude` của group – độ lớn tổng hợp, thể hiện mức độ tự tin: giá trị cao → nhiều anchor cùng dự đoán nhất quán về một hướng.
> - **Màu bbox**: 8 màu xoay vòng theo group_id, giúp phân biệt từng đối tượng.

#### 5.1. `002.jpg` – Leanbot góc khoảng -165°

**Link code:** [`tools/analyze_image.py`](tools/analyze_image.py) | **Output:** [`runs/002/`](runs/002/) | **CSV:** [`vector_summary.csv`](runs/002/vector_summary.csv)

**Lệnh chạy:**
```bash
python tools/analyze_image.py --input 24class_test_images/002.jpg --output runs/002
```

| group_id | Số Anchor | vector_magnitude | x_center | y_center | width | height | angle |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 2 | 22 | **15.34** | 569.02 | 328.25 | 101.05 | 60.62 | **`-169.34°`** |
| 3 | 18 | **14.09** | 389.13 | 321.32 | 94.60 | 61.04 | **`-171.94°`** |
| 7 | 18 | **13.90** | 215.25 | 344.95 | 97.66 | 64.57 | **`-173.33°`** |
| 8 | 21 | **12.66** | 183.93 | 506.07 | 113.83 | 82.18 | **`-170.27°`** |
| 5 | 25 | **12.15** | 407.55 | 498.46 | 123.35 | 82.72 | **`-173.81°`** |
| 1 | 24 | **11.91** | 531.60 | 211.09 | 87.88 | 51.38 | **`-171.14°`** |
| 6 | 18 | **11.85** | 224.42 | 220.81 | 79.93 | 49.60 | **`-176.04°`** |
| 9 | 19 | **9.74** | 611.56 | 493.01 | 56.81 | 95.68 | **`-166.83°`** |
| 4 | 24 | **8.93** | 381.71 | 215.92 | 80.71 | 49.45 | **`-174.33°`** |

![`002.jpg` – BBox đại diện của 12 group | nhãn: G{id} {angle}deg m={magnitude}](runs/002/detected_groups.jpg)

> Nhận xét: 9 group chính đều hội tụ về vùng **`-166°` đến `-176°`**. Group có magnitude cao nhất là **15.34**, model rất tự tin khi nhiều anchor cùng dự đoán về hướng đó.

---

#### 5.2. `000021.jpg` – Leanbot góc khoảng 0° đến +15°

**Link code:** [`tools/analyze_image.py`](tools/analyze_image.py) | **Output:** [`runs/000021/`](runs/000021/) | **CSV:** [`vector_summary.csv`](runs/000021/vector_summary.csv)

| group_id | Số Anchor | vector_magnitude | x_center | y_center | width | height | angle |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 3 | 23 | **14.58** | 370.86 | 257.90 | 85.48 | 54.40 | **`+13.58°`** |
| 4 | 23 | **13.45** | 193.52 | 380.92 | 102.52 | 69.74 | **`+11.88°`** |
| 5 | 19 | **12.93** | 576.09 | 384.13 | 108.93 | 71.52 | **`+5.50°`** |
| 7 | 23 | **11.32** | 377.51 | 387.04 | 103.56 | 69.67 | **`+14.35°`** |
| 6 | 23 | **11.08** | 214.13 | 256.65 | 86.72 | 53.92 | **`+14.02°`** |
| 1 | 21 | **10.96** | 230.10 | 162.28 | 74.76 | 46.98 | **`+8.10°`** |
| 2 | 18 | **10.07** | 361.58 | 165.45 | 74.21 | 46.27 | **`+4.10°`** |
| 9 | 19 | **9.05** | 534.52 | 251.12 | 90.27 | 58.33 | **`+8.53°`** |
| 8 | 19 | **8.65** | 506.36 | 156.68 | 79.65 | 49.09 | **`+9.33°`** |

![`000021.jpg` – BBox đại diện của 12 group | nhãn: G{id} {angle}deg m={magnitude}](runs/000021/detected_groups.jpg)

> Nhận xét: 9 group chính đều hội tụ về vùng **`+4°` đến `+14°`**, phù hợp với góc gần 0° (hoặc ~+15°) của Leanbot. Top Magnitude = **14.58** (Group 3).

---

#### 5.3. `000034.jpg` – Leanbot góc khoảng -45° đến -60°

**Link code:** [`tools/analyze_image.py`](tools/analyze_image.py) | **Output:** [`runs/000034/`](runs/000034/) | **CSV:** [`vector_summary.csv`](runs/000034/vector_summary.csv)

| group_id | Số Anchor | vector_magnitude | x_center | y_center | width | height | angle |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | 14 | **22.73** | 382.29 | 213.32 | 72.79 | 54.93 | **`-49.22°`** |
| 3 | 19 | **21.57** | 235.25 | 214.65 | 66.16 | 58.61 | **`-54.56°`** |
| 8 | 20 | **20.09** | 394.58 | 326.04 | 84.42 | 68.29 | **`-50.82°`** |
| 2 | 26 | **19.15** | 407.03 | 489.61 | 105.16 | 105.31 | **`-54.76°`** |
| 5 | 20 | **16.97** | 539.16 | 208.73 | 76.84 | 52.80 | **`-51.02°`** |
| 6 | 21 | **16.97** | 570.55 | 317.81 | 100.24 | 69.76 | **`-47.69°`** |
| 9 | 17 | **16.14** | 214.21 | 323.99 | 73.04 | 69.10 | **`-59.37°`** |
| 7 | 25 | **14.22** | 184.26 | 474.73 | 83.56 | 97.90 | **`-66.64°`** |
| 4 | 29 | **12.99** | 608.34 | 493.33 | 63.56 | 107.27 | **`-50.59°`** |

![`000034.jpg` – BBox đại diện của 13 group | nhãn: G{id} {angle}deg m={magnitude}](runs/000034/detected_groups.jpg)

> Nhận xét: 9 group chính đều hội tụ về vùng **`-47°` đến `-67°`**. Magnitude cao nhất trong cả 4 ảnh test (**22.73**), thể hiện model rất tự tin với góc ~-50°.

---

#### 5.4. `000070.jpg` – Leanbot góc khoảng -10° đến -15°

**Link code:** [`tools/analyze_image.py`](tools/analyze_image.py) | **Output:** [`runs/000070/`](runs/000070/) | **CSV:** [`vector_summary.csv`](runs/000070/vector_summary.csv)

| group_id | Số Anchor | vector_magnitude | x_center | y_center | width | height | angle |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 3 | 20 | **15.08** | 484.42 | 187.76 | 79.12 | 49.12 | **`-11.71°`** |
| 1 | 19 | **14.94** | 175.22 | 295.54 | 92.50 | 59.86 | **`-16.14°`** |
| 6 | 17 | **14.77** | 352.34 | 294.25 | 90.09 | 58.82 | **`-16.58°`** |
| 2 | 21 | **12.93** | 347.61 | 439.89 | 108.78 | 75.10 | **`-16.08°`** |
| 8 | 20 | **12.78** | 510.02 | 293.08 | 92.54 | 59.38 | **`-10.85°`** |
| 7 | 19 | **12.56** | 126.98 | 435.49 | 110.48 | 74.30 | **`-12.89°`** |
| 4 | 21 | **11.92** | 337.75 | 192.24 | 77.53 | 48.20 | **`-15.35°`** |
| 5 | 18 | **11.74** | 200.75 | 192.48 | 79.12 | 49.27 | **`-9.62°`** |
| 9 | 25 | **9.79** | 541.26 | 438.52 | 114.43 | 77.21 | **`-15.56°`** |

![`000070.jpg` – BBox đại diện của 12 group | nhãn: G{id} {angle}deg m={magnitude}](runs/000070/detected_groups.jpg)

> Nhận xét: 9 group chính đều hội tụ về vùng **`-9°` đến `-16°`**. Model nhận diện nhất quán góc xoay nhỏ âm của Leanbot. Top Magnitude = **15.08** (Group 3).

---

#### 5.5. Tổng hợp 4 ảnh

| Ảnh | Số group | Top Magnitude | Top Angle | Phạm vi 9 group chính | Nhận xét |
|:---|:---:|:---:|:---:|:---:|:---|
| [`002.jpg`](runs/002/vector_summary.csv) | 12 | **15.34** | **-169.34°** | `-166°` → `-176°` | Góc ~-165°, nhất quán |
| [`000021.jpg`](runs/000021/vector_summary.csv) | 12 | **14.58** | **+13.58°** | `+4°` → `+14°` | Góc ~0° đến +15°, nhất quán |
| [`000034.jpg`](runs/000034/vector_summary.csv) | 13 | **22.73** | **-49.22°** | `-47°` → `-67°` | Góc ~-50°, tự tin cao nhất |
| [`000070.jpg`](runs/000070/vector_summary.csv) | 12 | **15.08** | **-11.71°** | `-9°` → `-16°` | Góc ~-10°, nhất quán |

---


### 6. Tóm tắt các file đã tạo/sửa

| File | Loại | Nội dung thay đổi |
|:---|:---:|:---|
| [`tools/group_anchors.py`](tools/group_anchors.py) | Sửa | Thêm `compute_weighted_bbox()` và các cột `group_x/y/w/h` |
| [`tools/evaluate_group_vectors.py`](tools/evaluate_group_vectors.py) | Sửa | Sort by magnitude, thêm bbox columns, image_filename, xuất CSV |
| [`tools/analyze_image.py`](tools/analyze_image.py) | **Tạo mới** | Pipeline chạy 1 lần từ JPG → toàn bộ output |
---

## B. Khó khăn

- Như đã báo cáo thì hiện tại em đã thực hiện theo 2 cách tính góc cho vector tổng :
    - Script cũ (260620): tính `estimated_angle` của **từng anchor riêng lẻ** qua `atan2` trước, rồi biến đổi ngược về `(Vx, Vy)` để cộng dồn cấp group --> áp dụng `atan2` **hai lần**, khiến thông tin phân phối gốc của 24 class scores bị nén và mất đi, dẫn đến sai góc. 
    - Script mới (260701): lưu `(vector_x, vector_y)` thô của từng anchor, cộng dồn trực tiếp và chỉ dùng `atan2` **một lần duy nhất** ở cấp group --> cho kết quả tốt hơn so với script cũ.

  | Tiêu chí | Script cũ (260620) | Script mới (260701) |
  |:---|:---:|:---:|
  | Số lần `atan2` | **2 lần** | **1 lần** |
  | Input cộng dồn group | `(mag, estimated_angle)` đã nén | `(vector_x, vector_y)` thô |
  | Class dùng để tính góc | Top-K (2 class) | Đủ 24 class |
  | Kết quả Group 6 | `-60.37°`  | `-166.83°`  |
  | Kết quả Group 9 | `+174.47°`  | `-176.04°`  |



## C. Công việc tiếp theo
- Em xin phép nhận hướng đi tiếp theo từ Thầy ạ.
