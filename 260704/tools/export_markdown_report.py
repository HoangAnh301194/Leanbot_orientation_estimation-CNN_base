import argparse
import math
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import torch

try:
    from ultralytics import YOLO
    from ultralytics.utils.ops import scale_boxes, xywh2xyxy
except ImportError as exc:
    raise SystemExit("Chua cai ultralytics. Hay cai truoc khi chay script nay.") from exc

sys.path.append(str(Path(__file__).resolve().parent))
import check_confidence


IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".bmp", ".webp")
DEFAULT_MODEL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = DEFAULT_MODEL_DIR.parent
MAX_TABLE_CLASS_COLUMNS = 0


@dataclass
class DisplayGroup:
    label: str
    class_names: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Doc 1 anh hoac 1 folder anh, chay inference va xuat bao cao Markdown."
    )
    parser.add_argument(
        "--source",
        required=True,
        help="Duong dan toi 1 anh hoac 1 folder anh.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Duong dan toi model .pt. Mac dinh uu tien 24class.pt trong tools/.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Folder luu anh bbox va report.md. Mac dinh: <source>_markdown_report.",
    )
    parser.add_argument(
        "--report-name",
        default="report.md",
        help="Ten file Markdown dau ra.",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.25,
        help="Nguong confidence NMS.",
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=640,
        help="Kich thuoc suy luan.",
    )
    parser.add_argument(
        "--max-objects",
        type=int,
        default=9,
        help="Gioi han so object moi anh sau khi sort theo confidence. 0 = khong gioi han. Mac dinh: 9.",
    )
    parser.add_argument(
        "--display-groups",
        nargs="*",
        default=None,
        help=(
            "Danh sach cot class hien trong bang. Moi muc co the la 1 class hoac nhieu class "
            "ngan cach bang dau phay. Vi du: "
            "Leanbot_p60 Leanbot_p45 Leanbot_p30 Leanbot_p105 Leanbot_m15 "
            "Leanbot_p150,Leanbot_m150 Leanbot_p195 Leanbot_p180"
        ),
    )
    parser.add_argument(
        "--group-reducer",
        choices=("max", "sum"),
        default="max",
        help="Cach gop score khi 1 cot dai dien cho nhieu class.",
    )
    return parser.parse_args()


def resolve_cli_path(raw_value: str, *, must_exist: bool, label: str) -> Path:
    raw_path = Path(raw_value).expanduser()
    if raw_path.is_absolute():
        resolved = raw_path.resolve()
    else:
        resolved = (PROJECT_ROOT / raw_path).resolve()

    if must_exist and not resolved.exists():
        raise SystemExit(f"[ERROR] Khong tim thay {label}: {resolved}")
    return resolved


def find_default_model() -> Path | None:
    preferred = [
        DEFAULT_MODEL_DIR / "24class.pt",
        DEFAULT_MODEL_DIR / "best.pt",
        DEFAULT_MODEL_DIR / "leanbot_detection.pt",
        DEFAULT_MODEL_DIR / "last.pt",
    ]
    for candidate in preferred:
        if candidate.exists():
            return candidate

    pt_files = sorted(DEFAULT_MODEL_DIR.glob("*.pt"), key=lambda path: path.stat().st_mtime, reverse=True)
    return pt_files[0] if pt_files else None


def resolve_model_path(model_arg: str | None) -> Path:
    if model_arg:
        return resolve_cli_path(model_arg, must_exist=True, label="model")

    model_path = find_default_model()
    if model_path is None:
        raise SystemExit("[ERROR] Khong tim thay model .pt trong thu muc tools/.")
    return model_path


def resolve_output_dir(source_path: Path, output_dir_arg: str | None) -> Path:
    if output_dir_arg:
        return resolve_cli_path(output_dir_arg, must_exist=False, label="output dir")

    if source_path.is_file():
        return source_path.parent / f"{source_path.stem}_markdown_report"
    return source_path.parent / f"{source_path.name}_markdown_report"


