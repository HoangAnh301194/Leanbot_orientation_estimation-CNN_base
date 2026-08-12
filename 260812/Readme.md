# Báo cáo công việc ngày 12/08/2026

## A. Công việc đã làm 
- Thu thập dữ liệu Leanbot đi các quỹ đạo thẳng, tiến lùi với các góc chéo 0, 45, 90 độ (bổ sung thêm góc -45, 30, 60 độ)
- Vẽ biểu đồ, bổ sung thêm đồ thị làm mượt bằng polynomial bậc 2 và 3. 
- Chỉ vẽ biểu đồ trên các đoạn thẳng không đổi chiều vector vận tốc.
- Vẽ lại biểu đồ, chỉ vẽ EMA của góc tính toán bởi vector tiếp tuyến, chỉ vẽ Polynomial bậc 2 cho quỹ đạo
- Chọn 1 đoạn Leanbot đi trên sa bàn, cắt bớt 2 đầu chưa ổn định.
---

## 1. File Code & Lệnh chạy

- File code sử dụng: [`tools/plot_continuous_poly_segments.py`](tools/plot_continuous_poly_segments.py)

```powershell
# Tạo đồ thị EMA Selective & Polynomial Smooth Bậc 2 (Cửa sổ trượt 18) cho các đoạn di chuyển 1 chiều toàn phần (bỏ 10 frame 2 đầu)
python tools/plot_continuous_poly_segments.py benchmark/
```

---

## 2. Kết quả Biểu đồ Đánh giá theo Các Góc Quỹ đạo (0°, 30°, 45°, 60°, 90°, -45°)

- Leanbot di chuyển tiến lùi 3 lần (tổng cộng 6 lượt di chuyển 1 chiều).
- Để tránh hiện tượng vạch nhảy góc 180° xảy ra khi robot dừng lại và đảo chiều vận tốc (tiến <-> lùi), mỗi đồ thị trích xuất 1 lượt di chuyển 1 chiều đơn lẻ ngang qua sa bàn (~150 điểm).
- Chỉ loại bỏ 10 frame buffer ở đầu và cuối lượt di chuyển khi robot mới gia tốc hoặc chuẩn bị dừng hẳn (giai đoạn chưa ổn định).
- Mượt Polynomial Bậc 2 được tính trên cửa sổ trượt (Sliding Window `SMOOTH_LENGTH = 18`).
- Cả EMA và Polynomial fit chỉ áp dụng cho **Góc tiếp tuyến** (Tangent Angle).

### 2.1. Quỹ đạo 0 độ (`0_degree.csv`)

#### Ảnh thực nghiệm thực tế
![Leanbot 0 degree setup](benchmark/0_degree.png)

#### Biểu đồ Quỹ đạo 2D (Raw vs EMA vs Polynomial Bậc 2 Sliding Window 18) lượt di chuyển 1 chiều toàn phần
![0 degree EMA Selective Trajectory](benchmark/0_degree_ema_selective_2d_trajectory.png)

#### a) Đồ thị góc Raw_angle và các đường EMA của góc tiếp tuyến (Lượt 1 chiều)
![0 degree EMA Selective Time Series](benchmark/0_degree_ema_selective_time_series.png)

#### b) Đồ thị góc Raw_angle và đường làm mượt bằng Polynomial Bậc 2 của góc tiếp tuyến (Sliding Window 18)
![0 degree Poly Smooth Time Series](benchmark/0_degree_poly_smooth_time_series.png)

---

### 2.2. Quỹ đạo 30 độ (`30_degree.csv`)

#### Ảnh thực nghiệm thực tế
![Leanbot 30 degree setup](benchmark/30_degree.png)

#### Biểu đồ Quỹ đạo 2D (Raw vs EMA vs Polynomial Bậc 2 Sliding Window 18) lượt di chuyển 1 chiều toàn phần
![30 degree EMA Selective Trajectory](benchmark/30_degree_ema_selective_2d_trajectory.png)

#### a) Đồ thị góc Raw_angle và các đường EMA của góc tiếp tuyến (Lượt 1 chiều)
![30 degree EMA Selective Time Series](benchmark/30_degree_ema_selective_time_series.png)

#### b) Đồ thị góc Raw_angle và đường làm mượt bằng Polynomial Bậc 2 của góc tiếp tuyến (Sliding Window 18)
![30 degree Poly Smooth Time Series](benchmark/30_degree_poly_smooth_time_series.png)

---

### 2.3. Quỹ đạo 45 độ (`45_degree.csv`)

