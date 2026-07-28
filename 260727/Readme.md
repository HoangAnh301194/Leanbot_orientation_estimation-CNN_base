# Báo cáo công việc ngày 25/07/2026

## A. Công việc đã làm 
- Vẽ lại quỹ đạo di chuyển của toàn bộ các log csv trước đó. 
- Chụp lại ảnh dataset .
- Build dataset. 
### 1. Vẽ lại quỹ đạo di chuyển của các log csv. 
- Các log csv được tái sử dụng và đồ thị quỹ đạo tương ứng : 

|Folder báo cáo ngày|Link log csv | Cấu hình inference | Đồ thị góc, xy_center | Đồ thị quỹ đạo Oxy auto-zoom |
|:--:|:--:|:--:|:--:|:--:|
|[10/07/2026](../260710/Readme.md)|[log_roi_tracking_720p.csv](../260710/benchmark/log_roi_tracking_720p.csv) — 551 frame, lost `0`|ROI tracking; full model `640` + tracking model `160`; camera `source=1`, `1280x720`|![Angle và XY center](../260710/benchmark/log_roi_tracking_720p.png)|![Quỹ đạo Oxy 10/07](trajectory_plots/260710__benchmark__log_roi_tracking_720p_oxy_trajectory.png)|
|[14/07/2026](../260714/Readme.md)|[yolo11n_fp16_roi_tracking.csv — Full HD](../260714/benchmarkFullHD/yolo11n_fp16_roi_tracking.csv) — 561 frame, lost `0`|YOLO11n OpenVINO FP16; ROI `640/160`; camera `source=1`, `1920x1080`; `conf=0.25` mặc định|![YOLO11n trajectory](../260714/benchmarkFullHD/7_yolo11n_trajectory.png)|![Quỹ đạo YOLO11n Full HD](trajectory_plots/260714__benchmarkFullHD__yolo11n_fp16_roi_tracking_oxy_trajectory.png)|
|[14/07/2026](../260714/Readme.md)|[yolov8n_fp16_roi_tracking.csv — Full HD](../260714/benchmarkFullHD/yolov8n_fp16_roi_tracking.csv) — 566 frame, lost `0`|YOLOv8n OpenVINO FP16; ROI `640/160`; camera `source=1`, `1920x1080`; `conf=0.25` mặc định|![YOLOv8n trajectory](../260714/benchmarkFullHD/6_yolov8n_trajectory.png)|![Quỹ đạo YOLOv8n Full HD](trajectory_plots/260714__benchmarkFullHD__yolov8n_fp16_roi_tracking_oxy_trajectory.png)|
|[14/07/2026](../260714/Readme.md)|[yolo11n obstacle — conf 0.25 lần 2](../260714/benchmarkWithObstacle/yolo11n_fp16_roi_tracking_tunr2.csv) — 506 frame, lost `2`|YOLO11n OpenVINO FP16; ROI `640/160`; `1920x1080`; có khối gỗ chắn; `conf=0.25`|![Angle và XY center](../260714/benchmarkWithObstacle/yolo11n_fp16_roi_tracking_tunr2.png)|![Quỹ đạo obstacle conf 0.25](trajectory_plots/260714__benchmarkWithObstacle__yolo11n_fp16_roi_tracking_tunr2_oxy_trajectory.png)|
|[14/07/2026](../260714/Readme.md)|[yolo11n obstacle — conf 0.65](../260714/benchmarkWithObstacle_065/yolo11n_fp16_roi_tracking_065.csv) — 512 frame, lost `14`|YOLO11n OpenVINO FP16; ROI `640/160`; `1920x1080`; có khối gỗ chắn; tăng `conf=0.65`|![Angle và XY center](../260714/benchmarkWithObstacle_065/yolo11n_fp16_roi_tracking_065.png)|![Quỹ đạo obstacle conf 0.65](trajectory_plots/260714__benchmarkWithObstacle_065__yolo11n_fp16_roi_tracking_065_oxy_trajectory.png)|
|[16/07/2026](../260716/Readme.md)|[log_no_nms.csv](../260716/benchmark/log_no_nms.csv) — 549 frame, lost `0`|YOLO11n OpenVINO FP16 No-NMS; ROI static `640/160`; `source=1`; `conf=0.25`, `topk=200`, `IoU=0.5`, `min-mag=2.0`|![Trajectory No-NMS](../260716/benchmark/trajectory_angle_no_nms.png)|![Quỹ đạo No-NMS](trajectory_plots/260716__benchmark__log_no_nms_oxy_trajectory.png)|
|[20/07/2026](../260720/Readme.md)|[benchmark1/fullframe_test.csv](../260720/benchmark1/fullframe_test.csv) — 667 frame, lost `1`|Cùng video `1920x1080`; ROI; full/tracking No-NMS `640/160`; `conf=0.01`, `roi_conf=0.01`, `topk=100`, `IoU=0.5`, `min-mag=0.0`; lần 1|![Angle và XY center — lần 1](../260720/benchmark1/fullframe_test.png)|![Quỹ đạo 20/07 lần 1](trajectory_plots/260720__benchmark1__fullframe_test_oxy_trajectory.png)|
|[20/07/2026](../260720/Readme.md)|[benchmark/fullframe_test.csv](../260720/benchmark/fullframe_test.csv) — 667 frame, lost `1`|Cùng video `1920x1080`; ROI; full/tracking No-NMS `640/160`; `conf=0.01`, `roi_conf=0.01`, `topk=100`, `IoU=0.5`, `min-mag=0.0`; lần 2|![Angle và XY center — lần 2](../260720/benchmark/fullframe_test.png)|![Quỹ đạo 20/07 lần 2](trajectory_plots/260720__benchmark__fullframe_test_oxy_trajectory.png)|
|[21/07/2026](../260721/Readme.md)|[benchmark_0/fullframe_test.csv](../260721/benchmark_0/fullframe_test.csv) — 560 frame, lost `0`|Camera `source=1`; ROI No-NMS `640/160`; schema log cũ; chạy tắt ngưỡng lọc|![Angle và XY center](../260721/benchmark_0/fullframe_test.png)|![Quỹ đạo 21/07 schema cũ](trajectory_plots/260721__benchmark_0__fullframe_test_oxy_trajectory.png)|
|[21/07/2026](../260721/Readme.md)|[benchmark/fullframe_test.csv](../260721/benchmark/fullframe_test.csv) — 392 frame, lost `0`|Camera `source=1`; ROI No-NMS `640/160`; `conf=0`, `roi_conf=0`, `topk=100`, `IoU=0.5`, `min-mag=0`; log thêm Group 1/2|![Angle, XY center và magnitude](../260721/benchmark/fullframe_test.png)|![Quỹ đạo 21/07 Group 1/2](trajectory_plots/260721__benchmark__fullframe_test_oxy_trajectory.png)|
|[23/07/2026](../260723/Readme.md)|[roi_tracking_redObstacle.csv](../260723/benchmark/roi_tracking_redObstacle.csv) — 289 frame, lost `0`|Camera `source=1`; ROI No-NMS `640/160`; khối đỏ/cam quanh vòng chạy; `conf=0`, `roi_conf=0`, `topk=100`, `IoU=0.5`, `min-mag=0`|![Angle, XY center, IoU và magnitude](../260723/benchmark/roi_tracking_redObstacle.png)|![Quỹ đạo red obstacle 23/07](trajectory_plots/260723__benchmark__roi_tracking_redObstacle_oxy_trajectory.png)|
|[24/07/2026](../260724/Readme.md)|[roi_tracking_redObstacle.csv](../260724/benchmark/roi_tracking_redObstacle.csv) — 349 frame, lost `0`|Camera `source=1`; ROI No-NMS `640/160`; nhiều khối đỏ/cam; `conf=0`, `roi_conf=0`, `topk=100`, `IoU=0.5`, `mag-threshold=0`|![Angle, XY center, IoU và magnitude](../260724/benchmark/roi_tracking_redObstacle.png)|![Quỹ đạo red obstacle 24/07](trajectory_plots/260724__benchmark__roi_tracking_redObstacle_oxy_trajectory.png)|

