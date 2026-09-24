"""Collect lost frames with provisional YOLO labels from the last detection."""

import json
import logging
import math
import queue
import re
import threading
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import cv2
import numpy as np


IMAGE_SIZE = 640
CENTER_CROP_RATIO = 0.625
ANGLE_PATTERN = re.compile(r"^Leanbot_(?:(?P<sign>[pm])(?P<value>\d+)|(?P<plain>\d+))$")
LOGGER = logging.getLogger(__name__)


def _training_geometry(frame_shape):
    frame_height, frame_width = frame_shape[:2]
    crop_width = max(1, int(frame_width * CENTER_CROP_RATIO))
    start_x = (frame_width - crop_width) // 2
    square_size = max(crop_width, frame_height)
    pad_left = (square_size - crop_width) // 2
    pad_top = (square_size - frame_height) // 2
    return crop_width, start_x, square_size, pad_left, pad_top


def prepare_training_image(frame):
    """Match the controller's FULL center-crop, black-padding and 640 resize."""
    frame_height = frame.shape[0]
    crop_width, start_x, square_size, pad_left, pad_top = _training_geometry(frame.shape)
    padded = np.zeros((square_size, square_size, 3), dtype=frame.dtype)
    padded[pad_top:pad_top + frame_height, pad_left:pad_left + crop_width] = (
        frame[:, start_x:start_x + crop_width]
    )
    return cv2.resize(padded, (IMAGE_SIZE, IMAGE_SIZE))


def render_label_check(image, label, metadata):
    """Draw the exact serialized YOLO bbox and label name above the box."""
    preview = image.copy()
    image_height, image_width = preview.shape[:2]
    class_id, center_x, center_y, box_width, box_height = label.split()
    center_x, box_width = float(center_x) * image_width, float(box_width) * image_width
    center_y, box_height = float(center_y) * image_height, float(box_height) * image_height
    x_min = max(0, min(image_width - 1, round(center_x - box_width / 2)))
    y_min = max(0, min(image_height - 1, round(center_y - box_height / 2)))
    x_max = max(0, min(image_width - 1, round(center_x + box_width / 2)))
    y_max = max(0, min(image_height - 1, round(center_y + box_height / 2)))

    cv2.rectangle(preview, (x_min, y_min), (x_max, y_max), (0, 220, 0), 2, cv2.LINE_AA)

    label_text = str(metadata.get("class_name", class_id))
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.5
    thickness = 1
    (text_w, text_h), baseline = cv2.getTextSize(label_text, font, font_scale, thickness)
    text_x = max(0, min(x_min, image_width - text_w - 4))
    text_y = y_min - 4 if y_min - text_h - 4 >= 0 else y_min + text_h + 4

    bg_y1 = max(0, text_y - text_h - 2)
    bg_y2 = min(image_height, text_y + baseline)
    bg_x2 = min(image_width, text_x + text_w + 4)
    cv2.rectangle(preview, (text_x, bg_y1), (bg_x2, bg_y2), (0, 220, 0), -1)
    cv2.putText(preview, label_text, (text_x + 2, text_y - 1), font, font_scale, (0, 0, 0), thickness, cv2.LINE_AA)
    return preview

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "lost_tracking_dataset"


