"""
So sánh ba chuỗi góc trên một đoạn Leanbot chuyển động liên tục:

1. Raw Angle từ model.
2. Góc tiếp tuyến tại endpoint của đa thức cục bộ bậc hai.
3. Góc của vector nối hai điểm làm mượt liên tiếp.

Tool đồng thời vẽ quỹ đạo 2D, so sánh dữ liệu raw với các điểm endpoint
thu được sau khi fit polynomial bằng Least Squares.

Ví dụ:
    python tools/plot_poly_tangent_angle_comparison.py benchmark
    python tools/plot_poly_tangent_angle_comparison.py benchmark/45_degree.csv
    python tools/plot_poly_tangent_angle_comparison.py benchmark --window-size 18 --poly-degree 2
"""

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


DEFAULT_WINDOW_SIZE = 18
DEFAULT_POLY_DEGREE = 2
DEFAULT_SEED = 42
DEFAULT_BUFFER_FRAMES = 10
DEFAULT_MIN_SPEED = 1.5
DEFAULT_MIN_BLOCK_LENGTH = 30
DEFAULT_VECTOR_EPSILON = 1e-5
DEFAULT_DPI = 150

RAW_ANGLE_COLOR = "#8b0000"
POLY_TANGENT_COLOR = "#0055ff"
SMOOTH_POINT_COLOR = "#ff7f00"


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def find_angle_column(dataframe: pd.DataFrame) -> str:
    for column_name in ("raw_angle", "group1_angle", "angle"):
        if column_name in dataframe.columns:
            return column_name
    raise ValueError("Thiếu cột góc raw: raw_angle, group1_angle hoặc angle")


def load_valid_dataframe(csv_path: Path) -> pd.DataFrame:
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

    angle_column = find_angle_column(dataframe)
    numeric_columns = ["x_center", "y_center", angle_column]
    if "frame_id" in dataframe.columns:
        numeric_columns.append("frame_id")

    for column_name in numeric_columns:
        dataframe[column_name] = pd.to_numeric(
            dataframe[column_name], errors="coerce"
        )

    dataframe = dataframe.dropna(subset=["x_center", "y_center", angle_column])
    dataframe = dataframe.reset_index(drop=True)
    if len(dataframe) < 3:
        raise ValueError("không đủ dữ liệu hợp lệ")
    return dataframe


def find_full_pass_moving_segment(
    dataframe: pd.DataFrame,
    buffer_frames: int,
    seed: int,
    min_speed: float,
    min_block_length: int,
) -> pd.DataFrame:
    x_values = dataframe["x_center"].to_numpy(dtype=float)
    y_values = dataframe["y_center"].to_numpy(dtype=float)
    delta_x = np.diff(x_values, prepend=x_values[0])
    delta_y = np.diff(y_values, prepend=y_values[0])
    speed = np.hypot(delta_x, delta_y)
    smooth_speed = (
        pd.Series(speed)
        .rolling(window=11, center=True, min_periods=1)
        .mean()
        .to_numpy(dtype=float)
    )
    moving_mask = smooth_speed > min_speed

    blocks = []
    block_start = None
    for index, is_moving in enumerate(moving_mask):
        if is_moving and block_start is None:
            block_start = index
        elif not is_moving and block_start is not None:
            if index - block_start >= min_block_length:
                blocks.append((block_start, index))
            block_start = None

    if block_start is not None and len(dataframe) - block_start >= min_block_length:
        blocks.append((block_start, len(dataframe)))

    if not blocks:
        start_index = min(buffer_frames, max(0, len(dataframe) - 2))
        end_index = max(start_index + 2, len(dataframe) - buffer_frames)
        return dataframe.iloc[start_index:end_index].copy().reset_index(drop=True)

    random_generator = np.random.RandomState(seed)
    selected_index = int(random_generator.choice(len(blocks)))
    block_start, block_end = blocks[selected_index]
    segment_start = min(block_start + buffer_frames, block_end - 2)
    segment_end = max(block_end - buffer_frames, segment_start + 2)
    return dataframe.iloc[segment_start:segment_end].copy().reset_index(drop=True)


def fit_causal_endpoint_polynomials(
    x_values: np.ndarray,
    y_values: np.ndarray,
    window_size: int,
    poly_degree: int,
):
    sample_count = len(x_values)
    smooth_x = np.full(sample_count, np.nan, dtype=float)
    smooth_y = np.full(sample_count, np.nan, dtype=float)
    tangent_x = np.full(sample_count, np.nan, dtype=float)
    tangent_y = np.full(sample_count, np.nan, dtype=float)

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

        smooth_x[index] = float(np.polyval(coefficients_x, 0.0))
        smooth_y[index] = float(np.polyval(coefficients_y, 0.0))

        if current_degree >= 1:
            tangent_x[index] = float(
                np.polyval(np.polyder(coefficients_x), 0.0)
            )
            tangent_y[index] = float(
                np.polyval(np.polyder(coefficients_y), 0.0)
            )

    return smooth_x, smooth_y, tangent_x, tangent_y


