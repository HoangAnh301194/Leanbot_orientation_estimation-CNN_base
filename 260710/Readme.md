# Báo cáo công việc ngày 09/07/2026

## A. Công việc đã làm
- Chỉnh sửa lại code, thực hiện đúng pipeline để đánh giá Full frame model và ROI tracking model .
- Thử giảm Camera resolution từ 2K (2560x1440) xuống 1280x720 và đánh giá kết quả. 


### 1. Pipeline xử lí . 
#### 1.1 **Baseline Model Full frame ( 640x640 )**
- Link code thực hiện: [tools/roi_tracking_baseline_infer.py](tools/roi_tracking_baseline_infer.py)
- Lệnh chạy:
```bash
python tools/roi_tracking_baseline_infer.py --mode baseline --source 1 --log log_baseline_2k.csv --show
```
- Log csv: [benchmark/log_baseline_2k.csv](benchmark/log_baseline_2k.csv)

- Luồng xử lí: Camera 2560x1440 → center crop 1440x1440 → resize 640x640 → Full model static 640x640 → restore bbox về tọa độ ảnh gốc 2560x1440. 

#### 1.2 **ROI Tracking model ( 160x160 )**
- Link code thực hiện: [tools/roi_tracking_baseline_infer.py](tools/roi_tracking_baseline_infer.py)
- Lệnh chạy:
```bash
python tools/roi_tracking_baseline_infer.py --mode roi --source 1 --log log_roi_tracking_2k.csv --show
```
- Log csv: [benchmark/log_roi_tracking_2k.csv](benchmark/log_roi_tracking_2k.csv) *(sẽ tạo sau khi chạy ROI Tracking)*
- Lệnh vẽ đồ thị:
```bash
python tools/plot_log.py benchmark/log_roi_tracking_2k.csv
```
- Luồng xử lí: Full model khởi tạo bbox → tính ROI vuông NxN trên ảnh gốc 2560x1440 → crop ROI → resize 160x160 → Tracking model static 160x160 → restore bbox về ảnh gốc → cập nhật ROI mỗi frame.
- Flowchart chi tiết của ROI tracking:
  ```mermaid
  flowchart TD
      A[Frame gốc 2560x1440] --> B{Đã có bbox từ frame trước?}

      B -- Chưa có / tracking lost --> C[Chạy Full model 640x640 để khởi tạo lại bbox]
      C --> D[Bbox ảnh gốc 2560x1440]

      B -- Đã có bbox --> E[Tính ROI vuông từ bbox frame trước]
      D --> E

      E --> F[Crop ROI vuông NxN từ frame gốc 2560x1440]
      F --> G[Resize ROI về 160x160]
      G --> H[Tracking model static 160x160 detect]
      H --> I{Detect được Leanbot?}

      I -- Có --> J[Bbox trong hệ tọa độ 160x160]
      J --> K[Scale bbox về ROI gốc NxN]
      K --> L[Cộng offset ROI để về tọa độ ảnh gốc 2560x1440]
      L --> M[Cập nhật bbox mới]
      M --> N[Cập nhật ROI cho frame tiếp theo]

      I -- Không --> O[tracking_lost = 1]
      O --> P[Lưu frame gốc + ROI debug]
      P --> Q[Reset ROI]
      Q --> C
  ```
      

#### 1.3 Benchmark 2 model Baseline Full frame model vs ROI Tracking model
- Thực hiện đánh giá 2 model với Camera chạy realtime với Leanbot chạy vòng tròn. 
- Link code thực hiện vẽ đồ thị: 
  - [tools/roi_tracking_baseline_infer.py](tools/roi_tracking_baseline_infer.py)
  - [tools/plot_log.py](tools/plot_log.py)

- Link log csv:
  - Baseline Full frame: [benchmark/log_baseline_2k.csv](benchmark/log_baseline_2k.csv)
  - ROI Tracking: [benchmark/log_roi_tracking_2k.csv](benchmark/log_roi_tracking_2k.csv) *(sẽ tạo sau khi chạy ROI Tracking)*

