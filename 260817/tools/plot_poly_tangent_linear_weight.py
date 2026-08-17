"""
plot_poly_tangent_linear_weight.py
──────────────────────────────────
So sánh góc tiếp tuyến đa thức Least Squares với các trọng số Linear Weight khác nhau
cùng trường hợp Uniform Weight (baseline 1:1) và Raw Angle trên toàn bộ Stable Pass.

Pipeline:
1. Đọc CSV benchmark.
2. Dùng selector từ baseline: find_full_pass_moving_segment(...)
3. Cắt buffer (mặc định 10 frame) ở hai đầu đoạn chuyển động.
4. Trượt causal sliding window W (mặc định 18), bậc đa thức degree (mặc định 2).
5. Tính:
   - Raw Angle từ Model (màu đỏ đậm, #8b0000, nét liền)
   - Uniform Weight (Baseline ratio 1:1, màu xanh dương, #0055ff, nét liền)
   - Linear Weight với các tỷ lệ ratio (mặc định 1:1.5, 1:2.0, 1:3.0, nét liền)
6. Vẽ biểu đồ so sánh:
   - Combined Angle Comparison Plot (Tất cả trên 1 biểu đồ, toàn bộ nét liền)
   - Combined 2D Trajectory Comparison Plot

Ví dụ chạy:
    python tools/plot_poly_tangent_linear_weight.py benchmark/30_degree.csv
    python tools/plot_poly_tangent_linear_weight.py benchmark --window-size 18 --poly-degree 2
    python tools/plot_poly_tangent_linear_weight.py benchmark --weight-ratios 1.5,2,3
"""

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

# Import các hàm tiện ích từ baseline cùng thư mục
try:
    import plot_poly_tangent_angle_comparison as baseline
except ImportError:
    from tools import plot_poly_tangent_angle_comparison as baseline


DEFAULT_WINDOW_SIZE = 18
DEFAULT_POLY_DEGREE = 2
DEFAULT_BUFFER_FRAMES = 10
DEFAULT_WEIGHT_RATIOS = (1.5, 2.0, 3.0)
DEFAULT_SEED = 42
DEFAULT_MIN_SPEED = 1.5
DEFAULT_MIN_BLOCK_LENGTH = 30
DEFAULT_VECTOR_EPSILON = 1e-5
DEFAULT_DPI = 150

# Bảng màu chuẩn đồng bộ phong cách các ngày trước
RAW_ANGLE_COLOR = "#8b0000"       # Đỏ đậm (Raw Model)
UNIFORM_COLOR = "#0055ff"         # Xanh dương đậm (Uniform Baseline 1:1)
LINEAR_PALETTE = [
    "#ff7f0e",                    # Cam (Linear 1:1.5)
    "#2ca02c",                    # Xanh lá (Linear 1:2.0)
    "#9467bd",                    # Tím (Linear 1:3.0)
    "#e377c2",                    # Hồng tím
    "#17becf",                    # Cyan
    "#bcbd22",                    # Vàng chanh
]


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def linear_importance(window_length: int, ratio: float) -> np.ndarray:
    """
    Tạo trọng số importance alpha tăng tuyến tính:
        oldest = 1.0
        newest = ratio
    """
    if window_length < 1:
        raise ValueError("window_length phải >= 1")
    if ratio < 1.0:
        raise ValueError("ratio phải >= 1.0")

    if window_length == 1:
        return np.ones(1, dtype=float)

    return np.linspace(1.0, float(ratio), window_length, dtype=float)


def polyfit_weights(window_length: int, ratio: float) -> np.ndarray:
    """
    Chuyển importance alpha sang trọng số w cho np.polyfit.
    Vì np.polyfit(w=w) tối thiểu hóa sum((w_i * e_i)^2),
    nên w_i = sqrt(alpha_i).
    """
    return np.sqrt(linear_importance(window_length, ratio))


