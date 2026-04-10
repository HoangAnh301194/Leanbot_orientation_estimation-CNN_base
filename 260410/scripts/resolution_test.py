import cv2
import argparse
import os
import time
from pathlib import Path


RESOLUTIONS = [
    (640, 360),
    (640, 480),
    (680, 480),
    (1280, 720),
    (1280, 960),
    (1920, 1080),
    (2048, 1536),
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
        elapsed (float)
        count (int)
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
        return 0.0, None, False, elapsed, count

    fps = count / elapsed
    return fps, last_frame, True, elapsed, count


def capture_one_resolution(source, backend_flag, out_dir: Path, width: int, height: int, mode_name="Unknown"):
    cap = open_camera(source, backend_flag)
    if not cap.isOpened():
        return {
            "requested": f"{width}x{height}",
            "actual": "N/A",
            "fps_get": 0.0,
            "fps_actual": 0.0,
            "time": 0.0,
            "frames": 0,
            "saved": False,
            "reason": "cannot_open",
        }

    # Set resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    
    # Set FPS to 30.0 as requested
    cap.set(cv2.CAP_PROP_FPS, 30.0)

    warmup_camera(cap, num_frames=10, delay=0.01)

    # Get metadata before measuring
    fps_get = cap.get(cv2.CAP_PROP_FPS)
    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    actual_str = f"{actual_w}x{actual_h}"

    fps_actual, frame, ok, elapsed, count = measure_fps(cap, num_frames=60)

    cap.release()

    saved = False
    if ok and frame is not None:
        filename = f"{width}x{height}_actual_{actual_w}x{actual_h}.jpg"
        save_path = out_dir / filename
        saved = cv2.imwrite(str(save_path), frame)

    return {
        "requested": f"{width}x{height}",
        "actual": actual_str,
        "fps_get": fps_get,
        "fps_actual": fps_actual,
        "time": elapsed,
        "frames": count,
        "saved": saved,
        "reason": "" if ok else "failed_read",
    }


def print_mode_summary(backend_name, results):
    print(f"\n{'-'*95}")
    print(f"MODE: {backend_name}")
    print(f"{'-'*95}")
    header = f"{'Requested':<15} | {'Actual':<15} | {'FPS Set':<10} | {'FPS Actual':<12} | {'Time (s)':<10} | {'Frames':<8}"
    print(header)
    print(f"{'-'*85}")

    for r in results:
        fps_get_str = f"{r['fps_get']:.1f}"
        fps_act_str = f"{r['fps_actual']:.2f}"
        time_str = f"{r['time']:.2f}"
        row = f"{r['requested']:<15} | {r['actual']:<15} | {fps_get_str:<10} | {fps_act_str:<12} | {time_str:<10} | {r['frames']:<8}"
        print(row)
    print(f"{'-'*85}")


def run_capture_set(source, backend_name, backend_flag, folder_name: str):
    script_dir = Path(__file__).resolve().parent
    out_dir = script_dir / folder_name
    ensure_dir(out_dir)

    print(f"\nStarting test for: {backend_name}...")

    results = []
    for width, height in RESOLUTIONS:
        result = capture_one_resolution(
            source=source,
            backend_flag=backend_flag,
            out_dir=out_dir,
            width=width,
            height=height,
            mode_name=backend_name
        )
        results.append(result)

    print_mode_summary(backend_name, results)


def main():
    parser = argparse.ArgumentParser(
        description="Detailed Camera Resolution and Performance Test"
    )
    parser.add_argument(
        "--source",
        type=str,
        required=True,
        help="Camera index or URL",
    )
    args = parser.parse_args()

    source = parse_source(args.source)

    # 1. Default Backend
    run_capture_set(
        source=source,
        backend_name="DEFAULT (Any)",
        backend_flag=None,
        folder_name="default_format",
    )

    # 2. DSHOW (Windows only)
    if os.name == "nt":
        run_capture_set(
            source=source,
            backend_name="DSHOW",
            backend_flag=cv2.CAP_DSHOW,
            folder_name="dshow_format",
        )
    
    print("\nTest completed. Images saved in 'scripts/' format folders.")


if __name__ == "__main__":
    main()