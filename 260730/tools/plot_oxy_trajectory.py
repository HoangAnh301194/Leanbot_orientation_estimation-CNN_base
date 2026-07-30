import argparse
import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import cv2

DEFAULT_FRAME_WIDTH = 1920
DEFAULT_FRAME_HEIGHT = 1080
DEFAULT_DPI = 100
DEFAULT_PADDING_RATIO = 0.12
ELLIPSE_AXIS_EXTENSION_RATIO = 0.05
DEFAULT_FIGURE_SIZE = (12, 8)
MARKDOWN_SUFFIXES = {'.md', '.markdown'}

# Ensure UTF-8 output encoding for terminal printing
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def find_columns(df: pd.DataFrame):
    """Tu dong tim cot x_center, y_center va frame_id trong dataframe."""
    x_col, y_col, frame_col = None, None, None
    
    # Tim x_center
    for candidate in ['x_center', 'x', 'roi_center_x', 'center_x', 'X']:
        if candidate in df.columns:
            x_col = candidate
            break
            
    # Tim y_center
    for candidate in ['y_center', 'y', 'roi_center_y', 'center_y', 'Y']:
        if candidate in df.columns:
            y_col = candidate
            break
            
    # Tim frame_id
    for candidate in ['frame_id', 'frame', 'timestamp', 'index']:
        if candidate in df.columns:
            frame_col = candidate
            break
            
    return x_col, y_col, frame_col


def load_trajectory(csv_path: Path):
    """Đọc và lọc các điểm quỹ đạo hợp lệ từ một file CSV."""
    df = pd.read_csv(csv_path)
    if df.empty:
        raise ValueError("file rỗng")

    x_col, y_col, _ = find_columns(df)
    if not x_col or not y_col:
        raise ValueError("không tìm thấy cột x_center/y_center")

    x_values = pd.to_numeric(df[x_col], errors='coerce')
    y_values = pd.to_numeric(df[y_col], errors='coerce')
    valid_mask = x_values.notna() & y_values.notna() & (x_values > 0) & (y_values > 0)

    if 'tracking_lost' in df.columns:
        tracking_lost = pd.to_numeric(df['tracking_lost'], errors='coerce').fillna(1)
        valid_mask &= tracking_lost.eq(0)

    x = x_values[valid_mask].to_numpy(dtype=float)
    y = y_values[valid_mask].to_numpy(dtype=float)
    if len(x) < 2:
        raise ValueError("không đủ dữ liệu hợp lệ, cần ít nhất 2 điểm")

    return x, y


def extract_csv_paths_from_markdown(markdown_path: Path):
    """Lấy toàn bộ liên kết CSV cục bộ được liệt kê trong báo cáo Markdown."""
    content = markdown_path.read_text(encoding='utf-8')
    link_pattern = re.compile(r'\]\(\s*<?([^)>\s]+\.csv)>?(?:\s+["\'][^"\']*["\'])?\s*\)', re.IGNORECASE)
    csv_paths = []
    seen_paths = set()

    for match in link_pattern.finditer(content):
        raw_path = unquote(match.group(1)).split('#', 1)[0].split('?', 1)[0]
        if re.match(r'^[a-z][a-z0-9+.-]*://', raw_path, re.IGNORECASE):
            print(f"[WARN] Bỏ qua liên kết CSV từ xa: {raw_path}")
            continue

        csv_path = (markdown_path.parent / raw_path).resolve()
        normalized_path = os.path.normcase(str(csv_path))
        if normalized_path not in seen_paths:
            seen_paths.add(normalized_path)
            csv_paths.append(csv_path)

    return csv_paths


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


def apply_axis_limits(ax, x_values, y_values, cartesian, full_frame,
                      frame_width, frame_height, padding_ratio):
    """Áp dụng full-frame hoặc auto-zoom, luôn giữ cùng tỉ lệ đơn vị X/Y."""
    if full_frame:
        x_min, x_max = 0, frame_width
        y_min, y_max = 0, frame_height
    else:
        x_min, x_max, y_min, y_max = calculate_zoom_limits(
            x_values,
            y_values,
            padding_ratio=padding_ratio,
        )

    ax.set_xlim(x_min, x_max)
    ax.set_ylim((y_min, y_max) if cartesian else (y_max, y_min))
    ax.set_aspect('equal', adjustable='box')


