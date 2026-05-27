# Báo cáo công việc ngày 26/05/2026

## A. Công việc đã làm 
- Báo cáo lại quá trình lấy all classes's confidences
### 1. Quá Trình Lấy Confidenc Của Tất Cả Classes

**`check_confidence.py`** là một công cụ chuyên dụng để trích xuất và phân tích **confidence scores của tất cả các classes** cho mỗi object được phát hiện trong ảnh. Điều này khác với inference thông thường (chỉ lấy class tốt nhất), vì nó cung cấp **toàn bộ phân phối xác suất** trên tất cả các classes.

### Mục đích sử dụng
- Lấy confidence scores cho **tất cả nc classes** của mỗi detection (nc = 24 trong bài toán này)
- Xác định class tốt nhất + confidence của nó
- Có thể theo dõi các classes thứ cấp (secondary predictions)
- Lưu kết quả chi tiết dưới dạng ảnh + text file debug

---

## Các bước xử lí

```
Input Image
    ↓
[Preprocessing] - Chuẩn hóa kích thước + normalize
    ↓
[YOLO Model Forward Pass] - Raw predictions từ neural network
    ↓
[Raw Output Processing] - Lấy class scores từ raw predictions
    ↓
[NMS - Non-Maximum Suppression] - Loại bỏ box trùng lặp
    ↓
[Matching Raw → NMS Boxes] - Ánh xạ từng box sau NMS về raw predictions
    ↓
[Extract All Class Scores] - Lấy confidence của nc classes cho mỗi box
    ↓
[Top 200 Anchors Extraction] - Lấy top 200 proposals theo max confidence
    ↓
[Visualization & Logging] - Vẽ bbox + lưu debug info + export CSV
    ↓
Output: Ảnh debug + text file chi tiết + file CSV top 200 anchors (với nc class scores)
```

---

## Chi Tiết Từng Bước

**Bước 1: Preprocessing ảnh**

Bước này chuẩn hóa ảnh đầu vào để phù hợp với input của mô hình YOLO:

- Sử dụng LetterBox để đưa ảnh về kích thước chuẩn 640x640 với padding (giữ nguyên tỷ lệ khung hình)
- Chuyển đổi từ BGR sang RGB
- Chuyển từ định dạng HWC (Height, Width, Channel) sang CHW (Channel, Height, Width)
- Normalize giá trị pixel bằng cách chia cho 255
- Chuyển sang tensor PyTorch và đưa lên GPU
- Thêm batch dimension

```python
def preprocess_image(img_bgr, imgsz=640):
    img = LetterBox(new_shape=(imgsz, imgsz), auto=False, stride=32)(image=img_bgr)
    img = img[:, :, ::-1].transpose(2, 0, 1)  # BGR→RGB, HWC→CHW
    img_tensor = torch.from_numpy(np.ascontiguousarray(img)).to(device).float() / 255.0
    return img_tensor.unsqueeze(0)
```

|Input|Output|
|---|---|
| Ảnh BGR với kích thước bất kỳ (H, W, 3) | Tensor PyTorch [1, 3, 640, 640] trên GPU |
| **Ý nghĩa** | Input tensor đã chuẩn hóa sẵn sàng cho forward pass |

---

**Bước 2: Forward Pass & Raw Predictions**

Bước này chạy ảnh đã chuẩn hóa qua mô hình YOLO để lấy raw predictions:

- Vô hiệu hóa tính gradient (torch.no_grad()) để tiết kiệm bộ nhớ
- Chạy forward pass qua mô hình: `model.model(img_tensor)`
- Reshape raw predictions từ định dạng mô hình sang định dạng tiêu chuẩn

```python
with torch.no_grad():
    raw_pred = model.model(img_tensor)
    raw_pred = normalize_raw_pred_shape(raw_pred, nc)
```

|Input|Output|
|---|---|
| Tensor [1, 3, 640, 640] từ bước 1 | Tensor [1, 25200, 12] (1 batch, 25200 proposals, 4+8 channels) |
| **Ý nghĩa** | Raw predictions chứa tất cả candidate boxes + class scores cho mỗi box |

**Giải thích các dimension:**
- `[1]` = batch size
- `25200` = số lượng candidate boxes từ YOLO architecture (grid cells × anchors)
- `[4:4+nc]` = tọa độ bbox (x, y, w, h) - tọa độ tương đối so với ô grid
- `[4+nc:4+2*nc]` = confidence scores của nc classes (objectness × class probability), với nc = 24

