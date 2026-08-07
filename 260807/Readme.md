# Báo cáo công việc ngày 07/08/2026

## A. Công việc đã làm 

- Bổ sung polynomial smooth bậc 2, cửa sổ trượt 30 điểm cho hai chuỗi angle:
  - `raw_angle` -> `raw_angle_smooth`
  - `smooth_angle` -> `smooth_angle_smooth`
- Cập nhật biểu đồ để so sánh đồng thời bốn đường: Raw Angle, Smooth Angle, Raw Angle Smooth, Smooth Angle Smooth.
- Chọn 5 đoạn ngẫu nhiên, mỗi đoạn 30 điểm từ log csv thử nghiệm Leanbot chạy 1 vòng và 3 vòng.
- **Thử nghiệm nâng cao mới (Theo chỉ đạo từ Thầy Quang Định):**
  - Thử nghiệm các mức cửa sổ trượt `SMOOTH_LENGTH` giảm từ `30` xuống **`24`** và **`18`** điểm.
  - Thực hiện thuật toán **làm mịn vị trí 2 lần (Double Position Smoothing)**: $(raw\_x, raw\_y) \rightarrow (smooth\_x, smooth\_y) \rightarrow (smooth\_x2, smooth\_y2)$.
  - Trích xuất góc tiếp tuyến từ tọa độ mượt 2 lần `smooth_angle2` và làm mượt tiếp thành `smooth_angle2_smooth`.

---

## 1. File Code sử dụng

- [`tools/roi_tracking_online_poly_smooth.py`](tools/roi_tracking_online_poly_smooth.py): ROI tracking online; ghi `raw_angle`, `raw_angle_smooth`, `smooth_angle`, `smooth_angle_smooth` vào log mới.
- [`tools/postprocess_angle_poly_smooth.py`](tools/postprocess_angle_poly_smooth.py): Tái xử lý CSV cũ, thêm bốn cột angle mà không cần inference lại.
- [`tools/plot_online_poly_log.py`](tools/plot_online_poly_log.py): Vẽ quỹ đạo 2D, chuỗi thời gian bốn angle, X/Y và FPS.
- [`tools/plot_random_5segments.py`](tools/plot_random_5segments.py): Vẽ quỹ đạo và bốn angle cho các segment 30 điểm ngẫu nhiên.

---

## 2. Các bước thực hiện

### Step 1: Xác định bốn chuỗi angle

| Chuỗi | Nguồn |
|---|---|
| `raw_angle` | Hướng Leanbot gốc khi chạy inference. |
| `raw_angle_smooth` | Polynomial smooth của `raw_angle`. |
| `smooth_angle` | Góc tiếp tuyến từ hai điểm `(smooth_x, smooth_y)` liên tiếp. |
| `smooth_angle_smooth` | Polynomial smooth của `smooth_angle`. |

### Step 2: Nguyên lý & Quy trình Polynomial Fit

1. **Cửa sổ trượt dữ liệu góc, tọa độ (Sliding Window):**
   - Duy trì bộ đệm chứa 30 điểm dữ liệu gần nhất (`SMOOTH_LENGTH = 30`). 
   - Với 29 điểm đầu tiên (giai đoạn warm-up chưa đủ 30 điểm), giá trị mượt được giữ bằng giá trị gốc.

2. **Chuẩn hóa trục thời gian $t \in [0.0, 1.0]$:**
   - Tạo trục thời gian chuẩn hóa $t = \text{np.linspace}(0.0, 1.0, 30)$ cho 30 điểm trong cửa sổ.
   - Việc chuẩn hóa giúp ổn định số học khi tính toán ma trận bình phương tối thiểu, tránh hiện tượng nhiễu ma trận (ill-conditioned) khi chỉ số Frame ID tăng lớn.

3. **Mô hình Đa thức bậc 2 (Degree-2 Polynomial Fit):**
   - Khớp đa thức bậc 2 (`SMOOTH_ORDER = 2`) có dạng:
     $$f(t) = a \cdot t^2 + b \cdot t + c$$
   - Các hệ số $(a, b, c)$ được tìm bằng phương pháp Bình phương tối thiểu (Ordinary Least Squares - `np.polyfit`), sao cho tổng bình phương sai số giữa dữ liệu đo và đường cong đa thức đạt tối thiểu:
     $$\min_{a,b,c} \sum_{i=1}^{30} \left( f(t_i) - y_i \right)^2$$

