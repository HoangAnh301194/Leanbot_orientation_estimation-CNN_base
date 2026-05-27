# Báo cáo công việc ngày 25/05/2026

## A. Công việc đã làm

### 1. Báo cáo chi tiết cách lấy 9 confidence value cho 1 BBox 

#### 1.1. Tổng quan quy trình

Quy trình lấy **9 confidence value** cho 1 BBox gốc (chưa mở rộng) diễn ra theo 4 bước chính:

```text
Ảnh gốc 2K (2560x1440)
  -> Tiền xử lý (LetterBox resize về 640x640)
  -> Model YOLO forward pass -> Raw prediction tensor (8400 anchors × 28 giá trị)
  -> NMS lọc ra các BBox -> Tra ngược 24 class scores từ raw tensor
  -> Chọn top 9 object có confidence cao nhất -> Xuất bảng 9 dòng
```

#### 1.2. Ảnh input và độ phân giải

- **Ảnh input gốc**: `24class_test_images/002.jpg`
- **Độ phân giải gốc**: `2560 × 1440` (2K, tỷ lệ 16:9)
- **Độ phân giải sau LetterBox**: `640 × 640` (có padding đen để giữ tỷ lệ)
- **Ảnh crop BBox mẫu** (`expand_0`): `290 × 214` pixel

Giá trị `290 × 214` được ghi trong file [meta.txt](detect_crop_output/objects/Leanbot_p180_001/meta.txt) do tool [detect_crop_levels.py](tools/detect_crop_levels.py) tự động sinh ra khi crop object `Leanbot_p180_001`:

```text
bbox_xyxy=(1862, 1001, 2151, 1214)
expand_0=bounds(1862, 1001, 2152, 1215),size=290x214
```

Cách tính: hàm `crop_with_expansion()` trong [detect_crop_levels.py](tools/detect_crop_levels.py) (dòng 91-109) cộng thêm `+1` pixel ở cạnh phải và dưới khi crop:

```python
def crop_with_expansion(image, bbox_xyxy, expansion):
    x1, y1, x2, y2 = bbox_xyxy          # (1862, 1001, 2151, 1214)
    right  = min(img_w, x2 + expansion + 1)  # 2151 + 0 + 1 = 2152
    bottom = min(img_h, y2 + expansion + 1)  # 1214 + 0 + 1 = 1215
    # → width  = 2152 - 1862 = 290
    # → height = 1215 - 1001 = 214
```

#### 1.3. Code Python chi tiết từng bước

Toàn bộ logic nằm trong 2 file chính:
- File lấy ra confidence của các class : [check_confidence.py](tools/check_confidence.py)
- File tổng hợp và xuất báo cáo: [export_markdown_report.py](tools/export_markdown_report.py)

##### Bước 1: Tiền xử lý ảnh (Preprocessing)

File code: [check_confidence.py](tools/check_confidence.py), hàm `preprocess_image()` (dòng 43-47)

```python
from ultralytics.data.augment import LetterBox

IMG_SIZE = 640

def preprocess_image(img_bgr, imgsz=640):
    # LetterBox: resize ảnh gốc (2560x1440) về 640x640 với padding đen giữ tỷ lệ
    img = LetterBox(new_shape=(imgsz, imgsz), auto=False, stride=32)(image=img_bgr)
    # Chuyển BGR -> RGB, HWC -> CHW
    img = img[:, :, ::-1].transpose(2, 0, 1)
    # Chuyển sang tensor float, normalize về [0, 1]
    img_tensor = torch.from_numpy(np.ascontiguousarray(img)).to(device).float() / 255.0
    return img_tensor.unsqueeze(0)  # Thêm batch dimension: (1, 3, 640, 640)
```

**Giải thích:**
- `LetterBox` resize ảnh `2560×1440` -> `640×360`, sau đó pad thêm pixel đen cho đủ `640×640`.
- `auto=False`: buộc resize cố định `640×640`, không tự điều chỉnh.
- `stride=32`: đảm bảo kích thước chia hết cho 32 (yêu cầu kiến trúc YOLO).

