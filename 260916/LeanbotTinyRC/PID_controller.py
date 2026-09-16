"""Two-phase PID position controller for Leanbot navigation to a fixed target pixel."""

import math
import time
from typing import Any, Dict, Optional, Tuple


MAX_VELOCITY = 2000
DEFAULT_DIST_TOLERANCE_PX = 10.0
DEFAULT_HEADING_TOLERANCE_DEG = 20.0  # Phase 1 heading tolerance
DEFAULT_HEADING_TOLERANCE3_DEG = 10.0  # Phase 3 narrower heading tolerance
DEFAULT_SETTLE_TIME_MS = 200.0  # Stability duration in ms before complete
DEFAULT_FWD_BWD_TIME_S = 3.0  # Duration in seconds for forward & backward test
DEFAULT_FWD_BWD_SPEED = 1000  # Wheel speed for forward & backward test


def wrap_to_180(angle_deg: float) -> float:
    return (angle_deg + 180.0) % 360.0 - 180.0


class PositionPIDController:
    """PID position controller with Phase 1 (aligning), Phase 2 (driving), Phase 3 (final aligning), and Phase 4 (fwd/bwd test)."""

    PHASE_ALIGNING = 'PHASE_1_ALIGNING'
    PHASE_ALIGN_COMPLETE = 'PHASE_1_COMPLETE'
    PHASE_DRIVING = 'PHASE_2_DRIVING'
    PHASE_FINAL_ALIGNING = 'PHASE_3_FINAL_ALIGNING'
    PHASE_FORWARD = 'PHASE_4_FORWARD'
    PHASE_BACKWARD = 'PHASE_4_BACKWARD'
    PHASE_COMPLETED = 'COMPLETED'

    def __init__(
        self,
        Kp_dist: float = 25.0,
        Ki_dist: float = 0.0,
        Kd_dist: float = 0.0,
        Kp_angle: float = 15.0,
        Ki_angle: float = 0.0,
        Kd_angle: float = 0.0,
        Kp_angle2: float = 0.02,
        Ki_angle2: float = 0.0,
        Kd_angle2: float = 0.0,
        max_velocity: int = MAX_VELOCITY,
        dist_tolerance_px: float = DEFAULT_DIST_TOLERANCE_PX,
        heading_tolerance_deg: float = DEFAULT_HEADING_TOLERANCE_DEG,
        target_heading: Optional[float] = None,
        heading_tolerance3_deg: float = DEFAULT_HEADING_TOLERANCE3_DEG,
        settle_time_ms: float = DEFAULT_SETTLE_TIME_MS,
        fwd_bwd_time_s: float = DEFAULT_FWD_BWD_TIME_S,
        fwd_bwd_speed: int = DEFAULT_FWD_BWD_SPEED,
    ):
        # PID gains - distance
        self.Kp_dist = Kp_dist
        self.Ki_dist = Ki_dist
        self.Kd_dist = Kd_dist
        # PID gains - angle (Phase 1: aligning, also reused for Phase 3)
        self.Kp_angle = Kp_angle
        self.Ki_angle = Ki_angle
        self.Kd_angle = Kd_angle
        # PID gains - angle (Phase 2: driving)
        self.Kp_angle2 = Kp_angle2
        self.Ki_angle2 = Ki_angle2
        self.Kd_angle2 = Kd_angle2

        self.max_velocity = max_velocity
        self.dist_tolerance = dist_tolerance_px
        self.heading_tolerance = heading_tolerance_deg

        # Phase 3 parameters
        self.target_heading = target_heading
        self.heading_tolerance3 = heading_tolerance3_deg
        self.settle_time_ms = settle_time_ms

        # Phase 4 parameters (Forward & Backward test)
        self.fwd_bwd_time_s = fwd_bwd_time_s
        self.fwd_bwd_speed = fwd_bwd_speed

        self.phase = self.PHASE_ALIGNING

        # Internal state for I and D terms
        self._integral_dist = 0.0
        self._integral_angle = 0.0
        self._integral_angle2 = 0.0
        self._integral_angle3 = 0.0
        self._prev_dist_error = None
        self._prev_angle_error = None
        self._prev_angle2_error = None
        self._prev_angle3_error = None
        self._within_tolerance_since: Optional[float] = None
        self._fwd_start_time: Optional[float] = None
        self._bwd_start_time: Optional[float] = None

    def reset(self) -> None:
        self.phase = self.PHASE_ALIGNING
        self._integral_dist = 0.0
        self._integral_angle = 0.0
        self._integral_angle2 = 0.0
        self._integral_angle3 = 0.0
        self._prev_dist_error = None
        self._prev_angle_error = None
        self._prev_angle2_error = None
        self._prev_angle3_error = None
        self._within_tolerance_since = None
        self._fwd_start_time = None
        self._bwd_start_time = None

    def _scale_speeds(self, v_left: float, v_right: float) -> Tuple[int, int]:
        max_v = max(abs(v_left), abs(v_right))
        if max_v > self.max_velocity:
            scale_factor = self.max_velocity / max_v
            v_left *= scale_factor
            v_right *= scale_factor
        return int(round(v_left)), int(round(v_right))

    @staticmethod
    def _debug(
        state: str,
        distance: float,
        target_heading: float,
        angle_error: float,
        v_lr: float,
        v_diff: float,
        is_completed: bool = False,
    ) -> Dict[str, Any]:
        return {
            'state': state,
            'distance': distance,
            'target_heading': target_heading,
            'angle_error': angle_error,
            'v_lr': v_lr,
            'v_diff': v_diff,
            'v_linear': v_lr,
            'u_angular': v_diff,
            'is_completed': is_completed,
        }

    def compute(
        self,
        current_x: float,
        current_y: float,
        current_angle: float,
        target_x: float,
        target_y: float,
        current_time: Optional[float] = None,
    ) -> Tuple[int, int, Dict[str, Any]]:
        if current_time is None:
            current_time = time.perf_counter()

        dx = target_x - current_x
        dy = target_y - current_y
        distance_error = math.hypot(dx, dy)
        bearing_heading = math.degrees(math.atan2(-dy, dx))

        # Check if already completed
        if self.phase == self.PHASE_COMPLETED:
            target_h = self.target_heading if self.target_heading is not None else bearing_heading
            ang_err = wrap_to_180(current_angle - target_h)
            debug = self._debug(
                self.PHASE_COMPLETED, distance_error, target_h,
                ang_err, 0.0, 0.0, True,
            )
            return 0, 0, debug

        # Check if Leanbot reached destination distance in Phase 1 or Phase 2
        if self.phase in (self.PHASE_ALIGNING, self.PHASE_DRIVING) and distance_error <= self.dist_tolerance:
            if self.target_heading is not None:
                self.phase = self.PHASE_FINAL_ALIGNING
                self._within_tolerance_since = None
            else:
                self.phase = self.PHASE_COMPLETED
                debug = self._debug(
                    self.PHASE_COMPLETED, distance_error, bearing_heading,
                    wrap_to_180(current_angle - bearing_heading), 0.0, 0.0, True,
                )
                return 0, 0, debug

        # Phase 3: FINAL_ALIGNING - spin in place at target until final heading settles
        if self.phase == self.PHASE_FINAL_ALIGNING:
            target_h = float(self.target_heading)
            final_angle_error = wrap_to_180(current_angle - target_h)

            if abs(final_angle_error) <= self.heading_tolerance3:
                if self._within_tolerance_since is None:
                    self._within_tolerance_since = current_time
                elapsed_ms = (current_time - self._within_tolerance_since) * 1000.0
                if elapsed_ms >= self.settle_time_ms:
                    # If Phase 4 enabled (fwd_bwd_time_s > 0), transition to Phase 4A Forward
                    if self.fwd_bwd_time_s > 0.0:
                        self.phase = self.PHASE_FORWARD
                        self._fwd_start_time = current_time
                    else:
                        self.phase = self.PHASE_COMPLETED
                        debug = self._debug(
                            self.PHASE_COMPLETED, distance_error, target_h,
                            final_angle_error, 0.0, 0.0, True,
                        )
                        return 0, 0, debug
            else:
                self._within_tolerance_since = None

            if self.phase == self.PHASE_FINAL_ALIGNING:
                # Phase 3 reuses Phase 1 PID gains for spinning in place
                self._integral_angle3 += final_angle_error
                d_angle3 = (final_angle_error - self._prev_angle3_error) if self._prev_angle3_error is not None else 0.0
                self._prev_angle3_error = final_angle_error

                v_lr = 0.0
                v_diff = (self.Kp_angle * final_angle_error
                          + self.Ki_angle * self._integral_angle3
                          + self.Kd_angle * d_angle3)
                speed_left, speed_right = self._scale_speeds(v_lr + v_diff, v_lr - v_diff)
                debug = self._debug(
                    self.PHASE_FINAL_ALIGNING, distance_error, target_h,
                    final_angle_error, v_lr, v_diff, False,
                )
                return speed_left, speed_right, debug

        # Phase 4A: FORWARD - drive straight forward for fwd_bwd_time_s seconds
        if self.phase == self.PHASE_FORWARD:
            target_h = float(self.target_heading) if self.target_heading is not None else bearing_heading
            ang_err = wrap_to_180(current_angle - target_h)
            if self._fwd_start_time is None:
                self._fwd_start_time = current_time

            elapsed_fwd = current_time - self._fwd_start_time
            if elapsed_fwd >= self.fwd_bwd_time_s:
                self.phase = self.PHASE_BACKWARD
                self._bwd_start_time = current_time
                speed = -self.fwd_bwd_speed
                speed_left, speed_right = self._scale_speeds(speed, speed)
                debug = self._debug(
                    self.PHASE_BACKWARD, distance_error, target_h,
                    ang_err, float(speed), 0.0, False,
                )
                return speed_left, speed_right, debug
            else:
                speed = self.fwd_bwd_speed
                speed_left, speed_right = self._scale_speeds(speed, speed)
                debug = self._debug(
                    self.PHASE_FORWARD, distance_error, target_h,
                    ang_err, float(speed), 0.0, False,
                )
                return speed_left, speed_right, debug

        # Phase 4B: BACKWARD - drive straight backward for fwd_bwd_time_s seconds
        if self.phase == self.PHASE_BACKWARD:
            target_h = float(self.target_heading) if self.target_heading is not None else bearing_heading
            ang_err = wrap_to_180(current_angle - target_h)
            if self._bwd_start_time is None:
                self._bwd_start_time = current_time

            elapsed_bwd = current_time - self._bwd_start_time
            if elapsed_bwd >= self.fwd_bwd_time_s:
                self.phase = self.PHASE_COMPLETED
                debug = self._debug(
                    self.PHASE_COMPLETED, distance_error, target_h,
                    ang_err, 0.0, 0.0, True,
                )
                return 0, 0, debug
            else:
                speed = -self.fwd_bwd_speed
                speed_left, speed_right = self._scale_speeds(speed, speed)
                debug = self._debug(
                    self.PHASE_BACKWARD, distance_error, target_h,
                    ang_err, float(speed), 0.0, False,
                )
                return speed_left, speed_right, debug

        # Phase 1: ALIGNING - spin in place until heading error is within tolerance
        angle_error = wrap_to_180(current_angle - bearing_heading)
        if self.phase == self.PHASE_ALIGNING:
            if abs(angle_error) <= self.heading_tolerance:
                self.phase = self.PHASE_DRIVING
            else:
                # Phase 1 PID for angle
                self._integral_angle += angle_error
                d_angle = (angle_error - self._prev_angle_error) if self._prev_angle_error is not None else 0.0
                self._prev_angle_error = angle_error

                v_lr = 0.0
                v_diff = (self.Kp_angle * angle_error
                          + self.Ki_angle * self._integral_angle
                          + self.Kd_angle * d_angle)
                speed_left, speed_right = self._scale_speeds(v_lr + v_diff, v_lr - v_diff)
                debug = self._debug(
                    self.PHASE_ALIGNING, distance_error, bearing_heading,
                    angle_error, v_lr, v_diff, False,
                )
                return speed_left, speed_right, debug

        # Phase 2: DRIVING - move forward while correcting heading
        # PID for distance
        self._integral_dist += distance_error
        d_dist = (distance_error - self._prev_dist_error) if self._prev_dist_error is not None else 0.0
        self._prev_dist_error = distance_error

        v_lr = (self.Kp_dist * distance_error
                + self.Ki_dist * self._integral_dist
                + self.Kd_dist * d_dist)
        # Crop v_lr về dải 0 ... max_velocity
        v_lr_cropped = max(0.0, min(v_lr, float(self.max_velocity)))

        # PID for angle in Phase 2
        self._integral_angle2 += angle_error
        d_angle2 = wrap_to_180(angle_error - self._prev_angle2_error) if self._prev_angle2_error is not None else 0.0
        self._prev_angle2_error = angle_error

        # delta_V = (Kp_angle2 * err + Ki_angle2 * integral + Kd_angle2 * derivative) * v_LR
        delta_v = (self.Kp_angle2 * angle_error
                   + self.Ki_angle2 * self._integral_angle2
                   + self.Kd_angle2 * d_angle2) * v_lr_cropped

        # Calculate and scale individual wheel speeds
        speed_left, speed_right = self._scale_speeds(v_lr_cropped + delta_v, v_lr_cropped - delta_v)

        debug = self._debug(
            self.PHASE_DRIVING, distance_error, bearing_heading,
            angle_error, v_lr_cropped, delta_v, False,
        )
        return speed_left, speed_right, debug


def create_position_pid(**kwargs: Any) -> PositionPIDController:
    return PositionPIDController(**kwargs)
