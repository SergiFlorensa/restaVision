from __future__ import annotations

from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException, Request, status
from services.alerts.anomaly import OperationalAlert
from services.events.models import (
    CameraStatus,
    DomainEvent,
    TableDefinition,
    TableObservation,
    TablePrediction,
    TableSession,
    TableSnapshot,
    ZoneDefinition,
)
from services.events.persistence import SqlAlchemyMVPRepository
from services.events.service import RestaurantMVPService
from services.events.settings import PersistenceSettings

from apps.api.schemas import (
    AlertResponse,
    CameraResponse,
    CameraUpsertRequest,
    EventResponse,
    HealthResponse,
    MarkReadyRequest,
    ObservationRequest,
    ObservationResponse,
    PredictionResponse,
    SessionResponse,
    TableResponse,
    TableUpsertRequest,
    ZoneResponse,
    ZoneUpsertRequest,
)


def create_app(mvp_service: RestaurantMVPService | None = None) -> FastAPI:
    app = FastAPI(
        title="RestaurIA MVP API",
        version="0.1.0",
        summary="Local MVP API for the RestaurIA operational copilot.",
    )
    app.state.mvp_service = mvp_service or build_mvp_service_from_environment()

    @app.get("/", tags=["root"])
    def root() -> dict[str, str]:
        return {
            "project": "RestaurIA",
            "status": "bootstrap_ready",
            "docs_hint": "Usa /docs para explorar la API del MVP.",
        }

    @app.get("/health", response_model=HealthResponse, tags=["system"])
    def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            environment="local",
            now=datetime.now(UTC),
        )

    @app.get("/api/v1/cameras", response_model=list[CameraResponse], tags=["catalog"])
    def list_cameras(request: Request) -> list[CameraResponse]:
        service = get_service(request)
        return [
            CameraResponse(camera_id=camera.camera_id, name=camera.name, status=camera.status)
            for camera in service.list_cameras()
        ]

    @app.post(
        "/api/v1/cameras",
        response_model=CameraResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["catalog"],
    )
    def upsert_camera(request: Request, payload: CameraUpsertRequest) -> CameraResponse:
        service = get_service(request)
        camera = service.upsert_camera(
            CameraStatus(
                camera_id=payload.camera_id,
                name=payload.name,
                status=payload.status,
            )
        )
        return CameraResponse(camera_id=camera.camera_id, name=camera.name, status=camera.status)

    @app.get("/api/v1/zones", response_model=list[ZoneResponse], tags=["catalog"])
    def list_zones(request: Request) -> list[ZoneResponse]:
        service = get_service(request)
        return [serialize_zone(zone) for zone in service.list_zones()]

    @app.post(
        "/api/v1/zones",
        response_model=ZoneResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["catalog"],
    )
    def upsert_zone(request: Request, payload: ZoneUpsertRequest) -> ZoneResponse:
        service = get_service(request)
        try:
            zone = service.upsert_zone(
                ZoneDefinition(
                    zone_id=payload.zone_id,
                    name=payload.name,
                    camera_id=payload.camera_id,
                    polygon_definition=payload.polygon_definition,
                )
            )
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return serialize_zone(zone)

    @app.get("/api/v1/tables", response_model=list[TableResponse], tags=["catalog"])
    def list_tables(request: Request) -> list[TableResponse]:
        service = get_service(request)
        return [serialize_table(table) for table in service.list_table_snapshots()]

    @app.post(
        "/api/v1/tables",
        response_model=TableResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["catalog"],
    )
    def upsert_table(request: Request, payload: TableUpsertRequest) -> TableResponse:
        service = get_service(request)
        try:
            table = service.upsert_table(
                TableDefinition(
                    table_id=payload.table_id,
                    name=payload.name,
                    capacity=payload.capacity,
                    zone_id=payload.zone_id,
                    active=payload.active,
                )
            )
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return serialize_table(table)

    @app.get("/api/v1/sessions", response_model=list[SessionResponse], tags=["state"])
    def list_sessions(request: Request) -> list[SessionResponse]:
        service = get_service(request)
        return [serialize_session(session) for session in service.list_sessions()]

    @app.get("/api/v1/events", response_model=list[EventResponse], tags=["state"])
    def list_events(request: Request, limit: int = 50) -> list[EventResponse]:
        service = get_service(request)
        return [serialize_event(event) for event in service.list_events(limit=limit)]

    @app.get("/api/v1/predictions", response_model=list[PredictionResponse], tags=["prediction"])
    def list_predictions(request: Request, limit: int = 50) -> list[PredictionResponse]:
        service = get_service(request)
        return [
            serialize_prediction(prediction) for prediction in service.list_predictions(limit=limit)
        ]

    @app.get("/api/v1/alerts", response_model=list[AlertResponse], tags=["alerts"])
    def list_alerts(request: Request, limit: int = 50) -> list[AlertResponse]:
        service = get_service(request)
        return [serialize_alert(alert) for alert in service.list_alerts(limit=limit)]

    @app.post(
        "/api/v1/observations",
        response_model=ObservationResponse,
        status_code=status.HTTP_202_ACCEPTED,
        tags=["ingestion"],
    )
    def process_observation(request: Request, payload: ObservationRequest) -> ObservationResponse:
        service = get_service(request)
        try:
            result = service.process_observation(
                TableObservation(
                    camera_id=payload.camera_id,
                    zone_id=payload.zone_id,
                    table_id=payload.table_id,
                    people_count=payload.people_count,
                    confidence=payload.confidence,
                    observed_at=payload.observed_at,
                )
            )
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

        return ObservationResponse(
            table=serialize_table(result.table),
            session=serialize_session(result.session) if result.session else None,
            events=[serialize_event(event) for event in result.events],
            prediction=serialize_prediction(result.prediction) if result.prediction else None,
        )

    @app.post("/api/v1/tables/{table_id}/ready", response_model=TableResponse, tags=["state"])
    def mark_table_ready(
        request: Request, table_id: str, payload: MarkReadyRequest
    ) -> TableResponse:
        service = get_service(request)
        try:
            snapshot = service.mark_table_ready(table_id=table_id, observed_at=payload.observed_at)
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        return serialize_table(snapshot)

    return app


