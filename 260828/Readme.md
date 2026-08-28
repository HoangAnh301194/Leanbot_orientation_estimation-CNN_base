# Báo cáo công việc ngày 28/08/2026

## Mục lục
- [A. Công việc đã làm](#a-công-việc-đã-làm)
  - [1. Đối cơ chế start/end ghi log từ phím R thành S](#1-đối-cơ-chế-startend-ghi-log-từ-phím-r-thành-s)
  - [2. Hệ số Weight giữa Model Angle và Tangent Angle](#2-hệ-số-weight-giữa-model-angle-và-tangent-angle)
  - [3. Tăng Kp và kiểm thử](#3-tăng-kp-và-kiểm-thử)
  - [4. Tách PID thành 2 bộ PID_angle và PID_distance và Chỉnh sửa lại hệ số PID](#4-tách-pid-thành-2-bộ-pid_angle-và-pid_distance-và-chỉnh-sửa-lại-hệ-số-pid)
  - [5. Cập nhật công thức tính vận tốc Pha 2](#5-cập-nhật-công-thức-tính-vận-tốc-pha-2)
  - [6. Chạy Inference kiểm thử và đánh giá](#6-chạy-inference-kiểm-thử-và-đánh-giá)
  - [7. Nhận xét tổng quan](#7-nhận-xét-tổng-quan)
- [B. Khó khăn](#b-khó-khăn)
- [C. Công việc tiếp theo](#c-công-việc-tiếp-theo)

## A. Công việc đã làm 
- Đổi cơ chế start/end ghi log từ phím R thành phím S : khi bấm S thì Leanbot bắt đầu di chuyển và ghi log đồng thời, tới target sẽ kết thúc ghi log 
- Báo cáo lại hệ số weight giữa Model angle và Tangent Angle và chỉnh sửa hệ số . 
- Tăng kP và kiểm thử 

- Tách và hoàn thiện cấu trúc bộ điều khiển PID : chia thành 2 bộ PID độc lập cho 2 phase ( kp_angle2 dùng riêng cho phase 2)
- Cập nhật và hoàn thiện công thức tính vận tốc cho Phase 2
-  Chạy Inference thực nghiệm và đánh giá tuning hệ số Kp_angle2

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
![Detection UI 1](LeanbotTinyRC/benchmark_logs_0/manual_captures/manual_cap_152_20260828_144250_detection_ui.png)

**Đồ thị quỹ đạo 2D:**
![Trajectory 1](LeanbotTinyRC/benchmark_logs_0/plots/log_roi_20260828_144253_2d_trajectory.png)

**Đồ thị PID & Góc:**
![PID 1](LeanbotTinyRC/benchmark_logs_0/plots/log_roi_20260828_144253_pid_analysis.png)


---

##### Trường hợp 2 
**Ảnh Detection UI thực tế:**
![Detection UI 2](LeanbotTinyRC/benchmark_logs_0/manual_captures/manual_cap_561_20260828_144317_detection_ui.png)

**Đồ thị quỹ đạo 2D:**
![Trajectory 2](LeanbotTinyRC/benchmark_logs_0/plots/log_roi_20260828_144314_2d_trajectory.png)

**Đồ thị PID & Góc:**
![PID 2](LeanbotTinyRC/benchmark_logs_0/plots/log_roi_20260828_144314_pid_analysis.png)


---

##### Trường hợp 3 
**Ảnh Detection UI thực tế:**
![Detection UI 3](LeanbotTinyRC/benchmark_logs_0/manual_captures/manual_cap_863_20260828_144337_detection_ui.png)

**Đồ thị quỹ đạo 2D:**
![Trajectory 3](LeanbotTinyRC/benchmark_logs_0/plots/log_roi_20260828_144338_2d_trajectory.png)

**Đồ thị PID & Góc:**
![PID 3](LeanbotTinyRC/benchmark_logs_0/plots/log_roi_20260828_144338_pid_analysis.png)


---

##### Trường hợp 4 
**Ảnh Detection UI thực tế:**
![Detection UI 4](LeanbotTinyRC/benchmark_logs_0/manual_captures/manual_cap_449_20260828_145438_detection_ui.png)

**Đồ thị quỹ đạo 2D:**
![Trajectory 4](LeanbotTinyRC/benchmark_logs_0/plots/log_roi_20260828_145416_2d_trajectory.png)

**Đồ thị PID & Góc:**
![PID 4](LeanbotTinyRC/benchmark_logs_0/plots/log_roi_20260828_145416_pid_analysis.png)
---


> ở vị trí góc CRL , Leanbot bị nhiễu detect do dữ liệu frame ảnh đưa vào model để chạy detect đã chấp nhận cắt bớt một chút ở 2 góc dưới sa bàn để resize ảnh vừa hình vuông để đưa vào model . Nên khi đặt Leanbot ở góc, có thể đã bị cắt bới đặc trưng nên bị nhiễu detect ạ . 


- **TEST 2 : Thông số cấu hình (tăng kP):** `Kp_angle = 20.0`, `Kp_dist = 35.0`, `K = 1.0`, `heading_tolerance = 5.0°`, `dist_tolerance = 10.0 px`

---

##### Trường hợp 1 
**Ảnh Detection UI thực tế:**
![Detection UI 1](LeanbotTinyRC/benchmark_logs_0/manual_captures/manual_cap_215_20260828_151125_detection_ui.png)

**Đồ thị quỹ đạo 2D:**
![Trajectory 1](LeanbotTinyRC/benchmark_logs_0/plots/log_roi_20260828_151127_2d_trajectory.png)

**Đồ thị PID & Góc:**
![PID 1](LeanbotTinyRC/benchmark_logs_0/plots/log_roi_20260828_151127_pid_analysis.png)

---

##### Trường hợp 2 
**Ảnh Detection UI thực tế:**
![Detection UI 2](LeanbotTinyRC/benchmark_logs_0/manual_captures/manual_cap_608_20260828_151152_detection_ui.png)

**Đồ thị quỹ đạo 2D:**
![Trajectory 2](LeanbotTinyRC/benchmark_logs_0/plots/log_roi_20260828_151152_2d_trajectory.png)

**Đồ thị PID & Góc:**
![PID 2](LeanbotTinyRC/benchmark_logs_0/plots/log_roi_20260828_151152_pid_analysis.png)

---

##### Trường hợp 3 
**Ảnh Detection UI thực tế:**
![Detection UI 3](LeanbotTinyRC/benchmark_logs_0/manual_captures/manual_cap_1013_20260828_151219_detection_ui.png)

**Đồ thị quỹ đạo 2D:**
![Trajectory 3](LeanbotTinyRC/benchmark_logs_0/plots/log_roi_20260828_151219_2d_trajectory.png)

**Đồ thị PID & Góc:**
![PID 3](LeanbotTinyRC/benchmark_logs_0/plots/log_roi_20260828_151219_pid_analysis.png)

---

##### Trường hợp 4 
**Ảnh Detection UI thực tế:**
![Detection UI 4](LeanbotTinyRC/benchmark_logs_0/manual_captures/manual_cap_1561_20260828_151255_detection_ui.png)

**Đồ thị quỹ đạo 2D:**
![Trajectory 4](LeanbotTinyRC/benchmark_logs_0/plots/log_roi_20260828_151256_2d_trajectory.png)

**Đồ thị PID & Góc:**
![PID 4](LeanbotTinyRC/benchmark_logs_0/plots/log_roi_20260828_151256_pid_analysis.png)

---
> khi tăng Kp Góc thì Leanbot có hiện tượng vọt lố khỏi góc target ( hướng tới target pixel) khiến cho khi Leanbot chuyển qua chế độ PID đi tới target pixel bị lệch hướng và phải điều chỉnh vận tốc nên quỹ đạo di chuyển là đường cong .  

> Còn đối với Kp_dist = 35 thì chưa có dấu hiện vọt lố khi tới target pixel . 


- **TEST 3 : Thông số cấu hình (tăng Kp_dist lên 45.0, giữ Kp_angle = 15.0):** `Kp_angle = 15.0`, `Kp_dist = 45.0`, `K = 1.0`, `heading_tolerance = 5.0°`, `dist_tolerance = 10.0 px`
- *Mục đích:* Giữ `Kp_angle = 15.0` như ban đầu để không bị vọt lố góc trong Pha 1 căn hướng, đồng thời tăng `Kp_dist = 45.0` để thử nghiệm tốc độ đáp ứng khi tiến về target.

---

##### Trường hợp 1 
**Ảnh xuất phát (trước khi bấm S):**
![Start UI 1](LeanbotTinyRC/benchmark_logs_0/manual_captures/manual_cap_136_20260828_152841_detection_ui.png)

**Đồ thị quỹ đạo 2D:**
![Trajectory 1](LeanbotTinyRC/benchmark_logs_0/plots/log_roi_20260828_152841_2d_trajectory.png)

**Ảnh khi bị vọt lố, xoay tròn quanh target (trước khi bấm C):**
![Loop Error UI 1](LeanbotTinyRC/benchmark_logs_0/manual_captures/manual_cap_437_20260828_152901_detection_ui.png)

**Đồ thị PID & Góc:**
![PID 1](LeanbotTinyRC/benchmark_logs_0/plots/log_roi_20260828_152841_pid_analysis.png)

---

##### Trường hợp 2 
**Ảnh xuất phát (trước khi bấm S):**
![Start UI 2](LeanbotTinyRC/benchmark_logs_0/manual_captures/manual_cap_606_20260828_152912_detection_ui.png)

**Đồ thị quỹ đạo 2D:**
![Trajectory 2](LeanbotTinyRC/benchmark_logs_0/plots/log_roi_20260828_152914_2d_trajectory.png)

**Ảnh khi bị vọt lố, xoay tròn quanh target (trước khi bấm C):**
![Loop Error UI 2](LeanbotTinyRC/benchmark_logs_0/manual_captures/manual_cap_866_20260828_152930_detection_ui.png)

**Đồ thị PID & Góc:**
![PID 2](LeanbotTinyRC/benchmark_logs_0/plots/log_roi_20260828_152914_pid_analysis.png)

---

##### Trường hợp 3 
**Ảnh xuất phát (trước khi bấm S):**
![Start UI 3](LeanbotTinyRC/benchmark_logs_0/manual_captures/manual_cap_1125_20260828_152947_detection_ui.png)

**Đồ thị quỹ đạo 2D:**
![Trajectory 3](LeanbotTinyRC/benchmark_logs_0/plots/log_roi_20260828_152948_2d_trajectory.png)

**Đồ thị PID & Góc:**
![PID 3](LeanbotTinyRC/benchmark_logs_0/plots/log_roi_20260828_152948_pid_analysis.png)

---

##### Trường hợp 4 
**Ảnh xuất phát (trước khi bấm S):**
![Start UI 4](LeanbotTinyRC/benchmark_logs_0/manual_captures/manual_cap_1496_20260828_153012_detection_ui.png)

**Đồ thị quỹ đạo 2D:**
![Trajectory 4](LeanbotTinyRC/benchmark_logs_0/plots/log_roi_20260828_153012_2d_trajectory.png)

**Ảnh khi bị vọt lố, xoay tròn quanh target (trước khi bấm C):**
![Loop Error UI 4](LeanbotTinyRC/benchmark_logs_0/manual_captures/manual_cap_1699_20260828_153025_detection_ui.png)

**Đồ thị PID & Góc:**
![PID 4](LeanbotTinyRC/benchmark_logs_0/plots/log_roi_20260828_153012_pid_analysis.png)

---

> **Nhận xét và phân tích hiện tượng ở TEST 3:**
> - Khi tăng `Kp_dist` lên **45.0**, vận tốc tiến $v_{LR} = K_{p\_dist} \times err_{dist}$ duy trì ở mức cao kể cả khi khoảng cách tới đích đã nhỏ lại. 
> - Có thể do quán tính của robot và độ trễ truyền thông BLE hoặc tốc độ đáp ứng vận tốc của Stepper leanbot không kịp với sự thay đổi vận tốc nên Leanbot không kịp giảm tốc độ trước khi sai lệch vị trí nhỏ hơn vùng dung sai `10px` và bị **vọt lố ra khỏi target pixel**.
> - Khi đã vượt qua target, vector sai lệch vị trí bị đảo chiều `180 độ` , kéo theo sai số góc `angle_error` tăng vọt đột ngột. PID control liên tục trả về tín hiệu bẻ lái để quay đầu, tạo thành **vòng lặp vi sai xoay tròn xung quanh target pixel** em phải ngắt pid control thì mới dừng được vòng lặp .
> Theo em hiện tại công thức vận tốc hiện tại là `v_diff =Kp_angle × err_angle` có mức độ ảnh hưởng chưa được cao so với `v_LR= Kp_distance × err_distance` nên khi Leanbot di chuyển lệnh hướng ở  giai đoạn đầu khi err_distance còn lớn thì chỉ ưu tiên đi tới target pixel và chỉnh góc rất ít . Chỉ khi leanbot đi gần tới target pixle, err_distance giảm nhỏ , thì độ ảnh hưởng của `err_angle`mới lớn hơn và Leanbot mới bắt đầu cua để về đúng hướng của target pixel , nên quỹ đạo mới có đường cong ở giai đoạn cuối đường đi. 



### 4. Tách PID thành 2 bộ PID_angle và PID_distance và Chỉnh sửa lại hệ số PID 
- Các thay đổi trong code [(LeanbotTinyRC\PID_controller.py)](LeanbotTinyRC\PID_controller.py) như sau : 
- Khôi phục lại hệ số $K_{p\_dist}$ như ban đầu: **$K_{p\_dist} = 25.0$** .
- Tách riêng hệ số $K_{p\_angle}$ cho từng pha riêng biệt :
  - Pha 1 (Xoay tại chỗ): Dùng hệ số **$K_{p\_angle} = 15.0$**.
  - Pha 2 ( pha tiến tới target): Sử dụng hệ số góc mới **$K_{p\_angle2}$** để tinh chỉnh khả năng căn chỉnh mà không liên quan tới `kp_angle` 
  > Sẽ dùng `kp_angle2` để tinh chỉnh PID và đánh giá ( giữ nguyên `kp_dist` , chỉ tuning `kp_angle2` )


### 5. Cập nhật công thức tính vận tốc Pha 2
- **Công thức tính vận tốc điều khiển ở Pha 2 (Driving) cũ**:

  - Vận tốc tịnh tiến ($v_{LR}$) và vận tốc góc ($v_{diff}$) được tính độc lập với nhau theo khâu tỉ lệ (P):
  $$v_{LR} = K_{p\_dist} \times err_{dist}$$
  $$v_{diff} = K_{p\_angle} \times err_{angle}$$

  - Trộn 2 tín hiệu này để tính vận tốc thô của 2 bánh:
  $$v_{L\_raw} = v_{LR} + v_{diff}$$
  $$v_{R\_raw} = v_{LR} - v_{diff}$$

  - Nếu một trong hai bánh tính ra vượt quá giới hạn vận tốc Leanbot ($V_{max} = 2000$), sử dụng hệ số scale chung (giữ tỉ lệ vi sai) và giảm đồng thời vận tốc cả hai bánh:
  $$scale = \frac{2000}{\max(|v_{L\_raw}|, |v_{R\_raw}|)}$$
  $$v_L = v_{L\_raw} \times scale, \quad v_R = v_{R\_raw} \times scale$$

- **Công thức tính vận tốc sửa đổi mới**:

- **Crop giới hạn $v_{LR}$**:
   - $v_{LR}$ được tính trước và giới hạn ngay trong ngưỡng V_max của Leanbot :
     $$v_{LR} = \max(0, \min(K_{p\_dist} \times err_{dist}, 2000))$$
- **Tính vận tốc vi sai $\Delta v$**:
   - $\Delta v$ được tính tỉ lệ thuận với cả $err_{angle}$ và $v_{LR}$, sử dụng hệ số $K_{p\_angle2}$:
     $$\Delta v = K_{p\_angle2} \times err_{angle} \times v_{LR}$$
- **Tính toán và giới hạn vận tốc từng bánh**:
   - Cộng/trừ $\Delta v$ vào $v_{LR}$ và tiếp tục crop để đảm bảo vận tốc nhỏ hơn $V_{max}$:
     $$v_{L} = \max(-2000, \min(v_{LR} + \Delta v, 2000))$$
     $$v_{R} = \max(-2000, \min(v_{LR} - \Delta v, 2000))$$

- Code sử dụng: [`PID_controller.py`](file:///d:/PTIT/DTT/Nguyen_Huu_Hoang_Anh/260828/LeanbotTinyRC/PID_controller.py#L113-L129):

```python
        # Phase 2: DRIVING - move forward while correcting heading
        v_lr = self.Kp_dist * distance_error
        v_lr_cropped = max(0.0, min(v_lr, float(self.max_velocity)))
        
        # delta_V = Kp_angle2 * angle_error * v_LR
        delta_v = self.Kp_angle2 * angle_error * v_lr_cropped

        speed_left = self._crop_speed(v_lr_cropped + delta_v)
        speed_right = self._crop_speed(v_lr_cropped - delta_v)
        
        debug = self._debug(
            self.PHASE_DRIVING, distance_error, target_heading,
            angle_error, v_lr_cropped, delta_v,
        )
        return speed_left, speed_right, debug
```


### 6. Chạy Inference kiểm thử và đánh giá 
- Cấu hình các thông số hiện tại khi thử nghiệm:

| Bộ PID | Kp | Ki | Kd | Purpose |
|--------|----|----|-----|---------|
| Angle (Pha 1) | 15.0 | 0.0 | 0.0 | Xoay tại chỗ căn hướng tới target angle |
| Distance (Pha 2) | 25.0 | 0.0 | 0.0 | chỉnh vận tốc tiến tới target |
| Angle2 (Pha 2) | 0.02 | 0.0 | 0.0 | chỉnh hướng (nhân với v_LR) khi đang di chuyển |

- Các thông số khác:
  - `dist_tolerance = 10 px` (ngưỡng dừng khi tới đích)
  - `heading_tolerance = 5.0°` (ngưỡng chuyển từ Pha 1 sang Pha 2)
  - `max_velocity = 2000 step/s` (vận tốc tối đa của Leanbot)
- **Test 1: `kp_angle2 = 0.01`**

    - **Trường hợp 1** :
![Detection UI 1](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_604_20260828_171324_detection_ui.png)
![Trajectory 1](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_171324_2d_trajectory.png)
![PID 1](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_171324_pid_analysis.png)
    - **Trường hợp 2** :
![Detection UI 2](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_947_20260828_171347_detection_ui.png)
![Trajectory 2](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_171348_2d_trajectory.png)
![PID 2](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_171348_pid_analysis.png)
    - **Trường hợp 3** : Trường hợp này Leanbot ở góc nên nhiễu detect một vài frame ạ . 
![Detection UI 3](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_1299_20260828_171410_detection_ui.png)
![Trajectory 3](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_171411_2d_trajectory.png)
![PID 3](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_171411_pid_analysis.png)
    - **Trường hợp 4** :
![Detection UI 4](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_1546_20260828_171427_detection_ui.png)
![Trajectory 4](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_171428_2d_trajectory.png)
![PID 4](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_171428_pid_analysis.png)
- **Test 2 : `kp_angle2 = 0.02`**

    - **Trường hợp 1** :
![Detection UI 1](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_262_20260828_170514_detection_ui.png)
![Trajectory 1](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_170515_2d_trajectory.png)
![PID 1](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_170515_pid_analysis.png)
    - **Trường hợp 2** :
![Detection UI 2](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_776_20260828_170548_detection_ui.png)
![Trajectory 2](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_170549_2d_trajectory.png)
![PID 2](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_170549_pid_analysis.png)
    - **Trường hợp 3** :
![Detection UI 3](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_1112_20260828_170611_detection_ui.png)
![Trajectory 3](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_170611_2d_trajectory.png)
![PID 3](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_170611_pid_analysis.png)
    - **Trường hợp 4** :
![Detection UI 4](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_1513_20260828_170637_detection_ui.png)
![Trajectory 4](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_170638_2d_trajectory.png)
![PID 4](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_170638_pid_analysis.png)
- **Test 3: `kp_angle2 = 0.03`**
    - **Trường hợp 1** :
![Detection UI 1](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_149_20260828_172038_detection_ui.png)
![Trajectory 1](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_172038_2d_trajectory.png)
![PID 1](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_172038_pid_analysis.png)
    - **Trường hợp 2** :
![Detection UI 2](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_481_20260828_172100_detection_ui.png)
![Trajectory 2](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_172101_2d_trajectory.png)
![PID 2](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_172101_pid_analysis.png)
    - **Trường hợp 3** :
![Detection UI 3](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_766_20260828_172119_detection_ui.png)
![Trajectory 3](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_172120_2d_trajectory.png)
![PID 3](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_172120_pid_analysis.png)
    - **Trường hợp 4** :
![Detection UI 4](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_1112_20260828_172142_detection_ui.png)
![Trajectory 4](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_172142_2d_trajectory.png)
![PID 4](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_172142_pid_analysis.png)
- **Test 4: `kp_angle2 = 0.04`**
    - **Trường hợp 1** :
![Detection UI 1](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_234_20260828_172545_detection_ui.png)
![Trajectory 1](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_172546_2d_trajectory.png)
![PID 1](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_172546_pid_analysis.png)
    - **Trường hợp 2** :
![Detection UI 2](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_1034_20260828_172638_detection_ui.png)
![Trajectory 2](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_172639_2d_trajectory.png)
![PID 2](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_172639_pid_analysis.png)
    - **Trường hợp 3** :
![Detection UI 3](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_1333_20260828_172658_detection_ui.png)
![Trajectory 3](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_172659_2d_trajectory.png)
![PID 3](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_172659_pid_analysis.png)
    - **Trường hợp 4** :
![Detection UI 4](LeanbotTinyRC/benchmark_logs/manual_captures/manual_cap_1627_20260828_172718_detection_ui.png)
![Trajectory 4](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_172718_2d_trajectory.png)
![PID 4](LeanbotTinyRC/benchmark_logs/plots/log_roi_20260828_172718_pid_analysis.png)



### 7. Nhận xét tổng quan 
- Khi cố định hệ số `kp_angle` = 15, `kp_dist` = 25, và các hệ số `ki,kd` khác = 0 và Tuning giá trị `kp_angle2` từ `0.01 -> 0.04` thì bắt đâu từ giá trị `0.03` bắt đầu có hiện tượng dao động khi di chuyển. Khi tuning lên 0.04 thì hiện tượng dao động rõ hơn và mất ổn định khi góc lệch lớn. 
- Từ kết quả test trên , nhận thấy công thức tính vận tốc mới hoạt động tốt, Leanbot đã tự điều chỉnh hướng trong khi di chuyển. 
- Ngoài ra kết quả từ pha 1 khi PID xuay góc hướng về phía target pixel cũng ảnh hưởng tới độ ổn định của pha 2 . Nếu góc lệch từ pha 1 nhiều thì ở pha 2 Leanbot cần điều chỉnh mạnh hơn để về trạng thái cân bằng.

## B. Khó khăn
- Không

## C. Công việc tiếp theo
- Em xin phép nhận hướng đi và nhận xét tiếp theo từ Thầy ạ.
