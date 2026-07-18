import pandas as pd
import matplotlib.pyplot as plt
import argparse
import os
import sys
import numpy as np

# Fix UTF-8 output
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Define standard colors
COLOR_V8 = 'blue'
COLOR_V8_LIGHT = 'cornflowerblue'
COLOR_V11 = 'orange'
COLOR_V11_LIGHT = 'sandybrown'

def get_dir_size(path='.'):
    total = 0
    if os.path.isfile(path):
        total = os.path.getsize(path)
    elif os.path.isdir(path):
        with os.scandir(path) as it:
            for entry in it:
                if entry.is_file():
                    total += entry.stat().st_size
                elif entry.is_dir():
                    total += get_dir_size(entry.path)
    return total / (1024 * 1024) # MB

def autolabel(ax, rects):
    for rect in rects:
        height = rect.get_height()
        ax.annotate(f'{height:.2f}',
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha='center', va='bottom')

def main():
    parser = argparse.ArgumentParser(description="Generate benchmark plots for YOLOv8n vs YOLO11n")
    parser.add_argument("--v8-log", default=r"benchmark\yolov8n_fp16_roi_tracking.csv")
    parser.add_argument("--v11-log", default=r"benchmark\yolo11n_fp16_roi_tracking.csv")
    parser.add_argument("--v8-full", default=r"models\YOLOv8n_versions\quantized_fp16\best_24Class_Soft_Angular_BCE_openvino_model")
    parser.add_argument("--v8-static", default=r"models\YOLOv8n_versions\best_24Class_Soft_Angular_BCE_static_160_openvino_model")
    parser.add_argument("--v11-full", default=r"models\YOLO11n_versions\quantized_fp16\Soft_Angular_BCE_yolo11n_openvino_model")
    parser.add_argument("--v11-static", default=r"models\YOLO11n_versions\Soft_Angular_BCE_yolo11n_static_160_openvino_model")
    parser.add_argument("--out-dir", default="benchmark", help="Output directory")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    if not os.path.exists(args.v8_log) or not os.path.exists(args.v11_log):
        print("[ERROR] Could not find log files!")
        return

    df_v8 = pd.read_csv(args.v8_log)
    df_v11 = pd.read_csv(args.v11_log)

    print("[INFO] Generating comparison plots...")

    # 1. FPS Comparison (Line chart)
    plt.figure(figsize=(10, 5))
    plt.plot(range(len(df_v8)), df_v8['fps'], label='YOLOv8n', color=COLOR_V8, alpha=0.7)
    plt.plot(range(len(df_v11)), df_v11['fps'], label='YOLO11n', color=COLOR_V11, alpha=0.7)
    plt.xlabel("Frames from start")
    plt.ylabel("FPS")
    plt.title("FPS Comparison")
    plt.legend()
    plt.grid(True)
    plt.savefig(os.path.join(args.out_dir, "1_fps_comparison.png"))
    plt.close()

    # 2. Time Comparison (Bar chart)
    fig, ax = plt.subplots(figsize=(10, 6))
    labels = ['Inference Time', 'End-to-End Time']
    v8_times = [df_v8['inf_time_ms'].mean(), df_v8['end_to_end_time_ms'].mean()]
    v11_times = [df_v11['inf_time_ms'].mean(), df_v11['end_to_end_time_ms'].mean()]
    
    x = np.arange(len(labels))
    width = 0.35
    
    rects1 = ax.bar(x - width/2, v8_times, width, label='YOLOv8n', color=COLOR_V8, alpha=0.7)
    rects2 = ax.bar(x + width/2, v11_times, width, label='YOLO11n', color=COLOR_V11, alpha=0.7)
    
    ax.set_ylabel('Time (ms)')
    ax.set_title('Average Processing Time Comparison')
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.legend()
    autolabel(ax, rects1)
    autolabel(ax, rects2)
    plt.tight_layout()
    plt.savefig(os.path.join(args.out_dir, "2_time_comparison.png"))
    plt.close()

    # 3. CPU Load Comparison (Line chart)
    plt.figure(figsize=(10, 5))
    plt.plot(range(len(df_v8)), df_v8['cpu_load_pct'], label='YOLOv8n', color=COLOR_V8, alpha=0.7)
    plt.plot(range(len(df_v11)), df_v11['cpu_load_pct'], label='YOLO11n', color=COLOR_V11, alpha=0.7)
    plt.xlabel("Frames from start")
    plt.ylabel("CPU Load (%)")
    plt.title("CPU Load Comparison")
    plt.legend()
    plt.grid(True)
    plt.savefig(os.path.join(args.out_dir, "3_cpu_load_comparison.png"))
    plt.close()

    # 4. Tracking Lost Comparison (Bar chart)
    lost_v8 = int(df_v8['tracking_lost'].sum()) if 'tracking_lost' in df_v8.columns else 0
    lost_v11 = int(df_v11['tracking_lost'].sum()) if 'tracking_lost' in df_v11.columns else 0
    
    fig, ax = plt.subplots(figsize=(6, 5))
    rects = ax.bar(['YOLOv8n', 'YOLO11n'], [lost_v8, lost_v11], color=[COLOR_V8, COLOR_V11], alpha=0.7)
    ax.set_ylabel('Lost Frames Count')
    ax.set_title('Tracking Lost Comparison')
    autolabel(ax, rects)
    plt.tight_layout()
    plt.savefig(os.path.join(args.out_dir, "4_tracking_lost_comparison.png"))
    plt.close()

    # 5. Model Size Comparison (Bar chart, 4 columns)
    size_v8_full = get_dir_size(args.v8_full)
    size_v8_static = get_dir_size(args.v8_static)
    size_v11_full = get_dir_size(args.v11_full)
    size_v11_static = get_dir_size(args.v11_static)

    fig, ax = plt.subplots(figsize=(10, 6))
    model_labels = ['YOLOv8n Full (640)', 'YOLOv8n Static (160)', 'YOLO11n Full (640)', 'YOLO11n Static (160)']
    sizes = [size_v8_full, size_v8_static, size_v11_full, size_v11_static]
    colors = [COLOR_V8, COLOR_V8_LIGHT, COLOR_V11, COLOR_V11_LIGHT]
    
    rects = ax.bar(model_labels, sizes, color=colors, alpha=0.7)
    ax.set_ylabel('OpenVINO Folder Size (MB)')
    ax.set_title('Model Size Comparison')
    autolabel(ax, rects)
    plt.tight_layout()
    plt.savefig(os.path.join(args.out_dir, "5_model_size_comparison.png"))
    plt.close()

    # 6. Trajectory (Angle & X,Y Center)
    def plot_trajectory(df, title, filename):
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)
        fig.suptitle(title, fontsize=16, fontweight='bold')
        
        # Angle
        unwrapped_angle = np.degrees(np.unwrap(np.radians(df['angle'])))
        ax1.plot(range(len(df)), unwrapped_angle, color='green', marker='.', linestyle='-', label='Angle (deg)', linewidth=1.5)
        ax1.set_ylabel("Degrees")
        ax1.set_title("Angle Progression")
        ax1.legend()
        ax1.grid(True)

        # X, Y Center
        ax2.plot(range(len(df)), df['x_center'], color='blue', alpha=0.8, marker='.', linestyle='-', label='X Center', linewidth=1.5)
        ax2.plot(range(len(df)), df['y_center'], color='red', alpha=0.8, marker='.', linestyle='-', label='Y Center', linewidth=1.5)
        ax2.set_xlabel("Frames from start")
        ax2.set_ylabel("Pixels")
        ax2.set_title("Object Center Trajectory (X, Y)")
        ax2.legend()
        ax2.grid(True)

        plt.tight_layout()
        plt.savefig(os.path.join(args.out_dir, filename))
        plt.close()

    plot_trajectory(df_v8, "Trajectory & Angle - YOLOv8n", "6_yolov8n_trajectory.png")
    plot_trajectory(df_v11, "Trajectory & Angle - YOLO11n", "7_yolo11n_trajectory.png")

    print(f"[INFO] Complete! 7 plots saved to: {os.path.abspath(args.out_dir)}")

if __name__ == "__main__":
    main()
