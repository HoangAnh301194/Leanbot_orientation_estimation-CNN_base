# Báo cáo công việc ngày 04/05/2026

## A. Công việc đã làm
- Báo cáo lại các file code Python trong bộ `tools`
- Báo cáo lại cấu trúc datasets
- Gắn nhãn cho 2 class `Leanbot_back` và `Leanbot_front` -> tiến hành training và đánh giá kết quả.

### 1. Báo cáo lại các file code Python trong bộ `tools`
- Hiện tại bộ Tools bao gồm các file sau :

| Tên file |Link code| Vai trò trong Pipeline | Công dụng |
| :--- | :--- | :--- | :---|
| **`capture_session.py`** | [Code](tools/capture_session.py) | **1. Thu thập** | Công cụ chụp ảnh mẫu (background) và ảnh thực tế (raw) từ camera để tạo session. |
| **`mask_roi.py`** | [Code](tools/mask_roi.py) | **2. Cấu hình** | Hỗ trợ chọn vùng làm việc (ROI) bằng cách click chuột để loại bỏ nhiễu ngoài bàn. |
| **`process_auto_label.py`** | [Code](tools/process_auto_label.py) | **3. Xử lý** | Script chính chạy gán nhãn tự động cho Session dựa trên phương pháp Mask-based. |
| **`auto_label_core.py`** | [Code](tools/auto_label_core.py) | **Thư viện lõi** | Chứa toàn bộ logic xử lý chính (Merge BBox, Alignment, Image Diff). |
| **`alignment.py`** | [Code](tools/alignment.py) | **Thư viện con** | Hỗ trợ thuật toán căn chỉnh ảnh ECC. |
| **`abstract_hsv.py`** | [Code](tools/abstract_hsv.py) | **Thư viện con** | Hỗ trợ so sánh ảnh trên các không gian màu khác nhau. |
| **`build_dataset.py`** | [Code](tools/build_dataset.py) | **4. Tổng hợp** | Gom tất cả session đã gán nhãn vào một bộ Dataset chuẩn YOLO để train. |
| **`webcam_infer.py`** | [Code](tools/webcam_infer.py) | **5. Kiểm tra** | Chạy thử nghiệm model thực tế từ webcam (Inference). |

### 2. Cấu trúc Datasets
- 
## B. Khó khăn
## C. Công việc tiếp theo