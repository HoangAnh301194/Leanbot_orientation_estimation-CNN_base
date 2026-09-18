# Báo cáo công việc ngày 18/09/2026
## A. Công việc đã làm 
- Đã nhận thêm code của anh Thế Anh : bổ sung lệnh đi tiến lùi một lần duy nhất , đợt Leanbot về sát target, không gửi spam liên tục lệnh runLR 

- Chia bộ PID cho phase 3 riêng và tinh chỉnh lại PID cho phase 1 và 3 : phase 1 ưu tiên tốc độ , phase 3 ưu tiên độ chính xác 

- Vẽ thêm đồ thị Kp*error và Kd*d(error) để đánh giá thêm, điều chỉnh lại Kp, Kd ở phase 2 để giảm đánh võng 

- Khảo sát thêm các trường hợp góc ngẫu nhiên ( hiển thị targer heading segment và ko hiển thị các điểm trajectory bị lost tracking )  



### 1. Tiếp nhận code bổ sung lệnh runFwBw()
- **Code bổ sung lệnh gửi BLE :** 
```python
async def run_fw_bw(
    controller,
    speed: int,
    duration: int,
) -> None:

    command = f"rfb/{speed}/{duration}\n"

    log("TX", command.rstrip())

    await controller.send(
        command,
        response=False,
    )
```
- **Code Leanbot nhận chuỗi string và di chuyển :** 
```cpp
// Xử lý command rfb/2000/700
void runFwBw(String args) {

  int pos = args.indexOf('/');

  if (pos < 0)
    return;

  int speed  = args.substring(0, pos).toInt();
  int durationMs = args.substring(pos + 1).toInt();

  reportCommand("runFwBw", args);

  LbMotion.stopAndWait();
  LbMotion.runLR(+speed, +speed);
  LbDelay(durationMs);
  LbMotion.stopAndWait();
  LbMotion.runLR(-speed, -speed);
  LbDelay(durationMs);
  LbMotion.stopAndWait();
}

```
- **Tích hợp vào (`leanbotCameraController.py`):**
  - **Thay đổi trong code :**
    - Bổ sung hàm `send_run_fw_bw(speed, duration_ms)` trong class `BLEMotorWorker`.
    - Python gửi `rfb/<speed>/<durationMs>\n`. Leanbot sẽ dừng hoàn toàn trước khi nhận lệnh, sau khi nhận lệnh sẽ tiến thẳng $T$ ms, dừng, lùi thẳng $T$ ms, 
  - **Các tham số CLI bổ sung:**
    | Tham số CLI | Mặc định | Ý nghĩa |
    | :--- | :---: | :--- |
    | `--set-target-time` | `3.0` | Thời gian chạy cho mỗi chiều tiến/lùi (giây). Tổng thời gian thu quỹ đạo là $2 \times 3.0 = 6.0\text{ s}$. |
    | `--set-target-speed` | `2000` | Tốc độ động cơ khi tiến lùi set target |

> Leanbot nhận lệnh đi thẳng, lùi 1 lần , không spam lệnh BLE runLR 
> Trên thực nghiệm Leanbot lùi đúng vị trí target, khôgn bị sai lệnh . 

### 2. Triển khai bộ PID riêng cho Phase 3 và giữ lại hệ số Phase 1 ban đầu
  - Tách độc lập hoàn toàn bộ điều khiển góc của Phase 3 (`kp_angle3`, `kd_angle3`, `ki_angle3`), không dùng chung với Phase 1 (`kp_angle`, `kd_angle`).
  - **Phase 1 (Ưu tiên tốc độ nhanh)**: Giữ lại hệ số $K_p = 30.0$ như cũ. Với dung sai rộng ($\pm 35^\circ$).
  - **Phase 3 (Ưu tiên độ chính xác & xác lập ổn định)**:
    - Trong quá trình test em chọn hệ số P và D như sau : 
      - $K_p$-angle3 = `20.0` 
      - $K_d$-angle3 = `0.01`


### 3. Khảo sát thêm các trường hợp góc ngẫu nhiên 
- Trong quá trình thử nghiệm để Phase 2 giảm đánh võng em lựa chọn cấu hình sau : 
  - `kp-angle2 0.01`
  - `kd-angle2 0.04`

- **Toàn bộ cấu hình và lệnh chạy cuối cùng như sau :**
```powershell
python leanbotCameraController.py `
  --show `
  --source 1 `
  --ble 343944 `
  --target-config target_config.json `
  --kp-angle 30.0 --kd-angle 0.0 `
  --kp-angle2 0.01 --kd-angle2 0.04 `
  --kp-angle3 20.0 --kd-angle3 0.01 `
  --heading-tol 20.0 `
  --heading-tol3 5.0 `
  --settle-time-ms 500.0 `
  --fwd-bwd-time 3.0 --fwd-bwd-speed 2000
