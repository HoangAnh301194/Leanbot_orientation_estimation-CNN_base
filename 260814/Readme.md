# Báo cáo công việc ngày 14/08/2026

## A. Công việc đã làm
- Tính Góc tiếp tuyến của quỹ đạo (Không dùng góc từ hai điểm đã làm mượt liên tiếp)
    - Không cần Quy đổi đạo hàm sang thời gian thực
    - Chưa cần thử Dạng convolution và tối ưu khi chạy realtime
- Vẽ đồ thị so sánh, các đường đồ thị cần vẽ :
    - tiếp tuyến của quỹ đạo
    - góc từ hai điểm đã làm mượt liên tiếp
    - Raw angle (Model)
- Polyfit lần 2 để tính Endpoint Tangent Angle (Smooth2 tangent angle)
- Thực nghiệm so sánh khi thay đổi độ dài cửa sổ trượt Sliding Windows W = 18 -> 15 -> 12
- Ước lượng vận tốc (Estimated Speed = sqrt(dx^2 + dy^2)) trên toàn bộ chu trình 6 lần chạy tiến - lùi

### 1. Thử nghiệm tính góc tiếp tuyến trực tiếp từ đa thức cục bộ

- Tiếp tục sử dụng **Causal Sliding Window** gồm `N = 18` mẫu từ quá khứ đến hiện tại.
- Chuẩn hóa trục thời gian của mỗi cửa sổ về $t \in [-1,0]$.
- Fit riêng hai đa thức bậc hai $x(t)$ và $y(t)$ bằng Least Squares.
- Xác định hướng tiếp tuyến của hai đa thức tại endpoint $t=0$ để tính góc quỹ đạo.
- Không sử dụng góc tạo bởi hai điểm đã làm mượt liên tiếp làm kết quả chính.
- Sử dụng `np.polyfit()`, `np.polyder()` và `np.polyval()` fit đa thức
- Vẽ thêm biểu đồ quỹ đạo 2D để so sánh quỹ đạo raw và quỹ đạo từ các điểm endpoint sau khi fit Least Squares.

- Code sử dụng: [`plot_poly_tangent_angle_comparison.py`](tools/plot_poly_tangent_angle_comparison.py)

- Lệnh chạy:

  Chạy toàn bộ các file CSV trong thư mục `benchmark`:

  ```powershell
  cd 260814
  python tools/plot_poly_tangent_angle_comparison.py benchmark --window-size 18 --poly-degree 2 --seed 42
  ```

  Chạy riêng một file CSV:

  ```powershell
  cd 260814
  python tools/plot_poly_tangent_angle_comparison.py benchmark/45_degree.csv --window-size 18 --poly-degree 2 --seed 42
  ```

  Ảnh kết quả được lưu trong thư mục: `benchmark/poly_tangent_comparison/`

### 2. Biểu đồ kết quả

#### 2.1. Quỹ đạo 0 độ (`0_degree.csv`)

##### a) Biểu đồ quỹ đạo 2D (Raw vs Fit Polynomial Least Squares Bậc 2)
![0 degree 2D Trajectory](benchmark/poly_tangent_comparison/0_degree_poly_least_squares_2d_trajectory.png)

##### b) Đồ thị so sánh góc (Raw Model vs Fit Polynomial Tangent vs Hai điểm làm mượt liên tiếp)
![0 degree Tangent Angle Comparison](benchmark/poly_tangent_comparison/0_degree_poly_tangent_angle_comparison_3lines.png)

---

#### 2.2. Quỹ đạo 30 độ (`30_degree.csv`)

##### a) Biểu đồ quỹ đạo 2D (Raw vs Fit Polynomial Least Squares Bậc 2)
![30 degree 2D Trajectory](benchmark/poly_tangent_comparison/30_degree_poly_least_squares_2d_trajectory.png)

##### b) Đồ thị so sánh góc (Raw Model vs Fit Polynomial Tangent vs Hai điểm làm mượt liên tiếp)
![30 degree Tangent Angle Comparison](benchmark/poly_tangent_comparison/30_degree_poly_tangent_angle_comparison_3lines.png)

---

