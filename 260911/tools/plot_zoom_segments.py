
import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ─────────────────────────────────────────────────────────────────────────────
# Hằng số mặc định
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_SEGMENT_LENGTH = 150        # 150 điểm ≈ 10 giây × 15 FPS
DEFAULT_N_SEGMENTS = 3              # Số đoạn ngẫu nhiên mỗi file CSV
DEFAULT_ALPHAS = [0.1, 0.3, 0.5]    # Các giá trị alpha mặc định
DEFAULT_SEED = 42                   # Random seed để tái tạo kết quả
DEFAULT_DPI = 150
DEFAULT_PADDING_RATIO = 0.12
DEFAULT_FIGURE_SIZE = (12, 8)

# Ensure UTF-8 output encoding for terminal printing
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# ─────────────────────────────────────────────────────────────────────────────
# Các hàm tiện ích (giữ lại từ plot_oxy_trajectory.py)
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


def apply_bidirectional_ema(data_array, alpha):
    """Làm mượt dữ liệu 1D bằng Bidirectional Exponential Moving Average."""
    series = pd.Series(data_array)
    # Lọc tiến (Forward EMA)
    f_ema = series.ewm(alpha=alpha, adjust=False).mean()
    # Lọc lùi (Backward EMA)
    b_ema = f_ema.iloc[::-1].ewm(alpha=alpha, adjust=False).mean().iloc[::-1]
    return b_ema.to_numpy(dtype=float)


