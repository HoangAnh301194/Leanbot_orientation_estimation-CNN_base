# HƯỚNG DẪN SỬ DỤNG BỘ CÔNG CỤ LEANBOTTINYRC TRONG DỰ ÁN AI PID CONTROL
*(Tài liệu kỹ thuật & Báo cáo cập nhật phiên bản ngày 18/09/2026)*

---

## 1. Tổng quan Kiến trúc
Bộ công cụ **LeanbotTinyRC** là lớp giao tiếp cốt lõi giữa máy tính và robot **Leanbot** thông qua chuẩn kết nối Bluetooth Low Energy (BLE). Trong dự án `LeanbotTinyRC_AI_PIDControl`, module này đóng vai trò cơ cấu chấp hành (actuator driver) nhận lệnh điều khiển vận tốc tính toán từ thuật toán thị giác máy tính và PID controller để truyền xuống vi điều khiển xe theo thời gian thực.

```
+-----------------------------+        +--------------------------+
|  Camera (OpenVINO YOLO11n)  |        |  LeanbotTinyRC Driver    |
|  Angle Smoothing Engine     | =====> |  BLEMotorWorker (Thread) |
|  3-Phase PID Controller     |        |  LeanbotController (BLE) |
+-----------------------------+        +--------------------------+
                                                    || (BLE Serial)
                                                    \/
                                       +--------------------------+
                                       |  Leanbot Firmware        |
                                       |  (Arduino Uno / ATmega)  |
                                       |  LbMotion Driver         |
                                       +--------------------------+
```

---

## 2. Báo cáo Chi tiết Thay đổi trong Bản Cập Nhật (Commit `719c6fe`)

Bản cập nhật `719c6fe` ("update") mang đến những cải tiến quan trọng về tính ổn định của đường truyền BLE, cơ chế xác nhận lệnh (handshake) và chuẩn hóa cấu hình:

| Thành phần | File sửa đổi | Chi tiết thay đổi |
| :--- | :--- | :--- |
| **Firmware Arduino** | `LeanbotTinyRC.ino` | Thay đổi cơ chế in Serial: In `<lệnh>/START` ngay khi bắt đầu thực thi và `<lệnh>/END` ngay khi hoàn tất. Loại bỏ định dạng log cũ `RunLR(...)` để đồng bộ chuẩn hóa. |
| **Giao thức Gửi Lệnh** | `leanbotTinyRC.py` | Bổ sung hàm `sendTinyRCCommand()`: Gửi lệnh và chờ phản hồi `START` (timeout 300ms, tự động thử lại tối đa 3 lần), sau đó chờ phản hồi `END`. |
| **Bàn phím Điều khiển** | `leanbotTinyRC.py` | Chuyển sang dùng thư viện `readchar` đa nền tảng, bổ sung hàng đợi bất đồng bộ `asyncio.Queue`, hàm `flush_keyboard()` để tránh nghẽn phím, và phím `t` để test nhanh lệnh `run_fw_bw`. |
| **Lớp Controller** | `LeanbotController.py` | Hàm `__init__(leanbotid, config)` yêu cầu bắt buộc truyền cấu hình `config["LeanbotController"]`. Thêm hàng đợi 2 chiều `serialMessageFromLeanbotQueue` / `serialMessageToLeanbotQueue` và task `serialBLEHandlerTask`. |
| **Cấu hình Hệ thống** | `config.yaml` | Cập nhật version `Leanbot Tiny RC 260918:092800`, bổ sung trường cấu hình `bluetoothAdapter: "hci0"` hỗ trợ chọn adapter trên Linux. Bỏ phần compiler server cũ. |
| **Giao diện CLI** | `main.py` | Bắt buộc đối số `--configFile <path_to_config.yaml>`. Tích hợp quy trình cleanup Serial và disconnect an toàn khi tắt ứng dụng. |
| **Dependencies** | `requirements.txt` | Bổ sung thư viện `readchar`. |

---

## 3. Hướng dẫn Chi tiết Các Hàm Cốt Lõi trong `LeanbotTinyRC`

