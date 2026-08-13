# Báo cáo công việc ngày 12/08/2026

## A. Công việc đã làm 
- Chuẩn hóa lại trục thời gian `[-1;0]`
- Tìm hiểu phương pháp `2D tangent estimation from sequence of noisy sample points` bằng `Local Polynomial Regression (Savitzky-Golay Filter)`

### 1. Chuẩn hóa lại trục thời gian normaliza `[-1;0]`

Đồng bộ toàn bộ các công cụ làm mịn đa thức sang quy chuẩn **Causal Sliding Window** với trục thời gian chuẩn hóa $t \in [-1.0, 0.0]$ ($t = -1.0$ là mẫu cũ nhất, $t = 0.0$ là mẫu hiện tại ):

- **`tools/plot_continuous_poly_segments.py`**:
  ```python
  # Causal sliding window (chỉ dùng mẫu quá khứ -> hiện tại)
  w_start = max(0, i - window_size + 1)
  w_end = i + 1

  # Trục thời gian chuẩn hóa t in [-1.0, 0.0]
  t_norm = np.linspace(-1.0, 0.0, w_len)

  px = np.polyfit(t_norm, x_sub, deg=deg)
  py = np.polyfit(t_norm, y_sub, deg=deg)

  x_smooth[i] = float(np.polyval(px, 0.0))
  y_smooth[i] = float(np.polyval(py, 0.0))
  dx_dt[i] = float(np.polyval(np.polyder(px), 0.0))
  dy_dt[i] = float(np.polyval(np.polyder(py), 0.0))
  ```

### 2. Phương pháp `Local Polynomial Regression (Savitzky-Golay Filter)`

#### 2.1. Mục tiêu

Dữ liệu vị trí tâm Leanbot từ hệ thống thị giác có dạng:

$$
P_k=(x_k,y_k)
$$

Chuỗi vị trí có thể nhiễu do sai số phát hiện BBox của model hoặc tracking không ổn định. Mục tiêu:

1. Làm mượt quỹ đạo $(x_k,y_k)$ nhưng giữ xu hướng chuyển động.
2. Ước lượng vector tiếp tuyến tại thời điểm xét.
3. Tính góc chuyển động ổn định cho Leanbot.

#### 2.2. Tài liệu tham khảo

- [Smoothing and Differentiation of Data by Simplified Least Squares Procedures - Abraham Savitzky và Marcel J. E. Golay (1964)](1964%20-%20Perkin%20Elmer%20-%20Smoothing%20and%20Differentiation%20of%20Data%20by%20Simplified%20Least%20Squares%20Procedures%20-%20SAVITZKY,%20GOLAY.pdf)

Bài báo đề xuất làm mượt và tính đạo hàm dữ liệu bằng cách:

1. Chọn cửa sổ gồm các mẫu liên tiếp.
2. Fit đa thức cục bộ bằng bình phương tối thiểu ( Least Squares)
3. Đánh giá đa thức hoặc đạo hàm tại một vị trí xác định.
4. Chuyển phép tính thành bộ hệ số convolution cố định khi cấu hình cửa sổ không đổi.

#### 2.3. So sánh phương pháp gốc và bài toán Leanbot

| Thành phần | Savitzky-Golay gốc | Phương pháp cho Leanbot |
|---|---|---|
| Cửa sổ | Đối xứng, thường có $2m+1$ mẫu | Một phía, gồm $N$ mẫu quá khứ đến hiện tại |
| Miền thời gian | $[-m,m]$ hoặc tương đương | Chuẩn hóa về $[-1,0]$ |
| Điểm đánh giá | Tâm cửa sổ | Điểm cuối $t=0$ |
| Dữ liệu tương lai | Có sử dụng | Không sử dụng |
| Loại xử lý | Offline hoặc có độ trễ | Causal, phù hợp realtime |
| Đa thức | Tùy cấu hình | Bậc 2 |

Phương pháp này khi áp dụng Leanbot có thể coi là  **Causal Endpoint Savitzky-Golay Filter**. Phương pháp giữ nguyên nguyên lý Least Squares nhưng thay đổi vị trí cửa sổ và điểm đánh giá cho phù hợp bài toán

#### 2.4. Các bước triển khai trên lý thuyết

##### 2.4.1. Lấy cửa sổ xử lý dữ liệu

Tại thời điểm $k$, lấy $N$ mẫu gần nhất:

$$
\mathbf{P}_k=\left[P_{k-N+1},P_{k-N+2},\ldots,P_k\right]
$$

Trong đó $P_i=(x_i,y_i)$. Tách thành hai vector:

$$
\mathbf{x}_k=\begin{bmatrix}x_{k-N+1}&x_{k-N+2}&\cdots&x_k\end{bmatrix}^{T}
$$

$$
\mathbf{y}_k=\begin{bmatrix}y_{k-N+1}&y_{k-N+2}&\cdots&y_k\end{bmatrix}^{T}
$$

Yêu cầu hiện tại của Thầy là dùng cửa sổ mặc định `N = 18` mẫu. Điểm đánh giá nằm ở endpoint, không phải tâm cửa sổ.

##### 2.4.2. Chuẩn hóa trục thời gian

Với $i=0,1,\ldots,N-1$:

$$
t_i=\frac{i-(N-1)}{N-1},\qquad t_i\in[-1,0]
$$

- $t=-1$: mẫu cũ nhất.
- $t=0$: mẫu hiện tại.

```python
t_norm = np.linspace(-1.0, 0.0, window_size)
```

##### 2.4.3. Chọn đa thức xấp xỉ

Leanbot dùng đa thức bậc hai cho từng thành phần tọa độ:

$$
x(t)=a_{x,0}+a_{x,1}t+a_{x,2}t^2
$$

$$
y(t)=a_{y,0}+a_{y,1}t+a_{y,2}t^2
$$


##### 2.4.4. Fit đa thức bằng Least Squares

Ma trận thiết kế của đa thức bậc hai:

$$
\mathbf{X}=
\begin{bmatrix}
1&t_0&t_0^2\\
1&t_1&t_1^2\\
\vdots&\vdots&\vdots\\
1&t_{N-1}&t_{N-1}^2
\end{bmatrix}
$$

Vector hệ số:

$$
\mathbf{a}_x = \begin{bmatrix}
a_{x,0} \\
a_{x,1} \\
a_{x,2}
\end{bmatrix},
\qquad
\mathbf{a}_y = \begin{bmatrix}
a_{y,0} \\
a_{y,1} \\
a_{y,2}
\end{bmatrix}
$$

Bài toán bình phương tối thiểu:

$$
\hat{\mathbf{a}}_x = \arg\min_{\mathbf{a}_x} \left\|\mathbf{X}\mathbf{a}_x - \mathbf{x}_k\right\|_2^2
$$

$$
\hat{\mathbf{a}}_y = \arg\min_{\mathbf{a}_y} \left\|\mathbf{X}\mathbf{a}_y - \mathbf{y}_k\right\|_2^2
$$

Nghiệm lý thuyết, với $\mathbf{z}$ lần lượt là $\mathbf{x}_k$ và $\mathbf{y}_k$:

$$
\hat{\mathbf{a}}=(\mathbf{X}^{T}\mathbf{X})^{-1}\mathbf{X}^{T}\mathbf{z}
$$


##### 2.4.5. Đánh giá tại endpoint

Leanbot cần kết quả tại thời điểm hiện tại nên chọn:

$$
t_{\text{eval}}=0
$$

Vị trí sau làm mượt:

$$
\hat{x}_k=x(0)=\hat{a}_{x,0}
$$

$$
\hat{y}_k=y(0)=\hat{a}_{y,0}
$$

```python
px = np.polyfit(t_norm, x_sub, deg=2)
py = np.polyfit(t_norm, y_sub, deg=2)

x_smooth = float(np.polyval(px, 0.0))
y_smooth = float(np.polyval(py, 0.0))
```

##### 2.4.6. Tính vector tiếp tuyến

Đạo hàm của hai đa thức:

$$
x'(t)=a_{x,1}+2a_{x,2}t
$$

$$
y'(t)=a_{y,1}+2a_{y,2}t
$$

Tại $t=0$:

$$
x'(0)=a_{x,1},\qquad y'(0)=a_{y,1}
$$

Vector tiếp tuyến tại mẫu hiện tại:

$$
\mathbf{v}_k = \begin{bmatrix}
x'(0) \\
y'(0)
\end{bmatrix}
$$

Trong hệ tọa độ ảnh, trục $y$ hướng xuống. Khi chuyển sang quy ước Đề-các:

$$
\mathbf{v}^{\text{cartesian}}_k = \begin{bmatrix}
x'(0) \\
-y'(0)
\end{bmatrix}
$$