def concise_path_label(csv_path: Path):
    """Tạo nhãn đủ phân biệt nhưng không quá dài cho chú giải và tên ảnh."""
    runlr_match = re.search(r'runlr_(\d+)_(\d+)', csv_path.stem, re.IGNORECASE)
    if runlr_match:
        return f"LbMotion.runLR({runlr_match.group(1)}, {runlr_match.group(2)})"
    parts = csv_path.with_suffix('').parts[-3:]
    return '/'.join(parts)


def safe_output_stem(csv_path: Path):
    label = concise_path_label(csv_path)
    return re.sub(r'[^0-9A-Za-z._-]+', '__', label).strip('_.')

def fit_ellipse_to_pts(x_pts, y_pts):
    """
    Fit ellipse to 2D points using OpenCV fitEllipse.
    Tra ve (cx, cy), (a, b), angle_deg, (x_ellipse, y_ellipse), residual
    """
    pts = np.column_stack((x_pts, y_pts)).astype(np.float32)
    if len(pts) < 5:
        return None
    
    try:
        (cx, cy), (d1, d2), angle = cv2.fitEllipse(pts)
        a = max(d1, d2) / 2.0  # Semi-major axis
        b = min(d1, d2) / 2.0  # Semi-minor axis
        
        # Orient angle to major axis
        if d2 > d1:
            angle = (angle + 90) % 360
            
        t = np.linspace(0, 2 * np.pi, 360)
        rad = np.radians(angle)
        x_ellipse = cx + a * np.cos(t) * np.cos(rad) - b * np.sin(t) * np.sin(rad)
        y_ellipse = cy + a * np.cos(t) * np.sin(rad) + b * np.sin(t) * np.cos(rad)

        major_direction = np.array([np.cos(rad), np.sin(rad)])
        minor_direction = np.array([-np.sin(rad), np.cos(rad)])
        center = np.array([cx, cy])
        axis_scale = 1.0 + ELLIPSE_AXIS_EXTENSION_RATIO
        major_axis = np.vstack((center - a * axis_scale * major_direction,
                                center + a * axis_scale * major_direction))
        minor_axis = np.vstack((center - b * axis_scale * minor_direction,
                                center + b * axis_scale * minor_direction))
        
        # Calculate residual RMS distance error
        dx = x_pts - cx
        dy = y_pts - cy
        cos_a, sin_a = np.cos(-rad), np.sin(-rad)
        x_rot = dx * cos_a - dy * sin_a
        y_rot = dx * sin_a + dy * cos_a
        dist = np.sqrt((x_rot / a)**2 + (y_rot / b)**2) - 1.0
        rms_error = np.sqrt(np.mean(dist**2))
        
        return {
            'center': (cx, cy),
            'axes': (a, b),
            'angle': angle,
            'eccentricity': np.sqrt(1 - (b / a)**2) if a > 0 else 0,
            'contour': (x_ellipse, y_ellipse),
            'major_axis': major_axis,
            'minor_axis': minor_axis,
            'rms_error': rms_error
        }
    except Exception as e:
        print(f"[WARN] Error fitting ellipse: {e}")
        return None


def ellipse_plot_points(ellipse_info):
    """Trả về toàn bộ điểm ellipse và hai trục để tính giới hạn hiển thị."""
    contour_x, contour_y = ellipse_info['contour']
    major_axis = ellipse_info['major_axis']
    minor_axis = ellipse_info['minor_axis']
    return (
        np.concatenate((contour_x, major_axis[:, 0], minor_axis[:, 0])),
        np.concatenate((contour_y, major_axis[:, 1], minor_axis[:, 1])),
    )


def draw_fitted_ellipse(ax, ellipse_info, contour_color='red', major_color='darkorange',
                        minor_color='purple', alpha=1.0, show_labels=True):
    """Vẽ ellipse fit, tâm, trục lớn và trục nhỏ."""
    contour_x, contour_y = ellipse_info['contour']
    major_axis = ellipse_info['major_axis']
    minor_axis = ellipse_info['minor_axis']
    center_x, center_y = ellipse_info['center']
    semi_major, semi_minor = ellipse_info['axes']

    ax.plot(contour_x, contour_y, '--', color=contour_color, linewidth=2,
            alpha=alpha, zorder=4, label='Ellipse fit' if show_labels else None)
    ax.plot(major_axis[:, 0], major_axis[:, 1], '-', color=major_color,
            linewidth=2.2, alpha=alpha, zorder=5,
            label=f'Major axis: {2 * semi_major:.1f} px' if show_labels else None)
    ax.plot(minor_axis[:, 0], minor_axis[:, 1], '-', color=minor_color,
            linewidth=2.2, alpha=alpha, zorder=5,
            label=f'Minor axis: {2 * semi_minor:.1f} px' if show_labels else None)
    ax.scatter(center_x, center_y, color='black' if show_labels else contour_color,
               marker='+', s=120, linewidth=2, alpha=alpha, zorder=6,
               label='Ellipse center' if show_labels else None)

