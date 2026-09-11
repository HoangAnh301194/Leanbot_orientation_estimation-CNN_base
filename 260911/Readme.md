# Báo cáo công việc ngày 11/09/2026

## Mục lục
- [A. Công việc đã làm](#a-công-việc-đã-làm)
  - [1. Thu thập thêm ảnh](#1-thu-thập-thêm-ảnh)
  - [2. Thử chạy inference với Kd_angle2 = 0.04 với các mức heading_tol = 25, 35, 45 độ](#2-thử-chạy-inference-với-kd_angle2--004-với-các-mức-heading_tol--25-35-45-độ)
    - [2.1 Trường hợp 1 : kd_angle2 = 0.04 ; heading_tol = 25.0](#21-trường-hợp-1--kd_angle2--004--heading_tol--250)
    - [2.2 Trường hợp 2 : kd_angle2 = 0.04 ; heading_tol = 35.0](#22-trường-hợp-2--kd_angle2--004--heading_tol--350)
    - [2.3 Trường hợp 3 : kd_angle2 = 0.04 ; heading_tol = 45.0](#23-trường-hợp-3--kd_angle2--004--heading_tol--450)
- [B. Khó khăn](#b-khó-khăn)
- [C. Công việc tiếp theo](#c-công-việc-tiếp-theo)

## A. Công việc đã làm 
- Thu thập thêm dataset 
- Chạy inference với Model cũ , và cấu hình `kd_angle2` = 0.04 & `heading_tol` = 25 , 35,45 .
### 1. Thu thập thêm ảnh 
- 24 ảnh cho 24 class với setup nhưu sau : 
  - 9 Leanbot cho mỗi class góc (24 classs góc)
  - 3 Leanbot hiện Led RGB
  - 3 Leanbot quay gripper ngẫu nhiên
  - 3 Leanbot có khối gỗ 3cm đặt giữa gripper
  - Phân bố ngẫu nhiên, rải đều trên sa bàn 
  - Kết hợp với dataset cũ

- Folder dataset mới : [`datasets_24class_640`](./datasets_24class_640/) (24 ảnh 640x640 mới)
- Folder dataset hợp nhất : `datasets/` (204 ảnh 640x640 hoàn chỉnh)
- File zip nén sẵn sàng huấn luyện : `datasets.zip` (41.34 MB)

- 24 ảnh bổ sung như sau  :

| |  |  |   |
| :---: | :---: | :---: | :---: |
| **Class 0 (0°)**<br><img src="datasets_24class_640/images/000000.jpg" alt="Class 0" width="180"> | **Class 1 (15°)**<br><img src="datasets_24class_640/images/000001.jpg" alt="Class 1" width="180"> | **Class 2 (30°)**<br><img src="datasets_24class_640/images/000002.jpg" alt="Class 2" width="180"> | **Class 3 (45°)**<br><img src="datasets_24class_640/images/000003.jpg" alt="Class 3" width="180"> |
| **Class 4 (60°)**<br><img src="datasets_24class_640/images/000004.jpg" alt="Class 4" width="180"> | **Class 5 (75°)**<br><img src="datasets_24class_640/images/000005.jpg" alt="Class 5" width="180"> | **Class 6 (90°)**<br><img src="datasets_24class_640/images/000006.jpg" alt="Class 6" width="180"> | **Class 7 (105°)**<br><img src="datasets_24class_640/images/000007.jpg" alt="Class 7" width="180"> |
| **Class 8 (120°)**<br><img src="datasets_24class_640/images/000008.jpg" alt="Class 8" width="180"> | **Class 9 (135°)**<br><img src="datasets_24class_640/images/000009.jpg" alt="Class 9" width="180"> | **Class 10 (150°)**<br><img src="datasets_24class_640/images/000010.jpg" alt="Class 10" width="180"> | **Class 11 (165°)**<br><img src="datasets_24class_640/images/000011.jpg" alt="Class 11" width="180"> |
| **Class 12 (180°)**<br><img src="datasets_24class_640/images/000012.jpg" alt="Class 12" width="180"> | **Class 13 (195°)**<br><img src="datasets_24class_640/images/000013.jpg" alt="Class 13" width="180"> | **Class 14 (210°)**<br><img src="datasets_24class_640/images/000014.jpg" alt="Class 14" width="180"> | **Class 15 (225°)**<br><img src="datasets_24class_640/images/000015.jpg" alt="Class 15" width="180"> |
| **Class 16 (240°)**<br><img src="datasets_24class_640/images/000016.jpg" alt="Class 16" width="180"> | **Class 17 (255°)**<br><img src="datasets_24class_640/images/000017.jpg" alt="Class 17" width="180"> | **Class 18 (270°)**<br><img src="datasets_24class_640/images/000018.jpg" alt="Class 18" width="180"> | **Class 19 (285°)**<br><img src="datasets_24class_640/images/000019.jpg" alt="Class 19" width="180"> |
| **Class 20 (300°)**<br><img src="datasets_24class_640/images/000020.jpg" alt="Class 20" width="180"> | **Class 21 (315°)**<br><img src="datasets_24class_640/images/000021.jpg" alt="Class 21" width="180"> | **Class 22 (330°)**<br><img src="datasets_24class_640/images/000022.jpg" alt="Class 22" width="180"> | **Class 23 (345°)**<br><img src="datasets_24class_640/images/000023.jpg" alt="Class 23" width="180"> |

- Cấu tạo dataset sau khi cộng thêm 24 ảnh vào datasets trước đó : 

| Nhóm nguồn (`source_group`) | Số lượng ảnh | Số lượng nhãn | Số bounding box | Đặc điểm |
| :--- | :---: | :---: | :---: | :--- |
| `original_120` | 120 | 120 | 1.080 (45 box/class) | Tập robot cơ bản ban đầu (5 ảnh/class, 9 robot/ảnh) |
| `new_red_obstacle_48` | 48 | 48 | 432 (18 box/class) | Bổ sung vật cản khối hộp màu đỏ (2 ảnh/class, 9 robot/ảnh) |
| `background_negative_12` | 12 | 12 | 0 | Sa bàn trống không có robot (negative background samples) |
| `new_setup_24class_260911` | 24 | 24 | 216 (9 box/class) | Bổ sung mới hôm nay: Led RGB, gripper xoay, khối gỗ 3cm (1 ảnh/class, 9 robot/ảnh) |
| **Tổng cộng** | **204 ảnh** | **204 file labels ** | **1.728 bounding box** | **72 bounding box / class cho cả 24 class** |

- **Thông số ảnh trong Dataset**:
  - Kích thước ảnh: $640 \times 640 \times 3$
  - Chuẩn định dạng nhãn: YOLO Detection (`class_id x_center y_center width height`)
  - File metadata thông tin chi tiết: `datasets/manifest.json` ghi lại nguồn gốc từng ảnh
  - File nén huấn luyện: `datasets.zip` (41.34 MB)



### 2. Thử chạy inference với Kd_angle2 = 0.04 với các mức `heading_tol` = 25, 35, 45 độ.
- Cấu hình chạy inference thử nghiệm : 

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

#### 2.1 Trường hợp 1 : `kd_angle2 = 0.04 ; heading_tol = 25.0`

- Lệnh chạy:
```bash
python .\leanbotCameraController.py --show --source 1 --ble 896692 --kp-angle 30 --kd-angle2 0.04 --heading-tol 25 --kp-angle2 0.02
```

- **Lần chạy 1:**
  - **Thời gian di chuyển:** ~13.8 giây (209 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~2.2 giây (35 frames)
  - **Thời gian Pha 2 (DRIVING):** ~11.5 giây (174 frames)
  - **Sai số cự ly cuối:** 10.6 px

  **Ảnh Detection UI thực tế:**

  <img src="LeanbotTinyRC/benchmark_logs_25/manual_captures/manual_cap_347_20260911_164131_detection_ui.png" alt="Detection UI 1" width="800">

  **Đồ thị quỹ đạo 2D:**

  <img src="LeanbotTinyRC/benchmark_logs_25/plots/log_roi_20260911_164131_2d_trajectory.png" alt="Trajectory 1" width="800">

  **Đồ thị PID & Góc:**

  <img src="LeanbotTinyRC/benchmark_logs_25/plots/log_roi_20260911_164131_pid_analysis.png" alt="PID 1" width="800">

  **Đồ thị Vi phân & Tỉ số bẻ lái (Kp*error, Kd*diff(error), v_diff):**

  <img src="LeanbotTinyRC/benchmark_logs_25/plots/log_roi_20260911_164131_pid_diff_analysis.png" alt="Diff 1" width="800">

---

- **Lần chạy 2:**
  - **Thời gian di chuyển:** ~13.9 giây (211 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~1.9 giây (30 frames)
  - **Thời gian Pha 2 (DRIVING):** ~11.9 giây (181 frames)
  - **Sai số cự ly cuối:** 11.9 px

  **Ảnh Detection UI thực tế:**

  <img src="LeanbotTinyRC/benchmark_logs_25/manual_captures/manual_cap_1494_20260911_164247_detection_ui.png" alt="Detection UI 2" width="800">

  **Đồ thị quỹ đạo 2D:**

  <img src="LeanbotTinyRC/benchmark_logs_25/plots/log_roi_20260911_164247_2d_trajectory.png" alt="Trajectory 2" width="800">

  **Đồ thị PID & Góc:**

  <img src="LeanbotTinyRC/benchmark_logs_25/plots/log_roi_20260911_164247_pid_analysis.png" alt="PID 2" width="800">

  **Đồ thị Vi phân & Tỉ số bẻ lái (Kp*error, Kd*diff(error), v_diff):**

  <img src="LeanbotTinyRC/benchmark_logs_25/plots/log_roi_20260911_164247_pid_diff_analysis.png" alt="Diff 2" width="800">

---

- **Lần chạy 3:**
  - **Thời gian di chuyển:** ~9.9 giây (151 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~1.8 giây (29 frames)
  - **Thời gian Pha 2 (DRIVING):** ~8.0 giây (122 frames)
  - **Sai số cự ly cuối:** 10.3 px

  **Ảnh Detection UI thực tế:**

  <img src="LeanbotTinyRC/benchmark_logs_25/manual_captures/manual_cap_1809_20260911_164308_detection_ui.png" alt="Detection UI 3" width="800">

  **Đồ thị quỹ đạo 2D:**

  <img src="LeanbotTinyRC/benchmark_logs_25/plots/log_roi_20260911_164308_2d_trajectory.png" alt="Trajectory 3" width="800">

  **Đồ thị PID & Góc:**

  <img src="LeanbotTinyRC/benchmark_logs_25/plots/log_roi_20260911_164308_pid_analysis.png" alt="PID 3" width="800">

  **Đồ thị Vi phân & Tỉ số bẻ lái (Kp*error, Kd*diff(error), v_diff):**

  <img src="LeanbotTinyRC/benchmark_logs_25/plots/log_roi_20260911_164308_pid_diff_analysis.png" alt="Diff 3" width="800">

---

#### 2.2 Trường hợp 2 : `kd_angle2 = 0.04 ; heading_tol = 35.0`

- Lệnh chạy:
```bash
python .\leanbotCameraController.py --show --source 1 --ble 896692 --kp-angle 30 --kd-angle2 0.04 --heading-tol 35 --kp-angle2 0.02
```

- **Lần chạy 1:**
  - **Thời gian di chuyển:** ~14.6 giây (221 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~2.0 giây (32 frames)
  - **Thời gian Pha 2 (DRIVING):** ~12.5 giây (189 frames)
  - **Sai số cự ly cuối:** 10.8 px

  **Ảnh Detection UI thực tế:**

  <img src="LeanbotTinyRC/benchmark_logs_35/manual_captures/manual_cap_110_20260911_165057_detection_ui.png" alt="Detection UI 1" width="800">

  **Đồ thị quỹ đạo 2D:**

  <img src="LeanbotTinyRC/benchmark_logs_35/plots/log_roi_20260911_165057_2d_trajectory.png" alt="Trajectory 1" width="800">

  **Đồ thị PID & Góc:**

  <img src="LeanbotTinyRC/benchmark_logs_35/plots/log_roi_20260911_165057_pid_analysis.png" alt="PID 1" width="800">

  **Đồ thị Vi phân & Tỉ số bẻ lái (Kp*error, Kd*diff(error), v_diff):**

  <img src="LeanbotTinyRC/benchmark_logs_35/plots/log_roi_20260911_165057_pid_diff_analysis.png" alt="Diff 1" width="800">

---

- **Lần chạy 2:**
  - **Thời gian di chuyển:** ~10.1 giây (153 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~1.9 giây (30 frames)
  - **Thời gian Pha 2 (DRIVING):** ~8.2 giây (123 frames)
  - **Sai số cự ly cuối:** 11.2 px

  **Ảnh Detection UI thực tế:**

  <img src="LeanbotTinyRC/benchmark_logs_35/manual_captures/manual_cap_399_20260911_165116_detection_ui.png" alt="Detection UI 2" width="800">

  **Đồ thị quỹ đạo 2D:**

  <img src="LeanbotTinyRC/benchmark_logs_35/plots/log_roi_20260911_165116_2d_trajectory.png" alt="Trajectory 2" width="800">

  **Đồ thị PID & Góc:**

  <img src="LeanbotTinyRC/benchmark_logs_35/plots/log_roi_20260911_165116_pid_analysis.png" alt="PID 2" width="800">

  **Đồ thị Vi phân & Tỉ số bẻ lái (Kp*error, Kd*diff(error), v_diff):**

  <img src="LeanbotTinyRC/benchmark_logs_35/plots/log_roi_20260911_165116_pid_diff_analysis.png" alt="Diff 2" width="800">

---

- **Lần chạy 3:**
  - **Thời gian di chuyển:** ~14.8 giây (223 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~2.1 giây (33 frames)
  - **Thời gian Pha 2 (DRIVING):** ~12.6 giây (190 frames)
  - **Sai số cự ly cuối:** 10.8 px

  **Ảnh Detection UI thực tế:**

  <img src="LeanbotTinyRC/benchmark_logs_35/manual_captures/manual_cap_642_20260911_165132_detection_ui.png" alt="Detection UI 3" width="800">

  **Đồ thị quỹ đạo 2D:**

  <img src="LeanbotTinyRC/benchmark_logs_35/plots/log_roi_20260911_165132_2d_trajectory.png" alt="Trajectory 3" width="800">

  **Đồ thị PID & Góc:**

  <img src="LeanbotTinyRC/benchmark_logs_35/plots/log_roi_20260911_165132_pid_analysis.png" alt="PID 3" width="800">

  **Đồ thị Vi phân & Tỉ số bẻ lái (Kp*error, Kd*diff(error), v_diff):**

  <img src="LeanbotTinyRC/benchmark_logs_35/plots/log_roi_20260911_165132_pid_diff_analysis.png" alt="Diff 3" width="800">

---

#### 2.3 Trường hợp 3 : `kd_angle2 = 0.04 ; heading_tol = 45.0`

- Lệnh chạy:
```bash
python .\leanbotCameraController.py --show --source 1 --ble 896692 --kp-angle 30 --kd-angle2 0.04 --heading-tol 45 --kp-angle2 0.02
```

- **Lần chạy 1:**
  - **Thời gian di chuyển:** ~10.1 giây (153 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~2.0 giây (31 frames)
  - **Thời gian Pha 2 (DRIVING):** ~8.0 giây (122 frames)
  - **Sai số cự ly cuối:** 10.2 px

  **Ảnh Detection UI thực tế:**

  <img src="LeanbotTinyRC/benchmark_logs_45/manual_captures/manual_cap_70_20260911_164926_detection_ui.png" alt="Detection UI 1" width="800">

  **Đồ thị quỹ đạo 2D:**

  <img src="LeanbotTinyRC/benchmark_logs_45/plots/log_roi_20260911_164926_2d_trajectory.png" alt="Trajectory 1" width="800">

  **Đồ thị PID & Góc:**

  <img src="LeanbotTinyRC/benchmark_logs_45/plots/log_roi_20260911_164926_pid_analysis.png" alt="PID 1" width="800">

  **Đồ thị Vi phân & Tỉ số bẻ lái (Kp*error, Kd*diff(error), v_diff):**

  <img src="LeanbotTinyRC/benchmark_logs_45/plots/log_roi_20260911_164926_pid_diff_analysis.png" alt="Diff 1" width="800">

---

- **Lần chạy 2:**
  - **Thời gian di chuyển:** ~14.5 giây (218 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~2.0 giây (32 frames)
  - **Thời gian Pha 2 (DRIVING):** ~12.3 giây (186 frames)
  - **Sai số cự ly cuối:** 11.3 px

  **Ảnh Detection UI thực tế:**

  <img src="LeanbotTinyRC/benchmark_logs_45/manual_captures/manual_cap_310_20260911_164943_detection_ui.png" alt="Detection UI 2" width="800">

  **Đồ thị quỹ đạo 2D:**

  <img src="LeanbotTinyRC/benchmark_logs_45/plots/log_roi_20260911_164943_2d_trajectory.png" alt="Trajectory 2" width="800">

  **Đồ thị PID & Góc:**

  <img src="LeanbotTinyRC/benchmark_logs_45/plots/log_roi_20260911_164943_pid_analysis.png" alt="PID 2" width="800">

  **Đồ thị Vi phân & Tỉ số bẻ lái (Kp*error, Kd*diff(error), v_diff):**

  <img src="LeanbotTinyRC/benchmark_logs_45/plots/log_roi_20260911_164943_pid_diff_analysis.png" alt="Diff 2" width="800">

---

- **Lần chạy 3:**
  - **Thời gian di chuyển:** ~14.1 giây (214 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~2.0 giây (32 frames)
  - **Thời gian Pha 2 (DRIVING):** ~12.1 giây (182 frames)
  - **Sai số cự ly cuối:** 11.6 px

  **Ảnh Detection UI thực tế:**

  <img src="LeanbotTinyRC/benchmark_logs_45/manual_captures/manual_cap_618_20260911_165003_detection_ui.png" alt="Detection UI 3" width="800">

  **Đồ thị quỹ đạo 2D:**

  <img src="LeanbotTinyRC/benchmark_logs_45/plots/log_roi_20260911_165003_2d_trajectory.png" alt="Trajectory 3" width="800">

  **Đồ thị PID & Góc:**

  <img src="LeanbotTinyRC/benchmark_logs_45/plots/log_roi_20260911_165003_pid_analysis.png" alt="PID 3" width="800">

  **Đồ thị Vi phân & Tỉ số bẻ lái (Kp*error, Kd*diff(error), v_diff):**

  <img src="LeanbotTinyRC/benchmark_logs_45/plots/log_roi_20260911_165003_pid_diff_analysis.png" alt="Diff 3" width="800">

- **Kết luận**
  - Theo nhưu thực nghiệm em thấy Leanbot đi không ổn định lắm ạ, vẫn lắc qua lại một chút 
  - Theo nhưu quan sát thì sau khi đạt `heading_tol` thì leanbot không dừng mà chuyển qua Phase 2 luôn,  từ đó sai số góc vẫn còn lớn , nên khi tính toán PID thì vận tốc sẽ được đẩy lên để xuay Leanbot về hướng target. Kết hợp với các thông số PID khác khiến Leanbot bị overshoot liên tục ạ 
  - Ví dụ như theo đồ thị này thì khi chuyển phase Leanbot phải tăng vận tốc xuay để về hướng target khiến overshoot ở bước sau : 

  ![alt text](image.png)

## B. Khó khăn 
- Không
## C. Công việc tiếp theo
- Training lại với datasets mới 