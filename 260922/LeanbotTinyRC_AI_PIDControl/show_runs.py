"""Hiển thị lịch sử Set Target và các phiên chạy thực nghiệm đã ghi log."""

import os
import csv
import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

base_dir = os.path.dirname(os.path.abspath(__file__))
history_json = os.path.join(base_dir, "target_history.json")
index_csv = os.path.join(base_dir, "benchmark_logs", "experiment_index.csv")

print("=" * 75)
print(" 1. LỊCH SỬ CÁC LẦN SET TARGET (Phím T)")
print("=" * 75)
if os.path.exists(history_json):
    try:
        with open(history_json, "r") as f:
            targets = json.load(f)
        if targets:
            print(f"{'ID':<4} | {'Calibrated At':<20} | {'Target Pos (X, Y)':<20} | {'Heading':<10} | {'Pts':<5}")
            print("-" * 75)
            for t in targets:
                pos_str = f"({t.get('target_x', 0)}, {t.get('target_y', 0)})"
                head_str = f"{t.get('target_heading', 0):.1f}°"
                print(f"{t.get('target_id', 0):<4} | {t.get('calibrated_at', ''):<20} | {pos_str:<20} | {head_str:<10} | {t.get('trajectory_points', 0):<5}")
        else:
            print(" (Chưa có bản ghi nào)")
    except Exception as e:
        print(f" Lỗi đọc target_history.json: {e}")
else:
    print(" (Chưa có file target_history.json)")

print("\n" + "=" * 85)
print(" 2. MỤC LỤC CÁC PHIÊN CHẠY THỰC NGHIỆM (Phím S -> Log File)")
print("=" * 85)
if os.path.exists(index_csv):
    try:
        with open(index_csv, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        if rows:
            print(f"{'Log File':<28} | {'Target Heading':<14} | {'Target (X, Y)':<18} | {'PID (Kp, Kd)':<14}")
            print("-" * 85)
            for r in rows:
                pos = f"({r.get('target_x','')}, {r.get('target_y','')})"
                h = f"{r.get('target_heading_deg','')}°"
                pid = f"({r.get('kp_angle','')}, {r.get('kd_angle','')})"
                print(f"{r.get('log_file',''):<28} | {h:<14} | {pos:<18} | {pid:<14}")
        else:
            print(" (Chưa có phiên chạy nào được ghi)")
    except Exception as e:
        print(f" Lỗi đọc experiment_index.csv: {e}")
else:
    print(" (Chưa có file benchmark_logs/experiment_index.csv)")
print("=" * 85 + "\n")
