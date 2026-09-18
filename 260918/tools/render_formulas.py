import os
import matplotlib.pyplot as plt

os.makedirs('formulas', exist_ok=True)

def render_math(latex_str, basename):
    # 1. Render Light Mode version (Black text, larger fontsize 28, 300 DPI)
    fig_light = plt.figure(figsize=(12, 2.0), dpi=300)
    fig_light.text(0.5, 0.5, f"${latex_str}$", fontsize=28, ha='center', va='center', color='#111111')
    plt.axis('off')
    path_light = os.path.join('formulas', f"{basename}_light.png")
    plt.savefig(path_light, bbox_inches='tight', pad_inches=0.15, transparent=True)
    plt.close()

    # 2. Render Dark Mode version (White text, larger fontsize 28, 300 DPI)
    fig_dark = plt.figure(figsize=(12, 2.0), dpi=300)
    fig_dark.text(0.5, 0.5, f"${latex_str}$", fontsize=28, ha='center', va='center', color='#f0f0f0')
    plt.axis('off')
    path_dark = os.path.join('formulas', f"{basename}_dark.png")
    plt.savefig(path_dark, bbox_inches='tight', pad_inches=0.15, transparent=True)
    plt.close()

    print(f"Rendered extra enlarged: {path_light} & {path_dark}")

# Formula 1: Trajectory 2D EMA
f1 = r"S_{x, t} = \alpha \cdot x_t + (1 - \alpha) \cdot S_{x, t-1}, \quad S_{y, t} = \alpha \cdot y_t + (1 - \alpha) \cdot S_{y, t-1}"
render_math(f1, "formula_ema_xy")

# Formula 2: Vectorized Angle EMA
f2_1 = r"v_{\sin, t} = \sin(\theta_t), \quad v_{\cos, t} = \cos(\theta_t)"
render_math(f2_1, "formula_ema_vector_trig")

f2_2 = r"S_{\sin, t} = \alpha v_{\sin, t} + (1 - \alpha) S_{\sin, t-1}, \quad S_{\cos, t} = \alpha v_{\cos, t} + (1 - \alpha) S_{\cos, t-1}"
render_math(f2_2, "formula_ema_vector_smooth")

f2_3 = r"\theta_{\text{EMA\_Vector}, t} = \text{atan2}(S_{\sin, t}, S_{\cos, t})"
render_math(f2_3, "formula_ema_vector_atan")

# Formula 3: Tangent Angle from EMA Trajectory
f3 = r"\Delta x_{\text{EMA}} = S_{x, t} - S_{x, t-1}, \quad \Delta y_{\text{EMA}} = S_{y, t} - S_{y, t-1}"
render_math(f3, "formula_ema_traj_diff")

f3_atan = r"\theta_{\text{EMA\_Traj}, t} = \text{atan2}(-\Delta y_{\text{EMA}}, \Delta x_{\text{EMA}})"
render_math(f3_atan, "formula_ema_traj_atan")

print("All extra enlarged formula images rendered successfully!")
