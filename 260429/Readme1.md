# Báo cáo công việc ngày 29/04/2026.

## A. Công việc đã làm.
- Tìm hiểu ```cv2.groupRectangles()```
- Báo cáo chi tiết toàn bộ code tìm BBox hiện tại.

### 1. Hàm ```cv2.groupRectangles()```.
### 2. Code tìm BBox hiện tại. 

- Toàn bộ logic tìm BBox nằm trong hàm `detect_leanbot()` tại file `tools/auto_label_core.py` (dòng 535–664).
Hàm này được gọi từ `process_auto_label.py` (dòng 155–161) cho từng ảnh raw trong session.

Sơ đồ tổng quát: 
```
Ảnh raw + Ảnh nền (background)
        │
        ▼
 ┌──────────────────────────────┐
 │ Bước 1: Tính sai khác ảnh    │  ──▶  diff_mask (ảnh nhị phân)
 │ (Image Differencing)         │
 └──────────────────────────────┘
        │
        ▼
 ┌──────────────────────────────┐
 │ Bước 2: Xử lý hình thái      │  ──▶  diff_mask đã lọc nhiễu
 │ (Opening → Closing)          │
 └──────────────────────────────┘
        │
        ▼
 ┌──────────────────────────────┐
 │ Bước 3: Erode board mask     │  ──▶  diff_mask chỉ giữ vùng trong bàn
 └──────────────────────────────┘
        │
        ▼
 ┌──────────────────────────────┐
 │ Bước 4: Tìm Contour          │  ──▶  contours
 └──────────────────────────────┘
        │
        ▼
 ┌──────────────────────────────┐
 │ Bước 5: Lọc theo diện tích   │  ──▶  bboxes [ (x,y,w,h), ... ]
 │ và kích thước                │
 └──────────────────────────────┘
        │
        ▼
 ┌──────────────────────────────┐
 │ Bước 6: Merge BBoxes         │  ──▶  merged_bboxes
 └──────────────────────────────┘
        │
        ▼
 ┌──────────────────────────────┐
 │ Bước 7: Lưu kết quả          │  ──▶  file .txt (YOLO format)
 │ (Label + Debug images)       │       + file .jpg (debug)
 └──────────────────────────────┘
```

---

#### Bước 1: Tính sai khác ảnh (Image Differencing)

- **File:** `auto_label_core.py` dòng 592–627, sử dụng các hàm từ `abstract_hsv.py`.
- **Mục đích:** So sánh ảnh đã căn chỉnh (aligned) với ảnh nền (background) để tìm ra vùng có sự khác biệt — chính là vị trí Leanbot.
- **Output:** `diff_mask` — ảnh nhị phân.
- Hiện tại để tiện thử nghiệm em tạo 3 chế độ (mode) được chọn qua tham số `--diff_mode`:

**Mode 1 — GRAY (Baseline):** So sánh trên ảnh xám.
```python
# auto_label_core.py dòng 592-600
if diff_mode == "1":
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    bg_p = clahe.apply(aligner.template_gray)
    bg_p = cv2.GaussianBlur(bg_p, (blur_ksize, blur_ksize), 0)

    aligned_p = clahe.apply(aligned_gray_masked)
    aligned_p = cv2.GaussianBlur(aligned_p, (blur_ksize, blur_ksize), 0)

    _, diff_mask, _, _ = aligner.compute_diff(bg_p, aligned_p, threshold=threshold)
```
- CLAHE cân bằng sáng cục bộ -> GaussianBlur làm mịn -> Tính `absdiff` và ngưỡng hóa nhị phân.

