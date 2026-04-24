from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class MotionGateConfig:
    pixel_delta_threshold: float = 25.0
    motion_ratio_threshold: float = 0.05
    warmup_triggers_inference: bool = True
    shape_change_triggers_inference: bool = True


@dataclass(frozen=True, slots=True)
class MotionDecision:
    motion_detected: bool
    should_run_inference: bool
    changed_pixel_ratio: float
    mean_absolute_delta: float
    reason: str


class MotionGate:
    def __init__(self, config: MotionGateConfig | None = None) -> None:
        self.config = config or MotionGateConfig()
        self._previous_gray: np.ndarray | None = None

    def update(self, frame: np.ndarray) -> MotionDecision:
        current_gray = _to_grayscale_float(frame)
        previous_gray = self._previous_gray
        self._previous_gray = current_gray

        if previous_gray is None:
            return MotionDecision(
                motion_detected=True,
                should_run_inference=self.config.warmup_triggers_inference,
                changed_pixel_ratio=1.0,
                mean_absolute_delta=0.0,
                reason="warmup",
            )

        if previous_gray.shape != current_gray.shape:
            return MotionDecision(
                motion_detected=True,
                should_run_inference=self.config.shape_change_triggers_inference,
                changed_pixel_ratio=1.0,
                mean_absolute_delta=0.0,
                reason="shape_changed",
            )

        delta = np.abs(current_gray - previous_gray)
        changed_pixel_ratio = float(np.mean(delta >= self.config.pixel_delta_threshold))
        mean_absolute_delta = float(np.mean(delta))
        motion_detected = changed_pixel_ratio >= self.config.motion_ratio_threshold

        return MotionDecision(
            motion_detected=motion_detected,
            should_run_inference=motion_detected,
            changed_pixel_ratio=changed_pixel_ratio,
            mean_absolute_delta=mean_absolute_delta,
            reason="motion" if motion_detected else "static",
        )

    def reset(self) -> None:
        self._previous_gray = None


def detect_motion(
    previous_frame: np.ndarray,
    current_frame: np.ndarray,
    pixel_delta_threshold: float = 25.0,
    motion_ratio_threshold: float = 0.05,
) -> MotionDecision:
    previous_gray = _to_grayscale_float(previous_frame)
    current_gray = _to_grayscale_float(current_frame)
    if previous_gray.shape != current_gray.shape:
        raise ValueError("previous_frame and current_frame must have the same spatial shape.")

    delta = np.abs(current_gray - previous_gray)
    changed_pixel_ratio = float(np.mean(delta >= pixel_delta_threshold))
    mean_absolute_delta = float(np.mean(delta))
    motion_detected = changed_pixel_ratio >= motion_ratio_threshold
    return MotionDecision(
        motion_detected=motion_detected,
        should_run_inference=motion_detected,
        changed_pixel_ratio=changed_pixel_ratio,
        mean_absolute_delta=mean_absolute_delta,
        reason="motion" if motion_detected else "static",
    )


def _to_grayscale_float(frame: np.ndarray) -> np.ndarray:
    matrix = np.asarray(frame)
    if matrix.ndim == 2:
        return matrix.astype(float, copy=False)
    if matrix.ndim == 3 and matrix.shape[2] >= 3:
        channels = matrix[..., :3].astype(float, copy=False)
        return channels[..., 0] * 0.114 + channels[..., 1] * 0.587 + channels[..., 2] * 0.299
    raise ValueError("frame must be a 2D grayscale or 3D color image array.")
