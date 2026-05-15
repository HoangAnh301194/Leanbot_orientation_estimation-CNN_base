# Báo cáo nguyên lí Check_confidence.py với NMS

---

## 1. Tổng quan về Check_Confidence.py

`check_confidence.py` là một script xử lý và phân tích kết quả dự đoán của mô hình YOLO v8. 
- **Mục đích**: Kiểm tra và visualize confidence score của tất cả các class cho mỗi detection từ mô hình YOLO
- **Đầu vào**: Ảnh chụp thực tế từ Camera
- **Đầu ra**: Ảnh debug có vẽ bounding box và text log chi tiết confidence score cho toàn bộ các class mà model detect được.

---

## 2. Nguyên lý hoạt động chính

### 2.1. **Luồng Xử lý**

```
Input Images
    ↓
[Preprocessing - Chuẩn hóa ảnh]
    ↓
[YOLO Inference - Dự đoán từ mô hình]
    ↓
[NMS (Non-Maximum Suppression) - Lọc detection trùng lặp]
    ↓
[Match & Extract Scores - Lấy confidence score tất cả class]
    ↓
[Visualization & Logging - Vẽ BBox và lưu log]
    ↓
Output: Debug Images + Text Logs
```

### 2.2. **Chi tiết các module chính**

#### **2.2.1. Preprocessing (Chuẩn hóa ảnh)**
```python
def preprocess_image(img_bgr, imgsz=640):
    # Input: ảnh BGR từ OpenCV
    # Output: tensor đã chuẩn hóa kích thước 640x640
```

**Các bước:**
- **LetterBox**: Resize ảnh về 640x640 (kích thước input của YOLO) với padding để giữ aspect ratio
- **Color space conversion**: BGR → RGB
- **Transpose**: HWC (Height, Width, Channel) → CHW (Channel, Height, Width) để match format tensor PyTorch
- **Normalize**: Chia cho 255.0 để đưa giá trị pixel về [0, 1]
- **Device transfer**: Chuyển sang GPU/CPU tùy theo device khả dụng

#### **2.2.2. YOLO Inference**
```python
with torch.no_grad():
    raw_pred = normalize_raw_pred_shape(model.model(img_tensor), nc)
```

**Output của YOLO:**
- `raw_pred` shape: `[1, num_channels, num_detections]`
- `num_channels = 4 (bbox coordinates xywh) + num_classes (confidence scores)`
- Ví dụ: 8 class → 12 channels (4 bbox + 8 class scores)

#### **2.2.3. NMS (Non-Maximum Suppression)**

##### **2.2.3.1. Hàm NMS - `run_nms()`**

```python
def run_nms(raw_pred, nc):
    try:
        out = non_max_suppression(raw_pred.clone(), conf_thres=CONF_THRES, 
                                  iou_thres=IOU_THRES, max_det=MAX_DET, 
                                  nc=nc, return_idxs=True)
        if isinstance(out, tuple) and len(out) == 2:
            return out[0][0], out[1][0]
        return out[0], None
    except TypeError:
        out = non_max_suppression(raw_pred.clone(), conf_thres=CONF_THRES, 
                                  iou_thres=IOU_THRES, max_det=MAX_DET, nc=nc)
        return out[0][0] if isinstance(out, tuple) else out[0], None
```

**Parameters:**
- `CONF_THRES = 0.05`: Chỉ giữ detection nếu `max(P(class_i)) > 0.05`
- `IOU_THRES = 0.7`: Xóa detection nếu IoU > 0.7 với detection khác
- `MAX_DET = 300`: Tối đa 300 detection mỗi ảnh
- `return_idxs=True`: Trả về index của detection được giữ lại

##### **2. Lấy Raw Predictions P(xyz) trước NMS (Lines 134-138)**

```python
raw_boxes_xywh = raw_pred[0, :4, :].T           # Bbox coordinates (x, y, w, h)
raw_class_scores = raw_pred[0, 4:4 + nc, :].T  # *** Confidence P(xyz) trước NMS ***
detections, kept_idxs = run_nms(raw_pred, nc)  # Gọi NMS
```

**Chi tiết:**
- `raw_pred`: Output từ YOLO model có shape `[1, 4+num_classes, num_anchors]`
  - Ví dụ: `[1, 12, num_anchors]` (4 bbox + 8 classes)
