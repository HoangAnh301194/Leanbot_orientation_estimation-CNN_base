# Báo cáo công việc ngày 20/07/2026

## A. Công việc đã làm 
- Debug quá trình lost tracking 
- Quay 1 video lại để các định thời điểm, frame debug dễ hơn
- Debug , phân tích pipeLine của model full frame static 640x640.
### 1. Debug quá trình lost tracking 
- Video được quay ở FPS = 30
- Độ phân giải : Full HD (1920x1080)
- Các bước biến đổi kích thước, hình thái ảnh:

**Full frame model (static 640x640):**

| Bước | Mô tả | Độ phân giải kiểm chứng | Ảnh |
|------|-------|-------------------------|-----|
| 1 | Frame gốc từ video | ![full_raw_frame](imgszdebug/full_raw_frame.png) | ![full_01_raw_frame](imgszdebug/full_01_raw_frame.png) |
| 2 | Sau khi crop 62.5% giữa | ![full_cropped](imgszdebug/full_cropped.png) | ![full_02_cropped](imgszdebug/full_02_cropped.png) |
| 3 | Sau khi padding thành hình vuông | ![full_padded](imgszdebug/full_padded.png) | ![full_03_padded](imgszdebug/full_03_padded.png) |
| 4 | Sau khi resize về 640×640 (đưa vào model) | ![resize640](imgszdebug/resize640.png) | ![resized640](imgszdebug/full_04_resized_640.png) |

**ROI tracking model (static 160x160):**

| Bước | Mô tả | Độ phân giải kiểm chứng | Ảnh |
|------|-------|-------------------------|-----|
| 1 | Frame gốc từ video | ![full_01_raw_frame](imgszdebug/full_raw_frame.png) | ![full_01_raw_frame](imgszdebug/full_01_raw_frame.png) |
| 2 | Vùng ROI được cắt ra (kích thước bội 32) | ![roi_cropped](imgszdebug/roi_cropped.png) | ![roi_02_cropped_roi](imgszdebug/roi_02_cropped_roi.png) |
| 3 | Sau khi resize về 160×160 (đưa vào model) | ![roi_160x160](imgszdebug/roi_160x160.png) | ![roi_03_resized_160](imgszdebug/roi_03_resized_160.png) |


> Các bước resize ảnh đã theo đúng chuẩn luồng hoạt động --> Lỗi khiến việc mất tracking không đến từ lý do này 

- **Các lỗi có thể có để tiến hành debug kiểm tra :** 
    - Điều kiện vẽ BBox để tính ra ROI của Full frame model (static 640x640)
    - Điều kiện để tính là có Leanbot để trích xuất ra góc + vẽ bbox (Roi tracking model static 160x160)

#### 1.1 Debug lỗi của full frame model (static 640x640)
- **Output của model full frame (640x640):**
    - Frame được center-crop còn 62.5% chiều rộng, padding thành ảnh vuông, sau đó resize về `640x640`.
    - Input tensor OpenVINO có shape `[1, 3, 640, 640]`.
    - Output raw no-NMS tensor có shape `[1, 28, 8400]`; sau khi chuẩn hóa trong code có shape `[8400, 28]`.
    - Mỗi anchor có cấu trúc: `[x_center, y_center, width, height, score_class_0, ..., score_class_23]`.
    - `28` = `4 giá trị bounding box` +` 24 confidence tương ứng với 24 class góc Leanbot`.
    - `8400` = `80x80 + 40x40 + 20x20` anchor từ ba feature map.
    - Đây là output raw, chưa thực hiện NMS và chưa phải bounding box cuối cùng.


- **Điều kiện hiện tại để lọc ra Leanbot BBox trong PipeLine Roi tracking:**
    1. Model static 640 trả về cố định `8400` raw anchor. Với mỗi anchor, lấy confidence lớn nhất trong `24` class làm confidence đại diện để thực hiện bước lọc tiếp theo.
    2. Giữ các anchor có confidence lớn hơn `--conf`, mặc định đang đặt là `0.25`.
    3. Lấy Top-K anchor có confidence cao nhất, mặc định đang đặt là `100` anchor.
    4. Dùng toàn bộ 24 class score để tính vector góc cho từng anchor.
    5. Gom các anchor có IoU lớn hơn `--iou`, mặc định đang đặt là `0.5`.
    6. Tính bounding box trung bình có trọng số và vector tổng cho từng group (`vector_magnitude`)
    7. Loại các group có `vector_magnitude` nhỏ hơn `--min-mag`, mặc định đang đặt là `2.0`.
    8. Chọn group có `vector_magnitude` lớn nhất làm kết quả Leanbot cuối cùng.
    9. Điều kiện vẽ bounding box hiện tại là `vector_magnitude > 0`, 

- **Điều kiện ghi các thông tin liên quan đến output model vào CSV:**
    1. Mỗi frame đang recording đều có một dòng CSV. Các giá trị thật của bbox, `best_conf`, `vector_magnitude` và `angle` chỉ có khi pipeline tìm được ít nhất một group hợp lệ.
    2. Một group sẽ bao gồm các anchor được gom lại từ những anchor vượt ngưỡng confidence (`0.25` với FULL 640, `0.15` với ROI 160), tạo được group theo IoU (`IoU >= 0.5`) và có `vector_magnitude >= 2.0`.
    3. Nếu có nhiều group hợp lệ, chỉ thông tin của group có `vector_magnitude` lớn nhất được trả về và ghi vào CSV.
    4. `vector_magnitude` là độ lớn vector tổng hợp của toàn bộ anchor trong group được chọn.
    5. `angle` là góc của vector tổng hợp group, được tính từ toàn bộ score của 24 class góc bằng `atan2(sum_y, sum_x)`; không phải chỉ lấy góc của class có confidence lớn nhất.
    6. `x_center`, `y_center`, `width`, `height` là bbox trung bình có trọng số của group được chọn, sau đó được chuyển về hệ tọa độ frame gốc. (BBox của Leanbot)
    7. Nếu không có anchor vượt confidence, không tạo được group hoặc mọi group đều có `vector_magnitude < 2.0`, hàm trả về bbox, `best_conf`, `vector_magnitude` và `angle` bằng `0`; CSV sẽ ghi các giá trị `0` tương ứng.

> Các thôgn số ảnh hưởng tới việc lọc anchor để vẽ ra bbox group là : `--conf` , `--topk` , `--iou` , `--min-mag` và `--roi_conf` đối với roi tracking model . Trước mắt giảm toàn bộ về nhỏ nhất để thử . 
- **Chạy test model full frame riêng:**
```bash
python tools/roi_tracking_baseline_infer.py --show --video videoTest/test.mp4 --mode baseline --log fullframe_test.csv --full-model models/YOLO11n_versions/FP16_NO_NMS/best_640_openvino_model --tracking-model models/YOLO11n_versions/FP16_NO_NMS/best_160_openvino_model --conf 0.01 --iou 0.5 --topk 100 --min-mag 0.0
```
- **Chạy test full roi tracking mode :**
```bash
python tools/roi_tracking_baseline_infer.py --show --video videoTest/test.mp4 --mode roi --log fullframe_test.csv --full-model models/YOLO11n_versions/FP16_NO_NMS/best_640_openvino_model --tracking-model models/YOLO11n_versions/FP16_NO_NMS/best_160_openvino_model --conf 0.01 --roi_conf 0.01 --iou 0.5 --topk 100 --min-mag 0.0 
```

- Debug quá trình chạy inference 

## B. Khó khăn 

## C. Công việc tiếp theo 
