"""
Ước lượng vận tốc (Estimated Speed) từ vector đạo hàm endpoint (dx, dy):
v_est = sqrt(dx^2 + dy^2)

Chạy trên toàn bộ dữ liệu file CSV (gồm đủ 6 lượt di chuyển tiến - lùi)
để quan sát sự biến thiên vận tốc và kiểm chứng hiện tượng giảm tốc về 0 khi dừng lại đổi hướng.

Ví dụ:
    python tools/plot_estimated_speed.py benchmark
    python tools/plot_estimated_speed.py benchmark/45_degree.csv
    python tools/plot_estimated_speed.py benchmark --window-size 18 --poly-degree 2
"""

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


DEFAULT_WINDOW_SIZE = 18
DEFAULT_POLY_DEGREE = 2
DEFAULT_DPI = 150
SPEED_LINE_COLOR = "#0055ff"
STOP_THRESHOLD = 2.0


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def load_full_dataframe(csv_path: Path) -> pd.DataFrame:
    dataframe = pd.read_csv(csv_path)
    if dataframe.empty:
        raise ValueError("file CSV rỗng")

    required_columns = {"x_center", "y_center"}
    missing_columns = required_columns.difference(dataframe.columns)
    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))
        raise ValueError(f"thiếu cột bắt buộc: {missing_text}")

    if "frame_id" in dataframe.columns:
        dataframe = dataframe.sort_values("frame_id").reset_index(drop=True)

    if "tracking_lost" in dataframe.columns:
        tracking_lost = pd.to_numeric(
            dataframe["tracking_lost"], errors="coerce"
        ).fillna(1)
        dataframe = dataframe[tracking_lost == 0].copy()

    numeric_columns = ["x_center", "y_center"]
    if "frame_id" in dataframe.columns:
        numeric_columns.append("frame_id")

    for column_name in numeric_columns:
        dataframe[column_name] = pd.to_numeric(
            dataframe[column_name], errors="coerce"
        )

    dataframe = dataframe.dropna(subset=["x_center", "y_center"])
    dataframe = dataframe.reset_index(drop=True)
    if len(dataframe) < 10:
        raise ValueError("không đủ dữ liệu hợp lệ")
    return dataframe


def calculate_estimated_speed(
    x_values: np.ndarray,
    y_values: np.ndarray,
    window_size: int,
    poly_degree: int,
):
    sample_count = len(x_values)
    speed_values = np.full(sample_count, np.nan, dtype=float)
    dx_values = np.full(sample_count, np.nan, dtype=float)
    dy_values = np.full(sample_count, np.nan, dtype=float)

    for index in range(sample_count):
        window_start = max(0, index - window_size + 1)
        window_end = index + 1
        x_window = x_values[window_start:window_end]
        y_window = y_values[window_start:window_end]
        window_length = len(x_window)
        current_degree = min(poly_degree, window_length - 1)
        time_normalized = np.linspace(-1.0, 0.0, window_length)

        coefficients_x = np.polyfit(
            time_normalized, x_window, deg=current_degree
        )
        coefficients_y = np.polyfit(
            time_normalized, y_window, deg=current_degree
        )

        if current_degree >= 1:
            dx = float(np.polyval(np.polyder(coefficients_x), 0.0))
            dy = float(np.polyval(np.polyder(coefficients_y), 0.0))
            dx_values[index] = dx
            dy_values[index] = dy
            speed_values[index] = np.hypot(dx, dy)

    valid_start = min(window_size, sample_count)
    speed_values[:valid_start] = np.nan
    dx_values[:valid_start] = np.nan
    dy_values[:valid_start] = np.nan

    return {
        "speed": speed_values,
        "dx": dx_values,
        "dy": dy_values,
        "valid_start": valid_start,
    }


