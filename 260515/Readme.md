# Báo cáo công việc ngày 15/05/2026
## A. Công việc đã làm
- Báo cáo lại các trường hợp nhiễu của Model trong môi trường thực tế.
### 1. Các trường hợp nhiễu của Model trong thực tế 
- Khi test thực tế thì em để confidence để lọc lấy BBox có confidence lớn nhất và lớn hơn 0.5 .
- Và khi test ảnh lỗi với toàn bộ class thì em để bộ lọc là 0.05 để hiển thị toàn bộ Class có confidence > 0.05 .
- Kết quả thử nghiệm được chia thành các trường hợp có thể có nhưu sau:
#### 1.1. Một số vị trí không detect và không vẽ BBox .

| Ảnh BBox (Conf > 0.5) | Confidence Debug (Show all Class) |
| :---: | :---: |
| ![BBox 132748](./error_image/error_20260515_132748_bbox.jpg) | ![Conf 132748](./error_image/error_20260515_132748_conf.jpg) |
| ![BBox 132836](./error_image/error_20260515_132836_bbox.jpg) | ![Conf 132836](./error_image/error_20260515_132836_conf.jpg) |
| ![BBox 132902](./error_image/error_20260515_132902_bbox.jpg) | ![Conf 132902](./error_image/error_20260515_132902_conf.jpg) |
| ![BBox 132912](./error_image/error_20260515_132912_bbox.jpg) | ![Conf 132912](./error_image/error_20260515_132912_conf.jpg) |
| ![BBox 132940](./error_image/error_20260515_132940_bbox.jpg) | ![Conf 132940](./error_image/error_20260515_132940_conf.jpg) |
| ![BBox 132951](./error_image/error_20260515_132951_bbox.jpg) | ![Conf 132951](./error_image/error_20260515_132951_conf.jpg) |

#### 1.2. Nếu khu vực lân cận Leanbot có vật thể khác che mất Backgroud sa bàn thì Confidence giảm.
- Một số trường hợp mà em đã test như sau: 
  - Khi em đứng gần Sa bàn, khu vực lân cận Leanbot sẽ có thêm hình ảnh màu áo khác với sa bàn. 
  - Hoặc khi đưa tay lại gần Leanbot 
  - Hoặc có vật thể tương đối khác biệt so với sa bàn nằm gần Leanbot 
  - Khi Leanbot ở rìa sa bàn, và môi trường xung quanh là mới mẻ so với dataset. 
> Kết quả của các test case như bảng sau :

| Ảnh BBox (Conf > 0.5) | Confidence Debug (Show all Class) |
| :---: | :---: |
| ![BBox 133047](./error_image/error_20260515_133047_bbox.jpg) | ![Conf 133047](./error_image/error_20260515_133047_conf.jpg) |
| ![BBox 133058](./error_image/error_20260515_133058_bbox.jpg) | ![Conf 133058](./error_image/error_20260515_133058_conf.jpg) |
| ![BBox 133111](./error_image/error_20260515_133111_bbox.jpg) | ![Conf 133111](./error_image/error_20260515_133111_conf.jpg) |
| ![BBox 133118](./error_image/error_20260515_133118_bbox.jpg) | ![Conf 133118](./error_image/error_20260515_133118_conf.jpg) |
| ![BBox 134427](./error_image/error_20260515_134427_bbox.jpg) | ![Conf 134427](./error_image/error_20260515_134427_conf.jpg) |
| ![BBox 134438](./error_image/error_20260515_134438_bbox.jpg) | ![Conf 134438](./error_image/error_20260515_134438_conf.jpg) |
| ![BBox 134440](./error_image/error_20260515_134440_bbox.jpg) | ![Conf 134440](./error_image/error_20260515_134440_conf.jpg) |
| ![BBox 134631](./error_image/error_20260515_134631_bbox.jpg) | ![Conf 134631](./error_image/error_20260515_134631_conf.jpg) |
| ![BBox 134706](./error_image/error_20260515_134706_bbox.jpg) | ![Conf 134706](./error_image/error_20260515_134706_conf.jpg) |
| ![BBox 134916](./error_image/error_20260515_134916_bbox.jpg) | ![Conf 134916](./error_image/error_20260515_134916_conf.jpg) |
| ![BBox 135356](./error_image/error_20260515_135356_bbox.jpg) | ![Conf 135356](./error_image/error_20260515_135356_conf.jpg) |
| ![BBox 135438](./error_image/error_20260515_135438_bbox.jpg) | ![Conf 135438](./error_image/error_20260515_135438_conf.jpg) |
| ![BBox 135518](./error_image/error_20260515_135518_bbox.jpg) | ![Conf 135518](./error_image/error_20260515_135518_conf.jpg) |
| ![BBox 135601](./error_image/error_20260515_135601_bbox.jpg) | ![Conf 135601](./error_image/error_20260515_135601_conf.jpg) |

#### 1.3. Khi thay đổi độ sáng môi trường (tắt đèn )
- Khi tắt đèn, ánh sáng trong phòng yếu, model hoạt động không ổn định, confidence của các Class đều giảm mạnh.

| Ảnh BBox (Conf > 0.5) | Confidence Debug (Show all Class) |
| :---: | :---: |
| ![BBox 142058](./error_image/error_20260515_142058_bbox.jpg) | ![Conf 142058](./error_image/error_20260515_142058_conf.jpg) |
| ![BBox 142114](./error_image/error_20260515_142114_bbox.jpg) | ![Conf 142114](./error_image/error_20260515_142114_conf.jpg) |
| ![BBox 142149](./error_image/error_20260515_142149_bbox.jpg) | ![Conf 142149](./error_image/error_20260515_142149_conf.jpg) |
| ![BBox 142155](./error_image/error_20260515_142155_bbox.jpg) | ![Conf 142155](./error_image/error_20260515_142155_conf.jpg) |
| ![BBox 142206](./error_image/error_20260515_142206_bbox.jpg) | ![Conf 142206](./error_image/error_20260515_142206_conf.jpg) |
| ![BBox 142222](./error_image/error_20260515_142222_bbox.jpg) | ![Conf 142222](./error_image/error_20260515_142222_conf.jpg) |

## B. Khó khăn 
- Hiện tại trong quá trình test thực tế em chỉ mới nghĩ được một số test case như trên thôi ạ. 
- Em xin phép nhận thêm ý kiến của Thầy về các test case khác có thể có để đánh giá Model khách quan nhất ạ.
- Hiện tại trong quá trình chụp em quên mất không tạo debug txt để trích xuất thông tin Confidence ra. Nên giờ em chưa tạo bảng được ạ.
- Khi có các test case Thầy yêu cầu, em sẽ test lại, chụp ảnh và gửi lại cho Thầy các hình ảnh cùng với file txt chứa thông tin confidence và tạo bảng báo cáo chi tiết đầy đủ thông tin ạ.
## D. Công việc tiếp theo
- Em xin phép nhận thêm hướng đi tiếp theo từ Thầy ạ. 