import os
import cv2
import numpy as np
import glob

def main():
    base_dir = r"d:\PTIT\DTT\Nguyen_Huu_Hoang_Anh\260508"
    tool1_output_dir = os.path.join(base_dir, "tool1_output")
    
    crop_images_dir = os.path.join(base_dir, "crop_images")
    os.makedirs(crop_images_dir, exist_ok=True)
    
    if not os.path.exists(tool1_output_dir):
        print(f"Directory not found: {tool1_output_dir}")
        return

    for session_folder in os.listdir(tool1_output_dir):
        session_path = os.path.join(tool1_output_dir, session_folder)
        
        if not os.path.isdir(session_path) or not session_folder.startswith('session_'):
            continue
            
        print(f"\nProcessing session: {session_folder}")
        
        config_path = os.path.join(session_path, 'config.npy')
        aligned_images_dir = os.path.join(session_path, 'aligned_images')
        labels_dir = os.path.join(session_path, 'labels')
        
        if not os.path.exists(config_path):
            print(f"  -> Skipping, config.npy not found")
            continue
            
        if not os.path.exists(aligned_images_dir):
            print(f"  -> Skipping, aligned_images not found")
            continue
            
        try:
            config = np.load(config_path, allow_pickle=True).item()
        except Exception as e:
            print(f"  -> Error reading config.npy: {e}")
            continue
            
        roi_points = config.get('roi_points')
        if not roi_points or len(roi_points) == 0:
            print(f"  -> Skipping, no roi_points in config")
            continue
            
        pts = np.array(roi_points, dtype=np.int32)
        x, y, w, h = cv2.boundingRect(pts)
        
        print(f"  -> Found Bounding Box (x={x}, y={y}, w={w}, h={h}) from roi_points")
        
        session_crop_dir = os.path.join(crop_images_dir, session_folder)
        session_images_dir = os.path.join(session_crop_dir, "aligned_images")
        session_labels_dir = os.path.join(session_crop_dir, "labels")
        
        os.makedirs(session_crop_dir, exist_ok=True)
        os.makedirs(session_images_dir, exist_ok=True)
        os.makedirs(session_labels_dir, exist_ok=True)
        
        image_files = glob.glob(os.path.join(aligned_images_dir, "*.*"))
        image_count = 0
        
        for img_path in image_files:
            if not img_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                continue
                
            img = cv2.imread(img_path)
            if img is None:
                continue
                
            img_h, img_w = img.shape[:2]
            
            # Ensure crop box is within image bounds
            y1, y2 = max(0, y), min(img_h, y + h)
            x1, x2 = max(0, x), min(img_w, x + w)
            
            crop_w = x2 - x1
            crop_h = y2 - y1
            
            if crop_w <= 0 or crop_h <= 0:
                continue
                
            cropped_img = img[y1:y2, x1:x2]
            
            # Resize image to 640x640
            resized_img = cv2.resize(cropped_img, (640, 640))
            
            img_filename = os.path.basename(img_path)
            save_path = os.path.join(session_images_dir, img_filename)
            cv2.imwrite(save_path, resized_img)
            
            # Process label if exists
            base_name = os.path.splitext(img_filename)[0]
            label_path = os.path.join(labels_dir, base_name + ".txt")
            new_label_lines = []
            
            if os.path.exists(label_path):
                with open(label_path, "r") as lf:
                    lines = lf.readlines()
                    
                for line in lines:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        class_id = parts[0]
                        cx_norm, cy_norm = float(parts[1]), float(parts[2])
                        bw_norm, bh_norm = float(parts[3]), float(parts[4])
                        
                        # Convert to absolute coordinates of original image
                        abs_cx = cx_norm * img_w
                        abs_cy = cy_norm * img_h
                        abs_bw = bw_norm * img_w
                        abs_bh = bh_norm * img_h
                        
                        # Find absolute top-left and bottom-right
                        box_x1 = abs_cx - abs_bw / 2
                        box_y1 = abs_cy - abs_bh / 2
                        box_x2 = abs_cx + abs_bw / 2
                        box_y2 = abs_cy + abs_bh / 2
                        
                        # Map to cropped image coordinates
                        new_x1 = box_x1 - x1
                        new_y1 = box_y1 - y1
                        new_x2 = box_x2 - x1
                        new_y2 = box_y2 - y1
                        
                        # Clip bounding box to cropped image boundaries
                        new_x1 = max(0, new_x1)
                        new_y1 = max(0, new_y1)
                        new_x2 = min(crop_w, new_x2)
                        new_y2 = min(crop_h, new_y2)
                        
                        # Calculate new width and height
                        new_bw = new_x2 - new_x1
                        new_bh = new_y2 - new_y1
                        
                        # Only keep box if it has a positive area
                        if new_bw > 0 and new_bh > 0:
                            new_cx = new_x1 + new_bw / 2
                            new_cy = new_y1 + new_bh / 2
                            
                            # Normalize by cropped image dimensions
                            # Since resize to 640x640 doesn't change aspect ratio of the bounding boxes relatively,
                            # these normalized coordinates remain valid for the resized 640x640 image!
                            out_cx = new_cx / crop_w
                            out_cy = new_cy / crop_h
                            out_bw = new_bw / crop_w
                            out_bh = new_bh / crop_h
                            
                            new_label_lines.append(f"{class_id} {out_cx:.6f} {out_cy:.6f} {out_bw:.6f} {out_bh:.6f}\n")
                            
            # Save new label file
            if new_label_lines:
                new_label_path = os.path.join(session_labels_dir, base_name + ".txt")
                with open(new_label_path, "w") as out_lf:
                    out_lf.writelines(new_label_lines)
                    
            image_count += 1
            
        print(f"  -> Cropped, resized to 640x640, adjusted labels, and saved {image_count} images to {session_crop_dir}")

    print("\nCropping and label adjustment process completed!")

if __name__ == "__main__":
    main()
