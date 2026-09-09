import subprocess
import sys
from pathlib import Path

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

SCRIPT_DIR = Path(__file__).resolve().parent
GROUP_SCRIPT = SCRIPT_DIR / "group_to_class.py"

# 24 class theo thứ tự ngược chiều kim đồng hồ
classes = [
    (0,  "Leanbot_0",    "angle_0"),
    (1,  "Leanbot_p15",  "angle_p15"),
    (2,  "Leanbot_p30",  "angle_p30"),
    (3,  "Leanbot_p45",  "angle_p45"),
    (4,  "Leanbot_p60",  "angle_p60"),
    (5,  "Leanbot_p75",  "angle_p75"),
    (6,  "Leanbot_p90",  "angle_p90"),
    (7,  "Leanbot_p105", "angle_p105"),
    (8,  "Leanbot_p120", "angle_p120"),
    (9,  "Leanbot_p135", "angle_p135"),
    (10, "Leanbot_p150", "angle_p150"),
    (11, "Leanbot_p165", "angle_p165"),
    (12, "Leanbot_p180", "angle_p180"),
    (13, "Leanbot_p195", "angle_p195"),
    (14, "Leanbot_m150", "angle_m150"),
    (15, "Leanbot_m135", "angle_m135"),
    (16, "Leanbot_m120", "angle_m120"),
    (17, "Leanbot_m105", "angle_m105"),
    (18, "Leanbot_m90",  "angle_m90"),
    (19, "Leanbot_m75",  "angle_m75"),
    (20, "Leanbot_m60",  "angle_m60"),
    (21, "Leanbot_m45",  "angle_m45"),
    (22, "Leanbot_m30",  "angle_m30"),
    (23, "Leanbot_m15",  "angle_m15"),
]

print("=" * 60)
print("Tạo dataset 24class với index ngược chiều kim đồng hồ")
print("=" * 60)

failed = []
for class_id, class_name, folder in classes:
    print(f"\n[{class_id:2d}/23] {class_name} <- {folder}")
    cmd = [
        sys.executable, str(GROUP_SCRIPT),
        "--dataset_name", "24class",
        "--class_id", str(class_id),
        "--class_name", class_name,
        "--folders", folder,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    print(result.stdout.strip())
    if result.returncode != 0:
        print(f"  [LỖI] {result.stderr.strip()}")
        failed.append(class_name)

print("\n" + "=" * 60)
if failed:
    print(f"[CẢNH BÁO] Có {len(failed)} class bị lỗi: {', '.join(failed)}")
else:
    print(f"[THÀNH CÔNG] Đã tạo xong 24 class trong datasets/24class/raw_image/")
print("=" * 60)
