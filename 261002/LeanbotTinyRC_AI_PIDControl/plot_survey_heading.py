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
            # New survey logs keep BLE verification failures in the summary
            # CSV for traceability. They must not enter heading statistics.
            status = row.get("status", "OK").strip().upper()
            heading_text = row.get("heading", "").strip()
            if status != "OK" or not heading_text:
                continue

            records.append({
                "direction": int(row["direction"]),
                "steps": int(row["steps"]),
                "signed_steps": int(row["signed_steps"]),
                "intervalMs": int(row["intervalMs"]),
                "heading": float(heading_text),
                "duration": float(row["duration"])
            })

    # Phân tách dữ liệu: đi và về
    dir_0 = [r for r in records if r["direction"] == 0]
    dir_1 = [r for r in records if r["direction"] == 1]
    dir_neg1 = [r for r in records if r["direction"] == -1]

    def get_summary(data):
        unique_s = sorted(list(set(r["steps"] for r in data)))
        sum_list = []
        for s in unique_s:
            items = [r for r in data if r["steps"] == s]
            rads = np.radians([r["heading"] for r in items])
            avg = float(np.degrees(np.arctan2(np.mean(np.sin(rads)), np.mean(np.cos(rads)))))
            sum_list.append((s, avg))
        return sum_list

    base_val = get_summary(dir_0)[0][1] if get_summary(dir_0) else 0.0
    
    fwd_summary = [(0, base_val)] + get_summary(dir_1)
    bwd_summary = [(0, base_val)] + get_summary(dir_neg1)

    output_dir = csv_path.parent
    base_name = csv_path.stem

    # Plot 1
    plt.figure(figsize=(11, 6))
    unique_signed_steps = sorted(list(set(r["signed_steps"] for r in records)))
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
    
    fwd_x = np.array([s[0] for s in fwd_summary])
    fwd_y = np.array([s[1] for s in fwd_summary])
    bwd_x = np.array([s[0] for s in bwd_summary])
    bwd_y = np.array([s[1] for s in bwd_summary])
    
    # Plot Lượt đi (Nét liền)
    if len(fwd_x) > 1:
        p = np.polyfit(fwd_x, fwd_y, 1)
        y_fit = np.polyval(p, fwd_x)
        r2 = 1.0 - np.sum((fwd_y - y_fit)**2) / np.sum((fwd_y - np.mean(fwd_y))**2)
        plt.plot(fwd_x, y_fit, color='#d90429', linestyle='-', linewidth=1.5, alpha=0.5, label=f"Fit Đi: y = {p[0]:.4f}x + {p[1]:.2f} (R² = {r2:.4f})")
    
    plt.plot(fwd_x, fwd_y, marker='s', color='#0055d4', linewidth=2.0, label="Lượt đi (Quay xa dần tâm)")
    
    # Plot Lượt về (Nét đứt)
    plt.plot(bwd_x, bwd_y, marker='o', color='#ff8c00', linestyle='--', linewidth=2.0, label="Lượt về (Góc khi đã về lại tâm)")
    
    # Đường chuẩn (Initial heading)
    plt.axhline(y=base_val, color='gray', linestyle=':', alpha=0.7, label=f"Góc ban đầu (Base: {base_val:.2f}°)")

    plt.title("Phân tích Heading: Lượt đi (Spin Out) vs Lượt về (Return to Center)")
    plt.xlabel("Số bước Spin (n steps)")
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
