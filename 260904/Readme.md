# Báo cáo công việc ngày 04/09/2026


## A. Công việc đã làm 
- Bỏ lệnh gửi vận tốc về (0,0) khi kết thúc phase 1 chuyển sang phase 2 
- Tăng hệ số Angle kp lên 30 
- Tăng dần hệ số Angle2 kd lên và tìm ngưỡng ổn định



### 1. Bỏ bước gửi vận tốc về (0,0) khi kết thúc phase 1 chuyển sang phase 2 
- Code chuyển phase hiện tại 

```python 
        # Phase 1: ALIGNING - spin in place until heading error is within tolerance
        if self.phase == self.PHASE_ALIGNING:
            if abs(angle_error) <= self.heading_tolerance:
                self.phase = self.PHASE_DRIVING
                debug = self._debug(
                    self.PHASE_ALIGN_COMPLETE, distance_error, target_heading,
                    angle_error, 0.0, 0.0,
                )
                return 0, 0, debug # phần cần loại bỏ 

            # Phase 1 PID for angle
            self._integral_angle += angle_error
            d_angle = (angle_error - self._prev_angle_error) if self._prev_angle_error is not None else 0.0
            self._prev_angle_error = angle_error

            v_lr = 0.0
            v_diff = (self.Kp_angle * angle_error
                      + self.Ki_angle * self._integral_angle
                      + self.Kd_angle * d_angle)
            speed_left, speed_right = self._scale_speeds(v_lr + v_diff, v_lr - v_diff)
            debug = self._debug(
                self.PHASE_ALIGNING, distance_error, target_heading,
                angle_error, v_lr, v_diff,
            )
            return speed_left, speed_right, debug
```

- Code chỉnh sửa để bỏ phần gửi vận tốc về (0,0) khi chuyển phase

```python
        # Phase 1: ALIGNING - spin in place until heading error is within tolerance
        if self.phase == self.PHASE_ALIGNING:
            if abs(angle_error) <= self.heading_tolerance:
                self.phase = self.PHASE_DRIVING
            else:
                # Phase 1 PID for angle
                self._integral_angle += angle_error
                d_angle = (angle_error - self._prev_angle_error) if self._prev_angle_error is not None else 0.0
                self._prev_angle_error = angle_error

                v_lr = 0.0
                v_diff = (self.Kp_angle * angle_error
                          + self.Ki_angle * self._integral_angle
                          + self.Kd_angle * d_angle)
                speed_left, speed_right = self._scale_speeds(v_lr + v_diff, v_lr - v_diff)
                debug = self._debug(
                    self.PHASE_ALIGNING, distance_error, target_heading,
                    angle_error, v_lr, v_diff,
                )
                return speed_left, speed_right, debug
```

### 2. Tăng Angle Kp lên 30 và chạy thử nghiệm khi tăng Angle2 kd tăng lên 

- Cấu hình hiện tại của bộ điều khiển PID : 
  - `Kp_dist = 25.0`, `Ki_dist = 0.0`, `Kd_dist = 0.0`
  - `Kp_angle = 15.0`, `Ki_angle = 0.0`, `Kd_angle = 0.0`
  - `Kp_angle2 = 0.02`, `Ki_angle2 = 0.0`, `Kd_angle2 = 0.0`
  - `dist_tolerance = 10.0 px`
  - `heading_tolerance = 5.0°`

- Cấu hình thay đổi : 
  - `Kp_angle = 30.0`
  - `Kd_angle2`: khảo sát từ `0.0` và tăng dần từ `0.005` lên để tìm ngưỡng ổn định


#### 2.1 Chạy Inference cấu hình Angle2 kd = 0.0
- Lệnh chạy:
```bash
python .\leanbotCameraController.py --show --source 1 --ble 983949 --kp-angle 30 --kd-angle2 0.0
```

