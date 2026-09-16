# Báo cáo công việc ngày 16/09/2026

## A. Công việc đã làm
- Triển khai thêm Phase 3 và Phase 4 vào `PID_controller.py` và `leanbotCameraController.py`
- Bổ sung code vẽ đồ thị để phân tích quỹ đạo và đánh giá sai số heading Phase 4

---

### 1. Triển khai thêm Phase 3 và Phase 4

#### 1.1 Phase 3 – Căn chỉnh góc hướng cuối cùng (`PHASE_3_FINAL_ALIGNING`)
Sau khi Leanbot đã đến đích (Phase 2 hoàn thành), Phase 3 thực hiện xoay tại chỗ để căn chỉnh đúng góc hướng mong muốn `target_heading` — là tư thế dừng cuối cùng.

- **Code bổ sung:** [`PID_controller.py`](LeanbotTinyRC/PID_controller.py)
  ```python
  # Phase 3: spin in place, reuse Phase 1 PID gains (Kp_angle, Ki_angle, Kd_angle)
  if self.phase == self.PHASE_FINAL_ALIGNING:
      final_angle_error = wrap_to_180(current_angle - target_h)
      if abs(final_angle_error) <= self.heading_tolerance3:
          if self._within_tolerance_since is None:
              self._within_tolerance_since = current_time
          elapsed_ms = (current_time - self._within_tolerance_since) * 1000.0
          if elapsed_ms >= self.settle_time_ms:
              # Chuyển sang Phase 4 (nếu bật) hoặc COMPLETED
              ...
      else:
          self._within_tolerance_since = None  
      v_lr   = 0.0  
      v_diff = Kp_angle * err + Ki_angle * integral + Kd_angle * d_err
      ...
  ```

- **Cấu hình PID sử dụng:** Tái sử dụng bộ PID góc của Phase 1 (`Kp_angle`, `Ki_angle`, `Kd_angle`) — cùng mục tiêu căn góc, chỉ khác điểm tham chiếu (Phase 1: căn về hướng tới đích, Phase 3: căn về `target_heading` cố định).
- **Các argument đầu vào:**

 | Argument | Kiểu | Mặc định | Mô tả |
 |---|---|---|---|
 | `--target-heading` | `float` | `None` | **Target heading** |
 | `--heading-tol3` | `float` | `5.0` | Dải sai số góc |
 | `--settle-time-ms` | `float` | `200.0` | Thời gian giữ ổn định tối thiểu (ms) trước khi complete |
 | `--kp-angle` | `float` | `30.0` | Kp Phase 1 |
 | `--kd-angle` | `float` | `0.0` | Kd Phase 1 |



---


#### 1.2 Phase 4 – Tiến/Lùi thẳng (`PHASE_4_FORWARD` / `PHASE_4_BACKWARD`)
Ngay sau khi Phase 3 ổn định xong, Leanbot thực hiện đi **tiến thẳng** trong `fwd_bwd_time_s` giây, sau đó **lùi thẳng** trong `fwd_bwd_time_s` giây cùng vận tốc cố định `fwd_bwd_speed`. Dữ liệu quỹ đạo tiến/lùi này được ghi log và dùng để **fit đa thức bậc 1** tính ra heading thực tế, sau đó so sánh với `target_heading` đã truyền vào ở Phase 3.

- **Code bổ sung:** [`PID_controller.py`](LeanbotTinyRC/PID_controller.py)

  ```python
  # Phase 4A: FORWARD – đi tiến fwd_bwd_time_s giây
  if self.phase == self.PHASE_FORWARD:
      elapsed_fwd = current_time - self._fwd_start_time
      if elapsed_fwd >= self.fwd_bwd_time_s:
          self.phase = self.PHASE_BACKWARD
          self._bwd_start_time = current_time
          ...
      speed = self.fwd_bwd_speed  # 2 bánh cùng vận tốc, đi thẳng

  # Phase 4B: BACKWARD – đi lùi fwd_bwd_time_s giây
  if self.phase == self.PHASE_BACKWARD:
      elapsed_bwd = current_time - self._bwd_start_time
      if elapsed_bwd >= self.fwd_bwd_time_s:
          self.phase = self.PHASE_COMPLETED
          ...
      speed = -self.fwd_bwd_speed
  ```

- **Cấu hình PID sử dụng:** Phase 4 — tốc độ 2 bánh bằng nhau và cố định (`fwd_bwd_speed`), điều hướng là đi thẳng thuần túy.

- **Các argument đầu vào:**

 | Argument | Kiểu | Mặc định | Mô tả |
 |---|---|---|---|
 | `--fwd-bwd-time` | `float` | `10.0` | Thời gian tiến (và lùi) tính bằng giây |
 | `--fwd-bwd-speed` | `int` | `1000` | Vận tốc bánh xe trong Phase 4 (đơn vị `runLR`) |

