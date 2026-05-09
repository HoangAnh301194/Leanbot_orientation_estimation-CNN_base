# Báo cáo công việc ngày 08/05/2026

## A. Công việc đã làm
- Thu thập ảnh các góc `0`, `+-15`, `+-30`, cho 4 class: `Leanbot_front`, `Leanbot_back`, `Leanbot_left`, `Leanbot_right`.
- Đã thu thập đủ dataset để huấn luyện, đảm bảo cấu trúc thư mục và quy tắc đặt tên (`deg_[góc]_[stt].jpg`).
- Đã chuẩn bị sẵn thư mục `degree_45_test` cho dữ liệu test sau huấn luyện với các góc xéo (45, -45, 135, -135).

---

### 1. Danh sách file Raw đã chụp
Dưới đây là cấu trúc của `Raw_images` với ví dụ 1 session (Các session khác tương tự):

```text
Raw_images
├── session_20260508_142829
│   ├── deg_0_000.jpg
│   ├── deg_0_001.jpg
│   ├── deg_0_002.jpg
│   ├── deg_0_003.jpg
│   ├── deg_0_004.jpg
│   ├── deg_m15_015.jpg
│   ├── deg_m15_016.jpg
│   ├── deg_m15_017.jpg
│   ├── deg_m15_018.jpg
│   ├── deg_m15_019.jpg
│   ├── deg_m30_021.jpg
│   ├── deg_m30_022.jpg
│   ├── deg_m30_023.jpg
│   ├── deg_m30_024.jpg
│   ├── deg_m30_026.jpg
│   ├── deg_p15_005.jpg
│   ├── deg_p15_006.jpg
│   ├── deg_p15_007.jpg
│   ├── deg_p15_008.jpg
│   ├── deg_p15_009.jpg
│   ├── deg_p30_010.jpg
│   ├── deg_p30_011.jpg
│   ├── deg_p30_012.jpg
│   ├── deg_p30_013.jpg
│   └── deg_p30_014.jpg
|___> Session khác tương tự...
```


### 2. Thống kê Dataset Train/Val

> Mỗi ảnh chụp sa bàn đều chứa 9 con Leanbot. Do đó, sau khi chạy auto_label, số lượng Bounding Box (Nhãn) thu được là: `Số lượng ảnh × 9`.

| Class (Nhãn) | Góc 0° | Góc +15° | Góc -15° | Góc +30° | Góc -30° | Tổng số ẢNH | Tổng số NHÃN |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `Leanbot_front` | 5 | 5 | 5 | 5 | 5 | **25** | **225** |
| `Leanbot_back` | 5 | 5 | 5 | 5 | 5 | **25** | **225** |
| `Leanbot_left` | 5 | 5 | 5 | 5 | 5 | **25** | **225** |
| `Leanbot_right` | 5 | 5 | 5 | 5 | 5 | **25** | **225** |
| **TỔNG CỘNG** | **20** | **20** | **20** | **20** | **20** | **100** | **900** |

### 3. Thống kê Tập Test (Góc xéo 45°)
Thư mục `degree_45_test` đang được chuẩn bị để test khả năng tổng quát hóa của model với các góc khó hơn chưa từng xuất hiện trong tập Train:

| Góc chụp (Test) | Số lượng ảnh thực tế | Số nhãn tương ứng |
| :--- | :---: | :---: |
| Góc +45° (`degree_45`) | 5 | 45|
| Góc -45° (`degree_m45`) | 5 | 45 |
| Góc +135° (`degree_135`) | 5 | 45 |
| Góc -135° (`degree_m135`)| 5 | 45 |

---

### 4. Thông tin Training (Huấn luyện Model)


| Thông số | Giá trị / Kết quả |
| :--- | :--- |
| **Model Base** | YOLOv8n |
| **Epochs** | 100 (Có tắt Augmentation ở 10 epoch cuối) |
| **Batch Size** | 16 |
| **Image Size** | 640x640 (Đã crop 1600x1440, pad 1600x1600 và resize) |
| **Optimizer** | AdamW |
| **Datasets** | 100 ảnh |
| **Datasets.zip** | 20MB (Upload ~30s) |
| **Kết quả mAP50 (Tất cả class)** | **Tiệm cận 99.5%** |
| **Kết quả mAP50-95** | **Ổn định > 90%** |

