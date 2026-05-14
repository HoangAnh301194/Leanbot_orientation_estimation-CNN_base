import argparse
import threading
import time
from http import server
from pathlib import Path
from socketserver import ThreadingMixIn

import cv2


DEFAULT_MODEL_DIR = Path(__file__).resolve().parent


HTML_PAGE = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>Leanbot Webcam Test</title>
    <style>
      body { font-family: sans-serif; margin: 24px; background: #111; color: #eee; }
      h1 { margin-bottom: 8px; }
      p { color: #bbb; }
      img { max-width: 100%; border: 1px solid #333; border-radius: 8px; }
    </style>
  </head>
  <body>
    <h1>Leanbot Webcam Test</h1>
    <p>Nhan Ctrl+C trong terminal de dung stream.</p>
    <img src="/stream.mjpg" alt="webcam stream">
  </body>
</html>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Doc webcam va test model YOLO da fine-tune.")
    parser.add_argument(
        "--model",
        default=None,
        help=(
            "Duong dan toi file .pt. Neu bo trong, script se uu tien "
            "doc model trong thu muc models cua project."
        ),
    )
    parser.add_argument(
        "--source",
        default="0",
        help="Nguon camera. Mac dinh la webcam 0. Co the dung 1, 2... hoac duong dan video.",
    )
    parser.add_argument("--conf", type=float, default=0.5, help="Nguong confidence de hien thi box.")
    parser.add_argument("--imgsz", type=int, default=640, help="Kich thuoc anh suy luan.")
    parser.add_argument(
        "--window-name",
        default="Leanbot Webcam Test",
        help="Ten cua so hien thi neu dung che do opencv.",
    )
    parser.add_argument("--width", type=int, default=1280, help="Do rong webcam mong muon.")
    parser.add_argument("--height", type=int, default=720, help="Do cao webcam mong muon.")
    parser.add_argument(
        "--mirror",
        action="store_true",
        help="Lat ngang anh xem truoc webcam (giong soi guong).",
    )
    parser.add_argument(
        "--mode",
        choices=("auto", "opencv", "mjpeg"),
        default="auto",
        help="Cach hien thi ket qua. auto se tu fallback sang stream web neu OpenCV GUI khong ho tro.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host cho stream MJPEG.")
    parser.add_argument("--port", type=int, default=8765, help="Port cho stream MJPEG.")
    parser.add_argument(
        "--jpeg-quality",
        type=int,
        default=85,
        help="Chat luong JPEG cho stream MJPEG, 0-100.",
    )
    return parser.parse_args()


def find_default_model() -> Path | None:
    preferred_candidates = [
        DEFAULT_MODEL_DIR / "leanbot_detection.pt",
        DEFAULT_MODEL_DIR / "best.pt",
        DEFAULT_MODEL_DIR / "last.pt",
    ]
    for candidate in preferred_candidates:
        if candidate.exists():
            return candidate

    pt_files = sorted(DEFAULT_MODEL_DIR.glob("*.pt"), key=lambda path: path.stat().st_mtime)
    return pt_files[-1] if pt_files else None


def resolve_model_path(model_arg: str | None) -> Path:
    if model_arg:
        model_path = Path(model_arg)
        if not model_path.exists():
            raise FileNotFoundError(f"Khong tim thay model: {model_path}")
        return model_path

    default_model = find_default_model()
    if default_model is None:
        raise FileNotFoundError(
            f"Chua tim thay file .pt trong thu muc model mac dinh: {DEFAULT_MODEL_DIR}. "
            "Hay train xong truoc hoac truyen --model den file .pt can dung."
        )
    return default_model


def parse_source(source: str) -> int | str:
    return int(source) if source.isdigit() else source


def open_capture(source: int | str, width: int, height: int) -> cv2.VideoCapture:
    cap = cv2.VideoCapture(source)
    if isinstance(source, int):
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    if not cap.isOpened():
        raise RuntimeError(f"Khong mo duoc webcam/video source: {source}")
    return cap


def is_opencv_gui_available() -> bool:
    try:
        cv2.namedWindow("__cv_test__", cv2.WINDOW_NORMAL)
        cv2.destroyWindow("__cv_test__")
        return True
    except cv2.error:
        return False


def run_inference(model, frame, args: argparse.Namespace):
    # Model luon xem anh thuc te (khong bi lat) de dam bao class Left/Right chinh xac
    if args.mirror:
        frame = cv2.flip(frame, 1)
        
    result = model.predict(frame, conf=args.conf, imgsz=args.imgsz, verbose=False)[0]
    return result.plot()


def run_opencv_window(model, cap: cv2.VideoCapture, args: argparse.Namespace) -> None:
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

    cv2.destroyAllWindows()


class StreamState:
    def __init__(self) -> None:
        self.condition = threading.Condition()
        self.latest_jpeg: bytes | None = None
        self.stopped = False

    def update(self, jpeg_bytes: bytes) -> None:
        with self.condition:
            self.latest_jpeg = jpeg_bytes
            self.condition.notify_all()

    def wait_for_frame(self) -> bytes | None:
        with self.condition:
            while self.latest_jpeg is None and not self.stopped:
                self.condition.wait(timeout=1.0)
            return self.latest_jpeg

    def stop(self) -> None:
        with self.condition:
            self.stopped = True
            self.condition.notify_all()


class ThreadedHTTPServer(ThreadingMixIn, server.HTTPServer):
    daemon_threads = True


def make_handler(state: StreamState):
    class MJPEGHandler(server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path in ("/", "/index.html"):
                encoded = HTML_PAGE.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)
                return

            if self.path == "/stream.mjpg":
                self.send_response(200)
                self.send_header("Age", "0")
                self.send_header("Cache-Control", "no-cache, private")
                self.send_header("Pragma", "no-cache")
                self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
                self.end_headers()

                while not state.stopped:
                    frame = state.wait_for_frame()
                    if frame is None:
                        continue

                    try:
                        self.wfile.write(b"--frame\r\n")
                        self.wfile.write(b"Content-Type: image/jpeg\r\n")
                        self.wfile.write(f"Content-Length: {len(frame)}\r\n\r\n".encode("utf-8"))
                        self.wfile.write(frame)
                        self.wfile.write(b"\r\n")
                    except (BrokenPipeError, ConnectionResetError):
                        break
                return

            self.send_error(404)

        def log_message(self, fmt: str, *args) -> None:
            return

    return MJPEGHandler


def mjpeg_frame_producer(model, cap: cv2.VideoCapture, args: argparse.Namespace, state: StreamState) -> None:
    encode_params = [cv2.IMWRITE_JPEG_QUALITY, args.jpeg_quality]
    try:
        while not state.stopped:
            ok, frame = cap.read()
            if not ok:
                print("Khong doc duoc frame tu webcam/video. Dang dung stream.")
                state.stop()
                break

            annotated = run_inference(model, frame, args)
            success, encoded = cv2.imencode(".jpg", annotated, encode_params)
            if not success:
                continue
            state.update(encoded.tobytes())
    finally:
        state.stop()


def run_mjpeg_server(model, cap: cv2.VideoCapture, args: argparse.Namespace) -> None:
    state = StreamState()
    producer = threading.Thread(
        target=mjpeg_frame_producer,
        args=(model, cap, args, state),
        daemon=True,
    )
    producer.start()

    handler = make_handler(state)
    httpd = ThreadedHTTPServer((args.host, args.port), handler)
    print(f"Open trinh duyet tai http://{args.host}:{args.port}")
    print("Nhan Ctrl+C trong terminal de dung stream.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nDang dung stream...")
    finally:
        state.stop()
        httpd.shutdown()
        httpd.server_close()
        producer.join(timeout=2.0)


def main() -> None:
    args = parse_args()

    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise SystemExit(
            "Chua cai ultralytics. Hay cai dependency truoc khi test webcam, "
            "vi du: venv/bin/pip install -r requirements.txt"
        ) from exc

    if not 0 <= args.jpeg_quality <= 100:
        raise SystemExit("--jpeg-quality phai nam trong khoang 0-100.")

    model_path = resolve_model_path(args.model)
    source = parse_source(args.source)

    print(f"Dang dung model: {model_path}")

    model = YOLO(str(model_path))
    cap = open_capture(source, args.width, args.height)

    try:
        if args.mode == "opencv":
            run_opencv_window(model, cap, args)
            return

        if args.mode == "mjpeg":
            run_mjpeg_server(model, cap, args)
            return

        if is_opencv_gui_available():
            run_opencv_window(model, cap, args)
        else:
            print("OpenCV GUI khong ho tro tren may nay, dang fallback sang MJPEG stream.")
            run_mjpeg_server(model, cap, args)
    finally:
        cap.release()
        
if __name__ == "__main__":
    main()
