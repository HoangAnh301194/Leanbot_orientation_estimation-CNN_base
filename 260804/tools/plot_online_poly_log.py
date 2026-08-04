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

def plot_online_poly_log(csv_file: str, n_sample_segments: int = 3, poly_degree: int = 3):
    csv_path = Path(csv_file)
    if not csv_path.exists():
        print(f"[ERROR] File không tồn tại: {csv_file}")
        return

    df = pd.read_csv(csv_path)
    if df.empty:
        print(f"[ERROR] File {csv_file} rỗng.")
        return

    # Sắp xếp theo frame_id
    if 'frame_id' in df.columns:
        df = df.sort_values('frame_id').reset_index(drop=True)

    # Lọc bớt dữ liệu rác nếu có
    has_smooth = 'smooth_x' in df.columns and 'smooth_y' in df.columns
    has_raw = 'x_center' in df.columns and 'y_center' in df.columns

    if not has_raw:
        print(f"[ERROR] Thiếu cột x_center/y_center trong file {csv_file}")
        return

    out_dir = csv_path.parent
    base_name = csv_path.stem

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Đồ thị Quỹ đạo 2D (Raw vs Smooth) - Style Mảnh & Điểm Nhỏ
    # ─────────────────────────────────────────────────────────────────────────
    fig_traj, ax_traj = plt.subplots(figsize=(10, 8), dpi=150)
    
    if has_smooth:
        # Đường Smooth: màu xanh dương
        ax_traj.plot(df['smooth_x'], df['smooth_y'], color='#1f77b4', linewidth=2.0, label='Online Poly Smooth (deg=3)', zorder=1)
        ax_traj.scatter(df['smooth_x'], df['smooth_y'], color='#003366', s=5, alpha=0.7, zorder=2)

    # Đường Raw: màu đỏ, nét đứt vừa phải (linewidth=0.9), điểm vừa mắt (s=5)
    ax_traj.plot(df['x_center'], df['y_center'], color='#d62728', linewidth=0.9, linestyle='--', alpha=0.65, label='Raw Trajectory', zorder=3)
    ax_traj.scatter(df['x_center'], df['y_center'], color='#8b0000', s=5, alpha=0.7, marker='o', label='Raw Points', zorder=4)

    ax_traj.invert_yaxis()  # Đảo ngược trục Y cho đúng hệ tọa độ ảnh OpenCV
    ax_traj.set_title(f'2D Trajectory - Online Poly Smooth vs Raw\n{csv_path.name}', fontsize=14, fontweight='bold')
    ax_traj.set_xlabel('X Center (pixels)')
    ax_traj.set_ylabel('Y Center (pixels)')
    ax_traj.grid(True, linestyle=':', alpha=0.5)
    ax_traj.legend(loc='best')
    plt.tight_layout()

    out_traj_img = out_dir / f"{base_name}_2d_trajectory.png"
    fig_traj.savefig(out_traj_img, dpi=150)
    plt.close(fig_traj)
    print(f"[SUCCESS] Đã lưu đồ thị quỹ đạo 2D (nét mảnh, point nhỏ) tại: {out_traj_img}")

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Phân tích & Trích xuất công thức f_x(t), f_y(t) trên các đoạn 30 điểm
    # ─────────────────────────────────────────────────────────────────────────
    valid_df = df[df['tracking_lost'] == 0].copy() if 'tracking_lost' in df.columns else df.copy()
    n_points = len(valid_df)
    seg_len = 30

    if n_points >= seg_len:
        print(f"\n--- CÔNG THỨC ĐA THỨC BẬC 3 f_x(t) & f_y(t) CHO CÁC ĐOẠN 30 ĐIỂM ---")
        indices = np.linspace(0, n_points - seg_len, num=min(n_sample_segments, max(1, n_points // seg_len)), dtype=int)
        
        for idx_i, start_idx in enumerate(indices):
            seg = valid_df.iloc[start_idx : start_idx + seg_len]
            x_seg = seg['x_center'].values
            y_seg = seg['y_center'].values
            frame_start = int(seg['frame_id'].iloc[0])
            frame_end = int(seg['frame_id'].iloc[-1])

            t_norm = np.arange(seg_len, dtype=float) / float(seg_len)
            coeffs_x = np.polyfit(t_norm, x_seg, deg=poly_degree)
            coeffs_y = np.polyfit(t_norm, y_seg, deg=poly_degree)

            a3, a2, a1, a0 = coeffs_x
            b3, b2, b1, b0 = coeffs_y

            print(f"\n📌 Đoạn {idx_i + 1} (Frames [{frame_start} .. {frame_end}]):")
            print(f"   f_x(t) = {a3:+.3f}*t^3 {a2:+.3f}*t^2 {a1:+.3f}*t {a0:+.3f}")
            print(f"   f_y(t) = {b3:+.3f}*t^3 {b2:+.3f}*t^2 {b1:+.3f}*t {b0:+.3f}")

            # Vẽ đồ thị thành phần X(t) và Y(t) theo t chuẩn hóa
            fig_comp, (ax_x, ax_y) = plt.subplots(2, 1, figsize=(10, 6), sharex=True, dpi=150)
            t_dense = np.linspace(0, (seg_len - 1) / float(seg_len), 100)
            x_fit_dense = np.polyval(coeffs_x, t_dense)
            y_fit_dense = np.polyval(coeffs_y, t_dense)

            # Component X
            ax_x.scatter(t_norm, x_seg, color='red', s=12, label='Raw X', alpha=0.7)
            ax_x.plot(t_dense, x_fit_dense, color='blue', linewidth=1.5, label=f'f_x(t) Polynomial deg=3')
            ax_x.set_ylabel('X Coordinate (px)')
            ax_x.set_title(f'Segment {idx_i+1} (Frames {frame_start}-{frame_end}): f_x(t) = {a3:.2f}t³ + {a2:.2f}t² + {a1:.2f}t + {a0:.2f}')
            ax_x.grid(True, linestyle=':', alpha=0.6)
            ax_x.legend(loc='best')

            # Component Y
            ax_y.scatter(t_norm, y_seg, color='red', s=12, label='Raw Y', alpha=0.7)
            ax_y.plot(t_dense, y_fit_dense, color='blue', linewidth=1.5, label=f'f_y(t) Polynomial deg=3')
            ax_y.set_xlabel('Normalized Time t in [0, 1)')
            ax_y.set_ylabel('Y Coordinate (px)')
            ax_y.set_title(f'f_y(t) = {b3:.2f}t³ + {b2:.2f}t² + {b1:.2f}t + {b0:.2f}')
            ax_y.grid(True, linestyle=':', alpha=0.6)
            ax_y.legend(loc='best')

            plt.tight_layout()
            comp_img_path = out_dir / f"{base_name}_poly_components_seg{idx_i+1}.png"
            fig_comp.savefig(comp_img_path, dpi=150)
            plt.close(fig_comp)
            print(f"   --> Đã lưu đồ thị đa thức f_x(t), f_y(t) tại: {comp_img_path}")

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Đồ thị Thời gian Tổng hợp (Subplots: Angle, X/Y vs Time, FPS, IoU)
    # ─────────────────────────────────────────────────────────────────────────
    fig_time, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True, dpi=150)
    fig_time.suptitle(f'Online Poly Smooth Log Analysis\n{csv_path.name}', fontsize=14, fontweight='bold')

    # Subplot 1: Angle Unwrapped (Màu xanh dương - Blue 'b.-' giống plot_log.py)
    ax_ang = axes[0]
    if 'angle' in df.columns or 'group1_angle' in df.columns:
        ang_col = 'group1_angle' if 'group1_angle' in df.columns else 'angle'
        unwrapped_angle = np.degrees(np.unwrap(np.radians(df[ang_col])))
        ax_ang.plot(df['frame_id'], unwrapped_angle, 'b.-', linewidth=1.2, markersize=3, label='Angle (degrees)')
        ax_ang.set_ylabel('Degrees')
        ax_ang.grid(True, linestyle='--', alpha=0.7)
        ax_ang.legend(loc='upper right')
        ax_ang.set_title("Angle (Unwrapped)")

    # Subplot 2: X, Y Center (4 màu hoàn toàn khác biệt: Raw X đỏ, Smooth X xanh dương, Raw Y xanh lá, Smooth Y cam)
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

    # Subplot 3: End-to-End FPS (Màu xanh dương giống plot_log.py)
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
    parser.add_argument("--segments", type=int, default=3, help="Số đoạn mẫu để xuất công thức f_x(t), f_y(t) (mặc định 3)")
    parser.add_argument("--degree", type=int, default=3, help="Bậc đa thức (mặc định 3)")
    args = parser.parse_args()

    plot_online_poly_log(args.csv_file, n_sample_segments=args.segments, poly_degree=args.degree)
