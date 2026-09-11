# Báo cáo công việc ngày 09/09/2026

## A. Công việc đã làm 
- Tăng heading_tolerance = 20 
- Cập nhật lại đồ thị phân tích: vẽ ``Kp*error`` và ``Kd*diff(error)`` trên cùng 1 hệ trục tọa độ để so sánh
- Chạy thử nghiệm khảo sát hệ số `Kd_angle2` từ `0.0` đến `0.04` với dung sai góc `heading_tolerance = 20.0°`


### 1. Tăng heading_tolerance = 20 và cập nhật lại đồ thị phân tích
#### 1.1. Cấu hình thông số sau khi thay đổi

| Tham số cấu hình | Giá trị |
| :--- | :--- |
| `heading_tolerance` | **`20.0`** |
| `Kp_angle` (Pha 1) | **`30.0`** |
| `Ki_angle` / `Kd_angle` | **`0.0` / `0.0`** |
| `Kp_angle2` (Pha 2) | **`0.02`** |
| `Kd_angle2` (Pha 2) | **`0.005` -> `0.04`** |
| `Kp_dist` (Pha 2) | **`25.0`** |
| `dist_tolerance` | **`10.0`** |
| `max_velocity` | **`2000`** |


#### 1.2. Các loại biểu đồ phân tích hiện có
- Sau khi bổ sung, chỉnh sửa lại đồ thị : vẽ ``Kp*error`` và ``Kd*diff(error)`` trên cùng 1 hệ trục tọa độ để so sánh. Kết quả biểu đồ có dạng như sau : 

<img src="LeanbotTinyRC/benchmark_logs_004/plots/log_roi_20260909_083207_pid_diff_analysis.png" alt="PID Diff Analysis" width="800">

* **Subplot 1 (Error Angle & Dải dung sai chuyển pha):**
  * `Đường đỏ (Error Angle e(t))`: Sai số góc bám tới đích.
  * `Dải màu xanh lá (Tolerance Band ±20°)`: Vùng dung sai góc chuyển pha đã được nâng lên $\pm 20^\circ$.
* **Subplot 2 (So sánh trực tiếp `Kp*error` và `Kd*diff(error)` trên cùng hệ trục):**
  * `Đường xanh dương (Kp * error)`: Thành phần tỉ lệ $P = K_p \cdot e(t)$ (với $K_p = 0.02$). Đại diện cho lực kéo bẻ lái hướng về tâm đích.
  * `Đường cam (Kd * diff(error))`: Thành phần vi phân $D = K_d \cdot \Delta e(t)$ (với $\Delta e = e(t) - e(t-1)$). Đại diện cho lực cản hãm quán tính xoay.
  * `Đường xanh lá (Total P + D)`: Tín hiệu bẻ lái tổng hợp $P + D$.
* **Subplot 3 (Vận tốc bánh xe, Vận tốc vi sai & Tỉ số bẻ lái):**
  * `Đường xanh dương (v_L)` & `Đường hồng (v_R)`: Vận tốc 2 bánh xe.
  * `Đường tím (Differential Speed v_diff)`: Vận tốc bẻ lái vi sai.
  * `Đường xanh lá - Trục phụ (Ratio v_diff / v_LR)`: Tỉ số bẻ lái tương đối so với vận tốc tiến tịnh tiến.

---
#### 1.3 Lệnh chạy 

- **Lệnh chạy camera inference:**
```bash
python .\leanbotCameraController.py --show --source 1 --ble 896692 --heading-tol 20 --kp-angle 30 --kp-angle2 0.02 --kd-angle2 0.005
```
- **Lệnh tạo biểu đồ phân tích:**
```bash
python .\plot_pid_navigation_log.py --log benchmark_logs/<ten_file_log>.csv
```


### 2. Chạy thử nghiệm khi tăng kd Angle2 từ 0.0 -> 0.005 -> 0.01 -> 0.04

