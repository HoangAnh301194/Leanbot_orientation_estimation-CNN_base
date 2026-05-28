# Báo cáo công việc ngày 28/05/2026

## A.  Công việc đã làm

- Phân tích và định hướng chỉnh sửa loss cho YOLOv8 Detection trong bài toán Leanbot 24 class góc

## 1. Cấu hình training model hiện tại.

- Bài toán :
  - Object detection cho Leanbot.
  - Mỗi object vừa cần được phát hiện bằng bounding box, vừa cần được phân loại theo 24 class góc.
  - Các class góc trong `leanbot_data.yaml`:

```yaml
nc: 24
names:
  0: Leanbot_0
  1: Leanbot_p15
  2: Leanbot_p30
  3: Leanbot_p45
  4: Leanbot_p60
  5: Leanbot_p75
  6: Leanbot_p90
  7: Leanbot_p105
  8: Leanbot_p120
  9: Leanbot_p135
  10: Leanbot_p150
  11: Leanbot_p165
  12: Leanbot_p180
  13: Leanbot_p195
  14: Leanbot_m150
  15: Leanbot_m135
  16: Leanbot_m120
  17: Leanbot_m105
  18: Leanbot_m90
  19: Leanbot_m75
  20: Leanbot_m60
  21: Leanbot_m45
  22: Leanbot_m30
  23: Leanbot_m15
```

- Notebook hiện tại:
  - Cài `ultralytics`.
  - Tạo file `train.py`.
  - Tạo file `leanbot_data.yaml`.
  - Train bằng:

```python
from ultralytics import YOLO

model = YOLO("yolov8n.pt")
model.train(
    data=args.data,
    epochs=args.epochs,
    batch=args.batch,
    device=0,
    name=args.name,
    degrees=degrees,
    fliplr=fliplr,
    flipud=flipud,
)
```

- Mục tiêu cần đạt:
  - Không thay đổi bài toán detection thành classification thuần.
  - Không thay đổi format dataset YOLO hiện tại.
  - Chỉ can thiệp vào phần classification loss để đưa quan hệ hình học giữa các class góc vào quá trình học.
  - Giữ nguyên phần học bounding box

---

## 2. Các loss mặc định trong YOLOv8 Detection

Theo tài liệu/source chính thức của Ultralytics, `v8DetectionLoss` là criterion dùng cho YOLOv8 object detection. Trong phần tính loss, Ultralytics tạo tensor gồm 3 thành phần:

```python
loss = torch.zeros(3, device=self.device)  # box, cls, dfl
```

Do đó, với YOLOv8 detection, các loss chính gồm:

- `box_loss`
- `cls_loss`
- `dfl_loss`

Tổng loss có thể hiểu ở mức khái quát:

```text
total_loss = box_gain * box_loss
           + cls_gain * cls_loss
           + dfl_gain * dfl_loss
```

Trong source Ultralytics, sau khi tính từng thành phần, các loss được nhân với hệ số:

```python
loss[0] *= self.hyp.box  # box gain
loss[1] *= self.hyp.cls  # cls gain
loss[2] *= self.hyp.dfl  # dfl gain
```

### 2.1. `box_loss`

- Mục đích:
  - Đánh giá chất lượng định vị bounding box.
  - Phạt model nếu bbox dự đoán lệch so với bbox ground truth.

- Đối với bài toán Leanbot:
  - `box_loss` học vị trí và kích thước hộp bao Leanbot.

### 2.2. `cls_loss`

- Mục đích:
  - Đánh giá chất lượng phân loại class cho các prediction được gán với object.
  - Với dataset Leanbot, `cls_loss` học 24 class góc.

- Trong source Ultralytics, phần classification loss mặc định dùng:

```python
self.bce = nn.BCEWithLogitsLoss(reduction="none")
```

và được tính bằng:

```python
bce_loss = self.bce(pred_scores, target_scores.to(dtype))
loss[1] = bce_loss.sum() / target_scores_sum
```

