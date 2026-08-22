"""
Module bo dieu khien PID cho Leanbot (BLE Control).
Bao gom:
  1. PIDController: Dieu khien goc quay tai cho (Yaw Angle Control) ve goc mong muon (Target Angle, vd: 90 do).
  2. PositionPIDController: Dieu khien Leanbot di chuyen toi toa do pixel muc tieu (x_target, y_target).
"""

import time
import math
from typing import Tuple, Dict, Optional

# --- HANG SO HE THONG ---
MAX_VELOCITY: int = 1000           # Van toc toi da truyen cho dong co Leanbot
MIN_START_VELOCITY: int = 10     # Van toc toi thieu de thang ma sat tinh (Deadband compensation)
DEFAULT_DEADZONE_DEG: float = 1.0  # Vung chet sai so goc (+/- 1.0 do)
DEFAULT_DIST_TOLERANCE_PX: float = 3.0  # Dung sai khoang cach pixel de coi la den dich


def wrap_to_180(angle_deg: float) -> float:
    """
    Chuan hoa goc hoac sai so goc ve khoang [-180, 180] do.
    Giup xe luon chon chieu quay ngan nhat de toi goc muc tieu.
    """
    return (angle_deg + 180.0) % 360.0 - 180.0


class PIDController:
    """
    Bo dieu khien PID goc quay (Heading/Yaw Controller) cho Leanbot.
    
    Dau vao:
        - current_angle: Goc hien tai (thuong la Fused Angle tu Camera, don vi: do).
        - target_angle: Goc muc tieu mong muon (mac dinh: 90.0 do).
    
    Dau ra:
        - speed_left, speed_right: Van toc 2 banh xe trong khoang [-MAX_VELOCITY, MAX_VELOCITY].
    """

    def __init__(
        self,
        Kp: float = 15.0,
        Ki: float = 0.0,
        Kd: float = 0.0,
        max_velocity: int = MAX_VELOCITY,
        min_velocity: int = MIN_START_VELOCITY,
        deadzone_deg: float = DEFAULT_DEADZONE_DEG,
        max_i: float = 300.0,
    ):
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        
        self.max_velocity = max_velocity
        self.min_velocity = min_velocity
        self.deadzone_deg = deadzone_deg
        self.max_i = max_i
        
        # Bien trang thai noi bo
        self.integral: float = 0.0
        self.prev_error: Optional[float] = None
        self.prev_time: Optional[float] = None

    def reset(self):
        """Reset trang thai bo dieu khien khi bat dau luot moi hoac khi mat tracking."""
        self.integral = 0.0
        self.prev_error = None
        self.prev_time = None

    def compute(
        self,
        current_angle: float,
        target_angle: float = 90.0,
        dt: Optional[float] = None,
        base_speed: int = 0,
    ) -> Tuple[int, int, Dict[str, float]]:
        """
        Tinh toan tin hieu dieu khien va van toc 2 banh xe.
        """
        now = time.perf_counter()
        if dt is None:
            if self.prev_time is not None:
                dt = max(0.001, now - self.prev_time)
            else:
                dt = 0.033  # Mac dinh ~30 FPS (33ms)
        self.prev_time = now

        # 1. Tinh sai so goc ngan nhat
        error = wrap_to_180(target_angle - current_angle)

        # 2. Kiem tra Deadzone (da dat muc tieu -> dung xe)
        if abs(error) <= self.deadzone_deg:
            self.integral = 0.0
            self.prev_error = error
            debug_info = {
                "error": error,
                "p": 0.0,
                "i": 0.0,
                "d": 0.0,
                "u": 0.0,
                "is_aligned": True,
            }
            return (base_speed, base_speed, debug_info)

        # 3. Proportional
        P = self.Kp * error

        # 4. Integral (Anti-windup)
        self.integral += error * dt
        self.integral = max(-self.max_i, min(self.max_i, self.integral))
        I = self.Ki * self.integral

        # 5. Derivative
        if self.prev_error is not None and dt > 0:
            d_error = wrap_to_180(error - self.prev_error) / dt
        else:
            d_error = 0.0
        self.prev_error = error
        D = self.Kd * d_error

        # 6. Tong tin hieu dieu khien xoay u(t)
        u = P + I + D

        # 7. Bu ma sat tinh (Deadband compensation)
        if abs(u) < self.min_velocity:
            u = math.copysign(self.min_velocity, u)

        # 8. Quy doi ra toc do 2 banh xe
        speed_left = int(round(base_speed - u))
        speed_right = int(round(base_speed + u))

        # 9. Saturation
        speed_left = max(-self.max_velocity, min(self.max_velocity, speed_left))
        speed_right = max(-self.max_velocity, min(self.max_velocity, speed_right))

        debug_info = {
            "error": error,
            "p": P,
            "i": I,
            "d": D,
            "u": u,
            "is_aligned": False,
        }

        return (speed_left, speed_right, debug_info)


