from __future__ import annotations

import argparse

import cv2

from auto_label_core import (
    capture_session_frames,
    create_capture_session_dir,
    parse_source,
    save_capture_session_report,
    setup_camera,
)


def build_parser():
    parser = argparse.ArgumentParser(
        description="Capture multiple backgrounds and raw images into raw_image/session_X."
    )
    parser.add_argument("--source", default="0", help="Camera source")
    parser.add_argument(
        "--session_name",
        default=None,
        help="Optional session name. Default: session_YYYYMMDD_HHMMSS",
    )
    parser.add_argument("--class_name", default="Leanbot", help="Name of the class being captured")
    parser.add_argument("--class_id", type=int, default=0, help="ID of the class being captured")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    cap = None
    try:
        session_id, session_dir, backgrounds_dir, raw_dir = create_capture_session_dir(args.session_name)
        print(f"\n[NEW SESSION] {session_id}")
        print(f"[INFO] Session folder: {session_dir}")

        cap = setup_camera(parse_source(args.source))
        result = capture_session_frames(cap, session_id, backgrounds_dir, raw_dir)

        manifest = save_capture_session_report(session_dir, class_name=args.class_name, class_id=args.class_id)
        print(f"\n[FINISH] Session saved: {session_dir}")
        print(f"[FINISH] Class: {manifest['class_name']} (ID: {manifest['class_id']})")
        print(f"[FINISH] Background images: {manifest['background_count']}")
        print(f"[FINISH] Raw images: {manifest['raw_image_count']}")
        print(f"[FINISH] Metadata: {session_dir / 'session_metadata.json'}")
        if result["user_quit"]:
            print("[INFO] Capture stopped by user with 'q'.")
    finally:
        if cap is not None:
            cap.release()
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
