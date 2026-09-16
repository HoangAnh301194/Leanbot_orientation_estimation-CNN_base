import argparse
import shutil
import tempfile
from pathlib import Path

from ultralytics import YOLO


def parse_args():
    parser = argparse.ArgumentParser(
        description="Export a YOLO FP32 .pt model to OpenVINO FP16."
    )
    parser.add_argument(
        "--model",
        required=True,
        type=Path,
        help="Path to the input FP32 .pt model.",
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        choices=(160, 640),
        default=640,
        help="Export image size: 160 or 640 (default: 640).",
    )
    nms_group = parser.add_mutually_exclusive_group()
    nms_group.add_argument(
        "--nms",
        dest="nms",
        action="store_true",
        help="Include an NMS block in the exported model (default).",
    )
    nms_group.add_argument(
        "--no-nms",
        dest="nms",
        action="store_false",
        help="Export the model without an NMS block.",
    )
    parser.set_defaults(nms=True)
    return parser.parse_args()


def main():
    args = parse_args()
    model_path = args.model.expanduser().resolve()

    if not model_path.is_file():
        raise FileNotFoundError(f"Model not found: {model_path}")
    if model_path.suffix.lower() != ".pt":
        raise ValueError(f"Input model must be a .pt file: {model_path}")

    nms_name = "nms" if args.nms else "no_nms"
    export_stem = f"{model_path.stem}_fp16_{nms_name}_imgsz{args.imgsz}"
    destination = model_path.parent / f"{export_stem}_openvino_model"

    if destination.exists():
        raise FileExistsError(
            f"Output directory already exists: {destination}. Remove or rename it first."
        )

    print(f"[INFO] FP32 model: {model_path}")
    print(f"[INFO] Export: OpenVINO, FP16, NMS={args.nms}, imgsz={args.imgsz}")

    with tempfile.TemporaryDirectory(prefix="openvino_export_") as temp_dir:
        temp_model_path = Path(temp_dir) / f"{export_stem}.pt"
        shutil.copy2(model_path, temp_model_path)

        model = YOLO(temp_model_path)
        exported_path = Path(
            model.export(
                format="openvino",
                imgsz=args.imgsz,
                half=True,
                nms=args.nms,
            )
        )
        shutil.move(str(exported_path), str(destination))

    print(f"[SUCCESS] Export completed: {destination}")


if __name__ == "__main__":
    main()
