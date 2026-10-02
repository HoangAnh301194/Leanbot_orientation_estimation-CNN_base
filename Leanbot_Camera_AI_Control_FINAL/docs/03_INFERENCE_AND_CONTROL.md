# 3. Chạy Inference và các tính năng hiện có

Tài liệu này mô tả cách chạy hệ thống camera AI, pipeline inference, smoothing góc, set target, điều khiển PID tới target, cơ chế đi lùi, lost tracking và các phím điều khiển.

## 3.1. Các file runtime

- [`leanbotCameraController.py`](../LeanbotTinyRC_AI_PIDControl/leanbotCameraController.py): chương trình runtime chính.
- [`PID_controller.py`](../LeanbotTinyRC_AI_PIDControl/PID_controller.py): bộ điều khiển vị trí và heading.
- [`angle_smoothing.py`](../LeanbotTinyRC_AI_PIDControl/angle_smoothing.py): smoothing model angle, trajectory angle và fused angle.
- [`lost_tracking_collector.py`](../LeanbotTinyRC_AI_PIDControl/lost_tracking_collector.py): lưu sample khi ROI tracking thất bại.
- [`check_confidence.py`](../tools/check_confidence.py): các hàm phục hồi bbox và xử lý output model.
- [`LeanbotTinyRC/`](../LeanbotTinyRC_AI_PIDControl/LeanbotTinyRC/): thư viện giao tiếp Leanbot qua BLE.
- [`target_config.json`](../LeanbotTinyRC_AI_PIDControl/target_config.json): target đã lưu.
- [Model 640](../models/yolo11n_latest_version/best_fp16_no_nms_imgsz640_openvino_model/)
- [Model 160](../models/yolo11n_latest_version/best_fp16_no_nms_imgsz160_openvino_model/)

## 3.2. Cài dependency

Từ thư mục `Leanbot_Camera_AI_Control_FINAL`:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r .\requirements.txt
```

Các dependency chính:

```text
opencv-python
numpy
pandas
ultralytics
openvino
matplotlib
psutil
bleak
pyyaml
```

## 3.3. Chạy inference

Chuyển vào runtime folder:

```powershell
cd .\LeanbotTinyRC_AI_PIDControl
```

Lệnh cơ bản:

```powershell
python .\leanbotCameraController.py --source 1 --show --ble <BLE_ID>
```

Nếu không cần BLE:

```powershell
python .\leanbotCameraController.py --source 1 --show --ble 0
```

Nếu chạy từ video:

```powershell
python .\leanbotCameraController.py --video <path_to_video> --show --ble 0
```

## 3.4. Model mặc định

Main sử dụng:

```text
--full-model
models\yolo11n_latest_version\best_fp16_no_nms_imgsz640_openvino_model

--tracking-model
models\yolo11n_latest_version\best_fp16_no_nms_imgsz160_openvino_model
```

Có thể override:

```powershell
python .\leanbotCameraController.py `
  --source 1 `
  --full-model ..\models\...640_openvino_model `
  --tracking-model ..\models\...160_openvino_model `
  --ble <BLE_ID>
```

## 3.5. Pipeline inference

```text
Camera frame
    ↓
FULL detection 640
    ↓
BBox Leanbot
    ↓
Tạo ROI quanh bbox
    ↓
Resize ROI -> 160x160
    ↓
ROI tracking model
    ↓
Class scores + bbox
    ↓
Score-weighted orientation vector
    ↓
Center (cx, cy) + raw angle
    ↓
AngleSmoothingEngine
    ↓
Fused angle
    ↓
