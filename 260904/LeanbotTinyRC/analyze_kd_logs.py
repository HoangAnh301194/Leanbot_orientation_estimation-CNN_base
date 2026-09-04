import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "benchmark_kd_analysis"
KD_FOLDERS = {
    "benchmark_logs": 0.0,
    "benchmark_logs_1": 0.005,
    "benchmark_logs_2": 0.01,
    "benchmark_logs_3": 0.02,
    "benchmark_logs_4": 0.04,
    "benchmark_logs_5": 0.08,
}


def elapsed_seconds(series):
    parsed = pd.to_timedelta(series.astype(str))
    elapsed = (parsed - parsed.iloc[0]).dt.total_seconds()
    return elapsed.where(elapsed >= 0, elapsed + 86400)


def sign_changes(values, threshold):
    signs = np.sign(np.where(np.abs(values) > threshold, values, 0))
    signs = signs[signs != 0]
    return int(np.sum(signs[1:] != signs[:-1])) if len(signs) > 1 else 0


def analyze_run(folder, kd, csv_path):
    data = pd.read_csv(csv_path)
    data["time_s"] = elapsed_seconds(data["timestamp"])
    phase1 = data[data["pid_mode"] == "PHASE_1_ALIGNING"].copy()
    phase2 = data[data["pid_mode"] == "PHASE_2_DRIVING"].copy()
    lost = bool((data["pid_mode"] == "LOST_TRACKING").any() or (data["tracking_lost"] == 1).any())
    valid = len(phase2) >= 30 and not lost
    measured = data[data["pid_mode"] != "LOST_TRACKING"]
    error = phase2["angle_error"].to_numpy(float)
    left = phase2["ble_speed_left"].to_numpy(float)
    right = phase2["ble_speed_right"].to_numpy(float)
    time = phase2["time_s"].to_numpy(float)
    error_step = np.diff(error, prepend=error[0]) if len(error) else np.array([])
    dt = np.diff(time) if len(time) > 1 else np.array([])
    error_rate = np.diff(error) / np.maximum(dt, 1e-6) if len(error) > 1 else np.array([])
    denominator = left + right
    usable = np.abs(denominator) > 1
    ratio = np.full(len(phase2), np.nan)
    ratio[usable] = (left[usable] - right[usable]) / denominator[usable]
    control_error = error[usable]
    control_step = error_step[usable]
    control_ratio = ratio[usable]
    if len(control_ratio) >= 3:
        regression = np.linalg.lstsq(
            np.column_stack([np.ones(len(control_error)), control_error, control_step]),
            control_ratio,
            rcond=None,
        )[0]
    else:
        regression = [np.nan, np.nan, np.nan]
    p_term = 0.02 * control_error
    d_term = kd * control_step
    d_ratio_mask = np.abs(p_term) > 0.01
    phase2_duration = time[-1] - time[0] if len(time) > 1 else 0.0
    speed_step = (np.abs(np.diff(left)) + np.abs(np.diff(right))) / 2 if len(left) > 1 else np.array([])
    zero_crossings = sign_changes(error, 0.5)
    steering_flips = sign_changes(control_ratio, 0.01)
    record = {
        "folder": folder,
        "kd": kd,
        "file": csv_path.name,
        "valid": valid,
        "exclusion_reason": "" if valid else "lost_tracking" if lost else "insufficient_phase_2",
        "total_rows": len(data),
        "phase1_rows": len(phase1),
        "phase2_rows": len(phase2),
        "duration_s": data["time_s"].iloc[-1],
        "phase1_duration_s": phase1["time_s"].iloc[-1] - phase1["time_s"].iloc[0] if len(phase1) > 1 else 0,
        "phase2_duration_s": phase2_duration,
        "final_distance_px": measured["distance_error"].iloc[-1],
        "min_distance_px": measured["distance_error"].min(),
        "angle_mae_deg": np.mean(np.abs(error)),
        "angle_rms_deg": np.sqrt(np.mean(error ** 2)),
        "angle_p95_abs_deg": np.quantile(np.abs(error), 0.95),
        "angle_max_abs_deg": np.max(np.abs(error)),
        "angle_zero_crossings": zero_crossings,
        "angle_zero_crossings_per_s": zero_crossings / phase2_duration if phase2_duration else np.nan,
        "angle_variation_deg_per_s": np.sum(np.abs(np.diff(error))) / phase2_duration if phase2_duration else np.nan,
        "angle_rate_rms_deg_s": np.sqrt(np.mean(error_rate ** 2)) if len(error_rate) else np.nan,
        "mean_abs_steering_ratio": np.mean(np.abs(control_ratio)),
        "p95_abs_steering_ratio": np.quantile(np.abs(control_ratio), 0.95),
        "steering_sign_changes": steering_flips,
        "steering_sign_changes_per_s": steering_flips / phase2_duration if phase2_duration else np.nan,
        "speed_step_mae_units": np.mean(speed_step) if len(speed_step) else np.nan,
        "speed_step_p95_units": np.quantile(speed_step, 0.95) if len(speed_step) else np.nan,
        "speed_variation_units_per_s": np.sum(speed_step) / phase2_duration if phase2_duration else np.nan,
        "saturated_samples_pct": 100 * np.mean(np.maximum(np.abs(left), np.abs(right)) >= 1999),
        "inner_wheel_below_500_pct": 100 * np.mean(np.minimum(left, right) < 500),
        "opposite_wheel_direction_pct": 100 * np.mean(left * right < 0),
        "corr_angle_steering": np.corrcoef(control_error, control_ratio)[0, 1],
        "corr_abs_angle_wheel_gap": np.corrcoef(np.abs(error), np.abs(left - right))[0, 1],
        "fitted_intercept": regression[0],
        "fitted_kp_angle2": regression[1],
        "fitted_kd_angle2": regression[2],
        "mean_abs_p_term": np.mean(np.abs(p_term)),
        "mean_abs_d_term": np.mean(np.abs(d_term)),
        "p95_abs_d_term": np.quantile(np.abs(d_term), 0.95),
        "d_to_p_mean_ratio": np.mean(np.abs(d_term[d_ratio_mask] / p_term[d_ratio_mask])) if d_ratio_mask.any() else np.nan,
        "d_reverses_p_pct": 100 * np.mean(
            np.sign(p_term[d_ratio_mask] + d_term[d_ratio_mask]) != np.sign(p_term[d_ratio_mask])
        ) if d_ratio_mask.any() else 0,
    }
    return record, phase2.assign(steering_ratio=ratio, angle_step=error_step)


