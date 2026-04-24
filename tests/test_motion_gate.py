from __future__ import annotations

import numpy as np
from services.vision.motion import MotionGate, MotionGateConfig, detect_motion


def test_detect_motion_rejects_static_frame() -> None:
    previous = np.zeros((10, 10), dtype=np.uint8)
    current = np.zeros((10, 10), dtype=np.uint8)

    decision = detect_motion(previous, current)

    assert not decision.motion_detected
    assert not decision.should_run_inference
    assert decision.changed_pixel_ratio == 0.0
    assert decision.reason == "static"


def test_detect_motion_triggers_when_enough_pixels_change() -> None:
    previous = np.zeros((10, 10), dtype=np.uint8)
    current = np.zeros((10, 10), dtype=np.uint8)
    current[:3, :3] = 255

    decision = detect_motion(
        previous,
        current,
        pixel_delta_threshold=25,
        motion_ratio_threshold=0.05,
    )

    assert decision.motion_detected
    assert decision.should_run_inference
    assert decision.changed_pixel_ratio == 0.09
    assert decision.reason == "motion"


def test_motion_gate_runs_warmup_once_then_skips_static_frames() -> None:
    gate = MotionGate(MotionGateConfig(warmup_triggers_inference=True))
    frame = np.zeros((10, 10), dtype=np.uint8)

    warmup = gate.update(frame)
    static = gate.update(frame)

    assert warmup.should_run_inference
    assert warmup.reason == "warmup"
    assert not static.should_run_inference
    assert static.reason == "static"
