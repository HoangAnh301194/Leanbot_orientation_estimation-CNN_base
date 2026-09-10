# Báo cáo công việc ngày 10/09/2026

## A. Công việc đã làm

- Tìm hiểu phương pháp làm mịn dữ liệu Differential Data Filtering (DDF)

### 1. Công thức tính toán Khâu D hiện tại.

- Theo như em hiểu hiện tại thì từ khóa này nói về dữ liệu vi phân khâu D trong bộ điều khiển PID hiện tại.
- Hiện tại công thức tính toán khâu D như sau:
  - **Công thức**:

    $$
    D[k] = K_d \cdot \Delta e[k] = K_d \cdot (e[k] - e[k-1])
    $$

    *(Chu kỳ lấy mẫu $\Delta t$ được coi là hằng số và đã gộp ngầm vào hệ số $K_d = \frac{K_{d,\text{chuẩn}}}{\Delta t}$)*

  - **Code thực tế đang sử dụng (`PID_controller.py` & `plot_pid_navigation_log.py`)**:

    ```python
    # 1. Trong bộ điều khiển thực tế (PID_controller.py - Pha 2 Driving):
    d_angle2 = (angle_error - self._prev_angle2_error) if self._prev_angle2_error is not None else 0.0
    self._prev_angle2_error = angle_error

    # Thành phần D tham gia hiệu chỉnh vận tốc bẻ lái delta_v:
    delta_v = (self.Kp_angle2 * angle_error
               + self.Ki_angle2 * self._integral_angle2
               + self.Kd_angle2 * d_angle2) * v_lr_cropped

    # 2. Trong công cụ phân tích và vẽ đồ thị (plot_pid_navigation_log.py):
    err_diff = (df["angle_error"].diff() + 180.0) % 360.0 - 180.0
    d_term = kd_angle2 * err_diff
    ```

- Thực tế theo lý thuyết thì khâu D, là khâu vi phân nên phải có thời gian lấy mẫu delta T  như sau:
  - **Công thức theo lý thuyết điều khiển tự động**:
    - Dạng liên tục:

      $$
      u_D(t) = K_d \cdot \frac{de(t)}{dt}
      $$

    - Dạng rời rạc (Backward Euler) với khoảng thời gian lấy mẫu biến thiên $\Delta t_k = t_k - t_{k-1}$:

      $$
      u_D[k] = K_d \cdot \frac{e[k] - e[k-1]}{\Delta t_k}
      $$

  - **Code theo lý thuyết nếu đưa $\Delta t$ vào**:

    ```python
    # Đo thời gian thực tế dt giữa 2 frame xử lý liên tiếp:
    current_time = time.time()
    dt = (current_time - self._prev_time) if self._prev_time is not None else fallback_dt
    self._prev_time = current_time

    if dt > 0:
        # Tốc độ biến thiên sai số góc theo thời gian (de/dt, deg/s)
        err_diff = (angle_error - self._prev_angle_error + 180.0) % 360.0 - 180.0
        de_dt = err_diff / dt
        d_term = self.Kd_angle * de_dt
    else:
        d_term = 0.0

    self._prev_angle_error = angle_error
    ```

- Tuy nhiên vì trước đó khi triển khai em coi thời gian lấy mẫu là không thay đổi, và delta T = const nên có thể gộp chung với hệ số Kd để tuning chung. Và như báo cáo hôm qua thì với Kd (đã bao gồm cả Delta T) bằng `0.04` là tối ưu nhất trong khoảng từ `0.0` đến `0.08`.

> Việc coi delta T = const đối với bài toán này có thể sẽ không chính xác, vì tốc độ inference, tính toán trên từng frame ảnh không cố định. Em xin phép nhận thêm đề xuất của Thầy về vấn đề này ạ

### 2. Các phương pháp làm mịn dữ liệu Differential Data Filtering

- Theo như em tìm hiểu thì với từ khóa `Differential Data filtering for PID controllder` cho các kết quả phương pháp phổ biến như: bộ lọc thông thấp Low pass, First order fillter, Moving average fillter, EMA,...
- Em thấy Leanbot là dạng Robot vi sai, động học tương đối đơn giản nên em nghĩ phương pháp đơn giản, dễ triển khai thì phù hợp ạ. Em xin phép đề xuất dùng bộ lọc `First-order low-pass filtered Derivative` để triển khai thử trước ạ.

#### 2.1 First-order low-pass filtered Derivative

- Trong bộ điều khiển PID có thành phần D (Derivative) đạo hàm, phản ánh tốc độ thay đổi của sai số error, tuy nhiên phép đạo hàm có thể khuyếch đại nhiễu tần số cao trong tín hiệu đo. Người ta đưa ra hướng xử lí là sử dụng bộ lọc thông thấp vào riêng nhánh đạo hàm (D) này để hạn chế ảnh hưởng của nhiễu lên tín hiệu điều khiển.

- **Công thức ở dạng rời rạc nhưu sau:**

  - Với sai số $e(t)=r(t)-y(t)$, bộ lọc thông thấp bậc nhất được kết hợp với khâu đạo hàm như sau:

    $$
    G_f(s)=\frac{1}{1+T_f s},
    \qquad
    G_D(s)=K_d sG_f(s)=\frac{K_d s}{1+T_f s}.
    $$

    Bộ điều khiển PID dạng song song khi đó có biểu thức [2]:

    $$
    C(s)=K_p+\frac{K_i}{s}+\frac{K_d s}{1+T_f s},
    $$

