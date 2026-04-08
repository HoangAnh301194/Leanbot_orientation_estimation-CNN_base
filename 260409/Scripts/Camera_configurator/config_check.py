import cv2

cam_id = 1
cap = cv2.VideoCapture(cam_id)


if not cap.isOpened():
    raise RuntimeError("Khong mo duoc camera")

def is_close(a, b, tol=1e-6):
    return abs(a - b) <= tol

tests = [
    ("FRAME_WIDTH",  cv2.CAP_PROP_FRAME_WIDTH,  [1280, 2560]),
    ("FRAME_HEIGHT", cv2.CAP_PROP_FRAME_HEIGHT, [720, 1440]),
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
print("KIEM TRA PROPERTY NAO CO THE CONFIG DUOC")
print("=" * 110)

configurable = []
not_configurable = []

for name, pid, candidates in tests:
    before = cap.get(pid)

    target = None
    for v in candidates:
        if not is_close(before, v):
            target = v
            break

    if target is None:
        target = candidates[0]

    ok = cap.set(pid, target)
    after = cap.get(pid)

    changed = not is_close(after, before)
    matched_target = is_close(after, target)

    if ok and (changed or matched_target):
        status = "CONFIG DUOC"
        configurable.append((name, before, target, after, ok))
    else:
        status = "KHONG CONFIG DUOC / KHONG RO"
        not_configurable.append((name, before, target, after, ok))

    print(f"{name:15s} | before={before:8.3f} | target={target:8.3f} | ok={str(ok):5s} | after={after:8.3f} | {status}")

    # tra lai gia tri cu
    cap.set(pid, before)

cap.release()

print("\n" + "=" * 110)
print("CAC PROPERTY CONFIG DUOC")
print("=" * 110)
for name, before, target, after, ok in configurable:
    print(f"{name:15s} | before={before:.3f} | target={target:.3f} | after={after:.3f}")

print("\n" + "=" * 110)
print("CAC PROPERTY KHONG CONFIG DUOC / KHONG RO")
print("=" * 110)
for name, before, target, after, ok in not_configurable:
    print(f"{name:15s} | before={before:.3f} | target={target:.3f} | after={after:.3f} | ok={ok}")
    