```
  
- Tiến hành thử nghiệm với các góc ngẫu nhiên, không theo quy luật như 45°, 15°, 30°...
- Góc target heading và vị trí target pixel được lấy bằng cơ chế set target bằng phím `T` trước đó đã tạo.
- Bổ sung đồ thị `Kp*error` và `Kd*d(error)` để đánh giá trực quan tỷ trọng điều khiển.
- Vẽ thêm đoạn mũi tên segment màu vàng tại target goal trong đồ thị trajectory (và màu xanh dương đậm trong OpenCV).
- Các frame lost tracking thì không vẽ trajectory (tự động ngắt nét đứt quãng, không nối dây ảo).

#### Bảng tổng hợp kết quả toàn bộ 8 lần chạy thử nghiệm:

| # | Trường hợp | File Log | Target $\theta_{target}$ | Target Pixel $(x, y)$ | Heading Fit $\theta_{traj}$ | Sai số $|\Delta \theta|$ | Quãng đường Phase 4 | Số frames (Ph1/Ph2/Ph3/Ph4) | Lost Tracking |
|---|:---:|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | **TH 1 (Lần 1)** | `log_roi_20260918_173410.csv` | **-18.9°** | `(593.9, 265.1)` | **-10.9°** | **8.00°** | 230.4 px | 31f / 116f / 66f / 91f | 0f |
| 2 | **TH 1 (Lần 2)** | `log_roi_20260918_173437.csv` | **-18.9°** | `(593.9, 265.1)` | **-14.1°** | **4.77°** | 230.7 px | 28f / 143f / 32f / 91f | 0f |
| 3 | **TH 2 (Lần 1)** | `log_roi_20260918_173529.csv` | **+14.0°** | `(446.8, 327.2)` | **+11.1°** | **2.86°** | 235.8 px | 24f / 172f / 54f / 91f | 0f |
| 4 | **TH 2 (Lần 2)** | `log_roi_20260918_173601.csv` | **+14.0°** | `(446.8, 327.2)` | **+9.1°** | **4.94°** | 240.1 px | 37f / 130f / 69f / 91f | 0f |
| 5 | **TH 3 (Lần 1)** | `log_roi_20260918_173958.csv` | **-165.9°** | `(757.3, 200.6)` | **-164.8°** | **1.06°** | 202.3 px | 34f / 157f / 74f / 91f | 0f |
| 6 | **TH 3 (Lần 2)** | `log_roi_20260918_174107.csv` | **-165.9°** | `(757.3, 200.6)` | **-160.8°** | **5.09°** | 203.3 px | 34f / 144f / 85f / 91f | 0f |
| 7 | **TH 4 (Lần 1)** | `log_roi_20260918_174202.csv` | **+108.9°** | `(640.1, 480.0)` | **+100.2°** | **8.67°** | 229.5 px | 31f / 193f / 49f / 91f | 0f |
| 8 | **TH 4 (Lần 2)** | `log_roi_20260918_174236.csv` | **+108.9°** | `(640.1, 480.0)` | **+126.9°** | **18.02°** | 242.0 px | 38f / 172f / 58f / 88f | 2f |

> **Nhận xét chung:**
> - **Giảm hiện tượng đánh võng:** Với cấu hình $K_{p2} = 0.01$ và $K_{d2} = 0.04$, đường quỹ đạo 2D đi thẳng và ổn định hơn.
> - **Độ chính xác xoay góc (Phase 3):** Đa số các lần chạy đều bám sát góc target ngẫu nhiên với sai số $|\Delta \theta|$ nhỏ (trung bình chỉ khoảng **$4.46^\circ$** cho các lần chạy ổn định)
---

#### 3.1 Trường hợp 1 
- **Target heading:** `-18.9°`
- **Target pixel center:** `(593.9, 265.1)`

**Lần test 1 — `log_roi_20260918_173410.csv` | Heading Fit: `-10.9°` | $|\Delta \theta| = 8.00°$ | Phase 4: `230.4 px`**

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260918_173410_2d_trajectory.png" alt="Traj 1A" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260918_173410_pid_diff_analysis.png" alt="Diff 1A" width="800">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260918_173410_phase4_fwd_bwd_heading.png" alt="Ph4 Heading 1A" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260918_173410_pid_analysis.png" alt="PID 1A" width="800">

**Lần test 2 — `log_roi_20260918_173437.csv` | Heading Fit: `-14.1°` | $|\Delta \theta| = 4.77°$ | Phase 4: `230.7 px`**

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260918_173437_2d_trajectory.png" alt="Traj 1B" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260918_173437_pid_diff_analysis.png" alt="Diff 1B" width="800">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260918_173437_phase4_fwd_bwd_heading.png" alt="Ph4 Heading 1B" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260918_173437_pid_analysis.png" alt="PID 1B" width="800">

---

#### 3.2 Trường hợp 2 
- **Target heading:** `+14.0°`
- **Target pixel center:** `(446.8, 327.2)`

**Lần test 1 — `log_roi_20260918_173529.csv` | Heading Fit: `+11.1°` | $|\Delta \theta| = 2.86°$ | Phase 4: `235.8 px`**

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260918_173529_2d_trajectory.png" alt="Traj 2A" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260918_173529_pid_diff_analysis.png" alt="Diff 2A" width="800">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260918_173529_phase4_fwd_bwd_heading.png" alt="Ph4 Heading 2A" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260918_173529_pid_analysis.png" alt="PID 2A" width="800">

**Lần test 2 — `log_roi_20260918_173601.csv` | Heading Fit: `+9.1°` | $|\Delta \theta| = 4.94°$ | Phase 4: `240.1 px`**

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260918_173601_2d_trajectory.png" alt="Traj 2B" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260918_173601_pid_diff_analysis.png" alt="Diff 2B" width="800">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260918_173601_phase4_fwd_bwd_heading.png" alt="Ph4 Heading 2B" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260918_173601_pid_analysis.png" alt="PID 2B" width="800">

---

#### 3.3 Trường hợp 3 
- **Target heading:** `-165.9°`
- **Target pixel center:** `(757.3, 200.6)`

**Lần test 1 — `log_roi_20260918_173958.csv` | Heading Fit: `-164.8°` | $|\Delta \theta| = 1.06°$ | Phase 4: `202.3 px`**

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260918_173958_2d_trajectory.png" alt="Traj 3A" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260918_173958_pid_diff_analysis.png" alt="Diff 3A" width="800">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260918_173958_phase4_fwd_bwd_heading.png" alt="Ph4 Heading 3A" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260918_173958_pid_analysis.png" alt="PID 3A" width="800">

**Lần test 2 — `log_roi_20260918_174107.csv` | Heading Fit: `-160.8°` | $|\Delta \theta| = 5.09°$ | Phase 4: `203.3 px`**

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260918_174107_2d_trajectory.png" alt="Traj 3B" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260918_174107_pid_diff_analysis.png" alt="Diff 3B" width="800">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260918_174107_phase4_fwd_bwd_heading.png" alt="Ph4 Heading 3B" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260918_174107_pid_analysis.png" alt="PID 3B" width="800">

---

#### 3.4 Trường hợp 4 
- **Target heading:** `+108.9°`
- **Target pixel center:** `(640.1, 480.0)`

**Lần test 1 — `log_roi_20260918_174202.csv` | Heading Fit: `+100.2°` | $|\Delta \theta| = 8.67°$ | Phase 4: `229.5 px`**

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260918_174202_2d_trajectory.png" alt="Traj 4A" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260918_174202_pid_diff_analysis.png" alt="Diff 4A" width="800">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260918_174202_phase4_fwd_bwd_heading.png" alt="Ph4 Heading 4A" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260918_174202_pid_analysis.png" alt="PID 4A" width="800">

**Lần test 2 — `log_roi_20260918_174236.csv` | Heading Fit: `+126.9°` | $|\Delta \theta| = 18.02°$ | Phase 4: `242.0 px`**

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260918_174236_2d_trajectory.png" alt="Traj 4B" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260918_174236_pid_diff_analysis.png" alt="Diff 4B" width="800">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260918_174236_phase4_fwd_bwd_heading.png" alt="Ph4 Heading 4B" width="600">

<img src="LeanbotTinyRC_AI_PIDControl/benchmark_logs/plots/log_roi_20260918_174236_pid_analysis.png" alt="PID 4B" width="800">

---

**Lỗi còn tồn đọng :**
- **Log ngắt trước khi Leanbot về tới Target ở Phase 4:** Do bộ đếm thời gian Python trên máy tính chạy code kết thúc cứng ở `2 * 3.0 = 6.0` giây, trong khi phần cứng Leanbot thực thi lệnh `run_fw_bw` có thể cần thời gian nhiều hơn vì có hàm stopAndWait() và thời gian trễ giao tiếp BLE. 
- Quan sát trên đồ thị trajectory có thể thấy điểm End chưa về tới target 
> Phương án em đề xuất là thêm phần feedback/verify của Leanbot về hệ thống để kết thúc phase thay vì đếm thời gian nhưu hiện tại ạ . 

## B. Khó khăn 
- Về vấn đề chụp thêm data khi lost tracking :
  - Khi mất tracking , Leanbot không nhận được tín hiệu điều khiển BLE nữa, tuy nhiên Leanbot có quán tính và sẽ di chuyển 1 chút ạ 
  - Từ đó góc có thể sẽ bị sai lệnh đi 1 chút, nên nếu em dùng label góc của frame trước khi lost tracking thì có thể nó bị sai mất một chút ạ 
  - Em xin phép nhận thêm đề xuất của Thầy về nội dung này ạ . 
## C. Công việc tiếp theo 
- Thêm cơ chế chụp thêm data khi lost tracking 
- Em xin phép nhận hướng đi tiếp theo từ Thầy ạ . 