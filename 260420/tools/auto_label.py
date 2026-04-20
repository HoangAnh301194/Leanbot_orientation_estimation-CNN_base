"""
This tool is used to automaticaly detect the Leanbot on the Board, calculate the bounding box and create the label for the Leanbot.
The steps are as follows:
1. Capture the background image
2. Select the board ROI
3. Capture the image with Leanbot
4. Align the image with the background
5. Calculate the bounding box
6. Create the label file for the Leanbot
"""

import cv2
import os
import numpy as np
import argparse
import sys 
import time
from datetime import datetime
from pathlib import Path

# setup paths for importing libraries
CURRENT_DIR = Path(__file__).parent
sys.path.append(str(CURRENT_DIR))

# --- QUẢN LÝ ĐƯỜNG DẪN MỚI ---
OUTPUT_ROOT = CURRENT_DIR.parent / "output"
DATASETS_DIR = OUTPUT_ROOT / "datasets"
SESSIONS_ROOT = OUTPUT_ROOT / "sessions"

from alignment import ImageAligner
from mask_roi import select_four_points, build_mask

# define the resolution for Camera
WIDTH = 2560
HEIGHT = 1440

# define the window name
WINDOW_NAME = "Camera Stream"

# define the save directory
SAVE_DIR = CURRENT_DIR / "captures"

# define the preview resolution
PREVIEW_WIDTH = WIDTH // 4
PREVIEW_HEIGHT = HEIGHT // 4

def parse_source(raw_source: str):
    raw_source = raw_source.strip()
    return int(raw_source) if raw_source.isdigit() else raw_source

def setup_camera(source =0 , width = WIDTH, height = HEIGHT):
    cap = cv2.VideoCapture(source)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    if not cap.isOpened():
        raise IOError("Cannot open camera")
    return cap
# Step 1 : Capture the background image and select the board ROI
# capture the background
def capture_background(cap,width,height):
    print("Capturing background... Press 'c' to capture")
    bg_frame = None
    while True:
        ret, frame = cap.read()
        if not ret:
            raise IOError("Cannot read from camera")
            break
        preview = cv2.resize(frame, (PREVIEW_WIDTH, PREVIEW_HEIGHT))
        cv2.imshow(WINDOW_NAME, preview)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('c'):
            bg_frame = frame.copy()
            print("Background captured!")
            break
        elif key == ord('q'):
            print("Exiting...")
            break
    return bg_frame

# get board mask ROI
def get_board_mask(bg_frame):
    print("Select 4 points for the board ROI... Press 'c' to confirm")
    print("Press 'Enter' to save the points and build the mask")
    points = select_four_points(bg_frame)
    if points is None:
        raise ValueError("No points selected")
        return None, None
    mask = build_mask(bg_frame.shape, points)
    bg_masked = cv2.bitwise_and(bg_frame, bg_frame, mask=mask)

    # initialize aligner
    aligner = ImageAligner()
    aligner.set_template(bg_masked)
    return aligner, mask, points

def save_config(bg_frame, points, config_dir):
    config_dir.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(config_dir / "background.jpg"), bg_frame)
    np.save(str(config_dir / "board_points.npy"), points)
    print(f"[INFO] Cấu hình đã được lưu vào {config_dir}")

def load_config(config_dir):
    bg_path = config_dir / "background.jpg"
    pts_path = config_dir / "board_points.npy"
    if bg_path.exists() and pts_path.exists():
        bg_frame = cv2.imread(str(bg_path))
        points = np.load(str(pts_path))
        return bg_frame, points
    return None, None

def merge_bboxes(bboxes, dist_threshold=20):
    """
    Groups nearby bounding boxes and merges them into a single larger box.
    Uses an iterative approach: if two boxes are closer than dist_threshold, merge them.
    """
    if not bboxes:
        return []
    
    # Convert to list for mutability
    curr_bboxes = [list(b) for b in bboxes]
    
    changed = True
    while changed:
        changed = False
        new_bboxes = []
        visited = [False] * len(curr_bboxes)
        
        for i in range(len(curr_bboxes)):
            if visited[i]: continue
            
            # Start a new group
            group = [curr_bboxes[i]]
            visited[i] = True
            
            for j in range(i + 1, len(curr_bboxes)):
                if visited[j]: continue
                
                # Check distance between box i and j
                # boxes: [x, y, w, h]
                b1 = curr_bboxes[i]
                b2 = curr_bboxes[j]
                
                # Check if they are close (horizontal or vertical distance)
                # Expand box 1 by threshold and check overlap with box 2
                x_overlap = not (b1[0] + b1[2] + dist_threshold < b2[0] or b2[0] + b2[2] + dist_threshold < b1[0])
                y_overlap = not (b1[1] + b1[3] + dist_threshold < b2[1] or b2[1] + b2[3] + dist_threshold < b1[1])
                
                if x_overlap and y_overlap:
                    group.append(curr_bboxes[j])
                    visited[j] = True
                    changed = True
            
            # Merge the group into one bbox
            if len(group) == 1:
                new_bboxes.append(group[0])
            else:
                x_min = min(b[0] for b in group)
                y_min = min(b[1] for b in group)
                x_max = max(b[0] + b[2] for b in group)
                y_max = max(b[1] + b[3] for b in group)
                new_bboxes.append([x_min, y_min, x_max - x_min, y_max - y_min])
        
        curr_bboxes = new_bboxes
        
    return [tuple(b) for b in curr_bboxes]