def collect_images(source_path: Path) -> list[Path]:
    if source_path.is_file():
        if source_path.suffix.lower() not in IMAGE_EXTS:
            raise SystemExit(f"[ERROR] File khong phai anh ho tro: {source_path}")
        return [source_path]

    images = [path for path in source_path.rglob("*") if path.is_file() and path.suffix.lower() in IMAGE_EXTS]
    return sorted(images)


def short_class_label(name: str) -> str:
    return name.replace("Leanbot_", "")


def build_display_groups(model_names: list[str], display_groups_arg: list[str] | None) -> list[DisplayGroup]:
    if not display_groups_arg:
        return [DisplayGroup(label=short_class_label(name), class_names=[name]) for name in model_names]

    known = set(model_names)
    groups: list[DisplayGroup] = []
    for item in display_groups_arg:
        class_names = [token.strip() for token in item.split(",") if token.strip()]
        if not class_names:
            continue

        unknown = [name for name in class_names if name not in known]
        if unknown:
            raise SystemExit(f"[ERROR] Class khong ton tai trong model: {', '.join(unknown)}")

        label = "/".join(short_class_label(name) for name in class_names)
        groups.append(DisplayGroup(label=label, class_names=class_names))

    if not groups:
        raise SystemExit("[ERROR] --display-groups khong hop le.")
    return groups


ANGLE_PATTERN = re.compile(r"^Leanbot_(?:(?P<sign>[pm])(?P<value>\d+)|(?P<plain>\d+))$")


def parse_angle_from_class_name(class_name: str) -> float | None:
    match = ANGLE_PATTERN.match(class_name)
    if not match:
        return None

    if match.group("plain") is not None:
        return float(match.group("plain"))

    value = float(match.group("value"))
    return value if match.group("sign") == "p" else -value


def estimate_angle_from_scores(
    class_scores: dict[str, float],
) -> tuple[float | None, float]:
    angle_entries: list[tuple[str, float, float]] = []
    for class_name, score in class_scores.items():
        angle = parse_angle_from_class_name(class_name)
        if angle is None:
            continue
        angle_entries.append((class_name, float(score), angle))

    if not angle_entries:
        return None, 0.0

    sum_x = 0.0
    sum_y = 0.0

    for class_name, score, angle in angle_entries:
        theta_rad = math.radians(angle)
        sum_x += score * math.cos(theta_rad)
        sum_y += score * math.sin(theta_rad)

    magnitude = math.hypot(sum_x, sum_y)
    
    if magnitude <= 1e-9:
        return None, 0.0

    result_rad = math.atan2(sum_y, sum_x)

    return math.degrees(result_rad), magnitude


def group_score(class_scores: dict[str, float], group: DisplayGroup, reducer: str) -> float:
    scores = [float(class_scores.get(class_name, 0.0)) for class_name in group.class_names]
    if not scores:
        return 0.0
    if reducer == "sum":
        return float(sum(scores))
    return float(max(scores))


def select_top_display_groups(
    detections: list[dict],
    display_groups: list[DisplayGroup],
    group_reducer: str,
    limit: int = MAX_TABLE_CLASS_COLUMNS,
) -> list[DisplayGroup]:
    if limit <= 0 or len(display_groups) <= limit or not detections:
        return display_groups

    ranked_groups: list[tuple[float, str, DisplayGroup]] = []
    for group in display_groups:
        best_value = max(
            group_score(detection["class_scores"], group, group_reducer)
            for detection in detections
        )
        ranked_groups.append((best_value, group.label, group))

    ranked_groups.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [group for _, _, group in ranked_groups[:limit]]


def fmt_num(value: float) -> str:
    if math.isclose(value, round(value), abs_tol=1e-6):
        return str(int(round(value)))
    return f"{value:.1f}"


def fmt_score(value: float) -> str:
    return f"{value:.4f}"


