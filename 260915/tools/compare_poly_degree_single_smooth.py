"""
compare_poly_degree_single_smooth.py
────────────────────────────────────
Thực nghiệm so sánh độc lập Polynomial Bậc 1 vs Bậc 2 (1 lần smooth duy nhất - Single-pass smooth):
1. Cấu hình chuẩn hóa:
   - Window size: W = 18
   - Weight: Uniform
   - Evaluation index: index = -4
   - Số lần smooth: 1 lần duy nhất
   - K = 3.0
2. Hai nhánh thực nghiệm:
   - Nhánh 1: poly_degree = 1 (Bậc 1)
   - Nhánh 2: poly_degree = 2 (Bậc 2)
3. Các tín hiệu:
   - Model Angle: Raw Model vs Model Degree 1 vs Model Degree 2
   - Trajectory Angle: Trajectory Degree 1 vs Trajectory Degree 2 (fit 1 lần từ x, y)
   - Estimated Speed: sqrt(dx_dt^2 + dy_dt^2) / (W-1) từ chính đạo hàm quỹ đạo
   - Fused Angle: Fused Degree 1 vs Fused Degree 2
4. Xuất 3 biểu đồ riêng biệt cho mỗi dataset:
   - {dataset}_model_degree1_vs_degree2.png
   - {dataset}_trajectory_degree1_vs_degree2.png
   - {dataset}_fused_degree1_vs_degree2.png
   Thư mục: 260821/benchmark/poly_degree_single_smooth_comparison/

Lệnh chạy:
    python 260821/tools/compare_poly_degree_single_smooth.py 260821/benchmark --window-size 18 --eval-index -4 --K 3.0
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
DEFAULT_EVAL_INDEX = -4
DEFAULT_K = 3.0
DEFAULT_BUFFER_FRAMES = 10
DEFAULT_SEED = 42
DEFAULT_MIN_SPEED = 1.5
DEFAULT_MIN_BLOCK_LENGTH = 30
DEFAULT_VECTOR_EPSILON = 1e-5
DEFAULT_DPI = 150

# Bảng màu chuẩn
COLOR_RAW = "#8b0000"          # Đỏ đậm (Raw Model)
COLOR_DEG1 = "#1f77b4"         # Xanh dương (Bậc 1 - Degree 1)
COLOR_DEG2 = "#ff7f0e"         # Cam sẫm (Bậc 2 - Degree 2)
COLOR_REF = "#2ca02c"          # Xanh lá nét đứt (Ground Truth Ref)
COLOR_REF_SEC = "#7f7f7f"      # Xám nét đứt


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def smooth_1d_poly(
    values: np.ndarray,
    degree: int,
    window_size: int,
    eval_index: int = 0,
) -> np.ndarray:
    """
    Fit đa thức causal 1D trên chuỗi giá trị và đánh giá tại eval_index.
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
        current_degree = min(degree, len(valid_data) - 1)
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


def calculate_trajectory_tangent_single_pass(
    x_values: np.ndarray,
    y_values: np.ndarray,
    raw_model_unwrapped: np.ndarray,
    degree: int,
    window_size: int,
    eval_index: int = 0,
    vector_epsilon: float = DEFAULT_VECTOR_EPSILON,
):
    """
    Fit 1 lần duy nhất đa thức 2D trên (x, y) và tính đạo hàm tiếp tuyến tại eval_index.
    """
    sample_count = len(x_values)
    tangent_x = np.full(sample_count, np.nan, dtype=float)
    tangent_y = np.full(sample_count, np.nan, dtype=float)

    for index in range(sample_count):
        window_start = max(0, index - window_size + 1)
        window_end = index + 1
        x_window = x_values[window_start:window_end]
        y_window = y_values[window_start:window_end]
        window_length = len(x_window)
        current_degree = min(degree, window_length - 1)

        time_normalized = np.linspace(-1.0, 0.0, window_length)
        coefficients_x = np.polyfit(time_normalized, x_window, deg=current_degree)
        coefficients_y = np.polyfit(time_normalized, y_window, deg=current_degree)

        target_idx_in_window = max(0, window_length - 1 + eval_index)
        if window_length > 1:
            t_eval = (target_idx_in_window - (window_length - 1)) / (window_length - 1)
        else:
            t_eval = 0.0

        if current_degree >= 1:
            tangent_x[index] = float(np.polyval(np.polyder(coefficients_x), t_eval))
            tangent_y[index] = float(np.polyval(np.polyder(coefficients_y), t_eval))

    tangent_angles = np.degrees(np.arctan2(-tangent_y, tangent_x))
    tangent_magnitude = np.hypot(tangent_x, tangent_y)

    valid_start = min(window_size, len(x_values))
    sample_indices = np.arange(len(x_values))
    tangent_angles[
        (sample_indices < valid_start) | (tangent_magnitude <= vector_epsilon)
    ] = np.nan

    tangent_unwrapped = baseline.unwrap_finite_degrees(tangent_angles)
    tangent_aligned = baseline.align_orientation_phase(
        tangent_unwrapped, raw_model_unwrapped, period_degrees=180.0
    )

    speed = tangent_magnitude / max(1, window_size - 1)

    return {
        "tangent_angle": tangent_aligned,
        "speed": speed,
    }


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


