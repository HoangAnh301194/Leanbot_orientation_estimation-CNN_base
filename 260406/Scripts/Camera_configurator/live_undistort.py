import cv2
import numpy as np
import os

# ======================== CẤU HÌNH ========================
CAMERA_INDEX = 1
CAMERA_WIDTH = 1920
CAMERA_HEIGHT = 1080

# Đường dẫn trỏ tới file kết quả calibration đã làm ở bước trước
CALIB_FILE = r"D:\PTIT\DTT\Nguyen_Huu_Hoang_Anh\260403\Camera_Calibration\calibration_result.npz"

# THAM SỐ KHỬ MÉO (ALPHA)
# ALPHA = 0: Xén ảnh hoàn toàn để xóa viền đen (mất một chút góc nhìn ở cạnh)
# ALPHA = 1: Lấy toàn bộ góc nhìn (giữ hết viền, nhưng sẽ có các khoảng đen ở góc)
ALPHA = 1.0 
# ===========================================================

def main():
    print("=" * 60)
    print("  LIVE CAMERA UNDISTORTION CHECK")
    print("=" * 60)

    # 1. Kiểm tra và load file calibration
    if not os.path.exists(CALIB_FILE):
        print(f"[ERROR] Không tìm thấy file calibration tại: {CALIB_FILE}")
        print(" -> Hãy chắc chắn bạn đã chạy calibrate_camera.py thành công.")
        return

    data = np.load(CALIB_FILE)
    camera_matrix = data["camera_matrix"]
    dist_coeffs = data["dist_coeffs"]
    
    print("[INFO] Đã load thông số thấu kính thành công.")
    print(f"Mean Re-projection Error: {data.get('reprojection_error', 'N/A')}")

    # 2. Mở Camera
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print(f"[ERROR] Không thể mở camera index {CAMERA_INDEX}")
        return

    # Thiết lập độ phân giải
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"[INFO] Camera hoạt động tại: {actual_w}x{actual_h}")

    # 3. Tính toán Ma trận tối ưu và Map (để khử méo nhanh)
    # Sử dụng tham số ALPHA đã cấu hình ở trên
    new_camera_matrix, roi = cv2.getOptimalNewCameraMatrix(
        camera_matrix, dist_coeffs, (actual_w, actual_h), ALPHA, (actual_w, actual_h)
    )
    
    map1, map2 = cv2.initUndistortRectifyMap(
        camera_matrix, dist_coeffs, None, new_camera_matrix,
        (actual_w, actual_h), cv2.CV_16SC2
    )

    print("\n[INFO] Đang hiển thị 2 cửa sổ. Nhấn 'q' để thoát.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] Không đọc được frame từ camera.")
            break

        # Khử méo bằng remap
        undistorted = cv2.remap(frame, map1, map2, cv2.INTER_LINEAR)

        # Thêm nhãn chữ để phân biệt
        cv2.putText(frame, "ORIGINAL (MEO)", (30, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        cv2.putText(undistorted, "UNDISTORTED (THANG)", (30, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        # Resize nhẹ để hiển thị song song trên màn hình nếu cần
        # Ở đây ta hiển thị 2 cửa sổ riêng biệt với kích thước nhỏ hơn
        scale = 0.4
        display_w = int(actual_w * scale)
        display_h = int(actual_h * scale)

        cv2.imshow("1. Original Feed", cv2.resize(frame, (display_w, display_h)))
        cv2.imshow("2. Undistorted Feed", cv2.resize(undistorted, (display_w, display_h)))

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("[INFO] Đã đóng camera.")

if __name__ == "__main__":
    main()