- **Lệnh chạy thực tế (PowerShell):**


  ```powershell
  python leanbotCameraController.py `
    --kp-angle 30 `
    --target-heading 135 `
    --heading-tol3 5 `
    --settle-time-ms 500 `
    --fwd-bwd-time 10 `
    --fwd-bwd-speed 1000 `
    --full-model ..\models\yolo11n_latest_version\best_fp16_no_nms_imgsz640_openvino_model `
    --tracking-model ..\models\yolo11n_latest_version\best_fp16_no_nms_imgsz160_openvino_model `
    --show --source 1 `
    --ble 343944
  ```
---

### 2. Thực nghiệm thực tế và đánh giá

Cấu hình chạy thực nghiệm chung:

| Tham số | Giá trị |
|---|---|
| `--kp-angle` | `30.0` |
| `--heading-tol3` | `5.0°` |
| `--settle-time-ms` | `500 ms` |
| `--fwd-bwd-time` | `10 s` |
| `--fwd-bwd-speed` | `1000 runLR` |
| Model | `yolo11n_latest_version` |
| Leanbot BLE | `343944` |

#### 2.1 Tổng hợp kết quả

| # | Log | `--target-heading` | Thời gian | Ph1 | Ph2 | Ph3 | Ph4 FWD | Ph4 BWD | Heading Fit (θ_traj) | Sai số \|Δθ\| | Lost Tracking |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `152558` | **90°** | 39.8s | 33f | 170f | 94f | 144f | 145f | 91.9° | **1.9°** | 11f |
| 2 | `152648` | **90°** | 32.7s | 36f | 116f | 36f | 147f | 149f | 90.1° | **0.1°** | 8f |
| 3 | `152824` | **135°** | 57.5s | 36f | 133f | **305f** | 149f | 151f | 136.6° | **1.6°** | 57f |
| 4 | `153439` | **0°** | 38.1s | 40f | 175f | 57f | 149f | 151f | 1.5° | **1.5°** | 1f |
| 5 | `153523` | **0°** | 34.4s | 40f | 145f | 33f | 151f | 149f | 2.4° | **2.4°** | 0f |
| 6 | `153706` | **-90°** | 35.0s | 36f | 163f | 25f | 151f | 144f | -88.1° | **1.9°** | 4f |

> **Nhận xét:**
> - Tất cả 6 lần chạy hoàn chỉnh đều có sai số heading fit **dưới 2.4°**
> - Lần 3 (`152824`, target 135°): Phase 3 lost tracking nhiều nhất ( em đã thử chạy đi chạy lại nhiều lần ở các vị trí khác nhau trên sa bàn nhưng khi tới căn chỉnh góc 135 độ ở phase 3 thì lost tracking rất nhiều ạ)
---


#### 2.2 Kết quả từng lần chạy

**Lần 1 — `log_roi_20260916_152558` | `--target-heading 90°` | θ_traj = 91.9° | |Δθ| = 1.9° **

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260916_152558_pid_analysis.png" alt="PID 1" width="800">

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260916_152558_2d_trajectory.png" alt="Traj 1" width="600">

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260916_152558_phase4_fwd_bwd_heading.png" alt="Ph4 Heading 1" width="600">

---

**Lần 2 — `log_roi_20260916_152648` | `--target-heading 90°` | θ_traj = 90.1° | |Δθ| = 0.1° **

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260916_152648_pid_analysis.png" alt="PID 2" width="800">

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260916_152648_2d_trajectory.png" alt="Traj 2" width="600">

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260916_152648_phase4_fwd_bwd_heading.png" alt="Ph4 Heading 2" width="600">

---

**Lần 3 — `log_roi_20260916_152824` | `--target-heading 135°` | θ_traj = 136.6° | |Δθ| = 1.6° |  Phase 3 lâu (305f), lost tracking nhiều (57f)**

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260916_152824_pid_analysis.png" alt="PID 3" width="800">

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260916_152824_2d_trajectory.png" alt="Traj 3" width="600">

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260916_152824_phase4_fwd_bwd_heading.png" alt="Ph4 Heading 3" width="600">

---

**Lần 4 — `log_roi_20260916_153439` | `--target-heading 0°` | θ_traj = 1.5° | |Δθ| = 1.5° **

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260916_153439_pid_analysis.png" alt="PID 4" width="800">

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260916_153439_2d_trajectory.png" alt="Traj 4" width="600">

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260916_153439_phase4_fwd_bwd_heading.png" alt="Ph4 Heading 4" width="600">

---

**Lần 5 — `log_roi_20260916_153523` | `--target-heading 0°` | θ_traj = 2.4° | |Δθ| = 2.4° **

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260916_153523_pid_analysis.png" alt="PID 5" width="800">

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260916_153523_2d_trajectory.png" alt="Traj 5" width="600">

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260916_153523_phase4_fwd_bwd_heading.png" alt="Ph4 Heading 5" width="600">

---