**Mode 2 — MIX (Hybrid Gray + Hue):** Kết hợp sự khác biệt về độ sáng (Gray) và màu sắc (Hue).
```python
# auto_label_core.py dòng 601-611
# Gọi hàm compute_gray_hue_diff() từ abstract_hsv.py
elif diff_mode == "2":
    res = compute_gray_hue_diff(
        bg_bgr,
        aligned_color_masked,
        w_gray=w_gray,       # Trọng số cho kênh Gray
        w_hue=w_hue,         # Trọng số cho kênh Hue
        threshold=threshold,
        blur_ksize=blur_ksize,
        use_clahe=True,
    )
    diff_mask = res["mask"]
```
- Hàm `compute_gray_hue_diff()` (file `abstract_hsv.py` dòng 88-139):
  - Tính `dGray = absdiff(gray1, gray2)` — sai khác độ sáng.
  - Tính `dH` — sai khác Hue theo vòng tròn (circular difference, xử lý trường hợp 0° gần 180°).
  - Kết hợp: `score = max(w_gray * dGray, w_hue * dH)`.
  - Ngưỡng hóa nhị phân: `threshold(score, threshold) → mask`.

**Mode 3 — HUE (HSV Only):** So sánh đầy đủ trên không gian HSV.
```python
# auto_label_core.py dòng 612-624
# Gọi hàm compute_hsv_diff() từ abstract_hsv.py
elif diff_mode == "3":
    res = compute_hsv_diff(
        bg_bgr,
        aligned_color_masked,
        w_h=w_h,             # Trọng số cho Hue
        w_s=w_s,             # Trọng số cho Saturation
        w_v=w_v,             # Trọng số cho Value (độ sáng)
        threshold=threshold,
        min_saturation=20,
        blur_ksize=blur_ksize,
        use_clahe=True,
    )
    diff_mask = res["mask"]
```
- Hàm `compute_hsv_diff()` (file `abstract_hsv.py` dòng 23-86):
  - Chuyển cả 2 ảnh sang HSV, tách kênh H, S, V.
  - Tính `dH` (circular), `dS`, `dV` riêng biệt.
  - Kết hợp: `score = (w_h * dH + w_s * dS + w_v * dV) / (w_h + w_s + w_v)`.
  - Ngưỡng hóa nhị phân -> `mask`.


---

#### Bước 3: Erode Board Mask và loại nhiễu mép bàn

- **File:** `auto_label_core.py` dòng 642–643.
- **Mục đích:** Thu hẹp vùng ROI (mặt bàn) vào bên trong 15 pixel để loại bỏ nhiễu xuất hiện ở rìa viền bàn do Alignment không hoàn hảo (ảnh sau Alignment có thể hơi lệch 1 chút so với ảnh Background).
```python
# auto_label_core.py dòng 642-643
eroded_board_mask = cv2.erode(board_mask, np.ones((15, 15), np.uint8))
diff_mask = cv2.bitwise_and(diff_mask, diff_mask, mask=eroded_board_mask)
```

- `cv2.erode()` — co vùng trắng của mask mặt bàn vào 15px mỗi cạnh.
- `bitwise_and` — chỉ giữ lại các vùng trắng nằm bên trong vùng bàn đã thu hẹp, xóa sạch mọi thứ ngoài Roi Masked.

---

#### Bước 4: Tìm Contour

- **File:** `auto_label_core.py` dòng 645.
- **Mục đích:** Tìm các đường bao (contour) của các vùng trắng trên `diff_mask` — mỗi contour tương ứng với một vật thể (Leanbot) được phát hiện.

```python
# auto_label_core.py dòng 645
contours, _ = cv2.findContours(diff_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
```

- `cv2.findContours()` — tìm tất cả đường bao trên ảnh nhị phân.
- `cv2.RETR_EXTERNAL` — chỉ lấy đường bao ngoài cùng, bỏ qua các contour con bên trong.
- `cv2.CHAIN_APPROX_SIMPLE` — nén contour, chỉ giữ lại các điểm góc (tiết kiệm bộ nhớ).

---

#### Bước 5: Lọc Contour theo diện tích và kích thước

- **File:** `auto_label_core.py` dòng 650–656.
- **Mục đích:** Lọc bỏ các contour quá nhỏ (nhiễu) hoặc quá lớn (nền bị lỗi), chỉ giữ lại các contour có kích thước phù hợp với Leanbot.

