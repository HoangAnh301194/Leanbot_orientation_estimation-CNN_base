import argparse
from dataclasses import dataclass
from pathlib import Path

import cv2


IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp", ".webp")
CURRENT_DIR = Path(__file__).resolve().parent
DEFAULT_LABEL_DIR = CURRENT_DIR.parent / "output" / "datasets" / "labels"
DEFAULT_IMAGE_DIR = CURRENT_DIR.parent / "output" / "datasets" / "images"


@dataclass
class LabelCheckResult:
    line_no: int
    class_id: int | None
    values: tuple[float, float, float, float] | None
    pixel_box: tuple[int, int, int, int] | None
    issues: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate YOLO label files and export an image preview with bounding boxes."
    )
    parser.add_argument(
        "label_path",
        type=Path,
        nargs="?",
        default=DEFAULT_LABEL_DIR,
        help=(
            "Path to a YOLO label file or a directory containing YOLO label files. "
            f"Default: {DEFAULT_LABEL_DIR}"
        ),
    )
    parser.add_argument(
        "--image",
        type=Path,
        default=None,
        help="Optional image path. If omitted, the script will search for an image with the same stem.",
    )
    parser.add_argument(
        "--images-dir",
        type=Path,
        default=DEFAULT_IMAGE_DIR,
        help=(
            "Optional image directory used when resolving images from label filenames. "
            f"Default: {DEFAULT_IMAGE_DIR}"
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory to save preview images. Default: <labels_parent>/preview_checks",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat suspicious boxes as errors: tiny boxes, huge boxes, or extreme aspect ratios.",
    )
    return parser.parse_args()


def iter_label_files(label_path: Path) -> list[Path]:
    if label_path.is_file():
        return [label_path]
    if label_path.is_dir():
        return sorted(label_path.glob("*.txt"))
    raise FileNotFoundError(f"Label path does not exist: {label_path}")


def resolve_image_path(label_path: Path, explicit_image: Path | None, images_dir: Path | None) -> Path:
    if explicit_image is not None:
        if not explicit_image.exists():
            raise FileNotFoundError(f"Image file does not exist: {explicit_image}")
        return explicit_image

    search_dirs = []
    if images_dir is not None:
        search_dirs.append(images_dir)

    if label_path.parent.name.lower() == "labels":
        search_dirs.append(label_path.parent.parent / "images")

    search_dirs.extend([label_path.parent, label_path.parent.parent])

    for base_dir in search_dirs:
        for ext in IMAGE_EXTENSIONS:
            candidate = base_dir / f"{label_path.stem}{ext}"
            if candidate.exists():
                return candidate

    raise FileNotFoundError(
        f"Could not find image for label file '{label_path.name}'. "
        f"Use --image or --images-dir to specify where the image is."
    )


def load_label_lines(label_path: Path) -> list[str]:
    lines = label_path.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip()]


def clamp_pixel_box(x1: int, y1: int, x2: int, y2: int, width: int, height: int) -> tuple[int, int, int, int]:
    x1 = max(0, min(x1, width - 1))
    y1 = max(0, min(y1, height - 1))
    x2 = max(0, min(x2, width - 1))
    y2 = max(0, min(y2, height - 1))
    return x1, y1, x2, y2


def analyze_label_line(line: str, line_no: int, img_w: int, img_h: int, strict: bool) -> LabelCheckResult:
    issues: list[str] = []
    parts = line.split()
    if len(parts) != 5:
        return LabelCheckResult(line_no, None, None, None, [f"expected 5 columns, got {len(parts)}"])

    try:
        class_id = int(parts[0])
    except ValueError:
        return LabelCheckResult(line_no, None, None, None, ["class_id is not an integer"])

    try:
        x_center, y_center, box_w, box_h = (float(value) for value in parts[1:])
    except ValueError:
        return LabelCheckResult(line_no, class_id, None, None, ["bbox values must be numbers"])

    for name, value in (
        ("x_center", x_center),
        ("y_center", y_center),
        ("width", box_w),
        ("height", box_h),
    ):
        if not 0.0 <= value <= 1.0:
            issues.append(f"{name}={value:.6f} outside [0, 1]")

    if box_w <= 0.0:
        issues.append("width must be > 0")
    if box_h <= 0.0:
        issues.append("height must be > 0")

    x1 = int(round((x_center - box_w / 2) * img_w))
    y1 = int(round((y_center - box_h / 2) * img_h))
    x2 = int(round((x_center + box_w / 2) * img_w))
    y2 = int(round((y_center + box_h / 2) * img_h))

    if x1 < 0 or y1 < 0 or x2 > img_w or y2 > img_h:
        issues.append("bbox exceeds image boundary")

    pixel_w = x2 - x1
    pixel_h = y2 - y1
    if pixel_w <= 0 or pixel_h <= 0:
        issues.append("bbox becomes invalid in pixel coordinates")

    if strict and pixel_w > 0 and pixel_h > 0:
        box_area = pixel_w * pixel_h
        image_area = img_w * img_h
        aspect_ratio = max(pixel_w / pixel_h, pixel_h / pixel_w)

        if box_area < image_area * 0.0002:
            issues.append("bbox is suspiciously small")
        if box_area > image_area * 0.5:
            issues.append("bbox is suspiciously large")
        if aspect_ratio > 10:
            issues.append("bbox aspect ratio is suspiciously extreme")

    pixel_box = clamp_pixel_box(x1, y1, x2, y2, img_w, img_h)
    return LabelCheckResult(
        line_no=line_no,
        class_id=class_id,
        values=(x_center, y_center, box_w, box_h),
        pixel_box=pixel_box,
        issues=issues,
    )


