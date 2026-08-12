import argparse
import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Đảm bảo UTF-8 cho console terminal
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

class OnlineEMASmoother:
    """Online Streaming Exponential Moving Average Smoother."""
    def __init__(self, alpha: float):
        self.alpha = alpha
        self.sx = None
        self.sy = None
        self.s_sin = None
        self.s_cos = None

    def update(self, x: float, y: float, angle_deg: float):
        rad = math.radians(angle_deg)
        sin_val = math.sin(rad)
        cos_val = math.cos(rad)

        if self.sx is None:
            self.sx = float(x)
            self.sy = float(y)
            self.s_sin = sin_val
            self.s_cos = cos_val
        else:
            self.sx = self.alpha * float(x) + (1.0 - self.alpha) * self.sx
            self.sy = self.alpha * float(y) + (1.0 - self.alpha) * self.sy
            self.s_sin = self.alpha * sin_val + (1.0 - self.alpha) * self.s_sin
            self.s_cos = self.alpha * cos_val + (1.0 - self.alpha) * self.s_cos

        ema_angle_deg = math.degrees(math.atan2(self.s_sin, self.s_cos))
        return self.sx, self.sy, ema_angle_deg


def align_phase(target_arr, ref_arr):
    if len(target_arr) == 0 or len(ref_arr) == 0:
        return target_arr
    diff = np.mean(ref_arr) - np.mean(target_arr)
    k = np.round(diff / 180.0)
    target_shifted = target_arr + k * 180.0
    offset = np.mean(ref_arr) - np.mean(target_shifted)
    return target_shifted + offset


def find_midpoint_moving_segment(df: pd.DataFrame, seg_length: int = 30, seed: int = 42):
    """Tự động phát hiện các lượt di chuyển liên tục (Continuous Moving Blocks)
    và trích xuất đoạn 30 điểm nằm chính giữa lượt chạy (cách xa các điểm dừng).
    """
    valid_df = df[df['tracking_lost'] == 0].copy() if 'tracking_lost' in df.columns else df.copy()
    valid_df = valid_df.reset_index(drop=True)
    n = len(valid_df)
    if n < seg_length:
        return valid_df

    x = valid_df['x_center'].values
    y = valid_df['y_center'].values

    dx = np.diff(x, prepend=x[0])
    dy = np.diff(y, prepend=y[0])
    speed = np.sqrt(dx**2 + dy**2)

    # Smooth speed over 11 frames
    window = 11
    smooth_speed = np.convolve(speed, np.ones(window)/window, mode='same')

    # Lọc các khung hình robot đang di chuyển (speed > 1.5 px/frame)
    is_moving = smooth_speed > 1.5
    blocks = []
    start = None
    for i, m in enumerate(is_moving):
        if m and start is None:
            start = i
        elif not m and start is not None:
            if i - start >= 50:
                blocks.append((start, i))
            start = None
    if start is not None and n - start >= 50:
        blocks.append((start, n))

    if not blocks:
        start = (n - seg_length) // 2
        return valid_df.iloc[start : start + seg_length].copy().reset_index(drop=True)

    # Chọn 1 block liên tục bằng seed
    np.random.seed(seed)
    selected_block = blocks[np.random.choice(len(blocks))]
    
    # Lấy trung điểm (Midpoint) của block
    b_start, b_end = selected_block
    mid = (b_start + b_end) // 2
    
    half = seg_length // 2
    seg_start = max(b_start, mid - half)
    seg_end = min(b_end, seg_start + seg_length)
    if seg_end - seg_start < seg_length and seg_start > 0:
        seg_start = max(0, seg_end - seg_length)

    return valid_df.iloc[seg_start : seg_end].copy().reset_index(drop=True)


