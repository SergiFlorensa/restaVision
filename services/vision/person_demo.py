from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True, slots=True)
class DemoPersonDetection:
    x: int
    y: int
    width: int
    height: int
    confidence: float
    label: str = "persona"


@dataclass(frozen=True, slots=True)
class DemoPersonDetectionConfig:
    source: int | str = 0
    width: int = 640
    height: int = 480
    jpeg_quality: int = 80
    min_face_size: tuple[int, int] = (48, 48)

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("width and height must be positive.")
        if not 1 <= self.jpeg_quality <= 100:
            raise ValueError("jpeg_quality must be between 1 and 100.")
        if self.min_face_size[0] <= 0 or self.min_face_size[1] <= 0:
            raise ValueError("min_face_size values must be positive.")


class OpenCVPersonDemoDetector:
    """Lightweight local demo detector for webcam smoke tests.

    This detects human presence for local validation only. It does not identify people and it
    should be replaced by the production detector pipeline when YOLO/ByteTrack is connected.
    """

    def __init__(self, config: DemoPersonDetectionConfig | None = None) -> None:
        self.config = config or DemoPersonDetectionConfig()
        self._cv2: Any | None = None
        self._face_cascade: Any | None = None
        self._hog: Any | None = None

    def detect(self, frame: np.ndarray) -> list[DemoPersonDetection]:
        cv2 = self._load_cv2()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        detections = self._detect_faces(gray)
        if detections:
            return detections
        return self._detect_full_body(frame)

    def draw(self, frame: np.ndarray, detections: Iterable[DemoPersonDetection]) -> np.ndarray:
        cv2 = self._load_cv2()
        output = frame.copy()
        for detection in detections:
            x2 = detection.x + detection.width
            y2 = detection.y + detection.height
            cv2.rectangle(output, (detection.x, detection.y), (x2, y2), (40, 130, 55), 2)
            cv2.putText(
                output,
                f"{detection.label} {detection.confidence:.2f}",
                (detection.x, max(20, detection.y - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.58,
                (245, 245, 245),
                2,
                cv2.LINE_AA,
            )
        return output

    def encode_jpeg(self, frame: np.ndarray) -> bytes:
        cv2 = self._load_cv2()
        ok, buffer = cv2.imencode(
            ".jpg",
            frame,
            [int(cv2.IMWRITE_JPEG_QUALITY), self.config.jpeg_quality],
        )
        if not ok:
            raise RuntimeError("Could not encode frame as JPEG.")
        return buffer.tobytes()

    def _detect_faces(self, gray: np.ndarray) -> list[DemoPersonDetection]:
        face_cascade = self._load_face_cascade()
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.08,
            minNeighbors=5,
            minSize=self.config.min_face_size,
        )
        return [
            DemoPersonDetection(
                x=int(x),
                y=int(y),
                width=int(width),
                height=int(height),
                confidence=0.85,
            )
            for x, y, width, height in faces
        ]

    def _detect_full_body(self, frame: np.ndarray) -> list[DemoPersonDetection]:
        hog = self._load_hog()
        boxes, weights = hog.detectMultiScale(
            frame,
            winStride=(8, 8),
            padding=(8, 8),
            scale=1.05,
        )
        detections: list[DemoPersonDetection] = []
        for (x, y, width, height), weight in zip(boxes, weights, strict=False):
            if float(weight) < 0.25:
                continue
            detections.append(
                DemoPersonDetection(
                    x=int(x),
                    y=int(y),
                    width=int(width),
                    height=int(height),
                    confidence=min(0.99, max(0.25, float(weight))),
                )
            )
        return detections

    def _load_face_cascade(self) -> Any:
        if self._face_cascade is None:
            cv2 = self._load_cv2()
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            cascade = cv2.CascadeClassifier(cascade_path)
            if cascade.empty():
                raise RuntimeError("Could not load OpenCV frontal face cascade.")
            self._face_cascade = cascade
        return self._face_cascade

    def _load_hog(self) -> Any:
        if self._hog is None:
            cv2 = self._load_cv2()
            hog = cv2.HOGDescriptor()
            hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
            self._hog = hog
        return self._hog

    def _load_cv2(self) -> Any:
        if self._cv2 is None:
            try:
                import cv2
            except ModuleNotFoundError as exc:
                raise RuntimeError(
                    "OpenCV is required for the webcam demo. Install requirements/ml.txt."
                ) from exc
            self._cv2 = cv2
        return self._cv2
