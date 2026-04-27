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
    count_detections_by_label,
    draw_yolo_detections,
    encode_jpeg,
    is_ultralytics_available,
)

app = FastAPI(
    title="restaVision Table Service Demo",
    version="0.2.0",
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


class DemoTableEventRegistry:
    """In-memory registry for the local demo.

    It links everything detected by the camera to a table reference and a customer
    group/session reference. This is intentionally simple so the demo can be
    tested without PostgreSQL; later it can become the persistence layer.
    """

    def __init__(self) -> None:
        self._sessions_by_table: dict[str, dict[str, str]] = {}
        self._events_by_id: dict[str, dict[str, Any]] = {}
        self._events: list[dict[str, Any]] = []
        self._snapshots_by_table: dict[str, dict[str, Any]] = {}

    def enrich_analysis(self, analysis: dict[str, Any]) -> dict[str, Any]:
        table_id = str(analysis.get("table_id") or "mesa_01")
        table_ref = self._ensure_table_reference(table_id, analysis)
        enriched = {
            **analysis,
            "table_reference": table_ref,
            "session_id": table_ref["session_id"],
            "customer_group_id": table_ref["customer_group_id"],
        }
        enriched["timeline_events"] = [
            self._normalize_event(table_id, table_ref, event)
            for event in enriched.get("timeline_events", [])
        ]
        self._register_snapshot(table_id, enriched)
        return enriched

    def events(self, table_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        selected = self._events
        if table_id:
            selected = [event for event in selected if event.get("table_id") == table_id]
        return selected[:limit]

    def tables(self) -> list[dict[str, Any]]:
        return list(self._snapshots_by_table.values())

    def _ensure_table_reference(self, table_id: str, analysis: dict[str, Any]) -> dict[str, str]:
        if table_id not in self._sessions_by_table:
            stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            self._sessions_by_table[table_id] = {
                "table_id": table_id,
                "session_id": f"{table_id}_sesion_{stamp}",
                "customer_group_id": f"{table_id}_clientes_{stamp}",
            }
        return self._sessions_by_table[table_id]

    def _normalize_event(
        self,
        table_id: str,
        table_ref: dict[str, str],
        raw_event: dict[str, Any],
    ) -> dict[str, Any]:
        event_id = str(raw_event.get("event_id") or f"{table_id}_{len(self._events) + 1}")
        payload = raw_event.get("payload", {}) or {}
        event = {
            **raw_event,
            "event_id": event_id,
            "table_id": table_id,
            "session_id": table_ref["session_id"],
            "customer_group_id": table_ref["customer_group_id"],
            "relation_key": (
                f"{table_id}::{table_ref['session_id']}::{table_ref['customer_group_id']}"
            ),
            "payload": {
                **payload,
                "table_id": table_id,
                "session_id": table_ref["session_id"],
                "customer_group_id": table_ref["customer_group_id"],
            },
        }
        if event_id not in self._events_by_id:
            self._events_by_id[event_id] = event
            self._events.insert(0, event)
            self._events = self._events[:200]
        return self._events_by_id[event_id]

    def _register_snapshot(self, table_id: str, analysis: dict[str, Any]) -> None:
        self._snapshots_by_table[table_id] = {
            "table_id": table_id,
            "table_reference": analysis.get("table_reference"),
            "state": analysis.get("state"),
            "people_count": analysis.get("people_count", 0),
            "object_counts": analysis.get("object_counts", {}),
            "missing_items": analysis.get("missing_items", {}),
            "active_alerts": analysis.get("active_alerts", []),
            "seat_duration_seconds": analysis.get("seat_duration_seconds"),
            "away_duration_seconds": analysis.get("away_duration_seconds"),
            "updated_at": analysis.get("updated_at"),
        }


registry = DemoTableEventRegistry()


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
        "events_url": "/api/v1/demo/table-service/events",
        "tables_url": "/api/v1/demo/table-service/tables",
        "source": source,
        "model_path": model_path,
        "confidence": confidence,
        "iou": iou,
        "image_size": image_size,
        "inference_stride": inference_stride,
        "allowed_labels": list(SERVICE_RELEVANT_LABELS),
        "privacy_note": (
            "Demo sin reconocimiento facial: solo objetos, personas anónimas y eventos de mesa."
        ),
        "usage_note": (
            "Para plato/mano levantada hace falta modelo personalizado "
            "si YOLO base no trae esas clases."
        ),
    }


@app.get("/api/v1/demo/table-service/analysis")
def table_service_analysis() -> dict[str, Any]:
    return registry.enrich_analysis(service_monitor.current().to_payload())


@app.get("/api/v1/demo/table-service/events")
def table_service_events(
    table_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    return {"events": registry.events(table_id=table_id, limit=limit)}


@app.get("/api/v1/demo/table-service/tables")
def table_service_tables() -> dict[str, Any]:
    return {"tables": registry.tables()}


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
                analysis = service_monitor.process(latest_detections, observed_at=datetime.now(UTC))
                registry.enrich_analysis(analysis.to_payload())

            output = draw_yolo_detections(frame, latest_detections)
            output = _draw_operational_overlay(output, latest_detections, table_service_analysis())
            jpeg = encode_jpeg(output, jpeg_quality=80)
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"
    finally:
        capture.release()


def _draw_operational_overlay(frame: Any, detections: list[Any], analysis: dict[str, Any]) -> Any:
    output = frame.copy()
    height, width = output.shape[:2]

    left_width = min(300, max(220, width // 3))
    right_width = min(420, max(260, width // 2))
    bottom_width = min(width - 24, 760)

    output = _draw_panel(
        output,
        title="DETECCION",
        lines=_detection_lines(detections),
        x=12,
        y=12,
        width=left_width,
        max_height=max(120, height // 3),
    )
    output = _draw_panel(
        output,
        title="MESA Y SERVICIO",
        lines=_service_lines(analysis),
        x=max(12, width - right_width - 12),
        y=12,
        width=right_width,
        max_height=max(180, height // 2),
    )
    output = _draw_panel(
        output,
        title="REGISTRO RELACIONADO",
        lines=_event_lines(analysis),
        x=12,
        y=max(12, height - 190),
        width=bottom_width,
        max_height=178,
    )
    return output


def _draw_panel(
    frame: Any,
    title: str,
    lines: list[str],
    x: int,
    y: int,
    width: int,
    max_height: int,
) -> Any:
    cv2 = _load_cv2()
    output = frame.copy()
    frame_height, frame_width = output.shape[:2]
    x = max(6, min(x, frame_width - 60))
    y = max(6, min(y, frame_height - 60))
    width = max(160, min(width, frame_width - x - 6))
    max_height = max(80, min(max_height, frame_height - y - 6))

    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.48
    line_height = 20
    wrapped_lines: list[str] = []
    for line in lines:
        wrapped_lines.extend(_wrap_text(line, width - 24, font, font_scale, 1))

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


def _wrap_text(
    text: str,
    max_width: int,
    font: Any,
    font_scale: float,
    thickness: int,
) -> list[str]:
    cv2 = _load_cv2()
    words = str(text).split()
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


def _service_lines(analysis: dict[str, Any]) -> list[str]:
    table_ref = analysis.get("table_reference", {}) or {}
    lines = [
        f"Mesa: {analysis.get('table_id', 'mesa')} | {analysis.get('state', '-')}",
        f"Sesion: {table_ref.get('session_id', '-')}",
        f"Grupo: {table_ref.get('customer_group_id', '-')}",
        f"Personas: {analysis.get('people_count', 0)}",
    ]
    seat_seconds = analysis.get("seat_duration_seconds")
    if seat_seconds is not None:
        lines.append(f"Tiempo sentado: {_format_seconds(int(seat_seconds))}")
    away_seconds = analysis.get("away_duration_seconds")
    if away_seconds is not None:
        lines.append(f"Tiempo ausente: {_format_seconds(int(away_seconds))}")

    missing_items = analysis.get("missing_items", {}) or {}
    if missing_items:
        missing_text = ", ".join(f"{key}:{value}" for key, value in missing_items.items())
        lines.append(f"Falta: {missing_text}")
    else:
        lines.append("Servicio: sin faltas criticas")

    flags = analysis.get("service_flags", {}) or {}
    if flags.get("food_served"):
        lines.append("Comida detectada en mesa")
    if flags.get("customer_needs_attention"):
        lines.append("ALERTA: posible llamada cliente")
    return lines


def _event_lines(analysis: dict[str, Any]) -> list[str]:
    events = analysis.get("timeline_events", []) or []
    if not events:
        return ["Sin eventos registrados en esta mesa"]
    lines: list[str] = []
    for event in events[:5]:
        ts = str(event.get("ts", ""))[11:19]
        table_id = event.get("table_id") or analysis.get("table_id") or "mesa"
        event_type = event.get("event_type", "evento")
        message = event.get("message", "")
        lines.append(f"{ts} | {table_id} | {event_type} | {message}")
    return lines


def _format_seconds(seconds: int) -> str:
    minutes, remaining_seconds = divmod(max(0, seconds), 60)
    return f"{minutes:02d}:{remaining_seconds:02d}"


def _load_cv2() -> Any:
    try:
        import cv2
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "OpenCV es necesario para esta demo. Instala requirements/ml.txt."
        ) from exc
    return cv2
