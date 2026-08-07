import argparse
import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Đảm bảo UTF-8 cho console terminal
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def plot_online_poly_log(csv_file: str, n_sample_segments: int = 3, poly_degree: int = 2):
    csv_path = Path(csv_file)
    if not csv_path.exists():
        print(f"[ERROR] File không tồn tại: {csv_file}")
        return

    df = pd.read_csv(csv_path)
    if df.empty:
        print(f"[ERROR] File {csv_file} rỗng.")
        return

    if 'frame_id' in df.columns:
        df = df.sort_values('frame_id').reset_index(drop=True)

    has_smooth = 'smooth_x' in df.columns and 'smooth_y' in df.columns
    has_raw = 'x_center' in df.columns and 'y_center' in df.columns

    if not has_raw:
        print(f"[ERROR] Thiếu cột x_center/y_center trong file {csv_file}")
        return

    out_dir = csv_path.parent
    base_name = csv_path.stem

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Đồ thị Quỹ đạo 2D (Raw vs Smooth) - Smooth điểm chữ X, Raw điểm tròn O
    # ─────────────────────────────────────────────────────────────────────────
    fig_traj, ax_traj = plt.subplots(figsize=(10, 8), dpi=150)
    
    if has_smooth:
        # Đường Smooth: màu xanh dương, marker hình chữ X nhỏ gọn (s=8)
        ax_traj.plot(df['smooth_x'], df['smooth_y'], color='#1f77b4', linewidth=1.8, label=f'Online Poly Smooth (deg={poly_degree})', zorder=1)
        ax_traj.scatter(df['smooth_x'], df['smooth_y'], color='#003366', s=8, marker='x', alpha=0.8, label='Smooth Points (X)', zorder=2)

    # Đường Raw: màu đỏ, nét đứt vừa phải, marker tròn O
    ax_traj.plot(df['x_center'], df['y_center'], color='#d62728', linewidth=0.9, linestyle='--', alpha=0.65, label='Raw Trajectory', zorder=3)
    ax_traj.scatter(df['x_center'], df['y_center'], color='#8b0000', s=5, marker='o', alpha=0.7, label='Raw Points (O)', zorder=4)

    ax_traj.invert_yaxis()
    ax_traj.set_title(f'2D Trajectory - Online Poly Smooth (deg={poly_degree}) vs Raw\n{csv_path.name}', fontsize=14, fontweight='bold')
    ax_traj.set_xlabel('X Center (pixels)')
    ax_traj.set_ylabel('Y Center (pixels)')
    ax_traj.grid(True, linestyle=':', alpha=0.5)
    ax_traj.legend(loc='best')
    plt.tight_layout()

    out_traj_img = out_dir / f"{base_name}_2d_trajectory.png"
    fig_traj.savefig(out_traj_img, dpi=150)
    plt.close(fig_traj)
    print(f"[SUCCESS] Đã lưu đồ thị quỹ đạo 2D tại: {out_traj_img}")

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Phân tích & Trích xuất các đoạn 30 điểm (Chuẩn hóa t in [0.0, 1.0])
    # ─────────────────────────────────────────────────────────────────────────
    valid_df = df[df['tracking_lost'] == 0].copy() if 'tracking_lost' in df.columns else df.copy()
    n_points = len(valid_df)
    seg_len = 30

    if n_points >= seg_len:
        print(f"\n--- ĐA THỨC BẬC {poly_degree} f_x(t) & f_y(t) CHO CÁC ĐOẠN 30 ĐIỂM (t in [0, 1]) ---")
        indices = np.linspace(0, n_points - seg_len, num=min(n_sample_segments, max(1, n_points // seg_len)), dtype=int)
        
        # Pre-compute mảng thời gian t chuẩn hóa 1 lần duy nhất trong [0.0, 1.0] (29 / 29.0 = 1.0)
        t_norm = np.linspace(0.0, 1.0, seg_len)

        for idx_i, start_idx in enumerate(indices):
            seg = valid_df.iloc[start_idx : start_idx + seg_len]
            x_seg = seg['x_center'].values
            y_seg = seg['y_center'].values
            frame_start = int(seg['frame_id'].iloc[0])
            frame_end = int(seg['frame_id'].iloc[-1])

            coeffs_x = np.polyfit(t_norm, x_seg, deg=poly_degree)
            coeffs_y = np.polyfit(t_norm, y_seg, deg=poly_degree)

            # Vẽ đồ thị thành phần X(t) và Y(t) theo t chuẩn hóa [0, 1]
            fig_comp, (ax_x, ax_y) = plt.subplots(2, 1, figsize=(10, 6), sharex=True, dpi=150)
            t_dense = np.linspace(0.0, 1.0, 100)
            x_fit_dense = np.polyval(coeffs_x, t_dense)
            y_fit_dense = np.polyval(coeffs_y, t_dense)

            ax_x.scatter(t_norm, x_seg, color='red', s=12, marker='o', label='Raw X', alpha=0.7)
            ax_x.plot(t_dense, x_fit_dense, color='blue', linewidth=1.5, label=f'f_x(t) Poly deg={poly_degree}')
            ax_x.set_ylabel('X Coordinate (px)')
            ax_x.set_title(f'Segment {idx_i+1} (Frames {frame_start}-{frame_end}): f_x(t) Poly deg={poly_degree}')
            ax_x.grid(True, linestyle=':', alpha=0.6)
            ax_x.legend(loc='best')

            ax_y.scatter(t_norm, y_seg, color='red', s=12, marker='o', label='Raw Y', alpha=0.7)
            ax_y.plot(t_dense, y_fit_dense, color='blue', linewidth=1.5, label=f'f_y(t) Poly deg={poly_degree}')
            ax_y.set_xlabel('Normalized Time t in [0, 1]')
            ax_y.set_ylabel('Y Coordinate (px)')
            ax_y.set_title(f'Segment {idx_i+1}: f_y(t) Poly deg={poly_degree}')
            ax_y.grid(True, linestyle=':', alpha=0.6)
            ax_y.legend(loc='best')

            plt.tight_layout()
            comp_img_path = out_dir / f"{base_name}_poly_components_seg{idx_i+1}.png"
            fig_comp.savefig(comp_img_path, dpi=150)
            plt.close(fig_comp)
            print(f"   --> Đã lưu đồ thị đa thức f_x(t), f_y(t) tại: {comp_img_path}")

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Đồ thị Thời gian Tổng hợp (So sánh Raw Angle vs Smooth Angle)
    # ─────────────────────────────────────────────────────────────────────────
    fig_time, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True, dpi=150)
    fig_time.suptitle(f'Online Poly Smooth Log Analysis (deg={poly_degree})\n{csv_path.name}', fontsize=14, fontweight='bold')

    # Subplot 1: So sánh 4 đường angle (unwrapped & phase aligned)
    ax_ang = axes[0]
    has_angle = any(column in df.columns for column in ('raw_angle', 'group1_angle', 'angle'))
    if has_angle:
        ang_col = next(column for column in ('raw_angle', 'group1_angle', 'angle') if column in df.columns)
        raw_unwrapped = np.degrees(np.unwrap(np.radians(df[ang_col])))
        ax_ang.plot(df['frame_id'], raw_unwrapped, 'b.-', linewidth=1.0, markersize=2, alpha=0.4, label='Raw Angle')

    def align_phase(target_arr, ref_arr):
        if len(target_arr) == 0 or len(ref_arr) == 0:
            return target_arr
        diff = target_arr[0] - ref_arr[0]
        k = np.round(diff / 360.0)
        return target_arr - k * 360.0

    if 'smooth_angle' in df.columns:
        smooth_angle = df['smooth_angle'].bfill().ffill()
    elif has_smooth:
        dx = df['smooth_x'].diff()
        dy = df['smooth_y'].diff()
        smooth_angle = np.degrees(np.arctan2(-dy, dx))
        smooth_angle.iloc[0] = df[ang_col].iloc[0] if has_angle else 0.0
        smooth_angle = smooth_angle.bfill().ffill()
    else:
        smooth_angle = None

    if smooth_angle is not None:
        smooth_unwrapped = np.degrees(np.unwrap(np.radians(smooth_angle)))
        if has_angle:
            smooth_unwrapped = align_phase(smooth_unwrapped, raw_unwrapped)
        ax_ang.plot(df['frame_id'], smooth_unwrapped, color='#ff7f00', linewidth=1.2, alpha=0.5, label='Smooth Angle')

    if 'raw_angle_smooth' in df.columns:
        raw_angle_smooth = np.degrees(np.unwrap(np.radians(df['raw_angle_smooth'])))
        if has_angle:
            raw_angle_smooth = align_phase(raw_angle_smooth, raw_unwrapped)
        ax_ang.plot(df['frame_id'], raw_angle_smooth, color='#2ca02c', linewidth=2.0, label='Raw Angle Smooth (Poly)')

    if 'smooth_angle_smooth' in df.columns:
        smooth_angle_smooth = np.degrees(np.unwrap(np.radians(df['smooth_angle_smooth'])))
        if has_angle:
            smooth_angle_smooth = align_phase(smooth_angle_smooth, raw_unwrapped)
        ax_ang.plot(df['frame_id'], smooth_angle_smooth, color='#9467bd', linewidth=2.0, linestyle='--', label='Smooth Angle Smooth (Poly)')

    ax_ang.set_ylabel('Degrees')
    ax_ang.grid(True, linestyle='--', alpha=0.7)
    ax_ang.legend(loc='upper right', fontsize=8)
    ax_ang.set_title("Heading Angle: Raw / Smooth / Raw Smooth / Smooth Smooth")

    # Subplot 2: X, Y Center (Raw vs Smooth)
    ax_pos = axes[1]
    ax_pos.plot(df['frame_id'], df['x_center'], 'r.-', linewidth=1.0, markersize=3, alpha=0.5, label='Raw X center')
    ax_pos.plot(df['frame_id'], df['y_center'], 'g.-', linewidth=1.0, markersize=3, alpha=0.5, label='Raw Y center')
    if has_smooth:
        ax_pos.plot(df['frame_id'], df['smooth_x'], color='#1f77b4', linewidth=1.6, label='Smooth X center')
        ax_pos.plot(df['frame_id'], df['smooth_y'], color='#ff7f00', linewidth=1.6, label='Smooth Y center')
    ax_pos.set_ylabel('Pixels')
    ax_pos.grid(True, linestyle='--', alpha=0.7)
    ax_pos.legend(loc='upper right')
    ax_pos.set_title("X, Y Center (Raw vs Smooth)")

    # Subplot 3: End-to-End FPS
    ax_fps = axes[2]
    if 'fps' in df.columns:
        ax_fps.plot(df['frame_id'], df['fps'], 'b.-', linewidth=1.2, markersize=3, label='End-to-End FPS')
        ax_fps.set_ylabel('FPS')
        ax_fps.set_xlabel('Frame ID')
        ax_fps.grid(True, linestyle='--', alpha=0.7)
        ax_fps.legend(loc='upper right')
        ax_fps.set_title("System End-to-End FPS")

    plt.tight_layout()
    out_time_img = out_dir / f"{base_name}_time_series.png"
    fig_time.savefig(out_time_img, dpi=150)
    plt.close(fig_time)
    print(f"[SUCCESS] Đã lưu biểu đồ chuỗi thời gian tại: {out_time_img}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Vẽ đồ thị báo cáo Online Polynomial Smooth từ file CSV log")
    parser.add_argument("csv_file", type=str, help="Đường dẫn file CSV log")
    parser.add_argument("--segments", type=int, default=3, help="Số đoạn mẫu để xuất đồ thị f_x(t), f_y(t) (mặc định 3)")
    parser.add_argument("--degree", type=int, default=2, help="Bậc đa thức (mặc định 2)")
    args = parser.parse_args()

    plot_online_poly_log(args.csv_file, n_sample_segments=args.segments, poly_degree=args.degree)
