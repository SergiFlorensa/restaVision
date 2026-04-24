from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from services.vision.table_service_monitor import SERVICE_RELEVANT_LABELS, TableServiceMonitor
from services.vision.yolo_detector import (
    UltralyticsYoloDetector,
    YoloDetectorConfig,
    draw_detection_summary,
    draw_yolo_detections,
    encode_jpeg,
    is_ultralytics_available,
)

app = FastAPI(
    title="restaVision Table Service Demo",
    version="0.1.0",
    description="Demo local para analizar servicio de mesa con YOLO y una webcam/cámara IP.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

service_monitor = TableServiceMonitor()


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "now": datetime.now(UTC)}


@app.get("/api/v1/demo/table-service/status")
def table_service_status(
    source: str = Query(default="0", description="0 para webcam o URL RTSP/HTTP de cámara IP."),
    model_path: str = Query(default="yolo11n.pt"),
    confidence: float = Query(default=0.35, ge=0.01, le=1.0),
    iou: float = Query(default=0.5, ge=0.01, le=1.0),
    image_size: int = Query(default=480, ge=160, le=1280),
    inference_stride: int = Query(default=3, ge=1, le=30),
) -> dict[str, Any]:
    return {
        "available": is_ultralytics_available(),
        "stream_url": (
            "/api/v1/demo/table-service/stream"
            f"?source={source}&model_path={model_path}&confidence={confidence}"
            f"&iou={iou}&image_size={image_size}&inference_stride={inference_stride}"
        ),
        "analysis_url": "/api/v1/demo/table-service/analysis",
        "source": source,
        "model_path": model_path,
        "confidence": confidence,
        "iou": iou,
        "image_size": image_size,
        "inference_stride": inference_stride,
        "allowed_labels": list(SERVICE_RELEVANT_LABELS),
        "privacy_note": "Demo sin reconocimiento facial: solo objetos, personas anónimas y eventos de mesa.",
        "usage_note": "Para plato/mano levantada hace falta modelo personalizado si YOLO base no trae esas clases.",
    }


@app.get("/api/v1/demo/table-service/analysis")
def table_service_analysis() -> dict[str, Any]:
    return service_monitor.current().to_payload()


@app.get("/api/v1/demo/table-service/stream")
def table_service_stream(
    source: str = Query(default="0", description="0 para webcam o URL RTSP/HTTP de cámara IP."),
    model_path: str = Query(default="yolo11n.pt"),
    confidence: float = Query(default=0.35, ge=0.01, le=1.0),
    iou: float = Query(default=0.5, ge=0.01, le=1.0),
    image_size: int = Query(default=480, ge=160, le=1280),
    inference_stride: int = Query(default=3, ge=1, le=30),
) -> StreamingResponse:
    return StreamingResponse(
        _iter_service_stream(
            source=source,
            model_path=model_path,
            confidence=confidence,
            iou=iou,
            image_size=image_size,
            inference_stride=inference_stride,
        ),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


def _iter_service_stream(
    source: str,
    model_path: str,
    confidence: float,
    iou: float,
    image_size: int,
    inference_stride: int,
) -> Iterator[bytes]:
    cv2 = _load_cv2()
    camera_source: int | str = int(source) if source.isdigit() else source
    capture = cv2.VideoCapture(camera_source)
    if not capture.isOpened():
        raise RuntimeError(f"No se ha podido abrir la cámara o stream: {source}")

    detector = UltralyticsYoloDetector(
        YoloDetectorConfig(
            model_path=model_path,
            confidence_threshold=confidence,
            iou_threshold=iou,
            image_size=image_size,
            allowed_labels=tuple(SERVICE_RELEVANT_LABELS),
        )
    )

    frame_index = 0
    latest_detections = []
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break

            frame_index += 1
            if frame_index % inference_stride == 0:
                latest_detections = detector.detect(frame)
                service_monitor.process(latest_detections, observed_at=datetime.now(UTC))

            output = draw_yolo_detections(frame, latest_detections)
            output = draw_detection_summary(output, latest_detections, title="Mesa servicio")
            output = _draw_service_overlay(output, service_monitor.current().to_payload())
            jpeg = encode_jpeg(output, jpeg_quality=80)
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"
    finally:
        capture.release()


def _draw_service_overlay(frame: Any, analysis: dict[str, Any]) -> Any:
    cv2 = _load_cv2()
    output = frame.copy()
    height, width = output.shape[:2]
    panel_width = 430
    x1 = max(12, width - panel_width - 12)
    y1 = 12
    x2 = width - 12
    y2 = 236

    overlay = output.copy()
    cv2.rectangle(overlay, (x1, y1), (x2, y2), (18, 18, 20), -1)
    output = cv2.addWeighted(overlay, 0.76, output, 0.24, 0)

    lines = _service_overlay_lines(analysis)
    for index, line in enumerate(lines):
        y = y1 + 30 + index * 24
        color = (244, 244, 244) if index == 0 else (194, 222, 174)
        if "ALERTA" in line or "Falta" in line:
            color = (70, 110, 235)
        cv2.putText(
            output,
            line,
            (x1 + 14, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            2,
            cv2.LINE_AA,
        )
    return output


def _service_overlay_lines(analysis: dict[str, Any]) -> list[str]:
    lines = [f"Mesa: {analysis.get('table_id', 'mesa')} | {analysis.get('state', '-')}"]
    lines.append(f"Personas: {analysis.get('people_count', 0)}")
    seat_seconds = analysis.get("seat_duration_seconds")
    if seat_seconds is not None:
        lines.append(f"Sentado: {_format_seconds(int(seat_seconds))}")
    away_seconds = analysis.get("away_duration_seconds")
    if away_seconds is not None:
        lines.append(f"Ausente: {_format_seconds(int(away_seconds))}")

    missing_items = analysis.get("missing_items", {}) or {}
    if missing_items:
        missing_text = ", ".join(f"{key}:{value}" for key, value in missing_items.items())
        lines.append(f"Falta: {missing_text}")
    else:
        lines.append("Servicio: sin faltas críticas")

    flags = analysis.get("service_flags", {}) or {}
    if flags.get("food_served"):
        lines.append("Comida detectada en mesa")
    if flags.get("customer_needs_attention"):
        lines.append("ALERTA: posible llamada cliente")

    alerts = analysis.get("active_alerts", []) or []
    if alerts:
        lines.append(str(alerts[0].get("message", "Alerta activa"))[:44])
    return lines[:8]


def _format_seconds(seconds: int) -> str:
    minutes, remaining_seconds = divmod(max(0, seconds), 60)
    return f"{minutes:02d}:{remaining_seconds:02d}"


def _load_cv2() -> Any:
    try:
        import cv2
    except ModuleNotFoundError as exc:
        raise RuntimeError("OpenCV es necesario para esta demo. Instala requirements/ml.txt.") from exc
    return cv2
