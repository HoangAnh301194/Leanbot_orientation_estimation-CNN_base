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

  ![Trajectory 1](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260904_151012_2d_trajectory.png)

  **Đồ thị PID & Góc:**

  ![PID 1](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260904_151012_pid_analysis.png)


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



## B. Khó khăn 
- Em nghĩ một số nguyên nhân khiến xe bị lắc khi tăng kp và dùng thêm kd để hãm vận tốc nhưng không cải thiện, Có thể do độ trễ điều khiển thông qua BLE ạ
## C. Công việc tiếp theo 
 - Em xin phép nhận thêm đề xuất của Thầy về một số cách debug lỗi do đâu ạ 
 - Hiện tại em chỉ mới nghĩ được là có thể đo thời gian truyền, nhận lệnh điều khiển stepper qua BLE để kiểm tra độ trễ thôi ạ.