---

**Bước 3: Tách Tọa Độ và Class Scores từ Raw Predictions**

Bước này tách riêng thông tin tọa độ boxes và confidence scores để xử lý:

- Tách 4 channels đầu tiên (tọa độ bbox)
- Tách 8 channels còn lại (class scores)
- Transpose để dễ iterating qua từng proposal

```python
raw_boxes_xywh = raw_pred[0, :4, :].T           # Shape: [num_proposals, 4]
raw_class_scores = raw_pred[0, 4:4+nc, :].T    # Shape: [num_proposals, 8]
```

|Input|Output 1|Output 2|Ý nghĩa|
|---|---|---|---|
| Tensor raw_pred [1, 25200, 12] | raw_boxes_xywh [25200, 4] - tọa độ tất cả proposals | raw_class_scores [25200, nc] - class scores tất cả proposals (nc = 24) | Tách biệt dữ liệu tọa độ và class scores để xử lý riêng |

**Giải thích chi tiết:**
- `raw_boxes_xywh[i]` chứa 4 giá trị: [x_center, y_center, width, height] của proposal thứ i
- `raw_class_scores[i]` chứa nc giá trị (24 trong bài toán này): confidence scores của nc classes cho proposal thứ i
- Các scores này từ 0 đến 1 (đã qua sigmoid function từ neural network)

---

**Bước 4: Áp Dụng NMS (Non-Maximum Suppression)**

NMS loại bỏ các bounding boxes có độ tin cậy thấp và loại bỏ các boxes trùng lặp:

- Lọc bỏ tất cả boxes có confidence < 0.05
- Sắp xếp boxes theo confidence giảm dần
- Loại bỏ boxes có IoU (Intersection over Union) > 0.7 với boxes đã chọn (để tránh overlap)
- Giữ lại tối đa 300 detections
- Trả về index của các boxes được giữ (`kept_idxs`) để map lại raw predictions

```python
def run_nms(raw_pred, nc):
    out = non_max_suppression(
        raw_pred.clone(), 
        conf_thres=CONF_THRES,      # Threshold: 0.05
        iou_thres=IOU_THRES,        # Threshold: 0.7
        max_det=MAX_DET,            # Max 300 detections
        nc=nc, 
        return_idxs=True            # Trả về index để map lại
    )
    return detections, kept_idxs
```

|Input|Output 1|Output 2|Ý nghĩa|
|---|---|---|---|
| raw_pred [1, 25200, 4+nc] và raw_class_scores [25200, nc] (nc=24) | detections [num_kept, 6] - boxes sau lọc với format (x1, y1, x2, y2, best_conf, best_cls) | kept_idxs [num_kept] - index để map mỗi detection về raw predictions | Số lượng boxes giảm từ 25200 xuống 0-300, loại bỏ các predictions yếu |

**Giải thích thêm:**
- Điểm quan trọng: `return_idxs=True` giúp ta biết proposal nào (từ 25200 proposals) được giữ lại
- Điều này cho phép ta lấy được raw class scores của các detection cuối cùng
- IoU threshold 0.7 có nghĩa nếu 2 boxes overlap hơn 70%, chỉ giữ lại cái có confidence cao hơn

---

**Bước 5: Ánh Xạ Ngược về Raw Predictions**

Bước này là chìa khóa để lấy toàn bộ class scores của mỗi detection:

- Mỗi detection sau NMS tương ứng với một proposal từ raw predictions
- Sử dụng `kept_idxs` để biết proposal nào tương ứng
- Lấy class scores của proposal đó từ `raw_class_scores`

```python
for obj_id, det in enumerate(detections_scaled):
    x1, y1, x2, y2, best_conf, best_cls = map(float, det.cpu().numpy())
    best_cls = int(best_cls)
    
    # Cách 1: Nếu có kept_idxs từ NMS
    if kept_idxs is not None:
        raw_idx = int(kept_idxs[obj_id])  # Index vào raw_class_scores
    else:
        # Cách 2: Fallback - tính IoU để tìm matching proposal gần nhất
        ious = box_iou_numpy(np.array([x1, y1, x2, y2]), raw_boxes_xyxy_scaled)
        raw_idx = int(np.argmax(ious))
    
    # Lấy class scores của detection này từ raw predictions
    class_scores = raw_class_scores[raw_idx].cpu().numpy()  # Shape: [8]
```

