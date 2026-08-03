# Báo cáo công việc ngày 03/08/2026

## A. Công việc đã làm 
- Thử nghiệm phương pháp làm mượt quỹ đạo di chuyển Leanbot bằng **Polynomial Fitting (bậc 3)** trực tiếp trên dữ liệu $(t, x_t, y_t)$.

## 1. File Code sử dụng và dữ liệu Benchmark

- [`tools/plot_poly_smooth_segments.py`](tools/plot_poly_smooth_segments.py): công cụ chọn đoạn 30 điểm liên tiếp, chuẩn hóa thời gian $t$, fit polynomial bậc 3 cho $x(t)$ và $y(t)$, xuất công thức hệ số và đồ thị.
- [`benchmark/roi_tracking_runlr_2000_1000.csv`](benchmark/roi_tracking_runlr_2000_1000.csv): log quỹ đạo vận tốc `runLR(2000,1000)`.
- [`benchmark/roi_tracking_runlr_2000_1300.csv`](benchmark/roi_tracking_runlr_2000_1300.csv): log quỹ đạo vận tốc `runLR(2000,1300)`.
- [`benchmark/roi_tracking_runlr_2000_1600.csv`](benchmark/roi_tracking_runlr_2000_1600.csv): log quỹ đạo vận tốc `runLR(2000,1600)`.

---

## 2. Các bước thực hiện

### Bước 1: Đọc và chọn đoạn dữ liệu 30 điểm
- Chọn ngẫu nhiên đoạn có đúng 30 điểm liên tiếp (~ 2 giây ở 15 FPS).
- Không có tọa độ `NaN` hoặc vô hạn (`Inf`).
- Không chứa frame có `tracking_lost != 0`.
- Các đoạn được chọn không chồng lấn lên nhau.

### Bước 2: Chuẩn hóa trục thời gian $t$
- Chuỗi thời gian chuẩn hóa:
  $$t = \frac{[0, 1, 2, \dots, 29]}{30} \quad \implies \quad t \in [0.0, 0.967)$$

### Bước 3: Fit Polynomial bậc 3 cho $x(t)$ và $y(t)$
- Phương trình cho tọa độ $X$:
  $$x_{smooth}(t) = f_x(t) = a_3 t^3 + a_2 t^2 + a_1 t + a_0$$
- Phương trình cho tọa độ $Y$:
  $$y_{smooth}(t) = f_y(t) = b_3 t^3 + b_2 t^2 + b_1 t + b_0$$

#### Đoạn code sử dụng

```python
import numpy as np

# 1. Tạo trục thời gian chuẩn hóa t trong [0, 1)
n_pts = len(x_seg)  # 30 điểm
t_norm = np.arange(n_pts, dtype=float) / float(n_pts)  # [0/30, 1/30, ..., 29/30]

# 2. Fit Polynomial bậc 3 trực tiếp bằng NumPy
coeffs_x = np.polyfit(t_norm, x_seg, deg=3)  # Trả về [a3, a2, a1, a0]
coeffs_y = np.polyfit(t_norm, y_seg, deg=3)  # Trả về [b3, b2, b1, b0]

# 3. Tính tọa độ smooth từ các hệ số đa thức
x_smooth = np.polyval(coeffs_x, t_norm)
y_smooth = np.polyval(coeffs_y, t_norm)
```

#### Input của hàm `polyfit()`:
- `x_seg`: Mảng 1D gồm 30 tọa độ $X$ gốc từ tracking: $[x_0, x_1, \dots, x_{29}]$ (px).
- `y_seg`: Mảng 1D gồm 30 tọa độ $Y$ gốc từ tracking: $[y_0, y_1, \dots, y_{29}]$ (px).
- `deg`: Bậc của đa thức hồi quy (`deg = 3`).

#### Output của hàm `polyfit()`:
- `coeffs_x`: Mảng chứa 4 hệ số $[a_3, a_2, a_1, a_0]$ của hàm $f_x(t)$.
- `coeffs_y`: Mảng chứa 4 hệ số $[b_3, b_2, b_1, b_0]$ của hàm $f_y(t)$.

