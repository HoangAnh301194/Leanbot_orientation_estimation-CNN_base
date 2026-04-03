"""
=============================================================
BƯỚC 1: CHỤP ẢNH CHECKERBOARD TỪ WEBCAM HIKVISION DS-U04
=============================================================
Nội dung :
1. Cắm camera DS-U04 vào máy tính qua USB
2. In tấm checkerboard 5x5 ô (4x4 inner corners), mỗi ô 30mm
3. Dán phẳng lên bìa cứng ( có thể mở hình ảnh trên máy tính và zoom bàn cờ sao cho đúng 30mm mỗi ô)
4. Chạy script này
5. Đưa checkerboard trước camera ở nhiều vị trí/góc khác nhau
6. Nhấn 'c' để chụp khi thấy corners được detect (vẽ màu)
7. Nhấn 'x' để xóa tất cả ảnh cũ trong thư mục nếu muốn chụp lại từ đầu
8. Nhấn 'q' để thoát sau khi đủ 15 ảnh trở lên, càng nhiều ảnh càng tốt

Camera index mặc định = 1 ( nếu không được thì đổi số index camera 0,1,2...)
"""

import cv2
import os

# ======================== CẤU HÌNH ========================
CAMERA_INDEX = 1          # Index webcam (thay đổi nếu cần: 0, 1, 2...)
CAMERA_WIDTH = 1920       # Độ phân giải ngang (DS-U04 hỗ trợ đến 2560)
CAMERA_HEIGHT = 1080      # Độ phân giải dọc (DS-U04 hỗ trợ đến 1440)
CHECKERBOARD = (4, 4)     # Số inner corners (columns, rows) = (số_ô_ngang-1, số_ô_dọc-1)
SAVE_DIR = "./calibration_images"   # Thư mục lưu ảnh
# ===========================================================

def main():
    # Tạo thư mục lưu ảnh nếu chưa có
    os.makedirs(SAVE_DIR, exist_ok=True)

    # Mở camera
    cap = cv2.VideoCapture(CAMERA_INDEX)

    if not cap.isOpened():
        print(f"[ERRO] Không mở được camera index {CAMERA_INDEX}")
        print(" Thử đổi CAMERA_INDEX = 0, 1, hoặc 2")
        return

    # Đặt độ phân giải
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

    # Kiểm tra độ phân giải thực tế
    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"[INFO] Camera mở thành công: {actual_w}x{actual_h}")
    print(f"[INFO] Checkerboard: {CHECKERBOARD[0]}x{CHECKERBOARD[1]} inner corners")
    print()
    print("=" * 50)
    print("  HƯỚNG DẪN:")
    print("  'c' = Chụp ảnh (khi thấy corners xanh lá)")
    print("  'x' = Xóa toàn bộ ảnh đã chụp (làm lại từ đầu)")
    print("  'q' = Thoát")
    print("  Cần chụp ít nhất 15 ảnh từ nhiều góc!")
    print("=" * 50)

    img_count = 0
    # Đếm ảnh đã có sẵn trong thư mục
    existing = [f for f in os.listdir(SAVE_DIR) if f.endswith('.jpg')]
    img_count = len(existing)
    if img_count > 0:
        print(f"[INFO] Đã có {img_count} ảnh trong {SAVE_DIR}")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] Không đọc được frame từ camera")
            break

        # Chuyển sang ảnh xám để detect corners
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Tìm corners trên checkerboard
        found, corners = cv2.findChessboardCorners(
            gray, CHECKERBOARD,
            cv2.CALIB_CB_ADAPTIVE_THRESH +
            cv2.CALIB_CB_FAST_CHECK +
            cv2.CALIB_CB_NORMALIZE_IMAGE
        )

        # Hiển thị frame
        display = frame.copy()

        if found:
            # Vẽ corners lên ảnh (xanh lá = OK)
            cv2.drawChessboardCorners(display, CHECKERBOARD, corners, found)
            status_text = "CHECKERBOARD DETECTED - Nhan 'c' de chup!"
            status_color = (0, 255, 0)  # Xanh lá
        else:
            status_text = "Dang tim checkerboard..."
            status_color = (0, 0, 255)  # Đỏ

        # Hiển thị trạng thái
        cv2.putText(display, status_text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
        cv2.putText(display, f"So anh da chup: {img_count}",
                    (10, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

        # Resize để hiển thị vừa màn hình nếu ảnh quá lớn
        h, w = display.shape[:2]
        if w > 1280:
            scale = 1280 / w
            display = cv2.resize(display, (int(w * scale), int(h * scale)))

        cv2.imshow("Capture Calibration Images", display)

        key = cv2.waitKey(1) & 0xFF

        if key == ord('c') and found:
            # Lưu ảnh gốc (không vẽ corners)
            img_count += 1
            filename = os.path.join(SAVE_DIR, f"calib_{img_count:03d}.jpg")
            cv2.imwrite(filename, frame)
            print(f"Đã lưu ảnh {img_count}: {filename}")

        elif key == ord('x'):
            # Xóa toàn bộ ảnh
            for f in os.listdir(SAVE_DIR):
                if f.endswith('.jpg'):
                    os.remove(os.path.join(SAVE_DIR, f))
            img_count = 0
            print(f"\n[WARNING] Đã xóa toàn bộ ảnh cũ. Hãy chụp lại từ đầu!")

        elif key == ord('q'):
            print(f"\n[INFO] Thoát. Tổng cộng {img_count} ảnh trong {SAVE_DIR}")
            break

    cap.release()
    cv2.destroyAllWindows()

    if img_count < 15:
        print(f"\n[WARNING] Chỉ có {img_count} ảnh. Nên chụp ít nhất 15 ảnh!")
    else:
        print(f"\n[SUCCSESS] Đủ ảnh! Chạy 'calibrate_camera.py' để thực hiện calibration.")


if __name__ == "__main__":
    main()
