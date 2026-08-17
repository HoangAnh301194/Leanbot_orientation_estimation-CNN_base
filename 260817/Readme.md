# Báo cáo công việc ngày 17/08/2026

## A. Công việc đã làm

- Tiếp tục tìm hiểu và thử nghiệm **Weight Function** cho bài toán **Polynomial Least Squares**:
  - **Uniform Weight** (trọng số đều) với tỷ lệ `1:1`.
  - **Linear Weight** (trọng số tuyến tính) với các tỷ lệ:
    - `1:1.5`
    - `1:2`
    - `1:3`

---

### 1. Áp dụng Linear Weight vào Polynomial Least Squares

- **Hạn chế của Uniform Weight trước đây**:
  - Các điểm dữ liệu trong cửa sổ trượt quá khứ $W$ đều có mức độ ảnh hưởng như nhau:
    $$\alpha_0 = \alpha_1 = \dots = \alpha_{W-1} = 1$$

- **Ý tưởng của Linear Weight**:
  - Các frame càng gần thời điểm hiện tại càng mang nhiều thông tin thực tế về hướng chuyển động tức thời, do đó cần được gán trọng số lớn hơn các frame cũ trong quá khứ.
  - Với cửa sổ trượt gồm $W$ mẫu và tỷ lệ trọng số đầu - cuối là $1:r$:
    $$\alpha_i = 1 + \frac{i}{W-1}(r-1), \quad \text{với } i = 0, 1, \dots, W-1$$
  - Trong đó:
    - **Frame cũ nhất** ($i = 0$): $\alpha_0 = 1$
    - **Frame mới nhất** ($i = W-1$): $\alpha_{W-1} = r$
  - Ví dụ với $W = 18$ và tỷ lệ `1:2`:
    - Trọng số $\alpha$ tăng tuyến tính đều đặn từ $1 \to 2$ qua 18 mẫu.
  - **Mục tiêu**: Giảm độ trễ pha (phase lag) khi góc chuyển động thay đổi, đồng thời khảo sát mức độ làm mượt dao động nhiễu.

---

### 2. Áp dụng trọng số vào bài toán Least Squares Polynomial bậc 2

- **Hàm mục tiêu tối ưu hóa (Weighted Least Squares)**:
  - Với **Uniform Weight**:
    $$J = \sum_{i=1}^{W} e_i^2$$
  - Với **Linear Weight**:
    $$J = \sum_{i=1}^{W} \alpha_i e_i^2 \quad \text{với } e_i = y_i - \hat{y}_i$$

- **Quy đổi trọng số cho hàm `np.polyfit()`**:
  - Hàm `np.polyfit(..., w=w)` trong NumPy tối thiểu hóa $\sum (w_i e_i)^2$.
  - Do đó trọng số $w_i$ truyền vào hàm được tính bằng căn bậc hai của importance factor:
    $$w_i = \sqrt{\alpha_i}$$

- **Đoạn mã tạo Linear Weight và Fit đa thức**:
  ```python
  def linear_importance(window_length, ratio):
      return np.linspace(1.0, ratio, window_length)

  def polyfit_weights(window_length, ratio):
      return np.sqrt(linear_importance(window_length, ratio))
  ```
  - Áp dụng khi fit riêng biệt hai tọa độ $x(t)$ và $y(t)$:
  ```python
  coefficients_x = np.polyfit(time_normalized, x_window, deg=current_degree, w=fit_w)
  coefficients_y = np.polyfit(time_normalized, y_window, deg=current_degree, w=fit_w)
  ```

---

### 3. Các bước triển khai thuật toán

- **Bước 1**: Chuẩn hóa trục thời gian $t$ của cửa sổ $W$ mẫu về đoạn:
  $$t \in [-1, 0]$$
- **Bước 2**: Fit riêng hai đa thức bậc 2 theo phương pháp Weighted Least Squares:
  $$x(t) = a_x t^2 + b_x t + c_x$$
  $$y(t) = a_y t^2 + b_y t + c_y$$
- **Bước 3**: Lấy tọa độ làm mượt tại điểm cuối (Endpoint $t = 0$):
  $$x_{smooth} = x(0) = c_x, \quad y_{smooth} = y(0) = c_y$$
- **Bước 4**: Tính vector vận tốc tiếp tuyến tại Endpoint ($t = 0$):
  $$\frac{dx}{dt}\Big|_{t=0} = b_x, \quad \frac{dy}{dt}\Big|_{t=0} = b_y$$
- **Bước 5**: Xác định góc tiếp tuyến của quỹ đạo:
  $$\theta = \operatorname{atan2}\left(-\frac{dy}{dt}\Big|_{t=0}, \frac{dx}{dt}\Big|_{t=0}\right)$$

---

### 4. Các trường hợp thực nghiệm & So sánh