|Input|Process|Output|Ý nghĩa|
|---|---|---|---|
| detections [num_kept, 6], kept_idxs [num_kept], raw_class_scores [25200, 8] | Với mỗi detection, lấy index từ kept_idxs rồi index vào raw_class_scores | class_scores [8] - confidence của 8 classes cho detection này | Giờ ta có toàn bộ class scores (không chỉ best class) của mỗi detection |

**Giải thích chi tiết:**
- `raw_idx` cho biết proposal thứ mấy (từ 25200) được giữ lại là detection này
- `raw_class_scores[raw_idx]` là 1D array có 8 phần tử
- Ví dụ: class_scores = [0.85, 0.12, 0.02, 0.00, 0.01, 0.00, 0.00, 0.00]
  - Class 0: 0.85 (cao nhất → class tốt nhất)
  - Class 1: 0.12 (thứ hai)
  - Class 2-7: thấp (< 0.02)

---

**Bước 6: Lấy Top 200 Anchors Theo Max Confidence**

Bước này trích xuất 200 proposals tốt nhất (theo max confidence) để tạo báo cáo CSV:

- Tính max confidence của mỗi proposal (giá trị cao nhất trong 8 class scores)
- Sắp xếp các proposals theo max confidence giảm dần
- Lấy top 200 proposals (hoặc ít hơn nếu tổng proposals < 200)
- Lấy tọa độ và class scores của 200 proposals này
- Tạo DataFrame pandas với columns: x_center, y_center, width, height, class_0, class_1, ..., class_7
- Lưu DataFrame vào file CSV

```python
# Lấy max confidence của mỗi proposal
max_scores, _ = raw_class_scores.max(dim=1)  # Shape: [25200]

# Lấy top 200 indices
topk = min(200, max_scores.shape[0])
_, topk_indices = torch.topk(max_scores, topk)  # Shape: [200]

# Lấy tọa độ và scores của top proposals
top_boxes = raw_boxes_xywh[topk_indices].cpu().numpy()      # Shape: [200, 4]
top_scores = raw_class_scores[topk_indices].cpu().numpy()   # Shape: [200, 8]

# Tạo CSV data
csv_data = []
for i in range(topk):
    row = top_boxes[i].tolist() + top_scores[i].tolist()  # [x, y, w, h, s0, s1, ..., s7]
    csv_data.append(row)

# Tạo DataFrame và lưu
header = ["x_center", "y_center", "width", "height"] + [names[j] for j in range(nc)]
df = pd.DataFrame(csv_data, columns=header)
csv_path = os.path.join(out_subdir, f"{img_name}_top200.csv")
df.to_csv(csv_path, index=False)
```

|Input|Process|Output|Ý nghĩa|
|---|---|---|---|
| raw_boxes_xywh [25200, 4], raw_class_scores [25200, nc] (nc=24) | Lấy max confidence, top-k, tạo DataFrame | File CSV {img_name}_top200.csv với 200 dòng, (4+nc) columns | Báo cáo các proposals tốt nhất cho phân tích chi tiết |

**Giải thích chi tiết:**
- `max_scores` là 1D array [25200] chứa giá trị max của 8 class scores cho mỗi proposal
- `topk_indices` là indices của 200 proposals có max_scores cao nhất
- CSV file có 200 dòng (nếu < 200 proposals thì chỉ có đó)
- Mỗi dòng có (4+nc) columns: 4 tọa độ bbox + nc class scores (24 classes trong bài toán này)

**Ví dụ CSV structure:**

```
x_center,y_center,width,height,class_0,class_1,class_2,class_3,class_4,class_5,class_6,class_7
320.5,240.3,150.2,180.1,0.8547,0.1203,0.0142,0.0058,0.0031,0.0012,0.0005,0.0002
410.1,150.5,120.4,140.2,0.2145,0.1567,0.6234,0.0032,0.0015,0.0004,0.0002,0.0001
...
```

---

**Bước 7: Xử Lý và Lưu Kết Quả**

Bước này lấy toàn bộ class scores và lưu kết quả (ảnh + text debug + CSV):

- Duyệt qua mỗi detection
- Lấy toàn bộ 8 class scores của nó
- Vẽ bbox với các màu khác nhau cho các classes có score > ngưỡng
- Lưu debug info: bbox, tọa độ, toàn bộ class scores
- Lưu ảnh annotated và text file
- Lưu file CSV top 200 anchors (từ bước 6)

