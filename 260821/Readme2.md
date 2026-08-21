# Báo cáo công việc ngày 21/08/2026 (tiếp theo)

## A. Công việc đã làm
- Nhận code LeanbotTinyRC từ anh Thế Anh 
- Đọc, tìm hiểu code và cách sử dụng .


### 1. Tiếp nhận Code LeanbotTinyRC từ anh Thế Anh. 
- Cấu trúc các file bao gồm:
    - [`config.yaml`](LeanbotTinyRC/config.yaml): File cấu hình vận tốc, phím bấm điều khiển và server biên dịch.
    - [`LeanbotController.py`](LeanbotTinyRC/LeanbotController.py): Lớp điều phối trung gian nạp config, quản lý BLE và queue tin nhắn.
    - [`leanbotTinyRC.py`](LeanbotTinyRC/leanbotTinyRC.py): Xử lý bắt phím điều khiển và đóng gói chuỗi lệnh vận tốc `run_lr`.
    - [`LeanbotTinyRC.ino`](LeanbotTinyRC/LeanbotTinyRC.ino): Firmware Arduino nạp vào Leanbot nhận lệnh Serial/BLE điều khiển động cơ.
    - [`leanbot_ble.py`](LeanbotTinyRC/leanbot_ble.py): Driver giao tiếp Bluetooth Low Energy (BLE) qua thư viện `bleak` và OTA uploader.
    - [`leanbotCameraController.py`](LeanbotTinyRC/leanbotCameraController.py): Code Camera ROI tracking nhận diện robot và tính góc định hướng.
    - [`logs.py`](LeanbotTinyRC/logs.py): Module ghi log bất đồng bộ ra console/file.
    - [`main.py`](LeanbotTinyRC/main.py): File chạy chính (Entry point) kết nối BLE và khởi động RC.
    - [`requirements.txt`](LeanbotTinyRC/requirements.txt): Danh sách thư viện phụ thuộc (`bleak`, `pyyaml`).

- Các bước thực hiện sau khi tiếp nhận code và kiểm thử cách điều khiển Leanbot như sau:
    - Nạp code [`LeanbotTinyRC.ino`](LeanbotTinyRC/LeanbotTinyRC.ino) cho Leanbot bằng IDE Pythaverse.
    - Tạo môi trường ảo (nếu chưa có):
        ```powershell
        python -m venv .venv 
        ```
    - Cài đặt requirements:
        ```powershell
        python -m pip install -r requirements.txt
        ```
    - Chạy file [`main.py`](LeanbotTinyRC/main.py):
        ```powershell
        python main.py --leanbot <mã tên leanbot>
        ```
- Sử dụng các phím trên bàn phím để điều khiển Leanbot :
    - Nút số 8 để di chuyển tới ( Forward )
    - Nút số 2 để di chuyển lùi ( Backward )
    - Nút số 4 để di chuyển sang trái ( Turn Left )
    - Nút số 6 để di chuyển sang phải ( Turn Right )
    - Nút số 1 để di chuyển lùi sang trái ( Back Left )
    - Nút số 3 để di chuyển lùi sang phải ( Back Right )
    - Nút số 7 để di chuyển tới trái ( Forward Left )
    - Nút số 9 để di chuyển tới phải ( Forward Right )
    - Nút số 5 để dừng ( Stop )
- Leanbot sẽ dừng sau 3 giây nếu không có lệnh điều khiển được gửi tới.


### 2. Cách máy tính gửi lệnh điều khiển Leanbot

#### 2.1. File code `leanbot_ble.py`
- Link code: [`LeanbotTinyRC/leanbot_ble.py`](LeanbotTinyRC/leanbot_ble.py)
- File code này đã bao gồm cả phần OTA nạp code cho Leanbot thông qua BLE 
- Trong phần này để ứng dụng cho việc gửi lệnh điều khiển cho Leanbot thì chỉ cần dùng hàm send() 
- Hàm send() được mô tả như sau : 
```python
    async def send(self, msg, response=True):
        if self.__leanbotClient is None:
            raise RuntimeError("BLE client not connected")

        if isinstance(msg, str):
            data = msg.encode()
        else:
            data = bytes(msg)

        await self.__leanbotClient.write_gatt_char(self.CHAR_UUID, data, response)
```
- **Các tham số đầu vào của hàm `send(msg, response=True)`**:
  - `msg` (`str` | `bytes`): Chuỗi string (ví dụ `"r/2000/2000\n"`) hoặc mảng byte nhị phân. Hàm sẽ tự động mã hoá sang dạng byte UTF-8.
  - `response` (`bool`, mặc định `True`):
    - `True` (Write with Response): Có chờ xác nhận ACK từ robot, đảm bảo tin cậy.
    - `False` (Write without Response): Gửi trực tiếp không chờ ACK, tối ưu độ trễ thấp nhất cho điều khiển thời gian thực (RC).
