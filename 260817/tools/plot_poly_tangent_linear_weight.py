"""
plot_poly_tangent_linear_weight.py
──────────────────────────────────
Công cụ hợp nhất cho toàn bộ các thử nghiệm làm mượt góc tiếp tuyến đa thức (Smooth 1):
1. So sánh các tỷ lệ Linear Weight (1:1.5, 1:2, 1:3) vs Uniform Weight (1:1) - Mục 5.
2. So sánh Delayed Heading Angle (tại index = 0 vs index = -3) - Mục 6.
3. So sánh độ mịn RMS giữa 3 phương án (Smooth 1, Delayed -3, Smooth 2) cùng 3 đường Reference bậc 1 - Mục 7.

Lệnh chạy:
    # 1. Chạy so sánh các tỷ lệ Linear Weight (Mục 5)
    python tools/plot_poly_tangent_linear_weight.py benchmark --mode compare_weights

    # 2. Chạy so sánh Delayed Angle index = -3 (Mục 6)
    python tools/plot_poly_tangent_linear_weight.py benchmark --mode delayed

    # 3. Chạy so sánh RMS 3 phương án kèm 3 đường Reference bậc 1 (Mục 7)
    python tools/plot_poly_tangent_linear_weight.py benchmark --mode rms_compare

    # 4. Chạy toàn bộ tất cả các chế độ
    python tools/plot_poly_tangent_linear_weight.py benchmark --mode all
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
DEFAULT_WEIGHT_RATIOS = (1.5, 2.0, 3.0)
DEFAULT_SEED = 42
DEFAULT_MIN_SPEED = 1.5
DEFAULT_MIN_BLOCK_LENGTH = 30
DEFAULT_VECTOR_EPSILON = 1e-5
DEFAULT_DPI = 150

# Bảng màu chuẩn
RAW_ANGLE_COLOR = "#8b0000"       # Đỏ đậm (Raw Model)
UNIFORM_COLOR = "#0055ff"         # Xanh dương đậm (Smooth 1 / index=0)
DELAYED_COLOR = "#ff7f0e"         # Cam sẫm (Delayed Tangent index=-3)
SMOOTH2_COLOR = "#2ca02c"         # Xanh lá đậm (Smooth 2 W2=36)

LINEAR_PALETTE = [
    "#ff7f0e",                    # Cam (Linear 1:1.5)
    "#2ca02c",                    # Xanh lá (Linear 1:2.0)
    "#9467bd",                    # Tím (Linear 1:3.0)
    "#e377c2",                    # Hồng tím
    "#17becf",                    # Cyan
]


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def get_weights(window_length: int, weight_mode: str, ratio: float = 1.0) -> np.ndarray:
    """
    Tạo trọng số fit cho np.polyfit.
    """
    if window_length < 1:
        raise ValueError("window_length phải >= 1")
    if window_length == 1:
        return np.ones(1, dtype=float)

    if weight_mode == "uniform" or ratio == 1.0:
        return np.ones(window_length, dtype=float)
    elif weight_mode == "linear_0_to_1":
        alpha = np.linspace(0.0, 1.0, window_length, dtype=float)
        return np.sqrt(np.clip(alpha, 1e-6, 1.0))
    elif weight_mode == "linear_ratio":
        alpha = np.linspace(1.0, float(ratio), window_length, dtype=float)
        return np.sqrt(alpha)
    else:
        raise ValueError(f"weight_mode không hợp lệ: {weight_mode}")


def fit_causal_poly_tangent(
    x_values: np.ndarray,
    y_values: np.ndarray,
    window_size: int,
    poly_degree: int,
    weight_mode: str = "uniform",
    ratio: float = 1.0,
    eval_index: int = 0,
):
    """
    Fit đa thức causal sliding window và tính tiếp tuyến tại eval_index.
    eval_index = 0: endpoint mới nhất (t = 0.0)
    eval_index = -3: lùi lại 3 mẫu (t = -3 / (W-1))
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
        fit_w = get_weights(window_length, weight_mode=weight_mode, ratio=ratio)

        coefficients_x = np.polyfit(
            time_normalized, x_window, deg=current_degree, w=fit_w
        )
        coefficients_y = np.polyfit(
            time_normalized, y_window, deg=current_degree, w=fit_w
        )

        target_idx_in_window = max(0, window_length - 1 + eval_index)
        if window_length > 1:
            t_eval = (target_idx_in_window - (window_length - 1)) / (window_length - 1)
        else:
            t_eval = 0.0

        smooth_x[index] = float(np.polyval(coefficients_x, t_eval))
        smooth_y[index] = float(np.polyval(coefficients_y, t_eval))

        if current_degree >= 1:
            tangent_x[index] = float(
                np.polyval(np.polyder(coefficients_x), t_eval)
            )
            tangent_y[index] = float(
                np.polyval(np.polyder(coefficients_y), t_eval)
            )

    return smooth_x, smooth_y, tangent_x, tangent_y


