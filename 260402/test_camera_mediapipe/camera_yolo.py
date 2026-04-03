#!/usr/bin/env python3
"""
Simple person detection using YOLO (YOLOv8)
"""
import cv2
import time
from ultralytics import YOLO

def main():
    # Load YOLO model
    print("Loading YOLOv8 model...")
    model = YOLO("yolov8n.pt")  # nano model, fastest
    
    # Open camera
    cap = cv2.VideoCapture(1)  # Camera index 1
    
    if not cap.isOpened():
        print("Cannot open camera 1. Try camera 0 instead")
        cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Cannot open any camera")
        return
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    print("✓ Camera opened!")
    print("Press ESC or 'q' to exit\n")
    
    last_time = time.perf_counter()
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame = cv2.flip(frame, 1)
        
        # Run YOLO detection
        results = model(frame, conf=0.5)
        
        # Draw results
        annotated_frame = results[0].plot()
        
        # Calculate FPS
        current_time = time.perf_counter()
        delta = current_time - last_time
        fps = 1.0 / delta if delta > 0 else 0
        last_time = current_time
        
        # Count persons detected
        person_count = 0
        for result in results:
            for box in result.boxes:
                # Class 0 is person in COCO dataset
                if int(box.cls[0]) == 0:
                    person_count += 1
        
        # Add info
        cv2.putText(
            annotated_frame,
            f"FPS: {fps:.1f}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2,
        )
        cv2.putText(
            annotated_frame,
            f"Persons: {person_count}",
            (10, 70),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2,
        )
        
        cv2.imshow("YOLOv8 Person Detection", annotated_frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key in (27, ord("q")):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    print("\n✓ Done!")

if __name__ == "__main__":
    main()
