import argparse


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train YOLOv8 tren dataset custom.")
    parser.add_argument("--data", default="configs/leanbot_data.yaml", help="File yaml cua dataset.")
    parser.add_argument("--model", default="yolov8n.pt", help="Model pretrained de fine-tune.")
    parser.add_argument("--epochs", type=int, default=50, help="So epoch train.")
    parser.add_argument("--imgsz", type=int, default=640, help="Kich thuoc anh train.")
    parser.add_argument("--batch", type=int, default=8, help="Batch size.")
    parser.add_argument(
        "--degrees",
        type=float,
        default=10.0,
        help="Goc xoay ngau nhien toi da theo moi chieu, vi du 10 = xoay trong khoang [-10, 10].",
    )
    parser.add_argument(
        "--fliplr",
        type=float,
        default=0.5,
        help="Xac suat lat ngang ngau nhien cho moi anh train.",
    )
    parser.add_argument(
        "--flipud",
        type=float,
        default=0.1,
        help="Xac suat lat doc ngau nhien cho moi anh train.",
    )
    parser.add_argument(
        "--name",
        default="leanbot_demo",
        help="Ten run de luu ket qua trong runs/detect.",
    )
    parser.add_argument(
        "--device",
        default="cpu",
        help="Thiet bi train, vi du: cpu, 0, 0,1. Mac dinh dung cpu de chay tren may local.",
    )
    return parser.parse_args()


def train_model() -> None:
    args = parse_args()

    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise SystemExit(
            "Chua cai ultralytics. Hay cai dependency truoc khi train, "
            "vi du: venv/bin/pip install -r requirements.txt"
        ) from exc

    model = YOLO(args.model)
    model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        degrees=args.degrees,
        fliplr=args.fliplr,
        flipud=args.flipud,
        device=args.device,
        name=args.name,
    )


if __name__ == "__main__":
    train_model()