def unwrap_finite_degrees(angle_values: np.ndarray) -> np.ndarray:
    angle_values = np.asarray(angle_values, dtype=float)
    result = np.full(angle_values.shape, np.nan, dtype=float)
    finite_indices = np.flatnonzero(np.isfinite(angle_values))
    if finite_indices.size == 0:
        return result

    groups = np.split(finite_indices, np.where(np.diff(finite_indices) > 1)[0] + 1)
    for group in groups:
        radians = np.radians(angle_values[group])
        result[group] = np.degrees(np.unwrap(radians))
    return result


def align_orientation_phase(
    target_angles: np.ndarray,
    reference_angles: np.ndarray,
    period_degrees: float = 180.0,
) -> np.ndarray:
    aligned = np.asarray(target_angles, dtype=float).copy()
    valid_mask = np.isfinite(aligned) & np.isfinite(reference_angles)
    if not np.any(valid_mask):
        return aligned

    median_difference = np.median(
        reference_angles[valid_mask] - aligned[valid_mask]
    )
    phase_shift = np.round(median_difference / period_degrees) * period_degrees
    aligned += phase_shift
    return aligned


def calculate_angle_series(
    x_values: np.ndarray,
    y_values: np.ndarray,
    raw_angles: np.ndarray,
    window_size: int,
    poly_degree: int,
    vector_epsilon: float,
):
    smooth_x, smooth_y, tangent_x, tangent_y = fit_causal_endpoint_polynomials(
        x_values,
        y_values,
        window_size=window_size,
        poly_degree=poly_degree,
    )

    tangent_angles = np.degrees(np.arctan2(-tangent_y, tangent_x))
    smooth_delta_x = np.diff(smooth_x, prepend=np.nan)
    smooth_delta_y = np.diff(smooth_y, prepend=np.nan)
    smooth_point_angles = np.degrees(
        np.arctan2(-smooth_delta_y, smooth_delta_x)
    )

    tangent_magnitude = np.hypot(tangent_x, tangent_y)
    smooth_point_magnitude = np.hypot(smooth_delta_x, smooth_delta_y)
    valid_start = min(window_size, len(x_values))
    sample_indices = np.arange(len(x_values))

    tangent_angles[
        (sample_indices < valid_start) | (tangent_magnitude <= vector_epsilon)
    ] = np.nan
    smooth_point_angles[
        (sample_indices < valid_start)
        | (smooth_point_magnitude <= vector_epsilon)
    ] = np.nan

    raw_unwrapped = unwrap_finite_degrees(raw_angles)
    tangent_unwrapped = unwrap_finite_degrees(tangent_angles)
    smooth_point_unwrapped = unwrap_finite_degrees(smooth_point_angles)

    tangent_aligned = align_orientation_phase(
        tangent_unwrapped, raw_unwrapped, period_degrees=180.0
    )
    smooth_point_aligned = align_orientation_phase(
        smooth_point_unwrapped, raw_unwrapped, period_degrees=180.0
    )

    return {
        "smooth_x": smooth_x,
        "smooth_y": smooth_y,
        "raw_angle": raw_unwrapped,
        "poly_tangent_angle": tangent_aligned,
        "smooth_point_angle": smooth_point_aligned,
        "valid_start": valid_start,
    }


def set_robust_angle_limits(axis, angle_arrays) -> None:
    finite_arrays = [
        angle_array[np.isfinite(angle_array)]
        for angle_array in angle_arrays
        if np.any(np.isfinite(angle_array))
    ]
    if not finite_arrays:
        return

    all_angles = np.concatenate(finite_arrays)
    lower_bound, upper_bound = np.percentile(all_angles, [1.0, 99.0])
    angle_span = max(upper_bound - lower_bound, 1.0)
    padding = max(5.0, angle_span * 0.12)
    axis.set_ylim(lower_bound - padding, upper_bound + padding)


def print_angle_summary(label: str, angle_values: np.ndarray) -> None:
    finite_values = angle_values[np.isfinite(angle_values)]
    if finite_values.size == 0:
        print(f"    - {label}: không có dữ liệu hợp lệ")
        return
    print(
        f"    - {label}: mean={np.mean(finite_values):.2f}°, "
        f"std={np.std(finite_values):.2f}°"
    )


