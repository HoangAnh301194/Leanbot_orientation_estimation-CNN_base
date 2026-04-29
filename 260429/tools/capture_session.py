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

        manifest = save_capture_session_report(session_dir)
        print(f"\n[FINISH] Session saved: {session_dir}")
        print(f"[FINISH] Background images: {manifest['background_count']}")
        print(f"[FINISH] Raw images: {manifest['raw_image_count']}")
        print(f"[FINISH] Report: {session_dir / 'session_structure.txt'}")
        if result["user_quit"]:
            print("[INFO] Capture stopped by user with 'q'.")
    finally:
        if cap is not None:
            cap.release()
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
