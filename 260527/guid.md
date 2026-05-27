# Hướng Dẫn End-to-End Tạo Dataset Leanbot 24 Góc Để Train

## Mục tiêu

Tài liệu này mô tả toàn bộ quy trình để đi từ:

1. chụp hoặc chuẩn bị ảnh Leanbot theo từng góc,
2. gom ảnh thành 24 class,
3. auto-label bbox,
4. build dataset YOLO,
5. chia `train/val/test`,
6. tạo `data.yaml`,
7. đem dataset đi train.

Pipeline này bám theo đúng các tool đang có trong repo:

- `tools/run_group_24class.py`
- `tools/group_to_class.py`
- `tools/process_auto_label.py`
- `tools/build_dataset.py`
- `tools/finetuning_yolo_Leanbot.ipynb`


## Luồng dữ liệu tổng quát

```text
root_images/
  -> datasets/24class/raw_image/
  -> datasets/24class/tool1_output/
  -> datasets/24class/yolo_dataset_flat/
  -> datasets/24class/yolo_dataset_split/
  -> train YOLO
```

Ý nghĩa từng tầng:

- `root_images/`: ảnh gốc đã được chia theo từng góc Leanbot.
- `datasets/24class/raw_image/`: dữ liệu trung gian theo format mà tool auto-label hiểu được.
- `datasets/24class/tool1_output/`: ảnh đã align, label YOLO `.txt`, và ảnh debug bbox/mask.
- `datasets/24class/yolo_dataset_flat/`: bộ dữ liệu YOLO dạng phẳng `images/` và `labels/`.
- `datasets/24class/yolo_dataset_split/`: bộ dữ liệu YOLO đã chia `train/val/test`.


## Bước 0. Chuẩn bị môi trường

Chạy ở thư mục gốc repo:

```powershell
cd D:\PTIT\DTT\Nguyen_Huu_Hoang_Anh\260522
```

Nếu chưa có môi trường Python, cần cài tối thiểu:

```powershell
pip install opencv-python numpy ultralytics torch
```

Nếu bạn train trên Colab thì phần local chủ yếu cần để chuẩn bị dataset; phần train có thể làm ở Colab sau.


## Bước 1. Tạo ảnh gốc theo từng góc

### 1.1. Mục tiêu của `root_images/`

Mỗi góc Leanbot phải có một thư mục riêng trong `root_images/`.

Danh sách 24 góc hiện dùng:

```text
angle_0
angle_p15
angle_p30
angle_p45
angle_p60
angle_p75
angle_p90
angle_p105
angle_p120
angle_p135
angle_p150
angle_p165
angle_p180
angle_p195
angle_m150
angle_m135
angle_m120
angle_m105
angle_m90
angle_m75
angle_m60
angle_m45
angle_m30
angle_m15
```

### 1.2. Cấu trúc chuẩn của mỗi góc

Mỗi thư mục góc nên có:

- ảnh có Leanbot của đúng góc đó,
- một thư mục con `background/`,
- trong `background/` có ít nhất 1 ảnh nền không có Leanbot.

Ví dụ:

```text
root_images/
  angle_p45/
    angle_p45_000.jpg
    angle_p45_001.jpg
    angle_p45_002.jpg
    angle_p45_003.jpg
    angle_p45_004.jpg
    background/
      background_000.jpg
```

### 1.3. Cách chụp để auto-label dễ chạy

- Giữ camera cố định.
- Giữ nền tương đối ổn định.
- Mỗi góc nên có ít nhất `5-20` ảnh.
- Mỗi góc nên có ít nhất `1` ảnh nền cùng bối cảnh.
- Nếu ánh sáng đổi nhiều, nên chụp thêm background.
- Tên file không bắt buộc đúng mẫu, nhưng nên đặt có quy luật để dễ kiểm tra.

### 1.4. Nếu bạn chưa có ảnh

Repo có `tools/capture_session.py`, nhưng tool này phù hợp hơn với workflow theo session.

Với bài toán 24 góc, cách dễ nhất là:

1. chụp ảnh Leanbot cho từng góc,
2. tự sắp vào `root_images/angle_xxx/`,
3. thêm ảnh nền vào `root_images/angle_xxx/background/`.


## Bước 2. Biến từng góc thành từng class

### 2.1. Dùng sẵn pipeline 24 class

