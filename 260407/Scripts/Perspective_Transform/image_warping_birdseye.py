"""
Chụp mặt phẳng bị nghiêng (hình thang) và dựa vào 4 góc để kéo dãn
lại bức ảnh thành dạng nhìn từ trên xuống
Cách dùng scripts :
1. Chạy code, màn hình camera sẽ hiện lên.
2. Dùng chuột click chọn 4 đỉnh của hình thang cần kéo phẳng theo MỌI THỨ TỰ.
   (Tool sẽ tự động gom viền (sắp xếp lại toạ độ) một cách thông minh, tuy nhiên
    khuyến khích chọn theo thứ tự chuẩn: Trái-Trên, Phải-Trên, Phải-Dưới, Trái-Dưới).
3. Sau khi chọn 4 điểm, cửa sổ Warp sẽ mở ra.
4. Nhấn phím 'r' để reset. Nhấn 'q' để thoát.
"""

import cv2
import numpy as np
import os

# Kích thước khung hình Output mong muốn (ví dụ 600x800 cho khung giấy A4, hoặc vuông 600x600)
WARP_WIDTH = 600
WARP_HEIGHT = 600

clicked_points = []
transform_matrix = None

def sort_pts(pts):
    """ Hàm phụ trợ để tự động sắp xếp 4 điểm thành thứ tự: TL, TR, BR, BL """
    pts = np.array(pts)
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)] # Top-Left
    rect[2] = pts[np.argmax(s)] # Bottom-Right
    
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)] # Top-Right
    rect[3] = pts[np.argmax(diff)] # Bottom-Left
    
    return rect

def mouse_callback(event, x, y, flags, param):
    global clicked_points, transform_matrix
    
    # Bắt sự kiện click chuột trái
    if event == cv2.EVENT_LBUTTONDOWN:
        if len(clicked_points) < 4:
            clicked_points.append((x, y))
            print(f"-> Đã chọn điểm {len(clicked_points)}: ({x}, {y})")
            
            # Đủ 4 điểm thì bắt đầu kéo giãn
            if len(clicked_points) == 4:
                # Sắp xếp các điểm thành [Top-Left, Top-Right, Bottom-Right, Bottom-Left]
                src_rect = sort_pts(clicked_points)
                print("\n[INFO] Tính toán ma trận biến đổi...")
                
                # Định nghĩa 4 góc của ảnh đích (hình chữ nhật hoàn hảo)
                dst_rect = np.float32([
                    [0, 0],
                    [WARP_WIDTH, 0],
                    [WARP_WIDTH, WARP_HEIGHT],
                    [0, WARP_HEIGHT]
                ])
                
                # Hàm siêu nhân OpenCV để giải Homography Matrix (Perspective Transform)
                transform_matrix = cv2.getPerspectiveTransform(src_rect, dst_rect)
                print("[SUCCESS] Đã tạo Perspective Transform!")
                print(" -> Xem cửa sổ 'Warped Image' để thấy phép thuật Image Warping.")
                print(" -> Nhấn 'r' nếu muốn reset và chọn vùng khác.")

def main():
    global clicked_points, transform_matrix
    
    # Thử mở camera 1 trước, nếu không được mở camera 0
    cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("[ERROR] Không thể mở bất kỳ Camera nào!")
            return

    # ÉP OPENCV MỞ CAMERA Ở ĐỘ PHÂN GIẢI CAO NHẤT (2K - 2560x1440)
    # LƯU Ý: Đảm bảo bạn đã chạy lại file Calibrate bằng độ phân giải 2K 
    # để thư mục xuất ra file calibration_result.npz mới khớp với cấu hình này.
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 2560)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1440)

    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"[INFO] Camera đang chạy ở độ phân giải: {actual_w}x{actual_h}")

    # ================= TÍNH BẢN ĐỒ KHỬ MÉO =================
    CALIBRATION_FILE = "calibration_result.npz"
    map1, map2 = None, None

    if os.path.exists(CALIBRATION_FILE):
        print(f"[INFO] Đã tìm thấy {CALIBRATION_FILE}, đang nạp ma trận kính...")
        data = np.load(CALIBRATION_FILE, allow_pickle=True)
        camera_matrix = data["camera_matrix"]
        dist_coeffs = data["dist_coeffs"]
        
        new_camera_matrix, roi = cv2.getOptimalNewCameraMatrix(
            camera_matrix, dist_coeffs, (actual_w, actual_h), 1, (actual_w, actual_h)
        )
        map1, map2 = cv2.initUndistortRectifyMap(
            camera_matrix, dist_coeffs, None, new_camera_matrix,
            (actual_w, actual_h), cv2.CV_16SC2
        )
        print("[SUCCESS] Đã sẵn sàng hệ thống lọc méo thấu kính (Undistort)!")
    else:
        print(f"\n[WARNING] Không tìm thấy {CALIBRATION_FILE}!")
        print(" -> Hãy chắc chắn đã chạy calibrate_camera.py trước đó.\n")
    # ==================================================================

    # Sử dụng WINDOW_NORMAL để có thể thu nhỏ cửa sổ giao diện hiển thị
    # Các thao tác click chuột OpenCV sẽ tự động quy đổi đúng về tọa độ ảnh gốc 2K
    cv2.namedWindow("Original Window", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Original Window", 1024, 576) # Thu nhỏ giao diện lại cho không choán màn hình
    cv2.setMouseCallback("Original Window", mouse_callback)

    print("="*50)
    print(" HƯỚNG DẪN IMAGE WARPING / BIRD'S EYE VIEW")
    print(" Click 4 góc của đa giác bạn muốn 'nắn' trên màn hình.")
    print("="*50)

    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        # === 1. KHỬ MÉO THẤU KÍNH ===
        # Bóp lại những đường lồi lõm của ống kính Camera góc rộng
        if map1 is not None and map2 is not None:
            frame = cv2.remap(frame, map1, map2, cv2.INTER_LINEAR)

        display = frame.copy()
        
        # Vẽ các điểm đã đánh dấu lên màn hình
        for i, pt in enumerate(clicked_points):
            cv2.circle(display, pt, 6, (0, 0, 255), -1)
            cv2.putText(display, str(i+1), (pt[0]+10, pt[1]-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
        # Nối dây vẽ lại cái khung hình thang do user chọn
        if len(clicked_points) > 1:
            for i in range(len(clicked_points) - 1):
                cv2.line(display, clicked_points[i], clicked_points[i+1], (0, 255, 255), 2)
            if len(clicked_points) == 4:
                # Vẽ nốt đường nối đỉnh cuối quay về đỉnh đầu
                cv2.line(display, clicked_points[3], clicked_points[0], (0, 255, 255), 2)

        # Nếu đã có ma trận Transform -> tiến hành bóp nắn Toàn Bộ Bức Ảnh
        if transform_matrix is not None:
            # Sử dụng cv2.warpPerspective lên toàn bộ cái "frame" camera hiện tại.
            warped_image = cv2.warpPerspective(frame, transform_matrix, (WARP_WIDTH, WARP_HEIGHT))
            cv2.imshow("Warped Image", warped_image)
        else:
            cv2.putText(display, f"Chon goc: {len(clicked_points)}/4", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        # Show cam chính
        cv2.imshow("Original Window", display)
        

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):    # Nhấn q thoát
            break
        elif key == ord('r'):  # Nhấn r reset
            clicked_points = []
            transform_matrix = None
            try:
                cv2.destroyWindow("Warped Image")
            except Exception:
                pass
            print("\n[INFO] Đã Reset, hãy click lại!")

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
