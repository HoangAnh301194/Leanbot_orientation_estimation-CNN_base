# Báo cáo công việc ngày 17/09/2026
## A. Công việc đã làm 
- Thêm cơ chế lưu taret center pixel và target heading 
- Căn chỉnh lại PID 
- Tăng vận tốc và giảm thời gian phase 4 , báo cáo khoảng cách thực tế trên sa bàn 


### 1. Thêm cơ chế lưu target center pixel và target heading 
- Cơ chế hoạt động : 
  - Đặt Leanbot lên sa bàn, vào đúng vị trí target và heading mong muốn khi tới đích
  - Bấm phím T để bắt đầu quá trình set target 
  - Đo center x, y trung bình trong vòng 3 giây, set thành target x, y
  - Sau đó cho Leanbot chạy tiến lùi (Phase 4), rồi linear fit để tính và set target heading
  - Kết thúc quá trình  set target và lấy target này để thực hiện các phase 2 3 4. 

- Code sử dụng : [`leanbotCameraController.py`](LeanbotTinyRC/leanbotCameraController.py)

- Code bổ sung thêm : 

#### Luồng xử lý phím `T` trong vòng lặp chính

Khi bấm phím `T`, biến `set_target_state` được dùng để theo dõi bước hiện tại qua các frame:

**Bước 1 — Đo tọa độ (3 giây):** Xe đứng yên, mỗi frame nhận diện được thì lưu `(cx, cy)` vào buffer. Sau 3 giây tính trung bình -> gán `target_pos`.

**Bước 2 — Chạy tiến/lùi:** Xe chạy tiến thẳng `set_target_time` giây với tốc độ `set_target_speed`, rồi lùi thẳng `set_target_time` giây. Toàn bộ tọa độ quỹ đạo được thu thập 

**Bước 3 — Fit heading & lưu config:** Linear fit bậc 1 toàn bộ quỹ đạo -> tính `θ_fit = atan2(-ay, ax)` -> gán `target_heading`. Lưu ra file `target_config.json`:
```json
{
  "target_x": 573.3,
  "target_y": 245.1,
  "target_heading": 1.7
}
```

- **Các tham số cấu hình quy trình Set Target:**

| Tham số | Kiểu | Mặc định | Mô tả |
|---|---|---|---|
| `--target-config` | `str` | `target_config.json` | Đường dẫn file cấu hình target JSON để tự động nạp khi khởi động |
| `--set-target-time` | `float` | `5.0` | Thời gian chạy tiến/lùi khi lấy mẫu heading set target (giây) |
| `--set-target-speed` | `int` | `1000` | Tốc độ bánh xe khi chạy Set Target |
- **Tái sử dụng cấu hình khi chạy Inference**
- Khi khởi động script `leanbotCameraController.py` tự động nạp cấu hình từ file `target_config.json`:
  - `target_x`, `target_y`: Tự động nạp làm vị trí đích `target_pos`.
  - `target_heading`: Tự động nạp vào góc hướng mục tiêu cho Phase 3.

**Phím điều khiển:**
- `T`: Bắt đầu quy trình Set Target (nếu lấy lại set target thì json sẽ ghi đè file cũ)
- `C`: Hủy bỏ (nếu đang chạy)
- `S`: Sau khi Set Target xong (hoặc khởi động dùng lại file JSON), bấm S để bắt đầu PID chạy các phase 1 -> 2 -> 3 -> 4

--- 

- Thực nghiệm triển khai : 

**Lệnh chạy :**
```powershell
python leanbotCameraController.py `
  --set-target-time 3 `
  --set-target-speed 2000 `
  --kp-angle 30 `
  --heading-tol3 5 `
  --settle-time-ms 500 `
  --fwd-bwd-time 3 `
  --fwd-bwd-speed 2000 `
  --full-model ..\models\yolo11n_latest_version\best_fp16_no_nms_imgsz640_openvino_model `
  --tracking-model ..\models\yolo11n_latest_version\best_fp16_no_nms_imgsz160_openvino_model `
  --show --source 1 `
  --ble 343944