def plot_single_oxy(csv_path: Path, out_dir: Path = None, fit_ellipse: bool = True,
                    cartesian: bool = False, frame_width: int = DEFAULT_FRAME_WIDTH,
                    frame_height: int = DEFAULT_FRAME_HEIGHT, dpi: int = DEFAULT_DPI,
                    full_frame: bool = False, padding_ratio: float = DEFAULT_PADDING_RATIO,
                    output_name: str = None):
    """Vẽ đồ thị quy đạo Oxy cho 1 file CSV log."""
    if not csv_path.exists():
        print(f"[ERROR] File không tồn tại: {csv_path}")
        return None
        
    try:
        x, y = load_trajectory(csv_path)
    except (OSError, ValueError, pd.errors.ParserError) as error:
        print(f"[ERROR] Không thể đọc quỹ đạo từ {csv_path}: {error}")
        return None
    
    # Tính toán các thông số khoảng cách
    dx = np.diff(x)
    dy = np.diff(y)
    step_distances = np.sqrt(dx**2 + dy**2)
    total_distance = np.sum(step_distances)
    displacement = np.sqrt((x[-1] - x[0])**2 + (y[-1] - y[0])**2)
    
    # Bounds
    x_min, x_max = np.min(x), np.max(x)
    y_min, y_max = np.min(y), np.max(y)
    span_x, span_y = x_max - x_min, y_max - y_min

    fig, ax = plt.subplots(figsize=DEFAULT_FIGURE_SIZE, dpi=dpi)
    
    ax.plot(x, y, color='tab:blue', linewidth=2.0, alpha=0.85, zorder=2, label='Trajectory')
    ax.scatter(x, y, color='tab:blue', s=15, zorder=3, alpha=0.6, edgecolors='none')
    
    # Vẽ điểm Bắt đầu (Start) và Kết thúc (End)
    ax.scatter(x[0], y[0], color='green', marker='o', s=120, zorder=7,
               edgecolors='black', linewidth=1.5, label='Start')
    ax.scatter(x[-1], y[-1], color='red', marker='X', s=140, zorder=7,
               edgecolors='black', linewidth=1.5, label='End')
    
    # Fit Ellipse nếu được bật
    ellipse_info = None
    limit_x = x
    limit_y = y
    if fit_ellipse and len(x) >= 5:
        ellipse_info = fit_ellipse_to_pts(x, y)
        if ellipse_info:
            draw_fitted_ellipse(ax, ellipse_info)
            ellipse_x, ellipse_y = ellipse_plot_points(ellipse_info)
            limit_x = np.concatenate((x, ellipse_x))
            limit_y = np.concatenate((y, ellipse_y))

    # Thiết lập hệ trục Oxy
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.set_xlabel('X Center (pixels)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Y Center (pixels)', fontsize=12, fontweight='bold')
    
    coords_str = (
        "Cartesian Coords (Bottom-Left Origin, Y-Up)"
        if cartesian
        else "Image Coords (Top-Left Origin, Y-Down)"
    )
    view_str = (
        f"Full Frame {frame_width}x{frame_height}"
        if full_frame
        else "Auto Zoom; Equal X/Y Scale"
    )

    ax.set_title(
        f"2D Oxy Trajectory Path — {csv_path.name}\n"
        f"[{coords_str}; {view_str}]",
        fontsize=14,
        fontweight='bold',
        pad=12
    )

    apply_axis_limits(
        ax,
        limit_x,
        limit_y,
        cartesian=cartesian,
        full_frame=full_frame,
        frame_width=frame_width,
        frame_height=frame_height,
        padding_ratio=padding_ratio,
    )
    ax.legend(loc='best', fontsize=9, framealpha=0.9)

    plt.tight_layout()
    
    # Save Image
    if out_dir is None:
        out_dir = csv_path.parent
    else:
        os.makedirs(out_dir, exist_ok=True)
        
    output_stem = output_name or csv_path.stem
    out_file = Path(out_dir) / f"{output_stem}_oxy_trajectory.png"
    plt.savefig(out_file, dpi=dpi, bbox_inches='tight', pad_inches=0.15)
    print(f"[SUCCESS] Đã lưu đồ thị Oxy trajectory: {out_file}")
    plt.close(fig)
    
    return {
        'csv_name': csv_path.name,
        'valid_points': len(x),
        'total_distance': total_distance,
        'displacement': displacement,
        'span_x': span_x,
        'span_y': span_y,
        'frame_size': (frame_width, frame_height),
        'ellipse': ellipse_info,
        'output_path': out_file
    }

