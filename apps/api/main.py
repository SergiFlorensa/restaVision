from __future__ import annotations

import platform
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import sleep
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
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
from services.vision.detection_policy import DetectionPolicy, TemporalEvidenceAccumulator
from services.vision.person_demo import DemoPersonDetectionConfig, OpenCVPersonDemoDetector
from services.vision.realtime import FrameSkippingConfig, FrameSkippingPolicy
from services.vision.table_roi import TableRoi, TableRoiAnalyzer, parse_table_roi
from services.vision.table_service_monitor import (
    SERVICE_RELEVANT_LABELS,
    ServiceAlert,
    ServiceTimelineEvent,
    TableServiceAnalysis,
    TableServiceMonitor,
    TableServiceMonitorConfig,
)
from services.vision.yolo_detector import (
    YOLO_PERSON_LABELS,
    YOLO_RESTAURANT_LABELS,
    UltralyticsYoloDetector,
    YoloDetectorConfig,
    count_detections_by_label,
    draw_detection_summary,
    draw_yolo_detections,
    encode_jpeg,
    is_ultralytics_available,
)

from apps.api.schemas import (
    AlertResponse,
    CameraResponse,
    CameraSnapshotResponse,
    CameraUpsertRequest,
    DemoPersonDetectionStatusResponse,
    EventResponse,
    HealthResponse,
    MarkReadyRequest,
    ObservationRequest,
    ObservationResponse,
    PredictionResponse,
    ServiceAlertResponse,
    ServiceTimelineEventResponse,
    SessionResponse,
    TableResponse,
    TableServiceAnalysisResponse,
    TableServiceMonitorStatusResponse,
    TableUpsertRequest,
    YoloPersonDetectionStatusResponse,
    YoloRestaurantDetectionStatusResponse,
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
    app.state.table_service_analyses = {}

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

    @app.get(
        "/api/v1/demo/person-detection/status",
        response_model=DemoPersonDetectionStatusResponse,
        tags=["vision-demo"],
    )
    def person_detection_status(
        source: int | str = Query(default=0),
    ) -> DemoPersonDetectionStatusResponse:
        return DemoPersonDetectionStatusResponse(
            enabled=True,
            stream_url=f"/api/v1/demo/person-detection/stream?source={source}",
            camera_source=str(source),
            detector="OpenCV Haar face cascade + HOG person fallback",
            privacy_note="Detecta presencia humana para demo local; no identifica personas.",
        )

    @app.get("/api/v1/demo/person-detection/stream", tags=["vision-demo"])
    def person_detection_stream(
        source: int | str = Query(default=0),
        width: int = Query(default=640, ge=160, le=1920),
        height: int = Query(default=480, ge=120, le=1080),
    ) -> StreamingResponse:
        config = DemoPersonDetectionConfig(source=source, width=width, height=height)
        return StreamingResponse(
            _iter_person_detection_mjpeg(config),
            media_type="multipart/x-mixed-replace; boundary=frame",
        )

    @app.post(
        "/api/v1/demo/camera-snapshot",
        response_model=CameraSnapshotResponse,
        tags=["vision-demo"],
    )
    def create_camera_snapshot(
        source: int | str = Query(default=0),
        width: int = Query(default=640, ge=160, le=1920),
        height: int = Query(default=480, ge=120, le=1080),
        output_dir: str = Query(default="data/calibration/snapshots"),
    ) -> CameraSnapshotResponse:
        captured_at = datetime.now(UTC)
        normalized_source = _normalize_video_source(source)
        try:
            snapshot = _capture_camera_snapshot(
                source=normalized_source,
                width=width,
                height=height,
                output_dir=Path(output_dir),
                captured_at=captured_at,
            )
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc

        return CameraSnapshotResponse(
            saved=True,
            snapshot_path=str(snapshot.path),
            camera_source=str(normalized_source),
            width=snapshot.width,
            height=snapshot.height,
            captured_at=captured_at,
            usage_note=(
                "Snapshot local para marcar ROI de mesa/zona. No versionar imágenes reales."
            ),
        )

    @app.get(
        "/api/v1/demo/yolo-person/status",
        response_model=YoloPersonDetectionStatusResponse,
        tags=["vision-demo"],
    )
    def yolo_person_detection_status(
        source: int | str = Query(default=0),
        model: str = Query(default="yolo11n.pt"),
        confidence: float = Query(default=0.35, ge=0.0, le=1.0),
        iou: float = Query(default=0.5, ge=0.0, le=1.0),
        inference_stride: int = Query(default=3, ge=1, le=30),
    ) -> YoloPersonDetectionStatusResponse:
        return YoloPersonDetectionStatusResponse(
            available=is_ultralytics_available(),
            stream_url=(
                "/api/v1/demo/yolo-person/stream"
                f"?source={source}&model={model}&confidence={confidence}&iou={iou}"
                f"&inference_stride={inference_stride}"
            ),
            camera_source=str(source),
            model_path=model,
            detector="Ultralytics YOLO filtered to class 'person'",
            confidence_threshold=confidence,
            iou_threshold=iou,
            inference_stride=inference_stride,
            privacy_note="Detecta personas para demo local; no identifica rostros ni nombres.",
        )

    @app.get(
        "/api/v1/demo/yolo-restaurant/status",
        response_model=YoloRestaurantDetectionStatusResponse,
        tags=["vision-demo"],
    )
    def yolo_restaurant_detection_status(
        source: int | str = Query(default=0),
        model: str = Query(default="yolo11n.pt"),
        confidence: float = Query(default=0.25, ge=0.0, le=1.0),
        iou: float = Query(default=0.5, ge=0.0, le=1.0),
        inference_stride: int = Query(default=3, ge=1, le=30),
        labels: str | None = Query(default=None),
    ) -> YoloRestaurantDetectionStatusResponse:
        allowed_labels = _parse_yolo_labels(labels, YOLO_RESTAURANT_LABELS)
        return YoloRestaurantDetectionStatusResponse(
            available=is_ultralytics_available(),
            stream_url=(
                "/api/v1/demo/yolo-restaurant/stream"
                f"?source={source}&model={model}&confidence={confidence}&iou={iou}"
                f"&inference_stride={inference_stride}"
            ),
            camera_source=str(source),
            model_path=model,
            detector="Ultralytics YOLO filtered to restaurant-relevant COCO classes",
            confidence_threshold=confidence,
            iou_threshold=iou,
            inference_stride=inference_stride,
            allowed_labels=list(allowed_labels),
            usage_note=(
                "Modo de exploracion: sirve para probar mesa/sillas/objetos con COCO. "
                "La ocupacion real debe decidirse despues con ROI y reglas temporales."
            ),
            privacy_note=(
                "Detecta objetos/personas para demo local; no identifica rostros ni nombres."
            ),
        )

    @app.get("/api/v1/demo/yolo-person/stream", tags=["vision-demo"])
    def yolo_person_detection_stream(
        source: int | str = Query(default=0),
        model: str = Query(default="yolo11n.pt"),
        confidence: float = Query(default=0.35, ge=0.0, le=1.0),
        iou: float = Query(default=0.5, ge=0.0, le=1.0),
        width: int = Query(default=640, ge=160, le=1920),
        height: int = Query(default=480, ge=120, le=1080),
        image_size: int = Query(default=320, ge=160, le=1280),
        max_detections: int = Query(default=20, ge=1, le=100),
        inference_stride: int = Query(default=3, ge=1, le=30),
    ) -> StreamingResponse:
        config = YoloDetectorConfig(
            model_path=model,
            confidence_threshold=confidence,
            iou_threshold=iou,
            image_size=image_size,
            max_detections=max_detections,
            allowed_labels=YOLO_PERSON_LABELS,
        )
        return StreamingResponse(
            _iter_yolo_detection_mjpeg(
                source=source,
                width=width,
                height=height,
                detector_config=config,
                summary_title=None,
                inference_stride=inference_stride,
            ),
            media_type="multipart/x-mixed-replace; boundary=frame",
        )

    @app.get("/api/v1/demo/yolo-restaurant/stream", tags=["vision-demo"])
    def yolo_restaurant_detection_stream(
        source: int | str = Query(default=0),
        model: str = Query(default="yolo11n.pt"),
        confidence: float = Query(default=0.25, ge=0.0, le=1.0),
        iou: float = Query(default=0.5, ge=0.0, le=1.0),
        labels: str | None = Query(default=None),
        width: int = Query(default=640, ge=160, le=1920),
        height: int = Query(default=480, ge=120, le=1080),
        image_size: int = Query(default=320, ge=160, le=1280),
        max_detections: int = Query(default=30, ge=1, le=100),
        min_box_area_ratio: float = Query(default=0.0005, ge=0.0, le=1.0),
        inference_stride: int = Query(default=3, ge=1, le=30),
    ) -> StreamingResponse:
        allowed_labels = _parse_yolo_labels(labels, YOLO_RESTAURANT_LABELS)
        config = YoloDetectorConfig(
            model_path=model,
            confidence_threshold=confidence,
            iou_threshold=iou,
            image_size=image_size,
            max_detections=max_detections,
            min_box_area_ratio=min_box_area_ratio,
            allowed_labels=allowed_labels,
        )
        return StreamingResponse(
            _iter_yolo_detection_mjpeg(
                source=source,
                width=width,
                height=height,
                detector_config=config,
                summary_title="YOLO restaurante",
                inference_stride=inference_stride,
            ),
            media_type="multipart/x-mixed-replace; boundary=frame",
        )

    @app.get(
        "/api/v1/demo/table-service/status",
        response_model=TableServiceMonitorStatusResponse,
        tags=["vision-demo"],
    )
    def table_service_monitor_status(
        source: int | str = Query(default=0),
        table_id: str = Query(default="table_01"),
        model: str = Query(default="yolo11n.pt"),
        confidence: float = Query(default=0.25, ge=0.0, le=1.0),
        iou: float = Query(default=0.5, ge=0.0, le=1.0),
        inference_stride: int = Query(default=3, ge=1, le=30),
    ) -> TableServiceMonitorStatusResponse:
        return TableServiceMonitorStatusResponse(
            available=is_ultralytics_available(),
            stream_url=(
                "/api/v1/demo/table-service/stream"
                f"?source={source}&table_id={table_id}&model={model}"
                f"&confidence={confidence}&iou={iou}&inference_stride={inference_stride}"
            ),
            camera_source=str(source),
            table_id=table_id,
            detector="Ultralytics YOLO con análisis de servicio de mesa",
            inference_stride=inference_stride,
            privacy_note=(
                "Detecta cubiertos, platos, comida, personas y gestos de atención. "
                "No identifica rostros ni nombres. Análisis local de servicio."
            ),
        )

    @app.get(
        "/api/v1/demo/table-service/stream",
        tags=["vision-demo"],
    )
    def table_service_detection_stream(
        source: int | str = Query(default=0),
        table_id: str = Query(default="table_01"),
        model: str = Query(default="yolo11n.pt"),
        confidence: float = Query(default=0.25, ge=0.0, le=1.0),
        iou: float = Query(default=0.5, ge=0.0, le=1.0),
        width: int = Query(default=640, ge=160, le=1920),
        height: int = Query(default=480, ge=120, le=1080),
        image_size: int = Query(default=320, ge=160, le=1280),
        max_detections: int = Query(default=30, ge=1, le=100),
        inference_stride: int = Query(default=3, ge=1, le=30),
        min_box_area_ratio: float = Query(default=0.0002, ge=0.0, le=1.0),
        roi: str | None = Query(
            default=None,
            description="ROI opcional de mesa en formato x_min,y_min,x_max,y_max.",
        ),
        roi_margin: float = Query(default=0.05, ge=0.0, le=1.0),
        text_overlay: bool = Query(
            default=False,
            description=(
                "Muestra paneles de texto encima del vídeo. Por defecto se delega al dashboard."
            ),
        ),
    ) -> StreamingResponse:
        try:
            table_roi = parse_table_roi(roi, table_id=table_id, margin_ratio=roi_margin)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        config = YoloDetectorConfig(
            model_path=model,
            confidence_threshold=confidence,
            iou_threshold=iou,
            image_size=image_size,
            max_detections=max_detections,
            min_box_area_ratio=min_box_area_ratio,
            allowed_labels=SERVICE_RELEVANT_LABELS,
        )
        return StreamingResponse(
            _iter_table_service_analysis_mjpeg(
                source=source,
                table_id=table_id,
                width=width,
                height=height,
                detector_config=config,
                inference_stride=inference_stride,
                analysis_store=app.state.table_service_analyses,
                table_roi=table_roi,
                text_overlay=text_overlay,
            ),
            media_type="multipart/x-mixed-replace; boundary=frame",
        )

    @app.get(
        "/api/v1/demo/table-service/analysis",
        response_model=TableServiceAnalysisResponse,
        tags=["vision-demo"],
    )
    def get_table_service_analysis(
        request: Request,
        table_id: str = Query(default="table_01"),
    ) -> TableServiceAnalysisResponse:
        analyses: dict[str, TableServiceAnalysis] = request.app.state.table_service_analyses
        analysis = analyses.get(table_id)
        if analysis is None:
            analysis = TableServiceMonitor(TableServiceMonitorConfig(table_id=table_id)).current()
        return serialize_table_service_analysis(analysis)

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

    @app.post(
        "/api/v1/demo/table-service/analyze",
        response_model=TableServiceAnalysisResponse,
        tags=["vision-demo"],
    )
    def analyze_table_service_snapshot(
        source: int | str = Query(default=0),
        table_id: str = Query(default="table_01"),
        model: str = Query(default="yolo11n.pt"),
        confidence: float = Query(default=0.25, ge=0.0, le=1.0),
        iou: float = Query(default=0.5, ge=0.0, le=1.0),
        width: int = Query(default=640, ge=160, le=1920),
        height: int = Query(default=480, ge=120, le=1080),
        image_size: int = Query(default=320, ge=160, le=1280),
        max_detections: int = Query(default=30, ge=1, le=100),
        min_box_area_ratio: float = Query(default=0.0002, ge=0.0, le=1.0),
        roi: str | None = Query(
            default=None,
            description="ROI opcional de mesa en formato x_min,y_min,x_max,y_max.",
        ),
        roi_margin: float = Query(default=0.05, ge=0.0, le=1.0),
    ) -> TableServiceAnalysisResponse:
        """Captura un frame y devuelve el análisis actual de servicio de mesa."""
        try:
            table_roi = parse_table_roi(roi, table_id=table_id, margin_ratio=roi_margin)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        cv2 = _load_cv2_for_demo_stream()
        config = YoloDetectorConfig(
            model_path=model,
            confidence_threshold=confidence,
            iou_threshold=iou,
            image_size=image_size,
            max_detections=max_detections,
            min_box_area_ratio=min_box_area_ratio,
            allowed_labels=SERVICE_RELEVANT_LABELS,
        )
        detector = UltralyticsYoloDetector(config)
        table_detector = TableRoiAnalyzer(detector)
        detection_policy = DetectionPolicy()
        monitor = TableServiceMonitor(TableServiceMonitorConfig(table_id=table_id))

        normalized_source = _normalize_video_source(source)
        capture = _open_video_capture(cv2, normalized_source)
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

        try:
            if not capture.isOpened():
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Could not open video source: {source!r}",
                )

            ok, frame = capture.read()
            if not ok or frame is None:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Could not read frame from video source: {source!r}",
                )

            detections = table_detector.detect(frame, table_roi)
            detections = detection_policy.filter_detections(
                detections,
                frame_width=int(frame.shape[1]),
                frame_height=int(frame.shape[0]),
            )
            analysis = monitor.process(detections)
            app.state.table_service_analyses[table_id] = analysis
            return serialize_table_service_analysis(analysis)
        finally:
            capture.release()

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