- `raw_class_scores`: Extract tất cả confidence scores của 8 class
  - Shape: `[num_raw_detections, 8]`
  - Mỗi hàng: `[P(class_0), P(class_1), ..., P(class_7)]`
  - Giá trị từ 0 -> 1 (xác suất)

**Ví dụ:**
```
raw_class_scores[0] = [0.8234, 0.0523, 0.0001, 0.0000, 0.1200, 0.0032, 0.0009, 0.0001]
                       P(cls0) P(cls1) P(cls2) P(cls3) P(cls4) P(cls5) P(cls6) P(cls7)
                       ↑
                    Best class (max prob)
```

##### **2.2.3.2. NMS Filtering Process**

**Quy trình lọc:**
1. **Bước 1**: Filter theo `CONF_THRES = 0.05`
   - Chỉ giữ lại detection nếu `max(P(class_i)) > 0.05`
   - Loại bỏ detections với tất cả confidence < 0.05
   
2. **Bước 2**: Sắp xếp theo confidence descending
   - Detection có P max cao nhất được xem xét trước
   
3. **Bước 3**: Lặp qua từng detection
   - Giữ lại detection hiện tại nếu chưa bị mark xóa
   - Tính IoU với tất cả detection còn lại
   - Nếu IoU > `IOU_THRES = 0.7` → Xóa detection kia (giữ detection có confidence cao hơn)
   
4. **Bước 4**: Trả về
   - `detections`: Detections sau NMS
   - `kept_idxs`: Index của detection được giữ (trong raw_pred)

**Ví dụ NMS:**
```
Raw detections: 50 boxes
After CONF_THRES: 40 boxes (loại 10 có max P < 0.05)
After IoU filter: 15 boxes (loại 25 bị overlap IoU > 0.7)
Result: 15 clean detections
```

##### **2.2.3.3. Output của NMS**

```python
detections, kept_idxs = run_nms(raw_pred, nc)
```

- **`detections`**: Bounding box sau NMS
  - Shape: `[num_after_nms, 6]`
  - Format mỗi hàng: `[x1, y1, x2, y2, best_confidence, best_class_id]`
  - Ví dụ: `[100.5, 200.3, 300.8, 450.2, 0.8234, 0]` (class 0 với conf 0.8234)
  
- **`kept_idxs`**: Index để lấy P(xyz)
  - Shape: `[num_after_nms]`
  - Giá trị: Index trong `raw_class_scores`
  - Dùng để: `class_scores = raw_class_scores[kept_idxs[i]]`

#### **2.2.4. Matching & Confidence Score P(xyz) Extraction - Chi tiết**

##### **1. Tại sao cần Matching?**

**Vấn đề:**
- NMS **thay đổi thứ tự** và **giảm số lượng** detections
- Cần map từ detection sau NMS → raw_class_scores để lấy P(xyz)

**Giải pháp:**
- Sử dụng `kept_idxs` hoặc tính IoU fallback để tìm raw detection tương ứng

##### **2.2.4.1. Matching Process**

```python
# Matching logic
if kept_idxs is not None:
    # Method 1: Direct index mapping (từ NMS return_idxs)
    raw_idx, match_method, match_iou = int(kept_idxs[obj_id]), "return_idxs", None
else:
    # Method 2: IoU fallback (tính lại nếu không có return_idxs)
    ious = box_iou_numpy(np.array([x1, y1, x2, y2]), raw_boxes_xyxy_scaled)
    raw_idx, match_method, match_iou = int(np.argmax(ious)), "iou_fallback", float(np.max(ious))

# *** QUAN TRỌNG: Lấy vector P(xyz) cho detection này ***
class_scores = raw_class_scores[raw_idx].cpu().numpy()
```

**Chi tiết:**

**Method 1: Direct Index (Best)**
```
detections[0] ← kept_idxs[0] → raw_class_scores[kept_idxs[0]]
                   raw_idx = 7
                            ↓
                raw_class_scores[7] = [0.8234, 0.0523, ..., 0.0001]
                                       ↑
                                   P(xyz) vector
```

**Method 2: IoU Fallback (Backup)**
```
Tính IoU(detection_after_nms, tất cả raw_boxes_xyxy_scaled)
Lấy raw_box có IoU lớn nhất → đó chính là detection gốc
Lấy P(xyz) từ raw_class_scores
```

##### **2.2.4.2. Class Scores Vector**

```python
class_scores = raw_class_scores[raw_idx].cpu().numpy()
```

