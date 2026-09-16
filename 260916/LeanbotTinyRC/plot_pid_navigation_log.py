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


def wrap_to_180(angle_deg: float) -> float:
    """Normalize a scalar angle into [-180, 180] degrees range."""
    return (angle_deg + 180.0) % 360.0 - 180.0


def plot_pid_log(
    csv_path: str,
    save_dir: str = "",
    kp_angle2: float = 0.02,
    kd_angle2: float = None,
    heading_tolerance: float = 20.0,
):
    if not os.path.exists(csv_path):
        print(f"[ERROR] Log file not found: {csv_path}")
        return

    if kd_angle2 is None:
        parent_name = Path(csv_path).parent.name
        name = Path(csv_path).name
        if "0005" in parent_name or "logs_1" in parent_name:
            kd_angle2 = 0.005
        elif "001" in parent_name or "logs_2" in parent_name:
            kd_angle2 = 0.01
        elif "002" in parent_name or "logs_3" in parent_name:
            kd_angle2 = 0.02
        elif "004" in parent_name or "logs_4" in parent_name:
            kd_angle2 = 0.04
        elif "006" in parent_name:
            kd_angle2 = 0.06
        elif "008" in parent_name or "logs_5" in parent_name:
            kd_angle2 = 0.08
        elif "00" in parent_name or "logs_0" in parent_name:
            kd_angle2 = 0.0
        elif "1633" in name or "1634" in name:
            kd_angle2 = 0.01
        elif "1622" in name or "1623" in name:
            kd_angle2 = 0.005
        elif "1434" in name or "1437" in name or "1438" in name:
            kd_angle2 = 0.005
        else:
            kd_angle2 = 0.005

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

    # Detect Phase transitions
    split_frame = None
    split_frame_p3 = None
    split_frame_p4_fwd = None
    split_frame_p4_bwd = None
    if "pid_mode" in df.columns:
        p2_matches = df[df["pid_mode"] == "PHASE_2_DRIVING"]
        if len(p2_matches) > 0:
            split_frame = p2_matches["frame_id"].iloc[0]
        p3_matches = df[df["pid_mode"] == "PHASE_3_FINAL_ALIGNING"]
        if len(p3_matches) > 0:
            split_frame_p3 = p3_matches["frame_id"].iloc[0]
        p4_fwd_matches = df[df["pid_mode"] == "PHASE_4_FORWARD"]
        if len(p4_fwd_matches) > 0:
            split_frame_p4_fwd = p4_fwd_matches["frame_id"].iloc[0]
        p4_bwd_matches = df[df["pid_mode"] == "PHASE_4_BACKWARD"]
        if len(p4_bwd_matches) > 0:
            split_frame_p4_bwd = p4_bwd_matches["frame_id"].iloc[0]

    def apply_phase_shading(ax, show_labels=False):
        if len(frames) == 0:
            return
        f_start = frames.iloc[0]
        f_end = frames.iloc[-1]

        p2_end = split_frame_p3 if split_frame_p3 is not None else (split_frame_p4_fwd if split_frame_p4_fwd is not None else f_end)
        p3_end = split_frame_p4_fwd if split_frame_p4_fwd is not None else f_end
        p4_fwd_end = split_frame_p4_bwd if split_frame_p4_bwd is not None else f_end
        
        # Phase 1
        if split_frame is not None:
            ax.axvspan(f_start, split_frame, color="#666666", alpha=0.05, zorder=0)
            ax.axvline(split_frame, color="#444444", linestyle="--", linewidth=1.0, alpha=0.4, zorder=1)

        # Phase 3
        if split_frame_p3 is not None:
            ax.axvspan(split_frame_p3, p3_end, color="#ba68c8", alpha=0.06, zorder=0)
            ax.axvline(split_frame_p3, color="#ab47bc", linestyle="--", linewidth=1.0, alpha=0.4, zorder=1)

        # Phase 4 Forward
        if split_frame_p4_fwd is not None:
            ax.axvspan(split_frame_p4_fwd, p4_fwd_end, color="#4dd0e1", alpha=0.06, zorder=0)
            ax.axvline(split_frame_p4_fwd, color="#00acc1", linestyle="--", linewidth=1.0, alpha=0.4, zorder=1)

        # Phase 4 Backward
        if split_frame_p4_bwd is not None:
            ax.axvspan(split_frame_p4_bwd, f_end, color="#ff8a65", alpha=0.06, zorder=0)
            ax.axvline(split_frame_p4_bwd, color="#f4511e", linestyle="--", linewidth=1.0, alpha=0.4, zorder=1)

        if show_labels:
            y_min, y_max = ax.get_ylim()
            y_pos = y_max - (y_max - y_min) * 0.07
            if split_frame is not None:
                ax.text(f_start + (split_frame - f_start) * 0.03, y_pos, "PHASE 1 (ALIGN)",
                        fontsize=8.0, fontweight="bold", color="#555555", alpha=0.9, zorder=3)
                ax.text(split_frame + (p2_end - split_frame) * 0.02, y_pos, f"PHASE 2 (DRIVE, F={int(split_frame)})",
                        fontsize=8.0, fontweight="bold", color="#1565c0", alpha=0.9, zorder=3)
            if split_frame_p3 is not None:
                ax.text(split_frame_p3 + (p3_end - split_frame_p3) * 0.02, y_pos, f"PH3 (FINAL, F={int(split_frame_p3)})",
                        fontsize=8.0, fontweight="bold", color="#7b1fa2", alpha=0.9, zorder=3)
            if split_frame_p4_fwd is not None:
                ax.text(split_frame_p4_fwd + (p4_fwd_end - split_frame_p4_fwd) * 0.02, y_pos, f"PH4-FWD (F={int(split_frame_p4_fwd)})",
                        fontsize=8.0, fontweight="bold", color="#00838f", alpha=0.9, zorder=3)
            if split_frame_p4_bwd is not None:
                ax.text(split_frame_p4_bwd + (f_end - split_frame_p4_bwd) * 0.02, y_pos, f"PH4-BWD (F={int(split_frame_p4_bwd)})",
                        fontsize=8.0, fontweight="bold", color="#d84315", alpha=0.9, zorder=3)

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

    for idx, ax in enumerate(axes1):
        apply_phase_shading(ax, show_labels=(idx == 0))

    plt.tight_layout()
    out_fig1 = os.path.join(save_dir, f"{filename_stem}_pid_analysis.png")
    plt.savefig(out_fig1, dpi=300)
    plt.close(fig1)
    print(f"[SAVED] PID & Angle chart: {out_fig1}")

    # =========================================================================
    # FIGURE 2: DETAILED DIFFERENTIAL & ANGLE ERROR ANALYSIS (THEO CHỈ ĐẠO CỦA THẦY)
    #   1. Error Angle with Tolerance Band (±20°)
    #   2. Comparison: Proportional Term (Kp * error) vs Derivative Term (Kd * diff(error))
    #   3. Wheel Speeds (v_L, v_R), Differential Speed (v_diff), and Ratio (v_diff / v_LR)
    # =========================================================================
    fig2, axes2 = plt.subplots(3, 1, figsize=(14, 11), sharex=True)
    fig2.suptitle(f"ERROR ANGLE, KP*ERROR vs KD*DIFF(ERROR) & DIFFERENTIAL VELOCITY ANALYSIS\nFile: {os.path.basename(csv_path)}", fontsize=14, fontweight="bold")

    # Subplot 1: Error Angle
    ax_d1 = axes2[0]
    tol_deg = int(round(heading_tolerance))
    if "angle_error" in df.columns:
        ax_d1.plot(frames, df["angle_error"], label="Error Angle e(t)", color="#d62728", linewidth=2.0, linestyle="-")
        ax_d1.axhline(0, color="black", linestyle="-", alpha=0.5)
        # Tolerance boundaries ±20 deg
        ax_d1.axhline(heading_tolerance, color="gray", linestyle="-", alpha=0.4, label=f"Tolerance ±{tol_deg} deg")
        ax_d1.axhline(-heading_tolerance, color="gray", linestyle="-", alpha=0.4)
        ax_d1.fill_between(frames, -heading_tolerance, heading_tolerance, color="#2ca02c", alpha=0.08, label=f"Tolerance Band (±{tol_deg}°)")
    ax_d1.set_ylabel("Error Angle (deg)", fontsize=11)
    ax_d1.set_title(f"1. Error Angle: e(t) = target_angle - fused_angle (Tolerance Band: ±{tol_deg}°)", fontsize=12, fontweight="bold")
    ax_d1.grid(True, linestyle="-", alpha=0.25)
    ax_d1.legend(loc="upper right", framealpha=0.9)

    # Subplot 2: Comparison of Kp*error vs Kd*diff(error) on same axis
    ax_d2 = axes2[1]
    p_term = kp_angle2 * df["angle_error"] if "angle_error" in df.columns else pd.Series([0.0] * len(df))
    d_term = kd_angle2 * err_diff
    total_pd = p_term + d_term

    ax_d2.plot(frames, p_term, label=f"Kp * error (P-term, Kp={kp_angle2})", color="#1f77b4", linewidth=1.8, linestyle="-")
    ax_d2.plot(frames, d_term, label=f"Kd * diff(error) (D-term, Kd={kd_angle2})", color="#ff7f0e", linewidth=1.8, linestyle="-")
    ax_d2.plot(frames, total_pd, label="Total (Kp*error + Kd*diff(error))", color="#2ca02c", linewidth=1.5, alpha=0.85, linestyle="-")
    ax_d2.axhline(0, color="black", linestyle="-", alpha=0.3)
    ax_d2.set_ylabel("Control Term Value", fontsize=11)
    ax_d2.set_title(f"2. Comparison: Proportional Term (Kp*error) vs Derivative Term (Kd*diff(error)) [Kp={kp_angle2}, Kd={kd_angle2}]", fontsize=12, fontweight="bold")
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

    for idx, ax in enumerate(axes2):
        apply_phase_shading(ax, show_labels=(idx == 0))

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
            if split_frame is not None:
                p2_pts = valid_coords[valid_coords["frame_id"] == split_frame]
                if len(p2_pts) > 0:
                    px = p2_pts["x_center"].iloc[0]
                    py = p2_pts["y_center"].iloc[0]
                    plt.scatter(px, py, color="#ff9800", marker="D", s=110, zorder=6, label=f"Phase 2 Start ({px:.0f}, {py:.0f})")
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

    # =========================================================================
    # FIGURE 4: PHASE 4 FORWARD/BACKWARD TRAJECTORY & 1ST-ORDER FIT HEADING
    # =========================================================================
    if "pid_mode" in df.columns and "x_center" in df.columns and "y_center" in df.columns:
        fwd_df = df[df["pid_mode"] == "PHASE_4_FORWARD"].dropna(subset=["x_center", "y_center"])
        bwd_df = df[df["pid_mode"] == "PHASE_4_BACKWARD"].dropna(subset=["x_center", "y_center"])

        if len(fwd_df) >= 3 or len(bwd_df) >= 3:
            # 16:9 aspect ratio matching camera frame (1280x720)
            fig4, ax4 = plt.subplots(figsize=(14, 7.875))

            fit_df = fwd_df if len(fwd_df) >= 3 else bwd_df
            x_pts = fit_df["x_center"].values
            y_pts = fit_df["y_center"].values
            t_norm = np.linspace(0.0, 1.0, len(fit_df))

            # Fit polynomial degree 1: x(t) = ax*t + bx, y(t) = ay*t + by
            px = np.polyfit(t_norm, x_pts, deg=1)
            py = np.polyfit(t_norm, y_pts, deg=1)

            dx_fit = float(px[0])
            dy_fit = float(py[0])
            # In image coords, -dy is upward Cartesian
            theta_fit_deg = float(np.degrees(np.arctan2(-dy_fit, dx_fit)))

            # Target heading: lấy từ PHASE_3_FINAL_ALIGNING rows (= --target-heading argument)
            trg_h = None
            if "target_angle" in df.columns and "pid_mode" in df.columns:
                p3_sub = df[df["pid_mode"] == "PHASE_3_FINAL_ALIGNING"]
                if len(p3_sub) > 0:
                    non_zero = p3_sub["target_angle"].dropna()
                    if len(non_zero) > 0:
                        trg_h = float(non_zero.iloc[0])
            # Fallback: Phase 4 FWD rows
            if trg_h is None and "target_angle" in fit_df.columns:
                non_zero = fit_df["target_angle"].dropna()
                non_zero = non_zero[non_zero != 0]
                if len(non_zero) > 0:
                    trg_h = float(non_zero.iloc[0])
            if trg_h is None:
                trg_h = 0.0

            heading_diff_deg = wrap_to_180(theta_fit_deg - trg_h)

            # Plot raw forward & backward trajectory points
            if len(fwd_df) > 0:
                ax4.scatter(fwd_df["x_center"], fwd_df["y_center"], color="#00897b", s=40, alpha=0.8,
                            label=f"Phase 4 Forward ({len(fwd_df)} pts)")
                ax4.plot(fwd_df["x_center"], fwd_df["y_center"], color="#00897b", linewidth=1.5, alpha=0.5)
            if len(bwd_df) > 0:
                ax4.scatter(bwd_df["x_center"], bwd_df["y_center"], color="#e64a19", s=40, alpha=0.8,
                            label=f"Phase 4 Backward ({len(bwd_df)} pts)")
                ax4.plot(bwd_df["x_center"], bwd_df["y_center"], color="#e64a19", linewidth=1.5, alpha=0.5)

            # Plot fitted line extended across full axis range
            t_eval = np.linspace(-0.5, 1.5, 100)
            x_line = np.polyval(px, t_eval)
            y_line = np.polyval(py, t_eval)
            ax4.plot(x_line, y_line, color="#d81b60", linestyle="--", linewidth=2.5,
                     label=f"Degree-1 Fit Line (Heading={theta_fit_deg:.1f}°)")

            # --- Zoom out: fixed axis range matching camera frame 1280x720, centered on data centroid ---
            all_x = np.concatenate([fwd_df["x_center"].values if len(fwd_df) > 0 else np.array([640]),
                                     bwd_df["x_center"].values if len(bwd_df) > 0 else np.array([640])])
            all_y = np.concatenate([fwd_df["y_center"].values if len(fwd_df) > 0 else np.array([360]),
                                     bwd_df["y_center"].values if len(bwd_df) > 0 else np.array([360])])
            cx_data = float(np.mean(all_x))
            cy_data = float(np.mean(all_y))

            # Half-widths: keep 16:9 ratio, show at least 300px margin around data spread
            data_spread = max(
                np.ptp(all_x) if len(all_x) > 1 else 0,
                np.ptp(all_y) if len(all_y) > 1 else 0,
                200.0,  # minimum spread so it's never too zoomed in
            )
            margin = max(data_spread * 0.7, 220.0)
            half_w = margin  # X half-width
            half_h = half_w * (720 / 1280)  # maintain 16:9

            # Clamp to camera frame [0, 1280] x [0, 720]
            x_lo = max(0, cx_data - half_w)
            x_hi = min(1280, cx_data + half_w)
            y_lo = max(0, cy_data - half_h)
            y_hi = min(720, cy_data + half_h)

            ax4.set_xlim(x_lo, x_hi)
            ax4.set_ylim(y_hi, y_lo)  # inverted Y (image coords)

            # Text box with comparison summary — white background
            textstr = "\n".join([
                r"$\mathbf{PHASE\ 4\ HEADING\ VERIFICATION}$",
                rf"Target Heading ($\mathbf{{\theta_{{target}}}}$): {trg_h:.2f}°",
                rf"Fitted Traj Heading ($\mathbf{{\theta_{{traj}}}}$): {theta_fit_deg:.2f}°",
                rf"Absolute Angle Error ($|\Delta \theta|$): {abs(heading_diff_deg):.2f}°",
                f"Fit Displacement: {np.hypot(dx_fit, dy_fit):.1f} px",
            ])
            props = dict(boxstyle='round,pad=0.6', facecolor='white', edgecolor='#555555', alpha=0.95)
            ax4.text(0.02, 0.04, textstr, transform=ax4.transAxes, fontsize=10.5,
                     verticalalignment='bottom', bbox=props, zorder=10)

            ax4.set_title(f"PHASE 4 FORWARD/BACKWARD TRAJECTORY & 1ST-ORDER FIT HEADING\nFile: {os.path.basename(csv_path)}",
                          fontsize=13, fontweight="bold")
            ax4.set_xlabel("X Coordinate (Pixel)", fontsize=11)
            ax4.set_ylabel("Y Coordinate (Pixel - Inverted)", fontsize=11)
            ax4.grid(True, linestyle="-", alpha=0.3)
            ax4.legend(loc="upper right", framealpha=0.9)

            out_fig4 = os.path.join(save_dir, f"{filename_stem}_phase4_fwd_bwd_heading.png")
            plt.savefig(out_fig4, dpi=300, bbox_inches="tight")
            plt.close(fig4)
            print(f"[SAVED] Phase 4 trajectory & heading estimation chart: {out_fig4}")



