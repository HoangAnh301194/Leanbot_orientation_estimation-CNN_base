"""
plot_pid_navigation_log.py

Tool for plotting PID & Navigation analysis from Leanbot log data.
Stored in LeanbotTinyRC directory.

Supported plots:
  1. Overview PID & Angle analysis chart (_pid_analysis.png)
  2. Differential analysis chart (_pid_diff_analysis.png):
     - Error Angle e(t)
     - Differential of Error Angle: de/dt (deg/s)
     - Wheel Speeds (v_L, v_R), Differential Speed (v_diff), and Steering Ratio (v_diff / v_LR)
  3. 2D trajectory chart (Oxy) and Target Waypoint (_2d_trajectory.png)

NOTE: All plots strictly use solid lines (linestyle="-"), NO dashed or dotted lines.
"""

import argparse
import os
import glob
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


def parse_timestamps_to_seconds(ts_series: pd.Series) -> pd.Series:
    """Convert HH:MM:SS.mmm string timestamps into elapsed seconds."""
    secs = []
    for ts in ts_series:
        try:
            parts = str(ts).strip().split(":")
            if len(parts) == 3:
                h, m, s = float(parts[0]), float(parts[1]), float(parts[2])
                secs.append(h * 3600.0 + m * 60.0 + s)
            else:
                secs.append(np.nan)
        except Exception:
            secs.append(np.nan)
    return pd.Series(secs, index=ts_series.index)


def wrap_to_180_series(s: pd.Series) -> pd.Series:
    """Normalize angles into [-180, 180] degrees range."""
    return (s + 180.0) % 360.0 - 180.0