def format_bbox_xywh(bbox_xyxy: tuple[int, int, int, int]) -> str:
    x1, y1, x2, y2 = bbox_xyxy
    width = x2 - x1
    height = y2 - y1
    xc = x1 + width / 2.0
    yc = y1 + height / 2.0
    return f"({fmt_num(xc)}, {fmt_num(yc)}, {fmt_num(width)}, {fmt_num(height)})"


def render_webcam_style_bbox_image(model, frame: np.ndarray, args: argparse.Namespace) -> np.ndarray:
    # Keep the same drawing style as webcam_infer.py for saved *_bbox.jpg assets.
    result = model.predict(frame, conf=args.conf, imgsz=args.imgsz, verbose=False)[0]
    return result.plot()


def run_low_level_inference(model, frame: np.ndarray, args: argparse.Namespace) -> list[dict]:
    check_confidence.CONF_THRES = args.conf

    names_map = model.names
    model_names = [names_map[idx] for idx in sorted(names_map)]
    nc = len(model_names)
    detection_data: list[dict] = []

    img_tensor = check_confidence.preprocess_image(frame, args.imgsz)
    with torch.no_grad():
        raw_pred = check_confidence.normalize_raw_pred_shape(model.model(img_tensor), nc)

    detections, kept_idxs = check_confidence.run_nms(raw_pred, nc)
    if detections is None or len(detections) == 0:
        return detection_data

    raw_boxes_xywh = raw_pred[0, :4, :].T
    raw_class_scores = raw_pred[0, 4:4 + nc, :].T
    raw_boxes_xyxy = scale_boxes(
        img_tensor.shape[2:],
        xywh2xyxy(raw_boxes_xywh.clone()),
        frame.shape,
    ).cpu().numpy()

    detections_scaled = detections.clone()
    detections_scaled[:, :4] = scale_boxes(img_tensor.shape[2:], detections_scaled[:, :4], frame.shape).round()

    sorted_indices = torch.argsort(detections_scaled[:, 4], descending=True)
    if args.max_objects > 0:
        sorted_indices = sorted_indices[:args.max_objects]
    detections_scaled = detections_scaled[sorted_indices]

    if kept_idxs is not None:
        kept_idxs = kept_idxs[sorted_indices]

    for obj_id, det in enumerate(detections_scaled):
        x1, y1, x2, y2, best_conf, best_cls = map(float, det.cpu().numpy())
        best_cls_id = int(best_cls)

        if kept_idxs is not None:
            raw_idx = int(kept_idxs[obj_id])
        else:
            ious = check_confidence.box_iou_numpy(np.array([x1, y1, x2, y2]), raw_boxes_xyxy)
            raw_idx = int(np.argmax(ious)) if len(ious) > 0 else 0

        class_score_array = raw_class_scores[raw_idx].cpu().numpy()
        class_scores = {
            model_names[class_idx]: float(class_score_array[class_idx])
            for class_idx in range(nc)
        }

        detection_data.append(
            {
                "obj_id": obj_id,
                "bbox_xyxy": (int(x1), int(y1), int(x2), int(y2)),
                "class_scores": class_scores,
                "best_cls": model_names[best_cls_id],
                "best_conf": float(best_conf),
            }
        )

    return detection_data


def relative_asset_path(report_path: Path, asset_path: Path) -> str:
    return asset_path.relative_to(report_path.parent).as_posix()