- **Trường hợp 1:**
  - **Thời gian di chuyển:** ~13.0 giây (196 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~2.3 giây (36 frames)
  - **Thời gian Pha 2 (DRIVING):** ~10.6 giây (160 frames)
  - **Sai số cự ly cuối:** 10.2 px

  **Đồ thị quỹ đạo 2D:**

  ![Trajectory 1](LeanbotTinyRC/benchmark_logs_0/plots/log_roi_20260904_151012_2d_trajectory.png)

  **Đồ thị PID & Góc:**

  ![PID 1](LeanbotTinyRC/benchmark_logs_0/plots/log_roi_20260904_151012_pid_analysis.png)


#### 2.2 Chạy Inference cấu hình Angle2 kd = 0.005
- Lệnh chạy:
```bash
python .\leanbotCameraController.py --show --source 1 --ble 983949 --kp-angle 30 --kd-angle2 0.005
```

- **Trường hợp 1:**
  - **Thời gian di chuyển:** ~13.2 giây (200 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~2.3 giây (36 frames)
  - **Thời gian Pha 2 (DRIVING):** ~10.8 giây (164 frames)
  - **Sai số cự ly cuối:** 10.4 px

  **Đồ thị quỹ đạo 2D:**

  ![Trajectory 1](LeanbotTinyRC/benchmark_logs_1/plots/log_roi_20260904_143721_2d_trajectory.png)

  **Đồ thị PID & Góc:**

  ![PID 1](LeanbotTinyRC/benchmark_logs_1/plots/log_roi_20260904_143721_pid_analysis.png)

---

- **Trường hợp 2:**
  - **Thời gian di chuyển:** ~13.0 giây (196 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~2.4 giây (37 frames)
  - **Thời gian Pha 2 (DRIVING):** ~10.5 giây (159 frames)
  - **Sai số cự ly cuối:** 10.2 px

  **Đồ thị quỹ đạo 2D:**

  ![Trajectory 2](LeanbotTinyRC/benchmark_logs_1/plots/log_roi_20260904_143745_2d_trajectory.png)

  **Đồ thị PID & Góc:**

  ![PID 2](LeanbotTinyRC/benchmark_logs_1/plots/log_roi_20260904_143745_pid_analysis.png)


#### 2.3 Chạy Inference cấu hình Angle2 kd = 0.01
- Lệnh chạy:
```bash
python .\leanbotCameraController.py --show --source 1 --ble 983949 --kp-angle 30 --kd-angle2 0.01
```

- **Trường hợp 1:**
  - **Thời gian di chuyển:** ~16.3 giây (248 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~2.6 giây (42 frames)
  - **Thời gian Pha 2 (DRIVING):** ~13.7 giây (206 frames)
  - **Sai số cự ly cuối:** 11.5 px

  **Đồ thị quỹ đạo 2D:**

  ![Trajectory 1](LeanbotTinyRC/benchmark_logs_2/plots/log_roi_20260904_143938_2d_trajectory.png)

  **Đồ thị PID & Góc:**

  ![PID 1](LeanbotTinyRC/benchmark_logs_2/plots/log_roi_20260904_143938_pid_analysis.png)

---

- **Trường hợp 2:**
  - **Thời gian di chuyển:** ~14.0 giây (212 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~2.2 giây (35 frames)
  - **Thời gian Pha 2 (DRIVING):** ~11.7 giây (177 frames)
  - **Sai số cự ly cuối:** 10.6 px

  **Đồ thị quỹ đạo 2D:**

  ![Trajectory 2](LeanbotTinyRC/benchmark_logs_2/plots/log_roi_20260904_144000_2d_trajectory.png)

  **Đồ thị PID & Góc:**

  ![PID 2](LeanbotTinyRC/benchmark_logs_2/plots/log_roi_20260904_144000_pid_analysis.png)


#### 2.4 Chạy Inference cấu hình Angle2 kd = 0.02
- Lệnh chạy:
```bash
python .\leanbotCameraController.py --show --source 1 --ble 983949 --kp-angle 30 --kd-angle2 0.02
```

- **Trường hợp 1:**
  - **Thời gian di chuyển:** ~13.9 giây (210 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~2.6 giây (40 frames)
  - **Thời gian Pha 2 (DRIVING):** ~11.3 giây (170 frames)
  - **Sai số cự ly cuối:** 11.6 px

  **Đồ thị quỹ đạo 2D:**

  ![Trajectory 1](LeanbotTinyRC/benchmark_logs_3/plots/log_roi_20260904_144051_2d_trajectory.png)

  **Đồ thị PID & Góc:**

  ![PID 1](LeanbotTinyRC/benchmark_logs_3/plots/log_roi_20260904_144051_pid_analysis.png)

---

- **Trường hợp 2:**
  - **Thời gian di chuyển:** ~12.3 giây (185 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~2.2 giây (35 frames)
  - **Thời gian Pha 2 (DRIVING):** ~9.9 giây (150 frames)
  - **Sai số cự ly cuối:** 12.2 px

  **Đồ thị quỹ đạo 2D:**

  ![Trajectory 2](LeanbotTinyRC/benchmark_logs_3/plots/log_roi_20260904_144113_2d_trajectory.png)

  **Đồ thị PID & Góc:**

  ![PID 2](LeanbotTinyRC/benchmark_logs_3/plots/log_roi_20260904_144113_pid_analysis.png)


#### 2.5 Chạy Inference cấu hình Angle2 kd = 0.04
- Lệnh chạy:
```bash
python .\leanbotCameraController.py --show --source 1 --ble 983949 --kp-angle 30 --kd-angle2 0.04
```

- **Trường hợp 1:**
  - **Thời gian di chuyển:** ~16.4 giây (248 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~2.8 giây (44 frames)
  - **Thời gian Pha 2 (DRIVING):** ~13.5 giây (204 frames)
  - **Sai số cự ly cuối:** 11.6 px

  **Đồ thị quỹ đạo 2D:**

  ![Trajectory 1](LeanbotTinyRC/benchmark_logs_4/plots/log_roi_20260904_144208_2d_trajectory.png)

  **Đồ thị PID & Góc:**

  ![PID 1](LeanbotTinyRC/benchmark_logs_4/plots/log_roi_20260904_144208_pid_analysis.png)

---

- **Trường hợp 2:**
  - **Thời gian di chuyển:** ~12.7 giây (192 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~2.4 giây (38 frames)
  - **Thời gian Pha 2 (DRIVING):** ~10.3 giây (154 frames)
  - **Sai số cự ly cuối:** 11.2 px

  **Đồ thị quỹ đạo 2D:**

  ![Trajectory 2](LeanbotTinyRC/benchmark_logs_4/plots/log_roi_20260904_144231_2d_trajectory.png)

  **Đồ thị PID & Góc:**

  ![PID 2](LeanbotTinyRC/benchmark_logs_4/plots/log_roi_20260904_144231_pid_analysis.png)


#### 2.6 Chạy Inference cấu hình Angle2 kd = 0.08
- Lệnh chạy:
```bash
python .\leanbotCameraController.py --show --source 1 --ble 983949 --kp-angle 30 --kd-angle2 0.08
```

- **Trường hợp 1:**
  - **Thời gian di chuyển:** ~15.0 giây (227 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~3.1 giây (48 frames)
  - **Thời gian Pha 2 (DRIVING):** ~11.9 giây (179 frames)
  - **Sai số cự ly cuối:** 11.3 px

  **Đồ thị quỹ đạo 2D:**

  ![Trajectory 1](LeanbotTinyRC/benchmark_logs_5/plots/log_roi_20260904_144336_2d_trajectory.png)

  **Đồ thị PID & Góc:**

  ![PID 1](LeanbotTinyRC/benchmark_logs_5/plots/log_roi_20260904_144336_pid_analysis.png)

---

- **Trường hợp 2:**
  - **Thời gian di chuyển:** ~13.7 giây (207 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~2.7 giây (42 frames)
  - **Thời gian Pha 2 (DRIVING):** ~10.9 giây (165 frames)
  - **Sai số cự ly cuối:** 10.1 px

  **Đồ thị quỹ đạo 2D:**

  ![Trajectory 2](LeanbotTinyRC/benchmark_logs_5/plots/log_roi_20260904_144417_2d_trajectory.png)

  **Đồ thị PID & Góc:**

  ![PID 2](LeanbotTinyRC/benchmark_logs_5/plots/log_roi_20260904_144417_pid_analysis.png)


> **Từ kết quả thực nghiệm cho thấy ngay ở cấu hình `kp=30, kd=0.0` thì Leanbot đã có hiện tượng lắc qua lại trong quá trình di chuyển, và khi tăng dần từ `0.0` lên `0.005`, `0.01`, ..., `0.08` (và thực tế em đã thử tăng lên tới `0.1`, `0.5`) mà dao động không giảm mà xe càng bị lắc hơn.**



### 3. Chỉnh sửa cấu hình mới và chạy thử nghiệm 
- **Cấu hình chỉnh sửa mới** :
  - `heading_tolerance` = 15 
  - `Kp_angle` = 30
  - `Kp_angle2` = 0.02

- **Thử nghiệm với `kd_angle2 ` = 0.005 :**
- Lệnh chạy:
```bash
python .\leanbotCameraController.py --show --source 1 --ble 983949 --heading-tol 15 --kp-angle 30 --kp-angle2 0.02 --kd-angle2 0.005
```

- **Trường hợp 1:**
  - **Thời gian di chuyển:** ~15.4 giây (233 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~2.4 giây (37 frames)
  - **Thời gian Pha 2 (DRIVING):** ~13.0 giây (196 frames)
  - **Sai số cự ly cuối:** 11.0 px

  **Ảnh Detection UI thực tế:**

  ![Detection UI 1](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_122_20260904_162256_detection_ui.png)

  **Đồ thị quỹ đạo 2D:**

  ![Trajectory 1](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260904_162256_2d_trajectory.png)

  **Đồ thị PID & Góc:**

  ![PID 1](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260904_162256_pid_analysis.png)

  **Đồ thị Vi phân & Tỉ số bẻ lái (Error Angle, de/dt, v_diff):**

  ![Diff 1](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260904_162256_pid_diff_analysis.png)

---

- **Trường hợp 2:**
  - **Thời gian di chuyển:** ~13.1 giây (198 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~2.3 giây (36 frames)
  - **Thời gian Pha 2 (DRIVING):** ~10.7 giây (162 frames)
  - **Sai số cự ly cuối:** 10.1 px

  **Ảnh Detection UI thực tế:**

  ![Detection UI 2](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_415_20260904_162316_detection_ui.png)

  **Đồ thị quỹ đạo 2D:**

  ![Trajectory 2](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260904_162316_2d_trajectory.png)

  **Đồ thị PID & Góc:**

  ![PID 2](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260904_162316_pid_analysis.png)

  **Đồ thị Vi phân & Tỉ số bẻ lái (Error Angle, de/dt, v_diff):**

  ![Diff 2](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260904_162316_pid_diff_analysis.png)

---

- **Trường hợp 3:**
  - **Thời gian di chuyển:** ~23.7 giây (356 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~2.2 giây (35 frames)
  - **Thời gian Pha 2 (DRIVING):** ~21.3 giây (321 frames)
  - **Sai số cự ly cuối:** 21.6 px

  **Ảnh Detection UI thực tế:**

  ![Detection UI 3](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_683_20260904_162334_detection_ui.png)

  **Đồ thị quỹ đạo 2D:**

  ![Trajectory 3](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260904_162334_2d_trajectory.png)

  **Đồ thị PID & Góc:**

  ![PID 3](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260904_162334_pid_analysis.png)

  **Đồ thị Vi phân & Tỉ số bẻ lái (Error Angle, de/dt, v_diff):**

  ![Diff 3](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260904_162334_pid_diff_analysis.png)



- **Thử nghiệm với `kd_angle2 ` = 0.01 :**
- Lệnh chạy:
```bash
python .\leanbotCameraController.py --show --source 1 --ble 983949 --heading-tol 15 --kp-angle 30 --kp-angle2 0.02 --kd-angle2 0.01
```

- **Trường hợp 1:**
  - **Thời gian di chuyển:** ~16.4 giây (248 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~3.0 giây (47 frames)
  - **Thời gian Pha 2 (DRIVING):** ~13.4 giây (201 frames)
  - **Sai số cự ly cuối:** 10.2 px

  **Ảnh Detection UI thực tế:**

  ![Detection UI 1](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_28_20260904_163308_detection_ui.png)

  **Đồ thị quỹ đạo 2D:**

  ![Trajectory 1](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260904_163308_2d_trajectory.png)

  **Đồ thị PID & Góc:**

  ![PID 1](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260904_163308_pid_analysis.png)

  **Đồ thị Vi phân & Tỉ số bẻ lái (Error Angle, de/dt, v_diff):**

  ![Diff 1](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260904_163308_pid_diff_analysis.png)

---

- **Trường hợp 2:**
  - **Thời gian di chuyển:** ~13.0 giây (196 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~2.4 giây (37 frames)
  - **Thời gian Pha 2 (DRIVING):** ~10.5 giây (159 frames)
  - **Sai số cự ly cuối:** 10.7 px

  **Ảnh Detection UI thực tế:**

  ![Detection UI 2](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_340_20260904_163329_detection_ui.png)

  **Đồ thị quỹ đạo 2D:**

  ![Trajectory 2](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260904_163329_2d_trajectory.png)

  **Đồ thị PID & Góc:**

  ![PID 2](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260904_163329_pid_analysis.png)

  **Đồ thị Vi phân & Tỉ số bẻ lái (Error Angle, de/dt, v_diff):**

  ![Diff 2](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260904_163329_pid_diff_analysis.png)

---

- **Trường hợp 3:**
  - **Thời gian di chuyển:** ~10.1 giây (152 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~2.2 giây (34 frames)
  - **Thời gian Pha 2 (DRIVING):** ~7.8 giây (118 frames)
  - **Sai số cự ly cuối:** 10.3 px

  **Ảnh Detection UI thực tế:**

  ![Detection UI 3](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_638_20260904_163349_detection_ui.png)

  **Đồ thị quỹ đạo 2D:**

  ![Trajectory 3](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260904_163349_2d_trajectory.png)

  **Đồ thị PID & Góc:**

  ![PID 3](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260904_163349_pid_analysis.png)

> đồ thị góc không unwrap nên góc bị nhảy giữa -180 và 180 độ ạ .

  **Đồ thị Vi phân & Tỉ số bẻ lái (Error Angle, de/dt, v_diff):**

  ![Diff 3](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260904_163349_pid_diff_analysis.png)

---

- **Trường hợp 4:**
  - **Thời gian di chuyển:** ~10.2 giây (156 frames)
  - **Thời gian Pha 1 (ALIGNING):** ~2.1 giây (35 frames)
  - **Thời gian Pha 2 (DRIVING):** ~8.0 giây (121 frames)
  - **Sai số cự ly cuối:** 10.1 px

  **Ảnh Detection UI thực tế:**

  ![Detection UI 4](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_935_20260904_163410_detection_ui.png)

  **Đồ thị quỹ đạo 2D:**

  ![Trajectory 4](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260904_163409_2d_trajectory.png)

  **Đồ thị PID & Góc:**

  ![PID 4](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260904_163409_pid_analysis.png)

  **Đồ thị Vi phân & Tỉ số bẻ lái (Error Angle, de/dt, v_diff):**

  ![Diff 4](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260904_163409_pid_diff_analysis.png)




## B. Khó khăn 
- Không
## C. Công việc tiếp theo 
 - Em xin phép nhận hướng đi tiếp theo từ Thầy ạ .