# Step 2 : caculate the bounding box for each leanbot
def detect_leanbot(frame, aligner, board_mask, threshold=50, min_area=500, max_area=100000,
                   min_width=20, max_width=600, min_height=20, max_height=600, merge_dist=20):
    # get the board mask ROI
    frame_masked = cv2.bitwise_and(frame, frame, mask=board_mask)

    try:
        result = aligner.align(frame_masked)
        # 1. Lấy ảnh xám từ kết quả để tính diff (OpenCV yêu cầu cùng số kênh)
        aligned_gray = result['aligned']
        
        # 2. Tạo ảnh màu để lưu và hiển thị
        warp_matrix = result['warp']
        h, w = frame.shape[:2]
        
        if aligner.motion_type == cv2.MOTION_HOMOGRAPHY:
            # Warp trên ảnh GỐC (frame) để giữ bối cảnh xung quanh, không dùng frame_masked ở đây
            aligned_color = cv2.warpPerspective(frame, warp_matrix, (w, h),
                                        flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                                        borderMode=cv2.BORDER_REPLICATE)
        else:
            aligned_color = cv2.warpAffine(frame, warp_matrix, (w, h),
                                   flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                                   borderMode=cv2.BORDER_REPLICATE)
    except Exception as e:
        print(f"Error aligning image: {e}")
        return None, [], None
    
    # 2. Tiền xử lý để giảm nhiễu ánh sáng (Làm mịn ảnh)
    bg_blurred = cv2.GaussianBlur(aligner.template_gray, (5, 5), 0)
    aligned_blurred = cv2.GaussianBlur(aligned_gray, (5, 5), 0)

    # 3. Tính sự khác biệt (Trừ nền) - DÙNG ẢNH ĐÃ LÀM MỊN
    _, diff_mask, _, _ = aligner.compute_diff(bg_blurred, aligned_blurred, threshold=threshold)
    
    # 4. Xử lý hình thái học để "quét nhiễu" và "hàn" vật thể
    kernel_small = np.ones((3, 3), np.uint8)
    kernel_large = np.ones((25, 25), np.uint8) # Tăng lên 25 để nối các mảnh ở xa nhau
    
    # Bước A: MORPH_OPEN để xóa nhiễu li ti
    diff_mask = cv2.morphologyEx(diff_mask, cv2.MORPH_OPEN, kernel_small)
    
    # Bước B: DILATE (Nở) để các bộ phận Leanbot "phình" ra và chạm vào nhau
    diff_mask = cv2.dilate(diff_mask, np.ones((5, 5), np.uint8), iterations=1)
    
    # Bước C: MORPH_CLOSE để lấp các hố sâu và hàn gắn các mảnh đã chạm nhau
    diff_mask = cv2.morphologyEx(diff_mask, cv2.MORPH_CLOSE, kernel_large)
    
    # Bước D: Điền đầy (Fill holes) các contour kín
    cnts, _ = cv2.findContours(diff_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for c in cnts:
        cv2.drawContours(diff_mask, [c], -1, 255, thickness=-1)
    
    diff_mask = cv2.dilate(diff_mask, np.ones((3, 3), np.uint8), iterations=1)
    
    diff_mask = cv2.bitwise_and(diff_mask, diff_mask, mask=board_mask)

    # 4. Tìm các đường bao (Contours)
    contours, _ = cv2.findContours(diff_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # 5. Lấp đầy các lỗ hổng bên trong vật thể (Fill Holes)
    # Ta vẽ đè các contour đã tìm được với độ dày = -1 (tô đặc)
    mask_filled = np.zeros_like(diff_mask)
    cv2.drawContours(mask_filled, contours, -1, 255, thickness=-1)
    
    # Tìm lại contour trên mask đã được lấp đầy
    contours, _ = cv2.findContours(mask_filled, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    bboxes = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        
        # A. Lọc theo diện tích
        if min_area < area < max_area:
            x, y, w, h = cv2.boundingRect(cnt)
            
            # B. Lọc theo KÍCH THƯỚC CHIỀU RỘNG/CAO (Thay thế Aspect Ratio)
            if (min_width < w < max_width) and (min_height < h < max_height):
                bboxes.append((x, y, w, h))
    
    # C. GỘP CÁC BOX CẠNH NHAU (Để xử lý vật thể bị chia cắt)
    merged_bboxes = merge_bboxes(bboxes, dist_threshold=merge_dist)
            
    return aligned_color, merged_bboxes, diff_mask

def save_yolo_label(bboxes, img_width, img_height, output_path, class_id=0):
    """Saves bounding boxes in YOLO format: <class_id> <x_center> <y_center> <width> <height>"""
    with open(output_path, "w") as f:
        for (x, y, w, h) in bboxes:
            # Calculate normalized YOLO format
            x_center = (x + w / 2) / img_width
            y_center = (y + h / 2) / img_height
            w_norm = w / img_width
            h_norm = h / img_height
            
            f.write(f"{class_id} {x_center:.6f} {y_center:.6f} {w_norm:.6f} {h_norm:.6f}\n")
    

def main():
    cap = None # Khởi tạo để tránh lỗi UnboundLocalError
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="0", help="Camera source")
    parser.add_argument("--mode", choices=["capture", "relabel"], default="capture", help="Processing mode")
    parser.add_argument("--reuse", action="store_true", help="Reuse config from the latest session")
    parser.add_argument("--threshold", type=int, default=100, help="Brightness difference threshold (default 50)")
    parser.add_argument("--min_area", type=int, default=1000, help="Min contour area (default 500)")
    parser.add_argument("--max_area", type=int, default=100000, help="Max contour area (default 100000)")
    parser.add_argument("--min_width", type=int, default=40, help="Min bbox width (default 20)")
    parser.add_argument("--max_width", type=int, default=600, help="Max bbox width (default 600)")
    parser.add_argument("--min_height", type=int, default=40, help="Min bbox height (default 20)")
    parser.add_argument("--max_height", type=int, default=600, help="Max bbox height (default 600)")
    parser.add_argument("--merge_dist", type=int, default=40, help="Distance to merge nearby bboxes (default 20)")
    parser.add_argument("--class_id", type=int, default=0, help="Default class ID for labeling")
    args = parser.parse_args()

    # Đảm bảo thư mục gốc tồn tại
    DATASETS_DIR.mkdir(parents=True, exist_ok=True)
    (DATASETS_DIR / "images").mkdir(parents=True, exist_ok=True)
    (DATASETS_DIR / "labels").mkdir(parents=True, exist_ok=True)
    SESSIONS_ROOT.mkdir(parents=True, exist_ok=True)

    # --- BƯỚC 1: XÁC ĐỊNH SESSION ---
    if args.mode == "capture":
        # Tạo session mới khi chụp
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        current_session_dir = SESSIONS_ROOT / session_id
        config_dir = current_session_dir / "config"
        raw_dir = current_session_dir / "raw_images"
        config_dir.mkdir(parents=True, exist_ok=True)
        raw_dir.mkdir(parents=True, exist_ok=True)
        
        bg_frame, pts = None, None
        
        # LOGIC REUSE: Tìm session gần nhất
        if args.reuse:
            all_sessions = sorted([d for d in SESSIONS_ROOT.iterdir() if d.is_dir()], reverse=True)
            for s_dir in all_sessions:
                old_bg, old_pts = load_config(s_dir / "config")
                if old_bg is not None:
                    bg_frame, pts = old_bg, old_pts
                    save_config(bg_frame, pts, config_dir)
                    print(f"[REUSE] Đã lấy cấu hình từ session cũ: {s_dir.name}")
                    break
        
        print(f"\n[NEW SESSION] Khởi tạo phiên làm việc: {session_id}")
        
        # Nếu không có bg_frame (không reuse hoặc reuse thất bại), tiến hành chụp mới
        if bg_frame is None:
            cap = setup_camera(parse_source(args.source))
            bg_frame = capture_background(cap, WIDTH, HEIGHT)
            if bg_frame is None: return
            aligner_obj, mask_obj, pts = get_board_mask(bg_frame)
            save_config(bg_frame, pts, config_dir)
            aligner, mask = aligner_obj, mask_obj
        else:
            # Khởi tạo aligner từ config đã reuse
            board_mask = build_mask(bg_frame.shape, pts)
            bg_masked = cv2.bitwise_and(bg_frame, bg_frame, mask=board_mask)
            aligner = ImageAligner()
            aligner.set_template(bg_masked)
            mask = board_mask

        if cap is None:
            cap = setup_camera(parse_source(args.source))

        # --- BƯỚC 2: CHỤP LOẠT (CAPTURE MODE) ---
        captured_frames = []
        print("\n--- CHẾ ĐỘ CHỤP LOẠT (CAPTURE MODE) ---")
        print("Nhấn 'c' để lưu ảnh thô vào Session.")
        print("Nhấn 's' để DỪNG CHỤP và bắt đầu TẦP HỢP DATASET.")
        
        while True:
            ret, frame = cap.read()
            if not ret: break
            preview = cv2.resize(frame, (PREVIEW_WIDTH, PREVIEW_HEIGHT))
            cv2.putText(preview, f"Session: {session_id} | Raw: {len(captured_frames)}", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.imshow(WINDOW_NAME, preview)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('c'):
                idx = len(captured_frames)
                img_name = f"raw_{idx:03d}.jpg"
                cv2.imwrite(str(raw_dir / img_name), frame)
                captured_frames.append(frame.copy())
                print(f"[INFO] Đã lưu {img_name}")
            elif key == ord('s'):
                break
            elif key == ord('q'):
                if cap: cap.release()
                cv2.destroyAllWindows()
                return
        
        # Sau khi chụp xong, xử lý ngay Session này
        sessions_to_process = [(current_session_dir, captured_frames)]
        
    else:
        # CHẾ ĐỘ RELABEL: Quét tất cả các Session có sẵn
        print("\n--- CHẾ ĐỘ RELABEL (MULTI-SESSION MODE) ---")
        sessions_to_process = []
        for s_dir in SESSIONS_ROOT.iterdir():
            if s_dir.is_dir() and (s_dir / "config" / "background.jpg").exists():
                raw_imgs = []
                raw_dir = s_dir / "raw_images"
                if raw_dir.exists():
                    for img_p in raw_dir.glob("*.jpg"):
                        img = cv2.imread(str(img_p))
                        if img is not None: raw_imgs.append(img)
                
                if raw_imgs:
                    sessions_to_process.append((s_dir, raw_imgs))
        
        print(f"[INFO] Tìm thấy {len(sessions_to_process)} session có dữ liệu thô.")

    # --- BƯỚC 3: XỬ LÝ VÀ ĐẨY VÀO DATASETS ---
    for session_dir, frames in sessions_to_process:
        s_id = session_dir.name
        print(f"\n>>> Đang xử lý {s_id} ({len(frames)} ảnh)...")
        
        # Load đúng config của session này
        bg_f, bg_pts = load_config(session_dir / "config")
        board_mask = build_mask(bg_f.shape, bg_pts)
        bg_masked = cv2.bitwise_and(bg_f, bg_f, mask=board_mask)
        s_aligner = ImageAligner()
        s_aligner.set_template(bg_masked)
        
        for i, frame in enumerate(frames):
            aligned_img, bboxes, diff_mask = detect_leanbot(
                frame, s_aligner, board_mask, 
                threshold=args.threshold, 
                min_area=args.min_area, 
                max_area=args.max_area,
                min_width=args.min_width,
                max_width=args.max_width,
                min_height=args.min_height,
                max_height=args.max_height,
                merge_dist=args.merge_dist
            )
            
            # Preview debug (Luôn hiển thị để quan sát tại sao không bắt được)
            vis_bbox = aligned_img.copy()
            for (x, y, w, h) in bboxes:
                cv2.rectangle(vis_bbox, (x, y), (x + w, y + h), (0, 255, 0), 3)
            
            cv2.imshow("3. Difference Mask", cv2.resize(diff_mask, (PREVIEW_WIDTH, PREVIEW_HEIGHT)))
            cv2.imshow("4. Bounding Box Result", cv2.resize(vis_bbox, (PREVIEW_WIDTH, PREVIEW_HEIGHT)))
            cv2.waitKey(200) # Đợi 0.2s mỗi ảnh để quan sát

            if bboxes:
                # Lưu vào Datasets dùng chung
                base_name = f"{s_id}_img_{i:03d}"
                img_path = DATASETS_DIR / "images" / f"{base_name}.jpg"
                lbl_path = DATASETS_DIR / "labels" / f"{base_name}.txt"

                cv2.imwrite(str(img_path), aligned_img)
                save_yolo_label(bboxes, WIDTH, HEIGHT, str(lbl_path), class_id=args.class_id)
                print(f"   [OK] {base_name}: {len(bboxes)} Leanbot")
            else:
                print(f"   [SKIP] {s_id}_img_{i:03d}: Không có vật thể nào thỏa mãn bộ lọc (Width/Height/Area).")

    print("\n[FINISH] Đã cập nhật toàn bộ Dataset từ các Session!")
    cv2.waitKey(0)

    if cap is not None:
        cap.release()
    cv2.destroyAllWindows()

if __name__== "__main__":
    main()

    