def save_trajectory_comparison(
    csv_path: Path,
    output_dir: Path,
    x_values: np.ndarray,
    y_values: np.ndarray,
    smooth_x: np.ndarray,
    smooth_y: np.ndarray,
    frame_ids: np.ndarray,
    window_size: int,
    poly_degree: int,
    dpi: int,
) -> Path:
    frame_start = int(frame_ids[0])
    frame_end = int(frame_ids[-1])
    figure, axis = plt.subplots(figsize=(10, 8), dpi=dpi)
    axis.plot(
        x_values,
        y_values,
        color="#d62728",
        linewidth=1.5,
        linestyle="-",
        alpha=0.5,
        label="Raw Trajectory (O)",
        zorder=2,
    )
    axis.scatter(
        x_values,
        y_values,
        color="#8b0000",
        s=15,
        alpha=0.6,
        edgecolors="none",
        zorder=3,
    )
    axis.plot(
        smooth_x,
        smooth_y,
        color=POLY_TANGENT_COLOR,
        linewidth=2.5,
        linestyle="-",
        alpha=0.95,
        label=(
            f"Polynomial Least Squares Degree {poly_degree} "
            f"(Causal W={window_size})"
        ),
        zorder=6,
    )

    axis.invert_yaxis()
    axis.set_title(
        "2D Trajectory: Raw vs Polynomial Least Squares\n"
        f"File: {csv_path.name} | Frames {frame_start}-{frame_end} | "
        f"Causal W={window_size}, Polynomial Degree={poly_degree}",
        fontsize=12,
        fontweight="bold",
    )
    axis.set_xlabel("X Center (pixels)", fontweight="bold")
    axis.set_ylabel("Y Center (pixels)", fontweight="bold")
    axis.grid(True, linestyle=":", alpha=0.6)
    axis.legend(loc="best", fontsize=9)
    figure.tight_layout()

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / (
        f"{csv_path.stem}_poly_least_squares_2d_trajectory.png"
    )
    figure.savefig(
        output_path,
        dpi=dpi,
        bbox_inches="tight",
        pad_inches=0.15,
    )
    plt.close(figure)
    print(f"[SUCCESS] Đã lưu quỹ đạo: {output_path}")
    return output_path

def plot_angle_comparison(
    csv_path: Path,
    output_dir: Path,
    window_size: int,
    poly_degree: int,
    seed: int,
    buffer_frames: int,
    min_speed: float,
    min_block_length: int,
    vector_epsilon: float,
    dpi: int,
) -> tuple[Path, Path]:
    dataframe = load_valid_dataframe(csv_path)
    angle_column = find_angle_column(dataframe)
    segment = find_full_pass_moving_segment(
        dataframe,
        buffer_frames=buffer_frames,
        seed=seed,
        min_speed=min_speed,
        min_block_length=min_block_length,
    )
    if len(segment) <= window_size:
        raise ValueError(
            f"đoạn chuyển động chỉ có {len(segment)} mẫu, cần hơn {window_size} mẫu"
        )

    x_values = segment["x_center"].to_numpy(dtype=float)
    y_values = segment["y_center"].to_numpy(dtype=float)
    raw_angles = segment[angle_column].to_numpy(dtype=float)
    if "frame_id" in segment.columns:
        frame_ids = segment["frame_id"].to_numpy(dtype=float)
    else:
        frame_ids = np.arange(len(segment), dtype=float)

    angle_series = calculate_angle_series(
        x_values,
        y_values,
        raw_angles,
        window_size=window_size,
        poly_degree=poly_degree,
        vector_epsilon=vector_epsilon,
    )
    trajectory_output_path = save_trajectory_comparison(
        csv_path=csv_path,
        output_dir=output_dir,
        x_values=x_values,
        y_values=y_values,
        smooth_x=angle_series["smooth_x"],
        smooth_y=angle_series["smooth_y"],
        frame_ids=frame_ids,
        window_size=window_size,
        poly_degree=poly_degree,
        dpi=dpi,
    )
    valid_start = angle_series["valid_start"]
    plot_frames = frame_ids[valid_start:]
    raw_plot = angle_series["raw_angle"][valid_start:]
    tangent_plot = angle_series["poly_tangent_angle"][valid_start:]
    smooth_point_plot = angle_series["smooth_point_angle"][valid_start:]

    frame_start = int(plot_frames[0])
    frame_end = int(plot_frames[-1])
    figure, axis = plt.subplots(figsize=(12, 7), dpi=dpi)
    axis.plot(
        plot_frames,
        raw_plot,
        color=RAW_ANGLE_COLOR,
        linewidth=2.5,
        linestyle="-",
        alpha=0.85,
        label="Raw Angle (Model)",
        zorder=10,
    )
    axis.plot(
        plot_frames,
        tangent_plot,
        color=POLY_TANGENT_COLOR,
        linewidth=2.4,
        linestyle="-",
        label=f"Polynomial Endpoint Tangent Angle (W={window_size})",
        zorder=7,
    )
    axis.plot(
        plot_frames,
        smooth_point_plot,
        color=SMOOTH_POINT_COLOR,
        linewidth=1.8,
        linestyle="-",
        alpha=0.9,
        label="Two Consecutive Smoothed Points Angle",
        zorder=6,
    )

    axis.set_title(
        "Heading Angle Comparison: Raw Model vs Polynomial Tangent "
        "vs Consecutive Smoothed Points\n"
        f"File: {csv_path.name} | Frames {frame_start}-{frame_end} | "
        f"Causal W={window_size}, Polynomial Degree={poly_degree}",
        fontsize=12,
        fontweight="bold",
    )
    axis.set_xlabel("Frame ID", fontweight="bold")
    axis.set_ylabel("Angle (Degrees)", fontweight="bold")
    axis.grid(True, linestyle="--", alpha=0.6)
    axis.legend(loc="best", fontsize=9)
    set_robust_angle_limits(axis, [raw_plot, tangent_plot, smooth_point_plot])
    figure.tight_layout()

    output_dir.mkdir(parents=True, exist_ok=True)
    angle_output_path = output_dir / f"{csv_path.stem}_poly_tangent_angle_comparison.png"
    figure.savefig(
        angle_output_path,
        dpi=dpi,
        bbox_inches="tight",
        pad_inches=0.15,
    )
    plt.close(figure)

    print(
        f"[INFO] {csv_path.name}: {len(segment)} mẫu, "
        f"Frames {frame_start}-{frame_end}"
    )
    print_angle_summary("Raw Angle", raw_plot)
    print_angle_summary("Polynomial Tangent", tangent_plot)
    print_angle_summary("Two Smoothed Points", smooth_point_plot)
    print(f"[SUCCESS] Đã lưu góc: {angle_output_path}")
    return trajectory_output_path, angle_output_path


