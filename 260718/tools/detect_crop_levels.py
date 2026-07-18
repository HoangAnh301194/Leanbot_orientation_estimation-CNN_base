import argparse
from collections import defaultdict
from pathlib import Path

import cv2

try:
    from ultralytics import YOLO
except ImportError as exc:
    raise SystemExit("Chua cai ultralytics. Hay cai truoc khi chay script nay.") from exc

from export_markdown_report import (
    collect_images,
    render_webcam_style_bbox_image,
    resolve_cli_path,
    resolve_model_path,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Doc anh tu --input, detect Leanbot, luu anh bbox va crop moi object "
            "voi 4 muc mo rong bbox."
        )
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Duong dan toi 1 anh hoac 1 folder anh.",
    )
    parser.add_argument(
        "--output",
        "--output-dir",
        default=None,
        dest="output_dir",
        help="Folder dau ra. Mac dinh: <input>_crop_levels.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Duong dan toi model .pt. Mac dinh uu tien model trong tools/.",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.2,
        help="Nguong confidence cho inference.",
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=640,
        help="Kich thuoc anh suy luan.",
    )
    parser.add_argument(
        "--max-objects",
        type=int,
        default=0,
        help="So object toi da moi anh. 0 = khong gioi han.",
    )
    parser.add_argument(
        "--expansions",
        nargs="*",
        type=int,
        default=[0, 1, 2, 3],
        help="Danh sach so pixel mo rong bbox. Mac dinh: 0 1 2 3.",
    )
    return parser.parse_args()


def resolve_output_dir(input_path: Path, output_dir_arg: str | None) -> Path:
    if output_dir_arg:
        return resolve_cli_path(output_dir_arg, must_exist=False, label="output dir")

    if input_path.is_file():
        return input_path.parent / f"{input_path.stem}_crop_levels"
    return input_path.parent / f"{input_path.name}_crop_levels"


def normalize_expansions(values: list[int]) -> list[int]:
    unique_values = sorted(set(values))
    if not unique_values:
        raise SystemExit("[ERROR] Can it nhat 1 gia tri trong --expansions.")
    invalid = [value for value in unique_values if value < 0]
    if invalid:
        raise SystemExit("[ERROR] Gia tri --expansions phai >= 0.")
    return unique_values


def crop_with_expansion(
    image,
    bbox_xyxy: tuple[int, int, int, int],
    expansion: int,
) -> tuple[object, tuple[int, int, int, int]]:
    img_h, img_w = image.shape[:2]
    x1, y1, x2, y2 = bbox_xyxy

    left = max(0, x1 - expansion)
    top = max(0, y1 - expansion)
    right = min(img_w, x2 + expansion + 1)
    bottom = min(img_h, y2 + expansion + 1)

    if right <= left:
        right = min(img_w, left + 1)
    if bottom <= top:
        bottom = min(img_h, top + 1)

    return image[top:bottom, left:right].copy(), (left, top, right, bottom)


def draw_single_bbox_preview(
    image,
    bbox_xyxy: tuple[int, int, int, int],
    class_name: str,
    confidence: float,
):
    preview = image.copy()
    x1, y1, x2, y2 = bbox_xyxy
    color = (0, 255, 0)
    cv2.rectangle(preview, (x1, y1), (x2, y2), color, 2)

    label = f"{class_name}: {confidence:.3f}"
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.5
    thick = 1
    pad = 4
    (tw, th), _ = cv2.getTextSize(label, font, scale, thick)
    text_x = max(0, min(x1, preview.shape[1] - tw - pad * 2 - 1))
    text_y = y1 - 6
    if text_y < th + pad * 2:
        text_y = min(preview.shape[0] - 1, y1 + th + pad * 2 + 6)
    cv2.rectangle(
        preview,
        (text_x, text_y - th - pad * 2),
        (text_x + tw + pad * 2, text_y),
        color,
        -1,
    )
    cv2.putText(
        preview,
        label,
        (text_x + pad, text_y - pad),
        font,
        scale,
        (0, 0, 0),
        thick,
        cv2.LINE_AA,
    )
    return preview