#### Input của hàm `polyval()`:
- `coeffs_x`: Mảng chứa 4 hệ số $[a_3, a_2, a_1, a_0]$ của hàm $f_x(t)$.
- `coeffs_y`: Mảng chứa 4 hệ số $[b_3, b_2, b_1, b_0]$ của hàm $f_y(t)$.
- `t_norm`: Mảng 30 tọa độ thời gian chuẩn hóa từ 0 đến 1.

#### Output của hàm `polyval()`:
- `x_smooth`: Mảng 30 tọa độ mượt đã được tính toán nằm trên đường cong đa thức.
- `y_smooth`: Mảng 30 tọa độ mượt đã được tính toán nằm trên đường cong đa thức.

### Bước 4: Vẽ đồ thị đầu ra
Xuất 2 loại đồ thị cho mỗi đoạn:
1. **Component plot:** $X(t)$ và $Y(t)$ theo $t$, hiển thị công thức đa thức $f_x(t)$ và $f_y(t)$.
2. **2D Trajectory plot:** Quỹ đạo $(x, y)$ gốc vs smooth trong mặt phẳng ảnh.

---

## 3. Lệnh chạy

```powershell
python tools/plot_poly_smooth_segments.py benchmark --n-segments 3 --poly-degree 3 --seed 42
```

Thư mục đầu ra: [`benchmark/poly_smooth_segments`](benchmark/poly_smooth_segments)

---

## 4. Kết quả & Đồ thị chi tiết

### 4.1. `roi_tracking_runlr_2000_1000.csv`

#### Segment 1 — index `[408, 438)`
- $f_x(t) = -18.779 t^3 + 34.165 t^2 + 62.593 t + 591.678$
- $f_y(t) = -12.249 t^3 + 48.196 t^2 - 41.279 t + 203.605$

| Đồ thị X(t) & Y(t) theo t | Quỹ đạo 2D gốc và smooth |
|---|---|
| ![1000 seg1 components](benchmark/poly_smooth_segments/roi_tracking_runlr_2000_1000_seg1_xy_components.png) | ![1000 seg1 trajectory](benchmark/poly_smooth_segments/roi_tracking_runlr_2000_1000_seg1_trajectory.png) |

#### Segment 2 — index `[479, 509)`
- $f_x(t) = 3.609 t^3 - 41.393 t^2 + 12.805 t + 751.102$
- $f_y(t) = -1.884 t^3 - 12.199 t^2 + 77.767 t + 262.259$

| Đồ thị X(t) & Y(t) theo t | Quỹ đạo 2D gốc và smooth |
|---|---|
| ![1000 seg2 components](benchmark/poly_smooth_segments/roi_tracking_runlr_2000_1000_seg2_xy_components.png) | ![1000 seg2 trajectory](benchmark/poly_smooth_segments/roi_tracking_runlr_2000_1000_seg2_trajectory.png) |

#### Segment 3 — index `[691, 721)`
- $f_x(t) = -8.977 t^3 - 27.630 t^2 + 17.190 t + 749.211$
- $f_y(t) = 5.233 t^3 - 18.967 t^2 + 79.201 t + 256.963$

| Đồ thị X(t) & Y(t) theo t | Quỹ đạo 2D gốc và smooth |
|---|---|
| ![1000 seg3 components](benchmark/poly_smooth_segments/roi_tracking_runlr_2000_1000_seg3_xy_components.png) | ![1000 seg3 trajectory](benchmark/poly_smooth_segments/roi_tracking_runlr_2000_1000_seg3_trajectory.png) |

---

### 4.2. `roi_tracking_runlr_2000_1300.csv`

#### Segment 1 — index `[47, 77)`
- $f_x(t) = 18.733 t^3 - 54.469 t^2 + 103.149 t + 722.975$
- $f_y(t) = 4.445 t^3 + 7.868 t^2 + 32.978 t + 142.771$

