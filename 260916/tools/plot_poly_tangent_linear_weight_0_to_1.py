"""
plot_poly_tangent_linear_weight_0_to_1.py
────────────────────────────────────────
Thực nghiệm Linear Weight [0, 1] cho Polynomial Least Squares (Smooth 1).

Pipeline:
1. Đọc CSV benchmark.
2. Dùng selector từ baseline: find_full_pass_moving_segment(...)
3. Cắt buffer (mặc định 10 frame) ở hai đầu đoạn chuyển động.
4. Trượt causal sliding window W (mặc định 18), bậc đa thức degree (mặc định 2).
5. Tính:
   - Raw Angle từ Model (màu đỏ đậm #8b0000, nét liền)
   - Uniform Weight (Baseline 1:1, màu xanh dương #0055ff, nét liền)
   - Linear Weight [0, 1] (màu xanh lá #2ca02c, alpha tăng tuyến tính 0 -> 1, nét liền)
6. Xuất:
   - Biểu đồ quỹ đạo 2D so sánh
   - Biểu đồ góc so sánh (Toàn bộ nét liền)

Lệnh chạy:
    python tools/plot_poly_tangent_linear_weight_0_to_1.py benchmark/30_degree.csv
    python tools/plot_poly_tangent_linear_weight_0_to_1.py benchmark --window-size 18 --poly-degree 2
"""

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

try:
    import plot_poly_tangent_angle_comparison as baseline
except ImportError:
    from tools import plot_poly_tangent_angle_comparison as baseline


DEFAULT_WINDOW_SIZE = 18
DEFAULT_POLY_DEGREE = 2
DEFAULT_BUFFER_FRAMES = 10
DEFAULT_SEED = 42
DEFAULT_MIN_SPEED = 1.5
DEFAULT_MIN_BLOCK_LENGTH = 30
DEFAULT_VECTOR_EPSILON = 1e-5
DEFAULT_DPI = 150

RAW_ANGLE_COLOR = "#8b0000"       # Đỏ đậm (Raw Model)
UNIFORM_COLOR = "#0055ff"         # Xanh dương đậm (Uniform Baseline 1:1)
LINEAR_01_COLOR = "#2ca02c"       # Xanh lá đậm (Linear Weight [0, 1])


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def polyfit_weights_0_to_1(window_length: int) -> np.ndarray:
    """
    Tạo trọng số importance alpha tăng tuyến tính từ 0 đến 1:
        oldest = 0.0
        newest = 1.0
    Thêm epsilon nhỏ để tránh suy biến khi số mẫu nhỏ.
    """
    if window_length < 1:
        raise ValueError("window_length phải >= 1")
    if window_length == 1:
        return np.ones(1, dtype=float)
    alpha = np.linspace(0.0, 1.0, window_length, dtype=float)
    # Epsilon nhỏ 1e-6 để ổn định số học trong SVD
    return np.sqrt(np.clip(alpha, 1e-6, 1.0))