- **Cấu hình truyền dữ liệu BLE**:
  - Gửi qua Characteristic UUID chuẩn UART: `0000ffe1-0000-1000-8000-00805f9b34fb`.
  - Dữ liệu được module BLE nhận và đẩy thẳng vào cổng UART Serial của Arduino Nano Leanbot.

#### 2.2. File code `LeanbotController.py` & `leanbotTinyRC.py` 
- Link code `LeanbotController.py`: [`LeanbotTinyRC/LeanbotController.py`](LeanbotTinyRC/LeanbotController.py)
- Link code `leanbotTinyRC.py`: [`LeanbotTinyRC/leanbotTinyRC.py`](LeanbotTinyRC/leanbotTinyRC.py)
- **Cơ chế bắt phím và tạo chuỗi lệnh (`leanbotTinyRC.py`)**:
  - Hàm `manual_control()` lắng nghe các sự kiện phím bấm `1, 2, ... 8, 9` thông qua `msvcrt.getwch()` (non-blocking) và tra cứu bảng `KeyMap` trong `config.yaml` để lấy hệ số tốc độ `speed_l`, `speed_r`.
  - Hàm `run_lr()` tính toán tốc độ thực tế của bánh trái, bánh phải và đóng gói thành chuỗi lệnh dạng `"r/<left_speed>/<right_speed>\n"`:
  ```python
  async def run_lr(
      controller,
      velocity: int,
      speed_l: int,
      speed_r: int,
  ) -> None:
      left, right = calc_run_lr(
          velocity,
          speed_l,
          speed_r,
      )

      command = f"r/{left}/{right}\n"
      log("TX", command.rstrip())

      await controller.send(
          command,
          response=False,
      )
  ```

- Gửi chuỗi lệnh điều khiển thông qua BLE: 
  - `LeanbotController` sở hữu đối tượng `self.leanbot = LeanbotBLE(...)` (quan hệ Composition / Delegation) và cung cấp hàm `send()` để ủy quyền chuyển tiếp dữ liệu xuống tầng phát sóng Bluetooth:
  ```python
  async def send(self, data, response=True):
      await self.leanbot.send(
          data,
          response=response,
      )
  ```

#### 2.3. File code `LeanbotTinyRC.ino`
- Link code: [`LeanbotTinyRC/LeanbotTinyRC.ino`](LeanbotTinyRC/LeanbotTinyRC.ino)
- **nhận và giải mã chuỗi lệnh (`loop`)**:
  - Vòng lặp `loop()` liên tục đọc dữ liệu nhận được từ cổng Serial (UART kết nối với module BLE) cho tới khi gặp ký tự xuống dòng `\n`.
  - Tách chuỗi theo dấu `/` để lấy mã lệnh `cmd` (lệnh `"r"`) và tham số `args` (ví dụ `"2000/2000"`):
  ```cpp
  void loop() {
    // Chờ có command từ Serial trong tối đa 3000 ms
    while (waitSerialCommand(3000)) {
      String message = Serial.readStringUntil('\n');
      message.trim();

      int pos1 = message.indexOf('/');
      if (pos1 < 0)
        continue;

      String cmd  = message.substring(0, pos1);
      String args = message.substring(pos1 + 1);

      // Thực thi lệnh chạy động cơ nếu là lệnh "r"
      if (cmd == "r") { // run RL
        Leanbot_run(args);
      }
    }

    // Không có command mới trong 3 giây -> tự động dừng
    stopLeanbot();
  }
  ```