4. **Tính giá trị mượt tại thời điểm hiện tại ($t = 1.0$):**
   - Giá trị mượt của frame hiện tại chính là giá trị của đa thức tại mốc thời gian mới nhất $t = 1.0$:
     $$y_{\text{smooth}} = f(1.0) = a + b + c$$
   - Phương pháp này giúp mô hình đáp ứng realtime (online tracking) trực tiếp tại thời điểm hiện tại mà không bị độ trễ pha (phase lag).

5. **Xử lý đặc thù cho dữ liệu Góc (Angle):**
   - **Khử đứt gãy biên $\pm 180^\circ$ (Unwrapping):** Trước khi fit đa thức cho chuỗi góc, áp dụng `np.unwrap` trên radian để loại bỏ nét đứt gãy đột ngột tại biên $-180^\circ / +180^\circ$.
   - **Tính góc tiếp tuyến quỹ đạo (`smooth_angle`):** Dựa trên tọa độ đã làm mượt $(smooth\_x, smooth\_y)$, góc vận tốc chuyển động được tính theo hệ tọa độ OpenCV (trục Y hướng xuống):
     ```python
     dx = sx - prev_sx
     dy = sy - prev_sy
     smooth_angle = math.degrees(math.atan2(-dy, dx))
     ```
   - Sau đó tiếp tục áp dụng Polynomial Fit bậc 2 cho chuỗi `smooth_angle` để thu được `smooth_angle_smooth`.

## 3. Lệnh chạy

### Chạy online tracking

```powershell
python tools/roi_tracking_online_poly_smooth.py --source 1 --log 1turn.csv
python tools/roi_tracking_online_poly_smooth.py --source 1 --log 2turn.csv
python tools/roi_tracking_online_poly_smooth.py --source 1 --log 3turn.csv
```

### Xử lí dữ liệu sau khi đã có file log csv inference 

```powershell
python tools/postprocess_angle_poly_smooth.py benchmark/1turn.csv benchmark/2turn.csv benchmark/3turn.csv
```

### Vẽ biểu đồ tổng hợp

```powershell
python tools/plot_online_poly_log.py benchmark/1turn_polynomial_order2_length30.csv --segments 3 --degree 2
python tools/plot_online_poly_log.py benchmark/2turn_polynomial_order2_length30.csv --segments 3 --degree 2
python tools/plot_online_poly_log.py benchmark/3turn_polynomial_order2_length30.csv --segments 3 --degree 2
```

### Vẽ năm segment ngẫu nhiên

```powershell
python tools/plot_random_5segments.py benchmark/1turn_polynomial_order2_length30.csv --num 5 --seed 99
python tools/plot_random_5segments.py benchmark/2turn_polynomial_order2_length30.csv --num 5 --seed 42
python tools/plot_random_5segments.py benchmark/3turn_polynomial_order2_length30.csv --num 5 --seed 123
```

---

## 4. Kết quả Inference & Đồ thị chi tiết

## Dữ liệu đã sử dụng

| Thí nghiệm | CSV gốc | Số frame | Frame ID | Tracking lost | CSV bốn angle |
|---|---|---:|---|---:|---|
| Leanbot chạy 3 vòng | [`benchmark/3turn.csv`](benchmark/3turn.csv) | 973 | 258-1230 | 0 | [`benchmark/3turn_polynomial_order2_length30.csv`](benchmark/3turn_polynomial_order2_length30.csv) |
| Leanbot chạy 2 vòng | [`benchmark/2turn.csv`](benchmark/2turn.csv) | 646 | 106-751 | 0 | [`benchmark/2turn_polynomial_order2_length30.csv`](benchmark/2turn_polynomial_order2_length30.csv) |
| Leanbot chạy 1 vòng | [`benchmark/1turn.csv`](benchmark/1turn.csv) | 332 | 102-433 | 0 | [`benchmark/1turn_polynomial_order2_length30.csv`](benchmark/1turn_polynomial_order2_length30.csv) |


### Leanbot chạy 3 vòng

![3 turn trajectory](benchmark/3turn_polynomial_order2_length30_2d_trajectory.png)

![3 turn four angles](benchmark/3turn_polynomial_order2_length30_time_series.png)

