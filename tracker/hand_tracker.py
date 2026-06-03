"""
HandTracker — wraps MediaPipe LIVE_STREAM HandLandmarker.
Refactored from Marker.py into a reusable context-manager class.
"""
import time
import mediapipe as mp
import numpy as np

BaseOptions = mp.tasks.BaseOptions
HandLandmarker = mp.tasks.vision.HandLandmarker
HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
HandLandmarkerResult = mp.tasks.vision.HandLandmarkerResult
VisionRunningMode = mp.tasks.vision.RunningMode

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (0, 9), (9, 10), (10, 11), (11, 12),
    (0, 13), (13, 14), (14, 15), (15, 16),
    (0, 17), (17, 18), (18, 19), (19, 20),
    (5, 9), (9, 13), (13, 17),
]


class HandTracker:
    """
    Context manager that wraps MediaPipe HandLandmarker in LIVE_STREAM mode.

    Usage:
        with HandTracker('hand_landmarker.task') as tracker:
            landmarks = tracker.process_frame(bgr_frame)
            # landmarks: list of hands, each hand is a list of 21 NormalizedLandmark
            # None if no hands detected yet
    """

    def __init__(self, model_path: str = 'hand_landmarker.task', num_hands: int = 1):
        self._model_path = model_path
        self._num_hands = num_hands
        self._latest_result: HandLandmarkerResult | None = None
        self._landmarker: HandLandmarker | None = None

    def __enter__(self) -> 'HandTracker':
        options = HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=self._model_path),
            running_mode=VisionRunningMode.LIVE_STREAM,
            num_hands=self._num_hands,
            result_callback=self._on_result,
        )
        self._landmarker = HandLandmarker.create_from_options(options)
        return self

    def __exit__(self, *args):
        if self._landmarker:
            self._landmarker.close()

    def _on_result(self, result: HandLandmarkerResult, output_image: mp.Image, timestamp_ms: int):
        self._latest_result = result

    def process_frame(self, bgr_frame: np.ndarray) -> list | None:
        """
        Send a BGR frame to MediaPipe for async detection.
        Returns the most recently received landmark list:
          - list of hands (each hand = list of 21 NormalizedLandmark)
          - None if no result available yet or no hands in frame
        """
        import cv2
        rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        timestamp_ms = int(time.time() * 1000)
        self._landmarker.detect_async(mp_image, timestamp_ms)

        if self._latest_result and self._latest_result.hand_landmarks:
            return self._latest_result.hand_landmarks
        return None