#### 2.3. Quỹ đạo 45 độ (`45_degree.csv`)

##### a) Biểu đồ quỹ đạo 2D (Raw vs Fit Polynomial Least Squares Bậc 2)
![45 degree 2D Trajectory](benchmark/poly_tangent_comparison/45_degree_poly_least_squares_2d_trajectory.png)

##### b) Đồ thị so sánh góc (Raw Model vs Fit Polynomial Tangent vs Hai điểm làm mượt liên tiếp)
![45 degree Tangent Angle Comparison](benchmark/poly_tangent_comparison/45_degree_poly_tangent_angle_comparison_3lines.png)

---

#### 2.4. Quỹ đạo 60 độ (`60_degree.csv`)

##### a) Biểu đồ quỹ đạo 2D (Raw vs  Fit Polynomial Least Squares Bậc 2)
![60 degree 2D Trajectory](benchmark/poly_tangent_comparison/60_degree_poly_least_squares_2d_trajectory.png)

##### b) Đồ thị so sánh góc (Raw Model vs Fit Polynomial Tangent vs Hai điểm làm mượt liên tiếp)
![60 degree Tangent Angle Comparison](benchmark/poly_tangent_comparison/60_degree_poly_tangent_angle_comparison_3lines.png)

---

#### 2.5. Quỹ đạo 90 độ (`90_degree.csv`)

##### a) Biểu đồ quỹ đạo 2D (Raw vs Fit Polynomial Least Squares Bậc 2)
![90 degree 2D Trajectory](benchmark/poly_tangent_comparison/90_degree_poly_least_squares_2d_trajectory.png)

##### b) Đồ thị so sánh góc (Raw Model vs Fit Polynomial Tangent vs Hai điểm làm mượt liên tiếp)
![90 degree Tangent Angle Comparison](benchmark/poly_tangent_comparison/90_degree_poly_tangent_angle_comparison_3lines.png)

---

#### 2.6. Quỹ đạo -45 độ (`m45_degree.csv`)

##### a) Biểu đồ quỹ đạo 2D (Raw vs Fit Polynomial Least Squares Bậc 2)
![m45 degree 2D Trajectory](benchmark/poly_tangent_comparison/m45_degree_poly_least_squares_2d_trajectory.png)

##### b) Đồ thị so sánh góc (Raw Model vs Fit Polynomial Tangent vs Hai điểm làm mượt liên tiếp)
![m45 degree Tangent Angle Comparison](benchmark/poly_tangent_comparison/m45_degree_poly_tangent_angle_comparison_3lines.png)


### 3. Polyfit lần 2 để tính Endpoint Tangent Angle (Smooth2 tangent angle)
- **Code sử dụng**: [`plot_poly_tangent_angle_comparison.py`](tools/plot_poly_tangent_angle_comparison.py)
- **Lệnh chạy**:
  ```powershell
  cd 260814
  python tools/plot_poly_tangent_angle_comparison.py benchmark --window-size 18 --poly-degree 2 --seed 42
  ```
- **Đồ thị so sánh 4 đường** (`Raw Model`, `Consecutive smoothed Point`, `Endpoint Tangent`, `Endpoint Tangent Smooth2` với cửa sổ $W = 18$):

#### 3.1. Góc 0 độ (`0_degree.csv`)
![0 degree 4 angles comparison W18](benchmark/poly_tangent_comparison/0_degree_poly_tangent_angle_comparison_w18.png)

#### 3.2. Góc 30 độ (`30_degree.csv`)
![30 degree 4 angles comparison W18](benchmark/poly_tangent_comparison/30_degree_poly_tangent_angle_comparison_w18.png)

#### 3.3. Góc 45 độ (`45_degree.csv`)
![45 degree 4 angles comparison W18](benchmark/poly_tangent_comparison/45_degree_poly_tangent_angle_comparison_w18.png)

#### 3.4. Góc -45 độ (`m45_degree.csv`)
![m45 degree 4 angles comparison W18](benchmark/poly_tangent_comparison/m45_degree_poly_tangent_angle_comparison_w18.png)

