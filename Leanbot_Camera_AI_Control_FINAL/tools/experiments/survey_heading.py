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
sys.path.insert(0, str(current_dir.parent.parent / "LeanbotTinyRC_AI_PIDControl"))
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
                    cv2.putText(
                        vis,
                        f"[SPINNING] steps={steps} (+{speed})",
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
                        sys.exit(0)
            time.sleep(0.02)

        if ble.last_action_ok is not True:
            error = ble.last_action_error or "SPIN_ACTION_FAILED"
            print(
                f"[FATAL] spinSteps verification failed: speed={speed}, "
                f"steps={steps}, error={error}. Stopping survey."
            )
            if show_ui:
                cv2.destroyAllWindows()
            sys.exit(2)

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


def measureHeading(
    intervalMs: int,
    direction: int,
    steps: int,
    signed_steps: int,
    measurement_id: str,
) -> float:
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


fieldnames = [
    "measurement_id",
    "direction",
    "steps",
    "signed_steps",
    "intervalMs",
    "heading",
    "duration",
    "status",
    "error",
    "raw_trajectory_file",
]
csv_file = open(csv_path, "w", newline="", encoding="utf-8")
csv_writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
csv_writer.writeheader()

records = []
print(f"Start survey..... Data will be saved continuously to {csv_path}")


def run_measurement(direction: int, steps: int, signed_steps: int, intervalMs: int):
    """
    Execute one measureHeading() call and write exactly one summary CSV row.

    Returns:
        heading on success;
        None for a recoverable BLE verification failure.

    Fatal BLE failures stop the survey after their FAILED row has been flushed.
    """
    measurement_id = make_measurement_id(direction, steps, intervalMs)
    t0 = time.time()
    heading = measureHeading(
        intervalMs,
        direction=direction,
        steps=steps,
        signed_steps=signed_steps,
        measurement_id=measurement_id,
    )
    duration = time.time() - t0

    raw_rel = str(Path("trajectories") / f"{measurement_id}.csv")

    if heading is None:
        # measureHeading() also returns None when the user presses Q.  A BLE
        # verification failure is distinguishable by last_action_ok == False.
        if ble.last_action_ok is not False:
            print("Quitting survey by user request...")
            csv_file.flush()
            csv_file.close()
            if show_ui:
                cv2.destroyAllWindows()
            sys.exit(0)

        error = ble.last_action_error or "BLE_ACTION_FAILED"
        row_data = {
            "measurement_id": measurement_id,
            "direction": direction,
            "steps": steps,
            "signed_steps": signed_steps,
            "intervalMs": intervalMs,
            "heading": "",
            "duration": duration,
            "status": "FAILED",
            "error": error,
            "raw_trajectory_file": raw_rel,
        }
        records.append(row_data)
        csv_writer.writerow(row_data)
        csv_file.flush()

        print(
            f"[FAILED] dir={direction:+d} | steps={steps:4d} | "
            f"intervalMs={intervalMs:4d} | error={error} | time={duration:.2f}s"
        )

        # If END was still received, the physical action completed and the
        # serial stream was drained. The measurement is invalid, but the next
        # measurement can safely continue.
        if error == "START_TIMEOUT_END_RECEIVED":
            return None

        # Missing END or a BLE exception leaves the robot/action state
        # uncertain. Do not send another motion command.
        print(
            "[FATAL] BLE action state is uncertain. "
            "Stopping survey to avoid mixing trajectories."
        )
        csv_file.close()
        if show_ui:
            cv2.destroyAllWindows()
        sys.exit(2)

    row_data = {
        "measurement_id": measurement_id,
        "direction": direction,
        "steps": steps,
        "signed_steps": signed_steps,
        "intervalMs": intervalMs,
        "heading": heading,
        "duration": duration,
        "status": "OK",
        "error": "",
        "raw_trajectory_file": raw_rel,
    }
    records.append(row_data)
    csv_writer.writerow(row_data)
    csv_file.flush()

    if direction == 0:
        prefix = "Dir= 0 | steps=   0"
    elif direction > 0:
        prefix = f"Dir=+1 | steps={steps:4d}"
    else:
        prefix = f"Dir=-1 | Return= 0 (cycle steps={steps})"

    print(
        f"{prefix} | intervalMs={intervalMs:4d} | "
        f"heading={heading:6.2f} deg | time={duration:.2f}s | status=OK"
    )
    return heading


# Measure at center (0) first.
for intervalMs in range(1500, 3001, 250):
    run_measurement(direction=0, steps=0, signed_steps=0, intervalMs=intervalMs)


for steps in range(10, 201, 10):
    # Từ center, xoay thuận.
    spinSteps(+50, steps)

    for intervalMs in range(1500, 3001, 250):
        run_measurement(
            direction=1,
            steps=steps,
            signed_steps=steps,
            intervalMs=intervalMs,
        )

    # Từ vị trí hiện tại, quay nghịch đúng 'steps' bước để trả về center.
    spinSteps(-50, steps)

    for intervalMs in range(1500, 3001, 250):
        run_measurement(
            direction=-1,
            steps=steps,
            signed_steps=0,
            intervalMs=intervalMs,
        )


csv_file.close()
print(f"Survey completed. Data saved to {csv_path}")

if show_ui:
    cv2.destroyAllWindows()
