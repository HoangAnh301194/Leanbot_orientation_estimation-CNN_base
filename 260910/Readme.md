# Báo cáo công việc ngày 10/09/2026

## A. Công việc đã làm

- Tìm hiểu phương pháp làm mịn dữ liệu Differential Data Filtering (DDF)

### 1. Công thức tính toán Khâu D hiện tại.

Theo như em hiểu hiện tại thì từ khóa này nói về dữ liệu vi phân khâu D trong bộ điều khiển PID hiện tại.

Hiện tại công thức tính toán khâu D như sau:

**Công thức**:

```math
\begin{aligned}
\Delta e_\theta[k]
&= \mathrm{wrap}_{[-180^\circ,\,180^\circ)}\left(e_\theta[k]-e_\theta[k-1]\right),\\
D_{\mathrm{angle2}}[k]
&= K_{d,\mathrm{angle2}}\Delta e_\theta[k].
\end{aligned}
```

Sai phân sai số góc được wrap về khoảng $`[-180^\circ,180^\circ)`$ trước khi nhân với `Kd_angle2`. Ví dụ, khi sai số chuyển từ $`179^\circ`$ sang $`-179^\circ`$, sai phân sau wrap là $`2^\circ`$ thay vì $`-358^\circ`$. Nếu chưa có mẫu trước, `d_angle2 = 0.0`.

*(Chu kỳ lấy mẫu $`\Delta t`$ được coi là hằng số và đã gộp ngầm vào hệ số $`K_{d,\mathrm{angle2}} = \frac{K_{d,\mathrm{angle2}}^{\mathrm{chuẩn}}}{\Delta t}`$)*


**Code thực tế đang sử dụng (`PID_controller.py` & `plot_pid_navigation_log.py`)**:

```python
# 1. Trong bộ điều khiển thực tế (PID_controller.py - Pha 2 Driving):
d_angle2 = wrap_to_180(angle_error - self._prev_angle2_error) if self._prev_angle2_error is not None else 0.0
self._prev_angle2_error = angle_error

# Thành phần D tham gia hiệu chỉnh vận tốc bẻ lái delta_v:
delta_v = (self.Kp_angle2 * angle_error
           + self.Ki_angle2 * self._integral_angle2
           + self.Kd_angle2 * d_angle2) * v_lr_cropped

# 2. Trong công cụ phân tích và vẽ đồ thị (plot_pid_navigation_log.py):
err_diff = (df["angle_error"].diff() + 180.0) % 360.0 - 180.0
d_term = kd_angle2 * err_diff
```

Thực tế theo lý thuyết thì khâu D, là khâu vi phân nên phải có thời gian lấy mẫu delta T  như sau:

**Công thức theo lý thuyết điều khiển tự động**:

Dạng liên tục:

```math
u_D(t) = K_d \cdot \frac{de(t)}{dt}
```

Dạng rời rạc (Backward Euler) với khoảng thời gian lấy mẫu biến thiên $`\Delta t_k = t_k - t_{k-1}`$:

```math
u_D[k] = K_d \cdot \frac{e[k] - e[k-1]}{\Delta t_k}
```

**Code theo lý thuyết nếu đưa $`\Delta t`$ vào**:

```python
# Đo thời gian thực tế dt giữa 2 frame xử lý liên tiếp:
current_time = time.time()
dt = (current_time - self._prev_time) if self._prev_time is not None else fallback_dt
self._prev_time = current_time

if dt > 0:
    # Tốc độ biến thiên sai số góc theo thời gian (de/dt, deg/s)
    err_diff = wrap_to_180(angle_error - self._prev_angle2_error)
    de_dt = err_diff / dt
    d_term = self.Kd_angle2 * de_dt
else:
    d_term = 0.0

self._prev_angle2_error = angle_error
```

