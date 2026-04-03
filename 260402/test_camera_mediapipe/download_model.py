#!/usr/bin/env python3
"""Download MediaPipe Pose Landmarker model using MediaPipe's downloader."""

import sys
from pathlib import Path

try:
    import mediapipe_tasks as mptasks
    from mediapipe_tasks.python.tasks.vision import pose_landmarker
except ImportError:
    print("mediapipe_tasks not available. Trying alternative download method...")

# Alternative: try using urllib with headers
import urllib.request
import shutil

# Official GitHub releases
GITHUB_URL = "https://github.com/google-ai-edge/mediapipe/releases/download/v0.10.0/pose_landmarker_lite.task"

MODEL_PATH = Path(__file__).resolve().parent / "models" / "pose_landmarker_lite.task"

print(f"Downloading pose landmarker model from GitHub releases...")
print(f"Saving to: {MODEL_PATH}")

try:
    # Add headers to mimic a browser request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    request = urllib.request.Request(GITHUB_URL, headers=headers)
    
    with urllib.request.urlopen(request) as response, open(MODEL_PATH, 'wb') as out_file:
        shutil.copyfileobj(response, out_file)
    
    print(f"✓ Model downloaded successfully!")
    print(f"  File size: {MODEL_PATH.stat().st_size / (1024*1024):.1f} MB")
except Exception as e:
    print(f"✗ Error downloading model: {e}")
    print("\nManual download instructions:")
    print("1. Visit: https://github.com/google-ai-edge/mediapipe/releases")
    print("2. Find the pose_landmarker_lite.task file")
    print("3. Download and place in models/pose_landmarker_lite.task")
    exit(1)
