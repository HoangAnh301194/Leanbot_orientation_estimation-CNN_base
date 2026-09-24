# Báo cáo công việc ngày 24/09/2026
## A. Công việc đã làm
- Khảo sát thêm Phase 4 với `spin-speed = 50`, tìm hệ số Kp ưu tiên các trường hợp Sai số trước bù lớn.
- Giảm bớt thời gian Pha 1, 2 để khảo sát nhanh bằng cách đặt Leanbot gần và hướng về target pixel.
- Báo cáo thêm thời gian thực hiện Phase 4.

### 1. Khảo sát thêm với Phase 4 với `spin-speed = 50`
- **Lệnh chạy:**
```bash
python .\leanbotCameraController.py --source 1 --show --spin-speed 50 --kp-spin <kp-spin> --ble 654321
```
- **Công thức ước lượng số bước:**
  $$\text{rotationSteps} = Kp \times |\text{error}|$$

---

### Bảng tổng hợp kết quả các lần thử nghiệm theo từng hệ số Kp

| Kp | STT | Tên file Log | Target Heading | Sai số trước bù ($\text{Err}_1$) | Lệnh Spin (`Speed / Steps`) | Sai số sau bù ($\text{Err}_2$) | Độ cải thiện ($\Delta\text{Err}$) | Ph4_1 | Spin | Ph4_2 | Lost Frames |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **5** | 1 | `log_roi_20260924_092309.csv` | **93.2 deg** | **+7.33 deg** | +50 / 37 steps | **-0.39 deg** | **+6.93 deg** | 7.75s | 0.88s | 8.50s | 0 |
|  | 2 | `log_roi_20260924_092505.csv` | **93.2 deg** | **+8.07 deg** | +50 / 40 steps | **+2.05 deg** | **+6.03 deg** | 7.73s | 0.92s | 8.56s | **2** (0.5%) |
|  | 3 | `log_roi_20260924_092614.csv` | **39.4 deg** | **-18.91 deg** | -50 / 95 steps | **-14.52 deg** | **+4.39 deg** | 7.74s | 2.06s | 8.49s | 0 |
|  | 4 | `log_roi_20260924_092652.csv` | **39.4 deg** | **-19.63 deg** | -50 / 98 steps | **-15.53 deg** | **+4.10 deg** | 7.68s | 2.12s | 8.55s | 0 |
| **10** | 1 | `log_roi_20260924_092933.csv` | **39.4 deg** | **-17.72 deg** | -50 / 177 steps | **-9.88 deg** | **+7.85 deg** | 7.74s | 3.68s | 8.51s | 0 |
|  | 2 | `log_roi_20260924_093040.csv` | **39.4 deg** | **-11.49 deg** | -50 / 115 steps | **+2.18 deg** | **+9.31 deg** | 7.74s | 2.46s | 8.56s | **3** (0.7%) |
|  | 3 | `log_roi_20260924_093200.csv` | **138.1 deg** | **+11.13 deg** | +50 / 111 steps | **+3.04 deg** | **+8.09 deg** | 7.74s | 2.33s | 8.58s | 0 |
|  | 4 | `log_roi_20260924_093305.csv` | **138.1 deg** | **+1.77 deg** | +50 / 18 steps | **+1.19 deg** | **+0.58 deg** | 7.68s | 0.48s | 8.50s | **4** (1.0%) |
| **15** | 1 | `log_roi_20260924_093629.csv` | **26.9 deg** | **-8.82 deg** | -50 / 132 steps | **+2.97 deg** | **+5.85 deg** | 7.74s | 2.81s | 8.49s | **20** (5.0%) |
|  | 2 | `log_roi_20260924_093738.csv` | **61.2 deg** | **-7.95 deg** | -50 / 119 steps | **+1.43 deg** | **+6.52 deg** | 7.74s | 2.53s | 8.56s | 0 |
|  | 3 | `log_roi_20260924_093816.csv` | **61.2 deg** | **-5.83 deg** | -50 / 87 steps | **+1.63 deg** | **+4.20 deg** | 7.68s | 1.87s | 8.56s | 0 |
|  | 4 | `log_roi_20260924_093937.csv` | **61.2 deg** | **-4.17 deg** | -50 / 62 steps | **+4.55 deg** | **-0.38 deg** | 7.70s | 1.41s | 8.51s | 0 |
|  | 5 | `log_roi_20260924_094113.csv` | **61.2 deg** | **-3.44 deg** | -50 / 52 steps | **+1.34 deg** | **+2.10 deg** | 7.68s | 1.17s | 8.56s | 0 |
| **20** | 1 | `log_roi_20260924_094215.csv` | **61.2 deg** | **+5.11 deg** | +50 / 102 steps | **-0.40 deg** | **+4.71 deg** | 7.63s | 2.17s | 8.43s | **1** (0.2%) |
|  | 2 | `log_roi_20260924_094250.csv` | **61.2 deg** | **-9.39 deg** | -50 / 188 steps | **+1.67 deg** | **+7.72 deg** | 7.74s | 3.90s | 8.50s | 0 |
|  | 3 | `log_roi_20260924_094349.csv` | **-15.1 deg** | **+3.50 deg** | +50 / 70 steps | **-2.55 deg** | **+0.94 deg** | 7.74s | 1.57s | 8.52s | 0 |
|  | 4 | `log_roi_20260924_094439.csv` | **-15.1 deg** | **-2.66 deg** | -50 / 53 steps | **-1.54 deg** | **+1.12 deg** | 7.68s | 1.24s | 8.54s | 0 |
|  | 5 | `log_roi_20260924_094539.csv` | **-92.6 deg** | **-1.83 deg** | -50 / 37 steps | **+1.02 deg** | **+0.80 deg** | 7.69s | 0.93s | 8.51s | 0 |
|  | 6 | `log_roi_20260924_094612.csv` | **-92.6 deg** | **-5.31 deg** | -50 / 106 steps | **-3.91 deg** | **+1.40 deg** | 7.75s | 2.25s | 8.51s | **5** (1.1%) |
|  | 7 | `log_roi_20260924_094650.csv` | **-92.6 deg** | **+1.83 deg** | +50 / 37 steps | **+0.54 deg** | **+1.29 deg** | 7.74s | 0.88s | 8.56s | 0 |
|  | 8 | `log_roi_20260924_094739.csv` | **16.2 deg** | **-11.52 deg** | -50 / 230 steps | **+0.28 deg** | **+11.24 deg** | 7.70s | 4.78s | 8.49s | 0 |
|  | 9 | `log_roi_20260924_094826.csv` | **16.2 deg** | **-8.17 deg** | -50 / 163 steps | **+1.96 deg** | **+6.20 deg** | 7.74s | 3.44s | 8.56s | 0 |
| **25** | 1 | `log_roi_20260924_095054.csv` | **16.2 deg** | **-8.75 deg** | -50 / 219 steps | **+2.78 deg** | **+5.97 deg** | 7.74s | 4.55s | 8.51s | 0 |
|  | 2 | `log_roi_20260924_095128.csv` | **16.2 deg** | **-0.48 deg** | -50 / 12 steps | **-1.71 deg** | **-1.23 deg** | 7.70s | 0.40s | 8.51s | 0 |
|  | 3 | `log_roi_20260924_095219.csv` | **155.5 deg** | **+2.71 deg** | +50 / 68 steps | **+1.92 deg** | **+0.79 deg** | 7.74s | 1.52s | 8.49s | 0 |
|  | 4 | `log_roi_20260924_095257.csv` | **155.5 deg** | **+7.41 deg** | +50 / 185 steps | **-8.43 deg** | **-1.03 deg** | 7.76s | 3.84s | 8.50s | 0 |
|  | 5 | `log_roi_20260924_095352.csv` | **-176.0 deg** | **+1.33 deg** | +50 / 33 steps | **+0.74 deg** | **+0.59 deg** | 7.74s | 0.86s | 8.55s | **2** (0.5%) |

