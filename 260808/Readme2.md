# Báo cáo nghiên cứu Lab ngày 08/08/2026 (Tiếp theo)

## A. Công việc đã làm 
- Vẽ lại đồ thị góc và quỹ đạo: loại bỏ các đường smooth 1st, smooth 2nd và các đường EMA alpha = 0.1, 0.3.
- Chỉ giữ lại dữ liệu gốc **Raw** và các đường **EMA với hệ số alpha = 0.5, 0.7, 0.9**.
- Bổ sung đường biểu đồ góc tiếp tuyến được tính trực tiếp từ tọa độ mượt EMA của quỹ đạo.

---

## 1. Phương pháp thực hiện

### a. Làm mượt Quỹ đạo 2D (x, y) bằng EMA
Áp dụng công thức EMA độc lập trên 2 trục tọa độ với hệ số alpha = 0.5, 0.7, 0.9:

<p align="center">
  <img src="formulas/formula_ema_xy_dark.png#gh-dark-mode-only" alt="Công thức EMA Tọa độ 2D" height="75" />
  <img src="formulas/formula_ema_xy_light.png#gh-light-mode-only" alt="Công thức EMA Tọa độ 2D" height="75" />
</p>

### b. Làm mượt Góc từ Model bằng EMA Vector hóa
Để tránh đứt gãy biên khi xoay qua mốc 180 độ, áp dụng vector hóa lượng giác:

<p align="center">
  <img src="formulas/formula_ema_vector_trig_dark.png#gh-dark-mode-only" alt="Vector hóa lượng giác" height="65" />
  <img src="formulas/formula_ema_vector_trig_light.png#gh-light-mode-only" alt="Vector hóa lượng giác" height="65" />
  <br/>
  <img src="formulas/formula_ema_vector_smooth_dark.png#gh-dark-mode-only" alt="Làm mượt vector EMA" height="65" />
  <img src="formulas/formula_ema_vector_smooth_light.png#gh-light-mode-only" alt="Làm mượt vector EMA" height="65" />
  <br/>
  <img src="formulas/formula_ema_vector_atan_dark.png#gh-dark-mode-only" alt="Khôi phục góc mượt atan2" height="65" />
  <img src="formulas/formula_ema_vector_atan_light.png#gh-light-mode-only" alt="Khôi phục góc mượt atan2" height="65" />
</p>

### c. Tính Góc Tiếp tuyến Quỹ đạo từ Tọa độ mượt EMA (EMA Trajectory Angle)
Dựa trên vector dịch chuyển giữa 2 điểm tọa độ mượt EMA liên tiếp (Sx_t, Sy_t) và (Sx_{t-1}, Sy_{t-1}):

<p align="center">
  <img src="formulas/formula_ema_traj_diff_dark.png#gh-dark-mode-only" alt="Vector dịch chuyển mượt" height="65" />
  <img src="formulas/formula_ema_traj_diff_light.png#gh-light-mode-only" alt="Vector dịch chuyển mượt" height="65" />
  <br/>
  <img src="formulas/formula_ema_traj_atan_dark.png#gh-dark-mode-only" alt="Góc tiếp tuyến quỹ đạo mượt" height="65" />
  <img src="formulas/formula_ema_traj_atan_light.png#gh-light-mode-only" alt="Góc tiếp tuyến quỹ đạo mượt" height="65" />
</p>

---

## 2. File Code & Lệnh chạy

- File code sử dụng: [`tools/plot_ema_clean.py`](tools/plot_ema_clean.py)

```powershell
# Lệnh tạo file đồ thị EMA (Raw vs EMA alpha 0.5, 0.7, 0.9)
python tools/plot_ema_clean.py benchmark/1turn_polynomial_order2_length30.csv --seg-len 30 --num-segs 3 --seed 99
python tools/plot_ema_clean.py benchmark/2turn_polynomial_order2_length30.csv --seg-len 30 --num-segs 3 --seed 42
python tools/plot_ema_clean.py benchmark/3turn_polynomial_order2_length30.csv --seg-len 30 --num-segs 3 --seed 123
```

--- 

## 3. Kết quả Biểu đồ (Raw, EMA 0.5, 0.7, 0.9, EMA Traj Angle 0.5, 0.7, 0.9)

### 3.1. Leanbot chạy 3 vòng (`3turn`)

#### a) Đồ thị Quỹ đạo 2D & Chuỗi Thời gian Góc (Tổng thể)
![3turn EMA Selective Trajectory](benchmark/3turn_ema_selective_2d_trajectory.png)
![3turn EMA Selective Time Series](benchmark/3turn_ema_selective_time_series.png)

#### b) Các đoạn Zoom-in 30 điểm ngẫu nhiên (Raw vs EMA Vector Angle vs EMA Traj Angle)
![3turn EMA Selective Seg 1](benchmark/3turn_ema_selective_seg1.png)
![3turn EMA Selective Seg 2](benchmark/3turn_ema_selective_seg2.png)
![3turn EMA Selective Seg 3](benchmark/3turn_ema_selective_seg3.png)

---

### 3.2. Leanbot chạy 2 vòng (`2turn`)

#### a) Đồ thị Quỹ đạo 2D & Chuỗi Thời gian Góc (Tổng thể)
![2turn EMA Selective Trajectory](benchmark/2turn_ema_selective_2d_trajectory.png)
![2turn EMA Selective Time Series](benchmark/2turn_ema_selective_time_series.png)

#### b) Các đoạn Zoom-in 30 điểm ngẫu nhiên (Raw vs EMA Vector Angle vs EMA Traj Angle)
![2turn EMA Selective Seg 1](benchmark/2turn_ema_selective_seg1.png)
![2turn EMA Selective Seg 2](benchmark/2turn_ema_selective_seg2.png)
![2turn EMA Selective Seg 3](benchmark/2turn_ema_selective_seg3.png)

---

### 3.3. Leanbot chạy 1 vòng (`1turn`)

#### a) Đồ thị Quỹ đạo 2D & Chuỗi Thời gian Góc (Tổng thể)
![1turn EMA Selective Trajectory](benchmark/1turn_ema_selective_2d_trajectory.png)
![1turn EMA Selective Time Series](benchmark/1turn_ema_selective_time_series.png)

#### b) Các đoạn Zoom-in 30 điểm ngẫu nhiên (Raw vs EMA Vector Angle vs EMA Traj Angle)
![1turn EMA Selective Seg 1](benchmark/1turn_ema_selective_seg1.png)
![1turn EMA Selective Seg 2](benchmark/1turn_ema_selective_seg2.png)
![1turn EMA Selective Seg 3](benchmark/1turn_ema_selective_seg3.png)

---

## B. Khó khăn 
- Không 

## C. Công việc tiếp theo
- Em xin phép nhận hướng đi tiếp theo từ Thầy ạ.