from __future__ import annotations

import argparse

from capture_session import main as capture_main
from process_auto_label import main as process_main


def build_parser():
    parser = argparse.ArgumentParser(
        description="Compatibility wrapper. Use capture_session.py or process_auto_label.py for the split tools."
    )
    parser.add_argument(
        "--mode",
        choices=["capture", "relabel"],
        default="capture",
        help="capture -> capture_session.py, relabel -> process_auto_label.py",
    )
    return parser


def main(argv=None):
    parser = build_parser()
    args, remaining = parser.parse_known_args(argv)

    if args.mode == "capture":
        return capture_main(remaining)
    return process_main(remaining)


if __name__ == "__main__":
    raise SystemExit(main())
