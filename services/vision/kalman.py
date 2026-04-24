from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from services.vision.geometry import BoundingBox


@dataclass(frozen=True, slots=True)
class Kalman2DConfig:
    process_noise: float = 1.0
    measurement_noise: float = 25.0
    initial_position_variance: float = 100.0
    initial_velocity_variance: float = 1000.0


@dataclass(frozen=True, slots=True)
class KalmanEstimate:
    x: float
    y: float
    vx: float
    vy: float
    position_uncertainty: float
    corrected_with_measurement: bool


class ConstantVelocityKalmanFilter:
    """Small constant-velocity Kalman filter for 2D detector coordinates."""

    def __init__(
        self,
        initial_position: tuple[float, float],
        config: Kalman2DConfig | None = None,
    ) -> None:
        self.config = config or Kalman2DConfig()
        self.state = np.array(
            [initial_position[0], initial_position[1], 0.0, 0.0],
            dtype=float,
        )
        self.covariance = np.diag(
            [
                self.config.initial_position_variance,
                self.config.initial_position_variance,
                self.config.initial_velocity_variance,
                self.config.initial_velocity_variance,
            ]
        )

    def step(
        self,
        measurement: tuple[float, float] | None,
        dt_seconds: float = 1.0,
    ) -> KalmanEstimate:
        if dt_seconds <= 0:
            raise ValueError("dt_seconds must be positive.")

        self._predict(dt_seconds=dt_seconds)
        corrected = measurement is not None
        if measurement is not None:
            self._update(measurement)

        return self.estimate(corrected_with_measurement=corrected)

    def estimate(self, corrected_with_measurement: bool = False) -> KalmanEstimate:
        return KalmanEstimate(
            x=float(self.state[0]),
            y=float(self.state[1]),
            vx=float(self.state[2]),
            vy=float(self.state[3]),
            position_uncertainty=float(np.trace(self.covariance[:2, :2])),
            corrected_with_measurement=corrected_with_measurement,
        )

    def _predict(self, dt_seconds: float) -> None:
        transition = np.array(
            [
                [1.0, 0.0, dt_seconds, 0.0],
                [0.0, 1.0, 0.0, dt_seconds],
                [0.0, 0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0, 1.0],
            ],
            dtype=float,
        )
        process_noise = np.eye(4) * self.config.process_noise
        self.state = transition @ self.state
        self.covariance = transition @ self.covariance @ transition.T + process_noise

    def _update(self, measurement: tuple[float, float]) -> None:
        observation = np.array([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]], dtype=float)
        measurement_noise = np.eye(2) * self.config.measurement_noise
        measured_position = np.array([measurement[0], measurement[1]], dtype=float)

        innovation = measured_position - observation @ self.state
        innovation_covariance = observation @ self.covariance @ observation.T + measurement_noise
        kalman_gain = self.covariance @ observation.T @ np.linalg.inv(innovation_covariance)

        self.state = self.state + kalman_gain @ innovation
        identity = np.eye(4)
        self.covariance = (identity - kalman_gain @ observation) @ self.covariance


@dataclass(slots=True)
class BoundingBoxKalmanSmoother:
    config: Kalman2DConfig | None = None
    size_smoothing: float = 0.35
    _filter: ConstantVelocityKalmanFilter | None = None
    _width: float | None = None
    _height: float | None = None

    def step(
        self,
        bbox: BoundingBox | None,
        dt_seconds: float = 1.0,
    ) -> BoundingBox | None:
        if bbox is None and self._filter is None:
            return None

        measurement = bbox.center if bbox is not None else None
        if self._filter is None:
            if measurement is None:
                return None
            self._filter = ConstantVelocityKalmanFilter(measurement, config=self.config)
            self._width = bbox.width if bbox is not None else None
            self._height = bbox.height if bbox is not None else None

        estimate = self._filter.step(measurement, dt_seconds=dt_seconds)
        if bbox is not None:
            self._width = self._smooth_size(previous=self._width, current=bbox.width)
            self._height = self._smooth_size(previous=self._height, current=bbox.height)

        if self._width is None or self._height is None:
            return None

        half_width = self._width / 2
        half_height = self._height / 2
        return BoundingBox(
            x_min=estimate.x - half_width,
            y_min=estimate.y - half_height,
            x_max=estimate.x + half_width,
            y_max=estimate.y + half_height,
        )

    def _smooth_size(self, previous: float | None, current: float) -> float:
        if previous is None:
            return current
        return (previous * (1.0 - self.size_smoothing)) + (current * self.size_smoothing)
