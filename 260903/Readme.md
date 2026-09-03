# Báo cáo công việc ngày 03/09/2026

## A. Công việc đã làm 
- Sửa lại phần crop giới hạn vL, vR thành scale về dải +-2000
- Đổi polynomial order trong bước smooth center x, y từ bậc 2 -> bậc 1.
- Đổi smooth index từ `-4` về `0`
- Giữ Angle2 kp = `0.02` và chạy inference đánh giá ở các mức `heading_tolerance` tăng dần từ 10 -> 15 -> 20 . 


### 1. Chỉnh sửa các cấu hình cần thay đổi 

#### 1.1. Chuyển vL, vR scale về dải +-2000 thay vì crop tại giới hạn . 

- Các bước thực hiện scale về dải +-2000 giữ đúng tỉ lệ vận tốc hệ bánh vi sai:
  - Bước 1: Tính toán vận tốc lý thuyết ban đầu cho hai bánh (v_left, v_right) từ bộ điều khiển PID.
  - Bước 2: Tìm độ lớn vận tốc lớn nhất trong hai bánh: max_v = max(|v_left|, |v_right|).
  - Bước 3: So sánh max_v với giới hạn vận tốc tối đa (max_velocity = 2000). Nếu max_v > 2000, tính hệ số tỷ lệ: scale_factor = 2000 / max_v.
  - Bước 4: Cập nhật lại vận tốc cho cả hai bánh bằng cách nhân với hệ số tỷ lệ:
    - v_left = v_left * scale_factor
    - v_right = v_right * scale_factor
  - Bước 5: Làm tròn kết quả về số nguyên (nếu cần ) và gửi lệnh điều khiển xuống stepper . Trong code `PID_controller.py`, thay thế hàm `_crop_speed` cũ bằng hàm `_scale_speeds` và áp dụng đồng bộ cho cả hai giai đoạn: Phase 1 (ALIGNING, xuay căn chỉnh) và Phase 2 (DRIVING, đi thẳng tiến tới mục tiêu).

  - Đoạn code thay đổi trong `PID_controller.py`:
  ```python
    def _scale_speeds(self, v_left: float, v_right: float) -> Tuple[int, int]:
        max_v = max(abs(v_left), abs(v_right))
        if max_v > self.max_velocity:
            scale_factor = self.max_velocity / max_v
            v_left *= scale_factor
            v_right *= scale_factor
        return int(round(v_left)), int(round(v_right))
  ```

- Ví dụ : 
  - Tại một chu kỳ điều khiển rẽ gắt, bộ điều khiển PID tính ra:
    - v_left = 1000
    - v_right = 4000
    - Giới hạn vận tốc max_velocity = 2000
    - Tỷ lệ vi sai mong muốn: v_right / v_left = 4000 / 1000 = 4.0
  - Khi xử lý bằng cách Scale tỷ lệ:
    - Tìm max_v = max(|1000|, |4000|) = 4000 > 2000.
    - Hệ số scale_factor = 2000 / 4000 = 0.5.
    - Vận tốc sau scale:
      - v_left = 1000 * 0.5 = 500
      - v_right = 4000 * 0.5 = 2000


#### 1.2. Đổi polynomial order trong bước smooth center x, y từ bậc 2 -> bậc 1. Và đổi smooth index từ `-4` về `0` 

- **Cơ chế làm mượt Smoothing cho dữ liệu Center x,y hiện tại:**
  - Pipeline tính góc tiếp tuyến quỹ đạo (Trajectory Tangent Angle Stream):
    - Tọa độ tâm (x, y) của Leanbot qua từng frame được lưu vào cửa sổ trượt W = 18.
    - Sử dụng đa thức bậc 2 để làm mượt riêng cho các dữ liệu tọa độ x và tọa độ y theo thời gian.
    - Tính đạo hàm tại điểm đánh giá để lấy vector vận tốc (dx, dy), từ đó tính góc tiếp tuyến qua hàm atan2(-dy, dx) và độ lớn vận tốc (speed).
  - Hợp nhất góc (Fused Angle): Kết hợp hai luồng (Model Angle và Trajectory Angle) bằng hàm trọng số phụ thuộc theo vận tốc với hằng số K = 1.0 px/frame: weight_x = K / (K + speed). 