- Lệnh vẽ đồ thị cho toàn bộ log trong thư mục `benchmark`:
```bash
python tools/plot_log.py benchmark
```
- Đồ thị đánh giá : 

**Đồ thị CPU load**:

<!-- Thêm ảnh đồ thị CPU load tại đây -->

**Đồ thị FPS**:

<!-- Thêm ảnh đồ thị FPS tại đây -->

**Đồ thị Inference time**:

<!-- Thêm ảnh đồ thị inference time tại đây -->

**Đồ thị End-to-end processing time**:

<!-- Thêm ảnh đồ thị tổng thời gian xử lý tại đây -->

**Đồ thị Angle theo thời gian**:

<!-- Thêm ảnh đồ thị angle/unwrapped angle tại đây -->

**Đồ thị X-Y center theo thời gian**:

<!-- Thêm ảnh đồ thị x_center và y_center tại đây -->

**Đồ thị số frame lost tracking**:

<!-- Thêm ảnh hoặc bảng thống kê tracking_lost tại đây -->

**Bảng so sánh tổng hợp Baseline vs ROI Tracking**:

| Metric | Baseline Full frame 640x640 | ROI Tracking 160x160 | Nhận xét |
|---|---:|---:|---|
| FPS trung bình |  |  |  |
| CPU load trung bình |  |  |  |
| Inference time trung bình |  |  |  |
| End-to-end time trung bình |  |  |  |
| Số frame tracking lost |  |  |  |

#### 1.4 Thử đánh giá lại với độ phân giải giảm từ 2k (2560x1440) xuống 1280x720.
- Link code thực hiện: [tools/roi_tracking_baseline_infer.py](tools/roi_tracking_baseline_infer.py)
- Chỉnh sửa code: sau khi benchmark 2K ổn định, đổi cấu hình camera trong `tools/roi_tracking_baseline_infer.py` từ `2560x1440` sang `1280x720`, rồi chạy lại cùng 2 lệnh Baseline/ROI.
```python
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
``` 
- Full model vẫn phải dùng `training_style_crop_pad(frame)` để center crop về ảnh vuông trước khi resize 640x640, tránh resize trực tiếp 1280x720 về 640x640 làm méo ảnh.
- Các bước biến đổi kích thước frame ảnh :
  - Baseline Full frame Model : 1280x720
  - Full model : 1280x720 → center crop 720x720 → resize 640x640 → YOLO detect → bbox 640x640 → scale về 720x720 → cộng offset về 1280x720
  - ROI Tracking Model : 1280x720 → crop ROI vuông NxN → resize 160x160 → YOLO detect → bbox 160x160 → scale về ROI NxN → cộng offset ROI về 1280x720
    


## B. Khó khăn 

## C. Công việc tiếp theo 

### Checklist công việc ngày 10/07/2026

#### Mục tiêu
- Chạy lại pipeline ROI Tracking theo đúng xác nhận của Thầy với kích thước ảnh gốc 2K (2560x1440) trước.
- Sau khi pipeline 2K chạy ổn định, chỉnh sửa và đánh giá lại với kích thước camera 1280x720.

#### Pipeline cần triển khai trước với ảnh 2K (2560x1440)
- Frame đầu tiên hoặc khi chưa có `center_x`, `center_y`: dùng Full model static 640x640 để detect Leanbot trên toàn frame.
- Frame gốc vẫn giữ theo pipeline giống `webcam_infer.py` / `webcam_vector_infer.py`: lấy frame từ camera 2K, sau đó dùng `training_style_crop_pad()` để tạo ảnh 640x640 cho Full model.
- Kết quả bbox từ Full model 640x640 phải được restore về tọa độ ảnh gốc 2560x1440 bằng `restore_boxes_from_training_style()`.
- Từ bbox ảnh gốc, tính `center_x`, `center_y`, `width`, `height`.
- Frame tiếp theo: dùng bbox frame trước để tạo ROI hình vuông trên ảnh gốc 2560x1440.
- Crop ROI trực tiếp từ frame gốc 2560x1440, resize ROI một lần về 160x160, đưa vào Tracking model static 160x160.
- Kết quả bbox từ Tracking model 160x160 phải được unresize và cộng offset ROI để chuyển về tọa độ ảnh gốc 2560x1440.
- ROI phải được cập nhật sau mỗi frame bằng bbox mới nhất, không giữ cố định 5 frame.
- Khi Tracking model không detect được Leanbot: đánh dấu `tracking_lost`, lưu ảnh debug, reset ROI, frame sau quay lại Full model 640x640.