```python
# auto_label_core.py dòng 650-656
bboxes = []
for contour in contours:
    area = cv2.contourArea(contour)
    if min_area < area < max_area:                         # Lọc theo diện tích
        x, y, w, h = cv2.boundingRect(contour)
        if (min_width < w < max_width) and (min_height < h < max_height):  # Lọc theo kích thước
            bboxes.append((x, y, w, h))
```

| Tham số | Giá trị mặc định | Ý nghĩa |
|:---|:---:|:---|
| `min_area` | 0 | Diện tích contour tối thiểu (pixel²) |
| `max_area` | 500000 | Diện tích contour tối đa (pixel²) |
| `min_width` | 0 | Chiều rộng BBox tối thiểu (pixel) |
| `max_width` | 2000 | Chiều rộng BBox tối đa (pixel) |
| `min_height` | 0 | Chiều cao BBox tối thiểu (pixel) |
| `max_height` | 2000 | Chiều cao BBox tối đa (pixel) |

- `cv2.contourArea()` — tính diện tích của contour.
- `cv2.boundingRect()` — tính hình chữ nhật bao quanh nhỏ nhất dạng `(x, y, w, h)`.
- **Output:** danh sách `bboxes` chứa các tuple `(x, y, w, h)` đã qua lọc.

---

#### Bước 6: Merge BBoxes (Gộp các BBox lân cận)

- **File:** `auto_label_core.py` dòng 658–662, sử dụng hàm `merge_bboxes()` (dòng 424–473).
- **Mục đích:** Gộp các BBox nằm gần nhau thành một BBox lớn duy nhất. Do Leanbot có thể bị tách thành nhiều contour riêng biệt.
- Hiện tại có 2 phương pháp merge:

```python
# auto_label_core.py dòng 658-662
if use_overlap_merge:
    # Phương pháp 2: Gộp theo diện tích chồng lấn
    merged_bboxes = merge_bboxes_overlap(bboxes, overlap_ratio=overlap_ratio)
else:
    # Phương pháp 1 : Gộp theo khoảng cách
    merged_bboxes = merge_bboxes(bboxes, dist_threshold=merge_dist)
```

**Hàm `merge_bboxes()` — Distance-based:**
```python
# auto_label_core.py dòng 424-473
def merge_bboxes(bboxes, dist_threshold=10):
    if not bboxes:
        return []

    curr_bboxes = [list(b) for b in bboxes]
    changed = True
    while changed:                          # Lặp cho đến khi không còn cặp nào gộp được
        changed = False
        new_bboxes = []
        visited = [False] * len(curr_bboxes)

        for i in range(len(curr_bboxes)):
            if visited[i]:
                continue
            group = [curr_bboxes[i]]
            visited[i] = True

            for j in range(i + 1, len(curr_bboxes)):
                if visited[j]:
                    continue
                b1 = curr_bboxes[i]
                b2 = curr_bboxes[j]
                # Kiểm tra 2 box có gần nhau (trong phạm vi dist_threshold) không
                x_overlap = not (
                    b1[0] + b1[2] + dist_threshold < b2[0]
                    or b2[0] + b2[2] + dist_threshold < b1[0]
                )
                y_overlap = not (
                    b1[1] + b1[3] + dist_threshold < b2[1]
                    or b2[1] + b2[3] + dist_threshold < b1[1]
                )
                if x_overlap and y_overlap:
                    group.append(curr_bboxes[j])
                    visited[j] = True
                    changed = True

            if len(group) == 1:
                new_bboxes.append(group[0])
            else:
                # Tính BBox bao quanh toàn bộ nhóm
                x_min = min(b[0] for b in group)
                y_min = min(b[1] for b in group)
                x_max = max(b[0] + b[2] for b in group)
                y_max = max(b[1] + b[3] for b in group)
                new_bboxes.append([x_min, y_min, x_max - x_min, y_max - y_min])
        curr_bboxes = new_bboxes

    return [tuple(b) for b in curr_bboxes]
```

