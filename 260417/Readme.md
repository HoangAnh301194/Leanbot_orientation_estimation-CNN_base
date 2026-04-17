# Báo cáo công việc ngày 17/04/2026

## Mục lục
- [A. Công việc đã làm](#a-công-việc-đã-làm)
    - [1. Phương pháp Polygon Masking](#1-phương-pháp-polygon-masking)
        - [1.1. Mục tiêu và Giải pháp](#11-mục-tiêu-và-giải-pháp)
        - [1.2. Bản chất toán học của Mask và Bitwise AND](#12-bản-chất-toán-học-của-mask-và-bitwise-and)
        - [1.3. Bảng chân lý Bitwise Operations](#13-bảng-chân-lý-bitwise-operations)
    - [2. Hướng ý tưởng triển khai thực tế](#2-hướng-ý-tưởng-triển-khai-thực-tế)
    - [3. Code và kết quả thực nghiệm](#3-code-và-kết-quả-thực-nghiệm)
- [B. Khó khăn](#b-khó-khăn)
- [C. Tài liệu tham khảo](#c-tài-liệu-tham-khảo)
- [D. Công việc tiếp theo](#d-công-việc-tiếp-theo)

---

## A. Công việc đã làm
- Tìm hiểu và triển khai phương pháp xác định vùng sa bàn bằng **Polygon Mask** , **Bitwise** .
### 1. Phương pháp Polygon Masking

#### 1.1. Mục đích
*   **Mục tiêu**: Loại bỏ các vùng dư thừa ngoài sa bàn (người, đồ vật, nhiễu sáng) để tập trung xử lý AI trên một vùng hình thang cố định.
*   **Giải pháp**: Sử dụng một mảng nhị phân làm "mặt nạ" (Mask):
    - **Giá trị 255 (Trắng)**: Vùng sa bàn cần giữ lại.
    - **Giá trị 0 (Đen)**: Vùng nền cần loại bỏ.

#### 1.2. Bản chất của Mask và Bitwise AND
Phép toán `cv2.bitwise_and` thực hiện tính toán trên từng cặp pixel giữa ảnh đầu vào ($I_{in}$) và Mask:

$$I_{out}(x,y) = \begin{cases} I_{in}(x,y) & \text{nếu } Mask(x,y) = 255 \\ 0 & \text{nếu } Mask(x,y) = 0 \end{cases}$$

Về mặt logic, chỉ những điểm ảnh mà cả ảnh gốc và Mask đều có giá trị (bit 1) mới được giữ lại ở ảnh đầu ra.

#### 1.3. Bảng chân lý Bitwise Operations
Bảng dưới đây mô tả logic pixel khi thực hiện phép Bitwise giữa Ảnh gốc (X) và Mask (Y):

| X (Pixel ảnh) | Y (Pixel Mask) | AND (Kết quả) | Giải thích thực tế |
| :---: | :---: | :---: | :--- |
| 0 | 0 | 0 | Điểm đen ngoài Mask -> Đen |
| 0 | 1 | 0 | Điểm đen trong Mask -> Đen |
| 1 | 0 | 0 | **Vùng có màu ngoài Mask -> Bị xóa (Đen)** |
| 1 | 1 | 1 | **Vùng có màu trong Mask -> Giữ nguyên** |

### 2. Hướng ý tưởng triển khai thực tế

- **Bước 1: Chọn tọa độ**: Click chuột 4 góc sa bàn để chọn vùng mask
- **Bước 2: Tạo mặt nạ**: Dùng `cv2.fillPoly()` để tô trắng vùng hình thang từ 4 góc đã chọn, phần còn lại sẽ đen hoàn toàn.
- **Bước 3: Áp dụng mask đã tạo**: Áp dụng lệnh `masked = cv2.bitwise_and(frame, frame, mask=mask)` cho mọi frame ảnh từ Cam

### 3. Code và kết quả thực nghiệm
#### 3.1. Code 
- Link Code: [mask_roi.py](file:///d:/PTIT/DTT/Nguyen_Huu_Hoang_Anh/260417/Mask%20ROI/mask_roi.py)
- **Chi tiết các hàm xử lý thuật toán:**

##### a. Hàm xử lý sự kiện chuột (Tọa độ và Tỉ lệ)
Hàm này chịu trách nhiệm nhận tương tác từ người dùng và tự động tính toán lại tọa độ thực trên ảnh gốc 2K dựa vào tỉ lệ thu nhỏ `scale`. Phần này do ảnh 2k kích thước lớn quá nên tràn màn hình nên em phải thu nhỏ lại để dễ quan sát và chọn điểm ạ.
```python
def mouse_callback(event, x, y, flags, param):
    global points
    scale = param # Tỉ lệ thu nhỏ
    if event == cv2.EVENT_LBUTTONDOWN:
        if len(points) < 4:
            # Ánh xạ tọa độ click về tọa độ ảnh gốc 2K
            real_x, real_y = int(x * scale), int(y * scale)
            points.append((real_x, real_y))
            print(f"[INFO] Point {len(points)} = ({real_x}, {real_y})")
```

##### b. Hàm khởi tạo mặt nạ vùng chọn (Polygon Mask)
Sử dụng mảng NumPy để tạo nền đen và hàm `fillPoly` của OpenCV để vẽ đa giác trắng khép kín từ 4 điểm đã chọn.
```python
def build_mask(frame_shape, pts):
    # Tạo mảng đen toàn phần cùng kích thước ảnh gốc
    mask = np.zeros(frame_shape[:2], dtype=np.uint8)
    # Tô trắng (255) vùng đa giác xác định bởi 4 điểm pts
    cv2.fillPoly(mask, [pts], 255)
    return mask
```

##### c. Áp dụng Mask vào luồng video (Bitwise Process)
Sử dụng phép toán Bitwise AND để lọc ảnh. Chỉ những Pixel nằm trong vùng trắng của mặt nạ mới được giữ lại giá trị ảnh gốc.
```python
# Thực thi trong vòng lặp xử lý frame
masked = cv2.bitwise_and(frame, frame, mask=mask)
```
#### 3.2. Kết quả sau khi Mask
- Ảnh gốc sau khi chọn các điểm để tạo mask
![original](original.png)
- Ảnh sau khi Mask
![masked](mask.png)

## B. Khó khăn
- Hiện tại em đang chưa hiểu hưởng đi tổng thể cho lắm ạ :
    - Trước đó Thầy có bảo em tìm hiểu về các phương pháp chọn vùng hình thang của Sa bàn rồi nắn thẳng về hình vuông và chỉ cần xử lí trên hình vuông đó, nhưng giờ lại quay về bài toán chọn vùng hình thang của sa bàn trên ảnh rồi xử lí trên hình thang ạ.
    - Ngoài ra em vẫn chưa hình dung được output của bước chuẩn bị phần cơ sở xử lý ảnh để đi vào phần AI ạ. Kiểu cần phải xử lý đến mức nào thì được ạ? 

- Em nghĩ là sẽ có hạn chế nữa là khi mình chọn mask rồi, mà nếu sa bàn bị xê dịch một chút thì sẽ bị cắt mất một chút và mất thông tin để Alignment lại ạ. 
---
## C. Tài liệu tham khảo
1. **Viblo** – [Arithmetic Operations on Images with OpenCV](https://viblo.asia/p/arithmetic-operations-on-images-with-opencv-gDVK2denlLj#_bitwise-operations-4)
2. **OpenCV Documentation** – [Image Bitwise Operations](https://docs.opencv.org/4.x/d0/d86/tutorial_py_image_arithmetics.html)

---

## D. Công việc tiếp theo
- Khảo sát độ phân giải của ảnh Output sau khi Mask + alignment
