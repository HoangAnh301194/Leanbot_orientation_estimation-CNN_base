# Báo cáo công việc ngày 08/05/2026

## A. Công việc đã làm
- Thay đổi cấu hình degree augmentation về 10.
- Thêm tools Crop lấy vùng sa bàn, theo mask Roi trước đó đã làm.
    - Resize ảnh Crop về kích thước ảnh 640x640 
    - Tạo tập datasets chỉ có ảnh 640x640.
- Train thử để kiểm tra batch ghép ảnh Mosaic Augmentation
### 1. Thông tin training

| Thông số | 4 Class (`Leanbot_front, Leanbot_back, Leanbot_left, Leanbot_right`) |
| :--- | :---: |
| Model nền tảng | `yolov8n.pt` (YOLOv8 Nano - Pre-trained COCO) |
| Số class | 4 |
| Epochs | 100 |
| Batch size | 16 |
| Image size | 640 × 640 |
| Optimizer | AdamW (lr=0.002) |
| Thời gian Training | ~Cập nhật sau |
| Môi trường Training | Google Colab (GPU Tesla T4) |
| Datasets.zip | ~Chờ cập nhật|
| Link Notebook | [finetuning_yolo_Leanbot.ipynb](https://git.pythaverse.space/thomha/Nguyen_Huu_Hoang_Anh/blob/master/260508/tools/finetuning_yolo_Leanbot.ipynb) |

### 2. Tạo tools ```crop_tool.py```
- Input của tools là folder ```tool1_output``` - output của tool ```process_auto_label.py```
- Output của tools là folder ```crop_images``` chứa ảnh đã crop, resize 640x640 và Labels tương ứng với ảnh.
- Luồng hoạt động như sau :
    - Đọc config.npy
    - Crop ảnh hình vuông tính theo Mask ROI cạnh dưới của Sa bàn
    ![alt text](image-4.png)

    - Resize ảnh
    ![alt text](image-5.png)

    - Debug kích thước ảnh sau khi crop và resize:
    ``` 
    Processing session: session_20260508_142829
    -> Found Bounding Box (x=330, y=276, w=1993, h=1084) from roi_points
        [DEBUG] deg_0_000.jpg | Original: 2560x1440 | Cropped: 1993x1440 | Resized size: 640x640
        [DEBUG] deg_0_001.jpg | Original: 2560x1440 | Cropped: 1993x1440 | Resized size: 640x640
        [DEBUG] deg_0_002.jpg | Original: 2560x1440 | Cropped: 1993x1440 | Resized size: 640x640
        [DEBUG] deg_0_003.jpg | Original: 2560x1440 | Cropped: 1993x1440 | Resized size: 640x640
    ```
    - Mặc dù Crop theo hình vuông, lấy cạnh dưới sa bàn làm chuẩn, tuy nhiên cạnh dưới sa bàn có kích thước là 1993 pixel, trong khi chiều cao tối đa ảnh gốc là 1440 pixel (2560x1440), dẫn đến ảnh sau khi crop có kích thước 1993x1440 -> Vẫn là hình chữ nhật -> Resize ảnh vẫn méo. 
    - Cập nhật Label 
- Link code : [https://git.pythaverse.space/thomha/Nguyen_Huu_Hoang_Anh/blob/master/260508/tools/crop_tool.py](https://git.pythaverse.space/thomha/Nguyen_Huu_Hoang_Anh/blob/master/260508/tools/crop_tool.py)

#### 1.1. Mosaic Augmentation trong Yolo.
- Mặc định khi sử dụng hàm ```model.train()``` trong Yolo có hỗ trợ Mosaic Augmentation với tỉ lệ thực hiện 1.0 (thực hiện với 100 lượng ảnh). 
- Nếu muốn tùy chỉnh tỉ lệ này thì cần khai báo tham số ```mosaic``` trong hàm ```model.train()``` (ví dụ ```mosaic=0.5``` tức là thực hiện với 50 lượng ảnh).
- Hiện tại cấu hình chỉ có ```degrees = 0.0```, ```fliplr = 0.0```, ```flipud = 0.0```. Mosaic mặc định là `1.0`.
- Mosaic augmentation sẽ thực hiện các biến đổi sau:
    - Ghép ngẫu nhiên 4 ảnh lại với nhau thành 1 ảnh.
    - Trong quá trình ghép sẽ zoom ngẫu nhiên các ảnh con, xuay, cắt, đổi màu theo cấu hình augmentation.
    - Thêm padding xám vào các ảnh để có kích thước 640x640.
    - Tự động điều chỉnh box cho phù hợp với ảnh sau khi đã ghép.
- Các bước biến đổi này nằm sâu bên trong code của thư viện Ultralytics, **không thể can thiệp** trực tiếp code.
> Không thể tắt bước thêm padding xám khi sử dụng Mosaic Augmentation.
- Theo thư viện Ultralytic của YOLO thì Mosaic Augmentation sẽ ghép 4 ảnh trong `n-10` epoch đầu tiên, sau đó sẽ không thực hiện trong 10 epoch cuối. 
- Kết quả các batch sau khi Augmentation như sau :
    - Batch trong khoảng `n-10` epoch:
        ![Batch trong khoảng n-10 epoch](image.png)
    - Batch trong khoảng `10` epoch cuối:
        ![Batch trong khoảng 10 epoch cuối](image-1.png)
- Khi tạo Mosaic:
    - Thuật toán mặc định sẽ chọn ngẫu nhiên một điểm tâm chữ thập (center_x, center_y) bất kỳ trên ảnh. Sau đó nó chèn 4 bức ảnh vào 4 góc của điểm chữ thập này. Bởi vì điểm tâm này là ngẫu nhiên -> ảnh có thể lệch tâm,
    - Các bức ảnh con có thể bị thu nhỏ lại (Scale), nên chúng không thể lấp đầy hoàn toàn không gian 640x640 của bức ảnh tổng.
    > Mosaic augmentation mặc định sẽ thêm padding xám để lấp vào khoảng trống để cho kết quả là ảnh có kích thước 640x640. 


## B. Khó khăn 
- Không thể can thiệp vào code của thư viện Ultralytics để tắt bước thêm padding xám trong Mosaic Augmentation theo yêu cầu.
- Dạ em sẽ chụp lại data và đặt tên file đầy đủ theo class + góc như yêu cầu ạ.
- Em xin phép hỏi thêm: với mỗi class Front/Back/Left/Right, em cần chụp khoảng bao nhiêu ảnh cho từng góc 0, ±15, ±30 ạ? Còn các ảnh ±45 độ không dùng để train thì em nên chụp khoảng bao nhiêu ảnh để làm test riêng ạ? 
## C. Công việc tiếp theo
- Thu thập lại data và đặt tên theo đúng các góc
- Thử train đồng thời 4 class Front, Back, Left, Right
- Chỉ dùng và gán nhãn với các ảnh 0, +-15, +-30
- Các ảnh +-45 dùng để test.