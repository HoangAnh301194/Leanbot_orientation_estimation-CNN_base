from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from abstract_hsv import compute_gray_hue_diff, compute_hsv_diff
from alignment import ImageAligner
from mask_roi import build_mask, select_four_points


CURRENT_DIR = Path(__file__).resolve().parent
RAW_IMAGE_ROOT = CURRENT_DIR.parent / "raw_image"
TOOL1_OUTPUT_ROOT = CURRENT_DIR.parent / "tool1_output"

WIDTH = 2560
HEIGHT = 1440
WINDOW_NAME = "Camera Stream"
PREVIEW_WIDTH = WIDTH // 4
PREVIEW_HEIGHT = HEIGHT // 4


def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def session_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def parse_source(raw_source: str):
    raw_source = raw_source.strip()
    return int(raw_source) if raw_source.isdigit() else raw_source


def setup_camera(source=0, width=WIDTH, height=HEIGHT):
    cap = cv2.VideoCapture(source)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    if not cap.isOpened():
        raise IOError("Cannot open camera")
    return cap


def ensure_capture_root():
    RAW_IMAGE_ROOT.mkdir(parents=True, exist_ok=True)


def ensure_process_root():
    TOOL1_OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)


def create_capture_session_dir(session_name: str | None = None):
    ensure_capture_root()
    session_id = session_name or f"session_{session_stamp()}"
    session_dir = RAW_IMAGE_ROOT / session_id
    backgrounds_dir = session_dir / "backgrounds"
    raw_dir = session_dir / "raw_images"

    backgrounds_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)
    return session_id, session_dir, backgrounds_dir, raw_dir


def create_output_session_dir(session_name: str):
    import shutil
    ensure_process_root()
    session_dir = TOOL1_OUTPUT_ROOT / session_name
    
    # Create session dir if not exists
    session_dir.mkdir(parents=True, exist_ok=True)
    
    paths = {
        "session_dir": session_dir,
        "aligned_dir": session_dir / "aligned_images",
        "labels_dir": session_dir / "labels",
        "debug_dir": session_dir / "debug",
    }
    
    # Clear subdirectories to avoid polluting with old data, but keep config.npy
    for key, path in paths.items():
        if key == "session_dir":
            continue
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)
        
    return paths


