import argparse
import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import cv2

DEFAULT_FRAME_WIDTH = 1920
DEFAULT_FRAME_HEIGHT = 1080
DEFAULT_DPI = 100

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
            'rms_error': rms_error
        }
    except Exception as e:
        print(f"[WARN] Error fitting ellipse: {e}")
        return None

def plot_single_oxy(csv_path: Path, out_dir: Path = None, fit_ellipse: bool = True,
                    cartesian: bool = False, frame_width: int = DEFAULT_FRAME_WIDTH,
                    frame_height: int = DEFAULT_FRAME_HEIGHT, dpi: int = DEFAULT_DPI):
    """Vẽ đồ thị quy đạo Oxy cho 1 file CSV log."""
    if not csv_path.exists():
        print(f"[ERROR] File không tồn tại: {csv_path}")
        return None
        
    df = pd.read_csv(csv_path)
    if df.empty:
        print(f"[ERROR] File rỗng: {csv_path}")
        return None
        
    x_col, y_col, _ = find_columns(df)
    if not x_col or not y_col:
        print(f"[ERROR] Không tìm thấy cột x_center/y_center trong {csv_path.name}")
        return None
        
    # Lọc các frame hợp lệ (x > 0, y > 0 và không bị tracking lost nếu có cột tracking_lost)
    valid_mask = (~df[x_col].isna()) & (~df[y_col].isna())
        
    df_valid = df[valid_mask].copy()
    if len(df_valid) < 2:
        print(f"[WARN] Không đủ dữ liệu hợp lệ (cần ít nhất 2 điểm) trong {csv_path.name}")
        return None
        
    x = df_valid[x_col].values
    y = df_valid[y_col].values
    
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

    # Canvas và hệ trục dùng đúng kích thước frame camera.
    fig, ax = plt.subplots(figsize=(frame_width / dpi, frame_height / dpi), dpi=dpi)
    
    ax.plot(x, y, color='tab:blue', linewidth=2.0, alpha=0.85, zorder=2)
    ax.scatter(x, y, color='tab:blue', s=15, zorder=3, alpha=0.6, edgecolors='none')
    
    # Vẽ điểm Bắt đầu (Start) và Kết thúc (End)
    ax.scatter(x[0], y[0], color='green', marker='o', s=120, zorder=5, edgecolors='black', linewidth=1.5)
    ax.scatter(x[-1], y[-1], color='red', marker='X', s=140, zorder=5, edgecolors='black', linewidth=1.5)
    
    # Fit Ellipse nếu được bật
    ellipse_info = None
    if fit_ellipse and len(x) >= 5:
        ellipse_info = fit_ellipse_to_pts(x, y)
        if ellipse_info:
            ex, ey = ellipse_info['contour']
            ax.plot(ex, ey, 'r--', linewidth=2, zorder=4)

    # Thiết lập hệ trục Oxy
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.set_xlabel('X Center (pixels)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Y Center (pixels)', fontsize=12, fontweight='bold')
    
    # Coordinate system mode
    if not cartesian:
        # Standard camera/image coords: (0,0) at top-left, Y pointing DOWN
        ax.invert_yaxis()
        coords_str = "Image Coords (Top-Left Origin, Y-Down)"
    else:
        coords_str = "Cartesian Coords (Bottom-Left Origin, Y-Up)"

    ax.set_title(
        f"2D Oxy Trajectory Path — {csv_path.name}\n"
        f"[{coords_str}; Full Frame {frame_width}x{frame_height}]",
        fontsize=14,
        fontweight='bold',
        pad=12
    )

    ax.set_xlim(0, frame_width)
    if not cartesian:
        ax.set_ylim(frame_height, 0)
    else:
        ax.set_ylim(0, frame_height)
        
    ax.set_aspect('equal', adjustable='box')

    plt.tight_layout()
    
    # Save Image
    if out_dir is None:
        out_dir = csv_path.parent
    else:
        os.makedirs(out_dir, exist_ok=True)
        
    out_file = Path(out_dir) / f"{csv_path.stem}_oxy_trajectory.png"
    plt.savefig(out_file, dpi=dpi)
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
                   frame_height: int = DEFAULT_FRAME_HEIGHT, dpi: int = DEFAULT_DPI):
    """Vẽ đè nhiều quỹ đạo di chuyển của nhiều file CSV lên cùng 1 đồ thị Oxy để so sánh."""
    fig, ax = plt.subplots(figsize=(frame_width / dpi, frame_height / dpi), dpi=dpi)
    cmap = plt.get_cmap('tab10')
    colors = [cmap(i % 10) for i in range(len(csv_files))]
    
    has_data = False
    for idx, csv_path in enumerate(csv_files):
        try:
            df = pd.read_csv(csv_path)
            x_col, y_col, _ = find_columns(df)
            if not x_col or not y_col:
                continue
                
            valid_mask = (df[x_col] > 0) & (df[y_col] > 0) & (~df[x_col].isna()) & (~df[y_col].isna())
            if 'tracking_lost' in df.columns:
                valid_mask = valid_mask & (df['tracking_lost'] == 0)
                
            df_valid = df[valid_mask]
            if len(df_valid) < 2:
                continue
                
            x = df_valid[x_col].values
            y = df_valid[y_col].values
            
            color = colors[idx]
            ax.plot(x, y, '.-', color=color, linewidth=1.5, alpha=0.75)
            ax.scatter(x[0], y[0], color=color, marker='o', s=80, edgecolors='black', zorder=4)
            ax.scatter(x[-1], y[-1], color=color, marker='X', s=100, edgecolors='black', zorder=4)
            
            if fit_ellipse and len(x) >= 5:
                e_info = fit_ellipse_to_pts(x, y)
                if e_info:
                    ex, ey = e_info['contour']
                    ax.plot(ex, ey, '--', color=color, alpha=0.5, linewidth=1.2)
                    
            has_data = True
        except Exception as e:
            print(f"[WARN] Khong the doc file {csv_path.name}: {e}")

    if not has_data:
        print("[ERROR] Không có dữ liệu hợp lệ để vẽ so sánh multi-log.")
        plt.close(fig)
        return

    ax.grid(True, linestyle='--', alpha=0.5)
    ax.set_xlabel('X Center (pixels)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Y Center (pixels)', fontsize=12, fontweight='bold')
    
    if not cartesian:
        ax.invert_yaxis()
        coords_str = "Image Coords (Top-Left Origin, Y-Down)"
    else:
        coords_str = "Cartesian Coords (Bottom-Left Origin, Y-Up)"

    ax.set_title(
        f"Multi-Trajectory 2D Oxy Comparison\n"
        f"[{coords_str}; Full Frame {frame_width}x{frame_height}]",
        fontsize=14,
        fontweight='bold',
        pad=12
    )
    ax.set_xlim(0, frame_width)
    if not cartesian:
        ax.set_ylim(frame_height, 0)
    else:
        ax.set_ylim(0, frame_height)
    ax.set_aspect('equal', adjustable='box')
    plt.tight_layout()

    out_file = out_dir / "combined_multi_oxy_trajectory.png"
    plt.savefig(out_file, dpi=dpi)
    print(f"[SUCCESS] Đã lưu đồ thị so sánh multi-log: {out_file}")
    plt.close(fig)

