import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import argparse
from pathlib import Path
import sys

# Ensure UTF-8 output
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def plot_random_5segments(csv_file: str, num_segments: int = 5, seg_length: int = 30, seed: int = 42):
    csv_path = Path(csv_file)
    if not csv_path.exists():
        print(f"[ERROR] File CSV không tồn tại: {csv_file}")
        return

    df = pd.read_csv(csv_path)
    if df.empty:
        print(f"[ERROR] File CSV {csv_file} rỗng.")
        return

    if 'frame_id' in df.columns:
        df = df.sort_values('frame_id').reset_index(drop=True)

    # Filter out lost tracking frames if available
    valid_df = df[df['tracking_lost'] == 0].copy() if 'tracking_lost' in df.columns else df.copy()
    n_points = len(valid_df)

    if n_points < seg_length:
        print(f"[ERROR] Tổng số điểm hợp lệ ({n_points}) nhỏ hơn chiều dài segment ({seg_length}).")
        return

    np.random.seed(seed)
    max_start = n_points - seg_length
    # Pick num_segments non-overlapping random start indices
    candidate_starts = list(range(0, max_start, 5))
    np.random.shuffle(candidate_starts)

    selected_starts = []
    for start in candidate_starts:
        if not any(abs(start - s) < seg_length for s in selected_starts):
            selected_starts.append(start)
            if len(selected_starts) == num_segments:
                break

    selected_starts.sort()
    out_dir = csv_path.parent
    base_name = csv_path.stem

    ang_col = 'group1_angle' if 'group1_angle' in df.columns else ('angle' if 'angle' in df.columns else None)

    print(f"[INFO] Đã chọn ngẫu nhiên {len(selected_starts)} đoạn 30 điểm từ {csv_path.name} (seed={seed}):")

    saved_images = []
    for i, start_idx in enumerate(selected_starts):
        seg = valid_df.iloc[start_idx : start_idx + seg_length].copy().reset_index(drop=True)
        frame_start = int(seg['frame_id'].iloc[0])
        frame_end = int(seg['frame_id'].iloc[-1])

        print(f"  📌 Segment {i+1}: Frames [{frame_start} .. {frame_end}] (Indices {start_idx}..{start_idx+seg_length-1})")

        # Compute smooth angle with Cartesian Y (-dy)
        dx = seg['smooth_x'].diff()
        dy = seg['smooth_y'].diff()
        smooth_ang = np.degrees(np.arctan2(-dy, dx))
        if ang_col:
            smooth_ang.iloc[0] = seg[ang_col].iloc[0]
        else:
            smooth_ang.iloc[0] = 0.0
        smooth_ang = smooth_ang.bfill().ffill()

        # Unwrapping angles for smooth graph display
        if ang_col:
            raw_unwrapped = np.degrees(np.unwrap(np.radians(seg[ang_col])))
        else:
            raw_unwrapped = np.zeros(seg_length)

        smooth_unwrapped = np.degrees(np.unwrap(np.radians(smooth_ang)))

        # Create 2-panel subplot figure for this 30-point segment
        fig, (ax_traj, ax_ang) = plt.subplots(1, 2, figsize=(14, 6), dpi=150)
        fig.suptitle(f'Random Segment {i+1} Zoom-in (Frames {frame_start} - {frame_end})\nFile: {csv_path.name}', fontsize=13, fontweight='bold')

        # ── Panel 1: 2D Trajectory Zoom-in (30 points) ──
        # Smooth line & X markers
        ax_traj.plot(seg['smooth_x'], seg['smooth_y'], color='#1f77b4', linewidth=1.8, label='Smooth Trajectory (Poly deg=2)', zorder=1)
        ax_traj.scatter(seg['smooth_x'], seg['smooth_y'], color='#003366', s=25, marker='x', label='Smooth Points (X)', zorder=2)

        # Raw line & O markers
        ax_traj.plot(seg['x_center'], seg['y_center'], color='#d62728', linewidth=1.0, linestyle='--', alpha=0.65, label='Raw Trajectory', zorder=3)
        ax_traj.scatter(seg['x_center'], seg['y_center'], color='#8b0000', s=15, marker='o', alpha=0.7, label='Raw Points (O)', zorder=4)

        ax_traj.invert_yaxis()  # Image Y-axis upside down
        ax_traj.set_title(f'2D Trajectory Zoom-in (30 points)', fontsize=11, fontweight='bold')
        ax_traj.set_xlabel('X Center (px)')
        ax_traj.set_ylabel('Y Center (px)')
        ax_traj.grid(True, linestyle=':', alpha=0.6)
        ax_traj.legend(loc='best', fontsize=9)

        # ── Panel 2: Angle Comparison Zoom-in (Raw vs Smooth Angle) ──
        ax_ang.plot(seg['frame_id'], raw_unwrapped, 'b.-', linewidth=1.2, markersize=5, alpha=0.7, label='Raw Angle (Inference)')
        ax_ang.plot(seg['frame_id'], smooth_unwrapped, 'x-', color='#ff7f00', linewidth=1.8, markersize=6, label='Smooth Angle (Trajectory Vector)')

        ax_ang.set_title(f'Heading Angle Zoom-in (Raw vs Smooth)', fontsize=11, fontweight='bold')
        ax_ang.set_xlabel('Frame ID')
        ax_ang.set_ylabel('Angle (Degrees Unwrapped)')
        ax_ang.grid(True, linestyle='--', alpha=0.7)
        ax_ang.legend(loc='best', fontsize=9)

        plt.tight_layout()
        out_img = out_dir / f"{base_name}_random_seg{i+1}.png"
        fig.savefig(out_img, dpi=150)
        plt.close(fig)
        saved_images.append(out_img)
        print(f"     --> Đã lưu đồ thị segment {i+1} tại: {out_img}")

    return saved_images

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trích xuất và vẽ đồ thị zoom-in 5 đoạn 30 điểm ngẫu nhiên từ log CSV")
    parser.add_argument("csv_file", type=str, help="Đường dẫn file CSV log")
    parser.add_argument("--num", type=int, default=5, help="Số đoạn ngẫu nhiên (mặc định 5)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (mặc định 42)")
    args = parser.parse_args()

    plot_random_5segments(args.csv_file, num_segments=args.num, seed=args.seed)