- **Hiện tại theo trong code thì sai số được tính như sau:**

  $$
  e_\theta[k]
  =
  \operatorname{wrap}_{[-180^\circ,\,180^\circ)}
  \left(\theta[k]-\theta_{\mathrm{target}}[k]\right),
  $$

  trong đó:
  - $\theta[k]$: góc hướng robot từ kết quả hợp nhất `fused angle`.
  - $\theta_{\mathrm{target}}[k]$: góc hướng từ vị trí hiện tại đến điểm đích.
  - $e_\theta[k]$: sai số góc, tương ứng biến `angle_error`.

- **Code tính sai phân:**

  $$
  \Delta e_\theta[k]=e_\theta[k]-e_\theta[k-1],
  $$

  và thành phần D trong nhánh hiệu chỉnh góc:

  $$
  D_{\mathrm{angle2}}[k]=K_{d,\mathrm{angle2}}\Delta e_\theta[k].
  $$

- Với chu kì lấy mẫu $\Delta T = const$ nên gộp chugn vào với `Kd_angle2`.

  $$
  K_{d,\mathrm{angle2}}
  =
  \frac{K_{d,\mathrm{angle2}}^{\mathrm{chuẩn}}}{\Delta T}.
  $$

- **Bộ lọc thông thấp bậc nhất (low pass first order filtered derivative) theo như phương pháp đề xuất nhưu sau:**

  Gọi $q_\theta[k]$ là sai phân sai số góc đã lọc. Với phương pháp rời rạc hóa Backward Euler:

  $$
  \boxed{
  q_\theta[k]
  =
  \frac{T_f}{T_f+T_s}q_\theta[k-1]
  +
  \frac{T_s}{T_f+T_s}\Delta e_\theta[k]
  }
  $$

  Trong đó $T_f>0$ là hằng số thời gian lọc, cùng đơn vị giây với $T_s$ ( thời gian lấy mẫu).

  Đặt:

  $$
  \alpha=\frac{T_s}{T_f+T_s},
  $$

  ta được:

  $$
  \boxed{
  q_\theta[k]
  =
  (1-\alpha)q_\theta[k-1]
  +
  \alpha\Delta e_\theta[k]
  }
  $$

  Thành phần D sau lọc là:

  $$
  \boxed{
  D_{\mathrm{angle2}}^{\mathrm{filtered}}[k]
  =
  K_{d,\mathrm{angle2}}q_\theta[k]
  }
  $$

- **Tích hợp vào côgn thức điều khiển hiện tại nhưu sau:**

  Giữ nguyên cách tích lũy sai số trong code:

  $$
  S_{\mathrm{angle2}}[k]=S_{\mathrm{angle2}}[k-1]+e_\theta[k].
  $$

  Thay `d_angle2` bằng giá trị đã lọc $q_\theta[k]$, ta có:

  $$
  \boxed{
  \Delta v[k]
  =
  \left(
  K_{p,\mathrm{angle2}}e_\theta[k]
  +
  K_{i,\mathrm{angle2}}S_{\mathrm{angle2}}[k]
  +
  K_{d,\mathrm{angle2}}q_\theta[k]
  \right)
  v_{\mathrm{LR,cropped}}[k]
  }
  $$

  Trong đó $v_{\mathrm{LR,cropped}}[k]$ là lệnh tiến chung do nhánh điều khiển khoảng cách tính toán, sau khi giới hạn; tương ứng `v_lr_cropped`.

  Lệnh hai bánh trước bước giới hạn chung:

  $$
  \begin{aligned}
  v_L[k]&=v_{\mathrm{LR,cropped}}[k]+\Delta v[k],\\
  v_R[k]&=v_{\mathrm{LR,cropped}}[k]-\Delta v[k].
  \end{aligned}
  $$

  Sau đó, chương trình dùng `_scale_speeds` để giảm đồng thời hai lệnh theo cùng tỷ lệ nếu vượt `max_velocity`.
  Phường pháp đề xuất chỉ thay thành phần sai phân của nhánh D; giữ nguyên nhánh P, nhánh I và hệ số nhân `v_lr_cropped`. Ảnh hưởng riêng của D vào chênh lệch lệnh hai bánh là:

  $$
  \Delta v_D[k]
  =
  v_{\mathrm{LR,cropped}}[k]\,
  K_{d,\mathrm{angle2}}q_\theta[k].
  $$

## B. Khó khăn

- Em xem lại các đồ thị khâu D thì em không quan sát thấy nhiễu giật hay chattering gì nên em đang thắc mắc chút là việc thêm filter nhằm mục đích gì ạ Thầy? vì nếu làm mềm thêm tín hiệu khâu D thì sẽ làm giảm sự nhạy của Khâu D cho việc phản ứng với tốc độ thay đổi mạnh của khâu P ạ.

## C. Công việc tiếp theo

- Em xin phép nhận thêm đề xuất từ Thầy về việc setup và chụp thêm dữ liệu trainning ạ.