- **Cơ chế điều khiển động cơ và ngắt an toàn (`Leanbot_run` & `stopLeanbot`)**:
  - Hàm `Leanbot_run(args)` phân tách giá trị chuỗi thành 2 số nguyên `left` và `right`, sau đó gọi hàm phần cứng `LbMotion.runLR(left, right)` để điều khiển tốc độ 2 bánh xe.
  - Hàm `stopLeanbot()` tự động phanh dừng 2 bánh (`LbMotion.runLR(0, 0)`) khi quá 3 giây mà robot không nhận được lệnh mới:
  ```cpp
  void Leanbot_run(String args) {
    int pos = args.indexOf('/');
    if (pos < 0)
      return;

    int left  = args.substring(0, pos).toInt();
    int right = args.substring(pos + 1).toInt();

    Serial.print("RunLR(");
    Serial.print(left);
    Serial.print(", ");
    Serial.print(right);
    Serial.println(")");

    LbMotion.runLR(left, right);
  }

  void stopLeanbot(void) {
    Serial.println("Leanbot Stop");
    LbMotion.runLR(0, 0);
  }
  ```

### 3. Hướng triển khai 

#### 3.1. Thu thập dữ liệu & Tính toán góc hợp nhất `FusedAngle`
- **Bước 1 (Trích xuất dữ liệu gốc từ Camera)**:
  - Sử dụng Camera và mô hình YOLO / OpenVINO trong `leanbotCameraController.py` để trích xuất toạ độ tâm `(x, y)` và góc hướng thô `Raw Model Angle`.
- **Bước 2 (Làm mượt và Hợp nhất góc FusedAngle)**:
  - Làm mượt góc `RawModelAngle` bằng đa thức bậc 2 (Polynomial Degree 2) với kích thước cửa sổ `W = 18` mẫu, điểm đánh giá trễ `index = -4` để thu được `ModelAngle`.
  - Fit đa thức bậc 2 trên chuỗi toạ độ quỹ đạo `(x(t), y(t))` trong cửa sổ `W = 18`, lấy đạo hàm `(dx, dy)` tại `index = -4` để tính góc tiếp tuyến `TrajectoryAngle` và vận tốc tức thời `v`:
  ```math
  \theta_{\text{traj}} = \operatorname{atan2}(-dy, dx) \cdot \frac{180^\circ}{\pi}
  ```
  ```math
  v = \frac{\sqrt{dx^2 + dy^2}}{W - 1} \quad (\text{px/frame})
  ```
  - Tính hệ số trọng số thích nghi $x$ theo vận tốc với $K = 3.0\text{ px/frame}$:
  ```math
  x = \frac{K}{K + v}
  ```
  - Tính góc `FusedAngle`:
  ```math
  \theta_{\text{fused}} = x \cdot \theta_{\text{model}} + (1 - x) \cdot \theta_{\text{traj}}
  ```

#### 3.2. Mô hình toán học Leabot có 2 bánh vi sai & Hàm truyền hệ thống
- **1. Mô hình Động học**:
  - Robot Leanbot di chuyển bằng 2 bánh xe hay còn gọi là hệ thống bánh vi sai, 2 bánh cách nhau 1 khoảng L 
  - Mối quan hệ giữa vận tốc dài $v$, vận tốc góc $\omega$ của robot và vận tốc 2 bánh xe ($v_L, v_R$) như sau : 
    - *Động học thuận (Forward Kinematics)*:
      ```math
      v = \frac{v_R + v_L}{2}, \quad \omega = \frac{v_R - v_L}{L}
      ```
    - *Động học ngược (Inverse Kinematics)*:
      ```math
      \begin{cases}
      v_L = v - \dfrac{\omega \cdot L}{2} = u_v - u_\theta \\[8pt]
      v_R = v + \dfrac{\omega \cdot L}{2} = u_v + u_\theta
      \end{cases}
      ```
  - Trong đó:
    - $u_v = v$: Thành phần vận tốc tiến đồng pha (kéo cả 2 bánh cùng tiến).
    - $u_\theta = \dfrac{\omega \cdot L}{2}$: Thành phần vận tốc vi sai ngược pha (tạo mô-men xoay chuyển hướng). 

- **2. Hàm truyền đối tượng (Transfer Function)**:
  - *Hàm truyền động học góc xoay*: Vì $\omega(t) = \dot{\theta}(t) = \dfrac{v_R(t) - v_L(t)}{L} = \dfrac{\Delta v(t)}{L}$, biến đổi Laplace ta có:
    ```math
    G_\theta(s) = \frac{\Theta(s)}{\Delta V(s)} = \frac{1}{L \cdot s}
    ```
    *(Khâu tích phân thuần túy $1/s$)*.
  - *Hàm truyền động cơ chấp hành DC*:
    ```math
    G_m(s) = \frac{V(s)}{U(s)} = \frac{K_m}{\tau s + 1}
    ```
  - *Hàm truyền vòng hở tổng thể kênh góc xoay*:
    ```math
    G(s) = \frac{\Theta(s)}{U_\theta(s)} = \frac{K}{s(\tau s + 1)} \quad \left(\text{với } K = \frac{K_m}{L}\right)
    ```

