# Báo cáo công việc ngày 25/07/2026

## A. Công việc đã làm 
- Chụp dataset ảnh nhiễu cho 24 class ( mỗi class 2 ảnh)
- Build dataset 
- Train lại model

### 1. Chụp lại toàn bộ datasets.
- Bổ sung dataset cho toàn bộ 24 class , mỗi class có 2 ảnh và 2 back ground tương ứng . 

- Sau khi đã thử nghiệm lại, check kết quả bbox debug thì em đã chạy lệnh chạy trừ ảnh abstract & auto label vơi các tham số nhưu sau : 
```bash
python .\tools\process_auto_label_paired.py `
  --raw_dir .\staging `
  --out_dir .\output_paired_260727 `
  --diff_mode 1 `
  --threshold 90 `
  --blur 3 `
  --min_area 6000 `
  --max_area 500000 `
  --min_width 115 `
  --max_width 600 `
  --min_height 0 `
  --max_height 600 `
  --mask_merge_kernel 11 `
  --mask_merge_iterations 1 `
  --wait_ms 200
```


- Toàn bộ các ảnh bổ sung như sau:

| Class | Ảnh capture | Ảnh BBox debug |
|:--:|:--:|:--:|
| `Leanbot_0` | ![Leanbot_0 capture 000](raw_image/Leanbot_0_redObstacle/raw_images/deg_0_000.jpg)<br>![Leanbot_0 capture 001](raw_image/Leanbot_0_redObstacle/raw_images/deg_0_001.jpg) | ![Leanbot_0 bbox 000](output_paired_260727/Leanbot_0_redObstacle/debug/deg_0_000_bbox.jpg)<br>![Leanbot_0 bbox 001](output_paired_260727/Leanbot_0_redObstacle/debug/deg_0_001_bbox.jpg) |
| `Leanbot_p15` | ![Leanbot_p15 capture 000](raw_image/Leanbot_p15_redObstacle/raw_images/deg_0_000.jpg)<br>![Leanbot_p15 capture 001](raw_image/Leanbot_p15_redObstacle/raw_images/deg_0_001.jpg) | ![Leanbot_p15 bbox 000](output_paired_260727/Leanbot_p15_redObstacle/debug/deg_0_000_bbox.jpg)<br>![Leanbot_p15 bbox 001](output_paired_260727/Leanbot_p15_redObstacle/debug/deg_0_001_bbox.jpg) |
| `Leanbot_p30` | ![Leanbot_p30 capture 000](raw_image/Leanbot_p30_redObstacle/raw_images/deg_0_000.jpg)<br>![Leanbot_p30 capture 001](raw_image/Leanbot_p30_redObstacle/raw_images/deg_0_001.jpg) | ![Leanbot_p30 bbox 000](output_paired_260727/Leanbot_p30_redObstacle/debug/deg_0_000_bbox.jpg)<br>![Leanbot_p30 bbox 001](output_paired_260727/Leanbot_p30_redObstacle/debug/deg_0_001_bbox.jpg) |
| `Leanbot_p45` | ![Leanbot_p45 capture 000](raw_image/Leanbot_p45_redObstacle/raw_images/deg_0_000.jpg)<br>![Leanbot_p45 capture 001](raw_image/Leanbot_p45_redObstacle/raw_images/deg_0_001.jpg) | ![Leanbot_p45 bbox 000](output_paired_260727/Leanbot_p45_redObstacle/debug/deg_0_000_bbox.jpg)<br>![Leanbot_p45 bbox 001](output_paired_260727/Leanbot_p45_redObstacle/debug/deg_0_001_bbox.jpg) |
| `Leanbot_p60` | ![Leanbot_p60 capture 000](raw_image/Leanbot_p60_redObstacle/raw_images/deg_0_000.jpg)<br>![Leanbot_p60 capture 001](raw_image/Leanbot_p60_redObstacle/raw_images/deg_0_001.jpg) | ![Leanbot_p60 bbox 000](output_paired_260727/Leanbot_p60_redObstacle/debug/deg_0_000_bbox.jpg)<br>![Leanbot_p60 bbox 001](output_paired_260727/Leanbot_p60_redObstacle/debug/deg_0_001_bbox.jpg) |
| `Leanbot_p75` | ![Leanbot_p75 capture 000](raw_image/Leanbot_p75_redObstacle/raw_images/deg_0_000.jpg)<br>![Leanbot_p75 capture 001](raw_image/Leanbot_p75_redObstacle/raw_images/deg_0_001.jpg) | ![Leanbot_p75 bbox 000](output_paired_260727/Leanbot_p75_redObstacle/debug/deg_0_000_bbox.jpg)<br>![Leanbot_p75 bbox 001](output_paired_260727/Leanbot_p75_redObstacle/debug/deg_0_001_bbox.jpg) |
| `Leanbot_p90` | ![Leanbot_p90 capture 000](raw_image/Leanbot_p90_redObstacle/raw_images/deg_0_000.jpg)<br>![Leanbot_p90 capture 001](raw_image/Leanbot_p90_redObstacle/raw_images/deg_0_001.jpg) | ![Leanbot_p90 bbox 000](output_paired_260727/Leanbot_p90_redObstacle/debug/deg_0_000_bbox.jpg)<br>![Leanbot_p90 bbox 001](output_paired_260727/Leanbot_p90_redObstacle/debug/deg_0_001_bbox.jpg) |
| `Leanbot_p105` | ![Leanbot_p105 capture 000](raw_image/Leanbot_p105_redObstacle/raw_images/deg_0_000.jpg)<br>![Leanbot_p105 capture 001](raw_image/Leanbot_p105_redObstacle/raw_images/deg_0_001.jpg) | ![Leanbot_p105 bbox 000](output_paired_260727/Leanbot_p105_redObstacle/debug/deg_0_000_bbox.jpg)<br>![Leanbot_p105 bbox 001](output_paired_260727/Leanbot_p105_redObstacle/debug/deg_0_001_bbox.jpg) |
| `Leanbot_p120` | ![Leanbot_p120 capture 000](raw_image/Leanbot_p120_redObstacle/raw_images/deg_0_000.jpg)<br>![Leanbot_p120 capture 001](raw_image/Leanbot_p120_redObstacle/raw_images/deg_0_001.jpg) | ![Leanbot_p120 bbox 000](output_paired_260727/Leanbot_p120_redObstacle/debug/deg_0_000_bbox.jpg)<br>![Leanbot_p120 bbox 001](output_paired_260727/Leanbot_p120_redObstacle/debug/deg_0_001_bbox.jpg) |
| `Leanbot_p135` | ![Leanbot_p135 capture 000](raw_image/Leanbot_p135_redObstacle/raw_images/deg_0_000.jpg)<br>![Leanbot_p135 capture 001](raw_image/Leanbot_p135_redObstacle/raw_images/deg_0_001.jpg) | ![Leanbot_p135 bbox 000](output_paired_260727/Leanbot_p135_redObstacle/debug/deg_0_000_bbox.jpg)<br>![Leanbot_p135 bbox 001](output_paired_260727/Leanbot_p135_redObstacle/debug/deg_0_001_bbox.jpg) |
| `Leanbot_p150` | ![Leanbot_p150 capture 000](raw_image/Leanbot_p150_redObstacle/raw_images/deg_0_000.jpg)<br>![Leanbot_p150 capture 001](raw_image/Leanbot_p150_redObstacle/raw_images/deg_0_001.jpg) | ![Leanbot_p150 bbox 000](output_paired_260727/Leanbot_p150_redObstacle/debug/deg_0_000_bbox.jpg)<br>![Leanbot_p150 bbox 001](output_paired_260727/Leanbot_p150_redObstacle/debug/deg_0_001_bbox.jpg) |
| `Leanbot_p165` | ![Leanbot_p165 capture 000](raw_image/Leanbot_p165_redObstacle/raw_images/deg_0_000.jpg)<br>![Leanbot_p165 capture 001](raw_image/Leanbot_p165_redObstacle/raw_images/deg_0_001.jpg) | ![Leanbot_p165 bbox 000](output_paired_260727/Leanbot_p165_redObstacle/debug/deg_0_000_bbox.jpg)<br>![Leanbot_p165 bbox 001](output_paired_260727/Leanbot_p165_redObstacle/debug/deg_0_001_bbox.jpg) |
| `Leanbot_p180` | ![Leanbot_p180 capture 000](raw_image/Leanbot_p180_redObstacle/raw_images/deg_0_000.jpg)<br>![Leanbot_p180 capture 001](raw_image/Leanbot_p180_redObstacle/raw_images/deg_0_001.jpg) | ![Leanbot_p180 bbox 000](output_paired_260727/Leanbot_p180_redObstacle/debug/deg_0_000_bbox.jpg)<br>![Leanbot_p180 bbox 001](output_paired_260727/Leanbot_p180_redObstacle/debug/deg_0_001_bbox.jpg) |
| `Leanbot_p195` | ![Leanbot_p195 capture 000](raw_image/Leanbot_p195_redObstacle/raw_images/deg_0_000.jpg)<br>![Leanbot_p195 capture 001](raw_image/Leanbot_p195_redObstacle/raw_images/deg_0_001.jpg) | ![Leanbot_p195 bbox 000](output_paired_260727/Leanbot_p195_redObstacle/debug/deg_0_000_bbox.jpg)<br>![Leanbot_p195 bbox 001](output_paired_260727/Leanbot_p195_redObstacle/debug/deg_0_001_bbox.jpg) |
| `Leanbot_m150` | ![Leanbot_m150 capture 000](raw_image/Leanbot_m150_redObstacle/raw_images/deg_0_000.jpg)<br>![Leanbot_m150 capture 001](raw_image/Leanbot_m150_redObstacle/raw_images/deg_0_001.jpg) | ![Leanbot_m150 bbox 000](output_paired_260727/Leanbot_m150_redObstacle/debug/deg_0_000_bbox.jpg)<br>![Leanbot_m150 bbox 001](output_paired_260727/Leanbot_m150_redObstacle/debug/deg_0_001_bbox.jpg) |
| `Leanbot_m135` | ![Leanbot_m135 capture 000](raw_image/Leanbot_m135_redObstacle/raw_images/deg_0_000.jpg)<br>![Leanbot_m135 capture 001](raw_image/Leanbot_m135_redObstacle/raw_images/deg_0_001.jpg) | ![Leanbot_m135 bbox 000](output_paired_260727/Leanbot_m135_redObstacle/debug/deg_0_000_bbox.jpg)<br>![Leanbot_m135 bbox 001](output_paired_260727/Leanbot_m135_redObstacle/debug/deg_0_001_bbox.jpg) |
| `Leanbot_m120` | ![Leanbot_m120 capture 000](raw_image/Leanbot_m120_redObstacle/raw_images/deg_0_000.jpg)<br>![Leanbot_m120 capture 001](raw_image/Leanbot_m120_redObstacle/raw_images/deg_0_001.jpg) | ![Leanbot_m120 bbox 000](output_paired_260727/Leanbot_m120_redObstacle/debug/deg_0_000_bbox.jpg)<br>![Leanbot_m120 bbox 001](output_paired_260727/Leanbot_m120_redObstacle/debug/deg_0_001_bbox.jpg) |
| `Leanbot_m105` | ![Leanbot_m105 capture 000](raw_image/Leanbot_m105_redObstacle/raw_images/deg_0_000.jpg)<br>![Leanbot_m105 capture 001](raw_image/Leanbot_m105_redObstacle/raw_images/deg_0_001.jpg) | ![Leanbot_m105 bbox 000](output_paired_260727/Leanbot_m105_redObstacle/debug/deg_0_000_bbox.jpg)<br>![Leanbot_m105 bbox 001](output_paired_260727/Leanbot_m105_redObstacle/debug/deg_0_001_bbox.jpg) |
| `Leanbot_m90` | ![Leanbot_m90 capture 000](raw_image/Leanbot_m90_redObstacle/raw_images/deg_0_000.jpg)<br>![Leanbot_m90 capture 001](raw_image/Leanbot_m90_redObstacle/raw_images/deg_0_001.jpg) | ![Leanbot_m90 bbox 000](output_paired_260727/Leanbot_m90_redObstacle/debug/deg_0_000_bbox.jpg)<br>![Leanbot_m90 bbox 001](output_paired_260727/Leanbot_m90_redObstacle/debug/deg_0_001_bbox.jpg) |
| `Leanbot_m75` | ![Leanbot_m75 capture 000](raw_image/Leanbot_m75_redObstacle/raw_images/deg_0_000.jpg)<br>![Leanbot_m75 capture 001](raw_image/Leanbot_m75_redObstacle/raw_images/deg_0_001.jpg) | ![Leanbot_m75 bbox 000](output_paired_260727/Leanbot_m75_redObstacle/debug/deg_0_000_bbox.jpg)<br>![Leanbot_m75 bbox 001](output_paired_260727/Leanbot_m75_redObstacle/debug/deg_0_001_bbox.jpg) |
| `Leanbot_m60` | ![Leanbot_m60 capture 000](raw_image/Leanbot_m60_redObstacle/raw_images/deg_0_000.jpg)<br>![Leanbot_m60 capture 001](raw_image/Leanbot_m60_redObstacle/raw_images/deg_0_001.jpg) | ![Leanbot_m60 bbox 000](output_paired_260727/Leanbot_m60_redObstacle/debug/deg_0_000_bbox.jpg)<br>![Leanbot_m60 bbox 001](output_paired_260727/Leanbot_m60_redObstacle/debug/deg_0_001_bbox.jpg) |
| `Leanbot_m45` | ![Leanbot_m45 capture 000](raw_image/Leanbot_m45_redObstacle/raw_images/deg_0_000.jpg)<br>![Leanbot_m45 capture 001](raw_image/Leanbot_m45_redObstacle/raw_images/deg_0_001.jpg) | ![Leanbot_m45 bbox 000](output_paired_260727/Leanbot_m45_redObstacle/debug/deg_0_000_bbox.jpg)<br>![Leanbot_m45 bbox 001](output_paired_260727/Leanbot_m45_redObstacle/debug/deg_0_001_bbox.jpg) |
| `Leanbot_m30` | ![Leanbot_m30 capture 000](raw_image/Leanbot_m30_redObstacle/raw_images/deg_0_000.jpg)<br>![Leanbot_m30 capture 001](raw_image/Leanbot_m30_redObstacle/raw_images/deg_0_001.jpg) | ![Leanbot_m30 bbox 000](output_paired_260727/Leanbot_m30_redObstacle/debug/deg_0_000_bbox.jpg)<br>![Leanbot_m30 bbox 001](output_paired_260727/Leanbot_m30_redObstacle/debug/deg_0_001_bbox.jpg) |
| `Leanbot_m15` | ![Leanbot_m15 capture 000](raw_image/Leanbot_m15_redObstacle/raw_images/deg_0_000.jpg)<br>![Leanbot_m15 capture 001](raw_image/Leanbot_m15_redObstacle/raw_images/deg_0_001.jpg) | ![Leanbot_m15 bbox 000](output_paired_260727/Leanbot_m15_redObstacle/debug/deg_0_000_bbox.jpg)<br>![Leanbot_m15 bbox 001](output_paired_260727/Leanbot_m15_redObstacle/debug/deg_0_001_bbox.jpg) |