def write_markdown_report(
    report_path: Path,
    source_path: Path,
    model_path: Path,
    display_groups: list[DisplayGroup],
    group_reducer: str,
    image_reports: list[dict],
) -> None:
    lines: list[str] = []
    lines.append("# Leanbot Markdown Report")
    lines.append("")
    lines.append(f"- Source: `{source_path}`")
    lines.append(f"- Model: `{model_path}`")
    lines.append("- Goc uoc luong: Tinh tu vector tong cua tat ca cac class goc")
    lines.append(f"- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    for image_report in image_reports:
        image_name = image_report["image_name"]
        image_label = image_report["display_name"]
        detections = image_report["detections"]
        bbox_rel = relative_asset_path(report_path, image_report["bbox_path"])
        image_display_groups = select_top_display_groups(
            detections,
            display_groups,
            group_reducer,
        )

        lines.append(f"##### `{image_label}` ({len(detections)} vi tri Leanbot)")
        lines.append("| Anh BBox |")
        lines.append("| :---: |")
        lines.append(f"| ![{image_name} bbox]({bbox_rel}) |")
        lines.append("")

        if not detections:
            lines.append("Khong phat hien object nao.")
            lines.append("")
            lines.append("---")
            lines.append("")
            continue

        header = ["Vị trí", "BBox (Xc, Yc, W, H)", "Best Class", "Độ lớn Vector", "Góc ước lượng"]
        header.extend(group.label for group in image_display_groups)
        lines.append("| " + " | ".join(header) + " |")
        lines.append("|" + "|".join(["---"] * len(header)) + "|")

        for row_index, detection in enumerate(detections, start=1):
            class_scores = detection["class_scores"]
            estimated_angle, magnitude = estimate_angle_from_scores(class_scores)

            row_cells = [f"#{row_index}", format_bbox_xywh(detection["bbox_xyxy"])]
            row_cells.append(f"`{detection['best_cls']}` ({detection['best_conf']:.4f})")
            row_cells.append(f"{magnitude:.4f}")
            row_cells.append("" if estimated_angle is None else f"{estimated_angle:.1f}°")
            
            for group in image_display_groups:
                value = group_score(class_scores, group, group_reducer)
                cell = fmt_score(value)
                row_cells.append(cell)

            lines.append("| " + " | ".join(row_cells) + " |")

        lines.append("")
        lines.append("---")
        lines.append("")

    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()

    source_path = resolve_cli_path(args.source, must_exist=True, label="source")

    images = collect_images(source_path)
    if not images:
        raise SystemExit(f"[ERROR] Khong tim thay anh nao trong: {source_path}")

    model_path = resolve_model_path(args.model)
    output_dir = resolve_output_dir(source_path, args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / args.report_name

    print(f"[INFO] Source    : {source_path}")
    print(f"[INFO] Model     : {model_path}")
    print(f"[INFO] Output dir: {output_dir}")

    model = YOLO(str(model_path))
    names_map = model.names
    model_names = [names_map[idx] for idx in sorted(names_map)]
    display_groups = build_display_groups(model_names, args.display_groups)

    image_reports: list[dict] = []
    multiple_images = len(images) > 1

    for image_path in images:
        frame = cv2.imread(str(image_path))
        if frame is None:
            print(f"[SKIP] Khong doc duoc anh: {image_path}")
            continue

        bbox_image = render_webcam_style_bbox_image(model, frame, args)
        detections = run_low_level_inference(model, frame, args)

        if source_path.is_dir():
            relative_image = image_path.relative_to(source_path)
        else:
            relative_image = Path(image_path.name)

        out_subdir = output_dir / relative_image.parent
        out_subdir.mkdir(parents=True, exist_ok=True)

        stem = relative_image.stem
        bbox_path = out_subdir / f"{stem}_bbox.jpg"
        cv2.imwrite(str(bbox_path), bbox_image)

        display_name = relative_image.as_posix() if multiple_images else image_path.name
        image_reports.append(
            {
                "image_name": stem,
                "display_name": display_name,
                "bbox_path": bbox_path,
                "detections": detections,
            }
        )
        print(f"[OK] {image_path.name}: {len(detections)} detections")

    if not image_reports:
        raise SystemExit("[ERROR] Khong tao duoc report nao.")

    write_markdown_report(
        report_path=report_path,
        source_path=source_path,
        model_path=model_path,
        display_groups=display_groups,
        group_reducer=args.group_reducer,
        image_reports=image_reports,
    )

    print(f"[DONE] Markdown report: {report_path}")
    print(f"[DONE] Assets dir: {output_dir}")


if __name__ == "__main__":
    main()
