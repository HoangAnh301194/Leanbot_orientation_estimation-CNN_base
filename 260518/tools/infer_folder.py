"""
infer_folder.py — Quét folder ảnh, chạy YOLO inference, batch save + MJPEG web stream.

Usage:
    # Batch save only
    python infer_folder.py --source D:/path/to/root_images --mode batch

    # MJPEG stream only (xem trên browser, điều khiển prev/next)
    python infer_folder.py --source D:/path/to/root_images --mode stream

    # Cả hai (batch save + stream cùng lúc)
    python infer_folder.py --source D:/path/to/root_images --mode both
"""

import argparse
import glob
import json
import os
import sys
import threading
import time
from http import server
from pathlib import Path
from socketserver import ThreadingMixIn

import cv2
import numpy as np
import torch

sys.path.append(str(Path(__file__).resolve().parent))
import check_confidence

# ─── defaults ────────────────────────────────────────────────────────────────
DEFAULT_MODEL_DIR = Path(__file__).resolve().parent
IMAGE_EXTS = ("*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG")

# ─── HTML page ────────────────────────────────────────────────────────────────
HTML_PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Leanbot Folder Inference</title>
  <style>
    body { font-family: sans-serif; margin: 0; background: #111; color: #eee; }
    #topbar { display:flex; align-items:center; gap:12px; padding:12px 20px; background:#1e1e1e; border-bottom:1px solid #333; }
    h1 { margin:0; font-size:18px; }
    button { padding:8px 18px; border:none; border-radius:6px; background:#3a8dde; color:#fff; cursor:pointer; font-size:14px; }
    button:disabled { background:#444; cursor:default; }
    #info { font-size:13px; color:#aaa; margin-left:auto; }
    #main { padding:16px 20px; }
    #imgwrap { position:relative; display:inline-block; }
    #annotated { max-width:100%; border-radius:8px; border:1px solid #333; }
    #label { margin-top:10px; font-size:14px; color:#ccc; }
    #detbox { margin-top:12px; background:#1a1a1a; border-radius:8px; padding:12px; font-size:13px; max-width:700px; white-space:pre-wrap; color:#9ef; }
    #progress { margin-top:8px; font-size:12px; color:#666; }
    label.chk { font-size: 14px; cursor: pointer; display: flex; align-items: center; gap: 4px; margin-left: 10px; }
  </style>
</head>
<body>
  <div id="topbar">
    <h1>📁 Folder Inference</h1>
    <button id="btnPrev" onclick="navigate(-1)">◀ Prev</button>
    <button id="btnNext" onclick="navigate(1)">Next ▶</button>
    <button onclick="navigate(0)">↺ Reload</button>
    <label class="chk"><input type="checkbox" id="chkConf" onchange="renderImage()"> Show Confidence</label>
    <span id="info">Loading...</span>
  </div>
  <div id="main">
    <div id="imgwrap"><img id="annotated" src="" alt="result"></div>
    <div id="label"></div>
    <div id="detbox"></div>
    <div id="progress"></div>
  </div>
  <script>
    let currentData = null;
    function navigate(delta) {
      fetch('/api/navigate?delta=' + delta)
        .then(r => r.json()).then(updateUI);
    }
    function updateUI(data) {
      currentData = data;
      renderImage();
      document.getElementById('label').textContent = '📄 ' + data.path;
      document.getElementById('info').textContent = (data.idx+1) + ' / ' + data.total;
      document.getElementById('detbox').textContent = data.detections;
      document.getElementById('progress').textContent = 'Saved: ' + data.saved;
      document.getElementById('btnPrev').disabled = data.idx <= 0;
      document.getElementById('btnNext').disabled = data.idx >= data.total - 1;
    }
    function renderImage() {
      if(!currentData) return;
      const isConf = document.getElementById('chkConf').checked;
      document.getElementById('annotated').src = (isConf ? '/api/image_conf?' : '/api/image?') + Date.now();
    }
    fetch('/api/navigate?delta=0').then(r => r.json()).then(updateUI);
    // auto-reload current frame every 2s when streaming
    setInterval(() => {
      fetch('/api/state').then(r=>r.json()).then(updateUI);
    }, 2000);
  </script>
</body>
</html>"""


# ─── helpers ──────────────────────────────────────────────────────────────────

def find_default_model() -> Path | None:
    for name in ("leanbot_detection.pt", "best.pt", "last.pt"):
        p = DEFAULT_MODEL_DIR / name
        if p.exists():
            return p
    pts = sorted(DEFAULT_MODEL_DIR.glob("*.pt"), key=lambda x: x.stat().st_mtime)
    return pts[-1] if pts else None


def collect_images(source: Path) -> list[Path]:
    images = []
    for ext in IMAGE_EXTS:
        images.extend(source.rglob(ext))   # ext = "*.jpg", "*.png", ...
    return sorted(set(images))


def run_inference_on_frame(model, frame, args) -> tuple[np.ndarray, np.ndarray, list[dict], str]:
    """Returns (normal_annotated, detailed_annotated, detection_data, debug_text)."""
    from ultralytics.utils.ops import scale_boxes, xywh2xyxy

    # 1. Normal inference (like webcam_infer)
    result = model.predict(frame, conf=args.conf, imgsz=args.imgsz, verbose=False)[0]
    normal_annotated = result.plot()

    names = model.names
    nc = len(names)
    img_canvas = frame.copy()
    detection_data = []

    img_tensor = check_confidence.preprocess_image(frame, args.imgsz)
    with torch.no_grad():
        raw_pred = check_confidence.normalize_raw_pred_shape(model.model(img_tensor), nc)

    detections, kept_idxs = check_confidence.run_nms(raw_pred, nc)

    debug_lines = []
    if detections is not None and len(detections) > 0:
        raw_boxes_xywh = raw_pred[0, :4, :].T
        raw_class_scores = raw_pred[0, 4:4 + nc, :].T

        detections_scaled = detections.clone()
        detections_scaled[:, :4] = scale_boxes(img_tensor.shape[2:], detections_scaled[:, :4], frame.shape).round()
        
        # Sắp xếp các detection theo best_conf (cột thứ 4) giảm dần và lấy tối đa 9 objects
        sorted_indices = torch.argsort(detections_scaled[:, 4], descending=True)[:9]
        detections_scaled = detections_scaled[sorted_indices]
        
        # Nếu kept_idxs có tồn tại, cũng phải sort theo nó
        if kept_idxs is not None:
            kept_idxs = kept_idxs[sorted_indices]

        raw_boxes_xyxy = scale_boxes(img_tensor.shape[2:], xywh2xyxy(raw_boxes_xywh.clone()), frame.shape).cpu().numpy()

        for obj_id, det in enumerate(detections_scaled):
            x1, y1, x2, y2, best_conf, best_cls = map(float, det.cpu().numpy())
            best_cls_id = int(best_cls)

            if kept_idxs is not None:
                raw_idx = int(kept_idxs[obj_id])
            else:
                ious = check_confidence.box_iou_numpy(np.array([x1, y1, x2, y2]), raw_boxes_xyxy)
                raw_idx = int(np.argmax(ious)) if len(ious) > 0 else 0

            class_scores = raw_class_scores[raw_idx].cpu().numpy()
            
            # --- Custom draw all classes ---
            # Vẽ bbox
            color = (255, 255, 255)
            cv2.rectangle(img_canvas, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
            
            # Vẽ 8 class stacked
            for i, cls_score in enumerate(class_scores):
                bg_color = check_confidence.CLASS_COLOR_PALETTE[i % len(check_confidence.CLASS_COLOR_PALETTE)]
                text = f"Obj{obj_id} {names[i]}: {cls_score:.3f}"
                
                # Tính vị trí (stack dần lên trên)
                label_y = int(y1) - 6 - i * 20
                if label_y < 20: # Nếu sát mép trên quá thì đảo xuống dưới
                    label_y = int(y1) + 20 + i * 20
                    
                check_confidence.draw_label(img_canvas, text, int(x1), label_y, bg_color)
            # -------------------------------


            scores_dict = {names[i]: float(class_scores[i]) for i in range(nc)}
            detection_data.append({
                "obj_id": obj_id,
                "bbox": (int(x1), int(y1), int(x2), int(y2)),
                "class_scores": scores_dict,
                "best_cls": names[best_cls_id],
                "best_conf": round(best_conf, 4),
            })

            debug_lines.append(f"\nObject {obj_id} | Best: {names[best_cls_id]} (Conf: {best_conf:.4f})")
            debug_lines.append(f"Bbox (xyxy): ({x1:.1f}, {y1:.1f}, {x2:.1f}, {y2:.1f}) | Match: low_level")
            for name, score in scores_dict.items():
                marker = " <-- BEST" if name == names[best_cls_id] else ""
                debug_lines.append(f"  {name}: {score:.4f}{marker}")
    else:
        debug_lines.append("Không phát hiện object nào.")

    return normal_annotated, img_canvas, detection_data, "\n".join(debug_lines)


# ─── Batch mode ───────────────────────────────────────────────────────────────

def run_batch(model, images: list[Path], output_dir: Path, args, progress_cb=None):
    output_dir.mkdir(parents=True, exist_ok=True)
    total = len(images)
    for i, img_path in enumerate(images):
        frame = cv2.imread(str(img_path))
        if frame is None:
            print(f"[SKIP] Cannot read: {img_path}")
            continue

        normal, detailed, detections, debug_text = run_inference_on_frame(model, frame, args)

        # Mirror folder structure inside output_dir
        rel = img_path.relative_to(args.source_path)
        out_sub = output_dir / rel.parent
        out_sub.mkdir(parents=True, exist_ok=True)
        stem = img_path.stem

        cv2.imwrite(str(out_sub / f"{stem}_bbox.jpg"), normal)
        cv2.imwrite(str(out_sub / f"{stem}_conf.jpg"), detailed)
        with open(out_sub / f"{stem}_debug.txt", "w", encoding="utf-8") as f:
            f.write(f"Image: {img_path.name}\nPath: {img_path}\nRelative dir: {rel.parent}\n{'-'*60}\n{debug_text}")

        n_det = len(detections)
        best = detections[0]["best_cls"] if detections else "none"
        print(f"[{i+1}/{total}] {img_path.name} -> {n_det} det, best={best}")

        if progress_cb:
            progress_cb(i + 1, total, img_path, normal, detections, debug_text)

    print(f"\n[BATCH] Done. Results saved to: {output_dir}")


# ─── Stream mode ──────────────────────────────────────────────────────────────

class AppState:
    """Shared state between HTTP handler and inference engine."""
    def __init__(self, images: list[Path]):
        self.lock = threading.Lock()
        self.images = images
        self.idx = 0
        self.latest_jpeg: bytes | None = None
        self.latest_jpeg_conf: bytes | None = None
        self.latest_debug = "Loading..."
        self.saved_count = 0

    def get_state_dict(self):
        with self.lock:
            return {
                "idx": self.idx,
                "total": len(self.images),
                "path": str(self.images[self.idx]) if self.images else "",
                "detections": self.latest_debug,
                "saved": self.saved_count,
            }

    def navigate(self, delta: int):
        with self.lock:
            self.idx = max(0, min(len(self.images) - 1, self.idx + delta))
        return self.get_state_dict()

    def update_frame(self, jpeg: bytes, jpeg_conf: bytes, debug: str):
        with self.lock:
            self.latest_jpeg = jpeg
            self.latest_jpeg_conf = jpeg_conf
            self.latest_debug = debug


class ThreadedHTTPServer(ThreadingMixIn, server.HTTPServer):
    daemon_threads = True


def make_handler(app_state: AppState):
    class Handler(server.BaseHTTPRequestHandler):
        def do_GET(self):
            path = self.path.split("?")[0]
            query = self.path[len(path)+1:] if "?" in self.path else ""

            if path in ("/", "/index.html"):
                self._respond(200, "text/html; charset=utf-8", HTML_PAGE.encode())
            elif path == "/api/image":
                jpeg = app_state.latest_jpeg
                if jpeg:
                    self._respond(200, "image/jpeg", jpeg)
                else:
                    self.send_error(503)
            elif path == "/api/image_conf":
                jpeg = app_state.latest_jpeg_conf
                if jpeg:
                    self._respond(200, "image/jpeg", jpeg)
                else:
                    self.send_error(503)
            elif path == "/api/navigate":
                delta = 0
                for part in query.split("&"):
                    if part.startswith("delta="):
                        try: delta = int(part[6:])
                        except: pass
                data = app_state.navigate(delta)
                self._respond(200, "application/json", json.dumps(data).encode())
            elif path == "/api/state":
                data = app_state.get_state_dict()
                self._respond(200, "application/json", json.dumps(data).encode())
            else:
                self.send_error(404)

        def _respond(self, code, ctype, body):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt, *args): return

    return Handler


def inference_loop(model, app_state: AppState, args, output_dir: Path | None):
    """Background thread: runs inference on current image whenever idx changes."""
    last_idx = -1
    encode_params = [cv2.IMWRITE_JPEG_QUALITY, args.jpeg_quality]

    while True:
        with app_state.lock:
            cur_idx = app_state.idx
            images = app_state.images

        if cur_idx == last_idx:
            time.sleep(0.1)
            continue

        last_idx = cur_idx
        if not images:
            continue

        img_path = images[cur_idx]
        frame = cv2.imread(str(img_path))
        if frame is None:
            continue

        normal, detailed, detections, debug_text = run_inference_on_frame(model, frame, args)

        # Encode to JPEG for web
        success1, encoded1 = cv2.imencode(".jpg", normal, encode_params)
        success2, encoded2 = cv2.imencode(".jpg", detailed, encode_params)
        if success1 and success2:
            app_state.update_frame(encoded1.tobytes(), encoded2.tobytes(), debug_text)

        # Optionally batch-save
        if output_dir is not None:
            rel = img_path.relative_to(args.source_path)
            out_sub = output_dir / rel.parent
            out_sub.mkdir(parents=True, exist_ok=True)
            stem = img_path.stem
            cv2.imwrite(str(out_sub / f"{stem}_bbox.jpg"), normal)
            cv2.imwrite(str(out_sub / f"{stem}_conf.jpg"), detailed)
            with open(out_sub / f"{stem}_debug.txt", "w", encoding="utf-8") as f:
                f.write(f"Image: {img_path.name}\nPath: {img_path}\nRelative dir: {rel.parent}\n{'-'*60}\n{debug_text}")
            with app_state.lock:
                app_state.saved_count += 1


def run_stream(model, images: list[Path], args, output_dir: Path | None):
    app_state = AppState(images)

    # Pre-load first frame
    if images:
        frame = cv2.imread(str(images[0]))
        if frame is not None:
            normal, detailed, _, debug = run_inference_on_frame(model, frame, args)
            _, enc1 = cv2.imencode(".jpg", normal, [cv2.IMWRITE_JPEG_QUALITY, args.jpeg_quality])
            _, enc2 = cv2.imencode(".jpg", detailed, [cv2.IMWRITE_JPEG_QUALITY, args.jpeg_quality])
            app_state.update_frame(enc1.tobytes(), enc2.tobytes(), debug)

    # Start inference thread
    t = threading.Thread(target=inference_loop, args=(model, app_state, args, output_dir), daemon=True)
    t.start()

    handler = make_handler(app_state)
    httpd = ThreadedHTTPServer((args.host, args.port), handler)
    print(f"\n[STREAM] Mở browser tại: http://{args.host}:{args.port}")
    print(f"[STREAM] {len(images)} ảnh | Ctrl+C để dừng.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nDừng stream...")
    finally:
        httpd.shutdown()


# ─── CLI ──────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="Quét folder ảnh, chạy YOLO inference, batch save + MJPEG stream.")
    p.add_argument("--source", required=True, help="Folder chứa ảnh (quét đệ quy).")
    p.add_argument("--model", default=None, help="Đường dẫn file .pt. Mặc định tự tìm trong thư mục tools.")
    p.add_argument("--output", default=None, help="Folder lưu kết quả batch. Mặc định: <source>/../infer_output")
    p.add_argument("--mode", choices=("batch", "stream", "both"), default="both",
                   help="batch=chỉ lưu, stream=chỉ web, both=cả hai (mặc định).")
    p.add_argument("--conf", type=float, default=0.25, help="Ngưỡng confidence (default 0.25).")
    p.add_argument("--imgsz", type=int, default=640, help="Kích thước inference.")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--jpeg-quality", type=int, default=85)
    return p.parse_args()


def main():
    args = parse_args()

    # Resolve source: thử CWD trước, nếu không thấy thì thử từ thư mục cha của script (260518/)
    source = Path(args.source)
    if not source.exists():
        alt = DEFAULT_MODEL_DIR.parent / args.source
        if alt.exists():
            source = alt
            print(f"[INFO] Dùng path: {source}")
        else:
            raise SystemExit(f"[ERROR] Source không tồn tại: {source}\n       Thử: {alt}")
    args.source_path = source  # attach for use in helpers

    # Collect images
    images = collect_images(source)
    if not images:
        raise SystemExit(f"[ERROR] Không tìm thấy ảnh nào trong: {source}")
    print(f"[INFO] Tìm thấy {len(images)} ảnh trong {source}")

    # Resolve model
    model_path = Path(args.model) if args.model else find_default_model()
    if model_path is None or not model_path.exists():
        raise SystemExit("[ERROR] Không tìm thấy model .pt. Dùng --model để chỉ định.")
    print(f"[INFO] Model: {model_path}")

    # Load model
    try:
        from ultralytics import YOLO
    except ImportError:
        raise SystemExit("Chưa cài ultralytics. Chạy: pip install ultralytics")

    model = YOLO(str(model_path))

    # Resolve output dir
    output_dir = None
    if args.mode in ("batch", "both"):
        output_dir = Path(args.output) if args.output else source.parent / "infer_output"
        print(f"[INFO] Output: {output_dir}")

    # Run
    if args.mode == "batch":
        run_batch(model, images, output_dir, args)
    elif args.mode == "stream":
        run_stream(model, images, args, output_dir=None)
    else:  # both
        # Batch chạy trước, sau đó mở stream
        print("[INFO] Chạy batch trước...")
        run_batch(model, images, output_dir, args)
        print("[INFO] Mở stream để review kết quả...")
        # Stream từ output annotated images
        annotated_images = collect_images(output_dir)
        if annotated_images:
            run_stream(model, annotated_images, args, output_dir=None)
        else:
            print("[WARN] Không có ảnh output để stream.")


if __name__ == "__main__":
    main()
