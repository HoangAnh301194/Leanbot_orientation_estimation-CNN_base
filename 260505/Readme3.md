# Cập nhật báo cáo ngày 05/05/2026

## A. Công việc đã làm

---

### 1. Bảng thông tin Dataset cho lần Training

#### 1.1. Thông tin các Session thu thập

| Session | Class | Số ảnh Background | Số ảnh Raw | Số nhãn (labels) |
| :--- | :---: | :---: | :---: | :---: |
| `session_20260504_090104` | `Leanbot_back` | 1 | 7 | 7 |
| `session_20260504_090516` | `Leanbot_front` | 1 | 7 | 7 |
| `session_20260504_102751` | `Leanbot_front` | 1 | 14 | 14 |
| `session_20260504_103507` | `Leanbot_back` | 1 | 14 | 14 |
| **Tổng cộng** | | **4** | **42** | **42** |

#### 1.2. Thống kê theo Class

| Class | Class ID | Số ảnh | Số nhãn |
| :--- | :---: | :---: | :---: |
| `Leanbot_front` | 0 | 21 | 21 |
| `Leanbot_back` | 1 | 21 | 21 |
| **Tổng** | | **42** | **42** |

#### 1.3. Tỷ lệ chia Dataset (Stratified Split)

Sử dụng chiến lược **Stratified Split** để đảm bảo tỷ lệ 2 class luôn cân bằng trong mỗi tập.

| Tập | Tỷ lệ | Leanbot_front | Leanbot_back | Tổng |
| :--- | :---: | :---: | :---: | :---: |
| **Train** | 70% | 14 | 14 | 28 |
| **Validation** | 20% | 4 | 4 | 8 |
| **Test** | 10% | 3 | 3 | 6 |
| **Tổng** | 100% | **21** | **21** | **42** |

#### 1.4. Thông tin Training

