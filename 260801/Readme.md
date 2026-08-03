# Báo cáo công việc ngày 01/08/2026
## A. Công việc đã làm 
- Làm mượt quỹ đạo Leanbot bằng **Ellipse Fitting** sử dụng **Polynomial Regression bậc 2** trên phân đoạn **phase angle**. 

## 1. File Code sử dụng và các Log csv 

- [tools/plot_ellipse_smooth_segments.py](tools/plot_ellipse_smooth_segments.py): chọn đoạn ngẫu nhiên gồm 45 điểm, kiểm tra dữ liệu, fit polynomial, dựng điểm smooth và xuất đồ thị.
- [`benchmark/roi_tracking_runlr_2000_1000.csv`](benchmark/roi_tracking_runlr_2000_1000.csv): dữ liệu quỹ đạo trường hợp vận tốc di chuyển `LbMotion.runLR(2000,1000)`.
- [`benchmark/roi_tracking_runlr_2000_1300.csv`](benchmark/roi_tracking_runlr_2000_1300.csv): dữ liệu quỹ đạo trường hợp vận tốc di chuyển `LbMotion.runLR(2000,1300)`.
- [`benchmark/roi_tracking_runlr_2000_1600.csv`](benchmark/roi_tracking_runlr_2000_1600.csv): dữ liệu quỹ đạo trường hợp vận tốc di chuyển `LbMotion.runLR(2000,1600)`.

## 2. Quy trình xử lý

### Bước 1: Đọc các cột dữ liệu cần thiết
- `x_center`
- `y_center`
- `frame_id`
- `tracking_lost`
### Bước 2: Chọn đoạn ngẫu nhiên 45 điểm
- Có đúng 45 điểm liên tục.
- `frame_id` tăng từng đơn vị.
- Không có tọa độ `NaN` hoặc vô hạn.
- Không có frame `tracking_lost`.
- Không chồng lấn với đoạn khác.

> Random seed mặc định là `42` để có thể tái tạo kết quả. ( có thể dùng seed khác , seed chỉ để cố định trường hợp ngẫu nhiên khi cần tái tạo lại thí nghiệm mà không ảnh hưởng đến kết quả chung)
### Bước 3: Fit và kiểm tra ellipse
- Ellipse được fit bằng `cv2.fitEllipse()`.
- Kết quả gồm:
    - Tâm `(cx, cy)`.
    - Bán trục lớn `a`.
    - Bán trục nhỏ `b`.
    - Góc phase `theta`.
    - Sai số RMS.

Đoạn bị loại nếu ellipse không đạt các điều kiện:

| Điều kiện | Ngưỡng |
|---|---:|
| Bán trục lớn / độ dịch chuyển đoạn | `<= 5.0` |
| Bán trục lớn / bán trục nhỏ | `<= 20.0` |
| Độ dịch chuyển tối thiểu | `>= 5 px` |
| Sai số RMS | `<= 0.35` |
| Cung góc bao phủ (arc coverage) | `>= 60°` |

### Bước 4: Tính phase angle

Điểm `(x, y)` được chuyển về hệ tọa độ local của ellipse:

```python
dx = x - cx
dy = y - cy

x_local = dx*cos(theta) + dy*sin(theta)
y_local = -dx*sin(theta) + dy*cos(theta)
```

Phase angle chuẩn của ellipse:

```python
phase = atan2(-y_local / b, x_local / a)
```

Quy ước:

- `0°` nằm trên trục lớn hướng sang phải.
- Chiều dương là ngược chiều kim đồng hồ trong hệ Decaster
- `numpy.unwrap()` được dùng để tạo continuous phase angle, loại bước nhảy khi góc đi qua biên `0°/360°`.


### Bước 5: Làm mượt phase angle

Vẽ ra Polynomial( đa thức) bậc 2 được fit trên 45 continuous phase angle:

```text
smooth_phase(i) = c2*i^2 + c1*i + c0
```

Trong đó `i` chạy từ `0` đến `44`.

### Bước 6: Dựng lại 45 điểm smooth

Tọa độ local của điểm smooth:

```text
x_local_smooth = a*cos(smooth_phase)
y_local_smooth = -b*sin(smooth_phase)
```

Chuyển về hệ tọa độ ảnh:

```text
x_smooth = cx + x_local_smooth*cos(theta) - y_local_smooth*sin(theta)
y_smooth = cy + x_local_smooth*sin(theta) + y_local_smooth*cos(theta)
```

Kết quả gồm đúng 45 điểm smooth nằm trên ellipse.

## 4. Đồ thị đầu ra

Mỗi đoạn tạo hai ảnh.