def calculate_degree_branch(
    raw_model_unwrapped: np.ndarray,
    x_values: np.ndarray,
    y_values: np.ndarray,
    degree: int,
    window_size: int,
    eval_index: int,
    K: float,
):
    """
    Thực thi toàn bộ tính toán cho 1 nhánh bậc (degree 1 hoặc degree 2).
    """
    # 1. Góc Model Smooth (1 lần fit 1D)
    model_smooth = smooth_1d_poly(
        raw_model_unwrapped,
        degree=degree,
        window_size=window_size,
        eval_index=eval_index,
    )

    # 2. Góc Quỹ đạo Tangent (1 lần fit 2D) & Vận tốc
    res_traj = calculate_trajectory_tangent_single_pass(
        x_values=x_values,
        y_values=y_values,
        raw_model_unwrapped=raw_model_unwrapped,
        degree=degree,
        window_size=window_size,
        eval_index=eval_index,
    )
    traj_angle = res_traj["tangent_angle"]
    speed = res_traj["speed"]

    # 3. Hợp nhất Fused Angle
    weight_x = np.where(np.isfinite(speed), K / (K + speed), 1.0)
    traj_aligned = baseline.align_orientation_phase(traj_angle, model_smooth, period_degrees=180.0)
    fused_angle = weight_x * model_smooth + (1.0 - weight_x) * traj_aligned

    return {
        "model_smooth": model_smooth,
        "traj_angle": traj_aligned,
        "speed": speed,
        "weight_x": weight_x,
        "fused_angle": fused_angle,
    }


