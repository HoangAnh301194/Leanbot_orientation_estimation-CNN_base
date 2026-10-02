# Tổng hợp tài liệu bàn giao công việc

## A. Các nội dung

Tài liệu bàn giao được chia thành 3 phần chính:

- Thu thập dữ liệu ảnh và Build Dataset.
- Training và export OpenVINO FP16 model.
- Chạy inference và các tính năng hiện có.

### 1. Thu thập dữ liệu ảnh và Build Dataset

Phần này mô tả toàn bộ pipeline dữ liệu từ lúc chụp ảnh tới khi tạo dataset dùng cho training.

Nội dung chi tiết gồm:

- Thu thập background và ảnh Leanbot theo từng session bằng [`capture_session.py`](tools/capture_session.py).
- Auto-label theo cặp background/raw image bằng [`process_auto_label_paired.py`](tools/process_auto_label_paired.py).
- Các module hỗ trợ auto-label:
  - [`auto_label_core.py`](tools/auto_label_core.py)
  - [`abstract_hsv.py`](tools/abstract_hsv.py)
  - [`alignment.py`](tools/alignment.py)
  - [`mask_roi.py`](tools/mask_roi.py)
- Gộp các session thành dataset YOLO chung bằng [`build_dataset.py`](tools/build_dataset.py).
- Dataset hiện tại dùng cho model:
  - [`datasets.zip`](datasets.zip)
- Thu thêm dữ liệu khi ROI tracking thất bại bằng:
  - [`lost_tracking_collector.py`](LeanbotTinyRC_AI_PIDControl/lost_tracking_collector.py)
- Kiểm tra pseudo-label trong `check_labels/` trước khi sử dụng.
- Gộp lost-tracking samples đã kiểm tra vào dataset chung bằng:
  - [`merge_lost_tracking_dataset.py`](tools/merge_lost_tracking_dataset.py)

Tài liệu chi tiết:

- [01_DATASET_PIPELINE.md](docs/01_DATASET_PIPELINE.md)

Pipeline tổng quát:

```text
Camera
  ↓
capture_session.py
  ↓
raw_image/
  ↓
process_auto_label_paired.py
  ↓
tool1_output_paired/
  ↓
build_dataset.py
  ↓
datasets/
  ↓
Training

Runtime --save-lost
  ↓
lost_tracking_dataset/
  ↓
Review check_labels/
  ↓
merge_lost_tracking_dataset.py
  ↓
datasets_with_lost_tracking/
  ↓
Training lại model
```

### 2. Training và export OpenVINO FP16 model

Phần này mô tả quy trình training model YOLO11n với 24 class góc, đánh giá kết quả và export sang OpenVINO FP16.

Nội dung chi tiết gồm:

- Notebook training:
  - [`Leanbot_Train_SoftBCE.ipynb`](tools/Leanbot_Train_SoftBCE.ipynb)
- Dataset:
  - [`datasets.zip`](datasets.zip)
- Model nền:
  - `yolo11n.pt`
- 24 class hướng, mỗi class cách nhau 15 độ.
- Soft Angular BCE để giữ quan hệ tuần hoàn giữa các class góc.
- Training trên Google Colab GPU.
- Thông số training chính:
  - 150 epochs.
  - batch size 16.
  - image size 640.
  - tắt horizontal/vertical flip để bảo toàn hướng.
- Các metric cần kiểm tra:
  - Precision.
  - Recall.
  - mAP50.
  - mAP50-95.
  - confusion matrix.
- Export `best.pt` sang OpenVINO FP16 bằng:
  - [`export_openvino_fp16.py`](tools/export_openvino_fp16.py)
- Runtime sử dụng hai model no-NMS:
  - [OpenVINO FP16 640](models/yolo11n_latest_version/best_fp16_no_nms_imgsz640_openvino_model/)
  - [OpenVINO FP16 160](models/yolo11n_latest_version/best_fp16_no_nms_imgsz160_openvino_model/)

Tài liệu chi tiết:

- [02_TRAINING_AND_EXPORT.md](docs/02_TRAINING_AND_EXPORT.md)

Pipeline tổng quát:

```text
datasets.zip
  ↓
Leanbot_Train_SoftBCE.ipynb
  ↓
YOLO11n + Soft Angular BCE
  ↓
best.pt
  ↓
export_openvino_fp16.py
  ├── FP16 640 no-NMS
  └── FP16 160 no-NMS
  ↓
models/yolo11n_latest_version/
```

### 3. Chạy inference và các tính năng hiện có

Phần này mô tả runtime camera AI, ước lượng hướng, smoothing và điều khiển Leanbot tới target.

Code chính:

- [`leanbotCameraController.py`](LeanbotTinyRC_AI_PIDControl/leanbotCameraController.py)

Các module runtime:

- [`PID_controller.py`](LeanbotTinyRC_AI_PIDControl/PID_controller.py): điều khiển vị trí và heading.
- [`angle_smoothing.py`](LeanbotTinyRC_AI_PIDControl/angle_smoothing.py): smoothing model angle, trajectory angle và fused angle.
- [`lost_tracking_collector.py`](LeanbotTinyRC_AI_PIDControl/lost_tracking_collector.py): lưu sample khi lost tracking.
- [`check_confidence.py`](tools/check_confidence.py): xử lý output detection và bbox.
- [`LeanbotTinyRC/`](LeanbotTinyRC_AI_PIDControl/LeanbotTinyRC/): giao tiếp BLE với Leanbot.
- [`target_config.json`](LeanbotTinyRC_AI_PIDControl/target_config.json): cấu hình target đã lưu.

Các chức năng chính:

- Hybrid inference:
  - FULL detection bằng model 640x640.
  - ROI tracking bằng model 160x160.
- Ước lượng hướng bằng score-weighted vector trên 24 class.
- Smoothing:
  - model angle.
  - trajectory angle.
  - fused angle theo vận tốc.
- Set Target bằng phím `T`.
- Start navigation bằng phím `S`.
- PID theo các phase:
  - Phase 1: Aligning.
  - Phase 2: Driving.
  - Phase 3: Final Aligning.
  - Phase 4: Forward/Backward verification.
- Tự chọn đi tiến hoặc lùi dựa trên sai số heading ban đầu.
- Lost tracking và fallback từ ROI sang FULL detection.
- Thu thêm lost-tracking dataset bằng `--save-lost`.
- Đo heading bằng quỹ đạo với phím `M`.
- Manual capture, pause, cancel và logging.

Tài liệu chi tiết:

- [03_INFERENCE_AND_CONTROL.md](docs/03_INFERENCE_AND_CONTROL.md)

Lệnh chạy cơ bản:

```powershell
cd .\LeanbotTinyRC_AI_PIDControl

python .\leanbotCameraController.py `
  --source 1 `
  --show `
  --ble <BLE_ID>
```

Lệnh chạy có thu lost-tracking data:

```powershell
python .\leanbotCameraController.py `
  --source 1 `
  --show `
  --save-lost `
  --ble <BLE_ID>
```

## B. Cấu trúc thư mục bàn giao

```text
Leanbot_Camera_AI_Control_FINAL/
│
├── Readme.md
├── requirements.txt
├── datasets.zip
│
├── docs/
│   ├── 01_DATASET_PIPELINE.md
│   ├── 02_TRAINING_AND_EXPORT.md
│   └── 03_INFERENCE_AND_CONTROL.md
│
├── tools/
│   ├── capture_session.py
│   ├── process_auto_label_paired.py
│   ├── auto_label_core.py
│   ├── abstract_hsv.py
│   ├── alignment.py
│   ├── mask_roi.py
│   ├── build_dataset.py
│   ├── merge_lost_tracking_dataset.py
│   ├── Leanbot_Train_SoftBCE.ipynb
│   ├── export_openvino_fp16.py
│   ├── check_confidence.py
│   └── experiments/
│
├── models/
│   └── yolo11n_latest_version/
│       ├── best_fp16_no_nms_imgsz640_openvino_model/
│       └── best_fp16_no_nms_imgsz160_openvino_model/
│
└── LeanbotTinyRC_AI_PIDControl/
    ├── leanbotCameraController.py
    ├── PID_controller.py
    ├── angle_smoothing.py
    ├── lost_tracking_collector.py
    ├── target_config.json
    └── LeanbotTinyRC/
```

## C. Cài đặt môi trường

Từ thư mục `Leanbot_Camera_AI_Control_FINAL`:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r .\requirements.txt
```

Các package chính trong `requirements.txt`:

```text
opencv-python
numpy
pandas
ultralytics
openvino
matplotlib
psutil
bleak>=0.21.0
pyyaml>=6.0
```

## D. Thứ tự đọc tài liệu

Để tái tạo toàn bộ pipeline từ đầu:

1. [01_DATASET_PIPELINE.md](docs/01_DATASET_PIPELINE.md)
2. [02_TRAINING_AND_EXPORT.md](docs/02_TRAINING_AND_EXPORT.md)
3. [03_INFERENCE_AND_CONTROL.md](docs/03_INFERENCE_AND_CONTROL.md)

Ba tài liệu tương ứng với ba giai đoạn:

```text
Data
  ↓
Training / Deployment
  ↓
Inference / Control
```
