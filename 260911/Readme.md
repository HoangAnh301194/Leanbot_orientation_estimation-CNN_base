# Báo cáo công việc ngày 11/09/2026

## A. Công việc đã làm 
- Thu thập thêm dataset 
### 1. Thu thập thêm ảnh 
- 24 ảnh cho 24 class với setup nhưu sau : 
  - 9 Leanbot cho mỗi class góc (24 classs góc)
  - 3 Leanbot hiện Led RGB
  - 3 Leanbot quay gripper ngẫu nhiên
  - 3 Leanbot có khối gỗ 3mm đặt giữa gripper
  - Phân bố ngẫu nhiên, rải đều trên sa bàn 
  - Kết hợp với dataset cũ

- Folder dataset mới : [`datasets_24class_640`](./datasets_24class_640/) (24 ảnh 640x640 mới)
- Folder dataset hợp nhất : `datasets/` (204 ảnh 640x640 hoàn chỉnh)
- File zip nén sẵn sàng huấn luyện : `datasets.zip` (41.34 MB)

- 24 ảnh bổ sung như sau  :

| |  |  |   |
| :---: | :---: | :---: | :---: |
| **Class 0 (0°)**<br><img src="datasets_24class_640/images/000000.jpg" alt="Class 0" width="180"> | **Class 1 (15°)**<br><img src="datasets_24class_640/images/000001.jpg" alt="Class 1" width="180"> | **Class 2 (30°)**<br><img src="datasets_24class_640/images/000002.jpg" alt="Class 2" width="180"> | **Class 3 (45°)**<br><img src="datasets_24class_640/images/000003.jpg" alt="Class 3" width="180"> |
| **Class 4 (60°)**<br><img src="datasets_24class_640/images/000004.jpg" alt="Class 4" width="180"> | **Class 5 (75°)**<br><img src="datasets_24class_640/images/000005.jpg" alt="Class 5" width="180"> | **Class 6 (90°)**<br><img src="datasets_24class_640/images/000006.jpg" alt="Class 6" width="180"> | **Class 7 (105°)**<br><img src="datasets_24class_640/images/000007.jpg" alt="Class 7" width="180"> |
| **Class 8 (120°)**<br><img src="datasets_24class_640/images/000008.jpg" alt="Class 8" width="180"> | **Class 9 (135°)**<br><img src="datasets_24class_640/images/000009.jpg" alt="Class 9" width="180"> | **Class 10 (150°)**<br><img src="datasets_24class_640/images/000010.jpg" alt="Class 10" width="180"> | **Class 11 (165°)**<br><img src="datasets_24class_640/images/000011.jpg" alt="Class 11" width="180"> |
| **Class 12 (180°)**<br><img src="datasets_24class_640/images/000012.jpg" alt="Class 12" width="180"> | **Class 13 (195°)**<br><img src="datasets_24class_640/images/000013.jpg" alt="Class 13" width="180"> | **Class 14 (210°)**<br><img src="datasets_24class_640/images/000014.jpg" alt="Class 14" width="180"> | **Class 15 (225°)**<br><img src="datasets_24class_640/images/000015.jpg" alt="Class 15" width="180"> |
| **Class 16 (240°)**<br><img src="datasets_24class_640/images/000016.jpg" alt="Class 16" width="180"> | **Class 17 (255°)**<br><img src="datasets_24class_640/images/000017.jpg" alt="Class 17" width="180"> | **Class 18 (270°)**<br><img src="datasets_24class_640/images/000018.jpg" alt="Class 18" width="180"> | **Class 19 (285°)**<br><img src="datasets_24class_640/images/000019.jpg" alt="Class 19" width="180"> |
| **Class 20 (300°)**<br><img src="datasets_24class_640/images/000020.jpg" alt="Class 20" width="180"> | **Class 21 (315°)**<br><img src="datasets_24class_640/images/000021.jpg" alt="Class 21" width="180"> | **Class 22 (330°)**<br><img src="datasets_24class_640/images/000022.jpg" alt="Class 22" width="180"> | **Class 23 (345°)**<br><img src="datasets_24class_640/images/000023.jpg" alt="Class 23" width="180"> |

- Cấu tạo dataset sau khi cộng thêm 24 ảnh vào datasets trước đó : 

| Nhóm nguồn (`source_group`) | Số lượng ảnh | Số lượng nhãn | Số bounding box | Đặc điểm |
| :--- | :---: | :---: | :---: | :--- |
| `original_120` | 120 | 120 | 1.080 (45 box/class) | Tập robot cơ bản ban đầu (5 ảnh/class, 9 robot/ảnh) |
| `new_red_obstacle_48` | 48 | 48 | 432 (18 box/class) | Bổ sung vật cản khối hộp màu đỏ (2 ảnh/class, 9 robot/ảnh) |
| `background_negative_12` | 12 | 12 | 0 | Sa bàn trống không có robot (negative background samples) |
| `new_setup_24class_260911` | 24 | 24 | 216 (9 box/class) | Bổ sung mới hôm nay: Led RGB, gripper xoay, khối gỗ 3mm (1 ảnh/class, 9 robot/ảnh) |
| **Tổng cộng** | **204 ảnh** | **204 file labels ** | **1.728 bounding box** | **72 bounding box / class cho cả 24 class** |

- **Thông số ảnh trong Dataset**:
  - Kích thước ảnh: $640 \times 640 \times 3$
  - Chuẩn định dạng nhãn: YOLO Detection (`class_id x_center y_center width height`)
  - File metadata thông tin chi tiết: `datasets/manifest.json` ghi lại nguồn gốc từng ảnh
  - File nén huấn luyện: `datasets.zip` (41.34 MB)

## B. Khó khăn 
- Không
## C. Công việc tiếp theo
- Training lại với datasets mới 