##### Bước 2: Forward pass qua model YOLO

File: [check_confidence.py](tools/check_confidence.py), dòng 158-162 (trong `main()`) và hàm `normalize_raw_pred_shape()` (dòng 60-64)

```python
model = YOLO("tools/best.pt").to(device)
model.model.eval()
names, nc = model.names, len(model.names)  # nc = 24 classes

img_tensor = preprocess_image(img0, IMG_SIZE)  # (1, 3, 640, 640)

with torch.no_grad():
    raw_pred = model.model(img_tensor)  # Forward pass trực tiếp qua backbone
    raw_pred = normalize_raw_pred_shape(raw_pred, nc)
    # raw_pred shape: (1, 28, 8400)
    #   - 28 = 4 (bbox xywh) + 24 (class scores)
    #   - 8400 = tổng số anchor positions trên feature maps
```

**Giải thích `normalize_raw_pred_shape`:**
```python
def normalize_raw_pred_shape(raw_pred, nc):
    raw_pred = raw_pred[0] if isinstance(raw_pred, (tuple, list)) else raw_pred
    if raw_pred.shape[1] == 4 + nc:  # (1, 28, 8400) - đúng format
        return raw_pred
    if raw_pred.shape[2] == 4 + nc:  # (1, 8400, 28) - cần transpose
        return raw_pred.permute(0, 2, 1)
    raise ValueError(f"Unexpected shape: {raw_pred.shape}")
```

- Output của model YOLO là 1 tensor chứa **8400 anchor** (các vị trí ứng viên trên ảnh).
- Mỗi anchor có **28 giá trị**: 4 giá trị bbox `(x_center, y_center, width, height)` + 24 giá trị class score (1 score cho mỗi class Leanbot).

##### Bước 3: Tách raw class scores và chạy NMS

File code: [check_confidence.py](tools/check_confidence.py), dòng 161-163 và hàm `run_nms()` (dòng 66-74)

```python
# Tách 4 cột bbox và 24 cột class scores
raw_boxes_xywh = raw_pred[0, :4, :].T        # (8400, 4) - tọa độ bbox
raw_class_scores = raw_pred[0, 4:4+nc, :].T   # (8400, 24) - confidence mỗi class

# NMS: lọc ra các bbox không trùng lặp
CONF_THRES = 0.05   # Ngưỡng confidence tối thiểu
IOU_THRES = 0.7      # Ngưỡng IoU để gộp box
MAX_DET = 300        # Số detection tối đa

def run_nms(raw_pred, nc):
    out = non_max_suppression(
        raw_pred.clone(),
        conf_thres=CONF_THRES,
        iou_thres=IOU_THRES,
        max_det=MAX_DET,
        nc=nc,
        return_idxs=True  # Trả về index anchor gốc
    )
    # out = (detections, kept_indices)
    # detections: (N, 6) với [x1, y1, x2, y2, best_conf, best_class_id]
    # kept_indices: (N,) - index của anchor gốc trong 8400 anchors
    return out[0][0], out[1][0]
```

**Giải thích:**
- `non_max_suppression` lọc 8400 anchors, giữ lại ~30 BBox tốt nhất (tùy ảnh).
- `return_idxs=True`: trả về **index gốc** của anchor trong tensor 8400, rất quan trọng để tra ngược lại 24 class scores.
- Nếu YOLO không hỗ trợ `return_idxs`, dùng fallback bằng IoU matching:

```python
# Fallback: tìm anchor gốc bằng IoU matching
ious = box_iou_numpy(np.array([x1, y1, x2, y2]), raw_boxes_xyxy_scaled)
raw_idx = int(np.argmax(ious))  # Anchor có IoU cao nhất với detection
```

##### Bước 4: Tra ngược 24 class scores cho mỗi BBox → Chọn top 9

File code: [export_markdown_report.py](tools/export_markdown_report.py), hàm `run_low_level_inference()` (dòng 303-364)

