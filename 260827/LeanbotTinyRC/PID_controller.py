'''Bo dieu khien P hai giai doan cho Leanbot di den target pixel co dinh.'''

import math
from typing import Any, Dict, Tuple


MAX_VELOCITY = 2000
DEFAULT_DIST_TOLERANCE_PX = 10.0
DEFAULT_HEADING_TOLERANCE_DEG = 10.0


def wrap_to_180(angle_deg: float) -> float:
    return (angle_deg + 180.0) % 360.0 - 180.0


class PositionPIDController:
    '''Giu ten lop cu de tuong thich; thuat toan hien tai chi dung khau P.'''

    PHASE_ALIGNING = 'PHASE_1_ALIGNING'
    PHASE_ALIGN_COMPLETE = 'PHASE_1_COMPLETE'
    PHASE_DRIVING = 'PHASE_2_DRIVING'
    PHASE_COMPLETED = 'COMPLETED'

    def __init__(
        self,
        Kp_dist: float = 25.0,
        Kp_angle: float = 15.0,
        max_velocity: int = MAX_VELOCITY,
        dist_tolerance_px: float = DEFAULT_DIST_TOLERANCE_PX,
        heading_tolerance_deg: float = DEFAULT_HEADING_TOLERANCE_DEG,
    ):
        self.Kp_dist = Kp_dist
        self.Kp_angle = Kp_angle
        self.max_velocity = max_velocity
        self.dist_tolerance = dist_tolerance_px
        self.heading_tolerance = heading_tolerance_deg
        self.phase = self.PHASE_ALIGNING

    def reset(self) -> None:
        self.phase = self.PHASE_ALIGNING

    def _mix_wheel_speeds(self, v_lr: float, v_diff: float) -> Tuple[int, int]:
        speed_left = v_lr + v_diff
        speed_right = v_lr - v_diff
        max_abs_speed = max(abs(speed_left), abs(speed_right))
        if max_abs_speed > self.max_velocity:
            velocity_scale = self.max_velocity / max_abs_speed
            speed_left *= velocity_scale
            speed_right *= velocity_scale
        speed_left = int(round(speed_left))
        speed_right = int(round(speed_right))
        return speed_left, speed_right

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

        if distance_error <= self.dist_tolerance:
            self.phase = self.PHASE_COMPLETED
            debug = self._debug(
                self.PHASE_COMPLETED, distance_error, target_heading,
                angle_error, 0.0, 0.0, True,
            )
            return 0, 0, debug

        if self.phase == self.PHASE_ALIGNING:
            if abs(angle_error) <= self.heading_tolerance:
                self.phase = self.PHASE_DRIVING
                debug = self._debug(
                    self.PHASE_ALIGN_COMPLETE, distance_error, target_heading,
                    angle_error, 0.0, 0.0,
                )
                return 0, 0, debug

            v_lr = 0.0
            v_diff = self.Kp_angle * angle_error
            speed_left, speed_right = self._mix_wheel_speeds(v_lr, v_diff)
            debug = self._debug(
                self.PHASE_ALIGNING, distance_error, target_heading,
                angle_error, v_lr, v_diff,
            )
            return speed_left, speed_right, debug

        v_lr = self.Kp_dist * distance_error
        v_diff = self.Kp_angle * angle_error
        speed_left, speed_right = self._mix_wheel_speeds(v_lr, v_diff)
        debug = self._debug(
            self.PHASE_DRIVING, distance_error, target_heading,
            angle_error, v_lr, v_diff,
        )
        return speed_left, speed_right, debug


def create_position_pid(**kwargs: Any) -> PositionPIDController:
    return PositionPIDController(**kwargs)