- Hàm truyền sẽ để mô tả toán học chuyển động của Leanbot, có thể sử dụng Matlab simulink để mô phỏng từ đó chọn ra hệ số PID phù hợp . 

#### 3.3. Bộ điều khiển phản hồi kín (Closed-Loop P/PID Controller)
- **1. Tính toán sai số**:
  - Sai số góc (chuẩn hoá về khoảng $[-180^\circ, +180^\circ]$):
    ```math
    e_\theta = \operatorname{wrap\_to\_180}(\theta_{\text{target}} - \theta_{\text{fused}})
    ```
  - Sai số khoảng cách tới toạ độ mục tiêu $(x_{\text{target}}, y_{\text{target}})$:
    ```math
    e_d = \sqrt{(x_{\text{target}} - x)^2 + (y_{\text{target}} - y)^2}
    ```
- **2. Bộ điều khiển tỷ lệ (P Controller)**:
  - Tín hiệu điều khiển góc xoay $u_\theta$ (vận tốc góc / độ lệch tốc độ giữa 2 bánh):
    ```math
    u_\theta = K_p^\theta \cdot e_\theta
    ```
  - Tín hiệu điều khiển tiến $u_v$ (vận tốc dài tiến thẳng):
    ```math
    u_v = K_p^v \cdot e_d
    ```
- **3. Phân phối vận tốc cho 2 bánh xe vi sai**:
  ```math
  \begin{cases}
  v_L = u_v - u_\theta \\
  v_R = u_v + u_\theta
  \end{cases}
  ```
  *(Các giá trị $v_L, v_R$ được bão hòa trong khoảng an toàn $[-V_{\max}, V_{\max}]$)*.
- **4. Gửi lệnh qua BLE**:
  - Đóng gói thành chuỗi lệnh: `r/<v_L>/<v_R>\n` (ví dụ `r/1500/1800\n`) và gọi `controller.send(command, response=False)` để truyền không dây tới Leanbot.

- **Ví dụ**
- *Giả thiết cấu hình thực nghiệm*: $K_p^\theta = 20$, $K_p^v = 15$, giới hạn tốc độ $V_{\max} = 2000$.
- **Ví dụ Leanbot chỉ xoay góc $e_\theta = 50^\circ$, đứng tại chỗ $e_d = 0$**:
  ```math
  \begin{aligned}
  u_\theta &= 20 \times 50 = 1000 \\
  u_v &= 15 \times 0 = 0 \\
  v_L &= u_v - u_\theta = 0 - 1000 = -1000 \\
  v_R &= u_v + u_\theta = 0 + 1000 = 1000
  \end{aligned}
  ```
  $\rightarrow$ Chuỗi lệnh gửi BLE: `r/-1000/1000\n` (Leanbot xoay trái tại chỗ với vận tốc 1000).

- **Ví dụ Leanbot chỉ đi thẳng khoảng cách $e_d = 100\text{ px}$, góc chuẩn hướng $e_\theta = 0^\circ$**:
  ```math
  \begin{aligned}
  u_\theta &= 20 \times 0 = 0 \\
  u_v &= 15 \times 100 = 1500 \\
  v_L &= u_v - u_\theta = 1500 - 0 = 1500 \\
  v_R &= u_v + u_\theta = 1500 + 0 = 1500
  \end{aligned}
  ```
  $\rightarrow$ Chuỗi lệnh gửi BLE: `r/1500/1500\n` (Leanbot tiến thẳng tới mục tiêu với vận tốc 1500).

## B. Khó khăn 
- Hiện tại em chưa rõ là khi chạy inference thì góc FusedAngle sẽ được tính từ các dữ liệu góc Raw model và góc tiếp tuyến quỹ đạo với cấu hình smooth như thế nào ạ. 
- Cấu hình em sử dụng ở phần 3. Hướng thực hiện có đúng không ạ ?
- Em xin phép nhận ý kiến từ Thầy ạ. 

## C. Công việc tiếp theo.
- Thực hiện kết hợp với code Camera để điều khiển Leanbot xoay 90 độ 
- Thực hiện điều khiển Leanbot tới tọa độ chỉ định.