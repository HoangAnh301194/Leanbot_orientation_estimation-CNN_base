import os
import pandas as pd
from datetime import datetime
from pathlib import Path

runs_dir = Path(__file__).resolve().parents[1] / 'runs'
files = sorted([f for f in os.listdir(runs_dir) if f.endswith('.csv')])
print('Found', len(files), 'CSV files\n')
for i, fname in enumerate(files):
    fpath = os.path.join(runs_dir, fname)
    try:
        df = pd.read_csv(fpath)
        if df.empty: continue
        df_g1 = df[df['group_id']==1]
        t0 = datetime.strptime(df.iloc[0]['timestamp'], '%H:%M:%S.%f')
        t1 = datetime.strptime(df.iloc[-1]['timestamp'], '%H:%M:%S.%f')
        diff = (t1-t0).total_seconds()
        fps = len(df)/diff if diff>0 else 0
        ang = df_g1['angle'].mean() if not df_g1.empty else 0
        n_frames = len(df_g1)
        print(f'Case {i+1}: {fname} | FPS: {fps:.1f} | Avg Angle: {ang:.1f} | Frames: {n_frames}')
    except Exception as e:
        print(f'Error {fname}: {e}')
