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
    python tools/plot_ellipse_smooth_segments.py benchmark --n-segments 5 --poly-degree 2
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
DEFAULT_MAX_ELLIPSE_RMS_ERROR = 0.35
DEFAULT_MAX_ELLIPSE_SPAN_RATIO = 5.0
DEFAULT_MAX_ELLIPSE_AXIS_RATIO = 20.0
DEFAULT_MIN_SEGMENT_SPAN = 5.0
# Đoạn dữ liệu phải bao phủ ít nhất MIN_ARC_COVERAGE_DEG độ trên ellipse
# để fit đủ constrained (tránh under-determined khi dữ liệu chỉ là một đường thẳng/cung quá hẹp)
DEFAULT_MIN_ARC_COVERAGE_DEG = 60.0

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


def load_trajectory_rows(csv_path: Path):
    """Đọc toàn bộ hàng CSV, giữ nguyên thứ tự để kiểm tra tính liên tục."""
    df = pd.read_csv(csv_path)
    if df.empty:
        raise ValueError("file rỗng")
    x_col, y_col, frame_col = find_columns(df)
    if not x_col or not y_col:
        raise ValueError("không tìm thấy cột x_center/y_center")

    x_raw = pd.to_numeric(df[x_col], errors='coerce').to_numpy(dtype=float)
    y_raw = pd.to_numeric(df[y_col], errors='coerce').to_numpy(dtype=float)
    if np.count_nonzero(np.isfinite(x_raw) & np.isfinite(y_raw)) < 2:
        raise ValueError("không đủ dữ liệu hợp lệ")

    frame_ids = None
    if frame_col in {'frame_id', 'frame', 'index'}:
        frame_ids = pd.to_numeric(df[frame_col], errors='coerce').to_numpy(dtype=float)

    if 'tracking_lost' in df.columns:
        tracking_lost = pd.to_numeric(
            df['tracking_lost'], errors='coerce'
        ).fillna(1).to_numpy(dtype=float)
    else:
        tracking_lost = np.zeros(len(df), dtype=float)

    return x_raw, y_raw, frame_ids, tracking_lost


def load_raw_trajectory(csv_path: Path):
    """Đọc CSV và trả về các điểm hợp lệ, giữ tương thích với API cũ."""
    x_raw, y_raw, _, _ = load_trajectory_rows(csv_path)
    valid_mask = np.isfinite(x_raw) & np.isfinite(y_raw)
    return x_raw[valid_mask], y_raw[valid_mask]


def compute_arc_coverage_deg(x_seg, y_seg, ellipse_info):
    """Tính tổng cung góc tham số (°) mà các điểm trong đoạn bao phủ trên ellipse.

    Dùng để loại bỏ các đoạn mà 45 điểm chỉ nằm trên một cung rất nhỏ —
    khi đó ellipse fit under-constrained và cho kết quả không tin cậy.
    """
    cx, cy = ellipse_info['center']
    semi_major, semi_minor = ellipse_info['axes']
    ellipse_angle = np.radians(float(ellipse_info['angle']))

    dx = np.asarray(x_seg, dtype=float) - cx
    dy = np.asarray(y_seg, dtype=float) - cy
    cos_e = np.cos(ellipse_angle)
    sin_e = np.sin(ellipse_angle)
    x_local = dx * cos_e + dy * sin_e
    y_local = -dx * sin_e + dy * cos_e

    # Phase tham số từng điểm trên ellipse (CCW)
    phase = np.arctan2(-y_local / semi_minor, x_local / semi_major)
    phase_unwrapped = np.unwrap(phase)
    arc_deg = float(np.abs(phase_unwrapped[-1] - phase_unwrapped[0])) * 180.0 / np.pi
    return arc_deg


