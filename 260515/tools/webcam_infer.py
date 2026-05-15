import argparse
import sys
import threading
import time
from http import server
from pathlib import Path
from socketserver import ThreadingMixIn

# Add current directory to sys.path for importing check_confidence
sys.path.append(str(Path(__file__).resolve().parent))


import cv2
import numpy as np
import torch
import check_confidence


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


def generate_detailed_analysis(model, frame, args):
    """Run detailed inference and return (annotated_image, detection_data_list).
    
    Each item in detection_data_list is a dict:
      { 'obj_id': int, 'bbox': (x1,y1,x2,y2), 'class_scores': {name: score, ...}, 'best_cls': str, 'best_conf': float }
    """
    from ultralytics.utils.ops import scale_boxes, xywh2xyxy
    
    img_canvas = frame.copy()
    names = model.names
    nc = len(names)
    detection_data = []
    
    # 1. Preprocess
    img_tensor = check_confidence.preprocess_image(frame, args.imgsz)
    
    # 2. Inference (Low level to get raw scores)
    with torch.no_grad():
        raw_pred = check_confidence.normalize_raw_pred_shape(model.model(img_tensor), nc)
        
    # 3. NMS
    detections, kept_idxs = check_confidence.run_nms(raw_pred, nc)
    
    if detections is not None and len(detections) > 0:
        raw_boxes_xywh = raw_pred[0, :4, :].T
        raw_class_scores = raw_pred[0, 4:4+nc, :].T
        
        detections_scaled = detections.clone()
        detections_scaled[:, :4] = scale_boxes(img_tensor.shape[2:], detections_scaled[:, :4], frame.shape).round()
        
        raw_boxes_xyxy_scaled = scale_boxes(img_tensor.shape[2:], xywh2xyxy(raw_boxes_xywh.clone()), frame.shape).cpu().numpy()
        
        for obj_id, det in enumerate(detections_scaled):
            x1, y1, x2, y2, best_conf, best_cls = map(float, det.cpu().numpy())
            best_cls_id = int(best_cls)
            
            if kept_idxs is not None:
                raw_idx = int(kept_idxs[obj_id])
            else:
                ious = check_confidence.box_iou_numpy(np.array([x1, y1, x2, y2]), raw_boxes_xyxy_scaled)
                raw_idx = int(np.argmax(ious)) if len(ious) > 0 else 0
                
            class_scores = raw_class_scores[raw_idx].cpu().numpy()
            check_confidence.draw_bboxes(img_canvas, x1, y1, x2, y2, class_scores, obj_id, names)
            
            # Collect detection data
            scores_dict = {names[i]: float(class_scores[i]) for i in range(nc)}
            detection_data.append({
                'obj_id': obj_id,
                'bbox': (int(x1), int(y1), int(x2), int(y2)),
                'class_scores': scores_dict,
                'best_cls': names[best_cls_id],
                'best_conf': best_conf,
            })
            
    return img_canvas, detection_data


def format_debug_text(detection_data, names_list, img_name="webcam_capture"):
    """Format detection data into debug text file (same format as check_confidence.py)."""
    lines = []
    lines.append(f"Image: {img_name}")
    lines.append(f"Path: error_image/{img_name}")
    lines.append(f"Relative dir: error_image")
    lines.append("-" * 60)
    
    if not detection_data:
        lines.append("Không phát hiện object nào.")
    else:
        for det in detection_data:
            x1, y1, x2, y2 = det['bbox']
            lines.append(f"\nObject {det['obj_id']} | Best: {det['best_cls']} (Conf: {det['best_conf']:.4f})")
            lines.append(f"Bbox (xyxy): ({x1:.1f}, {y1:.1f}, {x2:.1f}, {y2:.1f}) | Match: low_level")
            for name in names_list:
                score = det['class_scores'].get(name, 0.0)
                marker = " <-- BEST" if name == det['best_cls'] else ""
                lines.append(f"  {name}: {score:.4f}{marker}")
    
    return "\n".join(lines)


def run_opencv_window(model, cap: cv2.VideoCapture, args: argparse.Namespace) -> None:
    print("Nhan 'q' de thoat. Nhan 'c' de chup 3 anh (raw, bbox, confidence) + debug text vao folder error_image.")
    error_dir = DEFAULT_MODEL_DIR.parent / "error_image"
    names_list = list(model.names.values())

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
        elif key == ord("c"):
            error_dir.mkdir(exist_ok=True)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            prefix = error_dir / f"error_{timestamp}"
            
            # 1. Save raw image (no annotations)
            cv2.imwrite(str(prefix) + "_raw.jpg", frame)
            
            # 2. Save annotated (standard bbox)
            cv2.imwrite(str(prefix) + "_bbox.jpg", annotated)
            
            # 3. Save detailed confidence image + debug text
            detailed_img, detection_data = generate_detailed_analysis(model, frame, args)
            cv2.imwrite(str(prefix) + "_conf.jpg", detailed_img)
            
            # 4. Save debug text with per-class confidence
            img_name = f"error_{timestamp}"
            debug_text = format_debug_text(detection_data, names_list, img_name)
            with open(str(prefix) + "_debug.txt", "w", encoding="utf-8") as f:
                f.write(debug_text)
            
            print(f"[CAPTURE] Da luu 3 anh + debug text vao: {error_dir} ({len(detection_data)} detections)")

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