| Segment | Frame ID |
|---|---|
| 1 | 278-307 |
| 2 | 388-417 |
| 3 | 463-492 |
| 4 | 643-672 |
| 5 | 1058-1087 |

![3 turn random segment 1](benchmark/3turn_polynomial_order2_length30_random_seg1.png)
![3 turn random segment 2](benchmark/3turn_polynomial_order2_length30_random_seg2.png)
![3 turn random segment 3](benchmark/3turn_polynomial_order2_length30_random_seg3.png)
![3 turn random segment 4](benchmark/3turn_polynomial_order2_length30_random_seg4.png)
![3 turn random segment 5](benchmark/3turn_polynomial_order2_length30_random_seg5.png)

### Leanbot chạy 2 vòng

![2 turn trajectory](benchmark/2turn_polynomial_order2_length30_2d_trajectory.png)

![2 turn four angles](benchmark/2turn_polynomial_order2_length30_time_series.png)

| Segment | Frame ID |
|---|---|
| 1 | 196-225 |
| 2 | 286-315 |
| 3 | 316-345 |
| 4 | 371-400 |
| 5 | 486-515 |

![2 turn random segment 1](benchmark/2turn_polynomial_order2_length30_random_seg1.png)
![2 turn random segment 2](benchmark/2turn_polynomial_order2_length30_random_seg2.png)
![2 turn random segment 3](benchmark/2turn_polynomial_order2_length30_random_seg3.png)
![2 turn random segment 4](benchmark/2turn_polynomial_order2_length30_random_seg4.png)
![2 turn random segment 5](benchmark/2turn_polynomial_order2_length30_random_seg5.png)

### Leanbot chạy 1 vòng

![1 turn trajectory](benchmark/1turn_polynomial_order2_length30_2d_trajectory.png)

![1 turn four angles](benchmark/1turn_polynomial_order2_length30_time_series.png)

| Segment | Frame ID |
|---|---|
| 1 | 137-166 |
| 2 | 182-211 |
| 3 | 222-251 |
| 4 | 257-286 |
| 5 | 367-396 |

![1 turn random segment 1](benchmark/1turn_polynomial_order2_length30_random_seg1.png)
![1 turn random segment 2](benchmark/1turn_polynomial_order2_length30_random_seg2.png)
![1 turn random segment 3](benchmark/1turn_polynomial_order2_length30_random_seg3.png)
![1 turn random segment 4](benchmark/1turn_polynomial_order2_length30_random_seg4.png)
![1 turn random segment 5](benchmark/1turn_polynomial_order2_length30_random_seg5.png)



###

---

## 5. Thử giảm kích thước cửa sổ trượt từ 30 xuống 24, 18 điểm , vẽ biểu đồ đánh giá. 

### 5.1. Các bước thực hiện `Double Position Smoothing` & `smooth_angle2`

1. **Làm mịn vị trí Lần 1:**
   $$(raw\_x, raw\_y) \xrightarrow{\text{Poly fit deg=2}} (smooth\_x, smooth\_y)$$
2. **Làm mịn vị trí Lần 2 (Double Smooth):**
   $$(smooth\_x, smooth\_y) \xrightarrow{\text{Poly fit deg=2}} (smooth\_x2, smooth\_y2)$$
3. **Tính góc tiếp tuyến từ vị trí mượt 2 lần:**
   $$\Delta x_2 = smooth\_x2_t - smooth\_x2_{t-1}, \quad \Delta y_2 = smooth\_y2_t - smooth\_y2_{t-1}$$
   $$smooth\_angle2 = \text{math.degrees}\left(\text{math.atan2}(-\Delta y_2, \Delta x_2)\right)$$
4. **Làm mịn góc tiếp tuyến 2 lần:**
   $$smooth\_angle2 \xrightarrow{\text{Poly fit deg=2}} smooth\_angle2\_smooth$$

### 5.2. Lệnh chạy 

#### a) Thử nghiệm với Cửa sổ trượt Length = 30 (Có Double Position Smoothing)

* **Bước 1: Hậu xử lý CSV (Double Position Smoothing & Window Length = 30)**
```powershell
python tools/postprocess_angle_poly_smooth.py benchmark/3turn.csv benchmark/2turn.csv benchmark/1turn.csv --window 30 --suffix _polynomial_order2_length30.csv
```

