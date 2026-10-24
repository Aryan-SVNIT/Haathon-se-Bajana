"""MediaPipe video-mode hand tracking and webcam helpers."""
import time

import cv2
import mediapipe as mp

from .config import CAMERA_INDEX, MODEL_PATH
from .model import ensure_model


class HandTrackingEngine:
    """Persistent MediaPipe hand tracker for one or two hands."""

    def __init__(self, max_hands: int = 1) -> None:
        ensure_model()
        base_options = mp.tasks.BaseOptions(model_asset_path=str(MODEL_PATH))
        options = mp.tasks.vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_hands=max_hands,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._landmarker = mp.tasks.vision.HandLandmarker.create_from_options(options)
        self.connections = mp.tasks.vision.HandLandmarksConnections.HAND_CONNECTIONS
        self._started_at = time.monotonic()
        self._last_timestamp_ms = -1

    def detect(self, frame_rgb):
        """Detect hands in an RGB frame and return MediaPipe's result object."""
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        timestamp_ms = max(
            int((time.monotonic() - self._started_at) * 1000),
            self._last_timestamp_ms + 1,
        )
        self._last_timestamp_ms = timestamp_ms
        return self._landmarker.detect_for_video(image, timestamp_ms)

    def close(self) -> None:
        """Release the MediaPipe model resources."""
        if self._landmarker is not None:
            self._landmarker.close()
            self._landmarker = None

    def __enter__(self) -> "HandTrackingEngine":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()


def open_camera():
    """Open the default Windows webcam with zero-latency buffer and smooth resolution."""
    camera = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
    if not camera.isOpened():
        camera.release()
        camera = cv2.VideoCapture(CAMERA_INDEX)
    if not camera.isOpened():
        camera.release()
        raise RuntimeError(
            "Could not open the webcam. Close apps using the camera (Teams/Zoom/browser) "
            "and check Windows Settings > Privacy & security > Camera."
        )

    # Set 1-frame buffer to eliminate camera lag/backlog, and use 640x480 for smooth 30+ FPS tracking.
    camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    camera.set(cv2.CAP_PROP_FPS, 30)
    return camera
