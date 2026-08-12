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


def sliding_window_poly2(x_arr: np.ndarray, y_arr: np.ndarray, window_size: int = 18):
    """Tính toán Polynomial Bậc 2 trên cửa sổ trượt (Sliding Window SMOOTH_LENGTH=18).
    Trả về vị trí mượt (x_smooth, y_smooth) và đạo hàm (dx_dt, dy_dt) tại điểm giữa cửa sổ.
    """
    n = len(x_arr)
    x_smooth = np.zeros(n)
    y_smooth = np.zeros(n)
    dx_dt = np.zeros(n)
    dy_dt = np.zeros(n)

    half_w = window_size // 2
    for i in range(n):
        w_start = max(0, i - half_w)
        w_end = min(n, i + half_w + 1)
        if w_end - w_start < 3:
            w_start = max(0, i - 1)
            w_end = min(n, i + 2)

        t_sub = np.arange(w_start, w_end) - i
        x_sub = x_arr[w_start:w_end]
        y_sub = y_arr[w_start:w_end]

        px = np.polyfit(t_sub, x_sub, deg=2)
        py = np.polyfit(t_sub, y_sub, deg=2)

        # Tại t_sub = 0 (tương ứng với khung hình i)
        x_smooth[i] = px[2]
        y_smooth[i] = py[2]
        dx_dt[i] = px[1]
        dy_dt[i] = py[1]

    return x_smooth, y_smooth, dx_dt, dy_dt


def find_full_pass_moving_segment(df: pd.DataFrame, buffer_frames: int = 10, seed: int = 42):
    """Tự động phát hiện các lượt di chuyển liên tục (Continuous Moving Blocks)
    và trích xuất gần như toàn bộ lượt chạy ngang sa bàn (chỉ bỏ buffer_frames ở 2 đầu chưa ổn định).
    """
    valid_df = df[df['tracking_lost'] == 0].copy() if 'tracking_lost' in df.columns else df.copy()
    valid_df = valid_df.reset_index(drop=True)
    n = len(valid_df)
    if n <= 2 * buffer_frames:
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
            if i - start >= 30:
                blocks.append((start, i))
            start = None
    if start is not None and n - start >= 30:
        blocks.append((start, n))

    if not blocks:
        return valid_df.iloc[buffer_frames : max(buffer_frames + 1, n - buffer_frames)].copy().reset_index(drop=True)

    # Chọn 1 block liên tục bằng seed
    np.random.seed(seed)
    selected_block = blocks[np.random.choice(len(blocks))]
    
    b_start, b_end = selected_block
    seg_start = min(b_start + buffer_frames, b_end - 1)
    seg_end = max(b_end - buffer_frames, seg_start + 1)

    return valid_df.iloc[seg_start : seg_end].copy().reset_index(drop=True)


