from __future__ import annotations

import argparse
from dataclasses import dataclass
from time import monotonic, sleep

from services.vision.table_roi import TableRoiAnalyzer, parse_table_roi
from services.vision.yolo_detector import (
    UltralyticsYoloDetector,
    YoloDetectorConfig,
    draw_yolo_detections,
)


@dataclass(slots=True)
class OccupancyState:
    state: str = "free"
    occupied_since: float | None = None
    empty_since: float | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Baseline práctico: cámara -> YOLO person -> ROI mesa -> estado OCUPADA/LIBRE."
        )
    )
    parser.add_argument("--source", default="0", help="Índice de cámara, vídeo o URL RTSP/HTTP.")
    parser.add_argument("--model", default="yolo11n.pt")
    parser.add_argument("--table-id", default="table_01")
    parser.add_argument(
        "--roi",
        default="",
        help="x_min,y_min,x_max,y_max. Vacío = frame completo.",
    )
    parser.add_argument("--roi-margin", type=float, default=0.05)
    parser.add_argument("--image-size", type=int, default=320)
    parser.add_argument("--confidence", type=float, default=0.35)
    parser.add_argument("--inference-stride", type=int, default=3)
    parser.add_argument("--occupied-seconds", type=float, default=3.0)
    parser.add_argument("--free-seconds", type=float, default=5.0)
    parser.add_argument("--display", action="store_true", help="Muestra ventana OpenCV local.")
    return parser.parse_args()


def run_baseline(args: argparse.Namespace) -> None:
    if args.inference_stride <= 0:
        raise ValueError("inference-stride must be positive.")
    if args.occupied_seconds < 0 or args.free_seconds < 0:
        raise ValueError("occupied/free seconds must be >= 0.")

    try:
        import cv2
    except ModuleNotFoundError as exc:
        raise RuntimeError("OpenCV es necesario. Instala requirements/ml.txt.") from exc

    capture = cv2.VideoCapture(normalize_source(args.source))
    if not capture.isOpened():
        raise RuntimeError(f"No se pudo abrir la fuente: {args.source!r}")

    detector = UltralyticsYoloDetector(
        YoloDetectorConfig(
            model_path=args.model,
            confidence_threshold=args.confidence,
            image_size=args.image_size,
            allowed_labels=("person",),
        )
    )
    table_detector = TableRoiAnalyzer(detector)
    table_roi = parse_table_roi(args.roi or None, args.table_id, args.roi_margin)
    state = OccupancyState()
    frame_index = 0
    last_detections = []

    try:
        print("Baseline iniciado. Pulsa Ctrl+C para salir.")
        while True:
            ok, frame = capture.read()
            if not ok or frame is None:
                sleep(0.05)
                continue

            if frame_index % args.inference_stride == 0:
                last_detections = table_detector.detect(frame, table_roi)
                person_count = sum(
                    1 for detection in last_detections if detection.label == "person"
                )
                update_occupancy_state(
                    state=state,
                    person_count=person_count,
                    now=monotonic(),
                    occupied_seconds=args.occupied_seconds,
                    free_seconds=args.free_seconds,
                    table_id=args.table_id,
                )
            frame_index += 1

            if args.display:
                output = draw_yolo_detections(frame, last_detections)
                cv2.imshow("RestaurIA baseline ocupacion", output)
                if cv2.waitKey(1) & 0xFF == 27:
                    break
    finally:
        capture.release()
        if args.display:
            cv2.destroyAllWindows()


def update_occupancy_state(
    state: OccupancyState,
    person_count: int,
    now: float,
    occupied_seconds: float,
    free_seconds: float,
    table_id: str,
) -> None:
    if person_count > 0:
        state.empty_since = None
        if state.occupied_since is None:
            state.occupied_since = now
        if state.state != "occupied" and now - state.occupied_since >= occupied_seconds:
            state.state = "occupied"
            print(f"{table_id}: OCUPADA ({person_count} persona/s)")
        return

    state.occupied_since = None
    if state.empty_since is None:
        state.empty_since = now
    if state.state != "free" and now - state.empty_since >= free_seconds:
        state.state = "free"
        print(f"{table_id}: LIBRE")


def normalize_source(source: str) -> str | int:
    return int(source) if source.isdigit() else source


if __name__ == "__main__":
    run_baseline(parse_args())