**Lần 6 — `log_roi_20260916_153706` | `--target-heading -90°` | θ_traj = -88.1° | |Δθ| = 1.9° **

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260916_153706_pid_analysis.png" alt="PID 6" width="800">

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260916_153706_2d_trajectory.png" alt="Traj 6" width="600">

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260916_153706_phase4_fwd_bwd_heading.png" alt="Ph4 Heading 6" width="600">

---

## B. Khó khăn

- Em nghĩ việc dùng fit quỹ đạo trên ảnh để suy ra heading chưa hoàn toàn chính xác để đánh giá, vì camera đặt góc chéo gây ra biến dạng phối cảnh. Leanbot đi thẳng trên thực tế nhưng quỹ đạo trên ảnh sẽ bị xiên nhẹ — đặc biệt khi di chuyển theo chiều dọc ($y(t) \neq 0$), do vùng xa camera hẹp hơn vùng gần camera. Em xin phép xin thêm ý kiến từ Thầy ạ.

<img src="LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_1291_20260916_153523_orig.png" alt="Phối cảnh camera" width="600">

- **Thông số PID Phase 1 không phù hợp cho Phase 3:** Khi tái sử dụng bộ PID góc của Phase 1 cho Phase 3, em thấy Leanbot thường bị lắc qua lại và không ổn định trong nhiều trường hợp test thực tế. 
- **Hiện tượng mất dấu (Lost Tracking) diễn ra thường xuyên:** Trong quá trình inference thời gian thực, hiện tượng lost tracking xảy ra tương đối dày và thường xuyên (thể hiện rõ qua các khoảng ngắt quãng / mất mẫu trên các đồ thị vận tốc và góc)
- Một số trường hợp bị lost tracking được hệ thống tự động ghi lại như sau: 

| Trường hợp mất dấu (Lost Tracking) | Trường hợp mất dấu (Lost Tracking) |
| :---: | :---: |
| <img src="LeanbotTinyRC/benchmark_logs/lost_tracking_captures/lost_frame_1598_15-26-22-825_ROI_roi.png" alt="Lost Frame 1598" width="360"><br>Frame 1598 (15:26:22) | <img src="LeanbotTinyRC/benchmark_logs/lost_tracking_captures/lost_frame_2056_15-26-53-369_ROI_roi.png" alt="Lost Frame 2056" width="360"><br>Frame 2056 (15:26:53) |
| <img src="LeanbotTinyRC/benchmark_logs/lost_tracking_captures/lost_frame_2191_15-27-02-345_ROI_roi.png" alt="Lost Frame 2191" width="360"><br>Frame 2191 (15:27:02) | <img src="LeanbotTinyRC/benchmark_logs/lost_tracking_captures/lost_frame_2411_15-27-17-031_ROI_roi.png" alt="Lost Frame 2411" width="360"><br>Frame 2411 (15:27:17) |
| <img src="LeanbotTinyRC/benchmark_logs/lost_tracking_captures/lost_frame_386_15-28-38-675_ROI_roi.png" alt="Lost Frame 386" width="360"><br>Frame 386 (15:28:38) | <img src="LeanbotTinyRC/benchmark_logs/lost_tracking_captures/lost_frame_653_15-28-57-964_ROI_roi.png" alt="Lost Frame 653" width="360"><br>Frame 653 (15:28:57) |
| <img src="LeanbotTinyRC/benchmark_logs/lost_tracking_captures/lost_frame_1358_15-29-45-793_ROI_roi.png" alt="Lost Frame 1358" width="360"><br>Frame 1358 (15:29:45) | <img src="LeanbotTinyRC/benchmark_logs/lost_tracking_captures/lost_frame_1737_15-30-11-281_ROI_roi.png" alt="Lost Frame 1737" width="360"><br>Frame 1737 (15:30:11) |
| <img src="LeanbotTinyRC/benchmark_logs/lost_tracking_captures/lost_frame_991_15-35-03-612_ROI_roi.png" alt="Lost Frame 991" width="360"><br>Frame 991 (15:35:03) | <img src="LeanbotTinyRC/benchmark_logs/lost_tracking_captures/lost_frame_473_15-37-32-651_ROI_roi.png" alt="Lost Frame 473" width="360"><br>Frame 473 (15:37:32) |

> Hầu hết các trường hợp lost tracking đề bình thường, không có vật thể nhiễu , chưa rõ nguyên nhân mất tracking Leanbot. 

- Khi em chạy test lại với cùng cấu hình (góc 135 độ) với **model cũ (`models/YOLO11n_versions/FP16_NO_NMS`)**  thì không có hiện tượng lost tracking ạ .

  <img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260916_162344_pid_analysis.png" alt="PID Model Cũ 135deg" width="800">

  <img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260916_162344_2d_trajectory.png" alt="Traj Model Cũ 135deg" width="600">

  <img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260916_162344_phase4_fwd_bwd_heading.png" alt="Ph4 Heading Model Cũ 135deg" width="600">

## C. Công việc tiếp theo
- Em xin phép nhận hướng đi tiếp theo từ Thầy ạ.
