# 2. Training và Export OpenVINO FP16 Model

Tài liệu này mô tả quy trình huấn luyện model YOLO11n cho 24 class góc Leanbot, đánh giá kết quả và export model sang OpenVINO FP16 để sử dụng trong runtime.

## 2.1. Các file sử dụng

- [`Leanbot_Train_SoftBCE.ipynb`](../tools/Leanbot_Train_SoftBCE.ipynb): notebook training chính.
- [`datasets.zip`](../datasets.zip): dataset dùng cho model hiện tại.
- [`export_openvino_fp16.py`](../tools/export_openvino_fp16.py): export model `.pt` sang OpenVINO FP16.
- [Model OpenVINO 640](../models/yolo11n_latest_version/best_fp16_no_nms_imgsz640_openvino_model/): model FULL detection.
- [Model OpenVINO 160](../models/yolo11n_latest_version/best_fp16_no_nms_imgsz160_openvino_model/): model ROI tracking.

## 2.2. Dataset dùng để training

Model hiện tại được train lại ngày 11/09/2026 với dataset gồm:

- 204 ảnh 640x640.
- 192 ảnh có Leanbot.
- 12 ảnh negative background.
- 1.728 bounding box.
- 24 class góc, mỗi class cách nhau 15 độ.

File dataset:

- [`datasets.zip`](../datasets.zip)

Nếu đã bổ sung lost-tracking samples bằng [`merge_lost_tracking_dataset.py`](../tools/merge_lost_tracking_dataset.py), có thể tạo một file zip dataset mới và dùng file đó thay cho `datasets.zip`.

## 2.3. Chuẩn bị Google Colab

Notebook được thiết kế để chạy trên Google Colab với GPU.

Upload các file sau lên Colab:

- `Leanbot_Train_SoftBCE.ipynb`
- `datasets.zip`

Trong notebook, dataset được giải nén và chia thành các tập:

```text
datasets/
├── train/
│   ├── images/
│   └── labels/
├── val/
│   ├── images/
│   └── labels/
└── test/
    ├── images/
    └── labels/
```

Notebook chia dữ liệu theo class để hạn chế mất cân bằng giữa các góc.

## 2.4. File cấu hình YOLO

Notebook tạo file `leanbot_data.yaml` với 24 class:

```yaml
path: /content/datasets
train: train/images
val: val/images
test: test/images

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

## 2.5. Model nền và Soft Angular BCE

Model nền:

```python
model = YOLO("yolo11n.pt")
```

Bài toán dùng 24 class hướng liên tiếp theo vòng tròn. Vì vậy notebook thay BCE mặc định bằng Soft Angular BCE.

Với class đúng có góc `theta`, target của các class lân cận được làm mềm theo khoảng cách góc vòng tròn:

```text
d = min(|theta_i - theta_j|, 360 - |theta_i - theta_j|)
```

Trọng số target được tính theo Gaussian:

```text
soft = exp(-0.5 * (d / sigma)^2)
```

Notebook hiện dùng:

```text
sigma = 15 degrees
```

Cách này giữ quan hệ tuần hoàn giữa các class, ví dụ:

```text
0° gần 15°
0° cũng gần 345°
```

## 2.6. Thông số training hiện tại

Lệnh training trong notebook:

```python
!python train.py --epochs 150 --batch 16
```

Các thông số chính:

```text
Base model     : yolo11n.pt
Epochs         : 150
Batch size     : 16
Image size     : 640
Device         : GPU
Degrees        : 10.0
Horizontal flip: 0.0
Vertical flip  : 0.0
Soft BCE sigma : 15°
```

Flip bị tắt vì lật ảnh sẽ làm thay đổi ý nghĩa hướng của Leanbot.

## 2.7. Output sau training

Ultralytics lưu kết quả mặc định trong:

```text
/content/runs/detect/leanbot_colab/
```

Các file cần lưu lại:

```text
weights/
├── best.pt
└── last.pt