def serialize_table_service_analysis(
    analysis: TableServiceAnalysis,
) -> TableServiceAnalysisResponse:
    return TableServiceAnalysisResponse(
        table_id=analysis.table_id,
        updated_at=analysis.updated_at,
        state=analysis.state,
        people_count=analysis.people_count,
        object_counts=analysis.object_counts,
        missing_items=analysis.missing_items,
        service_flags=analysis.service_flags,
        active_alerts=[serialize_service_alert(alert) for alert in analysis.active_alerts],
        timeline_events=[serialize_service_event(event) for event in analysis.timeline_events],
        seat_duration_seconds=analysis.seat_duration_seconds,
        away_duration_seconds=analysis.away_duration_seconds,
    )


def serialize_service_alert(alert: ServiceAlert) -> ServiceAlertResponse:
    return ServiceAlertResponse(
        alert_id=alert.alert_id,
        ts=alert.ts,
        alert_type=alert.alert_type,
        severity=alert.severity,
        message=alert.message,
        evidence=alert.evidence,
    )


def serialize_service_event(event: ServiceTimelineEvent) -> ServiceTimelineEventResponse:
    return ServiceTimelineEventResponse(
        event_id=event.event_id,
        ts=event.ts,
        event_type=event.event_type,
        message=event.message,
        payload=event.payload,
    )


