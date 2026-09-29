import torch
import ultralytics.utils.loss as loss_module
from ultralytics import YOLO

class SoftBCEWithLogitsLoss(torch.nn.Module):
    def __init__(self, original_bce, sigma=15.0):
        super().__init__()
        self.original_bce = original_bce
        self.sigma = sigma
        self.print_counter = 0

    def forward(self, pred_scores, target_scores):
        """
        pred_scores: (N, num_classes)
        target_scores: (N, num_classes) với giá trị max bằng IoU score tại vị trí class đúng, các vị trí khác bằng 0.
        """
        nc = target_scores.shape[-1]
        device = target_scores.device
        dtype = target_scores.dtype

        # Lọc các prediction dương tính (những hộp có chứa Leanbot)
        fg_mask = target_scores.sum(dim=-1) > 0

        # Clone để tránh làm hỏng target_scores gốc (vì YOLO còn dùng nó cho bbox loss)
        soft_target_scores = target_scores.clone()

        if fg_mask.sum() > 0:
            pos_targets = target_scores[fg_mask] # (num_pos, nc)
            
            # Class góc đúng nhất là class có giá trị lớn nhất trong hàng
            assigned_cls = pos_targets.argmax(dim=-1)
            original_iou_scores = pos_targets.sum(dim=-1, keepdim=True)
            
            # Mảng các góc (0, 15, 30, ..., 345)
            class_angles = torch.arange(nc, device=device, dtype=dtype) * 15.0
            true_angles = class_angles[assigned_cls]
            
            # Tính khoảng cách góc ngắn nhất theo vòng tròn 360 độ
            diff = (true_angles[:, None] - class_angles[None, :]).abs()
            d = torch.minimum(diff, 360.0 - diff)
            
            # Phân phối Gaussian (Soft)
            soft = torch.exp(-0.5 * (d / self.sigma) ** 2)
            
            # Đỉnh của Gaussian bằng 1, ta nhân với giá trị IoU cũ để giữ nguyên cường độ phạt
            soft = soft * original_iou_scores
            
            soft_target_scores[fg_mask] = soft
            
            # In ra debug để đối chiếu theo chu kỳ
            self.print_counter += 1
            if self.print_counter % 50 == 1:
                print("\n" + "="*70)
                print("[DEBUG] SO SÁNH TARGET TRƯỚC VÀ SAU KHI LÀM MỀM (Soft Target)")
                print("Original target_scores (Hard):")
                print(target_scores[fg_mask][0].cpu().numpy().round(3))
                print("\nModified target_scores (Soft - Sigma = {}):".format(self.sigma))
                print(soft_target_scores[fg_mask][0].cpu().numpy().round(3))
                print("="*70 + "\n")

        # Đưa soft_target_scores vào hàm BCE mặc định của YOLO để tính loss như bình thường
        return self.original_bce(pred_scores, soft_target_scores)

# =====================================================================
# THỦ THUẬT MONKEY PATCHING
# Mục đích: Ghi đè hàm khởi tạo của v8DetectionLoss trong thư viện ultralytics
# mà không cần phải can thiệp sửa đổi file mã nguồn hệ thống của Colab.
# =====================================================================
original_init = loss_module.v8DetectionLoss.__init__

def patched_init(self, model):
    # Gọi hàm khởi tạo gốc của YOLO
    original_init(self, model)
    # Sau khi YOLO tạo xong hàm BCE, ta tráo đổi nó bằng hàm Custom của chúng ta
    print("\n>>> Đã kích hoạt thành công Soft Angular Target (BCE Loss) với Sigma=15.0 <<<\n")
    self.bce = SoftBCEWithLogitsLoss(self.bce, sigma=15.0)

# Thực hiện tráo đổi lệnh
loss_module.v8DetectionLoss.__init__ = patched_init
# =====================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Train YOLOv8 với SoftBCE Loss cho Leanbot 24 góc")
    parser.add_argument("--data", default="leanbot_data.yaml", help="Đường dẫn file data YAML")
    parser.add_argument("--epochs", type=int, default=100, help="Số epoch huấn luyện")
    parser.add_argument("--batch", type=int, default=16, help="Batch size")
    parser.add_argument("--device", default="0", help="Device (0 cho GPU, cpu cho CPU)")
    parser.add_argument("--name", default="leanbot_soft_bce", help="Tên thí nghiệm")
    parser.add_argument("--model", default="yolov8n.pt", help="Model pretrained")
    parser.add_argument("--sigma", type=float, default=15.0, help="Sigma cho Gaussian trong SoftBCE")
    args = parser.parse_args()

    # Cập nhật sigma nếu khác mặc định
    if args.sigma != 15.0:
        # Patch lại với sigma mới
        def patched_init_custom(self, model):
            original_init(self, model)
            print(f"\n>>> Đã kích hoạt Soft Angular Target (BCE Loss) với Sigma={args.sigma} <<<\n")
            self.bce = SoftBCEWithLogitsLoss(self.bce, sigma=args.sigma)
        loss_module.v8DetectionLoss.__init__ = patched_init_custom

    print("=" * 60)
    print("[*] TRAINING VỚI SOFT BCE LOSS")
    print(f"    Model    : {args.model}")
    print(f"    Data     : {args.data}")
    print(f"    Epochs   : {args.epochs}")
    print(f"    Batch    : {args.batch}")
    print(f"    Device   : {args.device}")
    print(f"    Sigma    : {args.sigma}")
    print(f"    Name     : {args.name}")
    print()
    print("[*] DATA AUGMENTATION:")
    print("    degrees  = 10.0  (xoay ±10°)")
    print("    fliplr   = 0.0   (KHÔNG lật ngang — bảo toàn hướng)")
    print("    flipud   = 0.0   (KHÔNG lật dọc — bảo toàn hướng)")
    print("=" * 60)

    model = YOLO(args.model)
    model.train(
        data=args.data,
        epochs=args.epochs,
        batch=args.batch,
        device=args.device,
        name=args.name,
        # Augmentation cho bài toán góc quay:
        # KHÔNG lật ngang/dọc vì sẽ thay đổi hướng robot
        degrees=10.0,
        fliplr=0.0,
        flipud=0.0,
    )