#### 3.5. Góc 60 độ (`60_degree.csv`)
![60 degree 4 angles comparison W18](benchmark/poly_tangent_comparison/60_degree_poly_tangent_angle_comparison_w18.png)

#### 3.6. Góc 90 độ (`90_degree.csv`)
![90 degree 4 angles comparison W18](benchmark/poly_tangent_comparison/90_degree_poly_tangent_angle_comparison_w18.png)

> Từ đồ thị có thể thấy đường smooth lần 2 mịn hơn , tuy nhiên những điểm có đỉnh đồ thị biến đổi thì đường smooth lần 2 cao hơn đường smooth polynomial 1 lần . 

### 4. Thử thay đổi các cửa sổ Sliding Windows W = 18 -> 15 -> 12 

- **Code sử dụng**: [`plot_poly_tangent_angle_comparison.py`](tools/plot_poly_tangent_angle_comparison.py)
- **Param thay đổi**: `sliding windows length` (`--window-size 18`, `--window-size 15`, `--window-size 12`)
- **Lệnh chạy**:
  ```powershell
  cd 260814
  # Cửa sổ W = 18
  python tools/plot_poly_tangent_angle_comparison.py benchmark --window-size 18 --poly-degree 2 --seed 42

  # Cửa sổ W = 15
  python tools/plot_poly_tangent_angle_comparison.py benchmark --window-size 15 --poly-degree 2 --seed 42

  # Cửa sổ W = 12
  python tools/plot_poly_tangent_angle_comparison.py benchmark --window-size 12 --poly-degree 2 --seed 42
  ```


- **Đồ thị so sánh các độ dài cửa sổ**:

#### 4.1. Góc 0 độ (`0_degree.csv`)
- **Sliding windows length = 18**:
  ![0 degree W18](benchmark/poly_tangent_comparison/0_degree_poly_tangent_angle_comparison_w18.png)
- **Sliding windows length = 15**:
  ![0 degree W15](benchmark/poly_tangent_comparison/0_degree_poly_tangent_angle_comparison_w15.png)
- **Sliding windows length = 12**:
  ![0 degree W12](benchmark/poly_tangent_comparison/0_degree_poly_tangent_angle_comparison_w12.png)

---

#### 4.2. Góc 30 độ (`30_degree.csv`)
- **Sliding windows length = 18**:
  ![30 degree W18](benchmark/poly_tangent_comparison/30_degree_poly_tangent_angle_comparison_w18.png)
- **Sliding windows length = 15**:
  ![30 degree W15](benchmark/poly_tangent_comparison/30_degree_poly_tangent_angle_comparison_w15.png)
- **Sliding windows length = 12**:
  ![30 degree W12](benchmark/poly_tangent_comparison/30_degree_poly_tangent_angle_comparison_w12.png)

---

#### 4.3. Góc 45 độ (`45_degree.csv`)
- **Sliding windows length = 18**:
  ![45 degree W18](benchmark/poly_tangent_comparison/45_degree_poly_tangent_angle_comparison_w18.png)
- **Sliding windows length = 15**:
  ![45 degree W15](benchmark/poly_tangent_comparison/45_degree_poly_tangent_angle_comparison_w15.png)
- **Sliding windows length = 12**:
  ![45 degree W12](benchmark/poly_tangent_comparison/45_degree_poly_tangent_angle_comparison_w12.png)

---

#### 4.4. Góc -45 độ (`m45_degree.csv`)
- **Sliding windows length = 18**:
  ![m45 degree W18](benchmark/poly_tangent_comparison/m45_degree_poly_tangent_angle_comparison_w18.png)
- **Sliding windows length = 15**:
  ![m45 degree W15](benchmark/poly_tangent_comparison/m45_degree_poly_tangent_angle_comparison_w15.png)
- **Sliding windows length = 12**:
  ![m45 degree W12](benchmark/poly_tangent_comparison/m45_degree_poly_tangent_angle_comparison_w12.png)

---

#### 4.5. Góc 60 độ (`60_degree.csv`)
- **Sliding windows length = 18**:
  ![60 degree W18](benchmark/poly_tangent_comparison/60_degree_poly_tangent_angle_comparison_w18.png)
