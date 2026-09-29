# Báo cáo công việc ngày 29/09/2026

## Mục lục
- [A. Công việc đã làm](#a-công-việc-đã-làm)
  - [1. Bổ sung cơ chế đi lùi](#1-bổ-sung-cơ-chế-đi-lùi)
  - [2. Tách riêng bộ điều khiển PID cho 2 trường hợp tiến và lùi vể target pixel](#2-tách-riêng-bộ-điều-khiển-pid-cho-2-trường-hợp-tiến-và-lùi-vể-target-pixel)
- [B. Khó khăn](#b-khó-khăn)
- [C. Công việc tiếp theo](#c-công-việc-tiếp-theo)

## A. Công việc đã làm
- Cải tiến phase 1 và 2 cho phép đi lùi khi góc > +-90 độ
- Tách riêng bộ điều khiển PID cho 2 trường hợp tiến và lùi tới target pixel
### 1. Bổ sung cơ chế đi lùi 
- **Code chỉnh sửa & Bổ sung:** 
  - Module điều khiển PID: [`PID_controller.py`](LeanbotTinyRC_AI_PIDControl/PID_controller.py)
- Code bổ sung : 
```python
        # Phát hiện và đảo chiều ở Phase 1 nếu lệch > 90 độ
        if not self._initial_angle_checked and self.phase == self.PHASE_ALIGNING:
            initial_error = wrap_to_180(current_angle - bearing_heading)
            if abs(initial_error) > 90.0: # Nếu lệch quá 90 độ
                self.is_reversing = True # Đảo chiều
            self._initial_angle_checked = True

        if self.is_reversing:
            bearing_heading = wrap_to_180(bearing_heading + 180.0) # Đảo chiều hướng mục tiêu 

        # Đảo chiều vận tốc tiến/lùi ở Phase 2
        if self.is_reversing:
            v_lr_cropped = -v_lr_cropped
```

- Cơ chế hiện tại sau khi thay đổi : 
    - Ở Phase 1 (ALIGNING), hệ thống kiểm tra góc lệch `initial_error`. Nếu phát hiện góc lệch trên +-90 độ , hệ thống bật cờ `is_reversing = True` và cộng thêm 180 độ vào `bearing_heading`.
    - Leanbot xoay một góc nhỏ (để hướng đuôi về mục tiêu) không cần phải quay đầu 1 góc lớn hơn 90 độ.
    - Ở Phase 2 (DRIVING), nếu cờ `is_reversing = True`, vận tốc tịnh tiến `v_lr` được đảo thành số âm (chạy lùi). 
    - Các module điều khiển PID khác không thay đổi. 

- Chạy inference thực thế 
    - Lệnh chạy: 
        ```bash
        python leanbotCameraController.py --ble 654321 --source 1 --kp-spin 18.8 --spin-speed 50
        ```
- Kết quả đồ thị phân tích quỹ đạo đi lùi/tiến (Trích xuất từ các log chạy thực tế):

  - **Trường hợp 1 (log_roi_20260929_134715):** 
    ![Trajectory 134715](LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260929_134715_2d_trajectory.png)
    ![PID Analysis 134715](LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260929_134715_pid_analysis.png)
    ![PID Diff 134715](LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260929_134715_pid_diff_analysis.png)

  - **Trường hợp 2 (log_roi_20260929_134914):** 
    ![Trajectory 134914](LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260929_134914_2d_trajectory.png)
    ![PID Analysis 134914](LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260929_134914_pid_analysis.png)
    ![PID Diff 134914](LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260929_134914_pid_diff_analysis.png)

  - **Trường hợp 3 (log_roi_20260929_135027):** 
    ![Trajectory 135027](LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260929_135027_2d_trajectory.png)
    ![PID Analysis 135027](LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260929_135027_pid_analysis.png)
    ![PID Diff 135027](LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260929_135027_pid_diff_analysis.png)

  - **Trường hợp 4 (log_roi_20260929_135143):** 
    ![Trajectory 135143](LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260929_135143_2d_trajectory.png)
    ![PID Analysis 135143](LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260929_135143_pid_analysis.png)
    ![PID Diff 135143](LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260929_135143_pid_diff_analysis.png)

  - **Trường hợp 5 (log_roi_20260929_135213):** 
    ![Trajectory 135213](LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260929_135213_2d_trajectory.png)
    ![PID Analysis 135213](LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260929_135213_pid_analysis.png)
    ![PID Diff 135213](LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260929_135213_pid_diff_analysis.png)

> Từ các đồ thị góc có thể thấy Leanbot trong phase 1 và 2 dao động quanh góc 180 độ ( vì không unwrap nên đồ thị góc bị nhảy ) và đi lùi cho tới phase 3 sẽ bắt đầu xuay góc để về target heading . 

> Từ đồ thị vận tốc có thể thấy vận tốc Leanbot đi lùi ( vận tốc âm) trong phase 2 . Tuy nhiên có thể do phía đuôi Leanbot nặng hơn nên với cùng bộ điều khiển PID thì khi đi lùi bị bẻ cua hơi chậm ( theo đồ thị trajectory có thể thấy quỹ đạo cong rộng) . Ngoài ra theo em thấy thì do cuối Phase 1 + đầu phase 2 khi xuay góc về target pixel Leanbot bị xuay quá 1 chút nên Leanbot cần phải đi cong  1 đoạn để bẻ quỹ đạo thẳng về hướng target pixel ạ. 


### 2. Tách riêng bộ điều khiển PID cho 2 trường hợp tiến và lùi vể target pixel 
- Tách riêng bộ điều khiển cho 2 trường hợp và tuning hệ số sao cho khi đi Lùi ổn định nhanh hơn so với bộ PID dùng chung với trường hợp đi tiến.
- Bổ sung các CLI param hệ số PID cũ, thay bằng các tên mới phù hợp với 2 trường hợp tiến và lùi  
- **Code chỉnh sửa:** 
  - File điều khiển PID: [`PID_controller.py`](LeanbotTinyRC_AI_PIDControl/PID_controller.py)
- **Code bổ sung:** 
  - *Trong `leanbotCameraController.py` (Khai báo CLI param bổ sung):*
```python
    # Thông số cho trường hợp đi tiến (Forward) sẵn có 
    parser.add_argument("--kp-angle", type=float, default=30.0, help="PID Phase 1 heading gain (default 30.0)")
    parser.add_argument("--kd-angle", type=float, default=0.0, help="PID Phase 1 derivative gain (default 0.0)")
    parser.add_argument("--kp-angle2", type=float, default=0.01, help="PID Phase 2 heading gain (default 0.01)")
    parser.add_argument("--kd-angle2", type=float, default=0.04, help="PID Phase 2 derivative gain (default 0.04)")

    # Thông số bổ sung cho trường hợp đi lùi (Reverse)
    parser.add_argument("--kp-angle-rev", type=float, default=20.0, help="PID Phase 1 reversing heading gain")
    parser.add_argument("--kd-angle-rev", type=float, default=0.0, help="PID Phase 1 reversing derivative gain")
    parser.add_argument("--kp-angle2-rev", type=float, default=0.01, help="PID Phase 2 reversing heading gain")
    parser.add_argument("--kd-angle2-rev", type=float, default=0.05, help="PID Phase 2 reversing derivative gain")
```
  - *Trong `PID_controller.py` (Áp dụng hệ số riêng cho Phase 1 và Phase 2 khi đi lùi):*
```python
        # Phase 1: Xoay đầu/đuôi
        if self.is_reversing:
            # Dùng hệ số đi lùi
            kp = self.Kp_angle_rev
            kd = self.Kd_angle_rev
        else:
            # Dùng hệ số đi tiến gốc
            kp = self.Kp_angle
            kd = self.Kd_angle
            
        v_diff = (kp * angle_error + self.Ki_angle * self._integral_angle + kd * d_angle)

        # Phase 2: Chạy thẳng kết hợp bù góc
        if self.is_reversing:
            kp2 = self.Kp_angle2_rev
            kd2 = self.Kd_angle2_rev
        else:
            kp2 = self.Kp_angle2
            kd2 = self.Kd_angle2
            
        delta_v = (kp2 * angle_error + self.Ki_angle2 * self._integral_angle2 + kd2 * d_angle2) * abs(v_lr_cropped)
```

- Trong quá trình kiểm thử và tuning em chọn cấu hình hệ số PID phase 1&2 hiện tại như sau:
    - **Trường hợp đi tiến (Forward):**
        - Phase 1 (`--kp-angle`, `--kd-angle`): Kp = 30.0, Kd = 0.0
        - Phase 2 (`--kp-angle2`, `--kd-angle2`): Kp = 0.01, Kd = 0.04
    - **Trường hợp đi lùi (Reverse):** 
        - Phase 1 (`--kp-angle-rev`, `--kd-angle-rev`): Kp = 15.0, Kd = 0.0 
        - Phase 2 (`--kp-angle2-rev`, `--kd-angle2-rev`): Kp = 0.015, Kd = 0.05

- Lệnh chạy : 
```bash
python leanbotCameraController.py --ble 654321 --source 1 --kp-spin 18.8 --spin-speed 50 --kp-angle-rev 15.0 --kd-angle-rev 0.0 --kp-angle2-rev 0.015 --kd-angle2-rev 0.05
```

- Chạy inference thực tế : 

  - **Trường hợp 1 (log_roi_20260929_153636):** 
    ![Trajectory 153636](LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260929_153636_2d_trajectory.png)
    ![PID Analysis 153636](LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260929_153636_pid_analysis.png)
    ![PID Diff 153636](LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260929_153636_pid_diff_analysis.png)

  - **Trường hợp 2 (log_roi_20260929_153758):** 
    ![Trajectory 153758](LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260929_153758_2d_trajectory.png)
    ![PID Analysis 153758](LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260929_153758_pid_analysis.png)
    ![PID Diff 153758](LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260929_153758_pid_diff_analysis.png)

  - **Trường hợp 3 (log_roi_20260929_153835):** 
    ![Trajectory 153835](LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260929_153835_2d_trajectory.png)
    ![PID Analysis 153835](LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260929_153835_pid_analysis.png)
    ![PID Diff 153835](LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260929_153835_pid_diff_analysis.png)

## B. Khó khăn 
- Không
## C. Công việc tiếp theo
- Bố sung thêm cơ chế Spin thuật , nghịch và khảo sát lại với step nhỏ = 10 