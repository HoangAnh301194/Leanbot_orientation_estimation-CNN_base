from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import cv2

from auto_label_core import (
    PREVIEW_HEIGHT,
    PREVIEW_WIDTH,
    add_processing_arguments,
    build_detection_kwargs,
    build_mask,
    build_processing_config,
    create_output_session_dir,
    detect_leanbot,
    ensure_process_root,
    ensure_roi_points,
    load_background_images,
    load_config_dict,
    load_raw_images,
    now_stamp,
    resolve_capture_session,
    save_config_dict,
    save_detection_outputs,
    save_roi_preview,
)
from alignment import ImageAligner


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PAIRED_OUTPUT_ROOT = PROJECT_ROOT / "tool1_output_paired"
PAIR_INDEX_PATTERN = re.compile(r"(\d+)$")


def resolve_cli_dir(raw_value: str, *, must_exist: bool, label: str) -> Path:
    """Resolve a CLI path relative to the repo root for repo workflows.

    This lets users run the script either from the repo root or from tools/
    without having to rewrite arguments like `datasets/24class/raw_image`.
    """
    raw_path = Path(raw_value).expanduser()
    if raw_path.is_absolute():
        resolved = raw_path.resolve()
    else:
        resolved = (PROJECT_ROOT / raw_path).resolve()

    if must_exist and not resolved.exists():
        raise SystemExit(f"[ERROR] {label} not found: {resolved}")
    return resolved


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Auto-label raw images using the background with the same trailing index "
            "(background_000.jpg <-> *_000.jpg)."
        )
    )
    parser.add_argument(
        "--session",
        nargs="+",
        default=None,
        help="Session name(s), full path, or 'latest'. Default: process all sessions in raw_image.",
    )
    parser.add_argument(
        "--no_preview",
        action="store_true",
        help="Disable OpenCV preview windows while processing.",
    )
    parser.add_argument(
        "--wait_ms",
        type=int,
        default=200,
        help="Preview delay per image in milliseconds.",
    )
    parser.add_argument(
        "--pause_at_end",
        action="store_true",
        help="Keep preview windows open at the end until a key is pressed.",
    )
    parser.add_argument(
        "--raw_dir",
        type=str,
        default=None,
        help="Đường dẫn thư mục chứa ảnh gốc (Thay thế cho raw_image mặc định).",
    )
    parser.add_argument(
        "--out_dir",
        type=str,
        default=None,
        help="Thư mục kết quả (mặc định: tool1_output_paired).",
    )
    add_processing_arguments(parser)
    parser._option_string_actions["--background_index"].help = argparse.SUPPRESS
    parser._option_string_actions["--reset_roi"].help = (
        "Chọn lại ROI trên background của cặp đầu tiên."
    )
    return parser


def print_paired_processing_configuration(args):
    mode_names = {"1": "GRAY (Baseline)", "2": "MIX (Hybrid Hue+Gray)", "3": "HUE (HSV Only)"}
    print(f"\n[DEBUG] Algorithm: {mode_names.get(args.diff_mode, 'Unknown')}")
    print("        -> Background: ghép theo hậu tố số của tên file")
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


def extract_pair_index(image_path: Path) -> int:
    match = PAIR_INDEX_PATTERN.search(image_path.stem)
    if not match:
        raise ValueError(f"Tên file không có chỉ số cuối: {image_path.name}")
    return int(match.group(1))


def pair_images_by_index(backgrounds, raw_images):
    background_by_index = {}
    for background_record in backgrounds:
        background_path, _ = background_record
        pair_index = extract_pair_index(background_path)
        if pair_index in background_by_index:
            duplicate_path = background_by_index[pair_index][0]
            raise ValueError(
                f"Trùng background index {pair_index:03d}: "
                f"{duplicate_path.name}, {background_path.name}"
            )
        background_by_index[pair_index] = background_record

    pairs = []
    unmatched_raw_images = []
    for raw_record in raw_images:
        raw_path, _ = raw_record
        pair_index = extract_pair_index(raw_path)
        background_record = background_by_index.get(pair_index)
        if background_record is None:
            unmatched_raw_images.append(raw_record)
            continue
        pairs.append((pair_index, background_record, raw_record))

    return pairs, unmatched_raw_images