def build_mvp_service_from_environment() -> RestaurantMVPService:
    settings = PersistenceSettings.from_environment()
    repository = None
    if settings.enable_postgres:
        if settings.database_url is None:
            raise RuntimeError("DATABASE_URL is required when PostgreSQL persistence is enabled.")
        repository = SqlAlchemyMVPRepository(settings.database_url)
    return RestaurantMVPService(repository=repository)


def get_service(request: Request) -> RestaurantMVPService:
    return request.app.state.mvp_service


def serialize_table(snapshot: TableSnapshot) -> TableResponse:
    return TableResponse(
        table_id=snapshot.table_id,
        name=snapshot.name,
        capacity=snapshot.capacity,
        zone_id=snapshot.zone_id,
        state=snapshot.state.value,
        people_count=snapshot.people_count,
        people_count_peak=snapshot.people_count_peak,
        active_session_id=snapshot.active_session_id,
        updated_at=snapshot.updated_at,
    )


def serialize_zone(zone: ZoneDefinition) -> ZoneResponse:
    return ZoneResponse(
        zone_id=zone.zone_id,
        name=zone.name,
        camera_id=zone.camera_id,
        polygon_definition=zone.polygon_definition,
    )


def serialize_session(session: TableSession) -> SessionResponse:
    return SessionResponse(
        session_id=session.session_id,
        table_id=session.table_id,
        start_ts=session.start_ts,
        end_ts=session.end_ts,
        people_count_initial=session.people_count_initial,
        people_count_peak=session.people_count_peak,
        final_status=session.final_status,
        duration_seconds=session.duration_seconds,
    )


def serialize_event(event: DomainEvent) -> EventResponse:
    return EventResponse(
        event_id=event.event_id,
        ts=event.ts,
        camera_id=event.camera_id,
        zone_id=event.zone_id,
        table_id=event.table_id,
        event_type=event.event_type.value,
        confidence=event.confidence,
        payload_json=event.payload_json,
    )


def serialize_prediction(prediction: TablePrediction) -> PredictionResponse:
    return PredictionResponse(
        prediction_id=prediction.prediction_id,
        ts=prediction.ts,
        table_id=prediction.table_id,
        model_name=prediction.model_name,
        prediction_type=prediction.prediction_type,
        value=prediction.value,
        lower_bound=prediction.lower_bound,
        upper_bound=prediction.upper_bound,
        confidence=prediction.confidence,
        explanation=prediction.explanation,
    )


def serialize_alert(alert: OperationalAlert) -> AlertResponse:
    return AlertResponse(
        alert_id=alert.alert_id,
        ts=alert.ts,
        table_id=alert.table_id,
        session_id=alert.session_id,
        alert_type=alert.alert_type.value,
        severity=alert.severity.value,
        message=alert.message,
        score=alert.score,
        evidence_json=alert.evidence_json,
    )


app = create_app()