def validate_ellipse_fit(x_seg, y_seg, ellipse_info):
    """Loại ellipse suy biến hoặc không được ràng buộc đủ bởi đoạn dữ liệu."""
    if ellipse_info is None:
        return False, "OpenCV không fit được ellipse"

    cx, cy = ellipse_info['center']
    semi_major, semi_minor = ellipse_info['axes']
    rms_error = float(ellipse_info['rms_error'])
    values = np.array([cx, cy, semi_major, semi_minor, rms_error], dtype=float)
    if not np.all(np.isfinite(values)) or semi_minor <= 0:
        return False, "tham số ellipse không hợp lệ"

    data_span = max(float(np.ptp(x_seg)), float(np.ptp(y_seg)))
    if data_span < DEFAULT_MIN_SEGMENT_SPAN:
        return False, f"đoạn di chuyển quá ngắn ({data_span:.2f}px)"
    if semi_major / data_span > DEFAULT_MAX_ELLIPSE_SPAN_RATIO:
        return False, "bán trục ellipse quá lớn so với đoạn dữ liệu"
    if semi_major / semi_minor > DEFAULT_MAX_ELLIPSE_AXIS_RATIO:
        return False, "ellipse quá dẹt"
    if rms_error > DEFAULT_MAX_ELLIPSE_RMS_ERROR:
        return False, f"ellipse RMS quá lớn ({rms_error:.3f})"

    # Kiểm tra arc coverage: loại đoạn mà 45 điểm chỉ bao phủ cung quá hẹp
    arc_deg = compute_arc_coverage_deg(x_seg, y_seg, ellipse_info)
    if arc_deg < DEFAULT_MIN_ARC_COVERAGE_DEG:
        return False, f"cung quá hẹp ({arc_deg:.1f}° < {DEFAULT_MIN_ARC_COVERAGE_DEG}°)"

    return True, None


def select_random_segments(n_points, segment_length, n_segments, seed=None,
                           x_values=None, y_values=None, frame_ids=None,
                           tracking_lost=None):
    """Chọn các đoạn ngẫu nhiên, không chồng lấn, liên tục và fit ellipse tốt."""
    if segment_length < 5:
        raise ValueError("fit ellipse cần ít nhất 5 điểm mỗi đoạn")
    if n_segments < 1:
        raise ValueError("số đoạn phải lớn hơn 0")

    max_start = n_points - segment_length
    if max_start < 0:
        raise ValueError(
            f"Dữ liệu chỉ có {n_points} điểm, không đủ cho đoạn {segment_length} điểm"
        )

    rng = np.random.default_rng(seed)
    candidate_starts = rng.permutation(max_start + 1)
    selected = []

    for candidate in candidate_starts:
        start = int(candidate)
        end = start + segment_length
        if any(not (end <= old_start or start >= old_end)
               for old_start, old_end in selected):
            continue

        if x_values is not None and y_values is not None:
            x_seg = np.asarray(x_values[start:end], dtype=float)
            y_seg = np.asarray(y_values[start:end], dtype=float)
            if not np.all(np.isfinite(x_seg)) or not np.all(np.isfinite(y_seg)):
                continue
            if tracking_lost is not None and np.any(
                np.asarray(tracking_lost[start:end], dtype=float) != 0
            ):
                continue
            if frame_ids is not None:
                frame_seg = np.asarray(frame_ids[start:end], dtype=float)
                if not np.all(np.isfinite(frame_seg)) or not np.allclose(
                    np.diff(frame_seg), 1.0
                ):
                    continue

            ellipse_info = fit_ellipse_to_pts(x_seg, y_seg)
            ellipse_valid, _ = validate_ellipse_fit(x_seg, y_seg, ellipse_info)
            if not ellipse_valid:
                continue

        selected.append((start, end))
        if len(selected) == n_segments:
            break

    if len(selected) < n_segments:
        raise ValueError(
            f"chỉ tìm được {len(selected)}/{n_segments} đoạn hợp lệ, liên tục, không chồng lấn"
        )

    return sorted(selected)


# ─────────────────────────────────────────────────────────────────────────────
# Bước 4: Chiếu phase angle ngược lại lên ellipse
# ─────────────────────────────────────────────────────────────────────────────

