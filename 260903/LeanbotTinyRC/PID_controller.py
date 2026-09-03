"""Two-phase PID position controller for Leanbot navigation to a fixed target pixel."""

import math
from typing import Any, Dict, Tuple


MAX_VELOCITY = 2000
DEFAULT_DIST_TOLERANCE_PX = 10.0
DEFAULT_HEADING_TOLERANCE_DEG = 5.0  # 10.0 -> 5.0


def wrap_to_180(angle_deg: float) -> float:
    return (angle_deg + 180.0) % 360.0 - 180.0


class PositionPIDController:
    """PID position controller with separate gains for Phase 1 (aligning) and Phase 2 (driving)."""

    PHASE_ALIGNING = 'PHASE_1_ALIGNING'
    PHASE_ALIGN_COMPLETE = 'PHASE_1_COMPLETE'
    PHASE_DRIVING = 'PHASE_2_DRIVING'
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
    ):
        # PID gains - distance
        self.Kp_dist = Kp_dist
        self.Ki_dist = Ki_dist
        self.Kd_dist = Kd_dist
        # PID gains - angle (Phase 1: aligning)
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
        self.phase = self.PHASE_ALIGNING

        # Internal state for I and D terms
        self._integral_dist = 0.0
        self._integral_angle = 0.0
        self._integral_angle2 = 0.0
        self._prev_dist_error = None
        self._prev_angle_error = None
        self._prev_angle2_error = None

    def reset(self) -> None:
        self.phase = self.PHASE_ALIGNING
        self._integral_dist = 0.0
        self._integral_angle = 0.0
        self._integral_angle2 = 0.0
        self._prev_dist_error = None
        self._prev_angle_error = None
        self._prev_angle2_error = None

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
    ) -> Tuple[int, int, Dict[str, Any]]:
        dx = target_x - current_x
        dy = target_y - current_y
        distance_error = math.hypot(dx, dy)
        target_heading = math.degrees(math.atan2(-dy, dx))

        angle_error = wrap_to_180(current_angle - target_heading)

        # Phase complete: Leanbot reached the target pixel
        if distance_error <= self.dist_tolerance:
            self.phase = self.PHASE_COMPLETED
            debug = self._debug(
                self.PHASE_COMPLETED, distance_error, target_heading,
                angle_error, 0.0, 0.0, True,
            )
            return 0, 0, debug

        # Phase 1: ALIGNING - spin in place until heading error is within tolerance
        if self.phase == self.PHASE_ALIGNING:
            if abs(angle_error) <= self.heading_tolerance:
                self.phase = self.PHASE_DRIVING
                debug = self._debug(
                    self.PHASE_ALIGN_COMPLETE, distance_error, target_heading,
                    angle_error, 0.0, 0.0,
                )
                return 0, 0, debug

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
                self.PHASE_ALIGNING, distance_error, target_heading,
                angle_error, v_lr, v_diff,
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
        d_angle2 = (angle_error - self._prev_angle2_error) if self._prev_angle2_error is not None else 0.0
        self._prev_angle2_error = angle_error

        # delta_V = (Kp_angle2 * err + Ki_angle2 * integral + Kd_angle2 * derivative) * v_LR
        delta_v = (self.Kp_angle2 * angle_error
                   + self.Ki_angle2 * self._integral_angle2
                   + self.Kd_angle2 * d_angle2) * v_lr_cropped
        
        # Calculate and scale individual wheel speeds
        speed_left, speed_right = self._scale_speeds(v_lr_cropped + delta_v, v_lr_cropped - delta_v)
        
        debug = self._debug(
            self.PHASE_DRIVING, distance_error, target_heading,
            angle_error, v_lr_cropped, delta_v,
        )
        return speed_left, speed_right, debug


def create_position_pid(**kwargs: Any) -> PositionPIDController:
    return PositionPIDController(**kwargs)
