# Báo cáo công việc ngày 28/08/2026

## A. Công việc đã làm 
- Đổi cơ chế start/end ghi log từ phím R thành phím S : khi bấm S thì Leanbot bắt đầu di chuyển và ghi log đồng thời, tới target sẽ kết thúc ghi log 
- Báo cáo lại hệ số weight giữa Model angle và Tangent Angle và chỉnh sửa hệ số . 
- Tăng kP và kiểm thử 


### 1. Đối cơ chế start/end ghi log từ phím R thành S
- Vì trước đó tool được sử dụng để ghi log cho các lần test Leanbot trước đó nên em vẫn để phím R để start và end ghi log ạ 
- Chỉnh sửa tool từ phím R thành phím S/P : 
    - Khi bấm S thì Leanbot bắt đầu di chuyển và ghi log đồng thời
    - Khi Leanbot tới đích thì dừng di chuyển và kết thúc ghi log  
    - Khi bấm P thì Leanbot bắt đầu xuay tại chỗ và ghi log đồng thời 
    - Khi xuay tới Angle target thì dừng xuay và kết thúc ghi log  
- Code sử dụng : [leanbotCameraController.py](LeanbotTinyRC\leanbotCameraController.py)

| Phím | Chức năng |
|------|-----------|
| `S`  | Bắt đầu PID + tự động ghi log |
| `P`  | Tạm dừng PID |
| `C`  | Hủy lượt chạy |
| `Q`  | Thoát |
- Lệnh chạy : 
```bash
    python .\leanbotCameraController.py --show --source 1 --ble 983949
```

### 2. Hệ số Weight giữa Model Angle và Tangent Angle 

**Hệ số weight hiện tại : K = 3.0**
- Leanbot tính `Fused Angle` bằng cách kết hợp 2 nguồn góc:
  - **Model Angle Smooth**: góc hướng của Leanbot ước tính từ YOLO model (qua Poly Fit bậc 1)
  - **Trajectory Angle Smooth**: góc tiếp tuyến quỹ đạo di chuyển thực tế (từ tọa độ x, y qua Poly Fit bậc 2)
- Hệ số `weight_x` quyết định tỉ lệ ảnh hưởng của 2 dữ liệu góc này vào góc fused
**Công thức:**
```
x(v) = K / (K + v)
FusedAngle = x · ModelSmooth + (1 - x) · TrajectorySmooth
```
Trong đó:
- `v` = tốc độ ước tính (pixel/frame) từ đạo hàm quỹ đạo
- `K` = hằng số điều chỉnh mức độ phụ thuộc vào tốc độ
- `weight_x` = `x` ∈ (0, 1) 
  - `weight_x` -> 1: Model tỉ lệ ảnh hưởng nhiều hơn
  - `weight_x` -> 0: Trajectory tỉ lệ ảnh hưởng nhiều hơn 

**Hiện tại:** `K = 3.0` 

**Khi giảm K từ 3 -> 1:**
- Tại cùng tốc độ, `weight_x` giảm mạnh hơn -> Trajectory Angle được tin tưởng nhiều hơn so với Model Angle

- Code sử dụng để tính góc : [angle_smoothing.py](LeanbotTinyRC\angle_smoothing.py)
- Chỉnh sửa : 
```python
    def __init__(
        self,
        window_size: int = 18,
        eval_index: int = -4,
        K: float = 1.0, # K = 3.0 --> 1.0
     ):
```

### 3. Thử tăng Kp và kiểm thử , đánh giá 

**Hệ số PID hiện tại** 
- file code : ([PID_controller.py](LeanbotTinyRC\PID_controller.py)):

| Tham số | Giá trị | Ý nghĩa |
|---------|---------|---------|
| `Kp_angle` | **15.0** | Hệ số P điều khiển góc (Pha 1 - xoay tại chỗ + Pha 2 - bù góc khi chạy) |
| `Kp_dist` | **25.0** | Hệ số P điều khiển khoảng cách (Pha 2 - tiến thẳng) |
| `max_velocity` | **2000** | Tốc độ runLR tối đa |
| `dist_tolerance` | **10.0 px** | Ngưỡng coi là đã tới target pixel |
| `heading_tolerance` | **5.0°** | Ngưỡng coi là đã căn chỉnh góc xong để chuyển qua đi tới target pixel|