- Code sử dụng: [tools/plot_oxy_trajectory.py](tools/plot_oxy_trajectory.py)

- Lệnh chạy tại thư mục `260727`:

```powershell
python tools/plot_oxy_trajectory.py
```

- Đồ thị tổng hợp quỹ đạo của các log csv . 

![Đồ thị tổng hợp quỹ đạo Oxy của 12 log CSV](trajectory_plots/combined_multi_oxy_trajectory.png)

### 2. Chụp lại dataset .
- Trước khi tiến hành chụp thêm cho toàn bộ class em xin phép xin xác nhận từ Thầy các chụp các data như sau ạ 

Ví dụ 1 : 

| Ảnh capture | ảnh background | Ảnh trừ abstract | ảnh Bbox debug |
|-------------|----------------|------------------|----------------|
| ![Capture 1](raw_image_0/Leanbot_0_redObstacle/raw_images/deg_0_000.jpg) | ![Background 1](raw_image_0/Leanbot_0_redObstacle/backgrounds/background_000.jpg) | ![Mask 1](tool1_output_paired_0/Leanbot_0_redObstacle/debug/deg_0_000_mask.jpg) | ![Bbox 1](tool1_output_paired_0/Leanbot_0_redObstacle/debug/deg_0_000_bbox.jpg) |

Ví dụ 2 :

| Ảnh capture | ảnh background | Ảnh trừ abstract | ảnh Bbox debug |
|-------------|----------------|------------------|----------------|
| ![Capture 2](raw_image_0/Leanbot_0_redObstacle/raw_images/deg_0_001.jpg) | ![Background 2](raw_image_0/Leanbot_0_redObstacle/backgrounds/background_001.jpg) | ![Mask 2](tool1_output_paired_0/Leanbot_0_redObstacle/debug/deg_0_001_mask.jpg) | ![Bbox 2](tool1_output_paired_0/Leanbot_0_redObstacle/debug/deg_0_001_bbox.jpg) |

- Các bước chụp 1 ảnh : 
  - Đặt 9 Leanbot trên sa bàn 
  - Đặt các khối gỗ gần Leanbot mà theo thực nghiệm thấy rằng trường hợp đó sẽ lỗi 
  - Chụp ảnh Leanbot và các khối gỗ 
  - Bỏ Leanbot ra, chụp lại 1 lần nữa (chụp background)
  > Thời gian để chụp 1 bức ảnh dataset qua các bước như vậy có hơi mất thời gian ạ , khoảng 1-2 phút cho 1 ảnh ạ .

## B. Khó khăn 
- Không
## C. Công việc tiếp theo
- Training lại và đánh giá lại model mới khi chạy inference . 