def phase_angle_to_xy(phase_angles_deg, ellipse_info):
    """Chiếu phase tham số CCW ngược lên ellipse trong hệ tọa độ ảnh."""
    cx, cy = ellipse_info['center']
    a, b = ellipse_info['axes']
    ellipse_angle_deg = float(ellipse_info['angle'])
    phase_radians = np.radians(np.asarray(phase_angles_deg, dtype=float))

    # Tọa độ trên ellipse (hệ local, chưa xoay)
    x_local = a * np.cos(phase_radians)
    y_local = -b * np.sin(phase_radians)

    # Xoay theo góc ellipse (hệ ảnh: Y hướng xuống)
    ellipse_rad = np.radians(ellipse_angle_deg)
    cos_e = np.cos(ellipse_rad)
    sin_e = np.sin(ellipse_rad)

    x_smooth = cx + x_local * cos_e - y_local * sin_e
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
    ellipse_valid, invalid_reason = validate_ellipse_fit(x_seg, y_seg, ellipse_info)
    if not ellipse_valid:
        print(f"  [WARN] Bỏ đoạn #{segment_id}: {invalid_reason}")
        return None

    # 2. Tính phase angle gốc
    _, continuous_angles = calculate_ellipse_phase_angles(
        x_seg, y_seg, ellipse_info
    )

    # 3. Fit polynomial bậc 2 lên continuous phase angles (t_norm in [-1.0, 0.0])
    t_norm = np.linspace(-1.0, 0.0, n_pts)
    coeffs = np.polyfit(t_norm, continuous_angles, deg=poly_degree)
    smooth_continuous = np.polyval(coeffs, t_norm)

    # ── Plot 1: Continuous Phase Angle comparison ──
    csv_stem = Path(csv_name).stem
    fig1, ax_phase = plt.subplots(figsize=(12, 5), dpi=dpi)

    ax_phase.plot(indices, continuous_angles, 'b.-', linewidth=1.2, markersize=4,
                  label='Phase angle gốc (continuous)', alpha=0.7)
    ax_phase.plot(indices, smooth_continuous, 'r-', linewidth=2.5,
                  label=f'Smooth phase — Polynomial bậc {poly_degree}')
    ax_phase.set_xlabel('Index điểm', fontweight='bold')
    ax_phase.set_ylabel('Continuous angle (°)', fontweight='bold')
    ax_phase.set_title(
        f"Continuous Phase Angle — {csv_name}\n"
        f"[Index {start}–{end} | {n_pts} điểm | poly deg={poly_degree}]",
        fontsize=13, fontweight='bold'
    )
    ax_phase.legend(fontsize=9)
    ax_phase.grid(True, linestyle='--', alpha=0.5)
    fig1.tight_layout()

    os.makedirs(out_dir, exist_ok=True)
    phase_file = Path(out_dir) / f"{csv_stem}_seg{segment_id}_phase_angle.png"
    fig1.savefig(phase_file, dpi=dpi, bbox_inches='tight', pad_inches=0.15)
    print(f"  [SUCCESS] Phase angle: {phase_file}")
    plt.close(fig1)

    # 5. Chiếu smooth phase angle liên tục lên ellipse
    x_smooth, y_smooth = phase_angle_to_xy(smooth_continuous, ellipse_info)

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
    all_x = np.concatenate([x_seg, x_smooth])
    all_y = np.concatenate([y_seg, y_smooth])
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
    parser.add_argument("--poly-degree", type=int, choices=[DEFAULT_POLY_DEGREE],
                        default=DEFAULT_POLY_DEGREE,
                        help=f"Bậc polynomial fit theo yêu cầu: {DEFAULT_POLY_DEGREE}")
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
            x_raw, y_raw, frame_ids, tracking_lost = load_trajectory_rows(csv_file)
        except (OSError, ValueError, pd.errors.ParserError) as e:
            print(f"  [ERROR] Không thể đọc: {e}")
            continue

        print(f"  Tổng số điểm: {len(x_raw)}")

        try:
            segments = select_random_segments(
                len(x_raw), args.segment_length, args.n_segments, seed=args.seed,
                x_values=x_raw, y_values=y_raw, frame_ids=frame_ids,
                tracking_lost=tracking_lost,
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