---
### Nhận xét & Đánh giá tổng kết
1. **So sánh các mức hệ số $Kp_{\text{spin}}$:**
   - **$Kp = 5$:**  Khi góc lệch $\sim 19^\circ$, chỉ xuay $\sim 98$ steps, sai số còn $~ 15^\circ$ là tương đối lớn. 
   - **$Kp = 10$:** Cải thiện góc lệch tương đối (giảm từ $17.7^\circ$ xuống $9.8^\circ$, và từ $11.5^\circ$ xuống $2.2^\circ$), nhưng với các góc lệch $> 15^\circ$ thì vẫn còn thiếu 
   - **$Kp = 15$:** Bù góc rất tốt ở dải sai số trung bình ($5^\circ - 9^\circ$), tuy nhiên với góc lớn thì bù không đủ.
   - **$Kp = 20$:** Đạt hiệu quả tối ưu nhất, Các lần thử nghiệm đều giữ được sai số cuối cùng nằm dưới $3.9^\circ$ (đa số đều $< 1.9^\circ$).
   - **$Kp = 25$:** Bắt đầu có hiện tượng overshoot.
2. **Kết luận**
   - Cấu hình tối ưu nhất là:
     spin-speed = 50, Kp_spin = 20.0


### Các ví dụ lost tracking