### 3.1. Hàm `sendTinyRCCommand(controller, command)`
- **Vị trí:** `LeanbotTinyRC/leanbotTinyRC.py`
- **Mục đích:** Gửi một chuỗi lệnh điều khiển xuống xe kèm cơ chế bắt tay 2 chiều và retry tự động.
- **Nguyên lý:**
  1. Đăng ký một tác vụ chờ phản hồi `<command>/END`.
  2. Gửi chuỗi lệnh `<command>\n` qua BLE và chờ phản hồi `<command>/START` trong tối đa 300 ms.
  3. Nếu không nhận được `START`, tiến hành gửi lại (retry) tối đa 3 lần.
  4. Khi đã nhận `START`, chờ tác vụ `END` hoàn tất rồi mới trả về `True`.
- **Ứng dụng:** Sử dụng trong các lệnh điều khiển tự hành cần độ tin cậy tuyệt đối như `run_fw_bw`.

### 3.2. Hàm `run_lr(controller, velocity, speed_l, speed_r)`
- **Vị trí:** `LeanbotTinyRC/leanbotTinyRC.py`
- **Tham số:**
  - `controller`: Đối tượng `LeanbotController`.
  - `velocity`: Vận tốc cơ sở (đơn vị runLR, ví dụ 1000 - 2000).
  - `speed_l, speed_r`: Hệ số tốc độ bánh trái/phải theo phần trăm hoặc tỷ lệ.
- **Cơ chế:** Tính toán tốc độ thực tế của bánh trái (`left`) và bánh phải (`right`) thông qua hàm `calc_run_lr()`, sau đó gửi chuỗi `r/<left>/<right>`.

### 3.3. Hàm `run_fw_bw(controller, speed, duration)`
- **Vị trí:** `LeanbotTinyRC/leanbotTinyRC.py`
- **Tham số:**
  - `speed`: Tốc độ động cơ khi tiến và lùi (ví dụ: `1500` hoặc `2000`).
  - `duration`: Thời gian chạy cho mỗi chiều (mili-giây, ví dụ `3000` ms = 3 giây).
- **Cơ chế:** Gửi chuỗi `rfb/<speed>/<duration>`. Vi điều khiển Leanbot sẽ tự động thực hiện:
  $$\text{Dừng xe} \longrightarrow \text{Tiến thẳng } T\text{ ms} \longrightarrow \text{Dừng xe} \longrightarrow \text{Lùi thẳng } T\text{ ms} \longrightarrow \text{Dừng xe}$$
  *Ưu điểm:* Toàn bộ chu trình tiến - lùi được vi điều khiển Leanbot tự kiểm soát bằng phần cứng (`LbMotion` + `LbDelay`), máy tính không cần gửi lệnh liên tục từng frame, loại bỏ triệt để độ trễ mạng và nghẽn hàng đợi BLE.
- **Hai phạm vi ứng dụng chính trong hệ thống AI Vision:**
  1. **Quy trình Set Target (Phím T):** Xe tự động chạy tiến lùi để camera lấy mẫu quỹ đạo và tính góc `target_heading`.
  2. **Phase 4 (Pha Test Tiến - Lùi Sau Phase 3):** Sau khi xe xoay đúng `target_heading` và ổn định ở Phase 3, hệ thống kích hoạt đúng 1 lệnh `run_fw_bw` để xe tự tiến và lùi, camera chỉ việc ghi nhận quỹ đạo đánh giá sai số đi thẳng mà không cần spam BLE.

### 3.4. Hàm `manual_control(controller)`
- **Vị trí:** `LeanbotTinyRC/leanbotTinyRC.py`
- **Mục đích:** Điều khiển xe bằng bàn phím theo thời gian thực (W: tiến, S: lùi, A: quay trái, D: quay phải, Space: dừng, E: thoát).
- **Tính năng mới:** Bấm phím **`T`** để kích hoạt test nhanh lệnh tự hành `run_fw_bw(2000, 5000)`. Sử dụng `flush_keyboard()` tự động loại bỏ các phím bấm bị trễ trong hàng đợi.

### 3.5. Lớp `LeanbotController`
- **Vị trí:** `LeanbotTinyRC/LeanbotController.py`
- **Khởi tạo:**
  ```python
  from LeanbotController import LeanbotController
  controller = LeanbotController(leanbot_id, config_dict)
  ```
- **Các phương thức quan trọng:**
  - `await controller.find()`: Quét tìm thiết bị Leanbot BLE theo tên định dạng `Leanbot <id> BLE`.
  - `await controller.connect()`: Kết nối GATT Server qua BLE.
  - `await controller.send(command, response=False)`: Gửi chuỗi ký tự xuống BLE Serial.
  - `controller.openSerial()` / `controller.clearSerialState()`: Mở và xóa hàng đợi thông điệp Serial.
  - `controller.startSerialBLEHandler()`: Khởi chạy background task tiếp nhận thông điệp từ vi điều khiển.
  - `await controller.killSerialBLEHandlerTask()`: Hủy task tiếp nhận thông điệp khi đóng ứng dụng.
  - `await controller.disconnect()`: Ngắt kết nối BLE an toàn.