#### Quy trình build dataset

1. Crop ảnh đã align theo ROI, padding thành ảnh vuông `1600 x 1600`, resize về `640 x 640` và chuyển đổi lại tọa độ label:

```powershell
python .\tools\crop_tool.py `
  --input .\output_paired_260727 `
  --output .\crop_images_260727
```

2. Build riêng `48` ảnh mới thành dataset YOLO dạng phẳng `images/` và `labels/`:

```powershell
python .\tools\build_dataset.py `
  --input .\crop_images_260727 `
  --output .\dataset_new_48_260727
```


3. Sử dụng lại dataset `132` ảnh tại [`../260717/datasets`](../260717/datasets) làm dữ liệu có sẵn. Dataset này gồm `120` ảnh Leanbot và `12` ảnh nhiễu nền không có Leanbot.

4. Sao chép dataset `132` ảnh sang folder mới, sau đó bổ sung `48` cặp ảnh/label từ `dataset_new_48_260727`:
   - Giữ nguyên các file `000000` đến `000131` của dataset `132` ảnh.
   - Đánh số `48` ảnh mới từ `000132` đến `000179`.


- Thống kê dataset :

| Thành phần | Số lượng | Ghi chú |
|:--|--:|:--|
| Dataset gốc | `120` ảnh | `24` class, `5` ảnh/class Leanbot khôgn có nhiễu |
| Ảnh nhiễu nền | `12` ảnh | Không có Leanbot, label rỗng |
| Ảnh Leanbot có nhiễu | `48` ảnh | `24` class, `2` ảnh/class Leanbot có khối gỗ đỏ |
| Tổng dataset sau khi build dataset| `180` ảnh | `168` ảnh có Leanbot và `12` ảnh nhiễu nền không có Leanbot |

