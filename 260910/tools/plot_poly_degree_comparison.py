"""
plot_poly_degree_comparison.py
──────────────────────────────
Công cụ thực nghiệm & trực quan hóa so sánh toàn diện:
1. Dữ liệu thô chưa làm mượt:
   - Raw Model Angle
   - Raw Trajectory Angle (tính từ sai phân vị trí delta_x, delta_y liên tiếp)
2. Dữ liệu làm mượt Đa thức Bậc 1 (Tất cả - Degree 1):
   - Model Smooth (Deg 1)
   - Smooth 2 Delayed Tangent (Deg 1)
   - Fused Angle (Deg 1)
3. Dữ liệu làm mượt Đa thức Bậc 2 (Tất cả - Degree 2):
   - Model Smooth (Deg 2)
   - Smooth 2 Delayed Tangent (Deg 2)
   - Fused Angle (Deg 2)

Lệnh chạy:
    python 260821/tools/plot_poly_degree_comparison.py 260821/benchmark --K 3.0
    python 260821/tools/plot_poly_degree_comparison.py 260821/benchmark/0_degree.csv
"""

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:
    import plot_poly_tangent_angle_comparison as baseline
except ImportError:
    from tools import plot_poly_tangent_angle_comparison as baseline


DEFAULT_WINDOW_SIZE = 18
DEFAULT_WINDOW_SIZE_S2 = 18
DEFAULT_EVAL_INDEX = -4
DEFAULT_K = 3.0
DEFAULT_BUFFER_FRAMES = 10
DEFAULT_SEED = 42
DEFAULT_MIN_SPEED = 1.5
DEFAULT_MIN_BLOCK_LENGTH = 30
DEFAULT_VECTOR_EPSILON = 1e-5
DEFAULT_DPI = 150

# Bảng màu chuẩn
COLOR_RAW_MODEL = "#8b0000"         # Đỏ đậm (Raw Model)
COLOR_RAW_TRAJ = "#7f7f7f"          # Xám đậm (Raw Trajectory)
COLOR_MODEL_DEG1 = "#1f77b4"        # Xanh dương (Model Smooth Deg 1)
COLOR_MODEL_DEG2 = "#00008b"        # Xanh dương đậm (Model Smooth Deg 2)
COLOR_TANGENT_DEG1 = "#2ca02c"      # Xanh lá (Tangent Smooth Deg 1)
COLOR_TANGENT_DEG2 = "#006400"      # Xanh lá đậm (Tangent Smooth Deg 2)
COLOR_FUSED_DEG1 = "#ff7f0e"        # Cam sẫm (Fused Angle Deg 1)
COLOR_FUSED_DEG2 = "#d62728"        # Đỏ tươi / Đỏ ruby (Fused Angle Deg 2)
COLOR_REF_LINE = "#000000"          # Đen chấm gạch (Ref Ground Truth)


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def fit_causal_poly_tangent(
    x_values: np.ndarray,
    y_values: np.ndarray,
    window_size: int,
    poly_degree: int,
    eval_index: int = 0,
):
    """
    Fit đa thức causal 2D trên chuỗi tọa độ (x, y) và tính đạo hàm tiếp tuyến tại eval_index.
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

        coefficients_x = np.polyfit(time_normalized, x_window, deg=current_degree)
        coefficients_y = np.polyfit(time_normalized, y_window, deg=current_degree)

        target_idx_in_window = max(0, window_length - 1 + eval_index)
        if window_length > 1:
            t_eval = (target_idx_in_window - (window_length - 1)) / (window_length - 1)
        else:
            t_eval = 0.0

        smooth_x[index] = float(np.polyval(coefficients_x, t_eval))
        smooth_y[index] = float(np.polyval(coefficients_y, t_eval))

        if current_degree >= 1:
            tangent_x[index] = float(np.polyval(np.polyder(coefficients_x), t_eval))
            tangent_y[index] = float(np.polyval(np.polyder(coefficients_y), t_eval))

    return smooth_x, smooth_y, tangent_x, tangent_y


def fit_causal_poly_1d(
    values: np.ndarray,
    window_size: int,
    poly_degree: int,
    eval_index: int = 0,
) -> np.ndarray:
    """
    Fit đa thức causal 1D trên chuỗi giá trị và evaluate tại eval_index.
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


