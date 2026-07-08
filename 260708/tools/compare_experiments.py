import pandas as pd
import matplotlib.pyplot as plt
import argparse
import os
import sys

# Fix lỗi in tiếng Việt trên console Windows
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

def main():
    parser = argparse.ArgumentParser(description="Đánh giá và so sánh kết quả log ROI vs Baseline")
    parser.add_argument("--roi-log", required=True, help="Đường dẫn tới file csv của mode ROI")
    parser.add_argument("--baseline-log", required=True, help="Đường dẫn tới file csv của mode Baseline")
    parser.add_argument("--out-dir", default="benchmark", help="Thư mục lưu các biểu đồ")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    # Đọc dữ liệu
    df_roi = pd.read_csv(args.roi_log)
    df_base = pd.read_csv(args.baseline_log)

    print("=== KẾT QUẢ SO SÁNH TRUNG BÌNH ===")
    
    avg_fps_roi = df_roi['fps'].mean()
    avg_fps_base = df_base['fps'].mean()
    
    avg_inf_roi = df_roi['inf_time_ms'].mean()
    avg_inf_base = df_base['inf_time_ms'].mean()
    
    avg_cpu_roi = df_roi['cpu_load_pct'].mean()
    avg_cpu_base = df_base['cpu_load_pct'].mean()
    
    avg_input_roi = df_roi['input_width'].mean()
    avg_input_base = df_base['input_width'].mean()
    
    lost_roi = df_roi['lost_count'].iloc[-1] if not df_roi.empty else 0
    lost_base = df_base['lost_count'].iloc[-1] if not df_base.empty else 0

    print(f"1. FPS trung bình:")
    print(f"   - Baseline : {avg_fps_base:.2f} FPS")
    print(f"   - ROI      : {avg_fps_roi:.2f} FPS")
    
    print(f"2. Inference time trung bình:")
    print(f"   - Baseline : {avg_inf_base:.2f} ms")
    print(f"   - ROI      : {avg_inf_roi:.2f} ms")

    print(f"3. CPU load trung bình:")
    print(f"   - Baseline : {avg_cpu_base:.2f}%")
    print(f"   - ROI      : {avg_cpu_roi:.2f}%")
    
    print(f"4. Kích thước input trung bình (Width):")
    print(f"   - Baseline : {avg_input_base:.2f} px")
    print(f"   - ROI      : {avg_input_roi:.2f} px")
    
    print(f"5. Số lần mất detection (Fallback):")
    print(f"   - Baseline : {lost_base} lần")
    print(f"   - ROI      : {lost_roi} lần")

    # Vẽ biểu đồ 1: FPS over time
    plt.figure(figsize=(10, 5))
    plt.plot(df_base['frame_id'], df_base['fps'], label='Baseline (Full-frame)', alpha=0.7)
    plt.plot(df_roi['frame_id'], df_roi['fps'], label='ROI Tracking', alpha=0.7)
    plt.xlabel("Frame ID")
    plt.ylabel("FPS")
    plt.title("So sánh tốc độ khung hình (FPS)")
    plt.legend()
    plt.grid(True)
    plt.savefig(os.path.join(args.out_dir, "fps_comparison.png"))
    plt.close()

    # Vẽ biểu đồ 2: Inference Time
    plt.figure(figsize=(10, 5))
    plt.plot(df_base['frame_id'], df_base['inf_time_ms'], label='Baseline', alpha=0.7)
    plt.plot(df_roi['frame_id'], df_roi['inf_time_ms'], label='ROI', alpha=0.7)
    plt.xlabel("Frame ID")
    plt.ylabel("Inference Time (ms)")
    plt.title("So sánh Inference Time")
    plt.legend()
    plt.grid(True)
    plt.savefig(os.path.join(args.out_dir, "inf_time_comparison.png"))
    plt.close()

    # Vẽ biểu đồ 3: CPU Load
    plt.figure(figsize=(10, 5))
    plt.plot(df_base['frame_id'], df_base['cpu_load_pct'], label='Baseline', alpha=0.7)
    plt.plot(df_roi['frame_id'], df_roi['cpu_load_pct'], label='ROI', alpha=0.7)
    plt.xlabel("Frame ID")
    plt.ylabel("CPU Load (%)")
    plt.title("So sánh Tải CPU")
    plt.legend()
    plt.grid(True)
    plt.savefig(os.path.join(args.out_dir, "cpu_load_comparison.png"))
    plt.close()

    # Vẽ biểu đồ 4: Quỹ đạo (Tọa độ center_x, center_y và Angle) của bản ROI
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10))
    ax1.plot(df_roi['frame_id'], df_roi['center_x'], label='Center X', color='blue')
    ax1.plot(df_roi['frame_id'], df_roi['center_y'], label='Center Y', color='orange')
    ax1.set_xlabel("Frame ID")
    ax1.set_ylabel("Pixel Coordinate")
    ax1.set_title("Quỹ đạo tâm vật thể (Center X, Y) - ROI Mode")
    ax1.legend()
    ax1.grid(True)

    ax2.plot(df_roi['frame_id'], df_roi['angle'], label='Angle', color='green')
    ax2.set_xlabel("Frame ID")
    ax2.set_ylabel("Angle (rad/deg)")
    ax2.set_title("Góc nghiêng vật thể (Angle) - ROI Mode")
    ax2.legend()
    ax2.grid(True)
    
    plt.tight_layout()
    plt.savefig(os.path.join(args.out_dir, "trajectory_angle.png"))
    plt.close()

    print(f"\n[INFO] Đã lưu 4 biểu đồ vào thư mục: {os.path.abspath(args.out_dir)}")

if __name__ == "__main__":
    main()