- Folder dataset gốc `120` ảnh: [`../260713/datasets`](../260713/datasets).
- Folder dataset bổ sung thêm `12` ảnh nhiễu nền: [`../260717/raw_image/no_leanbot/backgrounds`](../260717/raw_image/no_leanbot/backgrounds).
-Toàn bộ Dataset 180 ảnh sau khi tích hợp thêm `48` ảnh có nhiễu: [`../datasets`](datasets).
 
### 2. Training model và kết quả train

#### 2.1. Thông tin training

Model được train bằng notebook [`tools/Leanbot_Train_SoftBCE.ipynb`](tools/Leanbot_Train_SoftBCE.ipynb), sử dụng YOLO11n pretrained và Soft Angular BCE loss function

| Thông tin | Giá trị thực tế |
| :--- | :--- |
| Model nền tảng | `yolo11n.pt` - YOLO11 Nano, pretrained |
| Task | Object Detection kết hợp phân loại hướng Leanbot |
| Số class | `24`, mỗi class cách nhau `15°` |
| Custom loss | Soft Angular BCE, `sigma=15.0°` |
| Tổng dataset | `180` ảnh: `168` ảnh có Leanbot và `12` ảnh nhiễu nền không có Leanbot |
| Phân bố dữ liệu | `120` ảnh gốc, `48` ảnh có vật cản đỏ, `12` ảnh background negative |
| Dataset split thực tế | `104` ảnh train, `26` ảnh validation, `50` ảnh test |
| Số epoch | `170` |
| Batch size | `16` |
| Image size | `640 x 640` |
| Optimizer | `auto` |
| Learning rate | `lr0=0.01`, `lrf=0.01` |
| Momentum / weight decay | `0.937` / `0.0005` |
| Warmup | `3` epochs |
| Augmentation chính | `degrees=10.0`, `translate=0.1`, `scale=0.5`, `mosaic=1.0` |
| Flip augmentation | `fliplr=0.0`, `flipud=0.0` để không làm sai nhãn góc |
| Close mosaic | Tắt mosaic trong `10` epoch cuối |
| Mixed precision | `amp=true` |
| Môi trường | Google Colab, GPU Tesla T4 |
| Thời gian training | `458.888 s`, tương đương khoảng `7 phút 39 giây` |
| Output | [`leanbot_colab`](leanbot_colab/) |
| Best model | [`leanbot_colab/weights/best.pt`](leanbot_colab/weights/best.pt) |
| Last model | [`leanbot_colab/weights/last.pt`](leanbot_colab/weights/last.pt) |


