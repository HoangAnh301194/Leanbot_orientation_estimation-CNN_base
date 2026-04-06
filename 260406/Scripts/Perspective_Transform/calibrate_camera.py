"""
=============================================================
BƯỚC 2: CALIBRATE CAMERA TỪ ẢNH ĐÃ CHỤP
=============================================================
Nội dung :
1. Đảm bảo đã chụp đủ 15 trở lên số ảnh bằng capture_calibration_images.py
2. Chạy script này để tính toán ma trận thấu kính
3. Kết quả tham số sẽ được lưu vào calibration_result.npz 
4. Hệ thống sẽ tự tạo thư mục comparison_results và lưu lại cặp ảnh gốc/khử méo để so sánh

Kết quả bao gồm:
- Camera Matrix (K): ma trận nội tham số
- Distortion Coefficients: hệ số méo ống kính
- Rotation vectors (rvecs): vector quay cho mỗi ảnh
- Translation vectors (tvecs): vector tịnh tiến cho mỗi ảnh
- Re-projection Error: sai số chiếu lại (càng nhỏ càng tốt, tối đa <= 0.5)
"""

import cv2
import numpy as np
import os
import glob

# ======================== CẤU HÌNH ========================
CHECKERBOARD = (4, 4)     # Số inner corners (phải giống file capture)
SQUARE_SIZE = 30.0        # Kích thước mỗi ô vuông (mm). ĐO LẠI bằng thước!
IMAGE_DIR = "./calibration_images"   # Thư mục chứa ảnh đã chụp
OUTPUT_FILE = "calibration_result.npz"  # File lưu kết quả
# ===========================================================


