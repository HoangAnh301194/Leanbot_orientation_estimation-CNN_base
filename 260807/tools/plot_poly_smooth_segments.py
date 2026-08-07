"""
plot_poly_smooth_segments.py
──────────────────────────────
Làm mượt quỹ đạo bằng Polynomial Fitting bậc 3 trực tiếp trên (t, x_t, y_t),
không sử dụng Ellipse.

Các bước thực hiện:
1. Chọn ngẫu nhiên đoạn 30 điểm liên tiếp (~2 giây ở 15 FPS).
2. Chuẩn hóa trục thời gian: t = [0, 1, ..., 29] / 30.
3. Fit polynomial bậc 3 độc lập cho (t, x_t) -> f_x(t) và (t, y_t) -> f_y(t).
4. Xuất các đồ thị:
   - x_t và x_t_smooth theo t
   - y_t và y_t_smooth theo t
   - Quỹ đạo 2D (x_t, y_t) và (x_t_smooth, y_t_smooth)
   - Báo cáo công thức / hệ số của f_x(t) và f_y(t).

Ví dụ chạy:
    python tools/plot_poly_smooth_segments.py benchmark
    python tools/plot_poly_smooth_segments.py benchmark --n-segments 3 --poly-degree 3
"""

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

# ─────────────────────────────────────────────────────────────────────────────
# Hằng số mặc định
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_SEGMENT_LENGTH = 30
DEFAULT_N_SEGMENTS = 3
DEFAULT_POLY_DEGREE = 3
DEFAULT_SEED = 42
DEFAULT_DPI = 150
DEFAULT_PADDING_RATIO = 0.12
DEFAULT_MIN_SEGMENT_SPAN = 3.0  # px


# ─────────────────────────────────────────────────────────────────────────────
# Hàm tiện ích đọc dữ liệu
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


def select_random_segments(n_points, segment_length, n_segments, seed=None,
                           x_values=None, y_values=None, frame_ids=None,
                           tracking_lost=None):
    """Chọn các đoạn ngẫu nhiên, không chồng lấn, liên tục và hợp lệ."""
    if segment_length < 4:
        raise ValueError("fit polynomial bậc 3 cần ít nhất 4 điểm mỗi đoạn")
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

        # Kiểm tra chồng lấn
        if any(not (end <= old_start or start >= old_end)
               for old_start, old_end in selected):
            continue

        if x_values is not None and y_values is not None:
            x_seg = np.asarray(x_values[start:end], dtype=float)
            y_seg = np.asarray(y_values[start:end], dtype=float)

            # Lọc điểm NaN / Inf
            if not np.all(np.isfinite(x_seg)) or not np.all(np.isfinite(y_seg)):
                continue

            # Lọc điểm tracking_lost
            if tracking_lost is not None and np.any(
                np.asarray(tracking_lost[start:end], dtype=float) != 0
            ):
                continue

            # Lọc tính liên tục của frame_ids nếu có
            if frame_ids is not None:
                frame_seg = np.asarray(frame_ids[start:end], dtype=float)
                if not np.all(np.isfinite(frame_seg)) or not np.allclose(
                    np.diff(frame_seg), 1.0
                ):
                    continue

            # Kiểm tra độ dịch chuyển tối thiểu
            data_span = max(float(np.ptp(x_seg)), float(np.ptp(y_seg)))
            if data_span < DEFAULT_MIN_SEGMENT_SPAN:
                continue

        selected.append((start, end))
        if len(selected) == n_segments:
            break

    if len(selected) < n_segments:
        raise ValueError(
            f"chỉ tìm được {len(selected)}/{n_segments} đoạn hợp lệ, liên tục, không chồng lấn"
        )

    return sorted(selected)


def format_poly_str(coeffs, var_name='t', func_name='f'):
    """Tạo chuỗi công thức đa thức dạng: f(t) = a3*t^3 + a2*t^2 + a1*t + a0."""
    deg = len(coeffs) - 1
    terms = []
    for i, c in enumerate(coeffs):
        power = deg - i
        if abs(c) < 1e-6:
            continue
        sign = "+" if c >= 0 and len(terms) > 0 else ("-" if c < 0 else "")
        val = abs(c)

        if power > 1:
            term_str = f"{sign} {val:.3f}{var_name}^{power}" if sign else f"{c:.3f}{var_name}^{power}"
        elif power == 1:
            term_str = f"{sign} {val:.3f}{var_name}" if sign else f"{c:.3f}{var_name}"
        else:
            term_str = f"{sign} {val:.3f}" if sign else f"{c:.3f}"

        terms.append(term_str.strip())

    if not terms:
        return f"{func_name}({var_name}) = 0"
    return f"{func_name}({var_name}) = " + " ".join(terms)