**Output:**
- Type: `numpy array`
- Shape: `[8]` (8 classes)
- Values: `[P(class_0), P(class_1), ..., P(class_7)]`
- Range: 0 → 1 (probability)

**Ví dụ:**
```
class_scores = [0.8234, 0.0523, 0.0001, 0.0000, 0.1200, 0.0032, 0.0009, 0.0001]
                  ↑        ↑       ↑       ↑       ↑       ↑       ↑       ↑
               cls_0    cls_1   cls_2   cls_3   cls_4   cls_5   cls_6   cls_7
               
Best class = argmax(class_scores) = 0 (P = 0.8234)
```

##### **2.2.4.2. Print Confidence Scores P(xyz)**

```python
# *** In tất cả 8 confidence scores ***
for cls_id, score in enumerate(map(float, class_scores)):
    debug_lines.append(f"  {cls_id} - {names[cls_id]}: {score:.4f} {'<-- BEST' if cls_id == best_cls else ''}")
```

**Format Output:**
```
Object 0 | Best: class_0 (Conf: 0.8234)
Bbox (xyxy): (100.0, 200.0, 300.0, 400.0) | Match: return_idxs

  0 - class_0: 0.8234 <-- BEST    ← Class được chọn
  1 - class_1: 0.0523              ← Các class khác
  2 - class_2: 0.0001
  3 - class_3: 0.0000
  4 - class_4: 0.1200
  5 - class_5: 0.0032
  6 - class_6: 0.0009
  7 - class_7: 0.0001
```

**Giải thích:**
- Dòng 1: Class có confidence cao nhất (`BEST`)
- Dòng 2-9: Confidence của tất cả 8 class (P(xyz))
- Giá trị format `.4f` = 4 chữ số thập phân

##### **2.2.4.2. Tóm tắt P(xyz) Extraction**

| **Bước** | **Dòng** | **Hành động** | **Output** |
| :---: | :---: | :--- | :--- |
| 1 | 135 | Gọi NMS | `detections, kept_idxs` |
| 2 | 153-162 | Matching raw_idx | `raw_idx` (vị trí trong raw_class_scores) |
| 3 | 162 | Extract P(xyz) | `class_scores` (vector 8 giá trị) |
| 4 | 174-176 | Print từng P(xyz) | Log file |

#### **2.2.4.3. Visualization**
```python
draw_bboxes(img, x1, y1, x2, y2, class_scores, obj_id, names)
```

**Quy trình vẽ:**
1. Duyệt qua 8 class
2. Filter class có confidence > `CLASS_DRAW_THRES = 0.0`
3. Vẽ rectangle theo màu riêng của mỗi class
4. Ghi label: `Obj{id} {class_name}: {confidence_score}`
5. Xử lý label overlap bằng cách offset vị trí text theo class_id

---

### 3. **Cấu hình quan trọng**

| Config | Giá trị | Ý nghĩa |
| :---: | :---: | :--- |
| `IMG_SIZE` | 640 | Kích thước input model YOLO |
| `CONF_THRES` | 0.05 | Ngưỡng confidence để xem là detection hợp lệ |
| `IOU_THRES` | 0.7 | Ngưỡng IoU để lọc detection trùng lặp trong NMS |
| `MAX_DET` | 300 | Số detection tối đa mỗi ảnh |
| `CLASS_DRAW_THRES` | 0.0 | Ngưỡng để vẽ label class (0.0 = vẽ tất cả) |

---

### 4. **Output & Logging**

Mỗi ảnh được xử lý tạo ra 2 file:

**File 1: Ảnh debug (`debug_{image_name}.jpg`)**
- Vẽ tất cả detection được giữ lại sau NMS
- Mỗi class có màu khác nhau
- Label hiển thị: `Obj{id} {class_name}: {confidence_value}`

**File 2: Text log (`{image_name}_debug.txt`)**
```
Image: test.jpg
Path: /full/path/test.jpg
Relative dir: subfolder/

Object 0 | Best: class_name (Conf: 0.8234)
Bbox (xyxy): (100.0, 200.0, 300.0, 400.0) | Match: return_idxs

  0 - class_0: 0.8234 <-- BEST
  1 - class_1: 0.0523
  2 - class_2: 0.0001
  ...
```

---

## C. Luồng dữ liệu chi tiết

