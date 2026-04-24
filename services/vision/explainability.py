from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class PatchOcclusionConfig:
    patch_size: int = 16
    stride: int = 8
    baseline_value: float = 0.0

    def __post_init__(self) -> None:
        if self.patch_size <= 0:
            raise ValueError("patch_size must be positive.")
        if self.stride <= 0:
            raise ValueError("stride must be positive.")


@dataclass(frozen=True, slots=True)
class PatchScore:
    x: int
    y: int
    width: int
    height: int
    occluded_score: float
    score_delta: float


@dataclass(frozen=True, slots=True)
class PatchImportanceMap:
    table_id: str
    score_name: str
    base_score: float
    heatmap: np.ndarray
    patches: tuple[PatchScore, ...]

    def top_patches(self, limit: int = 5, *, positive_only: bool = True) -> tuple[PatchScore, ...]:
        if limit <= 0:
            raise ValueError("limit must be positive.")

        patches = self.patches
        if positive_only:
            patches = tuple(patch for patch in patches if patch.score_delta > 0)
        return tuple(sorted(patches, key=lambda patch: patch.score_delta, reverse=True)[:limit])


def occlusion_sensitivity(
    image: np.ndarray,
    score_fn: Callable[[np.ndarray], float],
    *,
    table_id: str = "",
    score_name: str = "target_score",
    config: PatchOcclusionConfig | None = None,
) -> PatchImportanceMap:
    """Measures local evidence by masking image patches and observing score drops."""

    config = config or PatchOcclusionConfig()
    image_array = np.asarray(image)
    if image_array.ndim not in (2, 3):
        raise ValueError("image must be a 2D grayscale or 3D color array.")
    if image_array.shape[0] == 0 or image_array.shape[1] == 0:
        raise ValueError("image cannot be empty.")

    height, width = image_array.shape[:2]
    base_score = float(score_fn(image_array))
    if not np.isfinite(base_score):
        raise ValueError("score_fn must return a finite score.")

    heatmap = np.zeros((height, width), dtype=np.float64)
    coverage = np.zeros((height, width), dtype=np.float64)
    patch_scores: list[PatchScore] = []

    for y in _patch_starts(height, config.patch_size, config.stride):
        for x in _patch_starts(width, config.patch_size, config.stride):
            y2 = min(y + config.patch_size, height)
            x2 = min(x + config.patch_size, width)
            masked = image_array.copy()
            masked[y:y2, x:x2, ...] = config.baseline_value
            occluded_score = float(score_fn(masked))
            if not np.isfinite(occluded_score):
                raise ValueError("score_fn must return finite scores for occluded images.")

            score_delta = base_score - occluded_score
            heatmap[y:y2, x:x2] += score_delta
            coverage[y:y2, x:x2] += 1
            patch_scores.append(
                PatchScore(
                    x=x,
                    y=y,
                    width=x2 - x,
                    height=y2 - y,
                    occluded_score=occluded_score,
                    score_delta=score_delta,
                )
            )

    np.divide(heatmap, coverage, out=heatmap, where=coverage > 0)
    return PatchImportanceMap(
        table_id=table_id,
        score_name=score_name,
        base_score=base_score,
        heatmap=heatmap,
        patches=tuple(patch_scores),
    )


def normalize_importance_heatmap(heatmap: np.ndarray) -> np.ndarray:
    values = np.asarray(heatmap, dtype=np.float64)
    if values.ndim != 2:
        raise ValueError("heatmap must be a 2D array.")

    min_value = float(values.min())
    max_value = float(values.max())
    if max_value == min_value:
        return np.zeros_like(values, dtype=np.float64)
    return (values - min_value) / (max_value - min_value)


def _patch_starts(length: int, patch_size: int, stride: int) -> tuple[int, ...]:
    if length <= patch_size:
        return (0,)

    starts = list(range(0, length - patch_size + 1, stride))
    last_start = length - patch_size
    if starts[-1] != last_start:
        starts.append(last_start)
    return tuple(starts)
