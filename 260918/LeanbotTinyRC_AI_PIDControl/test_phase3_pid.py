import sys
import os
import time
import math
import argparse
from pathlib import Path
import cv2
import numpy as np
import openvino as ov
from ultralytics import YOLO

# Add directories to sys.path
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
sys.path.insert(0, str(current_dir / "LeanbotTinyRC"))
sys.path.append(str(current_dir))
sys.path.append(str(parent_dir / "tools"))
sys.path.append(str(parent_dir))

from PID_controller import PositionPIDController, create_position_pid, wrap_to_180
import check_confidence
from angle_smoothing import AngleSmoothingEngine
from leanbotCameraController import (
    BLEMotorWorker,
    select_best_vector_detection,
    calculate_roi,
    box_iou_numpy,
    IOU_THRES,
)


def resolve_path(p: str) -> str:
    if not p:
        return p
    if os.path.isabs(p) and os.path.exists(p):
        return p
    if os.path.exists(p):
        return p
    alt1 = os.path.join(str(parent_dir), p)
    if os.path.exists(alt1):
        return alt1
    alt2 = os.path.join(str(current_dir), p)
    if os.path.exists(alt2):
        return alt2
    return p


def run_unit_tests():
    """Chạy các bài kiểm tra logic toán học của Phase 3 (không cần Camera hay BLE)."""
    print("\n" + "=" * 60)
    print(" [UNIT TEST] RUNNING PHASE 3 PID LOGIC VERIFICATION TESTS")
    print("=" * 60)

    # Test 1: Backward compatibility
    pid1 = create_position_pid(dist_tolerance_px=10.0, heading_tolerance_deg=20.0, target_heading=None)
    sl, sr, dbg = pid1.compute(100, 100, 45.0, 200, 100, current_time=0.0)
    assert dbg['state'] == PositionPIDController.PHASE_ALIGNING
    sl, sr, dbg = pid1.compute(100, 100, 0.0, 200, 100, current_time=0.05)
    assert dbg['state'] == PositionPIDController.PHASE_DRIVING
    sl, sr, dbg = pid1.compute(195, 100, 0.0, 200, 100, current_time=0.10)
    assert dbg['state'] == PositionPIDController.PHASE_COMPLETED
    print("[PASS] Test 1: Backward Compatibility (2-phase mode) Passed!")

    # Test 2: Phase 3 transition and spin in place
    pid2 = create_position_pid(
        dist_tolerance_px=10.0, heading_tolerance_deg=20.0,
        target_heading=90.0, heading_tolerance3_deg=5.0,
        settle_time_ms=200.0, Kp_angle=15.0,
    )
    sl, sr, dbg = pid2.compute(200, 100, 0.0, 200, 100, current_time=1.0)
    assert dbg['state'] == PositionPIDController.PHASE_FINAL_ALIGNING
    assert dbg['v_lr'] == 0.0
    assert sl == -sr and sl != 0
    print("[PASS] Test 2: Phase 3 Transition & In-place Spin Passed!")

    # Test 3: Settle time logic
    settle_ms = 200.0
    pid3 = create_position_pid(
        dist_tolerance_px=10.0,
        heading_tolerance_deg=20.0,
        target_heading=90.0,
        heading_tolerance3_deg=5.0,
        settle_time_ms=settle_ms,
        Kp_angle=15.0,
        fwd_bwd_time_s=0.0,
    )
    sl, sr, dbg = pid3.compute(200, 100, 45.0, 200, 100, current_time=0.0)
    assert dbg['state'] == PositionPIDController.PHASE_FINAL_ALIGNING
    assert pid3._within_tolerance_since is None

    t_enter = 0.100
    sl, sr, dbg = pid3.compute(200, 100, 92.0, 200, 100, current_time=t_enter)
    assert not dbg['is_completed']
    assert pid3._within_tolerance_since == t_enter

    sl, sr, dbg = pid3.compute(200, 100, 91.0, 200, 100, current_time=0.200)
    assert not dbg['is_completed']

    sl, sr, dbg = pid3.compute(200, 100, 100.0, 200, 100, current_time=0.250)
    assert not dbg['is_completed']
    assert pid3._within_tolerance_since is None

    t_reenter = 0.300
    sl, sr, dbg = pid3.compute(200, 100, 89.0, 200, 100, current_time=t_reenter)
    assert not dbg['is_completed']
    assert pid3._within_tolerance_since == t_reenter

    sl, sr, dbg = pid3.compute(200, 100, 90.0, 200, 100, current_time=0.450)
    assert not dbg['is_completed']

    sl, sr, dbg = pid3.compute(200, 100, 90.5, 200, 100, current_time=0.505)
    assert dbg['is_completed']
    assert dbg['state'] == PositionPIDController.PHASE_COMPLETED
    assert sl == 0 and sr == 0
    print("[PASS] Test 3: Settle Time (200ms) Stabilization Logic Passed!")

    # Test 4: Independent PID gains
    pid4 = create_position_pid(
        dist_tolerance_px=10.0,
        heading_tolerance_deg=5.0,
        target_heading=90.0,
        heading_tolerance3_deg=2.0,
        settle_time_ms=200.0,
        Kp_angle=20.0,
        Kp_angle3=5.0,
        fwd_bwd_time_s=0.0,
    )
    sl1, sr1, dbg1 = pid4.compute(100, 100, 10.0, 200, 100, current_time=0.0)
    assert abs(dbg1['v_diff'] - 200.0) < 1e-3
    sl3, sr3, dbg3 = pid4.compute(200, 100, 100.0, 200, 100, current_time=1.0)
    assert abs(dbg3['v_diff'] - 50.0) < 1e-3
    print("[PASS] Test 4: Phase 1 & Phase 3 Independent PID Gains Passed!")

    print("\n" + "=" * 60)
    print(" [ALL UNIT TESTS PASSED SUCCESSFULLY!]")
    print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Phase 3 Live PID Test Runner: Test xoay goc tai cho truc tiep voi Camera va BLE (Khong xuat CSV, khong ve plot)."
    )
    # Tham so goc muc tieu va BLE
    parser.add_argument("--target-heading", type=float, default=0.0, help="Goc muc tieu Phase 3 (deg), vi du: 90.0, -45.0, 180.0")
    parser.add_argument("--ble", type=int, default=0, help="Leanbot BLE ID (vi du: 343944). Neu 0 thi chi test camera mo phong.")

    # Tham so PID Phase 3
    parser.add_argument("--kp3", type=float, default=10.0, help="Kp cho Phase 3 xoay tai cho (default 10.0)")
    parser.add_argument("--kd3", type=float, default=0.04, help="Kd cho Phase 3 xoay tai cho (default 0.04)")
    parser.add_argument("--ki3", type=float, default=0.0, help="Ki cho Phase 3 (default 0.0)")
    parser.add_argument("--tol3", type=float, default=5.0, help="Dung sai goc Phase 3 (deg, default 5.0)")
    parser.add_argument("--settle", type=float, default=200.0, help="Thoi gian giu on dinh trong dac tinh dung sai (ms, default 200.0)")
    parser.add_argument("--max-speed", type=int, default=1500, help="Toc do quay toi da (default 1500)")
    parser.add_argument("--min-speed", type=int, default=250, help="Toc do khoi dong toi thieu vuot ma sat tinh (default 250)")

    # Tham so Camera & Inference
    parser.add_argument("--source", default="1", help="Camera index hoac video path (default 1)")
    parser.add_argument("--width", type=int, default=1280, help="Camera width (default 1280)")
    parser.add_argument("--height", type=int, default=720, help="Camera height (default 720)")
    parser.add_argument("--mode", default="roi", choices=["roi", "baseline"], help="Mode: roi hoac baseline")
    parser.add_argument("--device", default="CPU", choices=["CPU", "GPU", "AUTO"], help="OpenVINO device (default CPU)")
    parser.add_argument("--full-model", default=r"models\yolo11n_latest_version\best_fp16_no_nms_imgsz640_openvino_model", help="Path to 640 OpenVINO model")
    parser.add_argument("--tracking-model", default=r"models\yolo11n_latest_version\best_fp16_no_nms_imgsz160_openvino_model", help="Path to 160 OpenVINO model")
    parser.add_argument("--no-show", action="store_true", help="Tat man hinh OpenCV GUI")
    parser.add_argument("--unit-test", action="store_true", help="Chay unit tests kiem tra logic Phase 3 (khong bat camera/BLE)")

    args = parser.parse_args()

    if args.unit_test:
        run_unit_tests()
        return

    print("=" * 65)
    print(" [PHASE 3 LIVE PID TEST RUNNER]")
    print(f"  * Target Heading  : {args.target_heading:.1f} deg (Truyen qua CLI)")
    print(f"  * BLE ID          : {args.ble if args.ble > 0 else 'OFF (Simulation mode)'}")
    print(f"  * Phase 3 Gains   : Kp3={args.kp3}, Ki3={args.ki3}, Kd3={args.kd3}")
    print(f"  * Tolerance & Settle: Tol3={args.tol3} deg, SettleTime={args.settle} ms")
    print(f"  * Speed Range     : Min={args.min_speed}, Max={args.max_speed}")
    print(f"  * Device / Mode   : {args.device} | {args.mode.upper()}")
    print("  * I/O Logging     : NONE (Toi uu FPS, khong ghi CSV, khong ve plot)")
    print("=" * 65)
    print("  Controls: [S] Start/Restart test | [P] Pause/Stop motors | [Q] Quit")
    print("=" * 65)

    # 1. Khoi tao BLE Worker (neu co truyen BLE ID)
    ble_worker = BLEMotorWorker(args.ble) if args.ble > 0 else None

    # 2. Khoi tao Model OpenVINO
    full_model_path = resolve_path(args.full_model)
    tracking_model_path = resolve_path(args.tracking_model)
    core = ov.Core()

    print(f"[INFO] Loading full model: {full_model_path} on {args.device}...")
    full_compiled = core.compile_model(os.path.join(full_model_path, "best_fp16_no_nms_imgsz640.xml"), args.device)
    tracking_compiled = None
    if args.mode == "roi":
        print(f"[INFO] Loading ROI tracking model: {tracking_model_path} on {args.device}...")
        tracking_compiled = core.compile_model(os.path.join(tracking_model_path, "best_fp16_no_nms_imgsz160.xml"), args.device)

    # Load class names
    try:
        full_model = YOLO(full_model_path, task='detect')
        names = full_model.names
    except Exception:
        names = {i: f"Leanbot_{i}" for i in range(360)}

    # 3. Khoi tao Camera
    try:
        cam_source = int(args.source)
    except ValueError:
        cam_source = args.source

    cap = cv2.VideoCapture(cam_source)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)

    if not cap.isOpened():
        print(f"[ERROR] Cannot open camera source: {args.source}")
        if ble_worker:
            ble_worker.stop()
        return

    # 4. Khoi tao Bo dieu khien PID
    pos_pid = create_position_pid(
        dist_tolerance_px=10.0,
        heading_tolerance_deg=20.0,
        target_heading=args.target_heading,
        heading_tolerance3_deg=args.tol3,
        settle_time_ms=args.settle,
        Kp_angle3=args.kp3,
        Kd_angle3=args.kd3,
        Ki_angle3=args.ki3,
        max_velocity=args.max_speed,
    )
    # Dat truc tiep vao Phase 3
    pos_pid.phase = PositionPIDController.PHASE_FINAL_ALIGNING
    pos_pid._within_tolerance_since = None

    smoothing_engine = AngleSmoothingEngine(window_size=18, eval_index=5, K=0.03)

    is_running_test = True
    prev_roi = None
    prev_bbox_xyxy = None

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[WARN] Failed to read frame from camera.")
                time.sleep(0.01)
                continue

            current_time = time.perf_counter()
            img_h, img_w = frame.shape[:2]

            # Tracking / Detection
            inference_mode = "FULL"
            offset_x, offset_y = 0, 0
            roi_scale_x, roi_scale_y = 1.0, 1.0

            if args.mode == "roi" and prev_roi is not None:
                inference_mode = "ROI"
                rx, ry, rw, rh = prev_roi
                offset_x, offset_y = rx, ry
                roi_input = frame[ry:ry + rh, rx:rx + rw]
                inference_input = cv2.resize(roi_input, (160, 160))
                roi_scale_x = rw / 160.0
                roi_scale_y = rh / 160.0
                infer_model = tracking_compiled
                conf_val = 0.15
            else:
                crop_w = int(img_w * 0.625)
                crop_h = img_h
                start_x = (img_w - crop_w) // 2
                cropped = frame[0:crop_h, start_x:start_x + crop_w]
                square_size = max(crop_w, crop_h)
                padded = np.zeros((square_size, square_size, 3), dtype=np.uint8)
                pad_top = (square_size - crop_h) // 2
                pad_left = (square_size - crop_w) // 2
                padded[pad_top:pad_top + crop_h, pad_left:pad_left + crop_w] = cropped
                inference_input = cv2.resize(padded, (640, 640))
                params = {
                    'start_x': start_x,
                    'pad_top': pad_top,
                    'pad_left': pad_left,
                    'crop_w': crop_w,
                    'scale': 640.0 / square_size,
                }
                infer_model = full_compiled
                conf_val = 0.25

            box, best_conf, raw_angle, mag, _, _ = select_best_vector_detection(
                infer_model, inference_input, names,
                conf_thres=conf_val, topk=100, iou_thres=IOU_THRES,
            )

            if inference_mode == "FULL":
                box = check_confidence.restore_boxes_from_training_style(box.reshape(1, 4), params)[0]

            detected = mag > 0
            cx, cy = 0.0, 0.0
            display_box = None

            if detected:
                if inference_mode == "ROI":
                    box = box.copy()
                    box[[0, 2]] *= roi_scale_x
                    box[[1, 3]] *= roi_scale_y
                x1 = int(box[0] + offset_x)
                y1 = int(box[1] + offset_y)
                x2 = int(box[2] + offset_x)
                y2 = int(box[3] + offset_y)
                cx = (x1 + x2) / 2.0
                cy = (y1 + y2) / 2.0
                display_box = (x1, y1, x2, y2)
                if args.mode == "roi":
                    prev_roi = calculate_roi([x1, y1, x2, y2], img_w, img_h)
            else:
                prev_roi = None

            smooth_res = smoothing_engine.update(raw_angle, cx, cy, detected)
            if smooth_res["fused_angle"] is not None:
                current_heading = smooth_res["fused_angle"]
                angle_src = "FUSED"
            elif smooth_res["model_angle_smooth"] is not None:
                current_heading = smooth_res["model_angle_smooth"]
                angle_src = "SMOOTH"
            else:
                current_heading = raw_angle
                angle_src = "RAW"

            # --- Tinh toan PID Phase 3 ---
            speed_l, speed_r = 0, 0
            ang_err = 0.0
            settle_pct = 0.0
            is_completed = False

            if detected and is_running_test:
                ang_err = wrap_to_180(current_heading - args.target_heading)
                # Tinh PID thong qua controller (gia lap khoang cach = 0 de o trong Phase 3)
                speed_l, speed_r, dbg = pos_pid.compute(cx, cy, current_heading, cx, cy, current_time)
                is_completed = dbg['is_completed']

                # Minimum speed kick de vuot qua ma sat tinh neu sai so goc con lon hon dung sai
                if not is_completed and abs(speed_l) > 0 and abs(speed_l) < args.min_speed:
                    speed_l = int(math.copysign(args.min_speed, speed_l))
                    speed_r = -speed_l

                # Tinh % thoi gian settle
                if pos_pid._within_tolerance_since is not None:
                    elapsed_settle = (current_time - pos_pid._within_tolerance_since) * 1000.0
                    settle_pct = min(100.0, (elapsed_settle / args.settle) * 100.0)

                # Gui lenh BLE
                if ble_worker is not None:
                    ble_worker.send_speed(speed_l, speed_r)
            else:
                if ble_worker is not None:
                    ble_worker.send_speed(0, 0)

            # --- Visual OSD ---
            if not args.no_show:
                vis = frame.copy()

                # Ve Robot BBox va Vector goc
                if display_box is not None:
                    bx1, by1, bx2, by2 = display_box
                    cv2.rectangle(vis, (bx1, by1), (bx2, by2), (255, 100, 0), 2)
                    center_pt = (int(cx), int(cy))

                    # 1. Vector goc hien tai cua robot (Mau xanh duong/cam)
                    cur_rad = math.radians(current_heading)
                    arrow_cur = (int(cx + 60 * math.cos(cur_rad)), int(cy - 60 * math.sin(cur_rad)))
                    cv2.arrowedLine(vis, center_pt, arrow_cur, (0, 140, 255), 3, tipLength=0.25)

                    # 2. Vector goc muc tieu (Target heading - Mau xanh la cay)
                    tgt_rad = math.radians(args.target_heading)
                    arrow_tgt = (int(cx + 80 * math.cos(tgt_rad)), int(cy - 80 * math.sin(tgt_rad)))
                    cv2.arrowedLine(vis, center_pt, arrow_tgt, (0, 255, 0), 3, tipLength=0.25)

                # OSD Header Panel
                panel_h = 175
                cv2.rectangle(vis, (15, 15), (560, 15 + panel_h), (20, 20, 20), -1)
                cv2.rectangle(vis, (15, 15), (560, 15 + panel_h), (80, 80, 80), 2)

                status_text = "COMPLETED (SUCCESS)" if is_completed else ("ALIGNING..." if is_running_test else "PAUSED")
                status_color = (0, 255, 0) if is_completed else ((0, 220, 255) if is_running_test else (0, 0, 255))

                cv2.putText(vis, "PHASE 3 LIVE PID TEST", (25, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
                cv2.putText(vis, f"Status: {status_text}", (25, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.65, status_color, 2)
                cv2.putText(vis, f"Target Heading : {args.target_heading:6.1f} deg", (25, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 1)
                cv2.putText(vis, f"Current Heading: {current_heading:6.1f} deg [{angle_src}]", (25, 118), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 140, 255), 1)
                cv2.putText(vis, f"Angle Error    : {ang_err:6.1f} deg (Tol: +/-{args.tol3} deg)", (25, 141), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)
                cv2.putText(vis, f"Motor Speed    : L={speed_l:5d}, R={speed_r:5d} | Settle: {settle_pct:3.0f}%", (25, 164), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

                cv2.imshow("Phase 3 PID Test Runner", vis)
                key = cv2.waitKey(1) & 0xFF

                if key in (ord('q'), ord('Q')):
                    print("\n[INFO] Exiting Phase 3 Test...")
                    break
                elif key in (ord('p'), ord('P')):
                    is_running_test = False
                    if ble_worker:
                        ble_worker.send_speed(0, 0)
                    print("\n[INFO] TEST PAUSED. Motors stopped. Press S to restart.")
                elif key in (ord('s'), ord('S')):
                    pos_pid.reset()
                    pos_pid.phase = PositionPIDController.PHASE_FINAL_ALIGNING
                    pos_pid._within_tolerance_since = None
                    is_running_test = True
                    print(f"\n[INFO] RESTARTING TEST: Heading={args.target_heading:.1f} deg, Kp3={args.kp3}, Kd3={args.kd3}")

    except KeyboardInterrupt:
        pass
    finally:
        if ble_worker:
            ble_worker.send_speed(0, 0)
            ble_worker.stop()
        cap.release()
        if not args.no_show:
            cv2.destroyAllWindows()
        print("[INFO] Cleanup complete. Phase 3 Test Runner finished.")


if __name__ == "__main__":
    main()