#### Ảnh thực nghiệm thực tế
![Leanbot 45 degree setup](benchmark/45_degree.png)

#### Biểu đồ Quỹ đạo 2D (Raw vs EMA vs Polynomial Bậc 2 Sliding Window 18) lượt di chuyển 1 chiều toàn phần
![45 degree EMA Selective Trajectory](benchmark/45_degree_ema_selective_2d_trajectory.png)

#### a) Đồ thị góc Raw_angle và các đường EMA của góc tiếp tuyến (Lượt 1 chiều)
![45 degree EMA Selective Time Series](benchmark/45_degree_ema_selective_time_series.png)

#### b) Đồ thị góc Raw_angle và đường làm mượt bằng Polynomial Bậc 2 của góc tiếp tuyến (Sliding Window 18)
![45 degree Poly Smooth Time Series](benchmark/45_degree_poly_smooth_time_series.png)

---

### 2.4. Quỹ đạo 60 độ (`60_degree.csv`)

#### Ảnh thực nghiệm thực tế
![Leanbot 60 degree setup](benchmark/60_degree.png)

#### Biểu đồ Quỹ đạo 2D (Raw vs EMA vs Polynomial Bậc 2 Sliding Window 18) lượt di chuyển 1 chiều toàn phần
![60 degree EMA Selective Trajectory](benchmark/60_degree_ema_selective_2d_trajectory.png)

#### a) Đồ thị góc Raw_angle và các đường EMA của góc tiếp tuyến (Lượt 1 chiều)
![60 degree EMA Selective Time Series](benchmark/60_degree_ema_selective_time_series.png)

#### b) Đồ thị góc Raw_angle và đường làm mượt bằng Polynomial Bậc 2 của góc tiếp tuyến (Sliding Window 18)
![60 degree Poly Smooth Time Series](benchmark/60_degree_poly_smooth_time_series.png)

---

### 2.5. Quỹ đạo 90 độ (`90_degree.csv`)

#### Ảnh thực nghiệm thực tế
![Leanbot 90 degree setup](benchmark/90_degree.png)

#### Biểu đồ Quỹ đạo 2D (Raw vs EMA vs Polynomial Bậc 2 Sliding Window 18) lượt di chuyển 1 chiều toàn phần
![90 degree EMA Selective Trajectory](benchmark/90_degree_ema_selective_2d_trajectory.png)

#### a) Đồ thị góc Raw_angle và các đường EMA của góc tiếp tuyến (Lượt 1 chiều)
![90 degree EMA Selective Time Series](benchmark/90_degree_ema_selective_time_series.png)

#### b) Đồ thị góc Raw_angle và đường làm mượt bằng Polynomial Bậc 2 của góc tiếp tuyến (Sliding Window 18)
![90 degree Poly Smooth Time Series](benchmark/90_degree_poly_smooth_time_series.png)

---

### 2.6. Quỹ đạo -45 độ (`m45_degree.csv`)

#### Ảnh thực nghiệm thực tế
![Leanbot -45 degree setup](benchmark/m45_degree.png)

#### Biểu đồ Quỹ đạo 2D (Raw vs EMA vs Polynomial Bậc 2 Sliding Window 18) lượt di chuyển 1 chiều toàn phần
![m45 degree EMA Selective Trajectory](benchmark/m45_degree_ema_selective_2d_trajectory.png)

#### a) Đồ thị góc Raw_angle và các đường EMA của góc tiếp tuyến (Lượt 1 chiều)
![m45 degree EMA Selective Time Series](benchmark/m45_degree_ema_selective_time_series.png)

#### b) Đồ thị góc Raw_angle và đường làm mượt bằng Polynomial Bậc 2 của góc tiếp tuyến (Sliding Window 18)
![m45 degree Poly Smooth Time Series](benchmark/m45_degree_poly_smooth_time_series.png)

---

> Khi xét riêng từng lượt di chuyển 1 chiều ngẫu nhiên ngang qua sa bàn (không đổi hướng vector), đồ thị góc Raw và đồ thị mượt (EMA & Polynomial Bậc 2 tính trên cửa sổ trượt 18) phẳng và ổn định, triệt tiêu hoàn toàn hiện tượng vạch nhảy bậc thang 180°.

> Phương pháp làm mịn bằng Polynomial Bậc 2 cửa sổ trượt 18 điểm thể hiện khả năng lọc nhiễu tốt hơn so với EMA, theo sát quỹ đạo chuyển động thực tế của robot hơn.

## B. Khó khăn 
- Không

## C. Công việc tiếp theo
- Em xin phép nhận công việc tiếp theo từ Thầy ạ.
