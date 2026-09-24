import contextlib
import csv
import io
import math
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np

import leanbotCameraController as controller


class CameraLoggingTests(unittest.TestCase):
    def run_headless_capture(self, target_heading=None):
        with tempfile.TemporaryDirectory(prefix="leanbot_logging_test_") as temporary_dir:
            root = Path(temporary_dir)
            model_dir = root / "model"
            model_dir.mkdir()
            (model_dir / "fake.xml").write_text("", encoding="utf-8")
            log_path = root / "capture.csv"
            frame = np.zeros((720, 1280, 3), dtype=np.uint8)
            camera = Mock()
            camera.isOpened.return_value = True
            camera.read.side_effect = [(True, frame.copy()) for frame_index in range(4)] + [(False, None)]
            compiled_model = Mock()
            compiled_model.get_property.return_value = ["CPU"]
            core = Mock()
            core.compile_model.return_value = compiled_model
            model = Mock(names={0: "Leanbot_0", 1: "Leanbot_p15"})
            missing = (np.zeros(4, dtype=np.float32), 0.0, 0.0, 0.0, 0.0, 0.0)
            detections = [
                missing,
                (np.array([64, 160, 192, 288], dtype=np.float32), 0.91, 16.0, 3.0, 0.0, 0.0),
                missing,
                missing,
            ]
            arguments = [
                "leanbotCameraController.py", "--ble", "0", "--no-show",
                "--full-model", str(model_dir), "--tracking-model", str(model_dir),
                "--target-config", str(root / "missing_target.json"), "--log", str(log_path),
            ]
            if target_heading is not None:
                arguments.extend(["--target-heading", str(target_heading)])

            with contextlib.ExitStack() as stack:
                stack.enter_context(patch.object(controller, "current_dir", root / "controller"))
                stack.enter_context(patch.object(controller, "parent_dir", root))
                stack.enter_context(patch.object(controller, "YOLO", return_value=model))
                stack.enter_context(patch.object(controller.ov, "Core", return_value=core))
                stack.enter_context(patch.object(controller.cv2, "VideoCapture", return_value=camera))
                ble_constructor = stack.enter_context(patch.object(controller, "BLEMotorWorker"))
                inference = stack.enter_context(patch.object(controller, "select_best_vector_detection", side_effect=detections))
                stack.enter_context(patch.object(sys, "argv", arguments))
                stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
                controller.main()

            ble_constructor.assert_not_called()
            camera.release.assert_called_once()
            self.assertEqual(inference.call_count, 4)
            with log_path.open(newline="", encoding="utf-8") as log_file:
                rows = list(csv.DictReader(log_file))
            self.assertEqual(len(rows), 4)
            self.assertEqual([row["tracking_lost"] for row in rows], ["1", "0", "1", "1"])
            sessions = list((root / "lost_tracking_dataset").iterdir())
            self.assertEqual(len(sessions), 1)
            for directory in ("images", "labels", "metadata", "check_labels"):
                self.assertEqual(list((sessions[0] / directory).iterdir()), [])
            self.assertEqual(list((root / "controller" / "benchmark_logs" / "lost_tracking_captures").iterdir()), [])
            return rows

    def test_missing_heading_logs_nan_without_stopping_camera(self):
        rows = self.run_headless_capture()
        for row in rows:
            self.assertEqual(row["target_angle"], "NaN")
            self.assertEqual(row["angle_error"], "NaN")

    def test_zero_heading_is_not_treated_as_missing(self):
        rows = self.run_headless_capture(target_heading=0.0)
        for row in rows:
            self.assertEqual(row["target_angle"], "0.00")
            self.assertTrue(math.isfinite(float(row["angle_error"])))

    def test_configured_heading_keeps_numeric_log_format(self):
        rows = self.run_headless_capture(target_heading=-45.5)
        for row in rows:
            self.assertEqual(row["target_angle"], "-45.50")
            self.assertTrue(math.isfinite(float(row["angle_error"])))


if __name__ == "__main__":
    unittest.main()
