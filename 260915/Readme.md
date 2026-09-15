# Báo cáo công việc ngày 15/09/2026 
## A. Công việc đã làm 
- Test model mới với các trường hợp Thầy đề xuất : 
  - Leanbot bật Led RGB
  - Quay gripper
  - Có khối gỗ màu trong vùng gripper ( khối 3cm, 2cm)
- Chạy inference điều khiển Leanbot.
### 1. Test model với các trường hợp thử nghiệm 
- Vì hiện tại code infrence đang dùng cho model export OpenVINO , các cỡ ảnh là 640 hoặc 160, để test luôn trực tiếp khả năng nhận diện của model thì em dùng lệnh test infrence của Ultralytics .
- Lệnh chạy : 
```bash
yolo predict model=leanbot_colab/weights/best.pt source=1 show=True conf=0.25
```
- Thực tế infrence các tường hợp Thầy đề xuất như sau : 

![alt text](image-1.png)

## 2. Export model sang dạng OpenVINO 640, 160 và chạy inference đánh giá dữ liệu .
### 2.1 Export model sang dạng OpenVINO FP16 No NMS 
- image size = 640 : 
```bash
python tools/export_openvino_fp16.py --model leanbot_colab/weights/best.pt --imgsz 640 --no-nms
``` 

- Image size = 160 : 
```bash
python tools/export_openvino_fp16.py --model leanbot_colab/weights/best.pt --imgsz 160 --no-nms
```
### 2.2 Tiến hành chạy inference : 
Sau khi export đầy đủ các model thì tiến hành chạy inference điều khiển Leanbot về tọa độ . 

- Lệnh chạy : 
```bash
python leanbotCameraController.py `
--source 1 `
--show `
--ble 896692 `
--full-model ../leanbot_colab/weights/best_fp16_no_nms_imgsz640_openvino_model `
--tracking-model ../leanbot_colab/weights/best_fp16_no_nms_imgsz160_openvino_model
```
- Cấu hình thử nghiệm : 
| Tham số cấu hình | Giá trị |
| :--- | :--- |
| `heading_tolerance` | **`25.0` -> `35.0` -> `45.0`** |
| `Kp_angle` (Pha 1) | **`30.0`** |
| `Ki_angle` / `Kd_angle` | **`0.0` / `0.0`** |
| `Kp_angle2` (Pha 2) | **`0.02`** |
| `Kd_angle2` (Pha 2) | **`0.04`** |
| `Kp_dist` (Pha 2) | **`25.0`** |
| `dist_tolerance` | **`10.0`** |
| `max_velocity` | **`2000`** |

#### Đối với heading_tol = 25 :

- Lệnh chạy : 
```bash 
python leanbotCameraController.py `
  --source 1 `
  --show `
  --ble 896692 `
  --kp-angle 30 `
  --kd-angle2 0.04 `
  --heading-tol 25 `
  --kp-angle2 0.02 `
  --full-model ../leanbot_colab/weights/best_fp16_no_nms_imgsz640_openvino_model `
  --tracking-model ../leanbot_colab/weights/best_fp16_no_nms_imgsz160_openvino_model
```

