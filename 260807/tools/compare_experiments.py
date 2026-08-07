import argparse
import os

import matplotlib.pyplot as plt
import pandas as pd


def tracking_lost_count(dataframe):
    if "tracking_lost" in dataframe.columns:
        return int(dataframe["tracking_lost"].sum())
    if "lost_count" in dataframe.columns and not dataframe.empty:
        return int(dataframe["lost_count"].iloc[-1])
    return 0


def save_line_plot(first_values, second_values, first_label, second_label,
                   ylabel, title, output_path):
    plt.figure(figsize=(10, 5))
    plt.plot(range(len(second_values)), second_values, label=second_label, alpha=0.7)
    plt.plot(range(len(first_values)), first_values, label=first_label, alpha=0.7)
    plt.xlabel("Frames from start")
    plt.ylabel(ylabel)
    plt.title(title)
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()


def main():
    parser = argparse.ArgumentParser(description="Compare benchmark logs from two models")
    parser.add_argument("--roi-log", required=True, help="CSV log for the first model")
    parser.add_argument("--baseline-log", required=True, help="CSV log for the second model")
    parser.add_argument("--roi-label", default="Model 1", help="Display name for the first model")
    parser.add_argument("--baseline-label", default="Model 2", help="Display name for the second model")
    parser.add_argument("--out-dir", default="benchmark", help="Directory for generated plots")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    first_data = pd.read_csv(args.roi_log)
    second_data = pd.read_csv(args.baseline_log)

    metrics = [
        ("Average FPS", "fps", "FPS"),
        ("Average inference time", "inf_time_ms", "ms"),
        ("Average CPU load", "cpu_load_pct", "%"),
        ("Average input width", "input_width", "px"),
    ]

    print("=== AVERAGE COMPARISON ===")
    for title, column, unit in metrics:
        first_average = first_data[column].mean()
        second_average = second_data[column].mean()
        print(f"{title}:")
        print(f"  - {args.roi_label}: {first_average:.2f} {unit}")
        print(f"  - {args.baseline_label}: {second_average:.2f} {unit}")

    print("Tracking-lost frames:")
    print(f"  - {args.roi_label}: {tracking_lost_count(first_data)}")
    print(f"  - {args.baseline_label}: {tracking_lost_count(second_data)}")

    save_line_plot(
        first_data["fps"], second_data["fps"],
        args.roi_label, args.baseline_label,
        "FPS", "FPS comparison",
        os.path.join(args.out_dir, "fps_comparison.png"),
    )
    save_line_plot(
        first_data["inf_time_ms"], second_data["inf_time_ms"],
        args.roi_label, args.baseline_label,
        "Inference time (ms)", "Inference time comparison",
        os.path.join(args.out_dir, "inf_time_comparison.png"),
    )
    save_line_plot(
        first_data["cpu_load_pct"], second_data["cpu_load_pct"],
        args.roi_label, args.baseline_label,
        "CPU load (%)", "CPU load comparison",
        os.path.join(args.out_dir, "cpu_load_comparison.png"),
    )

    print(f"Generated 3 plots in: {os.path.abspath(args.out_dir)}")


if __name__ == "__main__":
    main()
