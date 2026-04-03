"""
=============================================================
BƯỚC 3: ÁP DỤNG CALIBRATION CHO SA BÀN CỜ 1.2m × 1.2m
============================================================
Nội dung : 
1. Tải kết quả calibration
2. Mở camera, khử méo realtime
3. Chọn 4 góc sa bàn cờ bằng Click chuột
4. Tạo perspective transform: pixel -> tọa độ thực (mm)
5. Click vào bất kỳ điểm nào trên sa bàn -> hiển thị tọa độ thực

Công dụng: Xác định tọa độ 4 góc của Sa bàn và các điểm trên sa bàn
"""

import cv2
import numpy as np
import os

# ======================== CẤU HÌNH ========================
CAMERA_INDEX = 1
CAMERA_WIDTH = 1920
CAMERA_HEIGHT = 1080
CALIBRATION_FILE = "calibration_result.npz"
BOARD_SIZE_MM = 1200  # Sa bàn cờ 1.2m = 1200mm
# ===========================================================

# Biến toàn cục
clicked_points = []
transform_matrix = None
undist_frame = None


def mouse_callback(event, x, y, flags, param):
    """Xử lý click chuột"""
    global clicked_points, transform_matrix, undist_frame

    if event == cv2.EVENT_LBUTTONDOWN:
        if len(clicked_points) < 4:
            # Đang chọn 4 góc sa bàn
            clicked_points.append((x, y))
            print(f"  Góc {len(clicked_points)}: ({x}, {y})")

            if len(clicked_points) == 4:
                # Tính perspective transform
                src = np.float32(clicked_points)
                dst = np.float32([
                    [0, 0],
                    [BOARD_SIZE_MM, 0],
                    [BOARD_SIZE_MM, BOARD_SIZE_MM],
                    [0, BOARD_SIZE_MM]
                ])
                transform_matrix = cv2.getPerspectiveTransform(src, dst)
                print("\n[INFOR] Đã tạo Perspective Transform!")
                print(" -> Click vào bất kỳ điểm nào trên sa bàn để xem tọa độ thực")
                print(" -> Nhấn 'r' để chọn lại 4 góc")

        elif transform_matrix is not None:
            # Đã có transform → tính tọa độ thực
            pixel_pt = np.float32([[[x, y]]])
            real_pt = cv2.perspectiveTransform(pixel_pt, transform_matrix)
            real_x = real_pt[0][0][0]
            real_y = real_pt[0][0][1]
            print(f"  Pixel ({x}, {y}) → Thực ({real_x:.1f} mm, {real_y:.1f} mm) "
                  f"= ({real_x/10:.1f} cm, {real_y/10:.1f} cm)")


def main():
    global clicked_points, transform_matrix, undist_frame

    # Kiểm tra file calibration
    if not os.path.exists(CALIBRATION_FILE):
        print(f"[ERROR] Không tìm thấy {CALIBRATION_FILE}")
        print("  -> Chạy calibrate_camera.py trước!")
        return

    # Đọc kết quả calibration
    data = np.load(CALIBRATION_FILE, allow_pickle=True)
    camera_matrix = data["camera_matrix"]
    dist_coeffs = data["dist_coeffs"]

    print("=" * 60)
    print("  ÁP DỤNG CALIBRATION LÊN SA BÀN CỜ")
    print("=" * 60)
    print(f"\n[INFO] Camera Matrix:")
    print(camera_matrix)
    print(f"\n[INFO] Distortion Coefficients:")
    print(dist_coeffs)

    # Mở camera
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print(f"[ERROR] Không mở được camera index {CAMERA_INDEX}")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Tính ma trận camera tối ưu cho undistort
    new_camera_matrix, roi = cv2.getOptimalNewCameraMatrix(
        camera_matrix, dist_coeffs, (actual_w, actual_h), 1, (actual_w, actual_h)
    )

    # Tính map một lần (nhanh hơn undistort mỗi frame)
    map1, map2 = cv2.initUndistortRectifyMap(
        camera_matrix, dist_coeffs, None, new_camera_matrix,
        (actual_w, actual_h), cv2.CV_16SC2
    )

    print(f"\n[INFO] Camera: {actual_w}x{actual_h}")
    print(f"[INFO] Sa bàn: {BOARD_SIZE_MM}mm × {BOARD_SIZE_MM}mm")

    window_name = "Sa Ban Co - Undistorted"
    cv2.namedWindow(window_name)
    cv2.setMouseCallback(window_name, mouse_callback)

    print("\n" + "=" * 50)
    print("  HƯỚNG DẪN:")
    print("  1. Click chọn 4 GÓC sa bàn (theo thứ tự):")
    print("     Góc 1: Trên-Trái")
    print("     Góc 2: Trên-Phải")
    print("     Góc 3: Dưới-Phải")
    print("     Góc 4: Dưới-Trái")
    print("  2. Sau đó click bất kỳ điểm nào -> xem tọa độ thực")
    print("  3. Nhấn 'r' để chọn lại")
    print("  4. Nhấn 'q' để thoát")
    print("=" * 50)
    print("\n-> Click chọn GÓC 1 (Trên-Trái) của sa bàn:")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Khử méo
        undist_frame = cv2.remap(frame, map1, map2, cv2.INTER_LINEAR)

        display = undist_frame.copy()

        # Vẽ các điểm đã chọn
        for i, pt in enumerate(clicked_points):
            cv2.circle(display, pt, 8, (0, 255, 0), -1)
            cv2.putText(display, f"G{i+1}", (pt[0]+10, pt[1]-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Vẽ đường nối nếu đã chọn >= 2 điểm
        if len(clicked_points) >= 2:
            for i in range(len(clicked_points) - 1):
                cv2.line(display, clicked_points[i], clicked_points[i+1],
                         (0, 255, 255), 2)
            if len(clicked_points) == 4:
                cv2.line(display, clicked_points[3], clicked_points[0],
                         (0, 255, 255), 2)

        # Hiển thị trạng thái
        if len(clicked_points) < 4:
            status = f"Chon goc {len(clicked_points)+1}/4"
            color = (0, 0, 255)
        else:
            status = "READY! Click de xem toa do thuc (mm)"
            color = (0, 255, 0)

        cv2.putText(display, status, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        cv2.putText(display, "UNDISTORTED", (10, actual_h - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

        # Resize nếu quá lớn
        h, w = display.shape[:2]
        if w > 1280:
            scale = 1280 / w
            display = cv2.resize(display, (int(w * scale), int(h * scale)))

        cv2.imshow(window_name, display)

        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):
            break
        elif key == ord('r'):
            # Reset
            clicked_points = []
            transform_matrix = None
            print("\n[INFO] Đã reset. Click chọn lại 4 góc sa bàn.")
            print("-> Click chọn GÓC 1 (Trên-Trái):")

    cap.release()
    cv2.destroyAllWindows()
    print("\n[INFO] Đã thoát.")


if __name__ == "__main__":
    main()