results.csv
results.png
confusion_matrix.png
confusion_matrix_normalized.png
BoxP_curve.png
BoxR_curve.png
BoxF1_curve.png
BoxPR_curve.png
```

Model dùng để export là:

```text
best.pt
```

## 2.8. Các metric cần kiểm tra

Các chỉ số chính:

- Precision.
- Recall.
- mAP50.
- mAP50-95.
- Confusion matrix.

Với bài toán góc, confusion matrix cần được kiểm tra thêm theo quan hệ class lân cận. Sai lệch giữa hai class cách nhau 15 độ có ý nghĩa khác với nhầm sang một class cách xa nhiều góc.

Kết quả model train ngày 11/09/2026:

```text
mAP50     ≈ 0.9398
mAP50-95  ≈ 0.8061
Precision ≈ 0.7943
Recall    ≈ 0.9286
```

## 2.9. Tải model `best.pt` từ Colab

Notebook có cell tải:

```python
from google.colab import files

best_model = '/content/runs/detect/leanbot_colab/weights/best.pt'
files.download(best_model)
```

Sau khi tải về, đặt `best.pt` ở một thư mục tạm hoặc thư mục model để export.

## 2.10. Export OpenVINO FP16

Script:

- [`export_openvino_fp16.py`](../tools/export_openvino_fp16.py)

Script hỗ trợ hai kích thước input:

```text
160
640
```

Runtime hiện dùng model no-NMS, vì phần grouping/NMS được xử lý trong code Python.

### Export model 640

Từ thư mục `Leanbot_Camera_AI_Control_FINAL`:

```powershell
python .\tools\export_openvino_fp16.py `
  --model .\best.pt `
  --imgsz 640 `
  --no-nms
```

### Export model 160

```powershell
python .\tools\export_openvino_fp16.py `
  --model .\best.pt `
  --imgsz 160 `
  --no-nms
```

Output có dạng:

```text
best_fp16_no_nms_imgsz640_openvino_model/
best_fp16_no_nms_imgsz160_openvino_model/
```

Mỗi OpenVINO IR cần ít nhất:

```text
model.xml
model.bin
metadata.yaml
```

Không được chỉ copy file `.xml`; `.bin` chứa weights của model.

## 2.11. Vị trí model trong project

Runtime mặc định tìm model ở:

- [FULL 640](../models/yolo11n_latest_version/best_fp16_no_nms_imgsz640_openvino_model/)
- [ROI 160](../models/yolo11n_latest_version/best_fp16_no_nms_imgsz160_openvino_model/)

Cấu trúc:

```text
models/
└── yolo11n_latest_version/
    ├── best_fp16_no_nms_imgsz640_openvino_model/
    │   ├── best_fp16_no_nms_imgsz640.xml
    │   ├── best_fp16_no_nms_imgsz640.bin
    │   └── metadata.yaml
    │
    └── best_fp16_no_nms_imgsz160_openvino_model/
        ├── best_fp16_no_nms_imgsz160.xml
        ├── best_fp16_no_nms_imgsz160.bin
        └── metadata.yaml
```

## 2.12. Vai trò hai model trong runtime

```text
Camera frame
    │
    ├── FULL detection
    │      model 640x640
    │      dùng để tìm lại Leanbot trên toàn frame
    │
    └── ROI tracking
           model 160x160
           dùng khi đã có ROI quanh Leanbot
```

Model 640 ưu tiên phạm vi tìm kiếm toàn ảnh. Model 160 giảm kích thước input để phục vụ tracking ROI với chi phí inference thấp hơn.

## 2.13. Quy trình retrain sau khi bổ sung dữ liệu

```text
Dataset gốc
    │
    + Lost-tracking samples đã review
    │
    ↓
merge_lost_tracking_dataset.py
    ↓
datasets_with_lost_tracking/
    ↓
zip dataset
    ↓
Leanbot_Train_SoftBCE.ipynb
    ↓
best.pt
    ↓
export_openvino_fp16.py
    ├── 640 FP16 no-NMS
    └── 160 FP16 no-NMS
    ↓
thay model trong models/yolo11n_latest_version/
```