```
![alt text](image.png)

- File json cấu hình set target (`target_config.json`) sau khi đo và fit:
```json
{
  "target_x": 602.3,
  "target_y": 252.3,
  "target_heading": -4.6
}
```

### 2. Căn chỉnh PID tại Phase 3 (dùng chung bộ điều khiển góc với Phase 1)

- Bảng cấu hình PID lựa chọn sau thực nghiệm:

| Tham số | Giá trị | Mô tả / Ghi chú |
|---|---|---|
| `--kp-angle` | `20.0` | Kp góc (dùng chung Phase 1 & 3, giảm từ 30 xuống 25 để tránh vọt lố) |
| `--kd-angle` | `0.04` | Kd góc (dùng chung Phase 1 & 3, tạo lực hãm vi phân triệt tiêu lắc lư) |
| `--heading-tol3` | `5.0°` | Dung sai góc đích |
| `--settle-time-ms` | `500 ms` | Thời gian giữ ổn định tối thiểu trước khi hoàn thành |
| `--fwd-bwd-time` | `0` | Đặt 0 để tắt Phase 4 khi test căn góc Phase 3 |
| Model | `yolo11n_latest_version` | OpenVINO FP16 (640 full + 160 tracking) |
| BLE ID | `343944` | Leanbot BLE ID |

**Lệnh chạy thực nghiệm được**
```powershell
python leanbotCameraController.py `
  --target-config target_config.json `
  --set-target-time 5 `
  --set-target-speed 1500 `
  --kp-angle 20 --kd-angle 0.04 `
  --kp-angle2 0.02 --kd-angle2 0.04 `
  --heading-tol 20 `
  --heading-tol3 5 `
  --settle-time-ms 500 `
  --fwd-bwd-time 3 `
  --fwd-bwd-speed 2000 `
  --full-model ..\models\yolo11n_latest_version\best_fp16_no_nms_imgsz640_openvino_model `
  --tracking-model ..\models\yolo11n_latest_version\best_fp16_no_nms_imgsz160_openvino_model `
  --show --source 1 `
  --ble 343944