Nếu bạn đang làm đúng bộ 24 góc ở trên, chỉ cần chạy:

```powershell
python tools/run_group_24class.py
```

Script này sẽ tự:

- đọc ảnh từ `root_images/angle_xxx/`,
- tạo class tương ứng `Leanbot_xxx`,
- gán `class_id`,
- copy ảnh vào `datasets/24class/raw_image/`.

### 2.2. Output mong đợi

Sau khi chạy xong, bạn sẽ có cấu trúc kiểu:

```text
datasets/
  24class/
    raw_image/
      Leanbot_0/
        raw_images/
        backgrounds/
        session_metadata.json
      Leanbot_p15/
        raw_images/
        backgrounds/
        session_metadata.json
      ...
```

### 2.3. Mapping class hiện tại

Thứ tự class của repo đang là:

```text
0   -> Leanbot_0
1   -> Leanbot_p15
2   -> Leanbot_p30
3   -> Leanbot_p45
4   -> Leanbot_p60
5   -> Leanbot_p75
6   -> Leanbot_p90
7   -> Leanbot_p105
8   -> Leanbot_p120
9   -> Leanbot_p135
10  -> Leanbot_p150
11  -> Leanbot_p165
12  -> Leanbot_p180
13  -> Leanbot_p195
14  -> Leanbot_m150
15  -> Leanbot_m135
16  -> Leanbot_m120
17  -> Leanbot_m105
18  -> Leanbot_m90
19  -> Leanbot_m75
20  -> Leanbot_m60
21  -> Leanbot_m45
22  -> Leanbot_m30
23  -> Leanbot_m15
```

### 2.4. Nếu bạn muốn tự tạo class khác ngoài 24 class

Dùng:

```powershell
python tools/group_to_class.py `
  --dataset_name 8class `
  --class_id 0 `
  --class_name Leanbot_front `
  --folders angle_m15 angle_0 angle_p15
```

Khi đó bạn phải tự quản lý lại:

- `class_id`,
- `class_name`,
- thứ tự trong `data.yaml`.


## Bước 3. Auto-label bbox cho từng class

### 3.1. Chạy auto-label cho toàn bộ 24 class

Nên chỉ rõ `--raw_dir` và `--out_dir`, không nên dựa vào default:

```powershell
python tools/process_auto_label.py `
  --raw_dir datasets/24class/raw_image `
  --out_dir datasets/24class/tool1_output `
  --diff_mode 3 `
  --threshold 50 `
  --blur 5 `
  --min_area 6000 `
  --max_area 100000 `
  --min_width 20 `
  --max_width 600 `
  --min_height 20 `
  --max_height 600 `
  --mask_merge_kernel 12 `
  --mask_merge_iterations 1
```

Giải thích ngắn:

- `--diff_mode 3`: dùng chênh lệch trên HSV/Hue.
- `--threshold`, `--blur`: điều khiển độ nhạy của mask.
- `--min_area`, `--max_area`: lọc contour quá nhỏ hoặc quá lớn.
- `--min_width`, `--max_width`, `--min_height`, `--max_height`: lọc bbox bất thường.
- `--mask_merge_kernel`, `--mask_merge_iterations`: gộp các vùng mask gần nhau thành 1 bbox.

### 3.2. ROI sẽ được chọn khi nào

Lần đầu chạy cho mỗi class/session:

- tool sẽ yêu cầu chọn ROI,
- ROI được lưu lại,
- các lần chạy sau có thể dùng lại ROI cũ.

Nếu muốn chọn lại ROI:

```powershell
python tools/process_auto_label.py `
  --raw_dir datasets/24class/raw_image `
  --out_dir datasets/24class/tool1_output `
  --reset_roi
```

### 3.3. Output của auto-label

Mỗi class sẽ tạo ra một thư mục trong `datasets/24class/tool1_output/`:

```text
datasets/
  24class/
    tool1_output/
      Leanbot_p45/
        aligned_images/
        labels/
        debug/
        config.npy
```

Trong đó:

- `aligned_images/`: ảnh sau align.
- `labels/`: nhãn YOLO `.txt`.
- `debug/`: ảnh mask và bbox để kiểm tra nhanh.


## Bước 4. Kiểm tra chất lượng nhãn

