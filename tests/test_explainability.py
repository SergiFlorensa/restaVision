from __future__ import annotations

import numpy as np
import pytest
from services.vision.explainability import (
    PatchOcclusionConfig,
    normalize_importance_heatmap,
    occlusion_sensitivity,
)


def test_occlusion_sensitivity_finds_evidence_patch() -> None:
    image = np.zeros((16, 16), dtype=np.float32)
    image[4:8, 4:8] = 1.0

    def score_fn(candidate: np.ndarray) -> float:
        return float(candidate[4:8, 4:8].sum())

    explanation = occlusion_sensitivity(
        image,
        score_fn,
        table_id="table_01",
        score_name="dirty_table",
        config=PatchOcclusionConfig(patch_size=4, stride=4),
    )

    top_patch = explanation.top_patches(limit=1)[0]

    assert explanation.table_id == "table_01"
    assert explanation.base_score == pytest.approx(16.0)
    assert top_patch.x == 4
    assert top_patch.y == 4
    assert top_patch.score_delta == pytest.approx(16.0)
    assert explanation.heatmap[5, 5] > explanation.heatmap[0, 0]


def test_normalize_importance_heatmap_scales_values_to_unit_range() -> None:
    heatmap = np.array([[2.0, 4.0], [6.0, 10.0]])

    normalized = normalize_importance_heatmap(heatmap)

    assert normalized.min() == 0.0
    assert normalized.max() == 1.0


def test_occlusion_sensitivity_validates_score_function_outputs() -> None:
    image = np.zeros((4, 4), dtype=np.float32)

    with pytest.raises(ValueError, match="finite"):
        occlusion_sensitivity(image, lambda _: float("nan"))