Tuy nhiên vì trước đó khi triển khai em coi thời gian lấy mẫu là không thay đổi, và delta T = const nên có thể gộp chung với hệ số Kd để tuning chung. Và như báo cáo hôm qua thì với Kd (đã bao gồm cả Delta T) bằng `0.04` là tối ưu nhất trong khoảng từ `0.0` đến `0.08`.

> Việc coi delta T = const đối với bài toán này có thể sẽ không chính xác, vì tốc độ inference, tính toán trên từng frame ảnh không cố định. Em xin phép nhận thêm đề xuất của Thầy về vấn đề này ạ

### 2. Các phương pháp làm mịn dữ liệu Differential Data Filtering

- Theo như em tìm hiểu thì với từ khóa `Differential Data filtering for PID controllder` cho các kết quả phương pháp phổ biến như: bộ lọc thông thấp Low pass, First order fillter, Moving average fillter, EMA,...

- Em thấy Leanbot là dạng Robot vi sai, động học tương đối đơn giản nên em nghĩ phương pháp đơn giản, dễ triển khai thì phù hợp ạ. Em xin phép đề xuất dùng bộ lọc `First-order low-pass filtered Derivative` để triển khai thử trước ạ.

- Hai hướng triển khai cùng bộ lọc `First-order low-pass filtered Derivative` cho khâu D của bộ điều khiển góc pha 2 như sau:

    - **Hướng 1:** coi thời gian lấy mẫu là hằng số, tiếp tục gộp vào `Kd_angle2` như code hiện tại đang triển khai.
    - **Hướng 2:** đo thời gian giữa các lần cập nhật sai số góc giữa các frame ảnh, không gộp vào `Kd_angle2` như hướng 1.

**Công thức bộ lọc chung**

Trong bộ điều khiển PID, khâu D phản ánh tốc độ thay đổi của sai số nhưng có thể khuếch đại nhiễu tần số cao trong tín hiệu đo. Bộ lọc thông thấp được sử dụng riêng trong nhánh D để hạn chế ảnh hưởng này.

Mô hình liên tục của bộ lọc và nhánh đạo hàm được viết trong miền Laplace, với điều kiện đầu bằng 0:

```math
G_f(s)=\frac{1}{1+T_f s},
\qquad
G_D(s)=K_d sG_f(s)=\frac{K_d s}{1+T_f s}.
```

**Hàm truyền PID có lọc đạo hàm trong miền Laplace**

Bộ điều khiển PID dạng song song gồm ba nhánh P, I, D cùng tác động lên sai số; bộ lọc thông thấp được đặt trong nhánh D. Hàm truyền của bộ điều khiển là:

```math
C(s)=\frac{U(s)}{E(s)}
=K_p+\frac{K_i}{s}+\frac{K_d s}{1+T_f s}.
```
Trong đó:

- $`E(s)`$: biến đổi Laplace của tín hiệu sai số $`e(t)`$.
- $`U(s)`$: biến đổi Laplace của tín hiệu điều khiển $`u(t)`$.
- $`s`$: biến Laplace, không phải thời gian lấy mẫu $`T_s`$ hoặc $`\Delta t_k`$.

- Nhân lại với $`E(s)`$, ta có đầy đủ ba thành phần để quan sát công thức PID đầy đủ ở miền rời rạc :

```math
\begin{aligned}
U(s)&=U_P(s)+U_I(s)+U_D(s),\\
&=K_pE(s)+\frac{K_i}{s}E(s)+\frac{K_d s}{1+T_f s}E(s).
\end{aligned}
```

- **Thành phần tỉ lệ P:** $`U_P(s)=K_pE(s)`$, tương ứng $`u_P(t)=K_pe(t)`$ trong miền thời gian; phản ánh sai số tỉ lệ.
- **Thành phần tích phân I:** $`U_I(s)=\frac{K_i}{s}E(s)`$, tương ứng $`u_I(t)=K_i\int_0^t e(\tau)\,d\tau`$; tích lũy sai số theo thời gian. Phép chia cho $`s`$ trong miền Laplace tương ứng phép tích phân với điều kiện đầu bằng 0.
- **Thành phần đạo hàm có lọc D:** $`U_D(s)=\frac{K_d s}{1+T_f s}E(s)`$; nhân với $`s`$ tương ứng phép đạo hàm với điều kiện đầu bằng 0, còn $`\frac{1}{1+T_f s}`$ là bộ lọc thông thấp bậc nhất.