Các file kết quả chính:
- [`args.yaml`](leanbot_colab/args.yaml): toàn bộ cấu hình training.
- [`results.csv`](leanbot_colab/results.csv): loss và metric theo `170` epoch.
- [`results.png`](leanbot_colab/results.png): tổng hợp loss, Precision, Recall và mAP.
- [`confusion_matrix.png`](leanbot_colab/confusion_matrix.png) và [`confusion_matrix_normalized.png`](leanbot_colab/confusion_matrix_normalized.png): ma trận nhầm lẫn.
- [`BoxP_curve.png`](leanbot_colab/BoxP_curve.png), [`BoxR_curve.png`](leanbot_colab/BoxR_curve.png), [`BoxF1_curve.png`](leanbot_colab/BoxF1_curve.png), [`BoxPR_curve.png`](leanbot_colab/BoxPR_curve.png): các đường đánh giá theo confidence.
- [`labels.jpg`](leanbot_colab/labels.jpg), [`train_batch0.jpg`](leanbot_colab/train_batch0.jpg), [`train_batch1122.jpg`](leanbot_colab/train_batch1122.jpg): kiểm tra dữ liệu và augmentation.
- [`val_batch0_labels.jpg`](leanbot_colab/val_batch0_labels.jpg) và [`val_batch0_pred.jpg`](leanbot_colab/val_batch0_pred.jpg): so sánh label thật với kết quả dự đoán.