def calculate_tangent_series(
    x_values: np.ndarray,
    y_values: np.ndarray,
    raw_unwrapped: np.ndarray,
    window_size: int,
    poly_degree: int,
    weight_mode: str = "uniform",
    ratio: float = 1.0,
    eval_index: int = 0,
    vector_epsilon: float = DEFAULT_VECTOR_EPSILON,
):
    smooth_x, smooth_y, tangent_x, tangent_y = fit_causal_poly_tangent(
        x_values=x_values,
        y_values=y_values,
        window_size=window_size,
        poly_degree=poly_degree,
        weight_mode=weight_mode,
        ratio=ratio,
        eval_index=eval_index,
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


def compute_linear_fit_and_rms(frame_ids: np.ndarray, angle_values: np.ndarray):
    """
    Fit đa thức bậc 1 (đường thẳng Ground Truth) và tính sai số RMS.
    """
    valid_mask = np.isfinite(angle_values)
    if np.count_nonzero(valid_mask) < 2:
        return np.full_like(angle_values, np.nan), np.nan

    valid_frames = frame_ids[valid_mask]
    valid_angles = angle_values[valid_mask]

    p1 = np.polyfit(valid_frames, valid_angles, deg=1)
    ref_line = np.polyval(p1, frame_ids)

    residuals = valid_angles - np.polyval(p1, valid_frames)
    rms_error = float(np.sqrt(np.mean(residuals ** 2)))
    return ref_line, rms_error


# =========================================================================
# 1. Chế độ: So sánh Delayed Heading Angle (Mục 6)
# =========================================================================
def run_delayed_mode(df, csv_path: Path, output_dir: Path, window_size: int, poly_degree: int, buffer_frames: int, seed: int, dpi: int):
    angle_column = baseline.find_angle_column(df)
    segment = baseline.find_full_pass_moving_segment(
        df, buffer_frames=buffer_frames, seed=seed, min_speed=DEFAULT_MIN_SPEED, min_block_length=DEFAULT_MIN_BLOCK_LENGTH
    )
    if len(segment) <= window_size:
        raise ValueError(f"Số mẫu ({len(segment)}) nhỏ hơn W={window_size}")

    x_values = segment["x_center"].to_numpy(dtype=float)
    y_values = segment["y_center"].to_numpy(dtype=float)
    raw_angles = segment[angle_column].to_numpy(dtype=float)
    frame_ids = segment["frame_id"].to_numpy(dtype=float) if "frame_id" in segment.columns else np.arange(len(segment), dtype=float)
    raw_unwrapped = baseline.unwrap_finite_degrees(raw_angles)

    # 1. Endpoint Tangent (index = 0) với Linear Weight [0, 1]
    res_endpoint = calculate_tangent_series(
        x_values, y_values, raw_unwrapped, window_size, poly_degree, weight_mode="linear_0_to_1", eval_index=0
    )
    # 2. Delayed Tangent (index = -3) với Linear Weight [0, 1]
    res_delayed = calculate_tangent_series(
        x_values, y_values, raw_unwrapped, window_size, poly_degree, weight_mode="linear_0_to_1", eval_index=-3
    )

    valid_start = min(window_size, len(x_values))
    plot_frames = frame_ids[valid_start:]
    raw_plot = raw_unwrapped[valid_start:]
    endpoint_plot = res_endpoint["tangent_angle"][valid_start:]
    delayed_plot = res_delayed["tangent_angle"][valid_start:]

    # Vẽ quỹ đạo 2D (Đường fit chuẩn màu xanh dương #0055ff)
    fig, ax = plt.subplots(figsize=(10, 8), dpi=dpi)
    ax.plot(x_values, y_values, color="#d62728", linewidth=1.5, linestyle="-", alpha=0.5, label="Raw Trajectory (O)", zorder=2)
    ax.scatter(x_values, y_values, color=RAW_ANGLE_COLOR, s=15, alpha=0.6, edgecolors="none", zorder=3)
    ax.plot(res_endpoint["smooth_x"], res_endpoint["smooth_y"], color=UNIFORM_COLOR, linewidth=2.5, linestyle="-", alpha=0.95, label=f"Linear Weight [0, 1] Degree {poly_degree} (W={window_size})", zorder=6)
    ax.invert_yaxis()
    ax.set_title(
        f"2D Trajectory: Raw vs Polynomial Least Squares (Linear Weight [0, 1])\nFile: {csv_path.name} | Frames {int(frame_ids[0])}-{int(frame_ids[-1])} | Causal W={window_size}, Degree={poly_degree}",
        fontsize=12,
        fontweight="bold"
    )
    ax.set_xlabel("X Center (pixels)", fontweight="bold")
    ax.set_ylabel("Y Center (pixels)", fontweight="bold")
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(loc="best", fontsize=9)
    fig.tight_layout()

    output_dir.mkdir(parents=True, exist_ok=True)
    traj_path = output_dir / f"{csv_path.stem}_poly_tangent_delayed_2d_trajectory_w{window_size}.png"
    fig.savefig(traj_path, dpi=dpi, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)

    # Vẽ biểu đồ góc
    fig, ax = plt.subplots(figsize=(12, 7), dpi=dpi)
    ax.plot(plot_frames, raw_plot, color=RAW_ANGLE_COLOR, linewidth=2.5, linestyle="-", alpha=0.85, label="Raw Angle (Model)", zorder=12)
    ax.plot(plot_frames, endpoint_plot, color=UNIFORM_COLOR, linewidth=2.4, linestyle="-", label=f"Endpoint Tangent [0, 1] (index=0, W={window_size})", zorder=10)
    ax.plot(plot_frames, delayed_plot, color=DELAYED_COLOR, linewidth=2.3, linestyle="-", label=f"Delayed Tangent [0, 1] (index=-3, W={window_size})", zorder=9)
    ax.set_title(
        f"Heading Angle Comparison: Endpoint (index=0) vs Delayed (index=-3) with Linear Weight [0, 1]\nFile: {csv_path.name} | Frames {int(frame_ids[0])}-{int(frame_ids[-1])} | W={window_size}, Degree={poly_degree}",
        fontsize=12,
        fontweight="bold"
    )
    ax.set_xlabel("Frame ID", fontweight="bold")
    ax.set_ylabel("Angle (Degrees)", fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.legend(loc="best", fontsize=9)
    baseline.set_robust_angle_limits(ax, [raw_plot, endpoint_plot, delayed_plot])
    fig.tight_layout()

    angle_path = output_dir / f"{csv_path.stem}_poly_tangent_delayed_angle_w{window_size}.png"
    fig.savefig(angle_path, dpi=dpi, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)

    print(f"[SUCCESS-DELAYED] {csv_path.name}: Đã lưu quỹ đạo và biểu đồ góc Linear [0, 1] (index=0 vs index=-3)")


# =========================================================================
# 2. Chế độ: So sánh RMS với 3 cặp đường cùng tone màu (Mục 8)
# =========================================================================
def run_rms_compare_mode(df, csv_path: Path, output_dir: Path, window_size: int, poly_degree: int, buffer_frames: int, seed: int, dpi: int):
    angle_column = baseline.find_angle_column(df)
    segment = baseline.find_full_pass_moving_segment(
        df, buffer_frames=buffer_frames, seed=seed, min_speed=DEFAULT_MIN_SPEED, min_block_length=DEFAULT_MIN_BLOCK_LENGTH
    )
    if len(segment) <= window_size:
        raise ValueError(f"Số mẫu ({len(segment)}) nhỏ hơn W={window_size}")

    x_values = segment["x_center"].to_numpy(dtype=float)
    y_values = segment["y_center"].to_numpy(dtype=float)
    raw_angles = segment[angle_column].to_numpy(dtype=float)
    frame_ids = segment["frame_id"].to_numpy(dtype=float) if "frame_id" in segment.columns else np.arange(len(segment), dtype=float)
    raw_unwrapped = baseline.unwrap_finite_degrees(raw_angles)

    # 1. Smooth 1 (index = 0) với Linear Weight [0, 1]
    res_s1 = calculate_tangent_series(x_values, y_values, raw_unwrapped, window_size, poly_degree, weight_mode="linear_0_to_1", eval_index=0)
    # 2. Delayed Tangent (index = -3) với Linear Weight [0, 1]
    res_del = calculate_tangent_series(x_values, y_values, raw_unwrapped, window_size, poly_degree, weight_mode="linear_0_to_1", eval_index=-3)
    # 3. Smooth 2 (W2 = W1 * 2 = 36)
    res_all = baseline.calculate_angle_series(x_values, y_values, raw_angles, window_size, poly_degree, DEFAULT_VECTOR_EPSILON)

    valid_start = min(window_size, len(x_values))
    plot_frames = frame_ids[valid_start:]
    raw_plot = raw_unwrapped[valid_start:]
    s1_plot = res_s1["tangent_angle"][valid_start:]
    del_plot = res_del["tangent_angle"][valid_start:]
    s2_plot = res_all["poly_tangent_smooth2"][valid_start:]

    # Fit 3 đường reference đa thức bậc 1 và tính 3 giá trị RMS
    ref_s1, rms_s1 = compute_linear_fit_and_rms(plot_frames, s1_plot)
    ref_del, rms_del = compute_linear_fit_and_rms(plot_frames, del_plot)
    ref_s2, rms_s2 = compute_linear_fit_and_rms(plot_frames, s2_plot)

    # Vẽ biểu đồ góc với đường Raw Angle và 3 cặp đường (cùng màu, đường reference nét đứt)
    fig, ax = plt.subplots(figsize=(12, 7), dpi=dpi)

    # Đường Raw Angle (Model) - Màu đỏ đậm
    ax.plot(plot_frames, raw_plot, color=RAW_ANGLE_COLOR, linewidth=2.5, linestyle="-", alpha=0.85, label="Raw Angle (Model)", zorder=12)

    # Cặp 1: Smooth 1 (Xanh dương)
    ax.plot(plot_frames, s1_plot, color=UNIFORM_COLOR, linewidth=2.4, linestyle="-", label=f"Smooth 1 Linear [0, 1] (index=0) - RMS: {rms_s1:.2f}°", zorder=10)
    ax.plot(plot_frames, ref_s1, color=UNIFORM_COLOR, linewidth=1.6, linestyle="--", alpha=0.55, label="Poly Fit Bậc 1 (Ref Smooth 1)", zorder=5)

    # Cặp 2: Delayed Tangent (Cam)
    ax.plot(plot_frames, del_plot, color=DELAYED_COLOR, linewidth=2.2, linestyle="-", label=f"Delayed Tangent [0, 1] (index=-3) - RMS: {rms_del:.2f}°", zorder=9)
    ax.plot(plot_frames, ref_del, color=DELAYED_COLOR, linewidth=1.6, linestyle="--", alpha=0.55, label="Poly Fit Bậc 1 (Ref Delayed -3)", zorder=4)

    # Cặp 3: Smooth 2 (Xanh lá)
    ax.plot(plot_frames, s2_plot, color=SMOOTH2_COLOR, linewidth=2.2, linestyle="-", label=f"Smooth 2 (W2=36) - RMS: {rms_s2:.2f}°", zorder=8)
    ax.plot(plot_frames, ref_s2, color=SMOOTH2_COLOR, linewidth=1.6, linestyle="--", alpha=0.55, label="Poly Fit Bậc 1 (Ref Smooth 2)", zorder=3)

    ax.set_title(
        f"Heading Angle & Linear Fit RMS Comparison (Linear Weight [0, 1] on Smooth 1 & Delayed)\nFile: {csv_path.name} | Frames {int(frame_ids[0])}-{int(frame_ids[-1])} | W={window_size}, Degree={poly_degree}",
        fontsize=12,
        fontweight="bold"
    )
    ax.set_xlabel("Frame ID", fontweight="bold")
    ax.set_ylabel("Angle (Degrees)", fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.legend(loc="best", fontsize=9)
    baseline.set_robust_angle_limits(ax, [raw_plot, s1_plot, ref_s1, del_plot, ref_del, s2_plot, ref_s2])
    fig.tight_layout()

    output_dir.mkdir(parents=True, exist_ok=True)
    angle_path = output_dir / f"{csv_path.stem}_rms_smoothing_comparison_w{window_size}.png"
    fig.savefig(angle_path, dpi=dpi, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)

    print(f"\n[RMS RESULT] {csv_path.name}:")
    print(f"    - Smooth 1 Linear [0, 1] (index=0): RMS = {rms_s1:.2f}°")
    print(f"    - Delayed Tangent [0, 1] (-3): RMS = {rms_del:.2f}°")
    print(f"    - Smooth 2 (W2=36): RMS = {rms_s2:.2f}°")

    return {
        "file": csv_path.name,
        "rms_s1": rms_s1,
        "rms_del": rms_del,
        "rms_s2": rms_s2,
    }


# =========================================================================
# 3. Chế độ: So sánh các tỷ lệ Linear Weight (Mục 5)
# =========================================================================
def run_compare_weights_mode(df, csv_path: Path, output_dir: Path, window_size: int, poly_degree: int, weight_ratios: list[float], buffer_frames: int, seed: int, dpi: int):
    angle_column = baseline.find_angle_column(df)
    segment = baseline.find_full_pass_moving_segment(
        df, buffer_frames=buffer_frames, seed=seed, min_speed=DEFAULT_MIN_SPEED, min_block_length=DEFAULT_MIN_BLOCK_LENGTH
    )
    if len(segment) <= window_size:
        raise ValueError(f"Số mẫu ({len(segment)}) nhỏ hơn W={window_size}")

    x_values = segment["x_center"].to_numpy(dtype=float)
    y_values = segment["y_center"].to_numpy(dtype=float)
    raw_angles = segment[angle_column].to_numpy(dtype=float)
    frame_ids = segment["frame_id"].to_numpy(dtype=float) if "frame_id" in segment.columns else np.arange(len(segment), dtype=float)
    raw_unwrapped = baseline.unwrap_finite_degrees(raw_angles)

    uniform_res = calculate_tangent_series(x_values, y_values, raw_unwrapped, window_size, poly_degree, weight_mode="uniform")
    linear_cases_angles = {}
    linear_cases_xy = {}
    for ratio in weight_ratios:
        case_res = calculate_tangent_series(x_values, y_values, raw_unwrapped, window_size, poly_degree, weight_mode="linear_ratio", ratio=ratio)
        linear_cases_angles[ratio] = case_res["tangent_angle"]
        linear_cases_xy[ratio] = (case_res["smooth_x"], case_res["smooth_y"])

    valid_start = min(window_size, len(x_values))
    plot_frames = frame_ids[valid_start:]
    raw_plot = raw_unwrapped[valid_start:]
    uniform_plot = uniform_res["tangent_angle"][valid_start:]
    linear_plot_cases = {ratio: arr[valid_start:] for ratio, arr in linear_cases_angles.items()}

    # 2D Trajectory
    fig, ax = plt.subplots(figsize=(10, 8), dpi=dpi)
    ax.plot(x_values, y_values, color="#d62728", linewidth=1.5, linestyle="-", alpha=0.5, label="Raw Trajectory (O)", zorder=2)
    ax.scatter(x_values, y_values, color=RAW_ANGLE_COLOR, s=15, alpha=0.6, edgecolors="none", zorder=3)
    ax.plot(uniform_res["smooth_x"], uniform_res["smooth_y"], color=UNIFORM_COLOR, linewidth=2.5, linestyle="-", alpha=0.95, label=f"Polynomial Least Squares Degree {poly_degree} (Causal W={window_size})", zorder=6)
    ax.invert_yaxis()
    ax.set_title(
        f"2D Trajectory: Raw vs Polynomial Least Squares\nFile: {csv_path.name} | Frames {int(frame_ids[0])}-{int(frame_ids[-1])} | Causal W={window_size}, Polynomial Degree={poly_degree}",
        fontsize=12,
        fontweight="bold"
    )
    ax.set_xlabel("X Center (pixels)", fontweight="bold")
    ax.set_ylabel("Y Center (pixels)", fontweight="bold")
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(loc="best", fontsize=9)
    fig.tight_layout()

    output_dir.mkdir(parents=True, exist_ok=True)
    traj_path = output_dir / f"{csv_path.stem}_poly_tangent_linear_weight_2d_trajectory_w{window_size}.png"
    fig.savefig(traj_path, dpi=dpi, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)

    # Angle Comparison
    fig, ax = plt.subplots(figsize=(12, 7), dpi=dpi)
    ax.plot(plot_frames, raw_plot, color=RAW_ANGLE_COLOR, linewidth=2.5, linestyle="-", alpha=0.85, label="Raw Angle (Model)", zorder=10)
    ax.plot(plot_frames, uniform_plot, color=UNIFORM_COLOR, linewidth=2.4, linestyle="-", label=f"Uniform Weight 1:1 (W={window_size})", zorder=9)
    all_arrays = [raw_plot, uniform_plot]
    for idx, (ratio, angle_array) in enumerate(linear_plot_cases.items()):
        color = LINEAR_PALETTE[idx % len(LINEAR_PALETTE)]
        ax.plot(plot_frames, angle_array, color=color, linewidth=2.2, linestyle="-", label=f"Linear Weight 1:{ratio:g} (W={window_size})", zorder=8 - idx)
        all_arrays.append(angle_array)
    ax.set_title(
        f"Heading Angle Comparison: Uniform vs Linear Weighted Polynomial Tangent\nFile: {csv_path.name} | Frames {int(frame_ids[0])}-{int(frame_ids[-1])} | W={window_size}, Degree={poly_degree}",
        fontsize=12,
        fontweight="bold"
    )
    ax.set_xlabel("Frame ID", fontweight="bold")
    ax.set_ylabel("Angle (Degrees)", fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.legend(loc="best", fontsize=9)
    baseline.set_robust_angle_limits(ax, all_arrays)
    fig.tight_layout()

    angle_path = output_dir / f"{csv_path.stem}_poly_tangent_linear_weight_angle_w{window_size}.png"
    fig.savefig(angle_path, dpi=dpi, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)

    print(f"[SUCCESS-WEIGHTS] {csv_path.name}: Đã lưu so sánh các tỷ lệ Linear Weight")


def parse_args():
    parser = argparse.ArgumentParser(description="Unified Polynomial Tangent Comparison Tool")
    parser.add_argument("input_path", type=Path, help="CSV hoặc thư mục benchmark")
    parser.add_argument("--mode", type=str, default="all", choices=["compare_weights", "delayed", "rms_compare", "all"],
                        help="Chế độ chạy: compare_weights (Mục 5), delayed (Mục 6), rms_compare (Mục 7), all (tất cả)")
    parser.add_argument("--window-size", type=int, default=DEFAULT_WINDOW_SIZE, help=f"W (mặc định: {DEFAULT_WINDOW_SIZE})")
    parser.add_argument("--poly-degree", type=int, default=DEFAULT_POLY_DEGREE, help=f"Bậc đa thức (mặc định: {DEFAULT_POLY_DEGREE})")
    parser.add_argument("--weight-ratios", type=str, default="1.5,2,3", help="Danh sách tỷ lệ Linear Weight")
    parser.add_argument("--buffer-frames", type=int, default=DEFAULT_BUFFER_FRAMES, help=f"Buffer frame (mặc định: {DEFAULT_BUFFER_FRAMES})")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help=f"Seed (mặc định: {DEFAULT_SEED})")
    parser.add_argument("--dpi", type=int, default=DEFAULT_DPI, help=f"DPI (mặc định: {DEFAULT_DPI})")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        csv_files = baseline.collect_csv_files(args.input_path)
    except Exception as e:
        print(f"[ERROR] {e}")
        return 1

    weight_ratios = [float(x.strip()) for x in args.weight_ratios.split(",") if x.strip()]
    base_dir = args.input_path if args.input_path.is_dir() else args.input_path.parent

    print("=" * 72)
    print(f"[INFO] Files: {len(csv_files)} | Mode: {args.mode} | W = {args.window_size} | Degree = {args.poly_degree}")
    print("=" * 72)

    rms_results = []
    for csv_file in csv_files:
        df = baseline.load_valid_dataframe(csv_file)

        if args.mode in ("compare_weights", "all"):
            out_dir = base_dir / "poly_tangent_linear_weight_comparison"
            run_compare_weights_mode(df, csv_file, out_dir, args.window_size, args.poly_degree, weight_ratios, args.buffer_frames, args.seed, args.dpi)

        if args.mode in ("delayed", "all"):
            out_dir = base_dir / "poly_tangent_delayed_angle_comparison"
            run_delayed_mode(df, csv_file, out_dir, args.window_size, args.poly_degree, args.buffer_frames, args.seed, args.dpi)

        if args.mode in ("rms_compare", "all"):
            out_dir = base_dir / "rms_smoothing_comparison"
            res = run_rms_compare_mode(df, csv_file, out_dir, args.window_size, args.poly_degree, args.buffer_frames, args.seed, args.dpi)
            if res:
                rms_results.append(res)

    if rms_results:
        print("\n" + "=" * 72)
        print("[FINAL SUMMARY] BẢNG TỔNG HỢP SAI SỐ RMS SO VỚI 3 ĐƯỜNG FIT BẬC 1:")
        print(f"{'File':<18} | {'Smooth 1 (index=0)':<20} | {'Delayed (index=-3)':<20} | {'Smooth 2 (W2=36)':<18}")
        print("-" * 72)
        for r in rms_results:
            print(f"{r['file']:<18} | {r['rms_s1']:>18.2f}° | {r['rms_del']:>18.2f}° | {r['rms_s2']:>16.2f}°")
        print("=" * 72)

    print("\n[DONE] Hoàn thành xử lý toàn bộ các chế độ!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())