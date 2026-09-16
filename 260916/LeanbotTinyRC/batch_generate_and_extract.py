import os
import glob
import json
from pathlib import Path
import pandas as pd
import numpy as np

from plot_pid_navigation_log import plot_pid_log

BASE_DIR = Path(__file__).resolve().parent

KD_FOLDERS = [
    ("2.1", "0.0", "benchmark_logs_00", 0.0),
    ("2.2", "0.005", "benchmark_logs_0005", 0.005),
    ("2.3", "0.01", "benchmark_logs_001", 0.01),
    ("2.4", "0.02", "benchmark_logs_002", 0.02),
    ("2.5", "0.04", "benchmark_logs_004", 0.04),
    ("2.6", "0.06", "benchmark_logs_006", 0.06),
    ("2.7", "0.08", "benchmark_logs_008", 0.08),
]


def elapsed_seconds(series):
    parsed = pd.to_timedelta(series.astype(str))
    elapsed = (parsed - parsed.iloc[0]).dt.total_seconds()
    return elapsed.where(elapsed >= 0, elapsed + 86400)


def extract_metrics(csv_path: Path):
    df = pd.read_csv(csv_path)
    time_s = elapsed_seconds(df["timestamp"])
    df["time_s"] = time_s

    total_rows = len(df)
    total_time = time_s.iloc[-1] - time_s.iloc[0] if total_rows > 1 else 0.0

    p1 = df[df["pid_mode"] == "PHASE_1_ALIGNING"]
    p2 = df[df["pid_mode"] == "PHASE_2_DRIVING"]

    p1_rows = len(p1)
    p1_time = (p1["time_s"].iloc[-1] - p1["time_s"].iloc[0]) if p1_rows > 1 else 0.0

    p2_rows = len(p2)
    p2_time = (p2["time_s"].iloc[-1] - p2["time_s"].iloc[0]) if p2_rows > 1 else 0.0

    # final distance error
    valid_dist = df[df["distance_error"].notnull() & (df["distance_error"] > 0)]
    final_dist = valid_dist["distance_error"].iloc[-1] if len(valid_dist) > 0 else 0.0

    # Angle metrics in Phase 2
    if p2_rows > 0:
        angle_err = p2["angle_error"].dropna().to_numpy()
        mae_angle = float(np.mean(np.abs(angle_err)))
        rms_angle = float(np.sqrt(np.mean(angle_err**2)))
        max_angle = float(np.max(np.abs(angle_err)))

        # sign changes
        signs = np.sign(np.where(np.abs(angle_err) > 0.5, angle_err, 0))
        signs = signs[signs != 0]
        zero_cross = int(np.sum(signs[1:] != signs[:-1])) if len(signs) > 1 else 0

        # Steering diff
        v_L = p2["ble_speed_left"].to_numpy()
        v_R = p2["ble_speed_right"].to_numpy()
        v_sum = np.abs(v_L + v_R)
        v_diff = (v_L - v_R) / 2.0
        mask = v_sum > 10
        ratio = np.where(mask, v_diff / (v_sum / 2.0), 0.0)
        signs_steer = np.sign(np.where(np.abs(ratio) > 0.01, ratio, 0))
        signs_steer = signs_steer[signs_steer != 0]
        steer_flips = int(np.sum(signs_steer[1:] != signs_steer[:-1])) if len(signs_steer) > 1 else 0

        dt = np.diff(p2["time_s"].to_numpy())
        dt = np.where((dt > 0.001) & (dt < 1.0), dt, 0.05)
        d_err = np.diff(angle_err)
        rate = d_err / np.maximum(dt, 1e-4) if len(dt) > 0 else np.array([])
        rate_rms = float(np.sqrt(np.mean(rate**2))) if len(rate) > 0 else 0.0
    else:
        mae_angle = rms_angle = max_angle = zero_cross = steer_flips = rate_rms = 0.0

    return {
        "csv_name": csv_path.name,
        "total_time": round(total_time, 1),
        "total_frames": total_rows,
        "p1_time": round(p1_time, 1),
        "p1_frames": p1_rows,
        "p2_time": round(p2_time, 1),
        "p2_frames": p2_rows,
        "final_dist": round(final_dist, 1),
        "mae_angle": round(mae_angle, 2),
        "rms_angle": round(rms_angle, 2),
        "max_angle": round(max_angle, 1),
        "zero_crossings": zero_cross,
        "steer_flips": steer_flips,
        "rate_rms": round(rate_rms, 1),
    }


def find_matching_ui_image(folder_path: Path, csv_name: str):
    mc_dir = folder_path / "manual_captures"
    if not mc_dir.exists():
        return None

    ts_part = csv_name.replace("log_roi_", "").replace(".csv", "")
    matches = list(mc_dir.glob(f"*{ts_part}*detection_ui.png"))
    if matches:
        return matches[0]

    all_uis = sorted(list(mc_dir.glob("*detection_ui.png")), key=lambda p: p.stat().st_mtime)
    if all_uis:
        return all_uis[0]
    return None


def main():
    results = []

    for section_id, kd_str, folder_name, kd_val in KD_FOLDERS:
        fpath = BASE_DIR / folder_name
        if not fpath.exists():
            print(f"[WARN] Folder not found: {fpath}")
            continue

        csv_files = sorted(list(fpath.glob("*.csv")))
        print(f"\n=======================================================")
        print(f"Processing Section {section_id}: kd = {kd_str} ({len(csv_files)} files in {folder_name})")
        print(f"=======================================================")

        runs = []
        for idx, csv_file in enumerate(csv_files, 1):
            print(f"\n--- Run {idx}: {csv_file.name} (kd={kd_val}) ---")
            plots_dir = fpath / "plots"
            plots_dir.mkdir(exist_ok=True)

            # Generate all 3 plots
            plot_pid_log(str(csv_file), save_dir=str(plots_dir), kd_angle2=kd_val, heading_tolerance=20.0)

            # Extract metrics
            metrics = extract_metrics(csv_file)

            # Find matching UI capture
            ui_img = find_matching_ui_image(fpath, csv_file.name)
            ui_rel = str(ui_img.relative_to(BASE_DIR)).replace("\\", "/") if ui_img else ""

            stem = csv_file.stem
            traj_rel = f"LeanbotTinyRC/{folder_name}/plots/{stem}_2d_trajectory.png"
            pid_rel = f"LeanbotTinyRC/{folder_name}/plots/{stem}_pid_analysis.png"
            diff_rel = f"LeanbotTinyRC/{folder_name}/plots/{stem}_pid_diff_analysis.png"

            runs.append({
                "run_idx": idx,
                "metrics": metrics,
                "ui_img": f"LeanbotTinyRC/{ui_rel}" if ui_rel else "",
                "traj_img": traj_rel,
                "pid_img": pid_rel,
                "diff_img": diff_rel,
            })

        results.append({
            "section_id": section_id,
            "kd_str": kd_str,
            "folder_name": folder_name,
            "kd_val": kd_val,
            "runs": runs,
        })

    with open(BASE_DIR / "summary_kd_runs.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n[SUCCESS] Completed batch processing and generated summary_kd_runs.json!")


if __name__ == "__main__":
    main()