@dataclass(frozen=True, slots=True)
class CameraSnapshot:
    path: Path
    width: int
    height: int


def _iter_person_detection_mjpeg(config: DemoPersonDetectionConfig) -> Any:
    cv2 = _load_cv2_for_demo_stream()
    detector = OpenCVPersonDemoDetector(config)
    capture = _open_video_capture(cv2, config.source)
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, config.width)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, config.height)
    if not capture.isOpened():
        capture.release()
        raise RuntimeError(f"Could not open video source: {config.source!r}")

    try:
        while True:
            ok, frame = capture.read()
            if not ok or frame is None:
                sleep(0.05)
                continue

            detections = detector.detect(frame)
            annotated = detector.draw(frame, detections)
            frame_bytes = detector.encode_jpeg(annotated)
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n"
                b"Cache-Control: no-store\r\n\r\n" + frame_bytes + b"\r\n"
            )
    finally:
        capture.release()


def _capture_camera_snapshot(
    source: int | str,
    width: int,
    height: int,
    output_dir: Path,
    captured_at: datetime,
) -> CameraSnapshot:
    cv2 = _load_cv2_for_demo_stream()
    capture = _open_video_capture(cv2, source)
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    if not capture.isOpened():
        capture.release()
        raise RuntimeError(f"Could not open video source: {source!r}")

    try:
        ok, frame = capture.read()
        if not ok or frame is None:
            raise RuntimeError(f"Could not read frame from video source: {source!r}")

        output_dir.mkdir(parents=True, exist_ok=True)
        path = _build_snapshot_path(output_dir, source, captured_at)
        if not cv2.imwrite(str(path), frame):
            raise RuntimeError(f"Could not write snapshot to: {path}")
        return CameraSnapshot(
            path=path,
            width=int(frame.shape[1]),
            height=int(frame.shape[0]),
        )
    finally:
        capture.release()


