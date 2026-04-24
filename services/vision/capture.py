from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import numpy as np


@dataclass(frozen=True, slots=True)
class CaptureConfig:
    source: int | str = 0
    source_id: str = "camera_01"
    target_width: int | None = 1280
    target_height: int | None = 720
    buffer_size: int = 1


@dataclass(frozen=True, slots=True)
class FramePacket:
    frame: np.ndarray
    captured_at: datetime
    frame_index: int
    source_id: str
    width: int
    height: int


class OpenCVCaptureAdapter:
    def __init__(self, config: CaptureConfig | None = None) -> None:
        self.config = config or CaptureConfig()
        self._capture: Any | None = None
        self._frame_index = 0

    def open(self) -> None:
        cv2 = _load_cv2()
        capture = cv2.VideoCapture(self.config.source)
        if self.config.buffer_size > 0:
            capture.set(cv2.CAP_PROP_BUFFERSIZE, self.config.buffer_size)
        if self.config.target_width is not None:
            capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.target_width)
        if self.config.target_height is not None:
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.target_height)
        if not capture.isOpened():
            capture.release()
            raise RuntimeError(f"Could not open video source: {self.config.source!r}")
        self._capture = capture

    def read(self) -> FramePacket | None:
        if self._capture is None:
            self.open()

        ok, frame = self._capture.read()
        if not ok or frame is None:
            return None

        packet = FramePacket(
            frame=frame,
            captured_at=datetime.now(UTC),
            frame_index=self._frame_index,
            source_id=self.config.source_id,
            width=int(frame.shape[1]),
            height=int(frame.shape[0]),
        )
        self._frame_index += 1
        return packet

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    def __enter__(self) -> OpenCVCaptureAdapter:
        self.open()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def _load_cv2() -> Any:
    try:
        import cv2
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "OpenCV is required for OpenCVCaptureAdapter. Install requirements/ml.txt."
        ) from exc
    return cv2
