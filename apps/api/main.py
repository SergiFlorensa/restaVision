from __future__ import annotations

import asyncio
import json
import platform
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import Condition, Event, Thread
from time import perf_counter, sleep
from typing import Any

import numpy as np
from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from services.alerts.anomaly import OperationalAlert
from services.events.models import (
    CameraStatus,
    DomainEvent,
    OperationalAction,
    TableDefinition,
    TableObservation,
    TableOperationalUpdate,
    TablePrediction,
    TableSession,
    TableSnapshot,
    TableState,
    ZoneDefinition,
)
from services.events.persistence import SqlAlchemyMVPRepository
from services.events.realtime import RealtimeEvent, RealtimeEventBus, RealtimeSubscription
from services.events.service import RestaurantMVPService
from services.events.settings import PersistenceSettings
from services.vision.detection_policy import DetectionPolicy, TemporalEvidenceAccumulator
from services.vision.person_demo import DemoPersonDetectionConfig, OpenCVPersonDemoDetector
from services.vision.pose import (
    UltralyticsYoloPoseEstimator,
    YoloPoseConfig,
    draw_pose_detections,
)
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
from services.voice import VoiceReservationAgent

from apps.api.schemas import (
    AlertResponse,
    CameraResponse,
    CameraSnapshotResponse,
    CameraUpsertRequest,
    DecisionFeedbackRequest,
    DecisionFeedbackResponse,
    DecisionRecommendationResponse,
    DemoPersonDetectionStatusResponse,
    EventResponse,
    HealthResponse,
    MarkReadyRequest,
    ObservationRequest,
    ObservationResponse,
    OperationalActionRequest,
    OperationalActionResponse,
    PredictionResponse,
    QueueGroupCreateRequest,
    QueueGroupResponse,
    ServiceAlertResponse,
    ServiceTimelineEventResponse,
    SessionResponse,
    TableResponse,
    TableRuntimeUpdateRequest,
    TableServiceAnalysisResponse,
    TableServiceMonitorStatusResponse,
    TableUpsertRequest,
    VoiceAvailabilityResponse,
    VoiceCallCreateRequest,
    VoiceCallResponse,
    VoiceGatekeeperStatusResponse,
    VoiceMetricsResponse,
    VoiceReservationDraftResponse,
    VoiceReservationResponse,
    VoiceTurnRequest,
    VoiceTurnResponse,
    YoloPersonDetectionStatusResponse,
    YoloPoseDetectionStatusResponse,
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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:5173",
            "http://127.0.0.1:4173",
            "http://localhost:5173",
            "http://localhost:4173",
        ],
        allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["*"],
    )
    app.state.mvp_service = mvp_service or build_mvp_service_from_environment()
    app.state.voice_agent = VoiceReservationAgent(app.state.mvp_service)
    app.state.table_service_analyses = {}
    app.state.table_service_realtime_bus = RealtimeEventBus(max_queue_size=100)
    app.state.table_service_realtime_signatures = {}

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

    @app.get(
        "/api/v1/demo/yolo-pose/status",
        response_model=YoloPoseDetectionStatusResponse,
        tags=["vision-demo"],
    )
    def yolo_pose_detection_status(
        source: int | str = Query(default=0),
        model: str = Query(default="yolo11n-pose.pt"),
        confidence: float = Query(default=0.35, ge=0.0, le=1.0),
        keypoint_confidence: float = Query(default=0.35, ge=0.0, le=1.0),
        image_size: int = Query(default=256, ge=160, le=1280),
        inference_stride: int = Query(default=6, ge=1, le=30),
    ) -> YoloPoseDetectionStatusResponse:
        return YoloPoseDetectionStatusResponse(
            available=is_ultralytics_available(),
            stream_url=(
                "/api/v1/demo/yolo-pose/stream"
                f"?source={source}&model={model}&confidence={confidence}"
                f"&keypoint_confidence={keypoint_confidence}"
                f"&image_size={image_size}&inference_stride={inference_stride}"
            ),
            camera_source=str(source),
            model_path=model,
            detector="Ultralytics YOLO pose con esqueleto 2D y silueta aproximada",
            confidence_threshold=confidence,
            keypoint_confidence_threshold=keypoint_confidence,
            image_size=image_size,
            inference_stride=inference_stride,
            usage_note=(
                "Modo opcional para probar pose/silueta humana. No sustituye el flujo "
                "principal de ocupación; úsalo con image_size bajo y stride alto en CPU."
            ),
            privacy_note=(
                "Estima puntos corporales anónimos; no identifica rostros, nombres ni identidad."
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

    @app.get("/api/v1/demo/yolo-pose/stream", tags=["vision-demo"])
    def yolo_pose_detection_stream(
        source: int | str = Query(default=0),
        model: str = Query(default="yolo11n-pose.pt"),
        confidence: float = Query(default=0.35, ge=0.0, le=1.0),
        iou: float = Query(default=0.5, ge=0.0, le=1.0),
        keypoint_confidence: float = Query(default=0.35, ge=0.0, le=1.0),
        width: int = Query(default=640, ge=160, le=1920),
        height: int = Query(default=480, ge=120, le=1080),
        image_size: int = Query(default=256, ge=160, le=1280),
        max_detections: int = Query(default=10, ge=1, le=50),
        inference_stride: int = Query(default=6, ge=1, le=30),
        min_box_area_ratio: float = Query(default=0.001, ge=0.0, le=1.0),
        jpeg_quality: int = Query(default=72, ge=35, le=95),
        draw_boxes: bool = Query(default=False),
        draw_silhouette: bool = Query(default=True),
    ) -> StreamingResponse:
        config = YoloPoseConfig(
            model_path=model,
            confidence_threshold=confidence,
            iou_threshold=iou,
            image_size=image_size,
            max_detections=max_detections,
            keypoint_confidence_threshold=keypoint_confidence,
            min_box_area_ratio=min_box_area_ratio,
        )
        return StreamingResponse(
            _iter_yolo_pose_mjpeg(
                source=source,
                width=width,
                height=height,
                pose_config=config,
                inference_stride=inference_stride,
                jpeg_quality=jpeg_quality,
                draw_boxes=draw_boxes,
                draw_silhouette=draw_silhouette,
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
        pose_overlay: bool = Query(default=False),
    ) -> TableServiceMonitorStatusResponse:
        return TableServiceMonitorStatusResponse(
            available=is_ultralytics_available(),
            stream_url=(
                "/api/v1/demo/table-service/stream"
                f"?source={source}&table_id={table_id}&model={model}"
                f"&confidence={confidence}&iou={iou}&inference_stride={inference_stride}"
                f"&pose_overlay={str(pose_overlay).lower()}"
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
        jpeg_quality: int = Query(default=72, ge=35, le=95),
        dirty_grace_seconds: int = Query(default=180, ge=0, le=900),
        finishing_empty_plate_ratio: float = Query(default=0.5, gt=0.0, le=1.0),
        pose_overlay: bool = Query(
            default=False,
            description="Dibuja esqueleto/silueta humana encima del análisis de mesa.",
        ),
        pose_model: str = Query(default="yolo11n-pose.pt"),
        pose_image_size: int = Query(default=256, ge=160, le=1280),
        pose_inference_stride: int = Query(default=10, ge=1, le=60),
        pose_confidence: float = Query(default=0.35, ge=0.0, le=1.0),
        pose_keypoint_confidence: float = Query(default=0.35, ge=0.0, le=1.0),
        pose_draw_boxes: bool = Query(default=False),
        pose_draw_silhouette: bool = Query(default=True),
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
        edge_hud: bool = Query(
            default=False,
            description="Muestra FPS, latencia y frecuencia de inferencia sobre el v?deo.",
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
                jpeg_quality=jpeg_quality,
                pose_config=(
                    YoloPoseConfig(
                        model_path=pose_model,
                        confidence_threshold=pose_confidence,
                        image_size=pose_image_size,
                        max_detections=8,
                        keypoint_confidence_threshold=pose_keypoint_confidence,
                        min_box_area_ratio=0.001,
                    )
                    if pose_overlay
                    else None
                ),
                pose_inference_stride=pose_inference_stride,
                pose_draw_boxes=pose_draw_boxes,
                pose_draw_silhouette=pose_draw_silhouette,
                edge_hud=edge_hud,
                monitor_config=TableServiceMonitorConfig(
                    table_id=table_id,
                    dirty_grace_seconds=dirty_grace_seconds,
                    finishing_empty_plate_ratio=finishing_empty_plate_ratio,
                ),
                realtime_bus=app.state.table_service_realtime_bus,
                realtime_signatures=app.state.table_service_realtime_signatures,
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

    @app.get(
        "/api/v1/demo/table-service/events/stream",
        tags=["vision-demo"],
    )
    async def stream_table_service_events(
        request: Request,
        table_id: str | None = Query(
            default=None,
            description="Filtra eventos SSE por mesa. Si se omite, emite todas las mesas.",
        ),
        heartbeat_seconds: int = Query(default=15, ge=5, le=60),
    ) -> StreamingResponse:
        bus: RealtimeEventBus = request.app.state.table_service_realtime_bus
        subscription = bus.subscribe()
        return StreamingResponse(
            _iter_realtime_sse(
                request=request,
                bus=bus,
                subscription=subscription,
                table_id=table_id,
                heartbeat_seconds=heartbeat_seconds,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
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

    @app.patch("/api/v1/tables/{table_id}/runtime", response_model=TableResponse, tags=["state"])
    def update_table_runtime(
        request: Request,
        table_id: str,
        payload: TableRuntimeUpdateRequest,
    ) -> TableResponse:
        service = get_service(request)
        try:
            state = TableState(payload.state) if payload.state is not None else None
            snapshot = service.update_table_runtime(
                table_id,
                TableOperationalUpdate(
                    state=state,
                    phase=payload.phase,
                    people_count=payload.people_count,
                    needs_attention=payload.needs_attention,
                    assigned_staff=payload.assigned_staff,
                    last_attention_at=payload.last_attention_at,
                    operational_note=payload.operational_note,
                ),
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return serialize_table(snapshot)

    @app.post(
        "/api/v1/operational-actions",
        response_model=OperationalActionResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["operations"],
    )
    def record_operational_action(
        request: Request,
        payload: OperationalActionRequest,
    ) -> OperationalActionResponse:
        service = get_service(request)
        try:
            action = service.record_operational_action(
                action_type=payload.action_type,
                table_id=payload.table_id,
                queue_group_id=payload.queue_group_id,
                assigned_staff=payload.assigned_staff,
                target_channel=payload.target_channel,
                message=payload.message,
                payload=payload.payload,
            )
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return serialize_operational_action(action)

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

    @app.get("/api/v1/queue/groups", response_model=list[QueueGroupResponse], tags=["queue"])
    def list_queue_groups(request: Request) -> list[QueueGroupResponse]:
        service = get_service(request)
        return [serialize_queue_group(group) for group in service.list_queue_groups()]

    @app.post(
        "/api/v1/queue/groups",
        response_model=QueueGroupResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["queue"],
    )
    def create_queue_group(
        request: Request,
        payload: QueueGroupCreateRequest,
    ) -> QueueGroupResponse:
        service = get_service(request)
        try:
            group = service.create_queue_group(
                party_size=payload.party_size,
                arrival_ts=payload.arrival_ts or datetime.now(UTC),
                preferred_zone_id=payload.preferred_zone_id,
            )
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return serialize_queue_group(group)

    @app.post(
        "/api/v1/voice/calls",
        response_model=VoiceCallResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["voice"],
    )
    def create_voice_call(
        request: Request,
        payload: VoiceCallCreateRequest,
    ) -> VoiceCallResponse:
        voice_agent = get_voice_agent(request)
        call = voice_agent.start_call(
            caller_phone=payload.caller_phone,
            source_channel=payload.source_channel,
        )
        return serialize_voice_call(call)

    @app.get(
        "/api/v1/voice/calls",
        response_model=list[VoiceCallResponse],
        tags=["voice"],
    )
    def list_voice_calls(request: Request) -> list[VoiceCallResponse]:
        voice_agent = get_voice_agent(request)
        return [serialize_voice_call(call) for call in voice_agent.list_calls()]

    @app.get(
        "/api/v1/voice/calls/{call_id}",
        response_model=VoiceCallResponse,
        tags=["voice"],
    )
    def get_voice_call(request: Request, call_id: str) -> VoiceCallResponse:
        voice_agent = get_voice_agent(request)
        try:
            call = voice_agent.get_call(call_id)
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return serialize_voice_call(call)

    @app.post(
        "/api/v1/voice/calls/{call_id}/turns",
        response_model=VoiceTurnResponse,
        tags=["voice"],
    )
    def create_voice_turn(
        request: Request,
        call_id: str,
        payload: VoiceTurnRequest,
    ) -> VoiceTurnResponse:
        voice_agent = get_voice_agent(request)
        try:
            result = voice_agent.handle_turn(
                call_id,
                transcript=payload.transcript,
                confidence=payload.confidence,
                observed_at=payload.observed_at,
            )
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return serialize_voice_turn_result(result)

    @app.get(
        "/api/v1/voice/reservations",
        response_model=list[VoiceReservationResponse],
        tags=["voice"],
    )
    def list_voice_reservations(request: Request) -> list[VoiceReservationResponse]:
        voice_agent = get_voice_agent(request)
        return [
            serialize_voice_reservation(reservation)
            for reservation in voice_agent.list_reservations()
        ]

    @app.get(
        "/api/v1/voice/gatekeeper/status",
        response_model=VoiceGatekeeperStatusResponse,
        tags=["voice"],
    )
    def get_voice_gatekeeper_status(request: Request) -> VoiceGatekeeperStatusResponse:
        voice_agent = get_voice_agent(request)
        return serialize_voice_gatekeeper_status(voice_agent.gatekeeper_status())

    @app.get(
        "/api/v1/voice/metrics",
        response_model=VoiceMetricsResponse,
        tags=["voice"],
    )
    def get_voice_metrics(request: Request) -> VoiceMetricsResponse:
        voice_agent = get_voice_agent(request)
        return serialize_voice_metrics(voice_agent.metrics())

    @app.get(
        "/api/v1/decisions/next-best-action",
        response_model=list[DecisionRecommendationResponse],
        tags=["decisions"],
    )
    def next_best_action(
        request: Request,
        limit: int = Query(default=3, ge=1, le=10),
    ) -> list[DecisionRecommendationResponse]:
        service = get_service(request)
        return [
            serialize_decision_recommendation(recommendation)
            for recommendation in service.recommend_next_best_action(limit=limit)
        ]

    @app.post(
        "/api/v1/decisions/{decision_id}/feedback",
        response_model=DecisionFeedbackResponse,
        status_code=status.HTTP_201_CREATED,
        tags=["decisions"],
    )
    def record_decision_feedback(
        request: Request,
        decision_id: str,
        payload: DecisionFeedbackRequest,
    ) -> DecisionFeedbackResponse:
        service = get_service(request)
        try:
            feedback = service.record_decision_feedback(
                decision_id=decision_id,
                feedback_type=payload.feedback_type,
                accepted=payload.accepted,
                useful=payload.useful,
                outcome=payload.outcome,
                comment=payload.comment,
            )
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return serialize_decision_feedback(feedback)

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
        dirty_grace_seconds: int = Query(default=180, ge=0, le=900),
        finishing_empty_plate_ratio: float = Query(default=0.5, gt=0.0, le=1.0),
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
        monitor = TableServiceMonitor(
            TableServiceMonitorConfig(
                table_id=table_id,
                dirty_grace_seconds=dirty_grace_seconds,
                finishing_empty_plate_ratio=finishing_empty_plate_ratio,
            )
        )

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
            _publish_table_service_realtime_update(
                analysis=analysis,
                bus=app.state.table_service_realtime_bus,
                signatures=app.state.table_service_realtime_signatures,
            )
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


def get_voice_agent(request: Request) -> VoiceReservationAgent:
    return request.app.state.voice_agent


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
        phase=snapshot.phase,
        needs_attention=snapshot.needs_attention,
        assigned_staff=snapshot.assigned_staff,
        last_attention_at=snapshot.last_attention_at,
        operational_note=snapshot.operational_note,
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


def serialize_queue_group(group: Any) -> QueueGroupResponse:
    return QueueGroupResponse(
        queue_group_id=group.queue_group_id,
        party_size=group.party_size,
        arrival_ts=group.arrival_ts,
        status=str(group.status),
        promised_wait_min=group.promised_wait_min,
        promised_wait_max=group.promised_wait_max,
        promised_at=group.promised_at,
        preferred_zone_id=group.preferred_zone_id,
    )


def serialize_decision_recommendation(recommendation: Any) -> DecisionRecommendationResponse:
    return DecisionRecommendationResponse(
        decision_id=recommendation.decision_id,
        mode=recommendation.mode,
        priority=recommendation.priority,
        question=recommendation.question,
        answer=recommendation.answer,
        table_id=recommendation.table_id,
        queue_group_id=recommendation.queue_group_id,
        eta_minutes=recommendation.eta_minutes,
        confidence=recommendation.confidence,
        impact=recommendation.impact,
        reason=list(recommendation.reason),
        expires_in_seconds=recommendation.expires_in_seconds,
        metadata=recommendation.metadata,
    )


def serialize_decision_feedback(feedback: Any) -> DecisionFeedbackResponse:
    return DecisionFeedbackResponse(
        feedback_id=feedback.feedback_id,
        decision_id=feedback.decision_id,
        ts=feedback.ts,
        feedback_type=feedback.feedback_type,
        accepted=feedback.accepted,
        useful=feedback.useful,
        outcome=feedback.outcome,
        comment=feedback.comment,
    )


def serialize_operational_action(action: OperationalAction) -> OperationalActionResponse:
    return OperationalActionResponse(
        action_id=action.action_id,
        ts=action.ts,
        action_type=action.action_type,
        table_id=action.table_id,
        queue_group_id=action.queue_group_id,
        assigned_staff=action.assigned_staff,
        target_channel=action.target_channel,
        message=action.message,
        payload_json=action.payload_json,
    )


def serialize_voice_call(call: Any) -> VoiceCallResponse:
    draft = call.reservation_draft
    return VoiceCallResponse(
        call_id=call.call_id,
        started_at=call.started_at,
        source_channel=call.source_channel,
        caller_phone=call.caller_phone,
        status=str(call.status),
        intent=str(call.intent),
        scenario_id=call.scenario_id,
        reservation_draft=VoiceReservationDraftResponse(
            party_size=draft.party_size,
            requested_date=draft.requested_date,
            requested_date_text=draft.requested_date_text,
            date_parser=draft.date_parser,
            requested_time_text=draft.requested_time_text,
            requested_at=draft.requested_at,
            time_parser=draft.time_parser,
            customer_name=draft.customer_name,
            phone=draft.phone,
            preferred_zone_id=draft.preferred_zone_id,
        ),
        reservation_id=call.reservation_id,
        escalated_reason=call.escalated_reason,
        ended_at=call.ended_at,
    )


def serialize_voice_reservation(reservation: Any) -> VoiceReservationResponse:
    return VoiceReservationResponse(
        reservation_id=reservation.reservation_id,
        customer_name=reservation.customer_name,
        phone=reservation.phone,
        party_size=reservation.party_size,
        requested_time_text=reservation.requested_time_text,
        requested_at=reservation.requested_at,
        table_id=reservation.table_id,
        status=str(reservation.status),
        created_at=reservation.created_at,
        source_call_id=reservation.source_call_id,
        notes=reservation.notes,
    )


def serialize_voice_availability(availability: Any | None) -> VoiceAvailabilityResponse | None:
    if availability is None:
        return None
    return VoiceAvailabilityResponse(
        available=availability.available,
        table_id=availability.table_id,
        reason=availability.reason,
        confidence=availability.confidence,
        pressure_mode=availability.pressure_mode,
        pressure_reasons=list(availability.pressure_reasons),
    )


def serialize_voice_turn_result(result: Any) -> VoiceTurnResponse:
    return VoiceTurnResponse(
        call=serialize_voice_call(result.call),
        reply_text=result.reply_text,
        intent=str(result.intent),
        confidence=result.confidence,
        action_name=result.action_name,
        action_payload=result.action_payload,
        missing_fields=list(result.missing_fields),
        reservation=(
            serialize_voice_reservation(result.reservation)
            if result.reservation is not None
            else None
        ),
        availability=serialize_voice_availability(result.availability),
        escalated=result.escalated,
    )


def serialize_voice_gatekeeper_status(status: Any) -> VoiceGatekeeperStatusResponse:
    return VoiceGatekeeperStatusResponse(
        mode=status.mode,
        score=status.score,
        ready_tables=status.ready_tables,
        total_tables=status.total_tables,
        waiting_queue_groups=status.waiting_queue_groups,
        active_reservations=status.active_reservations,
        reasons=list(status.reasons),
    )


def serialize_voice_metrics(metrics: Any) -> VoiceMetricsResponse:
    return VoiceMetricsResponse(
        total_calls=metrics.total_calls,
        open_calls=metrics.open_calls,
        confirmed_calls=metrics.confirmed_calls,
        rejected_calls=metrics.rejected_calls,
        escalated_calls=metrics.escalated_calls,
        closed_calls=metrics.closed_calls,
        total_reservations=metrics.total_reservations,
        confirmed_reservations=metrics.confirmed_reservations,
        cancelled_reservations=metrics.cancelled_reservations,
        auto_resolution_rate=metrics.auto_resolution_rate,
        escalation_rate=metrics.escalation_rate,
        average_turns_per_call=metrics.average_turns_per_call,
        gatekeeper=serialize_voice_gatekeeper_status(metrics.gatekeeper),
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


def _publish_table_service_realtime_update(
    analysis: TableServiceAnalysis,
    bus: RealtimeEventBus,
    signatures: dict[str, tuple[Any, ...]],
) -> None:
    signature = _table_service_realtime_signature(analysis)
    if signatures.get(analysis.table_id) == signature:
        return
    signatures[analysis.table_id] = signature
    response = serialize_table_service_analysis(analysis)
    bus.publish(
        RealtimeEvent(
            event_type="table_service_analysis",
            event_id=f"{analysis.table_id}:{int(analysis.updated_at.timestamp() * 1000)}",
            payload=response.model_dump(mode="json"),
        )
    )


def _table_service_realtime_signature(analysis: TableServiceAnalysis) -> tuple[Any, ...]:
    latest_event_id = analysis.timeline_events[0].event_id if analysis.timeline_events else None
    active_alerts = tuple(
        (alert.alert_id, alert.alert_type, alert.severity, alert.message)
        for alert in analysis.active_alerts
    )
    return (
        analysis.state,
        analysis.people_count,
        tuple(sorted(analysis.object_counts.items())),
        tuple(sorted(analysis.missing_items.items())),
        tuple(sorted(analysis.service_flags.items())),
        active_alerts,
        latest_event_id,
        (analysis.seat_duration_seconds or 0) // 10,
        (analysis.away_duration_seconds or 0) // 10,
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


def _iter_yolo_pose_mjpeg(
    source: int | str,
    width: int,
    height: int,
    pose_config: YoloPoseConfig,
    inference_stride: int,
    jpeg_quality: int,
    draw_boxes: bool,
    draw_silhouette: bool,
) -> Any:
    cv2 = _load_cv2_for_demo_stream()
    estimator: UltralyticsYoloPoseEstimator | None = None
    frame_index = 0
    last_poses = []
    policy = FrameSkippingPolicy(
        FrameSkippingConfig(base_interval=inference_stride, hot_interval=inference_stride)
    )
    capture = _LatestFrameCapture(cv2=cv2, source=source, width=width, height=height)
    capture.start()
    last_frame_index = -1

    try:
        while True:
            packet = capture.read_latest(after_index=last_frame_index, timeout_seconds=1.0)
            if packet is None:
                sleep(0.05)
                continue
            current_frame_index, frame = packet
            if current_frame_index == last_frame_index:
                continue
            last_frame_index = current_frame_index

            if estimator is None:
                warmup_frame = frame.copy()
                cv2.putText(
                    warmup_frame,
                    "Inicializando YOLO pose...",
                    (20, 36),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.75,
                    (245, 245, 245),
                    2,
                    cv2.LINE_AA,
                )
                yield _mjpeg_frame(encode_jpeg(warmup_frame, jpeg_quality=jpeg_quality))
                estimator = UltralyticsYoloPoseEstimator(pose_config)

            if policy.should_process(frame_index) and estimator is not None:
                last_poses = estimator.detect(frame)
            frame_index += 1

            annotated = draw_pose_detections(
                frame,
                last_poses,
                draw_boxes=draw_boxes,
                draw_silhouette=draw_silhouette,
            )
            frame_bytes = encode_jpeg(annotated, jpeg_quality=jpeg_quality)
            yield _mjpeg_frame(frame_bytes)
    finally:
        capture.close()


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
    jpeg_quality: int,
    pose_config: YoloPoseConfig | None,
    pose_inference_stride: int,
    pose_draw_boxes: bool,
    pose_draw_silhouette: bool,
    edge_hud: bool,
    monitor_config: TableServiceMonitorConfig,
    realtime_bus: RealtimeEventBus,
    realtime_signatures: dict[str, tuple[Any, ...]],
) -> Any:
    cv2 = _load_cv2_for_demo_stream()
    detector: UltralyticsYoloDetector | None = None
    table_detector: TableRoiAnalyzer | None = None
    pose_estimator: UltralyticsYoloPoseEstimator | None = None
    detection_policy = DetectionPolicy()
    evidence = TemporalEvidenceAccumulator(detection_policy)
    monitor = TableServiceMonitor(monitor_config)
    frame_index = 0
    last_detections = []
    last_poses = []
    last_stable_counts: dict[str, int] = {}
    policy = FrameSkippingPolicy(
        FrameSkippingConfig(base_interval=inference_stride, hot_interval=inference_stride)
    )
    pose_policy = FrameSkippingPolicy(
        FrameSkippingConfig(base_interval=pose_inference_stride, hot_interval=pose_inference_stride)
    )
    capture = _LatestFrameCapture(cv2=cv2, source=source, width=width, height=height)
    try:
        capture.start()
    except RuntimeError as exc:
        error_frame = _build_stream_error_frame(
            cv2,
            title="Camara no disponible",
            message=str(exc),
            hint="Revisa DroidCam, IP, WiFi o cierra otro visor que use la camara.",
        )
        yield _mjpeg_frame(encode_jpeg(error_frame, jpeg_quality=jpeg_quality))
        return
    last_frame_index = -1
    last_frame_ts = perf_counter()
    fps_ema = 0.0
    table_latency_ms = 0.0
    pose_latency_ms = 0.0

    try:
        while True:
            frame_start = perf_counter()
            packet = capture.read_latest(after_index=last_frame_index, timeout_seconds=1.0)
            if packet is None:
                sleep(0.05)
                continue
            current_frame_index, frame = packet
            if current_frame_index == last_frame_index:
                continue
            last_frame_index = current_frame_index

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
                yield _mjpeg_frame(encode_jpeg(warmup_frame, jpeg_quality=jpeg_quality))
                detector = UltralyticsYoloDetector(detector_config)
                table_detector = TableRoiAnalyzer(detector)
                if pose_config is not None:
                    pose_estimator = UltralyticsYoloPoseEstimator(pose_config)

            if policy.should_process(frame_index) and table_detector is not None:
                table_start = perf_counter()
                detections = table_detector.detect(frame, table_roi)
                last_detections = detection_policy.filter_detections(
                    detections,
                    frame_width=int(frame.shape[1]),
                    frame_height=int(frame.shape[0]),
                )
                evidence_snapshot = evidence.update(last_detections)
                last_stable_counts = evidence_snapshot.stable_counts
                table_latency_ms = (perf_counter() - table_start) * 1000
            if (
                pose_config is not None
                and pose_estimator is not None
                and pose_policy.should_process(frame_index)
            ):
                pose_start = perf_counter()
                last_poses = pose_estimator.detect(frame)
                pose_latency_ms = (perf_counter() - pose_start) * 1000

            analysis = monitor.process(
                last_detections,
                stable_counts=last_stable_counts,
            )
            analysis_store[table_id] = analysis
            _publish_table_service_realtime_update(
                analysis=analysis,
                bus=realtime_bus,
                signatures=realtime_signatures,
            )
            frame_index += 1

            annotated = draw_yolo_detections(frame, last_detections)
            if pose_config is not None:
                annotated = draw_pose_detections(
                    annotated,
                    last_poses,
                    draw_boxes=pose_draw_boxes,
                    draw_silhouette=pose_draw_silhouette,
                )
            if table_roi is not None:
                annotated = _draw_table_roi(annotated, table_roi, cv2)
            if text_overlay:
                annotated = _draw_table_service_analysis(annotated, last_detections, analysis, cv2)
            now = perf_counter()
            instant_fps = 1.0 / max(0.001, now - last_frame_ts)
            fps_ema = instant_fps if fps_ema <= 0 else (fps_ema * 0.9 + instant_fps * 0.1)
            last_frame_ts = now
            if edge_hud:
                annotated = _draw_edge_hud(
                    annotated,
                    cv2=cv2,
                    fps=fps_ema,
                    table_latency_ms=table_latency_ms,
                    pose_latency_ms=pose_latency_ms,
                    frame_latency_ms=(perf_counter() - frame_start) * 1000,
                    inference_stride=inference_stride,
                    pose_inference_stride=(
                        pose_inference_stride if pose_config is not None else None
                    ),
                    object_count=len(last_detections),
                    pose_count=len(last_poses),
                )
            frame_bytes = encode_jpeg(annotated, jpeg_quality=jpeg_quality)
            yield _mjpeg_frame(frame_bytes)
    finally:
        capture.close()


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


def _draw_edge_hud(
    frame: Any,
    *,
    cv2: Any,
    fps: float,
    table_latency_ms: float,
    pose_latency_ms: float,
    frame_latency_ms: float,
    inference_stride: int,
    pose_inference_stride: int | None,
    object_count: int,
    pose_count: int,
) -> Any:
    """Dibuja telemetría edge mínima para validar fluidez en pruebas reales."""
    output = frame.copy()
    height, width = output.shape[:2]
    panel_width = min(360, max(250, width // 3))
    x = max(8, width - panel_width - 12)
    y = max(8, height - 118)
    lines = [
        f"FPS video: {fps:4.1f}",
        f"YOLO mesa: {table_latency_ms:5.0f} ms | cada {inference_stride} frames",
        (
            f"Pose: {pose_latency_ms:5.0f} ms | cada {pose_inference_stride} frames"
            if pose_inference_stride is not None
            else "Pose: OFF"
        ),
        f"Frame: {frame_latency_ms:5.0f} ms | obj {object_count} | poses {pose_count}",
    ]
    tone = (58, 128, 75) if fps >= 12 else (30, 135, 210) if fps >= 7 else (55, 55, 180)

    overlay = output.copy()
    cv2.rectangle(overlay, (x, y), (width - 12, height - 12), (16, 18, 16), -1)
    output = cv2.addWeighted(overlay, 0.72, output, 0.28, 0)
    cv2.rectangle(output, (x, y), (width - 12, height - 12), tone, 2)
    cv2.circle(output, (x + 16, y + 19), 6, tone, -1)
    cv2.putText(
        output,
        "EDGE HUD",
        (x + 30, y + 24),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.56,
        (245, 245, 245),
        2,
        cv2.LINE_AA,
    )
    for index, line in enumerate(lines):
        cv2.putText(
            output,
            line,
            (x + 12, y + 48 + index * 18),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (214, 232, 205),
            1,
            cv2.LINE_AA,
        )
    return output


def _build_stream_error_frame(cv2: Any, *, title: str, message: str, hint: str) -> Any:
    frame = np.zeros((480, 854, 3), dtype=np.uint8)
    frame[:] = (18, 14, 12)
    overlay = frame.copy()
    cv2.rectangle(overlay, (32, 52), (822, 428), (34, 29, 25), -1)
    frame = cv2.addWeighted(overlay, 0.92, frame, 0.08, 0)
    cv2.rectangle(frame, (32, 52), (822, 428), (121, 9, 24), 2)
    cv2.circle(frame, (74, 104), 14, (28, 28, 180), -1)
    cv2.putText(
        frame,
        title,
        (104, 112),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (245, 245, 245),
        2,
        cv2.LINE_AA,
    )
    lines = _wrap_overlay_text(message, 720, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1, cv2)
    lines.extend(_wrap_overlay_text(hint, 720, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1, cv2))
    lines.append("Para iPhone/DroidCam: abre la app, pulsa Start y evita abrir otro visor.")
    for index, line in enumerate(lines[:10]):
        cv2.putText(
            frame,
            line,
            (64, 166 + index * 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (218, 211, 198),
            1,
            cv2.LINE_AA,
        )
    return frame


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


class _LatestFrameCapture:
    """Reads camera frames in the background and exposes only the newest frame."""

    def __init__(
        self,
        cv2: Any,
        source: int | str,
        width: int,
        height: int,
        buffer_size: int = 1,
    ) -> None:
        self._cv2 = cv2
        self._source = source
        self._width = width
        self._height = height
        self._buffer_size = buffer_size
        self._capture: Any | None = None
        self._condition = Condition()
        self._stop = Event()
        self._thread: Thread | None = None
        self._latest_frame: Any | None = None
        self._latest_index = -1
        self._open_error: RuntimeError | None = None

    def start(self) -> None:
        capture = _open_video_capture(self._cv2, self._source)
        _configure_low_latency_capture(
            self._cv2,
            capture,
            source=self._source,
            width=self._width,
            height=self._height,
            buffer_size=self._buffer_size,
        )
        if not capture.isOpened():
            capture.release()
            raise RuntimeError(f"Could not open video source: {self._source!r}")

        self._capture = capture
        self._thread = Thread(
            target=self._read_loop,
            name="restauria-latest-frame-capture",
            daemon=True,
        )
        self._thread.start()

    def read_latest(
        self,
        after_index: int,
        timeout_seconds: float,
    ) -> tuple[int, Any] | None:
        with self._condition:
            if self._latest_index <= after_index and self._open_error is None:
                self._condition.wait(timeout_seconds)
            if self._open_error is not None:
                raise self._open_error
            if self._latest_frame is None or self._latest_index <= after_index:
                return None
            return self._latest_index, self._latest_frame

    def close(self) -> None:
        self._stop.set()
        with self._condition:
            self._condition.notify_all()
        if self._thread is not None:
            self._thread.join(timeout=1.5)
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    def _read_loop(self) -> None:
        if self._capture is None:
            return
        frame_index = 0
        while not self._stop.is_set():
            ok, frame = self._capture.read()
            if not ok or frame is None:
                sleep(0.02)
                continue
            with self._condition:
                self._latest_index = frame_index
                self._latest_frame = frame
                frame_index += 1
                self._condition.notify_all()


def _configure_low_latency_capture(
    cv2: Any,
    capture: Any,
    source: int | str,
    width: int,
    height: int,
    buffer_size: int,
) -> None:
    if buffer_size > 0:
        capture.set(cv2.CAP_PROP_BUFFERSIZE, buffer_size)
    normalized_source = _normalize_video_source(source)
    if not isinstance(normalized_source, int):
        return
    if width > 0:
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    if height > 0:
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)


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


async def _iter_realtime_sse(
    request: Request,
    bus: RealtimeEventBus,
    subscription: RealtimeSubscription,
    table_id: str | None,
    heartbeat_seconds: int,
) -> Any:
    try:
        yield b": restauria connected\n\n"
        while True:
            if await request.is_disconnected():
                break
            event = await asyncio.to_thread(subscription.get, float(heartbeat_seconds))
            if event is None:
                yield b": heartbeat\n\n"
                continue
            if table_id is not None and event.payload.get("table_id") != table_id:
                continue
            yield _sse_frame(event)
    finally:
        bus.unsubscribe(subscription)


def _sse_frame(event: RealtimeEvent) -> bytes:
    lines: list[str] = []
    if event.event_id is not None:
        lines.append(f"id: {event.event_id}")
    lines.append(f"event: {event.event_type}")
    data = json.dumps(event.payload, ensure_ascii=False, separators=(",", ":"))
    for line in data.splitlines() or ["{}"]:
        lines.append(f"data: {line}")
    return ("\n".join(lines) + "\n\n").encode("utf-8")


def _load_cv2_for_demo_stream() -> Any:
    try:
        import cv2
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "OpenCV is required for the webcam demo stream. Install requirements/ml.txt."
        ) from exc
    return cv2


app = create_app()
