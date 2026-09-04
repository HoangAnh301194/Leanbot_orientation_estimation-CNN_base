"""
plot_pid_navigation_log.py

Tool for plotting PID & Navigation analysis from Leanbot log data.
Stored in LeanbotTinyRC directory.

Supported plots:
  1. Angle response chart (Model Smooth, Trajectory Smooth, Fused) vs Target Angle & Angle Error.
  2. BLE wheel speed chart (Speed Left & Speed Right).
  3. 2D trajectory chart (Oxy) and Target Waypoint.
  4. Distance error chart.
"""

import argparse
import os
import glob
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


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

    # --- FIGURE 1: PID CONTROL & ANGLE ANALYSIS ---
    fig, axes = plt.subplots(3, 1, figsize=(14, 11), sharex=True)
    fig.suptitle(f"PID CONTROL & LEANBOT ROTATION ANGLE ANALYSIS\nFile: {os.path.basename(csv_path)}", fontsize=14, fontweight="bold")

    frames = df["frame_id"]

    # Normalize angles to [-180, 180] range for consistency with raw and target angles
    def wrap_to_180_series(s):
        return (s + 180.0) % 360.0 - 180.0

    # Subplot 1: Angle response (Model, Trajectory, Fused, Target) in [-180, 180] range
    ax1 = axes[0]
    if "raw_angle" in df.columns:
        ax1.plot(frames, wrap_to_180_series(df["raw_angle"]), label="Raw Model Angle", color="lightgray", alpha=0.7, linewidth=1, linestyle=":")
    if "model_angle_smooth" in df.columns:
        ax1.plot(frames, wrap_to_180_series(df["model_angle_smooth"]), label="Model Smooth (W=18)", color="#1f77b4", linewidth=1.6)
    if "trajectory_angle_smooth" in df.columns:
        ax1.plot(frames, wrap_to_180_series(df["trajectory_angle_smooth"]), label="Trajectory Smooth", color="#ff7f0e", linewidth=1.3, linestyle="--")
    if "fused_angle" in df.columns:
        ax1.plot(frames, wrap_to_180_series(df["fused_angle"]), label="Fused Angle (Control)", color="#2ca02c", linewidth=2.0)
    if "target_angle" in df.columns and (df["target_angle"] != 0).any():
        ax1.plot(frames, wrap_to_180_series(df["target_angle"]), label="Target Angle", color="red", linewidth=1.8, linestyle="-.")

    ax1.set_ylabel("Angle (deg)", fontsize=11)
    ax1.set_ylim(-190, 190)
    ax1.set_yticks(np.arange(-180, 181, 45))
    ax1.axhline(0, color="black", linestyle=":", alpha=0.4)
    ax1.set_title("1. Leanbot Angle Response in [-180 deg, 180 deg] (Model vs Trajectory vs Fused vs Target)", fontsize=12, fontweight="bold")
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.legend(loc="upper right", framealpha=0.9)

    # Subplot 2: Angle Error & Distance Error
    ax2 = axes[1]
    color_err = "#d62728"
    if "angle_error" in df.columns:
        ax2.plot(frames, df["angle_error"], label="Angle Error (deg)", color=color_err, linewidth=1.8)
        ax2.axhline(0, color="black", linestyle=":", alpha=0.7)
        ax2.set_ylabel("Angle Error (deg)", color=color_err, fontsize=11)
        ax2.tick_params(axis="y", labelcolor=color_err)

    if "distance_error" in df.columns and (df["distance_error"] > 0).any():
        ax2_dist = ax2.twinx()
        color_dist = "#9467bd"
        ax2_dist.plot(frames, df["distance_error"], label="Distance Error (px)", color=color_dist, linewidth=1.8, linestyle="--")
        ax2_dist.set_ylabel("Distance Error (px)", color=color_dist, fontsize=11)
        ax2_dist.tick_params(axis="y", labelcolor=color_dist)

    ax2.set_title("2. Control Error (Angle & Distance)", fontsize=12, fontweight="bold")
    ax2.grid(True, linestyle="--", alpha=0.5)

    # Subplot 3: BLE motor speed commands (Speed Left & Speed Right)
    ax3 = axes[2]
    if "ble_speed_left" in df.columns and "ble_speed_right" in df.columns:
        ax3.plot(frames, df["ble_speed_left"], label="Speed Left Motor", color="blue", linewidth=1.8, linestyle="-")
        ax3.plot(frames, df["ble_speed_right"], label="Speed Right Motor", color="red", linewidth=1.8, linestyle="-")
        ax3.axhline(0, color="black", linestyle=":", alpha=0.5)
        ax3.set_ylabel("Motor Speed (runLR units)", fontsize=11)
        ax3.set_xlabel("Frame ID", fontsize=11)
        ax3.set_title("3. Speed Commands Sent to Leanbot BLE (r/speed_l/speed_r)", fontsize=12, fontweight="bold")
        ax3.grid(True, linestyle="--", alpha=0.5)
        ax3.legend(loc="upper right", framealpha=0.9)

    plt.tight_layout()
    out_fig1 = os.path.join(save_dir, f"{filename_stem}_pid_analysis.png")
    plt.savefig(out_fig1, dpi=300)
    plt.close()
    print(f"[SAVED] PID & Angle chart: {out_fig1}")

    # --- FIGURE 2: 2D TRAJECTORY (Oxy) ---
    if "x_center" in df.columns and "y_center" in df.columns:
        plt.figure(figsize=(8, 8))
        valid_coords = df.dropna(subset=["x_center", "y_center"])
        if len(valid_coords) > 0:
            xs = valid_coords["x_center"].values
            ys = valid_coords["y_center"].values

            plt.plot(xs, ys, color="#1f77b4", linewidth=2.0, label="Leanbot Trajectory")
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
            plt.grid(True, linestyle="--", alpha=0.5)
            plt.legend(loc="best", framealpha=0.9)

            out_fig2 = os.path.join(save_dir, f"{filename_stem}_2d_trajectory.png")
            plt.savefig(out_fig2, dpi=300)
            plt.close()
            print(f"[SAVED] 2D trajectory chart: {out_fig2}")


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
        # Auto-select latest CSV log from benchmark_logs/, fall back to ../benchmark/
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