PID navigation
```

Khi ROI tracking thất bại, hệ thống chuyển lại FULL search để tìm lại Leanbot.

## 3.6. Các tham số inference chính

```text
--width           1280
--height          720
--device          CPU
--topk            100
--conf            0.25
--roi_conf        0.15
--iou             0.5
--mag-threshold   2.0
--fps             30
```

Ý nghĩa:

- `--conf`: threshold cho FULL 640.
- `--roi_conf`: threshold cho ROI 160.
- `--topk`: số anchor có score cao được giữ cho pipeline no-NMS.
- `--iou`: threshold grouping bbox.
- `--mag-threshold`: ngưỡng magnitude của vector class score.
- `--device`: `CPU`, `GPU` hoặc `AUTO`.

## 3.7. Các phím điều khiển

```text
T : Set Target
S : Start PID navigation
P : Pause
C : Cancel current run
K : Manual capture
M : measureHeading
Q : Quit
```

## 3.8. Set Target

Nhấn `T` để bắt đầu set target.

Quy trình:

```text
T
↓
Dừng robot
↓
Đo center (x,y) khi robot đứng yên
↓
Chạy forward/backward
↓
Thu trajectory center
↓
Ước lượng target heading
↓
Cập nhật PID target
↓
Lưu target_config.json
```

Thông số:

```text
--set-target-time   3.0 s
--set-target-speed  1500
--target-config     target_config.json
```

Lệnh tùy chỉnh:

```powershell
python .\leanbotCameraController.py `
  --source 1 `
  --ble <BLE_ID> `
  --set-target-time 3.0 `
  --set-target-speed 1500
```

## 3.9. Start navigation

Sau khi set target, nhấn `S`.

State machine:

```text
PHASE 1 - ALIGNING
    ↓
PHASE 2 - DRIVING
    ↓
PHASE 3 - FINAL ALIGNING
    ↓
PHASE 4 - FORWARD/BACKWARD
    ↓
Post-Phase-4 heading correction
    ↓
COMPLETED
```

### Phase 1 - ALIGNING

Robot quay tại chỗ để hướng về bearing của target.

Mặc định:

```text
Kp_angle      = 30.0
Kd_angle      = 0.0
heading_tol   = 20°
```

### Phase 2 - DRIVING

Robot di chuyển tới target và hiệu chỉnh heading đồng thời.

Distance controller trong `PID_controller.py`:

```text
Kp_dist = 25.0
Ki_dist = 0.0
Kd_dist = 0.0
```

Heading correction mặc định từ main:

```text
Kp_angle2 = 0.01
Kd_angle2 = 0.04
```

Differential term:

```text
delta_v = (Kp*error + Ki*integral + Kd*d_error) * |v_linear|

v_left  = v_linear + delta_v
v_right = v_linear - delta_v
```

Distance tolerance mặc định trong controller:

```text
10 px
```

Maximum wheel command mặc định:

```text
2000
```

### Phase 3 - FINAL ALIGNING

Sau khi đạt target position, robot quay tại chỗ tới target heading.

```text
Kp_angle3   = 20.0
Ki_angle3   = 0.0
Kd_angle3   = 0.01
heading_tol3 = 5°
settle_time  = 500 ms
```

### Phase 4 - Forward/Backward verification

```text
--fwd-bwd-time   3.0 s
--fwd-bwd-speed  2000
```

Robot gửi lệnh forward/backward tự động qua firmware.

## 3.10. Cơ chế tự chọn tiến hoặc lùi

Khi bắt đầu Phase 1:

```text
initial_error = wrap(current_angle - bearing_heading)
```

Nếu:

```text
|initial_error| > 90°
```

thì:

```text
is_reversing = True
```

Bearing điều khiển được cộng thêm 180 độ và vận tốc tuyến tính ở Phase 2 được đổi dấu.

Gain khi đi lùi:

```text
Phase 1:
Kp_angle_rev = 15.0
Kd_angle_rev = 0.0

Phase 2:
Kp_angle2_rev = 0.015
Kd_angle2_rev = 0.05
```

`delta_v` không bị đảo dấu khi lùi. Hướng quay vi sai vẫn được xác định từ heading error so với bearing đã offset 180 độ.

## 3.11. Smoothing center và angle

Code:

- [`angle_smoothing.py`](../LeanbotTinyRC_AI_PIDControl/angle_smoothing.py)

Tham số mặc định:

```text
--smooth-window 18
--smooth-index  0
--smooth-K      1.0
```

Pipeline gồm hai stream.

### Stream 1 - Model angle

```text
Raw orientation angle
    ↓
