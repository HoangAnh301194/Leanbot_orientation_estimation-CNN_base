import argparse
from pathlib import Path

import cv2


TARGET_WIDTH = 2560
TARGET_HEIGHT = 1440
PREVIEW_MAX_WIDTH = 2560/4
PREVIEW_MAX_HEIGHT = 1440/4
WINDOW_NAME = "Camera Stream"
SAVE_DIR = Path(__file__).resolve().parent / "captures"


def parse_source(raw_source: str):
    raw_source = raw_source.strip()
    return int(raw_source) if raw_source.isdigit() else raw_source


def to_fixed_2k(frame):
    if frame.shape[1] == TARGET_WIDTH and frame.shape[0] == TARGET_HEIGHT:
        return frame
    return cv2.resize(frame, (TARGET_WIDTH, TARGET_HEIGHT), interpolation=cv2.INTER_LINEAR)


def to_preview(frame):
    scale = min(PREVIEW_MAX_WIDTH / TARGET_WIDTH, PREVIEW_MAX_HEIGHT / TARGET_HEIGHT)
    size = (int(TARGET_WIDTH * scale), int(TARGET_HEIGHT * scale))
    return cv2.resize(frame, size, interpolation=cv2.INTER_AREA)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="0")
    args = parser.parse_args()

    cap = cv2.VideoCapture(parse_source(args.source))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, TARGET_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, TARGET_HEIGHT)

    if not cap.isOpened():
        raise SystemExit(f"Cannot open source: {args.source}")

    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_AUTOSIZE)

    print(f"Streaming source: {args.source}")
    print("Press 's' to capture, 'q' or ESC to quit.")

    while True:
        ok, frame = cap.read()
        if not ok or frame is None:
            break

        frame_2k = to_fixed_2k(frame)
        cv2.imshow(WINDOW_NAME, to_preview(frame_2k))

        key = cv2.waitKey(1) & 0xFF
        if key in (27, ord("q")):
            break
        if key == ord("s"):
            output_path = SAVE_DIR / f"capture_{cv2.getTickCount()}.jpg"
            cv2.imwrite(str(output_path), frame_2k)
            print(f"Saved: {output_path}")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
