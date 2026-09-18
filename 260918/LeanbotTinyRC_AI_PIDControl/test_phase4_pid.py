import sys
import os
import math
import numpy as np

# Add directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PID_controller import PositionPIDController, create_position_pid, wrap_to_180


def test_phase4_full_sequence():
    """Kiểm tra toàn bộ chuỗi: Phase 1 -> Phase 2 -> Phase 3 -> Phase 4 rfb trigger (2*3s) -> COMPLETED."""
    fwd_bwd_time = 3.0
    fwd_bwd_speed = 400
    pid = create_position_pid(
        dist_tolerance_px=10.0,
        heading_tolerance_deg=20.0,
        target_heading=90.0,
        heading_tolerance3_deg=5.0,
        settle_time_ms=200.0,
        fwd_bwd_time_s=fwd_bwd_time,
        fwd_bwd_speed=fwd_bwd_speed,
    )

    # 1. Start far away -> Phase 1
    sl, sr, dbg = pid.compute(100, 100, 45.0, 200, 100, current_time=0.0)
    assert dbg['state'] == PositionPIDController.PHASE_ALIGNING

    # 2. Reached destination distance -> Transitions to Phase 3 Final Aligning
    sl, sr, dbg = pid.compute(200, 100, 92.0, 200, 100, current_time=1.000)
    assert dbg['state'] == PositionPIDController.PHASE_FINAL_ALIGNING
    assert not dbg['is_completed']

    # 3. Angle holds in tolerance for 200ms -> Transitions to Phase 4 rfb!
    # At t = 1.100s (elapsed 100ms < 200ms)
    sl, sr, dbg = pid.compute(200, 100, 91.0, 200, 100, current_time=1.100)
    assert dbg['state'] == PositionPIDController.PHASE_FINAL_ALIGNING

    # At t = 1.205s (elapsed 205ms >= 200ms) -> Triggers Phase 4 Autonomous rfb!
    sl, sr, dbg = pid.compute(200, 100, 90.0, 200, 100, current_time=1.205)
    assert dbg['state'] == PositionPIDController.PHASE_FWD_BWD, f"Expected Phase 4 FWD_BWD, got {dbg['state']}"
    assert 'rfb_trigger' in dbg, "Should contain rfb_trigger in debug output!"
    assert dbg['rfb_trigger'] == (fwd_bwd_speed, int(fwd_bwd_time * 1000)), f"rfb_trigger mismatch: {dbg['rfb_trigger']}"
    assert sl == 0 and sr == 0, f"Autonomous speeds should be (0, 0), got ({sl}, {sr})"
    assert not dbg['is_completed']

    # 4. During Phase 4 Autonomous Drive (t = 1.205s + 3.0s = 4.205s) -> Remains FWD_BWD
    sl, sr, dbg = pid.compute(200, 90, 90.0, 200, 100, current_time=4.205)
    assert dbg['state'] == PositionPIDController.PHASE_FWD_BWD
    assert 'rfb_trigger' not in dbg, "rfb_trigger should only fire once!"
    assert sl == 0 and sr == 0
    assert not dbg['is_completed']

    # 5. After total duration (2 * 3.0s = 6.0s) -> at t = 1.205s + 6.01s = 7.215s -> Transitions to COMPLETED!
    sl, sr, dbg = pid.compute(200, 100, 90.0, 200, 100, current_time=7.215)
    assert dbg['state'] == PositionPIDController.PHASE_COMPLETED, f"Expected COMPLETED, got {dbg['state']}"
    assert dbg['is_completed']
    assert sl == 0 and sr == 0
    print("[PASS] Test 1: Full Phase 1 -> 2 -> 3 -> 4 Autonomous rfb (2*3s) -> COMPLETED Sequence Passed!")


def test_phase4_disabled_when_time_zero():
    """Kiểm tra khi fwd_bwd_time_s = 0.0 thì bỏ qua Phase 4, hoàn thành ngay sau Phase 3."""
    pid = create_position_pid(
        dist_tolerance_px=10.0,
        target_heading=90.0,
        heading_tolerance3_deg=5.0,
        settle_time_ms=200.0,
        fwd_bwd_time_s=0.0,
    )
    # Start at target
    sl, sr, dbg = pid.compute(200, 100, 90.0, 200, 100, current_time=1.000)
    assert dbg['state'] == PositionPIDController.PHASE_FINAL_ALIGNING
    
    # After 200ms -> Goes directly to COMPLETED
    sl, sr, dbg = pid.compute(200, 100, 90.0, 200, 100, current_time=1.205)
    assert dbg['state'] == PositionPIDController.PHASE_COMPLETED
    assert dbg['is_completed']
    print("[PASS] Test 2: Phase 4 Disabled when fwd_bwd_time_s = 0 Passed!")


def test_degree1_trajectory_heading_fit():
    """Kiểm tra thuật toán fit bậc 1 để tính góc heading quỹ đạo (90 độ và 45 độ)."""
    # Case A: Trajectory going straight UP in image coordinates (heading = 90 deg)
    # Image coords: X constant = 500, Y decreases from 400 to 200
    N = 50
    t_norm = np.linspace(0.0, 1.0, N)
    x_syn = 500.0 + np.random.normal(0, 0.2, N)  # small noise
    y_syn = 400.0 - 200.0 * t_norm + np.random.normal(0, 0.2, N)

    px = np.polyfit(t_norm, x_syn, deg=1)
    py = np.polyfit(t_norm, y_syn, deg=1)

    theta_fit = float(np.degrees(np.arctan2(-py[0], px[0])))
    assert abs(wrap_to_180(theta_fit - 90.0)) < 1.0, f"Expected ~90 deg, got {theta_fit:.2f} deg"
    print(f"[PASS] Test 3A: Degree-1 Trajectory Fit for 90 deg -> Result: {theta_fit:.2f} deg (Error < 1 deg)")

    # Case B: Trajectory going at 45 deg (X increases by 100, Y decreases by 100)
    x_syn45 = 500.0 + 100.0 * t_norm + np.random.normal(0, 0.2, N)
    y_syn45 = 400.0 - 100.0 * t_norm + np.random.normal(0, 0.2, N)

    px45 = np.polyfit(t_norm, x_syn45, deg=1)
    py45 = np.polyfit(t_norm, y_syn45, deg=1)

    theta_fit45 = float(np.degrees(np.arctan2(-py45[0], px45[0])))
    assert abs(wrap_to_180(theta_fit45 - 45.0)) < 1.0, f"Expected ~45 deg, got {theta_fit45:.2f} deg"
    print(f"[PASS] Test 3B: Degree-1 Trajectory Fit for 45 deg -> Result: {theta_fit45:.2f} deg (Error < 1 deg)")


if __name__ == "__main__":
    print("--- RUNNING PHASE 4 PID & HEADING FIT VERIFICATION TESTS ---")
    test_phase4_full_sequence()
    test_phase4_disabled_when_time_zero()
    test_degree1_trajectory_heading_fit()
    print("--- ALL PHASE 4 TESTS PASSED SUCCESSFULLY! ---")