def calculate_zoom_limits(x_values, y_values, padding_ratio=DEFAULT_PADDING_RATIO):
    """Tính viewport vuông theo span lớn nhất, có khoảng đệm quanh toàn bộ geometry."""
    x_min, x_max = float(np.min(x_values)), float(np.max(x_values))
    y_min, y_max = float(np.min(y_values)), float(np.max(y_values))
    span_x = x_max - x_min
    span_y = y_max - y_min
    reference_span = max(span_x, span_y, 10.0)
    padding = max(reference_span * padding_ratio, 1.0)
    half_view_span = reference_span / 2.0 + padding
    center_x = (x_min + x_max) / 2.0
    center_y = (y_min + y_max) / 2.0
    return (
        center_x - half_view_span,
        center_x + half_view_span,
        center_y - half_view_span,
        center_y + half_view_span,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Bước 2: Đọc dữ liệu gốc (raw, chưa làm mượt)
# ─────────────────────────────────────────────────────────────────────────────

def load_raw_trajectory(csv_path: Path):
    """Đọc CSV và trả về mảng x_raw, y_raw (chưa làm mượt)."""
    df = pd.read_csv(csv_path)
    if df.empty:
        raise ValueError("file rỗng")

    x_col, y_col, frame_col = find_columns(df)
    if not x_col or not y_col:
        raise ValueError("không tìm thấy cột x_center/y_center")

    x_values = pd.to_numeric(df[x_col], errors='coerce')
    y_values = pd.to_numeric(df[y_col], errors='coerce')
    valid_mask = x_values.notna() & y_values.notna()

    x_raw = x_values[valid_mask].to_numpy(dtype=float)
    y_raw = y_values[valid_mask].to_numpy(dtype=float)
    if len(x_raw) < 2:
        raise ValueError("không đủ dữ liệu hợp lệ, cần ít nhất 2 điểm")

    return x_raw, y_raw


# ─────────────────────────────────────────────────────────────────────────────
# Bước 3: Chọn ngẫu nhiên các đoạn liên tục
# ─────────────────────────────────────────────────────────────────────────────

def select_random_segments(n_points, segment_length, n_segments, seed=None):
    """Chọn ngẫu nhiên n_segments vị trí bắt đầu sao cho mỗi đoạn dài segment_length điểm.

    Returns:
        list of (start_index, end_index) tuples
    """
    max_start = n_points - segment_length
    if max_start < 0:
        raise ValueError(
            f"Dữ liệu chỉ có {n_points} điểm, không đủ cho đoạn {segment_length} điểm"
        )

    rng = np.random.default_rng(seed)

    # Chọn ngẫu nhiên, không trùng lặp nếu có thể
    n_possible = max_start + 1
    if n_segments <= n_possible:
        starts = rng.choice(n_possible, size=n_segments, replace=False)
    else:
        starts = rng.choice(n_possible, size=n_segments, replace=True)

    starts = sorted(starts)
    return [(int(s), int(s + segment_length)) for s in starts]


# ─────────────────────────────────────────────────────────────────────────────
# Bước 4: Vẽ so sánh quỹ đạo gốc vs đã làm mượt cho một đoạn
# ─────────────────────────────────────────────────────────────────────────────

# Bảng màu cho các đường smooth
SMOOTH_COLORS = ['#e74c3c', '#2ecc71', '#3498db', '#f39c12', '#9b59b6', '#1abc9c']

def plot_segment_comparison(x_raw, y_raw, start, end, alpha_list, csv_name,
                            segment_id, out_dir, dpi=DEFAULT_DPI):
    """Vẽ so sánh quỹ đạo gốc và đã làm mượt cho một đoạn [start, end).

    Quan trọng: Làm mượt trên TOÀN BỘ dữ liệu trước, rồi mới cắt đoạn,
    để tránh boundary effect ở đầu/cuối đoạn.
    """
    # Cắt đoạn raw
    x_seg_raw = x_raw[start:end]
    y_seg_raw = y_raw[start:end]

    fig, ax = plt.subplots(figsize=DEFAULT_FIGURE_SIZE, dpi=dpi)

    # Vẽ quỹ đạo gốc (raw)
    ax.plot(x_seg_raw, y_seg_raw, color='gray', linewidth=1.0, linestyle='--',
            alpha=0.7, zorder=2, label='Raw (gốc)')
    ax.scatter(x_seg_raw, y_seg_raw, color='gray', s=5, alpha=0.4,
               edgecolors='none', zorder=3)

    # Thu thập tất cả x, y để tính zoom limits
    all_x = [x_seg_raw]
    all_y = [y_seg_raw]

    # Vẽ quỹ đạo đã làm mượt cho từng alpha
    for idx, alpha in enumerate(alpha_list):
        # Làm mượt trên TOÀN BỘ dữ liệu trước
        x_smooth_full = apply_bidirectional_ema(x_raw, alpha)
        y_smooth_full = apply_bidirectional_ema(y_raw, alpha)

        # Cắt đoạn từ kết quả đã mượt
        x_seg_smooth = x_smooth_full[start:end]
        y_seg_smooth = y_smooth_full[start:end]

        color = SMOOTH_COLORS[idx % len(SMOOTH_COLORS)]
        ax.plot(x_seg_smooth, y_seg_smooth, color=color, linewidth=1.0,
                alpha=0.85, zorder=4 + idx, label=f'α={alpha}')
        ax.scatter(x_seg_smooth, y_seg_smooth, color=color, s=5,
                   alpha=0.5, edgecolors='none', zorder=5 + idx)

        all_x.append(x_seg_smooth)
        all_y.append(y_seg_smooth)

    # Điểm Start và End (dựa trên raw)
    ax.scatter(x_seg_raw[0], y_seg_raw[0], color='green', marker='o', s=100,
               zorder=20, edgecolors='black', linewidth=1.0, label='Start')
    ax.scatter(x_seg_raw[-1], y_seg_raw[-1], color='red', marker='X', s=100,
               zorder=20, edgecolors='black', linewidth=1.0, label='End')

    # Thiết lập trục
    combined_x = np.concatenate(all_x)
    combined_y = np.concatenate(all_y)
    x_min, x_max, y_min, y_max = calculate_zoom_limits(combined_x, combined_y)
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_max, y_min)  # Image coords: Y hướng xuống
    ax.set_aspect('equal', adjustable='box')

    ax.grid(True, linestyle='--', alpha=0.5)
    ax.set_xlabel('X Center (pixels)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Y Center (pixels)', fontsize=12, fontweight='bold')

    alphas_str = ', '.join([f'{a}' for a in alpha_list])
    ax.set_title(
        f"Zoom Segment #{segment_id} — {csv_name}\n"
        f"[Index {start}–{end} | {end - start} điểm | α = {alphas_str}]",
        fontsize=13, fontweight='bold', pad=12
    )

    ax.legend(loc='best', fontsize=9, framealpha=0.9)
    plt.tight_layout()

    # Lưu ảnh
    os.makedirs(out_dir, exist_ok=True)
    csv_stem = Path(csv_name).stem
    out_file = Path(out_dir) / f"{csv_stem}_segment_{segment_id}.png"
    plt.savefig(out_file, dpi=dpi, bbox_inches='tight', pad_inches=0.15)
    print(f"[SUCCESS] Đã lưu: {out_file}")
    plt.close(fig)
    return out_file


