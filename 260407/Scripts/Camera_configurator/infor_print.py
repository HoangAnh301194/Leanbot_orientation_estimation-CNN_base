import cv2
import math

def fourcc_to_str(v):
    try:
        v = int(v)
        chars = [chr((v >> (8 * i)) & 0xFF) for i in range(4)]
        s = "".join(chars)
        if all(32 <= ord(c) <= 126 for c in s):
            return s
        return repr(s)
    except:
        return "N/A"

def safe_get(cap, prop_id):
    try:
        val = cap.get(prop_id)
        if isinstance(val, float) and math.isnan(val):
            return "NaN"
        return val
    except Exception as e:
        return f"ERROR: {e}"

cam_id = 1
cap = cv2.VideoCapture(cam_id)

if not cap.isOpened():
    raise RuntimeError(f"Khong mo duoc camera index = {cam_id}")

# ===== PREVIEW CAMERA =====
print("Dang hien thi camera...")
print("Nhan 'q' neu dung camera de bat dau quet property")
print("Nhan 'ESC' neu sai camera de thoat")

while True:
    ret, frame = cap.read()
    if not ret:
        cap.release()
        cv2.destroyAllWindows()
        raise RuntimeError("Khong doc duoc frame tu camera")

    cv2.imshow(f"Camera Preview - index {cam_id}", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == 27:   # ESC
        cap.release()
        cv2.destroyAllWindows()
        print("Da thoat")
        exit()

cv2.destroyAllWindows()

# ===== QUET TOAN BO CAP_PROP_* =====
all_cap_props = []
for name in dir(cv2):
    if name.startswith("CAP_PROP_"):
        value = getattr(cv2, name)
        if isinstance(value, int):
            all_cap_props.append((name, value))

# bo trung theo id
unique_props = {}
for name, pid in all_cap_props:
    if pid not in unique_props:
        unique_props[pid] = name

sorted_props = sorted(
    [(name, pid) for pid, name in unique_props.items()],
    key=lambda x: x[1]
)

meaningful_props = []   # uu tien in truoc
zero_props = []
minus_one_props = []
error_props = []

for name, pid in sorted_props:
    val = safe_get(cap, pid)

    item = (name, pid, val)

    if isinstance(val, str) and val.startswith("ERROR"):
        error_props.append(item)
    elif val == "NaN":
        error_props.append(item)
    elif isinstance(val, (int, float)) and val == -1:
        minus_one_props.append(item)
    elif isinstance(val, (int, float)) and val == 0:
        zero_props.append(item)
    else:
        meaningful_props.append(item)

cap.release()

# ===== IN NHOM CO DU LIEU TRUOC =====
print("\n" + "=" * 110)
print("CAC THUOC TINH CO THE LAY DU LIEU RA ")
print("=" * 110)

for name, pid, val in meaningful_props:
    if name == "CAP_PROP_FOURCC" and isinstance(val, (int, float)):
        print(f"{name:40s} id={pid:5d} value={val} -> {fourcc_to_str(val)}")
    else:
        print(f"{name:40s} id={pid:5d} value={val}")

print("\n" + "=" * 110)
print("TOM TAT")
print("=" * 110)
print(f"So property co du lieu: {len(meaningful_props)}")
print(f"So property = 0      : {len(zero_props)}")
print(f"So property = -1     : {len(minus_one_props)}")
print(f"So property loi/NaN  : {len(error_props)}")

# ===== NEU MUON XEM CAC NHOM CON LAI THI BO COMMENT =====
print("\n" + "=" * 110)
print("CAC THUOC TINH TRA VE 0")
print("=" * 110)
for name, pid, val in zero_props:
    print(f"{name:40s} id={pid:5d} value={val}")

print("\n" + "=" * 110)
print("CAC THUOC TINH TRA VE -1")
print("=" * 110)
for name, pid, val in minus_one_props:
    print(f"{name:40s} id={pid:5d} value={val}")

print("\n" + "=" * 110)
print("CAC THUOC TINH BI LOI / NaN")
print("=" * 110)
for name, pid, val in error_props:
    print(f"{name:40s} id={pid:5d} value={val}")