- Trong đó:
  - `pred_scores`: logits/class scores do model dự đoán.
  - `target_scores`: target class scores được tạo sau quá trình assigner.
  - `fg_mask`: mask xác định prediction nào là foreground/positive.
  - `target_gt_idx`: chỉ số ground truth được gán cho từng positive prediction.

### 2.3. `dfl_loss`

- `DFL` là Distribution Focal Loss.
- Mục đích:
  - Hỗ trợ bbox regression bằng cách học phân phối khoảng cách từ prediction point đến các cạnh bbox.
  - Giúp việc định vị bbox chính xác hơn.
- Trong bài toán Leanbot:
  - `dfl_loss` vẫn thuộc nhóm loss phục vụ định vị bbox.


---

## 3. Tài liệu và nguồn trích dẫn

### 3.1. Ultralytics `v8DetectionLoss`

- Nguồn: Ultralytics documentation, `ultralytics/utils/loss.py`.
- Nội dung dùng để đối chiếu:
  - `v8DetectionLoss` là criterion cho YOLOv8 object detection.
  - Loss gồm 3 thành phần: `box`, `cls`, `dfl`.
  - Classification loss dùng `nn.BCEWithLogitsLoss(reduction="none")`.
  - `target_scores`, `fg_mask`, `target_gt_idx` được tạo sau bước assigner.
  - `loss[1]` là classification loss.
  - `box_loss` và `dfl_loss` nhận `target_scores` để làm trọng số cho bbox-related loss.

Link tài liệu:
- https://docs.ultralytics.com/reference/utils/loss/

### 3.2. PyTorch `BCEWithLogitsLoss`

- Nguồn: PyTorch documentation, `torch.nn.BCEWithLogitsLoss`.
- Nội dung dùng để đối chiếu:
  - `BCEWithLogitsLoss` kết hợp sigmoid và binary cross entropy trong một hàm.
  - Phù hợp cho bài toán binary hoặc multi-label, nơi mỗi class có thể được xem như một nhánh đúng/sai độc lập.
  - Có thể biểu diễn target toàn số 0, phù hợp cho background prediction trong detection.

Link tài liệu:
- https://docs.pytorch.org/docs/stable/generated/torch.nn.BCEWithLogitsLoss.html

### 3.3. PyTorch `CrossEntropyLoss`

- Nguồn: PyTorch documentation, `torch.nn.CrossEntropyLoss`.
- Nội dung dùng để đối chiếu:
  - Input của Cross Entropy là logits.
  - Target có thể là class index hoặc class probabilities.
  - Khi target là class probabilities, target cần có cùng shape với input.
  - Cross Entropy dùng logic softmax trên các class, tức là các class cạnh tranh nhau và tổng xác suất phân phối theo class bằng 1.
    - **Khái niệm Softmax** Hàm Softmax là một hàm toán học có tác dụng biến đổi một dãy các điểm số thô (logits) thành một phân phối xác suất. Các giá trị đầu ra của Softmax luôn nằm trong khoảng [0, 1] và tổng của chúng bắt buộc phải bằng 1. Điều này ép các class phải "cạnh tranh" với nhau (khi xác suất dự đoán của class này tăng lên thì xác suất của các class khác bắt buộc phải giảm xuống).
    - **Ví dụ:** Giả sử mô hình đưa ra điểm số thô (logits) cho 3 class là `[2.0, 1.0, 0.1]`. Nếu dùng hàm Sigmoid thông thường, các giá trị này sẽ độc lập với nhau. Nhưng khi đi qua hàm Softmax, các điểm số này sẽ được "ép" thành một phân phối xác suất tương ứng là `[0.66, 0.24, 0.10]`. Tổng xác suất bằng đúng 1 (0.66 + 0.24 + 0.10 = 1.0), trong đó class có điểm thô cao nhất sẽ "giành" được tỷ trọng phần trăm lớn nhất.

Link tài liệu:
- https://docs.pytorch.org/docs/stable/generated/torch.nn.CrossEntropyLoss.html

---