#### 2.2. Kết quả metric

Nguồn metric chính: [`leanbot_colab/results.csv`](leanbot_colab/results.csv).

Epoch có `mAP50-95` tốt nhất là epoch `140`. Đây cũng là epoch có `mAP50` cao nhất:

| Metric tại epoch `140` | Giá trị |
| :--- | ---: |
| `metrics/precision(B)` | `0.75357` |
| `metrics/recall(B)` | `0.89218` |
| `metrics/mAP50(B)` | `0.93596` |
| `metrics/mAP50-95(B)` | `0.79487` |
| `train/box_loss` | `0.62100` |
| `train/cls_loss` | `2.47076` |
| `train/dfl_loss` | `0.90197` |
| `val/box_loss` | `0.65783` |
| `val/cls_loss` | `2.16062` |
| `val/dfl_loss` | `0.89698` |

Metric ở epoch cuối (`epoch=170`):

| Metric | Giá trị |
| :--- | ---: |
| `train/box_loss` | `0.51901` |
| `train/cls_loss` | `2.35588` |
| `train/dfl_loss` | `0.86497` |
| `metrics/precision(B)` | `0.71059` |
| `metrics/recall(B)` | `0.87526` |
| `metrics/mAP50(B)` | `0.91024` |
| `metrics/mAP50-95(B)` | `0.77737` |
| `val/box_loss` | `0.63323` |
| `val/cls_loss` | `2.20850` |
| `val/dfl_loss` | `0.90293` |
| Learning rate | `5.649e-06` |