- **Tổng kết:** Trong toàn bộ quá trình khảo sát thực nghiệm (27 lần chạy infrence , tổng cộng 11,092 frames), có **37 frames** bị lost tracking (tỷ lệ **0.33%**), trong đó có **20 / 27 lần chạy (74.1%)** không bị mất tracking (0 frame lost tracking ).
- Bảng tổng hợp hiện tại em để là 10 ảnh , vì có nhiều ảnh gần như là y hệt nhau ạ .
 
| Ảnh Dataset (`images/`) | Ảnh Check Label (`check_labels/`) |
| :---: | :---: |
| **Trường hợp 1 (Kp = 5)** — Frame ID: 380 (09:22:54, ROI)<br><img src="lost_tracking_dataset/session_20260924_092228_359688_ad1d17f7/images/lost_00000380_000003.png" alt="Dataset 380" width="380"> | **Check Label Preview** (BBox & Class Angle)<br><img src="lost_tracking_dataset/session_20260924_092228_359688_ad1d17f7/check_labels/lost_00000380_000003.png" alt="Check Label 380" width="380"> |
| **Trường hợp 2 (Kp = 5)** — Frame ID: 2708 (09:25:29, ROI)<br><img src="lost_tracking_dataset/session_20260924_092228_359688_ad1d17f7/images/lost_00002708_000006.png" alt="Dataset 2708" width="380"> | **Check Label Preview** (BBox & Class Angle)<br><img src="lost_tracking_dataset/session_20260924_092228_359688_ad1d17f7/check_labels/lost_00002708_000006.png" alt="Check Label 2708" width="380"> |
| **Trường hợp 3 (Kp = 10)** — Frame ID: 1389 (09:30:41, ROI)<br><img src="lost_tracking_dataset/session_20260924_092907_892011_3c03a54c/images/lost_00001389_000001.png" alt="Dataset 1389" width="380"> | **Check Label Preview** (BBox & Class Angle)<br><img src="lost_tracking_dataset/session_20260924_092907_892011_3c03a54c/check_labels/lost_00001389_000001.png" alt="Check Label 1389" width="380"> |
| **Trường hợp 4 (Kp = 10)** — Frame ID: 2364 (09:31:46, ROI)<br><img src="lost_tracking_dataset/session_20260924_092907_892011_3c03a54c/images/lost_00002364_000008.png" alt="Dataset 2364" width="380"> | **Check Label Preview** (BBox & Class Angle)<br><img src="lost_tracking_dataset/session_20260924_092907_892011_3c03a54c/check_labels/lost_00002364_000008.png" alt="Check Label 2364" width="380"> |
| **Trường hợp 5 (Kp = 15)** — Frame ID: 843 (09:36:34, ROI)<br><img src="lost_tracking_dataset/session_20260924_093537_748833_f3d4ec9b/images/lost_00000843_000001.png" alt="Dataset 843" width="380"> | **Check Label Preview** (BBox & Class Angle)<br><img src="lost_tracking_dataset/session_20260924_093537_748833_f3d4ec9b/check_labels/lost_00000843_000001.png" alt="Check Label 843" width="380"> |
| **Trường hợp 6 (Kp = 15)** — Frame ID: 847 (09:36:34, FULL)<br><img src="lost_tracking_dataset/session_20260924_093537_748833_f3d4ec9b/images/lost_00000847_000005.png" alt="Dataset 847" width="380"> | **Check Label Preview** (BBox & Class Angle)<br><img src="lost_tracking_dataset/session_20260924_093537_748833_f3d4ec9b/check_labels/lost_00000847_000005.png" alt="Check Label 847" width="380"> |
| **Trường hợp 7 (Kp = 20)** — Frame ID: 3798 (09:46:19, ROI)<br><img src="lost_tracking_dataset/session_20260924_094205_101462_379fb453/images/lost_00003798_000005.png" alt="Dataset 3798" width="380"> | **Check Label Preview** (BBox & Class Angle)<br><img src="lost_tracking_dataset/session_20260924_094205_101462_379fb453/check_labels/lost_00003798_000005.png" alt="Check Label 3798" width="380"> |
| **Trường hợp 8 (Kp = 20)** — Frame ID: 3801 (09:46:19, ROI)<br><img src="lost_tracking_dataset/session_20260924_094205_101462_379fb453/images/lost_00003801_000006.png" alt="Dataset 3801" width="380"> | **Check Label Preview** (BBox & Class Angle)<br><img src="lost_tracking_dataset/session_20260924_094205_101462_379fb453/check_labels/lost_00003801_000006.png" alt="Check Label 3801" width="380"> |
| **Trường hợp 9 (Kp = 25)** — Frame ID: 2979 (09:54:05, ROI)<br><img src="lost_tracking_dataset/session_20260924_095046_054892_b5bc4344/images/lost_00002979_000002.png" alt="Dataset 2979" width="380"> | **Check Label Preview** (BBox & Class Angle)<br><img src="lost_tracking_dataset/session_20260924_095046_054892_b5bc4344/check_labels/lost_00002979_000002.png" alt="Check Label 2979" width="380"> |
| **Trường hợp 10 (Kp = 25)** — Frame ID: 3111 (09:54:14, ROI)<br><img src="lost_tracking_dataset/session_20260924_095046_054892_b5bc4344/images/lost_00003111_000003.png" alt="Dataset 3111" width="380"> | **Check Label Preview** (BBox & Class Angle)<br><img src="lost_tracking_dataset/session_20260924_095046_054892_b5bc4344/check_labels/lost_00003111_000003.png" alt="Check Label 3111" width="380"> |