def draw_preview(image, results: list[LabelCheckResult], output_path: Path) -> None:
    preview = image.copy()
    for result in results:
        if result.pixel_box is None:
            continue
        x1, y1, x2, y2 = result.pixel_box
        has_error = bool(result.issues)
        color = (0, 0, 255) if has_error else (0, 200, 0)
        label = f"#{result.line_no} cls={result.class_id}"
        if has_error:
            label += " INVALID"
        cv2.rectangle(preview, (x1, y1), (x2, y2), color, 3)
        text_y = max(25, y1 - 10)
        cv2.putText(preview, label, (x1, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2, cv2.LINE_AA)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), preview)


def check_single_label(
    label_path: Path,
    explicit_image: Path | None,
    images_dir: Path | None,
    output_dir: Path | None,
    strict: bool,
) -> tuple[int, int]:
    image_path = resolve_image_path(label_path, explicit_image, images_dir)
    image = cv2.imread(str(image_path))
    if image is None:
        raise RuntimeError(f"Could not read image file: {image_path}")

    img_h, img_w = image.shape[:2]
    lines = load_label_lines(label_path)
    results = [analyze_label_line(line, idx + 1, img_w, img_h, strict) for idx, line in enumerate(lines)]

    invalid_count = sum(1 for result in results if result.issues)
    preview_dir = output_dir if output_dir is not None else label_path.parent.parent / "preview_checks"
    preview_path = preview_dir / f"{label_path.stem}_check.jpg"
    draw_preview(image, results, preview_path)

    print(f"\n[CHECK] {label_path}")
    print(f"Image      : {image_path} ({img_w}x{img_h})")
    print(f"Preview    : {preview_path}")
    print(f"Total bbox : {len(results)}")
    print(f"Invalid    : {invalid_count}")

    if not lines:
        print("Status     : EMPTY label file")
        return 0, 1

    for result in results:
        if result.values is None:
            print(f"  - Line {result.line_no}: INVALID | {'; '.join(result.issues)}")
            continue

        x_center, y_center, box_w, box_h = result.values
        x1, y1, x2, y2 = result.pixel_box if result.pixel_box is not None else (-1, -1, -1, -1)
        status = "INVALID" if result.issues else "OK"
        print(
            "  - Line "
            f"{result.line_no}: {status} | cls={result.class_id} | "
            f"norm=({x_center:.6f}, {y_center:.6f}, {box_w:.6f}, {box_h:.6f}) | "
            f"px=({x1}, {y1}) -> ({x2}, {y2})"
        )
        if result.issues:
            print(f"    issues: {', '.join(result.issues)}")

    return len(results), invalid_count


def main() -> None:
    args = parse_args()
    if args.label_path == DEFAULT_LABEL_DIR:
        print(f"[INFO] Using default label directory: {args.label_path}")
    if args.images_dir == DEFAULT_IMAGE_DIR:
        print(f"[INFO] Using default image directory: {args.images_dir}")
    label_files = iter_label_files(args.label_path)
    if not label_files:
        raise FileNotFoundError(f"No .txt label files found in: {args.label_path}")

    total_boxes = 0
    total_invalid = 0
    files_with_errors = 0

    for label_file in label_files:
        box_count, invalid_count = check_single_label(
            label_path=label_file,
            explicit_image=args.image if len(label_files) == 1 else None,
            images_dir=args.images_dir,
            output_dir=args.output_dir,
            strict=args.strict,
        )
        total_boxes += box_count
        total_invalid += invalid_count
        if invalid_count > 0 or box_count == 0:
            files_with_errors += 1

    print("\n[SUMMARY]")
    print(f"Files checked : {len(label_files)}")
    print(f"Total bbox    : {total_boxes}")
    print(f"Invalid bbox  : {total_invalid}")
    print(f"Files flagged : {files_with_errors}")


if __name__ == "__main__":
    main()