def _iter_yolo_detection_mjpeg(
    source: int | str,
    width: int,
    height: int,
    detector_config: YoloDetectorConfig,
    summary_title: str | None,
    inference_stride: int,
) -> Any:
    cv2 = _load_cv2_for_demo_stream()
    detector: UltralyticsYoloDetector | None = None
    frame_index = 0
    last_detections = []
    policy = FrameSkippingPolicy(
        FrameSkippingConfig(base_interval=inference_stride, hot_interval=inference_stride)
    )
    capture = _open_video_capture(cv2, source)
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    if not capture.isOpened():
        capture.release()
        raise RuntimeError(f"Could not open video source: {source!r}")

    try:
        while True:
            ok, frame = capture.read()
            if not ok or frame is None:
                sleep(0.05)
                continue

            if detector is None:
                warmup_frame = frame.copy()
                cv2.putText(
                    warmup_frame,
                    "Inicializando YOLO...",
                    (20, 36),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.85,
                    (245, 245, 245),
                    2,
                    cv2.LINE_AA,
                )
                yield _mjpeg_frame(encode_jpeg(warmup_frame))
                detector = UltralyticsYoloDetector(detector_config)

            if policy.should_process(frame_index):
                last_detections = detector.detect(frame)
            frame_index += 1

            annotated = draw_yolo_detections(frame, last_detections)
            if summary_title:
                annotated = draw_detection_summary(annotated, last_detections, summary_title)
            frame_bytes = encode_jpeg(annotated)
            yield _mjpeg_frame(frame_bytes)
    finally:
        capture.release()


