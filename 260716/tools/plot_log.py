import argparse
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

def plot_log(csv_file: str):
    csv_path = Path(csv_file)
    if not csv_path.exists():
        print(f"Error: File not found {csv_file}")
        return

    df = pd.read_csv(csv_path)
    
    if df.empty:
        print(f"Error: File {csv_file} is empty.")
        return

    # Tương thích cả format cũ (có group_id) và format mới (không có group_id)
    if 'group_id' in df.columns:
        df_plot = df[df['group_id'] == 1].copy()
        if df_plot.empty:
            print(f"No Group 1 data found in log: {csv_file}")
            return
    else:
        # Format mới từ roi_tracking_baseline_infer.py
        required_cols = ['frame_id', 'angle', 'x_center', 'y_center']
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            print(f"Error: Missing columns {missing} in {csv_file}")
            return
        df_plot = df.copy()
        
    df_plot = df_plot.sort_values('frame_id')
    
    # Khởi tạo 2 biểu đồ con (Subplots)
    has_roi_cols = all(c in df_plot.columns for c in ['roi_center_x', 'roi_center_y', 'roi_pre_width', 'roi_pre_height'])
    n_axes = 4 if has_roi_cols else 2
    fig, axes = plt.subplots(n_axes, 1, figsize=(12, 12 if has_roi_cols else 8), sharex=True)
    fig.suptitle(f'Leanbot Spin Ploter\n{csv_path.name}', fontsize=16, fontweight='bold')
    
    # ---------------------------------------------------------
    # 1. Đồ thị Góc (Angle) 
    # ---------------------------------------------------------
    import numpy as np
    
    ax1 = axes[0]
    # Trải phẳng góc (unwrap) để tránh nhảy đột ngột từ -180 sang +180
    unwrapped_angle = np.degrees(np.unwrap(np.radians(df_plot['angle'])))
    
    ax1.plot(df_plot['frame_id'], unwrapped_angle, 'b.-', label='Angle (degrees)', linewidth=1.5, markersize=4)
    ax1.set_ylabel('Degrees')
    # Bỏ cố định trục y để đồ thị tự do vẽ góc vượt quá 180 độ
    ax1.grid(True, linestyle='--', alpha=0.7)
    ax1.legend(loc='upper right')
    ax1.set_title("Angle (Unwrapped)")
    
    # ---------------------------------------------------------
    # 2. Đồ thị Tọa độ X, Y (Để xem xe có bị trôi khi spin không)
    # ---------------------------------------------------------
    ax2 = axes[1]
    ax2.plot(df_plot['frame_id'], df_plot['x_center'], 'r.-', label='X center', linewidth=1.5)
    ax2.plot(df_plot['frame_id'], df_plot['y_center'], 'g.-', label='Y center', linewidth=1.5)
    ax2.set_ylabel('Pixels')
    ax2.grid(True, linestyle='--', alpha=0.7)
    ax2.legend(loc='upper right')
    ax2.set_xlabel('Frame ID')
    ax2.set_title("X, Y Center")

    if has_roi_cols:
        roi_df = df_plot[df_plot['mode'] == 'ROI'] if 'mode' in df_plot.columns else df_plot

        ax3 = axes[2]
        ax3.plot(roi_df['frame_id'], roi_df['roi_center_x'], 'm.-', label='ROI center X', linewidth=1.5)
        ax3.plot(roi_df['frame_id'], roi_df['roi_center_y'], 'c.-', label='ROI center Y', linewidth=1.5)
        ax3.set_ylabel('Pixels')
        ax3.grid(True, linestyle='--', alpha=0.7)
        ax3.legend(loc='upper right')
        ax3.set_title("ROI Center")

        ax4 = axes[3]
        ax4.plot(roi_df['frame_id'], roi_df['roi_pre_width'], 'r.-', label='ROI width before resize', linewidth=1.5)
        ax4.plot(roi_df['frame_id'], roi_df['roi_pre_height'], 'g.-', label='ROI height before resize', linewidth=1.5)
        ax4.set_ylabel('Pixels')
        ax4.grid(True, linestyle='--', alpha=0.7)
        ax4.legend(loc='upper right')
        ax4.set_xlabel('Frame ID')
        ax4.set_title("ROI Width/Height Before Resize")
    
    plt.tight_layout()
    
    # Lưu biểu đồ thành file ảnh cùng thư mục với file CSV
    out_img = csv_path.with_suffix('.png')
    plt.savefig(out_img, dpi=150)
    print(f"Saved plot successfully to: {out_img}")
    plt.close(fig) # Đóng biểu đồ để giải phóng bộ nhớ khi chạy hàng loạt

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Vẽ biểu đồ báo cáo từ file CSV log hoặc thư mục")
    parser.add_argument("path", type=str, help="Đường dẫn tới file CSV hoặc thư mục chứa các file CSV")
    args = parser.parse_args()
    
    target_path = Path(args.path)
    if target_path.is_file() and target_path.suffix == '.csv':
        plot_log(str(target_path))
    elif target_path.is_dir():
        csv_files = list(target_path.glob("*.csv"))
        print(f"Tim thay {len(csv_files)} file CSV trong thu muc {target_path}")
        for csv_file in csv_files:
            plot_log(str(csv_file))
    else:
        print("Invalid path! Please provide a valid .csv file or directory.")
