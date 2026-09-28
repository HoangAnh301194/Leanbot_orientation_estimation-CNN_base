# Triển khai khảo sát heading: cộng dồn 25 step, tăng thời gian 400 ms

Cập nhật: 28/09/2026. Căn cứ: `leanbot_heading_experiment_plan.md` do người dùng cung cấp.

## 1. Phạm vi và cách hiểu tham số

- Chương trình riêng: `LeanbotTinyRC_AI_PIDControl/heading_experiment.py`.
- Không sửa PID, firmware, cấu hình target hoặc cơ chế lost-tracking dataset hiện có.
- `steps` trong CSV là **tổng step đã ra lệnh kể từ đầu session**, không phải góc quay đo được.
- Các mốc: **0, 25, 50, 75, 100, 125, 150, 175, 200**.
- Mốc 0 đo hướng hiện tại, không phát lệnh quay. Mỗi mốc tiếp theo chỉ gửi `spst/50/25` một lần.
- Tổng lệnh quay: **8 × 25 = 200 step**, không phải cộng các lệnh 25 + 50 + ... + 200 = 900.
- `intervalMs`: **1000, 1400, 1800, 2200, 2600, 3000 ms**.
- Mỗi mốc step có 6 phép đo; toàn bộ session có **9 × 6 = 54 phép đo**.
- Mỗi phép đo gửi `rfb/2000/intervalMs`: tiến một khoảng `intervalMs`, lùi một khoảng `intervalMs`.
- Không quay lại hướng ban đầu giữa các phép đo. Mỗi session mới lấy tư thế hiện tại làm mốc 0.

## 2. Thành phần triển khai

| File | Trách nhiệm |
|---|---|
| `heading_measurement.py` | `HeadingMeter.measureHeading(intervalMs)`, Linear Fit, circular mean, chờ START/END |
| `heading_hardware.py` | Camera frame mới nhất, inference FULL 640/ROI 160, kết nối và lệnh BLE |
| `heading_experiment.py` | Tham số CLI, lịch cộng dồn, tuần tự hóa chuyển động, dừng khi lỗi |
| `heading_report.py` | CSV từng phép đo, quỹ đạo, tổng hợp và 3 biểu đồ |
| `test_heading_measurement.py` | Kiểm thử thuật toán heading và giao thức lệnh |
| `test_heading_experiment.py` | Kiểm thử lịch, CSV, biểu đồ và dừng khi đo lỗi |
| `test_heading_hardware.py` | Kiểm thử tọa độ FULL/ROI, hàng đợi camera và cleanup BLE bằng mock |

Các file Python nằm trong `LeanbotTinyRC_AI_PIDControl`.

## 3. Luồng một phép đo

1. Yêu cầu ba frame liên tiếp detect hợp lệ trước khi phát lệnh chuyển động.
2. Đăng ký bộ chờ cả `START` và `END` trước khi gửi lệnh BLE.
3. Chỉ gửi lệnh **một lần**. Không tự retry lệnh quay khi mất ACK, tránh quay lặp ngoài ý muốn.
4. Trong khi firmware chạy tiến–lùi, camera thu frame liên tục; inference lấy frame mới nhất, không tích lũy hàng đợi ảnh cũ.
5. Chỉ dùng mẫu thuộc đoạn tiến: `START + guard_ms` đến `START + intervalMs - guard_ms`. Mặc định loại 150 ms ở mỗi đầu đoạn tiến.
6. Fit độc lập `x(t)` và `y(t)` theo timestamp thực. Heading là `atan2(-dy/dt, dx/dt)`, đơn vị độ trong `[-180, 180)`.
7. Chờ đủ `END`, tính chất lượng fit, lưu CSV, nghỉ ổn định 300 ms rồi mới chạy phép tiếp theo.

