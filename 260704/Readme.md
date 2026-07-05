# Báo cáo công việc ngày 04/07/2026

# A. Công việc đã làm 
- Đánh giá thông tin kiến trúc, kích thước model đang sử dụng và model Leanbot detection ban đầu. 
- Tìm hiểu các phương pháp Optimize inference time cho Model 
- Thử nghiệm và đánh giá các phương pháp có thể tiến hành ngay.

## 1. Đánh giá thông tin kiến trúc, kích thước model đang sử dụng


Scripts phân tích sử dụng thư viện Ultralytics: [`tools/check_model_info.py`](tools/check_model_info.py).

Kết quả thu được chia thành các nhóm thông tin như sau:

### 1.1 Thông số vật lý & Kiến trúc mạng (Architecture)
- **File model:** `tools/best_24Class_Soft_Angular_BCE.pt`
- **Kích thước file model:** 5.97 MB 
- **Tổng số Layers:** 130 layers.
- **Tổng số Parameters:** 3,015,528 params
- **Khối lượng tính toán (GFLOPs):** 8.2 GFLOPs.

  > **Khái niệm GFLOPs:**
  > - **GFLOPs** (Giga Floating-point Operations Per Second) là chỉ số đo lường độ phức tạp của mô hình khi chạy suy luận (inference).
  > - 1 GFLOP tương đương với **1 tỷ phép tính** dấu phẩy động.
  > - **8.2 GFLOPs** nghĩa là: Để nhận diện xong *chỉ một bức ảnh duy nhất*, bộ vi xử lý phải thực hiện **8.2 tỷ phép tính toán học**.

### 1.2 Bài toán & Tập dữ liệu nhận diện (Task & Classes)
- **Loại tác vụ (Task):** Object Detection (`detect` - Nhận diện BBox).
- **Số lượng nhãn (Classes):** 24 Classes.
- **Chi tiết nhãn:** `Leanbot_0`, `Leanbot_p15`, `Leanbot_p30`,..., `Leanbot_m15`.

### 1.3 Cấu hình môi trường lúc Huấn luyện (Training Config)
- **Model nền tảng (Base Model):** Pre-trained weights `yolov8n.pt`.
- **Kích thước ảnh đầu vào (Image Size):** 640x640 pixel.
- **Số vòng huấn luyện (Epochs):** 100 vòng.
- **Kích thước lô ảnh (Batch size):** 16.
- **Bộ tối ưu hóa (Optimizer):** `auto` (SGD hoặc AdamW).
- **Thiết bị train:** GPU (`device: '0'` - mặc định sử dụng trên Google Colab).
- **File Dataset:** `leanbot_data.yaml`.

### 1.4 Các kỹ thuật tăng cường dữ liệu đã dùng (Data Augmentation)
Mô hình đã được train kết hợp với các kỹ thuật làm nhiễu/làm méo ảnh để tăng độ tổng quát hóa:
- **Mosaic (Ghép 4 ảnh):** Được bật 100% lúc train (tắt ở 10 epochs cuối).
- **Xoay ảnh (Rotation):** $\pm$ 10.0 độ.
- **Tịnh tiến (Translate):** Di chuyển tối đa 10% khung hình.
- **Phóng to/Thu nhỏ (Scale):** Tỉ lệ Scale up/down lên tới 50%.
- **Xóa ngẫu nhiên (Erasing):** Che lấp ngẫu nhiên 40% chi tiết trên ảnh.

**Nhận xét chung:**
- Mô hình thuộc loại model nhẹ (YOLOv8 Nano). 
- File nặng ~6MB, mức độ phức tạp tính toán 8.2 GFLOPS. 
- Độ phức tạp tính toán có thể là nguyên nhân khiến tốc độ thực tế đang giới hạn ở mức 5-8 FPS. 


## 2. Đánh giá thông tin kiến trúc, kích thước model Detection Leanbot Class ban đầu


### 2.1 Thông số vật lý & Kiến trúc mạng (Architecture)
- **File model:** `models/leanbot_colab.pt`
- **Kích thước file model:** 5.94 MB 
- **Tổng số Layers:** 130 layers.
- **Tổng số Parameters:** 3,011,043 params
- **Khối lượng tính toán (GFLOPs):** 8.2 GFLOPs.

### 2.2 Bài toán & Tập dữ liệu nhận diện (Task & Classes)
- **Loại tác vụ (Task):** Object Detection (`detect`).
- **Số lượng nhãn (Classes):** 1 Class.
- **Chi tiết nhãn:** `Class 0: Leanbot`

