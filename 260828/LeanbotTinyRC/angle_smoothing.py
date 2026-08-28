"""
angle_smoothing.py
------------------
Online (causal, realtime) angle smoothing pipeline for LeanbotCameraController.

Pipeline consists of 2 parallel streams:
  Stream 1 - Model Angle:
      Raw Model Angle -> Unwrap +/-360 deg -> Poly Fit 1D Degree 1 (W, index) -> Model Angle Smooth

  Stream 2 - Trajectory Angle:
      Coordinates (x, y) -> Poly Fit 2D Degree 2 (W, index)
          +- Derivative -> atan2(-dy, dx) -> Tangent angle (unwrap + 180 deg align)
          |       +- Poly Fit 1D Degree 1 (W, index) -> Trajectory Angle Smooth
          +- Speed = sqrt(dx^2+dy^2) / (W-1)

  Fusion:
      x(v) = K / (K + v)
      FusedAngle = x * ModelSmooth + (1-x) * TrajectorySmooth

Confirmed parameters (from reports 17/08 -> 19/08 -> 21/08):
  - Window size W = 18
  - Delay tangent index = -4
  - Poly degree for Model Smooth: Degree 1
  - Poly degree for Trajectory 2D fit: Degree 2
  - Poly degree for Trajectory Angle 1D smooth (2nd pass): Degree 1
  - Weight: Uniform
  - K = 1.0 px/frame  (changed from K = 3.0)
"""

import math
from collections import deque

import numpy as np


