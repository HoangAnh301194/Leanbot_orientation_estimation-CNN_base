import os
import pandas as pd
import numpy as np
from datetime import datetime

runs_dir = r'D:\PTIT\DTT\Nguyen_Huu_Hoang_Anh\260703\runs'

# Lấy 2 file mới nhất
files = sorted([f for f in os.listdir(runs_dir) if f.endswith('.csv')])
spin_files = files[-2:]

for fname in spin_files:
    fpath = os.path.join(runs_dir, fname)
    df = pd.read_csv(fpath)
    df_g1 = df[df['group_id']==1].copy()
    t0 = datetime.strptime(df.iloc[0]['timestamp'], '%H:%M:%S.%f')
    t1 = datetime.strptime(df.iloc[-1]['timestamp'], '%H:%M:%S.%f')
    diff = (t1-t0).total_seconds()
    fps = len(df)/diff if diff>0 else 0
    
    angles = df_g1['angle'].values
    print(f"\n=== {fname} ===")
    print(f"FPS: {fps:.1f} | Frames: {len(df_g1)} | Duration: {diff:.1f}s")
    print(f"Angle range: min={angles.min():.1f}° max={angles.max():.1f}°")
    print(f"First 5 angles: {[f'{a:.1f}' for a in angles[:5]]}")
    print(f"Last 5 angles: {[f'{a:.1f}' for a in angles[-5:]]}")
    # Tính "hướng xoay" bằng cách đếm bước angle tăng vs giảm
    diffs = np.diff(angles)
    # Loại bỏ jump lớn (qua biên ±180)
    diffs_clean = diffs[np.abs(diffs) < 90]
    trend = np.sum(diffs_clean)
    print(f"Trend (+ = CCW / counter-clockwise, - = CW / clockwise): {trend:.1f}")
