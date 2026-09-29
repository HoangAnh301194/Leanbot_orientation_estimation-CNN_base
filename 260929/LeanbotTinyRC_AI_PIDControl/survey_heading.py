import os
import sys
import time
import csv
import argparse
import cv2
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir))
from leanbotCameraController import BLEMotorWorker, LeanbotCameraTracker, measureHeading as _measureHeading

parser = argparse.ArgumentParser()
parser.add_argument("--ble", type=int, default=654321, help="Leanbot BLE ID")
parser.add_argument("--source", default="1", help="Camera source (index hoặc path)")
parser.add_argument("--no-show", action="store_true", help="Tắt hiển thị cửa sổ OpenCV")
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
                    cv2.waitKey(1)
            time.sleep(0.02)
        time.sleep(0.2)


def measureHeading(intervalMs: int) -> float:
    return _measureHeading(speed_or_interval=2000, intervalMs=intervalMs, ble_worker=ble, tracker=tracker, show_ui=show_ui)

records = []

STEP_SIZE = 200

print("Start survey...")
for steps in range(0, 2001, STEP_SIZE):
    if steps > 0:
        spinSteps(+50, STEP_SIZE)
    
    for intervalMs in range(1000, 3001, 500):
        t0 = time.time()
        heading = measureHeading(intervalMs)
        duration = time.time() - t0
        
        records.append({
            "steps": steps,
            "intervalMs": intervalMs,
            "heading": heading,
            "duration": duration
        })
        print(f"steps={steps:3d} | intervalMs={intervalMs:4d} | heading={heading:6.2f} deg | time={duration:.2f}s")

unique_steps = sorted(list(set(r["steps"] for r in records)))

summary = []
for steps in unique_steps:
    step_items = [r for r in records if r["steps"] == steps]
    rads = np.radians([r["heading"] for r in step_items])
    avg_heading = float(np.degrees(np.arctan2(np.mean(np.sin(rads)), np.mean(np.cos(rads)))))
    summary.append({"steps": steps, "avg_heading": avg_heading})

output_dir = current_dir / "heading_survey_results"
output_dir.mkdir(exist_ok=True)

with open(output_dir / "heading_survey.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["steps", "intervalMs", "heading", "duration"])
    writer.writeheader()
    writer.writerows(records)

plt.figure(figsize=(9, 5))
for s in unique_steps:
    s_data = [r for r in records if r["steps"] == s]
    plt.plot([r["intervalMs"] for r in s_data], [r["heading"] for r in s_data], marker='o', label=f"steps={s}")
plt.title("measuredHeading theo intervalMs")
plt.xlabel("intervalMs (ms)")
plt.ylabel("measuredHeading (độ)")
plt.legend()
plt.tight_layout()
plt.savefig(output_dir / "plot1_heading_vs_interval.png")
plt.close()

plt.figure(figsize=(9, 5))
x_steps = np.array([s["steps"] for s in summary])
y_headings = np.array([s["avg_heading"] for s in summary])

p = np.polyfit(x_steps, y_headings, 1)
y_fit = np.polyval(p, x_steps)
r2 = 1.0 - np.sum((y_headings - y_fit)**2) / np.sum((y_headings - np.mean(y_headings))**2)

plt.plot(x_steps, y_headings, marker='s', color='#0055d4', linewidth=1.8, label="Mean measuredHeading (Circular Mean)")
fit_label = f"polyFit 1st order: y = {p[0]:.4f}x + {p[1]:.2f} (R² = {r2:.4f})"
plt.plot(x_steps, y_fit, color='#d90429', linestyle='--', linewidth=2.0, label=fit_label)

plt.title("Mean measuredHeading / steps & Fit 1st order")
plt.xlabel("steps")
plt.ylabel("Mean measuredHeading (degree)")
plt.grid(True, linestyle="--", alpha=0.6)
plt.legend()
plt.tight_layout()
plt.savefig(output_dir / "plot2_avg_heading_vs_steps.png")
plt.close()

plt.figure(figsize=(9, 5))
plt.scatter([r["intervalMs"] for r in records], [r["duration"] for r in records], color='orange', alpha=0.5)
plt.title("Time measureHeading / intervalMs")
plt.xlabel("intervalMs (ms)")
plt.ylabel("Time (seconds)")
plt.grid(True)
plt.tight_layout()
plt.savefig(output_dir / "plot3_duration_vs_interval.png")
plt.close()

if show_ui:
    cv2.destroyAllWindows()
