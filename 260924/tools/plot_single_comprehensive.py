import pandas as pd
import matplotlib.pyplot as plt
import argparse
import os
import sys
import numpy as np
from pathlib import Path

# Fix UTF-8 output
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

COLOR_MAIN = 'blue'

def autolabel(ax, rects):
    for rect in rects:
        height = rect.get_height()
        ax.annotate(f'{height:.2f}',
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha='center', va='bottom')

def main():
    parser = argparse.ArgumentParser(description="Generate comprehensive plots for a single log file")
    parser.add_argument("log", help="Path to the CSV log file")
    parser.add_argument("--out-dir", default="leanbot_colab/plots", help="Output directory")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    if not os.path.exists(args.log):
        print(f"[ERROR] Could not find log file: {args.log}")
        return

    df = pd.read_csv(args.log)
    print("[INFO] Generating plots...")

    frames = range(len(df))

    # 1. Trajectory (Angle & X,Y Center)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)
    fig.suptitle("Trajectory & Angle Progression", fontsize=16, fontweight='bold')
    
    unwrapped_angle = np.degrees(np.unwrap(np.radians(df['angle'])))
    ax1.plot(frames, unwrapped_angle, color='green', marker='.', linestyle='-', label='Angle (deg)', linewidth=1.5)
    ax1.set_ylabel("Degrees")
    ax1.set_title("Angle Progression")
    ax1.legend()
    ax1.grid(True)

    ax2.plot(frames, df['x_center'], color='blue', alpha=0.8, marker='.', linestyle='-', label='X Center', linewidth=1.5)
    ax2.plot(frames, df['y_center'], color='red', alpha=0.8, marker='.', linestyle='-', label='Y Center', linewidth=1.5)
    ax2.set_xlabel("Frames from start")
    ax2.set_ylabel("Pixels")
    ax2.set_title("Object Center Trajectory (X, Y)")
    ax2.legend()
    ax2.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(args.out_dir, "1_trajectory.png"))
    plt.close()

    # 2. CPU Load Comparison (Line chart)
    plt.figure(figsize=(10, 5))
    if 'cpu_load_pct' in df.columns:
        plt.plot(frames, df['cpu_load_pct'], label='CPU Load', color=COLOR_MAIN, alpha=0.7)
    plt.xlabel("Frames from start")
    plt.ylabel("CPU Load (%)")
    plt.title("CPU Load over Time")
    plt.legend()
    plt.grid(True)
    plt.savefig(os.path.join(args.out_dir, "2_cpu_load.png"))
    plt.close()

    # 3. FPS Comparison (Line chart)
    plt.figure(figsize=(10, 5))
    if 'fps' in df.columns:
        plt.plot(frames, df['fps'], label='FPS', color='orange', alpha=0.7)
    plt.xlabel("Frames from start")
    plt.ylabel("FPS")
    plt.title("FPS over Time")
    plt.legend()
    plt.grid(True)
    plt.savefig(os.path.join(args.out_dir, "3_fps.png"))
    plt.close()

    # 4. Time Comparison (Bar chart)
    fig, ax = plt.subplots(figsize=(8, 6))
    labels = ['Inference Time', 'End-to-End Time']
    times = [df['inf_time_ms'].mean() if 'inf_time_ms' in df.columns else 0, 
             df['end_to_end_time_ms'].mean() if 'end_to_end_time_ms' in df.columns else 0]
    
    x = np.arange(len(labels))
    width = 0.5
    
    rects1 = ax.bar(x, times, width, color=COLOR_MAIN, alpha=0.7)
    
    ax.set_ylabel('Time (ms)')
    ax.set_title('Average Processing Time')
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    autolabel(ax, rects1)
    plt.tight_layout()
    plt.savefig(os.path.join(args.out_dir, "4_time_barchart.png"))
    plt.close()

    # 5. Tracking Lost over Frames (Bar chart/stem plot)
    plt.figure(figsize=(12, 4))
    if 'tracking_lost' in df.columns:
        lost_frames = df[df['tracking_lost'] == 1].index
        plt.vlines(x=lost_frames, ymin=0, ymax=1, colors='red', linewidth=2, label='Lost Tracking')
        plt.ylim(0, 1.2)
        plt.yticks([0, 1], ['Tracked', 'Lost'])
    plt.xlabel("Frames from start")
    plt.title("Tracking Lost Events over Time")
    plt.legend()
    plt.grid(True, axis='x', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig(os.path.join(args.out_dir, "5_tracking_lost.png"))
    plt.close()

    print(f"[INFO] Complete! 5 plots saved to: {os.path.abspath(args.out_dir)}")

if __name__ == '__main__':
    main()
