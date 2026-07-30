# Báo cáo công việc ngày 30/07/2026

## A. Công việc đã làm 
- Hướng dẫn anh Thế Anh chạy code Inference với Web cam 
  - Chỉ vướng một vài lỗi thư viện tương thích của python (đã cập nhật requirements.txt để install đúng)
- Chỉnh sửa lại code hiển thị ROI video zoom to Leanbot 
- Giảm FPS của camera 
- Train lại model YOLOv8n với dataset mới, chạy inference đánh giá

### 1. Chỉnh sửa code hiển thị ROI video 
- Code chỉnh sửa: [`tools/roi_tracking_dual_view_infer.py`](tools/roi_tracking_dual_view_infer.py).

- Thay đổi kích thước cửa sổ `ROI View` thành `600 x 600` thông qua hai biến `target_roi_w` và `target_roi_h`.
- Ảnh crop theo ROI tracking được resize về `600 x 600` để phóng to vùng chứa Leanbot, giúp quan sát hướng và trạng thái tracking rõ.

- Ảnh thực tế:

![Giao diện ROI tracking hai cửa sổ với ROI View 600x600](roi_tracking_dual_view_600x600.png)

### 2. Thiết lập lưu lượng frame của camera xuống 15 FPS
- Code chỉnh sửa: [`tools/roi_tracking_dual_view_infer.py`](tools/roi_tracking_dual_view_infer.py).

Sau khi khởi tạo camera và thiết lập độ phân giải, chương trình yêu cầu camera hoạt động ở mức `15 FPS`:

```python
cap = cv2.VideoCapture(source)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
cap.set(cv2.CAP_PROP_FPS, 15) # FPS set cho webcam = 15 fps
```

### 3. Train lại model với YOLOv8n

#### 3.1. Thông tin dataset

- Sử dụng dataset `180` ảnh đã build và chia tập ở buổi báo cáo ngày `28/07/2026`: [`../260728/datasets`](../260728/datasets).

| Thành phần | Số lượng | Ghi chú |
| :--- | ---: | :--- |
| Ảnh Leanbot gốc | `120` ảnh | `24` class, `5` ảnh/class, không có nhiễu |
| Ảnh Leanbot có nhiễu | `48` ảnh | `24` class, `2` ảnh/class, có các khối gỗ đỏ |
| Ảnh background negative | `12` ảnh | Không có Leanbot, label rỗng |
| **Tổng dataset** | **`180` ảnh** | `168` ảnh có Leanbot và `12` ảnh không có Leanbot |

Dataset được chia theo từng class để giữ phân bố dữ liệu giữa các tập:

| Tập dữ liệu | Số ảnh | Tỷ lệ thực tế |
| :--- | ---: | ---: |
| Train | `104` | `57.78%` |
| Validation | `51` | `28.33%` |
| Test | `25` | `13.89%` |

Quá trình chia dữ liệu sử dụng `n_test=max(1, floor(n*0.10))`, `n_val=max(1, ceil(n*0.20))` và lấy số ảnh còn lại làm tập train. Vì vậy:

- Mỗi class Leanbot có `7` ảnh được chia thành `4` ảnh train, `2` ảnh validation và `1` ảnh test.
- Nhóm `empty` có `12` ảnh được chia thành `8` ảnh train, `3` ảnh validation và `1` ảnh test.

#### 3.2. Thông tin training

Model được train bằng notebook [`tools/finetuning_yolo_Leanbot.ipynb`](tools/finetuning_yolo_Leanbot.ipynb), sử dụng model pretrained `yolov8n.pt`.

| Thông tin | Giá trị thực tế |
| :--- | :--- |
| Model nền tảng | `yolov8n.pt` - YOLOv8 Nano, pretrained |
| Task | Object Detection kết hợp phân loại hướng Leanbot |
| Số class | `24`, mỗi class cách nhau `15°` |
| Tổng dataset | `180` ảnh: `168` ảnh có Leanbot và `12` ảnh background negative |
| Dataset split | `104` ảnh train, `51` ảnh validation, `25` ảnh test |
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
##### Biểu đồ tổng hợp quá trình training

![YOLOv8n Leanbot training results](leanbot_colab/results.png)

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

- Chạy thử nghiệm inference với Leanbot chạy `5` vòng tròn liên tục:
```bash
python .\tools\roi_tracking_dual_view_infer.py `
  --source 1 `
  --mode roi `
  --full-model models\YOLOv8n_versions\FP16_NO_NMS\best_fp16_no_nms_imgsz640_openvino_model `
  --tracking-model models\YOLOv8n_versions\FP16_NO_NMS\best_fp16_no_nms_imgsz160_openvino_model `
  --device CPU `
  --width 1280 `
  --height 720 `
  --conf 0.1 `
  --roi_conf 0.1 `
  --topk 100 `
  --iou 0.5 `
  --mag-threshold 1.0 `
  --log "log_name.csv" `
  --show
```

#### Thử nghiệm `LbMotion.runLR(2000, 1000);`

- Ảnh inference thực tế:

![Leanbot inference với runLR 2000 1000](benchmark/leanbot_runlr_2000_1000_inference.png)

- Log CSV: [`roi_tracking_runlr_2000_1000.csv`](benchmark/roi_tracking_runlr_2000_1000.csv).
- Đồ thị trực quan hóa log:

![Biểu đồ log runLR 2000 1000](benchmark/roi_tracking_runlr_2000_1000.png)

- Quỹ đạo Oxy center và ellipse fit:

![Quỹ đạo Oxy runLR 2000 1000](benchmark/roi_tracking_runlr_2000_1000_oxy_trajectory.png)

#### Thử nghiệm `LbMotion.runLR(2000, 1300);`

- Ảnh inference thực tế:

![Leanbot inference với runLR 2000 1300](benchmark/leanbot_runlr_2000_1300_inference.png)

- Log CSV: [`roi_tracking_runlr_2000_1300.csv`](benchmark/roi_tracking_runlr_2000_1300.csv).
- Đồ thị trực quan hóa log:

![Biểu đồ log runLR 2000 1300](benchmark/roi_tracking_runlr_2000_1300.png)

- Quỹ đạo Oxy center và ellipse fit:

![Quỹ đạo Oxy runLR 2000 1300](benchmark/roi_tracking_runlr_2000_1300_oxy_trajectory.png)

#### Thử nghiệm `LbMotion.runLR(2000, 1600);`

- Ảnh inference thực tế:

![Leanbot inference với runLR 2000 1600](benchmark/leanbot_runlr_2000_1600_inference.png)

- Log CSV: [`roi_tracking_runlr_2000_1600.csv`](benchmark/roi_tracking_runlr_2000_1600.csv).
- Đồ thị trực quan hóa log:

![Biểu đồ log runLR 2000 1600](benchmark/roi_tracking_runlr_2000_1600.png)

- Quỹ đạo Oxy center và ellipse fit:

![Quỹ đạo Oxy runLR 2000 1600](benchmark/roi_tracking_runlr_2000_1600_oxy_trajectory.png)

#### So sánh quỹ đạo Oxy center của ba lần chạy

- Lệnh chạy:

```powershell
python .\tools\plot_oxy_trajectory.py `
  .\benchmark `
  --out-dir .\benchmark `
  --multi `
  --dpi 120
```
![So sánh quỹ đạo Oxy center theo tốc độ Leanbot](benchmark/combined_multi_oxy_trajectory.png)





## B. Khó khăn 
- Không
## C. Công việc tiếp theo 
- Em xin phép nhận hướng đi tiếp theo từ Thầy ạ 