OUTPUT.mkdir(exist_ok=True)
records = []
phase2_data = {}
for folder, kd in KD_FOLDERS.items():
    for csv_path in sorted((ROOT / folder).glob("*.csv")):
        record, phase2 = analyze_run(folder, kd, csv_path)
        records.append(record)
        phase2_data[(folder, csv_path.name)] = phase2

run_metrics = pd.DataFrame(records)
valid_runs = run_metrics[run_metrics["valid"]].copy()
numeric_columns = valid_runs.select_dtypes(include="number").columns.drop("kd")
means = valid_runs.groupby("kd")[numeric_columns].mean().add_suffix("_mean")
stds = valid_runs.groupby("kd")[numeric_columns].std(ddof=0).fillna(0).add_suffix("_sd")
summary = pd.concat([
    valid_runs.groupby("kd").size().rename("valid_runs"),
    means,
    stds,
], axis=1).reset_index()
run_metrics.to_csv(OUTPUT / "run_metrics.csv", index=False)
summary.to_csv(OUTPUT / "kd_summary.csv", index=False)

plt.rcParams.update({"font.size": 9, "axes.grid": True, "grid.alpha": 0.25})
comparison_metrics = [
    ("angle_mae_deg", "Phase 2 angle error", "Angle MAE (deg)"),
    ("speed_step_mae_units", "Wheel command variation", "Mean speed step per frame"),
    ("steering_sign_changes_per_s", "Correction direction changes", "Sign changes per second"),
    ("duration_s", "Run duration", "Seconds"),
    ("inner_wheel_below_500_pct", "Inner wheel below 500", "Samples percent"),
    ("d_to_p_mean_ratio", "D magnitude relative to P", "Mean D to P ratio"),
]
figure, axes = plt.subplots(3, 2, figsize=(14, 10), constrained_layout=True)
for axis, (metric, title, ylabel) in zip(axes.flat, comparison_metrics):
    axis.errorbar(
        summary["kd"],
        summary[f"{metric}_mean"],
        yerr=summary[f"{metric}_sd"],
        marker="o",
        linewidth=2,
        capsize=4,
    )
    axis.set_title(title, fontweight="bold")
    axis.set_xlabel("Kd_angle2")
    axis.set_ylabel(ylabel)
    axis.set_xticks(summary["kd"])