```python
def run_low_level_inference(model, frame, args):
    # ...


    # Sắp xếp detections theo confidence giảm dần
    sorted_indices = torch.argsort(detections_scaled[:, 4], descending=True)
    
    # args.max_objects = 9 → Chỉ giữ top 9 object
    if args.max_objects > 0:
        sorted_indices = sorted_indices[:args.max_objects]
    detections_scaled = detections_scaled[sorted_indices]

    for obj_id, det in enumerate(detections_scaled):
        x1, y1, x2, y2, best_conf, best_cls = map(float, det.cpu().numpy())
        best_cls_id = int(best_cls)

        # Tra ngược index anchor gốc
        if kept_idxs is not None:
            raw_idx = int(kept_idxs[obj_id])
        else:
            ious = box_iou_numpy(np.array([x1, y1, x2, y2]), raw_boxes_xyxy)
            raw_idx = int(np.argmax(ious))

        # LẤY 24 CLASS SCORES TỪ RAW TENSOR
        class_score_array = raw_class_scores[raw_idx].cpu().numpy()
        class_scores = {
            model_names[class_idx]: float(class_score_array[class_idx])
            for class_idx in range(nc)
        }
        # class_scores = {
        #     "Leanbot_0": 0.3298,
        #     "Leanbot_p15": 0.0178,
        #     "Leanbot_p30": 0.0021,
        #     ...  (tổng 24 class)
        # }

        detection_data.append({
            "obj_id": obj_id,
            "bbox_xyxy": (int(x1), int(y1), int(x2), int(y2)),
            "class_scores": class_scores,  # Dict 24 class → score
            "best_cls": model_names[best_cls_id],
            "best_conf": float(best_conf),
        })

    return detection_data  # List 9 detections, mỗi detection có 24 scores
```

**Tra ngược 24 class scores:**
- Sau NMS, mỗi detection chỉ còn `best_conf` và `best_class_id` (1 giá trị duy nhất).
- Nhưng vì cần **toàn bộ 24 class scores** nên phải dùng `raw_idx` (index anchor gốc) để truy ngược vào tensor `raw_class_scores[raw_idx]`.
- Kết quả: 1 mảng 24 phần tử, mỗi phần tử là confidence score cho 1 class Leanbot.

#### 1.4. Cách chọn 9 class scores để hiển thị trong bảng

- File code : [export_markdown_report.py](tools/export_markdown_report.py), hàm `select_top_display_groups()` (dòng 257-275)
- Mỗi object có **24 class scores**, nhưng bảng chỉ hiển thị **8 cột class** (giới hạn `MAX_TABLE_CLASS_COLUMNS = 8`). Cách chọn:

```python
MAX_TABLE_CLASS_COLUMNS = 8

def select_top_display_groups(detections, display_groups, group_reducer, limit=8):
    # Với mỗi class, lấy score cao nhất trong tất cả 9 detections
    ranked_groups = []
    for group in display_groups:  # 24 groups (mỗi group = 1 class)
        best_value = max(
            group_score(det["class_scores"], group, group_reducer)
            for det in detections
        )
        ranked_groups.append((best_value, group.label, group))
    
    # Sắp xếp giảm dần, lấy top 8 class
    ranked_groups.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [group for _, _, group in ranked_groups[:limit]]
```

- Chỉ 8 class nào có **best score cao nhất** trên toàn bộ 9 detections mới được hiển thị trong bảng. 16 class còn lại bị ẩn.






#### 1.7. Lệnh chạy

```powershell
# Chạy check_confidence trên ảnh toàn cảnh (chưa crop)
python tools/check_confidence.py `
  --input 24class_test_images `
  --output evaluate_crop_results
```

```powershell
# Chạy export_markdown_report với top 9 object
python tools/export_markdown_report.py `
  --source 24class_test_images `
  --output-dir evaluate_crop_results `
  --conf 0.05 `
```


## B. Khó khăn
- Không

## C. Công việc tiếp theo
- Tìm hiểu về phương pháp tính góc : `Vector Sum`
