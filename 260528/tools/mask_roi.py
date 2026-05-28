import cv2
import argparse
import numpy as np
from pathlib import Path


def parse_source(src: str):
    if src.isdigit():
        return int(src)
    return src


def mouse_callback(event, x, y, flags, param):
    # param bây giờ chứa [scale, points_list]
    scale, pts_list = param
    if event == cv2.EVENT_LBUTTONDOWN:
        if len(pts_list) < 4:
            real_x, real_y = int(x * scale), int(y * scale)
            pts_list.append((real_x, real_y))
            print(f"[INFO] point {len(pts_list)} = ({real_x}, {real_y})")


def draw_points_and_polygon(img, pts):
    out = img.copy()
    for i, p in enumerate(pts):
        cv2.circle(out, p, 5, (0, 0, 255), -1)
        cv2.putText(out, str(i + 1), (p[0] + 8, p[1] - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2, cv2.LINE_AA)

    if len(pts) >= 2:
        cv2.polylines(out, [np.array(pts, dtype=np.int32)],
                      isClosed=False, color=(0, 255, 0), thickness=2)
    if len(pts) == 4:
        cv2.polylines(out, [np.array(pts, dtype=np.int32)],
                      isClosed=True, color=(255, 0, 0), thickness=2)
    return out


def select_four_points(frame):
    """Hiển thị ảnh thu nhỏ để chọn 4 góc, trả về toạ độ gốc (2K)."""
    local_points = [] # Sử dụng biến local thay vì global

    h_orig, w_orig = frame.shape[:2]
    scale = 3.0
    disp = cv2.resize(frame, (int(w_orig / scale), int(h_orig / scale)))

    win = "Select 4 points"
    cv2.namedWindow(win, cv2.WINDOW_AUTOSIZE)
    # Truyền cả scale và list vào param của callback
    cv2.setMouseCallback(win, mouse_callback, param=[scale, local_points])

    while True:
        pts_draw = [(int(p[0] / scale), int(p[1] / scale)) for p in local_points]
        vis = draw_points_and_polygon(disp, pts_draw)
        cv2.putText(vis, "Click 4 corners | ENTER: confirm | c: clear | q: quit",
                    (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.imshow(win, vis)

        key = cv2.waitKey(20) & 0xFF
        if key == ord("c"):
            local_points.clear()
            print("[INFO] Cleared points")
        elif key == 13: # ENTER
            if len(local_points) == 4:
                cv2.destroyWindow(win)
                return np.array(local_points, dtype=np.int32)
            print("[WARN] Need exactly 4 points")
        elif key in (ord("q"), 27):
            cv2.destroyWindow(win)
            return None


def build_mask(frame_shape, pts):
    mask = np.zeros(frame_shape[:2], dtype=np.uint8)
    cv2.fillPoly(mask, [pts], 255)
    return mask


def main():
    ap = argparse.ArgumentParser(description="Polygon mask ROI for board region")
    ap.add_argument("--source", type=str, required=True,
                    help='Camera index ("0","1"...) or path to video file')
    ap.add_argument("--save_points", type=str, default="board_points.npy",
                    help="Path to save selected 4 points")
    ap.add_argument("--load_points", type=str, default="",
                    help="Optional .npy file of saved points to skip clicking")
    args = ap.parse_args()

    source = parse_source(args.source)
    cap = cv2.VideoCapture(source)


    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 2560)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1440)

    if not cap.isOpened():
        raise RuntimeError(f"Cannot open source: {args.source}")

    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"[INFO] Resolution: {actual_w}x{actual_h}")

    ret, first_frame = cap.read()
    if not ret:
        cap.release()
        raise RuntimeError("Cannot read first frame")

    # Load hoặc chọn 4 điểm
    if args.load_points and Path(args.load_points).exists():
        pts = np.load(args.load_points).astype(np.int32)
        if pts.shape != (4, 2):
            cap.release()
            raise ValueError("Loaded points must have shape (4, 2)")
        print(f"[INFO] Loaded points from {args.load_points}")
    else:
        pts = select_four_points(first_frame)
        if pts is None:
            cap.release()
            print("[INFO] User cancelled")
            return
        np.save(args.save_points, pts)
        print(f"[INFO] Saved points to {args.save_points}")

    # Tạo mask từ 4 điểm
    mask = build_mask(first_frame.shape, pts)

    # Hiển thị kết quả
    disp_w, disp_h = int(actual_w / 3), int(actual_h / 3)

    cv2.namedWindow("original", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("original", disp_w, disp_h)
    cv2.namedWindow("masked", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("masked", disp_w, disp_h)

    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        masked = cv2.bitwise_and(frame, frame, mask=mask)

        vis = frame.copy()
        cv2.polylines(vis, [pts], True, (0, 255, 0), 2)

        cv2.imshow("original", vis)
        cv2.imshow("masked", masked)

        if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
