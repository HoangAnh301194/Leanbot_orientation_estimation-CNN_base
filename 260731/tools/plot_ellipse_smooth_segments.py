"""
plot_ellipse_smooth_segments.py
───────────────────────────────
Chọn ngẫu nhiên các đoạn ngắn (mặc định 45 điểm ≈ 3 giây × 15 FPS),
fit ellipse trên mỗi đoạn, tính phase angle, fit polynomial bậc 2 để
làm mượt phase angle, rồi chiếu ngược lên ellipse để có quỹ đạo smooth.

Mỗi đoạn sinh ra 2 đồ thị:
  1. Phase angle gốc vs smooth phase angle
  2. Quỹ đạo gốc vs quỹ đạo smooth (trên ellipse)

Ví dụ chạy:
    python tools/plot_ellipse_smooth_segments.py benchmark
    python tools/plot_ellipse_smooth_segments.py benchmark --n-segments 5 --poly-degree 3
"""

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Thêm thư mục tools vào path để import từ plot_oxy_trajectory
sys.path.insert(0, str(Path(__file__).resolve().parent))
from plot_oxy_trajectory import fit_ellipse_to_pts, calculate_ellipse_phase_angles

# ─────────────────────────────────────────────────────────────────────────────
# Hằng số mặc định
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_SEGMENT_LENGTH = 45
DEFAULT_N_SEGMENTS = 3
DEFAULT_POLY_DEGREE = 2
DEFAULT_SEED = 42
DEFAULT_DPI = 150
DEFAULT_PADDING_RATIO = 0.12

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# ─────────────────────────────────────────────────────────────────────────────
# Hàm tiện ích
# ─────────────────────────────────────────────────────────────────────────────

def find_columns(df: pd.DataFrame):
    """Tự động tìm cột x_center, y_center và frame_id trong dataframe."""
    x_col, y_col, frame_col = None, None, None
    for candidate in ['x_center', 'x', 'roi_center_x', 'center_x', 'X']:
        if candidate in df.columns:
            x_col = candidate
            break
    for candidate in ['y_center', 'y', 'roi_center_y', 'center_y', 'Y']:
        if candidate in df.columns:
            y_col = candidate
            break
    for candidate in ['frame_id', 'frame', 'timestamp', 'index']:
        if candidate in df.columns:
            frame_col = candidate
            break
    return x_col, y_col, frame_col


def load_raw_trajectory(csv_path: Path):
    """Đọc CSV và trả về mảng x_raw, y_raw (chưa làm mượt)."""
    df = pd.read_csv(csv_path)
    if df.empty:
        raise ValueError("file rỗng")
    x_col, y_col, _ = find_columns(df)
    if not x_col or not y_col:
        raise ValueError("không tìm thấy cột x_center/y_center")
    x_values = pd.to_numeric(df[x_col], errors='coerce')
    y_values = pd.to_numeric(df[y_col], errors='coerce')
    valid_mask = x_values.notna() & y_values.notna()
    x_raw = x_values[valid_mask].to_numpy(dtype=float)
    y_raw = y_values[valid_mask].to_numpy(dtype=float)
    if len(x_raw) < 2:
        raise ValueError("không đủ dữ liệu hợp lệ")
    return x_raw, y_raw


def select_random_segments(n_points, segment_length, n_segments, seed=None):
    """Chọn ngẫu nhiên n_segments vị trí bắt đầu."""
    max_start = n_points - segment_length
    if max_start < 0:
        raise ValueError(
            f"Dữ liệu chỉ có {n_points} điểm, không đủ cho đoạn {segment_length} điểm"
        )
    rng = np.random.default_rng(seed)
    n_possible = max_start + 1
    if n_segments <= n_possible:
        starts = rng.choice(n_possible, size=n_segments, replace=False)
    else:
        starts = rng.choice(n_possible, size=n_segments, replace=True)
    starts = sorted(starts)
    return [(int(s), int(s + segment_length)) for s in starts]


# ─────────────────────────────────────────────────────────────────────────────
# Bước 4: Chiếu phase angle ngược lại lên ellipse
# ─────────────────────────────────────────────────────────────────────────────