def process_csv_and_plot(csv_file: str, seed: int = 42, smooth_length: int = 18):
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

    # Trích xuất gần như toàn bộ lượt chạy ngang sa bàn (bỏ 10 frame chưa ổn định ở 2 đầu)
    seg = find_full_pass_moving_segment(df, buffer_frames=10, seed=seed)
    n_seg = len(seg)
    frame_start = int(seg['frame_id'].iloc[0]) if 'frame_id' in seg.columns else 0
    frame_end = int(seg['frame_id'].iloc[-1]) if 'frame_id' in seg.columns else n_seg - 1

    print(f"[INFO] File: {csv_path.name} -> Đoạn chạy toàn phần ({n_seg} điểm, Frames {frame_start} - {frame_end})")

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

    x_raw = seg['x_center'].values
    y_raw = seg['y_center'].values

    # Tính toán Polynomial Bậc 2 trên cửa sổ trượt (Sliding Window SMOOTH_LENGTH=18)
    x_poly2_pts, y_poly2_pts, dx_poly2_dt, dy_poly2_dt = sliding_window_poly2(x_raw, y_raw, window_size=smooth_length)

    poly2_tangent_rad = np.unwrap(np.arctan2(-dy_poly2_dt, dx_poly2_dt))
    poly2_tangent_deg = np.degrees(poly2_tangent_rad)

    raw_unwrapped = np.degrees(np.unwrap(np.radians(seg[ang_col])))
    poly2_angle_aligned = align_phase(poly2_tangent_deg, raw_unwrapped)

    frame_ids = seg['frame_id'].values if 'frame_id' in seg.columns else np.arange(n_seg)

    # ─────────────────────────────────────────────────────────────────────────
    # ẢNH 1: Biểu đồ Quỹ đạo 2D (Raw vs EMA vs Polynomial Bậc 2 Sliding Window)
    # ─────────────────────────────────────────────────────────────────────────
    fig_traj, ax_traj = plt.subplots(figsize=(9, 7), dpi=150)
    ax_traj.plot(seg['x_center'], seg['y_center'], color='#d62728', linewidth=1.5, linestyle='-', alpha=0.5, label='Raw Trajectory (O)', zorder=1)
    ax_traj.scatter(seg['x_center'], seg['y_center'], color='#8b0000', s=15, marker='o', alpha=0.6, zorder=2)
    
    for a in alphas:
        ax_traj.plot(seg[f'ema_x_a{a}'], seg[f'ema_y_a{a}'], color=alpha_colors[a], linewidth=1.8, linestyle='-', label=f'EMA (alpha={a})', zorder=4)

    # Thêm đường Polynomial Bậc 2 nét liền trên 2D Trajectory (Cửa sổ trượt 18)
    ax_traj.plot(x_poly2_pts, y_poly2_pts, color='#0055ff', linewidth=2.4, linestyle='-', label=f'Polynomial Fit Bậc 2 (Sliding W={smooth_length})', zorder=6)

    ax_traj.invert_yaxis()
    ax_traj.set_title(f'2D Trajectory Full Pass (Single Unidirectional Pass)\nFile: {csv_path.name} (Frames {frame_start}-{frame_end})', fontsize=12, fontweight='bold')
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
    # ẢNH 2: Đồ thị góc Raw_angle và các đường EMA của góc tiếp tuyến
    # ─────────────────────────────────────────────────────────────────────────
    fig_ema_time, ax_ang = plt.subplots(figsize=(11, 6), dpi=150)
    ax_ang.plot(frame_ids, raw_unwrapped, color='#8b0000', linewidth=2.5, linestyle='-', label='Raw Angle (Model)', zorder=10)

    for a in alphas:
        ema_traj_ang_unwrapped = align_phase(np.degrees(np.unwrap(np.radians(seg[f'ema_traj_angle_a{a}']))), raw_unwrapped)
        ax_ang.plot(frame_ids, ema_traj_ang_unwrapped, color=traj_angle_colors[a], linewidth=1.8, linestyle='-', label=f'EMA Traj Tangent Angle (alpha={a})')

    ax_ang.set_title(f'a) Heading Angle Time-Series (Raw vs EMA Traj Tangent Angle - Single Pass)\nFile: {csv_path.name} (Frames {frame_start}-{frame_end})', fontsize=12, fontweight='bold')
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
    # ẢNH 3: Đồ thị góc Raw_angle và đường làm mượt Polynomial Bậc 2 của góc tiếp tuyến
    # ─────────────────────────────────────────────────────────────────────────
    fig_poly_time, ax_p_ang = plt.subplots(figsize=(11, 6), dpi=150)

    ax_p_ang.plot(frame_ids, raw_unwrapped, color='#8b0000', linewidth=2.2, linestyle='-', alpha=0.7, label='Raw Angle (Model)', zorder=1)
    ax_p_ang.plot(frame_ids, poly2_angle_aligned, color='#0055ff', linewidth=2.4, linestyle='-', label=f'Polynomial Fit Bậc 2 Tangent Angle (Sliding W={smooth_length})', zorder=5)

    ax_p_ang.set_title(f'b) Heading Angle Time-Series (Raw vs Poly Fit Bậc 2 Tangent Angle - Sliding W={smooth_length})\nFile: {csv_path.name} (Frames {frame_start}-{frame_end})', fontsize=12, fontweight='bold')
    ax_p_ang.set_xlabel('Frame ID')
    ax_p_ang.set_ylabel('Angle (Degrees)')
    ax_p_ang.grid(True, linestyle=':', alpha=0.6)
    ax_p_ang.legend(loc='best')
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
    parser.add_argument("--seed", type=int, default=42, help="Random seed chọn đoạn")
    parser.add_argument("--smooth-length", type=int, default=18, help="Cửa sổ trượt polynomial (mặc định 18)")
    args = parser.parse_args()

    input_path = Path(args.input_path)
    if input_path.is_file() and input_path.suffix == '.csv':
        process_csv_and_plot(str(input_path), seed=args.seed, smooth_length=args.smooth_length)
    elif input_path.is_dir():
        csv_files = sorted(list(input_path.glob("*.csv")))
        print(f"[INFO] Tìm thấy {len(csv_files)} file CSV trong {input_path}")
        for csv_f in csv_files:
            process_csv_and_plot(str(csv_f), seed=args.seed, smooth_length=args.smooth_length)
    else:
        print(f"[ERROR] Đường dẫn không hợp lệ: {args.input_path}")

if __name__ == "__main__":
    main()