def plot_pid_log(csv_path: str, save_dir: str = ""):
    if not os.path.exists(csv_path):
        print(f"[ERROR] Log file not found: {csv_path}")
        return

    df = pd.read_csv(csv_path)
    print(f"[INFO] Loaded {len(df)} rows from: {csv_path}")

    # Convert numeric columns
    numeric_cols = [
        "frame_id", "inf_time_ms", "end_to_end_time_ms", "fps",
        "x_center", "y_center", "raw_angle", "model_angle_smooth",
        "trajectory_angle_smooth", "fused_angle", "target_angle",
        "angle_error", "target_x", "target_y", "distance_error",
        "ble_speed_left", "ble_speed_right"
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    filename_stem = Path(csv_path).stem
    if not save_dir:
        save_dir = str(Path(csv_path).parent / "plots")
    os.makedirs(save_dir, exist_ok=True)

    frames = df["frame_id"]

    # Calculate real-time dt (seconds) between successive samples
    if "timestamp" in df.columns:
        time_secs = parse_timestamps_to_seconds(df["timestamp"])
        dt = time_secs.diff()
    else:
        dt = pd.Series([np.nan] * len(df))

    if "fps" in df.columns:
        fallback_dt = 1.0 / df["fps"].replace(0, np.nan).fillna(30.0)
    else:
        fallback_dt = pd.Series([0.05] * len(df))

    dt = dt.where((dt > 0.001) & (dt < 1.0), fallback_dt).fillna(0.05)

    # Differential of angle error: de/dt (deg/s)
    if "angle_error" in df.columns:
        err_diff = (df["angle_error"].diff() + 180.0) % 360.0 - 180.0
        de_dt = err_diff / dt
    else:
        de_dt = pd.Series([0.0] * len(df))

    # Wheel speeds and differential components
    has_speeds = "ble_speed_left" in df.columns and "ble_speed_right" in df.columns
    if has_speeds:
        v_L = df["ble_speed_left"]
        v_R = df["ble_speed_right"]
        v_diff = (v_L - v_R) / 2.0
        v_LR = (v_L + v_R) / 2.0
        ratio_v = np.where(np.abs(v_LR) > 10.0, v_diff / np.abs(v_LR), 0.0)
    else:
        v_L = v_R = v_diff = v_LR = ratio_v = pd.Series([0.0] * len(df))

    # =========================================================================
    # FIGURE 1: OVERVIEW PID & ANGLE ANALYSIS
    # =========================================================================
    fig1, axes1 = plt.subplots(3, 1, figsize=(14, 11), sharex=True)
    fig1.suptitle(f"PID CONTROL & LEANBOT ROTATION ANGLE OVERVIEW\nFile: {os.path.basename(csv_path)}", fontsize=14, fontweight="bold")

    # Subplot 1: Angle response
    ax1 = axes1[0]
    if "raw_angle" in df.columns:
        ax1.plot(frames, wrap_to_180_series(df["raw_angle"]), label="Raw Model Angle", color="lightgray", alpha=0.7, linewidth=1.2, linestyle="-")
    if "model_angle_smooth" in df.columns:
        ax1.plot(frames, wrap_to_180_series(df["model_angle_smooth"]), label="Model Smooth (W=18)", color="#1f77b4", linewidth=1.6, linestyle="-")
    if "trajectory_angle_smooth" in df.columns:
        ax1.plot(frames, wrap_to_180_series(df["trajectory_angle_smooth"]), label="Trajectory Smooth", color="#ff7f0e", linewidth=1.5, linestyle="-")
    if "fused_angle" in df.columns:
        ax1.plot(frames, wrap_to_180_series(df["fused_angle"]), label="Fused Angle (Control)", color="#2ca02c", linewidth=2.0, linestyle="-")
    if "target_angle" in df.columns and (df["target_angle"] != 0).any():
        ax1.plot(frames, wrap_to_180_series(df["target_angle"]), label="Target Angle", color="red", linewidth=1.8, linestyle="-")

    ax1.set_ylabel("Angle (deg)", fontsize=11)
    ax1.set_ylim(-190, 190)
    ax1.set_yticks(np.arange(-180, 181, 45))
    ax1.axhline(0, color="black", linestyle="-", alpha=0.3)
    ax1.set_title("1. Leanbot Angle Response (Model vs Trajectory vs Fused vs Target)", fontsize=12, fontweight="bold")
    ax1.grid(True, linestyle="-", alpha=0.25)
    ax1.legend(loc="upper right", framealpha=0.9)

    # Subplot 2: Control Error (Angle & Distance)
    ax2 = axes1[1]
    color_err = "#d62728"
    if "angle_error" in df.columns:
        ax2.plot(frames, df["angle_error"], label="Angle Error (deg)", color=color_err, linewidth=1.8, linestyle="-")
        ax2.axhline(0, color="black", linestyle="-", alpha=0.4)
        ax2.set_ylabel("Angle Error (deg)", color=color_err, fontsize=11)
        ax2.tick_params(axis="y", labelcolor=color_err)

    if "distance_error" in df.columns and (df["distance_error"] > 0).any():
        ax2_dist = ax2.twinx()
        color_dist = "#9467bd"
        ax2_dist.plot(frames, df["distance_error"], label="Distance Error (px)", color=color_dist, linewidth=1.8, linestyle="-")
        ax2_dist.set_ylabel("Distance Error (px)", color=color_dist, fontsize=11)
        ax2_dist.tick_params(axis="y", labelcolor=color_dist)

    ax2.set_title("2. Control Error (Angle & Distance)", fontsize=12, fontweight="bold")
    ax2.grid(True, linestyle="-", alpha=0.25)

    # Subplot 3: Motor speeds & Differential speed
    ax3 = axes1[2]
    if has_speeds:
        ax3.plot(frames, v_L, label="Speed Left (v_L)", color="#1f77b4", linewidth=1.6, linestyle="-")
        ax3.plot(frames, v_R, label="Speed Right (v_R)", color="#d62728", linewidth=1.6, linestyle="-")
        ax3.plot(frames, v_diff, label="Diff Speed v_diff = (v_L - v_R)/2", color="#2ca02c", linewidth=2.0, linestyle="-")
        ax3.axhline(0, color="black", linestyle="-", alpha=0.3)
        ax3.set_ylabel("Motor Speed (runLR units)", fontsize=11)
        ax3.set_xlabel("Frame ID", fontsize=11)
        ax3.set_title("3. Speed Commands (v_L, v_R, v_diff)", fontsize=12, fontweight="bold")
        ax3.grid(True, linestyle="-", alpha=0.25)
        ax3.legend(loc="upper right", framealpha=0.9)

    plt.tight_layout()
    out_fig1 = os.path.join(save_dir, f"{filename_stem}_pid_analysis.png")
    plt.savefig(out_fig1, dpi=300)
    plt.close(fig1)
    print(f"[SAVED] PID & Angle chart: {out_fig1}")

    # =========================================================================
    # FIGURE 2: DETAILED DIFFERENTIAL & ANGLE ERROR ANALYSIS (YÊU CẦU CỦA THẦY)
    #   1. Error Angle
    #   2. Differential of Error Angle: de/dt (deg/s)
    #   3. Wheel Speeds (v_L, v_R), Differential Speed (v_diff), and Ratio (v_diff / v_LR)
    # =========================================================================
    fig2, axes2 = plt.subplots(3, 1, figsize=(14, 11), sharex=True)
    fig2.suptitle(f"ERROR ANGLE, DIFFERENTIAL ERROR & DIFFERENTIAL VELOCITY ANALYSIS\nFile: {os.path.basename(csv_path)}", fontsize=14, fontweight="bold")

    # Subplot 1: Error Angle
    ax_d1 = axes2[0]
    if "angle_error" in df.columns:
        ax_d1.plot(frames, df["angle_error"], label="Error Angle e(t)", color="#d62728", linewidth=2.0, linestyle="-")
        ax_d1.axhline(0, color="black", linestyle="-", alpha=0.5)
        # Tolerance boundaries ±15 deg
        ax_d1.axhline(15, color="gray", linestyle="-", alpha=0.4, label="Tolerance ±15 deg")
        ax_d1.axhline(-15, color="gray", linestyle="-", alpha=0.4)
        ax_d1.fill_between(frames, -15, 15, color="#2ca02c", alpha=0.08, label="Tolerance Band (±15°)")
    ax_d1.set_ylabel("Error Angle (deg)", fontsize=11)
    ax_d1.set_title("1. Error Angle: e(t) = target_angle - fused_angle", fontsize=12, fontweight="bold")
    ax_d1.grid(True, linestyle="-", alpha=0.25)
    ax_d1.legend(loc="upper right", framealpha=0.9)

    # Subplot 2: Differential of Error Angle (de/dt)
    ax_d2 = axes2[1]
    ax_d2.plot(frames, de_dt, label="de/dt = d(Error Angle)/dt (deg/s)", color="#ff7f0e", linewidth=1.8, linestyle="-")
    ax_d2.axhline(0, color="black", linestyle="-", alpha=0.5)
    ax_d2.set_ylabel("Derivative (deg/s)", fontsize=11)
    ax_d2.set_title("2. Differential of Error Angle: de/dt (Derivative Input for D-Term)", fontsize=12, fontweight="bold")
    ax_d2.grid(True, linestyle="-", alpha=0.25)
    ax_d2.legend(loc="upper right", framealpha=0.9)

    # Subplot 3: Wheel Speeds, v_diff and Steering Ratio v_diff / v_LR
    ax_d3 = axes2[2]
    if has_speeds:
        ax_d3.plot(frames, v_L, label="Speed Left (v_L)", color="#1f77b4", linewidth=1.4, alpha=0.7, linestyle="-")
        ax_d3.plot(frames, v_R, label="Speed Right (v_R)", color="#e377c2", linewidth=1.4, alpha=0.7, linestyle="-")
        ax_d3.plot(frames, v_diff, label="Differential Speed v_diff = (v_L - v_R)/2", color="#6a0dad", linewidth=2.2, linestyle="-")
        ax_d3.axhline(0, color="black", linestyle="-", alpha=0.3)
        ax_d3.set_ylabel("Motor Speed (runLR units)", fontsize=11)
        ax_d3.set_xlabel("Frame ID", fontsize=11)

        # Twin axis for Steering Ratio v_diff / v_LR
        ax_ratio = ax_d3.twinx()
        color_ratio = "#2ca02c"
        ax_ratio.plot(frames, ratio_v, label="Ratio (v_diff / v_LR)", color=color_ratio, linewidth=1.8, linestyle="-")
        ax_ratio.set_ylabel("Ratio v_diff / v_LR", color=color_ratio, fontsize=11)
        ax_ratio.tick_params(axis="y", labelcolor=color_ratio)
        ax_ratio.axhline(1.0, color="gray", linestyle="-", alpha=0.25)
        ax_ratio.axhline(-1.0, color="gray", linestyle="-", alpha=0.25)

        # Combine legends from both axes
        lines_1, labels_1 = ax_d3.get_legend_handles_labels()
        lines_2, labels_2 = ax_ratio.get_legend_handles_labels()
        ax_d3.legend(lines_1 + lines_2, labels_1 + labels_2, loc="upper right", framealpha=0.9)

    ax_d3.set_title("3. Wheel Speeds (v_L, v_R), Differential Speed (v_diff) & Steering Ratio (v_diff / v_LR)", fontsize=12, fontweight="bold")
    ax_d3.grid(True, linestyle="-", alpha=0.25)

    plt.tight_layout()
    out_fig2 = os.path.join(save_dir, f"{filename_stem}_pid_diff_analysis.png")
    plt.savefig(out_fig2, dpi=300)
    plt.close(fig2)
    print(f"[SAVED] Differential analysis chart: {out_fig2}")

    # =========================================================================
    # FIGURE 3: 2D TRAJECTORY (Oxy)
    # =========================================================================
    if "x_center" in df.columns and "y_center" in df.columns:
        fig3 = plt.figure(figsize=(8, 8))
        valid_coords = df.dropna(subset=["x_center", "y_center"])
        if len(valid_coords) > 0:
            xs = valid_coords["x_center"].values
            ys = valid_coords["y_center"].values

            plt.plot(xs, ys, color="#1f77b4", linewidth=2.0, linestyle="-", label="Leanbot Trajectory")
            plt.scatter(xs[0], ys[0], color="green", s=120, zorder=5, label=f"Start ({xs[0]:.0f}, {ys[0]:.0f})")
            plt.scatter(xs[-1], ys[-1], color="blue", s=120, zorder=5, label=f"End ({xs[-1]:.0f}, {ys[-1]:.0f})")

            # Plot target waypoint if available
            if "target_x" in df.columns and (df["target_x"] > 0).any():
                targets = df[df["target_x"] > 0][["target_x", "target_y"]].drop_duplicates()
                for _, trg in targets.iterrows():
                    plt.scatter(trg["target_x"], trg["target_y"], color="red", marker="*", s=250, zorder=6, label=f"Target Goal ({trg['target_x']:.0f}, {trg['target_y']:.0f})")

            plt.xlim(240, 1040)
            plt.ylim(760, -40)  # Inverted Y axis (image coordinates)

            plt.title(f"LEANBOT 2D MOVEMENT TRAJECTORY (Oxy)\nFile: {os.path.basename(csv_path)}", fontsize=13, fontweight="bold")
            plt.xlabel("X Coordinate (Pixel)", fontsize=11)
            plt.ylabel("Y Coordinate (Pixel)", fontsize=11)
            plt.grid(True, linestyle="-", alpha=0.25)
            plt.legend(loc="best", framealpha=0.9)

            out_fig3 = os.path.join(save_dir, f"{filename_stem}_2d_trajectory.png")
            plt.savefig(out_fig3, dpi=300)
            plt.close(fig3)
            print(f"[SAVED] 2D trajectory chart: {out_fig3}")


def main():
    parser = argparse.ArgumentParser(description="Tool for plotting PID & Navigation log data from Leanbot")
    parser.add_argument("--log", default="", help="Path to the CSV log file (if omitted, auto-selects the latest file in benchmark_logs/)")
    parser.add_argument("--out", default="", help="Output directory for chart images (default: benchmark_logs/plots/)")
    args = parser.parse_args()

    local_benchmark_dir = Path(__file__).resolve().parent / "benchmark_logs"
    parent_benchmark_dir = Path(__file__).resolve().parent.parent / "benchmark"

    if args.log:
        target_csv = args.log
    else:
        csv_files = glob.glob(str(local_benchmark_dir / "*.csv"))
        if not csv_files:
            csv_files = glob.glob(str(parent_benchmark_dir / "*.csv"))
        if not csv_files:
            print(f"[WARN] No CSV files found in {local_benchmark_dir} or {parent_benchmark_dir}")
            return
        target_csv = max(csv_files, key=os.path.getmtime)
        print(f"[INFO] Auto-selected latest log file: {target_csv}")

    plot_pid_log(target_csv, save_dir=args.out)


if __name__ == "__main__":
    main()
