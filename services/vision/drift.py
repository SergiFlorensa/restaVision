from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import numpy as np

from services.vision.classical import sobel_gradients, to_grayscale_uint8


class VisualDriftLevel(StrEnum):
    OK = "ok"
    WARNING = "warning"
    DRIFT = "drift"


@dataclass(frozen=True, slots=True)
class VisualDistributionSignature:
    mean_intensity: float
    std_intensity: float
    edge_density: float
    histogram: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class VisualDriftConfig:
    histogram_bins: int = 16
    edge_threshold: float = 30.0
    warning_score: float = 0.18
    drift_score: float = 0.32

    def __post_init__(self) -> None:
        if self.histogram_bins <= 1:
            raise ValueError("histogram_bins must be greater than 1.")
        if self.edge_threshold < 0:
            raise ValueError("edge_threshold must be non-negative.")
        if not 0 <= self.warning_score <= self.drift_score:
            raise ValueError("warning_score must be between 0 and drift_score.")
        if self.drift_score > 1:
            raise ValueError("drift_score must be less than or equal to 1.")


@dataclass(frozen=True, slots=True)
class VisualDriftReport:
    score: float
    level: VisualDriftLevel
    brightness_delta: float
    contrast_delta: float
    edge_density_delta: float
    histogram_distance: float


class VisualDistributionMonitor:
    def __init__(
        self,
        baseline: VisualDistributionSignature,
        config: VisualDriftConfig | None = None,
    ) -> None:
        self.baseline = baseline
        self.config = config or VisualDriftConfig(histogram_bins=len(baseline.histogram))
        if len(self.baseline.histogram) != self.config.histogram_bins:
            raise ValueError("baseline histogram length must match histogram_bins.")

    def compare(self, current: VisualDistributionSignature) -> VisualDriftReport:
        if len(current.histogram) != self.config.histogram_bins:
            raise ValueError("current histogram length must match histogram_bins.")

        brightness_delta = abs(current.mean_intensity - self.baseline.mean_intensity) / 255
        contrast_delta = abs(current.std_intensity - self.baseline.std_intensity) / 128
        edge_density_delta = abs(current.edge_density - self.baseline.edge_density)
        histogram_distance = histogram_l1_distance(current.histogram, self.baseline.histogram)
        score = float(
            np.clip(
                0.25 * brightness_delta
                + 0.25 * contrast_delta
                + 0.25 * edge_density_delta
                + 0.25 * histogram_distance,
                0.0,
                1.0,
            )
        )

        if score >= self.config.drift_score:
            level = VisualDriftLevel.DRIFT
        elif score >= self.config.warning_score:
            level = VisualDriftLevel.WARNING
        else:
            level = VisualDriftLevel.OK

        return VisualDriftReport(
            score=score,
            level=level,
            brightness_delta=brightness_delta,
            contrast_delta=contrast_delta,
            edge_density_delta=edge_density_delta,
            histogram_distance=histogram_distance,
        )


def visual_distribution_signature(
    image: np.ndarray,
    config: VisualDriftConfig | None = None,
) -> VisualDistributionSignature:
    resolved_config = config or VisualDriftConfig()
    gray = to_grayscale_uint8(image)
    histogram, _ = np.histogram(
        gray,
        bins=resolved_config.histogram_bins,
        range=(0, 256),
        density=False,
    )
    total = float(histogram.sum())
    normalized_histogram = tuple((histogram / total).astype(float)) if total > 0 else ()
    gradients = sobel_gradients(gray)
    edge_density = float(np.mean(gradients.magnitude >= resolved_config.edge_threshold))
    return VisualDistributionSignature(
        mean_intensity=float(np.mean(gray)),
        std_intensity=float(np.std(gray)),
        edge_density=edge_density,
        histogram=normalized_histogram,
    )


def histogram_l1_distance(first: tuple[float, ...], second: tuple[float, ...]) -> float:
    if len(first) != len(second):
        raise ValueError("histograms must have the same length.")
    return float(np.sum(np.abs(np.asarray(first) - np.asarray(second))) / 2)
