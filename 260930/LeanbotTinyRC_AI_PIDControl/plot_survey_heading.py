import argparse
import csv
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", required=True, help="Path to the heading survey CSV file")
    args = parser.parse_args()

    csv_path = Path(args.log).resolve()
    if not csv_path.exists():
        print(f"Error: {csv_path} does not exist.")
        return

    records = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append({
                "direction": int(row["direction"]),
                "steps": int(row["steps"]),
                "signed_steps": int(row["signed_steps"]),
                "intervalMs": int(row["intervalMs"]),
                "heading": float(row["heading"]),
                "duration": float(row["duration"])
            })

    unique_signed_steps = sorted(list(set(r["signed_steps"] for r in records)))
    summary = []
    for s_steps in unique_signed_steps:
        step_items = [r for r in records if r["signed_steps"] == s_steps]
        rads = np.radians([r["heading"] for r in step_items])
        avg_heading = float(np.degrees(np.arctan2(np.mean(np.sin(rads)), np.mean(np.cos(rads)))))
        summary.append({"signed_steps": s_steps, "avg_heading": avg_heading})

    output_dir = csv_path.parent
    base_name = csv_path.stem

    # Plot 1
    plt.figure(figsize=(11, 6))
    for s in unique_signed_steps:
        s_data = [r for r in records if r["signed_steps"] == s]
        plt.plot([r["intervalMs"] for r in s_data], [r["heading"] for r in s_data], marker='o', label=f"steps={s}")
    plt.title("measuredHeading theo intervalMs (Thuận & Nghịch)")
    plt.xlabel("intervalMs (ms)")
    plt.ylabel("measuredHeading (độ)")
    plt.legend(bbox_to_anchor=(1.01, 1), loc='upper left', fontsize='small')
    plt.tight_layout()
    plt.savefig(output_dir / f"{base_name}_plot1_interval.png")
    plt.close()

    # Plot 2
    plt.figure(figsize=(10, 6))
    x_steps = np.array([s["signed_steps"] for s in summary])
    y_headings = np.array([s["avg_heading"] for s in summary])
    
    # Chỉ tính polyfit nếu có hơn 1 điểm dữ liệu
    if len(x_steps) > 1:
        p = np.polyfit(x_steps, y_headings, 1)
        y_fit = np.polyval(p, x_steps)
        r2 = 1.0 - np.sum((y_headings - y_fit)**2) / np.sum((y_headings - np.mean(y_headings))**2)
        fit_label = f"polyFit 1st order: y = {p[0]:.4f}x + {p[1]:.2f} (R² = {r2:.4f})"
        plt.plot(x_steps, y_fit, color='#d90429', linestyle='--', linewidth=2.0, label=fit_label)
    
    plt.plot(x_steps, y_headings, marker='s', color='#0055d4', linewidth=1.8, label="Mean measuredHeading (Thuận & Nghịch)")
    plt.axvline(x=0, color='gray', linestyle=':', alpha=0.7)
    plt.title("Mean measuredHeading / signed_steps & Fit 1st order")
    plt.xlabel("Signed steps (Âm=Nghịch, Dương=Thuận)")
    plt.ylabel("Mean measuredHeading (degree)")
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / f"{base_name}_plot2_steps.png")
    plt.close()

    # Plot 3
    plt.figure(figsize=(9, 5))
    plt.scatter([r["intervalMs"] for r in records], [r["duration"] for r in records], color='orange', alpha=0.5)
    plt.title("Time measureHeading / intervalMs")
    plt.xlabel("intervalMs (ms)")
    plt.ylabel("Time (seconds)")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(output_dir / f"{base_name}_plot3_duration.png")
    plt.close()

    print(f"Generated 3 plots in {output_dir}")

if __name__ == '__main__':
    main()
