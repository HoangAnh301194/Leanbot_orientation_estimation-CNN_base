# Báo cáo công việc ngày 20/04/2026

## A. Công việc đã làm
- Tạo tool Auto label, sử dụng nhiều Leanbot để lấy mẫu cùng lúc
- Tiến hành train thử nghiệm tập datasets vừa tạo bằng tool Auto_label.py 
### 1. Tạo tools Auto Label
- **Mục đích**: Tự động tách cùng lúc nhiều Leanbot ra khỏi Backgroud, tính toán Bounding Box và tạo file Label cho các Class Leanbot.
- **Link code**: [https://git.pythaverse.space/thomha/Nguyen_Huu_Hoang_Anh/blob/master/260420/tools/auto_label.py](https://git.pythaverse.space/thomha/Nguyen_Huu_Hoang_Anh/blob/master/260420/tools/auto_label.py)
- **Các bước thực hiện**

    - **Bước 1**: Chụp ảnh BackGround trắng (chưa có Leanbot), click chuột vào 4 góc để lấy Mask xử lí, tính toán.

    ![points](points.png)

    - **Bước 2**: Chụp ảnh có 9 Leanbot tại 9 trường hợp khác nhau -> căn chỉnh Alignment, CLAHE, Gaussian Blur -> Trừ ảnh với BackGround -> Tính countor, bounding box.

    ![leanbot](leanbot.png)

    - **Bước 3**: Tạo file label cho từng Leanbot.
    Ảnh sau khi xử lý sẽ được lưu vào thư mục `output/datasets/images` và `output/datasets/labels`.
    Định dạng file label là chuẩn **YOLO Normalized**:
    `<class_id> <x_center> <y_center> <width> <height>`
    *(Trong đó các tọa độ đều được chuẩn hóa về khoảng 0-1)*
    
- Kết quả :
    - Sau khi chạy tools bằng lệnh ```python tools/auto_label.py --source 1(tùy thuộc vào index mà camera được nhận)``` --> capture backgroud --> chọn Board ROI --> capture ảnh có Leanbot --> căn chỉnh Alignment --> thì ảnh Preview quá trình xử lý sẽ hiện lên như sau:
        - Ảnh tính toán sai khác, nhị phân hóa, tìm coutor:

        ![diff](diff.png)

        - Ảnh tìm Bounding box

        ![bbox](bbox.png)

    - file label sau khi chụp cho 9 Leanbot :
    ```
    0 0.495312 0.791319 0.120313 0.134028
    0 0.759766 0.759722 0.124219 0.116667
    0 0.595313 0.489236 0.092969 0.104861
    0 0.404883 0.481250 0.092578 0.106944
    0 0.744141 0.368403 0.059375 0.121528
    0 0.417773 0.300694 0.055859 0.108333
    0 0.575000 0.287847 0.054688 0.103472
    0 0.675781 0.152431 0.050000 0.063194
    0 0.508984 0.147917 0.065625 0.072222
    ```
### 2. Train thử nghiệm
- Sau khi có được tập datasets, tiến hành train thử nghiệm bằng Colab. 
- Link code colab : [https://git.pythaverse.space/thomha/Nguyen_Huu_Hoang_Anh/blob/master/260420/train_yolov8_colab.ipynb](https://git.pythaverse.space/thomha/Nguyen_Huu_Hoang_Anh/blob/master/260420/train_yolov8_colab.ipynb)
- Kết quả khi train :
    - Đối với tập dữ liệu train 10 ảnh, validate 3 ảnh, mỗi ảnh có 9 leanbot ở các tư thế khác nhau.
    - Bảng đánh giá tỉ lệ phán đoán nhầm lẫn 

    ![confusion](confusion_matrix.png)

    - Đồ thị đánh giá độ tự tin dự đoán 

    ![confidence](confidence.png)

    - Detect thực tế tại 3 ảnh đánh giá model - Validation

    ![detect](detect.png)

    - **Nhận xét** : qua các kết quả đánh giá, đối với tập dữ liệu 10 ảnh ( tương đương 90 mẫu Leanbot ) thì khả năng dự đoán của model chưa cao, độ tự tin thấp, tuy nhiên chỉ có 1 Class là Leanbot nên không có sự nhầm lẫn.
## B. Khó khăn
- Một số góc xuay của Leanbot khiến ánh sáng môi trường phản xạ, hoặc một số chi tiết của Leanbot khá giống với sa bàn nên khi tính sai khác, trừ ảnh sẽ bị mất pixel dẫn tới một số trường hợp countor ko ổn định, Bounding box ko hết toàn bộ Leanbot.

![bug](bug.png)

- Leanbot Bounding box không bao được hết thân: 

![alt text](image-1.png)

![alt text](image.png)

## C. Công việc tiếp theo
- Triển khai trainning với tập datasets vừa thu thập bằng auto_label.py.