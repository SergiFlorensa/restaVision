#!/usr/bin/env python
"""
Script para probar TableServiceMonitor en tiempo real con webcam.
Ejecuta: python test_table_service_webcam.py
"""

from services.vision.table_service_monitor import (
    SERVICE_RELEVANT_LABELS,
    TableServiceMonitor,
    TableServiceMonitorConfig,
)
from services.vision.yolo_detector import (
    UltralyticsYoloDetector,
    YoloDetectorConfig,
    is_ultralytics_available,
)


def test_table_service_with_webcam():
    """Prueba el monitor de servicio de mesa con webcam en tiempo real."""
    try:
        import cv2
    except ImportError:
        print("❌ OpenCV no está instalado. Instala: pip install opencv-python")
        return

    if not is_ultralytics_available():
        print("❌ Ultralytics YOLO no está disponible. Instala: pip install ultralytics")
        return

    print("🎥 Iniciando captura desde webcam...")
    print("📊 Analizando servicio de mesa con detección de:")
    print("   - Cubiertos (tenedor, cuchillo, cuchara)")
    print("   - Platos y recipientes")
    print("   - Comida")
    print("   - Personas y gestos de atención")
    print("\n⏹️  Presiona 'q' para salir.\n")

    # Configurar YOLO
    yolo_config = YoloDetectorConfig(
        model_path="yolo11n.pt",
        confidence_threshold=0.25,
        iou_threshold=0.5,
        image_size=320,
        max_detections=30,
        allowed_labels=SERVICE_RELEVANT_LABELS,
    )
    detector = UltralyticsYoloDetector(yolo_config)

    # Configurar monitor de servicio
    monitor_config = TableServiceMonitorConfig(
        table_id="demo_table_01",
        require_plate=True,
        require_fork=True,
        require_knife=True,
        require_spoon=False,
        min_people_for_service_check=1,
        alert_cooldown_seconds=5,
    )
    monitor = TableServiceMonitor(monitor_config)

    # Abrir cámara
    capture = cv2.VideoCapture(0)
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not capture.isOpened():
        print("❌ No se pudo abrir la cámara web.")
        return

    frame_count = 0
    inference_stride = 3

    try:
        while True:
            ok, frame = capture.read()
            if not ok or frame is None:
                print("⚠️  No se pudo leer frame de la cámara")
                continue

            # Detectar cada 3 frames para ahorrar CPU
            if frame_count % inference_stride == 0:
                detections = detector.detect(frame)
                analysis = monitor.process(detections)

                # Mostrar análisis en consola cada ciertos frames
                if frame_count % 30 == 0:
                    print("\n" + "=" * 70)
                    print(f"⏱️  Frame: {frame_count}")
                    print(f"📅 Timestamp: {analysis.updated_at.isoformat()}")
                    print(f"🪑 Estado: {analysis.state}")
                    print(f"👥 Personas: {analysis.people_count}")
                    print(f"⏳ Tiempo sentado: {analysis.seat_duration_seconds or 0}s")

                    if analysis.object_counts:
                        print("🔍 Objetos detectados:")
                        for label, count in sorted(analysis.object_counts.items()):
                            print(f"   - {label}: {count}")

                    if analysis.missing_items:
                        print("❌ Falta completar servicio:")
                        for item, count in analysis.missing_items.items():
                            print(f"   - {item}: {count} faltando")
                    else:
                        if analysis.people_count > 0:
                            print("✅ Servicio de mesa completo")

                    if analysis.service_flags:
                        print("🚩 Banderas de servicio:")
                        for flag, value in analysis.service_flags.items():
                            status = "✅" if value else "❌"
                            print(f"   {status} {flag}")

                    if analysis.active_alerts:
                        print(f"\n⚠️  ALERTAS ACTIVAS ({len(analysis.active_alerts)}):")
                        for alert in analysis.active_alerts:
                            print(f"   🔔 [{alert.severity.upper()}] {alert.message}")

                    if analysis.timeline_events:
                        print("\n📋 Últimos eventos:")
                        for event in analysis.timeline_events[:3]:
                            ts_str = event.ts.strftime("%H:%M:%S")
                            print(f"   [{ts_str}] {event.event_type}: {event.message}")

                    print("=" * 70)

                # Dibujar en frame
                frame = _draw_analysis_on_frame(frame, analysis, cv2)

            frame_count += 1

            # Mostrar frame con análisis
            cv2.imshow("RestaurIA - Análisis de Servicio de Mesa", frame)

            # Salir con 'q'
            if cv2.waitKey(1) & 0xFF == ord("q"):
                print("\n✅ Cerrando análisis de servicio de mesa...")
                break

    except KeyboardInterrupt:
        print("\n✅ Análisis interrumpido por usuario.")
    finally:
        capture.release()
        cv2.destroyAllWindows()


def _draw_analysis_on_frame(frame, analysis, cv2):
    """Dibuja el análisis sobre el frame."""
    height, width = frame.shape[:2]
    y_offset = 25
    line_height = 20
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.5
    thickness = 1
    text_color = (0, 255, 0)
    alert_color = (0, 0, 255)
    missing_color = (0, 165, 255)  # Naranja

    lines = [
        f"Mesa: {analysis.table_id}",
        f"Estado: {analysis.state}",
        f"Personas: {analysis.people_count}",
    ]

    if analysis.people_count > 0:
        lines.append(f"Tiempo: {analysis.seat_duration_seconds or 0}s")

    if analysis.missing_items:
        missing_str = ", ".join([f"{k}:{v}" for k, v in analysis.missing_items.items()])
        lines.append(f"FALTA: {missing_str}")

    if analysis.active_alerts:
        lines.append(f"ALERTAS: {len(analysis.active_alerts)}")

    for i, line in enumerate(lines):
        y = y_offset + (i * line_height)

        if "FALTA:" in line:
            color = missing_color
        elif "ALERTAS:" in line or "⚠️" in line:
            color = alert_color
        else:
            color = text_color

        cv2.putText(
            frame,
            line,
            (10, y),
            font,
            font_scale,
            color,
            thickness,
            cv2.LINE_AA,
        )

    return frame


if __name__ == "__main__":
    print("\n🚀 RestaurIA - Test de Análisis de Servicio de Mesa\n")
    test_table_service_with_webcam()
    print("\n✨ Test completado.\n")