Đây là bước rất quan trọng. Auto-label chỉ giúp tiết kiệm thời gian, không thay thế kiểm tra thủ công.

### 4.1. Cần xem các gì

Kiểm tra trong từng class:

- `debug/*_bbox.jpg`: bbox có ôm đúng Leanbot không.
- `debug/*_mask.jpg`: mask có tách đúng vật thể không.
- `labels/*.txt`: class id có đúng không, bbox có hợp lý không.

### 4.2. Dấu hiệu dữ liệu lỗi

- bbox quá to, ăn cả nền,
- bbox quá nhỏ, cắt mất Leanbot,
- ảnh có Leanbot nhưng label rỗng,
- ảnh không có Leanbot nhưng lại có bbox,
- một class bị lẫn ảnh của góc khác.

### 4.3. Cách xử lý

- Xóa các ảnh/label lỗi nặng.
- Nếu lỗi hàng loạt, chỉnh lại tham số auto-label rồi chạy lại.
- Nếu nền đổi nhiều, thêm background tốt hơn.
- Nếu ROI chưa đúng, chạy lại với `--reset_roi`.


## Bước 5. Build bộ dữ liệu YOLO dạng phẳng

Sau khi nhãn ổn, gom toàn bộ output thành một bộ dataset YOLO chuẩn:

```powershell
python tools/build_dataset.py `
  --input datasets/24class/tool1_output `
  --output datasets/24class/yolo_dataset_flat
```

### 5.1. Kết quả mong đợi

```text
datasets/
  24class/
    yolo_dataset_flat/
      images/
        000000.jpg
        000001.jpg
        ...
      labels/
        000000.txt
        000001.txt
        ...
      manifest.json
```

### 5.2. Lưu ý quan trọng

Mặc định `tools/build_dataset.py` sẽ bỏ qua label rỗng.

Điều này thường phù hợp nếu bạn đang train bộ 24 góc và chỉ muốn giữ các ảnh có Leanbot.

Nếu muốn giữ cả ảnh âm tính:

```powershell
python tools/build_dataset.py `
  --input datasets/24class/tool1_output `
  --output datasets/24class/yolo_dataset_flat `
  --include_empty
```


## Bước 6. Chia train, val, test

Repo hiện chưa có script `.py` riêng cho bước split; phần này đang nằm trong notebook `tools/finetuning_yolo_Leanbot.ipynb`.

Bạn có thể làm theo đúng logic của notebook:

- chia theo class,
- khoảng `70% train`, `20% val`, `10% test`.

### 6.1. Cấu trúc đích

```text
datasets/
  24class/
    yolo_dataset_split/
      train/
        images/
        labels/
      val/
        images/
        labels/
      test/
        images/
        labels/
```

### 6.2. Nguyên tắc split nên dùng

- Split theo class, không split ngẫu nhiên toàn bộ dataset một cục.
- Giữ phân bố giữa các góc tương đối cân bằng.
- Nếu dữ liệu ít, có thể dùng `80/10/10`.

### 6.3. Cách thực tế dễ nhất

Lấy `datasets/24class/yolo_dataset_flat/` đưa sang Colab hoặc local training env, rồi chạy phần split trong `tools/finetuning_yolo_Leanbot.ipynb`.

Notebook hiện đang làm:

1. đọc `images/` và `labels/`,
2. suy ra class từ dòng đầu của file label,
3. gom file theo class,
4. chia `train/val/test`,
5. chuyển file vào thư mục split tương ứng.


## Bước 7. Tạo `data.yaml`

Sau khi đã có `train/val/test`, tạo file `data.yaml` như sau:

```yaml
path: /content/datasets
train: train/images
val: val/images
test: test/images
nc: 24
names:
  0: Leanbot_0
  1: Leanbot_p15
  2: Leanbot_p30
  3: Leanbot_p45
  4: Leanbot_p60
  5: Leanbot_p75
  6: Leanbot_p90
  7: Leanbot_p105
  8: Leanbot_p120
  9: Leanbot_p135
  10: Leanbot_p150
  11: Leanbot_p165
  12: Leanbot_p180
  13: Leanbot_p195
  14: Leanbot_m150
  15: Leanbot_m135
  16: Leanbot_m120
  17: Leanbot_m105
  18: Leanbot_m90
  19: Leanbot_m75
  20: Leanbot_m60
  21: Leanbot_m45
  22: Leanbot_m30
  23: Leanbot_m15