---

### Chi tiết các lần chạy thực nghiệm

#### 1.1 Kp = 5

- **Lần chạy 1 — `log_roi_20260924_092309.csv`:**
```
Target Heading          : 93.2 deg
Heading Error 1         : +7.33 deg (trước spinSteps())
Spin Applied            : 37 steps (Speed: 50)
Heading Error 2         : -0.39 deg (Sau khi spinSteps() & chạy run_fw_bw())
Error Improvement       : +6.93 deg
Thời gian Phase 4 lần 1 : 7.75s
Thời gian SpinSteps     : 0.88s
Thời gian Phase 4 lần 2 : 8.50s
Lost Tracking           : 0 frame (100% Tracking)
```
<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_092309_2d_trajectory.png" alt="Traj 1" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_092309_pid_diff_analysis.png" alt="Diff 1" width="800">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_092309_pid_analysis.png" alt="PID 1" width="800">

- **Lần chạy 2 — `log_roi_20260924_092505.csv`:**
```
Target Heading          : 93.2 deg
Heading Error 1         : +8.07 deg (trước spinSteps())
Spin Applied            : 40 steps (Speed: 50)
Heading Error 2         : +2.05 deg (Sau khi spinSteps() & chạy run_fw_bw())
Error Improvement       : +6.03 deg
Thời gian Phase 4 lần 1 : 7.73s
Thời gian SpinSteps     : 0.92s
Thời gian Phase 4 lần 2 : 8.56s
Lost Tracking           : 2 / 379 frames
```
<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_092505_2d_trajectory.png" alt="Traj 2" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_092505_pid_diff_analysis.png" alt="Diff 2" width="800">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_092505_pid_analysis.png" alt="PID 2" width="800">

- **Lần chạy 3 — `log_roi_20260924_092614.csv`:**
```
Target Heading          : 39.4 deg
Heading Error 1         : -18.91 deg (trước spinSteps())
Spin Applied            : 95 steps (Speed: -50)
Heading Error 2         : -14.52 deg (Sau khi spinSteps() & chạy run_fw_bw())
Error Improvement       : +4.39 deg
Thời gian Phase 4 lần 1 : 7.74s
Thời gian SpinSteps     : 2.06s
Thời gian Phase 4 lần 2 : 8.49s
Lost Tracking           : 0 frame (100% Tracking)
```
<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_092614_2d_trajectory.png" alt="Traj 3" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_092614_pid_diff_analysis.png" alt="Diff 3" width="800">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_092614_pid_analysis.png" alt="PID 3" width="800">

- **Lần chạy 4 — `log_roi_20260924_092652.csv`:**
```
Target Heading          : 39.4 deg
Heading Error 1         : -19.63 deg (trước spinSteps())
Spin Applied            : 98 steps (Speed: -50)
Heading Error 2         : -15.53 deg (Sau khi spinSteps() & chạy run_fw_bw())
Error Improvement       : +4.10 deg
Thời gian Phase 4 lần 1 : 7.68s
Thời gian SpinSteps     : 2.12s
Thời gian Phase 4 lần 2 : 8.55s
Lost Tracking           : 0 frame (100% Tracking)
```
<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_092652_2d_trajectory.png" alt="Traj 4" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_092652_pid_diff_analysis.png" alt="Diff 4" width="800">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_092652_pid_analysis.png" alt="PID 4" width="800">

---

#### 1.2 Kp = 10