class PositionPIDController:
    """
    Bo dieu khien vi tri (Point-to-Point Navigation) cho Leanbot theo he toa do pixel camera.
    
    Chien luoc dieu khien (Move-to-Goal):
      1. Tinh khoang cach d = sqrt(dx^2 + dy^2) va goc huong ve dich theta_desired = atan2(-dy, dx).
      2. Neu sai so goc lon (|e_theta| > rotate_in_place_threshold):
         -> Xoay tai cho ve huong dich (base_speed = 0).
      3. Neu da huong ve dich (|e_theta| <= rotate_in_place_threshold):
         -> Vua tien toi vua be lai nhe:
            v_linear = PID_dist(d) * cos(e_theta)
            u_angular = PID_angle(e_theta)
            speed_l = v_linear - u_angular
            speed_r = v_linear + u_angular
      4. Khi d <= dist_tolerance (da den dich):
         -> Dung xe hoac xoay tiep ve goc mong muon cuoi cung (final_heading_deg neu co).
    """

    def __init__(
        self,
        Kp_dist: float = 10.0,
        Ki_dist: float = 0.0,
        Kd_dist: float = 0.5,
        Kp_angle: float = 15.0,
        Ki_angle: float = 0.0,
        Kd_angle: float = 1.0,
        max_velocity: int = MAX_VELOCITY,
        min_velocity: int = MIN_START_VELOCITY,
        dist_tolerance_px: float = DEFAULT_DIST_TOLERANCE_PX,
        angle_tolerance_deg: float = DEFAULT_DEADZONE_DEG,
        rotate_in_place_threshold_deg: float = 25.0,
    ):
        self.angle_pid = PIDController(
            Kp=Kp_angle, Ki=Ki_angle, Kd=Kd_angle,
            max_velocity=max_velocity, min_velocity=min_velocity,
            deadzone_deg=angle_tolerance_deg
        )
        
        self.Kp_dist = Kp_dist
        self.Ki_dist = Ki_dist
        self.Kd_dist = Kd_dist
        
        self.max_velocity = max_velocity
        self.min_velocity = min_velocity
        self.dist_tolerance = dist_tolerance_px
        self.angle_tolerance = angle_tolerance_deg
        self.rotate_threshold = rotate_in_place_threshold_deg
        
        # Bien trang thai dist
        self.dist_integral: float = 0.0
        self.prev_dist_error: Optional[float] = None
        self.prev_time: Optional[float] = None
        self.is_driving: bool = False

    def reset(self):
        """Reset ca 2 bo dieu khien goc va khoang cach."""
        self.angle_pid.reset()
        self.dist_integral = 0.0
        self.prev_dist_error = None
        self.prev_time = None
        self.is_driving = False

    def compute(
        self,
        current_x: float,
        current_y: float,
        current_angle: float,
        target_x: float,
        target_y: float,
        final_heading_deg: Optional[float] = None,
        dt: Optional[float] = None,
    ) -> Tuple[int, int, Dict[str, any]]:
        """
        Tinh toan toc do 2 banh xe de Leanbot chay toi toa do pixel (target_x, target_y).
        
        Tham so:
            current_x, current_y: Toa do tam hien tai tren anh camera (pixel).
            current_angle: Goc mui xe hien tai (Fused Angle, do).
            target_x, target_y: Toa do pixel dich mong muon.
            final_heading_deg: Goc quay mong muon sau khi da toi dich (tuy chon, vd: 90 do).
            dt: Thoi gian lay mau (giay).
            
        Tra ve:
            (speed_left, speed_right, debug_info)
        """
        now = time.perf_counter()
        if dt is None:
            if self.prev_time is not None:
                dt = max(0.001, now - self.prev_time)
            else:
                dt = 0.033
        self.prev_time = now

        # 1. Tinh vector toi dich tren he toa do anh (y chieu xuong duoi)
        dx = target_x - current_x
        dy = target_y - current_y
        dist = math.hypot(dx, dy)

        # 2. Kiem tra da den dich hay chua
        if dist <= self.dist_tolerance:
            # Da den toa do dich: Kiem tra co can xoay ve final_heading_deg khong
            if final_heading_deg is not None:
                sl, sr, dbg_ang = self.angle_pid.compute(
                    current_angle=current_angle, target_angle=final_heading_deg, dt=dt, base_speed=0
                )
                state = "REACHED_POSITION_ROTATING_FINAL" if not dbg_ang["is_aligned"] else "COMPLETED"
                debug_info = {
                    "state": state,
                    "distance": dist,
                    "angle_error": dbg_ang["error"],
                    "v_linear": 0,
                    "u_angular": dbg_ang["u"],
                    "is_completed": dbg_ang["is_aligned"],
                }
                return (sl, sr, debug_info)
            else:
                # Dung xe hoan toan
                self.reset()
                debug_info = {
                    "state": "COMPLETED",
                    "distance": dist,
                    "angle_error": 0.0,
                    "v_linear": 0,
                    "u_angular": 0,
                    "is_completed": True,
                }
                return (0, 0, debug_info)

        # 3. Tinh goc can huong toi toa do dich
        # Luu y: truc Y camera huong xuong -> -dy
        target_heading = math.degrees(math.atan2(-dy, dx))
        angle_error = wrap_to_180(target_heading - current_angle)

        # 4. Chien luoc bo cua lien tuc (Smooth Arc Navigation)
        # - Neu dang dung yen hoac bat dau xuat phat: can xoay sat huong (sai so <= 10 do)
        # - Khi da vao luong chay: cho phep vua chay vua be lai uon cong (khong dung xe neu lech < 75 do)
        need_in_place_rotate = False
        if not self.is_driving:
            # Chua xuat phat: xoay tai cho cho sat duong noi muc tieu
            if abs(angle_error) > 10.0:
                need_in_place_rotate = True
            else:
                self.is_driving = True
        else:
            # Dang chay: chi dung lai xoay neu nguoc dau qua nang (> 75 do)
            if abs(angle_error) > 75.0:
                need_in_place_rotate = True
                self.is_driving = False

        if need_in_place_rotate:
            sl, sr, dbg_ang = self.angle_pid.compute(
                current_angle=current_angle, target_angle=target_heading, dt=dt, base_speed=0
            )
            debug_info = {
                "state": "ALIGNING_HEADING",
                "distance": dist,
                "target_heading": target_heading,
                "angle_error": angle_error,
                "v_linear": 0,
                "u_angular": dbg_ang["u"],
                "is_completed": False,
            }
            return (sl, sr, debug_info)

        # 5. Vua tien vua be lai uon cong lien tuc (Continuous Arc Steering)
        # PID Khoang cach
        P_dist = self.Kp_dist * dist
        self.dist_integral += dist * dt
        self.dist_integral = max(-500.0, min(500.0, self.dist_integral))
        I_dist = self.Ki_dist * self.dist_integral
        
        if self.prev_dist_error is not None and dt > 0:
            D_dist = self.Kd_dist * (dist - self.prev_dist_error) / dt
        else:
            D_dist = 0.0
        self.prev_dist_error = dist

        v_linear = P_dist + I_dist + D_dist
        
        # Uon cong toc do: neu lech goc thi giam nhe toc do tien de bo cua muot
        cos_factor = max(0.2, math.cos(math.radians(angle_error)))
        v_linear *= cos_factor
        
        # Dam bao van toc tien toi thieu de xe khong bi khung
        if v_linear > 0 and v_linear < self.min_velocity:
            v_linear = self.min_velocity

        # PID goc de be lai nhe nhang theo duong cong
        sl_ang, sr_ang, dbg_ang = self.angle_pid.compute(
            current_angle=current_angle, target_angle=target_heading, dt=dt, base_speed=0
        )
        u_angular = dbg_ang["u"]

        # Quy doi ra toc do 2 banh (Pure Pursuit Arc Differential Drive)
        speed_left = int(round(v_linear - u_angular))
        speed_right = int(round(v_linear + u_angular))

        # Kẹp van toc trong khoang [-max_velocity, max_velocity]
        speed_left = max(-self.max_velocity, min(self.max_velocity, speed_left))
        speed_right = max(-self.max_velocity, min(self.max_velocity, speed_right))

        debug_info = {
            "state": "DRIVING_TO_TARGET",
            "distance": dist,
            "target_heading": target_heading,
            "angle_error": angle_error,
            "v_linear": v_linear,
            "u_angular": u_angular,
            "is_completed": False,
        }

        return (speed_left, speed_right, debug_info)