def _iter_table_service_analysis_mjpeg(
    source: int | str,
    table_id: str,
    width: int,
    height: int,
    detector_config: YoloDetectorConfig,
    inference_stride: int,
    analysis_store: dict[str, TableServiceAnalysis],
    table_roi: TableRoi | None,
    text_overlay: bool,
) -> Any:
    cv2 = _load_cv2_for_demo_stream()
    detector: UltralyticsYoloDetector | None = None
    table_detector: TableRoiAnalyzer | None = None
    detection_policy = DetectionPolicy()
    evidence = TemporalEvidenceAccumulator(detection_policy)
    monitor = TableServiceMonitor(TableServiceMonitorConfig(table_id=table_id))
    frame_index = 0
    last_detections = []
    last_stable_counts: dict[str, int] = {}
    policy = FrameSkippingPolicy(
        FrameSkippingConfig(base_interval=inference_stride, hot_interval=inference_stride)
    )
    capture = _open_video_capture(cv2, source)
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    if not capture.isOpened():
        capture.release()
        raise RuntimeError(f"Could not open video source: {source!r}")

    try:
        while True:
            ok, frame = capture.read()
            if not ok or frame is None:
                sleep(0.05)
                continue

            if detector is None:
                warmup_frame = frame.copy()
                cv2.putText(
                    warmup_frame,
                    f"Inicializando análisis de mesa {table_id}...",
                    (20, 36),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (245, 245, 245),
                    2,
                    cv2.LINE_AA,
                )
                yield _mjpeg_frame(encode_jpeg(warmup_frame))
                detector = UltralyticsYoloDetector(detector_config)
                table_detector = TableRoiAnalyzer(detector)

            if policy.should_process(frame_index) and table_detector is not None:
                detections = table_detector.detect(frame, table_roi)
                last_detections = detection_policy.filter_detections(
                    detections,
                    frame_width=int(frame.shape[1]),
                    frame_height=int(frame.shape[0]),
                )
                evidence_snapshot = evidence.update(last_detections)
                last_stable_counts = evidence_snapshot.stable_counts

            analysis = monitor.process(
                last_detections,
                stable_counts=last_stable_counts,
            )
            analysis_store[table_id] = analysis
            frame_index += 1

            annotated = draw_yolo_detections(frame, last_detections)
            if table_roi is not None:
                annotated = _draw_table_roi(annotated, table_roi, cv2)
            if text_overlay:
                annotated = _draw_table_service_analysis(annotated, last_detections, analysis, cv2)
            frame_bytes = encode_jpeg(annotated)
            yield _mjpeg_frame(frame_bytes)
    finally:
        capture.release()


