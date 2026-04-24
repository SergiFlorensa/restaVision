from __future__ import annotations

from dataclasses import dataclass
from importlib.util import find_spec
from typing import Any

import numpy as np

from services.vision.geometry import BoundingBox, ScoredDetection, non_max_suppression

YOLO_PERSON_LABELS: tuple[str, ...] = ("person",)
YOLO_RESTAURANT_LABELS: tuple[str, ...] = (
    "person",
    "chair",
    "dining table",
    "cup",
    "bottle",
    "wine glass",
    "bowl",
    "fork",
    "knife",
    "spoon",
    "pizza",
)


@dataclass(frozen=True, slots=True)
class YoloDetectorConfig:
    model_path: str = "yolo11n.pt"
    confidence_threshold: float = 0.35
    iou_threshold: float = 0.5
    image_size: int = 640
    max_detections: int = 50
    min_box_area_ratio: float = 0.002
    allowed_labels: tuple[str, ...] = YOLO_PERSON_LABELS
    device: str | None = None

    def __post_init__(self) -> None:
        if not 0 <= self.confidence_threshold <= 1:
            raise ValueError("confidence_threshold must be between 0 and 1.")
        if not 0 <= self.iou_threshold <= 1:
            raise ValueError("iou_threshold must be between 0 and 1.")
        if self.image_size <= 0:
            raise ValueError("image_size must be positive.")
        if self.max_detections <= 0:
            raise ValueError("max_detections must be positive.")
        if not 0 <= self.min_box_area_ratio <= 1:
            raise ValueError("min_box_area_ratio must be between 0 and 1.")


class UltralyticsYoloDetector:
    """YOLO detection adapter with RestaurIA domain filtering.

    Ultralytics is imported lazily so the backend can run without YOLO installed.
    """

    def __init__(self, config: YoloDetectorConfig | None = None, model: Any | None = None) -> None:
        self.config = config or YoloDetectorConfig()
        self._model = model

    def detect(self, frame: np.ndarray) -> list[ScoredDetection]:
        model = self._load_model()
        predict_kwargs: dict[str, Any] = {
            "conf": self.config.confidence_threshold,
            "iou": self.config.iou_threshold,
            "imgsz": self.config.image_size,
            "max_det": self.config.max_detections,
            "verbose": False,
        }
        if self.config.device:
            predict_kwargs["device"] = self.config.device

        results = model.predict(frame, **predict_kwargs)
        if not results:
            return []

        detections = detections_from_ultralytics_result(
            results[0],
            allowed_labels=self.config.allowed_labels,
            min_confidence=self.config.confidence_threshold,
        )
        detections = sanitize_detections_for_frame(
            detections,
            frame_width=int(frame.shape[1]),
            frame_height=int(frame.shape[0]),
            min_area_ratio=self.config.min_box_area_ratio,
        )
        return non_max_suppression(detections, iou_threshold=self.config.iou_threshold)

    def _load_model(self) -> Any:
        if self._model is None:
            try:
                from ultralytics import YOLO
            except ModuleNotFoundError as exc:
                raise RuntimeError(
                    "Ultralytics is required for YOLO detection. Install requirements/ml.txt."
                ) from exc
            self._model = YOLO(self.config.model_path)
        return self._model


def is_ultralytics_available() -> bool:
    return find_spec("ultralytics") is not None


def detections_from_ultralytics_result(
    result: Any,
    allowed_labels: tuple[str, ...],
    min_confidence: float,
) -> list[ScoredDetection]:
    boxes = getattr(result, "boxes", None)
    if boxes is None:
        return []

    xyxy = _to_numpy(getattr(boxes, "xyxy", []))
    confidences = _to_numpy(getattr(boxes, "conf", []))
    classes = _to_numpy(getattr(boxes, "cls", [])).astype(int, copy=False)
    names = getattr(result, "names", {})

    detections: list[ScoredDetection] = []
    for index, (coordinates, confidence, class_id) in enumerate(
        zip(xyxy, confidences, classes, strict=False)
    ):
        score = float(confidence)
        if score < min_confidence:
            continue

        label = _label_for_class(names, int(class_id))
        if allowed_labels and label not in allowed_labels:
            continue

        try:
            bbox = BoundingBox(
                x_min=float(coordinates[0]),
                y_min=float(coordinates[1]),
                x_max=float(coordinates[2]),
                y_max=float(coordinates[3]),
            )
        except (IndexError, ValueError):
            continue

        detections.append(
            ScoredDetection(
                detection_id=f"{label}_{index}",
                bbox=bbox,
                score=score,
                label=label,
            )
        )
    return detections


