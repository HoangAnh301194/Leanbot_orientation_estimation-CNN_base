"""
Cong cu ve do thi phan tich du lieu log PID & Navigation Leanbot.
Luu trong thu muc LeanbotTinyRC.

Ho tro ve:
  1. Do thi 3 duong goc (Model Smooth, Trajectory Smooth, Fused) vs Target Angle & Angle Error.
  2. Do thi van toc 2 banh xe BLE (Speed Left & Speed Right).
  3. Do thi quy dao 2D (Oxy Trajectory) va diem Target Waypoint.
  4. Do thi sai so khoang cach (Distance Error).
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
        print(f"[ERROR] Khong tim thay file log: {csv_path}")
        return

    df = pd.read_csv(csv_path)
    print(f"[INFO] Da doc {len(df)} dong du lieu tu: {csv_path}")

    # Chuyen doi cac cot so
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

    # --- FIGURE 1: TONG HOP DIEU KHIEN PID & GOC ---
    fig, axes = plt.subplots(3, 1, figsize=(14, 11), sharex=True)
    fig.suptitle(f"PHAN TICH DIEU KHIEN PID & GOC XOAY LEANBOT\nFile: {os.path.basename(csv_path)}", fontsize=14, fontweight="bold")

    frames = df["frame_id"]

    # Chuan hoa goc ve khoang [-180, 180] do de dong nhat voi goc raw va target
    def wrap_to_180_series(s):
        return (s + 180.0) % 360.0 - 180.0

    # Subplot 1: Goc (Model, Trajectory, Fused, Target) trong mien [-180, 180] do
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
        ax1.plot(frames, wrap_to_180_series(df["target_angle"]), label="Target Angle (90°)", color="red", linewidth=1.8, linestyle="-.")

    ax1.set_ylabel("Góc (Độ)", fontsize=11)
    ax1.set_ylim(-190, 190)
    ax1.set_yticks(np.arange(-180, 181, 45))
    ax1.axhline(0, color="black", linestyle=":", alpha=0.4)
    ax1.set_title("1. Đáp ứng Góc của Leanbot trong miền [-180°, 180°] (Model vs Trajectory vs Fused vs Target)", fontsize=12, fontweight="bold")
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.legend(loc="upper right", framealpha=0.9)

    # Subplot 2: Sai so goc (Angle Error) & Sai so khoang cach (Distance Error)
    ax2 = axes[1]
    color_err = "#d62728"
    if "angle_error" in df.columns:
        ax2.plot(frames, df["angle_error"], label="Angle Error (deg)", color=color_err, linewidth=1.8)
        ax2.axhline(0, color="black", linestyle=":", alpha=0.7)
        ax2.set_ylabel("Sai số góc (Độ)", color=color_err, fontsize=11)
        ax2.tick_params(axis="y", labelcolor=color_err)

    if "distance_error" in df.columns and (df["distance_error"] > 0).any():
        ax2_dist = ax2.twinx()
        color_dist = "#9467bd"
        ax2_dist.plot(frames, df["distance_error"], label="Distance Error (px)", color=color_dist, linewidth=1.8, linestyle="--")
        ax2_dist.set_ylabel("Sai số khoảng cách (Pixel)", color=color_dist, fontsize=11)
        ax2_dist.tick_params(axis="y", labelcolor=color_dist)

    ax2.set_title("2. Sai số điều khiển (Góc & Khoảng cách)", fontsize=12, fontweight="bold")
    ax2.grid(True, linestyle="--", alpha=0.5)

    # Subplot 3: Van toc dong co BLE (Speed Left & Speed Right)
    ax3 = axes[2]
    if "ble_speed_left" in df.columns and "ble_speed_right" in df.columns:
        ax3.plot(frames, df["ble_speed_left"], label="Speed Left Motor", color="#17becf", linewidth=1.8)
        ax3.plot(frames, df["ble_speed_right"], label="Speed Right Motor", color="#e377c2", linewidth=1.8, linestyle="--")
        ax3.axhline(0, color="black", linestyle=":", alpha=0.5)
        ax3.set_ylabel("Vận tốc Motor", fontsize=11)
        ax3.set_xlabel("Frame ID", fontsize=11)
        ax3.set_title("3. Lệnh vận tốc gửi sang Leanbot BLE (r/speed_l/speed_r)", fontsize=12, fontweight="bold")
        ax3.grid(True, linestyle="--", alpha=0.5)
        ax3.legend(loc="upper right", framealpha=0.9)

    plt.tight_layout()
    out_fig1 = os.path.join(save_dir, f"{filename_stem}_pid_analysis.png")
    plt.savefig(out_fig1, dpi=300)
    plt.close()
    print(f"[SAVED] Do thi PID & Goc: {out_fig1}")

    # --- FIGURE 2: QUY DAO 2D Oxy (TRAJECTORY) ---
    if "x_center" in df.columns and "y_center" in df.columns:
        plt.figure(figsize=(8, 8))
        valid_coords = df.dropna(subset=["x_center", "y_center"])
        if len(valid_coords) > 0:
            xs = valid_coords["x_center"].values
            ys = valid_coords["y_center"].values

            plt.plot(xs, ys, color="#1f77b4", linewidth=2.0, label="Quỹ đạo Leanbot")
            plt.scatter(xs[0], ys[0], color="green", s=120, zorder=5, label=f"Điểm bắt đầu ({xs[0]:.0f}, {ys[0]:.0f})")
            plt.scatter(xs[-1], ys[-1], color="blue", s=120, zorder=5, label=f"Điểm kết thúc ({xs[-1]:.0f}, {ys[-1]:.0f})")

            # Ve Target Waypoint neu co
            if "target_x" in df.columns and (df["target_x"] > 0).any():
                targets = df[df["target_x"] > 0][["target_x", "target_y"]].drop_duplicates()
                for _, trg in targets.iterrows():
                    plt.scatter(trg["target_x"], trg["target_y"], color="red", marker="*", s=250, zorder=6, label=f"Target Goal ({trg['target_x']:.0f}, {trg['target_y']:.0f})")

            plt.xlim(240, 1040)
            plt.ylim(760, -40)  # Inverted Y axis
            
            plt.title(f"QUỸ ĐẠO DI CHUYỂN 2D CỦA LEANBOT (Oxy)\nFile: {os.path.basename(csv_path)}", fontsize=13, fontweight="bold")
            plt.xlabel("Tọa độ X (Pixel)", fontsize=11)
            plt.ylabel("Tọa độ Y (Pixel)", fontsize=11)
            plt.grid(True, linestyle="--", alpha=0.5)
            plt.legend(loc="best", framealpha=0.9)

            out_fig2 = os.path.join(save_dir, f"{filename_stem}_2d_trajectory.png")
            plt.savefig(out_fig2, dpi=300)
            plt.close()
            print(f"[SAVED] Do thi quy dao 2D: {out_fig2}")


def main():
    parser = argparse.ArgumentParser(description="Tool ve do thi log PID & Navigation Leanbot")
    parser.add_argument("--log", default="", help="Duong dan toi file CSV log (neu khong truyen se tu chon file moi nhat trong benchmark_logs/)")
    parser.add_argument("--out", default="", help="Thu muc luu anh do thi (default: benchmark_logs/plots/)")
    args = parser.parse_args()

    local_benchmark_dir = Path(__file__).resolve().parent / "benchmark_logs"
    parent_benchmark_dir = Path(__file__).resolve().parent.parent / "benchmark"
    
    if args.log:
        target_csv = args.log
    else:
        # Tim file log CSV moi nhat trong benchmark_logs/ truoc, neu khong co thi tim trong ../benchmark/
        csv_files = glob.glob(str(local_benchmark_dir / "*.csv"))
        if not csv_files:
            csv_files = glob.glob(str(parent_benchmark_dir / "*.csv"))
        if not csv_files:
            print(f"[WARN] Khong tim thay file CSV nao trong {local_benchmark_dir} hoac {parent_benchmark_dir}")
            return
        target_csv = max(csv_files, key=os.path.getmtime)
        print(f"[INFO] Tu dong chon file log moi nhat: {target_csv}")

    plot_pid_log(target_csv, save_dir=args.out)


if __name__ == "__main__":
    main()