# ─────────────────────────────────────────────────────────────────────────────
# Xử lý & Vẽ đồ thị cho một đoạn
# ─────────────────────────────────────────────────────────────────────────────

def plot_segment_poly_smooth(x_raw, y_raw, start, end, poly_degree,
                            csv_name, segment_id, out_dir, dpi=DEFAULT_DPI):
    """Fit polynomial bậc 3 riêng biệt cho x(t) và y(t), xuất đồ thị và báo cáo hệ số."""
    x_seg = x_raw[start:end]
    y_seg = y_raw[start:end]
    n_pts = len(x_seg)

    # 1. Trục thời gian chuẩn hóa: t = [0, 1, ..., N-1] / N
    t_norm = np.arange(n_pts, dtype=float) / float(n_pts)

    # 2. Fit Polynomial bậc 3
    coeffs_x = np.polyfit(t_norm, x_seg, deg=poly_degree)
    coeffs_y = np.polyfit(t_norm, y_seg, deg=poly_degree)

    x_smooth = np.polyval(coeffs_x, t_norm)
    y_smooth = np.polyval(coeffs_y, t_norm)

    # Tạm thời comment phần tính sai số RMS
    # rms_x = np.sqrt(np.mean((x_seg - x_smooth) ** 2))
    # rms_y = np.sqrt(np.mean((y_seg - y_smooth) ** 2))
    # rms_2d = np.sqrt(np.mean((x_seg - x_smooth) ** 2 + (y_seg - y_smooth) ** 2))

    # Công thức đa thức
    str_fx = format_poly_str(coeffs_x, var_name='t', func_name='f_x')
    str_fy = format_poly_str(coeffs_y, var_name='t', func_name='f_y')

    # Console log chi tiết hệ số
    print(f"    - f_x(t) coefficients: {np.round(coeffs_x, 4)}")
    print(f"      {str_fx}")
    print(f"    - f_y(t) coefficients: {np.round(coeffs_y, 4)}")
    print(f"      {str_fy}")
    # print(f"    - RMS error: X={rms_x:.3f} px | Y={rms_y:.3f} px | 2D={rms_2d:.3f} px")

    csv_stem = Path(csv_name).stem
    os.makedirs(out_dir, exist_ok=True)

    # ── Plot 1: x(t) và y(t) theo t ──
    fig1, (ax_x, ax_y) = plt.subplots(2, 1, figsize=(12, 8), dpi=dpi, sharex=True)

    # Plot X(t)
    ax_x.plot(t_norm, x_seg, 'b.-', linewidth=1.2, markersize=5, label='X gốc (raw)', alpha=0.7)
    ax_x.plot(t_norm, x_smooth, 'r-', linewidth=2.5, label=f'X smooth (Poly deg={poly_degree})')
    ax_x.set_ylabel('X Center (pixels)', fontweight='bold')
    ax_x.set_title(
        f"X(t) & Y(t) vs t — {csv_name} — Đoạn #{segment_id} [Index {start}–{end})\n"
        f"{str_fx}",
        fontsize=11, fontweight='bold'
    )
    ax_x.legend(fontsize=9, loc='best')
    ax_x.grid(True, linestyle='--', alpha=0.5)

    # Plot Y(t)
    ax_y.plot(t_norm, y_seg, 'g.-', linewidth=1.2, markersize=5, label='Y gốc (raw)', alpha=0.7)
    ax_y.plot(t_norm, y_smooth, 'r-', linewidth=2.5, label=f'Y smooth (Poly deg={poly_degree})')
    ax_y.set_xlabel('Thời gian chuẩn hóa t (t = [0..29]/30)', fontweight='bold')
    ax_y.set_ylabel('Y Center (pixels)', fontweight='bold')
    ax_y.set_title(
        f"{str_fy}",
        fontsize=11, fontweight='bold'
    )
    ax_y.legend(fontsize=9, loc='best')
    ax_y.grid(True, linestyle='--', alpha=0.5)

    fig1.tight_layout()
    time_series_file = Path(out_dir) / f"{csv_stem}_seg{segment_id}_xy_components.png"
    fig1.savefig(time_series_file, dpi=dpi, bbox_inches='tight', pad_inches=0.15)
    plt.close(fig1)
    print(f"  [SUCCESS] Time-series Plot: {time_series_file}")

    # ── Plot 2: Quỹ đạo 2D comparison ──
    fig2, ax = plt.subplots(figsize=(10, 10), dpi=dpi)

    # Quỹ đạo gốc
    ax.plot(x_seg, y_seg, color='gray', linewidth=1.2, linestyle='--', alpha=0.7,
            zorder=2, label='Raw (gốc)')
    ax.scatter(x_seg, y_seg, color='gray', s=18, alpha=0.6, edgecolors='none', zorder=3)

    # Quỹ đạo smooth
    ax.plot(x_smooth, y_smooth, color='#e74c3c', linewidth=2.5, alpha=0.9,
            zorder=4, label=f'Smooth (Poly deg={poly_degree})')
    ax.scatter(x_smooth, y_smooth, color='#e74c3c', s=25, alpha=0.8,
               edgecolors='none', zorder=5)

    # Start / End
    ax.scatter(x_seg[0], y_seg[0], color='green', marker='o', s=130, zorder=20,
               edgecolors='black', linewidth=1.5, label='Start')
    ax.scatter(x_seg[-1], y_seg[-1], color='blue', marker='X', s=150, zorder=20,
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
        f"2D Trajectory — {csv_name} — Segment #{segment_id}\n"
        f"[Index {start}–{end} | {n_pts} điểm | Poly deg={poly_degree}]",
        fontsize=12, fontweight='bold', pad=12
    )
    ax.legend(loc='best', fontsize=9, framealpha=0.9)
    fig2.tight_layout()

    traj_file = Path(out_dir) / f"{csv_stem}_seg{segment_id}_trajectory.png"
    fig2.savefig(traj_file, dpi=dpi, bbox_inches='tight', pad_inches=0.15)
    plt.close(fig2)
    print(f"  [SUCCESS] 2D Trajectory Plot: {traj_file}")

    return {
        'time_series_file': time_series_file,
        'traj_file': traj_file,
        'coeffs_x': coeffs_x,
        'coeffs_y': coeffs_y,
        'str_fx': str_fx,
        'str_fy': str_fy
    }