def collect_csv_files(input_path: Path):
    if input_path.is_file() and input_path.suffix.lower() == ".csv":
        return [input_path]
    if input_path.is_dir():
        return sorted(input_path.glob("*.csv"))
    raise ValueError(f"đường dẫn không hợp lệ: {input_path}")


def parse_arguments():
    parser = argparse.ArgumentParser(
        description=(
            "So sánh Raw Angle, góc tiếp tuyến đa thức tại endpoint và góc "
            "từ hai điểm làm mượt liên tiếp."
        )
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
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Random seed chọn đoạn chạy, mặc định {DEFAULT_SEED}",
    )
    parser.add_argument(
        "--buffer-frames",
        type=int,
        default=DEFAULT_BUFFER_FRAMES,
        help="Số frame bỏ ở hai đầu đoạn chuyển động",
    )
    parser.add_argument(
        "--min-speed",
        type=float,
        default=DEFAULT_MIN_SPEED,
        help="Ngưỡng tốc độ phát hiện đoạn đang chuyển động",
    )
    parser.add_argument(
        "--min-block-length",
        type=int,
        default=DEFAULT_MIN_BLOCK_LENGTH,
        help="Số mẫu tối thiểu của một đoạn chuyển động",
    )
    parser.add_argument(
        "--vector-epsilon",
        type=float,
        default=DEFAULT_VECTOR_EPSILON,
        help="Ngưỡng loại vector có độ lớn gần zero",
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
        help="Thư mục lưu ảnh; mặc định <input>/poly_tangent_comparison",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    if arguments.window_size < 3:
        print("[ERROR] window-size phải từ 3 trở lên")
        return 1
    if arguments.poly_degree < 1:
        print("[ERROR] poly-degree phải từ 1 trở lên")
        return 1
    if arguments.poly_degree >= arguments.window_size:
        print("[ERROR] poly-degree phải nhỏ hơn window-size")
        return 1

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
        default_output_root / "poly_tangent_comparison"
    )

    print(f"[INFO] Tìm thấy {len(csv_files)} file CSV")
    failure_count = 0
    for csv_path in csv_files:
        try:
            plot_angle_comparison(
                csv_path=csv_path,
                output_dir=output_dir,
                window_size=arguments.window_size,
                poly_degree=arguments.poly_degree,
                seed=arguments.seed,
                buffer_frames=arguments.buffer_frames,
                min_speed=arguments.min_speed,
                min_block_length=arguments.min_block_length,
                vector_epsilon=arguments.vector_epsilon,
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
