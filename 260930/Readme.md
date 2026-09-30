# Báo cáo công việc ngày 30/09/2026

## A. Công việc đã làm 
- Khảo sát thêm ngẫu nhiên các trường hợp Leanbot chạy Phase 1 và 2 đi lùi, tiến ngẫu nhiên 
- Bổ sung chương trình khảo sát bước Step nhỏ : 
  - số step: range(0,201,10) 
  - khoảng thời gian : range(1500,3001,250) milisecond. 
  - Đảo chiều xoay về vị trí ban đầu sau mỗi bước step 

### 1. Khảo sát ngẫu nhiên các trường hợp Leanbot chạy tiến, lùi 
- Triển khai khảo sát ngẫu nhiên các trường hợp tiến, lùi về target pixel. 
- Lệnh chạy : 
```bash

```
- Các trường hợp thử nghiệm như sau : 

- **Trường hợp 1 (Chạy LÙI)**
  - Tên log: `log_roi_20260930_154848.csv`
  - Quỹ đạo 2D (2D Trajectory): ![Xem hình](LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260930_154848_2d_trajectory.png)
  - Đồ thị PID Analysis: ![Xem hình](LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260930_154848_pid_analysis.png)
  - Đồ thị sai số (Diff Analysis): ![Xem hình](LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260930_154848_pid_diff_analysis.png)
  - Tổng hợp Phase 4 (Spin bù góc): 
    - Target heading: 15.3°
    - Heading lần 1 (trước Spin): 17.86° (Error: +2.56°)
    - Bù góc: Xoay 48 steps (speed=50)
    - Heading lần 2 (sau Spin): 15.68° (Error: +0.38°)
    - Mức độ cải thiện: 2.18°

- **Trường hợp 2 (Chạy TIẾN)**
  - Tên log: `log_roi_20260930_154930.csv`
  - Quỹ đạo 2D (2D Trajectory): ![Xem hình](LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260930_154930_2d_trajectory.png)
  - Đồ thị PID Analysis: ![Xem hình](LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260930_154930_pid_analysis.png)
  - Đồ thị sai số (Diff Analysis): ![Xem hình](LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260930_154930_pid_diff_analysis.png)
  - Tổng hợp Phase 4 (Spin bù góc): 
    - Target heading: 15.3°
    - Heading lần 1 (trước Spin): 13.17° (Error: -2.13°)
    - Bù góc: Xoay 40 steps (speed=-50)
    - Heading lần 2 (sau Spin): 14.52° (Error: -0.78°)
    - Mức độ cải thiện: 1.35°

- **Trường hợp 3 (Chạy LÙI)**
  - Tên log: `log_roi_20260930_155020.csv`
  - Quỹ đạo 2D (2D Trajectory): ![Xem hình](LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260930_155020_2d_trajectory.png)
  - Đồ thị PID Analysis: ![Xem hình](LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260930_155020_pid_analysis.png)
  - Đồ thị sai số (Diff Analysis): ![Xem hình](LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260930_155020_pid_diff_analysis.png)
  - Tổng hợp Phase 4 (Spin bù góc): 
    - Target heading: 15.3°
    - Heading lần 1 (trước Spin): 12.99° (Error: -2.31°)
    - Bù góc: Xoay 43 steps (speed=-50)
    - Heading lần 2 (sau Spin): 14.29° (Error: -1.01°)
    - Mức độ cải thiện: 1.30°

- **Trường hợp 4 (Chạy LÙI)**
  - Tên log: `log_roi_20260930_155126.csv`
  - Quỹ đạo 2D (2D Trajectory): ![Xem hình](LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260930_155126_2d_trajectory.png)
  - Đồ thị PID Analysis: ![Xem hình](LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260930_155126_pid_analysis.png)
  - Đồ thị sai số (Diff Analysis): ![Xem hình](LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260930_155126_pid_diff_analysis.png)
  - Tổng hợp Phase 4 (Spin bù góc): 
    - Target heading: 15.3°
    - Heading lần 1 (trước Spin): 12.12° (Error: -3.18°)
    - Bù góc: Xoay 60 steps (speed=-50)
    - Heading lần 2 (sau Spin): 13.93° (Error: -1.37°)
    - Mức độ cải thiện: 1.81°

- **Trường hợp 5 (Chạy TIẾN)**
  - Tên log: `log_roi_20260930_155215.csv`
  - Quỹ đạo 2D (2D Trajectory): ![Xem hình](LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260930_155215_2d_trajectory.png)
  - Đồ thị PID Analysis: ![Xem hình](LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260930_155215_pid_analysis.png)
  - Đồ thị sai số (Diff Analysis): ![Xem hình](LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260930_155215_pid_diff_analysis.png)
  - Tổng hợp Phase 4 (Spin bù góc): 
    - Target heading: 15.3°
    - Heading lần 1 (trước Spin): 16.59° (Error: +1.29°)
    - Bù góc: Xoay 24 steps (speed=50)
    - Heading lần 2 (sau Spin): 15.52° (Error: +0.22°)
    - Mức độ cải thiện: 1.08°
- **Trường hợp 6 (Chạy TIẾN)**
  - Tên log: `log_roi_20260930_161600.csv`
  - Quỹ đạo 2D (2D Trajectory): ![Xem hình](LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260930_161600_2d_trajectory.png)
  - Đồ thị PID Analysis: ![Xem hình](LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260930_161600_pid_analysis.png)
  - Đồ thị sai số (Diff Analysis): ![Xem hình](LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260930_161600_pid_diff_analysis.png)
  - Tổng hợp Phase 4 (Spin bù góc): 
    - Target heading: 15.3°
    - Heading lần 1 (trước Spin): 14.32° (Error: -0.98°)
    - Bù góc: Xoay 18 steps (speed=-50)
    - Heading lần 2 (sau Spin): 15.26° (Error: -0.04°)
    - Mức độ cải thiện: 0.94°

## B. Khó khăn 


## C. Công việc tiếp theo 