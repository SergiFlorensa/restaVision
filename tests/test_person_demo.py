from __future__ import annotations

import pytest
from services.vision.person_demo import DemoPersonDetection, DemoPersonDetectionConfig


def test_demo_person_detection_config_validates_dimensions() -> None:
    with pytest.raises(ValueError, match="width and height"):
        DemoPersonDetectionConfig(width=0)


def test_demo_person_detection_config_validates_jpeg_quality() -> None:
    with pytest.raises(ValueError, match="jpeg_quality"):
        DemoPersonDetectionConfig(jpeg_quality=101)


def test_demo_person_detection_defaults_to_person_label() -> None:
    detection = DemoPersonDetection(x=1, y=2, width=3, height=4, confidence=0.8)

    assert detection.label == "persona"
    assert detection.confidence == 0.8