```python
debug_lines = []
for obj_id, det in enumerate(detections_scaled):
    # ... (lấy class_scores như ở bước 5)
    
    debug_lines.append(f"Object {obj_id} | Best: {names[best_cls]} (Conf: {best_conf:.4f})")
    debug_lines.append(f"Bbox (xyxy): ({x1:.1f}, {y1:.1f}, {x2:.1f}, {y2:.1f})")
    
    # In ra tất cả 8 class scores
    for cls_id, score in enumerate(map(float, class_scores)):
        marker = " <-- BEST" if cls_id == best_cls else ""
        debug_lines.append(f"  {cls_id} - {names[cls_id]}: {score:.4f}{marker}")
    
    # Vẽ bbox với nhiều màu cho các classes khác nhau
    draw_bboxes(img0, x1, y1, x2, y2, class_scores, obj_id, names)

# Lưu kết quả
cv2.imwrite(os.path.join(out_subdir, f"debug_{img_name}"), img0)
with open(os.path.join(out_subdir, f"{img_name}_debug.txt"), "w") as f:
    f.write("\n".join(debug_lines))
```

|Input|Process|Output 1|Output 2|Output 3|
|---|---|---|---|---|
| detections_scaled, class_scores, ảnh gốc, top 200 data từ bước 6 | Loop qua mỗi detection, visualization, tạo CSV, lưu files | Ảnh debug_{img_name} với bbox + labels | Text file {img_name}_debug.txt với chi tiết từng detection | CSV file {img_name}_top200.csv với 200 proposals tốt nhất |
| **Ý nghĩa** | Lưu lại toàn bộ kết quả: visualization + detections chi tiết + top anchors report |

**Giải thích thêm:**
- `debug_lines` là list chứa text information
- Mỗi detection được in 1 object ID + best class + bbox coordinates
- Tiếp theo là 8 dòng cho 8 classes (mark BEST class)
- Ảnh lưu có bbox vẽ với 8 màu khác nhau, mỗi màu = 1 class

---

## Kiến Trúc Dữ Liệu Chi Tiết

**Raw Predictions Tensor**

```
raw_pred shape: [batch=1, 4+nc=(4+24=28), num_proposals=25200]

Sau reshape: [1, num_proposals, 28]
├─ [:, :4, :] → bbox coordinates (x, y, w, h) - tọa độ tương đối
└─ [:, 4:4+nc, :] → class scores (nc=24 classes)
                ├─ [:, 4, :] = score_class_0
                ├─ [:, 5, :] = score_class_1
                ├─ ...
                └─ [:, 27, :] = score_class_23

Sau transpose thành [num_proposals, 28]:
├─ [:, :4] → bbox tọa độ
└─ [:, 4:28] → nc class scores (24 trong bài toán này)
```

**Class Scores Array (sau extraction)**

```
class_scores = [0.85, 0.12, 0.02, 0.00, 0.01, 0.00, ..., 0.0001] (24 values, nc=24)
               (index)  0    1    2    3    4    5    ...    23

Mapping sang class names:
- names[0] = "class_0", score = 0.85
- names[1] = "class_1", score = 0.12
- names[2] = "class_2", score = 0.02
- ...

Các thông tin rút ra:
- Best class = argmax(class_scores) = 0 (index)
- Best confidence = max(class_scores) = 0.85
- Class name = names[0] = "class_0"
- Entropy = -sum(p * log(p)) → đo độ chắc chắn của model
```

**Top 200 Anchors Selection**

```
raw_class_scores shape: [25200, 8]
    ↓
max_scores = raw_class_scores.max(dim=1) → [25200]
    ↓
Sort by max_scores descending
    ↓
topk_indices = top 200 indices → [200]
    ↓
top_boxes = raw_boxes_xywh[topk_indices] → [200, 4]
top_scores = raw_class_scores[topk_indices] → [200, 8]
    ↓
CSV DataFrame: 200 rows × 12 columns
    ├─ Columns 0-3: [x_center, y_center, width, height]
    └─ Columns 4-11: [class_0, class_1, ..., class_7]
```

**Ý Nghĩa:**
- `max_scores` lấy giá trị cao nhất từ 8 class scores của mỗi proposal
- Top 200 là những proposals có 8 class scores "mạnh nhất" (max score cao nhất)
- Điều này khác với NMS (lấy best_class = argmax, sau đó lọc overlap)
- CSV report giúp thấy toàn cảnh các candidates tốt nhất model phát hiện

---

## Ví Dụ Output Cụ Thể

**Debug Text File Format**

