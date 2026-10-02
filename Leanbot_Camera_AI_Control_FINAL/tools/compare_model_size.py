import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt


MODEL_SUFFIXES = {".xml", ".bin", ".yaml"}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Compare total OpenVINO model size (.xml + .bin + metadata.yaml)."
    )
    parser.add_argument(
        "--model-dir",
        action="append",
        required=True,
        type=Path,
        help="OpenVINO model directory. Repeat for every model.",
    )
    parser.add_argument(
        "--label",
        action="append",
        required=True,
        help="Display label. Repeat in the same order as --model-dir.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("benchmark/model_size_comparison.png"),
        help="Output PNG path.",
    )
    parser.add_argument(
        "--csv-output",
        type=Path,
        default=None,
        help="Optional CSV output path. Defaults next to the PNG.",
    )
    return parser.parse_args()


def collect_model_size(model_dir):
    model_dir = model_dir.expanduser().resolve()
    if not model_dir.is_dir():
        raise FileNotFoundError(f"Model directory not found: {model_dir}")

    files = []
    for path in model_dir.iterdir():
        if not path.is_file():
            continue
        if path.suffix.lower() in MODEL_SUFFIXES:
            files.append(path)

    xml_files = [path for path in files if path.suffix.lower() == ".xml"]
    bin_files = [path for path in files if path.suffix.lower() == ".bin"]
    metadata_files = [path for path in files if path.name.lower() == "metadata.yaml"]
    if len(xml_files) != 1 or len(bin_files) != 1 or len(metadata_files) != 1:
        raise ValueError(
            f"Expected one .xml, one .bin and one metadata.yaml in {model_dir}; "
            f"found xml={len(xml_files)}, bin={len(bin_files)}, metadata={len(metadata_files)}"
        )

    component_sizes = {
        "XML": xml_files[0].stat().st_size,
        "BIN": bin_files[0].stat().st_size,
        "Metadata": metadata_files[0].stat().st_size,
    }
    return model_dir, component_sizes


def main():
    args = parse_args()
    if len(args.model_dir) != len(args.label):
        raise SystemExit("--model-dir and --label must be provided the same number of times.")

    records = []
    for label, model_dir in zip(args.label, args.model_dir):
        resolved_dir, sizes = collect_model_size(model_dir)
        total_bytes = sum(sizes.values())
        records.append(
            {
                "label": label,
                "model_dir": str(resolved_dir),
                "xml_bytes": sizes["XML"],
                "bin_bytes": sizes["BIN"],
                "metadata_bytes": sizes["Metadata"],
                "total_bytes": total_bytes,
                "total_mib": total_bytes / (1024 * 1024),
            }
        )

    output_path = args.output.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path = (
        args.csv_output.expanduser().resolve()
        if args.csv_output
        else output_path.with_suffix(".csv")
    )
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    labels = [record["label"] for record in records]
    sizes_mib = [record["total_mib"] for record in records]
    colors = ["#4c78a8", "#f58518", "#54a24b", "#e45756", "#72b7b2", "#b279a2"]

    figure_width = max(8, len(records) * 2.2)
    _, axis = plt.subplots(figsize=(figure_width, 6))
    bars = axis.bar(labels, sizes_mib, color=colors[: len(records)])
    axis.set_title("OpenVINO Model Size Comparison")
    axis.set_ylabel("Total size (MiB)")
    axis.set_xlabel("Model")
    axis.grid(axis="y", linestyle="--", alpha=0.4)

    max_size = max(sizes_mib) if sizes_mib else 0
    axis.set_ylim(0, max_size * 1.18 if max_size else 1)
    for bar, size_mib in zip(bars, sizes_mib):
        axis.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{size_mib:.3f} MiB",
            ha="center",
            va="bottom",
        )

    plt.tight_layout()
    plt.savefig(output_path, dpi=180)
    plt.close()

    with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
        fieldnames = list(records[0].keys())
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    for record in records:
        print(f"{record['label']}: {record['total_mib']:.3f} MiB")
    print(f"PNG: {output_path}")
    print(f"CSV: {csv_path}")


if __name__ == "__main__":
    main()