# ─────────────────────────────────────────────────────────────────────────────
# main()
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Làm mượt quỹ đạo bằng Polynomial Fitting trực tiếp trên (t, x_t, y_t)"
    )
    parser.add_argument("path", type=str, help="File CSV hoặc thư mục chứa CSV")
    parser.add_argument("--segment-length", type=int, default=DEFAULT_SEGMENT_LENGTH,
                        help=f"Số điểm mỗi đoạn (mặc định: {DEFAULT_SEGMENT_LENGTH})")
    parser.add_argument("--n-segments", type=int, default=DEFAULT_N_SEGMENTS,
                        help=f"Số đoạn ngẫu nhiên mỗi file (mặc định: {DEFAULT_N_SEGMENTS})")
    parser.add_argument("--poly-degree", type=int, default=DEFAULT_POLY_DEGREE,
                        help=f"Bậc polynomial fit cho x(t) và y(t) (mặc định: {DEFAULT_POLY_DEGREE})")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED,
                        help=f"Random seed (mặc định: {DEFAULT_SEED})")
    parser.add_argument("--out-dir", type=str, default=None,
                        help="Thư mục đầu ra (mặc định: benchmark/poly_smooth_segments)")
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
        out_dir = base / 'poly_smooth_segments'

    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] Tìm thấy {len(csv_files)} file CSV")
    print(f"[INFO] Độ dài đoạn: {args.segment_length} điểm (~2s) | Số đoạn: {args.n_segments} | "
          f"Poly degree: {args.poly_degree} | Seed: {args.seed}")
    print(f"[INFO] Đầu ra: {out_dir}\n")

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
            print(f"\n  Đoạn #{seg_idx}: index [{start}–{end})")
            result = plot_segment_poly_smooth(
                x_raw, y_raw, start, end,
                poly_degree=args.poly_degree,
                csv_name=csv_file.name,
                segment_id=seg_idx,
                out_dir=str(out_dir),
                dpi=args.dpi,
            )
            if result:
                total_plots += 2  # 2 đồ thị per segment

        print()

    print(f"[DONE] Hoàn tất! Đã tạo tổng cộng {total_plots} đồ thị tại: {out_dir}")


if __name__ == "__main__":
    main()
