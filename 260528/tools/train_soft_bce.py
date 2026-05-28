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
    # ĐOẠN NÀY LÀ VÍ DỤ SỬ DỤNG
    # Bạn thay đổi tham số tương ứng với code train hiện tại của bạn trên Colab
    print("Khởi tạo mô hình và bắt đầu quá trình Training với Loss tùy chỉnh...")
    
    # model = YOLO("yolov8n.pt")  
    
    # model.train(
    #     data="leanbot_data.yaml",
    #     epochs=100,
    #     batch=16,
    #     device=0,
    #     name="soft_bce_train"
    # )