def sanitize_detections_for_frame(
    detections: list[ScoredDetection],
    frame_width: int,
    frame_height: int,
    min_area_ratio: float = 0.0,
) -> list[ScoredDetection]:
    if frame_width <= 0 or frame_height <= 0:
        raise ValueError("frame dimensions must be positive.")
    if not 0 <= min_area_ratio <= 1:
        raise ValueError("min_area_ratio must be between 0 and 1.")

    min_area = frame_width * frame_height * min_area_ratio
    sanitized: list[ScoredDetection] = []
    for detection in detections:
        bbox = clip_bounding_box_to_frame(detection.bbox, frame_width, frame_height)
        if bbox is None or bbox.area < min_area:
            continue
        sanitized.append(
            ScoredDetection(
                detection_id=detection.detection_id,
                bbox=bbox,
                score=detection.score,
                label=detection.label,
            )
        )
    return sanitized


def clip_bounding_box_to_frame(
    bbox: BoundingBox,
    frame_width: int,
    frame_height: int,
) -> BoundingBox | None:
    if frame_width <= 0 or frame_height <= 0:
        raise ValueError("frame dimensions must be positive.")

    x_min = min(max(bbox.x_min, 0.0), float(frame_width))
    y_min = min(max(bbox.y_min, 0.0), float(frame_height))
    x_max = min(max(bbox.x_max, 0.0), float(frame_width))
    y_max = min(max(bbox.y_max, 0.0), float(frame_height))
    if x_max <= x_min or y_max <= y_min:
        return None
    return BoundingBox(x_min=x_min, y_min=y_min, x_max=x_max, y_max=y_max)


def draw_yolo_detections(frame: np.ndarray, detections: list[ScoredDetection]) -> np.ndarray:
    cv2 = _load_cv2()
    output = frame.copy()
    for detection in detections:
        x1 = int(round(detection.bbox.x_min))
        y1 = int(round(detection.bbox.y_min))
        x2 = int(round(detection.bbox.x_max))
        y2 = int(round(detection.bbox.y_max))
        label = detection.label or "object"
        cv2.rectangle(output, (x1, y1), (x2, y2), (18, 132, 54), 2)
        cv2.putText(
            output,
            f"{label} {detection.score:.2f}",
            (x1, max(20, y1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.58,
            (245, 245, 245),
            2,
            cv2.LINE_AA,
        )
    return output


def draw_detection_summary(
    frame: np.ndarray,
    detections: list[ScoredDetection],
    title: str = "YOLO restaurante",
) -> np.ndarray:
    cv2 = _load_cv2()
    output = frame.copy()
    counts = count_detections_by_label(detections)
    panel_lines = [title]
    panel_lines.extend(f"{label}: {count}" for label, count in counts.items())

    if not panel_lines:
        return output

    line_height = 24
    panel_width = 260
    panel_height = 20 + line_height * len(panel_lines)
    overlay = output.copy()
    cv2.rectangle(overlay, (12, 12), (12 + panel_width, 12 + panel_height), (16, 18, 22), -1)
    output = cv2.addWeighted(overlay, 0.72, output, 0.28, 0)

    for index, line in enumerate(panel_lines):
        y = 42 + index * line_height
        color = (245, 245, 245) if index == 0 else (198, 226, 180)
        cv2.putText(
            output,
            line,
            (24, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.56,
            color,
            2,
            cv2.LINE_AA,
        )
    return output


def count_detections_by_label(detections: list[ScoredDetection]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for detection in detections:
        label = detection.label or "object"
        counts[label] = counts.get(label, 0) + 1
    return dict(sorted(counts.items()))


def encode_jpeg(frame: np.ndarray, jpeg_quality: int = 80) -> bytes:
    if not 1 <= jpeg_quality <= 100:
        raise ValueError("jpeg_quality must be between 1 and 100.")
    cv2 = _load_cv2()
    ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality])
    if not ok:
        raise RuntimeError("Could not encode frame as JPEG.")
    return buffer.tobytes()


def _to_numpy(value: Any) -> np.ndarray:
    if hasattr(value, "detach"):
        value = value.detach()
    if hasattr(value, "cpu"):
        value = value.cpu()
    if hasattr(value, "numpy"):
        return np.asarray(value.numpy())
    return np.asarray(value)


def _label_for_class(names: Any, class_id: int) -> str:
    if isinstance(names, dict):
        return str(names.get(class_id, class_id))
    if isinstance(names, (list, tuple)) and 0 <= class_id < len(names):
        return str(names[class_id])
    return str(class_id)


def _load_cv2() -> Any:
    try:
        import cv2
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "OpenCV is required for YOLO demo drawing. Install requirements/ml.txt."
        ) from exc
    return cv2