#### Code cần sửa / kiểm tra
- [x] `tools/roi_tracking_baseline_infer.py`: giữ chế độ camera 2K trước, đã set `cap.set(cv2.CAP_PROP_FRAME_WIDTH, 2560)` và `cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1440)`.
- [x] `tools/roi_tracking_baseline_infer.py`: đã sửa `calculate_roi()` thành ROI hình vuông, tâm tại `center_x`, `center_y`, cạnh ROI dựa trên `max(width, height) * 2.0`.
- [x] `tools/roi_tracking_baseline_infer.py`: đã bỏ logic cập nhật ROI mỗi 5 frame (`frames_since_roi_update`), hiện cập nhật ROI sau mỗi frame detect thành công.
- [x] `tools/roi_tracking_baseline_infer.py`: Full mode đã dùng `training_style_crop_pad(frame)` giống `webcam_infer.py` và restore bbox bằng `restore_boxes_from_training_style()`.
- [x] `tools/roi_tracking_baseline_infer.py`: ROI mode đã crop từ ảnh gốc, resize về 160x160, rồi convert bbox 160x160 về ảnh gốc bằng `roi_scale_x`, `roi_scale_y`, `offset_x`, `offset_y`.
- [x] `tools/roi_tracking_baseline_infer.py`: đã bổ sung lưu ROI crop riêng khi `tracking_lost`, đồng thời lưu frame gốc/full-res có vẽ bbox/ROI.
- [x] `tools/roi_tracking_baseline_infer.py`: log CSV đã có `frame_id`, `mode`, `input_width`, `input_height`, `inf_time_ms`, `end_to_end_time_ms`, `cpu_load_pct`, `fps`, `x_center`, `y_center`, `width`, `height`, `angle`, `best_conf`, `tracking_lost`.
- [x] `tools/plot_log.py`: đã tương thích format log mới không có `group_id`, vẽ được `angle`, `x_center`, `y_center`.
- [ ] Cần chạy thử thực tế Baseline và ROI Tracking trên camera 2K để xác nhận log, đồ thị, lost tracking capture.

#### Benchmark cần chạy với 2K trước
- Chạy Baseline Full-frame model 640x640 trên camera 2560x1440.
- Chạy ROI Tracking model 160x160 trên camera 2560x1440.
- Cho Leanbot chạy vòng tròn trên sa bàn khi benchmark.
- Ghi log CSV cho từng chế độ.
- Vẽ đồ thị `angle`, `x_center`, `y_center` cho từng log.
- So sánh FPS, CPU load, inference time, số frame `tracking_lost` giữa Baseline và ROI Tracking.

#### Sau khi 2K ổn định mới chuyển sang 1280x720
- Thêm tham số hoặc chỉnh `cap.set()` sang `1280x720`.
- Chạy lại đúng 2 chế độ Baseline và ROI Tracking.
- Kiểm tra toàn bộ bước convert tọa độ vẫn quy về ảnh gốc 1280x720.
- So sánh kết quả 2K và 1280x720: FPS, CPU load, inference time, độ ổn định tracking, đồ thị góc/tâm.

#### Kết quả cần đưa vào báo cáo
- Lệnh chạy Baseline 2K và ROI Tracking 2K.
- Đường dẫn log CSV của từng lần chạy.
- Ảnh đồ thị từ `plot_log.py`.
- Bảng so sánh FPS / CPU / inference time / tracking_lost.
- Nhận xét: pipeline ROI Tracking có đúng, nhanh hơn baseline không, có mất tracking không, và khi nào nên chuyển sang 1280x720.