Unwrap angle
    ↓
Polynomial fit degree 1
    ↓
model_angle_smooth
```

### Stream 2 - Trajectory angle

```text
Center x,y
    ↓
Sliding window
    ↓
Fit x(t), y(t), degree 1
    ↓
Derivative vector
    ↓
atan2(-dy, dx)
    ↓
180° phase alignment
    ↓
trajectory_angle_smooth
```

### Fusion

Model angle và trajectory angle được fusion theo tốc độ:

```text
weight_x = K / (K + speed)

fused_angle =
    weight_x * model_angle
    + (1 - weight_x) * trajectory_angle
```

Khi tốc độ thấp, model angle có trọng số lớn hơn. Khi robot di chuyển rõ ràng, trajectory angle có trọng số lớn hơn.

Frame lost tracking được đưa vào buffer dưới dạng NaN và không được dùng trực tiếp trong phép fit.

## 3.12. Lost tracking

Runtime sử dụng hai mức inference:

```text
FULL 640
   ↓ detected
ROI 160 tracking
   ↓ fail
FULL 640 search
```

Có thể bật thu dữ liệu lost tracking bằng:

```powershell
python .\leanbotCameraController.py `
  --source 1 `
  --show `
  --save-lost `
  --ble <BLE_ID>
```

Output mặc định:

```text
../lost_tracking_dataset/
```

Chi tiết cách review và merge vào dataset training được mô tả trong:

- [01_DATASET_PIPELINE.md](01_DATASET_PIPELINE.md)

## 3.13. measureHeading

Nhấn `M` để gọi:

```text
measureHeading(intervalMs=2000, speed=2000)
```

Quy trình:

```text
Forward
↓
Backward
↓
Camera thu center trajectory
↓
Fit trục chính của trajectory
↓
Xác định chiều forward
↓
Tính heading
```

Các script khảo sát liên quan nằm tại:

- [`survey_heading.py`](../tools/experiments/survey_heading.py)
- [`calc_heading_summary.py`](../tools/experiments/calc_heading_summary.py)
- [`plot_survey_heading.py`](../tools/experiments/plot_survey_heading.py)

## 3.14. Output runtime

Các output có thể được sinh trong quá trình chạy:

```text
benchmark_logs/
lost_tracking_dataset/
target_config.json
target_history.csv
target_history.json
```

`benchmark_logs/` chứa dữ liệu debug và capture, không phải dependency của runtime.

## 3.15. Ví dụ lệnh chạy đầy đủ

```powershell
python .\leanbotCameraController.py `
  --source 1 `
  --show `
  --device CPU `
  --conf 0.25 `
  --roi_conf 0.15 `
  --iou 0.5 `
  --smooth-window 18 `
  --smooth-index 0 `
  --smooth-K 1.0 `
  --kp-angle 30 `
  --kd-angle 0 `
  --kp-angle-rev 15 `
  --kd-angle-rev 0 `
  --kp-angle2 0.01 `
  --kd-angle2 0.04 `
  --kp-angle2-rev 0.015 `
  --kd-angle2-rev 0.05 `
  --heading-tol 20 `
  --kp-angle3 20 `
  --kd-angle3 0.01 `
  --heading-tol3 5 `
  --settle-time-ms 500 `
  --fwd-bwd-time 3 `
  --fwd-bwd-speed 2000 `
  --kp-spin 18.8 `
  --spin-speed 50 `
  --set-target-time 3 `
  --set-target-speed 1500 `
  --ble <BLE_ID>
```

## 3.16. Trình tự vận hành đề xuất

```text
1. Kết nối camera và Leanbot.
2. Chạy leanbotCameraController.py.
3. Kiểm tra FULL/ROI detection.
4. Đưa robot tới vị trí target mong muốn.
5. Nhấn T để set target position + heading.
6. Di chuyển robot khỏi target.
7. Nhấn S để bắt đầu navigation.
8. P để pause hoặc C để cancel khi cần.
9. Q để thoát chương trình.
```
