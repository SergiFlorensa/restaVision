from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from services.vision.geometry import ScoredDetection


@dataclass(frozen=True, slots=True)
class ClassDetectionRule:
    label: str
    confidence_threshold: float
    min_area_ratio: float = 0.0
    min_hits: int = 1
    window_size: int = 1

    def __post_init__(self) -> None:
        if not self.label:
            raise ValueError("label must not be empty.")
        if not 0 <= self.confidence_threshold <= 1:
            raise ValueError("confidence_threshold must be between 0 and 1.")
        if not 0 <= self.min_area_ratio <= 1:
            raise ValueError("min_area_ratio must be between 0 and 1.")
        if self.min_hits <= 0:
            raise ValueError("min_hits must be positive.")
        if self.window_size <= 0:
            raise ValueError("window_size must be positive.")
        if self.min_hits > self.window_size:
            raise ValueError("min_hits cannot be greater than window_size.")


@dataclass(frozen=True, slots=True)
class DetectionPolicyConfig:
    default_confidence_threshold: float = 0.35
    default_min_area_ratio: float = 0.0
    default_min_hits: int = 1
    default_window_size: int = 1
    rules: tuple[ClassDetectionRule, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not 0 <= self.default_confidence_threshold <= 1:
            raise ValueError("default_confidence_threshold must be between 0 and 1.")
        if not 0 <= self.default_min_area_ratio <= 1:
            raise ValueError("default_min_area_ratio must be between 0 and 1.")
        if self.default_min_hits <= 0:
            raise ValueError("default_min_hits must be positive.")
        if self.default_window_size <= 0:
            raise ValueError("default_window_size must be positive.")
        if self.default_min_hits > self.default_window_size:
            raise ValueError("default_min_hits cannot be greater than default_window_size.")


class DetectionPolicy:
    """Class-aware thresholds for restaurant object detection.

    Small service objects need lower confidence and temporal confirmation, while
    people should remain stricter and immediate.
    """

    def __init__(self, config: DetectionPolicyConfig | None = None) -> None:
        self.config = config or restaurant_service_policy_config()
        self._rules = {rule.label: rule for rule in self.config.rules}

    def rule_for(self, label: str | None) -> ClassDetectionRule:
        resolved_label = label or "object"
        return self._rules.get(
            resolved_label,
            ClassDetectionRule(
                label=resolved_label,
                confidence_threshold=self.config.default_confidence_threshold,
                min_area_ratio=self.config.default_min_area_ratio,
                min_hits=self.config.default_min_hits,
                window_size=self.config.default_window_size,
            ),
        )

    def filter_detections(
        self,
        detections: list[ScoredDetection],
        frame_width: int,
        frame_height: int,
    ) -> list[ScoredDetection]:
        if frame_width <= 0 or frame_height <= 0:
            raise ValueError("frame dimensions must be positive.")

        frame_area = frame_width * frame_height
        accepted: list[ScoredDetection] = []
        for detection in detections:
            rule = self.rule_for(detection.label)
            area_ratio = detection.bbox.area / frame_area
            if detection.score < rule.confidence_threshold:
                continue
            if area_ratio < rule.min_area_ratio:
                continue
            accepted.append(detection)
        return accepted


@dataclass(frozen=True, slots=True)
class EvidenceSnapshot:
    raw_counts: dict[str, int]
    stable_counts: dict[str, int]
    unstable_labels: tuple[str, ...]


class TemporalEvidenceAccumulator:
    """Confirms service objects across a rolling frame window."""

    def __init__(self, policy: DetectionPolicy | None = None) -> None:
        self.policy = policy or DetectionPolicy()
        self._history: dict[str, deque[int]] = {}

    def update(self, detections: list[ScoredDetection]) -> EvidenceSnapshot:
        raw_counts = _count_labels(detections)
        labels = set(raw_counts) | set(self._history)

        for label in labels:
            rule = self.policy.rule_for(label)
            history = self._history.get(label)
            if history is None or history.maxlen != rule.window_size:
                keep = max(0, rule.window_size - 1)
                previous = list(history or [])[-keep:] if keep else []
                history = deque(previous, maxlen=rule.window_size)
                self._history[label] = history
            history.append(raw_counts.get(label, 0))

        stable_counts: dict[str, int] = {}
        unstable_labels: list[str] = []
        for label in sorted(labels):
            rule = self.policy.rule_for(label)
            history_values = list(self._history[label])
            positive_values = [value for value in history_values if value > 0]
            if len(positive_values) >= rule.min_hits:
                stable_counts[label] = max(positive_values)
            elif raw_counts.get(label, 0) > 0:
                unstable_labels.append(label)

        return EvidenceSnapshot(
            raw_counts=raw_counts,
            stable_counts=stable_counts,
            unstable_labels=tuple(sorted(unstable_labels)),
        )

    def reset(self) -> None:
        self._history.clear()


def restaurant_service_policy_config() -> DetectionPolicyConfig:
    return DetectionPolicyConfig(
        default_confidence_threshold=0.35,
        default_min_area_ratio=0.0,
        default_min_hits=1,
        default_window_size=1,
        rules=(
            ClassDetectionRule("person", confidence_threshold=0.45, min_hits=1, window_size=1),
            ClassDetectionRule("chair", confidence_threshold=0.35, min_hits=1, window_size=1),
            ClassDetectionRule(
                "dining table",
                confidence_threshold=0.35,
                min_hits=1,
                window_size=1,
            ),
            ClassDetectionRule("cup", confidence_threshold=0.32, min_hits=2, window_size=4),
            ClassDetectionRule("bottle", confidence_threshold=0.32, min_hits=2, window_size=4),
            ClassDetectionRule("wine glass", confidence_threshold=0.30, min_hits=2, window_size=4),
            ClassDetectionRule("bowl", confidence_threshold=0.28, min_hits=2, window_size=4),
            ClassDetectionRule("fork", confidence_threshold=0.22, min_hits=3, window_size=5),
            ClassDetectionRule("knife", confidence_threshold=0.22, min_hits=3, window_size=5),
            ClassDetectionRule("spoon", confidence_threshold=0.22, min_hits=3, window_size=5),
            ClassDetectionRule("pizza", confidence_threshold=0.28, min_hits=2, window_size=4),
            ClassDetectionRule("sandwich", confidence_threshold=0.28, min_hits=2, window_size=4),
            ClassDetectionRule("hot dog", confidence_threshold=0.28, min_hits=2, window_size=4),
            ClassDetectionRule("cake", confidence_threshold=0.28, min_hits=2, window_size=4),
            ClassDetectionRule("donut", confidence_threshold=0.28, min_hits=2, window_size=4),
            ClassDetectionRule("banana", confidence_threshold=0.28, min_hits=2, window_size=4),
            ClassDetectionRule("apple", confidence_threshold=0.28, min_hits=2, window_size=4),
            ClassDetectionRule("orange", confidence_threshold=0.28, min_hits=2, window_size=4),
            ClassDetectionRule("broccoli", confidence_threshold=0.28, min_hits=2, window_size=4),
            ClassDetectionRule("carrot", confidence_threshold=0.28, min_hits=2, window_size=4),
            ClassDetectionRule("hand_raised", confidence_threshold=0.50, min_hits=2, window_size=4),
            ClassDetectionRule("raised_hand", confidence_threshold=0.50, min_hits=2, window_size=4),
            ClassDetectionRule(
                "finger_raised",
                confidence_threshold=0.50,
                min_hits=2,
                window_size=4,
            ),
            ClassDetectionRule("call_waiter", confidence_threshold=0.50, min_hits=2, window_size=4),
        ),
    )


def _count_labels(detections: list[ScoredDetection]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for detection in detections:
        label = detection.label or "object"
        counts[label] = counts.get(label, 0) + 1
    return dict(sorted(counts.items()))