- **Lần chạy 1 — `log_roi_20260924_092933.csv`:**
```
Target Heading          : 39.4 deg
Heading Error 1         : -17.72 deg (trước spinSteps())
Spin Applied            : 177 steps (Speed: -50)
Heading Error 2         : -9.88 deg (Sau khi spinSteps() & chạy run_fw_bw())
Error Improvement       : +7.85 deg
Thời gian Phase 4 lần 1 : 7.74s
Thời gian SpinSteps     : 3.68s
Thời gian Phase 4 lần 2 : 8.51s
Lost Tracking           : 0 frame (100% Tracking)
```
<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_092933_2d_trajectory.png" alt="Traj 1" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_092933_pid_diff_analysis.png" alt="Diff 1" width="800">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_092933_pid_analysis.png" alt="PID 1" width="800">

- **Lần chạy 2 — `log_roi_20260924_093040.csv`:**
```
Target Heading          : 39.4 deg
Heading Error 1         : -11.49 deg (trước spinSteps())
Spin Applied            : 115 steps (Speed: -50)
Heading Error 2         : +2.18 deg (Sau khi spinSteps() & chạy run_fw_bw())
Error Improvement       : +9.31 deg
Thời gian Phase 4 lần 1 : 7.74s
Thời gian SpinSteps     : 2.46s
Thời gian Phase 4 lần 2 : 8.56s
Lost Tracking           : 3 / 431 frames
```
<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_093040_2d_trajectory.png" alt="Traj 2" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_093040_pid_diff_analysis.png" alt="Diff 2" width="800">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_093040_pid_analysis.png" alt="PID 2" width="800">

- **Lần chạy 3 — `log_roi_20260924_093200.csv`:**
```
Target Heading          : 138.1 deg
Heading Error 1         : +11.13 deg (trước spinSteps())
Spin Applied            : 111 steps (Speed: 50)
Heading Error 2         : +3.04 deg (Sau khi spinSteps() & chạy run_fw_bw())
Error Improvement       : +8.09 deg
Thời gian Phase 4 lần 1 : 7.74s
Thời gian SpinSteps     : 2.33s
Thời gian Phase 4 lần 2 : 8.58s
Lost Tracking           : 0 frame (100% Tracking)
```
<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_093200_2d_trajectory.png" alt="Traj 3" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_093200_pid_diff_analysis.png" alt="Diff 3" width="800">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_093200_pid_analysis.png" alt="PID 3" width="800">

- **Lần chạy 4 — `log_roi_20260924_093305.csv`:**
```
Target Heading          : 138.1 deg
Heading Error 1         : +1.77 deg (trước spinSteps())
Spin Applied            : 18 steps (Speed: 50)
Heading Error 2         : +1.19 deg (Sau khi spinSteps() & chạy run_fw_bw())
Error Improvement       : +0.58 deg
Thời gian Phase 4 lần 1 : 7.68s
Thời gian SpinSteps     : 0.48s
Thời gian Phase 4 lần 2 : 8.50s
Lost Tracking           : 4 / 386 frames
```
<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_093305_2d_trajectory.png" alt="Traj 4" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_093305_pid_diff_analysis.png" alt="Diff 4" width="800">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_093305_pid_analysis.png" alt="PID 4" width="800">

---

#### 1.3 Kp = 15

- **Lần chạy 1 — `log_roi_20260924_093629.csv`:**
```
Target Heading          : 26.9 deg
Heading Error 1         : -8.82 deg (trước spinSteps())
Spin Applied            : 132 steps (Speed: -50)
Heading Error 2         : +2.97 deg (Sau khi spinSteps() & chạy run_fw_bw())
Error Improvement       : +5.85 deg
Thời gian Phase 4 lần 1 : 7.74s
Thời gian SpinSteps     : 2.81s
Thời gian Phase 4 lần 2 : 8.49s
Lost Tracking           : 20 / 398 frames
```
<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_093629_2d_trajectory.png" alt="Traj 1" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_093629_pid_diff_analysis.png" alt="Diff 1" width="800">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_093629_pid_analysis.png" alt="PID 1" width="800">

- **Lần chạy 2 — `log_roi_20260924_093738.csv`:**
```
Target Heading          : 61.2 deg
Heading Error 1         : -7.95 deg (trước spinSteps())
Spin Applied            : 119 steps (Speed: -50)
Heading Error 2         : +1.43 deg (Sau khi spinSteps() & chạy run_fw_bw())
Error Improvement       : +6.52 deg
Thời gian Phase 4 lần 1 : 7.74s
Thời gian SpinSteps     : 2.53s
Thời gian Phase 4 lần 2 : 8.56s
Lost Tracking           : 0 frame (100% Tracking)
```
<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_093738_2d_trajectory.png" alt="Traj 2" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_093738_pid_diff_analysis.png" alt="Diff 2" width="800">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_093738_pid_analysis.png" alt="PID 2" width="800">