### 2.3 Cấu hình môi trường lúc Huấn luyện (Training Config)
- **Model nền tảng (Base Model):** `yolov8n.pt`.
- **Kích thước ảnh đầu vào (Image Size):** 640x640 pixel.
- **Số vòng huấn luyện (Epochs):** 100 vòng.
- **Kích thước lô ảnh (Batch size):** 16.
- **Thiết bị train:** GPU (`device: '0'`).
- **File Dataset:** `configs/leanbot_data_colab.yaml`.

### 2.4 Các kỹ thuật tăng cường dữ liệu đã dùng (Data Augmentation)
- **Mosaic (Ghép 4 ảnh):** 100% (1.0).
- **Xoay ảnh (Rotation):** $\pm$ 10.0 độ.
- **Tịnh tiến (Translate):** $\pm$ 10% (0.1).
- **Phóng to/Thu nhỏ (Scale):** $\pm$ 50% (0.5).
- **Xóa ngẫu nhiên (Erasing):** 40% (0.4).

**Nhận xét so sánh (1 Class vs 24 Class):**
- Hai model có cấu trúc mạng giống hệt nhau (YOLOv8n) và khối lượng tính toán GFLOPs hoàn toàn tương đồng (8.2 GFLOPs). Sự khác biệt duy nhất nằm ở kích thước ma trận lớp Output cuối cùng (1 class vs 24 class) dẫn tới số Parameter chênh lệch vô cùng nhỏ (3,011,043 vs 3,015,528).

## 3. Các phương pháp tối ưu thời gian suy luận


### 3.1. Tối ưu runtime và đồ thị tính toán

Mô hình hiện tại được lưu dưới định dạng PyTorch `.pt`. Khi suy luận trực tiếp bằng PyTorch, chương trình phải thực hiện nhiều thao tác quản lý tensor, gọi kernel và điều phối toán tử trong thời gian chạy.

Có thể chuyển mô hình sang các runtime chuyên dụng như ONNX Runtime, OpenVINO hoặc TensorRT để tối ưu đồ thị tính toán.

#### ONNX Runtime

ONNX là định dạng trung gian dùng để biểu diễn mô hình dưới dạng đồ thị tính toán tĩnh. ONNX Runtime có thể thực hiện:

- Loại bỏ các node không cần thiết.
- Constant Folding.
- Gộp lớp Convolution và Batch Normalization.
- Gộp các toán tử liên tiếp.
- Giảm số tensor trung gian.
- Tối ưu thứ tự thực thi và truy cập bộ nhớ.

Ưu điểm của ONNX là khả năng tương thích với nhiều nền tảng và phần cứng. Tuy nhiên, ONNX chỉ là định dạng mô hình; tốc độ thực tế phụ thuộc vào Execution Provider được sử dụng, ví dụ CPU, CUDA, TensorRT hoặc OpenVINO.

#### OpenVINO

OpenVINO là runtime phù hợp khi mô hình được triển khai trên CPU Intel, GPU tích hợp Intel hoặc Intel NPU.

OpenVINO có thể tối ưu kernel cho kiến trúc CPU và hỗ trợ các chế độ FP32, FP16 và INT8. Nếu chương trình chỉ chạy trên CPU Intel, OpenVINO thường là lựa chọn phù hợp hơn so với chạy trực tiếp bằng PyTorch.

#### TensorRT

TensorRT là bộ công cụ tối ưu suy luận dành cho GPU NVIDIA và các thiết bị Jetson.

Trong quá trình xây dựng TensorRT Engine, TensorRT có thể:

- Gộp nhiều layer thành một GPU kernel.
- Lựa chọn thuật toán tính toán phù hợp cho từng layer.
- Tối ưu cấp phát bộ nhớ.
- Giảm dữ liệu trung gian.
- Sử dụng Tensor Cores.
- Hỗ trợ FP32, FP16 và INT8.
- Tối ưu cho kích thước tensor đầu vào cố định.

TensorRT Engine thường phụ thuộc vào kiến trúc GPU, phiên bản CUDA và phiên bản TensorRT của thiết bị triển khai.

### 3.2 Giảm độ chính xác số (Lượng tử hóa - Quantization)

#### FP16

Mặc định, mô hình thường sử dụng số thực 32 bit, ký hiệu FP32. Khi chuyển sang FP16, mỗi giá trị chỉ sử dụng 16 bit.

FP16 có thể giúp:

* Giảm dung lượng lưu trữ trọng số.
* Giảm lượng dữ liệu truyền giữa bộ nhớ và GPU.
* Giảm mức sử dụng VRAM.
* Tăng tốc phép nhân ma trận trên GPU có Tensor Cores.



