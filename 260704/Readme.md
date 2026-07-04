# Báo cáo công việc ngày 04/07/2026

# A. Công việc đã làm 
- Đánh giá thông tin kiến trúc, kích thước model đang sử dụng
- Tìm hiểu các phương pháp Optimize inference time cho Model Yolo

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

## 2. Các phương pháp tối ưu thời gian suy luận


### 2.1. Tối ưu runtime và đồ thị tính toán

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

### 2.2. Giảm độ chính xác số ( Lượng tử hóa - Quantization )

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

### 2.3. Giảm kích thước ảnh đầu vào

Khối lượng tính toán của CNN phụ thuộc gần đúng vào diện tích tensor đầu vào:

$$
FLOPs_{\text{new}}
\approx
FLOPs_{640}
\left(
\frac{S_{\text{new}}}{640}
\right)^2
$$

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

# B. Khó khăn
- Không
# C. Công việc tiếp theo
- Tiến hành chỉnh sửa code vẽ biểu đồ, unwrap giá trị góc thay đổi .
- Thử nghiệm đánh giá lại góc khi Leanbot spin tại chỗ
- Em xin phép nhận hướng đi tiếp theo từ Thầy ạ . Trước mắt em nên thử dùng phương pháp Optimize nào trước để đánh giá ạ ? 