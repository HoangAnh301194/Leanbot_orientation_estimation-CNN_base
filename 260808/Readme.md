# Báo cáo công việc ngày 08/08/2026

## A. Công việc đã làm 

- **Trả lời câu hỏi của Thầy:**
  - Xác nhận tham số `SMOOTH_LENGTH` (mặc định 30 điểm) đang được dùng chung cho cả lần smooth 1 ($raw \rightarrow smooth$) và lần smooth 2 ($smooth \rightarrow smooth2$).
- **Chỉnh sửa & Chuẩn hóa lại hiển thị Đồ thị Quỹ đạo 2D & Đồ thị Góc (Angle):**
  - **Raw Trajectory:** Dùng màu đỏ (`#d62728`), marker điểm tròn `o`, nét vẽ nối liền (`-`).
  - **Smooth 1st Pass:** Dùng màu xanh dương (`#1f77b4`), marker hình chữ `x`, nét vẽ nối liền (`-`).
  - **Smooth 2nd Pass:** Dùng màu xanh lá (`#2ca02c`), marker hình dấu cộng `+`, nét vẽ nối liền (`-`).
  - **Tất cả các đường Góc (Angle):** Đều được chuyển sang hiển thị bằng nét vẽ nối liền (`-`) đồng nhất.
- **Khảo sát & Thử nghiệm phương pháp làm mượt quỹ đạo bằng EMA (Exponential Moving Average):**
  - Thử công thức EMA làm mượt tọa độ $(x, y)$:
    $$S_t = \alpha \cdot X_t + (1 - \alpha) \cdot S_{t-1}$$
---

## 1. File Code đã chỉnh sửa

- [`tools/plot_online_poly_log.py`](tools/plot_online_poly_log.py): Vẽ đồ thị quỹ đạo 2D tổng hợp 3 đường (Raw, Smooth 1, Smooth 2) và chuỗi thời gian các góc/tọa độ/FPS.
- [`tools/plot_random_5segments.py`](tools/plot_random_5segments.py): Trích xuất 5 đoạn ngẫu nhiên, vẽ đồ thị Zoom-in 2D trajectory đúng định dạng 3 đường với marker `o`, `x`, `+`.

---

## 2. Lệnh chạy 

### a) Lệnh vẽ biểu đồ tổng hợp 2D Trajectory & Time-Series 

```powershell
# Cửa sổ trượt Length = 30
python tools/plot_online_poly_log.py benchmark/1turn_polynomial_order2_length30.csv --degree 2
python tools/plot_online_poly_log.py benchmark/2turn_polynomial_order2_length30.csv --degree 2
python tools/plot_online_poly_log.py benchmark/3turn_polynomial_order2_length30.csv --degree 2

# Cửa sổ trượt Length = 24
python tools/plot_online_poly_log.py benchmark/1turn_polynomial_order2_length24.csv --degree 2
python tools/plot_online_poly_log.py benchmark/2turn_polynomial_order2_length24.csv --degree 2
python tools/plot_online_poly_log.py benchmark/3turn_polynomial_order2_length24.csv --degree 2

# Cửa sổ trượt Length = 18
python tools/plot_online_poly_log.py benchmark/1turn_polynomial_order2_length18.csv --degree 2
python tools/plot_online_poly_log.py benchmark/2turn_polynomial_order2_length18.csv --degree 2
python tools/plot_online_poly_log.py benchmark/3turn_polynomial_order2_length18.csv --degree 2
```

### b) Lệnh trích xuất 5 Segment ngẫu nhiên (Zoom-in 2D Trajectory & 4-5 Angles)

```powershell
# Cửa sổ trượt Length = 30
python tools/plot_random_5segments.py benchmark/1turn_polynomial_order2_length30.csv --num 5 --seed 99
python tools/plot_random_5segments.py benchmark/2turn_polynomial_order2_length30.csv --num 5 --seed 42
python tools/plot_random_5segments.py benchmark/3turn_polynomial_order2_length30.csv --num 5 --seed 123

# Cửa sổ trượt Length = 24
python tools/plot_random_5segments.py benchmark/1turn_polynomial_order2_length24.csv --num 5 --seed 99
python tools/plot_random_5segments.py benchmark/2turn_polynomial_order2_length24.csv --num 5 --seed 42
python tools/plot_random_5segments.py benchmark/3turn_polynomial_order2_length24.csv --num 5 --seed 123

# Cửa sổ trượt Length = 18
python tools/plot_random_5segments.py benchmark/1turn_polynomial_order2_length18.csv --num 5 --seed 99
python tools/plot_random_5segments.py benchmark/2turn_polynomial_order2_length18.csv --num 5 --seed 42
python tools/plot_random_5segments.py benchmark/3turn_polynomial_order2_length18.csv --num 5 --seed 123
```

