from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from services.evaluation import ProbabilityEvaluationReport


class GateSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    BLOCKER = "blocker"


class ReleaseGateStatus(StrEnum):
    APPROVED = "approved"
    APPROVED_WITH_WARNINGS = "approved_with_warnings"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class ModelReleaseCandidate:
    model_id: str
    model_version: str
    dataset_id: str
    accuracy: float
    macro_f1: float
    expected_calibration_error: float
    p95_latency_ms: float
    model_size_mb: float | None = None
    test_set_locked: bool = False
    lineage_complete: bool = False
    privacy_review_passed: bool = False
    training_serving_consistency_checked: bool = False
    rollback_plan_ready: bool = False
    notes: str = ""

    @classmethod
    def from_probability_report(
        cls,
        *,
        model_id: str,
        model_version: str,
        dataset_id: str,
        report: ProbabilityEvaluationReport,
        p95_latency_ms: float,
        model_size_mb: float | None = None,
        test_set_locked: bool = False,
        lineage_complete: bool = False,
        privacy_review_passed: bool = False,
        training_serving_consistency_checked: bool = False,
        rollback_plan_ready: bool = False,
        notes: str = "",
    ) -> ModelReleaseCandidate:
        return cls(
            model_id=model_id,
            model_version=model_version,
            dataset_id=dataset_id,
            accuracy=report.accuracy,
            macro_f1=report.classification.macro_f1,
            expected_calibration_error=report.calibration.expected_calibration_error,
            p95_latency_ms=p95_latency_ms,
            model_size_mb=model_size_mb,
            test_set_locked=test_set_locked,
            lineage_complete=lineage_complete,
            privacy_review_passed=privacy_review_passed,
            training_serving_consistency_checked=training_serving_consistency_checked,
            rollback_plan_ready=rollback_plan_ready,
            notes=notes,
        )

    def validate(self) -> None:
        if not self.model_id:
            raise ValueError("model_id cannot be empty.")
        if not self.model_version:
            raise ValueError("model_version cannot be empty.")
        if not self.dataset_id:
            raise ValueError("dataset_id cannot be empty.")
        for name, value in (
            ("accuracy", self.accuracy),
            ("macro_f1", self.macro_f1),
            ("expected_calibration_error", self.expected_calibration_error),
        ):
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1.")
        if self.p95_latency_ms < 0:
            raise ValueError("p95_latency_ms must be non-negative.")
        if self.model_size_mb is not None and self.model_size_mb < 0:
            raise ValueError("model_size_mb must be non-negative.")


@dataclass(frozen=True, slots=True)
class ReleaseGateConfig:
    min_accuracy: float = 0.80
    min_macro_f1: float = 0.75
    max_expected_calibration_error: float = 0.10
    max_p95_latency_ms: float = 250.0
    max_model_size_mb: float | None = None
    require_locked_test_set: bool = True
    require_lineage: bool = True
    require_privacy_review: bool = True
    require_training_serving_consistency: bool = True
    require_rollback_plan: bool = True

    def __post_init__(self) -> None:
        for name, value in (
            ("min_accuracy", self.min_accuracy),
            ("min_macro_f1", self.min_macro_f1),
            ("max_expected_calibration_error", self.max_expected_calibration_error),
        ):
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1.")
        if self.max_p95_latency_ms < 0:
            raise ValueError("max_p95_latency_ms must be non-negative.")
        if self.max_model_size_mb is not None and self.max_model_size_mb < 0:
            raise ValueError("max_model_size_mb must be non-negative.")


@dataclass(frozen=True, slots=True)
class ReleaseGateCheck:
    name: str
    passed: bool
    severity: GateSeverity
    observed: str
    expected: str
    message: str


@dataclass(frozen=True, slots=True)
class ReleaseGateReport:
    status: ReleaseGateStatus
    candidate: ModelReleaseCandidate
    checks: tuple[ReleaseGateCheck, ...]

    @property
    def approved(self) -> bool:
        return self.status in (
            ReleaseGateStatus.APPROVED,
            ReleaseGateStatus.APPROVED_WITH_WARNINGS,
        )

    @property
    def blockers(self) -> tuple[ReleaseGateCheck, ...]:
        return tuple(
            check
            for check in self.checks
            if not check.passed and check.severity == GateSeverity.BLOCKER
        )

    @property
    def warnings(self) -> tuple[ReleaseGateCheck, ...]:
        return tuple(
            check
            for check in self.checks
            if not check.passed and check.severity == GateSeverity.WARNING
        )