#### INT8

INT8 sử dụng số nguyên 8 bit để biểu diễn trọng số và activation. So với FP32, INT8 giúp giảm đáng kể dung lượng bộ nhớ và băng thông truyền dữ liệu.

Tuy nhiên, lượng tử hóa INT8 yêu cầu một calibration dataset đại diện cho dữ liệu thực tế. Tập calibration cần bao gồm:

- Nhiều góc quay Leanbot.
- Các điều kiện ánh sáng khác nhau.
- Trường hợp nhiều Leanbot xuất hiện đồng thời.
- Leanbot ở gần biên ảnh.
- Trường hợp che khuất hoặc phản xạ ánh sáng.


Đối với bài toán 24 lớp góc, các lớp chỉ cách nhau 15 độ. Vì vậy, sai số lượng tử hóa nhỏ cũng có thể làm dự đoán chuyển sang lớp góc liền kề. INT8 chỉ nên thử nghiệm sau khi TensorRT FP16 vẫn chưa đạt tốc độ yêu cầu.

### 3.3 Giảm kích thước ảnh đầu vào

Khối lượng tính toán của CNN phụ thuộc gần đúng vào diện tích tensor đầu vào:

<p align="center"><img src="https://latex.codecogs.com/svg.image?FLOPs_{new}\approx%20FLOPs_{640}\times\left(\frac{S_{new}}{640}\right)^2" alt="FLOPs formula" /></p>

Với mô hình hiện tại có độ phức tạp 8.2 GFLOPs tại kích thước `640 × 640`, có thể ước lượng:

| Kích thước đầu vào | Tỷ lệ số pixel | GFLOPs ước tính |
| -----------------: | -------------: | --------------: |
|        `640 × 640` |           100% |            8.20 |
|        `512 × 512` |            64% |            5.25 |
|        `416 × 416` |         42.25% |            3.46 |
|        `320 × 320` |            25% |            2.05 |

Khi giảm từ `640 × 640` xuống `320 × 320`, số pixel giảm còn 25%, vì vậy khối lượng tính toán lý thuyết cũng giảm còn khoảng một phần tư.

Tuy nhiên, FPS thực tế không nhất thiết tăng bốn lần do thời gian đọc camera, hậu xử lý, hiển thị và truyền dữ liệu không giảm hoàn toàn theo kích thước ảnh.

Ngoài ra, nếu một ảnh chứa nhiều Leanbot thì mỗi robot chỉ chiếm một vùng nhỏ. Giảm resolution quá mạnh có thể làm mất các đặc trưng dùng để phân biệt hướng quay.

## 4. Thực nghiệm, đánh giá các phương pháp Optimize Inference time
Dựa theo độ phức tạp của phương pháp và khả năng triển khai được ngay thì các phương pháp được thực hiện theo thứ tự như sau : 
    1. Giảm kích thước ảnh đầu vào (Hiện tại là 640x640)
    2. Graph Optimization - sử dụng Runtime tối ưu cho phần cứng (TensorRT, OpenVINO, ONNX Runtime)
    3. Giảm độ chính xác số ( Lượng tử hóa - Quantization )
        - 3.1. Lượng tử hóa FP16 ( Giảm độ chính xác số từ 32 bit xuống 16 bit )
        - 3.2. Lượng tử hóa INT8 ( Giảm độ chính xác số từ 32 bit xuống 8 bit )

### 4.1 Giảm kích thước ảnh đầu vào
- Model sử dụng : [tools/best_24Class_Soft_Angular_BCE.pt](tools/best_24Class_Soft_Angular_BCE.pt)
- Kích thước ảnh đầu vào hiện tại : 640x640
- Các mức kích thước (Resolution) sẽ thử nghiệm: `512x512`, `416x416`, `320x320`.
    - Kiến trúc mạng YOLOv8 có hệ số thu nhỏ (max stride) lớn nhất qua các khối Tích chập (Conv) là 32. Do đó, kích thước chiều dài/rộng ảnh đầu vào bắt buộc phải là **bội số của 32** để tránh lỗi tính toán ma trận ở các layer cuối cùng nên các mức thử nghiệm là 512x512, 416x416, 320x320.
- Scripts sử dụng : [`tools/benchmark_imgsz.py`](tools/benchmark_imgsz.py)
- Lệnh chạy: 
  ```bash
  python tools/benchmark_imgsz.py
  ```
- Ảnh được test: `24class_test_images/000021.jpg`

  <img src="./24class_test_images/000021.jpg" width="400" />

