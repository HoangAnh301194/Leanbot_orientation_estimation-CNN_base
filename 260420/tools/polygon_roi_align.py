import cv2
import numpy as np
import sys
import time
import argparse
from pathlib import Path

# Setup paths for importing libraries
BASE_DIR = Path(__file__).parent.parent
sys.path.append(str(Path(__file__).parent))      # tools

from alignment import ImageAligner
from mask_roi import select_four_points, build_mask

def main():
    parser = argparse.ArgumentParser(description="Unified Polygon ROI and ECC Alignment Pipeline")
    parser.add_argument("--source", type=str, default="0", help="Camera index or video file path")
    parser.add_argument("--width", type=int, default=2560, help="Camera width")
    parser.add_argument("--height", type=int, default=1440, help="Camera height")
    args = parser.parse_args()

    # 1. Initialize Camera
    source = int(args.source) if args.source.isdigit() else args.source
    cap = cv2.VideoCapture(source)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)

    if not cap.isOpened():
        print(f"Error: Cannot open source {args.source}")
        return

    # Get first frame for ROI selection
    ret, initial_frame = cap.read()
    if not ret:
        print("Error: Cannot read from camera")
        cap.release()
        return

    print("--- STEP 1: INTERACTIVE ROI SELECTION ---")
    print("Please click 4 corners of the board. Press ENTER to confirm, C to clear.")
    pts = select_four_points(initial_frame)
    if pts is None:
        print("Selection cancelled. Exiting.")
        cap.release()
        return

    # 2. Setup Background and Mask
    print("\n--- STEP 2: BACKGROUND REGISTRATION ---")
    mask = build_mask(initial_frame.shape, pts)
    # Apply mask to the initial frame to create the reference background
    bg_masked = cv2.bitwise_and(initial_frame, initial_frame, mask=mask)
    
    aligner = ImageAligner()
    aligner.set_template(bg_masked)
    print("Background registered successfully.")

    # 3. Main Processing Loop
    print("\n--- STEP 3: REAL-TIME PIPELINE STARTED ---")
    print("Press 'q' or 'ESC' to exit.")

    scale_disp = 3.0 # Scale for display windows
    disp_w = int(args.width / scale_disp)
    disp_h = int(args.height / scale_disp)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # A. Apply Mask to current frame
        frame_masked = cv2.bitwise_and(frame, frame, mask=mask)

        # B. Perform Alignment
        try:
            result = aligner.align(frame_masked)
            aligned = result['aligned']
            cc = result['cc']
        except Exception as e:
            print(f"Alignment Error: {e}")
            aligned = frame_masked
            cc = 0.0

        # C. Compute Difference (Optional evaluation)
        # Using computed diff to visualize changes
        _, mask_diff, nz, avg = aligner.compute_diff(aligner.template_gray, aligned)

        # D. Visualization
        # Resize all for display
        view_orig = cv2.resize(frame, (disp_w, disp_h))
        view_aligned = cv2.resize(aligned, (disp_w, disp_h))
        view_diff = cv2.resize(mask_diff, (disp_w, disp_h))

        # Add text overlay
        cv2.putText(view_aligned, f"CC: {cc:.4f} | Time: {result['time_ms']:.1f}ms", 
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(view_diff, f"Diff Pixels: {nz}", 
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        cv2.imshow("Original Feed", view_orig)
        cv2.imshow("Aligned Board", view_aligned)
        cv2.imshow("Difference Mask", view_diff)

        if cv2.waitKey(1) & 0xFF in (ord('q'), 27):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("Pipeline stopped.")

if __name__ == "__main__":
    main()
