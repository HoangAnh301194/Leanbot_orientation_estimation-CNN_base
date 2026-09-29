# Báo cáo công việc ngày 29/09/2026

## A. Công việc đã làm
- Cải tiến phase 1 và 2 cho phép đi lùi khi góc > +-90 độ


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

- Các cấu hình hệ số PID phase 1&2 hiện tại
    - Phase 1 (Kp_angle, Kd_angle): Kp = 30.0, Kd = 0.0
    - Phase 2 (Kp_angle2, Kd_angle2): Kp = 0.01, Kd = 0.04

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

## B. Khó khăn 
- Không
## C. Công việc tiếp theo
- Em xin phép nhận hướng đi tiếp theo từ Thầy ạ.