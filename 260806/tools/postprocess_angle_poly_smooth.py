import argparse
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SMOOTH_LENGTH = 30
SMOOTH_ORDER = 2

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def smooth_angle_window(window, angle, t_norm, poly_degree):
    window.append(float(angle))
    if len(window) > len(t_norm):
        window.pop(0)
    if len(window) == len(t_norm):
        unwrapped = np.degrees(np.unwrap(np.radians(window)))
        coefficients = np.polyfit(t_norm, unwrapped, deg=poly_degree)
        return float(np.polyval(coefficients, 1.0))
    return float(angle)


def resolve_raw_angle_column(dataframe):
    for column in ("raw_angle", "group1_angle", "angle"):
        if column in dataframe.columns:
            return column
    raise ValueError("CSV thi?u c?t raw angle: raw_angle, group1_angle ho?c angle.")


def add_angle_smoothing(dataframe, window_size=SMOOTH_LENGTH, poly_degree=SMOOTH_ORDER):
    required_columns = {"smooth_x", "smooth_y"}
    missing_columns = required_columns.difference(dataframe.columns)
    if missing_columns:
        raise ValueError(f"CSV thi?u c?t: {', '.join(sorted(missing_columns))}")

    output = dataframe.copy()
    raw_angle_column = resolve_raw_angle_column(output)
    raw_angle = output[raw_angle_column].astype(float)
    valid_mask = output["tracking_lost"].eq(0) if "tracking_lost" in output.columns else output["smooth_x"].notna() & output["smooth_y"].notna()

    smooth_angle = np.full(len(output), np.nan)
    raw_angle_smooth = np.full(len(output), np.nan)
    smooth_angle_smooth = np.full(len(output), np.nan)
    t_norm = np.linspace(0.0, 1.0, window_size)
    raw_angle_window = []
    smooth_angle_window_values = []
    previous_x = None
    previous_y = None
    previous_smooth_angle = 0.0
    valid_count = 0

    for row_index in np.flatnonzero(valid_mask.to_numpy()):
        current_x = float(output.at[row_index, "smooth_x"])
        current_y = float(output.at[row_index, "smooth_y"])
        valid_count += 1

        if previous_x is None:
            current_smooth_angle = 0.0
        else:
            delta_x = current_x - previous_x
            delta_y = current_y - previous_y
            if math.hypot(delta_x, delta_y) > 1e-5:
                current_smooth_angle = math.degrees(math.atan2(-delta_y, delta_x))
            elif valid_count >= window_size:
                current_smooth_angle = previous_smooth_angle
            else:
                current_smooth_angle = 0.0

        current_raw_angle = float(raw_angle.iloc[row_index])
        smooth_angle[row_index] = current_smooth_angle
        raw_angle_smooth[row_index] = smooth_angle_window(raw_angle_window, current_raw_angle, t_norm, poly_degree)
        smooth_angle_smooth[row_index] = smooth_angle_window(
            smooth_angle_window_values,
            current_smooth_angle,
            t_norm,
            poly_degree,
        )
        previous_x = current_x
        previous_y = current_y
        previous_smooth_angle = current_smooth_angle

    output["raw_angle"] = raw_angle
    output["raw_angle_smooth"] = raw_angle_smooth
    output["smooth_angle"] = smooth_angle
    output["smooth_angle_smooth"] = smooth_angle_smooth

    angle_columns = ["raw_angle", "raw_angle_smooth", "smooth_angle", "smooth_angle_smooth"]
    insert_index = output.columns.get_loc("smooth_y") + 1
    for column in angle_columns:
        values = output.pop(column)
        output.insert(insert_index, column, values)
        insert_index += 1
    return output


def process_csv(csv_path, suffix, window_size, poly_degree):
    data = pd.read_csv(csv_path)
    processed = add_angle_smoothing(data, window_size=window_size, poly_degree=poly_degree)
    output_path = csv_path.with_name(f"{csv_path.stem}{suffix}")
    processed.to_csv(output_path, index=False, float_format="%.6f")
    valid_rows = int(processed["tracking_lost"].eq(0).sum()) if "tracking_lost" in processed.columns else len(processed)
    print(f"[SUCCESS] {csv_path.name} -> {output_path.name} | valid={valid_rows}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="B? sung b?n c?t angle b?ng polynomial smooth offline.")
    parser.add_argument("csv_files", nargs="+", help="C?c CSV log g?c c?n t?i x? l?.")
    parser.add_argument("--suffix", default="_polynomial_order2_length30.csv")
    parser.add_argument("--window", type=int, default=SMOOTH_LENGTH)
    parser.add_argument("--degree", type=int, default=SMOOTH_ORDER)
    args = parser.parse_args()

    if args.window <= args.degree:
        parser.error("--window ph?i l?n h?n --degree.")

    for csv_file in args.csv_files:
        csv_path = Path(csv_file)
        if not csv_path.exists():
            parser.error(f"Kh?ng t?m th?y CSV: {csv_path}")
        process_csv(csv_path, args.suffix, args.window, args.degree)


if __name__ == "__main__":
    main()