- **Lần chạy 3 — `log_roi_20260924_093816.csv`:**
```
Target Heading          : 61.2 deg
Heading Error 1         : -5.83 deg (trước spinSteps())
Spin Applied            : 87 steps (Speed: -50)
Heading Error 2         : +1.63 deg (Sau khi spinSteps() & chạy run_fw_bw())
Error Improvement       : +4.20 deg
Thời gian Phase 4 lần 1 : 7.68s
Thời gian SpinSteps     : 1.87s
Thời gian Phase 4 lần 2 : 8.56s
Lost Tracking           : 0 frame (100% Tracking)
```
<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_093816_2d_trajectory.png" alt="Traj 3" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_093816_pid_diff_analysis.png" alt="Diff 3" width="800">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_093816_pid_analysis.png" alt="PID 3" width="800">

- **Lần chạy 4 — `log_roi_20260924_093937.csv`:**
```
Target Heading          : 61.2 deg
Heading Error 1         : -4.17 deg (trước spinSteps())
Spin Applied            : 62 steps (Speed: -50)
Heading Error 2         : +4.55 deg (Sau khi spinSteps() & chạy run_fw_bw())
Error Improvement       : -0.38 deg
Thời gian Phase 4 lần 1 : 7.70s
Thời gian SpinSteps     : 1.41s
Thời gian Phase 4 lần 2 : 8.51s
Lost Tracking           : 0 frame (100% Tracking)
```
<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_093937_2d_trajectory.png" alt="Traj 4" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_093937_pid_diff_analysis.png" alt="Diff 4" width="800">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_093937_pid_analysis.png" alt="PID 4" width="800">

- **Lần chạy 5 — `log_roi_20260924_094113.csv`:**
```
Target Heading          : 61.2 deg
Heading Error 1         : -3.44 deg (trước spinSteps())
Spin Applied            : 52 steps (Speed: -50)
Heading Error 2         : +1.34 deg (Sau khi spinSteps() & chạy run_fw_bw())
Error Improvement       : +2.10 deg
Thời gian Phase 4 lần 1 : 7.68s
Thời gian SpinSteps     : 1.17s
Thời gian Phase 4 lần 2 : 8.56s
Lost Tracking           : 0 frame (100% Tracking)
```
<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_094113_2d_trajectory.png" alt="Traj 5" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_094113_pid_diff_analysis.png" alt="Diff 5" width="800">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_094113_pid_analysis.png" alt="PID 5" width="800">

---

#### 1.4 Kp = 20

- **Lần chạy 1 — `log_roi_20260924_094215.csv`:**
```
Target Heading          : 61.2 deg
Heading Error 1         : +5.11 deg (trước spinSteps())
Spin Applied            : 102 steps (Speed: 50)
Heading Error 2         : -0.40 deg (Sau khi spinSteps() & chạy run_fw_bw())
Error Improvement       : +4.71 deg
Thời gian Phase 4 lần 1 : 7.63s
Thời gian SpinSteps     : 2.17s
Thời gian Phase 4 lần 2 : 8.43s
Lost Tracking           : 1 / 431 frames
```
<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_094215_2d_trajectory.png" alt="Traj 1" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_094215_pid_diff_analysis.png" alt="Diff 1" width="800">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_094215_pid_analysis.png" alt="PID 1" width="800">

- **Lần chạy 2 — `log_roi_20260924_094250.csv`:**
```
Target Heading          : 61.2 deg
Heading Error 1         : -9.39 deg (trước spinSteps())
Spin Applied            : 188 steps (Speed: -50)
Heading Error 2         : +1.67 deg (Sau khi spinSteps() & chạy run_fw_bw())
Error Improvement       : +7.72 deg
Thời gian Phase 4 lần 1 : 7.74s
Thời gian SpinSteps     : 3.90s
Thời gian Phase 4 lần 2 : 8.50s
Lost Tracking           : 0 frame (100% Tracking)
```
<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_094250_2d_trajectory.png" alt="Traj 2" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_094250_pid_diff_analysis.png" alt="Diff 2" width="800">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_094250_pid_analysis.png" alt="PID 2" width="800">

- **Lần chạy 3 — `log_roi_20260924_094349.csv`:**
```
Target Heading          : -15.1 deg
Heading Error 1         : +3.50 deg (trước spinSteps())
Spin Applied            : 70 steps (Speed: 50)
Heading Error 2         : -2.55 deg (Sau khi spinSteps() & chạy run_fw_bw())
Error Improvement       : +0.94 deg
Thời gian Phase 4 lần 1 : 7.74s
Thời gian SpinSteps     : 1.57s
Thời gian Phase 4 lần 2 : 8.52s
Lost Tracking           : 0 frame (100% Tracking)
```
<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_094349_2d_trajectory.png" alt="Traj 3" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_094349_pid_diff_analysis.png" alt="Diff 3" width="800">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_094349_pid_analysis.png" alt="PID 3" width="800">