---

## 4. Kết quả Đồ thị đã cập nhật

### 4.1. Thử nghiệm Cửa sổ trượt Length = 30

#### Leanbot chạy 3 vòng (Length = 30)

![3 turn trajectory length 30](benchmark/3turn_polynomial_order2_length30_2d_trajectory.png)
![3 turn five angles length 30](benchmark/3turn_polynomial_order2_length30_time_series.png)

![3 turn len30 seg1](benchmark/3turn_polynomial_order2_length30_random_seg1.png)
![3 turn len30 seg2](benchmark/3turn_polynomial_order2_length30_random_seg2.png)
![3 turn len30 seg3](benchmark/3turn_polynomial_order2_length30_random_seg3.png)
![3 turn len30 seg4](benchmark/3turn_polynomial_order2_length30_random_seg4.png)
![3 turn len30 seg5](benchmark/3turn_polynomial_order2_length30_random_seg5.png)

#### Leanbot chạy 2 vòng (Length = 30)

![2 turn trajectory length 30](benchmark/2turn_polynomial_order2_length30_2d_trajectory.png)
![2 turn five angles length 30](benchmark/2turn_polynomial_order2_length30_time_series.png)

![2 turn len30 seg1](benchmark/2turn_polynomial_order2_length30_random_seg1.png)
![2 turn len30 seg2](benchmark/2turn_polynomial_order2_length30_random_seg2.png)
![2 turn len30 seg3](benchmark/2turn_polynomial_order2_length30_random_seg3.png)
![2 turn len30 seg4](benchmark/2turn_polynomial_order2_length30_random_seg4.png)
![2 turn len30 seg5](benchmark/2turn_polynomial_order2_length30_random_seg5.png)

#### Leanbot chạy 1 vòng (Length = 30)

![1 turn trajectory length 30](benchmark/1turn_polynomial_order2_length30_2d_trajectory.png)
![1 turn five angles length 30](benchmark/1turn_polynomial_order2_length30_time_series.png)

![1 turn len30 seg1](benchmark/1turn_polynomial_order2_length30_random_seg1.png)
![1 turn len30 seg2](benchmark/1turn_polynomial_order2_length30_random_seg2.png)
![1 turn len30 seg3](benchmark/1turn_polynomial_order2_length30_random_seg3.png)
![1 turn len30 seg4](benchmark/1turn_polynomial_order2_length30_random_seg4.png)
![1 turn len30 seg5](benchmark/1turn_polynomial_order2_length30_random_seg5.png)

---

### 4.2. Thử nghiệm Cửa sổ trượt Length = 24

#### Leanbot chạy 3 vòng (Length = 24)

![3 turn trajectory length 24](benchmark/3turn_polynomial_order2_length24_2d_trajectory.png)
![3 turn five angles length 24](benchmark/3turn_polynomial_order2_length24_time_series.png)

![3 turn len24 seg1](benchmark/3turn_polynomial_order2_length24_random_seg1.png)
![3 turn len24 seg2](benchmark/3turn_polynomial_order2_length24_random_seg2.png)
![3 turn len24 seg3](benchmark/3turn_polynomial_order2_length24_random_seg3.png)
![3 turn len24 seg4](benchmark/3turn_polynomial_order2_length24_random_seg4.png)
![3 turn len24 seg5](benchmark/3turn_polynomial_order2_length24_random_seg5.png)

#### Leanbot chạy 2 vòng (Length = 24)

![2 turn trajectory length 24](benchmark/2turn_polynomial_order2_length24_2d_trajectory.png)
![2 turn five angles length 24](benchmark/2turn_polynomial_order2_length24_time_series.png)

![2 turn len24 seg1](benchmark/2turn_polynomial_order2_length24_random_seg1.png)
![2 turn len24 seg2](benchmark/2turn_polynomial_order2_length24_random_seg2.png)
![2 turn len24 seg3](benchmark/2turn_polynomial_order2_length24_random_seg3.png)
![2 turn len24 seg4](benchmark/2turn_polynomial_order2_length24_random_seg4.png)
![2 turn len24 seg5](benchmark/2turn_polynomial_order2_length24_random_seg5.png)

#### Leanbot chạy 1 vòng (Length = 24)