# ─────────────────────────────────────────────────────────────────────────────
# Bước 5: Hàm main() với argparse
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Zoom vào các đoạn ngẫu nhiên để so sánh quỹ đạo gốc vs làm mượt Bidirectional EMA"
    )
    parser.add_argument(
        "path", type=str,
        help="File CSV hoặc thư mục chứa CSV"
    )
    parser.add_argument(
        "--segment-length", type=int, default=DEFAULT_SEGMENT_LENGTH,
        help=f"Số điểm mỗi đoạn (mặc định: {DEFAULT_SEGMENT_LENGTH})"
    )
    parser.add_argument(
        "--n-segments", type=int, default=DEFAULT_N_SEGMENTS,
        help=f"Số đoạn ngẫu nhiên mỗi file CSV (mặc định: {DEFAULT_N_SEGMENTS})"
    )
    parser.add_argument(
        "--alphas", type=str, default=','.join(map(str, DEFAULT_ALPHAS)),
        help="Danh sách alpha phân cách bằng dấu phẩy (mặc định: '0.1,0.3,0.5')"
    )
    parser.add_argument(
        "--seed", type=int, default=DEFAULT_SEED,
        help=f"Random seed để tái tạo kết quả (mặc định: {DEFAULT_SEED})"
    )
    parser.add_argument(
        "--out-dir", type=str, default=None,
        help="Thư mục đầu ra (mặc định: benchmark/zoom_segments)"
    )
    parser.add_argument(
        "--dpi", type=int, default=DEFAULT_DPI,
        help=f"DPI ảnh đầu ra (mặc định: {DEFAULT_DPI})"
    )

    args = parser.parse_args()

    # Parse alphas
    try:
        alpha_list = [float(a.strip()) for a in args.alphas.split(',')]
        for a in alpha_list:
            if not (0 < a <= 1):
                parser.error(f"Mỗi alpha phải nằm trong (0, 1], nhận được: {a}")
    except ValueError:
        parser.error(f"Không thể parse --alphas: '{args.alphas}'")

    # Tìm file CSV
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

    # Thư mục đầu ra
    if args.out_dir:
        out_dir = Path(args.out_dir).expanduser().resolve()
    else:
        base = target_path if target_path.is_dir() else target_path.parent
        out_dir = base / 'zoom_segments'

    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] Tìm thấy {len(csv_files)} file CSV")
    print(f"[INFO] Đoạn: {args.segment_length} điểm | Số đoạn: {args.n_segments} | "
          f"Alpha: {alpha_list} | Seed: {args.seed}")
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
            plot_segment_comparison(
                x_raw, y_raw,
                start, end,
                alpha_list=alpha_list,
                csv_name=csv_file.name,
                segment_id=seg_idx,
                out_dir=str(out_dir),
                dpi=args.dpi,
            )
            total_plots += 1

        print()

    print(f"[DONE] Đã vẽ tổng cộng {total_plots} đồ thị zoom segment.")


if __name__ == "__main__":
    main()
