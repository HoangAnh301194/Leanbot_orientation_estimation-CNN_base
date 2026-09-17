import sys
import os

# Add directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PID_controller import PositionPIDController, create_position_pid


def test_backward_compatibility():
    """Kiểm tra khi không truyền target_heading (None) thì hoạt động 2 pha như cũ."""
    pid = create_position_pid(
        dist_tolerance_px=10.0,
        heading_tolerance_deg=20.0,
        target_heading=None,
        fwd_bwd_time_s=0.0,
    )
    
    # 1. Start far away: Target at (200, 100), Start at (100, 100) -> dx = 100, dy = 0 -> heading = 0 deg
    # Current angle is 45 deg -> angle error = 45 deg > 20 deg -> Phase 1 Aligning
    sl, sr, dbg = pid.compute(100, 100, 45.0, 200, 100, current_time=0.0)
    assert dbg['state'] == PositionPIDController.PHASE_ALIGNING, f"Expected Phase 1, got {dbg['state']}"
    assert not dbg['is_completed']

    # 2. Angle aligned to 0 deg -> Transitions to Phase 2 Driving
    sl, sr, dbg = pid.compute(100, 100, 0.0, 200, 100, current_time=0.05)
    assert dbg['state'] == PositionPIDController.PHASE_DRIVING, f"Expected Phase 2, got {dbg['state']}"

    # 3. Arrive at destination (dist <= 10px) -> Transitions directly to COMPLETED
    sl, sr, dbg = pid.compute(195, 100, 0.0, 200, 100, current_time=0.10)
    assert dbg['state'] == PositionPIDController.PHASE_COMPLETED, f"Expected COMPLETED, got {dbg['state']}"
    assert dbg['is_completed']
    assert sl == 0 and sr == 0
    print("[PASS] Test 1: Backward Compatibility (2-phase mode) Passed!")


def test_phase3_transition_and_spin_in_place():
    """Kiểm tra chuyển sang Phase 3 khi tới đích và xe chỉ xoay tại chỗ (v_lr = 0)."""
    pid = create_position_pid(
        dist_tolerance_px=10.0,
        heading_tolerance_deg=20.0,
        target_heading=90.0,
        heading_tolerance3_deg=5.0,
        settle_time_ms=200.0,
        Kp_angle=15.0,
        fwd_bwd_time_s=0.0,
    )
    
    # Simulate already at destination: (200, 100) vs (200, 100), current angle 0 deg
    sl, sr, dbg = pid.compute(200, 100, 0.0, 200, 100, current_time=1.0)
    
    # Must enter Phase 3
    assert dbg['state'] == PositionPIDController.PHASE_FINAL_ALIGNING, f"Expected Phase 3, got {dbg['state']}"
    assert not dbg['is_completed']
    assert dbg['target_heading'] == 90.0
    # In Phase 3: v_lr must be 0 (spin in place)
    assert dbg['v_lr'] == 0.0
    # Left and right wheel speeds must be opposite for pure in-place spinning
    assert sl == -sr, f"Left ({sl}) and Right ({sr}) wheel speeds should be symmetric in Phase 3!"
    assert sl != 0, "Speed must be non-zero to correct 90-deg heading error"
    print("[PASS] Test 2: Phase 3 Transition & In-place Spin Passed!")


def test_phase3_settle_time_logic():
    """Kiểm tra điều kiện giữ ổn định trong dải tolerance ít nhất 200ms trước khi complete."""
    settle_ms = 200.0
    pid = create_position_pid(
        dist_tolerance_px=10.0,
        heading_tolerance_deg=20.0,
        target_heading=90.0,
        heading_tolerance3_deg=5.0,  # [85.0, 95.0]
        settle_time_ms=settle_ms,
        Kp_angle=15.0,
        fwd_bwd_time_s=0.0,
    )

    # Move to target location, start Phase 3 with angle = 45 deg (out of tolerance)
    sl, sr, dbg = pid.compute(200, 100, 45.0, 200, 100, current_time=0.0)
    assert dbg['state'] == PositionPIDController.PHASE_FINAL_ALIGNING
    assert pid._within_tolerance_since is None

    # Step 1: Robot enters tolerance: angle = 92.0 deg (error = 2.0 deg <= 5.0 deg) at t = 0.100s
    t_enter = 0.100
    sl, sr, dbg = pid.compute(200, 100, 92.0, 200, 100, current_time=t_enter)
    assert not dbg['is_completed'], "Should NOT complete immediately upon entering tolerance"
    assert pid._within_tolerance_since == t_enter

    # Step 2: At t = 0.200s (elapsed 100ms < 200ms)
    sl, sr, dbg = pid.compute(200, 100, 91.0, 200, 100, current_time=0.200)
    assert not dbg['is_completed'], "Should NOT complete at 100ms"

    # Step 3: Robot overshoots or is disturbed out of tolerance: angle = 100.0 deg (> 95 deg) at t = 0.250s
    sl, sr, dbg = pid.compute(200, 100, 100.0, 200, 100, current_time=0.250)
    assert not dbg['is_completed']
    assert pid._within_tolerance_since is None, "Timer must be reset when error exceeds tolerance3!"

    # Step 4: Robot enters tolerance again at t = 0.300s: angle = 89.0 deg
    t_reenter = 0.300
    sl, sr, dbg = pid.compute(200, 100, 89.0, 200, 100, current_time=t_reenter)
    assert not dbg['is_completed']
    assert pid._within_tolerance_since == t_reenter

    # Step 5: At t = 0.450s (elapsed 150ms < 200ms)
    sl, sr, dbg = pid.compute(200, 100, 90.0, 200, 100, current_time=0.450)
    assert not dbg['is_completed']

    # Step 6: At t = 0.505s (elapsed 205ms >= 200ms)
    sl, sr, dbg = pid.compute(200, 100, 90.5, 200, 100, current_time=0.505)
    assert dbg['is_completed'], "Should COMPLETE after holding in tolerance for >= 200ms!"
    assert dbg['state'] == PositionPIDController.PHASE_COMPLETED
    assert sl == 0 and sr == 0
    print("[PASS] Test 3: Settle Time (200ms) Stabilization Logic Passed!")


if __name__ == "__main__":
    print("--- RUNNING PHASE 3 PID VERIFICATION TESTS ---")
    test_backward_compatibility()
    test_phase3_transition_and_spin_in_place()
    test_phase3_settle_time_logic()
    print("--- ALL TESTS PASSED SUCCESSFULLY! ---")