def _draw_table_service_analysis(
    frame: Any,
    detections: list[Any],
    analysis: TableServiceAnalysis,
    cv2: Any,
) -> Any:
    """Dibuja paneles acotados para que el texto no salga del frame."""
    output = frame.copy()
    height, width = output.shape[:2]
    left_width = min(280, max(210, width // 3))
    right_width = min(410, max(250, width // 2))
    bottom_width = min(width - 24, 720)

    output = _draw_bounded_panel(
        output,
        title="DETECCION",
        lines=_detection_lines(detections),
        x=12,
        y=12,
        width=left_width,
        max_height=max(118, height // 3),
        cv2=cv2,
    )
    output = _draw_bounded_panel(
        output,
        title="MESA Y SERVICIO",
        lines=_service_analysis_lines(analysis),
        x=max(12, width - right_width - 12),
        y=12,
        width=right_width,
        max_height=max(170, height // 2),
        cv2=cv2,
    )
    output = _draw_bounded_panel(
        output,
        title="REGISTRO RELACIONADO",
        lines=_timeline_lines(analysis),
        x=12,
        y=max(12, height - 182),
        width=bottom_width,
        max_height=170,
        cv2=cv2,
    )
    return output


def _draw_table_roi(frame: Any, table_roi: TableRoi, cv2: Any) -> Any:
    output = frame.copy()
    height, width = output.shape[:2]
    x1 = int(round(max(0, min(table_roi.bbox.x_min, width))))
    y1 = int(round(max(0, min(table_roi.bbox.y_min, height))))
    x2 = int(round(max(0, min(table_roi.bbox.x_max, width))))
    y2 = int(round(max(0, min(table_roi.bbox.y_max, height))))
    if x2 <= x1 or y2 <= y1:
        return output
    cv2.rectangle(output, (x1, y1), (x2, y2), (212, 170, 94), 2)
    cv2.putText(
        output,
        f"ROI {table_roi.table_id}",
        (x1 + 6, max(20, y1 - 8)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (245, 245, 245),
        2,
        cv2.LINE_AA,
    )
    return output


def _draw_bounded_panel(
    frame: Any,
    title: str,
    lines: list[str],
    x: int,
    y: int,
    width: int,
    max_height: int,
    cv2: Any,
) -> Any:
    output = frame.copy()
    frame_height, frame_width = output.shape[:2]
    x = max(6, min(x, frame_width - 60))
    y = max(6, min(y, frame_height - 60))
    width = max(160, min(width, frame_width - x - 6))
    max_height = max(80, min(max_height, frame_height - y - 6))

    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.47
    line_height = 20
    wrapped_lines: list[str] = []
    for line in lines:
        wrapped_lines.extend(_wrap_overlay_text(str(line), width - 24, font, font_scale, 1, cv2))

    max_lines = max(1, (max_height - 44) // line_height)
    visible_lines = wrapped_lines[:max_lines]
    panel_height = min(max_height, 42 + len(visible_lines) * line_height)
    x2 = min(frame_width - 6, x + width)
    y2 = min(frame_height - 6, y + panel_height)

    overlay = output.copy()
    cv2.rectangle(overlay, (x, y), (x2, y2), (18, 18, 20), -1)
    output = cv2.addWeighted(overlay, 0.76, output, 0.24, 0)
    cv2.rectangle(output, (x, y), (x2, y2), (78, 86, 78), 1)

    cv2.putText(output, title, (x + 12, y + 24), font, 0.52, (245, 245, 245), 2, cv2.LINE_AA)
    for index, line in enumerate(visible_lines):
        text_y = y + 48 + index * line_height
        color = (205, 226, 190)
        if "ALERTA" in line or "Falta" in line:
            color = (80, 120, 245)
        cv2.putText(output, line, (x + 12, text_y), font, font_scale, color, 1, cv2.LINE_AA)
    return output


def _wrap_overlay_text(
    text: str,
    max_width: int,
    font: Any,
    font_scale: float,
    thickness: int,
    cv2: Any,
) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        text_width = cv2.getTextSize(candidate, font, font_scale, thickness)[0][0]
        if text_width <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _detection_lines(detections: list[Any]) -> list[str]:
    counts = count_detections_by_label(detections)
    if not counts:
        return ["Sin objetos detectados todavia"]
    return [f"{label}: {count}" for label, count in counts.items()]


def _service_analysis_lines(analysis: TableServiceAnalysis) -> list[str]:
    lines = [
        f"Mesa: {analysis.table_id} | {analysis.state}",
        f"Personas: {analysis.people_count}",
        f"Tiempo sentado: {_format_seconds(analysis.seat_duration_seconds or 0)}",
    ]
    if analysis.away_duration_seconds is not None:
        lines.append(f"Tiempo ausente: {_format_seconds(analysis.away_duration_seconds)}")
    if analysis.missing_items:
        missing_text = ", ".join(
            f"{label}:{amount}" for label, amount in analysis.missing_items.items()
        )
        lines.append(f"Falta: {missing_text}")
    else:
        lines.append("Servicio: sin faltas criticas")
    if analysis.service_flags.get("food_served"):
        lines.append("Comida detectada en mesa")
    if analysis.service_flags.get("customer_needs_attention"):
        lines.append("ALERTA: posible llamada cliente")
    return lines


def _timeline_lines(analysis: TableServiceAnalysis) -> list[str]:
    if not analysis.timeline_events:
        return ["Sin eventos registrados en esta mesa"]
    lines: list[str] = []
    for event in analysis.timeline_events[:5]:
        ts = event.ts.strftime("%H:%M:%S")
        lines.append(f"{ts} | {analysis.table_id} | {event.event_type} | {event.message}")
    return lines


def _format_seconds(seconds: int) -> str:
    minutes, remaining_seconds = divmod(max(0, seconds), 60)
    return f"{minutes:02d}:{remaining_seconds:02d}"


def _open_video_capture(cv2: Any, source: int | str) -> Any:
    source = _normalize_video_source(source)
    if platform.system() == "Windows" and isinstance(source, int):
        return cv2.VideoCapture(source, cv2.CAP_DSHOW)
    return cv2.VideoCapture(source)


def _normalize_video_source(source: int | str) -> int | str:
    if isinstance(source, str) and source.isdigit():
        return int(source)
    return source


def _parse_yolo_labels(labels: str | None, default: tuple[str, ...]) -> tuple[str, ...]:
    if labels is None:
        return default
    parsed = tuple(label.strip() for label in labels.split(",") if label.strip())
    return parsed or default


def _build_snapshot_path(output_dir: Path, source: int | str, captured_at: datetime) -> Path:
    timestamp = captured_at.strftime("%Y%m%d_%H%M%S")
    source_slug = _safe_source_slug(source)
    return output_dir / f"snapshot_{source_slug}_{timestamp}.jpg"


def _safe_source_slug(source: int | str) -> str:
    raw = str(source)
    sanitized = "".join(character if character.isalnum() else "_" for character in raw)
    return sanitized.strip("_") or "camera"


def _mjpeg_frame(frame_bytes: bytes) -> bytes:
    return (
        b"--frame\r\n"
        b"Content-Type: image/jpeg\r\n"
        b"Cache-Control: no-store\r\n\r\n" + frame_bytes + b"\r\n"
    )


def _load_cv2_for_demo_stream() -> Any:
    try:
        import cv2
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "OpenCV is required for the webcam demo stream. Install requirements/ml.txt."
        ) from exc
    return cv2


app = create_app()