def capture_session_frames(cap, session_id: str, backgrounds_dir: Path, raw_dir: Path):
    background_count = len(list(backgrounds_dir.glob("*.jpg")))
    raw_count = len(list(raw_dir.glob("*.jpg")))

    print("\n--- CAPTURE SESSION ---")
    print("Press 'b' to capture a background image.")
    print("Press 'z' (-30), 'x' (-15), 'c' (0), 'v' (15), 'n' (30) to capture raw images with angle prefixes.")
    print("Press 's' to save and finish the session.")
    print("Press 'q' to stop immediately.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        preview = cv2.resize(frame, (PREVIEW_WIDTH, PREVIEW_HEIGHT))
        cv2.putText(
            preview,
            f"Session: {session_id}",
            (10, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2,
        )
        cv2.putText(
            preview,
            f"BKG: {background_count} | RAW: {raw_count}",
            (10, 56),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 255),
            2,
        )
        cv2.putText(
            preview,
            "b:bkg | z/x/c/v/n:raw | s:save | q:quit",
            (10, 84),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
        )
        cv2.imshow(WINDOW_NAME, preview)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("b"):
            file_path = backgrounds_dir / f"background_{background_count:03d}.jpg"
            cv2.imwrite(str(file_path), frame)
            background_count += 1
            print(f"[INFO] Saved background: {file_path.name}")
        elif key in (ord("z"), ord("x"), ord("c"), ord("v"), ord("n")):
            if key == ord("z"): prefix = "deg_m30_"
            elif key == ord("x"): prefix = "deg_m15_"
            elif key == ord("c"): prefix = "deg_0_"
            elif key == ord("v"): prefix = "deg_p15_"
            elif key == ord("n"): prefix = "deg_p30_"
            
            file_path = raw_dir / f"{prefix}{raw_count:03d}.jpg"
            cv2.imwrite(str(file_path), frame)
            raw_count += 1
            print(f"[INFO] Saved raw image: {file_path.name}")
        elif key == ord("s"):
            return {
                "background_count": background_count,
                "raw_count": raw_count,
                "user_quit": False,
            }
        elif key == ord("q"):
            return {
                "background_count": background_count,
                "raw_count": raw_count,
                "user_quit": True,
            }

    return {
        "background_count": background_count,
        "raw_count": raw_count,
        "user_quit": False,
    }


def list_image_paths(directory: Path):
    if not directory.exists():
        return []
    extensions = ("*.jpg", "*.jpeg", "*.png", "*.bmp", "*.webp")
    image_paths = []
    for pattern in extensions:
        image_paths.extend(directory.glob(pattern))
    return sorted(image_paths)


def load_image_records(directory: Path):
    records = []
    for image_path in list_image_paths(directory):
        image = cv2.imread(str(image_path))
        if image is not None:
            records.append((image_path, image))
    return records


def load_background_images(session_dir: Path):
    return load_image_records(session_dir / "backgrounds")


def load_raw_images(session_dir: Path):
    return load_image_records(session_dir / "raw_images")


def resolve_capture_session(session_arg: str | None):
    ensure_capture_root()
    sessions = sorted([path for path in RAW_IMAGE_ROOT.iterdir() if path.is_dir()])
    if session_arg is None:
        return sessions
    if session_arg == "latest":
        return [sessions[-1]] if sessions else []

    requested_path = Path(session_arg)
    if requested_path.exists():
        candidate = requested_path
    else:
        candidate = RAW_IMAGE_ROOT / session_arg

    if candidate.is_dir():
        return [candidate]
    raise FileNotFoundError(f"Session not found: {session_arg}")


def describe_directory_tree(root_dir: Path):
    lines = [f"{root_dir.name}/"]
    for path in sorted(root_dir.rglob("*")):
        rel = path.relative_to(root_dir)
        depth = len(rel.parts) - 1
        indent = "  " * depth
        suffix = "/" if path.is_dir() else ""
        lines.append(f"{indent}- {rel.name}{suffix}")
    return "\n".join(lines)


def write_text_report(report_path: Path, lines: list[str]):
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def save_json(json_path: Path, payload: dict):
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def save_capture_session_report(session_dir: Path, class_name: str = "unknown", class_id: int = 0):
    backgrounds = list_image_paths(session_dir / "backgrounds")
    raw_images = list_image_paths(session_dir / "raw_images")
    manifest = {
        "session_name": session_dir.name,
        "session_dir": str(session_dir),
        "created_at": now_stamp(),
        "class_name": class_name,
        "class_id": class_id,
        "background_count": len(backgrounds),
        "raw_image_count": len(raw_images),
        "background_files": [path.name for path in backgrounds],
        "raw_image_files": [path.name for path in raw_images],
        "folder_description": {
            "backgrounds": "Reference background images captured in the session.",
            "raw_images": "Images containing Leanbot that will be processed by the labeling tool.",
        },
    }
    
    report_path = session_dir / "session_metadata.json"
    save_json(report_path, manifest)
    return manifest


def load_config_dict(config_path: Path):
    if not config_path.exists():
        return {}
    data = np.load(str(config_path), allow_pickle=True)
    if isinstance(data, np.ndarray) and data.shape == ():
        item = data.item()
        return item if isinstance(item, dict) else {}
    return {}


def save_config_dict(config_path: Path, payload: dict):
    np.save(str(config_path), payload, allow_pickle=True)


def save_roi_preview(image, roi_points, output_path: Path):
    preview = image.copy()
    cv2.polylines(preview, [np.array(roi_points, dtype=np.int32)], True, (0, 255, 0), 3)
    for idx, point in enumerate(np.array(roi_points, dtype=np.int32)):
        cv2.circle(preview, tuple(point), 6, (0, 0, 255), -1)
        cv2.putText(
            preview,
            str(idx + 1),
            (int(point[0]) + 10, int(point[1]) - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 0),
            2,
        )
    cv2.imwrite(str(output_path), preview)


def ensure_roi_points(
    output_session_dir: Path,
    background_path: Path,
    background_image,
    reset_roi: bool = False,
):
    config_path = output_session_dir / "config.npy"
    config = load_config_dict(config_path)
    roi_points = config.get("roi_points")

    if not reset_roi and roi_points is not None:
        points = np.asarray(roi_points, dtype=np.int32)
        if points.shape == (4, 2):
            save_roi_preview(background_image, points, output_session_dir / "roi_preview.jpg")
            return points, config

    print("Select 4 ROI points on the selected background image. Press Enter to confirm.")
    points = select_four_points(background_image)
    if points is None:
        raise ValueError("ROI selection was cancelled")

    config["roi_points"] = points.astype(int).tolist()
    config["roi_background_path"] = str(background_path)
    save_config_dict(config_path, config)
    save_roi_preview(background_image, points, output_session_dir / "roi_preview.jpg")
    return points, config


def build_processing_config(args, input_session_dir: Path, output_session_dir: Path, background_path: Path, roi_points):
    config = {
        "saved_at": now_stamp(),
        "session_name": input_session_dir.name,
        "input_session_dir": str(input_session_dir),
        "output_session_dir": str(output_session_dir),
        "selected_background_path": str(background_path),
        "background_index": int(args.background_index),
        "roi_points": np.asarray(roi_points, dtype=np.int32).astype(int).tolist(),
        "threshold": int(args.threshold),
        "blur": int(args.blur),
        "min_area": int(args.min_area),
        "max_area": int(args.max_area),
        "min_width": int(args.min_width),
        "max_width": int(args.max_width),
        "min_height": int(args.min_height),
        "max_height": int(args.max_height),
        "mask_merge_kernel": int(args.mask_merge_kernel),
        "mask_merge_iterations": int(args.mask_merge_iterations),
        "class_id": int(args.class_id),
        "diff_mode": str(args.diff_mode),
        "w_gray": float(args.w_gray),
        "w_hue": float(args.w_hue),
        "w_h": float(args.w_h),
        "w_s": float(args.w_s),
        "w_v": float(args.w_v),
    }
    return config


def save_processing_report(output_session_dir: Path, input_session_dir: Path, config: dict, summary: dict):
    pass

def add_processing_arguments(parser: argparse.ArgumentParser):
    parser.add_argument("--threshold", type=int, default=70, help="Brightness difference threshold")
    parser.add_argument("--blur", type=int, default=3, help="Gaussian blur kernel size")
    parser.add_argument("--min_area", type=int, default=2500, help="Minimum contour area")
    parser.add_argument("--max_area", type=int, default=500000, help="Maximum contour area")
    parser.add_argument("--min_width", type=int, default=0, help="Minimum bbox width")
    parser.add_argument("--max_width", type=int, default=2000, help="Maximum bbox width")
    parser.add_argument("--min_height", type=int, default=0, help="Minimum bbox height")
    parser.add_argument("--max_height", type=int, default=2000, help="Maximum bbox height")
    parser.add_argument("--class_id", type=int, default=0, help="Class ID used when saving labels")
    parser.add_argument(
        "--diff_mode",
        choices=["1", "2", "3"],
        default="1",
        help="Differencing mode: 1-Gray, 2-Mix (Hybrid), 3-Hue (HSV)",
    )
    parser.add_argument("--w_gray", type=float, default=1.0, help="Weight for gray in Mix mode")
    parser.add_argument("--w_hue", type=float, default=0.1, help="Weight for hue in Mix mode")
    parser.add_argument("--w_h", type=float, default=5.0, help="Weight for hue in HSV mode")
    parser.add_argument("--w_s", type=float, default=1.0, help="Weight for saturation in HSV mode")
    parser.add_argument("--w_v", type=float, default=10.0, help="Weight for value in HSV mode")
    parser.add_argument(
        "--background_index",
        type=int,
        default=0,
        help="Index of the background image inside raw_image/session_X/backgrounds",
    )
    parser.add_argument(
        "--reset_roi",
        action="store_true",
        help="Force ROI selection again even if tool1_output/session_X/config.npy already exists.",
    )
    parser.add_argument(
        "--mask_merge_kernel",
        type=int,
        default=15,
        help="Kernel size for dilation in mask-based merging. Larger = merge more aggressively.",
    )
    parser.add_argument(
        "--mask_merge_iterations",
        type=int,
        default=1,
        help="Number of dilation iterations in mask-based merging.",
    )
    return parser


def build_detection_kwargs(args):
    return {
        "diff_mode": args.diff_mode,
        "threshold": args.threshold,
        "blur_ksize": args.blur,
        "w_gray": args.w_gray,
        "w_hue": args.w_hue,
        "w_h": args.w_h,
        "w_s": args.w_s,
        "w_v": args.w_v,
        "min_area": args.min_area,
        "max_area": args.max_area,
        "min_width": args.min_width,
        "max_width": args.max_width,
        "min_height": args.min_height,
        "max_height": args.max_height,
        "mask_merge_kernel": args.mask_merge_kernel,
        "mask_merge_iterations": args.mask_merge_iterations,
    }


def print_processing_configuration(args):
    mode_names = {"1": "GRAY (Baseline)", "2": "MIX (Hybrid Hue+Gray)", "3": "HUE (HSV Only)"}
    print(f"\n[DEBUG] Algorithm: {mode_names.get(args.diff_mode, 'Unknown')}")
    print(f"        -> Background index: {args.background_index}")
    if args.diff_mode == "1":
        print(f"        -> Params: Threshold={args.threshold}, Blur={args.blur}, CLAHE=True")
    elif args.diff_mode == "2":
        print(
            f"        -> Params: Weights(G={args.w_gray}, H={args.w_hue}), "
            f"Threshold={args.threshold}, Blur={args.blur}, CLAHE=True"
        )
    elif args.diff_mode == "3":
        print(
            f"        -> Params: Weights(H={args.w_h}, S={args.w_s}, V={args.w_v}), "
            f"Threshold={args.threshold}, Blur={args.blur}, CLAHE=True"
        )


def merge_bboxes_by_mask(bboxes, image_shape, kernel_size=15, iterations=1):
    """Mask-Based Merging: vẽ bbox lên mask → dilate → findContours → boundingRect.

    bboxes: list of (x, y, w, h)
    image_shape: shape của ảnh gốc, ví dụ image.shape
    kernel_size: kích thước kernel dilation (càng lớn → merge càng mạnh)
    iterations: số lần dilation
    """
    if not bboxes:
        return []

    H, W = image_shape[:2]

    # Bước 1: Tạo mask đen cùng kích thước ảnh gốc
    mask = np.zeros((H, W), dtype=np.uint8)

    # Bước 2: Vẽ tất cả bbox lên mask bằng màu trắng (tô kín)
    for x, y, w, h in bboxes:
        cv2.rectangle(mask, (int(x), int(y)), (int(x + w), int(y + h)), 255, -1)

    # Bước 3: Dilate để nối các bbox nằm gần nhau
    mask_dilated = mask.copy()
    if kernel_size > 0:
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
        mask_dilated = cv2.dilate(mask_dilated, kernel, iterations=iterations)

    # Bước 4: Tìm contour trên mask đã dilate để xác định các cụm (groups)
    contours, _ = cv2.findContours(mask_dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Bước 5: Với mỗi cụm, lấy BBox bao quanh các pixel GỐC (không lấy phần dilation dư)
    merged_bboxes = []
    for cnt in contours:
        # Tạo mask riêng cho cụm này từ contour đã dilate
        group_mask = np.zeros_like(mask)
        cv2.drawContours(group_mask, [cnt], -1, 255, -1)

        # Chỉ giữ lại những pixel gốc (trước khi dilate) nằm trong vùng cụm này
        tight_mask = cv2.bitwise_and(mask, group_mask)

        # Lấy BBox bao quanh các pixel gốc -> Kết quả sẽ sát với Leanbot hơn
        x, y, w, h = cv2.boundingRect(tight_mask)
        if w > 0 and h > 0:
            merged_bboxes.append((x, y, w, h))

    # Trả về kết quả và các mask trung gian để debug
    debug_masks = {
        "initial": mask,
        "dilated": mask_dilated
    }

    return merged_bboxes, debug_masks


def detect_leanbot(
    frame,
    bg_bgr,
    aligner,
    board_mask,
    diff_mode="3",
    threshold=50,
    blur_ksize=5,
    w_gray=10.0,
    w_hue=3.0,
    w_h=5.0,
    w_s=1.0,
    w_v=10.0,
    min_area=500,
    max_area=100000,
    min_width=20,
    max_width=600,
    min_height=20,
    max_height=600,
    mask_merge_kernel=15,
    mask_merge_iterations=1,
):
    frame_masked = cv2.bitwise_and(frame, frame, mask=board_mask)

    try:
        result = aligner.align(frame_masked)
        aligned_gray = result["aligned"]
        warp_matrix = result["warp"]
        h, w = frame.shape[:2]

        if aligner.motion_type == cv2.MOTION_HOMOGRAPHY:
            aligned_color = cv2.warpPerspective(
                frame,
                warp_matrix,
                (w, h),
                flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                borderMode=cv2.BORDER_REPLICATE,
            )
        else:
            aligned_color = cv2.warpAffine(
                frame,
                warp_matrix,
                (w, h),
                flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                borderMode=cv2.BORDER_REPLICATE,
            )
        # Do NOT mask the final aligned_color here, as user wants the full image in output.
        # We will mask a copy for processing instead.
        
    except Exception as exc:
        print(f"Error aligning image: {exc}")
        return None, [], None

    aligned_color_masked = cv2.bitwise_and(aligned_color, aligned_color, mask=board_mask)
    aligned_gray_masked = cv2.bitwise_and(aligned_gray, aligned_gray, mask=board_mask)

    if diff_mode == "1":
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        bg_p = clahe.apply(aligner.template_gray)
        bg_p = cv2.GaussianBlur(bg_p, (blur_ksize, blur_ksize), 0)

        aligned_p = clahe.apply(aligned_gray_masked)
        aligned_p = cv2.GaussianBlur(aligned_p, (blur_ksize, blur_ksize), 0)

        _, diff_mask, _, _ = aligner.compute_diff(bg_p, aligned_p, threshold=threshold)
    elif diff_mode == "2":
        res = compute_gray_hue_diff(
            bg_bgr,
            aligned_color_masked,
            w_gray=w_gray,
            w_hue=w_hue,
            threshold=threshold,
            blur_ksize=blur_ksize,
            use_clahe=True,
        )
        diff_mask = res["mask"]
    elif diff_mode == "3":
        res = compute_hsv_diff(
            bg_bgr,
            aligned_color_masked,
            w_h=w_h,
            w_s=w_s,
            w_v=w_v,
            threshold=threshold,
            min_saturation=20,
            blur_ksize=blur_ksize,
            use_clahe=True,
        )
        diff_mask = res["mask"]
    else:
        diff_mask = cv2.absdiff(aligner.template_gray, aligned_gray_masked)
        _, diff_mask = cv2.threshold(diff_mask, threshold, 255, cv2.THRESH_BINARY)


    eroded_board_mask = cv2.erode(board_mask, np.ones((15, 15), np.uint8))
    diff_mask = cv2.bitwise_and(diff_mask, diff_mask, mask=eroded_board_mask)

    contours, _ = cv2.findContours(diff_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # 1. Lấy toàn bộ BBox từ các contour (chưa lọc)
    initial_bboxes = [cv2.boundingRect(cnt) for cnt in contours]

    # 2. Thực hiện Merge trước
    merged_bboxes_raw, debug_masks = merge_bboxes_by_mask(
        initial_bboxes,
        image_shape=diff_mask.shape,
        kernel_size=mask_merge_kernel,
        iterations=mask_merge_iterations,
    )

    # 3. Sau đó mới lọc diện tích và kích thước trên kết quả đã merge
    merged_bboxes = []
    for (x, y, w, h) in merged_bboxes_raw:
        area = w * h  # Diện tích vùng bao ngoài
        if min_area < area < max_area:
            if (min_width < w < max_width) and (min_height < h < max_height):
                merged_bboxes.append((x, y, w, h))

    return aligned_color, merged_bboxes, diff_mask, debug_masks


def save_yolo_label(bboxes, img_width, img_height, output_path, class_id=0):
    with open(output_path, "w", encoding="utf-8") as file:
        for x, y, w, h in bboxes:
            x_center = (x + w / 2) / img_width
            y_center = (y + h / 2) / img_height
            w_norm = w / img_width
            h_norm = h / img_height
            file.write(f"{class_id} {x_center:.6f} {y_center:.6f} {w_norm:.6f} {h_norm:.6f}\n")


def save_detection_outputs(output_paths: dict[str, Path], base_name: str, aligned_img, diff_mask, bboxes, class_id=0, debug_masks=None):
    aligned_path = output_paths["aligned_dir"] / f"{base_name}.jpg"
    label_path = output_paths["labels_dir"] / f"{base_name}.txt"
    mask_path = output_paths["debug_dir"] / f"{base_name}_mask.jpg"
    bbox_path = output_paths["debug_dir"] / f"{base_name}_bbox.jpg"

    # Save main aligned image
    cv2.imwrite(str(aligned_path), aligned_img)

    # Save Step-by-Step Merge Debug Masks
    if debug_masks:
        cv2.imwrite(str(output_paths["debug_dir"] / f"{base_name}_merge_1_initial.jpg"), debug_masks["initial"])
        cv2.imwrite(str(output_paths["debug_dir"] / f"{base_name}_merge_2_dilated.jpg"), debug_masks["dilated"])

    # Save debug: Difference Mask WITH Bboxes
    if diff_mask is not None:
        # Convert grayscale mask to BGR to draw colored boxes
        mask_bgr = cv2.cvtColor(diff_mask, cv2.COLOR_GRAY2BGR)
        for x, y, w, h in bboxes:
            cv2.rectangle(mask_bgr, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.imwrite(str(mask_path), mask_bgr)

    # Save debug: Image with Bounding Boxes
    bbox_img = aligned_img.copy()
    for x, y, w, h in bboxes:
        cv2.rectangle(bbox_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(bbox_img, f"cls:{class_id}", (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    cv2.imwrite(str(bbox_path), bbox_img)

    img_height, img_width = aligned_img.shape[:2]
    save_yolo_label(bboxes, img_width, img_height, str(label_path), class_id=class_id)
    return aligned_path, label_path
