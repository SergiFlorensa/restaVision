from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from services.vision.geometry import BoundingBox
from services.vision.yolo_detector import clip_bounding_box_to_frame

COCO_POSE_KEYPOINTS: tuple[str, ...] = (
    "nose",
    "left_eye",
    "right_eye",
    "left_ear",
    "right_ear",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
)

COCO_POSE_SKELETON: tuple[tuple[int, int], ...] = (
    (5, 6),
    (5, 7),
    (7, 9),
    (6, 8),
    (8, 10),
    (5, 11),
    (6, 12),
    (11, 12),
    (11, 13),
    (13, 15),
    (12, 14),
    (14, 16),
    (0, 1),
    (0, 2),
    (1, 3),
    (2, 4),
)


@dataclass(frozen=True, slots=True)
class PoseKeypoint:
    name: str
    x: float
    y: float
    confidence: float


@dataclass(frozen=True, slots=True)
class HumanPose:
    pose_id: str
    bbox: BoundingBox
    score: float
    keypoints: tuple[PoseKeypoint, ...]

    @property
    def visible_keypoints(self) -> tuple[PoseKeypoint, ...]:
        return tuple(keypoint for keypoint in self.keypoints if keypoint.confidence > 0)


@dataclass(frozen=True, slots=True)
class YoloPoseConfig:
    model_path: str = "yolo11n-pose.pt"
    confidence_threshold: float = 0.35
    iou_threshold: float = 0.5
    image_size: int = 256
    max_detections: int = 10
    keypoint_confidence_threshold: float = 0.35
    min_box_area_ratio: float = 0.002
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
        if not 0 <= self.keypoint_confidence_threshold <= 1:
            raise ValueError("keypoint_confidence_threshold must be between 0 and 1.")
        if not 0 <= self.min_box_area_ratio <= 1:
            raise ValueError("min_box_area_ratio must be between 0 and 1.")


class UltralyticsYoloPoseEstimator:
    """Optional YOLO pose adapter for CPU-friendly human skeleton demos."""

    def __init__(self, config: YoloPoseConfig | None = None, model: Any | None = None) -> None:
        self.config = config or YoloPoseConfig()
        self._model = model

    def detect(self, frame: np.ndarray) -> list[HumanPose]:
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
        return poses_from_ultralytics_result(
            results[0],
            frame_width=int(frame.shape[1]),
            frame_height=int(frame.shape[0]),
            min_confidence=self.config.confidence_threshold,
            min_keypoint_confidence=self.config.keypoint_confidence_threshold,
            min_area_ratio=self.config.min_box_area_ratio,
        )

    def _load_model(self) -> Any:
        if self._model is None:
            try:
                from ultralytics import YOLO
            except ModuleNotFoundError as exc:
                raise RuntimeError(
                    "Ultralytics is required for YOLO pose. Install requirements/ml.txt."
                ) from exc
            self._model = YOLO(self.config.model_path)
        return self._model


def poses_from_ultralytics_result(
    result: Any,
    frame_width: int,
    frame_height: int,
    min_confidence: float,
    min_keypoint_confidence: float,
    min_area_ratio: float = 0.0,
) -> list[HumanPose]:
    boxes = getattr(result, "boxes", None)
    keypoints = getattr(result, "keypoints", None)
    if boxes is None or keypoints is None:
        return []

    xyxy = _to_numpy(getattr(boxes, "xyxy", []))
    box_confidences = _to_numpy(getattr(boxes, "conf", []))
    keypoint_xy = _to_numpy(getattr(keypoints, "xy", []))
    keypoint_confidences = _to_numpy(getattr(keypoints, "conf", []))
    min_area = frame_width * frame_height * min_area_ratio

    poses: list[HumanPose] = []
    for index, (coordinates, score) in enumerate(zip(xyxy, box_confidences, strict=False)):
        confidence = float(score)
        if confidence < min_confidence:
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
        bbox = clip_bounding_box_to_frame(bbox, frame_width, frame_height)
        if bbox is None or bbox.area < min_area:
            continue
        if index >= len(keypoint_xy):
            continue

        person_points = keypoint_xy[index]
        person_confidences = (
            keypoint_confidences[index]
            if index < len(keypoint_confidences)
            else np.ones(len(person_points), dtype=np.float32)
        )
        pose_keypoints = _pose_keypoints(
            person_points,
            person_confidences,
            min_keypoint_confidence,
        )
        poses.append(
            HumanPose(
                pose_id=f"pose_{index}",
                bbox=bbox,
                score=confidence,
                keypoints=tuple(pose_keypoints),
            )
        )
    return poses