# --- HAM CONVENIENCE DE DUNG TRUC TIEP ---
def create_default_pid(**kwargs) -> PIDController:
    """Tao bo dieu khien PID goc quay voi thiet lap chuan cho Leanbot."""
    return PIDController(**kwargs)


def create_position_pid(**kwargs) -> PositionPIDController:
    """Tao bo dieu khien vi tri (di chuyen toi toa do pixel) cho Leanbot."""
    return PositionPIDController(**kwargs)


if __name__ == "__main__":
    print(f"=== TEST 1: PID YAW CONTROLLER (Goc quay) ===")
    pid = create_default_pid()
    target = 90.0
    for ang in [0.0, 45.0, 85.0, 89.5, 90.0, 135.0, 270.0]:
        sl, sr, dbg = pid.compute(current_angle=ang, target_angle=target)
        status = "ALIGNED" if dbg["is_aligned"] else "ROTATING"
        print(f"Angle: {ang:5.1f} deg | Err: {dbg['error']:6.1f} deg | Left: {sl:5d} | Right: {sr:5d} | {status}")

    print(f"\n=== TEST 2: POSITION PID CONTROLLER (Toa do pixel) ===")
    pos_pid = create_position_pid()
    # Xe dang o (100, 100) huong 0 do, dich o (400, 400)
    cur_x, cur_y, cur_ang = 100.0, 100.0, 0.0
    tx, ty = 400.0, 400.0
    
    print(f"Start: ({cur_x}, {cur_y}), Heading: {cur_ang} deg -> Target: ({tx}, {ty})\n")
    for step in range(5):
        sl, sr, dbg = pos_pid.compute(cur_x, cur_y, cur_ang, tx, ty, final_heading_deg=90.0)
        print(f"Step {step}: State={dbg['state']:<25} | Dist={dbg['distance']:6.1f}px | ErrAng={dbg['angle_error']:5.1f} deg | L={sl:4d}, R={sr:4d}")