![1 turn trajectory length 24](benchmark/1turn_polynomial_order2_length24_2d_trajectory.png)
![1 turn five angles length 24](benchmark/1turn_polynomial_order2_length24_time_series.png)

![1 turn len24 seg1](benchmark/1turn_polynomial_order2_length24_random_seg1.png)
![1 turn len24 seg2](benchmark/1turn_polynomial_order2_length24_random_seg2.png)
![1 turn len24 seg3](benchmark/1turn_polynomial_order2_length24_random_seg3.png)
![1 turn len24 seg4](benchmark/1turn_polynomial_order2_length24_random_seg4.png)
![1 turn len24 seg5](benchmark/1turn_polynomial_order2_length24_random_seg5.png)

---

### 4.3. Thử nghiệm Cửa sổ trượt Length = 18

#### Leanbot chạy 3 vòng (Length = 18)

![3 turn trajectory length 18](benchmark/3turn_polynomial_order2_length18_2d_trajectory.png)
![3 turn five angles length 18](benchmark/3turn_polynomial_order2_length18_time_series.png)

![3 turn len18 seg1](benchmark/3turn_polynomial_order2_length18_random_seg1.png)
![3 turn len18 seg2](benchmark/3turn_polynomial_order2_length18_random_seg2.png)
![3 turn len18 seg3](benchmark/3turn_polynomial_order2_length18_random_seg3.png)
![3 turn len18 seg4](benchmark/3turn_polynomial_order2_length18_random_seg4.png)
![3 turn len18 seg5](benchmark/3turn_polynomial_order2_length18_random_seg5.png)

#### Leanbot chạy 2 vòng (Length = 18)

![2 turn trajectory length 18](benchmark/2turn_polynomial_order2_length18_2d_trajectory.png)
![2 turn five angles length 18](benchmark/2turn_polynomial_order2_length18_time_series.png)

![2 turn len18 seg1](benchmark/2turn_polynomial_order2_length18_random_seg1.png)
![2 turn len18 seg2](benchmark/2turn_polynomial_order2_length18_random_seg2.png)
![2 turn len18 seg3](benchmark/2turn_polynomial_order2_length18_random_seg3.png)
![2 turn len18 seg4](benchmark/2turn_polynomial_order2_length18_random_seg4.png)
![2 turn len18 seg5](benchmark/2turn_polynomial_order2_length18_random_seg5.png)

#### Leanbot chạy 1 vòng (Length = 18)

![1 turn trajectory length 18](benchmark/1turn_polynomial_order2_length18_2d_trajectory.png)
![1 turn five angles length 18](benchmark/1turn_polynomial_order2_length18_time_series.png)

![1 turn len18 seg1](benchmark/1turn_polynomial_order2_length18_random_seg1.png)
![1 turn len18 seg2](benchmark/1turn_polynomial_order2_length18_random_seg2.png)
![1 turn len18 seg3](benchmark/1turn_polynomial_order2_length18_random_seg3.png)
![1 turn len18 seg4](benchmark/1turn_polynomial_order2_length18_random_seg4.png)
![1 turn len18 seg5](benchmark/1turn_polynomial_order2_length18_random_seg5.png)

---

## 5. Thử nghiệm Smooth quỹ đạo & Góc bằng EMA (Exponential Moving Average)

### 5.1. Cách thức thực hiện EMA

Mô hình xử lý dữ liệu chuẩn **Online Stream** (tại thời điểm $t$ chỉ dùng điểm dữ liệu hiện tại và trạng thái quá khứ $t-1$, không dùng dữ liệu tương lai $t+1, t+2, \dots$):

#### a. Đối với dữ liệu Quỹ đạo 2D $(x, y)$:
Áp dụng công thức EMA độc lập trên 2 trục tọa độ với cửa sổ dữ liệu trượt 30 điểm:
$$S_{x, t} = \alpha \cdot x_t + (1 - \alpha) \cdot S_{x, t-1}$$

$$S_{y, t} = \alpha \cdot y_t + (1 - \alpha) \cdot S_{y, t-1}$$

với $S_{x, 0} = x_0$, $S_{y, 0} = y_0$ và hệ số làm mượt $\alpha \in \{0.1, 0.3, 0.5, 0.7, 0.9\}$.

#### b. Đối với dữ liệu Góc (Angle Vectorization):
Để tránh góc khi tới biên bị giật, gãy khi xoay qua mốc $\pm 180^\circ$,cần áp dụng phương pháp **Vector hóa lượng giác $(\sin \theta, \cos \theta)$**:
1. Chuyển góc $\theta_t$ thành 2 thành phần lượng giác:
   $$v_{\sin, t} = \sin(\theta_t), \quad v_{\cos, t} = \cos(\theta_t)$$
