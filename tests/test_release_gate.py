from __future__ import annotations

from services.evaluation import evaluate_probability_predictions
from services.governance import (
    ModelReleaseCandidate,
    ReleaseGateConfig,
    ReleaseGateStatus,
    evaluate_model_release,
)


def test_release_gate_approves_candidate_that_meets_metrics_and_controls() -> None:
    candidate = ModelReleaseCandidate(
        model_id="restauria-yolo",
        model_version="2026.04.24",
        dataset_id="validation-v1",
        accuracy=0.91,
        macro_f1=0.88,
        expected_calibration_error=0.04,
        p95_latency_ms=120,
        model_size_mb=18,
        test_set_locked=True,
        lineage_complete=True,
        privacy_review_passed=True,
        training_serving_consistency_checked=True,
        rollback_plan_ready=True,
    )

    report = evaluate_model_release(
        candidate,
        ReleaseGateConfig(max_model_size_mb=25),
    )

    assert report.status == ReleaseGateStatus.APPROVED
    assert report.approved
    assert report.blockers == ()


def test_release_gate_blocks_low_f1_and_missing_governance_controls() -> None:
    candidate = ModelReleaseCandidate(
        model_id="restauria-yolo",
        model_version="2026.04.24",
        dataset_id="validation-v1",
        accuracy=0.86,
        macro_f1=0.51,
        expected_calibration_error=0.16,
        p95_latency_ms=300,
        test_set_locked=False,
        lineage_complete=False,
        privacy_review_passed=True,
        training_serving_consistency_checked=False,
        rollback_plan_ready=False,
    )

    report = evaluate_model_release(candidate)
    blocker_names = {check.name for check in report.blockers}

    assert report.status == ReleaseGateStatus.BLOCKED
    assert not report.approved
    assert "macro_f1" in blocker_names
    assert "expected_calibration_error" in blocker_names
    assert "p95_latency_ms" in blocker_names
    assert "test_set_locked" in blocker_names
    assert "lineage_complete" in blocker_names
    assert "training_serving_consistency_checked" in blocker_names
    assert "rollback_plan_ready" in blocker_names


def test_release_candidate_can_be_created_from_probability_report() -> None:
    probability_report = evaluate_probability_predictions(
        labels=("ready", "occupied"),
        y_true=("ready", "occupied", "occupied"),
        probability_rows=[
            {"ready": 0.95, "occupied": 0.05},
            {"ready": 0.10, "occupied": 0.90},
            {"ready": 0.20, "occupied": 0.80},
        ],
        bins=2,
    )

    candidate = ModelReleaseCandidate.from_probability_report(
        model_id="restauria-yolo",
        model_version="2026.04.24",
        dataset_id="test-v1",
        report=probability_report,
        p95_latency_ms=90,
        test_set_locked=True,
        lineage_complete=True,
        privacy_review_passed=True,
        training_serving_consistency_checked=True,
        rollback_plan_ready=True,
    )
    report = evaluate_model_release(
        candidate,
        ReleaseGateConfig(
            min_accuracy=0.90,
            min_macro_f1=0.90,
            max_expected_calibration_error=0.20,
            max_p95_latency_ms=100,
        ),
    )

    assert candidate.accuracy == probability_report.accuracy
    assert candidate.macro_f1 == probability_report.classification.macro_f1
    assert report.status == ReleaseGateStatus.APPROVED


def test_release_gate_can_relax_non_mvp_controls_explicitly() -> None:
    candidate = ModelReleaseCandidate(
        model_id="baseline",
        model_version="dev",
        dataset_id="dev-validation",
        accuracy=0.82,
        macro_f1=0.76,
        expected_calibration_error=0.08,
        p95_latency_ms=80,
    )

    report = evaluate_model_release(
        candidate,
        ReleaseGateConfig(
            require_locked_test_set=False,
            require_lineage=False,
            require_privacy_review=False,
            require_training_serving_consistency=False,
            require_rollback_plan=False,
        ),
    )

    assert report.status == ReleaseGateStatus.APPROVED
    assert all(check.passed for check in report.checks)
