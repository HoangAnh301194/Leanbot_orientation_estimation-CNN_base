# Báo cáo công việc ngày 17/07/2026

## Mục lục
- [A. Công việc đã làm](#a-công-việc-đã-làm)
  - [1. Thu thập thêm ảnh nhiễu không có Leanbot](#1-thu-thập-thêm-ảnh-nhiễu-không-có-leanbot)
  - [2. Training với dataset mới và kết quả](#2-training-với-dataset-mới-và-kết-quả)
    - [2.1. Thông tin training](#21-thông-tin-training)
    - [2.2. Kết quả training](#22-kết-quả-training)
  - [3. Triển khai model chạy Inference](#3-triển-khai-model-chạy-inference)
- [B. Khó khăn](#b-khó-khăn)
- [C. Công việc tiếp theo](#c-công-việc-tiếp-theo)

---
## A. Công việc đã làm
- Thu thập thêm ảnh nền, không có Leanbot 
- Tiến hành bổ sung dataset , báo cáo thông tin training
- Báo cáo kết quả sau training.
- Chạy inference model và đánhg giá kết quả.
### 1. Thu thập thêm ảnh nhiễu không có Leanbot 
- Bối cảnh thu thập thêm ảnh : 
    - Vẫn là ảnh sa bàn 
    - Thêm các khối gỗ màu gây nhiễu ( có đỏ và cam , đặt ở nhiều góc độ, tình trạng ngẫu nhiên)
    - Đặt thêm các linh kiện rời vào sa bàn ( PCB LbBase, LbSide, SRF-05, bánh xe, servo, stepper, gripper, JDY-33, LbStepper, Arduino Nano) 
    - Vì các linh kiện đỏ dễ nhầm sang Leanbot hơn nên em đã ưu tiên đặt các vật màu đỏ vào để chụp ạ.

- Thông tin bộ dataset hiện tại 

| Số class | Số ảnh mỗi class | Tổng lượng ảnh | Ảnh nhiễu nền đã chụp |
|:---:|:---:|:---:|:---:|
| 24 | 5 | 120 | 12 |

- Theo thông tin khuyến nghị của [Ultralytics - Tips for Best Training Results](https://docs.ultralytics.com/yolov5/tutorials/tips-for-best-training-results#model-selection), ảnh background nên chiếm khoảng `0–10%` tổng số ảnh trong dataset.
> Tổng lượng ảnh nền chụp thêm chiếm khoảng `10%` so với bộ data gốc = 12 ảnh ( 120/10 ).

- Folder ảnh chụp thêm : [`no_leanbot/backgrounds`](raw_image/no_leanbot/backgrounds)
- Các ảnh chụp thêm như sau:

|  |  |
|:---:|:---:|
| ![0](raw_image/no_leanbot/backgrounds/background_000.jpg) | ![1](raw_image/no_leanbot/backgrounds/background_001.jpg) |
| ![2](raw_image/no_leanbot/backgrounds/background_002.jpg) | ![3](raw_image/no_leanbot/backgrounds/background_003.jpg) |
| ![4](raw_image/no_leanbot/backgrounds/background_004.jpg) | ![5](raw_image/no_leanbot/backgrounds/background_005.jpg) |
| ![6](raw_image/no_leanbot/backgrounds/background_006.jpg) | ![7](raw_image/no_leanbot/backgrounds/background_007.jpg) |
| ![8](raw_image/no_leanbot/backgrounds/background_008.jpg) | ![9](raw_image/no_leanbot/backgrounds/background_009.jpg) |
| ![10](raw_image/no_leanbot/backgrounds/background_010.jpg) | ![11](raw_image/no_leanbot/backgrounds/background_011.jpg) |


- Sau khi thu thập thêm 12 ảnh , tiến hành bổ sung thêm dataset theo các bước :     
    - Crop center --> 1600x1440
    - Padding --> 1600x1600 
    - resize --> 640x640
    - Bổ sung vào folder `datasets\images` với `.txt` label trống nhãn. 
## 2. Training với dataset mới và kết quả. 

### 2.1. Thông tin training

#### 2.1.1. Thông tin dataset

| Thông tin | Giá trị |
|:---|:---|
| Dataset | Leanbot 24 class góc quay, bổ sung ảnh nền không có Leanbot |
| Thư mục dataset | [`datasets`](datasets) |
| Tổng số ảnh | `132` ảnh |
| Ảnh có Leanbot | `120` ảnh |
| Ảnh nền không có Leanbot | `12` ảnh, chiếm `9.09%` tổng dataset (`12/132`) |
| Tổng số class | `24` |
| Số ảnh mỗi class | `5` ảnh/class |
| Khoảng cách class góc | `15°` |
| Định dạng ảnh/nhãn | `.jpg` / YOLO `.txt` |
| Nhãn ảnh nền | File `.txt` rỗng, không chứa bounding box |
| Kích thước sau tiền xử lý | `640 x 640` pixel |
| Quy trình tiền xử lý | Crop center `1600 x 1440` → padding `1600 x 1600` → resize `640 x 640` |
| Kiểm tra số file | `132` ảnh, `132` nhãn; `120` nhãn có object, `12` nhãn rỗng |
| File cấu hình trên Colab | `leanbot_data.yaml` |
| Dataset split | Artifact trả về chưa chứa `leanbot_data.yaml`, chưa xác minh được số ảnh train/validation/test |

> Ảnh nền không tạo class mới. Nhãn rỗng giúp model học phân biệt Leanbot với vật gây nhiễu và giảm False Positive.

#### 2.1.2. Cấu hình training thực tế

- Nguồn cấu hình: [`leanbot_colab/args.yaml`](leanbot_colab/args.yaml) 
- Model sau train : [`leanbot_colab/weights/best.pt`](leanbot_colab/weights/best.pt)

| Thông số | Giá trị thực tế |
|:---|:---|
| Model nền tảng | `yolo11n.pt` pretrained |
| Epochs | `150` |
| Batch size | `16` |
| Image size | `640 x 640` |
| Optimizer | `auto` |
| Initial learning rate (`lr0`) | `0.01` |
| Final learning-rate factor (`lrf`) | `0.01` |
| Seed | `0` |
| Workers | `8` |
| Device | GPU `0` |
| Validation | Bật, dùng split `val` |
| Validation IoU | `0.7` |
| Max detections | `300` |
| Box loss gain | `7.5` |
| Classification loss gain | `0.5` |
| DFL loss gain | `1.5` |
| Custom classification loss | Soft Angular BCE, `sigma=15.0` |

#### 2.1.3. Custom loss Soft Angular BCE

| Nội dung | Cấu hình |
|:---|:---|
| File triển khai | [`tools/train_soft_bce.py`](tools/train_soft_bce.py) |
| Loss gốc | BCE cho classification target |
| Loss chỉnh sửa | Soft Angular BCE |
| Vị trí chỉnh sửa | Bọc `v8DetectionLoss.bce` bằng `SoftBCEWithLogitsLoss` |
| Phần được chỉnh | Classification loss/class target |
| Phần giữ nguyên | Box loss và DFL loss mặc định |
| Sigma | `15.0` |
| Ánh xạ góc | `class_id × 15°` |
| Khoảng cách góc | `min(abs(a-b), 360-abs(a-b))` |
| Mục đích | Làm mềm target sang class góc lân cận, giúp model học quan hệ góc liên tục |

```text
soft_target(d) = exp(-0.5 × (d / sigma)²) × original_iou_score
```

#### 2.1.4. Data augmentation 

| Augmentation | Giá trị |
|:---|---:|
| `degrees` | `10.0` | 
| `translate` | `0.1` |
| `scale` | `0.5` |
| `mosaic` | `1.0` |
| `hsv_h` | `0.015` |
| `hsv_s` | `0.7` |
| `hsv_v` | `0.4` |
| `auto_augment` | `randaugment` |
| `erasing` | `0.4` |


#### 2.1.5. Môi trường train và thông tin model sau train

| Thông tin | chi tiết |
|:---|:---|
| Ultralytics | `8.4.98` |
| GPU | Device `0`  |
| Kiến trúc model | `YOLO11n` - Object Detection |
| Số class đầu ra | `24` class góc Leanbot |
| Kích thước input đánh giá | `640 x 640` |
| Số layer | `182` layers theo `model.info()` |
| Số parameters | `2,594,520` parameters, khoảng `2.59M` |
| Số gradients trong checkpoint | `0` khi load checkpoint để inference |
| Độ phức tạp tính toán | `6.465 GFLOPs`|
| Detection strides | `[8, 16, 32]` pixel |
| Tổng thời gian training | `306.728 s`, khoảng `5.11` phút |
| Thời gian trung bình mỗi epoch | Khoảng `2.045 s/epoch` |
| Output training | [`leanbot_colab`](leanbot_colab) |
| Best checkpoint | [`leanbot_colab/weights/best.pt`](leanbot_colab/weights/best.pt) |
| Last checkpoint | [`leanbot_colab/weights/last.pt`](leanbot_colab/weights/last.pt) |
| Kích thước `best.pt` | `5,494,042` bytes, khoảng `5.24 MiB` |
| Kích thước `last.pt` | `5,494,042` bytes, khoảng `5.24 MiB` |

### 2.2. Kết quả training

Nguồn metric: [`leanbot_colab/results.csv`](leanbot_colab/results.csv)

#### 2.2.1. Biểu đồ tổng hợp quá trình training

![Kết quả loss và metric theo epoch](leanbot_colab/results.png)


#### 2.2.2. Phân bố nhãn dataset

![Phân bố class và bounding box trong dữ liệu training](leanbot_colab/labels.jpg)

#### 2.2.3. Confusion matrix

**Confusion matrix theo số lượng:**

![Confusion matrix](leanbot_colab/confusion_matrix.png)

**Confusion matrix chuẩn hóa:**

![Normalized confusion matrix](leanbot_colab/confusion_matrix_normalized.png)


#### 2.2.4. Precision, Recall, F1 và PR curves

**F1 theo confidence:**

![Box F1 curve](leanbot_colab/BoxF1_curve.png)

**Precision theo confidence:**

![Box Precision curve](leanbot_colab/BoxP_curve.png)

**Recall theo confidence:**

![Box Recall curve](leanbot_colab/BoxR_curve.png)

**Precision-Recall curve:**

![Box Precision Recall curve](leanbot_colab/BoxPR_curve.png)

#### 2.2.5. Ảnh batch đầu và cuối quá trình training

| Batch đầu | Batch cuối |
|:---:|:---:|
| ![Train batch 0](leanbot_colab/train_batch0.jpg) | ![Train batch 700](leanbot_colab/train_batch700.jpg) |
| ![Train batch 1](leanbot_colab/train_batch1.jpg) | ![Train batch 701](leanbot_colab/train_batch701.jpg) |
| ![Train batch 2](leanbot_colab/train_batch2.jpg) | ![Train batch 702](leanbot_colab/train_batch702.jpg) |

#### 2.2.6. So sánh ground truth và prediction trên validation

| Ground truth | Prediction |
|:---:|:---:|
| ![Validation labels](leanbot_colab/val_batch0_labels.jpg) | ![Validation predictions](leanbot_colab/val_batch0_pred.jpg) |

> Ảnh nền nhiễu không bị detect ra Leanbot --> Model học được cách phân biệt Leanbot với vật gây nhiễu và giảm False Positive.


### 3. Triển khai model chạy Inference 

#### 3.1 Export model Yolo11n OpenVINO FP16 Quantization 
- Code sử dụng : [`tools/export_openvino_fp16.py`](tools/export_openvino_fp16.py)
- Lệnh sử dụng : 
    - Model không có NMS Layer : 
        - Static 640x640:
        ```bash
        python tools/export_openvino_fp16.py --model leanbot_colab/weights/best.pt --imgsz 640 --no-nms
        ```
        - Static 160x160:
        ```bash
        python tools/export_openvino_fp16.py --model leanbot_colab/weights/best.pt --imgsz 160 --no-nms
        ```

- Output model : Tự động sinh ra nằm cùng thư mục với file model gốc `.pt` : [`leanbot_colab/weights/best_fp16_no_nms_imgsz160_openvino_model/`](leanbot_colab/weights/best_fp16_no_nms_imgsz160_openvino_model/)


#### 3.2 Chạy Inference và đánh giá kết quả.
- Chạy Leanbot 5 vòng liên tục, bán kính rộng hơn : 
```cpp
    #include <Leanbot.h>

    const int TURN_ANGLE_DEG = 370;

    void setup() {
    Leanbot.begin();
    LbMission.begin(TB1A + TB1B);

    Leanbot.tone(1500, 200);
    delay(1000);
    }

    void loop() {

        LbMotion.runLR(1200, 2000);
        LbMotion.waitRotationDeg(TURN_ANGLE_DEG);
        LbMotion.stopAndWait();
        delay(1000);
        LbMission.end() ;
    }
```
- Code chạy Inference : [`tools/roi_tracking_baseline_infer.py`](tools/roi_tracking_baseline_infer.py)
- Độ phân giải đầu vào : **1920x1080**.
- Ngưỡng lọc confidence : ```detected = best_conf >= 0.25```
- Lệnh chạy :

```bash
python tools/roi_tracking_baseline_infer.py --source 1 --mode roi --show --full-model leanbot_colab/weights/best_fp16_no_nms_imgsz640_openvino_model --tracking-model leanbot_colab/weights/best_fp16_no_nms_imgsz160_openvino_model --log leanbot_colab/roi_tracking_log.csv --conf 0.25 --topk 200 --iou 0.5 --min-mag 2.0
``` 

- Output log csv : [`leanbot_colab/roi_tracking_log.csv`](leanbot_colab/roi_tracking_log.csv)

#### 3.3. Đánh giá quá trình Tracking (Biểu đồ)

Sau khi thu được file CSV từ quá trình Inference, dưới đây là các biểu đồ phân tích chi tiết được vẽ bởi tool `plot_single_comprehensive.py`:

**1. Biểu đồ Góc quay và Tọa độ tâm (Trajectory)**
![Trajectory & Angle](leanbot_colab/plots/1_trajectory.png)

**2. Biểu đồ CPU Load**
![CPU Load](leanbot_colab/plots/2_cpu_load.png)

**3. Biểu đồ FPS**
![FPS](leanbot_colab/plots/3_fps.png)

**4. Biểu đồ Inference vs End-to-End**
![Time Barchart](leanbot_colab/plots/4_time_barchart.png)

**5. Biểu đồ Thời điểm Tracking Lost**
![Tracking Lost](leanbot_colab/plots/5_tracking_lost.png)

**6. Ảnh thực tế triển khai**
![alt text](image.png)


> Thực tế triển khai thì Model sau khi export lại detect kém rất nhiều, mặc dù em đã thử giảm best_conf threshold xuống còn `0.05` nhưng vẫn không detect được Leanbot. 

Dưới đây là một số frame hình ghi nhận tình trạng Tracking Lost trong quá trình Inference:

| Ảnh Toàn cảnh (Frame) | Ảnh cắt (ROI) |
| :---: | :---: |
| ![Frame](leanbot_colab/lost_tracking_captures/lost_frame_2517_16-58-21-172_ROI_frame.png) | ![ROI](leanbot_colab/lost_tracking_captures/lost_frame_2517_16-58-21-172_ROI_roi.png) |
| ![Frame](leanbot_colab/lost_tracking_captures/lost_frame_2523_16-58-21-545_ROI_frame.png) | ![ROI](leanbot_colab/lost_tracking_captures/lost_frame_2523_16-58-21-545_ROI_roi.png) |
| ![Frame](leanbot_colab/lost_tracking_captures/lost_frame_2537_16-58-22-213_ROI_frame.png) | ![ROI](leanbot_colab/lost_tracking_captures/lost_frame_2537_16-58-22-213_ROI_roi.png) |
| ![Frame](leanbot_colab/lost_tracking_captures/lost_frame_2684_16-58-27-954_ROI_frame.png) | ![ROI](leanbot_colab/lost_tracking_captures/lost_frame_2684_16-58-27-954_ROI_roi.png) |

## B. Khó khăn 
- Model khi triển khai thì hiệu quả detection kém, em chưa tìm được nguyên nhân lỗi ạ. 
## C. Công việc tiếp theo 
- Trước mắt em sẽ thử train lại và export lại rồi test riêng Model OpenVINO FP16 để debug confidence xem có lỗi không ạ . 
- Em xin phép nhận hướng đi tiếp theo ạ.