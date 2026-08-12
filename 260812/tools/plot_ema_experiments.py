import argparse
import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Ensure UTF-8 output for console terminal
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

class OnlineEMASmoother:
    """Online Streaming Exponential Moving Average Smoother.
    Strictly point-by-point online processing without using future data.
    - Coordinates: S_x(t) = alpha * x(t) + (1 - alpha) * S_x(t-1)
    - Vectorized Angle: S_sin(t) = alpha * sin(angle) + (1 - alpha) * S_sin(t-1)
                       S_cos(t) = alpha * cos(angle) + (1 - alpha) * S_cos(t-1)
                       angle_ema(t) = atan2(S_sin(t), S_cos(t))
    """
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
    diff = target_arr[0] - ref_arr[0]
    k = np.round(diff / 360.0)
    return target_arr - k * 360.0


def run_ema_experiments(csv_file: str, seg_length: int = 30, num_segments: int = 3, seed: int = 42):
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

    valid_df = df[df['tracking_lost'] == 0].copy() if 'tracking_lost' in df.columns else df.copy()
    valid_df = valid_df.reset_index(drop=True)

    has_raw = 'x_center' in valid_df.columns and 'y_center' in valid_df.columns
    if not has_raw:
        print(f"[ERROR] Thiếu cột x_center/y_center trong file {csv_file}")
        return

    ang_col = next((c for c in ('raw_angle', 'group1_angle', 'angle') if c in valid_df.columns), None)
    if not ang_col:
        print(f"[ERROR] Thiếu cột góc raw trong file {csv_file}")
        return

    alphas = [0.1, 0.3, 0.5, 0.7, 0.9]
    alpha_colors = {
        0.1: '#8c564b', # Brown
        0.3: '#e377c2', # Pink
        0.5: '#7f7f7f', # Gray
        0.7: '#bcbd22', # Yellow-green
        0.9: '#17becf'  # Cyan
    }

    # 1. Calculate Online EMA Streams over full dataset for all alphas
    for a in alphas:
        smoother = OnlineEMASmoother(alpha=a)
        ema_x, ema_y, ema_ang = [], [], []
        for _, row in valid_df.iterrows():
            cx = float(row['x_center'])
            cy = float(row['y_center'])
            ang = float(row[ang_col])
            sx, sy, sang = smoother.update(cx, cy, ang)
            ema_x.append(sx)
            ema_y.append(sy)
            ema_ang.append(sang)

        valid_df[f'ema_x_a{a}'] = ema_x
        valid_df[f'ema_y_a{a}'] = ema_y
        valid_df[f'ema_angle_a{a}'] = ema_ang

    out_dir = csv_path.parent
    base_name = csv_path.stem

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Đồ thị Quỹ đạo 2D Tổng hợp (2D Trajectory - All Methods & All Alphas)
    # ─────────────────────────────────────────────────────────────────────────
    fig_traj, ax_traj = plt.subplots(figsize=(10, 8), dpi=150)
    ax_traj.plot(valid_df['x_center'], valid_df['y_center'], color='#d62728', linewidth=1.2, linestyle='-', alpha=0.6, label='Raw Trajectory (O)', zorder=1)
    ax_traj.scatter(valid_df['x_center'], valid_df['y_center'], color='#8b0000', s=10, marker='o', alpha=0.7, zorder=2)

    if 'smooth_x' in valid_df.columns:
        ax_traj.plot(valid_df['smooth_x'], valid_df['smooth_y'], color='#1f77b4', linewidth=1.5, linestyle='-', alpha=0.7, label='Smooth 1st Pass Poly (X)', zorder=3)
        ax_traj.scatter(valid_df['smooth_x'], valid_df['smooth_y'], color='#003366', s=14, marker='x', alpha=0.8, zorder=4)

    if 'smooth_x2' in valid_df.columns:
        ax_traj.plot(valid_df['smooth_x2'], valid_df['smooth_y2'], color='#2ca02c', linewidth=1.8, linestyle='-', alpha=0.8, label='Smooth 2nd Pass Poly (+)', zorder=5)
        ax_traj.scatter(valid_df['smooth_x2'], valid_df['smooth_y2'], color='#006600', s=18, marker='+', alpha=0.9, zorder=6)

    for a in alphas:
        ax_traj.plot(valid_df[f'ema_x_a{a}'], valid_df[f'ema_y_a{a}'], color=alpha_colors[a], linewidth=1.5, linestyle='-', label=f'EMA (alpha={a})', zorder=7)

    ax_traj.invert_yaxis()
    ax_traj.set_title(f'2D Trajectory - EMA Alphas vs Poly Smooth vs Raw\n{csv_path.name}', fontsize=14, fontweight='bold')
    ax_traj.set_xlabel('X Center (px)')
    ax_traj.set_ylabel('Y Center (px)')
    ax_traj.grid(True, linestyle=':', alpha=0.5)
    ax_traj.legend(loc='best')
    plt.tight_layout()

    out_traj_img = out_dir / f"{base_name}_ema_2d_trajectory.png"
    fig_traj.savefig(out_traj_img, dpi=150)
    plt.close(fig_traj)
    print(f"[SUCCESS] Đã lưu đồ thị quỹ đạo 2D tổng hợp tại: {out_traj_img}")

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Biểu đồ Chuỗi Thời gian Góc (Time-Series - All Methods & All Alphas)
    # ─────────────────────────────────────────────────────────────────────────
    fig_time, ax_ang = plt.subplots(figsize=(12, 6), dpi=150)
    raw_unwrapped = np.degrees(np.unwrap(np.radians(valid_df[ang_col])))
    # Line 149 in full time-series:
    ax_ang.plot(valid_df['frame_id'], raw_unwrapped, color='#8b0000', linewidth=2.5, linestyle='-', alpha=1.0, label='Raw Angle (Model)', zorder=10)

    if 'smooth_angle' in valid_df.columns:
        smooth_unwrapped = align_phase(np.degrees(np.unwrap(np.radians(valid_df['smooth_angle']))), raw_unwrapped)
        ax_ang.plot(valid_df['frame_id'], smooth_unwrapped, color='#ff7f00', linewidth=1.2, linestyle='-', alpha=0.6, label='Smooth Angle (1st Pass)')

    if 'smooth_angle_smooth' in valid_df.columns:
        smooth_angle_smooth = align_phase(np.degrees(np.unwrap(np.radians(valid_df['smooth_angle_smooth']))), raw_unwrapped)
        ax_ang.plot(valid_df['frame_id'], smooth_angle_smooth, color='#9467bd', linewidth=1.6, linestyle='-', label='Smooth Angle Smooth (Poly)')

    if 'smooth_angle2_smooth' in valid_df.columns:
        smooth_angle2_smooth = align_phase(np.degrees(np.unwrap(np.radians(valid_df['smooth_angle2_smooth']))), raw_unwrapped)
        ax_ang.plot(valid_df['frame_id'], smooth_angle2_smooth, color='#e377c2', linewidth=1.8, linestyle='-', label='Smooth Angle2 Smooth (Double Poly)')

    for a in alphas:
        ema_ang_unwrapped = align_phase(np.degrees(np.unwrap(np.radians(valid_df[f'ema_angle_a{a}']))) , raw_unwrapped)
        ax_ang.plot(valid_df['frame_id'], ema_ang_unwrapped, color=alpha_colors[a], linewidth=1.4, linestyle='-', label=f'EMA Vector (alpha={a})')

    ax_ang.set_title(f'Heading Angle Time-Series - EMA Alphas vs Poly Smooth vs Raw\n{csv_path.name}', fontsize=14, fontweight='bold')
    ax_ang.set_xlabel('Frame ID')
    ax_ang.set_ylabel('Degrees (Unwrapped)')
    ax_ang.grid(True, linestyle='--', alpha=0.6)
    ax_ang.legend(loc='best', fontsize=8)
    plt.tight_layout()

    out_time_img = out_dir / f"{base_name}_ema_time_series.png"
    fig_time.savefig(out_time_img, dpi=150)
    plt.close(fig_time)
    print(f"[SUCCESS] Đã lưu biểu đồ chuỗi thời gian góc tại: {out_time_img}")

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Trích xuất 3 Đoạn ngẫu nhiên (3 Segments x 30 points) cho TỪNG Alpha
    # ─────────────────────────────────────────────────────────────────────────
    n_points = len(valid_df)
    if n_points >= seg_length:
        np.random.seed(seed)
        max_start = n_points - seg_length
        candidate_starts = list(range(0, max_start, 5))
        np.random.shuffle(candidate_starts)

        selected_starts = []
        for start in candidate_starts:
            if not any(abs(start - s) < seg_length for s in selected_starts):
                selected_starts.append(start)
                if len(selected_starts) == num_segments:
                    break
        selected_starts.sort()

        print(f"\n[INFO] Đã chọn {len(selected_starts)} đoạn {seg_length} điểm cho {csv_path.name}:")
        for idx_seg, start_idx in enumerate(selected_starts):
            seg = valid_df.iloc[start_idx : start_idx + seg_length].copy().reset_index(drop=True)
            frame_start = int(seg['frame_id'].iloc[0])
            frame_end = int(seg['frame_id'].iloc[-1])
            print(f"  📌 Segment {idx_seg+1}: Frames [{frame_start} .. {frame_end}]")

            # A. Đồ thị Segment Tổng hợp tất cả các mức Alpha
            fig_seg_all, (ax_st, ax_sa) = plt.subplots(1, 2, figsize=(15, 6), dpi=150)
            fig_seg_all.suptitle(f'Random Segment {idx_seg+1} Zoom-in ({seg_length} points: Frames {frame_start}-{frame_end}) - All Alphas\nFile: {csv_path.name}', fontsize=13, fontweight='bold')

            # Trajectory Zoom-in
            ax_st.plot(seg['x_center'], seg['y_center'], color='#d62728', linewidth=1.2, linestyle='-', alpha=0.7, label='Raw Trajectory (O)', zorder=1)
            ax_st.scatter(seg['x_center'], seg['y_center'], color='#8b0000', s=16, marker='o', alpha=0.8, zorder=2)
            if 'smooth_x' in seg.columns:
                ax_st.plot(seg['smooth_x'], seg['smooth_y'], color='#1f77b4', linewidth=1.6, linestyle='-', alpha=0.8, label='Smooth 1st Pass Poly (X)', zorder=3)
                ax_st.scatter(seg['smooth_x'], seg['smooth_y'], color='#003366', s=24, marker='x', alpha=0.9, zorder=4)
            if 'smooth_x2' in seg.columns:
                ax_st.plot(seg['smooth_x2'], seg['smooth_y2'], color='#2ca02c', linewidth=2.0, linestyle='-', alpha=0.9, label='Smooth 2nd Pass Poly (+)', zorder=5)
                ax_st.scatter(seg['smooth_x2'], seg['smooth_y2'], color='#006600', s=32, marker='+', alpha=1.0, zorder=6)

            for a in alphas:
                ax_st.plot(seg[f'ema_x_a{a}'], seg[f'ema_y_a{a}'], color=alpha_colors[a], linewidth=1.8, linestyle='-', label=f'EMA (alpha={a})', zorder=7)

            ax_st.invert_yaxis()
            ax_st.set_title(f'2D Trajectory Zoom-in ({seg_length} pts)', fontsize=11, fontweight='bold')
            ax_st.set_xlabel('X Center (px)')
            ax_st.set_ylabel('Y Center (px)')
            ax_st.grid(True, linestyle=':', alpha=0.6)
            ax_st.legend(loc='best', fontsize=8)

            # Angle Zoom-in (Dark red bold Raw Angle line)
            seg_raw_unwrapped = np.degrees(np.unwrap(np.radians(seg[ang_col])))
            ax_sa.plot(seg['frame_id'], seg_raw_unwrapped, color='#8b0000', linewidth=2.5, linestyle='-', alpha=1.0, label='Raw Angle (Model)', zorder=10)
            if 'smooth_angle' in seg.columns:
                seg_smooth_unwrapped = align_phase(np.degrees(np.unwrap(np.radians(seg['smooth_angle']))), seg_raw_unwrapped)
                ax_sa.plot(seg['frame_id'], seg_smooth_unwrapped, color='#ff7f00', linewidth=1.4, linestyle='-', alpha=0.7, label='Smooth Angle (1st Pass)')
            if 'smooth_angle_smooth' in seg.columns:
                seg_smooth_angle_smooth = align_phase(np.degrees(np.unwrap(np.radians(seg['smooth_angle_smooth']))), seg_raw_unwrapped)
                ax_sa.plot(seg['frame_id'], seg_smooth_angle_smooth, color='#9467bd', linewidth=1.8, linestyle='-', label='Smooth Angle Smooth (Poly)')
            if 'smooth_angle2_smooth' in seg.columns:
                seg_smooth_angle2_smooth = align_phase(np.degrees(np.unwrap(np.radians(seg['smooth_angle2_smooth']))), seg_raw_unwrapped)
                ax_sa.plot(seg['frame_id'], seg_smooth_angle2_smooth, color='#e377c2', linewidth=2.0, linestyle='-', label='Smooth Angle2 Smooth (Double Poly)')

            for a in alphas:
                seg_ema_ang_unwrapped = align_phase(np.degrees(np.unwrap(np.radians(seg[f'ema_angle_a{a}']))) , seg_raw_unwrapped)
                ax_sa.plot(seg['frame_id'], seg_ema_ang_unwrapped, color=alpha_colors[a], linewidth=1.8, linestyle='-', label=f'EMA Vector (alpha={a})')

            ax_sa.set_title(f'Heading Angle Zoom-in ({seg_length} pts)', fontsize=11, fontweight='bold')
            ax_sa.set_xlabel('Frame ID')
            ax_sa.set_ylabel('Degrees')
            ax_sa.grid(True, linestyle='--', alpha=0.6)
            ax_sa.legend(loc='best', fontsize=8)

            plt.tight_layout()
            out_seg_all_img = out_dir / f"{base_name}_ema_random_seg{idx_seg+1}.png"
            fig_seg_all.savefig(out_seg_all_img, dpi=150)
            plt.close(fig_seg_all)
            print(f"   --> Đã lưu đồ thị segment {idx_seg+1} tổng hợp tại: {out_seg_all_img}")

            # B. Đồ thị Segment Chi tiết Từng giá trị Alpha riêng biệt (alpha = 0.1, 0.3, 0.5, 0.7, 0.9)
            for a in alphas:
                fig_seg_a, (ax_sat, ax_saa) = plt.subplots(1, 2, figsize=(15, 6), dpi=150)
                fig_seg_a.suptitle(f'Segment {idx_seg+1} Zoom-in ({seg_length} pts: Frames {frame_start}-{frame_end}) - Alpha={a}\nFile: {csv_path.name}', fontsize=13, fontweight='bold')

                # Trajectory
                ax_sat.plot(seg['x_center'], seg['y_center'], color='#d62728', linewidth=1.2, linestyle='-', alpha=0.7, label='Raw Trajectory (O)', zorder=1)
                ax_sat.scatter(seg['x_center'], seg['y_center'], color='#8b0000', s=16, marker='o', alpha=0.8, zorder=2)
                if 'smooth_x' in seg.columns:
                    ax_sat.plot(seg['smooth_x'], seg['smooth_y'], color='#1f77b4', linewidth=1.6, linestyle='-', alpha=0.8, label='Smooth 1st Pass Poly (X)', zorder=3)
                    ax_sat.scatter(seg['smooth_x'], seg['smooth_y'], color='#003366', s=24, marker='x', alpha=0.9, zorder=4)
                if 'smooth_x2' in seg.columns:
                    ax_sat.plot(seg['smooth_x2'], seg['smooth_y2'], color='#2ca02c', linewidth=2.0, linestyle='-', alpha=0.9, label='Smooth 2nd Pass Poly (+)', zorder=5)
                    ax_sat.scatter(seg['smooth_x2'], seg['smooth_y2'], color='#006600', s=32, marker='+', alpha=1.0, zorder=6)

                ax_sat.plot(seg[f'ema_x_a{a}'], seg[f'ema_y_a{a}'], color=alpha_colors[a], linewidth=2.2, linestyle='-', label=f'EMA Stream (alpha={a})', zorder=7)

                ax_sat.invert_yaxis()
                ax_sat.set_title(f'2D Trajectory Zoom-in (Alpha={a})', fontsize=11, fontweight='bold')
                ax_sat.set_xlabel('X Center (px)')
                ax_sat.set_ylabel('Y Center (px)')
                ax_sat.grid(True, linestyle=':', alpha=0.6)
                ax_sat.legend(loc='best', fontsize=8)

                # Angle (Dark red bold Raw Angle line)
                ax_saa.plot(seg['frame_id'], seg_raw_unwrapped, color='#8b0000', linewidth=2.5, linestyle='-', alpha=1.0, label='Raw Angle (Model)', zorder=10)
                if 'smooth_angle' in seg.columns:
                    ax_saa.plot(seg['frame_id'], seg_smooth_unwrapped, color='#ff7f00', linewidth=1.4, linestyle='-', alpha=0.7, label='Smooth Angle (1st Pass)')
                if 'smooth_angle_smooth' in seg.columns:
                    ax_saa.plot(seg['frame_id'], seg_smooth_angle_smooth, color='#9467bd', linewidth=1.8, linestyle='-', label='Smooth Angle Smooth (Poly)')
                if 'smooth_angle2_smooth' in seg.columns:
                    ax_saa.plot(seg['frame_id'], seg_smooth_angle2_smooth, color='#e377c2', linewidth=2.0, linestyle='-', label='Smooth Angle2 Smooth (Double Poly)')

                seg_ema_ang_unwrapped = align_phase(np.degrees(np.unwrap(np.radians(seg[f'ema_angle_a{a}']))) , seg_raw_unwrapped)
                ax_saa.plot(seg['frame_id'], seg_ema_ang_unwrapped, color=alpha_colors[a], linewidth=2.2, linestyle='-', label=f'EMA Vector (alpha={a})')

                ax_saa.set_title(f'Heading Angle Zoom-in (Alpha={a})', fontsize=11, fontweight='bold')
                ax_saa.set_xlabel('Frame ID')
                ax_saa.set_ylabel('Degrees')
                ax_saa.grid(True, linestyle='--', alpha=0.6)
                ax_saa.legend(loc='best', fontsize=8)

                plt.tight_layout()
                out_seg_alpha_img = out_dir / f"{base_name}_ema_alpha{a}_seg{idx_seg+1}.png"
                fig_seg_a.savefig(out_seg_alpha_img, dpi=150)
                plt.close(fig_seg_a)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Online EMA Streaming Experiments for Trajectory and Vectorized Angle")
    parser.add_argument("csv_file", type=str, help="Path to input benchmark CSV file")
    parser.add_argument("--seg-len", type=int, default=30, help="Random segment zoom-in length (default 30)")
    parser.add_argument("--num-segs", type=int, default=3, help="Number of random segments (default 3)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for segment extraction (default 42)")
    args = parser.parse_args()

    run_ema_experiments(args.csv_file, seg_length=args.seg_len, num_segments=args.num_segs, seed=args.seed)