---

## 4. Giao thức Truyền thông Serial BLE (Protocol Reference)

### 4.1. Lệnh từ Máy tính gửi xuống Leanbot (TX)
Tất cả các lệnh được kết thúc bằng ký tự xuống dòng `\n`:
1. **Lệnh quay động cơ độc lập:**
   ```
   r/<speed_left>/<speed_right>\n
   ```
   *Ví dụ:* `r/1200/-1200\n` (quay tại chỗ ngược chiều kim đồng hồ với tốc độ 1200).
2. **Lệnh tiến - lùi tự hành (Set Target & Test Quỹ đạo):**
   ```
   rfb/<speed>/<duration_ms>\n
   ```
   *Ví dụ:* `rfb/1500/3000\n` (tiến 3 giây với tốc độ 1500, sau đó lùi 3 giây với tốc độ 1500).

### 4.2. Phản hồi từ Leanbot gửi lên Máy tính (RX)
1. **Bắt đầu thực thi:** `<command>/START\n` (ví dụ: `rfb/1500/3000/START`).
2. **Hoàn thành thực thi:** `<command>/END\n` (ví dụ: `rfb/1500/3000/END`).

---

## 5. Tích hợp vào Hệ thống AI Camera PID Controller

Trong hệ thống thị giác máy tính (`leanbotCameraController.py` và `test_phase3_pid.py`), để tránh việc vòng lặp giao diện GUI của OpenCV và COM STA trên hệ điều hành Windows xung đột với luồng `asyncio` của BLE, toàn bộ quá trình giao tiếp BLE được đóng gói trong class **`BLEMotorWorker`**:

```python
class BLEMotorWorker:
    """Chạy giao tiếp BLE trên một luồng nền riêng biệt, non-blocking."""
    def __init__(self, leanbot_id: int):
        self.leanbot_id = leanbot_id
        self.cmd_queue = queue.Queue(maxsize=1)
        self.running = True
        self.connected = False
        self.leanbot = None
        self.thread = threading.Thread(target=self._worker_thread, daemon=True)
        self.thread.start()
```

### Điểm cải tiến tương thích phiên bản mới:
- Tự động nạp cấu hình `LeanbotController` từ file `LeanbotTinyRC/config.yaml` thông qua hàm `load_leanbot_config()`.
- Hỗ trợ giá trị fallback mặc định `{ "LeanbotBLE": { "bluetoothAdapter": None } }` khi chạy trên hệ điều hành Windows.
- Tự động khởi chạy `startSerialBLEHandler()` và dọn dẹp tài nguyên `killSerialBLEHandlerTask()` khi ngắt kết nối.

---

## 6. Sổ tay Lệnh Chạy (Cheat Sheet)

### 6.1. Chạy điều khiển thủ công bằng bàn phím (Tool gốc)
```powershell
cd LeanbotTinyRC
python main.py --leanbot 343944 --configFile config.yaml
```
*(Phím W/S/A/D để lái xe, phím T để test tiến lùi 5s, phím E để thoát).*

### 6.2. Chạy Test Xoay Góc PID Phase 3 Trực Tiếp (Không log CSV, Không vẽ Plot)
```powershell
# Test xoay xe tới góc 90 độ với xe 343944
python test_phase3_pid.py --target-heading 90.0 --ble 343944 --source 1

# Test xoay xe tới góc -45 độ với Kp3/Kd3 tùy chỉnh
python test_phase3_pid.py --target-heading -45.0 --ble 343944 --kp3 12.0 --kd3 0.05
```
*(Phím S để reset test lại, phím P để tạm dừng động cơ, phím Q để thoát).*

### 6.3. Chạy Kiểm tra Logic Toán học (Unit Test)
```powershell
python test_phase3_pid.py --unit-test
```

### 6.4. Chạy Toàn Bộ Hệ Thống Điều Hướng AI Vision PID (Phím T để Set Target)
```powershell
python leanbotCameraController.py --show --source 1 --ble 343944
```
*(Phím T để Set Target với lệnh `rfb` gửi 1 lần duy nhất, phím S để bắt đầu bám mục tiêu).*