- Code thay đổi 
  - Đoạn code cập nhật trong `angle_smoothing.py`:
  ```python
    # 2b. Fit 2D Degree 1 on (x, y) -> derivative at index -> angle + speed
    traj_raw_angle, speed = self._fit_trajectory_2d(
        x_buf=self.x_buffer,
        y_buf=self.y_buffer,
        degree=1, # sửa từ bậc 2 --> bậc 1
        eval_index=self.eval_index,
    )
  ```

- **Chỉ số trễ đánh giá (Smooth Index / Eval Index):**
  - Giá trị hiện tại: eval_index = `-4`
  - Code thay đổi cấu hình từ `-4` -> `0` trong `leanbotCameraController.py`
  ```python
    parser.add_argument("--smooth-index", type=int, default=0, help="Delayed tangent eval index (default 0)")
  ```


### 2. Chạy inference đánh giá với cấu hình : Kp_angle2 = 0.02 , angle_tolerance 10 -> 15 -> 20 

#### 2.1 angle_tolerance = 10
- Lệnh chạy:
```bash
python .\leanbotCameraController.py --show --source 1 --ble 387902 --heading-tol 10 --kp-angle2 0.02
```
- **Trường hợp 1:**
  - **Thời gian di chuyển:** ~17.4 giây (262 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~3.9 giây (59 frames)
  - **Thời gian Pha 2 (DRIVING):** ~13.4 giây (202 frames)
  - **Sai số cự ly cuối:** 12.3 px

  **Ảnh Detection UI thực tế:**

  ![Detection UI 1](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_115_20260903_112921_detection_ui.png)

  **Đồ thị quỹ đạo 2D:**

  ![Trajectory 1](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260903_112921_2d_trajectory.png)

  **Đồ thị PID & Góc:**

  ![PID 1](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260903_112921_pid_analysis.png)

---

- **Trường hợp 2:**
  - **Thời gian di chuyển:** ~11.3 giây (170 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~3.9 giây (60 frames)
  - **Thời gian Pha 2 (DRIVING):** ~7.2 giây (109 frames)
  - **Sai số cự ly cuối:** 10.2 px

  **Ảnh Detection UI thực tế:**

  ![Detection UI 2](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_467_20260903_112945_detection_ui.png)

  **Đồ thị quỹ đạo 2D:**

  ![Trajectory 2](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260903_112945_2d_trajectory.png)

  **Đồ thị PID & Góc:**

  ![PID 2](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260903_112945_pid_analysis.png)

---

- **Trường hợp 3:**
  - **Thời gian di chuyển:** ~14.7 giây (222 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~2.8 giây (44 frames)
  - **Thời gian Pha 2 (DRIVING):** ~11.8 giây (177 frames)
  - **Sai số cự ly cuối:** 10.5 px

  **Ảnh Detection UI thực tế:**

  ![Detection UI 3](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_762_20260903_113005_detection_ui.png)

  **Đồ thị quỹ đạo 2D:**

  ![Trajectory 3](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260903_113005_2d_trajectory.png)

  **Đồ thị PID & Góc:**

  ![PID 3](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260903_113005_pid_analysis.png)

---

- **Trường hợp 4:**
  - **Thời gian di chuyển:** ~12.6 giây (191 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~4.0 giây (61 frames)
  - **Thời gian Pha 2 (DRIVING):** ~8.5 giây (129 frames)
  - **Sai số cự ly cuối:** 12.8 px

  **Ảnh Detection UI thực tế:**

  ![Detection UI 4](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_1185_20260903_113033_detection_ui.png)

  **Đồ thị quỹ đạo 2D:**

  ![Trajectory 4](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260903_113033_2d_trajectory.png)

  **Đồ thị PID & Góc:**

  ![PID 4](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260903_113033_pid_analysis.png)






#### 2.2 angle_tolerance = 15
- Lệnh chạy:
```bash
python .\leanbotCameraController.py --show --source 1 --ble 387902 --heading-tol 15 --kp-angle2 0.02
```

- **Trường hợp 1:**
  - **Thời gian di chuyển:** ~17.5 giây (264 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~3.8 giây (59 frames)
  - **Thời gian Pha 2 (DRIVING):** ~13.6 giây (204 frames)
  - **Sai số cự ly cuối:** 11.7 px

  **Ảnh Detection UI thực tế:**

  ![Detection UI 1](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_451_20260903_113843_detection_ui.png)

  **Đồ thị quỹ đạo 2D:**

  ![Trajectory 1](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260903_113843_2d_trajectory.png)

  **Đồ thị PID & Góc:**

  ![PID 1](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260903_113843_pid_analysis.png)

---

- **Trường hợp 2:**
  - **Thời gian di chuyển:** ~11.4 giây (171 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~2.5 giây (38 frames)
  - **Thời gian Pha 2 (DRIVING):** ~8.8 giây (132 frames)
  - **Sai số cự ly cuối:** 11.0 px

  **Ảnh Detection UI thực tế:**

  ![Detection UI 2](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_821_20260903_113908_detection_ui.png)

  **Đồ thị quỹ đạo 2D:**

  ![Trajectory 2](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260903_113908_2d_trajectory.png)

  **Đồ thị PID & Góc:**

  ![PID 2](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260903_113908_pid_analysis.png)

---

- **Trường hợp 3:**
  - **Thời gian di chuyển:** ~13.5 giây (205 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~2.8 giây (43 frames)
  - **Thời gian Pha 2 (DRIVING):** ~10.7 giây (161 frames)
  - **Sai số cự ly cuối:** 10.8 px

  **Ảnh Detection UI thực tế:**

  ![Detection UI 3](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_1088_20260903_113925_detection_ui.png)

  **Đồ thị quỹ đạo 2D:**

  ![Trajectory 3](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260903_113925_2d_trajectory.png)

  **Đồ thị PID & Góc:**

  ![PID 3](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260903_113925_pid_analysis.png)

---

- **Trường hợp 4:**
  - **Thời gian di chuyển:** ~11.5 giây (174 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~3.8 giây (58 frames)
  - **Thời gian Pha 2 (DRIVING):** ~7.6 giây (115 frames)
  - **Sai số cự ly cuối:** 10.1 px

  **Ảnh Detection UI thực tế:**

  ![Detection UI 4](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_1383_20260903_113945_detection_ui.png)

  **Đồ thị quỹ đạo 2D:**

  ![Trajectory 4](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260903_113945_2d_trajectory.png)

  **Đồ thị PID & Góc:**

  ![PID 4](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260903_113945_pid_analysis.png)





#### 2.3 angle_tolerance = 20
- Lệnh chạy:
```bash
python .\leanbotCameraController.py --show --source 1 --ble 387902 --heading-tol 20 --kp-angle2 0.02
```
- **Trường hợp 1:**
  - **Thời gian di chuyển:** ~16.2 giây (244 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~2.9 giây (44 frames)
  - **Thời gian Pha 2 (DRIVING):** ~13.2 giây (199 frames)
  - **Sai số cự ly cuối:** 12.6 px

  **Ảnh Detection UI thực tế:**

  ![Detection UI 1](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_445_20260903_114719_detection_ui.png)

  **Đồ thị quỹ đạo 2D:**

  ![Trajectory 1](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260903_114719_2d_trajectory.png)

  **Đồ thị PID & Góc:**

  ![PID 1](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260903_114719_pid_analysis.png)

---

- **Trường hợp 2:**
  - **Thời gian di chuyển:** ~10.3 giây (155 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~2.4 giây (37 frames)
  - **Thời gian Pha 2 (DRIVING):** ~7.7 giây (117 frames)
  - **Sai số cự ly cuối:** 10.3 px

  **Ảnh Detection UI thực tế:**

  ![Detection UI 2](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_783_20260903_114742_detection_ui.png)

  **Đồ thị quỹ đạo 2D:**

  ![Trajectory 2](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260903_114742_2d_trajectory.png)

  **Đồ thị PID & Góc:**

  ![PID 2](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260903_114742_pid_analysis.png)

---

- **Trường hợp 3:**
  - **Thời gian di chuyển:** ~13.1 giây (197 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~2.4 giây (38 frames)
  - **Thời gian Pha 2 (DRIVING):** ~10.5 giây (158 frames)
  - **Sai số cự ly cuối:** 10.5 px

  **Ảnh Detection UI thực tế:**

  ![Detection UI 3](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_1061_20260903_114801_detection_ui.png)

  **Đồ thị quỹ đạo 2D:**

  ![Trajectory 3](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260903_114801_2d_trajectory.png)

  **Đồ thị PID & Góc:**

  ![PID 3](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260903_114801_pid_analysis.png)

---

- **Trường hợp 4:**
  - **Thời gian di chuyển:** ~13.7 giây (203 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~4.0 giây (60 frames)
  - **Thời gian Pha 2 (DRIVING):** ~9.6 giây (142 frames)
  - **Sai số cự ly cuối:** 11.3 px

  **Ảnh Detection UI thực tế:**

  ![Detection UI 4](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_1373_20260903_114822_detection_ui.png)

  **Đồ thị quỹ đạo 2D:**

  ![Trajectory 4](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260903_114822_2d_trajectory.png)

  **Đồ thị PID & Góc:**

  ![PID 4](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260903_114822_pid_analysis.png)


#### 2.4 Nhận xét tổng quan

| Tiêu chí so sánh | angle_tolerance = 10 | angle_tolerance = 15 | angle_tolerance = 20 | Đánh giá & Xu hướng |
| :--- | :---: | :---: | :---: | :--- |
| **Thời gian Pha 1 trung bình (Xoay ALIGNING)** | **3.64 s** (2.81 - 3.95s) | **3.21 s** (2.50 - 3.84s) | **2.91 s** (2.40 - 3.98s) | Giảm hơn , vì góc cần xuay nhỏ hơn và không cần căn chỉnh nhiều |
| **Thời gian Pha 2 trung bình (Chạy DRIVING)** | **10.22 s** (7.22 - 13.39s) | **10.15 s** (7.63 - 13.57s) | **10.27 s** (7.68 - 13.22s) | tương đương nhau |
| **Tổng thời gian hoàn thành trung bình** | **13.98 s** (11.27 - 17.37s) | **13.48 s** (11.36 - 17.54s) | **13.30 s** (10.27 - 16.20s) | Mức 20° tối ưu thời gian nhất, rút ngắn ~0.7s so với mức 10°. |
| **Sai số góc khi xong Pha 1** | **6.99°** (max 8.95°) | **12.38°** (max 14.87°) | **16.76°** (max 18.44°) | Luôn nhỏ hơn ngưỡng của angle_tol do quán tính của Leanbot |
| **Sai số cự ly cuối (Pixel)** | **11.49 px** (10.25 - 12.84px) | **10.91 px** (10.06 - 11.74px) | **11.18 px** (10.32 - 12.62px) | đều đúng với cấu hình 10px sai số chiều chỉnh trong code|

- **Về độ ổn định và quỹ đạo vi sai:**
  - **Mức 10°:** Leanbot cần phải xuay hướng chính xác hơn , từ đó sai số góc nhỏ , thì quỹ đạo di chuyển không bị lắc
  - **Mức 15° và 20°:** có độ ổn định thấp hơn vì góc dung sai lệch nhiều hơn, khiến Leanbot cần điều chỉnh nhiều dẫn tới quỹ đạo dao động liên tục 
  - Đối với cấu hình hiện tại em thấy mức Angle2 kp = 0.02 vẫn còn hơi cao ạ.

## B. Khó khăn 
- Không
## C. Công việc tiếp theo 
- Hiện tại nếu tăng Angle_tolrence thì với Angle kp = 0.02 thì Leanbot khi đi bị lắc ( overshoot) ạ, em có cần giảm kp và chạy thửu nghiệm lại không ạ ? 
- Em xin phép nhận hướng đi tiếp theo từ Thầy ạ 