def process_csv_and_plot(csv_file: str, seg_length: int = 30, seed: int = 42):
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

    ang_col = next((c for c in ('raw_angle', 'group1_angle', 'angle') if c in df.columns), None)
    if not ang_col:
        print(f"[ERROR] Thiếu cột góc raw trong file {csv_file}")
        return

    seg = find_midpoint_moving_segment(df, seg_length=seg_length, seed=seed)
    n_seg = len(seg)
    frame_start = int(seg['frame_id'].iloc[0]) if 'frame_id' in seg.columns else 0
    frame_end = int(seg['frame_id'].iloc[-1]) if 'frame_id' in seg.columns else n_seg - 1

    print(f"[INFO] File: {csv_path.name} -> Zoom đoạn 30 điểm (Frames {frame_start} - {frame_end})")

    out_dir = csv_path.parent
    base_name = csv_path.stem

    alphas = [0.5, 0.7, 0.9]
    alpha_colors = {0.5: '#9467bd', 0.7: '#2ca02c', 0.9: '#0e7490'}
    traj_angle_colors = {0.5: '#e8a5e8', 0.7: '#8cd98c', 0.9: '#82c0c7'}

    for a in alphas:
        smoother = OnlineEMASmoother(alpha=a)
        ema_x, ema_y, ema_ang = [], [], []
        for _, row in seg.iterrows():
            sx, sy, sang = smoother.update(float(row['x_center']), float(row['y_center']), float(row[ang_col]))
            ema_x.append(sx)
            ema_y.append(sy)
            ema_ang.append(sang)

        seg[f'ema_x_a{a}'] = ema_x
        seg[f'ema_y_a{a}'] = ema_y
        seg[f'ema_angle_a{a}'] = ema_ang

        dx = pd.Series(ema_x).diff()
        dy = pd.Series(ema_y).diff()
        ema_traj_ang = np.degrees(np.arctan2(-dy, dx))
        ema_traj_ang.iloc[0] = seg[ang_col].iloc[0]
        ema_traj_ang = ema_traj_ang.bfill().ffill()
        seg[f'ema_traj_angle_a{a}'] = ema_traj_ang.values

    t_norm = np.linspace(0.0, 1.0, n_seg)
    x_raw = seg['x_center'].values
    y_raw = seg['y_center'].values

    poly2_x_coeffs = np.polyfit(t_norm, x_raw, deg=2)
    poly2_y_coeffs = np.polyfit(t_norm, y_raw, deg=2)
    poly3_x_coeffs = np.polyfit(t_norm, x_raw, deg=3)
    poly3_y_coeffs = np.polyfit(t_norm, y_raw, deg=3)

    x_poly2_pts = np.polyval(poly2_x_coeffs, t_norm)
    y_poly2_pts = np.polyval(poly2_y_coeffs, t_norm)
    x_poly3_pts = np.polyval(poly3_x_coeffs, t_norm)
    y_poly3_pts = np.polyval(poly3_y_coeffs, t_norm)

    poly2_dx_dt = np.polyval(np.polyder(poly2_x_coeffs), t_norm)
    poly2_dy_dt = np.polyval(np.polyder(poly2_y_coeffs), t_norm)
    poly2_tangent_rad = np.unwrap(np.arctan2(-poly2_dy_dt, poly2_dx_dt))
    poly2_tangent_deg = np.degrees(poly2_tangent_rad)

    poly3_dx_dt = np.polyval(np.polyder(poly3_x_coeffs), t_norm)
    poly3_dy_dt = np.polyval(np.polyder(poly3_y_coeffs), t_norm)
    poly3_tangent_rad = np.unwrap(np.arctan2(-poly3_dy_dt, poly3_dx_dt))
    poly3_tangent_deg = np.degrees(poly3_tangent_rad)

    raw_unwrapped = np.degrees(np.unwrap(np.radians(seg[ang_col])))
    poly2_angle_aligned = poly2_tangent_deg + (np.mean(raw_unwrapped) - np.mean(poly2_tangent_deg))
    poly3_angle_aligned = poly3_tangent_deg + (np.mean(raw_unwrapped) - np.mean(poly3_tangent_deg))

    frame_ids = seg['frame_id'].values if 'frame_id' in seg.columns else np.arange(n_seg)

    # ─────────────────────────────────────────────────────────────────────────
    # ẢNH 1: Biểu đồ Quỹ đạo 2D (Raw vs EMA vs Polynomial Bậc 2, Bậc 3) - Nét liền
    # ─────────────────────────────────────────────────────────────────────────
    fig_traj, ax_traj = plt.subplots(figsize=(9, 7), dpi=150)
    ax_traj.plot(seg['x_center'], seg['y_center'], color='#d62728', linewidth=1.5, linestyle='-', alpha=0.5, label='Raw Trajectory (O)', zorder=1)
    ax_traj.scatter(seg['x_center'], seg['y_center'], color='#8b0000', s=20, marker='o', alpha=0.7, zorder=2)
    
    for a in alphas:
        ax_traj.plot(seg[f'ema_x_a{a}'], seg[f'ema_y_a{a}'], color=alpha_colors[a], linewidth=1.8, linestyle='-', label=f'EMA (alpha={a})', zorder=4)

    # Thêm đường Polynomial Bậc 2 & Bậc 3 nét liền trên 2D Trajectory
    ax_traj.plot(x_poly2_pts, y_poly2_pts, color='#0055ff', linewidth=2.4, linestyle='-', label='Polynomial Bậc 2', zorder=6)
    ax_traj.plot(x_poly3_pts, y_poly3_pts, color='#009900', linewidth=2.4, linestyle='-', label='Polynomial Bậc 3', zorder=7)

    ax_traj.invert_yaxis()
    ax_traj.set_title(f'2D Trajectory Zoom-in (30 Points Unidirectional Pass)\nFile: {csv_path.name} (Frames {frame_start}-{frame_end})', fontsize=12, fontweight='bold')
    ax_traj.set_xlabel('X Center (pixels)')
    ax_traj.set_ylabel('Y Center (pixels)')
    ax_traj.grid(True, linestyle=':', alpha=0.6)
    ax_traj.legend(loc='best')
    plt.tight_layout()

    out_ema_2d_img = out_dir / f"{base_name}_ema_selective_2d_trajectory.png"
    fig_traj.savefig(out_ema_2d_img, dpi=150)
    plt.close(fig_traj)
    print(f"  -> Lưu: {out_ema_2d_img.name}")

    # ─────────────────────────────────────────────────────────────────────────
    # ẢNH 2: a) Đồ thị góc Raw_angle và các đường EMA từ góc tiếp tuyến 2 điểm liên tục
    # ─────────────────────────────────────────────────────────────────────────
    fig_ema_time, ax_ang = plt.subplots(figsize=(11, 6), dpi=150)
    ax_ang.plot(frame_ids, raw_unwrapped, color='#8b0000', linewidth=2.5, linestyle='-', label='Raw Angle (Model)', zorder=10)

    for a in alphas:
        ema_ang_unwrapped = align_phase(np.degrees(np.unwrap(np.radians(seg[f'ema_angle_a{a}']))), raw_unwrapped)
        ax_ang.plot(frame_ids, ema_ang_unwrapped, color=alpha_colors[a], linewidth=1.8, linestyle='-', label=f'EMA Vector Angle (alpha={a})')

    for a in alphas:
        ema_traj_ang_unwrapped = align_phase(np.degrees(np.unwrap(np.radians(seg[f'ema_traj_angle_a{a}']))), raw_unwrapped)
        ax_ang.plot(frame_ids, ema_traj_ang_unwrapped, color=traj_angle_colors[a], linewidth=1.5, linestyle='-', label=f'EMA Traj Tangent Angle (alpha={a})')

    ax_ang.set_title(f'a) Heading Angle Time-Series (Raw vs EMA Vector & Traj Angle)\nFile: {csv_path.name} (Frames {frame_start}-{frame_end})', fontsize=12, fontweight='bold')
    ax_ang.set_xlabel('Frame ID')
    ax_ang.set_ylabel('Angle (Degrees)')
    ax_ang.grid(True, linestyle='--', alpha=0.6)
    ax_ang.legend(loc='best', fontsize=9)
    plt.tight_layout()

    out_ema_time_img = out_dir / f"{base_name}_ema_selective_time_series.png"
    fig_ema_time.savefig(out_ema_time_img, dpi=150)
    plt.close(fig_ema_time)
    print(f"  -> Lưu: {out_ema_time_img.name}")

    # ─────────────────────────────────────────────────────────────────────────
    # ẢNH 3: b) Đồ thị góc Raw_angle và các đường làm mượt bằng polynomial bậc 2, bậc 3 (Chỉ vẽ 1 đồ thị góc - Nét liền)
    # ─────────────────────────────────────────────────────────────────────────
    fig_poly_time, ax_p_ang = plt.subplots(figsize=(11, 6), dpi=150)

    ax_p_ang.plot(frame_ids, raw_unwrapped, color='#8b0000', linewidth=2.2, linestyle='-', alpha=0.7, label='Raw Angle (Model)', zorder=1)
    ax_p_ang.plot(frame_ids, poly2_angle_aligned, color='#0055ff', linewidth=2.4, linestyle='-', label='Polynomial Fit Bậc 2 Angle', zorder=5)
    ax_p_ang.plot(frame_ids, poly3_angle_aligned, color='#009900', linewidth=2.4, linestyle='-', label='Polynomial Fit Bậc 3 Angle', zorder=6)

    ax_p_ang.set_title(f'b) Heading Angle Time-Series (Raw vs Polynomial Fit Bậc 2 & Bậc 3)\nFile: {csv_path.name} (Frames {frame_start}-{frame_end})', fontsize=12, fontweight='bold')
    ax_p_ang.set_xlabel('Frame ID')
    ax_p_ang.set_ylabel('Angle (Degrees)')
    ax_p_ang.grid(True, linestyle=':', alpha=0.6)
    ax_p_ang.legend(loc='best')

    plt.tight_layout()

    out_poly_time_img = out_dir / f"{base_name}_poly_smooth_time_series.png"
    fig_poly_time.savefig(out_poly_time_img, dpi=150)
    plt.close(fig_poly_time)
    print(f"  -> Lưu: {out_poly_time_img.name}")


def main():
    parser = argparse.ArgumentParser(description="Vẽ và làm mượt quỹ đạo đoạn di chuyển 1 chiều bằng Polynomial & EMA")
    parser.add_argument("input_path", type=str, help="Đường dẫn file CSV hoặc thư mục benchmark chứa các file CSV")
    parser.add_argument("--seg-length", type=int, default=30, help="Chiều dài đoạn 1 chiều (mặc định 30 điểm)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed chọn đoạn")
    args = parser.parse_args()

    input_path = Path(args.input_path)
    if input_path.is_file() and input_path.suffix == '.csv':
        process_csv_and_plot(str(input_path), seg_length=args.seg_length, seed=args.seed)
    elif input_path.is_dir():
        csv_files = sorted(list(input_path.glob("*.csv")))
        print(f"[INFO] Tìm thấy {len(csv_files)} file CSV trong {input_path}")
        for csv_f in csv_files:
            process_csv_and_plot(str(csv_f), seg_length=args.seg_length, seed=args.seed)
    else:
        print(f"[ERROR] Đường dẫn không hợp lệ: {args.input_path}")

if __name__ == "__main__":
    main()
