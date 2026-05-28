# Báo cáo công việc ngày 28/05/2026

## A. Công việc đã làm
- Chỉnh sửa code trong `check_confidence.py` để file CSV chỉ in giới hạn ở 2 chữ số thập phân
- Tạo thêm tool góp các nhóm Anchors overlap nhau thành 1 group 
### 1. Giới hạn số thập phân của file CSV
- **Link code:** [tools/check_confidence.py](tools/check_confidence.py)
- **Chỉnh sửa code:** Đã bổ sung tham số định dạng `float_format="%.2f"` vào hàm lưu file CSV của thư viện Pandas. Việc này đảm bảo các tọa độ (x_center, y_center, width, height) và 24 giá trị confidence xuất ra luôn được làm tròn và giới hạn ở đúng 2 chữ số thập phân.
- **File CSV sau khi chạy tool:** [002_top200.csv](yolo_class_bbox_results/002_top200.csv)
- **Ví dụ một đoạn dữ liệu trong file CSV:**
```csv
x_center,y_center,width,height,Leanbot_0,Leanbot_p15,Leanbot_p30,Leanbot_p45,Leanbot_p60,Leanbot_p75,Leanbot_p90,Leanbot_p105,Leanbot_p120,Leanbot_p135,Leanbot_p150,Leanbot_p165,Leanbot_p180,Leanbot_p195,Leanbot_m150,Leanbot_m135,Leanbot_m120,Leanbot_m105,Leanbot_m90,Leanbot_m75,Leanbot_m60,Leanbot_m45,Leanbot_m30,Leanbot_m15
260.89,334.18,55.04,35.50,0.34,0.02,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.01,0.00,0.61,0.00,0.00,0.00,0.01,0.00,0.00,0.00,0.00,0.00,0.01
353.88,261.39,46.30,26.38,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.01,0.57,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.13
```

### 2. Gom nhóm (Clustering) các Anchors trùng lặp
- **Link code:** [tools/group_anchors.py](tools/group_anchors.py)
- **Mục đích:** Thuật toán NMS mặc định sẽ xóa các bounding box phụ xung quanh vật thể. Công cụ này thay vì xóa sẽ gom toàn bộ các bounding box nhìn vào cùng một con Leanbot (có độ chồng lấp IoU > 0.5, đây là giá trị mặc định, có thể giảm ngưỡng để lấy thêm nhiều anchors có độ overlap thấp hơn) thành một nhóm duy nhất. Từ đó giúp phân tích được sự nhầm lẫn các class theo góc của Model.
- **Quy trình thuật toán lọc và gop nhóm nhưu sau :**
  1. Tìm anchor có `max_confidence` cao nhất làm tâm điểm của nhóm mới.
  2. Quét 199 anchors còn lại, nếu anchor nào đè lên tâm điểm (IoU > 0.5) thì được đưa vào chung nhóm.
  3. Sắp xếp các anchors trong nhóm theo thứ tự confidence từ cao xuống thấp.
  4. Lặp lại với các anchors chưa được phân nhóm cho tới khi hết.
- **File CSV sau khi chạy tool:** 
  - File CSV chứa nhóm: [002_grouped.csv](yolo_class_bbox_results/002_grouped.csv) 
  - Báo cáo định dạng (text): [002_grouped_report.txt](yolo_class_bbox_results/002_grouped_report.txt)
- **Ví dụ một đoạn dữ liệu trong CSV:**
```csv
group_id,best_class,max_conf,x_center,y_center,width,height,Leanbot_0,Leanbot_p15,Leanbot_p30,Leanbot_p45,Leanbot_p60,Leanbot_p75,Leanbot_p90,Leanbot_p105,Leanbot_p120,Leanbot_p135,Leanbot_p150,Leanbot_p165,Leanbot_p180,Leanbot_p195,Leanbot_m150,Leanbot_m135,Leanbot_m120,Leanbot_m105,Leanbot_m90,Leanbot_m75,Leanbot_m60,Leanbot_m45,Leanbot_m30,Leanbot_m15,x1,y1,x2
1,Leanbot_p195,0.61,260.89,334.18,55.04,35.50,0.34,0.02,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.01,0.00,0.61,0.00,0.00,0.00,0.01,0.00,0.00,0.00,0.00,0.00,0.01,233.37,316.43,288.41
1,Leanbot_p195,0.52,260.56,334.08,55.32,36.46,0.18,0.00,0.00,0.00,0.00,0.00,0.01,0.00,0.00,0.00,0.00,0.00,0.01,0.52,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.05,232.90,315.85,288.22
```

## B. Khó khăn 
- Không

## C. Công việc tiếp theo 
- Chỉnh sửa file notebook Colab để cấu hình theo hướng Soft Angular Target với BCE loss.
- In ra các metrics và giá trị target để đánh giá và kiểm tra.