def draw_pose_detections(
    frame: np.ndarray,
    poses: list[HumanPose],
    *,
    draw_boxes: bool = False,
    draw_silhouette: bool = True,
) -> np.ndarray:
    cv2 = _load_cv2()
    output = frame.copy()

    for pose in poses:
        if draw_silhouette:
            output = _draw_pose_silhouette(output, pose, cv2)
        _draw_pose_skeleton(output, pose, cv2)
        if draw_boxes:
            _draw_pose_box(output, pose, cv2)
    return output


def _pose_keypoints(
    points: np.ndarray,
    confidences: np.ndarray,
    min_keypoint_confidence: float,
) -> list[PoseKeypoint]:
    pose_keypoints: list[PoseKeypoint] = []
    for index, point in enumerate(points[: len(COCO_POSE_KEYPOINTS)]):
        confidence = float(confidences[index]) if index < len(confidences) else 1.0
        if confidence < min_keypoint_confidence:
            confidence = 0.0
        pose_keypoints.append(
            PoseKeypoint(
                name=COCO_POSE_KEYPOINTS[index],
                x=float(point[0]),
                y=float(point[1]),
                confidence=confidence,
            )
        )
    return pose_keypoints


def _draw_pose_skeleton(output: np.ndarray, pose: HumanPose, cv2: Any) -> None:
    points = pose.keypoints
    for start, end in COCO_POSE_SKELETON:
        if start >= len(points) or end >= len(points):
            continue
        first = points[start]
        second = points[end]
        if first.confidence <= 0 or second.confidence <= 0:
            continue
        cv2.line(
            output,
            (round(first.x), round(first.y)),
            (round(second.x), round(second.y)),
            (62, 185, 96),
            2,
            cv2.LINE_AA,
        )

    for keypoint in points:
        if keypoint.confidence <= 0:
            continue
        cv2.circle(output, (round(keypoint.x), round(keypoint.y)), 3, (245, 245, 245), -1)


def _draw_pose_silhouette(output: np.ndarray, pose: HumanPose, cv2: Any) -> np.ndarray:
    visible = np.array(
        [(keypoint.x, keypoint.y) for keypoint in pose.visible_keypoints],
        dtype=np.float32,
    )
    if len(visible) < 3:
        return output

    hull = cv2.convexHull(visible.astype(np.int32))
    overlay = output.copy()
    cv2.fillConvexPoly(overlay, hull, (62, 185, 96))
    output = cv2.addWeighted(overlay, 0.16, output, 0.84, 0)
    cv2.polylines(output, [hull], isClosed=True, color=(62, 185, 96), thickness=1)
    return output


def _draw_pose_box(output: np.ndarray, pose: HumanPose, cv2: Any) -> None:
    x1 = int(round(pose.bbox.x_min))
    y1 = int(round(pose.bbox.y_min))
    x2 = int(round(pose.bbox.x_max))
    y2 = int(round(pose.bbox.y_max))
    cv2.rectangle(output, (x1, y1), (x2, y2), (18, 132, 54), 1)
    cv2.putText(
        output,
        f"pose {pose.score:.2f}",
        (x1, max(20, y1 - 8)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.52,
        (245, 245, 245),
        2,
        cv2.LINE_AA,
    )


def _to_numpy(value: Any) -> np.ndarray:
    if hasattr(value, "detach"):
        value = value.detach()
    if hasattr(value, "cpu"):
        value = value.cpu()
    if hasattr(value, "numpy"):
        return np.asarray(value.numpy())
    return np.asarray(value)


def _load_cv2() -> Any:
    try:
        import cv2
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "OpenCV is required for pose drawing. Install requirements/ml.txt."
        ) from exc
    return cv2
