import os
import sys
import time
import csv
import argparse
import cv2
from pathlib import Path
from datetime import datetime

current_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(current_dir))

from leanbotCameraController import (
    BLEMotorWorker,
    LeanbotCameraTracker,
    measureHeading as _measureHeading,
)


parser = argparse.ArgumentParser()
parser.add_argument("--ble", type=int, default=654321, help="Leanbot BLE ID")
parser.add_argument("--source", default="1", help="Camera source (index hoặc path)")
parser.add_argument("--no-show", action="store_true", help="Tắt hiển thị cửa sổ OpenCV")
parser.add_argument(
    "--result-hold-ms",
    type=int,
    default=250,
    help="Thời gian giữ ảnh kết quả trajectory/PCA sau mỗi phép đo (default 250 ms)",
)
args = parser.parse_args()
show_ui = not args.no_show

ble = BLEMotorWorker(args.ble)
tracker = LeanbotCameraTracker(source=args.source)
time.sleep(2.0)


survey_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_dir = current_dir / "heading_survey_results"
output_dir.mkdir(exist_ok=True)
raw_output_dir = output_dir / f"raw_xy_{survey_stamp}"
raw_output_dir.mkdir(exist_ok=True)

csv_filename = f"heading_survey_{survey_stamp}.csv"
csv_path = output_dir / csv_filename

summary_fields = [
    "measurement_id",
    "direction",
    "steps",
    "signed_steps",
    "intervalMs",
    "heading",
    "duration",
    "action_elapsed_s",
    "points",
    "turn_idx",
    "fit_vx",
    "fit_vy",
    "raw_csv",
]

csv_file = open(csv_path, "w", newline="", encoding="utf-8")
csv_writer = csv.DictWriter(csv_file, fieldnames=summary_fields)
csv_writer.writeheader()

records = []
measurement_seq = 0


def spinSteps(speed: int, steps: int):
    if steps <= 0:
        return

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
                cv2.putText(
                    vis,
                    f"[SPINNING] speed={speed:+d} | steps={steps}",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 255),
                    2,
                )
                cv2.imshow("Leanbot Heading Survey", vis)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    print("User interrupted survey.")
                    raise KeyboardInterrupt
        time.sleep(0.02)

    time.sleep(0.2)


def measureHeading(intervalMs: int, direction: int, steps: int, signed_steps: int):
    global measurement_seq
    measurement_seq += 1

    if direction > 0:
        state_tag = "after_positive_spin"
    elif direction < 0:
        state_tag = "returned_to_origin"
    else:
        state_tag = "initial_origin"

    measurement_id = (
        f"m{measurement_seq:04d}_"
        f"{state_tag}_steps{steps:03d}_pos{signed_steps:+04d}_int{intervalMs:04d}"
    )

    details = _measureHeading(
        speed_or_interval=2000,
        intervalMs=intervalMs,
        ble_worker=ble,
        tracker=tracker,
        show_ui=show_ui,
        raw_output_dir=raw_output_dir,
        measurement_tag=measurement_id,
        result_hold_ms=args.result_hold_ms,
        return_details=True,
    )
    return measurement_id, details


def record_measurement(direction: int, steps: int, signed_steps: int, intervalMs: int):
    t0 = time.time()
    measurement_id, details = measureHeading(
        intervalMs=intervalMs,
        direction=direction,
        steps=steps,
        signed_steps=signed_steps,
    )
    if details is None:
        raise KeyboardInterrupt

    duration = time.time() - t0
    heading = float(details["heading"])

    row_data = {
        "measurement_id": measurement_id,
        "direction": direction,
        "steps": steps,
        "signed_steps": signed_steps,
        "intervalMs": intervalMs,
        "heading": heading,
        "duration": duration,
        "action_elapsed_s": details.get("action_elapsed_s"),
        "points": details.get("points"),
        "turn_idx": details.get("turn_idx"),
        "fit_vx": details.get("fit_vx"),
        "fit_vy": details.get("fit_vy"),
        "raw_csv": details.get("raw_csv"),
    }

    records.append(row_data)
    csv_writer.writerow(row_data)
    csv_file.flush()

    state_txt = (
        "origin"
        if direction == 0
        else ("+steps" if direction > 0 else "returned-origin")
    )
    print(
        f"[{measurement_id}] state={state_txt:15s} | steps={steps:3d} | "
        f"interval={intervalMs:4d}ms | heading={heading:+7.2f} deg | "
        f"pts={row_data['points']} | turn_idx={row_data['turn_idx']} | "
        f"time={duration:.2f}s"
    )


print(f"Start survey. Summary CSV: {csv_path}")
print(f"Raw XY directory: {raw_output_dir}")
print("During run_fw_bw: only inference + raw XY acquisition.")
print("After BLE END: raw CSV is saved first, then TURN/PCA/TLS/heading are computed.")

try:
    # Measure at the initial origin first.
    for intervalMs in range(1500, 3001, 250):
        record_measurement(
            direction=0,
            steps=0,
            signed_steps=0,
            intervalMs=intervalMs,
        )

    for steps in range(10, 201, 10):
        # Origin -> +steps
        spinSteps(+50, steps)

        for intervalMs in range(1500, 3001, 250):
            record_measurement(
                direction=1,
                steps=steps,
                signed_steps=steps,
                intervalMs=intervalMs,
            )

        # +steps -> origin
        spinSteps(-50, steps)

        for intervalMs in range(1500, 3001, 250):
            record_measurement(
                direction=-1,
                steps=steps,
                signed_steps=0,
                intervalMs=intervalMs,
            )

except KeyboardInterrupt:
    print("Survey interrupted by user.")

finally:
    csv_file.close()
    tracker.release()
    ble.stop()
    if show_ui:
        cv2.destroyAllWindows()

print(f"Survey finished. Summary saved to: {csv_path}")
print(f"Raw XY samples saved under: {raw_output_dir}")
