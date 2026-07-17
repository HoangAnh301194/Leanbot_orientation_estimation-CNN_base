# Báo cáo công việc ngày 17/07/2026

## A. Công việc đã làm
- Thu thập thêm ảnh nền, không có Leanbot 

### 1. Thu thập thêm ảnh nhiễu không có Leanbot 
- Bối cảnh thu thập thêm ảnh : 
    - Vẫn là ảnh sa bàn 
    - Thêm các khối gỗ màu gây nhiễu ( có đỏ và cam , đặt ở nhiều góc độ, tình trạng ngẫu nhiên)
    - Đặt thêm các linh kiện rời vào sa bàn ( PCB LbBase, LbSide, SRF-05, bánh xe, servo, stepper, gripper, JDY-33, LbStepper, Arduino Nano) 
    - Vì các linh kiện đỏ dễ nhầm sang Leanbot hơn nên em đã ưu tiên đặt các vật màu đỏ vào để chụp ạ.

- Thông tin bộ dataset hiện tại 

| Số class | Số ảnh mỗi class | Tổng lượng ảnh | Ảnh nhiễu nền đã chụp |
|:---:|:---:|:---:|:---:|
| 24 | 5 | 120 | 30 |

- Theo như thôgn tin khuyến nghị của [Ultralytics - tips for best training results](https://docs.ultralytics.com/yolov5/tutorials/tips-for-best-training-results#model-selection) thì họ bảo ảnh backgroud nền nên chiếm khoảng `0~10%` tổng lượng ảnh trong dataset, nên em chụp 30 ảnh ạ . 
> *Background images. Background images are images with no objects that are added to a dataset to reduce False Positives (FP). We recommend about 0-10% background images to help reduce FPs (COCO has 1000 background images for reference, 1% of the total). No labels are required for background images*.

- Folder ảnh chụp thêm : [`no_leanbot/backgrounds`](raw_image/no_leanbot/backgrounds)
- Các ảnh chụp thêm như sau:

|  |  |
|:---:|:---:|
| ![0](raw_image/no_leanbot/backgrounds/background_000.jpg) | ![1](raw_image/no_leanbot/backgrounds/background_001.jpg) |
| ![2](raw_image/no_leanbot/backgrounds/background_002.jpg) | ![3](raw_image/no_leanbot/backgrounds/background_003.jpg) |
| ![4](raw_image/no_leanbot/backgrounds/background_004.jpg) | ![5](raw_image/no_leanbot/backgrounds/background_005.jpg) |
| ![6](raw_image/no_leanbot/backgrounds/background_006.jpg) | ![7](raw_image/no_leanbot/backgrounds/background_007.jpg) |
| ![8](raw_image/no_leanbot/backgrounds/background_008.jpg) | ![9](raw_image/no_leanbot/backgrounds/background_009.jpg) |
| ![10](raw_image/no_leanbot/backgrounds/background_010.jpg) | ![11](raw_image/no_leanbot/backgrounds/background_011.jpg) |
| ![12](raw_image/no_leanbot/backgrounds/background_012.jpg) | ![13](raw_image/no_leanbot/backgrounds/background_013.jpg) |
| ![14](raw_image/no_leanbot/backgrounds/background_014.jpg) | ![15](raw_image/no_leanbot/backgrounds/background_015.jpg) |
| ![16](raw_image/no_leanbot/backgrounds/background_016.jpg) | ![17](raw_image/no_leanbot/backgrounds/background_017.jpg) |
| ![18](raw_image/no_leanbot/backgrounds/background_018.jpg) | ![19](raw_image/no_leanbot/backgrounds/background_019.jpg) |
| ![20](raw_image/no_leanbot/backgrounds/background_020.jpg) | ![21](raw_image/no_leanbot/backgrounds/background_021.jpg) |
| ![22](raw_image/no_leanbot/backgrounds/background_022.jpg) | ![23](raw_image/no_leanbot/backgrounds/background_023.jpg) |
| ![24](raw_image/no_leanbot/backgrounds/background_024.jpg) | ![25](raw_image/no_leanbot/backgrounds/background_025.jpg) |
| ![26](raw_image/no_leanbot/backgrounds/background_026.jpg) | ![27](raw_image/no_leanbot/backgrounds/background_027.jpg) |
| ![28](raw_image/no_leanbot/backgrounds/background_028.jpg) | ![29](raw_image/no_leanbot/backgrounds/background_029.jpg) |
## B. Khó khăn 
- Không
## C. Công việc tiếp theo 
- Chờ xác nhận ảnh nền từ Thầy để finetune lại Model 