**2 pha chuyển động :** Khi Leanbot cần tới điểm target pixel là tâm frame ảnh . 
- **Pha 1 – ALIGNING:** Leanbot xoay tại chỗ để căn góc về hướng target. `v_lr = 0`, `v_diff = Kp_angle × angle_error`
- **Pha 2 – DRIVING:** Leanbot tiến thẳng đến target, đồng thời bù góc theo công thức vận tốc :  `v_lr = Kp_dist × dist`, `v_diff = Kp_angle × angle_error`


**Kết quả kiểm thử:**

- **TEST 1 : Thông số cấu hình ( PID gốc, chưa tăng kP ):** `Kp_angle = 15.0`, `Kp_dist = 25.0`, `K = 1.0`, `heading_tolerance = 5.0°`, `dist_tolerance = 10.0 px`

---

##### Trường hợp 1 
**Ảnh Detection UI thực tế:**
![Detection UI 1](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_152_20260828_144250_detection_ui.png)

**Đồ thị quỹ đạo 2D:**
![Trajectory 1](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_144253_2d_trajectory.png)

**Đồ thị PID & Góc:**
![PID 1](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_144253_pid_analysis.png)


---

##### Trường hợp 2 
**Ảnh Detection UI thực tế:**
![Detection UI 2](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_561_20260828_144317_detection_ui.png)

**Đồ thị quỹ đạo 2D:**
![Trajectory 2](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_144314_2d_trajectory.png)

**Đồ thị PID & Góc:**
![PID 2](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_144314_pid_analysis.png)


---

##### Trường hợp 3 
**Ảnh Detection UI thực tế:**
![Detection UI 3](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_863_20260828_144337_detection_ui.png)

**Đồ thị quỹ đạo 2D:**
![Trajectory 3](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_144338_2d_trajectory.png)

**Đồ thị PID & Góc:**
![PID 3](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_144338_pid_analysis.png)


---

##### Trường hợp 4 
**Ảnh Detection UI thực tế:**
![Detection UI 4](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_449_20260828_145438_detection_ui.png)

**Đồ thị quỹ đạo 2D:**
![Trajectory 4](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_145416_2d_trajectory.png)

**Đồ thị PID & Góc:**
![PID 4](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_145416_pid_analysis.png)
---


> ở vị trí góc CRL , Leanbot bị nhiễu detect do dữ liệu frame ảnh đưa vào model để chạy detect đã chấp nhận cắt bớt một chút ở 2 góc dưới sa bàn để resize ảnh vừa hình vuông để đưa vào model . Nên khi đặt Leanbot ở góc, có thể đã bị cắt bới đặc trưng nên bị nhiễu detect ạ . 


- **TEST 2 : Thông số cấu hình (tăng kP):** `Kp_angle = 20.0`, `Kp_dist = 35.0`, `K = 1.0`, `heading_tolerance = 5.0°`, `dist_tolerance = 10.0 px`

---

##### Trường hợp 1 
**Ảnh Detection UI thực tế:**
![Detection UI 1](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_215_20260828_151125_detection_ui.png)

**Đồ thị quỹ đạo 2D:**
![Trajectory 1](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_151127_2d_trajectory.png)

**Đồ thị PID & Góc:**
![PID 1](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_151127_pid_analysis.png)

---

##### Trường hợp 2 
**Ảnh Detection UI thực tế:**
![Detection UI 2](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_608_20260828_151152_detection_ui.png)

**Đồ thị quỹ đạo 2D:**
![Trajectory 2](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_151152_2d_trajectory.png)

**Đồ thị PID & Góc:**
![PID 2](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_151152_pid_analysis.png)

---

##### Trường hợp 3 
**Ảnh Detection UI thực tế:**
![Detection UI 3](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_1013_20260828_151219_detection_ui.png)

**Đồ thị quỹ đạo 2D:**
![Trajectory 3](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_151219_2d_trajectory.png)

**Đồ thị PID & Góc:**
![PID 3](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_151219_pid_analysis.png)

---

##### Trường hợp 4 
**Ảnh Detection UI thực tế:**
![Detection UI 4](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_1561_20260828_151255_detection_ui.png)

**Đồ thị quỹ đạo 2D:**
![Trajectory 4](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_151256_2d_trajectory.png)

**Đồ thị PID & Góc:**
![PID 4](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_151256_pid_analysis.png)

---
> khi tăng Kp Góc thì Leanbot có hiện tượng vọt lố khỏi góc target ( hướng tới target pixel) khiến cho khi Leanbot chuyển qua chế độ PID đi tới target pixel bị lệch hướng và phải điều chỉnh vận tốc nên quỹ đạo di chuyển là đường cong .  

> Còn đối với Kp_dist = 35 thì chưa có dấu hiện vọt lố khi tới target pixel . 