### 4.1. Continuous phase angle

Đồ thị gồm:

- 45 continuous phase angle gốc.
- 45 smooth continuous phase angle từ polynomial bậc 2.

Tên file:

```text
<csv_name>_seg<N>_phase_angle.png
```

### 4.2. Quỹ đạo

Đồ thị gồm:

- 45 điểm gốc.
- Ellipse fit.
- 45 điểm smooth.

Tên file:

```text
<csv_name>_seg<N>_trajectory.png
```

## 5. Tham số

| Tham số | Mặc định | Ý nghĩa |
|---|---:|---|
| `path` | Bắt buộc | File CSV hoặc thư mục CSV |
| `--segment-length` | `45` | Số điểm trong một đoạn |
| `--n-segments` | `3` | Số đoạn trên mỗi CSV |
| `--poly-degree` | `2` | Đa thức bậc 2 |
| `--seed` | `42` | Random seed |
| `--out-dir` | `benchmark/ellipse_smooth_segments` | Thư mục lưu ảnh |

> Lưu ý: `--n-segments` mặc định là `3`.

## 6. Lệnh chạy

```powershell
python tools/plot_ellipse_smooth_segments.py benchmark --n-segments 3 --poly-degree 2
```

Thư mục đầu ra: [benchmark/ellipse_smooth_segments](benchmark/ellipse_smooth_segments)

## 7. Kết quả

Đã chạy trên 3 CSV, mỗi CSV chọn 3 đoạn.

Cấu hình thử nghiệm: **RMS ≤ 0.35** và **arc coverage ≥ 60°**.

| File CSV | Số đoạn | Phase plots | Trajectory plots |
|---|---:|---:|---:|
| `roi_tracking_runlr_2000_1000.csv` | 3 | 3 | 3 |
| `roi_tracking_runlr_2000_1300.csv` | 3 | 3 | 3 |
| `roi_tracking_runlr_2000_1600.csv` | 3 | 3 | 3 |

Tổng cộng: **9 đoạn và 18 đồ thị**.

## 8. Hình ảnh kết quả


### 8.1. `roi_tracking_runlr_2000_1000.csv`

#### Segment 1 — index `[130,175)`

| Continuous phase angle | Quỹ đạo gốc và smooth |
|---|---|
| ![1000 segment 1 phase](benchmark/ellipse_smooth_segments/roi_tracking_runlr_2000_1000_seg1_phase_angle.png) | ![1000 segment 1 trajectory](benchmark/ellipse_smooth_segments/roi_tracking_runlr_2000_1000_seg1_trajectory.png) |

#### Segment 2 — index `[511,556)`

| Continuous phase angle | Quỹ đạo gốc và smooth |
|---|---|
| ![1000 segment 2 phase](benchmark/ellipse_smooth_segments/roi_tracking_runlr_2000_1000_seg2_phase_angle.png) | ![1000 segment 2 trajectory](benchmark/ellipse_smooth_segments/roi_tracking_runlr_2000_1000_seg2_trajectory.png) |

#### Segment 3 — index `[614,659)` — RMS `0.7369`

| Continuous phase angle | Quỹ đạo gốc và smooth |
|---|---|
| ![1000 segment 3 phase](benchmark/ellipse_smooth_segments/roi_tracking_runlr_2000_1000_seg3_phase_angle.png) | ![1000 segment 3 trajectory](benchmark/ellipse_smooth_segments/roi_tracking_runlr_2000_1000_seg3_trajectory.png) |

#### Segment 4 — index `[856,901)`

| Continuous phase angle | Quỹ đạo gốc và smooth |
|---|---|
| ![1000 segment 4 phase](benchmark/ellipse_smooth_segments/roi_tracking_runlr_2000_1000_seg4_phase_angle.png) | ![1000 segment 4 trajectory](benchmark/ellipse_smooth_segments/roi_tracking_runlr_2000_1000_seg4_trajectory.png) |

#### Segment 5 — index `[911,956)`

| Continuous phase angle | Quỹ đạo gốc và smooth |
|---|---|
| ![1000 segment 5 phase](benchmark/ellipse_smooth_segments/roi_tracking_runlr_2000_1000_seg5_phase_angle.png) | ![1000 segment 5 trajectory](benchmark/ellipse_smooth_segments/roi_tracking_runlr_2000_1000_seg5_trajectory.png) |

### 8.2. `roi_tracking_runlr_2000_1300.csv`

#### Segment 1 — index `[146,191)`

