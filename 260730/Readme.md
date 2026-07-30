# Báo cáo công việc ngày 30/07/2026

## A. Công việc đã làm 
- Hướng dẫn anh Thế Anh chạy code Inference với Web cam 
  - Chỉ vướng một vài lỗi thư viện tương thích của python (đã cập nhật requirements.txt để install đúng)
- Chỉnh sửa lại code hiển thị ROI video zoom to Leanbot 
- Giảm FPS của camera 
- Train lại Model Yolov8n với dataset mới, chạy Inference đánh giá

### 1. Chỉnh sửa code hiển thị ROI video 
- 

### 2. Sửa code ép lưu lượng Frame ảnh của Cam xuống 15 FPS 

### 3. Train lại model với YOLOv8n

#### 3.1. Thông tin dataset

- Sử dụng lại dataset `180` ảnh đã build và chia tập ở buổi báo cáo ngày `28/07/2026`: [`../260728/datasets`](../260728/datasets).
- Dataset gồm `24` class hướng Leanbot, mỗi class cách nhau `15°`.

| Thành phần | Số lượng | Ghi chú |
| :--- | ---: | :--- |
| Ảnh Leanbot gốc | `120` ảnh | `24` class, `5` ảnh/class, không có vật cản đỏ |
| Ảnh Leanbot có nhiễu | `48` ảnh | `24` class, `2` ảnh/class, có các khối gỗ đỏ |
| Ảnh background negative | `12` ảnh | Không có Leanbot, label rỗng |
| **Tổng dataset** | **`180` ảnh** | `168` ảnh có Leanbot và `12` ảnh không có Leanbot |

Dataset được chia theo từng class để giữ phân bố dữ liệu giữa các tập:

| Tập dữ liệu | Số ảnh | Tỷ lệ thực tế |
| :--- | ---: | ---: |
| Train | `104` | `57.78%` |
| Validation | `26` | `14.44%` |
| Test | `50` | `27.78%` |

> Tỷ lệ thực tế khác tỷ lệ mục tiêu `70% - 20% - 10%` do mỗi class chỉ có `7` ảnh và quá trình chia được thực hiện riêng theo từng class bằng phép lấy phần nguyên.

#### 3.2. Thông tin training

Model được train bằng notebook [`tools/finetuning_yolo_Leanbot.ipynb`](tools/finetuning_yolo_Leanbot.ipynb), sử dụng trọng số pretrained `yolov8n.pt`.

| Thông tin | Giá trị thực tế |
| :--- | :--- |
| Model nền tảng | `yolov8n.pt` - YOLOv8 Nano, pretrained |
| Task | Object Detection kết hợp phân loại hướng Leanbot |
| Số class | `24`, mỗi class cách nhau `15°` |
| Tổng dataset | `180` ảnh: `168` ảnh có Leanbot và `12` ảnh background negative |
| Dataset split | `104` ảnh train, `26` ảnh validation, `50` ảnh test |
| Số epoch | `150` |
| Batch size | `16` |
| Image size | `640 x 640` |
| Optimizer | `auto` |
| Learning rate | `lr0=0.01`, `lrf=0.01` |
| Momentum / weight decay | `0.937` / `0.0005` |
| Warmup | `3` epochs |
| Augmentation chính | `degrees=10.0`, `translate=0.1`, `scale=0.5`, `mosaic=1.0` |
| Flip augmentation | `fliplr=0.0`, `flipud=0.0` để không làm sai nhãn góc |
| Close mosaic | Tắt mosaic trong `10` epoch cuối |
| Mixed precision | `amp=true` |
| Seed / deterministic | `seed=0`, `deterministic=true` |
| Môi trường | Google Colab, GPU `device=0` |
| Thời gian training | `363.950 s`, tương đương khoảng `6 phút 04 giây` |
| Output | [`leanbot_colab`](leanbot_colab/) |
| Best model | [`leanbot_colab/weights/best.pt`](leanbot_colab/weights/best.pt) |
| Last model | [`leanbot_colab/weights/last.pt`](leanbot_colab/weights/last.pt) |

Các file kết quả chính:

- [`args.yaml`](leanbot_colab/args.yaml): toàn bộ cấu hình training.
- [`results.csv`](leanbot_colab/results.csv): loss và metric theo `150` epoch.
- [`results.png`](leanbot_colab/results.png): biểu đồ tổng hợp quá trình training.
- [`confusion_matrix.png`](leanbot_colab/confusion_matrix.png) và [`confusion_matrix_normalized.png`](leanbot_colab/confusion_matrix_normalized.png): ma trận nhầm lẫn.
- [`BoxP_curve.png`](leanbot_colab/BoxP_curve.png), [`BoxR_curve.png`](leanbot_colab/BoxR_curve.png), [`BoxF1_curve.png`](leanbot_colab/BoxF1_curve.png), [`BoxPR_curve.png`](leanbot_colab/BoxPR_curve.png): các đường đánh giá theo confidence.
- [`labels.jpg`](leanbot_colab/labels.jpg), [`train_batch0.jpg`](leanbot_colab/train_batch0.jpg), [`train_batch980.jpg`](leanbot_colab/train_batch980.jpg): kiểm tra dữ liệu và augmentation.
- [`val_batch0_labels.jpg`](leanbot_colab/val_batch0_labels.jpg) và [`val_batch0_pred.jpg`](leanbot_colab/val_batch0_pred.jpg): so sánh label thật với kết quả dự đoán.

#### 3.3. Kết quả training

Nguồn metric chính: [`leanbot_colab/results.csv`](leanbot_colab/results.csv).

Epoch có `mAP50-95` và fitness tốt nhất là epoch `140`:

| Metric tại epoch `140` | Giá trị |
| :--- | ---: |
| `metrics/precision(B)` | `0.60517` |
| `metrics/recall(B)` | `0.86585` |
| `metrics/mAP50(B)` | `0.78773` |
| `metrics/mAP50-95(B)` | `0.67907` |
| `train/box_loss` | `0.61929` |
| `train/cls_loss` | `2.48286` |
| `train/dfl_loss` | `0.90142` |
| `val/box_loss` | `0.64164` |
| `val/cls_loss` | `2.28386` |
| `val/dfl_loss` | `0.93678` |

Metric ở epoch cuối (`epoch=150`):

| Metric | Giá trị |
| :--- | ---: |
| `train/box_loss` | `0.58119` |
| `train/cls_loss` | `2.34112` |
| `train/dfl_loss` | `0.89115` |
| `metrics/precision(B)` | `0.59991` |
| `metrics/recall(B)` | `0.84416` |
| `metrics/mAP50(B)` | `0.77338` |
| `metrics/mAP50-95(B)` | `0.66374` |
| `val/box_loss` | `0.64985` |
| `val/cls_loss` | `2.33549` |
| `val/dfl_loss` | `0.94900` |
| Learning rate | `5.9262e-06` |

Giá trị tốt nhất trong toàn bộ quá trình train:

| Metric | Best value | Epoch | Ghi chú |
| :--- | ---: | ---: | :--- |
| `metrics/precision(B)` | `0.60902` | `111` | Precision cao nhất |
| `metrics/recall(B)` | `0.96759` | `10` | Recall cao sớm, khi Precision còn thấp |
| `metrics/mAP50(B)` | `0.79025` | `142` | mAP tại IoU `0.5` cao nhất |
| `metrics/mAP50-95(B)` | `0.67907` | `140` | Metric chính để chọn `best.pt` |
| `train/box_loss` | `0.54103` | `147` | Loss bbox train thấp nhất |
| `train/cls_loss` | `2.34097` | `148` | Loss class train thấp nhất |
| `train/dfl_loss` | `0.86310` | `147` | Loss DFL train thấp nhất |
| `val/box_loss` | `0.63609` | `138` | Loss bbox validation thấp nhất |
| `val/cls_loss` | `2.28189` | `141` | Loss class validation thấp nhất |
| `val/dfl_loss` | `0.91051` | `3` | Loss DFL validation thấp nhất |

##### Biểu đồ tổng hợp quá trình training

![YOLOv8n Leanbot training results](leanbot_colab/results.png)

