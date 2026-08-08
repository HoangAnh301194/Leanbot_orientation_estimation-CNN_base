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


def run_clean_ema_experiments(csv_file: str, seg_length: int = 30, num_segments: int = 3, seed: int = 42):
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

    # ONLY ALPHAS 0.5, 0.7, 0.9
    alphas = [0.5, 0.7, 0.9]

    # Deep, Matte, High-Contrast Color Palette per Alpha Family:
    # - Alpha 0.5: Tím đậm (Smoothed) & Tím/Hồng dịu (Unsmoothed Traj Angle)
    # - Alpha 0.7: Xanh lá cây mờ/đậm (Smoothed) & Xanh lá nhạt dịu (Unsmoothed Traj Angle)
    # - Alpha 0.9: Xanh Ngọc Teal đậm mờ (Smoothed) & Xanh Ngọc nhạt dịu (Unsmoothed Traj Angle)
    alpha_colors = {
        0.5: '#9467bd', # Deep Purple
        0.7: '#2ca02c', # Emerald Green
        0.9: '#0e7490'  # Deep Matte Teal (Khôn bị chói, dịu mắt, tương phản cao)
    }
    traj_angle_colors = {
        0.5: '#e8a5e8', # Soft Pink/Purple
        0.7: '#8cd98c', # Soft Mint Green
        0.9: '#82c0c7'  # Soft Light Teal
    }

    # 1. Compute EMA streams for alphas 0.5, 0.7, 0.9
    for a in alphas:
        # 1st Pass: EMA on coordinates & Raw Angle
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

        # Tangent Angle computed from EMA Trajectory (atan2(-dy, dx))
        dx = valid_df[f'ema_x_a{a}'].diff()
        dy = valid_df[f'ema_y_a{a}'].diff()
        ema_traj_ang = np.degrees(np.arctan2(-dy, dx))
        ema_traj_ang.iloc[0] = valid_df[ang_col].iloc[0]
        ema_traj_ang = ema_traj_ang.bfill().ffill()
        valid_df[f'ema_traj_angle_a{a}'] = ema_traj_ang

        # 2nd Pass: EMA Smooth on Trajectory Tangent Angle using matching alpha
        smoother_angle = OnlineEMASmoother(alpha=a)
        ema_smooth_traj_ang = []
        for ang in valid_df[f'ema_traj_angle_a{a}']:
            _, _, sang = smoother_angle.update(0, 0, float(ang))
            ema_smooth_traj_ang.append(sang)
        valid_df[f'ema_smooth_traj_angle_a{a}'] = ema_smooth_traj_ang

    out_dir = csv_path.parent
    base_name = csv_path.stem.split('_polynomial_order2_length')[0]

    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 3 IMAGES: SELECTIVE EMA (Raw + EMA Vector Angle + EMA Traj Angle)
    # ─────────────────────────────────────────────────────────────────────────
    fig_traj, ax_traj = plt.subplots(figsize=(10, 8), dpi=150)
    ax_traj.plot(valid_df['x_center'], valid_df['y_center'], color='#d62728', linewidth=1.2, linestyle='-', alpha=0.6, label='Raw Trajectory (O)', zorder=1)
    ax_traj.scatter(valid_df['x_center'], valid_df['y_center'], color='#8b0000', s=12, marker='o', alpha=0.8, zorder=2)
    for a in alphas:
        ax_traj.plot(valid_df[f'ema_x_a{a}'], valid_df[f'ema_y_a{a}'], color=alpha_colors[a], linewidth=1.8, linestyle='-', label=f'EMA Trajectory (alpha={a})', zorder=5)

    ax_traj.invert_yaxis()
    ax_traj.set_title(f'2D Trajectory - Raw vs EMA (alpha = 0.5, 0.7, 0.9)\nFile: {csv_path.name}', fontsize=14, fontweight='bold')
    ax_traj.set_xlabel('X Center (px)')
    ax_traj.set_ylabel('Y Center (px)')
    ax_traj.grid(True, linestyle=':', alpha=0.5)
    ax_traj.legend(loc='best')
    plt.tight_layout()

    out_traj_img = out_dir / f"{base_name}_ema_selective_2d_trajectory.png"
    fig_traj.savefig(out_traj_img, dpi=150)
    plt.close(fig_traj)

    # Time Series (Section 3)
    fig_time, ax_ang = plt.subplots(figsize=(13, 7), dpi=150)
    raw_unwrapped = np.degrees(np.unwrap(np.radians(valid_df[ang_col])))
    ax_ang.plot(valid_df['frame_id'], raw_unwrapped, color='#8b0000', linewidth=2.5, linestyle='-', alpha=1.0, label='Raw Angle (Model)', zorder=10)

    for a in alphas:
        ema_ang_unwrapped = align_phase(np.degrees(np.unwrap(np.radians(valid_df[f'ema_angle_a{a}']))) , raw_unwrapped)
        ax_ang.plot(valid_df['frame_id'], ema_ang_unwrapped, color=alpha_colors[a], linewidth=1.8, linestyle='-', label=f'EMA Vector Angle (alpha={a})')

    for a in alphas:
        ema_traj_ang_unwrapped = align_phase(np.degrees(np.unwrap(np.radians(valid_df[f'ema_traj_angle_a{a}']))) , raw_unwrapped)
        ax_ang.plot(valid_df['frame_id'], ema_traj_ang_unwrapped, color=traj_angle_colors[a], linewidth=1.4, linestyle='-', label=f'EMA Traj Tangent Angle (alpha={a})')

    ax_ang.set_title(f'Heading Angle Time-Series - Raw vs EMA Vector Angle vs EMA Traj Angle (alpha = 0.5, 0.7, 0.9)\nFile: {csv_path.name}', fontsize=14, fontweight='bold')
    ax_ang.set_xlabel('Frame ID')
    ax_ang.set_ylabel('Degrees (Unwrapped)')
    ax_ang.grid(True, linestyle='--', alpha=0.6)
    ax_ang.legend(loc='best', fontsize=8)
    plt.tight_layout()

    out_time_img = out_dir / f"{base_name}_ema_selective_time_series.png"
    fig_time.savefig(out_time_img, dpi=150)
    plt.close(fig_time)

    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 4 IMAGES: DOUBLE SMOOTH (Teal 0.9, Green 0.7, Purple 0.5)
    # ─────────────────────────────────────────────────────────────────────────
    fig_traj4, ax_traj4 = plt.subplots(figsize=(10, 8), dpi=150)
    ax_traj4.plot(valid_df['x_center'], valid_df['y_center'], color='#d62728', linewidth=1.2, linestyle='-', alpha=0.6, label='Raw Trajectory (O)', zorder=1)
    ax_traj4.scatter(valid_df['x_center'], valid_df['y_center'], color='#8b0000', s=12, marker='o', alpha=0.8, zorder=2)
    for a in alphas:
        ax_traj4.plot(valid_df[f'ema_x_a{a}'], valid_df[f'ema_y_a{a}'], color=alpha_colors[a], linewidth=1.8, linestyle='-', label=f'EMA Trajectory (alpha={a})', zorder=5)

    ax_traj4.invert_yaxis()
    ax_traj4.set_title(f'2D Trajectory - Raw vs EMA Trajectory (alpha = 0.5, 0.7, 0.9)\nFile: {csv_path.name}', fontsize=14, fontweight='bold')
    ax_traj4.set_xlabel('X Center (px)')
    ax_traj4.set_ylabel('Y Center (px)')
    ax_traj4.grid(True, linestyle=':', alpha=0.5)
    ax_traj4.legend(loc='best')
    plt.tight_layout()

    out_traj4_img = out_dir / f"{base_name}_ema_double_smooth_2d_trajectory.png"
    fig_traj4.savefig(out_traj4_img, dpi=150)
    plt.close(fig_traj4)

    # Time Series for Section 4:
    fig_time4, ax_ang4 = plt.subplots(figsize=(13, 7), dpi=150)
    ax_ang4.plot(valid_df['frame_id'], raw_unwrapped, color='#8b0000', linewidth=2.5, linestyle='-', alpha=1.0, label='Raw Angle (Model)', zorder=10)

    # 1st Pass Tangent Angle (Light tone of alpha color family)
    for a in alphas:
        ema_traj_ang_unwrapped = align_phase(np.degrees(np.unwrap(np.radians(valid_df[f'ema_traj_angle_a{a}']))) , raw_unwrapped)
        ax_ang4.plot(valid_df['frame_id'], ema_traj_ang_unwrapped, color=traj_angle_colors[a], linewidth=1.4, linestyle='-', label=f'EMA Traj Angle (Raw alpha={a})')

    # 2nd Pass EMA Smooth Tangent Angle (Dark tone of alpha color family)
    for a in alphas:
        ema_smooth_traj_unwrapped = align_phase(np.degrees(np.unwrap(np.radians(valid_df[f'ema_smooth_traj_angle_a{a}']))) , raw_unwrapped)
        ax_ang4.plot(valid_df['frame_id'], ema_smooth_traj_unwrapped, color=alpha_colors[a], linewidth=2.0, linestyle='-', label=f'EMA Smooth Traj Angle (alpha={a})')

    ax_ang4.set_title(f'Heading Angle Time-Series - Raw vs EMA Traj Angle (Light) vs EMA Smooth Traj Angle (Dark)\nFile: {csv_path.name}', fontsize=14, fontweight='bold')
    ax_ang4.set_xlabel('Frame ID')
    ax_ang4.set_ylabel('Degrees (Unwrapped)')
    ax_ang4.grid(True, linestyle='--', alpha=0.6)
    ax_ang4.legend(loc='best', fontsize=8)
    plt.tight_layout()

    out_time4_img = out_dir / f"{base_name}_ema_double_smooth_time_series.png"
    fig_time4.savefig(out_time4_img, dpi=150)
    plt.close(fig_time4)

    # ─────────────────────────────────────────────────────────────────────────
    # Random Segments (Both Section 3 and Section 4)
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

        for idx_seg, start_idx in enumerate(selected_starts):
            seg = valid_df.iloc[start_idx : start_idx + seg_length].copy().reset_index(drop=True)
            frame_start = int(seg['frame_id'].iloc[0])
            frame_end = int(seg['frame_id'].iloc[-1])

            # Segment plot for Section 3
            fig_seg, (ax_st, ax_sa) = plt.subplots(1, 2, figsize=(16, 6.5), dpi=150)
            fig_seg.suptitle(f'Random Segment {idx_seg+1} Zoom-in ({seg_length} points: Frames {frame_start}-{frame_end})\nFile: {csv_path.name}', fontsize=13, fontweight='bold')

            ax_st.plot(seg['x_center'], seg['y_center'], color='#d62728', linewidth=1.2, linestyle='-', alpha=0.7, label='Raw Trajectory (O)', zorder=1)
            ax_st.scatter(seg['x_center'], seg['y_center'], color='#8b0000', s=16, marker='o', alpha=0.8, zorder=2)
            for a in alphas:
                ax_st.plot(seg[f'ema_x_a{a}'], seg[f'ema_y_a{a}'], color=alpha_colors[a], linewidth=2.0, linestyle='-', label=f'EMA Trajectory (alpha={a})', zorder=5)

            ax_st.invert_yaxis()
            ax_st.set_title(f'2D Trajectory Zoom-in ({seg_length} pts)', fontsize=11, fontweight='bold')
            ax_st.set_xlabel('X Center (px)')
            ax_st.set_ylabel('Y Center (px)')
            ax_st.grid(True, linestyle=':', alpha=0.6)
            ax_st.legend(loc='best', fontsize=8)

            seg_raw_unwrapped = np.degrees(np.unwrap(np.radians(seg[ang_col])))
            ax_sa.plot(seg['frame_id'], seg_raw_unwrapped, color='#8b0000', linewidth=2.5, linestyle='-', alpha=1.0, label='Raw Angle (Model)', zorder=10)
            for a in alphas:
                seg_ema_ang_unwrapped = align_phase(np.degrees(np.unwrap(np.radians(seg[f'ema_angle_a{a}']))) , seg_raw_unwrapped)
                ax_sa.plot(seg['frame_id'], seg_ema_ang_unwrapped, color=alpha_colors[a], linewidth=2.0, linestyle='-', label=f'EMA Vector Angle (alpha={a})')
            for a in alphas:
                seg_ema_traj_ang_unwrapped = align_phase(np.degrees(np.unwrap(np.radians(seg[f'ema_traj_angle_a{a}']))) , seg_raw_unwrapped)
                ax_sa.plot(seg['frame_id'], seg_ema_traj_ang_unwrapped, color=traj_angle_colors[a], linewidth=1.4, linestyle='-', label=f'EMA Traj Tangent Angle (alpha={a})')

            ax_sa.set_title(f'Heading Angle Zoom-in ({seg_length} pts)', fontsize=11, fontweight='bold')
            ax_sa.set_xlabel('Frame ID')
            ax_sa.set_ylabel('Degrees')
            ax_sa.grid(True, linestyle='--', alpha=0.6)
            ax_sa.legend(loc='best', fontsize=8)
            plt.tight_layout()

            out_seg_img = out_dir / f"{base_name}_ema_selective_seg{idx_seg+1}.png"
            fig_seg.savefig(out_seg_img, dpi=150)
            plt.close(fig_seg)

            # Segment plot for Section 4 (Matte Deep Colors: Purple 0.5, Green 0.7, Teal 0.9)
            fig_seg4, (ax_st4, ax_sa4) = plt.subplots(1, 2, figsize=(16, 6.5), dpi=150)
            fig_seg4.suptitle(f'Random Segment {idx_seg+1} Zoom-in (Frames {frame_start}-{frame_end}) - Matte Deep Color Palette\nFile: {csv_path.name}', fontsize=13, fontweight='bold')

            ax_st4.plot(seg['x_center'], seg['y_center'], color='#d62728', linewidth=1.2, linestyle='-', alpha=0.7, label='Raw Trajectory (O)', zorder=1)
            ax_st4.scatter(seg['x_center'], seg['y_center'], color='#8b0000', s=16, marker='o', alpha=0.8, zorder=2)
            for a in alphas:
                ax_st4.plot(seg[f'ema_x_a{a}'], seg[f'ema_y_a{a}'], color=alpha_colors[a], linewidth=2.0, linestyle='-', label=f'EMA Trajectory (alpha={a})', zorder=5)

            ax_st4.invert_yaxis()
            ax_st4.set_title(f'2D Trajectory Zoom-in ({seg_length} pts)', fontsize=11, fontweight='bold')
            ax_st4.set_xlabel('X Center (px)')
            ax_st4.set_ylabel('Y Center (px)')
            ax_st4.grid(True, linestyle=':', alpha=0.6)
            ax_st4.legend(loc='best', fontsize=8)

            ax_sa4.plot(seg['frame_id'], seg_raw_unwrapped, color='#8b0000', linewidth=2.5, linestyle='-', alpha=1.0, label='Raw Angle (Model)', zorder=10)

            # 1st Pass Tangent Angle (Light tone of alpha color family)
            for a in alphas:
                seg_ema_traj_unwrapped = align_phase(np.degrees(np.unwrap(np.radians(seg[f'ema_traj_angle_a{a}']))) , seg_raw_unwrapped)
                ax_sa4.plot(seg['frame_id'], seg_ema_traj_unwrapped, color=traj_angle_colors[a], linewidth=1.4, linestyle='-', label=f'EMA Traj Angle (Raw alpha={a})')

            # 2nd Pass EMA Smooth Tangent Angle (Dark tone of alpha color family)
            for a in alphas:
                seg_ema_smooth_traj_unwrapped = align_phase(np.degrees(np.unwrap(np.radians(seg[f'ema_smooth_traj_angle_a{a}']))) , seg_raw_unwrapped)
                ax_sa4.plot(seg['frame_id'], seg_ema_smooth_traj_unwrapped, color=alpha_colors[a], linewidth=2.0, linestyle='-', label=f'EMA Smooth Traj Angle (alpha={a})')

            ax_sa4.set_title(f'Heading Angle Zoom-in (Alpha Families: Purple 0.5, Green 0.7, Teal 0.9)', fontsize=11, fontweight='bold')
            ax_sa4.set_xlabel('Frame ID')
            ax_sa4.set_ylabel('Degrees')
            ax_sa4.grid(True, linestyle='--', alpha=0.6)
            ax_sa4.legend(loc='best', fontsize=8)
            plt.tight_layout()

            out_seg4_img = out_dir / f"{base_name}_ema_double_smooth_seg{idx_seg+1}.png"
            fig_seg4.savefig(out_seg4_img, dpi=150)
            plt.close(fig_seg4)

    print(f"[SUCCESS] Đã lưu thành công bộ đồ thị Section 3 & Section 4 với bảng màu dịu mắt (Tím, Xanh lá, Xanh Ngọc Teal) cho file {csv_path.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Selective & Double Smooth EMA Plotting with Deep Matte Color Palette")
    parser.add_argument("csv_file", type=str, help="Path to input benchmark CSV file")
    parser.add_argument("--seg-len", type=int, default=30, help="Segment length (default 30)")
    parser.add_argument("--num-segs", type=int, default=3, help="Number of random segments (default 3)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default 42)")
    args = parser.parse_args()

    run_clean_ema_experiments(args.csv_file, seg_length=args.seg_len, num_segments=args.num_segs, seed=args.seed)