2. Áp dụng EMA trên từng thành phần vector:
   $$S_{\sin, t} = \alpha \cdot v_{\sin, t} + (1 - \alpha) \cdot S_{\sin, t-1}$$
   $$S_{\cos, t} = \alpha \cdot v_{\cos, t} + (1 - \alpha) \cdot S_{\cos, t-1}$$
3. Khôi phục góc mượt bằng hàm $\text{atan2}$:
   $$\theta_{\text{EMA}, t} = \text{math.degrees}\left(\text{atan2}(S_{\sin, t}, S_{\cos, t})\right)$$

---

### 5.2. File Code & Lệnh chạy

- File code sử dụng :  [`tools/plot_ema_experiments.py`](tools/plot_ema_experiments.py)

```powershell
# Chạy thử nghiệm EMA trực tuyến cho 3 file benchmark (cửa sổ 30 điểm, 3 đoạn cho mỗi file, alphas = 0.1, 0.3, 0.5, 0.7, 0.9)
python tools/plot_ema_experiments.py benchmark/1turn_polynomial_order2_length30.csv --seg-len 30 --num-segs 3 --seed 99
python tools/plot_ema_experiments.py benchmark/2turn_polynomial_order2_length30.csv --seg-len 30 --num-segs 3 --seed 42
python tools/plot_ema_experiments.py benchmark/3turn_polynomial_order2_length30.csv --seg-len 30 --num-segs 3 --seed 123
```

---

### 5.3. Đồ thị So sánh Chi tiết (Cấu trúc tương tự Báo cáo ngày 07/08/2026)

#### a) Leanbot chạy 3 vòng (`3turn`)

![3 turn EMA 2d trajectory](benchmark/3turn_polynomial_order2_length30_ema_2d_trajectory.png)
![3 turn EMA time series](benchmark/3turn_polynomial_order2_length30_ema_time_series.png)

| Segment | Frame ID |
|---|---|
| 1 | 278-307 |
| 2 | 388-417 |
| 3 | 463-492 |

##### Các đoạn Segment 30 điểm ngẫu nhiên (So sánh All Alphas & Phương pháp trước đó):
![3 turn EMA seg 1](benchmark/3turn_polynomial_order2_length30_ema_random_seg1.png)
![3 turn EMA seg 2](benchmark/3turn_polynomial_order2_length30_ema_random_seg2.png)
![3 turn EMA seg 3](benchmark/3turn_polynomial_order2_length30_ema_random_seg3.png)

#### b) Leanbot chạy 2 vòng (`2turn`)

![2 turn EMA 2d trajectory](benchmark/2turn_polynomial_order2_length30_ema_2d_trajectory.png)
![2 turn EMA time series](benchmark/2turn_polynomial_order2_length30_ema_time_series.png)

| Segment | Frame ID |
|---|---|
| 1 | 196-225 |
| 2 | 286-315 |
| 3 | 316-345 |

##### Các đoạn Segment 30 điểm ngẫu nhiên (So sánh All Alphas & Phương pháp trước đó):
![2 turn EMA seg 1](benchmark/2turn_polynomial_order2_length30_ema_random_seg1.png)
![2 turn EMA seg 2](benchmark/2turn_polynomial_order2_length30_ema_random_seg2.png)
![2 turn EMA seg 3](benchmark/2turn_polynomial_order2_length30_ema_random_seg3.png)

#### c) Leanbot chạy 1 vòng (`1turn`)

![1 turn EMA 2d trajectory](benchmark/1turn_polynomial_order2_length30_ema_2d_trajectory.png)
![1 turn EMA time series](benchmark/1turn_polynomial_order2_length30_ema_time_series.png)

| Segment | Frame ID |
|---|---|
| 1 | 137-166 |
| 2 | 182-211 |
| 3 | 367-396 |

##### Các đoạn Segment 30 điểm ngẫu nhiên (So sánh All Alphas & Phương pháp trước đó):
![1 turn EMA seg 1](benchmark/1turn_polynomial_order2_length30_ema_random_seg1.png)
![1 turn EMA seg 2](benchmark/1turn_polynomial_order2_length30_ema_random_seg2.png)
![1 turn EMA seg 3](benchmark/1turn_polynomial_order2_length30_ema_random_seg3.png)

## B. Khó khăn 
- Không 

## C. Công việc tiếp theo
- Chuẩn bị báo cáo thử nghiệm thực tế lên Lab với Thầy.