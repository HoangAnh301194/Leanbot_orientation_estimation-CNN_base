# Báo cáo công việc ngày 01/10/2026

## A. Công việc đã làm
- Chỉnh sửa cơ chế thu thập dataset khi ROI tracking bị mất.
- Dataset mới lấy trực tiếp ROI raw tại frame ROI tracker bị fail, sau đó resize trực tiếp lên 640x640 để phục vụ train bổ sung.

### 1. Checklist chỉnh sửa lost-tracking dataset
- [x] Giữ nguyên cơ chế `calculate_roi()`: ROI có kích thước động, vuông, cạnh bằng khoảng 2 lần cạnh lớn nhất của BBOX và làm tròn lên bội số 32.
- [ ] Giữ lại `lost_roi_input = roi_input.copy()` trước bước resize ROI về 160x160 để inference.
- [ ] Chỉ thu sample khi lỗi xảy ra ở `inference_mode == "ROI"`; không lấy các frame FULL-search thất bại.
- [ ] Lưu `roi_rect = (rx, ry, rw, rh)` của đúng frame bị lost.
- [ ] Khi tracking thành công, cache BBOX/angle/confidence/class gần nhất ở hệ tọa độ full frame.
- [ ] Khi ROI tracking fail, chuyển BBOX đã cache từ full-frame coordinate sang ROI coordinate bằng offset `(rx, ry)`.
- [ ] Clip BBOX vào biên ROI và bỏ sample nếu BBOX sau clip không hợp lệ.
- [ ] Tính lại YOLO normalized label theo kích thước ROI `rw x rh`.
- [ ] Tạo ảnh dataset bằng `cv2.resize(lost_roi_input, (640, 640))`; không dùng chuỗi ROI -> 160 -> 640.
- [ ] Giữ `metadata/` và `check_labels/` để kiểm tra pseudo-label trước khi train.
- [ ] Giữ background writer/queue để không block camera inference.
- [ ] Đổi từ giới hạn 1 sample/run sang 1 sample/lost episode.
- [ ] Lost episode kết thúc khi detect thành công trở lại; episode tiếp theo được phép lưu thêm 1 sample trong cùng run.
- [ ] Giữ `lost_tracking_captures/` tách riêng để debug.

### 2. Behavior mong muốn

```text
TRACKING
TRACKING
ROI LOST       <- lưu sample #1
FULL SEARCH
FULL SEARCH
FULL DETECT    <- kết thúc lost episode
ROI TRACKING
ROI TRACKING
ROI LOST       <- lưu sample #2
FULL SEARCH
```

Mỗi lost episode chỉ lấy frame ROI fail đầu tiên, nhưng một run có thể chứa nhiều lost episode.

### 3. Pipeline dataset mục tiêu

```text
successful detection
        |
        v
calculate_roi()
        |
        v
raw ROI (ví dụ 224x224)
        |
        +--> resize 160x160 --> tracking model
                              |
                              +--> FAIL
                                    |
                                    v
                           lấy raw ROI 224x224
                                    |
                         full bbox -> ROI bbox
                                    |
                         YOLO normalize theo ROI
                                    |
                         resize raw ROI -> 640x640
                                    |
                    images / labels / metadata / check_labels
```

- Lệnh chạy dự kiến: dùng `--save-lost` như hiện tại.
- Label là pseudo-label kế thừa từ detection thành công gần nhất nên vẫn phải review trước khi đưa vào train.

## B. Khó khăn
- BBOX được cache ở hệ tọa độ full frame trong khi ảnh train mới là ROI; cần transform đúng trước khi serialize YOLO label.
- Không được lấy ảnh 160x160 đã dùng cho inference rồi phóng lên 640x640 vì sẽ mất thêm thông tin.

## C. Công việc tiếp theo
- Chạy thực nghiệm và kiểm tra các ảnh trong `check_labels/`.
- Sau khi xác nhận bbox/class đúng, ghép các hard samples này vào dataset train bổ sung.
