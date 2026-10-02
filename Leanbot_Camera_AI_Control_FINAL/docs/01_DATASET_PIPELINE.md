# 1. Thu thập dữ liệu ảnh và Build Dataset

Toàn bộ hướng dẫn tái triển khai lại pipeline tạo dữ liệu cho bài toán nhận diện Leanbot và ước lượng hướng theo 24 lớp góc. Pipeline gồm các bước: thu thập ảnh, auto-label, build dataset chuẩn YOLO và bổ sung dữ liệu từ các trường hợp lost tracking.

## 1.1. Các file sử dụng

- [`capture_session.py`](../tools/capture_session.py): thu thập background và ảnh Leanbot theo từng session.
- [`process_auto_label_paired.py`](../tools/process_auto_label_paired.py): auto-label ảnh bằng phép trừ background theo cặp.
- [`auto_label_core.py`](../tools/auto_label_core.py): các hàm dùng chung cho capture và auto-label.
- [`abstract_hsv.py`](../tools/abstract_hsv.py): tính sai khác ảnh theo Gray/Hue/HSV.
- [`alignment.py`](../tools/alignment.py): căn chỉnh ảnh trước khi trừ background.
- [`mask_roi.py`](../tools/mask_roi.py): chọn và áp dụng vùng ROI của sa bàn.
- [`build_dataset.py`](../tools/build_dataset.py): gộp output auto-label thành dataset YOLO chung.
- [`merge_lost_tracking_dataset.py`](../tools/merge_lost_tracking_dataset.py): gộp dataset nền với các sample lost tracking đã được kiểm tra.
- [`lost_tracking_collector.py`](../LeanbotTinyRC_AI_PIDControl/lost_tracking_collector.py): thu sample lost tracking trong khi chạy inference.

Dataset dùng cho model hiện tại được lưu tại [`datasets.zip`](../datasets.zip).

## 1.2. Quy ước 24 class góc

Model sử dụng 24 class, mỗi class cách nhau 15 độ:

```text
0  : Leanbot_0
1  : Leanbot_p15
2  : Leanbot_p30
3  : Leanbot_p45
4  : Leanbot_p60
5  : Leanbot_p75
6  : Leanbot_p90
7  : Leanbot_p105
8  : Leanbot_p120
9  : Leanbot_p135
10 : Leanbot_p150
11 : Leanbot_p165
12 : Leanbot_p180
13 : Leanbot_p195
14 : Leanbot_m150
15 : Leanbot_m135
16 : Leanbot_m120
17 : Leanbot_m105
18 : Leanbot_m90
19 : Leanbot_m75
20 : Leanbot_m60
21 : Leanbot_m45
22 : Leanbot_m30
23 : Leanbot_m15
```

Trong đó `p` biểu diễn góc dương và `m` biểu diễn góc âm. Ví dụ `Leanbot_m15` tương ứng -15 độ, tương đương 345 độ trong hệ [0, 360).

## 1.3. Thu thập dữ liệu ảnh
- Lệnh chạy : 

```powershell
python .\tools\capture_session.py --source 1 --session_name Leanbot_0_new --class_name Leanbot_0 --class_id 0
```

Các tham số:

- `--source`: camera index hoặc đường dẫn video.
- `--session_name`: tên session. Nếu bỏ qua, chương trình tự tạo tên theo thời gian.
- `--class_name`: tên class góc.
- `--class_id`: ID class tương ứng từ 0 đến 23.

Trong cửa sổ capture:

- `B`: lưu một ảnh background cho phiên đang thu thập, backgroud này sẽ được dùng chung cho các ảnh trong cùng một session để đánh nhãn tự động. 
- `SPACE`: Chụp ảnh data Leanbot.
- `S`: kết thúc và lưu session.
- `Q`: dừng ngay quá trình capture.

Cấu trúc output:

```text
raw_image/
└── Leanbot_0_new/
    ├── backgrounds/
    │   ├── background_000.jpg
    │   └── ...
    ├── raw_images/
    │   ├── <image>_000.jpg
    │   └── ...
    └── session_metadata.json
```


Background phải chứa cùng điều kiện sa bàn, vật cản hoặc vật thể tĩnh như ảnh dữ liệu tương ứng, nhưng không được chứa Leanbot.

## 1.4. Auto-label theo cặp background/raw image

Ví dụ cấu hình đã sử dụng:

```powershell
python .\tools\process_auto_label_paired.py `
  --raw_dir .\raw_image `
  --out_dir .\tool1_output_paired `
  --diff_mode 1 `
  --threshold 90 `
  --blur 3 `
  --min_area 6000 `
  --max_area 500000 `
  --min_width 115 `
  --max_width 600 `
  --min_height 0 `
  --max_height 600 `
  --mask_merge_kernel 11 `
  --mask_merge_iterations 1 `
  --wait_ms 200
```

Các bước xử lý chính:

1. Đọc background và raw image có cùng trailing index.
2. Chọn ROI của vùng sa bàn nếu chưa có cấu hình ROI.
3. Căn chỉnh ảnh bằng `ImageAligner`.
4. Tính ảnh sai khác giữa background và ảnh có Leanbot.
5. Lọc vùng theo threshold, kích thước và diện tích.
6. Sinh bounding box.
7. Ghi ảnh đã căn chỉnh và YOLO label.

Output:

```text
tool1_output_paired/
├── processing_config.json
└── <session_name>/
    ├── aligned_images/
    ├── labels/
    ├── debug/
    ├── roi_preview.jpg
    └── config.npy
```

Định dạng YOLO label:

```text
class_id x_center y_center width height
```

Các tọa độ được chuẩn hóa về [0, 1]. Sau auto-label cần kiểm tra ảnh trong `debug/` để xác nhận bounding box, class ID và vùng ROI trước khi đưa dữ liệu vào dataset chung.

## 1.5. Build dataset từ output auto-label

Tool [`build_dataset.py`](../tools/build_dataset.py) gộp các cặp ảnh-label từ nhiều session và đánh lại tên file liên tục.

Chạy kiểm tra trước:

```powershell
python .\tools\build_dataset.py `
  --input .\tool1_output_paired `
  --output .\datasets `
  --dry_run
```

Build dataset:

```powershell
python .\tools\build_dataset.py `
  --input .\tool1_output_paired `
  --output .\datasets
```

Nếu cần giữ cả ảnh negative background có label rỗng:

```powershell
python .\tools\build_dataset.py `
  --input .\tool1_output_paired `
  --output .\datasets `
  --include_empty
```

Output:

```text
datasets/
├── images/
├── labels/
└── manifest.json
```

`manifest.json` lưu nguồn của từng ảnh để truy vết lại session ban đầu.

## 1.6. Dataset hiện tại

Dataset dùng cho lần train ngày 11/09/2026 được lưu tại:

- [`datasets.zip`](../datasets.zip)

Dataset này có 204 ảnh 640x640, gồm 192 ảnh có Leanbot và 12 ảnh negative background. Tổng số bounding box là 1.728 trên 24 class góc.

Các sample lost tracking thu sau đó chưa được sử dụng để train model ngày 11/09/2026.

## 1.7. Thu thập dữ liệu khi lost tracking

Khi cần lưu thêm các trường hợp ROI tracking thất bại khi chạy module Camera AI controll inference thì cần thêm tham số `--save-lost`:

```powershell
cd .\LeanbotTinyRC_AI_PIDControl

python .\leanbotCameraController.py `
  --source 1 `
  --show `
  --save-lost `
  --ble <BLE_ID>
```

Khi ROI tracking bị mất, [`lost_tracking_collector.py`](../LeanbotTinyRC_AI_PIDControl/lost_tracking_collector.py):

1. lấy ROI raw tại frame bị mất tracking;
2. resize ROI thành 640x640;
3. chuyển bounding box gần nhất từ hệ full-frame sang hệ ROI;
4. tạo YOLO label dựa trên detection thành công gần nhất;
5. lưu ảnh kiểm tra và metadata.

Cấu trúc:

```text
lost_tracking_dataset/
└── session_YYYYMMDD_HHMMSS_xxxxxx/
    ├── images/
    ├── labels/
    ├── metadata/
    ├── check_labels/
    └── classes.json
```

Label lost tracking là pseudo-label kế thừa từ detection thành công gần nhất. Metadata đánh dấu `requires_review=true`. Vì vậy phải kiểm tra `check_labels/` trước khi merge vào dataset training. Sample sai bbox hoặc sai class cần được sửa hoặc loại bỏ.

## 1.8. Merge lost-tracking data vào dataset chung

Tool:

- [`merge_lost_tracking_dataset.py`](../tools/merge_lost_tracking_dataset.py)

Tool không ghi đè dataset nền. Nó tạo dataset mới, kiểm tra cấu trúc YOLO label, đánh lại tên file và ghi nguồn dữ liệu vào manifest.

### Bước 1: Giải nén dataset nền

```powershell
Expand-Archive -Path .\datasets.zip -DestinationPath .\datasets -Force
```

Sau khi giải nén folder datasets sẽ có:

```text
datasets/
├── images/
└── labels/
```

### Bước 2: Kiểm tra lost-tracking samples

Kiểm tra toàn bộ ảnh trong:

```text
lost_tracking_dataset/<session>/check_labels/
```

Chỉ giữ các sample có bbox và class phù hợp.

### Bước 3: Tạo dataset mới

```powershell
python .\tools\merge_lost_tracking_dataset.py `
  --base .\datasets `
  --lost-root .\lost_tracking_dataset `
  --output .\datasets_with_lost_tracking
```

Nếu output đã tồn tại và cần tạo lại:

```powershell
python .\tools\merge_lost_tracking_dataset.py `
  --base .\datasets `
  --lost-root .\lost_tracking_dataset `
  --output .\datasets_with_lost_tracking `
  --overwrite
```

Output:

```text
datasets_with_lost_tracking/
├── images/
├── labels/
└── manifest.json
```

- Sau khi có datasets_with_lost_tracking thì kiểm tra qua một lần xem ảnh đã được thêm chưa, và đổi tên thành datasets.zip để dùng cho module Training . 

## 1.9. Pipeline tổng hợp

```text
Camera
  │
  ├── capture_session.py
  │       ↓
  │   raw_image/
  │
  ├── process_auto_label_paired.py
  │       ↓
  │   tool1_output_paired/
  │
  ├── build_dataset.py
  │       ↓
  │   datasets/
  │
  └── Runtime --save-lost
          ↓
      lost_tracking_dataset/
          ↓
      Review check_labels/
          ↓
      merge_lost_tracking_dataset.py
          ↓
      datasets_with_lost_tracking/
          ↓
      Training
```