```
┌─ Raw Image (RGB)
│
├─ Preprocessing
│  ├─ LetterBox resize (640x640)
│  ├─ Normalize pixel values [0, 1]
│  └─ Convert to tensor [1, 3, 640, 640]
│
├─ YOLO Forward Pass
│  └─ Output: raw_pred [1, 12, num_anchors] (for 8 classes)
│
├─ Parse Output
│  ├─ Extract bbox coordinates (xywh)
│  └─ Extract class scores (8 values per detection)
│
├─ NMS Filtering
│  ├─ Filter by CONF_THRES
│  ├─ Remove overlapping detections (IoU > 0.7)
│  └─ Output: filtered detections + kept indices
│
├─ Score Extraction
│  └─ Get all 8 class scores for each filtered detection
│
└─ Visualization
   ├─ Draw bounding boxes (color per class)
   ├─ Draw confidence labels
   └─ Save output image + debug log
```

---

## D. IoU (Intersection over Union) Calculation

**Công thức:**
$$IoU = \frac{Area_{intersection}}{Area_{union}} = \frac{Area_{intersection}}{Area_1 + Area_2 - Area_{intersection}}$$

**Ví dụ:**
- 2 box overlap diện tích 50 pixel
- Box 1 diện tích: 100 pixel
- Box 2 diện tích: 120 pixel
- IoU = 50 / (100 + 120 - 50) = 50/170 ≈ 0.294

**Trong NMS**: Nếu IoU > 0.7 → Xóa box có confidence thấp hơn

---

## E. Tại sao cần Confidence Score của tất cả Class?

### **Vấn đề**: 
- YOLO model output: giá trị confidence cao nhất được chọn là class kết quả
- Nhưng confidence của class dự đoán có thể không cao

### **Giải pháp**:
- `check_confidence.py` hiển thị tất cả 8 class confidence scores
- Cho phép phân tích:
  - Có bao nhiêu class được model "xem xét" (confidence > 0)?
  - Model "chắc chắn" đến mức độ nào?
  - Có các class cạnh tranh không (gần bằng nhau)?

### **Ứng dụng thực tế**:
- Debug model khi detection sai
- Hiểu được mức độ "lưỡng lự" của model
- Phát hiện trường hợp background noise bị detect

---

## F. Các bước xử lý chi tiết

### **Bước 1: Load Model**
```python
model = YOLO(model_path).to(device)
model.model.eval()  # Chuyển sang inference mode
```

### **Bước 2: Đọc ảnh từ folder**
```python
image_paths = sorted([p for ext in exts 
                      for p in glob.glob(..., recursive=True)])
```
- Tìm tất cả `.jpg`, `.jpeg`, `.png` (case-insensitive) trong subfolder

### **Bước 3: Xử lý từng ảnh**
```python
for img_path in image_paths:
    img0 = cv2.imread(img_path)
    img_tensor = preprocess_image(img0, IMG_SIZE)
```

### **Bước 4: Inference**
```python
with torch.no_grad():  # Tắt gradient computation để tiết kiệm memory
    raw_pred = model.model(img_tensor)
```

### **Bước 5: Scale Boxes**
```python
detections_scaled = scale_boxes(img_tensor.shape[2:], 
                                detections_scaled[:, :4], 
                                img0.shape)
```
- Bbox được tính trên ảnh 640x640
- Scale lại về ảnh gốc để vẽ đúng vị trí

### **Bước 6: Vẽ & Lưu**
```python
draw_bboxes(img0, x1, y1, x2, y2, class_scores, obj_id, names)
cv2.imwrite(os.path.join(out_subdir, f"debug_{img_name}"), img0)
```

---

## L. Luồng Dữ Liệu NMS & P(xyz) - Chi Tiết Hoàn Toàn

### **Stage 1: Raw Predictions từ YOLO (Trước NMS)**

```
YOLO Model Output:
    raw_pred shape: [1, 12, num_anchors]  (cho 8 classes)
    
    Breakdown:
    ├─ Channels 0-3: Bounding box (x, y, w, h)
    └─ Channels 4-11: Class confidence (P(class_0) ... P(class_7))
    
Extract:
    raw_boxes_xywh = raw_pred[0, :4, :].T       → [num_anchors, 4]
    raw_class_scores = raw_pred[0, 4:12, :].T   → [num_anchors, 8]
                                                     ↑
                                            P(xyz) của tất cả detection
```