* **Bước 2: Vẽ đồ thị tổng hợp cho Length = 30**
```powershell
python tools/plot_online_poly_log.py benchmark/3turn_polynomial_order2_length30.csv --degree 2
python tools/plot_online_poly_log.py benchmark/2turn_polynomial_order2_length30.csv --degree 2
python tools/plot_online_poly_log.py benchmark/1turn_polynomial_order2_length30.csv --degree 2
```

* **Bước 3: Trích xuất 5 segment ngẫu nhiên cho Length = 30**
```powershell
python tools/plot_random_5segments.py benchmark/3turn_polynomial_order2_length30.csv --num 5 --seed 123
python tools/plot_random_5segments.py benchmark/2turn_polynomial_order2_length30.csv --num 5 --seed 42
python tools/plot_random_5segments.py benchmark/1turn_polynomial_order2_length30.csv --num 5 --seed 99
```

#### b) Thử nghiệm với Cửa sổ trượt Length = 24

* **Bước 1: Hậu xử lý CSV (Double Position Smoothing & Window Length = 24)**
```powershell
python tools/postprocess_angle_poly_smooth.py benchmark/3turn.csv benchmark/2turn.csv benchmark/1turn.csv --window 24 --suffix _polynomial_order2_length24.csv
```

* **Bước 2: Vẽ đồ thị tổng hợp cho Length = 24**
```powershell
python tools/plot_online_poly_log.py benchmark/3turn_polynomial_order2_length24.csv --degree 2
python tools/plot_online_poly_log.py benchmark/2turn_polynomial_order2_length24.csv --degree 2
python tools/plot_online_poly_log.py benchmark/1turn_polynomial_order2_length24.csv --degree 2
```

* **Bước 3: Trích xuất 5 segment ngẫu nhiên cho Length = 24**
```powershell
python tools/plot_random_5segments.py benchmark/3turn_polynomial_order2_length24.csv --num 5 --seed 123
python tools/plot_random_5segments.py benchmark/2turn_polynomial_order2_length24.csv --num 5 --seed 42
python tools/plot_random_5segments.py benchmark/1turn_polynomial_order2_length24.csv --num 5 --seed 99
```

#### c) Thử nghiệm với Cửa sổ trượt Length = 18

* **Bước 1: Hậu xử lý CSV (Double Position Smoothing & Window Length = 18)**
```powershell
python tools/postprocess_angle_poly_smooth.py benchmark/3turn.csv benchmark/2turn.csv benchmark/1turn.csv --window 18 --suffix _polynomial_order2_length18.csv
```

* **Bước 2: Vẽ đồ thị tổng hợp cho Length = 18**
```powershell
python tools/plot_online_poly_log.py benchmark/3turn_polynomial_order2_length18.csv --degree 2
python tools/plot_online_poly_log.py benchmark/2turn_polynomial_order2_length18.csv --degree 2
python tools/plot_online_poly_log.py benchmark/1turn_polynomial_order2_length18.csv --degree 2
```

* **Bước 3: Trích xuất 5 segment ngẫu nhiên cho Length = 18**
```powershell
python tools/plot_random_5segments.py benchmark/3turn_polynomial_order2_length18.csv --num 5 --seed 123
python tools/plot_random_5segments.py benchmark/2turn_polynomial_order2_length18.csv --num 5 --seed 42
python tools/plot_random_5segments.py benchmark/1turn_polynomial_order2_length18.csv --num 5 --seed 99
```

### 5.3. Kết quả so sánh các mức Cửa sổ trượt (30 vs 24 vs 18) & Double Smoothing

#### a) Thử nghiệm với Cửa sổ trượt Length = 30 (Double Position Smoothing & Đồ thị 5 đường Angle)

##### Leanbot chạy 3 vòng (Length = 30)

![3 turn trajectory length 30](benchmark/3turn_polynomial_order2_length30_2d_trajectory.png)
![3 turn five angles length 30](benchmark/3turn_polynomial_order2_length30_time_series.png)

![3 turn len30 seg1](benchmark/3turn_polynomial_order2_length30_random_seg1.png)
![3 turn len30 seg2](benchmark/3turn_polynomial_order2_length30_random_seg2.png)
![3 turn len30 seg3](benchmark/3turn_polynomial_order2_length30_random_seg3.png)
![3 turn len30 seg4](benchmark/3turn_polynomial_order2_length30_random_seg4.png)
![3 turn len30 seg5](benchmark/3turn_polynomial_order2_length30_random_seg5.png)