def calculate_tangent_series(
    x_values: np.ndarray,
    y_values: np.ndarray,
    raw_unwrapped: np.ndarray,
    window_size: int,
    poly_degree: int,
    eval_index: int = 0,
    vector_epsilon: float = DEFAULT_VECTOR_EPSILON,
):
    """
    Tính chuỗi góc tiếp tuyến và vận tốc từ fit đa thức tọa độ 2D.
    """
    smooth_x, smooth_y, tangent_x, tangent_y = fit_causal_poly_tangent(
        x_values=x_values,
        y_values=y_values,
        window_size=window_size,
        poly_degree=poly_degree,
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

    speed = tangent_magnitude / max(1, window_size - 1)

    return {
        "smooth_x": smooth_x,
        "smooth_y": smooth_y,
        "tangent_angle": tangent_aligned,
        "speed": speed,
    }


def compute_raw_trajectory_angle(x_values: np.ndarray, y_values: np.ndarray, raw_unwrapped: np.ndarray):
    """
    Tính góc quỹ đạo thô từ sai phân vị trí delta_x, delta_y giữa 2 khung hình liên tiếp.
    """
    dx = np.diff(x_values, prepend=x_values[0])
    dy = np.diff(y_values, prepend=y_values[0])
    raw_traj = np.degrees(np.arctan2(-dy, dx))
    speed = np.hypot(dx, dy)
    raw_traj[speed < 0.5] = np.nan
    raw_traj_unwrapped = baseline.unwrap_finite_degrees(raw_traj)
    raw_traj_aligned = baseline.align_orientation_phase(raw_traj_unwrapped, raw_unwrapped, period_degrees=180.0)
    return raw_traj_aligned


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


def run_degree_comparison_single_file(
    csv_path: Path,
    output_dir: Path,
    window_size: int = DEFAULT_WINDOW_SIZE,
    window_size_s2: int = DEFAULT_WINDOW_SIZE_S2,
    eval_index: int = DEFAULT_EVAL_INDEX,
    K: float = DEFAULT_K,
    buffer_frames: int = DEFAULT_BUFFER_FRAMES,
    seed: int = DEFAULT_SEED,
    dpi: int = DEFAULT_DPI,
):
    df = baseline.load_valid_dataframe(csv_path)
    angle_column = baseline.find_angle_column(df)
    segment = baseline.find_full_pass_moving_segment(
        df, buffer_frames=buffer_frames, seed=seed, min_speed=DEFAULT_MIN_SPEED, min_block_length=DEFAULT_MIN_BLOCK_LENGTH
    )
    if len(segment) <= window_size_s2:
        raise ValueError(f"Số mẫu ({len(segment)}) nhỏ hơn W2={window_size_s2}")

    x_values = segment["x_center"].to_numpy(dtype=float)
    y_values = segment["y_center"].to_numpy(dtype=float)
    raw_angles = segment[angle_column].to_numpy(dtype=float)
    frame_ids = segment["frame_id"].to_numpy(dtype=float) if "frame_id" in segment.columns else np.arange(len(segment), dtype=float)
    raw_unwrapped = baseline.unwrap_finite_degrees(raw_angles)

    # 1. Dữ liệu thô
    raw_model = raw_unwrapped
    raw_traj = compute_raw_trajectory_angle(x_values, y_values, raw_unwrapped)

    # 2. Xử lý Bậc 1 (Degree 1)
    # - Model Smooth Deg 1
    model_s1_deg1 = fit_causal_poly_1d(raw_unwrapped, window_size=window_size, poly_degree=1, eval_index=eval_index)
    # - Tangent Smooth Deg 1
    res_tangent_deg1 = calculate_tangent_series(x_values, y_values, raw_unwrapped, window_size=window_size, poly_degree=1, eval_index=eval_index)
    s1_tangent_deg1 = res_tangent_deg1["tangent_angle"]
    s2_tangent_deg1 = fit_causal_poly_1d(s1_tangent_deg1, window_size=window_size_s2, poly_degree=1, eval_index=eval_index)
    # - Fused Deg 1
    speed_deg1 = res_tangent_deg1["speed"]
    weight_x_deg1 = np.where(np.isfinite(speed_deg1), K / (K + speed_deg1), 1.0)
    s2_deg1_aligned = baseline.align_orientation_phase(s2_tangent_deg1, model_s1_deg1, period_degrees=180.0)
    fused_deg1 = weight_x_deg1 * model_s1_deg1 + (1.0 - weight_x_deg1) * s2_deg1_aligned

    # 3. Xử lý Bậc 2 (Degree 2)
    # - Model Smooth Deg 2
    model_s1_deg2 = fit_causal_poly_1d(raw_unwrapped, window_size=window_size, poly_degree=2, eval_index=eval_index)
    # - Tangent Smooth Deg 2
    res_tangent_deg2 = calculate_tangent_series(x_values, y_values, raw_unwrapped, window_size=window_size, poly_degree=2, eval_index=eval_index)
    s1_tangent_deg2 = res_tangent_deg2["tangent_angle"]
    s2_tangent_deg2 = fit_causal_poly_1d(s1_tangent_deg2, window_size=window_size_s2, poly_degree=2, eval_index=eval_index)
    # - Fused Deg 2
    speed_deg2 = res_tangent_deg2["speed"]
    weight_x_deg2 = np.where(np.isfinite(speed_deg2), K / (K + speed_deg2), 1.0)
    s2_deg2_aligned = baseline.align_orientation_phase(s2_tangent_deg2, model_s1_deg2, period_degrees=180.0)
    fused_deg2 = weight_x_deg2 * model_s1_deg2 + (1.0 - weight_x_deg2) * s2_deg2_aligned

    # Cắt phần khởi động cửa sổ trượt W2
    valid_start = min(window_size_s2, len(raw_unwrapped))
    plot_frames = frame_ids[valid_start:]
    plot_raw_model = raw_model[valid_start:]
    plot_raw_traj = raw_traj[valid_start:]
    plot_model_deg1 = model_s1_deg1[valid_start:]
    plot_model_deg2 = model_s1_deg2[valid_start:]
    plot_tangent_deg1 = s2_tangent_deg1[valid_start:]
    plot_tangent_deg2 = s2_tangent_deg2[valid_start:]
    plot_fused_deg1 = fused_deg1[valid_start:]
    plot_fused_deg2 = fused_deg2[valid_start:]

    # Tính RMS so với Ground Truth Reference (Poly Fit bậc 1 của Frame)
    ref_raw, rms_raw = compute_linear_fit_and_rms(plot_frames, plot_raw_model)
    ref_traj, rms_traj = compute_linear_fit_and_rms(plot_frames, plot_raw_traj)
    ref_model_deg1, rms_model_deg1 = compute_linear_fit_and_rms(plot_frames, plot_model_deg1)
    ref_model_deg2, rms_model_deg2 = compute_linear_fit_and_rms(plot_frames, plot_model_deg2)
    ref_tangent_deg1, rms_tangent_deg1 = compute_linear_fit_and_rms(plot_frames, plot_tangent_deg1)
    ref_tangent_deg2, rms_tangent_deg2 = compute_linear_fit_and_rms(plot_frames, plot_tangent_deg2)
    ref_fused_deg1, rms_fused_deg1 = compute_linear_fit_and_rms(plot_frames, plot_fused_deg1)
    ref_fused_deg2, rms_fused_deg2 = compute_linear_fit_and_rms(plot_frames, plot_fused_deg2)

    output_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------
    # BIỂU ĐỒ 1: SO SÁNH TỔNG THỂ (ALL SIGNALS COMPARISON)
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(14, 8), dpi=dpi)
    ax.plot(plot_frames, plot_raw_model, color=COLOR_RAW_MODEL, linewidth=2.2, linestyle="-", alpha=0.7, label=f"Raw Model Angle - RMS: {rms_raw:.2f}°", zorder=12)
    if np.count_nonzero(np.isfinite(plot_raw_traj)) > 5:
        ax.plot(plot_frames, plot_raw_traj, color=COLOR_RAW_TRAJ, linewidth=1.5, linestyle=":", alpha=0.5, label=f"Raw Trajectory Tangent - RMS: {rms_traj:.2f}°", zorder=8)

    ax.plot(plot_frames, plot_model_deg1, color=COLOR_MODEL_DEG1, linewidth=2.0, linestyle="--", label=f"Model Smooth (Bậc 1) - RMS: {rms_model_deg1:.2f}°", zorder=9)
    ax.plot(plot_frames, plot_model_deg2, color=COLOR_MODEL_DEG2, linewidth=2.0, linestyle="-", label=f"Model Smooth (Bậc 2) - RMS: {rms_model_deg2:.2f}°", zorder=10)

    ax.plot(plot_frames, plot_tangent_deg1, color=COLOR_TANGENT_DEG1, linewidth=2.0, linestyle="--", label=f"Smooth 2 Tangent (Bậc 1) - RMS: {rms_tangent_deg1:.2f}°", zorder=7)
    ax.plot(plot_frames, plot_tangent_deg2, color=COLOR_TANGENT_DEG2, linewidth=2.0, linestyle="-", label=f"Smooth 2 Tangent (Bậc 2) - RMS: {rms_tangent_deg2:.2f}°", zorder=8)

    ax.plot(plot_frames, plot_fused_deg1, color=COLOR_FUSED_DEG1, linewidth=2.5, linestyle="--", label=f"Fused Angle (Bậc 1, K={K}) - RMS: {rms_fused_deg1:.2f}°", zorder=14)
    ax.plot(plot_frames, plot_fused_deg2, color=COLOR_FUSED_DEG2, linewidth=2.5, linestyle="-", label=f"Fused Angle (Bậc 2, K={K}) - RMS: {rms_fused_deg2:.2f}°", zorder=15)

    ax.plot(plot_frames, ref_raw, color=COLOR_REF_LINE, linewidth=1.5, linestyle="-.", alpha=0.4, label="Ground Truth Reference (Poly Fit Bậc 1)", zorder=2)

    ax.set_title(
        f"Heading Angle Comparison: Raw vs Polynomial Degree 1 vs Degree 2 (All Signals)\nFile: {csv_path.name} | Frames {int(frame_ids[0])}-{int(frame_ids[-1])} | W1={window_size}, W2={window_size_s2}, index={eval_index}, K={K}",
        fontsize=12,
        fontweight="bold"
    )
    ax.set_xlabel("Frame ID", fontweight="bold")
    ax.set_ylabel("Angle (Degrees)", fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.legend(loc="best", fontsize=8.5, framealpha=0.9)
    baseline.set_robust_angle_limits(ax, [plot_raw_model, plot_model_deg1, plot_model_deg2, plot_tangent_deg1, plot_tangent_deg2, plot_fused_deg1, plot_fused_deg2])
    fig.tight_layout()

    out_all_path = output_dir / f"{csv_path.stem}_all_signals_degree_comparison.png"
    fig.savefig(out_all_path, dpi=dpi, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)

    # -------------------------------------------------------------
    # BIỂU ĐỒ 2: SO SÁNH TRỰC DIỆN FUSED ANGLE BẬC 1 VS BẬC 2
    # -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(13, 7), dpi=dpi)
    ax.plot(plot_frames, plot_raw_model, color=COLOR_RAW_MODEL, linewidth=2.0, linestyle="-", alpha=0.6, label=f"Raw Model Angle - RMS: {rms_raw:.2f}°", zorder=10)
    ax.plot(plot_frames, plot_fused_deg1, color=COLOR_FUSED_DEG1, linewidth=2.5, linestyle="-", label=f"Fused Angle (Bậc 1 Toàn Bộ) - RMS: {rms_fused_deg1:.2f}°", zorder=13)
    ax.plot(plot_frames, plot_fused_deg2, color=COLOR_FUSED_DEG2, linewidth=2.5, linestyle="-", label=f"Fused Angle (Bậc 2 Toàn Bộ) - RMS: {rms_fused_deg2:.2f}°", zorder=14)
    ax.plot(plot_frames, ref_raw, color=COLOR_REF_LINE, linewidth=1.6, linestyle="--", alpha=0.5, label="Ground Truth Ref Line", zorder=4)

    ax.set_title(
        f"Fused Angle Direct Comparison: Degree 1 vs Degree 2\nFile: {csv_path.name} | Frames {int(frame_ids[0])}-{int(frame_ids[-1])} | W1={window_size}, W2={window_size_s2}, index={eval_index}, K={K}",
        fontsize=12,
        fontweight="bold"
    )
    ax.set_xlabel("Frame ID", fontweight="bold")
    ax.set_ylabel("Angle (Degrees)", fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.legend(loc="best", fontsize=9.5, framealpha=0.9)
    baseline.set_robust_angle_limits(ax, [plot_raw_model, plot_fused_deg1, plot_fused_deg2, ref_raw])
    fig.tight_layout()

    out_fused_path = output_dir / f"{csv_path.stem}_fused_deg1_vs_deg2.png"
    fig.savefig(out_fused_path, dpi=dpi, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)

    # Nếu là file quỹ đạo vòng tròn (turn), xuất thêm biểu đồ phóng to 100 frame
    zoom_path = None
    if "turn" in csv_path.stem.lower() and len(plot_frames) >= 120:
        zoom_start = len(plot_frames) // 3
        zoom_end = min(len(plot_frames), zoom_start + 100)
        z_frames = plot_frames[zoom_start:zoom_end]
        z_raw = plot_raw_model[zoom_start:zoom_end]
        z_fused1 = plot_fused_deg1[zoom_start:zoom_end]
        z_fused2 = plot_fused_deg2[zoom_start:zoom_end]
        z_ref = ref_raw[zoom_start:zoom_end]

        fig, ax = plt.subplots(figsize=(12, 6), dpi=dpi)
        ax.plot(z_frames, z_raw, color=COLOR_RAW_MODEL, linewidth=2.0, linestyle="-", alpha=0.6, label="Raw Model Angle", zorder=10)
        ax.plot(z_frames, z_fused1, color=COLOR_FUSED_DEG1, linewidth=2.5, linestyle="-", label=f"Fused Angle Deg 1 (RMS: {rms_fused_deg1:.2f}°)", zorder=13)
        ax.plot(z_frames, z_fused2, color=COLOR_FUSED_DEG2, linewidth=2.5, linestyle="-", label=f"Fused Angle Deg 2 (RMS: {rms_fused_deg2:.2f}°)", zorder=14)
        ax.plot(z_frames, z_ref, color=COLOR_REF_LINE, linewidth=1.6, linestyle="--", alpha=0.5, label="Ground Truth Ref Line", zorder=4)

        ax.set_title(
            f"Zoom 100 Frames: Fused Angle Degree 1 vs Degree 2\nFile: {csv_path.name} | Frames {int(z_frames[0])}-{int(z_frames[-1])}",
            fontsize=12,
            fontweight="bold"
        )
        ax.set_xlabel("Frame ID", fontweight="bold")
        ax.set_ylabel("Angle (Degrees)", fontweight="bold")
        ax.grid(True, linestyle="--", alpha=0.6)
        ax.legend(loc="best", fontsize=9.5)
        baseline.set_robust_angle_limits(ax, [z_raw, z_fused1, z_fused2, z_ref])
        fig.tight_layout()

        zoom_path = output_dir / f"{csv_path.stem}_fused_deg1_vs_deg2_zoom100.png"
        fig.savefig(zoom_path, dpi=dpi, bbox_inches="tight", pad_inches=0.15)
        plt.close(fig)

    print(
        f"[SUCCESS] {csv_path.name} | Raw: {rms_raw:.2f}° | "
        f"Model S1 (Deg1: {rms_model_deg1:.2f}°, Deg2: {rms_model_deg2:.2f}°) | "
        f"Tangent S2 (Deg1: {rms_tangent_deg1:.2f}°, Deg2: {rms_tangent_deg2:.2f}°) | "
        f"Fused (Deg1: {rms_fused_deg1:.2f}°, Deg2: {rms_fused_deg2:.2f}°)"
    )

    return {
        "file": csv_path.name,
        "rms_raw": rms_raw,
        "rms_traj": rms_traj,
        "rms_model_deg1": rms_model_deg1,
        "rms_model_deg2": rms_model_deg2,
        "rms_tangent_deg1": rms_tangent_deg1,
        "rms_tangent_deg2": rms_tangent_deg2,
        "rms_fused_deg1": rms_fused_deg1,
        "rms_fused_deg2": rms_fused_deg2,
    }


def main():
    parser = argparse.ArgumentParser(description="So sánh Polynomial Bậc 1 vs Bậc 2 toàn bộ tín hiệu")
    parser.add_argument("target", type=str, help="Đường dẫn đến file CSV hoặc thư mục benchmark")
    parser.add_argument("--window-size", type=int, default=DEFAULT_WINDOW_SIZE, help="Cửa sổ trượt W1 (mặc định 18)")
    parser.add_argument("--window-size-s2", type=int, default=DEFAULT_WINDOW_SIZE_S2, help="Cửa sổ trượt W2 (mặc định 36)")
    parser.add_argument("--eval-index", type=int, default=DEFAULT_EVAL_INDEX, help="Chỉ số trễ đánh giá (mặc định -4)")
    parser.add_argument("--K", type=float, default=DEFAULT_K, help="Hệ số K thích ứng vận tốc (mặc định 3.0)")
    parser.add_argument("--buffer-frames", type=int, default=DEFAULT_BUFFER_FRAMES, help="Frame đệm biên (mặc định 10)")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Random seed (mặc định 42)")
    parser.add_argument("--dpi", type=int, default=DEFAULT_DPI, help="DPI ảnh xuất ra (mặc định 150)")
    parser.add_argument("--output-dir", type=str, default="", help="Thư mục xuất ảnh")

    args = parser.parse_args()
    target_path = Path(args.target)

    if target_path.is_file():
        csv_files = [target_path]
        output_dir = Path(args.output_dir) if args.output_dir else target_path.parent / "degree_1_vs_2_comparison"
    elif target_path.is_dir():
        csv_files = sorted(list(target_path.glob("*.csv")))
        output_dir = Path(args.output_dir) if args.output_dir else target_path / "degree_1_vs_2_comparison"
    else:
        raise FileNotFoundError(f"Không tìm thấy {target_path}")

    if not csv_files:
        print(f"Không tìm thấy file CSV nào tại {target_path}")
        return

    results = []
    for csv_file in csv_files:
        try:
            res = run_degree_comparison_single_file(
                csv_path=csv_file,
                output_dir=output_dir,
                window_size=args.window_size,
                window_size_s2=args.window_size_s2,
                eval_index=args.eval_index,
                K=args.K,
                buffer_frames=args.buffer_frames,
                seed=args.seed,
                dpi=args.dpi,
            )
            results.append(res)
        except Exception as exc:
            print(f"[ERROR] {csv_file.name}: {exc}")

    if not results:
        return

    df_res = pd.DataFrame(results)
    print("\n" + "=" * 120)
    print("BẢNG TỔNG HỢP SAI SỐ RMS: BẬC 1 VS BẬC 2 (TOÀN BỘ CÁC KHÂU)")
    print("=" * 120)
    print(df_res.to_string(index=False))

    # Tách nhóm góc benchmark cố định và nhóm quay vòng tròn (turn)
    benchmark_fixed = df_res[~df_res["file"].str.contains("turn", case=False, na=False)]
    benchmark_turn = df_res[df_res["file"].str.contains("turn", case=False, na=False)]

    if not benchmark_fixed.empty:
        print("\n" + "-" * 80)
        print("TRUNG BÌNH 6 TẬP GÓC BENCHMARK CỐ ĐỊNH:")
        print(f"- Raw Model RMS:             {benchmark_fixed['rms_raw'].mean():.2f}°")
        print(f"- Model Smooth (Bậc 1) RMS:  {benchmark_fixed['rms_model_deg1'].mean():.2f}°")
        print(f"- Model Smooth (Bậc 2) RMS:  {benchmark_fixed['rms_model_deg2'].mean():.2f}°")
        print(f"- Tangent Smooth 2 (Bậc 1):  {benchmark_fixed['rms_tangent_deg1'].mean():.2f}°")
        print(f"- Tangent Smooth 2 (Bậc 2):  {benchmark_fixed['rms_tangent_deg2'].mean():.2f}°")
        print(f"- Fused Angle (Bậc 1) RMS:   {benchmark_fixed['rms_fused_deg1'].mean():.2f}°")
        print(f"- Fused Angle (Bậc 2) RMS:   {benchmark_fixed['rms_fused_deg2'].mean():.2f}°")

    if not benchmark_turn.empty:
        print("\n" + "-" * 80)
        print("TRUNG BÌNH 3 TẬP QUỸ ĐẠO QUAY VÒNG (1turn, 2turn, 3turn):")
        print(f"- Raw Model RMS:             {benchmark_turn['rms_raw'].mean():.2f}°")
        print(f"- Model Smooth (Bậc 1) RMS:  {benchmark_turn['rms_model_deg1'].mean():.2f}°")
        print(f"- Model Smooth (Bậc 2) RMS:  {benchmark_turn['rms_model_deg2'].mean():.2f}°")
        print(f"- Tangent Smooth 2 (Bậc 1):  {benchmark_turn['rms_tangent_deg1'].mean():.2f}°")
        print(f"- Tangent Smooth 2 (Bậc 2):  {benchmark_turn['rms_tangent_deg2'].mean():.2f}°")
        print(f"- Fused Angle (Bậc 1) RMS:   {benchmark_turn['rms_fused_deg1'].mean():.2f}°")
        print(f"- Fused Angle (Bậc 2) RMS:   {benchmark_turn['rms_fused_deg2'].mean():.2f}°")
    print("=" * 120 + "\n")


if __name__ == "__main__":
    main()
