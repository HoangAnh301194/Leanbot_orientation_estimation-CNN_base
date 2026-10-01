import sys
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
in_file = r"D:\PTIT\DTT\Nguyen_Huu_Hoang_Anh\260930\LeanbotTinyRC_AI_PIDControl\heading_survey_results\heading_survey_20260930_162531.csv"
df = pd.read_csv(in_file)

flipped = df[df['heading'] > 90]
print(f"Tổng cộng có {len(flipped)} lần đo bị lật góc 180 độ (>90 độ).")
print("Chi tiết các bước bắt đầu bị lỗi:")
for steps in sorted(flipped['steps'].unique()):
    count = len(flipped[flipped['steps'] == steps])
    total = len(df[df['steps'] == steps])
    print(f" - Tại steps = {steps}: Lỗi {count}/{total} lần đo.")
