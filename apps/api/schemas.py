from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: str
    environment: str
    now: datetime


class DemoPersonDetectionStatusResponse(BaseModel):
    enabled: bool
    stream_url: str
    camera_source: str
    detector: str
    privacy_note: str


class CameraSnapshotResponse(BaseModel):
    saved: bool
    snapshot_path: str
    camera_source: str
    width: int
    height: int
    captured_at: datetime
    usage_note: str


class YoloPersonDetectionStatusResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    available: bool
    stream_url: str
    camera_source: str
    model_path: str
    detector: str
    confidence_threshold: float
    iou_threshold: float
    inference_stride: int
    privacy_note: str


class YoloRestaurantDetectionStatusResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    available: bool
    stream_url: str
    camera_source: str
    model_path: str
    detector: str
    confidence_threshold: float
    iou_threshold: float
    inference_stride: int
    allowed_labels: list[str]
    usage_note: str
    privacy_note: str


class YoloPoseDetectionStatusResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    available: bool
    stream_url: str
    camera_source: str
    model_path: str
    detector: str
    confidence_threshold: float
    keypoint_confidence_threshold: float
    image_size: int
    inference_stride: int
    usage_note: str
    privacy_note: str


class ServiceAlertResponse(BaseModel):
    alert_id: str
    ts: datetime
    alert_type: str
    severity: str
    message: str
    evidence: dict


class ServiceTimelineEventResponse(BaseModel):
    event_id: str
    ts: datetime
    event_type: str
    message: str
    payload: dict


class TableServiceAnalysisResponse(BaseModel):
    table_id: str
    updated_at: datetime
    state: str
    people_count: int
    object_counts: dict
    missing_items: dict
    service_flags: dict
    active_alerts: list[ServiceAlertResponse]
    timeline_events: list[ServiceTimelineEventResponse]
    seat_duration_seconds: int | None
    away_duration_seconds: int | None


class TableServiceMonitorStatusResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    available: bool
    stream_url: str
    camera_source: str
    table_id: str
    detector: str
    inference_stride: int
    privacy_note: str


class CameraResponse(BaseModel):
    camera_id: str
    name: str
    status: str


class CameraUpsertRequest(BaseModel):
    camera_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    status: str = Field(default="online", min_length=1)


class ZoneResponse(BaseModel):
    zone_id: str
    name: str
    camera_id: str
    polygon_definition: list[list[int]]


class ZoneUpsertRequest(BaseModel):
    zone_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    camera_id: str = Field(min_length=1)
    polygon_definition: list[list[int]]


class TableResponse(BaseModel):
    table_id: str
    name: str
    capacity: int
    zone_id: str
    state: str
    people_count: int
    people_count_peak: int
    active_session_id: str | None
    updated_at: datetime | None
    phase: str
    needs_attention: bool
    assigned_staff: str | None
    last_attention_at: datetime | None
    operational_note: str | None


class TableUpsertRequest(BaseModel):
    table_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    capacity: int = Field(gt=0)
    zone_id: str = Field(min_length=1)
    active: bool = True


class SessionResponse(BaseModel):
    session_id: str
    table_id: str
    start_ts: datetime
    end_ts: datetime | None
    people_count_initial: int
    people_count_peak: int
    final_status: str | None
    duration_seconds: int | None


class EventResponse(BaseModel):
    event_id: str
    ts: datetime
    camera_id: str
    zone_id: str
    table_id: str | None
    event_type: str
    confidence: float
    payload_json: dict[str, object]


class PredictionResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    prediction_id: str
    ts: datetime
    table_id: str
    model_name: str
    prediction_type: str
    value: float
    lower_bound: float
    upper_bound: float
    confidence: float
    explanation: str


class AlertResponse(BaseModel):
    alert_id: str
    ts: datetime
    table_id: str
    session_id: str | None
    alert_type: str
    severity: str
    message: str
    score: float
    evidence_json: dict[str, object]


class ObservationRequest(BaseModel):
    camera_id: str
    zone_id: str
    table_id: str
    people_count: int = Field(ge=0)
    confidence: float = Field(default=0.95, ge=0.0, le=1.0)
    observed_at: datetime


class MarkReadyRequest(BaseModel):
    observed_at: datetime | None = None


class TableRuntimeUpdateRequest(BaseModel):
    state: str | None = None
    phase: str | None = None
    people_count: int | None = Field(default=None, ge=0)
    needs_attention: bool | None = None
    assigned_staff: str | None = None
    last_attention_at: datetime | None = None
    operational_note: str | None = None


class OperationalActionRequest(BaseModel):
    action_type: str = Field(min_length=1)
    table_id: str | None = None
    queue_group_id: str | None = None
    assigned_staff: str | None = None
    target_channel: str = Field(default="shared_panel", min_length=1)
    message: str | None = None
    payload: dict[str, object] = Field(default_factory=dict)


class OperationalActionResponse(BaseModel):
    action_id: str
    ts: datetime
    action_type: str
    table_id: str | None
    queue_group_id: str | None
    assigned_staff: str | None
    target_channel: str
    message: str | None
    payload_json: dict[str, object]


class ObservationResponse(BaseModel):
    table: TableResponse
    session: SessionResponse | None
    events: list[EventResponse]
    prediction: PredictionResponse | None


class QueueGroupCreateRequest(BaseModel):
    party_size: int = Field(gt=0)
    arrival_ts: datetime | None = None
    preferred_zone_id: str | None = None


class QueueGroupResponse(BaseModel):
    queue_group_id: str
    party_size: int
    arrival_ts: datetime
    status: str
    promised_wait_min: int | None
    promised_wait_max: int | None
    promised_at: datetime | None
    preferred_zone_id: str | None


class DecisionRecommendationResponse(BaseModel):
    decision_id: str
    mode: str
    priority: str
    question: str
    answer: str
    table_id: str | None
    queue_group_id: str | None
    eta_minutes: float | None
    confidence: float
    impact: str
    reason: list[str]
    expires_in_seconds: int
    metadata: dict[str, object]


class DecisionFeedbackRequest(BaseModel):
    feedback_type: str = Field(default="manual", min_length=1)
    accepted: bool
    useful: bool | None = None
    outcome: dict[str, object] = Field(default_factory=dict)
    comment: str | None = None


class DecisionFeedbackResponse(BaseModel):
    feedback_id: str
    decision_id: str
    ts: datetime
    feedback_type: str
    accepted: bool
    useful: bool | None
    outcome: dict[str, object]
    comment: str | None
