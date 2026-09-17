import pandas as pd
import matplotlib.pyplot as plt
import argparse
import sys
from pathlib import Path

# Fix UTF-8 output
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

def main():
    parser = argparse.ArgumentParser(description="Ve bieu do Hieu nang (FPS, CPU, Conf)")
    parser.add_argument("csv_path", type=str)
    args = parser.parse_args()

    csv_file = Path(args.csv_path)
    if not csv_file.exists():
        print(f"Khong tim thay file: {csv_file}")
        return

    df = pd.read_csv(csv_file)
    if df.empty:
        print("File CSV rong!")
        return

    fig, axes = plt.subplots(3, 1, figsize=(10, 12), sharex=True)
    
    # 1. FPS
    if 'fps' in df.columns:
        axes[0].plot(df['frame_id'], df['fps'], 'b-', label='FPS', linewidth=1.5)
        axes[0].set_ylabel('FPS')
        axes[0].grid(True, linestyle='--', alpha=0.7)
        axes[0].legend(loc='lower right')
        axes[0].set_title("Inference FPS")
    
    # 2. CPU
    if 'cpu_load_pct' in df.columns:
        axes[1].plot(df['frame_id'], df['cpu_load_pct'], 'r-', label='CPU Load (%)', linewidth=1.5)
        axes[1].set_ylabel('CPU (%)')
        axes[1].grid(True, linestyle='--', alpha=0.7)
        axes[1].legend(loc='upper right')
        axes[1].set_title("CPU Usage (per Core)")

    # 3. Confidence
    if 'best_conf' in df.columns:
        axes[2].plot(df['frame_id'], df['best_conf'], 'g-', label='Confidence', linewidth=1.5)
        axes[2].set_ylabel('Score (0-1)')
        axes[2].set_ylim(0, 1.05)
        axes[2].grid(True, linestyle='--', alpha=0.7)
        axes[2].legend(loc='lower right')
        axes[2].set_xlabel('Frame ID')
        axes[2].set_title("Detection Confidence")
    
    plt.tight_layout()
    out_img = csv_file.parent / f"{csv_file.stem}_performance.png"
    plt.savefig(out_img, dpi=150)
    print(f"Saved performance plot to: {out_img}")

if __name__ == '__main__':
    main()
