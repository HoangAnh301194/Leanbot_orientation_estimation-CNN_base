# Báo cáo công việc ngày 12/08/2026

## A. Công việc đã làm 
- Thu thập dữ liệu Leanbot đi các quỹ đạo thẳng, tiến lùi với các góc chéo 0, 45, 90 độ (bổ sung thêm góc -45, 30, 60 độ)
- Vẽ biểu đồ, bổ sung thêm đồ thị làm mượt bằng polynomial bậc 2 và 3. 
- Chỉ vẽ biểu đồ trên các đoạn thẳng không đổi chiều vector vận tốc.

---

## 1. File Code & Lệnh chạy

- File code sử dụng: [`tools/plot_continuous_poly_segments.py`](tools/plot_continuous_poly_segments.py)

```powershell
# Tạo đồ thị EMA Selective & Polynomial Smooth (bậc 2, 3) cho các đoạn 30 điểm 1 chiều ngẫu nhiên không đổi hướng
python tools/plot_continuous_poly_segments.py benchmark/0_degree.csv
python tools/plot_continuous_poly_segments.py benchmark/30_degree.csv
python tools/plot_continuous_poly_segments.py benchmark/45_degree.csv
python tools/plot_continuous_poly_segments.py benchmark/60_degree.csv
python tools/plot_continuous_poly_segments.py benchmark/90_degree.csv
python tools/plot_continuous_poly_segments.py benchmark/m45_degree.csv
```

---

## 2. Kết quả Biểu đồ Đánh giá theo Các Góc Quỹ đạo (0°, 30°, 45°, 60°, 90°, -45°)

- Leanbot di chuyển tiến lùi 3 lần (tổng cộng 6 lượt di chuyển 1 chiều)

### 2.1. Quỹ đạo 0 độ (`0_degree.csv`)

#### Ảnh thực nghiệm thực tế
![Leanbot 0 degree setup](benchmark/0_degree.png)

#### Biểu đồ Quỹ đạo 2D (Raw vs EMA 0.5, 0.7, 0.9) zoom 30 điểm ngẫu nhiên không đảo chiều vector vận tốc
![0 degree EMA Selective Trajectory](benchmark/0_degree_ema_selective_2d_trajectory.png)

#### a) Đồ thị góc Raw_angle và các đường EMA từ góc tiếp tuyến 2 điểm đồ thị liên tục 
![0 degree EMA Selective Time Series](benchmark/0_degree_ema_selective_time_series.png)

#### b) Đồ thị góc Raw_angle và các đường làm  mượt bằng polynomial bậc 2, bậc 3. 
![0 degree Poly Smooth Time Series](benchmark/0_degree_poly_smooth_time_series.png)

---

### 2.2. Quỹ đạo 30 độ (`30_degree.csv`)

#### Ảnh thực nghiệm thực tế
![Leanbot 30 degree setup](benchmark/30_degree.png)

#### Biểu đồ Quỹ đạo 2D (Raw vs EMA 0.5, 0.7, 0.9) zoom 30 điểm ngẫu nhiên không đảo chiều vector vận tốc
![30 degree EMA Selective Trajectory](benchmark/30_degree_ema_selective_2d_trajectory.png)

#### a) Đồ thị góc Raw_angle và các đường EMA từ góc tiếp tuyến 2 điểm đồ thị liên tục 
![30 degree EMA Selective Time Series](benchmark/30_degree_ema_selective_time_series.png)

#### b) Đồ thị góc Raw_angle và các đường làm  mượt bằng polynomial bậc 2, bậc 3. 
![30 degree Poly Smooth Time Series](benchmark/30_degree_poly_smooth_time_series.png)

---

### 2.3. Quỹ đạo 45 độ (`45_degree.csv`)

#### Ảnh thực nghiệm thực tế
![Leanbot 45 degree setup](benchmark/45_degree.png)

#### Biểu đồ Quỹ đạo 2D (Raw vs EMA 0.5, 0.7, 0.9) zoom 30 điểm ngẫu nhiên không đảo chiều vector vận tốc
![45 degree EMA Selective Trajectory](benchmark/45_degree_ema_selective_2d_trajectory.png)

#### a) Đồ thị góc Raw_angle và các đường EMA từ góc tiếp tuyến 2 điểm đồ thị liên tục 
![45 degree EMA Selective Time Series](benchmark/45_degree_ema_selective_time_series.png)