`await meter.measureHeading(intervalMs)` trả về heading dạng `float`; thông tin đầy đủ nằm trong `meter.last_result`.
Nếu fit không hợp lệ, heading là `NaN` kèm trạng thái; chương trình khảo sát lưu dòng lỗi rồi dừng.
Lỗi camera/BLE phát sinh exception, vẫn giữ kết quả và dữ liệu đã thu trước đó.

Không dùng nhãn góc YOLO để thay thế kết quả Linear Fit. YOLO chỉ cung cấp tâm bbox để xây dựng quỹ đạo.
Không gộp đoạn lùi vào fit theo thời gian vì vận tốc đổi dấu có thể triệt tiêu đoạn tiến.

### Điều kiện hợp lệ mặc định

- Ít nhất 5 mẫu tâm hợp lệ trong cửa sổ fit.
- Mẫu hợp lệ phủ ít nhất 50% thời gian cửa sổ fit.
- Tỷ lệ mất detection trong các frame đã inference của cửa sổ fit không quá 50%.
- Quãng dịch chuyển theo đường fit ít nhất 5 pixel.
- Có đủ ACK `START` và `END`.

Tỷ lệ mất tracking không tính các frame camera được bỏ qua do inference chậm; số mẫu và độ phủ thời gian được kiểm tra riêng.
RMSE được báo cáo, chưa áp ngưỡng loại bỏ mặc định.

### Giới hạn đồng bộ cần ghi nhận trong báo cáo

Firmware hiện tại chỉ báo START/END toàn lệnh, chưa báo chính xác thời điểm motor bắt đầu tiến hoặc đảo chiều.
Vì vậy cửa sổ tiến được ước lượng từ START và `intervalMs`, có vùng loại bỏ đầu/cuối.
Timestamp ảnh là thời điểm máy tính nhận frame, không phải timestamp phơi sáng của camera.
Cần kiểm tra `heading_samples.csv`, độ trễ camera và tăng `--guard-ms` nếu thấy mẫu phanh/đảo chiều lọt vào fit.

## 4. Cách chạy

Chạy PowerShell từ thư mục dự án:

```powershell
cd D:\PTIT\DTT\Nguyen_Huu_Hoang_Anh\260925
```

### Xem lịch, không kết nối robot

```powershell
..\venv\Scripts\python.exe LeanbotTinyRC_AI_PIDControl\heading_experiment.py --dry-run
```

Không có `--run` thì mặc định chỉ xem lịch. Không mở camera, không BLE, không tạo kết quả đo giả.

### An toàn trước khi chạy thật

**Chỉ dùng `--run` sau khi đã chuẩn bị vùng chạy trống đủ rộng, kiểm tra camera và có công tắc dừng vật lý trong tầm tay.**
Không chạy đồng thời với `leanbotCameraController.py` hoặc chương trình khác đang điều khiển cùng robot.
Không sử dụng video ghi sẵn làm nguồn tracking để điều khiển robot thật.

Firmware thực thi `rfb` và `spst` theo kiểu chặn vòng đọc Serial. Ctrl+C có thể chỉ đưa lệnh dừng vào hàng đợi;
robot có thể nhận lệnh dừng sau khi chuyển động hiện tại kết thúc. **Ctrl+C không thay thế dừng khẩn cấp vật lý.**
Chương trình không phát hiện vật cản hoặc mép bàn, không tự đưa robot về vị trí ban đầu khi quỹ đạo tiến–lùi bị trôi.

### Thử rút gọn: 4 phép đo

Nhập đúng ID Leanbot; thay camera index nếu thiết bị không nằm ở index 1.

```powershell
$leanbotId = [int](Read-Host 'Leanbot ID')
..\venv\Scripts\python.exe LeanbotTinyRC_AI_PIDControl\heading_experiment.py --run --ble $leanbotId --source 1 --max-steps 25 --interval-stop 1400
```

Sau lần thử, đặt lại robot về tư thế tham chiếu mong muốn trước khi bắt đầu session đầy đủ.

### Chạy đầy đủ: 54 phép đo