- Cấu hình hiện tại của bộ điều khiển PID : 
  - `Kp_dist = 25.0`, `Ki_dist = 0.0`, `Kd_dist = 0.0`
  - `Kp_angle = 30.0`, `Ki_angle = 0.0`, `Kd_angle = 0.0`
  - `Kp_angle2 = 0.02`, `Ki_angle2 = 0.0`, `Kd_angle2 = 0.0 -> 0.04`
  - `dist_tolerance = 10.0 px`
  - `heading_tolerance = 20.0°`



#### 2.1 Chạy Inference cấu hình Angle2 kd = 0.0
- Lệnh chạy:
```bash
python .\leanbotCameraController.py --show --source 1 --ble 896692 --kp-angle 30 --kd-angle2 0.0 --heading-tol 20 --kp-angle2 0.02
```

- **Trường hợp 1:**
  - **Thời gian di chuyển:** ~14.5 giây (219 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~2.1 giây (34 frames)
  - **Thời gian Pha 2 (DRIVING):** ~12.2 giây (185 frames)
  - **Sai số cự ly cuối:** 10.7 px

  **Ảnh Detection UI thực tế:**

  <img src="LeanbotTinyRC/benchmark_logs_00/manual_captures/manual_cap_123_20260909_082414_detection_ui.png" alt="Detection UI 1" width="800">

  **Đồ thị quỹ đạo 2D:**

  <img src="LeanbotTinyRC/benchmark_logs_00/plots/log_roi_20260909_082414_2d_trajectory.png" alt="Trajectory 1" width="800">

  **Đồ thị PID & Góc:**

  <img src="LeanbotTinyRC/benchmark_logs_00/plots/log_roi_20260909_082414_pid_analysis.png" alt="PID 1" width="800">

  **Đồ thị Vi phân & Tỉ số bẻ lái (Kp*error, Kd*diff(error), v_diff):**

  <img src="LeanbotTinyRC/benchmark_logs_00/plots/log_roi_20260909_082414_pid_diff_analysis.png" alt="Diff 1" width="800">

---

- **Trường hợp 2:**
  - **Thời gian di chuyển:** ~16.1 giây (243 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~2.3 giây (37 frames)
  - **Thời gian Pha 2 (DRIVING):** ~13.6 giây (206 frames)
  - **Sai số cự ly cuối:** 10.0 px

  **Ảnh Detection UI thực tế:**

  <img src="LeanbotTinyRC/benchmark_logs_00/manual_captures/manual_cap_464_20260909_082436_detection_ui.png" alt="Detection UI 2" width="800">

  **Đồ thị quỹ đạo 2D:**

  <img src="LeanbotTinyRC/benchmark_logs_00/plots/log_roi_20260909_082436_2d_trajectory.png" alt="Trajectory 2" width="800">

  **Đồ thị PID & Góc:**

  <img src="LeanbotTinyRC/benchmark_logs_00/plots/log_roi_20260909_082436_pid_analysis.png" alt="PID 2" width="800">

  **Đồ thị Vi phân & Tỉ số bẻ lái (Kp*error, Kd*diff(error), v_diff):**

  <img src="LeanbotTinyRC/benchmark_logs_00/plots/log_roi_20260909_082436_pid_diff_analysis.png" alt="Diff 2" width="800">


#### 2.2 Chạy Inference cấu hình Angle2 kd = 0.005
- Lệnh chạy:
```bash
python .\leanbotCameraController.py --show --source 1 --ble 896692 --kp-angle 30 --kd-angle2 0.005 --heading-tol 20 --kp-angle2 0.02
```

- **Trường hợp 1:**
  - **Thời gian di chuyển:** ~15.8 giây (238 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~2.3 giây (35 frames)
  - **Thời gian Pha 2 (DRIVING):** ~13.5 giây (203 frames)
  - **Sai số cự ly cuối:** 10.4 px

  **Ảnh Detection UI thực tế:**

  <img src="LeanbotTinyRC/benchmark_logs_0005/manual_captures/manual_cap_127_20260909_082719_detection_ui.png" alt="Detection UI 1" width="800">

  **Đồ thị quỹ đạo 2D:**

  <img src="LeanbotTinyRC/benchmark_logs_0005/plots/log_roi_20260909_082719_2d_trajectory.png" alt="Trajectory 1" width="800">

  **Đồ thị PID & Góc:**

  <img src="LeanbotTinyRC/benchmark_logs_0005/plots/log_roi_20260909_082719_pid_analysis.png" alt="PID 1" width="800">

  **Đồ thị Vi phân & Tỉ số bẻ lái (Kp*error, Kd*diff(error), v_diff):**

  <img src="LeanbotTinyRC/benchmark_logs_0005/plots/log_roi_20260909_082719_pid_diff_analysis.png" alt="Diff 1" width="800">

---

- **Trường hợp 2:**
  - **Thời gian di chuyển:** ~14.7 giây (222 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~2.1 giây (33 frames)
  - **Thời gian Pha 2 (DRIVING):** ~12.5 giây (189 frames)
  - **Sai số cự ly cuối:** 10.3 px

  **Ảnh Detection UI thực tế:**

  <img src="LeanbotTinyRC/benchmark_logs_0005/manual_captures/manual_cap_480_20260909_082742_detection_ui.png" alt="Detection UI 2" width="800">

  **Đồ thị quỹ đạo 2D:**

  <img src="LeanbotTinyRC/benchmark_logs_0005/plots/log_roi_20260909_082742_2d_trajectory.png" alt="Trajectory 2" width="800">

  **Đồ thị PID & Góc:**

  <img src="LeanbotTinyRC/benchmark_logs_0005/plots/log_roi_20260909_082742_pid_analysis.png" alt="PID 2" width="800">

  **Đồ thị Vi phân & Tỉ số bẻ lái (Kp*error, Kd*diff(error), v_diff):**

  <img src="LeanbotTinyRC/benchmark_logs_0005/plots/log_roi_20260909_082742_pid_diff_analysis.png" alt="Diff 2" width="800">


#### 2.3 Chạy Inference cấu hình Angle2 kd = 0.01
- Lệnh chạy:
```bash
python .\leanbotCameraController.py --show --source 1 --ble 896692 --kp-angle 30 --kd-angle2 0.01 --heading-tol 20 --kp-angle2 0.02
```

- **Trường hợp 1:**
  - **Thời gian di chuyển:** ~16.3 giây (246 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~2.3 giây (36 frames)
  - **Thời gian Pha 2 (DRIVING):** ~13.9 giây (210 frames)
  - **Sai số cự ly cuối:** 10.6 px

  **Ảnh Detection UI thực tế:**

  <img src="LeanbotTinyRC/benchmark_logs_001/manual_captures/manual_cap_203_20260909_082909_detection_ui.png" alt="Detection UI 1" width="800">

  **Đồ thị quỹ đạo 2D:**

  <img src="LeanbotTinyRC/benchmark_logs_001/plots/log_roi_20260909_082909_2d_trajectory.png" alt="Trajectory 1" width="800">

  **Đồ thị PID & Góc:**

  <img src="LeanbotTinyRC/benchmark_logs_001/plots/log_roi_20260909_082909_pid_analysis.png" alt="PID 1" width="800">

  **Đồ thị Vi phân & Tỉ số bẻ lái (Kp*error, Kd*diff(error), v_diff):**

  <img src="LeanbotTinyRC/benchmark_logs_001/plots/log_roi_20260909_082909_pid_diff_analysis.png" alt="Diff 1" width="800">

---

- **Trường hợp 2:**
  - **Thời gian di chuyển:** ~14.3 giây (216 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~2.3 giây (37 frames)
  - **Thời gian Pha 2 (DRIVING):** ~11.9 giây (179 frames)
  - **Sai số cự ly cuối:** 10.2 px

  **Ảnh Detection UI thực tế:**

  <img src="LeanbotTinyRC/benchmark_logs_001/manual_captures/manual_cap_552_20260909_082933_detection_ui.png" alt="Detection UI 2" width="800">

  **Đồ thị quỹ đạo 2D:**

  <img src="LeanbotTinyRC/benchmark_logs_001/plots/log_roi_20260909_082933_2d_trajectory.png" alt="Trajectory 2" width="800">

  **Đồ thị PID & Góc:**

  <img src="LeanbotTinyRC/benchmark_logs_001/plots/log_roi_20260909_082933_pid_analysis.png" alt="PID 2" width="800">

  **Đồ thị Vi phân & Tỉ số bẻ lái (Kp*error, Kd*diff(error), v_diff):**

  <img src="LeanbotTinyRC/benchmark_logs_001/plots/log_roi_20260909_082933_pid_diff_analysis.png" alt="Diff 2" width="800">


#### 2.4 Chạy Inference cấu hình Angle2 kd = 0.04
- Lệnh chạy:
```bash
python .\leanbotCameraController.py --show --source 1 --ble 896692 --kp-angle 30 --kd-angle2 0.04 --heading-tol 20 --kp-angle2 0.02
```

- **Trường hợp 1:**
  - **Thời gian di chuyển:** ~13.8 giây (210 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~2.1 giây (34 frames)
  - **Thời gian Pha 2 (DRIVING):** ~11.6 giây (176 frames)
  - **Sai số cự ly cuối:** 10.1 px

  **Ảnh Detection UI thực tế:**

  <img src="LeanbotTinyRC/benchmark_logs_004/manual_captures/manual_cap_187_20260909_083207_detection_ui.png" alt="Detection UI 1" width="800">

  **Đồ thị quỹ đạo 2D:**

  <img src="LeanbotTinyRC/benchmark_logs_004/plots/log_roi_20260909_083207_2d_trajectory.png" alt="Trajectory 1" width="800">

  **Đồ thị PID & Góc:**

  <img src="LeanbotTinyRC/benchmark_logs_004/plots/log_roi_20260909_083207_pid_analysis.png" alt="PID 1" width="800">

  **Đồ thị Vi phân & Tỉ số bẻ lái (Kp*error, Kd*diff(error), v_diff):**

  <img src="LeanbotTinyRC/benchmark_logs_004/plots/log_roi_20260909_083207_pid_diff_analysis.png" alt="Diff 1" width="800">

---

- **Trường hợp 2:**
  - **Thời gian di chuyển:** ~13.3 giây (202 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~2.2 giây (34 frames)
  - **Thời gian Pha 2 (DRIVING):** ~11.1 giây (168 frames)
  - **Sai số cự ly cuối:** 10.6 px

  **Ảnh Detection UI thực tế:**

  <img src="LeanbotTinyRC/benchmark_logs_004/manual_captures/manual_cap_494_20260909_083228_detection_ui.png" alt="Detection UI 2" width="800">

  **Đồ thị quỹ đạo 2D:**

  <img src="LeanbotTinyRC/benchmark_logs_004/plots/log_roi_20260909_083228_2d_trajectory.png" alt="Trajectory 2" width="800">

  **Đồ thị PID & Góc:**

  <img src="LeanbotTinyRC/benchmark_logs_004/plots/log_roi_20260909_083228_pid_analysis.png" alt="PID 2" width="800">

  **Đồ thị Vi phân & Tỉ số bẻ lái (Kp*error, Kd*diff(error), v_diff):**

  <img src="LeanbotTinyRC/benchmark_logs_004/plots/log_roi_20260909_083228_pid_diff_analysis.png" alt="Diff 2" width="800">

---

- **Trường hợp 3:**
  - **Thời gian di chuyển:** ~9.7 giây (147 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~2.1 giây (33 frames)
  - **Thời gian Pha 2 (DRIVING):** ~7.6 giây (114 frames)
  - **Sai số cự ly cuối:** 11.2 px

  **Ảnh Detection UI thực tế:**

  <img src="LeanbotTinyRC/benchmark_logs_004/manual_captures/manual_cap_773_20260909_083247_detection_ui.png" alt="Detection UI 3" width="800">

  **Đồ thị quỹ đạo 2D:**

  <img src="LeanbotTinyRC/benchmark_logs_004/plots/log_roi_20260909_083247_2d_trajectory.png" alt="Trajectory 3" width="800">

  **Đồ thị PID & Góc:**

  <img src="LeanbotTinyRC/benchmark_logs_004/plots/log_roi_20260909_083247_pid_analysis.png" alt="PID 3" width="800">

  **Đồ thị Vi phân & Tỉ số bẻ lái (Kp*error, Kd*diff(error), v_diff):**

  <img src="LeanbotTinyRC/benchmark_logs_004/plots/log_roi_20260909_083247_pid_diff_analysis.png" alt="Diff 3" width="800">

---

- **Trường hợp 4:**
  - **Thời gian di chuyển:** ~10.5 giây (160 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~2.1 giây (34 frames)
  - **Thời gian Pha 2 (DRIVING):** ~8.3 giây (126 frames)
  - **Sai số cự ly cuối:** 10.4 px

  **Ảnh Detection UI thực tế:**

  <img src="LeanbotTinyRC/benchmark_logs_004/manual_captures/manual_cap_1008_20260909_083303_detection_ui.png" alt="Detection UI 4" width="800">

  **Đồ thị quỹ đạo 2D:**

  <img src="LeanbotTinyRC/benchmark_logs_004/plots/log_roi_20260909_083303_2d_trajectory.png" alt="Trajectory 4" width="800">

  **Đồ thị PID & Góc:**

  <img src="LeanbotTinyRC/benchmark_logs_004/plots/log_roi_20260909_083303_pid_analysis.png" alt="PID 4" width="800">

  **Đồ thị Vi phân & Tỉ số bẻ lái (Kp*error, Kd*diff(error), v_diff):**

  <img src="LeanbotTinyRC/benchmark_logs_004/plots/log_roi_20260909_083303_pid_diff_analysis.png" alt="Diff 4" width="800">


### 2.5 Kết luận về ngưỡng ổn định của Kd Angle2

#### Bảng tổng hợp số liệu thực nghiệm định lượng giữa các cấu hình Kd:

| Cấu hình `Kd_angle2` | Thời gian P2 TB (s) | Sai số góc $MAE$ TB (deg) | Sai số góc hiệu dụng $RMS$ TB (deg) | Số lần đảo chiều lái TB (lần) | Tần suất đảo lái TB (lần/s) | Mức độ ổn định thực tế |
| :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **`0.0`** | 12.90s | 18.63° | 22.75° | 8.0 | 0.62 | Dao động hình sin lớn |
| **`0.005`** | 13.00s | 16.76° | 19.99° | 7.5 | 0.58 | Giảm nhẹ dao động |
| **`0.01`** | 12.90s | 17.67° | 21.69° | 7.5 | 0.58 | Góc lượn vẫn còn khá rộng |
| **`0.04`** | 9.65s | **7.33°** | **10.75°** | 14.0 | 1.45 | **ổn định:** Sai số góc nhỏ nhất, quỹ đạo bám thẳng hầu như không có dao động |

> - **Cấu hình ổn định và hiệu quả nhất:** **`Kd_angle2 = 0.04`**


## B. Khó khăn 

- Về phần thu thập thêm dataset Leanbot, Thầy có thể cho em xin thêm đề xuất về số lượng ảnh cho mỗi trường hợp và cách bố trí góc/vị trí chụp được không ạ? 
  
## C. Công việc tiếp theo
- Tìm hiểu về thêm về kĩ thuật *filter noisy differential data in a PID controller*
- Thu thập thêm dữ liệu ảnh để trainning 

