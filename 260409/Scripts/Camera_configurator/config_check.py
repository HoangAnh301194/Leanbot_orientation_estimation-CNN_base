import cv2

cam_id = 1
cap = cv2.VideoCapture(cam_id)

if not cap.isOpened():
    raise RuntimeError("Khong mo duoc camera")

def is_close(a, b, tol=1e-6):
    return abs(a - b) <= tol

# 1. Danh sách các độ phân giải cần kiểm tra (theo cặp Width, Height)
resolution_tests = [
    (1280, 720),
    (1920, 1080),
    (2560, 1440)
]

# 2. Danh sách các thuộc tính đơn lẻ khác
other_tests = [
    ("FPS",          cv2.CAP_PROP_FPS,          [15, 60]),
    ("BRIGHTNESS",   cv2.CAP_PROP_BRIGHTNESS,   [64, 192]),
    ("CONTRAST",     cv2.CAP_PROP_CONTRAST,     [64, 192]),
    ("SATURATION",   cv2.CAP_PROP_SATURATION,   [64, 192]),
    ("HUE",          cv2.CAP_PROP_HUE,          [64, 192]),
    ("GAIN",         cv2.CAP_PROP_GAIN,         [64, 192]),
    ("EXPOSURE",     cv2.CAP_PROP_EXPOSURE,     [-8, -5]),
    ("SHARPNESS",    cv2.CAP_PROP_SHARPNESS,    [64, 192]),
    ("TEMPERATURE",  cv2.CAP_PROP_TEMPERATURE,  [350, 500]),
    ("BACKLIGHT",    cv2.CAP_PROP_BACKLIGHT,    [0, 1]),
    ("ZOOM",         cv2.CAP_PROP_ZOOM,         [100, 120]),
]

print("=" * 110)
print(f"{'PROPERTY':15s} | {'BEFORE':18s} | {'TARGET':18s} | {'AFTER':18s} | {'STATUS'}")
print("=" * 110)

configurable = []
not_configurable = []

# --- KIỂM TRA ĐỘ PHÂN GIẢI (RESOLUTION) ---
w_before = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
h_before = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)

for w_target, h_target in resolution_tests:
    name = f"RES {w_target}x{h_target}"
    
    # Thử đặt cả 2 thông số cùng lúc
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, w_target)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h_target)
    
    w_after = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    h_after = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    
    matched = is_close(w_after, w_target) and is_close(h_after, h_target)
    
    before_str = f"{int(w_before)}x{int(h_before)}"
    target_str = f"{w_target}x{h_target}"
    after_str = f"{int(w_after)}x{int(h_after)}"
    
    if matched:
        status = "CONFIG DUOC"
        configurable.append((name, before_str, target_str, after_str))
    else:
        status = "KHONG CONFIG DUOC"
        not_configurable.append((name, before_str, target_str, after_str))
        
    print(f"{name:15s} | before={before_str:>8s} | target={target_str:>8s} | after={after_str:>8s} | {status}")

# Trả lại độ phân giải cũ
cap.set(cv2.CAP_PROP_FRAME_WIDTH, w_before)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h_before)

# --- KIỂM TRA CÁC THUỘC TÍNH KHÁC ---
for name, pid, candidates in other_tests:
    before = cap.get(pid)
    target = candidates[1] if is_close(before, candidates[0]) else candidates[0]

    ok = cap.set(pid, target)
    after = cap.get(pid)

    if ok and (not is_close(after, before) or is_close(after, target)):
        status = "CONFIG DUOC"
        configurable.append((name, f"{before:.3f}", f"{target:.3f}", f"{after:.3f}"))
    else:
        status = "KHONG CONFIG DUOC"
        not_configurable.append((name, f"{before:.3f}", f"{target:.3f}", f"{after:.3f}"))

    print(f"{name:15s} | before={before:8.3f} | target={target:8.3f} | after={after:8.3f} | {status}")
    
    # Trả lại giá trị cũ
    cap.set(pid, before)

cap.release()

print("\n" + "=" * 110)
print("TONG HOP KET QUA")
print("=" * 110)
print(f"CONFIG DUOC: {', '.join([c[0] for c in configurable]) if configurable else 'None'}")
print(f"KHONG DUOC : {', '.join([n[0] for n in not_configurable]) if not_configurable else 'None'}")