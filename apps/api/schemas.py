from __future__ import annotations

from datetime import date, datetime

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


class VoiceCallCreateRequest(BaseModel):
    caller_phone: str | None = None
    source_channel: str = Field(default="browser_simulator", min_length=1)


class VoiceReservationDraftResponse(BaseModel):
    party_size: int | None
    requested_date: date | None
    requested_date_text: str | None
    date_parser: str | None
    requested_time_text: str | None
    requested_at: datetime | None
    time_parser: str | None
    customer_name: str | None
    phone: str | None
    preferred_zone_id: str | None


class VoiceCallResponse(BaseModel):
    call_id: str
    started_at: datetime
    source_channel: str
    caller_phone: str | None
    status: str
    intent: str
    scenario_id: str | None
    reservation_draft: VoiceReservationDraftResponse
    reservation_id: str | None
    escalated_reason: str | None
    ended_at: datetime | None
    background_reply_status: str
    background_reply_text: str | None
    background_reply_reason: str | None


class VoiceTurnRequest(BaseModel):
    transcript: str = Field(min_length=1)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    observed_at: datetime | None = None


class VoiceAvailabilityResponse(BaseModel):
    available: bool
    table_id: str | None
    reason: str
    confidence: float
    pressure_mode: str
    pressure_reasons: list[str]


class VoiceReservationResponse(BaseModel):
    reservation_id: str
    customer_name: str
    phone: str
    party_size: int
    requested_time_text: str
    requested_at: datetime | None
    table_id: str | None
    status: str
    created_at: datetime
    source_call_id: str
    notes: str | None


class VoiceTurnResponse(BaseModel):
    call: VoiceCallResponse
    reply_text: str
    intent: str
    confidence: float
    action_name: str
    action_payload: dict[str, object]
    missing_fields: list[str]
    reservation: VoiceReservationResponse | None
    availability: VoiceAvailabilityResponse | None
    escalated: bool


class VoiceGatekeeperStatusResponse(BaseModel):
    mode: str
    score: int
    ready_tables: int
    total_tables: int
    waiting_queue_groups: int
    active_reservations: int
    reasons: list[str]


class VoiceMetricsResponse(BaseModel):
    total_calls: int
    open_calls: int
    confirmed_calls: int
    rejected_calls: int
    escalated_calls: int
    closed_calls: int
    total_reservations: int
    confirmed_reservations: int
    cancelled_reservations: int
    auto_resolution_rate: float
    escalation_rate: float
    average_turns_per_call: float
    gatekeeper: VoiceGatekeeperStatusResponse


class VoiceEvaluationClassMetricsResponse(BaseModel):
    precision: float
    recall: float
    f1: float
    support: int


class VoiceEvaluationCaseResponse(BaseModel):
    case_id: str
    transcript: str
    expected_intent: str
    actual_intent: str
    intent_ok: bool
    expected_action_name: str
    actual_action_name: str
    action_ok: bool
    expected_call_status: str | None
    actual_call_status: str
    call_status_ok: bool
    expected_scenario_id: str | None
    actual_scenario_id: str | None
    scenario_ok: bool
    expected_missing_fields: list[str]
    actual_missing_fields: list[str]
    missing_fields_ok: bool
    expected_slots: dict[str, object]
    actual_slots: dict[str, object]
    slot_matches: dict[str, bool]
    slots_ok: bool
    expected_escalated: bool | None
    actual_escalated: bool
    escalated_ok: bool
    reply_text: str


class VoiceEvaluationReportResponse(BaseModel):
    source: str
    generated_at: datetime
    sample_count: int
    intent_accuracy: float
    intent_macro_precision: float
    intent_macro_recall: float
    intent_macro_f1: float
    action_accuracy: float
    call_status_accuracy: float
    scenario_accuracy: float
    missing_fields_accuracy: float
    slot_exact_match_rate: float
    slot_field_accuracy: float
    escalation_accuracy: float
    failed_case_ids: list[str]
    per_intent: dict[str, VoiceEvaluationClassMetricsResponse]
    confusion_matrix: dict[str, dict[str, int]]
    cases: list[VoiceEvaluationCaseResponse]


class VoiceAudioQualityRequest(BaseModel):
    wav_path: str = Field(min_length=1)
    transcript: str | None = None
    reference_text: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class VoiceAudioBufferResponse(BaseModel):
    path: str
    sample_rate_hz: int
    channels: int
    sample_width_bytes: int
    frame_count: int
    duration_ms: int
    rms: float
    peak: float


class VoiceVadSegmentResponse(BaseModel):
    start_ms: int
    end_ms: int
    rms: float


class VoiceVadResponse(BaseModel):
    has_speech: bool
    speech_ratio: float
    speech_ms: int
    total_ms: int
    threshold: float
    rms: float
    peak: float
    segments: list[VoiceVadSegmentResponse]
    reason: str


class VoiceTranscriptQualityResponse(BaseModel):
    accepted: bool
    risk_level: str
    reasons: list[str]
    normalized_text: str
    token_count: int
    unique_token_ratio: float
    confidence: float | None
    wer: float | None


class VoiceAudioQualityResponse(BaseModel):
    audio: VoiceAudioBufferResponse
    vad: VoiceVadResponse
    transcript_quality: VoiceTranscriptQualityResponse | None
    accepted_for_agent: bool
    blocking_reasons: list[str]
    recommendation: str
