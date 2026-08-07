import csv
import matplotlib.pyplot as plt
import os
import numpy as np

def read_metrics(csv_path):
    fps_list = []
    inf_time_list = []
    e2e_time_list = []
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                fps = float(row['fps'])
                inf = float(row['inf_time_ms'])
                e2e = float(row['end_to_end_time_ms'])
                fps_list.append(fps)
                inf_time_list.append(inf)
                e2e_time_list.append(e2e)
            except ValueError:
                continue
    return fps_list, inf_time_list, e2e_time_list

def main():
    v8_path = r"benchmark\yolov8n_fp16_roi_tracking.csv"
    v11_path = r"benchmark\yolo11n_fp16_roi_tracking.csv"
    
    if not os.path.exists(v8_path) or not os.path.exists(v11_path):
        print("[ERROR] Không tìm thấy đủ 2 file log!")
        return

    v8_fps, v8_inf, v8_e2e = read_metrics(v8_path)
    v11_fps, v11_inf, v11_e2e = read_metrics(v11_path)
    
    # Calculate Averages
    v8_avg_fps = sum(v8_fps) / len(v8_fps) if v8_fps else 0
    v11_avg_fps = sum(v11_fps) / len(v11_fps) if v11_fps else 0
    
    v8_avg_inf = sum(v8_inf) / len(v8_inf) if v8_inf else 0
    v11_avg_inf = sum(v11_inf) / len(v11_inf) if v11_inf else 0
    
    v8_avg_e2e = sum(v8_e2e) / len(v8_e2e) if v8_e2e else 0
    v11_avg_e2e = sum(v11_e2e) / len(v11_e2e) if v11_e2e else 0

    print(f"YOLOv8n - Avg FPS: {v8_avg_fps:.2f}, Avg Inf: {v8_avg_inf:.2f}ms, Avg E2E: {v8_avg_e2e:.2f}ms")
    print(f"YOLO11n - Avg FPS: {v11_avg_fps:.2f}, Avg Inf: {v11_avg_inf:.2f}ms, Avg E2E: {v11_avg_e2e:.2f}ms")
    
    # Plotting
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # Subplot 1: FPS over time
    axes[0].plot(v8_fps, label=f'YOLOv8n (Avg: {v8_avg_fps:.1f})', color='blue', alpha=0.7)
    axes[0].plot(v11_fps, label=f'YOLO11n (Avg: {v11_avg_fps:.1f})', color='orange', alpha=0.7)
    axes[0].set_title("FPS over frames (ROI Tracking)")
    axes[0].set_xlabel("Frames")
    axes[0].set_ylabel("FPS")
    axes[0].legend()
    axes[0].grid(True)
    
    # Subplot 2: Bar chart for times
    labels = ['Inference Time (ms)', 'End-to-End Time (ms)']
    v8_times = [v8_avg_inf, v8_avg_e2e]
    v11_times = [v11_avg_inf, v11_avg_e2e]
    
    x = np.arange(len(labels))
    width = 0.35
    
    rects1 = axes[1].bar(x - width/2, v8_times, width, label='YOLOv8n', color='blue', alpha=0.7)
    rects2 = axes[1].bar(x + width/2, v11_times, width, label='YOLO11n', color='orange', alpha=0.7)
    
    axes[1].set_title("Average Processing Time Comparison")
    axes[1].set_ylabel("Time (ms)")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(labels)
    axes[1].legend()
    
    # Add labels on top of bars
    for rects in [rects1, rects2]:
        for rect in rects:
            height = rect.get_height()
            axes[1].annotate(f'{height:.2f}',
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3),  # 3 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom')

    plt.tight_layout()
    plot_path = r"benchmark\comparison_plot.png"
    plt.savefig(plot_path)
    print(f"Plot saved successfully to {plot_path}")

if __name__ == "__main__":
    main()
