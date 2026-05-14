# Báo cáo công việc ngày 14/05/2026
## A. Công việc đã làm
- Chụp data cho 8 class Leanbot ở các góc 0, +-45, +_90, +-135, 180 độ 
- Chỉnh sửa code Colab để train 8 class
- Tiến hành train và đánh giá kết quả training Model cho 8 class
- Thực nghiệm model trên thực tế và đánh giá một số trường hợp hạn chế 
### 1. Thu thập data cho 8 class Leanbot
- Dữ liệu `raw_image` được thu thập gồm 8 session, mỗi session là ảnh của 1 class
- Mỗi class có 15 ảnh tại các góc chênh lệch -15,0,15 .
- Dữ liệu `raw_image` có cấu trúc như sau :

```text
raw_image/
├── session_20260508_142829/
├── session_20260508_150734/
├── ... (tổng cộng 8 session)
└── session_20260514_095902/
    ├── backgrounds/          # Ảnh nền không có robot
    ├── raw_images/           # 15 ảnh robot với quy tắc đặt tên:
    │   ├── deg_0_xxx.jpg     # 5 ảnh ở góc 0 độ
    │   ├── deg_m15_xxx.jpg   # 5 ảnh ở góc -15 độ (minus)
    │   └── deg_p15_xxx.jpg   # 5 ảnh ở góc +15 độ (plus)
    └── session_metadata.json # Metadata chứa class_name và class_id
```
- Sau khi thu thập ảnh và có `raw_image` ta tiến hành xử lý crop ảnh sa bàn cỡ 1600x1400 --> thêm padding đen thành 1600x1600 --> resize thành 640x640 với tools `crop_tool.py`.
- Kết quả thu được tập dữ liệu `crop_image` với cấu trúc như sau :

```text
crop_images/
├── session_20260508_142829/
├── ...
└── session_20260514_095902/
    ├── aligned_images/     # 15 ảnh (640x640)
    │   ├── deg_0_000.jpg
    │   ├── deg_m15_013.jpg
    │   └── deg_p15_005.jpg
    ├── labels/             # 15 file nhãn YOLO (.txt)
    │   ├── deg_0_000.txt
    │   ├── deg_m15_013.txt
    │   └── deg_p15_005.txt
    └── raw_cropped_images/ # 15 ảnh (1600x1600)
        ├── deg_0_000.jpg
        ├── deg_m15_013.jpg
        └── deg_p15_005.jpg
```
- Sau khi crop ảnh và resize, chạy tools `build_dataset.py` để tạo dataset cho YOLO
- Dataset được lưu ở dạng : 

```text
datasets/
├── images/
│   ├── 000000.jpg
│   ├── 000001.jpg
│   └── ... (được đánh số liên tục)
├── labels/
│   ├── 000000.txt
│   ├── 000001.txt
│   └── ... (tương ứng với file ảnh)
└── manifest.json  # File ánh xạ giúp biết ảnh 000xxx.jpg thuộc session nào
```

### 2. Code notebook Google Colab để train 8 class
- Sau khi đã có tập `datasets`, ta tiến hành chỉnh sửa lại code notebook train Model cho 8 class:
- Sửa cấu hình thành 8 class như sau :
```python
yaml_content = """
path: /content/datasets
train: train/images
val: val/images
test: test/images
nc: 8
names:
  0: Leanbot_0
  1: Leanbot_p45
  2: Leanbot_m45
  3: Leanbot_p90
  4: Leanbot_m90
  5: Leanbot_p135
  6: Leanbot_m135
  7: Leanbot_180
"""
```
- Ngoài cấu hình 8 class ra thì không cần chỉnh sửa gì thêm.
### 3. Training và đánh giá kết quả Model cho 8 class
- Tiến hành train model và đánh giá kết quả :

#### 1.1. Thống kê Datasets