class LostTrackingCollector:
    """Single camera-thread producer, bounded background writer; no BLE dependency.

    Labels are copied, not re-detected or extrapolated. Review them before training,
    especially when the robot moves, rotates or leaves the camera view.
    """

    def __init__(self, output_dir=None, class_names=None, max_queue_size=32):
        if max_queue_size < 1:
            raise ValueError("max_queue_size must be at least 1")
        if output_dir is None:
            output_dir = DEFAULT_OUTPUT_DIR
        if class_names is None:
            raise ValueError("class_names must be provided")
        name_items = class_names.items() if isinstance(class_names, dict) else enumerate(class_names)
        self.class_names = {int(class_id): name for class_id, name in name_items}
        self._class_angles = {}
        for class_id, name in self.class_names.items():
            match = ANGLE_PATTERN.fullmatch(name)
            if match is None:
                continue
            if match.group("plain") is not None:
                class_angle = float(match.group("plain"))
            else:
                class_angle = float(match.group("value"))
                if match.group("sign") == "m":
                    class_angle = -class_angle
            self._class_angles[class_id] = class_angle
        if not self._class_angles:
            raise ValueError("No Leanbot angle classes found in model names")

        session_name = f"session_{datetime.now():%Y%m%d_%H%M%S_%f}_{uuid4().hex[:8]}"
        self.session_dir = Path(output_dir).expanduser().resolve() / session_name
        self.images_dir = self.session_dir / "images"
        self.labels_dir = self.session_dir / "labels"
        self.metadata_dir = self.session_dir / "metadata"
        self.check_labels_dir = self.session_dir / "check_labels"
        for directory in (self.images_dir, self.labels_dir, self.metadata_dir, self.check_labels_dir):
            directory.mkdir(parents=True, exist_ok=True)
        (self.session_dir / "classes.json").write_text(
            json.dumps(self.class_names, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        self.saved_count = 0
        self.dropped_count = 0
        self.skipped_count = 0
        self.failed_count = 0
        self._sample_count = 0
        self._last_detection = None
        self._closed = False
        self._queue = queue.Queue(maxsize=max_queue_size)
        self._thread = threading.Thread(target=self._writer_loop, name="lost-dataset-writer", daemon=True)
        self._thread.start()

    def _remember_detection(self, frame, frame_id, bbox_xyxy, angle, confidence, inference_mode):
        self._last_detection = None
        if bbox_xyxy is None or angle is None:
            return
        coordinates = tuple(float(value) for value in bbox_xyxy)
        angle = float(angle)
        if len(coordinates) != 4 or not all(math.isfinite(value) for value in (*coordinates, angle)):
            return
        x_min, y_min, x_max, y_max = coordinates
        frame_height, frame_width = frame.shape[:2]
        crop_width, start_x, square_size, pad_left, pad_top = _training_geometry(frame.shape)
        x_min = max(x_min, start_x)
        x_max = min(x_max, start_x + crop_width)
        y_min = max(y_min, 0.0)
        y_max = min(y_max, frame_height)
        if x_max <= x_min or y_max <= y_min:
            return
        class_id = min(
            self._class_angles,
            key=lambda candidate: abs((angle - self._class_angles[candidate] + 180.0) % 360.0 - 180.0),
        )
        yolo_bbox = [
            ((x_min + x_max) / 2.0 - start_x + pad_left) / square_size,
            ((y_min + y_max) / 2.0 + pad_top) / square_size,
            (x_max - x_min) / square_size,
            (y_max - y_min) / square_size,
        ]
        confidence = float(confidence) if confidence is not None else None
        if confidence is not None and not math.isfinite(confidence):
            confidence = None
        self._last_detection = {
            "source_frame_id": int(frame_id),
            "source_frame_size": [frame_width, frame_height],
            "source_inference_mode": inference_mode,
            "source_bbox_xyxy": list(coordinates),
            "source_angle_deg": angle,
            "source_confidence": confidence,
            "class_id": class_id,
            "class_name": self.class_names[class_id],
            "class_angle_deg": self._class_angles[class_id],
            "bbox_yolo": yolo_bbox,
        }

    def update(self, frame, frame_id, detected, bbox_xyxy=None, angle=None,
               confidence=None, inference_mode="FULL", collect_lost=True,
               best_conf=None):
        """Cache detections; enqueue lost frames only when collection is enabled."""
        if confidence is None and best_conf is not None:
            confidence = best_conf
        if self._closed:
            return False
        if detected:
            self._remember_detection(frame, frame_id, bbox_xyxy, angle, confidence, inference_mode)
            return False
        if not collect_lost:
            self._last_detection = None
            return False
        if self._last_detection is None:
            self.skipped_count += 1
            return False
        if self._last_detection["source_frame_size"] != [frame.shape[1], frame.shape[0]]:
            self._last_detection = None
            self.skipped_count += 1
            return False
        sample_number = self._sample_count + 1
        metadata = {
            **self._last_detection,
            "frame_id": int(frame_id),
            "frames_since_detection": int(frame_id) - self._last_detection["source_frame_id"],
            "inference_mode": inference_mode,
            "captured_at": datetime.now().astimezone().isoformat(timespec="milliseconds"),
            "label_source": "last_successful_detection",
            "requires_review": True,
            "image_size": [IMAGE_SIZE, IMAGE_SIZE],
            "center_crop_ratio": CENTER_CROP_RATIO,
        }
        stem = f"lost_{int(frame_id):08d}_{sample_number:06d}"
        try:
            self._queue.put_nowait((stem, frame.copy(), metadata))
        except queue.Full:
            self.dropped_count += 1
            if self.dropped_count == 1:
                LOGGER.warning("Lost dataset queue full; dropping samples rather than blocking the camera")
            return False
        self._sample_count = sample_number
        return True

    def _save_sample(self, stem, frame, metadata):
        image = prepare_training_image(frame)
        success, encoded = cv2.imencode(".png", image)
        if not success:
            raise OSError("Could not encode lost tracking image")
        image_path = self.images_dir / f"{stem}.png"
        label_path = self.labels_dir / f"{stem}.txt"
        metadata_path = self.metadata_dir / f"{stem}.json"
        check_path = self.check_labels_dir / f"{stem}.png"
        label = str(metadata["class_id"]) + " " + " ".join(
            f"{value:.6f}" for value in metadata["bbox_yolo"]
        ) + "\n"
        check_image = render_label_check(image, label, metadata)
        check_success, check_encoded = cv2.imencode(".png", check_image)
        if not check_success:
            raise OSError("Could not encode label check image")
        try:
            image_path.write_bytes(encoded.tobytes())
            label_path.write_text(label, encoding="utf-8")
            metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
            check_path.write_bytes(check_encoded.tobytes())
        except OSError:
            for path in (image_path, label_path, metadata_path, check_path):
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    LOGGER.warning("Could not remove incomplete lost dataset sample: %s", path)
            raise

    def _writer_loop(self):
        while True:
            sample = self._queue.get()
            try:
                if sample is None:
                    return
                self._save_sample(*sample)
                self.saved_count += 1
            except Exception as error:
                self.failed_count += 1
                if self.failed_count == 1:
                    LOGGER.warning("Could not save lost dataset sample: %s", error)
            finally:
                self._queue.task_done()

    def close(self):
        """Flush pending writes. Call after stopping the robot during shutdown."""
        if not self._closed:
            self._closed = True
            self._queue.put(None)
            self._thread.join()