def plot_multi_oxy(csv_files: list, out_dir: Path, cartesian: bool = False,
                   fit_ellipse: bool = False, frame_width: int = DEFAULT_FRAME_WIDTH,
                   frame_height: int = DEFAULT_FRAME_HEIGHT, dpi: int = DEFAULT_DPI,
                   full_frame: bool = False, padding_ratio: float = DEFAULT_PADDING_RATIO,
                   display_labels: list = None):
    """Vẽ đè nhiều quỹ đạo di chuyển của nhiều file CSV lên cùng 1 đồ thị Oxy để so sánh."""
    fig, ax = plt.subplots(figsize=(14, 9), dpi=dpi)
    cmap = plt.get_cmap('tab20')
    colors = [cmap(i % 20) for i in range(len(csv_files))]
    
    has_data = False
    all_x = []
    all_y = []
    for idx, csv_path in enumerate(csv_files):
        try:
            x, y = load_trajectory(csv_path)
            
            color = colors[idx]
            label = display_labels[idx] if display_labels else concise_path_label(csv_path)
            ax.plot(x, y, '.-', color=color, linewidth=1.5, alpha=0.75, label=label)
            ax.scatter(x[0], y[0], color=color, marker='o', s=80, edgecolors='black', zorder=4)
            ax.scatter(x[-1], y[-1], color=color, marker='X', s=100, edgecolors='black', zorder=4)
            
            if fit_ellipse and len(x) >= 5:
                e_info = fit_ellipse_to_pts(x, y)
                if e_info:
                    draw_fitted_ellipse(
                        ax,
                        e_info,
                        contour_color=color,
                        major_color=color,
                        minor_color=color,
                        alpha=0.45,
                        show_labels=False,
                    )
                    ellipse_x, ellipse_y = ellipse_plot_points(e_info)
                    all_x.append(ellipse_x)
                    all_y.append(ellipse_y)
                    
            all_x.append(x)
            all_y.append(y)
            has_data = True
        except (OSError, ValueError, pd.errors.ParserError) as error:
            print(f"[WARN] Không thể đọc file {csv_path}: {error}")

    if not has_data:
        print("[ERROR] Không có dữ liệu hợp lệ để vẽ so sánh multi-log.")
        plt.close(fig)
        return

    ax.grid(True, linestyle='--', alpha=0.5)
    ax.set_xlabel('X Center (pixels)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Y Center (pixels)', fontsize=12, fontweight='bold')

    coords_str = (
        "Cartesian Coords (Bottom-Left Origin, Y-Up)"
        if cartesian
        else "Image Coords (Top-Left Origin, Y-Down)"
    )
    view_str = (
        f"Full Frame {frame_width}x{frame_height}"
        if full_frame
        else "Auto Zoom; Equal X/Y Scale"
    )

    ax.set_title(
        f"Multi-Trajectory 2D Oxy Comparison\n"
        f"[{coords_str}; {view_str}]",
        fontsize=14,
        fontweight='bold',
        pad=12
    )
    apply_axis_limits(
        ax,
        np.concatenate(all_x),
        np.concatenate(all_y),
        cartesian=cartesian,
        full_frame=full_frame,
        frame_width=frame_width,
        frame_height=frame_height,
        padding_ratio=padding_ratio,
    )
    ax.legend(loc='center left', bbox_to_anchor=(1.02, 0.5), fontsize=8, framealpha=0.9)
    fig.tight_layout(rect=(0, 0, 0.78, 1))

    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "combined_multi_oxy_trajectory.png"
    plt.savefig(out_file, dpi=dpi, bbox_inches='tight', pad_inches=0.15)
    print(f"[SUCCESS] Đã lưu đồ thị so sánh multi-log: {out_file}")
    plt.close(fig)