**Sai số góc và sai phân dùng chung**

Theo quy ước trong code:

```math
e_\theta[k]
=
\mathrm{wrap}_{[-180^\circ,\,180^\circ)}
\left(\theta[k]-\theta_{\mathrm{target}}[k]\right).
```

Trong đó:

- $`\theta[k]`$: góc hướng robot từ kết quả hợp nhất `fused angle`.
- $`\theta_{\mathrm{target}}[k]`$: góc hướng từ vị trí hiện tại đến điểm đích.
- $`e_\theta[k]`$: sai số góc, tương ứng biến `angle_error`.

Sai phân sai số góc được wrap trước khi tính khâu D:

```math
\Delta e_\theta[k]
=
\mathrm{wrap}_{[-180^\circ,\,180^\circ)}
\left(e_\theta[k]-e_\theta[k-1]\right).
```

#### 2.1 Hướng 1: Coi thời gian lấy mẫu là hằng số, gộp vào Kd_angle2


Giả sử khoảng thời gian giữa hai lần cập nhật liên tiếp là:

```math
\Delta t_k=T_s=\mathrm{const}>0.
```

Tức là trong code hiện tại Kd_angle2 bản chất là : 

```math
K_{d,\mathrm{angle2}}^{(1)}
=
\frac{K_{d,\mathrm{angle2}}^{\mathrm{chuẩn}}}{T_s}.
```

Khi chưa lọc:

```math
D_{\mathrm{angle2}}^{(1)}[k]
=
K_{d,\mathrm{angle2}}^{(1)}\Delta e_\theta[k].
```

Vì $`1/T_s`$ đã nằm trong hệ số $`K_{d,\mathrm{angle2}}^{(1)}`$, không chia thêm sai phân cho $`T_s`$ trong mỗi lần tính khâu D.

**Lọc sai phân sai số góc**

Gọi $`q_\theta[k]`$ là sai phân đã lọc, có đơn vị độ. Với phương pháp Backward Euler:

```math
q_\theta[k]
=
\frac{T_f}{T_f+T_s}q_\theta[k-1]
+
\frac{T_s}{T_f+T_s}\Delta e_\theta[k].
```

Đặt hệ số lọc cố định:

```math
\alpha=\frac{T_s}{T_f+T_s},
```

ta có:

```math
q_\theta[k]
=
(1-\alpha)q_\theta[k-1]+\alpha\Delta e_\theta[k].
```

Thành phần D sau lọc:

```math
\boxed{
D_{\mathrm{angle2}}^{(1)}[k]
=
K_{d,\mathrm{angle2}}^{(1)}q_\theta[k]
}
```

Hướng này giữ cách chỉnh định Kd hiện tại và dùng hệ số lọc $`\alpha`$ cố định. Tuy nhiên, nếu thời gian xử lý từng frame thay đổi đáng kể, giả thiết $`T_s=\mathrm{const}`$ không còn phản ánh đúng khoảng thời gian giữa các lần cập nhật nữa, khiến cho khâu D có thể hoạt động không chính xác .

#### 2.2 Hướng 2: Đo thời gian lấy mẫu, không gộp vào Kd_angle2

**Đo thời gian giữa hai lần cập nhật**

Gọi $`t_k`$ là thời điểm cập nhật sai số góc thứ $`k`$:

```math
\Delta t_k=t_k-t_{k-1}>0.
```