- **Thuật toán:** Duyệt tất cả các cặp BBox, nếu khoảng cách giữa hai box ≤ `dist_threshold` pixel (cả 2 chiều X và Y), thì gộp chúng thành 1 box bao quanh. Lặp lại cho đến khi không còn cặp nào gộp được nữa.
- **Tham số:** `--merge_dist` (mặc định = 10 pixel).

**Hàm `merge_bboxes_overlap()` — Area-based Overlap:**
```python
# auto_label_core.py dòng 476-532
def merge_bboxes_overlap(bboxes, overlap_ratio=0.25):
    if not bboxes:
        return []

    curr_bboxes = [list(b) for b in bboxes]
    changed = True
    while changed:
        changed = False
        new_bboxes = []
        visited = [False] * len(curr_bboxes)

        for i in range(len(curr_bboxes)):
            if visited[i]:
                continue
            group = [curr_bboxes[i]]
            visited[i] = True

            for j in range(i + 1, len(curr_bboxes)):
                if visited[j]:
                    continue
                b1 = curr_bboxes[i]  # [x, y, w, h]
                b2 = curr_bboxes[j]

                # Chuyển sang [x1, y1, x2, y2]
                r1 = [b1[0], b1[1], b1[0] + b1[2], b1[1] + b1[3]]
                r2 = [b2[0], b2[1], b2[0] + b2[2], b2[1] + b2[3]]

                # Kiểm tra có chồng lấn (AABB overlap) không
                if not (r2[0] > r1[2] or r2[2] < r1[0] or r2[1] > r1[3] or r2[3] < r1[1]):
                    # Tính diện tích phần giao nhau
                    inter_x = min(r1[2], r2[2]) - max(r1[0], r2[0])
                    inter_y = min(r1[3], r2[3]) - max(r1[1], r2[1])
                    inter_area = inter_x * inter_y

                    area1 = b1[2] * b1[3]
                    area2 = b2[2] * b2[3]

                    # Gộp nếu phần giao >= overlap_ratio so với diện tích một trong hai box
                    if (inter_area >= overlap_ratio * area1) or (inter_area >= overlap_ratio * area2):
                        group.append(curr_bboxes[j])
                        visited[j] = True
                        changed = True

            if len(group) == 1:
                new_bboxes.append(group[0])
            else:
                x_min = min(b[0] for b in group)
                y_min = min(b[1] for b in group)
                x_max = max(b[0] + b[2] for b in group)
                y_max = max(b[1] + b[3] for b in group)
                new_bboxes.append([x_min, y_min, x_max - x_min, y_max - y_min])
        curr_bboxes = new_bboxes

    return [tuple(b) for b in curr_bboxes]
```

- **Thuật toán:** Duyệt tất cả các cặp BBox, nếu hai box có phần chồng lấn và diện tích giao nhau ≥ `overlap_ratio` (tỉ lệ %) so với diện tích của một trong hai box, thì gộp lại. Lặp cho đến khi không còn cặp nào gộp được.
- **Tham số:** `--overlap_ratio` (mặc định = 0.1), bật bằng flag `--use_overlap_merge`.
- **So sánh với Distance-based:** Phương pháp này chỉ gộp khi hai box thực sự đè lên nhau, không gộp các box nằm gần nhau nhưng không chồng lấn → có thể để lọt các mảnh rời của cùng một Leanbot.

---

#### Bước 7: Lưu kết quả (Label YOLO + Debug images)

- **File:** `auto_label_core.py` dòng 667–703, được gọi từ `process_auto_label.py` dòng 171–178.
- **Mục đích:** Chuyển đổi BBox từ pixel sang định dạng YOLO chuẩn hóa và lưu ra file.

