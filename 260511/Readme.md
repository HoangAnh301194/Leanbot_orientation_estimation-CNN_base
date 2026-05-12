# Báo cáo công việc ngày 11/05/2026

## A. Công việc đã làm
- Xây dựng và chạy `check_confidence.py` để kiểm tra đầy đủ confidence của từng class và bbox tương ứng trên cùng một object Leanbot.
- Hiển thị bbox tương ứng với từng class/confidence để quan sát mức độ phân biệt giữa các hướng Leanbot.

### 1. Công cụ `check_confidence.py`
- Link code: [https://git.pythaverse.space/thomha/Nguyen_Huu_Hoang_Anh/blob/master/260511/tools/check_confidence.py](https://git.pythaverse.space/thomha/Nguyen_Huu_Hoang_Anh/blob/master/260511/tools/check_confidence.py)
- Mục tiêu:
  - Load trực tiếp mô hình YOLO đã train và lấy raw prediction thay vì chỉ lấy kết quả top-1 mặc định.
  - Giữ lại confidence của toàn bộ class trên từng object sau khi đã match với bbox cuối cùng.
  - Xuất đồng thời ảnh debug và file text log để tiện kiểm tra lại.

- Các bước chính trong code:
  - **Bước 1 - Khởi tạo tool**: thiết lập đường dẫn model, thư mục ảnh test, thư mục output, các ngưỡng confidence/IoU và load mô hình YOLO trên thiết bị phù hợp.
  - **Bước 2 - Đọc và tiền xử lý dữ liệu ảnh**: quét toàn bộ ảnh trong tập test, resize theo chuẩn đầu vào của model, chuẩn hóa ảnh và chuyển sang tensor để sẵn sàng suy luận.
  - **Bước 3 - Trích xuất raw prediction**: chạy suy luận trực tiếp trên model để lấy đầy đủ bbox và confidence của tất cả class, không chỉ lấy class tốt nhất như luồng mặc định.
  - **Bước 4 - Lọc và khớp object sau NMS**: loại bỏ các bbox trùng lặp, sau đó khớp lại từng bbox cuối cùng với prediction gốc để giữ lại vector confidence đầy đủ cho từng object.
  - **Bước 5 - Trực quan hóa confidence theo từng class**: vẽ bbox cho từng class quanh cùng object, gắn nhãn class và confidence để so sánh mức độ tin cậy trực tiếp trên ảnh.
  - **Bước 6 - Lưu kết quả kiểm tra**: xuất ảnh debug và file text log theo từng ảnh đầu vào vào đúng thư mục con trong `yolo_class_bbox_results`.
> Vì các BBox đều trùng hết với nhau và không có sự khác biệt, nên em đã dãn khoảng cách các BBox để dễ quan sát ạ.Thực tế là các BBox trùng hết với nhau ạ.

### 2. Kết quả đầu ra trong `yolo_class_bbox_results`
- Thư mục output hiện có đủ 20 ảnh debug, chia theo 4 góc chụp: `degree_m135`, `degree_m45`, `degree_45`, `degree_135`.
- Mỗi ảnh debug đi kèm một file text log cùng tên để kiểm tra chi tiết confidence của từng class.

#### `degree_45`
| STT | Ảnh kết quả |
| --- | --- |
| 000 | ![](./yolo_class_bbox_results/degree_45/debug_deg_p45_000.jpg) |
| 001 | ![](./yolo_class_bbox_results/degree_45/debug_deg_p45_001.jpg) |
| 002 | ![](./yolo_class_bbox_results/degree_45/debug_deg_p45_002.jpg) |
| 003 | ![](./yolo_class_bbox_results/degree_45/debug_deg_p45_003.jpg) |
| 004 | ![](./yolo_class_bbox_results/degree_45/debug_deg_p45_004.jpg) |

#### `degree_135`
| STT | Ảnh kết quả |
| --- | --- |
| 000 | ![](./yolo_class_bbox_results/degree_135/debug_deg_p135_000.jpg) |
| 001 | ![](./yolo_class_bbox_results/degree_135/debug_deg_p135_001.jpg) |
| 002 | ![](./yolo_class_bbox_results/degree_135/debug_deg_p135_002.jpg) |
| 003 | ![](./yolo_class_bbox_results/degree_135/debug_deg_p135_003.jpg) |
| 004 | ![](./yolo_class_bbox_results/degree_135/debug_deg_p135_004.jpg) |

#### `degree_m45`
| STT | Ảnh kết quả |
| --- | --- |
| 000 | ![](./yolo_class_bbox_results/degree_m45/debug_deg_m45_000.jpg) |
| 001 | ![](./yolo_class_bbox_results/degree_m45/debug_deg_m45_001.jpg) |
| 002 | ![](./yolo_class_bbox_results/degree_m45/debug_deg_m45_002.jpg) |
| 003 | ![](./yolo_class_bbox_results/degree_m45/debug_deg_m45_003.jpg) |
| 004 | ![](./yolo_class_bbox_results/degree_m45/debug_deg_m45_004.jpg) |

#### `degree_m135`
| STT | Ảnh kết quả |
| --- | --- |
| 000 | ![](./yolo_class_bbox_results/degree_m135/debug_deg_m135_000.jpg) |
| 001 | ![](./yolo_class_bbox_results/degree_m135/debug_deg_m135_001.jpg) |
| 002 | ![](./yolo_class_bbox_results/degree_m135/debug_deg_m135_002.jpg) |
| 003 | ![](./yolo_class_bbox_results/degree_m135/debug_deg_m135_003.jpg) |
| 004 | ![](./yolo_class_bbox_results/degree_m135/debug_deg_m135_004.jpg) |

### 3. Đánh giá khách quan kết quả
- Công cụ đã xử lý đủ 20 ảnh test và sinh ra đầy đủ cặp file `debug_*.jpg` và `*_debug.txt`, toàn bộ được lưu trong thư mục `yolo_class_bbox_results` theo từng góc chụp.
- Ngưỡng confidence được đặt ở mức `0.05` để giữ lại toàn bộ score của các class, do đó số lượng detection tăng và bao gồm cả các detection không tương ứng với Leanbot trong thực tế.
- Nhóm `degree_135` cho kết quả ổn định: tổng 57 detection, confidence trung bình khoảng `0.735`, trong đó có 32 detection đạt từ `0.8` trở lên; class tốt nhất chủ yếu là `Leanbot_back` với `44/57` detection.
- Nhóm `degree_45` và `degree_m45` có xác định được hướng chính trong phần lớn detection, tuy nhiên còn xuất hiện hiện tượng chồng lấn giữa các cặp class gần nhau như `back/right` hoặc `front/right`; riêng `degree_45` có 22 detection dưới `0.5`, cho thấy khả năng tách class tại góc này còn chưa ổn định.
- Nhóm `degree_m135` có độ phân bố không đều: confidence trung bình khoảng `0.605`, có 20 detection dưới `0.5`, và kết quả phân bố giữa `Leanbot_left` (`37` detection) và `Leanbot_front` (`26` detection) --> nhầm lẫn giữa các class với nhau nhiều.
- Một số detection rất thấp nằm sát ngưỡng `0.05`, ví dụ trong `deg_m45_000`, `deg_m135_004`, `deg_p135_004`. --> Vì khi lọc với confidence rât thấp thì cả những vật thể xugn quang cũng có thể tính là Object Leanbot, tuy nhiên với confidence của các detection này là rất thấp nên không ảnh hưởng nhiều đến bài toán.

## B. Khó khăn
- Khi kiểm tra confidence giữa các class, phương pháp dùng YOLO để phân biệt các hướng của Leanbot vẫn cần được đánh giá thêm về độ ổn định, đặc biệt tại các góc trung gian hoặc các góc có khả năng gây nhầm lẫn giữa các class.
- Một hướng có thể xem xét bổ sung là sử dụng YOLO Pose/keypoint để mô tả đặc trưng hình học của Leanbot, thay vì chỉ dựa trên classification/detection theo bbox.
## C. Công việc tiếp theo
- Tiếp tục đánh giá phương án phân biệt hướng Leanbot và xem xét khả năng mở rộng sang hướng YOLO Pose/keypoint nếu cần.
