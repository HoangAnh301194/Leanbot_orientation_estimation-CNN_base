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
> Model vẫn nhận diện tốt các trường hợp có khối gỗ, tay gắp gripper ngẫu nhiên và các tường hợp bật Led RGB


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


### 3. Chọn bộ cấu hình ổn định nhất và chạy inference pipeLine đánh giá góc target_heading

- Cấu hình ổn định nhất qua các lần khảo sát:

| Tham số | Giá trị đề xuất |
| :--- | :---: |
| `heading_tolerance` | **`25.0°`** | 
| `Kp_angle` (Pha 1) | **`30.0`** |
| `Kp_angle2` (Pha 2) | **`0.02`** |
| `Kd_angle2` (Pha 2) | **`0.04`** |
| `Kp_dist` (Pha 2) | **`25.0`** |
| `dist_tolerance` | **`10.0 px`** |
| `max_velocity` | **`2000`** | 


- Lệnh chạy : 

```bash
python leanbotCameraController.py `
  --source 1 `
  --show `
  --ble 343944 `
  --heading-tol 20 `
  --kp-angle 30 `
  --kp-angle2 0.02 `
  --kd-angle2 0.04 `
  --full-model ../leanbot_colab/weights/best_fp16_no_nms_imgsz640_openvino_model `
  --tracking-model ../leanbot_colab/weights/best_fp16_no_nms_imgsz160_openvino_model
```

- Kết quả inference : 

- **Lần chạy 1:**
  **Ảnh Detection UI thực tế:**

  <img src="LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_81_20260915_173443_detection_ui.png" alt="Detection UI 1" width="800">

  **Đồ thị quỹ đạo 2D:**

  <img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260915_173443_2d_trajectory.png" alt="Trajectory 1" width="800">

  **Đồ thị PID & Góc:**

  <img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260915_173443_pid_analysis.png" alt="PID 1" width="800">

  **Đồ thị Vi phân & Tỉ số bẻ lái (Kp*error, Kd*diff(error), v_diff):**

  <img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260915_173443_pid_diff_analysis.png" alt="Diff 1" width="800">

---

- **Lần chạy 2:**

  **Ảnh Detection UI thực tế:**

  <img src="LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_372_20260915_173502_detection_ui.png" alt="Detection UI 2" width="800">

  **Đồ thị quỹ đạo 2D:**

  <img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260915_173502_2d_trajectory.png" alt="Trajectory 2" width="800">

  **Đồ thị PID & Góc:**

  <img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260915_173502_pid_analysis.png" alt="PID 2" width="800">

  **Đồ thị Vi phân & Tỉ số bẻ lái (Kp*error, Kd*diff(error), v_diff):**

  <img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260915_173502_pid_diff_analysis.png" alt="Diff 2" width="800">

---

- **Lần chạy 3:**

  **Ảnh Detection UI thực tế:**

  <img src="LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_670_20260915_173522_detection_ui.png" alt="Detection UI 3" width="800">

  **Đồ thị quỹ đạo 2D:**

  <img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260915_173522_2d_trajectory.png" alt="Trajectory 3" width="800">

  **Đồ thị PID & Góc:**

  <img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260915_173522_pid_analysis.png" alt="PID 3" width="800">

  **Đồ thị Vi phân & Tỉ số bẻ lái (Kp*error, Kd*diff(error), v_diff):**

  <img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260915_173522_pid_diff_analysis.png" alt="Diff 3" width="800">

---

- **Lần chạy 4:**

  **Ảnh Detection UI thực tế:**

  <img src="LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_912_20260915_173538_detection_ui.png" alt="Detection UI 4" width="800">

  **Đồ thị quỹ đạo 2D:**

  <img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260915_173538_2d_trajectory.png" alt="Trajectory 4" width="800">

  **Đồ thị PID & Góc:**

  <img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260915_173538_pid_analysis.png" alt="PID 4" width="800">

  **Đồ thị Vi phân & Tỉ số bẻ lái (Kp*error, Kd*diff(error), v_diff):**

  <img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260915_173538_pid_diff_analysis.png" alt="Diff 4" width="800">

---

> **Nhận xét kết quả thực nghiệm:**

> - Kết quả khảo sát với mô hình mới và cấu hình ổn định nhất từ các buổi chạy khảo sát inference, em thấy Leanbot di chuyển kém ổn định hơn. Mặc dù em đã thửu thay đổi thêm các thông số kd_angle2 trong dải từ 0.0001 tới 0.01 nhưng chưa thấy có xu hướng cải thiện ở cấu hình nào ạ.

> - Độ ổn định phụ thuộc nhiều vào mức độ lệch góc ở cuối phase 1. Nếu góc ở phase 1 lệch càng nhiều thì khi chuyển sang phase 2 xe càng dễ mất ổn định do lực bẻ lái bù ban đầu lớn.
 
> Em cũng chưa biết được là do model mới , hay do các yếu tố khác nữa , vì thông thường em nghĩ phải xét tới cả sự đồng bộ giữa tần số tính toán PID (tốc độ xử lý frame/FPS của Camera & Model) và tần số truyền nhận lệnh điều khiển (chu kỳ gửi BLE và tần số đáp ứng động cơ của Leanbot). 


## B. Khó khăn 
- Hiện tại em vẫn chưa hiểu về phần tính ra heading chính xác , và so sánh với target heading lắm ạ . 
- Hiện tại heading trong quá trình điều khiển leanbot là tính liên tục, từ vị trí leanbot realtime tới target pixel ạ. 
```python 
dx = target_x - current_x
dy = target_y - current_y
target_heading = math.degrees(math.atan2(-dy, dx))
```
- Vậy tức là em cần tính thêm 1 target_heading là góc tính từ vị trí start tới vị trí target rồi dùng nó để điều khiển Leanbot bằng PID ở phase 3 ( đi tiến lùi -> tính heading thật ,...) và dùng để so sánh heading thật đúng không ạ Thầy ? 
## C. Công việc tiếp theo 
- Em xin phép nhận hướng đi tiếp theo từ Thầy về phần bộ điều khiển PID ạ 
- Thực hiện triển khai thêm phase 3 , đi tiến lùi để tính toán ra heading và so sánh với target_heading .