Đo delta T bằng `time.perf_counter()` của module `time`. Lấy mốc thời gian ở cùng một vị trí trong mỗi lần cập nhật PID để tính khoảng cách thời gian giữa hai mẫu sai số, không phải thời gian chạy riêng đoạn code khâu D.

Ở hướng này, hệ số Kd được giữ độc lập với thời gian lấy mẫu:

```math
K_{d,\mathrm{angle2}}^{(2)}
=
K_{d,\mathrm{angle2}}^{\mathrm{chuẩn}}.
```

Đạo hàm sai số chưa lọc, đơn vị độ/giây:

```math
d_{\mathrm{raw}}[k]
=
\frac{\Delta e_\theta[k]}{\Delta t_k}.
```

Khi chưa lọc:

```math
D_{\mathrm{angle2}}^{(2)}[k]
=
K_{d,\mathrm{angle2}}^{(2)}
\frac{\Delta e_\theta[k]}{\Delta t_k}.
```

**Lọc đạo hàm với thời gian lấy mẫu đo được**

Gọi $`d_f[k]`$ là đạo hàm đã lọc, đơn vị độ/giây. Với $`T_f`$ cố định, hệ số lọc được cập nhật theo từng khoảng thời gian đo được:

```math
\alpha_k=\frac{\Delta t_k}{T_f+\Delta t_k}.
```

Công thức lọc:

```math
d_f[k]
=
(1-\alpha_k)d_f[k-1]+\alpha_k d_{\mathrm{raw}}[k].
```

Dạng tương đương theo Backward Euler:

```math
\boxed{
d_f[k]
=
\frac{T_f}{T_f+\Delta t_k}d_f[k-1]
+
\frac{\Delta e_\theta[k]}{T_f+\Delta t_k}
}
```

Thành phần D sau lọc:

```math
\boxed{
D_{\mathrm{angle2}}^{(2)}[k]
=
K_{d,\mathrm{angle2}}^{(2)}d_f[k]
}
```

Từ đó  $`\Delta t_k`$ được sử dụng riêng trong phép tính đạo hàm và hệ số lọc; không gộp vào Kd như hướng 1 . Nếu chỉ giữ $`\alpha`$ cố định khi $`\Delta t_k`$ thay đổi, bộ lọc sẽ không còn giữ cùng hằng số thời gian $`T_f`$. Hướng 2 sẽ phù hợp hơn với hệ thống có thời gian lấy mẫu không cố định, hoặc ổn định tại 1 giá trị. 

**Code ví dụ cho hướng 2**

Khi bắt đầu pha 2 hoặc reset, đặt `self._prev_time_angle2 = None`, `self._prev_angle2_error = None`, `self._filtered_derivative_angle2 = 0.0`. Thuộc tính `self.derivative_filter_time` tương ứng $`T_f>0`$, còn `self.Kd_angle2` sẽ là hệ số của hướng 2. 

```python
import time

current_time = time.perf_counter()

if self._prev_time_angle2 is None or self._prev_angle2_error is None:
    self._filtered_derivative_angle2 = 0.0
    d_term = 0.0
else:
    dt = current_time - self._prev_time_angle2
    if dt > 0.0:
        err_diff = wrap_to_180(angle_error - self._prev_angle2_error)
        derivative_raw = err_diff / dt
        alpha = dt / (self.derivative_filter_time + dt)
        self._filtered_derivative_angle2 = (
            (1.0 - alpha) * self._filtered_derivative_angle2
            + alpha * derivative_raw
        )
        d_term = self.Kd_angle2 * self._filtered_derivative_angle2
    else:
        self._filtered_derivative_angle2 = 0.0
        d_term = 0.0

self._prev_time_angle2 = current_time
self._prev_angle2_error = angle_error
```
**Tích hợp vào bộ điều khiển pha 2, áp dụng cho cả hai hướng**

Để chỉ khảo sát ảnh hưởng của khâu D, giữ nguyên nhánh P, nhánh I và nhánh điều khiển khoảng cách trong code hiện tại. Trong đó, tổng sai số của nhánh I vẫn được cập nhật theo cách đang dùng:

```math
S_{\mathrm{angle2}}[k]
=
S_{\mathrm{angle2}}[k-1]+e_\theta[k].
```

Gọi $`D_{\mathrm{angle2}}[k]`$ là thành phần D sau lọc được chọn theo hướng 1 hoặc hướng 2:

```math
\Delta v[k]
=
\left(
K_{p,\mathrm{angle2}}e_\theta[k]
+
K_{i,\mathrm{angle2}}S_{\mathrm{angle2}}[k]
+
D_{\mathrm{angle2}}[k]
\right)
v_{\mathrm{LR,cropped}}[k].
```

Trong đó $`v_{\mathrm{LR,cropped}}[k]`$ là lệnh tiến chung do nhánh điều khiển khoảng cách tính toán, sau khi giới hạn; tương ứng `v_lr_cropped`. Đóng góp riêng của khâu D vào chênh lệch lệnh hai bánh là:

```math
\Delta v_D[k]
=
v_{\mathrm{LR,cropped}}[k]D_{\mathrm{angle2}}[k].
```

Lệnh hai bánh trước bước giới hạn chung:

```math
\begin{aligned}
v_L[k]&=v_{\mathrm{LR,cropped}}[k]+\Delta v[k],\\
v_R[k]&=v_{\mathrm{LR,cropped}}[k]-\Delta v[k].
\end{aligned}
```

Sau đó, chương trình dùng `_scale_speeds` để giảm đồng thời hai lệnh theo cùng tỷ lệ nếu vượt `max_velocity`.

#### 2.3 Chi tiết công thức tính bộ lọc và mã nguồn áp dụng vào code hiện tại

##### 1. Trường hợp 1: Thời gian lấy mẫu cố định ($`T_s = \mathrm{const}`$ - Hướng 1)

* **Công thức tính bộ lọc**:
  - Sai phân sai số góc có wrap $`[-180^\circ, 180^\circ)`$:
    ```math
    \Delta e_\theta[k] = \mathrm{wrap}_{[-180^\circ,\,180^\circ)}\left(e_\theta[k] - e_\theta[k-1]\right)
    ```
  - Lọc sai phân góc qua bộ lọc thông thấp bậc nhất với hệ số cố định $`\alpha = \frac{T_s}{T_f + T_s}`$:
    ```math
    q_\theta[k] = (1 - \alpha) q_\theta[k-1] + \alpha \Delta e_\theta[k]
    ```
  - Thành phần vi phân $`D_{\mathrm{angle2}}^{(1)}[k]`$:
    ```math
    D_{\mathrm{angle2}}^{(1)}[k] = K_{d,\mathrm{angle2}}^{(1)} q_\theta[k]
    ```

* **Mã nguồn áp dụng trong `compute()` (Pha 2 - Driving)**:
  ```python
  # --- TRƯỜNG HỢP 1: T cố định (Hướng 1) ---
  if self._prev_angle2_error is None:
      delta_e = 0.0
      self._filtered_q_angle2 = 0.0
  else:
      # 1. Sai phân góc có wrap [-180, 180)
      delta_e = wrap_to_180(angle_error - self._prev_angle2_error)
      # 2. Lọc thông thấp bậc nhất với alpha cố định
      self._filtered_q_angle2 = (
          (1.0 - self.alpha_filter) * self._filtered_q_angle2
          + self.alpha_filter * delta_e
      )

  self._prev_angle2_error = angle_error

  # 3. Tính thành phần D sau lọc
  D_angle2 = self.Kd_angle2 * self._filtered_q_angle2

  # 4. Tính chênh lệch vận tốc delta_v và lệnh 2 bánh
  delta_v = (self.Kp_angle2 * angle_error
             + self.Ki_angle2 * self._integral_angle2
             + D_angle2) * v_lr_cropped

  speed_left, speed_right = self._scale_speeds(v_lr_cropped + delta_v, v_lr_cropped - delta_v)
  ```

