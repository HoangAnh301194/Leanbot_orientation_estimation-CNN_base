import pandas as pd

in_file = r"D:\PTIT\DTT\Nguyen_Huu_Hoang_Anh\260930\LeanbotTinyRC_AI_PIDControl\heading_survey_results\heading_survey_20260930_162531.csv"
out_file = r"D:\PTIT\DTT\Nguyen_Huu_Hoang_Anh\260930\LeanbotTinyRC_AI_PIDControl\heading_survey_results\heading_survey_20260930_162531_filtered.csv"

df = pd.read_csv(in_file)
# Filter only steps <= 60 as requested
df_filtered = df[df['steps'] <= 60]

df_filtered.to_csv(out_file, index=False)
print(f"Saved {len(df_filtered)} samples (steps 0 to 60).")