def evaluate_model_release(
    candidate: ModelReleaseCandidate,
    config: ReleaseGateConfig | None = None,
) -> ReleaseGateReport:
    config = config or ReleaseGateConfig()
    candidate.validate()

    checks = [
        _metric_check(
            name="accuracy",
            observed=candidate.accuracy,
            expected=config.min_accuracy,
            passed=candidate.accuracy >= config.min_accuracy,
            comparator=">=",
            message="Accuracy del test set insuficiente.",
        ),
        _metric_check(
            name="macro_f1",
            observed=candidate.macro_f1,
            expected=config.min_macro_f1,
            passed=candidate.macro_f1 >= config.min_macro_f1,
            comparator=">=",
            message="F1 macro insuficiente: posible clase minoritaria mal cubierta.",
        ),
        _metric_check(
            name="expected_calibration_error",
            observed=candidate.expected_calibration_error,
            expected=config.max_expected_calibration_error,
            passed=candidate.expected_calibration_error <= config.max_expected_calibration_error,
            comparator="<=",
            message="Calibración probabilística insuficiente para usar umbrales.",
        ),
        _metric_check(
            name="p95_latency_ms",
            observed=candidate.p95_latency_ms,
            expected=config.max_p95_latency_ms,
            passed=candidate.p95_latency_ms <= config.max_p95_latency_ms,
            comparator="<=",
            message="Latencia P95 demasiado alta para operación local.",
        ),
    ]

    if config.max_model_size_mb is not None:
        checks.append(
            _metric_check(
                name="model_size_mb",
                observed=candidate.model_size_mb,
                expected=config.max_model_size_mb,
                passed=(
                    candidate.model_size_mb is not None
                    and candidate.model_size_mb <= config.max_model_size_mb
                ),
                comparator="<=",
                message="Tamaño del modelo no apto para despliegue edge previsto.",
            )
        )

    checks.extend(
        [
            _required_check(
                name="test_set_locked",
                passed=candidate.test_set_locked,
                required=config.require_locked_test_set,
                message="El test set debe permanecer cerrado para validez científica.",
            ),
            _required_check(
                name="lineage_complete",
                passed=candidate.lineage_complete,
                required=config.require_lineage,
                message="Falta linaje completo de modelo, datos o configuración.",
            ),
            _required_check(
                name="privacy_review_passed",
                passed=candidate.privacy_review_passed,
                required=config.require_privacy_review,
                message="Falta revisión de privacidad antes de desplegar.",
            ),
            _required_check(
                name="training_serving_consistency_checked",
                passed=candidate.training_serving_consistency_checked,
                required=config.require_training_serving_consistency,
                message="No se ha verificado consistencia train-serving.",
            ),
            _required_check(
                name="rollback_plan_ready",
                passed=candidate.rollback_plan_ready,
                required=config.require_rollback_plan,
                message="Falta plan de rollback operativo.",
            ),
        ]
    )

    failed_blockers = [
        check for check in checks if not check.passed and check.severity == GateSeverity.BLOCKER
    ]
    failed_warnings = [
        check for check in checks if not check.passed and check.severity == GateSeverity.WARNING
    ]

    if failed_blockers:
        status = ReleaseGateStatus.BLOCKED
    elif failed_warnings:
        status = ReleaseGateStatus.APPROVED_WITH_WARNINGS
    else:
        status = ReleaseGateStatus.APPROVED

    return ReleaseGateReport(
        status=status,
        candidate=candidate,
        checks=tuple(checks),
    )


def _metric_check(
    *,
    name: str,
    observed: float | None,
    expected: float,
    passed: bool,
    comparator: str,
    message: str,
) -> ReleaseGateCheck:
    observed_text = "missing" if observed is None else f"{observed:.4f}"
    return ReleaseGateCheck(
        name=name,
        passed=passed,
        severity=GateSeverity.BLOCKER,
        observed=observed_text,
        expected=f"{comparator} {expected:.4f}",
        message="OK" if passed else message,
    )


def _required_check(
    *,
    name: str,
    passed: bool,
    required: bool,
    message: str,
) -> ReleaseGateCheck:
    if not required:
        return ReleaseGateCheck(
            name=name,
            passed=True,
            severity=GateSeverity.INFO,
            observed="not_required",
            expected="not_required",
            message="No requerido por configuración.",
        )

    return ReleaseGateCheck(
        name=name,
        passed=passed,
        severity=GateSeverity.BLOCKER,
        observed=str(passed).lower(),
        expected="true",
        message="OK" if passed else message,
    )