def prepare_pair_context(
    session_dir: Path,
    output_paths: dict[str, Path],
    args,
    background_path: Path,
    background_image,
    effective_class_id: int,
    reset_roi: bool,
):

    output_session_dir = output_paths["session_dir"]
    config_path = output_session_dir / "config.npy"
    old_config = load_config_dict(config_path)

    roi_points, roi_config = ensure_roi_points(
        output_session_dir=output_session_dir,
        background_path=background_path,
        background_image=background_image,
        reset_roi=reset_roi,
    )

    board_mask = build_mask(background_image.shape, roi_points)
    bg_masked = cv2.bitwise_and(background_image, background_image, mask=board_mask)

    aligner = ImageAligner()
    aligner.set_template(bg_masked)

    # Temporarily override args.class_id for building config if effective_class_id is provided
    original_class_id = args.class_id
    if effective_class_id is not None:
        args.class_id = effective_class_id

    config = build_processing_config(
        args=args,
        input_session_dir=session_dir,
        output_session_dir=output_session_dir,
        background_path=background_path,
        roi_points=roi_points,
    )
    # Restore original args.class_id
    args.class_id = original_class_id
    if old_config.get("roi_points") and not reset_roi:
        config["roi_points"] = old_config["roi_points"]
        config["roi_background_path"] = old_config.get("roi_background_path", str(background_path))
    else:
        config["roi_background_path"] = str(background_path)
    config["background_count"] = len(load_background_images(session_dir))
    config["raw_image_count"] = len(load_raw_images(session_dir))
    config["background_mode"] = "paired_by_trailing_index"
    save_config_dict(config_path, config)

    save_roi_preview(background_image, roi_points, output_session_dir / "roi_preview.jpg")
    return bg_masked, board_mask, aligner, config


def show_debug_preview(diff_mask, aligned_img, bboxes, wait_ms: int):
    vis_bbox = aligned_img.copy()
    for x, y, w, h in bboxes:
        cv2.rectangle(vis_bbox, (x, y), (x + w, y + h), (0, 255, 0), 3)

    cv2.imshow("3. Difference Mask", cv2.resize(diff_mask, (PREVIEW_WIDTH, PREVIEW_HEIGHT)))
    cv2.imshow("4. Bounding Box Result", cv2.resize(vis_bbox, (PREVIEW_WIDTH, PREVIEW_HEIGHT)))
    cv2.waitKey(wait_ms)


def process_session(session_dir: Path, args):
    session_name = session_dir.name
    backgrounds = load_background_images(session_dir)
    if not backgrounds:
        print(f"\n>>> Skipping {session_name}: no background images found in raw_image/session_X/backgrounds.")
        return {"images": 0, "positive": 0, "negative": 0, "failed": 0}

    raw_images = load_raw_images(session_dir)
    if not raw_images:
        print(f"\n>>> Skipping {session_name}: no raw images found in raw_image/session_X/raw_images.")
        return {"images": 0, "positive": 0, "negative": 0, "failed": 0}

    try:
        image_pairs, unmatched_raw_images = pair_images_by_index(backgrounds, raw_images)
    except ValueError as error:
        print(f"\n>>> Skipping {session_name}: {error}")
        return {"images": len(raw_images), "positive": 0, "negative": 0, "failed": len(raw_images)}

    for raw_path, _ in unmatched_raw_images:
        print(f"   [FAIL] Không tìm thấy background cùng chỉ số cho {raw_path.name}")

    if not image_pairs:
        print(f"\n>>> Skipping {session_name}: không có cặp background/raw image hợp lệ.")
        return {"images": len(raw_images), "positive": 0, "negative": 0, "failed": len(raw_images)}

    output_paths = create_output_session_dir(session_name)
    print(f"\n>>> Processing {session_name}")
    
    # Load class metadata if available
    metadata_path = session_dir / "session_metadata.json"
    effective_class_id = args.class_id
    if metadata_path.exists():
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            effective_class_id = metadata.get("class_id", args.class_id)
            class_name = metadata.get("class_name", "unknown")
            print(f"    Class : {class_name} (ID: {effective_class_id}) [from metadata]")
        except Exception:
            print("    [WARN] Could not parse session_metadata.json, using defaults.")
    else:
        print(f"    Class : ID={effective_class_id} [from arguments]")

    print(f"    Input : {session_dir}")
    print(f"    Output: {output_paths['session_dir']}")

    detection_kwargs = build_detection_kwargs(args)
    summary = {
        "images": len(raw_images),
        "positive": 0,
        "negative": 0,
        "failed": len(unmatched_raw_images),
    }
    config = None
    pairing_manifest = []

    for pair_position, (pair_index, background_record, raw_record) in enumerate(image_pairs):
        background_path, background_image = background_record
        image_path, frame = raw_record
        base_name = image_path.stem
        pairing_manifest.append({
            "index": pair_index,
            "background": background_path.name,
            "raw_image": image_path.name,
        })
        print(f"   [PAIR {pair_index:03d}] {image_path.name} <- {background_path.name}")

        try:
            bg_masked, board_mask, aligner, config = prepare_pair_context(
                session_dir=session_dir,
                output_paths=output_paths,
                args=args,
                background_path=background_path,
                background_image=background_image,
                effective_class_id=effective_class_id,
                reset_roi=args.reset_roi and pair_position == 0,
            )
        except Exception as error:
            summary["failed"] += 1
            print(f"   [FAIL] {base_name}: không thể chuẩn bị background: {error}")
            continue

        aligned_img, bboxes, diff_mask, debug_masks = detect_leanbot(
            frame,
            bg_masked,
            aligner,
            board_mask,
            **detection_kwargs,
        )

        if aligned_img is None or diff_mask is None:
            summary["failed"] += 1
            print(f"   [FAIL] {base_name}: alignment/detection failed.")
            continue

        if not args.no_preview:
            show_debug_preview(diff_mask, aligned_img, bboxes, max(1, args.wait_ms))

        save_detection_outputs(
            output_paths=output_paths,
            base_name=base_name,
            aligned_img=aligned_img,
            diff_mask=diff_mask,
            bboxes=bboxes,
            class_id=effective_class_id,
            debug_masks=debug_masks,
        )

        if not bboxes:
            summary["negative"] += 1
            print(f"   [EMPTY] {base_name}: empty label saved.")
            continue

        summary["positive"] += 1
        print(f"   [OK] {base_name}: {len(bboxes)} Leanbot")

    if config is not None:
        config["summary"] = summary
        config["background_pairing"] = pairing_manifest
        save_config_dict(output_paths["session_dir"] / "config.npy", config)
    return summary