- **Lần chạy 1:**
  - **Thời gian di chuyển:** ~13.6 giây (206 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~2.2 giây (35 frames)
  - **Thời gian Pha 2 (DRIVING):** ~11.3 giây (171 frames)
  - **Sai số cự ly cuối:** 11.2 px

  **Ảnh Detection UI thực tế:**

  <img src="LeanbotTinyRC/benchmark_logs_25/manual_captures/manual_cap_137_20260915_145830_detection_ui.png" alt="Detection UI 1" width="800">

  **Đồ thị quỹ đạo 2D:**

  <img src="LeanbotTinyRC/benchmark_logs_25/plots/log_roi_20260915_145830_2d_trajectory.png" alt="Trajectory 1" width="800">

  **Đồ thị PID & Góc:**

  <img src="LeanbotTinyRC/benchmark_logs_25/plots/log_roi_20260915_145830_pid_analysis.png" alt="PID 1" width="800">

  **Đồ thị Vi phân & Tỉ số bẻ lái (Kp*error, Kd*diff(error), v_diff):**

  <img src="LeanbotTinyRC/benchmark_logs_25/plots/log_roi_20260915_145830_pid_diff_analysis.png" alt="Diff 1" width="800">

---

- **Lần chạy 2:**
  - **Thời gian di chuyển:** ~14.1 giây (214 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~2.1 giây (33 frames)
  - **Thời gian Pha 2 (DRIVING):** ~12.0 giây (181 frames)
  - **Sai số cự ly cuối:** 11.1 px

  **Ảnh Detection UI thực tế:**

  <img src="LeanbotTinyRC/benchmark_logs_25/manual_captures/manual_cap_464_20260915_145852_detection_ui.png" alt="Detection UI 2" width="800">

  **Đồ thị quỹ đạo 2D:**

  <img src="LeanbotTinyRC/benchmark_logs_25/plots/log_roi_20260915_145852_2d_trajectory.png" alt="Trajectory 2" width="800">

  **Đồ thị PID & Góc:**

  <img src="LeanbotTinyRC/benchmark_logs_25/plots/log_roi_20260915_145852_pid_analysis.png" alt="PID 2" width="800">

  **Đồ thị Vi phân & Tỉ số bẻ lái (Kp*error, Kd*diff(error), v_diff):**

  <img src="LeanbotTinyRC/benchmark_logs_25/plots/log_roi_20260915_145852_pid_diff_analysis.png" alt="Diff 2" width="800">

---

#### Đối với heading_tol = 35 :

- Lệnh chạy : 
```bash 
python leanbotCameraController.py `
  --source 1 `
  --show `
  --ble 896692 `
  --kp-angle 30 `
  --kd-angle2 0.04 `
  --heading-tol 35 `
  --kp-angle2 0.02 `
  --full-model ../leanbot_colab/weights/best_fp16_no_nms_imgsz640_openvino_model `
  --tracking-model ../leanbot_colab/weights/best_fp16_no_nms_imgsz160_openvino_model
```

- **Lần chạy 1:**
  - **Thời gian di chuyển:** ~15.4 giây (233 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~2.9 giây (45 frames)
  - **Thời gian Pha 2 (DRIVING):** ~12.5 giây (188 frames)
  - **Sai số cự ly cuối:** 11.6 px

  **Ảnh Detection UI thực tế:**

  <img src="LeanbotTinyRC/benchmark_logs_35/manual_captures/manual_cap_29_20260915_150014_detection_ui.png" alt="Detection UI 1" width="800">

  **Đồ thị quỹ đạo 2D:**

  <img src="LeanbotTinyRC/benchmark_logs_35/plots/log_roi_20260915_150014_2d_trajectory.png" alt="Trajectory 1" width="800">

  **Đồ thị PID & Góc:**

  <img src="LeanbotTinyRC/benchmark_logs_35/plots/log_roi_20260915_150014_pid_analysis.png" alt="PID 1" width="800">

  **Đồ thị Vi phân & Tỉ số bẻ lái (Kp*error, Kd*diff(error), v_diff):**

  <img src="LeanbotTinyRC/benchmark_logs_35/plots/log_roi_20260915_150014_pid_diff_analysis.png" alt="Diff 1" width="800">

---

- **Lần chạy 2:**
  - **Thời gian di chuyển:** ~13.8 giây (206 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~2.0 giây (31 frames)
  - **Thời gian Pha 2 (DRIVING):** ~11.8 giây (174 frames)
  - **Sai số cự ly cuối:** 10.3 px

  **Ảnh Detection UI thực tế:**

  <img src="LeanbotTinyRC/benchmark_logs_35/manual_captures/manual_cap_346_20260915_150035_detection_ui.png" alt="Detection UI 2" width="800">

  **Đồ thị quỹ đạo 2D:**

  <img src="LeanbotTinyRC/benchmark_logs_35/plots/log_roi_20260915_150035_2d_trajectory.png" alt="Trajectory 2" width="800">

  **Đồ thị PID & Góc:**

  <img src="LeanbotTinyRC/benchmark_logs_35/plots/log_roi_20260915_150035_pid_analysis.png" alt="PID 2" width="800">

  **Đồ thị Vi phân & Tỉ số bẻ lái (Kp*error, Kd*diff(error), v_diff):**

  <img src="LeanbotTinyRC/benchmark_logs_35/plots/log_roi_20260915_150035_pid_diff_analysis.png" alt="Diff 2" width="800">

---

#### Đối với heading_tol = 45 :

- Lệnh chạy : 
```bash 
python leanbotCameraController.py `
  --source 1 `
  --show `
  --ble 896692 `
  --kp-angle 30 `
  --kd-angle2 0.04 `
  --heading-tol 45 `
  --kp-angle2 0.02 `
  --full-model ../leanbot_colab/weights/best_fp16_no_nms_imgsz640_openvino_model `
  --tracking-model ../leanbot_colab/weights/best_fp16_no_nms_imgsz160_openvino_model
```

- **Lần chạy 1:**
  - **Thời gian di chuyển:** ~14.6 giây (221 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~1.9 giây (29 frames)
  - **Thời gian Pha 2 (DRIVING):** ~12.7 giây (192 frames)
  - **Sai số cự ly cuối:** 10.4 px

  **Ảnh Detection UI thực tế:**

  <img src="LeanbotTinyRC/benchmark_logs_45/manual_captures/manual_cap_659_20260915_150218_detection_ui.png" alt="Detection UI 1" width="800">

  **Đồ thị quỹ đạo 2D:**

  <img src="LeanbotTinyRC/benchmark_logs_45/plots/log_roi_20260915_150218_2d_trajectory.png" alt="Trajectory 1" width="800">

  **Đồ thị PID & Góc:**

  <img src="LeanbotTinyRC/benchmark_logs_45/plots/log_roi_20260915_150218_pid_analysis.png" alt="PID 1" width="800">

  **Đồ thị Vi phân & Tỉ số bẻ lái (Kp*error, Kd*diff(error), v_diff):**

  <img src="LeanbotTinyRC/benchmark_logs_45/plots/log_roi_20260915_150218_pid_diff_analysis.png" alt="Diff 1" width="800">

---

- **Lần chạy 2:**
  - **Thời gian di chuyển:** ~9.4 giây (141 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~2.2 giây (34 frames)
  - **Thời gian Pha 2 (DRIVING):** ~7.1 giây (107 frames)
  - **Sai số cự ly cuối:** 11.4 px

  **Ảnh Detection UI thực tế:**

  <img src="LeanbotTinyRC/benchmark_logs_45/manual_captures/manual_cap_942_20260915_150237_detection_ui.png" alt="Detection UI 2" width="800">

  **Đồ thị quỹ đạo 2D:**

  <img src="LeanbotTinyRC/benchmark_logs_45/plots/log_roi_20260915_150237_2d_trajectory.png" alt="Trajectory 2" width="800">

  **Đồ thị PID & Góc:**

  <img src="LeanbotTinyRC/benchmark_logs_45/plots/log_roi_20260915_150237_pid_analysis.png" alt="PID 2" width="800">

  **Đồ thị Vi phân & Tỉ số bẻ lái (Kp*error, Kd*diff(error), v_diff):**

  <img src="LeanbotTinyRC/benchmark_logs_45/plots/log_roi_20260915_150237_pid_diff_analysis.png" alt="Diff 2" width="800">

---

## B. Khó khăn 
- Nhưu trước đó em báo cáo là ma trận nhầm lẫn ( fussion matrix ) của lần training lại với dữ liệu thêm này phân bố đúng với lý thuyết hơn , nhưng ngoài việc Model vẫn nhận diện tốt các trường hợp bật ledRGB , có khúc gỗ, gripper ngẫu nhiên thì em đang không biết model mới có hiệu quả hơn cho việc phân tích góc hơn khôgn, có giảm nhiễu noise hơn khôgn ạ 
- Em có cần kiểm thử , so sánh 2 model trước và sau khôgn ạ ? hay dùng luôn model mới train ạ ? 

## C. Công việc tiếp theo 
- Em xin phép nhận hướng đi tiếp theo từ Thầy ạ . 