def phase_angle_to_xy(phase_angles_deg, ellipse_info):
    """Chiếu các phase angle (wrapped, 0-360) ngược lại lên ellipse để tính tọa độ (x, y).

    Phase angle ở đây là góc đã được trừ đi góc trục lớn trong hệ Cartesian
    (do calculate_ellipse_phase_angles trả về). Ta cần cộng lại góc trục lớn
    rồi tính tọa độ parametric trên ellipse.
    """
    cx, cy = ellipse_info['center']
    a, b = ellipse_info['axes']
    ellipse_angle_deg = float(ellipse_info['angle'])

    # Tính reference_angle_cartesian giống hệt calculate_ellipse_phase_angles
    reference_angle_image = ellipse_angle_deg
    if np.cos(np.radians(reference_angle_image)) < 0:
        reference_angle_image = (reference_angle_image + 180.0) % 360.0
    reference_angle_cartesian = -reference_angle_image

    # Góc thực trong hệ Cartesian (cộng lại reference)
    real_angles_deg = phase_angles_deg + reference_angle_cartesian
    real_angles_rad = np.radians(real_angles_deg)

    # Chuyển từ radial angle sang parametric angle trên ellipse
    # Radial: arctan2(y, x), Parametric: x = a*cos(t), y = b*sin(t)
    # Quan hệ: tan(radial) = (b*sin(t)) / (a*cos(t))
    # => t = arctan2(a * sin(radial), b * cos(radial))
    t = np.arctan2(a * np.sin(real_angles_rad), b * np.cos(real_angles_rad))

    # Tọa độ trên ellipse (hệ local, chưa xoay)
    x_local = a * np.cos(t)
    y_local = b * np.sin(t)

    # Xoay theo góc ellipse (hệ ảnh: Y hướng xuống)
    ellipse_rad = np.radians(ellipse_angle_deg)
    cos_e = np.cos(ellipse_rad)
    sin_e = np.sin(ellipse_rad)

    # OpenCV fitEllipse trả về angle trong hệ ảnh (Y xuống)
    x_smooth = cx + x_local * cos_e - y_local * sin_e
    # Vì hệ Cartesian: y_cartesian = b*sin(t), nhưng ảnh: y_image = cy - y_cartesian
    # => y_smooth = cy + x_local * sin_e + y_local * cos_e (hệ ảnh)
    y_smooth = cy + x_local * sin_e + y_local * cos_e

    return x_smooth, y_smooth


# ─────────────────────────────────────────────────────────────────────────────
# Bước 5: Vẽ 2 đồ thị cho mỗi đoạn
# ─────────────────────────────────────────────────────────────────────────────