- **Lần chạy 4 — `log_roi_20260924_094439.csv`:**
```
Target Heading          : -15.1 deg
Heading Error 1         : -2.66 deg (trước spinSteps())
Spin Applied            : 53 steps (Speed: -50)
Heading Error 2         : -1.54 deg (Sau khi spinSteps() & chạy run_fw_bw())
Error Improvement       : +1.12 deg
Thời gian Phase 4 lần 1 : 7.68s
Thời gian SpinSteps     : 1.24s
Thời gian Phase 4 lần 2 : 8.54s
Lost Tracking           : 0 frame (100% Tracking)
```
<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_094439_2d_trajectory.png" alt="Traj 4" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_094439_pid_diff_analysis.png" alt="Diff 4" width="800">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_094439_pid_analysis.png" alt="PID 4" width="800">

- **Lần chạy 5 — `log_roi_20260924_094539.csv`:**
```
Target Heading          : -92.6 deg
Heading Error 1         : -1.83 deg (trước spinSteps())
Spin Applied            : 37 steps (Speed: -50)
Heading Error 2         : +1.02 deg (Sau khi spinSteps() & chạy run_fw_bw())
Error Improvement       : +0.80 deg
Thời gian Phase 4 lần 1 : 7.69s
Thời gian SpinSteps     : 0.93s
Thời gian Phase 4 lần 2 : 8.51s
Lost Tracking           : 0 frame (100% Tracking)
```
<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_094539_2d_trajectory.png" alt="Traj 5" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_094539_pid_diff_analysis.png" alt="Diff 5" width="800">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_094539_pid_analysis.png" alt="PID 5" width="800">

- **Lần chạy 6 — `log_roi_20260924_094612.csv`:**
```
Target Heading          : -92.6 deg
Heading Error 1         : -5.31 deg (trước spinSteps())
Spin Applied            : 106 steps (Speed: -50)
Heading Error 2         : -3.91 deg (Sau khi spinSteps() & chạy run_fw_bw())
Error Improvement       : +1.40 deg
Thời gian Phase 4 lần 1 : 7.75s
Thời gian SpinSteps     : 2.25s
Thời gian Phase 4 lần 2 : 8.51s
Lost Tracking           : 5 / 438 frames
```
<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_094612_2d_trajectory.png" alt="Traj 6" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_094612_pid_diff_analysis.png" alt="Diff 6" width="800">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_094612_pid_analysis.png" alt="PID 6" width="800">

- **Lần chạy 7 — `log_roi_20260924_094650.csv`:**
```
Target Heading          : -92.6 deg
Heading Error 1         : +1.83 deg (trước spinSteps())
Spin Applied            : 37 steps (Speed: 50)
Heading Error 2         : +0.54 deg (Sau khi spinSteps() & chạy run_fw_bw())
Error Improvement       : +1.29 deg
Thời gian Phase 4 lần 1 : 7.74s
Thời gian SpinSteps     : 0.88s
Thời gian Phase 4 lần 2 : 8.56s
Lost Tracking           : 0 frame (100% Tracking)
```
<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_094650_2d_trajectory.png" alt="Traj 7" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_094650_pid_diff_analysis.png" alt="Diff 7" width="800">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_094650_pid_analysis.png" alt="PID 7" width="800">

- **Lần chạy 8 — `log_roi_20260924_094739.csv`:**
```
Target Heading          : 16.2 deg
Heading Error 1         : -11.52 deg (trước spinSteps())
Spin Applied            : 230 steps (Speed: -50)
Heading Error 2         : +0.28 deg (Sau khi spinSteps() & chạy run_fw_bw())
Error Improvement       : +11.24 deg
Thời gian Phase 4 lần 1 : 7.70s
Thời gian SpinSteps     : 4.78s
Thời gian Phase 4 lần 2 : 8.49s
Lost Tracking           : 0 frame (100% Tracking)
```
<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_094739_2d_trajectory.png" alt="Traj 8" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_094739_pid_diff_analysis.png" alt="Diff 8" width="800">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_094739_pid_analysis.png" alt="PID 8" width="800">

- **Lần chạy 9 — `log_roi_20260924_094826.csv`:**
```
Target Heading          : 16.2 deg
Heading Error 1         : -8.17 deg (trước spinSteps())
Spin Applied            : 163 steps (Speed: -50)
Heading Error 2         : +1.96 deg (Sau khi spinSteps() & chạy run_fw_bw())
Error Improvement       : +6.20 deg
Thời gian Phase 4 lần 1 : 7.74s
Thời gian SpinSteps     : 3.44s
Thời gian Phase 4 lần 2 : 8.56s
Lost Tracking           : 0 frame (100% Tracking)
```
<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_094826_2d_trajectory.png" alt="Traj 9" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_094826_pid_diff_analysis.png" alt="Diff 9" width="800">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_094826_pid_analysis.png" alt="PID 9" width="800">

