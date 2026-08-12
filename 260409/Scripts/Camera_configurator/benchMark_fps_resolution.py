import cv2
import time

def benchmark_camera(cam_id, use_dshow=False, use_mjpg=False, width=2560, height=1440, num_frames=100):
    backend_str = "DSHOW" if use_dshow else "DEFAULT (MSMF)"
    mjpg_str = "MJPG" if use_mjpg else "DEFAULT"
    print(f"\n--- TESTING: Backend={backend_str}, Format={mjpg_str}, Res={width}x{height} ---")

    # 1. Khởi tạo camera
    if use_dshow:
        cap = cv2.VideoCapture(cam_id, cv2.CAP_DSHOW)
    else:
        cap = cv2.VideoCapture(cam_id)

    if not cap.isOpened():
        print(f"[ERROR] Không thể mở camera với {backend_str}")
        return None

    # 2. Cấu hình MJPG nếu cần (Rất quan trọng cho 2K)
    if use_mjpg:
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

    # 3. Cấu hình độ phân giải 2K
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    
    # Ép FPS lên 30 (DSHOW thường cần dòng này để không bị lag)
    if use_dshow:
        cap.set(cv2.CAP_PROP_FPS, 30)

    # Đọc thử 1 vài frame để ổn định camera (Warm-up)
    for _ in range(10):
        cap.read()

    # Kiểm tra thực tế
    actual_w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    actual_h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    actual_fps = cap.get(cv2.CAP_PROP_FPS)
    print(f"[INFO] Thực tế đang chạy: {int(actual_w)}x{int(actual_h)}, Preset FPS: {actual_fps}")

    # 4. Tính toán FPS thực tế qua 100 frame
    start_time = time.time()
    count = 0
    for i in range(num_frames):
        ret, frame = cap.read()
        if not ret:
            print(f"[ERROR] Fail tại frame {i}")
            break
        count += 1
    
    end_time = time.time()
    elapsed = end_time - start_time
    calc_fps = count / elapsed if elapsed > 0 else 0

    print(f"[RESULT] Thời gian đọc {count} frame: {elapsed:.2f}s")
    print(f"[RESULT] FPS thực tế: {calc_fps:.2f}")

    cap.release()
    return calc_fps

if __name__ == "__main__":
    CAM_ID = 1
    # Độ phân giải 2K thật sự của DS-U04
    W, H = 2560, 1440 
    
    print("BAT DAU BENCHMARK CAMERA HIKVISION DS-U04 TAI DO PHAN GIAI 2K")
    
    # Test 1: Mặc định (MSMF)
    fps_default = benchmark_camera(CAM_ID, use_dshow=False, use_mjpg=False, width=W, height=H)
    
    # Test 2: Tối ưu (DSHOW + MJPG)
    fps_optimized = benchmark_camera(CAM_ID, use_dshow=True, use_mjpg=True, width=W, height=H)
    
    print("\n" + "="*60)
    print("TONG KET TAI 2560x1440:")
    if fps_default: print(f" - FPS Mac dinh (MSMF): {fps_default:.2f}")
    if fps_optimized: print(f" - FPS Toi uu (DSHOW + MJPG): {fps_optimized:.2f}")
    
    if fps_default and fps_optimized:
        improvement = ((fps_optimized / fps_default) - 1) * 100
        print(f"==> Cai thien: {improvement:.1f}%")
    print("="*60)