**Ví dụ:**
```
raw_class_scores = 
[
  [0.8234, 0.0523, 0.0001, 0.0000, 0.1200, 0.0032, 0.0009, 0.0001],  ← Detection 0
  [0.0012, 0.0001, 0.8905, 0.0082, 0.0000, 0.0000, 0.0000, 0.0000],  ← Detection 1
  [0.0234, 0.0891, 0.0003, 0.8800, 0.0001, 0.0002, 0.0069, 0.0000],  ← Detection 2
  ...
  [0.0001, 0.0001, 0.0001, 0.0001, 0.0001, 0.0001, 0.0001, 0.9900],  ← Detection n
]
```

### **Stage 2: Apply NMS Filter**

```
Condition 1: max(class_scores) > CONF_THRES (0.05)
    Detection 0: max = 0.8234 ✓ Keep
    Detection 1: max = 0.8905 ✓ Keep
    Detection 2: max = 0.8800 ✓ Keep
    Detection n: max = 0.9900 ✓ Keep
    
Condition 2: IoU < IOU_THRES (0.7) with all other kept detections
    Check overlap between detections
    If IoU > 0.7 → Remove the one with lower confidence
    
Result: 
    detections = [[x1,y1,x2,y2, 0.8234, 0], ...]     ← After NMS (15 boxes)
    kept_idxs = [0, 1, 2, ...]                        ← Original indices (raw_class_scores)
```

### **Stage 3: Match Detection → P(xyz)**

```
for obj_id, det in enumerate(detections_scaled):  # obj_id = 0, 1, 2, ...
    
    Step 1: Get raw_idx
    ├─ if kept_idxs is not None:
    │   raw_idx = kept_idxs[obj_id]                    ← Lấy từ NMS output
    │
    └─ else:
        Calculate IoU(det_bbox, all_raw_boxes)
        raw_idx = argmax(ious)                         ← Lấy raw box có IoU cao nhất
    
    Step 2: Extract P(xyz)
    class_scores = raw_class_scores[raw_idx]           ← Vector 8 giá trị
    
    Ví dụ:
    raw_idx = 7
    class_scores = raw_class_scores[7] = [0.0001, 0.0001, ..., 0.9900]
```

### **Stage 4: Print P(xyz)**

```python
# Chi tiết print
for cls_id, score in enumerate(map(float, class_scores)):
    # cls_id = 0, 1, 2, ..., 7
    # score = P(class_i)
    
    debug_output = f"  {cls_id} - {names[cls_id]}: {score:.4f}"
    
    if cls_id == best_cls:
        debug_output += " <-- BEST"
```

**Output file:**
```
Object 0 | Best: class_0 (Conf: 0.8234)
Bbox (xyxy): (100.0, 200.0, 300.0, 400.0) | Match: return_idxs

  0 - class_0: 0.8234 <-- BEST
  1 - class_1: 0.0523
  2 - class_2: 0.0001
  3 - class_3: 0.0000
  4 - class_4: 0.1200
  5 - class_5: 0.0032
  6 - class_6: 0.0009
  7 - class_7: 0.0001

Object 1 | Best: class_2 (Conf: 0.8905)
Bbox (xyxy): (350.0, 100.0, 600.0, 350.0) | Match: return_idxs

  0 - class_0: 0.0012
  1 - class_1: 0.0001
  2 - class_2: 0.8905 <-- BEST
  3 - class_3: 0.0082
  ...
```

### **Stage 5: Visualization**

```python
# Vẽ bounding box cho mỗi detection
draw_bboxes(img, x1, y1, x2, y2, class_scores, obj_id, names)

For mỗi class:
├─ If score > CLASS_DRAW_THRES (0.0):
│   ├─ Color = CLASS_COLOR_PALETTE[cls_id % 8]
│   ├─ Draw rectangle
│   └─ Draw label: f"Obj{obj_id} {names[cls_id]}: {score:.3f}"
│
└─ Else: Skip (score = 0)
```

---

## M. So Sánh Before/After NMS

| Thuộc tính | Before NMS | After NMS | Ghi chú |
| :---: | :---: | :---: | :--- |
| Số detections | 50 | 15 | Loại 35 boxes |
| CONF_THRES applied | ❌ No | ✓ Yes | Only keep max P > 0.05 |
| IoU filtering | ❌ No | ✓ Yes | Remove overlap (IoU > 0.7) |
| P(xyz) available | ✓ Yes | ✓ Yes | Lấy via kept_idxs |
| Data stored | `raw_class_scores` | `class_scores` | Extract per detection |

