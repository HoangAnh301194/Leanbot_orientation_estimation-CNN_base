# Báo cáo nguyên lý Check_confidence.py (Tập trung vào NMS & Trích xuất Confidence)

---

## 1. Tổng quan
- **Mục đích**: Trích xuất và hiển thị confidence score của **tất cả các class** cho mỗi vật thể nhận diện được.

## 2. Mục đích sử dụng NMS

- Lấy kết quả dự đoán thô (Raw Predictions) trước khi qua NMS, sau đó chạy NMS để lấy các vật thể được giữ lại, và dùng Index map ngược lại để lấy toàn bộ phân bố xác suất của 8 class.

## 3. Chi tiết quá trình xử lý NMS và Trích xuất Confidence

### 3.1. Lấy dữ liệu Raw (Trước NMS)
YOLO trả về `raw_pred` chứa hàng ngàn bounding box dự đoán. Đoạn code trích xuất dữ liệu:
```python
# img_tensor.shape = [1, 3, 640, 640]
with torch.no_grad():
    # Model trả về tensor shape [1, 12, số_lượng_anchors]
    raw_pred = normalize_raw_pred_shape(model.model(img_tensor), nc)

# Tách riêng tọa độ và confidence
raw_boxes_xywh = raw_pred[0, :4, :].T           # Tọa độ các box dự đoán
raw_class_scores = raw_pred[0, 4:4 + nc, :].T   # Confidence của cả 8 class cho mỗi box
```
Ví dụ 1 vector `raw_class_scores[i]`: `[0.82, 0.05, 0.00, 0.00, 0.12, 0.00, 0.00, 0.00]`
 
### 3.2. Quá trình lọc NMS (Non-Maximum Suppression)
NMS được gọi qua hàm `run_nms(raw_pred, nc)` để loại các hộp trùng lặp:
1. **Lọc CONF_THRES**: Bỏ các box có max confidence `< 0.05`.
2. **Lọc IOU_THRES**: Sắp xếp các box theo confidence giảm dần. Nếu 2 box trùng lên nhau (IoU > 0.7), xóa box có confidence thấp hơn.

Đoạn code gọi NMS:
```python
# Gọi hàm NMS của Ultralytics
detections, kept_idxs = run_nms(raw_pred, nc)
```

Hàm trả về:
- `detections`: Các hộp (box) được giữ lại, bao gồm tọa độ và `best_class_id`.
- `kept_idxs`: Vị trí (index) của các hộp đó trong mảng `raw_class_scores` ban đầu.

### 3.3. Trích xuất Confidence (Matching)
Để lấy mảng 8 confidence cho từng `detection`, ta dùng `kept_idxs` duyệt từng phần tử và ánh xạ về `raw_class_scores`:

```python
# Duyệt qua các bbox được giữ lại sau NMS
for obj_id, det in enumerate(detections_scaled):
    x1, y1, x2, y2, best_conf, best_cls = map(float, det.cpu().numpy())
    best_cls = int(best_cls)

    if kept_idxs is not None:
        # Lấy index trực tiếp từ NMS
        raw_idx = int(kept_idxs[obj_id])
    else:
         
        # Tìm raw box có độ khớp tọa độ (IoU) cao nhất
        ious = box_iou_numpy(np.array([x1, y1, x2, y2]), raw_boxes_xyxy_scaled)
        raw_idx = int(np.argmax(ious))

    # Trích xuất confidence của toàn bộ 8 class
    class_scores = raw_class_scores[raw_idx].cpu().numpy()
    # từ class_scores có thể dùng để vẽ lên ảnh các thôgn tin confidence 
```

## 4. Chi tiết logic gọi NMS và in log phân bố xác suất P(xyz)

### 4.1. Hàm gọi NMS (`run_nms`)

```python
def run_nms(raw_pred, nc):
    try:
        # Cố gắng lấy both detections và indices (bản Ultralytics mới)
        out = non_max_suppression(raw_pred.clone(), conf_thres=CONF_THRES, 
                                  iou_thres=IOU_THRES, max_det=MAX_DET, 
                                  nc=nc, return_idxs=True)
        if isinstance(out, tuple) and len(out) == 2:
            return out[0][0], out[1][0]
        return out[0], None
    except TypeError:
        # Nếu hàm không nhận tham số return_idxs (bản cũ), chỉ lấy detections
        out = non_max_suppression(raw_pred.clone(), conf_thres=CONF_THRES, 
                                  iou_thres=IOU_THRES, max_det=MAX_DET, nc=nc)
        return out[0][0] if isinstance(out, tuple) else out[0], None
```

### 4.2. Code in thông tin P(xyz) ra Text Log
Sau khi đã lấy được mảng `class_scores` chứa 8 giá trị xác suất, script dùng vòng lặp để ghi từng giá trị ra file log `_debug.txt`:

```python 
# Mảng debug_lines dùng để lưu nội dung file log
for cls_id, score in enumerate(map(float, class_scores)):
    # Đánh dấu <-- BEST cho class có confidence cao nhất
    marker = " <-- BEST" if cls_id == best_cls else ""
    
    # Định dạng mỗi dòng: {id} - {tên class}: {xác suất}
    debug_lines.append(f"  {cls_id} - {names[cls_id]}: {score:.4f}{marker}")
```

---

## 5. Kết quả (Output)

Với mỗi vật thể được giữ lại, file log `_debug.txt` hiển thị:
```text
Object 0 | Best: Leanbot_right (Conf: 0.8234)
Bbox (xyxy): (100.0, 200.0, 300.0, 400.0) | Match: return_idxs

  0 - Leanbot_front: 0.0523
  1 - Leanbot_right: 0.8234 <-- BEST
  2 - Leanbot_back: 0.0001
  ...
```
Đồng thời vẽ BBox lên ảnh và lưu lại (`debug_{image_name}.jpg`). Các bbox của các class khác nhau (nếu confidence > 0) có thể được vẽ chồng lên nhau để phân tích trực quan.

---

## 6. Các thông số cấu hình chính
- `CONF_THRES = 0.05`: Ngưỡng confidence tối thiểu để NMS duyệt box.
- `IOU_THRES = 0.7`: Mức độ chồng lấn (Overlap) để NMS tiến hành xóa box có conf thấp hơn.
- `CLASS_DRAW_THRES = 0.0`: Ngưỡng để quyết định có vẽ bbox của một class lên ảnh debug hay không (0.0 = vẽ tất cả các class model predict > 0).