def main():
    parser = argparse.ArgumentParser(description="Tool vẽ đồ thị path di chuyển trong không gian Oxy từ file CSV log")
    parser.add_argument("path", type=str, help="Đường dẫn tới file CSV log hoặc thư mục chứa các file CSV log")
    parser.add_argument("--out-dir", type=str, default=None, help="Thư mục đầu ra lưu ảnh đồ thị (Mặc định: cùng thư mục với CSV)")
    parser.add_argument("--no-ellipse", action="store_true", help="Tắt tính năng fit hình Elipse")
    parser.add_argument("--cartesian", action="store_true", help="Sử dụng trục Oxy Cartesian chuẩn (Y hướng lên) thay vì trục ảnh (Y hướng xuống)")
    parser.add_argument("--multi", action="store_true", help="Khi input là thư mục, vẽ đè tất cả quỹ đạo CSV lên cùng 1 đồ thị")
    parser.add_argument("--frame-width", type=int, default=DEFAULT_FRAME_WIDTH, help="Chiều rộng frame/canvas theo pixel (mặc định 1920)")
    parser.add_argument("--frame-height", type=int, default=DEFAULT_FRAME_HEIGHT, help="Chiều cao frame/canvas theo pixel (mặc định 1080)")
    parser.add_argument("--dpi", type=int, default=DEFAULT_DPI, help="DPI ảnh đầu ra; canvas mặc định vẫn là 1920x1080 pixel")

    args = parser.parse_args()
    target_path = Path(args.path)

    if target_path.is_file() and target_path.suffix.lower() == '.csv':
        out_dir = Path(args.out_dir) if args.out_dir else target_path.parent
        plot_single_oxy(
            target_path, 
            out_dir=out_dir, 
            fit_ellipse=not args.no_ellipse,
            cartesian=args.cartesian,
            frame_width=args.frame_width,
            frame_height=args.frame_height,
            dpi=args.dpi
        )
    elif target_path.is_dir():
        csv_files = sorted(list(target_path.glob("*.csv")))
        if not csv_files:
            print(f"[ERROR] Không tìm thấy file .csv nào trong thư mục: {target_path}")
            return
            
        print(f"[INFO] Tìm thấy {len(csv_files)} file CSV trong thư mục {target_path}")
        out_dir = Path(args.out_dir) if args.out_dir else target_path
        
        for csv_file in csv_files:
            plot_single_oxy(
                csv_file,
                out_dir=out_dir,
                fit_ellipse=not args.no_ellipse,
                cartesian=args.cartesian,
                frame_width=args.frame_width,
                frame_height=args.frame_height,
                dpi=args.dpi
            )
            
        if args.multi or len(csv_files) > 1:
            plot_multi_oxy(
                csv_files,
                out_dir=out_dir,
                cartesian=args.cartesian,
                fit_ellipse=not args.no_ellipse,
                frame_width=args.frame_width,
                frame_height=args.frame_height,
                dpi=args.dpi
            )
    else:
        print("[ERROR] Đường dẫn không hợp lệ. Vui lòng truyền file .csv hoặc thư mục chứa file .csv")

if __name__ == "__main__":
    main()