class AngleSmoothingEngine:
    """Online causal pipeline for angle smoothing and fused angle computation."""

    def __init__(
        self,
        window_size: int = 18,
        eval_index: int = -4,
        K: float = 1.0,
    ):
        self.window_size = window_size
        self.eval_index = eval_index
        self.K = K

        # ---------- Buffers (Stream 1: Model Angle) ----------
        # Continuously unwrapped raw model angle sequence
        self.raw_angle_buffer: deque = deque(maxlen=window_size)

        # ---------- Buffers (Stream 2: Trajectory Angle) ----------
        self.x_buffer: deque = deque(maxlen=window_size)
        self.y_buffer: deque = deque(maxlen=window_size)
        # Unwrapped + aligned trajectory tangent angle sequence for 2nd-pass smoothing
        self.traj_angle_buffer: deque = deque(maxlen=window_size)

        # ---------- Unwrap state ----------
        self.prev_unwrapped_model: float | None = None   # Continuous model angle
        self.prev_unwrapped_traj: float | None = None    # Continuous trajectory angle

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
        """Called every frame. Returns a dict of pipeline results.

        When ``detected=False`` (lost tracking), all buffers receive NaN
        and all results are None (bad frames are excluded from computation).

        When the buffer has fewer than ``window_size`` finite samples, the
        pipeline still computes using however many finite samples are available.
        Minimum of 2 finite samples required for polynomial fitting.
        """
        result = {
            "model_angle_smooth": None,
            "trajectory_angle_smooth": None,
            "estimated_speed": None,
            "fused_angle": None,
            "fused_weight_x": None,
        }

        self.frame_count += 1

        # -- Lost tracking: push NaN to all buffers, return None results --
        if not detected:
            self.raw_angle_buffer.append(float("nan"))
            self.x_buffer.append(float("nan"))
            self.y_buffer.append(float("nan"))
            self.traj_angle_buffer.append(float("nan"))
            return result

        # ====================================================
        # STREAM 1: Model Angle Smoothing
        # ====================================================

        # 1a. Unwrap raw angle
        unwrapped_model = self._unwrap_angle(raw_angle, self.prev_unwrapped_model)
        self.prev_unwrapped_model = unwrapped_model
        self.raw_angle_buffer.append(unwrapped_model)

        # 1b. Poly Fit 1D Degree 1
        model_smooth = self._smooth_1d_poly(
            buffer=self.raw_angle_buffer,
            degree=1,
            eval_index=self.eval_index,
        )
        result["model_angle_smooth"] = model_smooth

        # ====================================================
        # STREAM 2: Trajectory Tangent Angle
        # ====================================================

        # 2a. Store coordinates
        self.x_buffer.append(float(x_center))
        self.y_buffer.append(float(y_center))

        # 2b. Fit 2D Degree 2 on (x, y) -> derivative at index -> angle + speed
        traj_raw_angle, speed = self._fit_trajectory_2d(
            x_buf=self.x_buffer,
            y_buf=self.y_buffer,
            degree=2,
            eval_index=self.eval_index,
        )
        result["estimated_speed"] = speed

        if traj_raw_angle is not None:
            # 2c. Unwrap + 180 deg phase alignment
            traj_unwrapped = self._unwrap_angle(traj_raw_angle, self.prev_unwrapped_traj)
            # Align to model angle (use model_smooth if available, otherwise unwrapped_model)
            ref_angle = model_smooth if model_smooth is not None else unwrapped_model
            traj_aligned = self._align_trajectory_phase(traj_unwrapped, ref_angle)
            self.prev_unwrapped_traj = traj_aligned
            self.traj_angle_buffer.append(traj_aligned)

            # 2d. 2nd-pass smoothing using Poly Fit 1D Degree 1
            traj_smooth = self._smooth_1d_poly(
                buffer=self.traj_angle_buffer,
                degree=1,
                eval_index=self.eval_index,
            )
            result["trajectory_angle_smooth"] = traj_smooth
        else:
            self.traj_angle_buffer.append(float("nan"))
            traj_smooth = None

        # ====================================================
        # FUSION: Fused Angle
        # ====================================================

        if model_smooth is not None and traj_smooth is not None and speed is not None:
            fused, weight_x = self._compute_fused_angle(
                model_smooth, traj_smooth, speed, self.K
            )
            result["fused_angle"] = fused
            result["fused_weight_x"] = weight_x

        return result

    def reset(self):
        """Clear all buffers — call on lost tracking if a hard reset is needed."""
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
        """Online +/-360 deg phase unwrapping.

        Keeps the angle sequence continuous - wraps by +/-360 deg when the jump exceeds 180 deg.
        """
        if prev_angle is None:
            return float(new_angle)
        diff = new_angle - prev_angle
        # Phase correction: wrap if difference exceeds 180 deg
        diff = (diff + 180.0) % 360.0 - 180.0
        return prev_angle + diff

    @staticmethod
    def _smooth_1d_poly(
        buffer: deque,
        degree: int,
        eval_index: int,
    ) -> float | None:
        """Causal 1D polynomial fit on buffer, evaluated at eval_index.

        Works with short windows (uses however many finite samples are available).
        Requires at least 2 finite samples.
        """
        data = np.array(buffer, dtype=float)
        n = len(data)
        if n < 2:
            return None

        finite_mask = np.isfinite(data)
        n_finite = int(np.count_nonzero(finite_mask))
        if n_finite < 2:
            return None

        # Normalize time to [-1, 0]
        time_all = np.linspace(-1.0, 0.0, n)
        t_finite = time_all[finite_mask]
        d_finite = data[finite_mask]

        current_degree = min(degree, n_finite - 1)
        coefficients = np.polyfit(t_finite, d_finite, deg=current_degree)

        # Compute t_eval from eval_index
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
        """Fit a 2D polynomial of given degree on (x, y), compute derivative at eval_index.

        Returns:
            (tangent_angle_degrees, estimated_speed)
            Both are None if insufficient data.
        """
        x_data = np.array(x_buf, dtype=float)
        y_data = np.array(y_buf, dtype=float)
        n = len(x_data)
        if n < 2:
            return None, None

        # Use only samples that are finite in both x and y
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

        # Compute t_eval
        target_idx = max(0, n - 1 + eval_index)
        if n > 1:
            t_eval = (target_idx - (n - 1)) / (n - 1)
        else:
            t_eval = 0.0

        # Derivative
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
        """Align trajectory tangent angle to 180 deg phase of the reference Model angle.

        Because atan2 has +/-180 deg ambiguity (forward/backward), we align
        the trajectory angle to the nearest candidate closest to the model reference.

        Tries all offset candidates +/-k*period and selects the one nearest to ref.
        """
        diff = traj_angle - ref_angle
        # Try the 2 nearest k candidates (floor and ceil)
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
        """Compute velocity-adaptive fused angle.

        x(v) = K / (K + v)
        fused = x * model_smooth + (1 - x) * traj_smooth

        Returns:
            (fused_angle, weight_x)
        """
        weight_x = K / (K + speed)
        fused = weight_x * model_smooth + (1.0 - weight_x) * traj_smooth
        return fused, weight_x