#### b) Đồ thị góc Raw_angle và các đường làm  mượt bằng polynomial bậc 2, bậc 3. 
![45 degree Poly Smooth Time Series](benchmark/45_degree_poly_smooth_time_series.png)

---

### 2.4. Quỹ đạo 60 độ (`60_degree.csv`)

#### Ảnh thực nghiệm thực tế
![Leanbot 60 degree setup](benchmark/60_degree.png)

#### Biểu đồ Quỹ đạo 2D (Raw vs EMA 0.5, 0.7, 0.9) zoom 30 điểm ngẫu nhiên không đảo chiều vector vận tốc
![60 degree EMA Selective Trajectory](benchmark/60_degree_ema_selective_2d_trajectory.png)

#### a) Đồ thị góc Raw_angle và các đường EMA từ góc tiếp tuyến 2 điểm đồ thị liên tục 
![60 degree EMA Selective Time Series](benchmark/60_degree_ema_selective_time_series.png)

#### b) Đồ thị góc Raw_angle và các đường làm  mượt bằng polynomial bậc 2, bậc 3. 
![60 degree Poly Smooth Time Series](benchmark/60_degree_poly_smooth_time_series.png)

---

### 2.5. Quỹ đạo 90 độ (`90_degree.csv`)

#### Ảnh thực nghiệm thực tế
![Leanbot 90 degree setup](benchmark/90_degree.png)

#### Biểu đồ Quỹ đạo 2D (Raw vs EMA 0.5, 0.7, 0.9) zoom 30 điểm ngẫu nhiên không đảo chiều vector vận tốc
![90 degree EMA Selective Trajectory](benchmark/90_degree_ema_selective_2d_trajectory.png)

#### a) Đồ thị góc Raw_angle và các đường EMA từ góc tiếp tuyến 2 điểm đồ thị liên tục 
![90 degree EMA Selective Time Series](benchmark/90_degree_ema_selective_time_series.png)

#### b) Đồ thị góc Raw_angle và các đường làm  mượt bằng polynomial bậc 2, bậc 3. 
![90 degree Poly Smooth Time Series](benchmark/90_degree_poly_smooth_time_series.png)

---

### 2.6. Quỹ đạo -45 độ (`m45_degree.csv`)

#### Ảnh thực nghiệm thực tế
![Leanbot -45 degree setup](benchmark/m45_degree.png)

#### Biểu đồ Quỹ đạo 2D (Raw vs EMA 0.5, 0.7, 0.9) zoom 30 điểm ngẫu nhiên không đảo chiều vector vận tốc
![m45 degree EMA Selective Trajectory](benchmark/m45_degree_ema_selective_2d_trajectory.png)

#### a) Đồ thị góc Raw_angle và các đường EMA từ góc tiếp tuyến 2 điểm đồ thị liên tục 
![m45 degree EMA Selective Time Series](benchmark/m45_degree_ema_selective_time_series.png)

#### b) Đồ thị góc Raw_angle và các đường làm  mượt bằng polynomial bậc 2, bậc 3. 
![m45 degree Poly Smooth Time Series](benchmark/m45_degree_poly_smooth_time_series.png)

---

> Khi xét riêng từng đoạn di chuyển 1 chiều ngẫu nhiên (không đổi hướng vector), đồ thị góc Raw và đồ thị mượt (EMA & Polynomial bậc 2, 3) phẳng và ổn định, triệt tiêu hoàn toàn hiện tượng vạch nhảy bậc thang 180°.

> Phương pháp làm mịn bằng Polynomial (bậc 2 & bậc 3) thể hiện khả năng lọc nhiễu tốt hơn so với EMA, theo sát quỹ đạo chuyển động thực tế của robot hơn . 

## B. Khó khăn 
- Vì hiện tại nhiều dạng dữ liệu có thể làm mượt như : quỹ đạo, góc tính từ vector tiếp tuyến, góc từ Model, nên khi Thầy yêu cầu `Vẽ cả cách làm mịn với polynomial`  mà không nói rõ là làm mịn loại dữ liệu nào nên em làm với cả quỹ đạo và góc ạ. 

## C. Công việc tiếp theo
- Em xin phép nhận công việc tiếp theo từ Thầy ạ.