---

#### 1.5 Kp = 25

- **Lần chạy 1 — `log_roi_20260924_095054.csv`:**
```
Target Heading          : 16.2 deg
Heading Error 1         : -8.75 deg (trước spinSteps())
Spin Applied            : 219 steps (Speed: -50)
Heading Error 2         : +2.78 deg (Sau khi spinSteps() & chạy run_fw_bw())
Error Improvement       : +5.97 deg
Thời gian Phase 4 lần 1 : 7.74s
Thời gian SpinSteps     : 4.55s
Thời gian Phase 4 lần 2 : 8.51s
Lost Tracking           : 0 frame (100% Tracking)
```
<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_095054_2d_trajectory.png" alt="Traj 1" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_095054_pid_diff_analysis.png" alt="Diff 1" width="800">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_095054_pid_analysis.png" alt="PID 1" width="800">

- **Lần chạy 2 — `log_roi_20260924_095128.csv`:**
```
Target Heading          : 16.2 deg
Heading Error 1         : -0.48 deg (trước spinSteps())
Spin Applied            : 12 steps (Speed: -50)
Heading Error 2         : -1.71 deg (Sau khi spinSteps() & chạy run_fw_bw())
Error Improvement       : -1.23 deg
Thời gian Phase 4 lần 1 : 7.70s
Thời gian SpinSteps     : 0.40s
Thời gian Phase 4 lần 2 : 8.51s
Lost Tracking           : 0 frame (100% Tracking)
```
<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_095128_2d_trajectory.png" alt="Traj 2" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_095128_pid_diff_analysis.png" alt="Diff 2" width="800">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_095128_pid_analysis.png" alt="PID 2" width="800">

- **Lần chạy 3 — `log_roi_20260924_095219.csv`:**
```
Target Heading          : 155.5 deg
Heading Error 1         : +2.71 deg (trước spinSteps())
Spin Applied            : 68 steps (Speed: 50)
Heading Error 2         : +1.92 deg (Sau khi spinSteps() & chạy run_fw_bw())
Error Improvement       : +0.79 deg
Thời gian Phase 4 lần 1 : 7.74s
Thời gian SpinSteps     : 1.52s
Thời gian Phase 4 lần 2 : 8.49s
Lost Tracking           : 0 frame (100% Tracking)
```
<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_095219_2d_trajectory.png" alt="Traj 3" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_095219_pid_diff_analysis.png" alt="Diff 3" width="800">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_095219_pid_analysis.png" alt="PID 3" width="800">

- **Lần chạy 4 — `log_roi_20260924_095257.csv`:**
```
Target Heading          : 155.5 deg
Heading Error 1         : +7.41 deg (trước spinSteps())
Spin Applied            : 185 steps (Speed: 50)
Heading Error 2         : -8.43 deg (Sau khi spinSteps() & chạy run_fw_bw())
Error Improvement       : -1.03 deg
Thời gian Phase 4 lần 1 : 7.76s
Thời gian SpinSteps     : 3.84s
Thời gian Phase 4 lần 2 : 8.50s
Lost Tracking           : 0 frame (100% Tracking)
```
<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_095257_2d_trajectory.png" alt="Traj 4" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_095257_pid_diff_analysis.png" alt="Diff 4" width="800">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_095257_pid_analysis.png" alt="PID 4" width="800">

- **Lần chạy 5 — `log_roi_20260924_095352.csv`:**
```
Target Heading          : -176.0 deg
Heading Error 1         : +1.33 deg (trước spinSteps())
Spin Applied            : 33 steps (Speed: 50)
Heading Error 2         : +0.74 deg (Sau khi spinSteps() & chạy run_fw_bw())
Error Improvement       : +0.59 deg
Thời gian Phase 4 lần 1 : 7.74s
Thời gian SpinSteps     : 0.86s
Thời gian Phase 4 lần 2 : 8.55s
Lost Tracking           : 2 / 410 frames
```
<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_095352_2d_trajectory.png" alt="Traj 5" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_095352_pid_diff_analysis.png" alt="Diff 5" width="800">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260924_095352_pid_analysis.png" alt="PID 5" width="800">

---


## B. Khó khăn
- Không
## C. Công việc tiếp theo.
- Em xin phép nhận hướng đi tiếp theo từ Thầy ạ.