| Session | Class | Số ảnh Background | Số ảnh Raw | Tổng số nhãn |
| :--- | :---: | :---: | :---: | :---: |
| `session_20260508_160321` | `Leanbot_0` | 1 | 15 | 135 |
| `session_20260514_090621` | `Leanbot_p45` | 1 | 15 | 135 |
| `session_20260514_092154` | `Leanbot_m45` | 1 | 15 | 135 |
| `session_20260508_150734` | `Leanbot_p90` | 1 | 15 | 135 |
| `session_20260508_142829` | `Leanbot_m90` | 1 | 15 | 135 |
| `session_20260514_094210` | `Leanbot_p135` | 1 | 15 | 135 |
| `session_20260514_095902` | `Leanbot_m135` | 1 | 15 | 135 |
| `session_20260508_154908` | `Leanbot_180` | 1 | 15 | 135 |
| **Tổng cộng** | | **8** | **120** | **1080** |


#### 1.2. Tỷ lệ chia Dataset (Stratified Split 70/20/10)
- Chia dataset được thực hiện trong Notebook Google Colab 
- Dataset được chi như sau : 
```
Class 0: Total=15, Train=10, Val=3, Test=2
Class 3: Total=15, Train=10, Val=3, Test=2
Class 5: Total=15, Train=10, Val=3, Test=2
Class 7: Total=15, Train=10, Val=3, Test=2
Class 2: Total=15, Train=10, Val=3, Test=2
Class 1: Total=15, Train=10, Val=3, Test=2
Class 4: Total=15, Train=10, Val=3, Test=2
Class 6: Total=15, Train=10, Val=3, Test=2
Đã chia : 80 train, 24 val, 16 test.
```

| Tập | Tỷ lệ | Số ảnh | Số nhãn |
| :--- | :---: | :---: | :---: |
| **Train** | 70% | 80 | 720 |
| **Validation** | 20% | 24 | 216 |
| **Test** | 10% | 12 | 108 |
| **Tổng** | 100% | **120** | **1080** |

#### 1.3. Thông tin Training Model 8 Class