def main():
    parser = argparse.ArgumentParser(description="Tool for plotting PID & Navigation log data from Leanbot")
    parser.add_argument("--log", default="", help="Path to the CSV log file (if omitted, auto-selects the latest file in benchmark_logs/)")
    parser.add_argument("--all", action="store_true", help="Plot all CSV log files found in benchmark_logs/")
    parser.add_argument("--kd", type=float, default=None, help="Kd value for angle PID in phase 2 (auto-detected if omitted)")
    parser.add_argument("--out", default="", help="Output directory for chart images (default: <log_dir>/plots/)")
    args = parser.parse_args()

    local_benchmark_dir = Path(__file__).resolve().parent / "benchmark_logs"
    parent_benchmark_dir = Path(__file__).resolve().parent.parent / "benchmark"

    if args.log:
        target_csvs = [args.log]
    elif args.all:
        csv_files = glob.glob(str(local_benchmark_dir / "*.csv"))
        if not csv_files:
            csv_files = glob.glob(str(parent_benchmark_dir / "*.csv"))
        if not csv_files:
            print(f"[WARN] No CSV files found in {local_benchmark_dir} or {parent_benchmark_dir}")
            return
        target_csvs = sorted(csv_files)
        print(f"[INFO] Found {len(target_csvs)} log files to plot.")
    else:
        csv_files = glob.glob(str(local_benchmark_dir / "*.csv"))
        if not csv_files:
            csv_files = glob.glob(str(parent_benchmark_dir / "*.csv"))
        if not csv_files:
            print(f"[WARN] No CSV files found in {local_benchmark_dir} or {parent_benchmark_dir}")
            return
        target_csvs = [max(csv_files, key=os.path.getmtime)]
        print(f"[INFO] Auto-selected latest log file: {target_csvs[0]}")

    for target_csv in target_csvs:
        print(f"\n=== Processing: {os.path.basename(target_csv)} ===")
        try:
            plot_pid_log(target_csv, save_dir=args.out, kd_angle2=args.kd)
        except Exception as e:
            print(f"[ERROR] Failed to plot {target_csv}: {e}")


if __name__ == "__main__":
    main()