---

## N. Code Execution Flow - Visualized

```
def main():
    ├─ Load model & get names, nc=8
    ├─ For each image:
    │   ├─ preprocess_image() → [1, 3, 640, 640] tensor
    │   ├─ model.model() → raw_pred [1, 12, anchors]
    │   ├─ Extract:
    │   │   ├─ raw_boxes_xywh [anchors, 4]
    │   │   └─ raw_class_scores [anchors, 8]  ← *** P(xyz) before NMS ***
    │   ├─ run_nms() → detections, kept_idxs
    │   ├─ For each detection after NMS:
    │   │   ├─ Get raw_idx from kept_idxs
    │   │   ├─ class_scores = raw_class_scores[raw_idx]  ← *** Get P(xyz) ***
    │   │   ├─ Print 8 values: P(class_0) ... P(class_7)  ← *** Print P(xyz) ***
    │   │   └─ draw_bboxes() with class_scores
    │   └─ Save image + log file
    └─ Done
```

---

## O. Thông Số Quan Trọng - Cheat Sheet

**NMS Parameters:**
```python
CONF_THRES = 0.05      # Min confidence để giữ detection
IOU_THRES = 0.7        # Max IoU để giữ cả 2 detection
MAX_DET = 300          # Max detections per image
CLASS_DRAW_THRES = 0.0 # Min confidence để vẽ label
```

**P(xyz) Info:**
```python
raw_class_scores.shape = [num_raw_detections, 8]
class_scores.shape = [8]
class_scores range = [0.0, 1.0]
class_scores sum ≠ 1.0 (independent probabilities)
```

**Output Format:**
```
{class_id} - {class_name}: {probability:.4f}
  Example: 0 - class_0: 0.8234
```

---

### **1. Empty Detections**
```python
if detections is None or len(detections) == 0:
    print("Không phát hiện object nào.")
```

### **2. Box Validation**
```python
if xc2 > xc1 + 5 and yc2 > yc1 + 5:  # Min 5 pixel width/height
    cv2.rectangle(img, ...)
```

### **3. Label Position Adjustment**
```python
label_y = min(img_h - 1, yc1 + 20 + cls_id * 20)
```
- Tránh label vẽ ngoài ảnh

### **4. NMS Return Value Handling**
```python
try:
    out = non_max_suppression(..., return_idxs=True)
except TypeError:
    out = non_max_suppression(...)  # Fallback for older versions
```

---

## H. Performance Considerations

| Yếu tố | Tác động | Giải pháp |
| :---: | :---: | :--- |
| Số lượng ảnh lớn | Xử lý lâu | Xử lý batch hoặc parallel processing |
| GPU memory | OOM errors | Giảm `MAX_DET` hoặc batch size |
| Ảnh đầu vào lớn | Chậm | Resize before preprocessing |
| Model lớn (YOLOv8-L/X) | Inference chậm | Dùng YOLOv8-S hoặc YOLOv8-M |

---

## I. Tóm tắt Nguyên lý

| Bước | Chức năng | Input | Output |
| :---: | :--- | :--- | :--- |
| 1 | Preprocess | BGR image | [1, 3, 640, 640] tensor |
| 2 | Inference | Tensor | raw_pred [1, 12, anchors] |
| 3 | Parse | raw_pred | bbox + class scores |
| 4 | NMS | All detections | Filtered detections |
| 5 | Match | Filtered + raw | Confidence scores for all classes |
| 6 | Visualize | Scores + image | Debug image + log |
| 7 | Save | Debug data | Disk |

---

## J. Công dụng trong thực tế

**Sử dụng cho:**
- ✅ Debug khi model detection sai
- ✅ Phân tích confidence score distribution
- ✅ Kiểm tra NMS hoạt động đúng không
- ✅ Hiểu được "cách suy nghĩ" của model
- ✅ Tạo dataset với annotation chi tiết

---

## K. Các file liên quan

| File | Mục đích |
| :---: | :--- |
| `best.pt` | Trained YOLO model |
| `degree_45_test/` | Folder input ảnh test |
| `yolo_class_bbox_results/` | Folder output debug images & logs |
| `check_confidence.py` | Script chính |

---

**Tài liệu này giải thích chi tiết nguyên lý hoạt động của `check_confidence.py` - công cụ phân tích confidence score trong object detection pipeline.**