Ảnh được trải qua các bước sau khi đưa 1 frame ảnh qua model ( chưa tính thời gian cho các bước ước lượng góc, chỉ tính mỗi thời gian đi qua model để có ouput cho các bước ước tính vector, ước lượng góc, tạo csv,...)
1. **Tiền xử lý (Pre-process)**: Resize ảnh, thêm padding,...đưa ảnh từ kích thước gốc về kích thước vuông của mạng (ví dụ 640x640 hoặc 416x416), chuyển đổi hệ màu BGR sang RGB của PyTorch, chuẩn hóa giá trị Pixel thành Tensor và đẩy vào bộ nhớ.
2. **Suy luận (Inference)**: Dữ liệu ảnh chạy qua các khối mạng Convolution của YOLO để tính toán đặc trưng.
3. **Hậu xử lý (Post-process)**: Xử lý ma trận dự đoán đầu ra để tạo ra kết quả cuối cùng để cho các bước ứng dụng kế tiếp.

- Kết quả đánh giá trên tập ảnh test (4 ảnh, các giá trị được chia trung bình):

| Kích thước (imgsz) | Tiền xử lý (ms) | Suy luận (ms) | Hậu xử lý (ms) | Ước tính FPS |
| :--- | :---: | :---: | :---: | :---: |
| **640x640** | 3.68 ms | 104.77 ms | 1.02 ms | **9.14 FPS** |
| **512x512** | 1.81 ms | 72.81 ms | 0.99 ms | **13.23 FPS** |
| **416x416** | 1.29 ms | 54.09 ms | 0.95 ms | **17.75 FPS** |
| **320x320** | 0.97 ms | 42.80 ms | 0.92 ms | **22.38 FPS** |

> **Kết luận** : Từ thực nghiệm cho thấy khi giảm kích thước ảnh đầu vào sẽ tăng tốc độ suy luận của mô hình, tuy nhiên sẽ làm giảm độ chính xác của mô hình. Cụ thể, vì model được train ở kích thước 640x640 nên khi giảm kích thước ảnh đầu vào sẽ làm giảm kích thước của feature map, tức là hình ảnh Leanbot sẽ mờ hơn và nhỏ đi có thể dẫn tới việc giảm độ chính xác model (có thể phải train lại với đúng kích thước ảnh mong muốn)

### 4.2 Graph Optimization (Tối ưu cấu trúc đồ thị)
- Model gốc sử dụng: [tools/best_24Class_Soft_Angular_BCE.pt](tools/best_24Class_Soft_Angular_BCE.pt)
- Nền tảng thực nghiệm: Máy tính sử dụng vi xử lý **CPU Intel**.
- **Giải pháp lựa chọn:** Dựa trên cấu hình phần cứng hiện tại là CPU Intel, hai Runtime tối ưu nhất được đề xuất thực nghiệm là:
    1. **ONNX Runtime (Định dạng `.onnx`):** 
    2. **OpenVINO (Định dạng `.xml` và `.bin`):** 

- **Cách thức thực hiện:**
  Quá trình chuyển đổi (Graph Export) được thực hiện thông qua API của Ultralytics trên nền tảng PyTorch. Đồ thị mạng nơ-ron động của `.pt` sẽ được dò vết (Graph Tracing), loại bỏ các thành phần chỉ dùng cho quá trình Huấn luyện (như tham số tính Gradient) và lưu lại dưới định dạng đồ thị tĩnh.

  **Script minh họa quá trình chuyển đổi:**
  ```python
  from ultralytics import YOLO

  # 1. Tải mô hình PyTorch gốc (.pt)
  model = YOLO("tools/best_24Class_Soft_Angular_BCE.pt")

  # 2. Export sang định dạng ONNX (Tối ưu hóa đồ thị tiêu chuẩn)
  onnx_path = model.export(format="onnx", imgsz=416, half=False)
  print(f"Đã xuất thành công file ONNX tại: {onnx_path}")

  # 3. Export sang định dạng OpenVINO (Tối ưu hóa chuyên sâu cho vi xử lý Intel)
  openvino_path = model.export(format="openvino", imgsz=416, half=False)
  print(f"Đã xuất thành công thư mục OpenVINO tại: {openvino_path}")
  ```
  > Sau khi thực thi 2 phương thức trên, các model tĩnh mới sẽ được tự động tạo ra. Ta tiếp tục sử dụng các file model mới này đưa vào Script Benchmark model để so sánh đối chiếu thời gian Suy luận.

- **Code thực hiện chuyển đổi và Benchmark:** [`tools/export_benchmark.py`](tools/export_benchmark.py)