def plot_model_comparison(
    csv_stem: str,
    output_dir: Path,
    plot_frames: np.ndarray,
    plot_raw_model: np.ndarray,
    plot_model_deg1: np.ndarray,
    plot_model_deg2: np.ndarray,
    rms_raw: float,
    rms_deg1: float,
    rms_deg2: float,
    ref_raw: np.ndarray,
    ref_deg1: np.ndarray,
    ref_deg2: np.ndarray,
    window_size: int,
    eval_index: int,
    dpi: int = DEFAULT_DPI,
):
    fig, ax = plt.subplots(figsize=(12, 6.5), dpi=dpi)
    # Raw Model (Đỏ đậm) & Linear Ref của Raw Model (Đỏ đậm nét đứt)
    ax.plot(plot_frames, plot_raw_model, color=COLOR_RAW, linewidth=2.0, linestyle="-", alpha=0.85, label=f"Raw Model Angle (RMS: {rms_raw:.2f}°)", zorder=10)
    ax.plot(plot_frames, ref_raw, color=COLOR_RAW, linewidth=1.5, linestyle="--", alpha=0.45, label="Linear Ref (Raw Model)", zorder=4)

    # Model Degree 1 (Xanh dương) & Linear Ref của Degree 1 (Xanh dương nét đứt)
    ax.plot(plot_frames, plot_model_deg1, color=COLOR_DEG1, linewidth=2.3, linestyle="-", label=f"Model Angle Degree 1 (RMS: {rms_deg1:.2f}°)", zorder=12)
    ax.plot(plot_frames, ref_deg1, color=COLOR_DEG1, linewidth=1.5, linestyle="--", alpha=0.55, label="Linear Ref (Degree 1)", zorder=5)

    # Model Degree 2 (Cam sẫm) & Linear Ref của Degree 2 (Cam sẫm nét đứt)
    ax.plot(plot_frames, plot_model_deg2, color=COLOR_DEG2, linewidth=2.3, linestyle="-", label=f"Model Angle Degree 2 (RMS: {rms_deg2:.2f}°)", zorder=13)
    ax.plot(plot_frames, ref_deg2, color=COLOR_DEG2, linewidth=1.5, linestyle="--", alpha=0.55, label="Linear Ref (Degree 2)", zorder=6)

    ax.set_title(
        f"Model Angle Comparison: Degree 1 vs Degree 2 (Single Smooth)\nFile: {csv_stem}.csv | W={window_size}, index={eval_index}",
        fontsize=12,
        fontweight="bold"
    )
    ax.set_xlabel("Frame ID", fontweight="bold")
    ax.set_ylabel("Angle (Degrees)", fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.legend(loc="best", fontsize=9.0, framealpha=0.9)
    baseline.set_robust_angle_limits(ax, [plot_raw_model, plot_model_deg1, plot_model_deg2, ref_raw])
    fig.tight_layout()

    out_path = output_dir / f"{csv_stem}_model_degree1_vs_degree2.png"
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    return out_path


def plot_trajectory_comparison(
    csv_stem: str,
    output_dir: Path,
    plot_frames: np.ndarray,
    plot_traj_deg1: np.ndarray,
    plot_traj_deg2: np.ndarray,
    rms_traj_deg1: float,
    rms_traj_deg2: float,
    ref_traj_deg1: np.ndarray,
    ref_traj_deg2: np.ndarray,
    window_size: int,
    eval_index: int,
    dpi: int = DEFAULT_DPI,
):
    fig, ax = plt.subplots(figsize=(12, 6.5), dpi=dpi)
    # Trajectory Degree 1 (Xanh dương) & Linear Ref của Degree 1 (Xanh dương nét đứt)
    ax.plot(plot_frames, plot_traj_deg1, color=COLOR_DEG1, linewidth=2.3, linestyle="-", label=f"Trajectory Angle Degree 1 (RMS: {rms_traj_deg1:.2f}°)", zorder=12)
    ax.plot(plot_frames, ref_traj_deg1, color=COLOR_DEG1, linewidth=1.5, linestyle="--", alpha=0.55, label="Linear Ref (Degree 1)", zorder=5)

    # Trajectory Degree 2 (Cam sẫm) & Linear Ref của Degree 2 (Cam sẫm nét đứt)
    ax.plot(plot_frames, plot_traj_deg2, color=COLOR_DEG2, linewidth=2.3, linestyle="-", label=f"Trajectory Angle Degree 2 (RMS: {rms_traj_deg2:.2f}°)", zorder=13)
    ax.plot(plot_frames, ref_traj_deg2, color=COLOR_DEG2, linewidth=1.5, linestyle="--", alpha=0.55, label="Linear Ref (Degree 2)", zorder=6)

    ax.set_title(
        f"Trajectory Tangent Angle Comparison: Degree 1 vs Degree 2 (Single Smooth)\nFile: {csv_stem}.csv | W={window_size}, index={eval_index}",
        fontsize=12,
        fontweight="bold"
    )
    ax.set_xlabel("Frame ID", fontweight="bold")
    ax.set_ylabel("Angle (Degrees)", fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.legend(loc="best", fontsize=9.0, framealpha=0.9)
    baseline.set_robust_angle_limits(ax, [plot_traj_deg1, plot_traj_deg2, ref_traj_deg1, ref_traj_deg2])
    fig.tight_layout()

    out_path = output_dir / f"{csv_stem}_trajectory_degree1_vs_degree2.png"
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    return out_path


def plot_fused_comparison(
    csv_stem: str,
    output_dir: Path,
    plot_frames: np.ndarray,
    plot_fused_deg1: np.ndarray,
    plot_fused_deg2: np.ndarray,
    plot_traj_deg1: np.ndarray,
    plot_traj_deg2: np.ndarray,
    plot_raw_model: np.ndarray,
    rms_fused_deg1: float,
    rms_fused_deg2: float,
    rms_raw: float,
    ref_fused_deg1: np.ndarray,
    ref_fused_deg2: np.ndarray,
    window_size: int,
    eval_index: int,
    K: float,
    dpi: int = DEFAULT_DPI,
):
    fig, ax = plt.subplots(figsize=(12, 6.5), dpi=dpi)
    # Raw Model Angle (Đỏ đậm làm mốc tham chiếu thực nghiệm)
    ax.plot(plot_frames, plot_raw_model, color=COLOR_RAW, linewidth=1.8, linestyle="-", alpha=0.55, label=f"Raw Model Angle (RMS: {rms_raw:.2f}°)", zorder=8)

    # Góc tiếp tuyến quỹ đạo thành phần dùng để tính Fused (nét chấm gạch)
    ax.plot(plot_frames, plot_traj_deg1, color=COLOR_DEG1, linewidth=1.5, linestyle="-.", alpha=0.5, label="Trajectory Angle Degree 1", zorder=9)
    ax.plot(plot_frames, plot_traj_deg2, color=COLOR_DEG2, linewidth=1.5, linestyle="-.", alpha=0.5, label="Trajectory Angle Degree 2", zorder=9)

    # Fused Degree 1 (Xanh dương) & Linear Ref của Fused Degree 1 (Xanh dương nét đứt)
    ax.plot(plot_frames, plot_fused_deg1, color=COLOR_DEG1, linewidth=2.5, linestyle="-", label=f"Fused Angle Degree 1 (RMS: {rms_fused_deg1:.2f}°)", zorder=13)
    ax.plot(plot_frames, ref_fused_deg1, color=COLOR_DEG1, linewidth=1.5, linestyle="--", alpha=0.55, label="Linear Ref (Degree 1)", zorder=5)

    # Fused Degree 2 (Cam sẫm) & Linear Ref của Fused Degree 2 (Cam sẫm nét đứt)
    ax.plot(plot_frames, plot_fused_deg2, color=COLOR_DEG2, linewidth=2.5, linestyle="-", label=f"Fused Angle Degree 2 (RMS: {rms_fused_deg2:.2f}°)", zorder=14)
    ax.plot(plot_frames, ref_fused_deg2, color=COLOR_DEG2, linewidth=1.5, linestyle="--", alpha=0.55, label="Linear Ref (Degree 2)", zorder=6)

    ax.set_title(
        f"Fused Angle Comparison: Degree 1 vs Degree 2 (K={K})\nFile: {csv_stem}.csv | W={window_size}, index={eval_index}",
        fontsize=12,
        fontweight="bold"
    )
    ax.set_xlabel("Frame ID", fontweight="bold")
    ax.set_ylabel("Angle (Degrees)", fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.legend(loc="best", fontsize=9.0, framealpha=0.9)
    baseline.set_robust_angle_limits(ax, [plot_raw_model, plot_traj_deg1, plot_traj_deg2, plot_fused_deg1, plot_fused_deg2, ref_fused_deg1, ref_fused_deg2])
    fig.tight_layout()

    out_path = output_dir / f"{csv_stem}_fused_degree1_vs_degree2.png"
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    return out_path


def process_single_dataset(
    csv_path: Path,
    output_dir: Path,
    window_size: int = DEFAULT_WINDOW_SIZE,
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
    if len(segment) <= window_size:
        raise ValueError(f"Số mẫu ({len(segment)}) nhỏ hơn W={window_size}")

    x_values = segment["x_center"].to_numpy(dtype=float)
    y_values = segment["y_center"].to_numpy(dtype=float)
    raw_angles = segment[angle_column].to_numpy(dtype=float)
    frame_ids = segment["frame_id"].to_numpy(dtype=float) if "frame_id" in segment.columns else np.arange(len(segment), dtype=float)
    raw_model_unwrapped = baseline.unwrap_finite_degrees(raw_angles)

    # Tính toán 2 nhánh độc lập
    branch1 = calculate_degree_branch(
        raw_model_unwrapped=raw_model_unwrapped,
        x_values=x_values,
        y_values=y_values,
        degree=1,
        window_size=window_size,
        eval_index=eval_index,
        K=K,
    )
    branch2 = calculate_degree_branch(
        raw_model_unwrapped=raw_model_unwrapped,
        x_values=x_values,
        y_values=y_values,
        degree=2,
        window_size=window_size,
        eval_index=eval_index,
        K=K,
    )

    # Cắt W mẫu đầu tiên (khởi tạo cửa sổ)
    valid_start = min(window_size, len(raw_model_unwrapped))
    plot_frames = frame_ids[valid_start:]
    plot_raw_model = raw_model_unwrapped[valid_start:]

    plot_model_deg1 = branch1["model_smooth"][valid_start:]
    plot_model_deg2 = branch2["model_smooth"][valid_start:]

    plot_traj_deg1 = branch1["traj_angle"][valid_start:]
    plot_traj_deg2 = branch2["traj_angle"][valid_start:]

    plot_fused_deg1 = branch1["fused_angle"][valid_start:]
    plot_fused_deg2 = branch2["fused_angle"][valid_start:]

    # Tính RMS so với Ground Truth Reference (Poly Fit bậc 1 theo frame) cho từng tín hiệu
    ref_raw, rms_raw = compute_linear_fit_and_rms(plot_frames, plot_raw_model)
    ref_m1, rms_m1 = compute_linear_fit_and_rms(plot_frames, plot_model_deg1)
    ref_m2, rms_m2 = compute_linear_fit_and_rms(plot_frames, plot_model_deg2)
    ref_t1, rms_t1 = compute_linear_fit_and_rms(plot_frames, plot_traj_deg1)
    ref_t2, rms_t2 = compute_linear_fit_and_rms(plot_frames, plot_traj_deg2)
    ref_f1, rms_f1 = compute_linear_fit_and_rms(plot_frames, plot_fused_deg1)
    ref_f2, rms_f2 = compute_linear_fit_and_rms(plot_frames, plot_fused_deg2)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Xuất 3 biểu đồ
    p_model = plot_model_comparison(
        csv_stem=csv_path.stem,
        output_dir=output_dir,
        plot_frames=plot_frames,
        plot_raw_model=plot_raw_model,
        plot_model_deg1=plot_model_deg1,
        plot_model_deg2=plot_model_deg2,
        rms_raw=rms_raw,
        rms_deg1=rms_m1,
        rms_deg2=rms_m2,
        ref_raw=ref_raw,
        ref_deg1=ref_m1,
        ref_deg2=ref_m2,
        window_size=window_size,
        eval_index=eval_index,
        dpi=dpi,
    )
    p_traj = plot_trajectory_comparison(
        csv_stem=csv_path.stem,
        output_dir=output_dir,
        plot_frames=plot_frames,
        plot_traj_deg1=plot_traj_deg1,
        plot_traj_deg2=plot_traj_deg2,
        rms_traj_deg1=rms_t1,
        rms_traj_deg2=rms_t2,
        ref_traj_deg1=ref_t1,
        ref_traj_deg2=ref_t2,
        window_size=window_size,
        eval_index=eval_index,
        dpi=dpi,
    )
    p_fused = plot_fused_comparison(
        csv_stem=csv_path.stem,
        output_dir=output_dir,
        plot_frames=plot_frames,
        plot_fused_deg1=plot_fused_deg1,
        plot_fused_deg2=plot_fused_deg2,
        plot_traj_deg1=plot_traj_deg1,
        plot_traj_deg2=plot_traj_deg2,
        plot_raw_model=plot_raw_model,
        rms_fused_deg1=rms_f1,
        rms_fused_deg2=rms_f2,
        rms_raw=rms_raw,
        ref_fused_deg1=ref_f1,
        ref_fused_deg2=ref_f2,
        window_size=window_size,
        eval_index=eval_index,
        K=K,
        dpi=dpi,
    )

    print(
        f"[DONE] {csv_path.name} | Raw: {rms_raw:.2f}° | "
        f"Model (D1: {rms_m1:.2f}°, D2: {rms_m2:.2f}°) | "
        f"Traj (D1: {rms_t1:.2f}°, D2: {rms_t2:.2f}°) | "
        f"Fused (D1: {rms_f1:.2f}°, D2: {rms_f2:.2f}°)"
    )

    return {
        "file": csv_path.name,
        "rms_raw_model": rms_raw,
        "rms_model_deg1": rms_m1,
        "rms_model_deg2": rms_m2,
        "rms_traj_deg1": rms_t1,
        "rms_traj_deg2": rms_t2,
        "rms_fused_deg1": rms_f1,
        "rms_fused_deg2": rms_f2,
    }


def main():
    parser = argparse.ArgumentParser(description="So sánh độc lập Polynomial Bậc 1 vs Bậc 2 (1 lần smooth duy nhất)")
    parser.add_argument("target", type=str, help="Đường dẫn đến file CSV hoặc thư mục benchmark")
    parser.add_argument("--window-size", type=int, default=DEFAULT_WINDOW_SIZE, help="Cửa sổ trượt W (mặc định 18)")
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
        output_dir = Path(args.output_dir) if args.output_dir else target_path.parent / "poly_degree_single_smooth_comparison"
    elif target_path.is_dir():
        # Lọc chỉ lấy các file góc benchmark cố định, bỏ các file turn
        csv_files = sorted([f for f in target_path.glob("*.csv") if "turn" not in f.stem.lower()])
        output_dir = Path(args.output_dir) if args.output_dir else target_path / "poly_degree_single_smooth_comparison"
    else:
        raise FileNotFoundError(f"Không tìm thấy {target_path}")

    results = []
    for csv_file in csv_files:
        try:
            res = process_single_dataset(
                csv_path=csv_file,
                output_dir=output_dir,
                window_size=args.window_size,
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
    print("BẢNG TỔNG HỢP SAI SỐ RMS: POLYNOMIAL BẬC 1 VS BẬC 2 (SINGLE SMOOTH W=18, INDEX=-4, K=3.0)")
    print("=" * 120)
    print(df_res.to_string(index=False))

    # Tách 2 nhóm: Góc cố định và Quỹ đạo vòng tròn
    benchmark_fixed = df_res[~df_res["file"].str.contains("turn", case=False, na=False)]
    benchmark_turn = df_res[df_res["file"].str.contains("turn", case=False, na=False)]

    if not benchmark_fixed.empty:
        print("\n" + "-" * 90)
        print("NHÓM 1: TRUNG BÌNH 6 TẬP GÓC CỐ ĐỊNH (0°, 30°, 45°, -45°, 60°, 90°)")
        print(f"- Raw Model RMS:             {benchmark_fixed['rms_raw_model'].mean():.2f}°")
        print(f"- Model Smooth (Bậc 1) RMS:  {benchmark_fixed['rms_model_deg1'].mean():.2f}°")
        print(f"- Model Smooth (Bậc 2) RMS:  {benchmark_fixed['rms_model_deg2'].mean():.2f}°")
        print(f"- Trajectory Angle (Bậc 1):  {benchmark_fixed['rms_traj_deg1'].mean():.2f}°")
        print(f"- Trajectory Angle (Bậc 2):  {benchmark_fixed['rms_traj_deg2'].mean():.2f}°")
        print(f"- Fused Angle (Bậc 1) RMS:   {benchmark_fixed['rms_fused_deg1'].mean():.2f}°")
        print(f"- Fused Angle (Bậc 2) RMS:   {benchmark_fixed['rms_fused_deg2'].mean():.2f}°")

    if not benchmark_turn.empty:
        print("\n" + "-" * 90)
        print("NHÓM 2: TRUNG BÌNH 3 TẬP QUỸ ĐẠO QUAY VÒNG (1turn, 2turn, 3turn)")
        print(f"- Raw Model RMS:             {benchmark_turn['rms_raw_model'].mean():.2f}°")
        print(f"- Model Smooth (Bậc 1) RMS:  {benchmark_turn['rms_model_deg1'].mean():.2f}°")
        print(f"- Model Smooth (Bậc 2) RMS:  {benchmark_turn['rms_model_deg2'].mean():.2f}°")
        print(f"- Trajectory Angle (Bậc 1):  {benchmark_turn['rms_traj_deg1'].mean():.2f}°")
        print(f"- Trajectory Angle (Bậc 2):  {benchmark_turn['rms_traj_deg2'].mean():.2f}°")
        print(f"- Fused Angle (Bậc 1) RMS:   {benchmark_turn['rms_fused_deg1'].mean():.2f}°")
        print(f"- Fused Angle (Bậc 2) RMS:   {benchmark_turn['rms_fused_deg2'].mean():.2f}°")
    print("=" * 120 + "\n")


if __name__ == "__main__":
    main()