- **Các chuỗi góc được so sánh đồng thời trên cùng biểu đồ**:
  - **Raw Angle (Model)**: Góc thô nhận diện từ Model (màu đỏ đậm `#8b0000`, nét liền).
  - **Uniform Weight `1:1`**: Baseline làm mượt trọng số đều (màu xanh dương `#0055ff`, nét liền).
  - **Linear Weight `1:1.5`**: Trọng số tuyến tính tỷ lệ 1:1.5 (màu cam `#ff7f0e`, nét liền).
  - **Linear Weight `1:2`**: Trọng số tuyến tính tỷ lệ 1:2 (màu xanh lá `#2ca02c`, nét liền).
  - **Linear Weight `1:3`**: Trọng số tuyến tính tỷ lệ 1:3 (màu tím `#9467bd`, nét liền).

- **Mã nguồn thực thi**: [`plot_poly_tangent_linear_weight.py`](tools/plot_poly_tangent_linear_weight.py)
- **Lệnh chạy toàn bộ benchmark**:
  ```powershell
  python tools/plot_poly_tangent_linear_weight.py benchmark --window-size 18 --poly-degree 2 --weight-ratios 1.5,2,3
  ```
- **Thư mục lưu ảnh kết quả**: `benchmark/poly_tangent_linear_weight_comparison/`

---

## 5. Kết quả thử nghiệm

### 5.1. Góc 0 độ (`0_degree.csv`)

- **a) So sánh quỹ đạo 2D**:
  ![0 degree trajectory](benchmark/poly_tangent_linear_weight_comparison/0_degree_poly_tangent_linear_weight_2d_trajectory_w18.png)

- **b) So sánh biểu đồ góc**:
  ![0 degree angle](benchmark/poly_tangent_linear_weight_comparison/0_degree_poly_tangent_linear_weight_angle_w18.png)

---

### 5.2. Góc 30 độ (`30_degree.csv`)

- **a) So sánh quỹ đạo 2D**:
  ![30 degree trajectory](benchmark/poly_tangent_linear_weight_comparison/30_degree_poly_tangent_linear_weight_2d_trajectory_w18.png)

- **b) So sánh biểu đồ góc**:
  ![30 degree angle](benchmark/poly_tangent_linear_weight_comparison/30_degree_poly_tangent_linear_weight_angle_w18.png)

---

### 5.3. Góc 45 độ (`45_degree.csv`)

- **a) So sánh quỹ đạo 2D**:
  ![45 degree trajectory](benchmark/poly_tangent_linear_weight_comparison/45_degree_poly_tangent_linear_weight_2d_trajectory_w18.png)

- **b) So sánh biểu đồ góc**:
  ![45 degree angle](benchmark/poly_tangent_linear_weight_comparison/45_degree_poly_tangent_linear_weight_angle_w18.png)

---

### 5.4. Góc -45 độ (`m45_degree.csv`)

- **a) So sánh quỹ đạo 2D**:
  ![m45 degree trajectory](benchmark/poly_tangent_linear_weight_comparison/m45_degree_poly_tangent_linear_weight_2d_trajectory_w18.png)

- **b) So sánh biểu đồ góc**:
  ![m45 degree angle](benchmark/poly_tangent_linear_weight_comparison/m45_degree_poly_tangent_linear_weight_angle_w18.png)

---

### 5.5. Góc 60 độ (`60_degree.csv`)

- **a) So sánh quỹ đạo 2D**:
  ![60 degree trajectory](benchmark/poly_tangent_linear_weight_comparison/60_degree_poly_tangent_linear_weight_2d_trajectory_w18.png)

- **b) So sánh biểu đồ góc**:
  ![60 degree angle](benchmark/poly_tangent_linear_weight_comparison/60_degree_poly_tangent_linear_weight_angle_w18.png)

---

### 5.6. Góc 90 độ (`90_degree.csv`)

- **a) So sánh quỹ đạo 2D**:
  ![90 degree trajectory](benchmark/poly_tangent_linear_weight_comparison/90_degree_poly_tangent_linear_weight_2d_trajectory_w18.png)

- **b) So sánh biểu đồ góc**:
  ![90 degree angle](benchmark/poly_tangent_linear_weight_comparison/90_degree_poly_tangent_linear_weight_angle_w18.png)

---

> **Nhận xét**:
> - **Uniform Weight `1:1`**: Coi toàn bộ 18 frame trong quá khứ có vai trò ngang nhau, cho đường góc tiếp tuyến ổn định nhưng có độ trễ nhất định khi hướng xe thay đổi đột ngột.
> - **Linear Weight (`1:1.5`, `1:2`, `1:3`)**: Đã ưu tiên trọng số lớn hơn cho các frame mới nhất gần thời điểm hiện tại.
> - **Đánh giá thực nghiệm**: Với 3 tỷ lệ `1:1.5`, `1:2` và `1:3`, đường đồ thị góc tiếp tuyến bám sát quỹ đạo rất tốt, tuy nhiên độ chênh lệch giữa các mức trọng số này chưa tạo ra sự phân hóa quá rõ rệt trên biểu đồ toàn chu trình so với Uniform Weight.

## B. Khó khăn
- Không

## C. Công việc tiếp theo
- Em xin phép nhận công việc tiếp theo từ Thầy ạ.