def weighted_poly_smooth_xy_0_to_1(
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
        fit_w = polyfit_weights_0_to_1(window_length)

        coefficients_x = np.polyfit(
            time_normalized, x_window, deg=current_degree, w=fit_w
        )
        coefficients_y = np.polyfit(
            time_normalized, y_window, deg=current_degree, w=fit_w
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


def calculate_uniform_tangent(
    x_values: np.ndarray,
    y_values: np.ndarray,
    raw_unwrapped: np.ndarray,
    window_size: int,
    poly_degree: int,
    vector_epsilon: float,
):
    smooth_x, smooth_y, tangent_x, tangent_y = baseline.fit_causal_endpoint_polynomials(
        x_values=x_values,
        y_values=y_values,
        window_size=window_size,
        poly_degree=poly_degree,
    )
    tangent_angles = np.degrees(np.arctan2(-tangent_y, tangent_x))
    tangent_magnitude = np.hypot(tangent_x, tangent_y)

    valid_start = min(window_size, len(x_values))
    sample_indices = np.arange(len(x_values))
    tangent_angles[
        (sample_indices < valid_start) | (tangent_magnitude <= vector_epsilon)
    ] = np.nan

    tangent_unwrapped = baseline.unwrap_finite_degrees(tangent_angles)
    tangent_aligned = baseline.align_orientation_phase(
        tangent_unwrapped, raw_unwrapped, period_degrees=180.0
    )
    return {
        "smooth_x": smooth_x,
        "smooth_y": smooth_y,
        "tangent_angle": tangent_aligned,
    }


def calculate_linear_01_tangent(
    x_values: np.ndarray,
    y_values: np.ndarray,
    raw_unwrapped: np.ndarray,
    window_size: int,
    poly_degree: int,
    vector_epsilon: float,
):
    smooth_x, smooth_y, tangent_x, tangent_y = weighted_poly_smooth_xy_0_to_1(
        x_values=x_values,
        y_values=y_values,
        window_size=window_size,
        poly_degree=poly_degree,
    )
    tangent_angles = np.degrees(np.arctan2(-tangent_y, tangent_x))
    tangent_magnitude = np.hypot(tangent_x, tangent_y)

    valid_start = min(window_size, len(x_values))
    sample_indices = np.arange(len(x_values))
    tangent_angles[
        (sample_indices < valid_start) | (tangent_magnitude <= vector_epsilon)
    ] = np.nan

    tangent_unwrapped = baseline.unwrap_finite_degrees(tangent_angles)
    tangent_aligned = baseline.align_orientation_phase(
        tangent_unwrapped, raw_unwrapped, period_degrees=180.0
    )
    return {
        "smooth_x": smooth_x,
        "smooth_y": smooth_y,
        "tangent_angle": tangent_aligned,
    }


def save_angle_plot_01(
    csv_path: Path,
    output_dir: Path,
    plot_frames: np.ndarray,
    raw_plot: np.ndarray,
    uniform_plot: np.ndarray,
    linear_01_plot: np.ndarray,
    window_size: int,
    poly_degree: int,
    dpi: int,
) -> Path:
    frame_start = int(plot_frames[0])
    frame_end = int(plot_frames[-1])

    figure, axis = plt.subplots(figsize=(12, 7), dpi=dpi)

    # 1. Raw Angle (Model)
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

    # 2. Uniform Weight 1:1
    axis.plot(
        plot_frames,
        uniform_plot,
        color=UNIFORM_COLOR,
        linewidth=2.4,
        linestyle="-",
        label=f"Uniform Weight 1:1 (W={window_size})",
        zorder=9,
    )

    # 3. Linear Weight [0, 1]
    axis.plot(
        plot_frames,
        linear_01_plot,
        color=LINEAR_01_COLOR,
        linewidth=2.3,
        linestyle="-",
        label=f"Linear Weight [0, 1] (W={window_size})",
        zorder=8,
    )

    axis.set_title(
        "Heading Angle Comparison: Uniform Weight vs Linear Weight [0, 1]\n"
        f"File: {csv_path.name} | Frames {frame_start}-{frame_end} | "
        f"Causal W={window_size}, Polynomial Degree={poly_degree}",
        fontsize=12,
        fontweight="bold",
    )
    axis.set_xlabel("Frame ID", fontweight="bold")
    axis.set_ylabel("Angle (Degrees)", fontweight="bold")
    axis.grid(True, linestyle="--", alpha=0.6)
    axis.legend(loc="best", fontsize=9)

    baseline.set_robust_angle_limits(
        axis, [raw_plot, uniform_plot, linear_01_plot]
    )
    figure.tight_layout()

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / (
        f"{csv_path.stem}_poly_tangent_linear_0_to_1_angle_w{window_size}.png"
    )
    figure.savefig(
        output_path,
        dpi=dpi,
        bbox_inches="tight",
        pad_inches=0.15,
    )
    plt.close(figure)

    print(f"[SUCCESS] Đã lưu biểu đồ góc [0, 1]: {output_path}")
    return output_path


def save_trajectory_plot_01(
    csv_path: Path,
    output_dir: Path,
    x_values: np.ndarray,
    y_values: np.ndarray,
    frame_ids: np.ndarray,
    uniform_xy: tuple[np.ndarray, np.ndarray],
    linear_xy: tuple[np.ndarray, np.ndarray],
    window_size: int,
    poly_degree: int,
    dpi: int,
) -> Path:
    frame_start = int(frame_ids[0])
    frame_end = int(frame_ids[-1])

    figure, axis = plt.subplots(figsize=(10, 8), dpi=dpi)

    # 1. Raw Trajectory
    axis.plot(
        x_values,
        y_values,
        color="#d62728",
        linewidth=1.4,
        linestyle="-",
        alpha=0.45,
        label="Raw Trajectory (O)",
        zorder=2,
    )
    axis.scatter(
        x_values,
        y_values,
        color=RAW_ANGLE_COLOR,
        s=14,
        alpha=0.55,
        edgecolors="none",
        zorder=3,
    )

    # 2. Uniform Trajectory
    ux, uy = uniform_xy
    axis.plot(
        ux,
        uy,
        color=UNIFORM_COLOR,
        linewidth=2.4,
        linestyle="-",
        alpha=0.9,
        label=f"Uniform Weight 1:1 (W={window_size})",
        zorder=7,
    )

    # 3. Linear [0, 1] Trajectory
    lx, ly = linear_xy
    axis.plot(
        lx,
        ly,
        color=LINEAR_01_COLOR,
        linewidth=2.2,
        linestyle="-",
        alpha=0.9,
        label=f"Linear Weight [0, 1] (W={window_size})",
        zorder=6,
    )

    axis.invert_yaxis()
    axis.set_title(
        "2D Trajectory: Uniform Weight vs Linear Weight [0, 1]\n"
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
        f"{csv_path.stem}_poly_tangent_linear_0_to_1_2d_trajectory_w{window_size}.png"
    )
    figure.savefig(
        output_path,
        dpi=dpi,
        bbox_inches="tight",
        pad_inches=0.15,
    )
    plt.close(figure)

    print(f"[SUCCESS] Đã lưu quỹ đạo 2D [0, 1]: {output_path}")
    return output_path


def process_single_csv(
    csv_path: Path,
    output_dir: Path,
    window_size: int,
    poly_degree: int,
    buffer_frames: int,
    min_speed: float,
    min_block_length: int,
    vector_epsilon: float,
    seed: int,
    dpi: int,
):
    df = baseline.load_valid_dataframe(csv_path)
    angle_column = baseline.find_angle_column(df)

    segment = baseline.find_full_pass_moving_segment(
        df,
        buffer_frames=buffer_frames,
        seed=seed,
        min_speed=min_speed,
        min_block_length=min_block_length,
    )

    if len(segment) <= window_size:
        raise ValueError(
            f"Đoạn chuyển động chỉ có {len(segment)} mẫu sau khi trim buffer, "
            f"cần nhiều hơn W={window_size} mẫu"
        )

    x_values = segment["x_center"].to_numpy(dtype=float)
    y_values = segment["y_center"].to_numpy(dtype=float)
    raw_angles = segment[angle_column].to_numpy(dtype=float)
    if "frame_id" in segment.columns:
        frame_ids = segment["frame_id"].to_numpy(dtype=float)
    else:
        frame_ids = np.arange(len(segment), dtype=float)

    raw_unwrapped = baseline.unwrap_finite_degrees(raw_angles)

    # 1. Uniform case
    uniform_res = calculate_uniform_tangent(
        x_values=x_values,
        y_values=y_values,
        raw_unwrapped=raw_unwrapped,
        window_size=window_size,
        poly_degree=poly_degree,
        vector_epsilon=vector_epsilon,
    )

    # 2. Linear [0, 1] case
    linear_01_res = calculate_linear_01_tangent(
        x_values=x_values,
        y_values=y_values,
        raw_unwrapped=raw_unwrapped,
        window_size=window_size,
        poly_degree=poly_degree,
        vector_epsilon=vector_epsilon,
    )

    valid_start = min(window_size, len(x_values))
    plot_frames = frame_ids[valid_start:]
    raw_plot = raw_unwrapped[valid_start:]
    uniform_plot = uniform_res["tangent_angle"][valid_start:]
    linear_01_plot = linear_01_res["tangent_angle"][valid_start:]

    # Save trajectory
    save_trajectory_plot_01(
        csv_path=csv_path,
        output_dir=output_dir,
        x_values=x_values,
        y_values=y_values,
        frame_ids=frame_ids,
        uniform_xy=(uniform_res["smooth_x"], uniform_res["smooth_y"]),
        linear_xy=(linear_01_res["smooth_x"], linear_01_res["smooth_y"]),
        window_size=window_size,
        poly_degree=poly_degree,
        dpi=dpi,
    )

    # Save angle
    save_angle_plot_01(
        csv_path=csv_path,
        output_dir=output_dir,
        plot_frames=plot_frames,
        raw_plot=raw_plot,
        uniform_plot=uniform_plot,
        linear_01_plot=linear_01_plot,
        window_size=window_size,
        poly_degree=poly_degree,
        dpi=dpi,
    )

    print(f"\n[SUMMARY] {csv_path.name} (Frames {int(frame_ids[0])}-{int(frame_ids[-1])}):")
    baseline.print_angle_summary("Raw Angle (Model)", raw_plot)
    baseline.print_angle_summary(f"Uniform Weight 1:1 (W={window_size})", uniform_plot)
    baseline.print_angle_summary(f"Linear Weight [0, 1] (W={window_size})", linear_01_plot)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Linear Weight [0, 1] Polynomial Tangent Comparison Tool"
    )
    parser.add_argument(
        "input_path",
        type=Path,
        help="File CSV hoặc thư mục benchmark",
    )
    parser.add_argument(
        "--window-size",
        type=int,
        default=DEFAULT_WINDOW_SIZE,
        help=f"Kích thước cửa sổ trượt W (mặc định: {DEFAULT_WINDOW_SIZE})",
    )
    parser.add_argument(
        "--poly-degree",
        type=int,
        default=DEFAULT_POLY_DEGREE,
        help=f"Bậc đa thức fit (mặc định: {DEFAULT_POLY_DEGREE})",
    )
    parser.add_argument(
        "--buffer-frames",
        type=int,
        default=DEFAULT_BUFFER_FRAMES,
        help=f"Buffer frame cắt bỏ ở 2 đầu (mặc định: {DEFAULT_BUFFER_FRAMES})",
    )
    parser.add_argument(
        "--min-speed",
        type=float,
        default=DEFAULT_MIN_SPEED,
        help=f"Ngưỡng tốc độ px/frame (mặc định: {DEFAULT_MIN_SPEED})",
    )
    parser.add_argument(
        "--min-block-length",
        type=int,
        default=DEFAULT_MIN_BLOCK_LENGTH,
        help=f"Độ dài tối thiểu đoạn chuyển động (mặc định: {DEFAULT_MIN_BLOCK_LENGTH})",
    )
    parser.add_argument(
        "--vector-epsilon",
        type=float,
        default=DEFAULT_VECTOR_EPSILON,
        help=f"Epsilon lọc tangent vector (mặc định: {DEFAULT_VECTOR_EPSILON})",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Random seed (mặc định: {DEFAULT_SEED})",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=DEFAULT_DPI,
        help=f"DPI ảnh output (mặc định: {DEFAULT_DPI})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Thư mục output (mặc định: benchmark/poly_tangent_linear_weight_0_to_1)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.window_size < 3:
        print("[ERROR] window-size phải >= 3")
        return 1

    if args.poly_degree < 1:
        print("[ERROR] poly-degree phải >= 1")
        return 1

    if args.poly_degree >= args.window_size:
        print("[ERROR] poly-degree phải nhỏ hơn window-size")
        return 1

    try:
        csv_files = baseline.collect_csv_files(args.input_path)
    except Exception as err:
        print(f"[ERROR] Lỗi đọc CSV: {err}")
        return 1

    if not csv_files:
        print(f"[ERROR] Không tìm thấy CSV trong {args.input_path}")
        return 1

    if args.output_dir is not None:
        output_dir = args.output_dir
    else:
        base_dir = (
            args.input_path
            if args.input_path.is_dir()
            else args.input_path.parent
        )
        output_dir = base_dir / "poly_tangent_linear_weight_0_to_1"

    print("=" * 72)
    print(f"[INFO] Files: {len(csv_files)} | W = {args.window_size} | Degree = {args.poly_degree}")
    print(f"[INFO] Cases: Raw Angle, Uniform 1:1, Linear [0, 1]")
    print(f"[INFO] Output dir: {output_dir}")
    print("=" * 72)

    failures = 0
    for csv_file in csv_files:
        print(f"\n>>> Đang xử lý: {csv_file.name}")
        try:
            process_single_csv(
                csv_path=csv_file,
                output_dir=output_dir,
                window_size=args.window_size,
                poly_degree=args.poly_degree,
                buffer_frames=args.buffer_frames,
                min_speed=args.min_speed,
                min_block_length=args.min_block_length,
                vector_epsilon=args.vector_epsilon,
                seed=args.seed,
                dpi=args.dpi,
            )
        except Exception as exc:
            failures += 1
            print(f"[ERROR] Lỗi khi xử lý {csv_file.name}: {exc}")

    if failures > 0:
        print(f"\n[WARNING] Có {failures} file bị lỗi.")
        return 1

    print("\n[DONE] Hoàn thành thử nghiệm Linear Weight [0, 1]!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