```
### 3. Tăng vận tốc Phase 4 và chạy thửu nghiệm . 
- Tăng vận tốc Phase 4, giảm thời gian chạy xuống 3 giây . 
- Báo cáo quãng đường thực tế trên Sa bàn tại Phase 4. 
#### Bảng tổng hợp kết quả toàn bộ 12 lần chạy thử nghiệm:

| # | Góc Đích | File Log | Target $\theta_{target}$ | Heading Fit $\theta_{traj}$ | Sai số \|Δθ\| | Quãng đường Phase 4 (px) | Số frames (Ph1/Ph2/Ph3/Ph4) | Lost Tracking |
|---|:---:|---|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | **135°** | `log_roi_20260917_121433.csv` | **144.8°** | **154.5°** | **9.61°** | 143.9 px | 28f / 140f / 98f / 91f | 0f |
| 2 | **135°** | `log_roi_20260917_121504.csv` | **144.8°** | **154.8°** | **9.93°** | 157.6 px | 30f / 141f / 56f / 90f | 1f |
| 3 | **-135°** | `log_roi_20260917_121339.csv` | **-145.8°** | **-151.0°** | **5.12°** | 142.7 px | 30f / 128f / 39f / 92f | 0f |
| 4 | **45°** | `log_roi_20260917_120502.csv` | **35.3°** | **34.0°** | **1.36°** | 127.2 px | 29f / 136f / 63f / 92f | 2f |
| 5 | **-45°** | `log_roi_20260917_120412.csv` | **-37.8°** | **-31.7°** | **6.17°** | 159.0 px | 25f / 114f / 47f / 91f | 0f |
| 6 | **0°** | `log_roi_20260917_120325.csv` | **-1.1°** | **-5.4°** | **4.26°** | 170.9 px | 0f / 160f / 33f / 92f | 0f |
| 7 | **180°** | `log_roi_20260917_120208.csv` | **176.8°** | **-178.9°** | **4.29°** | 168.9 px | 32f / 148f / 40f / 92f | 0f |
| 8 | **90°** | `log_roi_20260917_121007.csv` | **93.3°** | **97.6°** | **4.33°** | 156.2 px | 35f / 194f / 79f / 91f | 0f |
| 9 | **-90°** | `log_roi_20260917_121104.csv` | **-89.8°** | **-110.5°** | **20.64°** | 125.3 px | 42f / 156f / 60f / 91f | 9f |
| 10 | **-90°** | `log_roi_20260917_121134.csv` | **-89.8°** | **-97.6°** | **7.82°** | 129.4 px | 26f / 140f / 89f / 91f | 10f |
| 11 | **-90°** | `log_roi_20260917_121614.csv` | **-99.1°** | **-123.8°** | **24.68°** | 93.6 px | 32f / 238f / 70f / 91f | 9f |
| 12 | **-90°** | `log_roi_20260917_122010.csv` | **-99.1°** | **-109.2°** | **10.05°** | 90.5 px | 35f / 167f / 103f / 92f | 31f |

> **Nhận xét chung:**
> - **Độ chính xác góc:** Đa số các lần chạy ổn định đều có sai số góc hướng Phase 4 so với `target_heading` tương đối nhỏ với mức trung bình khoảng **5.63°** (dao động từ 1.36° đến 9.93°), nhỏ nhất đối với góc 45° chỉ lệch **1.36°**. Đối với góc -90° thì sai số lớn hơn rõ rệt, trung bình khoảng **15.80°** .
> Lí do sai số có thể do : 
  - Dung sai góc hiện tại đặt là 5 độ
  - Ngoài ra góc từ model cũng có sai số liên tục dao động trong khoảng 2-3 độ theo quan sát thực tế của em ạ. 
> - **Độ dài quãng đường Phase 4:** Quãng đường chạy Phase 4 ở tốc độ `2000` trong `3s` đạt từ $125 \sim 171\text{ px}$ trên camera (tương đương thực tế khoảng **30 cm**, khoảng đúng 1 ô grid sa bàn).

---

#### 3.1 Thử nghiệm lần 1 - Góc 135 độ 

**Lần test 1 — `log_roi_20260917_121433.csv` | Target: `144.8°` | Fit: `154.5°` | $|\Delta \theta| = 9.61°$ | Phase 4: `143.9 px`**

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260917_121433_pid_analysis.png" alt="PID 1A" width="800">

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260917_121433_2d_trajectory.png" alt="Traj 1A" width="600">

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260917_121433_phase4_fwd_bwd_heading.png" alt="Ph4 Heading 1A" width="600">

**Lần test 2 (chạy lại) — `log_roi_20260917_121504.csv` | Target: `144.8°` | Fit: `154.8°` | $|\Delta \theta| = 9.93°$ | Phase 4: `157.6 px`**

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260917_121504_pid_analysis.png" alt="PID 1B" width="800">

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260917_121504_2d_trajectory.png" alt="Traj 1B" width="600">

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260917_121504_phase4_fwd_bwd_heading.png" alt="Ph4 Heading 1B" width="600">

---

#### 3.2 Thử nghiệm lần 2 - Góc -135 độ
- **Log file:** `log_roi_20260917_121339.csv` | **Target Heading:** `-145.8°` | **Heading Fit:** `-151.0°` | **Sai số $|\Delta \theta|$:** `5.12°` | **Quãng đường Phase 4:** `142.7 px`

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260917_121339_pid_analysis.png" alt="PID 2" width="800">

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260917_121339_2d_trajectory.png" alt="Traj 2" width="600">

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260917_121339_phase4_fwd_bwd_heading.png" alt="Ph4 Heading 2" width="600">

---

#### 3.3 Thử nghiệm lần 3 - Góc 45 độ 
- **Log file:** `log_roi_20260917_120502.csv` | **Target Heading:** `35.3°` | **Heading Fit:** `34.0°` | **Sai số $|\Delta \theta|$:** `1.36°` | **Quãng đường Phase 4:** `127.2 px`

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260917_120502_pid_analysis.png" alt="PID 3" width="800">

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260917_120502_2d_trajectory.png" alt="Traj 3" width="600">

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260917_120502_phase4_fwd_bwd_heading.png" alt="Ph4 Heading 3" width="600">

---

#### 3.4 Thử nghiệm lần 4 - Góc -45 độ 
- **Log file:** `log_roi_20260917_120412.csv` | **Target Heading:** `-37.8°` | **Heading Fit:** `-31.7°` | **Sai số $|\Delta \theta|$:** `6.17°` | **Quãng đường Phase 4:** `159.0 px`

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260917_120412_pid_analysis.png" alt="PID 4" width="800">

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260917_120412_2d_trajectory.png" alt="Traj 4" width="600">

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260917_120412_phase4_fwd_bwd_heading.png" alt="Ph4 Heading 4" width="600">

---

#### 3.5 Thử nghiệm lần 5 - Góc 0 độ 
- **Log file:** `log_roi_20260917_120325.csv` | **Target Heading:** `-1.1°` | **Heading Fit:** `-5.4°` | **Sai số $|\Delta \theta|$:** `4.26°` | **Quãng đường Phase 4:** `170.9 px`

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260917_120325_pid_analysis.png" alt="PID 5" width="800">

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260917_120325_2d_trajectory.png" alt="Traj 5" width="600">

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260917_120325_phase4_fwd_bwd_heading.png" alt="Ph4 Heading 5" width="600">

---

#### 3.6 Thử nghiệm lần 6 - Góc 180 độ 
- **Log file:** `log_roi_20260917_120208.csv` | **Target Heading:** `176.8°` | **Heading Fit:** `-178.9°` | **Sai số $|\Delta \theta|$:** `4.29°` | **Quãng đường Phase 4:** `168.9 px`

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260917_120208_pid_analysis.png" alt="PID 6" width="800">

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260917_120208_2d_trajectory.png" alt="Traj 6" width="600">

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260917_120208_phase4_fwd_bwd_heading.png" alt="Ph4 Heading 6" width="600">

---

#### 3.7 Thử nghiệm lần 7 - Góc 90 độ 
- **Log file:** `log_roi_20260917_121007.csv` | **Target Heading:** `93.3°` | **Heading Fit:** `97.6°` | **Sai số $|\Delta \theta|$:** `4.33°` | **Quãng đường Phase 4:** `156.2 px`

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260917_121007_pid_analysis.png" alt="PID 7" width="800">

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260917_121007_2d_trajectory.png" alt="Traj 7" width="600">

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260917_121007_phase4_fwd_bwd_heading.png" alt="Ph4 Heading 7" width="600">

---

#### 3.8 Thử nghiệm lần 8 - Góc -90 độ 

**Lần test 1 — `log_roi_20260917_121104.csv` | Target: `-89.8°` | Fit: `-110.5°` | $|\Delta \theta| = 20.64°$ | Phase 4: `125.3 px` (Bị trượt bánh)**

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260917_121104_pid_analysis.png" alt="PID 8A" width="800">

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260917_121104_2d_trajectory.png" alt="Traj 8A" width="600">

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260917_121104_phase4_fwd_bwd_heading.png" alt="Ph4 Heading 8A" width="600">

**Lần test 2 — `log_roi_20260917_121134.csv` | Target: `-89.8°` | Fit: `-97.6°` | $|\Delta \theta| = 7.82°$ | Phase 4: `129.4 px` (Ổn định)**

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260917_121134_pid_analysis.png" alt="PID 8B" width="800">

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260917_121134_2d_trajectory.png" alt="Traj 8B" width="600">

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260917_121134_phase4_fwd_bwd_heading.png" alt="Ph4 Heading 8B" width="600">

**Lần test 3 (Vị trí target mới) — `log_roi_20260917_121614.csv` | Target: `-99.1°` | Fit: `-123.8°` | $|\Delta \theta| = 24.68°$ | Phase 4: `93.6 px`**

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260917_121614_pid_analysis.png" alt="PID 8C" width="800">

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260917_121614_2d_trajectory.png" alt="Traj 8C" width="600">

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260917_121614_phase4_fwd_bwd_heading.png" alt="Ph4 Heading 8C" width="600">

**Lần test 4 (Chạy lại target mới) — `log_roi_20260917_122010.csv` | Target: `-99.1°` | Fit: `-109.2°` | $|\Delta \theta| = 10.05°$ | Phase 4: `90.5 px`**

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260917_122010_pid_analysis.png" alt="PID 8D" width="800">

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260917_122010_2d_trajectory.png" alt="Traj 8D" width="600">

<img src="LeanbotTinyRC/benchmark_logs/plots/log_roi_20260917_122010_phase4_fwd_bwd_heading.png" alt="Ph4 Heading 8D" width="600"> 


## B. Khó khăn 
- Không
## C. Công việc tiếp theo 
- Sửa code để khi lost tracking thì tự động lưu lại ROI là lable tương ứng ngay trước lúc mất tracking để train thêm. 

