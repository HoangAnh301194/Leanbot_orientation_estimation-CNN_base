import cv2
import argparse
import os
import time
from pathlib import Path


RESOLUTIONS = [
    (680, 480),
    (1280, 720),
    (1920, 1080),
    (2560, 1440),
]


def parse_source(src: str):
    if src.isdigit():
        return int(src)
    return src


def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def open_camera(source, backend=None):
    if backend is None:
        return cv2.VideoCapture(source)
    return cv2.VideoCapture(source, backend)


def warmup_camera(cap, num_frames=10, delay=0.02):
    for _ in range(num_frames):
        cap.read()
        time.sleep(delay)


def measure_fps(cap, num_frames=60):
    """
    Measure read FPS by grabbing num_frames frames.
    Returns:
        fps (float)
        last_frame (ndarray or None)
        ok (bool)
    """
    start = time.perf_counter()
    last_frame = None
    count = 0

    for _ in range(num_frames):
        ret, frame = cap.read()
        if not ret or frame is None:
            break
        last_frame = frame
        count += 1

    elapsed = time.perf_counter() - start

    if count == 0 or elapsed <= 0:
        return 0.0, None, False

    fps = count / elapsed
    return fps, last_frame, True


def capture_one_resolution(source, backend_flag, out_dir: Path, width: int, height: int):
    cap = open_camera(source, backend_flag)
    if not cap.isOpened():
        return {
            "requested": f"{width}x{height}",
            "actual": "N/A",
            "fps": 0.0,
            "saved": False,
            "file": "",
            "reason": "cannot_open_camera",
        }

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    warmup_camera(cap, num_frames=12, delay=0.02)

    fps, frame, ok = measure_fps(cap, num_frames=60)

    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    actual_str = f"{actual_w}x{actual_h}"

    cap.release()

    if not ok or frame is None:
        return {
            "requested": f"{width}x{height}",
            "actual": actual_str,
            "fps": 0.0,
            "saved": False,
            "file": "",
            "reason": "cannot_read_frame",
        }

    filename = f"{width}x{height}_actual_{actual_w}x{actual_h}.jpg"
    save_path = out_dir / filename
    saved = cv2.imwrite(str(save_path), frame)

    return {
        "requested": f"{width}x{height}",
        "actual": actual_str,
        "fps": fps,
        "saved": bool(saved),
        "file": str(save_path) if saved else "",
        "reason": "" if saved else "imwrite_failed",
    }


def print_mode_summary(backend_name, results):
    print(f"\n[{backend_name}] Summary")
    print("-" * 60)
    print(f"{'Requested':<14}{'Actual':<14}{'FPS':<12}{'Saved':<8}")
    print("-" * 60)

    fps_values = []
    for r in results:
        fps_text = f"{r['fps']:.2f}" if r["fps"] > 0 else "0.00"
        saved_text = "Yes" if r["saved"] else "No"
        print(f"{r['requested']:<14}{r['actual']:<14}{fps_text:<12}{saved_text:<8}")

        if r["fps"] > 0:
            fps_values.append(r["fps"])

    print("-" * 60)


def run_capture_set(source, backend_name, backend_flag, folder_name: str):
    script_dir = Path(__file__).resolve().parent
    out_dir = script_dir / folder_name
    ensure_dir(out_dir)

    print(f"\nRunning mode: {backend_name}")

    results = []
    for width, height in RESOLUTIONS:
        result = capture_one_resolution(
            source=source,
            backend_flag=backend_flag,
            out_dir=out_dir,
            width=width,
            height=height,
        )
        results.append(result)

    print_mode_summary(backend_name, results)


def main():
    parser = argparse.ArgumentParser(
        description="Capture webcam images at multiple resolutions with default backend and DSHOW"
    )
    parser.add_argument(
        "--source",
        required=True,
        help="Camera index or stream/video source, e.g. 0 or 1",
    )
    args = parser.parse_args()

    source = parse_source(args.source)

    run_capture_set(
        source=source,
        backend_name="DEFAULT",
        backend_flag=None,
        folder_name="default_format",
    )

    if os.name == "nt":
        run_capture_set(
            source=source,
            backend_name="DSHOW",
            backend_flag=cv2.CAP_DSHOW,
            folder_name="dshow_format",
        )
    else:
        print("\nDSHOW skipped: only available on Windows.")


if __name__ == "__main__":
    main()