def main():
    print("=" * 60)
    print("  CAMERA CALIBRATION - Hikvision DS-U04")
    print("=" * 60)

    # -------- BƯỚC 1: Tạo tọa độ 3D thực (Object Points) --------
    # Mỗi corner có tọa độ (X*SQUARE_SIZE, Y*SQUARE_SIZE, 0)
    objp = np.zeros((CHECKERBOARD[0] * CHECKERBOARD[1], 3), np.float32)
    objp[:, :2] = np.mgrid[0:CHECKERBOARD[0], 0:CHECKERBOARD[1]].T.reshape(-1, 2)
    objp *= SQUARE_SIZE  # Scale theo kích thước ô thực tế (mm)

    # Danh sách lưu points cho tất cả ảnh
    objpoints = []  # 3D points (giống nhau cho mọi ảnh)
    imgpoints = []  # 2D points (khác nhau tùy ảnh)

    # Tiêu chí dừng cho cornerSubPix
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

    # -------- BƯỚC 2: Đọc và xử lý từng ảnh --------
    images = sorted(glob.glob(os.path.join(IMAGE_DIR, "*.jpg")))

    if len(images) == 0:
        print(f"[ERROR] Không tìm thấy ảnh trong {IMAGE_DIR}")
        print(" -> Chạy capture_calibration_images.py trước!")
        return

    print(f"\n[INFO] Tìm thấy {len(images)} ảnh trong {IMAGE_DIR}")
    print("[INFO] Đang xử lý...\n")

    img_shape = None
    success_count = 0

    for i, fname in enumerate(images):
        img = cv2.imread(fname)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        img_shape = gray.shape[::-1]  # (width, height)

        # Tìm corners
        ret, corners = cv2.findChessboardCorners(
            gray, CHECKERBOARD,
            cv2.CALIB_CB_ADAPTIVE_THRESH +
            cv2.CALIB_CB_FAST_CHECK +
            cv2.CALIB_CB_NORMALIZE_IMAGE
        )

        if ret:
            success_count += 1
            objpoints.append(objp)

            # Tinh chỉnh corners với độ chính xác sub-pixel
            corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
            imgpoints.append(corners2)

            # Hiển thị corners (tùy chọn)
            display = img.copy()
            cv2.drawChessboardCorners(display, CHECKERBOARD, corners2, ret)

            # Resize để hiển thị
            h, w = display.shape[:2]
            if w > 960:
                scale = 960 / w
                display = cv2.resize(display, (int(w * scale), int(h * scale)))

            cv2.imshow("Corners Detected", display)
            cv2.waitKey(300)  # Hiện 300ms mỗi ảnh

            basename = os.path.basename(fname)
            print(f" [Done] {basename} — Corners detected ({success_count})")
        else:
            basename = os.path.basename(fname)
            print(f" [Error] {basename} — Không tìm thấy corners (bỏ qua)")

    cv2.destroyAllWindows()

    if success_count < 10:
        print(f"\n[ERROR] Chỉ detect được {success_count} ảnh. Nên có ít nhất 10!")
        if success_count < 3:
            print("[ERROR] Không đủ ảnh để calibrate. Chụp lại!")
            return

    # -------- BƯỚC 3: CALIBRATE --------
    print(f"\n[INFO] Calibrating với {success_count} ảnh...")
    print("[INFO] Đang tính toán... (có thể mất vài giây)\n")

    ret, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(
        objpoints, imgpoints, img_shape, None, None
    )

    # -------- BƯỚC 4: HIỂN THỊ KẾT QUẢ --------
    print("=" * 60)
    print("  KẾT QUẢ CALIBRATION")
    print("=" * 60)

    print(f"\n Re-projection Error: {ret:.4f} pixel")
    if ret < 0.5:
        print(f" Calibration thành công với sai số {ret:.4f} pixel.")
    elif ret < 1.0:
        print(f" Calibartion tương đối ở mức {ret:.4f} pixel.Cần chụp thêm các góc ảnh khác để tính toán lại")
    else:
        print(f" Calibration không thành công với sai số {ret:.4f} pixel.Cần chụp lại ảnh cẩn thận hơn.")

    print(f"\n Camera Matrix (K):")
    print(camera_matrix)
    print(f"\n  fx = {camera_matrix[0, 0]:.2f} pixel")
    print(f"  fy = {camera_matrix[1, 1]:.2f} pixel")
    print(f"  cx = {camera_matrix[0, 2]:.2f} pixel (tâm quang học X)")
    print(f"  cy = {camera_matrix[1, 2]:.2f} pixel (tâm quang học Y)")

    print(f"\n Distortion Coefficients:")
    print(dist_coeffs)
    print(f"\n  k1 = {dist_coeffs[0, 0]:.6f}  (radial)")
    print(f"  k2 = {dist_coeffs[0, 1]:.6f}  (radial)")
    print(f"  p1 = {dist_coeffs[0, 2]:.6f}  (tangential)")
    print(f"  p2 = {dist_coeffs[0, 3]:.6f}  (tangential)")
    print(f"  k3 = {dist_coeffs[0, 4]:.6f}  (radial)")

    # -------- BƯỚC 5: LƯU KẾT QUẢ --------
    np.savez(OUTPUT_FILE,
             camera_matrix=camera_matrix,
             dist_coeffs=dist_coeffs,
             rvecs=np.array(rvecs, dtype=object),
             tvecs=np.array(tvecs, dtype=object),
             reprojection_error=ret,
             image_size=img_shape,
             checkerboard_size=CHECKERBOARD,
             square_size=SQUARE_SIZE)

    print(f"\n Đã lưu kết quả vào: {OUTPUT_FILE}")

    # -------- BƯỚC 6: DEMO UNDISTORT --------
    print(f"\n Demo khử méo ảnh (undistort)...")

    # Lấy ảnh đầu tiên để demo
    sample_img = cv2.imread(images[3])
    h, w = sample_img.shape[:2]

    # Tính ma trận camera tối ưu
    new_camera_matrix, roi = cv2.getOptimalNewCameraMatrix(
        camera_matrix, dist_coeffs, (w, h), 1, (w, h)
    )

    # Undistort
    undistorted = cv2.undistort(sample_img, camera_matrix, dist_coeffs,
                                None, new_camera_matrix)

    # Crop theo ROI
    x, y, roi_w, roi_h = roi
    if roi_w > 0 and roi_h > 0:
        undistorted = undistorted[y:y + roi_h, x:x + roi_w]

    # Lưu ảnh demo vào folder
    comp_dir = "comparison_results"
    os.makedirs(comp_dir, exist_ok=True)
    
    orig_path = os.path.join(comp_dir, "1_original_sample.jpg")
    undist_path = os.path.join(comp_dir, "2_undistorted_sample.jpg")
    
    cv2.imwrite(orig_path, sample_img)
    cv2.imwrite(undist_path, undistorted)
    print(f" Đã lưu 2 ảnh so sánh (gốc và khử méo) vào thư mục: {comp_dir}/")

    # Hiển thị so sánh
    # Resize cả 2 cho dễ nhìn
    scale = min(640 / w, 480 / h)
    orig_small = cv2.resize(sample_img, (int(w * scale), int(h * scale)))
    undist_small = cv2.resize(undistorted,
                               (int(undistorted.shape[1] * scale),
                                int(undistorted.shape[0] * scale)))

    cv2.imshow("Original", orig_small)
    cv2.imshow("Undistorted", undist_small)
    print("\n[INFO] Nhấn phím bất kỳ để đóng...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    # -------- TÍNH RE-PROJECTION ERROR CHI TIẾT --------
    print("\n" + "=" * 60)
    print("  RE-PROJECTION ERROR CHI TIẾT CHO TỪNG ẢNH")
    print("=" * 60)

    total_error = 0
    for i in range(len(objpoints)):
        imgpoints_proj, _ = cv2.projectPoints(objpoints[i], rvecs[i], tvecs[i],
                                               camera_matrix, dist_coeffs)
        error = cv2.norm(imgpoints[i], imgpoints_proj, cv2.NORM_L2) / len(imgpoints_proj)
        total_error += error
        print(f"  Ảnh {i + 1:3d}: error = {error:.4f} pixel")

    mean_error = total_error / len(objpoints)
    print(f"\n  Mean re-projection error: {mean_error:.4f} pixel")
    print("\n HOÀN TẤT CALIBRATION!")


if __name__ == "__main__":
    main()
