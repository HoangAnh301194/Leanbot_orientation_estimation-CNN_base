"""
angle_smoothing.py
──────────────────
Module online (causal, realtime) pipeline làm mượt góc cho LeanbotCameraController.

Pipeline gồm 2 luồng song song:
  Luồng 1 Góc Model:
      Raw Model Angle → Unwrap ±360° → Poly Fit 1D Bậc 1 (W, index) → Model Angle Smooth

  Luồng 2 Góc Quỹ Đạo:
      Tọa độ (x, y) → Poly Fit 2D Bậc 2 (W, index)
          ├─ Đạo hàm → atan2(-dy, dx) → Góc tiếp tuyến (unwrap + align 180°)
          │       └─ Poly Fit 1D Bậc 1 (W, index) → Trajectory Angle Smooth
          └─ Speed = sqrt(dx²+dy²) / (W-1)

  Hợp nhất:
      x(v) = K / (K + v)
      FusedAngle = x·ModelSmooth + (1-x)·TrajectorySmooth

Tham số đã chốt (từ báo cáo 17/08 → 19/08 → 21/08):
  - Window size W = 18
  - Delay tangent index = -4
  - Poly degree cho Model Smooth: Bậc 1
  - Poly degree cho Trajectory 2D fit: Bậc 2
  - Poly degree cho Trajectory Angle 1D smooth (lần 2): Bậc 1
  - Weight: Uniform
  - K = 3.0 px/frame
"""

import math
from collections import deque

import numpy as np