```
Image: test_image.jpg
Path: /path/to/test_image.jpg
Relative dir: test_dir
------------------------------------------------------------

Number of detections after NMS: 2

Object 0 | Best: class_0 (Conf: 0.8547)
Bbox (xyxy): (100.0, 150.0, 250.0, 300.0) | Match: return_idxs
  0 - class_0: 0.8547 <-- BEST
  1 - class_1: 0.1203
  2 - class_2: 0.0142
  3 - class_3: 0.0058
  4 - class_4: 0.0031
  5 - class_5: 0.0012
  6 - class_6: 0.0005
  7 - class_7: 0.0002

Object 1 | Best: class_2 (Conf: 0.6234)
Bbox (xyxy): (400.0, 120.0, 550.0, 280.0) | Match: return_idxs
  0 - class_0: 0.2145
  1 - class_1: 0.1567
  2 - class_2: 0.6234 <-- BEST
  3 - class_3: 0.0032
  4 - class_4: 0.0015
  5 - class_5: 0.0004
  6 - class_6: 0.0002
  7 - class_7: 0.0001
```

---

## CSV Top 200 Anchors Report

**Mục Đích:**

File CSV `{img_name}_top200.csv` chứa dữ liệu 200 anchors tốt nhất (theo max confidence) từ raw predictions. Đây là dữ liệu thô (trước NMS) được sắp xếp theo độ tin cậy.

**Nội Dung File:**

| Column | Ý Nghĩa | Giải Thích |
|--------|---------|-----------|
| x_center | Tọa độ X của bbox | Tọa độ tương đối so với grid cell |
| y_center | Tọa độ Y của bbox | Tọa độ tương đối so với grid cell |
| width | Chiều rộng bbox | Relative width (tương đối 640x640) |
| height | Chiều cao bbox | Relative height (tương đối 640x640) |
| class_0...class_7 | Confidence scores | 8 giá trị, mỗi giá trị từ 0 đến 1 |

**Tính Chất Của Data:**

- **Trước NMS:** Dữ liệu này là raw predictions chưa qua NMS filtering, có thể có overlaps
- **Top 200:** Được chọn dựa trên `max(score_0, score_1, ..., score_7)` (max confidence)
- **Sắp Xếp:** Từ cao xuống thấp theo max confidence
- **Số Lượng:** Tối đa 200, nhưng nếu ảnh chỉ có < 200 proposals thì lấy tất cả
- **Tọa Độ Mô Hình:** Tọa độ ở định dạng YOLO (tương đối, chưa scale về kích thước ảnh gốc)

**Ví Dụ Dữ Liệu CSV:**

```csv
x_center,y_center,width,height,class_0,class_1,class_2,class_3,class_4,class_5,class_6,class_7
320.5,240.3,150.2,180.1,0.8547,0.1203,0.0142,0.0058,0.0031,0.0012,0.0005,0.0002
410.1,150.5,120.4,140.2,0.2145,0.1567,0.6234,0.0032,0.0015,0.0004,0.0002,0.0001
275.8,380.2,160.5,95.3,0.0847,0.0923,0.0512,0.7234,0.0341,0.0089,0.0042,0.0012
...
(200 rows total)
```
---

## Visualization

**Vẽ Bbox**

```python
def draw_bboxes(img, x1, y1, x2, y2, class_scores, obj_id, names):
    # Với mỗi class
    for cls_id, score in enumerate(class_scores):
        if score < CLASS_DRAW_THRES:  # Ngưỡng: 0.05
            continue
        
        # Chọn màu dựa trên class_id
        color = CLASS_COLOR_PALETTE[cls_id % len(CLASS_COLOR_PALETTE)]
        
        # Vẽ bbox
        cv2.rectangle(img, (xc1, yc1), (xc2, yc2), color, 2)
        
        # Vẽ label: "Obj0 class_2: 0.6234"
        draw_label(img, f"Obj{obj_id} {names[cls_id]}: {score:.3f}", xc1, label_y, color)
```

**Ảnh output:**
- Sẽ có nhiều bbox với các màu khác nhau, mỗi màu đại diện cho một class
- Mỗi bbox có label kèm theo: Object ID + Class name + Confidence score
- Nếu class score < 0.05, không vẽ label để tránh quá đông

---

## Configuration & Parameters