- **TEST 3 : Thông số cấu hình (tăng Kp_dist lên 45.0, giữ Kp_angle = 15.0):** `Kp_angle = 15.0`, `Kp_dist = 45.0`, `K = 1.0`, `heading_tolerance = 5.0°`, `dist_tolerance = 10.0 px`
- *Mục đích:* Giữ `Kp_angle = 15.0` như ban đầu để không bị vọt lố góc trong Pha 1 căn hướng, đồng thời tăng `Kp_dist = 45.0` để thử nghiệm tốc độ đáp ứng khi tiến về target.

---

##### Trường hợp 1 
**Ảnh xuất phát (trước khi bấm S):**
![Start UI 1](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_136_20260828_152841_detection_ui.png)

**Đồ thị quỹ đạo 2D:**
![Trajectory 1](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_152841_2d_trajectory.png)

**Ảnh khi bị vọt lố, xoay tròn quanh target (trước khi bấm C):**
![Loop Error UI 1](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_437_20260828_152901_detection_ui.png)

**Đồ thị PID & Góc:**
![PID 1](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_152841_pid_analysis.png)

---

##### Trường hợp 2 
**Ảnh xuất phát (trước khi bấm S):**
![Start UI 2](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_606_20260828_152912_detection_ui.png)

**Đồ thị quỹ đạo 2D:**
![Trajectory 2](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_152914_2d_trajectory.png)

**Ảnh khi bị vọt lố, xoay tròn quanh target (trước khi bấm C):**
![Loop Error UI 2](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_866_20260828_152930_detection_ui.png)

**Đồ thị PID & Góc:**
![PID 2](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_152914_pid_analysis.png)

---

##### Trường hợp 3 
**Ảnh xuất phát (trước khi bấm S):**
![Start UI 3](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_1125_20260828_152947_detection_ui.png)

**Đồ thị quỹ đạo 2D:**
![Trajectory 3](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_152948_2d_trajectory.png)

**Đồ thị PID & Góc:**
![PID 3](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_152948_pid_analysis.png)

---

##### Trường hợp 4 
**Ảnh xuất phát (trước khi bấm S):**
![Start UI 4](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_1496_20260828_153012_detection_ui.png)

**Đồ thị quỹ đạo 2D:**
![Trajectory 4](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_153012_2d_trajectory.png)

**Ảnh khi bị vọt lố, xoay tròn quanh target (trước khi bấm C):**
![Loop Error UI 4](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_1699_20260828_153025_detection_ui.png)

**Đồ thị PID & Góc:**
![PID 4](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_153012_pid_analysis.png)

---

> **Nhận xét và phân tích hiện tượng ở TEST 3:**
> - Khi tăng `Kp_dist` lên **45.0**, vận tốc tiến $v_{LR} = K_{p\_dist} \times err_{dist}$ duy trì ở mức cao kể cả khi khoảng cách tới đích đã nhỏ lại. 
> - Có thể do quán tính của robot và độ trễ truyền thông BLE hoặc tốc độ đáp ứng vận tốc của Stepper leanbot không kịp với sự thay đổi vận tốc nên Leanbot không kịp giảm tốc độ trước khi sai lệch vị trí nhỏ hơn vùng dung sai `10px` và bị **vọt lố ra khỏi target pixel**.
> - Khi đã vượt qua target, vector sai lệch vị trí bị đảo chiều `180 độ` , kéo theo sai số góc `angle_error` tăng vọt đột ngột. PID control liên tục trả về tín hiệu bẻ lái để quay đầu, tạo thành **vòng lặp vi sai xoay tròn xung quanh target pixel** em phải ngắt pid control thì mới dừng được vòng lặp .
> Theo em hiện tại công thức vận tốc hiện tại là `v_diff =Kp_angle × err_angle` có mức độ ảnh hưởng chưa được cao so với `v_LR= Kp_distance × err_distance` nên khi Leanbot di chuyển lệnh hướng ở  giai đoạn đầu khi err_distance còn lớn thì chỉ ưu tiên đi tới target pixel và chỉnh góc rất ít . Chỉ khi leanbot đi gần tới target pixle, err_distance giảm nhỏ , thì độ ảnh hưởng của `err_angle`mới lớn hơn và Leanbot mới bắt đầu cua để về đúng hướng của target pixel , nên quỹ đạo mới có đường cong ở giai đoạn cuối đường đi. 


## B. Khó khăn
- Không

## C. Công việc tiếp theo
- Em xin phép nhận hướng đi và nhận xét tiếp theo từ Thầy ạ.