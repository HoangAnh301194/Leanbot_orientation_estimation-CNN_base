import os
import cv2
import glob
import numpy as np

def add_backgrounds_to_dataset(bg_dir, dataset_dir):
    images_dir = os.path.join(dataset_dir, 'images')
    labels_dir = os.path.join(dataset_dir, 'labels')
    
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(labels_dir, exist_ok=True)
    
    # 1. Đếm số lượng ảnh hiện có để biết index bắt đầu
    existing_images = glob.glob(os.path.join(images_dir, '*.jpg'))
    start_idx = len(existing_images)
    
    # Nếu tên file đang theo format 000000.jpg, ta có thể tìm số lớn nhất để chắc chắn
    if existing_images:
        indices = [int(os.path.splitext(os.path.basename(f))[0]) for f in existing_images if os.path.basename(f).split('.')[0].isdigit()]
        if indices:
            start_idx = max(indices) + 1
            
    print(f"Dataset hiện tại đang có {len(existing_images)} ảnh. Bắt đầu đánh số từ: {start_idx:06d}")
    
    # 2. Xử lý ảnh nền
    bg_files = sorted(glob.glob(os.path.join(bg_dir, '*.jpg')))
    if not bg_files:
        print(f"Không tìm thấy ảnh nền nào trong thư mục {bg_dir}")
        return
        
    print(f"Tìm thấy {len(bg_files)} ảnh nền mới cần thêm.")
    
    count = 0
    for path in bg_files:
        img = cv2.imread(path)
        if img is None:
            continue
            
        img_h, img_w = img.shape[:2]
        crop_w_req = 1600
        crop_h_req = 1440
        
        # Crop Center
        center_x = img_w // 2
        x1 = center_x - crop_w_req // 2
        x2 = x1 + crop_w_req
        y1 = 0
        y2 = crop_h_req
        
        if x1 < 0: x1 = 0; x2 = crop_w_req
        if x2 > img_w: x2 = img_w; x1 = img_w - crop_w_req
            
        cropped = img[y1:y2, x1:x2]
        
        # Pad to 1600x1600
        square_size = 1600
        square_crop = np.zeros((square_size, square_size, 3), dtype=np.uint8)
        pad_top = (square_size - crop_h_req) // 2
        square_crop[pad_top:pad_top+crop_h_req, :] = cropped
        
        # Resize to 640x640
        resized = cv2.resize(square_crop, (640, 640))
        
        # 3. Lưu ảnh và tạo label rỗng trực tiếp vào datasets
        new_name = f"{start_idx:06d}"
        
        # Ghi ảnh
        cv2.imwrite(os.path.join(images_dir, f"{new_name}.jpg"), resized)
        
        # Ghi nhãn rỗng
        with open(os.path.join(labels_dir, f"{new_name}.txt"), 'w') as f:
            pass
            
        start_idx += 1
        count += 1
        
    print(f"Hoàn tất! Đã thêm thành công {count} ảnh nền (crop center chuẩn) vào dataset.")
    print(f"Tổng số ảnh trong dataset bây giờ là: {start_idx}")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Tự động xử lý và thêm ảnh nền nhiễu vào dataset.")
    parser.add_argument(
        '--input', 
        type=str, 
        default=r'raw_image/no_leanbot/backgrounds',
        help="Đường dẫn thư mục chứa ảnh nền gốc cần xử lý."
    )
    parser.add_argument(
        '--dataset', 
        type=str, 
        default=r'datasets',
        help="Đường dẫn thư mục dataset chính (chứa images và labels)."
    )
    
    args = parser.parse_args()
    add_backgrounds_to_dataset(args.input, args.dataset)
