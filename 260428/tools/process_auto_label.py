from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2

from auto_label_core import (
    PREVIEW_HEIGHT,
    PREVIEW_WIDTH,
    TOOL1_OUTPUT_ROOT,
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
    print_processing_configuration,
    resolve_capture_session,
    save_config_dict,
    save_detection_outputs,
    save_roi_preview,
)
from alignment import ImageAligner


def build_parser():
    parser = argparse.ArgumentParser(
        description="Read raw_image/session_X and export auto-label results to tool1_output/session_X."
    )
    parser.add_argument(
        "--session",
        default=None,
        help="Session name, full path, or 'latest'. Default: process all sessions in raw_image.",
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
    add_processing_arguments(parser)
    return parser


def choose_background(backgrounds, background_index: int):
    if not backgrounds:
        raise FileNotFoundError("No background images were found in the input session.")
    if background_index < 0 or background_index >= len(backgrounds):
        raise IndexError(
            f"background_index={background_index} is out of range. "
            f"Available backgrounds: 0..{len(backgrounds) - 1}"
        )
    return backgrounds[background_index]


def prepare_session_context(session_dir: Path, output_paths: dict[str, Path], args):
    backgrounds = load_background_images(session_dir)
    background_path, background_image = choose_background(backgrounds, args.background_index)

    output_session_dir = output_paths["session_dir"]
    config_path = output_session_dir / "config.npy"
    old_config = load_config_dict(config_path)

    roi_points, roi_config = ensure_roi_points(
        output_session_dir=output_session_dir,
        background_path=background_path,
        background_image=background_image,
        reset_roi=args.reset_roi,
    )

    board_mask = build_mask(background_image.shape, roi_points)
    bg_masked = cv2.bitwise_and(background_image, background_image, mask=board_mask)

    aligner = ImageAligner()
    aligner.set_template(bg_masked)

    config = build_processing_config(
        args=args,
        input_session_dir=session_dir,
        output_session_dir=output_session_dir,
        background_path=background_path,
        roi_points=roi_points,
    )
    if old_config.get("roi_points") and not args.reset_roi:
        config["roi_points"] = old_config["roi_points"]
        config["roi_background_path"] = old_config.get("roi_background_path", str(background_path))
    else:
        config["roi_background_path"] = str(background_path)
    config["background_count"] = len(backgrounds)
    config["raw_image_count"] = len(load_raw_images(session_dir))
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

    output_paths = create_output_session_dir(session_name)
    print(f"\n>>> Processing {session_name}")
    print(f"    Input : {session_dir}")
    print(f"    Output: {output_paths['session_dir']}")

    try:
        bg_masked, board_mask, aligner, config = prepare_session_context(session_dir, output_paths, args)
    except Exception as exc:
        print(f"   [FAIL] Could not prepare session context: {exc}")
        return {"images": 0, "positive": 0, "negative": 0, "failed": len(raw_images)}

    detection_kwargs = build_detection_kwargs(args)

    summary = {"images": 0, "positive": 0, "negative": 0, "failed": 0}
    for image_path, frame in raw_images:
        base_name = image_path.stem
        summary["images"] += 1

        aligned_img, bboxes, diff_mask = detect_leanbot(
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
            class_id=args.class_id,
        )

        if not bboxes:
            summary["negative"] += 1
            print(f"   [EMPTY] {base_name}: empty label saved.")
            continue

        summary["positive"] += 1
        print(f"   [OK] {base_name}: {len(bboxes)} Leanbot")

    config["summary"] = summary
    save_config_dict(output_paths["session_dir"] / "config.npy", config)
    return summary


def build_shared_config(args, sessions_processed: list[str], total: dict) -> dict:
    """Build a shared JSON config summarizing the processing run."""
    mode_names = {"1": "GRAY", "2": "MIX", "3": "HUE"}
    return {
        "created_at": now_stamp(),
        "diff_mode": mode_names.get(args.diff_mode, args.diff_mode),
        "threshold": args.threshold,
        "blur": args.blur,
        "min_area": args.min_area,
        "max_area": args.max_area,
        "min_width": args.min_width,
        "max_width": args.max_width,
        "min_height": args.min_height,
        "max_height": args.max_height,
        "merge_dist": args.merge_dist,
        "class_id": args.class_id,
        "background_index": args.background_index,
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

    ensure_process_root()
    sessions = resolve_capture_session(args.session)
    if not sessions:
        print("[INFO] No sessions found in raw_image.")
        return 0

    print_processing_configuration(args)

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
        config_json_path = TOOL1_OUTPUT_ROOT / "processing_config.json"
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