def plot_segment_ellipse_smooth(x_raw, y_raw, start, end, poly_degree,
                                 csv_name, segment_id, out_dir, dpi=DEFAULT_DPI):
    """Fit ellipse trên đoạn, smooth phase angle bằng polynomial, vẽ 2 plots."""
    x_seg = x_raw[start:end]
    y_seg = y_raw[start:end]
    n_pts = len(x_seg)

    # 1. Fit ellipse trên đoạn này
    ellipse_info = fit_ellipse_to_pts(x_seg, y_seg)
    if ellipse_info is None:
        print(f"  [WARN] Không thể fit ellipse cho đoạn #{segment_id} (cần >= 5 điểm)")
        return None

    # 2. Tính phase angle gốc
    wrapped_angles, continuous_angles = calculate_ellipse_phase_angles(
        x_seg, y_seg, ellipse_info
    )

    # 3. Fit polynomial bậc 2 lên continuous phase angles
    indices = np.arange(n_pts)
    coeffs = np.polyfit(indices, continuous_angles, deg=poly_degree)
    smooth_continuous = np.polyval(coeffs, indices)

    # 4. Chuyển smooth continuous angles về wrapped (0-360) để chiếu lên ellipse
    smooth_wrapped = np.mod(smooth_continuous, 360.0)

    # ── Plot 1: Phase Angle comparison ──
    csv_stem = Path(csv_name).stem
    fig1, (ax_top, ax_bot) = plt.subplots(2, 1, figsize=(12, 7), dpi=dpi)

    ax_top.plot(indices, continuous_angles, 'b.-', linewidth=1.2, markersize=4,
                label='Phase angle gốc (continuous)', alpha=0.7)
    ax_top.plot(indices, smooth_continuous, 'r-', linewidth=2.5,
                label=f'Polynomial bậc {poly_degree} fit')
    ax_top.set_ylabel('Continuous angle (°)', fontweight='bold')
    ax_top.set_title(f'Continuous Phase Angle — Segment #{segment_id}')
    ax_top.legend(fontsize=9)
    ax_top.grid(True, linestyle='--', alpha=0.5)

    ax_bot.plot(indices, wrapped_angles, 'b.-', linewidth=1.2, markersize=4,
                label='Phase angle gốc (wrapped 0-360°)', alpha=0.7)
    ax_bot.plot(indices, smooth_wrapped, 'r.-', linewidth=1.5, markersize=5,
                label=f'Smooth phase angle (wrapped)', alpha=0.85)
    ax_bot.set_xlabel('Index điểm', fontweight='bold')
    ax_bot.set_ylabel('Wrapped angle (°)', fontweight='bold')
    ax_bot.set_title('Wrapped Phase Angle (0–360°)')
    ax_bot.legend(fontsize=9)
    ax_bot.grid(True, linestyle='--', alpha=0.5)

    fig1.suptitle(
        f"Phase Angle — {csv_name}\n[Index {start}–{end} | {n_pts} điểm | poly deg={poly_degree}]",
        fontsize=13, fontweight='bold'
    )
    fig1.tight_layout()

    os.makedirs(out_dir, exist_ok=True)
    phase_file = Path(out_dir) / f"{csv_stem}_seg{segment_id}_phase_angle.png"
    fig1.savefig(phase_file, dpi=dpi, bbox_inches='tight', pad_inches=0.15)
    print(f"  [SUCCESS] Phase angle: {phase_file}")
    plt.close(fig1)

    # 5. Chiếu smooth phase angle lên ellipse
    x_smooth, y_smooth = phase_angle_to_xy(smooth_wrapped, ellipse_info)

    # ── Plot 2: Quỹ đạo comparison ──
    fig2, ax = plt.subplots(figsize=(10, 10), dpi=dpi)

    # Vẽ ellipse fit
    ex, ey = ellipse_info['contour']
    ax.plot(ex, ey, '--', color='gray', linewidth=1.5, alpha=0.5, label='Ellipse fit')

    # Quỹ đạo gốc
    ax.plot(x_seg, y_seg, color='gray', linewidth=1.0, linestyle='--', alpha=0.7,
            zorder=2, label='Raw (gốc)')
    ax.scatter(x_seg, y_seg, color='gray', s=15, alpha=0.5, edgecolors='none', zorder=3)

    # Quỹ đạo smooth
    ax.plot(x_smooth, y_smooth, color='#e74c3c', linewidth=2.0, alpha=0.9,
            zorder=4, label='Smooth (ellipse)')
    ax.scatter(x_smooth, y_smooth, color='#e74c3c', s=20, alpha=0.7,
               edgecolors='none', zorder=5)

    # Start / End
    ax.scatter(x_seg[0], y_seg[0], color='green', marker='o', s=120, zorder=20,
               edgecolors='black', linewidth=1.5, label='Start')
    ax.scatter(x_seg[-1], y_seg[-1], color='blue', marker='X', s=140, zorder=20,
               edgecolors='black', linewidth=1.5, label='End')

    # Auto-zoom
    all_x = np.concatenate([x_seg, x_smooth, ex])
    all_y = np.concatenate([y_seg, y_smooth, ey])
    x_min, x_max = float(np.min(all_x)), float(np.max(all_x))
    y_min, y_max = float(np.min(all_y)), float(np.max(all_y))
    span = max(x_max - x_min, y_max - y_min, 10.0)
    padding = max(span * DEFAULT_PADDING_RATIO, 1.0)
    half = span / 2.0 + padding
    cx_view = (x_min + x_max) / 2.0
    cy_view = (y_min + y_max) / 2.0
    ax.set_xlim(cx_view - half, cx_view + half)
    ax.set_ylim(cy_view + half, cy_view - half)  # Y hướng xuống (image coords)
    ax.set_aspect('equal', adjustable='box')

    ax.grid(True, linestyle='--', alpha=0.5)
    ax.set_xlabel('X Center (pixels)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Y Center (pixels)', fontsize=12, fontweight='bold')
    ax.set_title(
        f"Trajectory — {csv_name} — Segment #{segment_id}\n"
        f"[Index {start}–{end} | {n_pts} điểm | Ellipse + Poly deg={poly_degree}]",
        fontsize=13, fontweight='bold', pad=12
    )
    ax.legend(loc='best', fontsize=9, framealpha=0.9)
    fig2.tight_layout()

    traj_file = Path(out_dir) / f"{csv_stem}_seg{segment_id}_trajectory.png"
    fig2.savefig(traj_file, dpi=dpi, bbox_inches='tight', pad_inches=0.15)
    print(f"  [SUCCESS] Trajectory:  {traj_file}")
    plt.close(fig2)

    return {'phase_file': phase_file, 'traj_file': traj_file}