### 5. Đánh giá
Dựa trên các trích xuất từ quá trình huấn luyện, dưới đây là phân tích kỹ thuật về chất lượng của mô hình:

#### 5.1. Khả năng Hội tụ và Mức độ Ổn định (Convergence & Stability)

![Results](Leanbot4Class/results.png)

- Biểu đồ quá trình giảm Loss và tăng trưởng độ chính xác cho thấy mô hình hội tụ tốt. Các chỉ số Loss (đặc biệt là Box Loss và Class Loss) giảm nhanh ở những epoch đầu và đi vào trạng thái ổn định.
- Validation Loss bám sát Training Loss, cho thấy **không xảy ra hiện tượng Overfitting**, mô hình duy trì được khả năng tổng quát hóa trên tập dữ liệu kiểm thử.
- Các độ đo mAP50 và mAP50-95 tăng với độ dốc lớn ở giai đoạn đầu và đạt trạng thái bão hòa (plateau) ở giai đoạn cuối, xác nhận mức độ tin cậy trong việc nhận diện và phân loại mục tiêu.

#### 5.2. Chất lượng Phân loại Class (Confusion Matrix)

![Confusion Matrix Normalized](Leanbot4Class/confusion_matrix_normalized.png)

- Ma trận nhầm lẫn chuẩn hóa có đường chéo chính đạt giá trị `1.0` (hoặc tiệm cận 1.0) cho cả 4 lớp: `Leanbot_front`, `Leanbot_back`, `Leanbot_left`, `Leanbot_right`.
- **Đánh giá:** Mô hình không gặp tình trạng nhầm lẫn đặc trưng chéo (ví dụ: không nhận diện sai giữa Front với Back, hay Left với Right). Điều này cho thấy thuật toán đã phân tách được các điểm neo (anchor features) của từng mặt robot ở các góc nghiêng nhỏ ($\pm15^{\circ}$, $\pm30^{\circ}$).

#### 5.3. Đồ thị PR (Precision-Recall) và F1-Score

![Box PR Curve](Leanbot4Class/BoxPR_curve.png)
![Box F1 Curve](Leanbot4Class/BoxF1_curve.png)

- Các đồ thị cho thấy sự cân bằng giữa Precision (Độ chính xác) và Recall (Độ bao phủ). Đường cong PR duy trì ở mức cao gần góc phải trên, minh chứng cho việc mô hình có thể phát hiện đúng đối tượng đồng thời duy trì tỷ lệ báo động sai (False Positives) ở mức thấp.

#### 5.4. Hiệu quả của Chiến lược Augmentation
- **Ảnh input tham chiếu** (Kích thước 640x640):

![alt text](images/resize_padded_640.png)

- **Ảnh batch tại epoch đầu** (Có sử dụng Mosaic & Augmentation):

![Train Batch 0](Leanbot4Class/train_batch0.jpg)

- **Đánh giá:** Việc kích hoạt Mosaic ở các epoch đầu giúp mô hình học cách trích xuất đặc trưng đối tượng trong các không gian thu nhỏ và điều kiện nhiễu ngẫu nhiên.

- **Ảnh batch tại 10 epoch cuối** (Tắt Mosaic, dùng ảnh gốc để fine-tune Bounding Box):

![Train Batch 452](Leanbot4Class/train_batch452.jpg)

- **Đánh giá:** Việc tự động tắt Mosaic ở 10 epoch cuối giúp Box Loss giảm tiếp tục. Khi dữ liệu không còn bị biến đổi (augmentation), mô hình tập trung tinh chỉnh tọa độ của Bounding Box sao cho khớp với đối tượng thực tế, góp phần tăng chỉ số mAP50-95.

#### 5.5 Kết quả dự đoán trên tập test ( không có +-45 độ)

| **Class Leanbot_front** | **Class Leanbot_back** |
| :---: | :---: |
| ![alt text](images/image.png) | ![alt text](images/image-1.png) |

| **Class Leanbot_left** | **Class Leanbot_right** |
| :---: | :---: |
| ![alt text](images/image-3.png) | ![alt text](images/image-2.png) |