## 4. Vấn đề hạn chế khi toàn bộ BCE mặc định bằng Soft-label Cross Entropy

### 4.1. Bản chất của detection khác classification thuần

- Classification thuần:
  - Một ảnh hoặc một crop đầu vào thường tương ứng với một class.
  - Ví dụ: crop Leanbot đã biết có object, cần phân loại thành `p45`.
  - Cross Entropy phù hợp vì sample luôn thuộc một trong các class.

- Detection:
  - Model tạo rất nhiều prediction points trên ảnh.
  - Chỉ một phần nhỏ prediction points được gán với object thật.
  - Phần lớn prediction points là background.

Ví dụ khái quát:

```text
num_predictions = 8400

positive predictions: ( dự đoán dương tính - tức là dự đoán có chứa object Leanbot)
  - được gán với object Leanbot thật
  - cần học class góc

negative predictions: ( dự đoán âm tính - tức là dự đoán không chứa object Leanbot , là background của ảnh )
  - không được gán với object nào
  - là background
  - cần bị ép không dự đoán thành bất kỳ class Leanbot nào
```

### 4.2. BCE biểu diễn được background bằng target toàn số 0

Với 24 class Leanbot, một negative prediction có thể được biểu diễn bằng BCE như sau:

```text
target = [
  0, 0, 0, 0, 0, 0, 0, 0,
  0, 0, 0, 0, 0, 0, 0, 0,
  0, 0, 0, 0, 0, 0, 0, 0
]
```

Ý nghĩa:

- Prediction này không phải `Leanbot_0`.
- Prediction này không phải `Leanbot_p15`.
- Prediction này không phải `Leanbot_p30`.
- ...
- Prediction này không phải `Leanbot_m15`.

BCE phù hợp vì mỗi class được xem như một nhánh nhị phân độc lập:

```text
class_i: có / không
```

### 4.3. Cross Entropy không biểu diễn background nếu không có class background riêng

Cross Entropy yêu cầu target là một class index hoặc một phân phối xác suất trên các class.

Với 24 class góc:

```text
0, p15, p30, ..., m15
```

Nếu dùng CE, target phải mang ý nghĩa:

```text
sample thuộc một trong 24 class
```

Vấn đề hạn chế trong bài toán phân biệt góc Leanbot nhưu sau : 

- Negative prediction là background.
- Background không thuộc class góc nào.
- Nếu không có class thứ 25 là `background`, CE không có nhãn hợp lệ cho negative prediction.
- Nếu thực sự tạo class 25 là `background` thì gần như không thể, vì background rất đa dạng về hình ảnh và đặc trưng ( khi vị trí Leanbot thay đổi thì đặc trưng của Background cũng thay đổi theo) nên không thể gán 1 class duy nhất cho background.

Do đó, nếu thay toàn bộ BCE bằng CE cho tất cả prediction points:

- Các prediction background cũng bị ép thuộc một class góc nào đó.
- Model mất đi cơ chế rõ ràng để học "không có object".
- Dẫn đến Nguy cơ tăng false positive.
- Pipeline detection bị lệch khỏi thiết kế ban đầu là phát hiện Leanbot trên Background .

### 4.4. Soft-label CE chỉ hợp lý khi prediction đã là foreground

Soft-label CE theo góc phù hợp cho prediction đã được gán với Leanbot thật.

Ví dụ ground truth là `p45`:

```text
p30 = 0.10
p45 = 0.80
p60 = 0.10
```

Target này có ý nghĩa vì:

- Prediction đã biết là object Leanbot.
- Việc cần học là góc của object.
- Các class góc có quan hệ lân cận theo chu kỳ 360 độ.

Với background, không tồn tại góc thật. Vì vậy không thể tạo soft-label Gaussian theo góc cho negative prediction.

### 4.5. Thay `target_scores` toàn cục có thể ảnh hưởng đến bbox loss

Trong source Ultralytics, `target_scores` không chỉ dùng cho classification loss. Nó còn được truyền vào `bbox_loss`:

