import os
from PIL import Image, ImageSequence
import sys

gif_path = r'D:\PTIT\DTT\Nguyen_Huu_Hoang_Anh\260824\LeanbotTinyRC\benchmark_logs\demo_point_to_point.gif'
out_path = r'D:\PTIT\DTT\Nguyen_Huu_Hoang_Anh\260824\LeanbotTinyRC\benchmark_logs\demo_point_to_point_small.gif'

print("Loading GIF...")
img = Image.open(gif_path)
frames = [frame.copy() for frame in ImageSequence.Iterator(img)]
print(f"Original frames: {len(frames)}")

# 1. Keep every 3rd frame (speed up 3x, reduces frame count)
frames = frames[::3]

# 2. Resize frames and reduce colors
new_frames = []
for i, frame in enumerate(frames):
    # Resize to 50% width
    w, h = frame.size
    new_w = 320
    new_h = int(h * (new_w / w))
    frame = frame.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    # Convert to 64 colors to save space
    frame = frame.convert('P', palette=Image.ADAPTIVE, colors=64)
    new_frames.append(frame)

print(f"Processed frames: {len(new_frames)}")

print("Saving optimized GIF...")
# duration is in ms. If original was e.g. 66ms, we skipped 3, so to keep same visual speed duration = 66*3 = ~200ms.
# To make it look faster and snappier, let's set duration to 100ms (10 fps)
new_frames[0].save(
    out_path,
    save_all=True,
    append_images=new_frames[1:],
    optimize=True,
    duration=100,
    loop=0
)

print(f"Done! New size: {os.path.getsize(out_path) / (1024*1024):.2f} MB")
