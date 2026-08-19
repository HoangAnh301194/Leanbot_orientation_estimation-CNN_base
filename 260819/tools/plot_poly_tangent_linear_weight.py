"""
plot_poly_tangent_linear_weight.py
──────────────────────────────────
Công cụ thực nghiệm & trực quan hóa toàn diện cho Báo cáo công việc ngày 19/08/2026:
1. So sánh Delayed Tangent giữa Uniform Weight và Linear Weight [0, 1] (W=18, index=-3).
2. So sánh Smooth 1 Delayed Tangent [0, 1] (W1=18, index=-3) vs Smooth 2 Delayed Tangent (W2=36, index=-3).
3. So sánh kích thước cửa sổ W=18 vs W=15 đối với Delayed Tangent [0, 1] (index=-3).
4. So sánh các mức delay (-2, -3, -4) đối với Delayed Tangent Linear [0, 1] (W=18).
5. Tính toán định lượng sai số RMS độ mịn và RMS trung bình (Average RMS) cho tất cả các kịch bản.

Lệnh chạy:
    # Chạy toàn bộ benchmark và xuất tất cả biểu đồ & bảng RMS
    python 260819/tools/plot_poly_tangent_linear_weight.py 260819/benchmark --mode all
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

# Bảng màu chuẩn
RAW_ANGLE_COLOR = "#8b0000"       # Đỏ đậm (Raw Model)
UNIFORM_COLOR = "#0055ff"         # Xanh dương đậm (Uniform / index=-2)
LINEAR_COLOR = "#ff7f0e"          # Cam sẫm (Linear [0, 1] / index=-3)
SMOOTH2_COLOR = "#2ca02c"         # Xanh lá đậm (Smooth 2 / index=-4)
PURPLE_COLOR = "#9467bd"          # Tím (Cửa sổ W=15)


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

    if weight_mode == "uniform":
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


def fit_causal_poly_1d(
    values: np.ndarray,
    window_size: int,
    poly_degree: int,
    eval_index: int = 0,
) -> np.ndarray:
    """
    Fit đa thức causal 1D trên chuỗi góc và evaluate tại eval_index (Smooth 2).
    """
    sample_count = len(values)
    smoothed = np.full(sample_count, np.nan, dtype=float)
    for index in range(sample_count):
        window_start = max(0, index - window_size + 1)
        window_end = index + 1
        window_data = values[window_start:window_end]
        finite_mask = np.isfinite(window_data)
        if np.count_nonzero(finite_mask) < 2:
            continue
        valid_data = window_data[finite_mask]
        current_degree = min(poly_degree, len(valid_data) - 1)
        raw_indices = np.arange(len(window_data))[finite_mask]
        time_normalized = (raw_indices - (len(window_data) - 1)) / max(1, len(window_data) - 1)

        coefficients = np.polyfit(time_normalized, valid_data, deg=current_degree)
        target_idx_in_window = max(0, len(window_data) - 1 + eval_index)
        if len(window_data) > 1:
            t_eval = (target_idx_in_window - (len(window_data) - 1)) / (len(window_data) - 1)
        else:
            t_eval = 0.0
        smoothed[index] = float(np.polyval(coefficients, t_eval))
    return smoothed


def compute_linear_fit_and_rms(frame_ids: np.ndarray, angle_values: np.ndarray):
    """
    Fit đa thức bậc 1 (đường thẳng Ground Truth Reference) và tính sai số RMS.
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
# 1. Chế độ: So sánh Delayed Uniform vs Delayed Linear [0, 1] (index = -3)
# =========================================================================
def run_compare_uniform_linear_delayed(df, csv_path: Path, output_dir: Path, window_size: int = 18, poly_degree: int = 2, buffer_frames: int = 10, seed: int = 42, dpi: int = 150):
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

    res_uniform = calculate_tangent_series(x_values, y_values, raw_unwrapped, window_size, poly_degree, weight_mode="uniform", eval_index=-3)
    res_linear = calculate_tangent_series(x_values, y_values, raw_unwrapped, window_size, poly_degree, weight_mode="linear_0_to_1", eval_index=-3)

    valid_start = min(window_size, len(x_values))
    plot_frames = frame_ids[valid_start:]
    raw_plot = raw_unwrapped[valid_start:]
    uniform_plot = res_uniform["tangent_angle"][valid_start:]
    linear_plot = res_linear["tangent_angle"][valid_start:]

    ref_uni, rms_uni = compute_linear_fit_and_rms(plot_frames, uniform_plot)
    ref_lin, rms_lin = compute_linear_fit_and_rms(plot_frames, linear_plot)

    output_dir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(12, 7), dpi=dpi)
    ax.plot(plot_frames, raw_plot, color=RAW_ANGLE_COLOR, linewidth=2.5, linestyle="-", alpha=0.85, label="Raw Angle (Model)", zorder=12)

    ax.plot(plot_frames, uniform_plot, color=UNIFORM_COLOR, linewidth=2.3, linestyle="-", label=f"Delayed Tangent Uniform (index=-3) - RMS: {rms_uni:.2f}°", zorder=10)
    ax.plot(plot_frames, ref_uni, color=UNIFORM_COLOR, linewidth=1.6, linestyle="--", alpha=0.55, label="Poly Fit Bậc 1 (Ref Uniform)", zorder=4)

    ax.plot(plot_frames, linear_plot, color=LINEAR_COLOR, linewidth=2.3, linestyle="-", label=f"Delayed Tangent Linear [0, 1] (index=-3) - RMS: {rms_lin:.2f}°", zorder=9)
    ax.plot(plot_frames, ref_lin, color=LINEAR_COLOR, linewidth=1.6, linestyle="--", alpha=0.55, label="Poly Fit Bậc 1 (Ref Linear [0, 1])", zorder=3)

    ax.set_title(
        f"Delayed Tangent Heading Angle: Uniform vs Linear Weight [0, 1] (index=-3)\nFile: {csv_path.name} | Frames {int(frame_ids[0])}-{int(frame_ids[-1])} | W={window_size}, Degree={poly_degree}",
        fontsize=12,
        fontweight="bold"
    )
    ax.set_xlabel("Frame ID", fontweight="bold")
    ax.set_ylabel("Angle (Degrees)", fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.legend(loc="best", fontsize=9)
    baseline.set_robust_angle_limits(ax, [raw_plot, uniform_plot, ref_uni, linear_plot, ref_lin])
    fig.tight_layout()

    angle_path = output_dir / f"{csv_path.stem}_uniform_vs_linear_delayed_angle_w{window_size}.png"
    fig.savefig(angle_path, dpi=dpi, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)

    print(f"[SUCCESS-UNI-VS-LIN] {csv_path.name} | Uniform RMS: {rms_uni:.2f}° | Linear RMS: {rms_lin:.2f}°")
    return {
        "file": csv_path.name,
        "rms_uniform_delayed": rms_uni,
        "rms_linear_delayed": rms_lin,
    }


# =========================================================================
# 2. Chế độ: So sánh Smooth 1 Delayed vs Smooth 2 Delayed (W2 = 36, index = -3)
# =========================================================================
def run_compare_smooth1_smooth2_delayed(df, csv_path: Path, output_dir: Path, window_size: int = 18, poly_degree: int = 2, buffer_frames: int = 10, seed: int = 42, dpi: int = 150):
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

    res_s1_del = calculate_tangent_series(x_values, y_values, raw_unwrapped, window_size, poly_degree, weight_mode="linear_0_to_1", eval_index=-3)
    s1_angle = res_s1_del["tangent_angle"]

    window_size_smooth2 = window_size * 2
    s2_del_angle = fit_causal_poly_1d(s1_angle, window_size=window_size_smooth2, poly_degree=poly_degree, eval_index=-3)

    valid_start = min(window_size_smooth2, len(x_values))
    plot_frames = frame_ids[valid_start:]
    raw_plot = raw_unwrapped[valid_start:]
    s1_plot = s1_angle[valid_start:]
    s2_plot = s2_del_angle[valid_start:]

    ref_s1, rms_s1 = compute_linear_fit_and_rms(plot_frames, s1_plot)
    ref_s2, rms_s2 = compute_linear_fit_and_rms(plot_frames, s2_plot)

    output_dir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(12, 7), dpi=dpi)
    ax.plot(plot_frames, raw_plot, color=RAW_ANGLE_COLOR, linewidth=2.5, linestyle="-", alpha=0.85, label="Raw Angle (Model)", zorder=12)

    ax.plot(plot_frames, s1_plot, color=LINEAR_COLOR, linewidth=2.3, linestyle="-", label=f"Smooth 1 Delayed [0, 1] (W1={window_size}, index=-3) - RMS: {rms_s1:.2f}°", zorder=10)
    ax.plot(plot_frames, ref_s1, color=LINEAR_COLOR, linewidth=1.6, linestyle="--", alpha=0.55, label="Poly Fit Bậc 1 (Ref Smooth 1 Delayed)", zorder=4)

    ax.plot(plot_frames, s2_plot, color=SMOOTH2_COLOR, linewidth=2.3, linestyle="-", label=f"Smooth 2 Delayed (W2={window_size_smooth2}, index=-3) - RMS: {rms_s2:.2f}°", zorder=9)
    ax.plot(plot_frames, ref_s2, color=SMOOTH2_COLOR, linewidth=1.6, linestyle="--", alpha=0.55, label="Poly Fit Bậc 1 (Ref Smooth 2 Delayed)", zorder=3)

    ax.set_title(
        f"Heading Angle Comparison: Smooth 1 Delayed vs Smooth 2 Delayed (index=-3)\nFile: {csv_path.name} | Frames {int(frame_ids[0])}-{int(frame_ids[-1])} | W1={window_size}, W2={window_size_smooth2}, Degree={poly_degree}",
        fontsize=12,
        fontweight="bold"
    )
    ax.set_xlabel("Frame ID", fontweight="bold")
    ax.set_ylabel("Angle (Degrees)", fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.legend(loc="best", fontsize=9)
    baseline.set_robust_angle_limits(ax, [raw_plot, s1_plot, ref_s1, s2_plot, ref_s2])
    fig.tight_layout()

    angle_path = output_dir / f"{csv_path.stem}_smooth1_vs_smooth2_delayed_angle_w{window_size}.png"
    fig.savefig(angle_path, dpi=dpi, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)

    print(f"[SUCCESS-S1-VS-S2-DEL] {csv_path.name} | Smooth 1 Delayed RMS: {rms_s1:.2f}° | Smooth 2 Delayed RMS: {rms_s2:.2f}°")
    return {
        "file": csv_path.name,
        "rms_smooth1_delayed": rms_s1,
        "rms_smooth2_delayed": rms_s2,
    }


# =========================================================================
# 3. Chế độ: So sánh kích thước cửa sổ W = 18 vs W = 15 (Delayed [0, 1], index = -3)
# =========================================================================
def run_compare_window_18_15(df, csv_path: Path, output_dir: Path, poly_degree: int = 2, buffer_frames: int = 10, seed: int = 42, dpi: int = 150):
    angle_column = baseline.find_angle_column(df)
    segment = baseline.find_full_pass_moving_segment(
        df, buffer_frames=buffer_frames, seed=seed, min_speed=DEFAULT_MIN_SPEED, min_block_length=DEFAULT_MIN_BLOCK_LENGTH
    )
    if len(segment) <= 18:
        raise ValueError(f"Số mẫu ({len(segment)}) nhỏ hơn W=18")

    x_values = segment["x_center"].to_numpy(dtype=float)
    y_values = segment["y_center"].to_numpy(dtype=float)
    raw_angles = segment[angle_column].to_numpy(dtype=float)
    frame_ids = segment["frame_id"].to_numpy(dtype=float) if "frame_id" in segment.columns else np.arange(len(segment), dtype=float)
    raw_unwrapped = baseline.unwrap_finite_degrees(raw_angles)

    res_w18 = calculate_tangent_series(x_values, y_values, raw_unwrapped, window_size=18, poly_degree=poly_degree, weight_mode="linear_0_to_1", eval_index=-3)
    res_w15 = calculate_tangent_series(x_values, y_values, raw_unwrapped, window_size=15, poly_degree=poly_degree, weight_mode="linear_0_to_1", eval_index=-3)

    valid_start = 18
    plot_frames = frame_ids[valid_start:]
    raw_plot = raw_unwrapped[valid_start:]
    w18_plot = res_w18["tangent_angle"][valid_start:]
    w15_plot = res_w15["tangent_angle"][valid_start:]

    ref_w18, rms_w18 = compute_linear_fit_and_rms(plot_frames, w18_plot)
    ref_w15, rms_w15 = compute_linear_fit_and_rms(plot_frames, w15_plot)

    output_dir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(12, 7), dpi=dpi)
    ax.plot(plot_frames, raw_plot, color=RAW_ANGLE_COLOR, linewidth=2.5, linestyle="-", alpha=0.85, label="Raw Angle (Model)", zorder=12)

    ax.plot(plot_frames, w18_plot, color=LINEAR_COLOR, linewidth=2.3, linestyle="-", label=f"Delayed Tangent [0, 1] (W=18, index=-3) - RMS: {rms_w18:.2f}°", zorder=10)
    ax.plot(plot_frames, ref_w18, color=LINEAR_COLOR, linewidth=1.6, linestyle="--", alpha=0.55, label="Poly Fit Bậc 1 (Ref W=18)", zorder=4)

    ax.plot(plot_frames, w15_plot, color=PURPLE_COLOR, linewidth=2.3, linestyle="-", label=f"Delayed Tangent [0, 1] (W=15, index=-3) - RMS: {rms_w15:.2f}°", zorder=9)
    ax.plot(plot_frames, ref_w15, color=PURPLE_COLOR, linewidth=1.6, linestyle="--", alpha=0.55, label="Poly Fit Bậc 1 (Ref W=15)", zorder=3)

    ax.set_title(
        f"Heading Angle Comparison: Window Size W=18 vs W=15 (Delayed [0, 1], index=-3)\nFile: {csv_path.name} | Frames {int(frame_ids[0])}-{int(frame_ids[-1])} | Degree={poly_degree}",
        fontsize=12,
        fontweight="bold"
    )
    ax.set_xlabel("Frame ID", fontweight="bold")
    ax.set_ylabel("Angle (Degrees)", fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.legend(loc="best", fontsize=9)
    baseline.set_robust_angle_limits(ax, [raw_plot, w18_plot, ref_w18, w15_plot, ref_w15])
    fig.tight_layout()

    angle_path = output_dir / f"{csv_path.stem}_window_18_vs_15_angle.png"
    fig.savefig(angle_path, dpi=dpi, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)

    print(f"[SUCCESS-W18-VS-W15] {csv_path.name} | W=18 RMS: {rms_w18:.2f}° | W=15 RMS: {rms_w15:.2f}°")
    return {
        "file": csv_path.name,
        "rms_w18": rms_w18,
        "rms_w15": rms_w15,
    }


# =========================================================================
# 4. Chế độ: So sánh các mức delay (-2, -3, -4) trên Linear Weight [0, 1] (W = 18)
# =========================================================================
def run_compare_delays_mode(df, csv_path: Path, output_dir: Path, window_size: int = 18, poly_degree: int = 2, buffer_frames: int = 10, seed: int = 42, dpi: int = 150):
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

    # Tính 3 mức delay: index = -2, -3, -4
    res_m2 = calculate_tangent_series(x_values, y_values, raw_unwrapped, window_size, poly_degree, weight_mode="linear_0_to_1", eval_index=-2)
    res_m3 = calculate_tangent_series(x_values, y_values, raw_unwrapped, window_size, poly_degree, weight_mode="linear_0_to_1", eval_index=-3)
    res_m4 = calculate_tangent_series(x_values, y_values, raw_unwrapped, window_size, poly_degree, weight_mode="linear_0_to_1", eval_index=-4)

    valid_start = min(window_size, len(x_values))
    plot_frames = frame_ids[valid_start:]
    raw_plot = raw_unwrapped[valid_start:]
    m2_plot = res_m2["tangent_angle"][valid_start:]
    m3_plot = res_m3["tangent_angle"][valid_start:]
    m4_plot = res_m4["tangent_angle"][valid_start:]

    ref_m2, rms_m2 = compute_linear_fit_and_rms(plot_frames, m2_plot)
    ref_m3, rms_m3 = compute_linear_fit_and_rms(plot_frames, m3_plot)
    ref_m4, rms_m4 = compute_linear_fit_and_rms(plot_frames, m4_plot)

    output_dir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(12, 7), dpi=dpi)
    ax.plot(plot_frames, raw_plot, color=RAW_ANGLE_COLOR, linewidth=2.5, linestyle="-", alpha=0.85, label="Raw Angle (Model)", zorder=12)

    # Delay -2 (Xanh dương)
    ax.plot(plot_frames, m2_plot, color=UNIFORM_COLOR, linewidth=2.3, linestyle="-", label=f"Delayed Tangent (index=-2) - RMS: {rms_m2:.2f}°", zorder=10)
    ax.plot(plot_frames, ref_m2, color=UNIFORM_COLOR, linewidth=1.6, linestyle="--", alpha=0.55, label="Poly Fit Bậc 1 (Ref Delay -2)", zorder=5)

    # Delay -3 (Cam)
    ax.plot(plot_frames, m3_plot, color=LINEAR_COLOR, linewidth=2.3, linestyle="-", label=f"Delayed Tangent (index=-3) - RMS: {rms_m3:.2f}°", zorder=9)
    ax.plot(plot_frames, ref_m3, color=LINEAR_COLOR, linewidth=1.6, linestyle="--", alpha=0.55, label="Poly Fit Bậc 1 (Ref Delay -3)", zorder=4)

    # Delay -4 (Xanh lá)
    ax.plot(plot_frames, m4_plot, color=SMOOTH2_COLOR, linewidth=2.3, linestyle="-", label=f"Delayed Tangent (index=-4) - RMS: {rms_m4:.2f}°", zorder=8)
    ax.plot(plot_frames, ref_m4, color=SMOOTH2_COLOR, linewidth=1.6, linestyle="--", alpha=0.55, label="Poly Fit Bậc 1 (Ref Delay -4)", zorder=3)

    ax.set_title(
        f"Heading Angle Comparison: Delay Levels (index = -2, -3, -4) with Linear Weight [0, 1]\nFile: {csv_path.name} | Frames {int(frame_ids[0])}-{int(frame_ids[-1])} | W={window_size}, Degree={poly_degree}",
        fontsize=12,
        fontweight="bold"
    )
    ax.set_xlabel("Frame ID", fontweight="bold")
    ax.set_ylabel("Angle (Degrees)", fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.legend(loc="best", fontsize=9)
    baseline.set_robust_angle_limits(ax, [raw_plot, m2_plot, ref_m2, m3_plot, ref_m3, m4_plot, ref_m4])
    fig.tight_layout()

    angle_path = output_dir / f"{csv_path.stem}_delay_levels_angle_w{window_size}.png"
    fig.savefig(angle_path, dpi=dpi, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)

    print(f"[SUCCESS-DELAYS] {csv_path.name} | -2 RMS: {rms_m2:.2f}° | -3 RMS: {rms_m3:.2f}° | -4 RMS: {rms_m4:.2f}°")
    return {
        "file": csv_path.name,
        "rms_delay_m2": rms_m2,
        "rms_delay_m3": rms_m3,
        "rms_delay_m4": rms_m4,
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Unified Polynomial Tangent Comparison Tool - 19/08/2026")
    parser.add_argument("input_path", type=Path, help="CSV hoặc thư mục benchmark")
    parser.add_argument("--mode", type=str, default="all",
                        choices=["compare_uniform_linear_delayed", "compare_smooth1_smooth2_delayed", "compare_window_18_15", "compare_delays", "all"],
                        help="Chế độ chạy")
    parser.add_argument("--window-size", type=int, default=DEFAULT_WINDOW_SIZE, help=f"W (mặc định: {DEFAULT_WINDOW_SIZE})")
    parser.add_argument("--poly-degree", type=int, default=DEFAULT_POLY_DEGREE, help=f"Bậc đa thức (mặc định: {DEFAULT_POLY_DEGREE})")
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

    base_dir = args.input_path if args.input_path.is_dir() else args.input_path.parent

    print("=" * 80)
    print(f"[INFO] Files: {len(csv_files)} | Mode: {args.mode} | W = {args.window_size} | Degree = {args.poly_degree}")
    print("=" * 80)

    res_uni_lin = []
    res_s1_s2 = []
    res_w18_w15 = []
    res_delays = []

    for csv_file in csv_files:
        df = baseline.load_valid_dataframe(csv_file)

        if args.mode in ("compare_uniform_linear_delayed", "all"):
            out_dir = base_dir / "uniform_vs_linear_delayed"
            r = run_compare_uniform_linear_delayed(df, csv_file, out_dir, args.window_size, args.poly_degree, args.buffer_frames, args.seed, args.dpi)
            if r:
                res_uni_lin.append(r)

        if args.mode in ("compare_smooth1_smooth2_delayed", "all"):
            out_dir = base_dir / "smooth1_vs_smooth2_delayed"
            r = run_compare_smooth1_smooth2_delayed(df, csv_file, out_dir, args.window_size, args.poly_degree, args.buffer_frames, args.seed, args.dpi)
            if r:
                res_s1_s2.append(r)

        if args.mode in ("compare_window_18_15", "all"):
            out_dir = base_dir / "window_18_vs_15_comparison"
            r = run_compare_window_18_15(df, csv_file, out_dir, args.poly_degree, args.buffer_frames, args.seed, args.dpi)
            if r:
                res_w18_w15.append(r)

        if args.mode in ("compare_delays", "all"):
            out_dir = base_dir / "delay_levels_comparison"
            r = run_compare_delays_mode(df, csv_file, out_dir, args.window_size, args.poly_degree, args.buffer_frames, args.seed, args.dpi)
            if r:
                res_delays.append(r)

    # In các bảng tổng kết kèm hàng Trung bình (Average)
    if res_uni_lin:
        avg_uni = np.mean([r['rms_uniform_delayed'] for r in res_uni_lin])
        avg_lin = np.mean([r['rms_linear_delayed'] for r in res_uni_lin])
        print("\n" + "=" * 80)
        print("[SUMMARY 1] SO SÁNH RMS: DELAYED UNIFORM VS DELAYED LINEAR [0, 1] (index = -3):")
        print(f"{'Tập Benchmark':<18} | {'Delayed Uniform (-3)':<24} | {'Delayed Linear [0, 1] (-3)':<26}")
        print("-" * 80)
        for r in res_uni_lin:
            print(f"{r['file']:<18} | {r['rms_uniform_delayed']:>22.2f}° | {r['rms_linear_delayed']:>24.2f}°")
        print("-" * 80)
        print(f"{'Trung bình (Mean)':<18} | {avg_uni:>22.2f}° | {avg_lin:>24.2f}°")
        print("=" * 80)

    if res_s1_s2:
        avg_s1 = np.mean([r['rms_smooth1_delayed'] for r in res_s1_s2])
        avg_s2 = np.mean([r['rms_smooth2_delayed'] for r in res_s1_s2])
        print("\n" + "=" * 80)
        print("[SUMMARY 2] SO SÁNH RMS: SMOOTH 1 DELAYED VS SMOOTH 2 DELAYED (index = -3):")
        print(f"{'Tập Benchmark':<18} | {'Smooth 1 Delayed (W1=18)':<26} | {'Smooth 2 Delayed (W2=36)':<26}")
        print("-" * 80)
        for r in res_s1_s2:
            print(f"{r['file']:<18} | {r['rms_smooth1_delayed']:>24.2f}° | {r['rms_smooth2_delayed']:>24.2f}°")
        print("-" * 80)
        print(f"{'Trung bình (Mean)':<18} | {avg_s1:>24.2f}° | {avg_s2:>24.2f}°")
        print("=" * 80)

    if res_w18_w15:
        avg_w18 = np.mean([r['rms_w18'] for r in res_w18_w15])
        avg_w15 = np.mean([r['rms_w15'] for r in res_w18_w15])
        print("\n" + "=" * 80)
        print("[SUMMARY 3] SO SÁNH RMS: CỬA SỔ W = 18 VS W = 15 (DELAYED [0, 1], index = -3):")
        print(f"{'Tập Benchmark':<18} | {'Delayed W = 18':<22} | {'Delayed W = 15':<22}")
        print("-" * 80)
        for r in res_w18_w15:
            print(f"{r['file']:<18} | {r['rms_w18']:>20.2f}° | {r['rms_w15']:>20.2f}°")
        print("-" * 80)
        print(f"{'Trung bình (Mean)':<18} | {avg_w18:>20.2f}° | {avg_w15:>20.2f}°")
        print("=" * 80)

    if res_delays:
        avg_m2 = np.mean([r['rms_delay_m2'] for r in res_delays])
        avg_m3 = np.mean([r['rms_delay_m3'] for r in res_delays])
        avg_m4 = np.mean([r['rms_delay_m4'] for r in res_delays])
        print("\n" + "=" * 80)
        print("[SUMMARY 4] SO SÁNH RMS: CÁC MỨC DELAY (-2, -3, -4) TRÊN LINEAR [0, 1] (W = 18):")
        print(f"{'Tập Benchmark':<18} | {'Delay (-2)':<18} | {'Delay (-3)':<18} | {'Delay (-4)':<18}")
        print("-" * 80)
        for r in res_delays:
            print(f"{r['file']:<18} | {r['rms_delay_m2']:>16.2f}° | {r['rms_delay_m3']:>16.2f}° | {r['rms_delay_m4']:>16.2f}°")
        print("-" * 80)
        print(f"{'Trung bình (Mean)':<18} | {avg_m2:>16.2f}° | {avg_m3:>16.2f}° | {avg_m4:>16.2f}°")
        print("=" * 80)

    print("\n[DONE] Hoàn thành xử lý và tạo biểu đồ cho toàn bộ các chế độ!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())