```python
loss[0], loss[2] = self.bbox_loss(
    pred_distri,
    pred_bboxes,
    anchor_points,
    target_bboxes / stride_tensor,
    target_scores,
    target_scores_sum,
    fg_mask,
    imgsz,
    stride_tensor,
)
```

**Khái niệm về `target_scores` trong YOLOv8:**
Trong kiến trúc của YOLOv8, `target_scores` (được tạo ra từ quá trình gán nhãn của `TaskAlignedAssigner`) không phải là nhãn cứng `0` và `1`. Nó là một ma trận điểm số được tính toán dựa trên sự kết hợp giữa nhãn class thực tế và độ khớp của bounding box (điểm IoU).
Về bản chất, `target_scores` đóng vai trò như một trọng số chất lượng (alignment metric). Khi được truyền vào `bbox_loss` và `dfl_loss`, nó giúp mô hình tập trung ưu tiên tối ưu hóa tọa độ cho những bounding box có dự đoán class tốt và IoU cao, đồng thời giảm bớt sự ảnh hưởng từ các bounding box có chất lượng kém.

Do đó:

- Không nên ghi đè `target_scores` gốc một cách toàn cục nếu chưa kiểm soát tác động.
- Cách an toàn hơn:
  - Giữ `target_scores` gốc cho `box_loss` và `dfl_loss`.
  - Tạo biến mới, ví dụ `soft_cls_targets`, chỉ dùng cho `cls_loss`.

### 4.6. Kết 

- Không nên thay toàn bộ BCE bằng CE một cách trực tiếp.

**Cách tối ưu:**

```text
Positive predictions:
  - Có object Leanbot thật.
  - Dùng Soft-label Cross Entropy theo góc.

Negative predictions:
  - Không có object.
  - Dùng BCE background để ép toàn bộ class score về 0.
```

Tức là:

```text
cls_loss_new = positive_soft_label_CE + negative_BCE_background
```

---

## 5. Phương án chỉnh sửa đề xuất

### 5.1. Giữ nguyên các phần không liên quan trực tiếp đến góc

Không chỉnh:

- `box_loss`
- `dfl_loss`
- bbox format
- file label YOLO
- `data.yaml`
- NMS/inference pipeline

Chỉ chỉnh:

- `cls_loss` trong `v8DetectionLoss`.

### 5.2. Tạo mapping class index sang góc

Với thứ tự class hiện tại, có thể dùng:

```python
class_angles = torch.arange(nc, device=device, dtype=dtype) * 15.0
```

Tương ứng:

```text
0      -> 0°
p15    -> 15°
p30    -> 30°
...
p195   -> 195°
m150   -> 210°
m135   -> 225°
...
m15    -> 345°
```

### 5.3. Tính khoảng cách góc theo chu kỳ

```python
def circular_distance(a, b):
    diff = (a - b).abs()
    return torch.minimum(diff, 360.0 - diff)
```

Ý nghĩa:

- `0°` gần `p15`.
- `0°` cũng gần `m15`.
- `p195` gần `p180` và `m150`.

### 5.4. Tạo soft-label Gaussian cho positive predictions

```python
def build_angular_soft_targets(
    gt_labels,
    target_gt_idx,
    fg_mask,
    target_scores,
    sigma=7.5,
):
    soft_target_scores = torch.zeros_like(target_scores)

    if fg_mask.sum() == 0:
        return soft_target_scores

    bs, num_predictions, nc = target_scores.shape
    device = target_scores.device
    dtype = target_scores.dtype

    class_angles = torch.arange(nc, device=device, dtype=dtype) * 15.0

    batch_idx = torch.arange(bs, device=device)[:, None].expand(bs, num_predictions)

    assigned_cls = gt_labels.squeeze(-1)[
        batch_idx[fg_mask],
        target_gt_idx[fg_mask]
    ].long()

    true_angles = class_angles[assigned_cls]

    d = circular_distance(
        true_angles[:, None],
        class_angles[None, :]
    )

    soft = torch.exp(-0.5 * (d / sigma) ** 2)
    soft = soft / soft.sum(dim=1, keepdim=True).clamp_min(1e-9)

    soft_target_scores[fg_mask] = soft

    return soft_target_scores
```