##### 2.4.7. Tính góc chuyển động

Góc tiếp tuyến của quỹ đạo:

$$
\theta_k = \text{atan2}\left(-y'(0),x'(0)\right)
$$

Đổi sang độ:

$$
\theta_k^{\circ}=\theta_k\frac{180}{\pi}
$$

Triển khai realtime hiện tại tính góc từ hai điểm đã làm mượt liên tiếp:

$$
\Delta x_k=\hat{x}_k-\hat{x}_{k-1},\qquad
\Delta y_k=\hat{y}_k-\hat{y}_{k-1}
$$

$$
\theta_k = \text{atan2}(-\Delta y_k,\Delta x_k)
$$



##### 2.4.8. Quy đổi đạo hàm sang thời gian thực

Đạo hàm trên được tính theo trục chuẩn hóa. Nếu chu kỳ lấy mẫu là $\Delta T$, độ dài thời gian của cửa sổ:

$$
T_w=(N-1)\Delta T
$$

Đạo hàm theo thời gian thực:

$$
\frac{dx}{d\tau}=\frac{x'(0)}{T_w},\qquad
\frac{dy}{d\tau}=\frac{y'(0)}{T_w}
$$

Hệ số $1/T_w$ không làm đổi góc khi áp dụng đồng thời cho hai trục, nhưng cần thiết nếu kết quả được dùng để tính vận tốc.

#### 2.5. Dạng convolution và tối ưu khi chạy realtime

Khi $N$, bậc đa thức và các giá trị $t_i$ không đổi, ma trận sau có thể tính trước:

$$
\mathbf{B}=(\mathbf{X}^{T}\mathbf{X})^{-1}\mathbf{X}^{T}
$$

Giá trị làm mượt và đạo hàm trở thành phép nhân vector:

$$
\hat{x}_k=\mathbf{h}_0^{T}\mathbf{x}_k,
\qquad
x'(0)=\mathbf{h}_1^{T}\mathbf{x}_k
$$

$$
\hat{y}_k=\mathbf{h}_0^{T}\mathbf{y}_k,
\qquad
y'(0)=\mathbf{h}_1^{T}\mathbf{y}_k
$$

Trong đó $\mathbf{h}_0$ là hệ số làm mượt, $\mathbf{h}_1$ là hệ số đạo hàm tại endpoint.

Từ việc tính toán dạng convolution sẽ tối ưuu được một số điểm : 

- Không gọi hàm tính toán đa thức `np.polyfit()` tại mỗi frame.
- Chỉ cần phép nhân và cộng.
- Độ phức tạp mỗi lần cập nhật: $O(N)$.
- Bộ nhớ cần sử dụng: $O(N)$.

#### 2.6. Các hàm Savitzky-Golay trong thư viện SciPy

Thư viện SciPy cung cấp hai hàm chính liên quan trực tiếp đến bộ lọc Savitzky-Golay trong module `scipy.signal`:

```python
from scipy.signal import savgol_filter, savgol_coeffs
```

- `savgol_filter()`: nhận dữ liệu đầu vào và trả về dữ liệu đã được làm mượt hoặc lấy đạo hàm.
- `savgol_coeffs()`: không nhận dữ liệu cần lọc; hàm chỉ tính và trả về bộ hệ số Savitzky-Golay.

Tài liệu tham khảo:

- [`scipy.signal.savgol_filter`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.savgol_filter.html)
- [`scipy.signal.savgol_coeffs`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.savgol_coeffs.html)

##### 2.6.1. Hàm `savgol_filter()`

Cú pháp hàm:

```python
savgol_filter(
    x,
    window_length,
    polyorder,
    deriv=0,
    delta=1.0,
    axis=-1,
    mode="interp",
    cval=0.0,
)
```

###### a. Chức năng

Hàm `savgol_filter()` áp dụng bộ lọc Savitzky-Golay trực tiếp lên dữ liệu. Tùy theo giá trị của tham số `deriv`, hàm có thể thực hiện:

- Làm mượt dữ liệu khi `deriv=0`.
- Ước lượng đạo hàm bậc nhất khi `deriv=1`.
- Ước lượng đạo hàm bậc cao hơn khi `deriv>1`.

Hàm xử lý được cả mảng một chiều và mảng nhiều chiều. Với mảng nhiều chiều, phép lọc được thực hiện dọc theo trục được chỉ định bởi tham số `axis`.

###### b. Dữ liệu đầu vào

| Tham số | Kiểu dữ liệu | Ý nghĩa |
|---|---|---|
| `x` | `array_like` | Mảng dữ liệu cần làm mượt hoặc lấy đạo hàm. |
| `window_length` | `int` | Số mẫu trong mỗi cửa sổ cục bộ dùng để fit đa thức. |
| `polyorder` | `int` | Bậc của đa thức được fit trong mỗi cửa sổ. |
| `deriv` | `int`, mặc định `0` | Bậc đạo hàm cần trả về. `0` có nghĩa là chỉ làm mượt. |
| `delta` | `float`, mặc định `1.0` | Khoảng cách giữa hai mẫu liên tiếp; chỉ ảnh hưởng khi `deriv>0`. |
| `axis` | `int`, mặc định `-1` | Trục của mảng `x` mà bộ lọc được áp dụng. |
| `mode` | `str`, mặc định `"interp"` | Phương pháp xử lý các mẫu ở hai biên của dữ liệu. |
| `cval` | `scalar`, mặc định `0.0` | Giá trị dùng để mở rộng dữ liệu khi `mode="constant"`. |

- `polyorder < window_length`

Khi sử dụng `mode="interp"`, kích thước cửa sổ không được lớn hơn số phần tử của dữ liệu trên trục được lọc.

Các giá trị của `mode` gồm:

| `mode` | Cách xử lý biên |
|---|---|
| `"interp"` | Fit một đa thức tại biên và dùng đa thức đó để tính các giá trị đầu ra ở biên. |
| `"mirror"` | Mở rộng dữ liệu bằng cách phản chiếu các mẫu tại biên. |
| `"nearest"` | Mở rộng bằng cách lặp lại giá trị gần biên nhất. |
| `"constant"` | Mở rộng bằng giá trị `cval`. |
| `"wrap"` | Lấy các mẫu ở đầu mảng để mở rộng cuối mảng và ngược lại. |

###### c. Dữ liệu đầu ra

Hàm trả về một mảng `ndarray` có cùng kích thước với mảng đầu vào `x`.

- Nếu `deriv=0`, mỗi phần tử đầu ra là giá trị dữ liệu đã được làm mượt.
- Nếu `deriv=1`, mỗi phần tử đầu ra là giá trị đạo hàm bậc nhất được ước lượng tại vị trí tương ứng.
- Nếu `deriv=n`, đầu ra là đạo hàm bậc $n$ của đa thức cục bộ tại từng vị trí.

Hàm chỉ trả về một loại kết quả trong mỗi lần gọi. Ví dụ, một lần gọi với `deriv=0` không đồng thời trả về đạo hàm; muốn lấy đạo hàm cần gọi lại hàm với `deriv=1` hoặc giá trị khác.

###### d. Các công việc được thực hiện bên trong hàm

Về mặt nguyên lý, `savgol_filter()` thực hiện các công việc sau:

1. Chia dữ liệu thành các cửa sổ cục bộ có `window_length` mẫu.
2. Xây dựng đa thức bậc `polyorder` cho mỗi cửa sổ.
3. Fit đa thức với các mẫu trong cửa sổ theo phương pháp bình phương tối thiểu.
4. Đánh giá đa thức hoặc đạo hàm của đa thức tại vị trí cần tính.
5. Áp dụng các hệ số Savitzky-Golay tương đương dưới dạng phép convolution cho các điểm bên trong dữ liệu.
6. Xử lý các điểm ở biên theo phương pháp được chọn bởi `mode`.
7. Ghép các kết quả thành mảng đầu ra có cùng kích thước với dữ liệu đầu vào.

##### 2.6.2. Hàm `savgol_coeffs()`

Cú pháp hàm :

```python
savgol_coeffs(
    window_length,
    polyorder,
    deriv=0,
    delta=1.0,
    pos=None,
    use="conv",
)
```

###### a. Chức năng

Hàm `savgol_coeffs()` tính bộ hệ số của bộ lọc Savitzky-Golay nhưng không áp dụng bộ lọc lên dữ liệu.

Bộ hệ số được tạo ra có thể dùng để:

- Làm mượt dữ liệu.
- Ước lượng đạo hàm.
- Đánh giá đa thức tại tâm hoặc tại một vị trí khác trong cửa sổ.
- Thực hiện phép convolution hoặc tích vô hướng với một cửa sổ dữ liệu.

###### b. Dữ liệu đầu vào

| Tham số | Kiểu dữ liệu | Ý nghĩa |
|---|---|---|
| `window_length` | `int` | Số hệ số cần tạo, đồng thời là số mẫu trong cửa sổ. |
| `polyorder` | `int` | Bậc đa thức được dùng để xây dựng bộ hệ số. |
| `deriv` | `int`, mặc định `0` | Bậc đạo hàm mà bộ hệ số cần ước lượng. |
| `delta` | `float`, mặc định `1.0` | Khoảng cách giữa hai mẫu; dùng để chia tỷ lệ hệ số đạo hàm. |
| `pos` | `int` hoặc `None` | Vị trí trong cửa sổ mà đa thức hoặc đạo hàm được đánh giá. `None` chọn vị trí mặc định ở giữa cửa sổ. |
| `use` | `"conv"` hoặc `"dot"` | Quy định thứ tự của hệ số để dùng cho convolution hoặc tích vô hướng. |

Ý nghĩa của `use`:

- `use="conv"`: hệ số được sắp xếp theo thứ tự phù hợp với phép convolution.
- `use="dot"`: hệ số được đảo thứ tự để nhân trực tiếp với cửa sổ dữ liệu bằng tích vô hướng.

###### c. Dữ liệu đầu ra

Hàm trả về một mảng một chiều chứa `window_length` hệ số:

$$
\mathbf{h}=
\begin{bmatrix}
h_0&h_1&\cdots&h_{N-1}
\end{bmatrix}^{T}
$$

Hàm không trả về dữ liệu đã lọc. Muốn thu được kết quả, bộ hệ số phải được áp dụng lên một cửa sổ dữ liệu bằng convolution hoặc tích vô hướng.

- Với `deriv=0`, đầu ra là hệ số dùng để ước lượng giá trị đã làm mượt.
- Với `deriv=1`, đầu ra là hệ số dùng để ước lượng đạo hàm bậc nhất.
- Với `deriv=n`, đầu ra là hệ số dùng để ước lượng đạo hàm bậc $n$.

###### d. Các công việc được thực hiện bên trong hàm

Về mặt nguyên lý, `savgol_coeffs()` thực hiện:

1. Xây dựng các vị trí mẫu trong cửa sổ.
2. Xây dựng ma trận thiết kế của đa thức bậc `polyorder`.
3. Giải bài toán bình phương tối thiểu để xác định phép ánh xạ từ dữ liệu đầu vào sang giá trị cần ước lượng.
4. Tính bộ hệ số tương ứng với bậc đạo hàm `deriv` và khoảng cách mẫu `delta`.
5. Chọn điểm đánh giá trong cửa sổ bằng `pos`.
6. Sắp xếp hệ số theo kiểu sử dụng được chỉ định bởi `use`.
7. Trả về bộ hệ số mà không thực hiện lọc dữ liệu.

##### 2.6.3. So sánh hai hàm

| Tiêu chí | `savgol_filter()` | `savgol_coeffs()` |
|---|---|---|
| Dữ liệu đầu vào | Có nhận mảng dữ liệu `x` | Không nhận dữ liệu cần lọc |
| Kết quả đầu ra | Mảng dữ liệu đã làm mượt hoặc đạo hàm | Mảng hệ số Savitzky-Golay |
| Tạo hệ số | Có | Có |
| Áp dụng hệ số lên dữ liệu | Có | Không |
| Xử lý biên | Có, thông qua `mode` | Không |
| Chọn vị trí đánh giá bằng `pos` | Không cung cấp trực tiếp | Có |
| Mức độ sử dụng | Hàm mức cao, sử dụng trực tiếp | Hàm mức thấp, cung cấp hệ số |

Có thể mô tả quan hệ giữa hai hàm như sau:

```text
savgol_filter()
    = xác định hệ số Savitzky-Golay
    + áp dụng hệ số lên dữ liệu
    + xử lý các điểm ở biên

savgol_coeffs()
    = chỉ xác định và trả về hệ số Savitzky-Golay
```

## B. Khó khăn 
- Không
## C. Công việc tiếp theo
- Em xin phép xin xác nhận từ Thầy về thông tin đã tìm hiểu và các bước triển khai nhưu trên báo cáo đã phù hợp để triển khai và đánh giá luôn chưa ạ ? 
- Tiếp tục tìm hiểu về `weight function for weighted sliding windows` : 
    - Uniform Weight
    - Linear Weight