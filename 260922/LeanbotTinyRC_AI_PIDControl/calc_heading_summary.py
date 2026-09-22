import glob
import os
import pandas as pd
import numpy as np
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def wrap_to_180(angle_deg):
    return (angle_deg + 180.0) % 360.0 - 180.0

base_dir = os.path.dirname(os.path.abspath(__file__))
logs = sorted(glob.glob(os.path.join(base_dir, "benchmark_logs", "log_roi_*.csv")))
results = []

for log_path in logs:
    df = pd.read_csv(log_path)
    fn = os.path.basename(log_path)
    
    trg_h = float(df['target_angle'].iloc[-1]) if 'target_angle' in df.columns else np.nan
    
    fwd_df = df[df['pid_mode'] == 'PHASE_4_FORWARD']
    bwd_df = df[df['pid_mode'] == 'PHASE_4_BACKWARD']
    
    ph1_len = len(df[df['pid_mode'] == 'PHASE_1_ALIGNING'])
    ph2_len = len(df[df['pid_mode'] == 'PHASE_2_DRIVING'])
    ph3_len = len(df[df['pid_mode'] == 'PHASE_3_FINAL_ALIGNING'])
    fwd_len = len(fwd_df)
    bwd_len = len(bwd_df)
    lost_len = len(df[df['tracking_lost'] == 1]) if 'tracking_lost' in df.columns else 0
    
    theta_fit_deg = np.nan
    delta_theta = np.nan
    fit_disp = np.nan
    
    if len(fwd_df) >= 3 and len(bwd_df) >= 3:
        pts_x = np.concatenate([fwd_df['x_center'].values, bwd_df['x_center'].values])
        pts_y = np.concatenate([fwd_df['y_center'].values, bwd_df['y_center'].values])
        t_norm = np.linspace(0.0, 1.0, len(pts_x))
        px = np.polyfit(t_norm, pts_x, deg=1)
        py = np.polyfit(t_norm, pts_y, deg=1)
        dx_fit = px[0]
        dy_fit = py[0]
        theta_fit_deg = float(np.degrees(np.arctan2(-dy_fit, dx_fit)))
        heading_diff_deg = wrap_to_180(theta_fit_deg - trg_h)
        delta_theta = abs(heading_diff_deg)
        fit_disp = np.hypot(dx_fit, dy_fit)
        
    results.append({
        'file': fn,
        'target_h': trg_h,
        'theta_fit': theta_fit_deg,
        'delta_theta': delta_theta,
        'fit_disp_px': fit_disp,
        'ph1': ph1_len, 'ph2': ph2_len, 'ph3': ph3_len,
        'fwd': fwd_len, 'bwd': bwd_len, 'lost': lost_len,
        'total_frames': len(df)
    })

hdr = f"{'File':<27} | {'Tgt_H':<8} | {'Fit_H':<8} | {'|dTheta|':<8} | {'Disp(px)':<8} | {'Ph1':<4} | {'Ph2':<4} | {'Ph3':<4} | {'FWD':<4} | {'BWD':<4} | {'Lost':<4}"
print(hdr)
print("-" * len(hdr))
for r in results:
    th_s = f"{r['target_h']:.1f}°" if not np.isnan(r['target_h']) else "N/A"
    fit_s = f"{r['theta_fit']:.1f}°" if not np.isnan(r['theta_fit']) else "N/A"
    d_s = f"{r['delta_theta']:.2f}°" if not np.isnan(r['delta_theta']) else "N/A"
    disp_s = f"{r['fit_disp_px']:.1f}" if not np.isnan(r['fit_disp_px']) else "N/A"
    print(f"{r['file']:<27} | {th_s:<8} | {fit_s:<8} | {d_s:<8} | {disp_s:<8} | {r['ph1']:<4} | {r['ph2']:<4} | {r['ph3']:<4} | {r['fwd']:<4} | {r['bwd']:<4} | {r['lost']:<4}")
