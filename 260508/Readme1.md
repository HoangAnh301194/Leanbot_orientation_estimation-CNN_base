# Cập nhật báo cáo ngày 08/05/2026

## A. Công việc đã làm
- Báo cáo chi tiết lại các bước Crop và resize ảnh 
### 1. Crop và resize ảnh
- Chỉnh sửa `crop_tool.py` để thay đổi cách crop và resize ảnh như sau: 
- **Bước 1:** Đọc 4 điểm Mask Roi có sẵn trong folder `tool1_output` của mỗi session
- **Bước 2:** Lấy cạnh dưới của mask sa bàn làm chuẩn, crop theo hình vuông sao cho cạnh dưới trùng với cạnh dưới của mask sa bàn.

    ![Bước 1](image-4.png)

- **Bước 3:** Resize ảnh về kích thước 640x640. 

    ![Bước 3](image-5.png)
- Log debug kích thước ảnh tại các bước như sau :
```
    Processing session: session_20260508_142829
    -> Found Bounding Box (x=330, y=276, w=1993, h=1084) from roi_points
        [DEBUG] deg_0_000.jpg | Original: 2560x1440 | Cropped: 1993x1440 | Resized size: 640x640
        [DEBUG] deg_0_001.jpg | Original: 2560x1440 | Cropped: 1993x1440 | Resized size: 640x640
        [DEBUG] deg_0_002.jpg | Original: 2560x1440 | Cropped: 1993x1440 | Resized size: 640x640
        [DEBUG] deg_0_003.jpg | Original: 2560x1440 | Cropped: 1993x1440 | Resized size: 640x640
```
- Mặc dù Crop theo hình vuông, lấy cạnh dưới sa bàn làm chuẩn, tuy nhiên cạnh dưới sa bàn có kích thước là 1993 pixel, trong khi chiều cao tối đa ảnh gốc là 1440 pixel (2560x1440), dẫn đến ảnh sau khi crop có kích thước 1993x1440 -> Vẫn là hình chữ nhật -> Resize ảnh vẫn méo. 


## B. Khó khăn 
- Như mô tả ở trên về việc resize vẫn bị méo, do ảnh crop vẫn là hình chữ nhật ạ.
- Em có cần thêm Padding đen hoặc xám để bù kích thước chiều rộng cho đúng hình vuông không ạ ? 
## C. Công việc tiếp theo
- Thu thập lại data và đặt tên theo đúng các góc
- Thử train đồng thời 4 class Front, Back, Left, Right
- Chỉ dùng và gán nhãn với các ảnh 0, +-15, +-30
- Các ảnh +-45 dùng để test.