- Các loss train giảm ổn định trong toàn bộ `150` epoch; loss validation giảm mạnh ở giai đoạn đầu và ổn định từ khoảng epoch `80`.
- `mAP50` và `mAP50-95` tăng đều, đạt mức tốt nhất quanh epoch `140` rồi dao động nhẹ ở các epoch cuối.
- Recall cao hơn Precision khá nhiều. Model bắt được phần lớn Leanbot nhưng vẫn còn dự đoán dư hoặc nhận nhầm class hướng.
- Nên sử dụng [`best.pt`](leanbot_colab/weights/best.pt) thay vì `last.pt` cho bước export và inference.

##### Phân bố label và dữ liệu augmentation

![YOLOv8n Leanbot labels distribution](leanbot_colab/labels.jpg)

Ảnh batch ở giai đoạn đầu, khi mosaic và augmentation còn hoạt động:

![YOLOv8n first training batch](leanbot_colab/train_batch0.jpg)

Ảnh batch gần cuối quá trình training, khi mosaic đã được tắt bởi `close_mosaic=10`:

![YOLOv8n final training batch](leanbot_colab/train_batch980.jpg)

##### Precision, Recall, F1 và PR curve

![YOLOv8n Leanbot Box F1 curve](leanbot_colab/BoxF1_curve.png)

- F1 tổng hợp cao nhất đạt khoảng `0.68` tại confidence `0.764`.

![YOLOv8n Leanbot Box Precision curve](leanbot_colab/BoxP_curve.png)

![YOLOv8n Leanbot Box Recall curve](leanbot_colab/BoxR_curve.png)

![YOLOv8n Leanbot Box PR curve](leanbot_colab/BoxPR_curve.png)

##### Ma trận nhầm lẫn

![YOLOv8n Leanbot normalized confusion matrix](leanbot_colab/confusion_matrix_normalized.png)

![YOLOv8n Leanbot confusion matrix](leanbot_colab/confusion_matrix.png)

- Ma trận nhầm lẫn còn phân tán nhiều ngoài đường chéo, cho thấy model chưa phân biệt ổn định `24` class góc gần nhau.
- Các class cách nhau `15°` có đặc trưng hình ảnh tương tự, trong khi tập validation chỉ có `1` ảnh/class, nên tỷ lệ chuẩn hóa dao động mạnh khi một object bị dự đoán sai.
- Kết quả hiện tại phù hợp để tiếp tục chạy inference thực tế, nhưng cần kiểm tra thêm hiện tượng dự đoán chồng lặp và sai class hướng.

##### So sánh label thật và ảnh prediction

Ground truth của batch validation:

![YOLOv8n Leanbot validation labels](leanbot_colab/val_batch0_labels.jpg)

Kết quả prediction của model:

![YOLOv8n Leanbot validation predictions](leanbot_colab/val_batch0_pred.jpg)

- **Export model FP16 OpenVINO static 640 & 160**
```bash
python tools/export_openvino_fp16.py --model models/YOLOv8n_versions/FP16_NO_NMS/best.pt --imgsz 640 --no-nms

python tools/export_openvino_fp16.py --model models/YOLOv8n_versions/FP16_NO_NMS/best.pt --imgsz 160 --no-nms
```
- Chạy thửu nghiệm Inference với Leanbot chạy 5 vòng tròn liên tục 
```bash
python .\tools\roi_tracking_dual_view_infer.py `
  --source 1 `
  --mode roi `
  --device CPU `
  --width 1280 `
  --height 720 `
  --conf 0.1 `
  --roi_conf 0.1`
  --topk 100 `
  --iou 0.5 `
  --mag-threshold 1.0 `
  --log "roi_tracking_dual_debug.csv" `
  --show
```
  - Tốc độ di chuyển : `LbMotion.runLR(2000, 1000);`
    - Log csv : []()
    - Đồ thị trực quan hóa.
  - Tốc độ di chuyển : `LbMotion.runLR(2000, 1200);`
    - Log csv : []()
    - Đồ thị trực quan hóa.
  - Tốc độ di chuyển : `LbMotion.runLR(2000, 1500);`
    - Log csv : []()
    - Đồ thị trực quan hóa.
- ĐỒ thị quỹ đạo Oxy_center của các lần chạy : 


## B. Khó khăn 
- Không
## C. Công việc tiếp theo 
- Em xin phép nhận hướng đi tiếp theo từ Thầy ạ 
