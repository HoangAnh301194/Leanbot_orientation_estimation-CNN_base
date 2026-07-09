# Checklist task ngày 260709

Cập nhật gần nhất: 2026/07/09

## Đã làm
- [x] Export model OpenVINO FP16 static `640x640`.
- [x] Export model OpenVINO FP16 static `160x160`.
- [x] Kiểm tra model full detection input shape: `[1, 3, 640, 640]`.
- [x] Kiểm tra model ROI tracking input shape: `[1, 3, 160, 160]`.
- [x] Sửa `tools/roi_tracking_inference.py` để load 2 model riêng:
  - full detection: `models/quantized_fp16/best_24Class_Soft_Angular_BCE_openvino_model`
  - ROI tracking: `models/best_24Class_Soft_Angular_BCE_static_160_openvino_model`
- [x] Resize ROI về `160x160` trước khi đưa vào tracking model.
- [x] Scale bbox từ output `160x160` về kích thước ROI gốc.

## Cần làm tiếp
- [x] Chạy inference riêng từng model để xác nhận runtime ổn định.
- [ ] Chỉnh ROI thành hình vuông bao quanh Leanbot.
- [ ] Ghi log thêm `roi_x`, `roi_y`, `roi_width`, `roi_height`.
- [x] Ghi log thêm `tracking_lost` theo từng frame, bỏ `lost_count`.
- [ ] Ghi log thêm `cycle_frame` trong chu kỳ khóa ROI 5 frame.
- [ ] Chạy lại baseline `640x640` sau khi cố định model static.
- [ ] Chạy lại pipeline `640 full + 160 ROI` với Leanbot chạy vòng tròn.
- [ ] Thống kê tổng frame mất tracking.
- [ ] Thống kê số lần fallback về full detection.
- [ ] Tính thời gian tìm lại Leanbot sau lost tracking.
- [ ] Vẽ đồ thị `angle`, `center_x`, `center_y`.
- [ ] Vẽ lại đồ thị FPS, inference time, CPU load, total processing time.
- [ ] Thêm bảng so sánh baseline và ROI tracking.
- [x] Cập nhật `Readme.md` mô tả rõ pipeline static 640 + static 160.
- [ ] Báo cáo rõ vấn đề static/dynamic input.
- [ ] Báo cáo rõ logic ROI khóa cố định trong 5 frame.
- [ ] Liệt kê các frame bị lost tracking.

## Ghi chú kỹ thuật
- Không dùng lại dynamic model cho benchmark chính.
- Full detection dùng input cố định `640x640`.
- ROI tracking dùng input cố định `160x160`.
- ROI trong ảnh gốc có thể thay đổi kích thước, nhưng tensor đưa vào tracking model luôn là `160x160`.





- [x] Thêm điều khiển ghi log bằng phím `r`; bấm `r` lại để dừng, bấm tiếp để ghi đè log cũ.
- [x] Tắt timeout 30 giây khi đang record; reset timeout sau khi dừng record.