def main():
    default_report = Path(__file__).resolve().parents[1] / 'Readme.md'
    parser = argparse.ArgumentParser(
        description="Vẽ quỹ đạo Oxy từ một CSV, thư mục CSV hoặc các liên kết CSV trong Readme.md"
    )
    parser.add_argument(
        "path",
        type=str,
        nargs='?',
        default=str(default_report),
        help="File CSV, thư mục CSV hoặc báo cáo Markdown (mặc định: Readme.md của ngày 260727)",
    )
    parser.add_argument(
        "--out-dir",
        type=str,
        default=None,
        help="Thư mục ảnh đầu ra; Markdown mặc định dùng thư mục trajectory_plots cạnh báo cáo",
    )
    parser.add_argument("--no-ellipse", action="store_true", help="Tắt tính năng fit hình ellipse")
    parser.add_argument("--cartesian", action="store_true", help="Dùng trục Cartesian Y hướng lên thay cho trục ảnh Y hướng xuống")
    parser.add_argument("--multi", action="store_true", help="Vẽ thêm ảnh tổng hợp khi đầu vào chứa nhiều CSV")
    parser.add_argument("--recursive", action="store_true", help="Tìm CSV trong toàn bộ thư mục con khi đầu vào là thư mục")
    parser.add_argument("--full-frame", action="store_true", help="Dùng giới hạn full-frame cũ thay cho auto-zoom")
    parser.add_argument("--padding", type=float, default=DEFAULT_PADDING_RATIO, help="Khoảng đệm auto-zoom theo span lớn nhất, mặc định 0.12")
    parser.add_argument("--frame-width", type=int, default=DEFAULT_FRAME_WIDTH, help="Chiều rộng frame khi dùng --full-frame")
    parser.add_argument("--frame-height", type=int, default=DEFAULT_FRAME_HEIGHT, help="Chiều cao frame khi dùng --full-frame")
    parser.add_argument("--dpi", type=int, default=DEFAULT_DPI, help="DPI ảnh đầu ra, mặc định 100")

    args = parser.parse_args()
    if args.padding < 0:
        parser.error("--padding phải lớn hơn hoặc bằng 0")
    if args.dpi <= 0 or args.frame_width <= 0 or args.frame_height <= 0:
        parser.error("--dpi, --frame-width và --frame-height phải lớn hơn 0")

    target_path = Path(args.path).expanduser().resolve()
    is_markdown = target_path.is_file() and target_path.suffix.lower() in MARKDOWN_SUFFIXES

    if target_path.is_file() and target_path.suffix.lower() == '.csv':
        csv_files = [target_path]
    elif is_markdown:
        linked_csv_files = extract_csv_paths_from_markdown(target_path)
        missing_files = [csv_path for csv_path in linked_csv_files if not csv_path.is_file()]
        for missing_file in missing_files:
            print(f"[WARN] CSV trong báo cáo không tồn tại: {missing_file}")
        csv_files = [csv_path for csv_path in linked_csv_files if csv_path.is_file()]
    elif target_path.is_dir():
        csv_iterator = target_path.rglob('*.csv') if args.recursive else target_path.glob('*.csv')
        csv_files = sorted(csv_iterator)
    else:
        print("[ERROR] Đường dẫn phải là file .csv, file .md/.markdown hoặc thư mục chứa CSV")
        return

    if not csv_files:
        print(f"[ERROR] Không tìm thấy file CSV hợp lệ từ: {target_path}")
        return

    if args.out_dir:
        out_dir = Path(args.out_dir).expanduser().resolve()
    elif is_markdown:
        out_dir = target_path.parent / 'trajectory_plots'
    else:
        out_dir = target_path.parent if target_path.is_file() else target_path

    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[INFO] Tìm thấy {len(csv_files)} file CSV; đầu ra: {out_dir}")

    use_path_in_name = is_markdown or len({csv_path.name for csv_path in csv_files}) < len(csv_files)
    plotted_files = []
    for csv_file in csv_files:
        result = plot_single_oxy(
            csv_file,
            out_dir=out_dir,
            fit_ellipse=not args.no_ellipse,
            cartesian=args.cartesian,
            frame_width=args.frame_width,
            frame_height=args.frame_height,
            dpi=args.dpi,
            full_frame=args.full_frame,
            padding_ratio=args.padding,
            output_name=safe_output_stem(csv_file) if use_path_in_name else None,
        )
        if result:
            plotted_files.append(csv_file)

    if len(csv_files) > 1 and (args.multi or is_markdown or target_path.is_dir()):
        plot_multi_oxy(
            csv_files,
            out_dir=out_dir,
            cartesian=args.cartesian,
            fit_ellipse=not args.no_ellipse,
            frame_width=args.frame_width,
            frame_height=args.frame_height,
            dpi=args.dpi,
            full_frame=args.full_frame,
            padding_ratio=args.padding,
            display_labels=[concise_path_label(csv_file) for csv_file in csv_files],
        )

    print(f"[DONE] Đã vẽ {len(plotted_files)}/{len(csv_files)} quỹ đạo riêng.")

if __name__ == "__main__":
    main()