##### 2. Trường hợp 2: Thời gian lấy mẫu có tính toán thực tế ($`\Delta t_k = t_k - t_{k-1}`$ - Hướng 2)

* **Công thức tính bộ lọc**:
  - Khoảng thời gian lấy mẫu thực tế giữa 2 frame liên tiếp (đo bằng `time.perf_counter()`):
    ```math
    \Delta t_k = t_k - t_{k-1} > 0
    ```
  - Đạo hàm sai số thô (chưa lọc, đơn vị: độ/giây):
    ```math
    d_{\mathrm{raw}}[k] = \frac{\Delta e_\theta[k]}{\Delta t_k} = \frac{\mathrm{wrap}_{[-180^\circ,\,180^\circ)}\left(e_\theta[k] - e_\theta[k-1]\right)}{\Delta t_k}
    ```
  - Cập nhật hệ số lọc động $`\alpha_k = \frac{\Delta t_k}{T_f + \Delta t_k}`$ và lọc đạo hàm:
    ```math
    d_f[k] = (1 - \alpha_k) d_f[k-1] + \alpha_k d_{\mathrm{raw}}[k] = \frac{T_f}{T_f + \Delta t_k} d_f[k-1] + \frac{\Delta e_\theta[k]}{T_f + \Delta t_k}
    ```
  - Thành phần vi phân $`D_{\mathrm{angle2}}^{(2)}[k]`$:
    ```math
    D_{\mathrm{angle2}}^{(2)}[k] = K_{d,\mathrm{angle2}}^{(2)} d_f[k]
    ```

* **Mã nguồn áp dụng trong `compute()` (Pha 2 - Driving)**:
  ```python
  # --- TRƯỜNG HỢP 2: T có tính toán (Hướng 2) ---
  current_time = time.perf_counter()

  if self._prev_time_angle2 is None or self._prev_angle2_error is None:
      self._filtered_derivative_angle2 = 0.0
      D_angle2 = 0.0
  else:
      dt = current_time - self._prev_time_angle2
      if dt > 0.0:
          # 1. Sai phân góc có wrap [-180, 180)
          delta_e = wrap_to_180(angle_error - self._prev_angle2_error)
          # 2. Đạo hàm thô (độ/giây)
          derivative_raw = delta_e / dt
          # 3. Cập nhật alpha_k động theo dt thực tế
          alpha_k = dt / (self.derivative_filter_time + dt)
          # 4. Lọc thông thấp bậc nhất cho đạo hàm
          self._filtered_derivative_angle2 = (
              (1.0 - alpha_k) * self._filtered_derivative_angle2
              + alpha_k * derivative_raw
          )
          D_angle2 = self.Kd_angle2 * self._filtered_derivative_angle2
      else:
          D_angle2 = 0.0

  self._prev_time_angle2 = current_time
  self._prev_angle2_error = angle_error

  # 5. Tính chênh lệch vận tốc delta_v và lệnh 2 bánh
  delta_v = (self.Kp_angle2 * angle_error
             + self.Ki_angle2 * self._integral_angle2
             + D_angle2) * v_lr_cropped

  speed_left, speed_right = self._scale_speeds(v_lr_cropped + delta_v, v_lr_cropped - delta_v)
  ```

## B. Khó khăn

- Em xem lại các đồ thị khâu D thì em không quan sát thấy nhiễu giật hay chattering gì nên em đang thắc mắc chút là việc thêm filter nhằm mục đích gì ạ Thầy? vì nếu làm mềm thêm tín hiệu khâu D thì sẽ làm giảm sự nhạy của Khâu D cho việc phản ứng với tốc độ thay đổi mạnh của khâu P ạ.

## C. Công việc tiếp theo

- Em xin phép nhận thêm đề xuất từ Thầy về việc setup và chụp thêm dữ liệu trainning ạ.
