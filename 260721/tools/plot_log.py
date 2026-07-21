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
        if 'group1_angle' in df.columns and 'angle' not in df.columns:
            df['angle'] = df['group1_angle']
        if 'group1_magnitude' in df.columns and 'vector_magnitude' not in df.columns:
            df['vector_magnitude'] = df['group1_magnitude']
            
        required_cols = ['frame_id', 'angle', 'x_center', 'y_center']
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            print(f"Error: Missing columns {missing} in {csv_file}")
            return
        df_plot = df.copy()
        
    df_plot = df_plot.sort_values('frame_id')
    
    # Khởi tạo 2 biểu đồ con (Subplots)
    has_roi_cols = all(c in df_plot.columns for c in ['roi_center_x', 'roi_center_y', 'roi_pre_width', 'roi_pre_height'])
    has_mag_cols = 'vector_magnitude' in df_plot.columns or 'group1_magnitude' in df_plot.columns
    n_axes = 2
    if has_mag_cols:
        n_axes += 1
    if has_roi_cols:
        n_axes += 2
    fig_height = 4 * n_axes
    fig, axes = plt.subplots(n_axes, 1, figsize=(12, fig_height), sharex=True)
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
    ax2.set_title("X, Y Center")

    # ---------------------------------------------------------
    # 3. Đồ thị Vector Magnitude (Group 1 và Group 2)
    # ---------------------------------------------------------
    ax_idx = 2
    if has_mag_cols:
        ax3 = axes[ax_idx]
        mag_col = 'group1_magnitude' if 'group1_magnitude' in df_plot.columns else 'vector_magnitude'
        ax3.plot(df_plot['frame_id'], df_plot[mag_col], 'r.-', label='Group 1 Magnitude', linewidth=1.5, markersize=4)
        if 'group2_magnitude' in df_plot.columns:
            ax3.plot(df_plot['frame_id'], df_plot['group2_magnitude'], 'b.-', label='Group 2 Magnitude', linewidth=1.5, markersize=3, alpha=0.7)
        ax3.set_ylabel('Magnitude')
        ax3.grid(True, linestyle='--', alpha=0.7)
        ax3.legend(loc='upper right')
        ax3.set_title("Vector Magnitude (Group 1 vs Group 2)")
        ax_idx += 1

    if has_roi_cols:
        roi_df = df_plot[df_plot['mode'] == 'ROI'] if 'mode' in df_plot.columns else df_plot

        ax_roi1 = axes[ax_idx]
        ax_roi1.plot(roi_df['frame_id'], roi_df['roi_center_x'], 'm.-', label='ROI center X', linewidth=1.5)
        ax_roi1.plot(roi_df['frame_id'], roi_df['roi_center_y'], 'c.-', label='ROI center Y', linewidth=1.5)
        ax_roi1.set_ylabel('Pixels')
        ax_roi1.grid(True, linestyle='--', alpha=0.7)
        ax_roi1.legend(loc='upper right')
        ax_roi1.set_title("ROI Center")

        ax_roi2 = axes[ax_idx + 1]
        ax_roi2.plot(roi_df['frame_id'], roi_df['roi_pre_width'], 'r.-', label='ROI width before resize', linewidth=1.5)
        ax_roi2.plot(roi_df['frame_id'], roi_df['roi_pre_height'], 'g.-', label='ROI height before resize', linewidth=1.5)
        ax_roi2.set_ylabel('Pixels')
        ax_roi2.grid(True, linestyle='--', alpha=0.7)
        ax_roi2.legend(loc='upper right')
        ax_roi2.set_xlabel('Frame ID')
        ax_roi2.set_title("ROI Width/Height Before Resize")
    
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
