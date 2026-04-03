import argparse
from pathlib import Path

import cv2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Doc webcam va test model YOLO da fine-tune.",
        allow_abbrev=False,
    )
    # Thu muc goc cua project (parent cua scripts/)
    project_root = Path(__file__).resolve().parent.parent
    default_model = str(project_root / "models" / "leanbot_colab.pt")

    parser.add_argument(
        "--model",
        default=default_model,
        help="Duong dan toi file .pt. Mac dinh: models/leanbot_colab.pt",
    )
    parser.add_argument(
        "--source",
        default="0",
        help="Nguon camera. Mac dinh la webcam 0. Co the dung 1, 2... hoac duong dan video.",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.7,
        help="Nguong confidence de xac nhan Leanbot. Chi box >= nguong nay moi duoc hien thi.",
    )
    parser.add_argument("--imgsz", type=int, default=640, help="Kich thuoc anh suy luan.")
    parser.add_argument(
        "--window-name",
        default="Leanbot Webcam Test",
        help="Ten cua so hien thi.",
    )
    parser.add_argument("--width", type=int, default=1280, help="Do rong webcam mong muon.")
    parser.add_argument("--height", type=int, default=720, help="Do cao webcam mong muon.")
    parser.add_argument(
        "--no-mirror",
        action="store_true",
        help="Khong lat ngang anh xem truoc webcam.",
    )
    return parser.parse_args()


def resolve_model_path(model_arg: str) -> Path:
    model_path = Path(model_arg)
    if not model_path.exists():
        raise FileNotFoundError(
            f"Khong tim thay model: {model_path}\n"
            "Hay tai model tu Colab va dat vao thu muc models/."
        )
    return model_path


def parse_source(source: str) -> int | str:
    return int(source) if source.isdigit() else source


def ensure_opencv_gui() -> None:
    try:
        cv2.namedWindow("__cv_test__", cv2.WINDOW_NORMAL)
        cv2.destroyWindow("__cv_test__")
    except cv2.error as exc:
        raise SystemExit(
            "OpenCV hien tai khong ho tro cua so GUI. "
            "Hay cai ban co GUI backend, vi du opencv-python, va dam bao may co display."
        ) from exc


def open_capture(source: int | str, width: int, height: int) -> cv2.VideoCapture:
    cap = cv2.VideoCapture(source)
    if isinstance(source, int):
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    if not cap.isOpened():
        raise RuntimeError(f"Khong mo duoc webcam/video source: {source}")
    return cap


def run_inference(model, frame, args: argparse.Namespace):
    result = model.predict(frame, conf=args.conf, imgsz=args.imgsz, verbose=False)[0]
    return result.plot()


def main() -> None:
    args = parse_args()

    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise SystemExit(
            "Chua cai ultralytics. Hay cai dependency truoc khi test webcam, "
            "vi du: venv/bin/pip install -r requirements.txt"
        ) from exc

    if not 0 <= args.conf <= 1:
        raise SystemExit("--conf phai nam trong khoang 0-1.")

    model_path = resolve_model_path(args.model)
    source = parse_source(args.source)

    print(f"Dang dung model: {model_path}")
    print(f"Nguong xac nhan Leanbot: {args.conf:.2f}")

    ensure_opencv_gui()

    model = YOLO(str(model_path))
    cap = open_capture(source, args.width, args.height)

    try:
        print("Nhan 'q' de thoat cua so webcam.")
        while True:
            ok, frame = cap.read()
            if not ok:
                print("Khong doc duoc frame tu webcam/video. Dang dung.")
                break

            annotated = run_inference(model, frame, args)
            cv2.imshow(args.window_name, annotated)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
    finally:
        cap.release()
        try:
            cv2.destroyAllWindows()
        except cv2.error:
            pass


if __name__ == "__main__":
    main()
