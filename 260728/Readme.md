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
 
## B. Khó khăn  
- Không 

## C. Công việc tiếp theo
- Training lại model , export model FP16 OpenVINO static 640 & 160
- Chạy inference với Leanbot chạy vòng tròn có nhiễu gỗ và đánh giá kết quả.