Giá trị tốt nhất trong toàn bộ quá trình train:

| Metric | Best value | Epoch | Ghi chú |
| :--- | ---: | ---: | :--- |
| `metrics/precision(B)` | `0.78531` | `146` | Precision cao nhất |
| `metrics/recall(B)` | `0.98148` | `14` | Recall cao sớm, khi Precision còn thấp |
| `metrics/mAP50(B)` | `0.93596` | `140` | mAP tại IoU `0.5` cao nhất |
| `metrics/mAP50-95(B)` | `0.79487` | `140` | Metric chính để chọn `best.pt` |
| `train/box_loss` | `0.51901` | `170` | Loss bbox train thấp nhất |
| `train/cls_loss` | `2.35083` | `166` | Loss class train thấp nhất |
| `train/dfl_loss` | `0.86497` | `170` | Loss DFL train thấp nhất |
| `val/box_loss` | `0.61825` | `152` | Loss bbox validation thấp nhất |
| `val/cls_loss` | `2.13431` | `146` | Loss class validation thấp nhất |
| `val/dfl_loss` | `0.86411` | `8` | Loss DFL validation thấp nhất |

#### 2.3. Biểu đồ tổng hợp quá trình training

![Leanbot training results](leanbot_colab/results.png)


- Precision tăng chậm hơn Recall. Kết quả cuối có `Recall=0.87526` cao hơn `Precision=0.71059`, cho thấy model bắt được phần lớn đối tượng nhưng vẫn còn nhiều dự đoán dư hoặc sai class.
- Nên sử dụng [`best.pt`](leanbot_colab/weights/best.pt) thay vì `last.pt` cho bước export và inference.