- **Sliding windows length = 15**:
  ![60 degree W15](benchmark/poly_tangent_comparison/60_degree_poly_tangent_angle_comparison_w15.png)
- **Sliding windows length = 12**:
  ![60 degree W12](benchmark/poly_tangent_comparison/60_degree_poly_tangent_angle_comparison_w12.png)

---

#### 4.6. Góc 90 độ (`90_degree.csv`)
- **Sliding windows length = 18**:
  ![90 degree W18](benchmark/poly_tangent_comparison/90_degree_poly_tangent_angle_comparison_w18.png)
- **Sliding windows length = 15**:
  ![90 degree W15](benchmark/poly_tangent_comparison/90_degree_poly_tangent_angle_comparison_w15.png)
- **Sliding windows length = 12**:
  ![90 degree W12](benchmark/poly_tangent_comparison/90_degree_poly_tangent_angle_comparison_w12.png)

> Từ các đồ thị có thể quan sát được nếu cửa sổ càng ngắn thì khả năng smooth giảm đi, các đỉnh nhiễu cao hơn so với Sliding windows = 18 .


### 5. Ước lượng vận tốc (Estimated Speed) trên toàn bộ chu trình 6 lần chạy tiến - lùi

- **Các bước tính toán**:
  - Khi fit đa thức bậc hai trên cửa sổ trượt quá khứ $W = 18$ ($t \in [-1, 0]$), vector đạo hàm tại endpoint $t = 0$ là:
    ```text
    dx = x'(0)
    dy = y'(0)
    ```
  - Độ lớn vận tốc chuyển động tức thời (Estimated Speed) được tính bằng:
    ```text
    Estimated Speed: v = sqrt(dx^2 + dy^2) = sqrt(dx * dx + dy * dy)
    ```
- Chạy trên **toàn bộ dữ liệu của file CSV** (đầy đủ cả 6 lượt di chuyển tiến - lùi.

- **Code sử dụng**: [`plot_estimated_speed.py`](tools/plot_estimated_speed.py)
- **Lệnh chạy**:
  ```powershell
  python tools/plot_estimated_speed.py benchmark --window-size 18 --poly-degree 2
  ```

- **Đồ thị kết quả theo từng góc đo**:

#### 5.1. Quỹ đạo 0 độ (`0_degree.csv`)
![0 degree Estimated Speed Full](benchmark/estimated_speed/0_degree_estimated_speed_full.png)

#### 5.2. Quỹ đạo 30 độ (`30_degree.csv`)
![30 degree Estimated Speed Full](benchmark/estimated_speed/30_degree_estimated_speed_full.png)

#### 5.3. Quỹ đạo 45 độ (`45_degree.csv`)
![45 degree Estimated Speed Full](benchmark/estimated_speed/45_degree_estimated_speed_full.png)

#### 5.4. Quỹ đạo -45 độ (`m45_degree.csv`)
![m45 degree Estimated Speed Full](benchmark/estimated_speed/m45_degree_estimated_speed_full.png)

#### 5.5. Quỹ đạo 60 độ (`60_degree.csv`)
![60 degree Estimated Speed Full](benchmark/estimated_speed/60_degree_estimated_speed_full.png)

#### 5.6. Quỹ đạo 90 độ (`90_degree.csv`)
![90 degree Estimated Speed Full](benchmark/estimated_speed/90_degree_estimated_speed_full.png)

> **Nhận xét & Trả lời câu hỏi kiểm chứng**:
> - Trên toàn bộ chu trình 6 lượt di chuyển tiến - lùi, đồ thị `Estimated Speed` thể hiện rõ các đường đồ thị tụt sát về 0, vận tốc cực tiểu tại các thời điểm robot giảm tốc, dừng lại ở mép sa bàn trước khi đổi hướng chạy ngược lại.
> - Khi robot di chuyển ổn định trên sa bàn, vận tốc duy trì ở mức cao và tương đối phẳng, nhưng vẫn dao động vì nhiễu .


## B. Khó khăn

- Không

## C. Công việc tiếp theo
- Tiếp tục tìm hiểu thêm  `weight function for weighted sliding windows` :
    - Uniform Weight
    - Linear Weight