```powershell
..\venv\Scripts\python.exe LeanbotTinyRC_AI_PIDControl\heading_experiment.py --run --ble $leanbotId --source 1 --max-steps 200 --step-increment 25 --interval-start 1000 --interval-stop 3000 --interval-step 400
```

Riêng thời gian tiến–lùi theo lệnh là 216 giây; thời gian thực còn gồm quay, phanh, chờ ổn định, inference và BLE.
Khoảng tham số phải chạm đúng mốc cuối; chương trình báo lỗi thay vì âm thầm bỏ mốc không chia hết.

## 5. Đầu ra

Mỗi lần chạy thật tạo thư mục riêng `heading_experiments/session_<timestamp>_<id>/`, không ghi đè session cũ.

| File | Nội dung |
|---|---|
| `session.json` | Tham số, lịch, quy ước góc/timestamp, trạng thái hoàn thành hoặc lý do dừng |
| `heading_measurements.csv` | `steps`, `spin_delta_steps`, `intervalMs`, `measuredHeading_deg`, `duration_s`, chất lượng và lỗi |
| `heading_summary.csv` | Số phép thử/hợp lệ, circular mean heading, góc tương đối mốc 0, thời gian trung bình |
| `heading_samples.csv` | Timestamp, tọa độ tâm, detection, FULL/ROI, dấu hiệu mẫu thuộc cửa sổ fit |
| `heading_spins.csv` | Mỗi lệnh quay tăng thêm, tổng step, thời gian và lỗi ACK |
| `ble_commands.log` | Log giao tiếp với robot |
| `heading_vs_interval.png` | Heading theo interval, một ô cho mỗi mốc step, trục y riêng để thấy chênh lệch nhỏ |
| `mean_heading_vs_steps.png` | Circular mean heading theo tổng step cộng dồn |
| `duration_vs_interval.png` | Thời gian từng phép đo; tham chiếu `2 × intervalMs` |

- `duration_s` đo toàn bộ lời gọi `measureHeading`: gửi lệnh, thu quỹ đạo, chờ END, fit và xử lý mẫu cuối.
- Nếu `tracking_not_ready`, hàm đo chưa được gọi: `duration_s=NaN`; thời gian kiểm tra ban đầu ghi trong `error`.
- `command_duration_s` đo từ bắt đầu thực hiện lệnh BLE đến ACK END; không thay thế `duration_s`.
- CSV giữ góc wrapped; biểu đồ unwrap để tránh đường nhảy giả ở biên ±180°.
- Circular mean chỉ dùng phép đo `status=ok`. Trung bình thời gian dùng tất cả phép có thời gian hữu hạn.
- Tập số liệu thực phải được thu bằng robot; kiểm thử mô phỏng không được dùng làm kết quả thực nghiệm.

Tạo lại biểu đồ từ một session đã có CSV:

```powershell
..\venv\Scripts\python.exe LeanbotTinyRC_AI_PIDControl\heading_experiment.py --plot-only .\heading_experiments\session_THAY_BANG_TEN_THUC
```

## 6. Kiểm thử phần mềm

```powershell
..\venv\Scripts\python.exe -B -m unittest discover -s LeanbotTinyRC_AI_PIDControl -p 'test_heading_*.py' -v
```

Kiểm thử không phát lệnh BLE thật. Kiểm chứng trên thiết bị vẫn cần: chiều quay, độ trễ ACK/camera,
vùng fit đoạn tiến, chất lượng tracking, độ trôi vị trí và khả năng dừng vật lý.

Kết quả kiểm tra phần mềm ngày 28/09/2026: **33/33 test đạt**. Hai model OpenVINO FULL/ROI đã chạy
inference offline trên CPU; camera thật và BLE không được mở. Ba biểu đồ đã được kiểm tra bằng
dữ liệu mô phỏng trong thư mục tạm, không phải số liệu thực nghiệm của robot.