#### 2.4. Phân bố label và dữ liệu augmentation

![Leanbot labels distribution](leanbot_colab/labels.jpg)


Ảnh batch ở giai đoạn đầu, khi mosaic và augmentation còn hoạt động:

![Leanbot first training batch](leanbot_colab/train_batch0.jpg)

Ảnh batch gần cuối quá trình training, khi mosaic đã được tắt bởi `close_mosaic=10`:

![Leanbot final training batch](leanbot_colab/train_batch1122.jpg)


#### 2.5. Precision, Recall, F1 và PR curve

![Leanbot Box F1 curve](leanbot_colab/BoxF1_curve.png)

- F1 tổng hợp cao nhất đạt khoảng `0.78` tại confidence `0.799`. 
![Leanbot Box Precision curve](leanbot_colab/BoxP_curve.png)


![Leanbot Box Recall curve](leanbot_colab/BoxR_curve.png)


![Leanbot Box PR curve](leanbot_colab/BoxPR_curve.png)


#### 2.6. Ma trận nhầm lẫn

![Leanbot normalized confusion matrix](leanbot_colab/confusion_matrix_normalized.png)

![Leanbot confusion matrix](leanbot_colab/confusion_matrix.png)

- Ma trận còn phân tán nhiều ngoài đường chéo, cho thấy khả năng phân biệt chính xác `24` class góc nhiễu nặng
- Cột `background` có số lượng lớn, phản ánh nhiều prediction không ghép đúng với ground truth hoặc có nhiều class prediction trên cùng một Leanbot.
- Tập validation chỉ có `1` ảnh/class, tương đương khoảng `9` object/class, nên mỗi object sai có thể làm tỷ lệ chuẩn hóa thay đổi khoảng `0.11`. Ma trận hiện tại vì vậy có độ dao động lớn.


#### 2.7. So sánh label thật và ảnh prediction

Ground truth của batch validation:

![Leanbot validation labels](leanbot_colab/val_batch0_labels.jpg)

Kết quả prediction của model:

![Leanbot validation predictions](leanbot_colab/val_batch0_pred.jpg)



## B. Khó khăn  
- Sau train thì em thấy ma trận nhầm lần (Confusion matrix) bị nhiễu ạ . 
- Từ hôm qua tới giờ em bị lỗi không đăng nhập được lại vào git pythaverse mặc dù nhập đúng tên và Api key ạ 
- Em xin phép báo cáo tạm bằng git cá nhân ạ 
## C. Công việc tiếp theo
- Export model FP16 OpenVINO static 640 & 160
- Chạy inference với Leanbot chạy vòng tròn có nhiễu gỗ và đánh giá kết quả.