figure.suptitle(
    "Leanbot oscillation comparison by Kd_angle2\nMean +/- standard deviation across valid runs",
    fontsize=16,
    fontweight="bold",
)
figure.savefig(OUTPUT / "kd_comparison.png", dpi=180)
plt.close(figure)

figure, axes = plt.subplots(3, 2, figsize=(14, 10), constrained_layout=True)
colors = plt.cm.tab10(np.linspace(0, 1, len(KD_FOLDERS)))
for axis, ((folder, kd), color) in zip(axes.flat, zip(KD_FOLDERS.items(), colors)):
    selected = run_metrics[(run_metrics["folder"] == folder) & run_metrics["valid"]]
    for _, run in selected.iterrows():
        phase2 = phase2_data[(folder, run["file"])]
        sample = phase2.iloc[::max(1, len(phase2) // 350)]
        axis.scatter(sample["angle_error"], sample["steering_ratio"], s=10, alpha=0.28, color=color)
    angle_line = np.linspace(-60, 60, 200)
    axis.plot(angle_line, 0.02 * angle_line, "k--", linewidth=1.5, label="P-only")
    axis.set_xlim(-60, 60)
    axis.set_ylim(-1.25, 1.25)
    axis.set_title(f"Kd={kd:g} - {len(selected)} runs", fontweight="bold")
    axis.set_xlabel("angle_error (deg)")
    axis.set_ylabel("(L-R)/(L+R)")
figure.suptitle(
    "Phase 2 angle versus differential wheel command\nScatter around P-only line shows D response to angle change",
    fontsize=16,
    fontweight="bold",
)
figure.savefig(OUTPUT / "speed_angle_relationship.png", dpi=180)
plt.close(figure)

folder = "benchmark_logs_1"
logs1 = run_metrics[run_metrics["folder"] == folder]
figure, axes = plt.subplots(2, 2, figsize=(15, 8), constrained_layout=True)
for axis, (_, run) in zip(axes.flat, logs1.iterrows()):
    phase2 = phase2_data[(folder, run["file"])]
    time = phase2["time_s"] - phase2["time_s"].iloc[0]
    axis.plot(time, phase2["angle_error"], color="tab:red", linewidth=2)
    speed_axis = axis.twinx()
    speed_axis.plot(time, phase2["ble_speed_left"], color="tab:blue", alpha=0.65)
    speed_axis.plot(time, phase2["ble_speed_right"], color="tab:green", alpha=0.65)
    axis.axhline(0, color="black", linewidth=0.8)
    status = "valid" if run["valid"] else "lost tracking"
    axis.set_title(f"{run['file']} - {status}", fontweight="bold")
    axis.set_xlabel("Phase 2 time (s)")
    axis.set_ylabel("Angle error (deg)", color="tab:red")
    speed_axis.set_ylabel("Wheel command", color="tab:blue")
figure.suptitle("benchmark_logs_1 - Kd_angle2=0.005", fontsize=16, fontweight="bold")
figure.savefig(OUTPUT / "benchmark_logs_1_detail.png", dpi=180)
plt.close(figure)

compact_runs = run_metrics[[
    "kd", "file", "valid", "exclusion_reason", "duration_s", "phase2_duration_s",
    "final_distance_px", "angle_mae_deg", "angle_p95_abs_deg",
    "angle_zero_crossings_per_s", "speed_step_mae_units",
    "steering_sign_changes_per_s", "inner_wheel_below_500_pct",
    "fitted_kp_angle2", "fitted_kd_angle2", "d_to_p_mean_ratio",
]].round(4)
compact_summary = summary[[
    "kd", "valid_runs", "duration_s_mean", "angle_mae_deg_mean",
    "angle_p95_abs_deg_mean", "angle_zero_crossings_per_s_mean",
    "speed_step_mae_units_mean", "steering_sign_changes_per_s_mean",
    "inner_wheel_below_500_pct_mean", "saturated_samples_pct_mean",
    "d_to_p_mean_ratio_mean", "d_reverses_p_pct_mean",
    "fitted_kp_angle2_mean", "fitted_kd_angle2_mean",
]].round(4)
print(json.dumps({
    "runs": compact_runs.to_dict(orient="records"),
    "summary": compact_summary.to_dict(orient="records"),
}, ensure_ascii=False, indent=2))