# ─────────────────────────────────────────────────────────────────────────────
# Bước 6: main()
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Làm mượt quỹ đạo bằng Ellipse Fitting + Phase Angle Polynomial Regression"
    )
    parser.add_argument("path", type=str, help="File CSV hoặc thư mục chứa CSV")
    parser.add_argument("--segment-length", type=int, default=DEFAULT_SEGMENT_LENGTH,
                        help=f"Số điểm mỗi đoạn (mặc định: {DEFAULT_SEGMENT_LENGTH})")
    parser.add_argument("--n-segments", type=int, default=DEFAULT_N_SEGMENTS,
                        help=f"Số đoạn ngẫu nhiên mỗi file (mặc định: {DEFAULT_N_SEGMENTS})")
    parser.add_argument("--poly-degree", type=int, default=DEFAULT_POLY_DEGREE,
                        help=f"Bậc polynomial fit (mặc định: {DEFAULT_POLY_DEGREE})")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED,
                        help=f"Random seed (mặc định: {DEFAULT_SEED})")
    parser.add_argument("--out-dir", type=str, default=None,
                        help="Thư mục đầu ra (mặc định: benchmark/ellipse_smooth_segments)")
    parser.add_argument("--dpi", type=int, default=DEFAULT_DPI,
                        help=f"DPI ảnh đầu ra (mặc định: {DEFAULT_DPI})")

    args = parser.parse_args()

    target_path = Path(args.path).expanduser().resolve()
    if target_path.is_file() and target_path.suffix.lower() == '.csv':
        csv_files = [target_path]
    elif target_path.is_dir():
        csv_files = sorted(target_path.glob('*.csv'))
    else:
        print(f"[ERROR] Đường dẫn phải là file .csv hoặc thư mục: {target_path}")
        return

    if not csv_files:
        print(f"[ERROR] Không tìm thấy file CSV trong: {target_path}")
        return

    if args.out_dir:
        out_dir = Path(args.out_dir).expanduser().resolve()
    else:
        base = target_path if target_path.is_dir() else target_path.parent
        out_dir = base / 'ellipse_smooth_segments'

    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] Tìm thấy {len(csv_files)} file CSV")
    print(f"[INFO] Đoạn: {args.segment_length} điểm | Số đoạn: {args.n_segments} | "
          f"Poly degree: {args.poly_degree} | Seed: {args.seed}")
    print(f"[INFO] Đầu ra: {out_dir}")
    print()

    total_plots = 0
    for csv_file in csv_files:
        print(f"── {csv_file.name} ──")
        try:
            x_raw, y_raw = load_raw_trajectory(csv_file)
        except (OSError, ValueError, pd.errors.ParserError) as e:
            print(f"  [ERROR] Không thể đọc: {e}")
            continue

        print(f"  Tổng số điểm: {len(x_raw)}")

        try:
            segments = select_random_segments(
                len(x_raw), args.segment_length, args.n_segments, seed=args.seed
            )
        except ValueError as e:
            print(f"  [ERROR] {e}")
            continue

        for seg_idx, (start, end) in enumerate(segments, 1):
            print(f"  Đoạn #{seg_idx}: index [{start}–{end})")
            result = plot_segment_ellipse_smooth(
                x_raw, y_raw, start, end,
                poly_degree=args.poly_degree,
                csv_name=csv_file.name,
                segment_id=seg_idx,
                out_dir=str(out_dir),
                dpi=args.dpi,
            )
            if result:
                total_plots += 2  # 2 plots per segment

        print()

    print(f"[DONE] Đã vẽ tổng cộng {total_plots} đồ thị.")


if __name__ == "__main__":
    main()
