import contextlib
import csv
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np

import leanbotCameraController as controller


class CameraCaptureSessionTests(unittest.TestCase):
    def run_session(self, detected_frames, keys, frame_times=None, complete_pid=False,
                    auto_record_video=False):
        self.assertEqual(len(detected_frames), len(keys))
        if frame_times is None:
            frame_times = [frame_index * 0.1 for frame_index in range(len(keys))]
        self.assertEqual(len(frame_times), len(keys))
        with tempfile.TemporaryDirectory(prefix="leanbot_session_test_") as temporary_dir:
            root = Path(temporary_dir)
            model_dir = root / "model"
            model_dir.mkdir()
            (model_dir / "fake.xml").write_text("", encoding="utf-8")
            log_path = root / "capture.csv"
            frame = np.zeros((720, 1280, 3), dtype=np.uint8)
            current_frame_index = -1
            current_time = 0.0

            def read_frame():
                nonlocal current_frame_index, current_time
                current_frame_index += 1
                if current_frame_index >= len(keys):
                    return False, None
                current_time = frame_times[current_frame_index]
                return True, frame.copy()

            def detect_frame(compiled_model, image, names, **kwargs):
                if not detected_frames[current_frame_index]:
                    return np.zeros(4, dtype=np.float32), 0.0, 0.0, 0.0, 0.0, 0.0
                box = [40, 40, 120, 120] if image.shape[0] == 160 else [64, 160, 192, 288]
                return np.array(box, dtype=np.float32), 0.91, 16.0, 3.0, 0.0, 0.0

            original_pid_factory = controller.create_position_pid

            def create_completed_pid(*args, **kwargs):
                pid = original_pid_factory(*args, **kwargs)
                pid.compute = Mock(return_value=(0, 0, {
                    "distance": 0.0, "angle_error": 0.0, "target_heading": 0.0,
                    "state": "COMPLETED", "is_completed": True,
                }))
                return pid

            camera = Mock()
            camera.isOpened.return_value = True
            camera.read.side_effect = read_frame
            compiled_model = Mock()
            compiled_model.get_property.return_value = ["CPU"]
            core = Mock()
            core.compile_model.return_value = compiled_model
            model = Mock(names={0: "Leanbot_0", 1: "Leanbot_p15"})
            clock = Mock(wraps=controller.time)
            clock.perf_counter.side_effect = lambda: current_time
            arguments = [
                "leanbotCameraController.py", "--ble", "0", "--show",
                "--full-model", str(model_dir), "--tracking-model", str(model_dir),
                "--target-config", str(root / "missing_target.json"), "--log", str(log_path),
                "--target-heading", "0", "--set-target-time", "1", "--fwd-bwd-time", "1",
            ]
            if auto_record_video:
                arguments.extend(["--video", str(root / "fake.avi")])
            output = io.StringIO()
            with contextlib.ExitStack() as stack:
                stack.enter_context(patch.object(controller, "current_dir", root / "controller"))
                stack.enter_context(patch.object(controller, "parent_dir", root))
                stack.enter_context(patch.object(controller, "YOLO", return_value=model))
                stack.enter_context(patch.object(controller.ov, "Core", return_value=core))
                stack.enter_context(patch.object(controller.cv2, "VideoCapture", return_value=camera))
                stack.enter_context(patch.object(controller, "time", clock))
                ble_constructor = stack.enter_context(patch.object(controller, "BLEMotorWorker"))
                inference = stack.enter_context(patch.object(controller, "select_best_vector_detection", side_effect=detect_frame))
                for method in ("namedWindow", "resizeWindow", "moveWindow", "imshow", "destroyAllWindows"):
                    stack.enter_context(patch.object(controller.cv2, method))
                stack.enter_context(patch.object(controller.cv2, "getWindowProperty", return_value=1))
                stack.enter_context(patch.object(controller.cv2, "waitKey", side_effect=[ord(key) if key else -1 for key in keys]))
                if complete_pid:
                    stack.enter_context(patch.object(controller, "create_position_pid", side_effect=create_completed_pid))
                stack.enter_context(patch.object(sys, "argv", arguments))
                stack.enter_context(contextlib.redirect_stdout(output))
                controller.main()

            ble_constructor.assert_not_called()
            camera.release.assert_called_once()
            self.assertEqual(inference.call_count, len(keys))
            rows = []
            if log_path.exists():
                with log_path.open(newline="", encoding="utf-8") as log_file:
                    rows = list(csv.DictReader(log_file))
            sessions = list((root / "lost_tracking_dataset").iterdir())
            self.assertEqual(len(sessions), 1)
            sample_names = {path.stem for path in (sessions[0] / "metadata").iterdir()}
            for directory in ("images", "labels", "check_labels"):
                self.assertEqual({path.stem for path in (sessions[0] / directory).iterdir()}, sample_names)
            samples = [json.loads(path.read_text(encoding="utf-8"))
                       for path in sorted((sessions[0] / "metadata").iterdir())]
            log_frames = [int(row["frame_id"]) for row in rows]
            self.assertTrue(all(sample["frame_id"] in log_frames for sample in samples))
            debug_dir = root / "controller" / "benchmark_logs" / "lost_tracking_captures"
            debug_frames = sorted(int(path.name.split("_")[2]) for path in debug_dir.glob("*_frame.png"))
            return {
                "sample_frames": [sample["frame_id"] for sample in samples],
                "source_frames": [sample["source_frame_id"] for sample in samples],
                "log_frames": log_frames,
                "debug_frames": debug_frames,
                "output": output.getvalue(),
            }

    def test_idle_camera_does_not_capture_lost_frames(self):
        result = self.run_session([True, False, False], [None, None, None])
        self.assertEqual(result["sample_frames"], [])
        self.assertEqual(result["debug_frames"], [])
        self.assertEqual(result["log_frames"], [])

    def test_auto_recorded_video_without_s_or_t_does_not_capture(self):
        result = self.run_session([True, False, False], [None, None, None], auto_record_video=True)
        self.assertEqual(result["sample_frames"], [])
        self.assertEqual(result["debug_frames"], [])
        self.assertEqual(result["log_frames"], [1, 2, 3])

    def test_s_starts_capture_and_c_stops_it(self):
        result = self.run_session(
            [True, False, True, False, False, False], ["s", None, None, "c", None, None],
        )
        self.assertEqual(result["sample_frames"], [2, 4])
        self.assertEqual(result["debug_frames"], [2, 4])
        self.assertEqual(result["log_frames"], [2, 3, 4])

    def test_t_starts_log_and_capture_then_c_stops_both(self):
        result = self.run_session(
            [True, False, True, False, False], ["t", None, None, "c", None],
        )
        self.assertEqual(result["sample_frames"], [2, 4])
        self.assertEqual(result["debug_frames"], [2, 4])
        self.assertEqual(result["log_frames"], [2, 3, 4])

    def test_pid_pause_does_not_capture_even_if_log_stays_open(self):
        result = self.run_session(
            [True, False, True, False, True, False], ["s", None, "p", None, "s", None],
        )
        self.assertEqual(result["sample_frames"], [2, 6])
        self.assertEqual(result["source_frames"], [1, 5])
        self.assertEqual(result["debug_frames"], [2, 6])
        self.assertEqual(result["log_frames"], [2, 3, 4, 5, 6])

    def test_failed_t_stops_log_and_capture(self):
        result = self.run_session(
            [True, False, False, False, False], ["t", None, None, None, None],
            frame_times=[0.0, 1.0, 2.0, 3.1, 4.0],
        )
        self.assertEqual(result["sample_frames"], [2, 3])
        self.assertEqual(result["debug_frames"], [2, 3])
        self.assertEqual(result["log_frames"], [2, 3])
        self.assertIn("[SET TARGET] FAILED", result["output"])

    def test_completed_t_stops_log_and_capture(self):
        result = self.run_session(
            [True, True, True, True, True, True, False, True,
             False, True, True, True, True, True, False, False],
            ["t"] + [None] * 15,
            frame_times=[0.0, 0.4, 0.8, 1.2, 1.6, 2.0, 2.4, 3.1,
                         3.3, 3.5, 3.8, 4.1, 4.4, 5.2, 5.3, 5.4],
        )
        self.assertEqual(result["sample_frames"], [7, 9])
        self.assertEqual(result["debug_frames"], [7, 9])
        self.assertEqual(result["log_frames"], list(range(2, 14)))
        self.assertIn("[SET TARGET] COMPLETED SUCCESSFULLY", result["output"])

    def test_s_captures_post_phase_actions_then_stops_on_completion(self):
        result = self.run_session(
            [True, True, False, False, False, False, False], ["s"] + [None] * 6,
            frame_times=[0.0, 0.1, 0.2, 2.3, 2.5, 3.2, 3.4], complete_pid=True,
        )
        self.assertEqual(result["sample_frames"], [3, 4, 5])
        self.assertEqual(result["debug_frames"], [3, 4, 5])
        self.assertEqual(result["log_frames"], [2, 3, 4, 5])
        self.assertIn("Post-Phase 4 re-verification completed", result["output"])


if __name__ == "__main__":
    unittest.main()
