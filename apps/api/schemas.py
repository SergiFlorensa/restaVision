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


class ObservationResponse(BaseModel):
    table: TableResponse
    session: SessionResponse | None
    events: list[EventResponse]
    prediction: PredictionResponse | None