def build_shared_config(args, sessions_processed: list[str], total: dict) -> dict:
    """Build a shared JSON config summarizing the processing run."""
    mode_names = {"1": "GRAY", "2": "MIX", "3": "HUE"}
    return {
        "created_at": now_stamp(),
        "merge_method": "mask-based",
        "mask_merge_kernel": args.mask_merge_kernel,
        "mask_merge_iterations": args.mask_merge_iterations,
        "diff_mode": mode_names.get(args.diff_mode, args.diff_mode),
        "threshold": args.threshold,
        "blur": args.blur,
        "min_area": args.min_area,
        "max_area": args.max_area,
        "min_width": args.min_width,
        "max_width": args.max_width,
        "min_height": args.min_height,
        "max_height": args.max_height,
        "class_id": args.class_id,
        "background_mode": "paired_by_trailing_index",
        "w_gray": args.w_gray,
        "w_hue": args.w_hue,
        "w_h": args.w_h,
        "w_s": args.w_s,
        "w_v": args.w_v,
        "sessions_processed": sessions_processed,
        "summary": total,
    }


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    import auto_label_core
    if args.raw_dir:
        auto_label_core.RAW_IMAGE_ROOT = resolve_cli_dir(
            args.raw_dir,
            must_exist=True,
            label="Raw dir",
        )
    if args.out_dir:
        auto_label_core.TOOL1_OUTPUT_ROOT = resolve_cli_dir(
            args.out_dir,
            must_exist=False,
            label="Output dir",
        )
    else:
        auto_label_core.TOOL1_OUTPUT_ROOT = DEFAULT_PAIRED_OUTPUT_ROOT

    ensure_process_root()
    print(f"[INFO] Raw root   : {auto_label_core.RAW_IMAGE_ROOT}")
    print(f"[INFO] Output root: {auto_label_core.TOOL1_OUTPUT_ROOT}")

    sessions = resolve_capture_session(args.session)
    if not sessions:
        print(f"[INFO] No session/class folders found in: {auto_label_core.RAW_IMAGE_ROOT}")
        print("[INFO] Expected each subfolder to contain raw_images/ and backgrounds/.")
        return 0

    print_paired_processing_configuration(args)
    print(f"        -> Merge: Mask-Based (kernel={args.mask_merge_kernel}, iterations={args.mask_merge_iterations})")

    total = {"sessions": 0, "images": 0, "positive": 0, "negative": 0, "failed": 0}
    sessions_processed = []
    try:
        for session_dir in sessions:
            summary = process_session(session_dir, args)
            total["sessions"] += 1
            total["images"] += summary["images"]
            total["positive"] += summary["positive"]
            total["negative"] += summary["negative"]
            total["failed"] += summary["failed"]
            sessions_processed.append(session_dir.name)

        print("\n[SUMMARY]")
        print(f"Sessions processed : {total['sessions']}")
        print(f"Images processed   : {total['images']}")
        print(f"Positive labels    : {total['positive']}")
        print(f"Negative labels    : {total['negative']}")
        print(f"Failed images      : {total['failed']}")

        # Save shared config JSON at tool1_output root
        shared_config = build_shared_config(args, sessions_processed, total)
        config_json_path = auto_label_core.TOOL1_OUTPUT_ROOT / "processing_config.json"
        config_json_path.write_text(
            json.dumps(shared_config, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"\n[INFO] Config saved: {config_json_path}")

        if args.pause_at_end and not args.no_preview:
            print("\n[INFO] Press any key in a preview window to close.")
            cv2.waitKey(0)
    finally:
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