```

Nếu bạn train local thay vì Colab, đổi `path:` thành đường dẫn local tới thư mục dataset split của bạn.


## Bước 8. Train model

Repo đã có notebook:

- `tools/finetuning_yolo_Leanbot.ipynb`

Trong notebook này đã có sẵn các phần:

- cài `ultralytics`,
- split dataset,
- tạo `leanbot_data.yaml`,
- train bằng `YOLO("yolov8n.pt")`.

### 8.1. Lệnh train tối thiểu nếu bạn muốn chạy bằng Python

```python
from ultralytics import YOLO

model = YOLO("yolov8n.pt")
model.train(
    data="leanbot_data.yaml",
    epochs=100,
    batch=16,
    imgsz=640,
    degrees=10.0,
    fliplr=0.0,
    flipud=0.0,
    name="leanbot_24class"
)
```

### 8.2. Gợi ý augment ban đầu

- `degrees=10.0`
- `fliplr=0.0`
- `flipud=0.0`

Không nên bật lật ngang hoặc lật dọc khi label đang mang ý nghĩa góc quay, vì có thể làm sai nhãn góc.


## Phu luc. Cach chay nhanh cac tool Python trong `tools/`

Phan nay gom cac lenh hay dung de ban khong phai mo tung file `.py` de nho tham so.

### A. Tool pipeline tao dataset

#### 1. Gom `root_images/` thanh `datasets/24class/raw_image/`

```powershell
python tools/run_group_24class.py
```

#### 2. Tao class tuy chinh tu mot nhom folder goc

```powershell
python tools/group_to_class.py `
  --dataset_name 8class `
  --class_id 0 `
  --class_name Leanbot_front `
  --folders angle_m15 angle_0 angle_p15
```

#### 3. Auto-label bbox cho du lieu 24 class

```powershell
python tools/process_auto_label.py `
  --raw_dir datasets/24class/raw_image `
  --out_dir datasets/24class/tool1_output `
  --diff_mode 3 `
  --threshold 50 `
  --blur 5 `
  --min_area 6000 `
  --max_area 100000 `
  --min_width 20 `
  --max_width 600 `
  --min_height 20 `
  --max_height 600 `
  --mask_merge_kernel 12 `
  --mask_merge_iterations 1
```

#### 4. Build bo dataset YOLO dang phang

```powershell
python tools/build_dataset.py `
  --input datasets/24class/tool1_output `
  --output datasets/24class/yolo_dataset_flat
```

### B. Tool infer, debug va xuat anh bbox

#### 1. Webcam infer theo style YOLO plot

```powershell
python tools/webcam_infer.py --source 0 --conf 0.5 --mode auto
```

Neu muon doc video file thay cho webcam:

```powershell
python tools/webcam_infer.py --source path\to\video.mp4 --conf 0.5 --mode auto
```

Luu y:

- `webcam_infer.py` phu hop nhat cho webcam/video stream.
- Nhan `c` trong cua so OpenCV de luu anh debug vao `error_image/`.
- Nhan `q` de thoat.

#### 2. Xuat anh bbox + report markdown tu 1 anh hoac 1 folder anh

```powershell
python tools/export_markdown_report.py `
  --source 24class_test_images `
  --output-dir detect_report_output
```

Co the truyen `--source` la 1 file anh hoac 1 folder anh.

Output thuong gom:

- anh `*_bbox.jpg`
- file `report.md`

#### 3. Detect object roi crop theo 4 muc mo rong bbox

Tool nay dung cho truong hop:

- doc anh tu `--input`
- ve anh bbox tong
- tach tung object detect duoc
- crop theo cac muc mo rong `0 1 2 3` pixel

Chay voi output o folder khac ben ngoai `24class_test_images`:

```powershell
python tools/detect_crop_levels.py `
  --input 24class_test_images `
  --output detect_crop_output `
  --conf 0.2
```

Neu chi muon xu ly 1 anh:

```powershell
python tools/detect_crop_levels.py `
  --input 24class_test_images\000.jpg `
  --output detect_crop_output\000_run `
  --conf 0.2
```

Output cua tool nay:

- `bbox_images/`: anh full da ve bbox
- `objects/Leanbot_p15_001/`: moi object mot folder rieng
- trong moi folder object co:
- `object_bbox.jpg`
- `expand_0.jpg`
- `expand_1.jpg`
- `expand_2.jpg`
- `expand_3.jpg`
- `meta.txt`

Co the doi cac muc mo rong bbox bang:

```powershell
python tools/detect_crop_levels.py `
  --input 24class_test_images `
  --output detect_crop_output `
  --conf 0.2 `
  --expansions 0 2 4 8
```

#### 4. Tool `check_confidence.py`

Tool nay van co the dung de debug confidence theo tung class, nhung hien tai duong dan input/output dang hard-code trong file.

Chi nen dung khi ban chap nhan sua cac bien sau trong source:

- `test_image_dir`
- `OUTPUT_DIR`

Neu muon workflow linh hoat hon, uu tien:

- `export_markdown_report.py` de xuat bbox + report
- `detect_crop_levels.py` de detect va crop tung object


## Checklist trước khi train

- Mỗi class đều có đủ ảnh.
- Mỗi class có background phù hợp để auto-label.
- `datasets/24class/tool1_output/*/labels/` có file `.txt`.
- File label có `class_id` đúng với mapping 24 class.
- Bbox nhìn ổn trên ảnh debug.
- Sau khi build dataset, số lượng ảnh giữa các class không lệch quá mạnh.
- `data.yaml` dùng đúng thứ tự class.


## Lỗi thường gặp và cách xử lý

### 1. `group_to_class.py` báo không tìm thấy folder

Nguyên nhân:

- thiếu thư mục trong `root_images/`,
- tên folder không đúng như `angle_p45`, `angle_m30`, ...

Cách xử lý:

- kiểm tra lại tên thư mục,
- giữ đúng chuẩn `angle_...`.

### 2. Auto-label ra bbox sai hàng loạt

Nguyên nhân thường gặp:

- background không khớp,
- ROI chọn sai,
- threshold chưa phù hợp,
- ánh sáng thay đổi mạnh.

Cách xử lý:

- chạy lại với `--reset_roi`,
- tăng hoặc giảm `--threshold`,
- đổi `--diff_mode`,
- thêm background tốt hơn.

### 3. Build dataset ra ít ảnh hơn mong đợi

Nguyên nhân:

- label rỗng bị bỏ qua mặc định,
- nhiều ảnh không có file label tương ứng,
- bạn đang trỏ nhầm `--input`.

Cách xử lý:

- kiểm tra lại `datasets/24class/tool1_output/`,
- nếu muốn giữ ảnh âm tính thì thêm `--include_empty`,
- luôn truyền rõ `--input` và `--output`.

### 4. Train bị sai class

Nguyên nhân:

- `data.yaml` không khớp thứ tự class,
- ảnh bị bỏ nhầm vào sai folder góc từ đầu,
- `session_metadata.json` của class bị sai `class_id`.

Cách xử lý:

- kiểm tra lại mapping 24 class,
- mở ngẫu nhiên một số file label để đối chiếu.


## Quy trình ngắn gọn nên dùng hằng ngày

Nếu làm đúng bộ 24 góc, flow ngắn gọn nhất là:

1. chuẩn bị `root_images/angle_xxx/` và `background/`,
2. chạy `python tools/run_group_24class.py`,
3. chạy `python tools/process_auto_label.py --raw_dir datasets/24class/raw_image --out_dir datasets/24class/tool1_output ...`,
4. kiểm tra ảnh debug và dọn nhãn lỗi,
5. chạy `python tools/build_dataset.py --input datasets/24class/tool1_output --output datasets/24class/yolo_dataset_flat`,
6. split `train/val/test`,
7. tạo `data.yaml`,
8. train bằng notebook hoặc Ultralytics.


## Gợi ý thực tế để có dataset tốt hơn

- Chụp nhiều hơn ở các góc dễ nhầm như `p180`, `p195`, `m150`, `m135`.
- Thêm đa dạng ánh sáng nhưng vẫn giữ background đủ sạch cho auto-label.
- Không nên chỉ chụp đúng một khoảng cách.
- Nên có vài ảnh bị che nhẹ hoặc lệch nhẹ để model bền hơn.
- Sau vòng train đầu, lấy các ảnh model dự đoán sai để bổ sung lại vào dataset.