- **Kết quả so sánh tốc độ các Runtime** (Cố định vòng lặp trên toàn bộ 4 ảnh ở mức `imgsz=640`):

| Định dạng Model | Tiền xử lý (ms) | Suy luận (ms) | Hậu xử lý (ms) | Ước tính FPS |
| :--- | :---: | :---: | :---: | :---: |
| **PyTorch Gốc (.pt)** | 3.07 ms | 101.10 ms | 1.15 ms | **9.49 FPS** |
| **ONNX Runtime** | 7.59 ms | 104.79 ms | 2.97 ms | **8.67 FPS** |
| **OpenVINO (Intel)** | 6.68 ms | 182.25 ms | 1.72 ms | **5.25 FPS** |

> **Kết luận:** Trên vi xử lý Core i3-1115G4 của laptop hiện tại, ở độ phân giải gốc (640x640), PyTorch thuần túy lại cho tốc độ nhanh hơn (~9.5 FPS). 
Nguyên nhân khiến cho FPS của ONNX Runtime và OpenVINO thấp hơn thì em cũng chưa rõ, em sẽ tìm hiểu thêm các bài báo benchmark để khảo sát ạ.

### 4.3 Lượng tử hóa (Quantization)
Lượng tử hóa là kỹ thuật nén mô hình bằng cách cắt giảm số lượng bit dùng để biểu diễn các tham số trọng số (weights) của mạng neural từ số thực 32-bit (FP32) nguyên bản xuống mức thấp hơn.

**Các mức lượng tử hóa cần thực nghiệm:**
1. **Lượng tử hóa FP16 (Half Precision - 16 bit):** 
   - *Đặc điểm:* Giảm dung lượng mô hình đi một nửa so với gốc, hầu như không làm ảnh hưởng đến độ chính xác (mAP).
   - *Triển khai:* mô hình không cần phải điều chỉnh lại thuật toán toán học. Trong Ultralytics, chỉ cần thêm cờ `half=True` khi thực hiện gọi hàm Export.

2. **Lượng tử hóa INT8 (Integer - 8 bit):**
   - *Đặc điểm:* Giảm dung lượng mô hình xuống 4 lần, tốc độ suy luận nhanh hơn so với FP16. Tuy nhiên, việc ép số thực về số nguyên sẽ dẫn tới sai số làm giảm độ chính xác nhận diện.
   - *Yêu cầu bắt buộc (Calibration Dataset):* Bắt buộc phải có một tập dữ liệu hiệu chuẩn (Calibration Dataset). Đây là tập các bức ảnh đại diện được đưa vào để đo đạc và căn chỉnh lại dải giá trị (Range) của các phép nhân ma trận. Nếu bỏ qua bước nạp Calibration Dataset, model INT8 xuất ra sẽ bị giảm độ chính xác nhận diện đáng kể.

- Vì INT8 cần có tập ảnh dataset riêng để thực hiện calibration, em sẽ thực hiện thử nghiệm phương pháp lượng tử hóa FP16 và so sánh với model gốc trước ạ. 
- **Scripts thực hiện Lượng tử hóa FP16 và Benchmark:** [`tools/export_fp16_benchmark.py`](tools/export_fp16_benchmark.py)

- **Bảng Kết quả so sánh tốc độ (Quantization FP16 vs FP32 Gốc):**
| Định dạng Model | Tiền xử lý (ms) | Suy luận (ms) | Hậu xử lý (ms) | Ước tính FPS |
| :--- | :---: | :---: | :---: | :---: |
| **PyTorch (FP32 Gốc)** | 3.51 ms | 119.26 ms | 1.35 ms | **8.06 FPS** |
| **ONNX (FP16)** | 6.40 ms | 87.30 ms | 2.40 ms | **10.41 FPS** |
| **OpenVINO (FP16)** | 8.23 ms | 24.77 ms | 2.16 ms | **28.44 FPS** |

> **Kết luận:** Sau khi nén Lượng tử hóa xuống mức FP16, OpenVINO đã cải thiện tốc độ tính toán đáng kể. Thời gian suy luận (Inference) giảm từ 182.25ms (ở bản FP32) xuống chỉ còn **24.77ms**, giúp tăng số Khung hình/giây lên **28.44 FPS** (Nhanh gấp 3.5 lần so với PyTorch gốc). Mặc dù không cần điều chỉnh thuật toán hay dùng Calibration Dataset, phương pháp này đã tận dụng rất tốt phần cứng CPU để tăng tốc độ.

## B. Khó khăn
- Không
## C. Công việc tiếp theo
- Em xin phép nhận hướng đi tiếp theo từ Thầy ạ .