| Thông số | Giá trị |
| :--- | :--- |
| Model nền tảng | `yolov8n.pt` |
| Số class | 8 |
| **Tổng số ảnh** | 120 |
| **Tổng số nhãn** | 1080 |
| **datasets** | 24MB |
| **datasets.zip** | upload ~2 phút|
| Epochs | 100 |
| Batch size | 16 |
| Image size | 640 × 640 |
| Optimizer | AdamW |
| Thời gian Training | ~5 phút |
| Môi trường | Google Colab |
| Link Notebook | [Link Colab](https://git.pythaverse.space/thomha/Nguyen_Huu_Hoang_Anh/blob/master/260514/tools/finetuning_yolo_Leanbot.ipynb) |

#### 1.5. Đánh giá kết quả Training

##### 1.5.1. Khả năng Hội tụ và Mức độ Ổn định (Convergence & Stability)

![Results](Training_result/results.png)

- **Hội tụ:** Các chỉ số Loss (Box Loss, Class Loss, DFL Loss) giảm nhanh trong khoảng 20 epoch đầu, sau đó duy trì ổn định cho đến hết quá trình huấn luyện.
- **Overfitting:** Validation Loss bám sát Training Loss trong suốt 100 epochs, cho thấy mô hình không xảy ra hiện tượng Overfitting trên tập 120 ảnh (15 ảnh/lớp).
- **Độ chính xác:** mAP50 đạt ~0.995 và mAP50-95 đạt ~0.86, cho thấy mô hình nhận diện được Leanbot ở cả 8 hướng với độ chính xác cao với tập dữ liệu train.

##### 1.5.2. Chất lượng Phân loại Class (Confusion Matrix)

![Confusion Matrix Normalized](Training_result/confusion_matrix_normalized.png)
![Confusion Matrix](Training_result/confusion_matrix.png)

- **Đường chéo chính:** Ma trận nhầm lẫn chuẩn hóa có đường chéo chính đạt giá trị tiệm cận 1.0 cho cả 8 lớp, cho thấy mô hình phân loại đúng hướng Robot trong hầu hết các trường hợp với tập datasets trainning
- **Background False Positives:** Tỷ lệ nhầm lẫn với Background ở mức thấp, mô hình ít xảy ra tình trạng phát hiện sai các chi tiết sa bàn thành robot.

##### 1.5.3. Đồ thị Precision, Recall và F1-Score

![Box P Curve](Training_result/BoxP_curve.png)
![Box R Curve](Training_result/BoxR_curve.png)
![Box F1 Curve](Training_result/BoxF1_curve.png)
![Box PR Curve](Training_result/BoxPR_curve.png)

- **Precision & Recall:** Cả hai chỉ số đều đạt mức > 0.99 ở ngưỡng Confidence mặc định, cho thấy tỷ lệ bỏ sót (False Negative) và báo giả (False Positive) đều ở mức thấp.
- **Đường cong PR:** Diện tích dưới đường cong PR (AUC) đạt ~0.995, phản ánh sự cân bằng ổn định giữa Precision và Recall trên toàn bộ dải ngưỡng Confidence.

##### 1.5.4. Phân tích phân phối nhãn (Labels Distribution)

![Labels](Training_result/labels.jpg)

- **Tương quan tọa độ:** Biểu đồ cho thấy các bounding box tập trung ở khu vực trung tâm ảnh, phù hợp với vị trí robot thường xuất hiện trên sa bàn sau khi crop ( vị trí đa số là ở các ô A, B ,C,.. CTRL)
- **Kích thước đối tượng:** Phân phối kích thước bounding box tương đối đồng đều, phản ánh dữ liệu huấn luyện bao quát được nhiều tỷ lệ kích thước khác nhau của robot trong khung hình.

##### 1.5.5. Kết quả model trên tập test 
- Như em đã báo cáo ở phần trên thì tập test có tổng cộng 16 ảnh, mỗi Class có 2 ảnh.
- Kết quả như bảng sau : 

| | | | |
| :---: | :---: | :---: | :---: |
| ![1](test_result/1.png) | ![2](test_result/2.png) | ![3](test_result/3.png) | ![4](test_result/4.png) |
| ![5](test_result/5.png) | ![6](test_result/6.png) | ![7](test_result/7.png) | ![8](test_result/8.png) |
| ![9](test_result/9.png) | ![10](test_result/10.png) | ![11](test_result/11.png) | ![12](test_result/12.png) |
| ![13](test_result/13.png) | ![14](test_result/14.png) | ![15](test_result/15.png) | ![16](test_result/16.png) |

- Kết quả cho thấy hầu hết các ảnh test đầu đạt độ chính xác cao , tuy nhiên có một vài trường hợp bị nhầm lẫn Class . 

##### 1.5.6. Thực nghiệm model trên thực tế
- Tải model `best.pt` vừa train vào folder `tools` sau đó chạy `webcam_infer.py` :
```powershell
python webcam_infer.py --source 1 --model best.pt
```
- Với bộ lọc confidence là `0.5` cho kết quả như sau :

![alt text](image-1.png)

> Dựa vào kết quả có thể thấy Confidence ở một số Class chưa cao ( p90, p135). Và còn bị nhầm lẫn class từ m90 nhầm thành m45 . 

- Một số kết quả test khác : 

**Không detect được Class m45** : 

![alt text](image.png)


**Confidence các Leanbot ảnh hưởng đến nhau ( thay đổi trạng thái của 1 Leanbot thì confidence của Leanbot lân cận cũng bị ảnh hưởng)**

![alt text](image-3.png)
![alt text](image-2.png)

**Nếu cho vật thể lạ (tay người, cục gỗ,...) thì confidence giảm** .

![alt text](image-4.png)
![alt text](image-5.png)

![alt text](image-6.png)
![alt text](image-7.png)

![alt text](image-8.png)
![alt text](image-9.png)

## B. Khó khăn 
- Em thấy model vẫn chưa tối ưu khi thử nghiệm thực tế ạ. Em có cần thu thập thêm data không ạ ?
- Ngoài ra model đang không thực sự học đặc trưng của Leanbot mà còn học thêm cả đặc trưng sa bàn, nếu sa bàn có thêm vật thể khác thì model sẽ bị nhiễu và confidence sẽ giảm ạ.
- Em xin phép đề xuất chụp thêm data ở các môi trường khác (khác hoàn toàn sa bàn ) để Model thực sự học được đặc trưng các góc của Leanbot ạ 

## D. Công việc tiếp theo
- Em xin phép nhận hướng đi tiếp theo từ Thầy ạ.