### 5.5. Positive loss: Soft-label Cross Entropy

```python
pos_logits = pred_scores[fg_mask]              # [num_pos, nc]
pos_targets = soft_cls_targets[fg_mask]        # [num_pos, nc]

loss_pos = F.cross_entropy(
    pos_logits,
    pos_targets.to(dtype),
    reduction="sum",
)
```


- `pos_logits` là logits, chưa qua softmax.
- `pos_targets` là phân phối xác suất mềm trên 24 class.
- Chỉ áp dụng cho positive predictions.

### 5.6. Negative loss: BCE background

```python
neg_logits = pred_scores[~fg_mask]
neg_targets = torch.zeros_like(neg_logits)

loss_neg = self.bce(
    neg_logits,
    neg_targets.to(dtype),
).sum()
```

Ghi chú:

- `neg_targets` toàn số 0.
- Mục đích là ép background không kích hoạt bất kỳ class Leanbot nào.

### 5.7. Classification loss mới

```python
target_scores_sum = max(target_scores.sum(), 1)

loss[1] = (loss_pos + loss_neg) / target_scores_sum
```

Trong đó:

- `target_scores_sum` vẫn lấy từ `target_scores` gốc.
- `target_scores` gốc vẫn dùng cho bbox-related loss.
- `soft_cls_targets` chỉ dùng cho classification loss.

---

## 6. Vị trí cần sửa trong code Ultralytics 

### 6.1. File cần can thiệp

Trong môi trường train, tìm file loss bằng:

```python
import ultralytics
import ultralytics.utils.loss as loss

print(ultralytics.__version__)
print(loss.__file__)
```

File thường có dạng:

```text
.../site-packages/ultralytics/utils/loss.py
```

### 6.2. Class cần can thiệp

Tìm class:

```python
class v8DetectionLoss:
```

### 6.3. Đoạn mặc định cần thay

Đoạn classification loss mặc định thường có dạng:

```python
target_scores_sum = max(target_scores.sum(), 1)

bce_loss = self.bce(pred_scores, target_scores.to(dtype))
if self.class_weights is not None:
    bce_loss *= self.class_weights
loss[1] = bce_loss.sum() / target_scores_sum
```

### 6.4. Thay bằng logic hybrid

Thay đoạn trên bằng logic:

```python
soft_cls_targets = self.build_angular_soft_targets(
    gt_labels=gt_labels,
    target_gt_idx=target_gt_idx,
    fg_mask=fg_mask,
    target_scores=target_scores,
    sigma=7.5,
)

target_scores_sum = max(target_scores.sum(), 1)

if fg_mask.sum():
    pos_logits = pred_scores[fg_mask]
    pos_targets = soft_cls_targets[fg_mask]
    pos_targets = pos_targets / pos_targets.sum(dim=1, keepdim=True).clamp_min(1e-9)

    loss_pos = F.cross_entropy(
        pos_logits,
        pos_targets.to(dtype),
        reduction="sum",
    )
else:
    loss_pos = pred_scores.sum() * 0.0

neg_logits = pred_scores[~fg_mask]
if neg_logits.numel():
    neg_targets = torch.zeros_like(neg_logits)
    loss_neg = self.bce(
        neg_logits,
        neg_targets.to(dtype),
    ).sum()
else:
    loss_neg = pred_scores.sum() * 0.0

loss[1] = (loss_pos + loss_neg) / target_scores_sum
```

Cần thêm:

```python
import torch.nn.functional as F
```

nếu file chưa có.



## 7. Các phương án thực nghiệm và đánh giá kết quả so sánh giữa Mặc định và chỉnh sửa lại Loss Function .

### 7.1. Hướng mặc định 

- Train bằng YOLOv8 mặc định.
- Không chỉnh loss.
- Lưu kết quả:
  - `box_loss`
  - `cls_loss`
  - `dfl_loss`
  - mAP
  - confusion matrix
  - angle error nếu có script riêng.