def plot_single_csv_speed(
    csv_path: Path,
    output_dir: Path,
    window_size: int,
    poly_degree: int,
    dpi: int,
) -> Path:
    dataframe = load_full_dataframe(csv_path)
    x_values = dataframe["x_center"].to_numpy(dtype=float)
    y_values = dataframe["y_center"].to_numpy(dtype=float)
    if "frame_id" in dataframe.columns:
        frame_ids = dataframe["frame_id"].to_numpy(dtype=float)
    else:
        frame_ids = np.arange(len(dataframe), dtype=float)

    result = calculate_estimated_speed(
        x_values=x_values,
        y_values=y_values,
        window_size=window_size,
        poly_degree=poly_degree,
    )

    valid_start = result["valid_start"]
    plot_frames = frame_ids[valid_start:]
    plot_speed = result["speed"][valid_start:]

    figure, axis = plt.subplots(figsize=(14, 6), dpi=dpi)

    axis.plot(
        plot_frames,
        plot_speed,
        color=SPEED_LINE_COLOR,
        linewidth=2.0,
        linestyle="-",
        label=r"Estimated Speed $v = \sqrt{dx^2 + dy^2}$" + f" (Causal W={window_size})",
        zorder=5,
    )

    frame_start = int(plot_frames[0])
    frame_end = int(plot_frames[-1])
    axis.set_title(
        f"Estimated Speed Across Full Trajectory (6 Passes)\n"
        f"File: {csv_path.name} | Frames {frame_start}-{frame_end} | "
        f"Causal W={window_size}, Polynomial Degree={poly_degree}",
        fontsize=12,
        fontweight="bold",
    )
    axis.set_xlabel("Frame ID (Full Run)", fontweight="bold")
    axis.set_ylabel("Estimated Speed (pixels / normalized unit time)", fontweight="bold")
    axis.set_ylim(bottom=0)
    axis.grid(True, linestyle="-", alpha=0.3)
    axis.legend(loc="upper right", fontsize=9)
    figure.tight_layout()

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{csv_path.stem}_estimated_speed_full.png"
    figure.savefig(output_path, dpi=dpi, bbox_inches="tight", pad_inches=0.15)
    plt.close(figure)

    finite_speed = plot_speed[np.isfinite(plot_speed)]
    mean_speed = np.mean(finite_speed) if finite_speed.size > 0 else 0.0
    max_speed = np.max(finite_speed) if finite_speed.size > 0 else 0.0
    min_speed = np.min(finite_speed) if finite_speed.size > 0 else 0.0
    print(
        f"[INFO] {csv_path.name}: {len(dataframe)} frames, "
        f"Speed: min={min_speed:.2f}, mean={mean_speed:.2f}, max={max_speed:.2f}"
    )
    print(f"[SUCCESS] Đã lưu đồ thị Estimated Speed: {output_path}")
    return output_path


def collect_csv_files(input_path: Path):
    if input_path.is_file() and input_path.suffix.lower() == ".csv":
        return [input_path]
    if input_path.is_dir():
        return sorted(input_path.glob("*.csv"))
    raise ValueError(f"đường dẫn không hợp lệ: {input_path}")


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Vẽ Estimated Speed = sqrt(dx^2 + dy^2) trên toàn bộ chu trình 6 lần chạy."
    )
    parser.add_argument(
        "input_path",
        type=Path,
        help="File CSV hoặc thư mục chứa các file CSV",
    )
    parser.add_argument(
        "--window-size",
        type=int,
        default=DEFAULT_WINDOW_SIZE,
        help=f"Kích thước cửa sổ causal, mặc định {DEFAULT_WINDOW_SIZE}",
    )
    parser.add_argument(
        "--poly-degree",
        type=int,
        default=DEFAULT_POLY_DEGREE,
        help=f"Bậc đa thức, mặc định {DEFAULT_POLY_DEGREE}",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=DEFAULT_DPI,
        help=f"Độ phân giải ảnh, mặc định {DEFAULT_DPI}",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Thư mục lưu ảnh; mặc định <input>/estimated_speed",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    try:
        csv_files = collect_csv_files(arguments.input_path)
    except ValueError as error:
        print(f"[ERROR] {error}")
        return 1

    if not csv_files:
        print(f"[ERROR] Không tìm thấy file CSV trong {arguments.input_path}")
        return 1

    default_output_root = (
        arguments.input_path
        if arguments.input_path.is_dir()
        else arguments.input_path.parent
    )
    output_dir = arguments.output_dir or (
        default_output_root / "estimated_speed"
    )

    print(f"[INFO] Tìm thấy {len(csv_files)} file CSV")
    failure_count = 0
    for csv_path in csv_files:
        try:
            plot_single_csv_speed(
                csv_path=csv_path,
                output_dir=output_dir,
                window_size=arguments.window_size,
                poly_degree=arguments.poly_degree,
                dpi=arguments.dpi,
            )
        except (OSError, ValueError, KeyError) as error:
            failure_count += 1
            print(f"[ERROR] {csv_path.name}: {error}")

    if failure_count:
        print(f"[WARNING] Có {failure_count}/{len(csv_files)} file xử lý thất bại")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