| Thông số | Giá trị |
| :--- | :--- |
| Model nền tảng | `yolov8n.pt` (YOLOv8 Nano - Pre-trained trên COCO) |
| Số class | 2 (`Leanbot_front`, `Leanbot_back`) |
| Epochs | 150 |
| Image size | 640 x 640 |
| Thời gian Training | ~4 phút |
| Môi trường Training | Google Colab (GPU T4) |
| Link Notebook | [finetuning_yolo_Leanbot.ipynb](https://git.pythaverse.space/thomha/Nguyen_Huu_Hoang_Anh/blob/master/260505/tools/finetuning_yolo_Leanbot.ipynb) |

---

### 2. So sánh: 2 class (Front/Back) vs. 1 class (Leanbot chung)

> **Mục tiêu:** Sử dụng **cùng bộ dữ liệu 42 ảnh**, nhưng bỏ phân biệt class, gộp tất cả thành 1 class duy nhất là `Leanbot` để so sánh chất lượng nhận diện với mô hình 2 class.

#### 2.1. Cách thực hiện
Để chạy thử nghiệm 1 class, cần sửa lại file YAML trong notebook:
```python
# Cấu hình 1 class (Leanbot chung)
yaml_content = """
path: /content/datasets
train: train/images
val: val/images
test: test/images
nc: 1
names:
  0: Leanbot
"""
```
Đồng thời, cần sửa lại tất cả các file nhãn `.txt` để đổi class ID `1` (Leanbot_back) thành `0` (gộp chung), hoặc chạy lại `process_auto_label.py` với `--class_id 0` cho tất cả các session.

#### 2.2. Kết quả so sánh

| Tiêu chí | 1 Class (`Leanbot`) | 2 Class (`Front` / `Back`) |
| :--- | :---: | :---: |
| **mAP@0.5** | *(điền vào)* | *(điền vào)* |
| **Precision** | *(điền vào)* | *(điền vào)* |
| **Recall** | *(điền vào)* | *(điền vào)* |
| Tỷ lệ bỏ sót đối tượng | *(điền vào)* | *(điền vào)* |
| Nhận diện khi test thực tế | *(điền vào)* | *(điền vào)* |

#### 2.3. Phân tích dự kiến

**Giả thuyết:** Mô hình 1 class sẽ có kết quả tốt hơn đáng kể vì:
- Bài toán đơn giản hơn: chỉ cần xác định "có Leanbot hay không" thay vì phân biệt mặt trước/sau.
- Với 42 ảnh, 1 class sẽ có nhiều mẫu hơn cho một nhiệm vụ đơn (42 ảnh cho 1 class vs. 21 ảnh cho mỗi class trong bài toán 2 class).
- Các đặc trưng tổng thể của Leanbot (màu đỏ, hình dạng, kích thước) dễ học hơn các đặc trưng phân biệt mặt trước/sau (2 mắt cảm biến HC-SR04 rất nhỏ).

*(Cập nhật bảng so sánh sau khi có kết quả thực nghiệm)*

---

### 3. Data Augmentation có sẵn trong YOLO

YOLO (thư viện Ultralytics) tích hợp sẵn một bộ **Data Augmentation**, được áp dụng tự động trong quá trình training. Tất cả các tham số này có thể được cấu hình khi gọi hàm `model.train()`.

#### 3.1. Bảng các kỹ thuật Augmentation chính

| Tham số | Mặc định | Mô tả |
| :--- | :---: | :--- |
| `hsv_h` | 0.015 | Thay đổi ngẫu nhiên **Hue** (màu sắc) ±1.5% |
| `hsv_s` | 0.7 | Thay đổi ngẫu nhiên **Saturation** (độ bão hòa) ±70% |
| `hsv_v` | 0.4 | Thay đổi ngẫu nhiên **Value** (độ sáng) ±40% |
| `degrees` | 0.0 | Xoay ảnh ngẫu nhiên (độ) |
| `translate` | 0.1 | Dịch chuyển ảnh ngẫu nhiên ±10% chiều rộng/cao |
| `scale` | 0.5 | Thu/phóng ảnh ngẫu nhiên ±50% |
| `shear` | 0.0 | Biến dạng cắt (shear) ảnh |
| `perspective` | 0.0 | Biến đổi phối cảnh 3D ngẫu nhiên |
| `flipud` | 0.0 | Lật ảnh theo chiều dọc (xác suất) |
| `fliplr` | 0.5 | Lật ảnh theo chiều ngang (xác suất 50%) |
| `mosaic` | 1.0 | Ghép 4 ảnh thành 1 (Mosaic Augmentation) |
| `mixup` | 0.0 | Trộn 2 ảnh lại với nhau (MixUp) |
| `copy_paste` | 0.0 | Cắt đối tượng và dán vào ảnh khác (Copy-Paste) |
| `erasing` | 0.4 | Xóa ngẫu nhiên một vùng trong ảnh |
| `crop_fraction` | 1.0 | Tỷ lệ crop ảnh trong quá trình phân loại |

#### 3.2. Ví dụ cấu hình tăng cường cho bài toán Leanbot

Vì ảnh Leanbot được chụp từ góc trên xuống và cần phân biệt mặt trước/sau dựa trên các chi tiết nhỏ (cảm biến HC-SR04), nên các tham số sau sẽ có ích nhất:

```python
model.train(
    data='leanbot_data.yaml',
    epochs=100,
    imgsz=640,
    # --- Augmentation đề xuất cho Leanbot ---
    hsv_h=0.02,      # Thay đổi màu sắc nhẹ (ánh sáng phòng)
    hsv_s=0.5,       # Thay đổi độ bão hòa
    hsv_v=0.4,       # Thay đổi độ sáng (bóng đèn, góc chiếu)
    degrees=15.0,    # Xoay ảnh (Leanbot đặt ở nhiều góc trên sa bàn)
    scale=0.5,       # Thu/phóng (Leanbot ở xa/gần camera)
    fliplr=0.5,      # Lật ngang (tăng gấp đôi mẫu)
    mosaic=1.0,      # Mosaic (ghép nhiều hoàn cảnh lại)
    translate=0.1,   # Dịch chuyển nhẹ
)
```


## B. Khó khăn
- *(Cập nhật sau khi thực nghiệm)*

## C. Công việc tiếp theo
- Chạy thực nghiệm training 1 class và điền kết quả vào bảng so sánh ở **Mục 2.2**.
- Thử nghiệm cấu hình Augmentation đề xuất ở **Mục 3.2** và đánh giá kết quả.
- Thu thập thêm ảnh đa dạng hơn (nhiều nền, nhiều góc, nhiều điều kiện ánh sáng).