def weighted_poly_smooth_xy(
    x_values: np.ndarray,
    y_values: np.ndarray,
    window_size: int,
    poly_degree: int,
    ratio: float,
):
    """
    Causal sliding-window weighted polynomial fit bậc poly_degree.

    Với mỗi frame k:
        1. Lấy cửa sổ [max(0, k - W + 1) ... k]
        2. Chuẩn hóa trục thời gian về t in [-1, 0]
        3. Fit x(t), y(t) bằng Weighted Least Squares
        4. Lấy tọa độ endpoint tại t=0: x_smooth(0), y_smooth(0)
        5. Lấy đạo hàm tại t=0: dxdt(0), dydt(0) để tính góc tiếp tuyến
    """
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
        fit_w = polyfit_weights(window_length, ratio)

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


def calculate_case_tangent(
    x_values: np.ndarray,
    y_values: np.ndarray,
    raw_unwrapped: np.ndarray,
    window_size: int,
    poly_degree: int,
    ratio: float,
    vector_epsilon: float,
):
    smooth_x, smooth_y, tangent_x, tangent_y = weighted_poly_smooth_xy(
        x_values=x_values,
        y_values=y_values,
        window_size=window_size,
        poly_degree=poly_degree,
        ratio=ratio,
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


def save_combined_angle_plot(
    csv_path: Path,
    output_dir: Path,
    plot_frames: np.ndarray,
    raw_plot: np.ndarray,
    uniform_plot: np.ndarray,
    linear_cases: dict[float, np.ndarray],
    window_size: int,
    poly_degree: int,
    dpi: int,
) -> Path:
    frame_start = int(plot_frames[0])
    frame_end = int(plot_frames[-1])

    figure, axis = plt.subplots(figsize=(12, 7), dpi=dpi)

    # 1. Raw Angle (Model) - Nét liền, màu đỏ đậm
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

    # 2. Uniform Weight (Baseline 1:1) - Nét liền, màu xanh dương
    axis.plot(
        plot_frames,
        uniform_plot,
        color=UNIFORM_COLOR,
        linewidth=2.4,
        linestyle="-",
        label=f"Uniform Weight 1:1 (W={window_size})",
        zorder=9,
    )

    # 3. Các đường Linear Weight - Toàn bộ nét liền, các màu phân biệt rõ
    all_arrays_for_limits = [raw_plot, uniform_plot]
    for idx, (ratio, angle_array) in enumerate(linear_cases.items()):
        color = LINEAR_PALETTE[idx % len(LINEAR_PALETTE)]
        axis.plot(
            plot_frames,
            angle_array,
            color=color,
            linewidth=2.2,
            linestyle="-",
            label=f"Linear Weight 1:{ratio:g} (W={window_size})",
            zorder=8 - idx,
        )
        all_arrays_for_limits.append(angle_array)

    axis.set_title(
        "Heading Angle Comparison: Uniform vs Linear Weighted Polynomial Tangent\n"
        f"File: {csv_path.name} | Frames {frame_start}-{frame_end} | "
        f"Causal W={window_size}, Degree={poly_degree}",
        fontsize=12,
        fontweight="bold",
    )
    axis.set_xlabel("Frame ID", fontweight="bold")
    axis.set_ylabel("Angle (Degrees)", fontweight="bold")
    axis.grid(True, linestyle="--", alpha=0.6)
    axis.legend(loc="best", fontsize=9)

    baseline.set_robust_angle_limits(axis, all_arrays_for_limits)
    figure.tight_layout()

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / (
        f"{csv_path.stem}_poly_tangent_linear_weight_angle_w{window_size}.png"
    )
    figure.savefig(
        output_path,
        dpi=dpi,
        bbox_inches="tight",
        pad_inches=0.15,
    )
    plt.close(figure)

    print(f"[SUCCESS] Đã lưu biểu đồ góc so sánh: {output_path}")
    return output_path


def save_combined_trajectory_plot(
    csv_path: Path,
    output_dir: Path,
    x_values: np.ndarray,
    y_values: np.ndarray,
    frame_ids: np.ndarray,
    uniform_xy: tuple[np.ndarray, np.ndarray],
    linear_xy_cases: dict[float, tuple[np.ndarray, np.ndarray]],
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

    # 3. Linear Trajectories
    for idx, (ratio, (lx, ly)) in enumerate(linear_xy_cases.items()):
        color = LINEAR_PALETTE[idx % len(LINEAR_PALETTE)]
        axis.plot(
            lx,
            ly,
            color=color,
            linewidth=2.0,
            linestyle="-",
            alpha=0.85,
            label=f"Linear Weight 1:{ratio:g} (W={window_size})",
            zorder=6 - idx,
        )

    axis.invert_yaxis()
    axis.set_title(
        "2D Trajectory: Uniform vs Linear Weighted Polynomial Least Squares\n"
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
        f"{csv_path.stem}_poly_tangent_linear_weight_2d_trajectory_w{window_size}.png"
    )
    figure.savefig(
        output_path,
        dpi=dpi,
        bbox_inches="tight",
        pad_inches=0.15,
    )
    plt.close(figure)

    print(f"[SUCCESS] Đã lưu quỹ đạo 2D so sánh: {output_path}")
    return output_path


def process_single_csv(
    csv_path: Path,
    output_dir: Path,
    window_size: int,
    poly_degree: int,
    weight_ratios: list[float],
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

    # 1. Tính Uniform Case (ratio = 1.0)
    uniform_res = calculate_case_tangent(
        x_values=x_values,
        y_values=y_values,
        raw_unwrapped=raw_unwrapped,
        window_size=window_size,
        poly_degree=poly_degree,
        ratio=1.0,
        vector_epsilon=vector_epsilon,
    )

    # 2. Tính các Linear Cases
    linear_cases_angles = {}
    linear_cases_xy = {}
    for ratio in weight_ratios:
        case_res = calculate_case_tangent(
            x_values=x_values,
            y_values=y_values,
            raw_unwrapped=raw_unwrapped,
            window_size=window_size,
            poly_degree=poly_degree,
            ratio=ratio,
            vector_epsilon=vector_epsilon,
        )
        linear_cases_angles[ratio] = case_res["tangent_angle"]
        linear_cases_xy[ratio] = (case_res["smooth_x"], case_res["smooth_y"])

    valid_start = min(window_size, len(x_values))
    plot_frames = frame_ids[valid_start:]
    raw_plot = raw_unwrapped[valid_start:]
    uniform_plot = uniform_res["tangent_angle"][valid_start:]

    linear_plot_cases = {
        ratio: arr[valid_start:]
        for ratio, arr in linear_cases_angles.items()
    }

    # 3. Vẽ 2D Trajectory Comparison
    save_combined_trajectory_plot(
        csv_path=csv_path,
        output_dir=output_dir,
        x_values=x_values,
        y_values=y_values,
        frame_ids=frame_ids,
        uniform_xy=(uniform_res["smooth_x"], uniform_res["smooth_y"]),
        linear_xy_cases=linear_cases_xy,
        window_size=window_size,
        poly_degree=poly_degree,
        dpi=dpi,
    )

    # 4. Vẽ Combined Angle Comparison
    save_combined_angle_plot(
        csv_path=csv_path,
        output_dir=output_dir,
        plot_frames=plot_frames,
        raw_plot=raw_plot,
        uniform_plot=uniform_plot,
        linear_cases=linear_plot_cases,
        window_size=window_size,
        poly_degree=poly_degree,
        dpi=dpi,
    )

    # In tóm tắt thống kê
    print(f"\n[SUMMARY] {csv_path.name} (Frames {int(frame_ids[0])}-{int(frame_ids[-1])}):")
    baseline.print_angle_summary("Raw Angle (Model)", raw_plot)
    baseline.print_angle_summary(f"Uniform Weight 1:1 (W={window_size})", uniform_plot)
    for ratio in weight_ratios:
        baseline.print_angle_summary(
            f"Linear Weight 1:{ratio:g} (W={window_size})",
            linear_plot_cases[ratio],
        )


def parse_weight_ratios(text: str) -> list[float]:
    ratios = [float(item.strip()) for item in text.split(",") if item.strip()]
    if not ratios:
        raise ValueError("weight-ratios không được rỗng")
    for ratio in ratios:
        if ratio < 1.0:
            raise ValueError(f"weight ratio phải >= 1.0, nhận được {ratio}")
    return ratios


def parse_args():
    parser = argparse.ArgumentParser(
        description="Linear Weighted Polynomial Tangent Angle Comparison Tool"
    )
    parser.add_argument(
        "input_path",
        type=Path,
        help="Đường dẫn file CSV hoặc thư mục chứa các file CSV benchmark",
    )
    parser.add_argument(
        "--window-size",
        type=int,
        default=DEFAULT_WINDOW_SIZE,
        help=f"Kích thước cửa sổ trượt quá khứ W (mặc định: {DEFAULT_WINDOW_SIZE})",
    )
    parser.add_argument(
        "--poly-degree",
        type=int,
        default=DEFAULT_POLY_DEGREE,
        help=f"Bậc đa thức fit (mặc định: {DEFAULT_POLY_DEGREE})",
    )
    parser.add_argument(
        "--weight-ratios",
        type=str,
        default="1.5,2,3",
        help="Danh sách các tỷ lệ Linear Weight (mặc định: 1.5,2,3)",
    )
    parser.add_argument(
        "--buffer-frames",
        type=int,
        default=DEFAULT_BUFFER_FRAMES,
        help=f"Số frame cắt bỏ ở hai đầu đoạn di chuyển (mặc định: {DEFAULT_BUFFER_FRAMES})",
    )
    parser.add_argument(
        "--min-speed",
        type=float,
        default=DEFAULT_MIN_SPEED,
        help=f"Ngưỡng tốc độ tối thiểu px/frame (mặc định: {DEFAULT_MIN_SPEED})",
    )
    parser.add_argument(
        "--min-block-length",
        type=int,
        default=DEFAULT_MIN_BLOCK_LENGTH,
        help=f"Độ dài tối thiểu của đoạn di chuyển (mặc định: {DEFAULT_MIN_BLOCK_LENGTH})",
    )
    parser.add_argument(
        "--vector-epsilon",
        type=float,
        default=DEFAULT_VECTOR_EPSILON,
        help=f"Epsilon lọc vector tiếp tuyến (mặc định: {DEFAULT_VECTOR_EPSILON})",
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
        help=f"DPI ảnh xuất ra (mặc định: {DEFAULT_DPI})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Thư mục xuất ảnh (mặc định: benchmark/poly_tangent_linear_weight_comparison)",
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
        weight_ratios = parse_weight_ratios(args.weight_ratios)
    except ValueError as err:
        print(f"[ERROR] {err}")
        return 1

    try:
        csv_files = baseline.collect_csv_files(args.input_path)
    except Exception as err:
        print(f"[ERROR] Không thể lấy danh sách CSV: {err}")
        return 1

    if not csv_files:
        print(f"[ERROR] Không tìm thấy file CSV nào trong {args.input_path}")
        return 1

    if args.output_dir is not None:
        output_dir = args.output_dir
    else:
        base_dir = (
            args.input_path
            if args.input_path.is_dir()
            else args.input_path.parent
        )
        output_dir = base_dir / "poly_tangent_linear_weight_comparison"

    print("=" * 72)
    print(f"[INFO] Tổng số file CSV: {len(csv_files)}")
    print(f"[INFO] Causal Sliding Window W = {args.window_size} | Poly Degree = {args.poly_degree}")
    print(f"[INFO] Cases so sánh: Uniform (1:1), Linear ({', '.join(f'1:{r:g}' for r in weight_ratios)})")
    print(f"[INFO] Thư mục lưu kết quả: {output_dir}")
    print("=" * 72)

    failure_count = 0
    for csv_file in csv_files:
        print(f"\n>>> Đang xử lý: {csv_file.name}")
        try:
            process_single_csv(
                csv_path=csv_file,
                output_dir=output_dir,
                window_size=args.window_size,
                poly_degree=args.poly_degree,
                weight_ratios=weight_ratios,
                buffer_frames=args.buffer_frames,
                min_speed=args.min_speed,
                min_block_length=args.min_block_length,
                vector_epsilon=args.vector_epsilon,
                seed=args.seed,
                dpi=args.dpi,
            )
        except Exception as exc:
            failure_count += 1
            print(f"[ERROR] Lỗi khi xử lý {csv_file.name}: {exc}")

    if failure_count > 0:
        print(f"\n[WARNING] Có {failure_count} file bị lỗi trong quá trình thực thi.")
        return 1

    print("\n[DONE] Hoàn thành toàn bộ thực nghiệm so sánh Linear Weight!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())