def write_metadata(
    output_path: Path,
    *,
    source_path: Path,
    source_rel: Path,
    bbox_image_path: Path,
    class_name: str,
    confidence: float,
    bbox_xyxy: tuple[int, int, int, int],
    crop_bounds: list[tuple[int, tuple[int, int, int, int], tuple[int, int]]],
) -> None:
    lines = [
        f"source={source_path}",
        f"source_relative={source_rel.as_posix()}",
        f"bbox_image={bbox_image_path}",
        f"class_name={class_name}",
        f"confidence={confidence:.6f}",
        f"bbox_xyxy={bbox_xyxy}",
    ]
    for expansion, bounds, size in crop_bounds:
        lines.append(
            f"expand_{expansion}=bounds{bounds},size={size[0]}x{size[1]}"
        )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    args.expansions = normalize_expansions(args.expansions)

    input_path = resolve_cli_path(args.input, must_exist=True, label="input")
    image_paths = collect_images(input_path)
    if not image_paths:
        raise SystemExit(f"[ERROR] Khong tim thay anh nao trong: {input_path}")

    model_path = resolve_model_path(args.model)
    output_dir = resolve_output_dir(input_path, args.output_dir)
    bbox_root = output_dir / "bbox_images"
    object_root = output_dir / "objects"
    bbox_root.mkdir(parents=True, exist_ok=True)
    object_root.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] Input     : {input_path}")
    print(f"[INFO] Model     : {model_path}")
    print(f"[INFO] Output dir: {output_dir}")
    print(f"[INFO] Expansions: {args.expansions}")

    model = YOLO(str(model_path))
    class_counters: defaultdict[str, int] = defaultdict(int)
    total_objects = 0

    for image_path in image_paths:
        frame = cv2.imread(str(image_path))
        if frame is None:
            print(f"[SKIP] Khong doc duoc anh: {image_path}")
            continue

        if input_path.is_dir():
            relative_image = image_path.relative_to(input_path)
        else:
            relative_image = Path(image_path.name)

        bbox_image = render_webcam_style_bbox_image(model, frame, args)
        
        # Chạy inference trực tiếp bằng API chuẩn của YOLO
        # Bật agnostic_nms=True để gom các box đè lên nhau dù khác class
        results = model.predict(frame, conf=args.conf, imgsz=args.imgsz, verbose=False, agnostic_nms=True)
        
        detections = []
        for box in results[0].boxes:
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            conf = float(box.conf[0].cpu().numpy())
            cls_id = int(box.cls[0].cpu().numpy())
            class_name = model.names[cls_id]
            
            detections.append({
                "bbox_xyxy": (int(x1), int(y1), int(x2), int(y2)),
                "best_conf": conf,
                "best_cls": class_name
            })

        bbox_output_dir = bbox_root / relative_image.parent
        bbox_output_dir.mkdir(parents=True, exist_ok=True)
        bbox_image_path = bbox_output_dir / f"{relative_image.stem}_bbox.jpg"
        cv2.imwrite(str(bbox_image_path), bbox_image)

        if not detections:
            print(f"[OK] {relative_image.as_posix()}: 0 detections")
            continue

        print(f"[OK] {relative_image.as_posix()}: {len(detections)} detections")
        for detection in detections:
            class_name = detection["best_cls"]
            class_counters[class_name] += 1
            object_index = class_counters[class_name]
            object_name = f"{class_name}_{object_index:03d}"
            object_dir = object_root / object_name
            object_dir.mkdir(parents=True, exist_ok=True)

            bbox_xyxy = detection["bbox_xyxy"]
            confidence = float(detection["best_conf"])

            preview = draw_single_bbox_preview(frame, bbox_xyxy, class_name, confidence)
            cv2.imwrite(str(object_dir / "object_bbox.jpg"), preview)

            crop_bounds: list[tuple[int, tuple[int, int, int, int], tuple[int, int]]] = []
            for expansion in args.expansions:
                cropped, bounds = crop_with_expansion(frame, bbox_xyxy, expansion)
                crop_path = object_dir / f"expand_{expansion}.jpg"
                cv2.imwrite(str(crop_path), cropped)
                crop_bounds.append((expansion, bounds, (cropped.shape[1], cropped.shape[0])))

            write_metadata(
                object_dir / "meta.txt",
                source_path=image_path,
                source_rel=relative_image,
                bbox_image_path=bbox_image_path,
                class_name=class_name,
                confidence=confidence,
                bbox_xyxy=bbox_xyxy,
                crop_bounds=crop_bounds,
            )

            total_objects += 1

    print(f"[DONE] Images processed : {len(image_paths)}")
    print(f"[DONE] Objects exported : {total_objects}")
    print(f"[DONE] Output root      : {output_dir}")


if __name__ == "__main__":
    main()