```python
# Preprocessing
IMG_SIZE = 640              # Input size cho model

# NMS
CONF_THRES = 0.05          # Confidence threshold trước NMS (ngưỡng lọc)
IOU_THRES = 0.7            # IoU threshold cho NMS (ngưỡng overlap)
MAX_DET = 300              # Max detections sau NMS (giới hạn số detection)

# Visualization
CLASS_DRAW_THRES = 0.05    # Min confidence để vẽ label trên ảnh
CLASS_COLOR_PALETTE = [
    (0, 255, 0), (255, 0, 0), (0, 0, 255), (0, 255, 255), 
    (255, 0, 255), (255, 255, 0), (128, 128, 0), (0, 128, 128)
]  # 8 màu cho 8 classes
```

---

## Các lệnh sử dụng

```bash
# Chạy trên một folder ảnh
python check_confidence.py --input test_images --output results

# Hoặc với absolute paths
python check_confidence.py --input /abs/path/to/images --output /abs/path/to/output
```

**Output Structure:**

```
results/
├── subdir1/
│   ├── image1_debug.jpg          (Ảnh với bbox visualization)
│   ├── image1_debug.txt          (Text file với chi tiết detections)
│   └── image1_top200.csv         (Top 200 anchors report)
├── subdir2/
│   ├── image2_debug.jpg
│   ├── image2_debug.txt
│   └── image2_top200.csv
└── ...
```


---

## Tóm tắt 3 output của tool check_confidence.py

**Ảnh Debug (debug_{img_name}.jpg)**

- Loại: Hình ảnh
- Chứa: Ảnh gốc + bounding boxes + labels
- Mục đích: Visualization nhanh, kiểm tra detection results trực quan
- Cách sử dụng: Xem trực tiếp, trao đổi với team, demo
- Bbox được vẽ với 8 màu khác nhau (mỗi class = 1 màu)
- Label format: "Obj{id} {class_name}: {confidence:.3f}"

**Text Debug File ({img_name}_debug.txt)**

- Loại: Text file, encoded UTF-8
- Chứa: 
  - Image info (path, name, directory)
  - Per-detection info: bbox, best class, và toàn bộ 8 class scores
  - Match method (return_idxs hoặc iou_fallback)
- Mục đích: Lưu trữ chi tiết, có thể parse lại, human-readable
- Cách sử dụng: Tìm kiếm, phân tích, build statistics
- Format dễ parse: mỗi dòng có cấu trúc rõ ràng

**CSV Top 200 Report ({img_name}_top200.csv)**

- Loại: CSV file (tabular data)
- Chứa: 
  - 200 proposals tốt nhất (top 200)
  - Tọa độ bbox (4 columns)
  - Class scores (8 columns)
  - Sắp xếp từ cao xuống thấp theo max confidence
- Mục đích: Analysis chuyên sâu, thống kê, machine learning preprocessing
- Cách sử dụng: 
  - Load vào pandas/numpy
  - Tính thống kê, entropy, correlation
  - Filter, sort, aggregate
  - Build confusion matrix, training data



---

## Tóm Tắt quá trình End-to-End

Quá trình lấy confidence của tất cả `nc` classes cho mỗi object (trong project này `nc = 24`):

1. **Preprocessing** - Ảnh BGR bất kỳ → Tensor [1, 3, 640, 640] đã chuẩn hóa
2. **Forward Pass** - Tensor input → Raw predictions [1, num_proposals, 4+nc]
3. **Tách dữ liệu** - Tách tọa độ [num_proposals, 4] và scores [num_proposals, nc]
4. **Apply NMS** - Từ num_proposals → 0-300 detections + mapping indices
5. **Map Back** - Sử dụng indices để lấy raw class scores của mỗi final detection
6. **Extract All Scores** - Mỗi detection có `nc` class scores (không chỉ best class)
7. **Top 200 Anchors** - Lấy 200 proposals tốt nhất theo max confidence để tạo CSV report
8. **Visualization & Save** - Vẽ bbox + lưu 3 file: ảnh annotated + text debug + CSV top 200

**Output Cuối Cùng:**
- `debug_{img_name}`: Ảnh với bbox visualization (mỗi class một màu, tổng `nc` màu)
- `{img_name}_debug.txt`: Text file chi tiết với tất cả detections và class scores (nc values)
- `{img_name}_top200.csv`: CSV file chứa 200 proposals tốt nhất (x_center, y_center, width, height + `nc` class scores)

## B. Khó khăn
- không
## C. Công việc tiếp theo
- Em xin phép nhận hướng đi tiếp theo từ Thầy ạ .