| Continuous phase angle | Quỹ đạo gốc và smooth |
|---|---|
| ![1300 segment 1 phase](benchmark/ellipse_smooth_segments/roi_tracking_runlr_2000_1300_seg1_phase_angle.png) | ![1300 segment 1 trajectory](benchmark/ellipse_smooth_segments/roi_tracking_runlr_2000_1300_seg1_trajectory.png) |

#### Segment 2 — index `[248,293)`

| Continuous phase angle | Quỹ đạo gốc và smooth |
|---|---|
| ![1300 segment 2 phase](benchmark/ellipse_smooth_segments/roi_tracking_runlr_2000_1300_seg2_phase_angle.png) | ![1300 segment 2 trajectory](benchmark/ellipse_smooth_segments/roi_tracking_runlr_2000_1300_seg2_trajectory.png) |

#### Segment 3 — index `[1074,1119)`

| Continuous phase angle | Quỹ đạo gốc và smooth |
|---|---|
| ![1300 segment 3 phase](benchmark/ellipse_smooth_segments/roi_tracking_runlr_2000_1300_seg3_phase_angle.png) | ![1300 segment 3 trajectory](benchmark/ellipse_smooth_segments/roi_tracking_runlr_2000_1300_seg3_trajectory.png) |

#### Segment 4 — index `[1129,1174)`

| Continuous phase angle | Quỹ đạo gốc và smooth |
|---|---|
| ![1300 segment 4 phase](benchmark/ellipse_smooth_segments/roi_tracking_runlr_2000_1300_seg4_phase_angle.png) | ![1300 segment 4 trajectory](benchmark/ellipse_smooth_segments/roi_tracking_runlr_2000_1300_seg4_trajectory.png) |

#### Segment 5 — index `[1522,1567)`

| Continuous phase angle | Quỹ đạo gốc và smooth |
|---|---|
| ![1300 segment 5 phase](benchmark/ellipse_smooth_segments/roi_tracking_runlr_2000_1300_seg5_phase_angle.png) | ![1300 segment 5 trajectory](benchmark/ellipse_smooth_segments/roi_tracking_runlr_2000_1300_seg5_trajectory.png) |

### 8.3. `roi_tracking_runlr_2000_1600.csv`

#### Segment 1 — index `[709,754)`

| Continuous phase angle | Quỹ đạo gốc và smooth |
|---|---|
| ![1600 segment 1 phase](benchmark/ellipse_smooth_segments/roi_tracking_runlr_2000_1600_seg1_phase_angle.png) | ![1600 segment 1 trajectory](benchmark/ellipse_smooth_segments/roi_tracking_runlr_2000_1600_seg1_trajectory.png) |

#### Segment 2 — index `[1738,1783)`

| Continuous phase angle | Quỹ đạo gốc và smooth |
|---|---|
| ![1600 segment 2 phase](benchmark/ellipse_smooth_segments/roi_tracking_runlr_2000_1600_seg2_phase_angle.png) | ![1600 segment 2 trajectory](benchmark/ellipse_smooth_segments/roi_tracking_runlr_2000_1600_seg2_trajectory.png) |

#### Segment 3 — index `[2114,2159)`

| Continuous phase angle | Quỹ đạo gốc và smooth |
|---|---|
| ![1600 segment 3 phase](benchmark/ellipse_smooth_segments/roi_tracking_runlr_2000_1600_seg3_phase_angle.png) | ![1600 segment 3 trajectory](benchmark/ellipse_smooth_segments/roi_tracking_runlr_2000_1600_seg3_trajectory.png) |

#### Segment 4 — index `[2180,2225)`

| Continuous phase angle | Quỹ đạo gốc và smooth |
|---|---|
| ![1600 segment 4 phase](benchmark/ellipse_smooth_segments/roi_tracking_runlr_2000_1600_seg4_phase_angle.png) | ![1600 segment 4 trajectory](benchmark/ellipse_smooth_segments/roi_tracking_runlr_2000_1600_seg4_trajectory.png) |

#### Segment 5 — index `[2661,2706)` — RMS `1.0438`

| Continuous phase angle | Quỹ đạo gốc và smooth |
|---|---|
| ![1600 segment 5 phase](benchmark/ellipse_smooth_segments/roi_tracking_runlr_2000_1600_seg5_phase_angle.png) | ![1600 segment 5 trajectory](benchmark/ellipse_smooth_segments/roi_tracking_runlr_2000_1600_seg5_trajectory.png) |

## B. Khó khăn 
- Hình elipse được vẽ ra chỉ fit với đoạn dữ liệu, còn đối với toàn bộ  quỹ đạo thực tế thì không đúng . 
## C. Công việc tiếp theo 
- Em xin phép nhận công việc tiếp theo từ Thầy ạ.