class AngleSmoothingEngine:
    """Online causal pipeline cho làm mượt góc và tính fused angle."""

    def __init__(
        self,
        window_size: int = 18,
        eval_index: int = -4,
        K: float = 3.0,
    ):
        self.window_size = window_size
        self.eval_index = eval_index
        self.K = K

        # ---------- Buffers (Luồng 1: Góc Model) ----------
        # Chuỗi raw model angle đã unwrap liên tục
        self.raw_angle_buffer: deque = deque(maxlen=window_size)

        # ---------- Buffers (Luồng 2: Góc Quỹ đạo) ----------
        self.x_buffer: deque = deque(maxlen=window_size)
        self.y_buffer: deque = deque(maxlen=window_size)
        # Chuỗi góc tiếp tuyến quỹ đạo (đã unwrap+align) để smooth lần 2
        self.traj_angle_buffer: deque = deque(maxlen=window_size)

        # ---------- Trạng thái unwrap ----------
        self.prev_unwrapped_model: float | None = None   # Góc model liên tục
        self.prev_unwrapped_traj: float | None = None    # Góc traj liên tục

        self.frame_count: int = 0

    # ==============================================================
    # PUBLIC API
    # ==============================================================

    def update(
        self,
        raw_angle: float,
        x_center: float,
        y_center: float,
        detected: bool,
    ) -> dict:
        """Gọi mỗi frame.  Trả về dict kết quả pipeline.

        Khi ``detected=False`` (lost tracking), tất cả buffer nhận NaN
        và kết quả trả về là None (không dùng frame lỗi vào tính toán).

        Khi buffer chưa đủ ``window_size`` mẫu hữu ích (finite), pipeline
        vẫn tính toán với cửa sổ ngắn (bao nhiêu mẫu có thì dùng bấy nhiêu).
        Yêu cầu tối thiểu 2 mẫu finite để fit đa thức.
        """
        result = {
            "model_angle_smooth": None,
            "trajectory_angle_smooth": None,
            "estimated_speed": None,
            "fused_angle": None,
            "fused_weight_x": None,
        }

        self.frame_count += 1

        # ── Khi mất tracking: đẩy NaN vào buffer, trả None ──
        if not detected:
            self.raw_angle_buffer.append(float("nan"))
            self.x_buffer.append(float("nan"))
            self.y_buffer.append(float("nan"))
            self.traj_angle_buffer.append(float("nan"))
            return result

        # ══════════════════════════════════════════════════════
        # LUỒNG 1: Làm mượt góc Model
        # ══════════════════════════════════════════════════════

        # 1a. Unwrap raw angle
        unwrapped_model = self._unwrap_angle(raw_angle, self.prev_unwrapped_model)
        self.prev_unwrapped_model = unwrapped_model
        self.raw_angle_buffer.append(unwrapped_model)

        # 1b. Poly Fit 1D Bậc 1
        model_smooth = self._smooth_1d_poly(
            buffer=self.raw_angle_buffer,
            degree=1,
            eval_index=self.eval_index,
        )
        result["model_angle_smooth"] = model_smooth

        # ══════════════════════════════════════════════════════
        # LUỒNG 2: Góc tiếp tuyến quỹ đạo
        # ══════════════════════════════════════════════════════

        # 2a. Lưu tọa độ
        self.x_buffer.append(float(x_center))
        self.y_buffer.append(float(y_center))

        # 2b. Fit 2D Bậc 2 trên (x, y) → đạo hàm tại index → góc + speed
        traj_raw_angle, speed = self._fit_trajectory_2d(
            x_buf=self.x_buffer,
            y_buf=self.y_buffer,
            degree=2,
            eval_index=self.eval_index,
        )
        result["estimated_speed"] = speed

        if traj_raw_angle is not None:
            # 2c. Unwrap + align pha 180°
            traj_unwrapped = self._unwrap_angle(traj_raw_angle, self.prev_unwrapped_traj)
            # Align theo model (sử dụng model_smooth nếu có, hoặc unwrapped_model)
            ref_angle = model_smooth if model_smooth is not None else unwrapped_model
            traj_aligned = self._align_trajectory_phase(traj_unwrapped, ref_angle)
            self.prev_unwrapped_traj = traj_aligned
            self.traj_angle_buffer.append(traj_aligned)

            # 2d. Smooth lần 2 bằng Poly Fit 1D Bậc 1
            traj_smooth = self._smooth_1d_poly(
                buffer=self.traj_angle_buffer,
                degree=1,
                eval_index=self.eval_index,
            )
            result["trajectory_angle_smooth"] = traj_smooth
        else:
            self.traj_angle_buffer.append(float("nan"))
            traj_smooth = None

        # ══════════════════════════════════════════════════════
        # HỢP NHẤT: Fused Angle
        # ══════════════════════════════════════════════════════

        if model_smooth is not None and traj_smooth is not None and speed is not None:
            fused, weight_x = self._compute_fused_angle(
                model_smooth, traj_smooth, speed, self.K
            )
            result["fused_angle"] = fused
            result["fused_weight_x"] = weight_x

        return result

    def reset(self):
        """Xóa toàn bộ buffer — gọi khi lost tracking nếu muốn hard reset."""
        self.raw_angle_buffer.clear()
        self.x_buffer.clear()
        self.y_buffer.clear()
        self.traj_angle_buffer.clear()
        self.prev_unwrapped_model = None
        self.prev_unwrapped_traj = None

    # ==============================================================
    # INTERNAL HELPERS
    # ==============================================================

    @staticmethod
    def _unwrap_angle(new_angle: float, prev_angle: float | None) -> float:
        """Unwrap online pha ±360°.

        Giữ cho chuỗi góc liên tục — khi góc nhảy > 180° thì bù ±360°.
        """
        if prev_angle is None:
            return float(new_angle)
        diff = new_angle - prev_angle
        # Bù pha: nếu chênh lệch > 180° thì wrap lại
        diff = (diff + 180.0) % 360.0 - 180.0
        return prev_angle + diff

    @staticmethod
    def _smooth_1d_poly(
        buffer: deque,
        degree: int,
        eval_index: int,
    ) -> float | None:
        """Fit đa thức 1D causal trên buffer, đánh giá tại eval_index.

        Hoạt động với cửa sổ ngắn (bao nhiêu mẫu finite thì dùng bấy nhiêu).
        Cần tối thiểu 2 mẫu finite.
        """
        data = np.array(buffer, dtype=float)
        n = len(data)
        if n < 2:
            return None

        finite_mask = np.isfinite(data)
        n_finite = int(np.count_nonzero(finite_mask))
        if n_finite < 2:
            return None

        # Chuẩn hóa thời gian [-1, 0]
        time_all = np.linspace(-1.0, 0.0, n)
        t_finite = time_all[finite_mask]
        d_finite = data[finite_mask]

        current_degree = min(degree, n_finite - 1)
        coefficients = np.polyfit(t_finite, d_finite, deg=current_degree)

        # Tính t_eval từ eval_index
        target_idx = max(0, n - 1 + eval_index)
        if n > 1:
            t_eval = (target_idx - (n - 1)) / (n - 1)
        else:
            t_eval = 0.0

        return float(np.polyval(coefficients, t_eval))

    @staticmethod
    def _fit_trajectory_2d(
        x_buf: deque,
        y_buf: deque,
        degree: int,
        eval_index: int,
    ) -> tuple[float | None, float | None]:
        """Fit đa thức 2D bậc 2 trên (x, y), tính đạo hàm tại eval_index.

        Returns:
            (tangent_angle_degrees, estimated_speed)
            Cả hai là None nếu không đủ dữ liệu.
        """
        x_data = np.array(x_buf, dtype=float)
        y_data = np.array(y_buf, dtype=float)
        n = len(x_data)
        if n < 2:
            return None, None

        # Chỉ dùng các mẫu finite ở cả x lẫn y
        finite_mask = np.isfinite(x_data) & np.isfinite(y_data)
        n_finite = int(np.count_nonzero(finite_mask))
        if n_finite < 2:
            return None, None

        time_all = np.linspace(-1.0, 0.0, n)
        t_finite = time_all[finite_mask]
        x_finite = x_data[finite_mask]
        y_finite = y_data[finite_mask]

        current_degree = min(degree, n_finite - 1)
        coeff_x = np.polyfit(t_finite, x_finite, deg=current_degree)
        coeff_y = np.polyfit(t_finite, y_finite, deg=current_degree)

        # Tính t_eval
        target_idx = max(0, n - 1 + eval_index)
        if n > 1:
            t_eval = (target_idx - (n - 1)) / (n - 1)
        else:
            t_eval = 0.0

        # Đạo hàm
        if current_degree < 1:
            return None, None

        deriv_x = np.polyder(coeff_x)
        deriv_y = np.polyder(coeff_y)
        dx = float(np.polyval(deriv_x, t_eval))
        dy = float(np.polyval(deriv_y, t_eval))

        magnitude = math.hypot(dx, dy)
        if magnitude < 1e-5:
            return None, None

        tangent_angle = math.degrees(math.atan2(-dy, dx))
        window_size = max(n, 2)
        speed = magnitude / (window_size - 1)

        return tangent_angle, speed

    @staticmethod
    def _align_trajectory_phase(
        traj_angle: float,
        ref_angle: float,
        period: float = 180.0,
    ) -> float:
        """Căn chỉnh pha 180° cho góc tiếp tuyến theo góc Model tham chiếu.

        Vì atan2 có tính bất định hướng ±180° (tiến/lùi), cần align
        sao cho góc trajectory gần nhất với góc model reference.

        Thử tất cả các ứng viên offset ±k*period và chọn cái gần ref nhất.
        """
        diff = traj_angle - ref_angle
        # Thử 2 ứng viên k gần nhất (floor và ceil)
        k_floor = math.floor(diff / period)
        best_angle = traj_angle
        best_dist = float("inf")
        for k in (k_floor, k_floor + 1):
            candidate = traj_angle - k * period
            dist = abs(candidate - ref_angle)
            if dist < best_dist:
                best_dist = dist
                best_angle = candidate
        return best_angle

    @staticmethod
    def _compute_fused_angle(
        model_smooth: float,
        traj_smooth: float,
        speed: float,
        K: float,
    ) -> tuple[float, float]:
        """Tính fused angle thích ứng theo vận tốc.

        x(v) = K / (K + v)
        fused = x * model_smooth + (1 - x) * traj_smooth

        Returns:
            (fused_angle, weight_x)
        """
        weight_x = K / (K + speed)
        fused = weight_x * model_smooth + (1.0 - weight_x) * traj_smooth
        return fused, weight_x
