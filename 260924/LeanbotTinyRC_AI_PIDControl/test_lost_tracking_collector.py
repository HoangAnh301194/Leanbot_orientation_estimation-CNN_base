import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np

from lost_tracking_collector import LostTrackingCollector, prepare_training_image, render_label_check


class LostTrackingCollectorTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="leanbot_lost_test_")
        self.addCleanup(self.temp_dir.cleanup)
        self.frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        self.class_names = {0: "Leanbot_0", 1: "Leanbot_p15", 12: "Leanbot_p180", 13: "Leanbot_p195"}
        self.bbox = [320.0, 160.0, 480.0, 320.0]

    def make_collector(self, **kwargs):
        collector = LostTrackingCollector(self.temp_dir.name, self.class_names, **kwargs)
        self.addCleanup(collector.close)
        return collector

    def remember(self, collector, frame_id=10, angle=16.0, bbox=None, frame=None):
        collector.update(
            self.frame if frame is None else frame, frame_id, True,
            bbox_xyxy=self.bbox if bbox is None else bbox,
            angle=angle, confidence=0.91, inference_mode="ROI",
        )

    def metadata(self, collector):
        return [json.loads(path.read_text(encoding="utf-8"))
                for path in sorted(collector.metadata_dir.glob("*.json"))]

    def labels(self, collector):
        return [path.read_text(encoding="utf-8").split()
                for path in sorted(collector.labels_dir.glob("*.txt"))]

    def test_no_label_before_first_detection(self):
        collector = self.make_collector()
        self.assertFalse(collector.update(self.frame, 1, False))
        collector.close()
        self.assertEqual(collector.skipped_count, 1)
        self.assertEqual(collector.saved_count, 0)
        self.assertEqual(list(collector.labels_dir.iterdir()), [])

    def test_inactive_loss_is_not_saved_and_clears_cached_label(self):
        collector = self.make_collector()
        self.remember(collector)
        self.assertFalse(collector.update(self.frame, 11, False, collect_lost=False))
        self.assertEqual(collector.skipped_count, 0)
        self.assertFalse(collector.update(self.frame, 12, False, collect_lost=True))
        self.assertEqual(collector.skipped_count, 1)
        self.remember(collector, frame_id=13)
        self.assertTrue(collector.update(self.frame, 14, False, collect_lost=True))
        collector.close()
        self.assertEqual(collector.saved_count, 1)
        self.assertEqual(self.metadata(collector)[0]["source_frame_id"], 13)

    def test_idle_detection_can_seed_first_running_lost_frame(self):
        collector = self.make_collector()
        collector.update(self.frame, 10, True, bbox_xyxy=self.bbox, angle=16.0, collect_lost=False)
        self.assertTrue(collector.update(self.frame, 11, False, collect_lost=True))
        collector.close()
        self.assertEqual(collector.saved_count, 1)
        self.assertEqual(self.metadata(collector)[0]["source_frame_id"], 10)

    def test_every_lost_frame_uses_current_image_and_last_valid_label(self):
        collector = self.make_collector()
        self.remember(collector)
        first_lost_frame = np.full_like(self.frame, 117)
        expected_image = prepare_training_image(first_lost_frame)
        self.assertTrue(collector.update(first_lost_frame, 11, False, inference_mode="ROI"))
        first_lost_frame.fill(0)
        self.assertTrue(collector.update(self.frame, 12, False, inference_mode="FULL"))
        collector.close()
        self.assertEqual(collector.saved_count, 2)
        images = sorted(collector.images_dir.glob("*.png"))
        saved_image = cv2.imdecode(np.frombuffer(images[0].read_bytes(), dtype=np.uint8), cv2.IMREAD_COLOR)
        self.assertEqual(saved_image.shape, (640, 640, 3))
        np.testing.assert_array_equal(saved_image, expected_image)
        labels = self.labels(collector)
        self.assertEqual(labels[0], labels[1])
        self.assertEqual(labels[0][0], "1")
        np.testing.assert_allclose([float(value) for value in labels[0][1:]], [0.2, 0.35, 0.2, 0.2])
        metadata = self.metadata(collector)
        self.assertEqual([item["source_frame_id"] for item in metadata], [10, 10])
        self.assertEqual([item["frames_since_detection"] for item in metadata], [1, 2])
        self.assertEqual([item["inference_mode"] for item in metadata], ["ROI", "FULL"])
        self.assertTrue(all(item["requires_review"] for item in metadata))
        self.assertEqual(metadata[0]["source_confidence"], 0.91)
        self.assertEqual(metadata[0]["class_angle_deg"], 15.0)
        self.assertEqual({path.stem for path in images}, {path.stem for path in collector.labels_dir.iterdir()})
        self.assertEqual({path.stem for path in images}, {path.stem for path in collector.check_labels_dir.iterdir()})

    def test_saved_label_check_is_separate_from_clean_training_image(self):
        collector = self.make_collector()
        self.remember(collector)
        collector.update(self.frame, 11, False)
        collector.close()
        image_path = next(collector.images_dir.glob("*.png"))
        check_path = collector.check_labels_dir / image_path.name
        image = cv2.imdecode(np.frombuffer(image_path.read_bytes(), dtype=np.uint8), cv2.IMREAD_COLOR)
        check_image = cv2.imdecode(np.frombuffer(check_path.read_bytes(), dtype=np.uint8), cv2.IMREAD_COLOR)
        self.assertEqual(check_image.shape, (640, 640, 3))
        np.testing.assert_array_equal(image, np.zeros_like(image))
        np.testing.assert_array_equal(check_image[160, 100], [0, 220, 0])
        self.assertTrue(np.any(check_image != image))

    def test_label_check_draws_serialized_bbox_and_label_text(self):
        image = np.full((640, 640, 3), 117, dtype=np.uint8)
        original_image = image.copy()
        metadata = {
            "class_name": "Leanbot_p15", "class_angle_deg": 15.0,
            "source_angle_deg": 16.0, "source_frame_id": 10,
            "frame_id": 11, "frames_since_detection": 1,
            "bbox_yolo": [0.9, 0.9, 0.1, 0.1],
        }
        with patch("lost_tracking_collector.cv2.rectangle", wraps=cv2.rectangle) as rectangle:
            with patch("lost_tracking_collector.cv2.putText", wraps=cv2.putText) as put_text:
                preview = render_label_check(image, "1 0.2 0.35 0.2 0.2", metadata)
        rect_args = [call.args[1:3] for call in rectangle.call_args_list]
        self.assertIn(((64, 160), (192, 288)), rect_args)
        texts = [call.args[1] for call in put_text.call_args_list]
        self.assertEqual(texts, ["Leanbot_p15"])
        self.assertEqual(preview.shape, image.shape)
        np.testing.assert_array_equal(image, original_image)

    def test_reacquisition_replaces_cached_label_without_saving_detected_frames(self):
        collector = self.make_collector()
        self.remember(collector)
        collector.update(self.frame, 11, False)
        self.remember(collector, frame_id=12, angle=-164.0, bbox=[400, 240, 600, 440])
        collector.update(self.frame, 13, False)
        collector.close()
        self.assertEqual(collector.saved_count, 2)
        metadata = self.metadata(collector)
        self.assertEqual([item["source_frame_id"] for item in metadata], [10, 12])
        self.assertEqual([label[0] for label in self.labels(collector)], ["1", "13"])
        self.assertNotEqual(metadata[0]["bbox_yolo"], metadata[1]["bbox_yolo"])

    def test_bbox_matches_object_pixels_after_crop_padding_resize(self):
        collector = self.make_collector()
        self.frame[160:320, 320:480] = (0, 255, 0)
        self.remember(collector)
        collector.update(self.frame, 11, False)
        collector.close()
        image_path = next(collector.images_dir.glob("*.png"))
        image = cv2.imdecode(np.frombuffer(image_path.read_bytes(), dtype=np.uint8), cv2.IMREAD_COLOR)
        rows, columns = np.nonzero(image[:, :, 1] > 128)
        center_x, center_y, width, height = [float(value) * 640 for value in self.labels(collector)[0][1:]]
        np.testing.assert_allclose(
            [columns.min(), rows.min(), columns.max() + 1, rows.max() + 1],
            [center_x - width / 2, center_y - height / 2, center_x + width / 2, center_y + height / 2],
            atol=1,
        )

    def test_bbox_clipping_keeps_labels_inside_real_image(self):
        collector = self.make_collector()
        self.remember(collector, bbox=[0, -40, 400, 800])
        collector.update(self.frame, 11, False)
        collector.close()
        np.testing.assert_allclose(
            [float(value) for value in self.labels(collector)[0][1:]], [0.1, 0.5, 0.2, 0.9]
        )

    def test_portrait_image_horizontal_padding(self):
        collector = self.make_collector()
        portrait = np.full((800, 640, 3), 255, dtype=np.uint8)
        self.remember(collector, frame=portrait, bbox=[120, 200, 520, 600])
        collector.update(portrait, 11, False)
        collector.close()
        np.testing.assert_allclose(
            [float(value) for value in self.labels(collector)[0][1:]], [0.5, 0.5, 0.5, 0.5]
        )

    def test_invalid_or_outside_bbox_does_not_reuse_older_detection(self):
        collector = self.make_collector()
        for bbox in ([0, 20, 200, 100], [400, 200, 300, 300], [320, 160, 320, 320],
                     [float("nan"), 0, 400, 400], [320, 160, float("inf"), 320], [320, 160, 480]):
            with self.subTest(bbox=bbox):
                self.remember(collector)
                self.remember(collector, frame_id=11, bbox=bbox)
                self.assertFalse(collector.update(self.frame, 12, False))
        collector.close()
        self.assertEqual(collector.saved_count, 0)

    def test_nonfinite_angle_does_not_create_label(self):
        collector = self.make_collector()
        for angle in (float("nan"), float("inf")):
            self.remember(collector, angle=angle)
            self.assertFalse(collector.update(self.frame, 11, False))

    def test_class_ids_follow_model_names_and_wrap_angles(self):
        self.class_names = {7: "Leanbot_p195", 9: "Leanbot_m15", 3: "Leanbot_0", 5: "Leanbot_p180", 21: "other"}
        collector = self.make_collector()
        for frame_id, angle in enumerate((-165.0, 345.0, 359.0, -179.0), start=10):
            self.remember(collector, frame_id=frame_id * 2, angle=angle)
            collector.update(self.frame, frame_id * 2 + 1, False)
        collector.close()
        self.assertEqual([label[0] for label in self.labels(collector)], ["7", "9", "3", "5"])
        self.assertEqual([item["class_angle_deg"] for item in self.metadata(collector)], [195.0, -15.0, 0.0, 180.0])
        class_map = json.loads((collector.session_dir / "classes.json").read_text(encoding="utf-8"))
        self.assertEqual(class_map["7"], "Leanbot_p195")

    def test_resolution_change_requires_new_detection(self):
        collector = self.make_collector()
        self.remember(collector)
        changed_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        self.assertFalse(collector.update(changed_frame, 11, False))
        self.assertFalse(collector.update(self.frame, 12, False))
        self.remember(collector, frame_id=13)
        self.assertTrue(collector.update(self.frame, 14, False))
        collector.close()
        self.assertEqual(collector.saved_count, 1)

    def test_full_queue_drops_samples_without_waiting_for_writer(self):
        collector = self.make_collector(max_queue_size=1)
        self.remember(collector)
        writer_started = threading.Event()
        release_writer = threading.Event()
        original_save = collector._save_sample

        def slow_save(*args):
            writer_started.set()
            if not release_writer.wait(timeout=5):
                raise TimeoutError("Test writer was not released")
            original_save(*args)

        with patch.object(collector, "_save_sample", side_effect=slow_save):
            try:
                self.assertTrue(collector.update(self.frame, 11, False))
                self.assertTrue(writer_started.wait(timeout=3))
                self.assertTrue(collector.update(self.frame, 12, False))
                with self.assertLogs("lost_tracking_collector", level="WARNING"):
                    self.assertFalse(collector.update(self.frame, 13, False))
            finally:
                release_writer.set()
                collector.close()
        self.assertEqual(collector.saved_count, 2)
        self.assertEqual(collector.dropped_count, 1)

    def test_write_failure_cleans_partial_pair_and_writer_recovers(self):
        collector = self.make_collector()
        self.remember(collector)
        with self.assertLogs("lost_tracking_collector", level="WARNING"):
            with patch.object(Path, "write_text", side_effect=OSError("disk full")):
                collector.update(self.frame, 11, False)
                collector._queue.join()
        self.assertEqual(collector.failed_count, 1)
        self.assertEqual(list(collector.images_dir.iterdir()), [])
        self.assertEqual(list(collector.labels_dir.iterdir()), [])
        self.assertEqual(list(collector.metadata_dir.iterdir()), [])
        self.assertEqual(list(collector.check_labels_dir.iterdir()), [])
        collector.update(self.frame, 12, False)
        collector.close()
        self.assertEqual(collector.saved_count, 1)

    def test_preview_write_failure_cleans_all_sample_files(self):
        collector = self.make_collector()
        self.remember(collector)
        original_write_bytes = Path.write_bytes

        def fail_check_write(path, data):
            if path.parent == collector.check_labels_dir:
                original_write_bytes(path, data[:10])
                raise OSError("Label check write failed")
            return original_write_bytes(path, data)

        with self.assertLogs("lost_tracking_collector", level="WARNING"):
            with patch.object(Path, "write_bytes", new=fail_check_write):
                collector.update(self.frame, 11, False)
                collector._queue.join()
        self.assertEqual(collector.failed_count, 1)
        for directory in (collector.images_dir, collector.labels_dir, collector.metadata_dir, collector.check_labels_dir):
            self.assertEqual(list(directory.iterdir()), [])
        collector.update(self.frame, 12, False)
        collector.close()
        self.assertEqual(collector.saved_count, 1)
        self.assertEqual(len(list(collector.check_labels_dir.iterdir())), 1)

    def test_preview_encode_failure_does_not_leave_incomplete_sample(self):
        collector = self.make_collector()
        self.remember(collector)
        encoded_image = cv2.imencode(".png", np.zeros((640, 640, 3), dtype=np.uint8))
        with self.assertLogs("lost_tracking_collector", level="WARNING"):
            with patch("lost_tracking_collector.cv2.imencode", side_effect=[encoded_image, (False, None)]):
                collector.update(self.frame, 11, False)
                collector.close()
        self.assertEqual(collector.failed_count, 1)
        for directory in (collector.images_dir, collector.labels_dir, collector.metadata_dir, collector.check_labels_dir):
            self.assertEqual(list(directory.iterdir()), [])

    def test_encode_failure_is_contained(self):
        collector = self.make_collector()
        self.remember(collector)
        with self.assertLogs("lost_tracking_collector", level="WARNING"):
            with patch("lost_tracking_collector.cv2.imencode", return_value=(False, None)):
                collector.update(self.frame, 11, False)
                collector.close()
        self.assertEqual(collector.failed_count, 1)
        self.assertEqual(list(collector.images_dir.iterdir()), [])

    def test_close_flushes_pending_writes_and_is_idempotent(self):
        collector = self.make_collector()
        self.remember(collector)
        for frame_id in range(11, 20):
            self.assertTrue(collector.update(self.frame, frame_id, False))
        collector.close()
        collector.close()
        self.assertEqual(collector.saved_count, 9)
        self.assertFalse(collector.update(self.frame, 20, False))
        self.assertFalse(collector._thread.is_alive())

    def test_invalid_configuration_fails_before_starting_writer(self):
        with self.assertRaises(ValueError):
            self.make_collector(max_queue_size=0)
        with self.assertRaises(ValueError):
            LostTrackingCollector(self.temp_dir.name, {0: "unknown"})


if __name__ == "__main__":
    unittest.main()