### 7.2. Hướng 1: Soft angular target với BCE

- Giữ BCE mặc định.
- Chỉ đổi target từ hard one-hot sang soft angular target.
- Mức can thiệp thấp.
- Không phải Soft-label CE đúng bản chất , nhưng cũng có ý tưởng học hỏi từ các góc gần đó.

### 7.3. Hướng 2: Hybrid loss

- Positive predictions:
  - Soft-label Cross Entropy theo góc.
- Negative predictions:
  - BCE background.
- Mức can thiệp trung bình.
- Phù hợp hơn với mục tiêu Soft-label Cross Entropy.
- Vẫn giữ cơ chế triệt background của detection.


## 8. Metric đánh giá sau khi sửa loss

Ngoài các metric đánh giá như `mAP` hoặc `accuracy`, nên  bổ sung các chỉ số theo góc:

- Top-1 class accuracy.
- Top-2 class accuracy.
- Mean Angular Error.
- Median Angular Error.
- Tỷ lệ mẫu có sai số góc nhỏ hơn hoặc bằng:
  - 15°
  - 30°
  - 45°
- Tỷ lệ top-2 prediction nằm gần nhau trong vòng:
  - 15°
  - 30°

Công thức sai số góc:

```python
def angular_error(pred_angle, true_angle):
    diff = abs(pred_angle - true_angle)
    return min(diff, 360.0 - diff)
```

---

## 9. Kết luận

- YOLOv8 detection mặc định sử dụng 3 loss chính:
  - `box_loss`
  - `cls_loss`
  - `dfl_loss`

- Trong bài toán Leanbot 24 class góc:
  - `box_loss` và `dfl_loss` phục vụ định vị bbox.
  - `cls_loss` là phần cần chỉnh để học quan hệ hình học giữa các góc.

- Không nên thay toàn bộ BCE classification loss bằng Soft-label Cross Entropy trực tiếp vì:
  - Detection có nhiều negative/background predictions.
  - Cross Entropy không biểu diễn được target background toàn số 0 nếu không có class background riêng.
  - Thay toàn bộ có thể làm model ép background vào một trong 24 class góc.
  - Nguy cơ tăng false positive và phá logic detection.
  - `target_scores` gốc còn được dùng cho bbox-related loss, nên không nên ghi đè toàn cục.

- Hai phương án chỉnh sửa (Custom Loss) được đề xuất:
  - Cả hai phương án đều giữ nguyên `box_loss` và `dfl_loss`, đồng thời tạo biến `soft_cls_targets` riêng biệt để tính `cls_loss` mà không làm ảnh hưởng đến `target_scores` gốc dùng cho bbox.
  - **Hướng 1 (Soft Angular Target với BCE):** Phương pháp an toàn, ít can thiệp. Giữ nguyên hàm BCE mặc định của YOLO nhưng thay đổi nhãn (từ Hard One-hot thành Soft Label dạng số thập phân) dựa trên khoảng cách góc.
  - **Hướng 2 (Hybrid Loss):** Phương pháp tối ưu và bám sát bản chất Soft-label Cross Entropy. Tách `cls_loss` thành 2 luồng riêng biệt:
    - Dùng Soft-label Cross Entropy cho các positive predictions (vật thể thật).
    - Dùng BCE cho các negative predictions (background) để giữ nguyên cơ chế triệt tiêu nhiễu nền của detection.

- Công thức tổng quát (Nếu triển khai theo Hướng 2 - Hybrid Loss):

```text
YOLO_loss = box_loss + dfl_loss + cls_loss_new

cls_loss_new = positive_soft_label_cross_entropy
             + negative_bce_background
```

## B. Khó khăn
- Không
## C. Công việc tiếp theo 
- Chờ xác nhận của Thầy về hướng áp dụng Soft label CE .
- Triển khai train lại model và đánh giá các metrics so sánh kết quả với cấu hình train mặc định