#### 5.6 Kết quả dự đoán trên tập Test 45°
- Vì khi đặt 45 độ thì một số trường hợp sẽ bị trùng (ví dụ góc 45 độ của `Leanbot_front` sẽ là -45 của `Leanbot_left`).
- Vì vậy tập test 45 độ sẽ có 4 trường hợp là $\pm45^\circ$ và $\pm135^\circ$.
- Tập dữ liệu test có cấu trúc như sau:

```text
degree_45_test
├── degree_45
│   ├── deg_p45_000.jpg
│   ├── deg_p45_001.jpg
│   ├── deg_p45_002.jpg
│   ├── deg_p45_003.jpg
│   └── deg_p45_004.jpg
├── degree_m45
│   ├── deg_m45_000.jpg
│   ├── deg_m45_001.jpg
│   ├── deg_m45_002.jpg
│   ├── deg_m45_003.jpg
│   └── deg_m45_004.jpg
├── degree_135
│   ├── deg_p135_000.jpg
│   ├── deg_p135_001.jpg
│   ├── deg_p135_002.jpg
│   ├── deg_p135_003.jpg
│   └── deg_p135_004.jpg
└── degree_m135
    ├── deg_m135_000.jpg
    ├── deg_m135_001.jpg
    ├── deg_m135_002.jpg
    ├── deg_m135_003.jpg
    └── deg_m135_004.jpg
```
- **Kết quả dự đoán cho 4 trường hợp +-45 và +-135 độ:** 

**1. Góc +45° (`p45`)**
| | |
| :---: | :---: |
| ![p45_0](degree_45_test_result/p45/deg_p45_000.jpg) | ![p45_1](degree_45_test_result/p45/deg_p45_001.jpg) |
| ![p45_2](degree_45_test_result/p45/deg_p45_002.jpg) | ![p45_3](degree_45_test_result/p45/deg_p45_003.jpg) |
| ![p45_4](degree_45_test_result/p45/deg_p45_004.jpg) |  |

**2. Góc -45° (`m45`)**
| | |
| :---: | :---: |
| ![m45_0](degree_45_test_result/m45/deg_m45_000.jpg) | ![m45_1](degree_45_test_result/m45/deg_m45_001.jpg) |
| ![m45_2](degree_45_test_result/m45/deg_m45_002.jpg) | ![m45_3](degree_45_test_result/m45/deg_m45_003.jpg) |
| ![m45_4](degree_45_test_result/m45/deg_m45_004.jpg) |  |

**3. Góc +135° (`p135`)**
| | |
| :---: | :---: |
| ![p135_0](degree_45_test_result/p135/deg_p135_000.jpg) | ![p135_1](degree_45_test_result/p135/deg_p135_001.jpg) |
| ![p135_2](degree_45_test_result/p135/deg_p135_002.jpg) | ![p135_3](degree_45_test_result/p135/deg_p135_003.jpg) |
| ![p135_4](degree_45_test_result/p135/deg_p135_004.jpg) | |

**4. Góc -135° (`m135`)**
| | |
| :---: | :---: |
| ![m135_0](degree_45_test_result/m135/deg_m135_000.jpg) | ![m135_1](degree_45_test_result/m135/deg_m135_001.jpg) |
| ![m135_2](degree_45_test_result/m135/deg_m135_002.jpg) | ![m135_3](degree_45_test_result/m135/deg_m135_003.jpg) |
| ![m135_4](degree_45_test_result/m135/deg_m135_004.jpg) | |

- **Kết luận**:
  - Tồn tại một số trường hợp mô hình không nhận diện được đối tượng (không đánh được BBox).
  - Phân tích hiện tượng phân loại sai (Bias) theo từng góc test:

| Góc Test | Hiện tượng Bias (Nhận diện lệch) |
| :---: | :--- |
| **+45° (`p45`)** | Bias sang class `Leanbot_right` |
| **-45° (`m45`)** | Bias sang class `Leanbot_right` |
| **+135° (`p135`)** | Bias sang class `Leanbot_back` |
| **-135° (`m135`)** | Bias sang class `Leanbot_left` |

## B. Khó khăn
- Không

## C. Công việc tiếp theo
- Em xin phép nhận hướng đi tiếp theo từ Thầy ạ.