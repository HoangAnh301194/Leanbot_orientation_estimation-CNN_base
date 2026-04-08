# Báo cáo công việc ngày 09/04/2026

<a id="muc-luc"></a>
## Mục lục
- [A. Công việc đã làm](#a-cong-viec-da-lam)
- [2. Thu thập lại Data ảnh của Leanbot trên Sa bàn](#2-thu-thap-lai-data-anh-cua-leanbot-tren-sa-ban)
- [3. Bài toán phân loại trong DeepLearning và YOLO](#3-bai-toan-phan-loai-trong-deeplearning-va-yolo)
- [4. Các bước gắn nhãn ảnh Leanbot](#4-cac-buoc-gan-nhan-anh-leanbot)
- [5. Huấn luyện mô hình YOLO và triển khai thực tế](#5-huan-luyen-mo-hinh-yolo-va-trien-khai-thuc-te)
- [B. Khó khăn](#b-kho-khan)

<a id="a-cong-viec-da-lam"></a>
## A. Công việc đã làm
- Thu thập lại Data ảnh của Leanbot trên Sa bàn.
- Tìm hiểu bài toán phân loại trong DeepLearning và mô hình YOLO.
- Gắn nhãn ảnh Leanbot bằng Label Studio.
- Huấn luyện mô hình YOLO và triển khai thử nghiệm thực tế.

<a id="2-thu-thap-lai-data-anh-cua-leanbot-tren-sa-ban"></a>
### 2. Thu thập lại Data ảnh của Leanbot trên Sa bàn
Em đã chụp lại ảnh Leanbot tại các vị trí khác nhau trên sa bàn, mỗi vị trí có các góc chụp khác nhau, bao gồm:

- Ảnh Leanbot tại các vị trí A, B, ...

  ![Ảnh Leanbot tại vị trí 01](image/leanbot_board_position_01.jpg)

  ![Ảnh Leanbot tại vị trí 02](image/leanbot_board_position_02.jpg)

  ![Ảnh Leanbot tại vị trí 03](image/leanbot_board_position_03.jpg)

  ![Ảnh Leanbot tại vị trí 04](image/leanbot_board_position_04.jpg)

  ![Ảnh Leanbot tại vị trí 05](image/leanbot_board_position_05.jpg)

  ![Ảnh Leanbot tại vị trí 06](image/leanbot_board_position_06.jpg)

  ![Ảnh Leanbot tại vị trí 07](image/leanbot_board_position_07.jpg)

  ![Ảnh Leanbot tại vị trí 08](image/leanbot_board_position_08.jpg)

  ![Ảnh Leanbot tại vị trí 09](image/leanbot_board_position_09.jpg)

- Ảnh Leanbot tại các góc

  ![Ảnh Leanbot tại góc 01](image/leanbot_board_corner_01.jpg)

  ![Ảnh Leanbot tại góc 02](image/leanbot_board_corner_02.jpg)

  ![Ảnh Leanbot tại góc 03](image/leanbot_board_corner_03.jpg)

  ![Ảnh Leanbot tại góc 04](image/leanbot_board_corner_04.jpg)

- Ảnh Leanbot trên đường đen

  ![Ảnh Leanbot trên đường đen 01](image/leanbot_black_line_01.jpg)

  ![Ảnh Leanbot trên đường đen 02](image/leanbot_black_line_02.jpg)

- Ảnh có 2 Leanbot xuất hiện đồng thời

  ![Ảnh hai Leanbot xuất hiện đồng thời](image/leanbot_two_robots.jpg)

- Ảnh Leanbot cùng các khối màu ngẫu nhiên

  ![Ảnh Leanbot cùng các khối màu ngẫu nhiên](image/leanbot_with_random_blocks.jpg)

- Ảnh chỉ có khối gỗ

  ![Ảnh chỉ có khối gỗ](image/wooden_blocks_only.jpg)

- Ảnh chỉ có nền trắng

  ![Ảnh chỉ có nền trắng](image/white_background_only.jpg)

<a id="3-bai-toan-phan-loai-trong-deeplearning-va-yolo"></a>
### 3. Bài toán phân loại trong DeepLearning và YOLO
- Trong bài toán phân loại (classification), dữ liệu đầu vào được đưa vào model và model sẽ trả về một nhãn phù hợp nhất cho dữ liệu đó. Với bài toán này, nhãn có thể là Leanbot hoặc không phải Leanbot.
- Bản chất của model là đọc dữ liệu đầu vào, trích xuất đặc trưng và dự đoán nhãn đầu ra. Khi có tập dữ liệu và nhãn tương ứng, ta có thể huấn luyện model để nhận diện đối tượng cần quan tâm.
- Có rất nhiều model xử lý ảnh khác nhau, mỗi model có ưu nhược điểm riêng và phù hợp với từng bài toán cụ thể, tùy theo thiết bị triển khai, tốc độ yêu cầu và độ chính xác mong muốn.

#### Về mô hình YOLO
- YOLO là một model xử lý ảnh được huấn luyện trên lượng dữ liệu rất lớn. Với YOLOv8, model nền được huấn luyện trên tập COCO gồm khoảng 120.000 ảnh với 80 lớp đối tượng đã gắn nhãn sẵn.
- Trong tập COCO không có đối tượng Leanbot, vì vậy em sử dụng dữ liệu Leanbot để fine-tune model nhằm giúp model nhận diện thêm đối tượng này.
- Về bản chất, kiến trúc YOLO gồm nhiều lớp (layer), mỗi lớp đảm nhiệm một chức năng khác nhau trong quá trình trích xuất đặc trưng và dự đoán.

![Sơ đồ kiến trúc YOLO](image/yolo_architecture.jpg)

#### Lý do em chọn YOLO
- Có tài liệu hướng dẫn chi tiết, dễ hiểu.
- Có cộng đồng hỗ trợ lớn và bộ thư viện Ultralytics thuận tiện khi triển khai.
- Có thể chạy trên nhiều nền tảng và nhiều thiết bị khác nhau.
- Tốc độ xử lý nhanh, độ chính xác tốt cho bài toán nhận diện thời gian thực.

<a id="4-cac-buoc-gan-nhan-anh-leanbot"></a>
### 4. Các bước gắn nhãn ảnh Leanbot
Để gắn nhãn cho Leanbot, em sử dụng **[Label Studio](https://labelstud.io/)**. Các bước thực hiện như sau:

#### Bước 1: Mở Label Studio
- Truy cập vào trang web của Label Studio.

  ![Kết quả tìm kiếm Label Studio](image/label_studio_search_result.jpg)

- Kéo xuống và bấm vào **Free Cloud Trial**.

  ![Nút Free Cloud Trial của Label Studio](image/label_studio_free_cloud_trial.jpg)

- Đăng nhập hoặc tạo tài khoản mới. Sau đó tại giao diện chính bấm **Create Project**.

  ![Màn hình chính với nút Create Project](image/label_studio_home_create_project.jpg)

- Nhập tên project và các thông tin cần thiết.

  ![Form nhập thông tin Project](image/label_studio_project_general.jpg)

- Chuyển sang **Data Import** để tải ảnh Leanbot lên project. Bấm **Upload** và chọn ảnh Leanbot.

  ![Tab Data Import với nút Upload Files](image/label_studio_data_import_upload.jpg)

  ![Danh sách ảnh đã được tải lên](image/label_studio_uploaded_files.jpg)

- Sau khi upload xong thì chuyển sang **Labeling Setup**, cuộn xuống để chọn mẫu **Object Detection with Bounding Boxes**.

  ![Chọn mẫu Object Detection with Bounding Boxes](image/label_studio_select_bounding_box_template.jpg)

  ![Mẫu bounding box với nhãn mặc định](image/label_studio_bounding_box_template_selected.jpg)

- Xóa 2 class mặc định `Airplane` và `Car`, sau đó thêm class `Leanbot`.

  ![Xóa nhãn mặc định Airplane và Car](image/label_studio_remove_default_labels.jpg)

  ![Nhập nhãn Leanbot](image/label_studio_add_leanbot_label_text.jpg)

  ![Nhãn Leanbot đã được thêm](image/label_studio_leanbot_label_added.jpg)

- Bấm **Save & Open** để bắt đầu gắn nhãn.

  ![Nút Save & Open](image/label_studio_save_and_open.jpg)

- Giao diện gắn nhãn sẽ hiện ra. Chọn nhãn `Leanbot`, kéo chuột để tạo khung bao quanh Leanbot, sau đó bấm **Submit** để lưu.

  ![Danh sách task trong Data Manager](image/label_studio_data_manager_task_list.jpg)

  ![Giao diện gắn nhãn](image/label_studio_annotation_workspace.jpg)

  ![Khung bao Leanbot sau khi gắn nhãn](image/label_studio_annotated_bounding_box.jpg)

- Sau khi gắn nhãn xong, bấm vào **Data Manager** để kiểm tra lịch sử annotation.

  ![Lịch sử annotation sau khi submit](image/label_studio_annotation_submitted.jpg)

- Bấm vào **Review All Tasks**, sau đó accept toàn bộ. Sau khi hoàn tất sẽ có thông báo hoàn thành.

  ![Danh sách task chờ review](image/label_studio_review_all_tasks.jpg)

  ![Màn hình review và nút Accept](image/label_studio_review_accept_task.jpg)

  ![Thông báo review finished](image/label_studio_review_finished.jpg)

- Quay về **Data Manager** và bấm **Export** để xuất dữ liệu. Khi cửa sổ export hiện lên, bấm **Create New Snapshot** và điền tên.

  ![Cửa sổ Exported Snapshots](image/label_studio_exported_snapshots.jpg)

  ![Form tạo snapshot mới](image/label_studio_create_snapshot.jpg)

- Bấm download và chọn loại dataset **YOLO WITH IMAGES**.

  ![Chọn định dạng export dataset](image/label_studio_select_export_format.jpg)

- Sau khi tải về thì giải nén ra, ta sẽ có 2 thư mục là `images` chứa ảnh Leanbot và `labels` chứa nhãn của Leanbot.

  ![File zip dataset đã tải xuống](image/label_studio_downloaded_dataset_zip.jpg)

  ![Cấu trúc thư mục dataset sau khi giải nén](image/label_studio_extracted_dataset_structure.jpg)

<a id="5-huan-luyen-mo-hinh-yolo-va-trien-khai-thuc-te"></a>
### 5. Huấn luyện mô hình YOLO và triển khai thực tế

Em sử dụng notebook **[Leanbot_detection/train_yolov8_colab.ipynb]()** trên Google Colab để huấn luyện và kiểm tra mô hình YOLOv8.

- Tìm Google Colab và mở môi trường làm việc.

  ![Tìm kiếm Google Colab](image/colab_search_result.jpg)

  ![Notebook huấn luyện trên Google Colab](image/colab_training_notebook_overview.jpg)

- Upload notebook huấn luyện lên Colab.

  ![Mở hộp thoại upload notebook trên Colab](image/colab_upload_notebook.jpg)

- Chọn cấu hình runtime phù hợp để huấn luyện.

  ![Mở menu Runtime trên Google Colab](image/colab_runtime_menu.jpg)

  ![Chọn Python 3 và T4 GPU](image/colab_change_runtime_t4_gpu.jpg)

- Upload file dữ liệu **[datasets.zip](https://drive.google.com/file/d/1dTYFQGfYl1c8RRx3Qcur2HRSKe_ZzCAZ/view?usp=sharing)** để notebook chuẩn bị dữ liệu đầu vào.

  ![Cửa sổ Files trước khi upload dữ liệu](image/colab_files_panel_before_upload.jpg)

  ![File datasets.zip sau khi được upload](image/colab_datasets_zip_uploaded.jpg)

- Chạy toàn bộ notebook để cài thư viện, giải nén dữ liệu và huấn luyện mô hình.

  ![Nút Run all trên notebook](image/colab_run_all_notebook.jpg)

  ![Gợi ý thao tác Run all](image/colab_run_all_tooltip.jpg)

- Kết quả bước đầu cho thấy mô hình đã dự đoán được vị trí Leanbot trên ảnh kiểm tra.

  ![Lưới ảnh kết quả dự đoán của mô hình](image/yolov8_prediction_grid.jpg)

- Khi triển khai thử nghiệm với webcam, mô hình có thể nhận diện một hoặc nhiều Leanbot trong cùng khung hình.

  ![Kết quả nhận diện 1 Leanbot](image/webcam_detection_single_leanbot.jpg)

  ![Kết quả nhận diện 2 Leanbot](image/webcam_detection_two_leanbots.jpg)

  ![Kết quả nhận diện 3 Leanbot](image/webcam_detection_three_leanbots.jpg)

<a id="b-kho-khan"></a>
## B. Khó khăn
- Cần tiếp tục tối ưu thêm dữ liệu và điều kiện chụp để mô hình nhận diện ổn định hơn trong nhiều bối cảnh khác nhau. Vì hiện tại chỉ mới có 50 ảnh là quá ít để Model có thể nhận diện chính xác Leanbot ở mọi trường hợp ngẫu nhiên trên sa bàn. 
- Vì việc gắn nhẵn, đóng gói project để chạy trên colab và triển khai mất hơi nhiều thời gian nên em chưa tìm hiểu lại được phần Resolution của Camera ạ. Khi về em sẽ bổ sung báo cáo gửi Thầy ạ. 
