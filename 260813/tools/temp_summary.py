import os
import pandas as pd
from datetime import datetime

runs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'runs')
fname = 'webcam_vector_log_20260703_123113.csv'
fpath = os.path.join(runs_dir, fname)
df = pd.read_csv(fpath)
df_g1 = df[df['group_id']==1]
t0 = datetime.strptime(df.iloc[0]['timestamp'], '%H:%M:%S.%f')
t1 = datetime.strptime(df.iloc[-1]['timestamp'], '%H:%M:%S.%f')
diff = (t1-t0).total_seconds()
fps = len(df)/diff if diff>0 else 0
print(f"File: {fname}")
print(f"FPS: {fps:.1f} | Frames: {len(df_g1)} | Duration: {diff:.1f}s")
print(f"Angle range: {df_g1['angle'].min():.1f} -> {df_g1['angle'].max():.1f}")