##### Leanbot chạy 2 vòng (Length = 30)

![2 turn trajectory length 30](benchmark/2turn_polynomial_order2_length30_2d_trajectory.png)
![2 turn five angles length 30](benchmark/2turn_polynomial_order2_length30_time_series.png)

![2 turn len30 seg1](benchmark/2turn_polynomial_order2_length30_random_seg1.png)
![2 turn len30 seg2](benchmark/2turn_polynomial_order2_length30_random_seg2.png)
![2 turn len30 seg3](benchmark/2turn_polynomial_order2_length30_random_seg3.png)
![2 turn len30 seg4](benchmark/2turn_polynomial_order2_length30_random_seg4.png)
![2 turn len30 seg5](benchmark/2turn_polynomial_order2_length30_random_seg5.png)

##### Leanbot chạy 1 vòng (Length = 30)

![1 turn trajectory length 30](benchmark/1turn_polynomial_order2_length30_2d_trajectory.png)
![1 turn five angles length 30](benchmark/1turn_polynomial_order2_length30_time_series.png)

![1 turn len30 seg1](benchmark/1turn_polynomial_order2_length30_random_seg1.png)
![1 turn len30 seg2](benchmark/1turn_polynomial_order2_length30_random_seg2.png)
![1 turn len30 seg3](benchmark/1turn_polynomial_order2_length30_random_seg3.png)
![1 turn len30 seg4](benchmark/1turn_polynomial_order2_length30_random_seg4.png)
![1 turn len30 seg5](benchmark/1turn_polynomial_order2_length30_random_seg5.png)

#### b) Thử nghiệm với Cửa sổ trượt Length = 24 (Double Position Smoothing & Đồ thị 5 đường Angle)

##### Leanbot chạy 3 vòng (Length = 24)

![3 turn trajectory length 24](benchmark/3turn_polynomial_order2_length24_2d_trajectory.png)
![3 turn five angles length 24](benchmark/3turn_polynomial_order2_length24_time_series.png)

![3 turn len24 seg1](benchmark/3turn_polynomial_order2_length24_random_seg1.png)
![3 turn len24 seg2](benchmark/3turn_polynomial_order2_length24_random_seg2.png)
![3 turn len24 seg3](benchmark/3turn_polynomial_order2_length24_random_seg3.png)
![3 turn len24 seg4](benchmark/3turn_polynomial_order2_length24_random_seg4.png)
![3 turn len24 seg5](benchmark/3turn_polynomial_order2_length24_random_seg5.png)

##### Leanbot chạy 2 vòng (Length = 24)

![2 turn trajectory length 24](benchmark/2turn_polynomial_order2_length24_2d_trajectory.png)
![2 turn five angles length 24](benchmark/2turn_polynomial_order2_length24_time_series.png)

![2 turn len24 seg1](benchmark/2turn_polynomial_order2_length24_random_seg1.png)
![2 turn len24 seg2](benchmark/2turn_polynomial_order2_length24_random_seg2.png)
![2 turn len24 seg3](benchmark/2turn_polynomial_order2_length24_random_seg3.png)
![2 turn len24 seg4](benchmark/2turn_polynomial_order2_length24_random_seg4.png)
![2 turn len24 seg5](benchmark/2turn_polynomial_order2_length24_random_seg5.png)

##### Leanbot chạy 1 vòng (Length = 24)

![1 turn trajectory length 24](benchmark/1turn_polynomial_order2_length24_2d_trajectory.png)
![1 turn five angles length 24](benchmark/1turn_polynomial_order2_length24_time_series.png)

![1 turn len24 seg1](benchmark/1turn_polynomial_order2_length24_random_seg1.png)
![1 turn len24 seg2](benchmark/1turn_polynomial_order2_length24_random_seg2.png)
![1 turn len24 seg3](benchmark/1turn_polynomial_order2_length24_random_seg3.png)
![1 turn len24 seg4](benchmark/1turn_polynomial_order2_length24_random_seg4.png)
![1 turn len24 seg5](benchmark/1turn_polynomial_order2_length24_random_seg5.png)

#### c) Thử nghiệm với Cửa sổ trượt Length = 18 (Double Position Smoothing & Đồ thị 5 đường Angle)