| Đồ thị X(t) & Y(t) theo t | Quỹ đạo 2D gốc và smooth |
|---|---|
| ![1300 seg1 components](benchmark/poly_smooth_segments/roi_tracking_runlr_2000_1300_seg1_xy_components.png) | ![1300 seg1 trajectory](benchmark/poly_smooth_segments/roi_tracking_runlr_2000_1300_seg1_trajectory.png) |

#### Segment 2 — index `[656, 686)`
- $f_x(t) = 27.065 t^3 - 64.954 t^2 + 106.951 t + 719.508$
- $f_y(t) = 18.044 t^3 - 12.519 t^2 + 39.691 t + 140.569$

| Đồ thị X(t) & Y(t) theo t | Quỹ đạo 2D gốc và smooth |
|---|---|
| ![1300 seg2 components](benchmark/poly_smooth_segments/roi_tracking_runlr_2000_1300_seg2_xy_components.png) | ![1300 seg2 trajectory](benchmark/poly_smooth_segments/roi_tracking_runlr_2000_1300_seg2_trajectory.png) |

#### Segment 3 — index `[1139, 1169)`
- $f_x(t) = 26.669 t^3 + 3.965 t^2 - 64.063 t + 526.184$
- $f_y(t) = -22.305 t^3 + 37.700 t^2 - 87.066 t + 300.798$

| Đồ thị X(t) & Y(t) theo t | Quỹ đạo 2D gốc và smooth |
|---|---|
| ![1300 seg3 components](benchmark/poly_smooth_segments/roi_tracking_runlr_2000_1300_seg3_xy_components.png) | ![1300 seg3 trajectory](benchmark/poly_smooth_segments/roi_tracking_runlr_2000_1300_seg3_trajectory.png) |

---

### 4.3. `roi_tracking_runlr_2000_1600.csv`

#### Segment 1 — index `[1472, 1502)`
- $f_x(t) = 5.100 t^3 + 10.546 t^2 - 14.522 t + 344.287$
- $f_y(t) = -18.315 t^3 + 30.487 t^2 - 100.739 t + 326.121$

| Đồ thị X(t) & Y(t) theo t | Quỹ đạo 2D gốc và smooth |
|---|---|
| ![1600 seg1 components](benchmark/poly_smooth_segments/roi_tracking_runlr_2000_1600_seg1_xy_components.png) | ![1600 seg1 trajectory](benchmark/poly_smooth_segments/roi_tracking_runlr_2000_1600_seg1_trajectory.png) |

#### Segment 2 — index `[2463, 2493)`
- $f_x(t) = -31.996 t^3 + 63.439 t^2 - 161.024 t + 635.153$
- $f_y(t) = 16.542 t^3 - 49.988 t^2 - 2.130 t + 534.131$

| Đồ thị X(t) & Y(t) theo t | Quỹ đạo 2D gốc và smooth |
|---|---|
| ![1600 seg2 components](benchmark/poly_smooth_segments/roi_tracking_runlr_2000_1600_seg2_xy_components.png) | ![1600 seg2 trajectory](benchmark/poly_smooth_segments/roi_tracking_runlr_2000_1600_seg2_trajectory.png) |

#### Segment 3 — index `[2639, 2669)`
- $f_x(t) = -28.983 t^3 + 51.726 t^2 + 48.952 t + 432.463$
- $f_y(t) = 14.439 t^3 - 11.702 t^2 - 40.849 t + 116.183$

| Đồ thị X(t) & Y(t) theo t | Quỹ đạo 2D gốc và smooth |
|---|---|
| ![1600 seg3 components](benchmark/poly_smooth_segments/roi_tracking_runlr_2000_1600_seg3_xy_components.png) | ![1600 seg3 trajectory](benchmark/poly_smooth_segments/roi_tracking_runlr_2000_1600_seg3_trajectory.png) |

---

## B. Khó khăn 
- Không.

## C. Công việc tiếp theo 
- Em xin phép nhận công việc tiếp theo từ Thầy ạ.