**Hàm `save_yolo_label()` — Chuyển đổi sang YOLO format:**
```python
# auto_label_core.py dòng 667-674
def save_yolo_label(bboxes, img_width, img_height, output_path, class_id=0):
    with open(output_path, "w", encoding="utf-8") as file:
        for x, y, w, h in bboxes:
            x_center = (x + w / 2) / img_width    # Tâm X chuẩn hóa (0-1)
            y_center = (y + h / 2) / img_height   # Tâm Y chuẩn hóa (0-1)
            w_norm = w / img_width                 # Chiều rộng chuẩn hóa (0-1)
            h_norm = h / img_height                # Chiều cao chuẩn hóa (0-1)
            file.write(f"{class_id} {x_center:.6f} {y_center:.6f} {w_norm:.6f} {h_norm:.6f}\n")
```
- Mỗi dòng trong file `.txt` có dạng: `<class_id> <x_center> <y_center> <width> <height>` (chuẩn hóa về 0–1).

**Hàm `save_detection_outputs()` — Lưu toàn bộ output:**
```python
# auto_label_core.py dòng 677-703
def save_detection_outputs(output_paths, base_name, aligned_img, diff_mask, bboxes, class_id=0):
    aligned_path = output_paths["aligned_dir"] / f"{base_name}.jpg"   # Ảnh gốc đã căn chỉnh
    label_path   = output_paths["labels_dir"]  / f"{base_name}.txt"   # Label YOLO
    mask_path    = output_paths["debug_dir"]   / f"{base_name}_mask.jpg"  # Debug: mask + BBox
    bbox_path    = output_paths["debug_dir"]   / f"{base_name}_bbox.jpg"  # Debug: RGB + BBox

    cv2.imwrite(str(aligned_path), aligned_img)

    # Vẽ BBox lên mask (debug)
    if diff_mask is not None:
        mask_bgr = cv2.cvtColor(diff_mask, cv2.COLOR_GRAY2BGR)
        for x, y, w, h in bboxes:
            cv2.rectangle(mask_bgr, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.imwrite(str(mask_path), mask_bgr)

    # Vẽ BBox lên ảnh RGB (debug)
    bbox_img = aligned_img.copy()
    for x, y, w, h in bboxes:
        cv2.rectangle(bbox_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(bbox_img, f"cls:{class_id}", (x, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    cv2.imwrite(str(bbox_path), bbox_img)

    # Lưu label YOLO
    img_height, img_width = aligned_img.shape[:2]
    save_yolo_label(bboxes, img_width, img_height, str(label_path), class_id=class_id)
```

**Cấu trúc output cho mỗi session:**
```
tool1_output/session_X/
├── aligned_images/        ← Ảnh đã căn chỉnh (dùng để train)
│   ├── raw_000.jpg
│   └── raw_001.jpg
├── labels/                ← Label YOLO tương ứng (dùng để train)
│   ├── raw_000.txt
│   └── raw_001.txt
├── debug/                 ← Ảnh debug kiểm tra kết quả
│   ├── raw_000_mask.jpg   ← Ảnh mask nhị phân + BBox xanh
│   ├── raw_000_bbox.jpg   ← Ảnh RGB + BBox xanh + class_id
│   └── ...
├── config.npy             ← Cấu hình xử lý (ROI, tham số, ...)
└── roi_preview.jpg        ← Ảnh preview vùng ROI đã chọn
```

## B. Khó khăn
- Theo tìm hiểu và thực nghiệm em thấy dùng ```cv2.groupRectangles``` chưa phải là tối ưu nhất ạ.
- Em đã thử nghiệm và đề xuất phương pháp sau ạ :
    - Sử dụng phép biến đổi hình thái ảnh Morphological ( Opening + Closing)
    - Gộp BBox xử dụng Distace base
    - Kết quả thử nghiệm và so sánh với Overlap base cụ thể chi tiết trong báo cáo sau :
        - [link](akshdsajfla)
## C. Công việc tiếp theo
