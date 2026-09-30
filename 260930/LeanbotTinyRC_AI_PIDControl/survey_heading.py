import os
import sys
import time
import csv
import argparse
import cv2
from pathlib import Path
import numpy as np
from datetime import datetime
current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir))
from leanbotCameraController import BLEMotorWorker, LeanbotCameraTracker, measureHeading as _measureHeading

parser = argparse.ArgumentParser()
parser.add_argument("--ble", type=int, default=654321, help="Leanbot BLE ID")
parser.add_argument("--source", default="1", help="Camera source (index hoặc path)")
parser.add_argument("--no-show", action="store_true", help="Tắt hiển thị cửa sổ OpenCV")
parser.add_argument("--result-hold-ms", type=int, default=900, help="Thời gian giữ ảnh kết quả fit sau mỗi phép đo (ms)")
args = parser.parse_args()
show_ui = not args.no_show

ble = BLEMotorWorker(args.ble)
tracker = LeanbotCameraTracker(source=args.source)
time.sleep(2.0) 


def spinSteps(speed: int, steps: int):
    if steps > 0:
        ble.send_spin_steps(speed, steps)
        t_spin = time.perf_counter()
        dur = 0.5 + steps * 0.04
        while (time.perf_counter() - t_spin < dur) or ble.is_busy:
            if show_ui:
                frame, (cx, cy), detected, _ = tracker.read_and_track()
                if frame is not None:
                    vis = frame.copy()
                    if detected:
                        cv2.circle(vis, (int(cx), int(cy)), 6, (0, 0, 255), -1)
                    cv2.putText(vis, f"[SPINNING] steps={steps} (+{speed})", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                    cv2.imshow("Leanbot Heading Survey", vis)
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        print("User interrupted survey.")
                        sys.exit(0)
            time.sleep(0.02)
        time.sleep(0.2)


output_dir = current_dir / "heading_survey_results"
output_dir.mkdir(exist_ok=True)
raw_trajectory_dir = output_dir / "trajectories"
raw_trajectory_dir.mkdir(exist_ok=True)
csv_filename = f"heading_survey_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
csv_path = output_dir / csv_filename

measurement_counter = 0


def make_measurement_id(direction: int, steps: int, intervalMs: int) -> str:
    global measurement_counter
    measurement_counter += 1
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return f"m{measurement_counter:04d}_dir{direction:+d}_steps{steps:03d}_int{intervalMs}_{ts}"


def measureHeading(intervalMs: int, direction: int, steps: int, signed_steps: int, measurement_id: str) -> float:
    return _measureHeading(
        speed_or_interval=2000,
        intervalMs=intervalMs,
        ble_worker=ble,
        tracker=tracker,
        show_ui=show_ui,
        raw_csv_dir=raw_trajectory_dir,
        measurement_id=measurement_id,
        measurement_meta={
            "direction": direction,
            "steps": steps,
            "signed_steps": signed_steps,
            "intervalMs": intervalMs,
        },
        result_hold_ms=args.result_hold_ms,
    )

csv_file = open(csv_path, "w", newline="", encoding="utf-8")
csv_writer = csv.DictWriter(csv_file, fieldnames=["measurement_id", "direction", "steps", "signed_steps", "intervalMs", "heading", "duration", "raw_trajectory_file"])
csv_writer.writeheader()

records = []
print(f"Start survey..... Data will be saved continuously to {csv_path}")

# Measure at center (0) first
for intervalMs in range(1500, 3001, 250):
    measurement_id = make_measurement_id(0, 0, intervalMs)
    t0 = time.time()
    heading = measureHeading(intervalMs, direction=0, steps=0, signed_steps=0, measurement_id=measurement_id)
    if heading is None:
        print("Quitting survey...")
        sys.exit(0)
    duration = time.time() - t0
    row_data = {
        "measurement_id": measurement_id,
        "direction": 0,
        "steps": 0,
        "signed_steps": 0,
        "intervalMs": intervalMs,
        "heading": heading,
        "duration": duration,
        "raw_trajectory_file": str(Path("trajectories") / f"{measurement_id}.csv"),
    }
    records.append(row_data)
    csv_writer.writerow(row_data)
    csv_file.flush()
    print(f"Dir= 0 | steps=   0 | intervalMs={intervalMs:4d} | heading={heading:6.2f} deg | time={duration:.2f}s")

for steps in range(10, 201, 10):
    # Từ center, xoay thuận
    spinSteps(+50, steps)
    
    for intervalMs in range(1500, 3001, 250):
        measurement_id = make_measurement_id(1, steps, intervalMs)
        t0 = time.time()
        heading = measureHeading(intervalMs, direction=1, steps=steps, signed_steps=steps, measurement_id=measurement_id)
        if heading is None:
            print("Quitting survey...")
            sys.exit(0)
        duration = time.time() - t0
        row_data = {
            "measurement_id": measurement_id,
            "direction": 1,
            "steps": steps,
            "signed_steps": steps,
            "intervalMs": intervalMs,
            "heading": heading,
            "duration": duration,
            "raw_trajectory_file": str(Path("trajectories") / f"{measurement_id}.csv"),
        }
        records.append(row_data)
        csv_writer.writerow(row_data)
        csv_file.flush()
        print(f"Dir=+1 | steps={steps:4d} | intervalMs={intervalMs:4d} | heading={heading:6.2f} deg | time={duration:.2f}s")
    
    # Từ vị trí hiện tại, quay nghịch đúng 'steps' bước để trả về lại center
    spinSteps(-50, steps)
    
    for intervalMs in range(1500, 3001, 250):
        measurement_id = make_measurement_id(-1, steps, intervalMs)
        t0 = time.time()
        heading = measureHeading(intervalMs, direction=-1, steps=steps, signed_steps=0, measurement_id=measurement_id)
        if heading is None:
            print("Quitting survey...")
            sys.exit(0)
        duration = time.time() - t0
        row_data = {
            "measurement_id": measurement_id,
            "direction": -1,
            "steps": steps,
            "signed_steps": 0,  # Thực chất nó đang ở 0
            "intervalMs": intervalMs,
            "heading": heading,
            "duration": duration,
            "raw_trajectory_file": str(Path("trajectories") / f"{measurement_id}.csv"),
        }
        records.append(row_data)
        csv_writer.writerow(row_data)
        csv_file.flush()
        print(f"Dir=-1 | Return= 0 | intervalMs={intervalMs:4d} | heading={heading:6.2f} deg | time={duration:.2f}s")

csv_file.close()
print(f"Survey completed. Data saved to {csv_path}")

if show_ui:
    cv2.destroyAllWindows()