##### Leanbot chạy 3 vòng (Length = 18)

![3 turn trajectory length 18](benchmark/3turn_polynomial_order2_length18_2d_trajectory.png)
![3 turn five angles length 18](benchmark/3turn_polynomial_order2_length18_time_series.png)

![3 turn len18 seg1](benchmark/3turn_polynomial_order2_length18_random_seg1.png)
![3 turn len18 seg2](benchmark/3turn_polynomial_order2_length18_random_seg2.png)
![3 turn len18 seg3](benchmark/3turn_polynomial_order2_length18_random_seg3.png)
![3 turn len18 seg4](benchmark/3turn_polynomial_order2_length18_random_seg4.png)
![3 turn len18 seg5](benchmark/3turn_polynomial_order2_length18_random_seg5.png)

##### Leanbot chạy 2 vòng (Length = 18)

![2 turn trajectory length 18](benchmark/2turn_polynomial_order2_length18_2d_trajectory.png)
![2 turn five angles length 18](benchmark/2turn_polynomial_order2_length18_time_series.png)

![2 turn len18 seg1](benchmark/2turn_polynomial_order2_length18_random_seg1.png)
![2 turn len18 seg2](benchmark/2turn_polynomial_order2_length18_random_seg2.png)
![2 turn len18 seg3](benchmark/2turn_polynomial_order2_length18_random_seg3.png)
![2 turn len18 seg4](benchmark/2turn_polynomial_order2_length18_random_seg4.png)
![2 turn len18 seg5](benchmark/2turn_polynomial_order2_length18_random_seg5.png)

##### Leanbot chạy 1 vòng (Length = 18)

![1 turn trajectory length 18](benchmark/1turn_polynomial_order2_length18_2d_trajectory.png)
![1 turn five angles length 18](benchmark/1turn_polynomial_order2_length18_time_series.png)

![1 turn len18 seg1](benchmark/1turn_polynomial_order2_length18_random_seg1.png)
![1 turn len18 seg2](benchmark/1turn_polynomial_order2_length18_random_seg2.png)
![1 turn len18 seg3](benchmark/1turn_polynomial_order2_length18_random_seg3.png)
![1 turn len18 seg4](benchmark/1turn_polynomial_order2_length18_random_seg4.png)
![1 turn len18 seg5](benchmark/1turn_polynomial_order2_length18_random_seg5.png)

### 5.4. Đánh giá & Nhận xét so sánh

1. **Ảnh hưởng của chiều dài cửa sổ trượt (`SMOOTH_LENGTH` = 30 vs 24 vs 18):**
   - Khi giảm `SMOOTH_LENGTH` xuống 24 và 18 điểm, đường mượt phản ứng nhanh hơn với các biến đổi góc đột ngột ở khúc cua (giảm trễ pha).
   - Độ mượt ở length = 24 đạt sự cân bằng tốt giữa tính mượt mà và khả năng đáp ứng nhanh ở các khúc ngoặt.

2. **Hiệu quả của việc làm mịn vị trí 2 lần (Double Position Smoothing):**
   - Đường `smooth_angle2_smooth` thu được từ vị trí mượt 2 lần $(smooth\_x2, smooth\_y2)$ triệt tiêu thêm các biến động răng cưa nhỏ còn sót lại của bước làm mượt 1 lần.
   - Quỹ đạo $smooth\_x2, smooth\_y2$ liên tục và mịn hơn rõ rệt trên biểu đồ 2D.



## B. Khó khăn 
- Em thưa Thầy. Việc làm mượt dữ liệu này thì đạt kết quả như thế nào thì mới có thể chấp nhận được và chuyển sang bước tiếp theo ạ ? 
- Hiện tại em vẫn chưa rõ mục tiêu cần thực hiện là smooth dữ liệu góc, hay smooth quỹ đạo chuyển động ạ ? nếu chỉ để giảm nhiễu , spike đột ngột thì em nghĩ EMA cũng có thể đáp ứng được rồi ạ . 
## C. Công việc tiếp theo 
- Em sẽ tìm hiểu thêm các phương pháp khác trong bài toán làm mượt dữ liệu ạ .
- Em xin phép nhận công việc tiếp theo từ Thầy để em thực hiện và báo cáo vào buổi lên Lab ngày mai ạ .