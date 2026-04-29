from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

DEFAULT_LABELS = ("plate", "bowl", "plate_empty", "plate_full")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Extrae recortes temporales de platos desde vídeo/cámara para etiquetar "
            "plate_empty y plate_full sin guardar vídeos completos."
        )
    )
    parser.add_argument(
        "--source",
        required=True,
        help="Ruta de vídeo, índice de cámara o URL RTSP/HTTP.",
    )
    parser.add_argument("--model", default="yolo11n.pt", help="Modelo YOLO base o fine-tuned.")
    parser.add_argument(
        "--output-dir",
        default="data/annotations/plate_states/raw",
        help="Directorio local ignorado por Git para guardar crops y manifest.",
    )
    parser.add_argument("--labels", default=",".join(DEFAULT_LABELS), help="Etiquetas a recortar.")
    parser.add_argument("--sample-stride", type=int, default=5, help="Guardar 1 de cada N frames.")
    parser.add_argument("--min-confidence", type=float, default=0.25)
    parser.add_argument("--max-frames", type=int, default=0, help="0 = sin límite.")
    return parser.parse_args()


def collect_plate_sequences(
    source: str | int,
    model_path: str,
    output_dir: Path,
    labels: Iterable[str],
    sample_stride: int,
    min_confidence: float,
    max_frames: int,
) -> int:
    if sample_stride <= 0:
        raise ValueError("sample_stride must be positive.")
    if not 0 <= min_confidence <= 1:
        raise ValueError("min_confidence must be between 0 and 1.")

    try:
        import cv2
        from ultralytics import YOLO
    except ModuleNotFoundError as exc:
        raise RuntimeError("Instala requirements/ml.txt para usar este script.") from exc

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.jsonl"
    model = YOLO(model_path)
    capture = cv2.VideoCapture(source)
    if not capture.isOpened():
        raise RuntimeError(f"No se pudo abrir la fuente de vídeo: {source!r}")

    label_filter = {label.strip() for label in labels if label.strip()}
    saved = 0
    frame_index = 0
    try:
        with manifest_path.open("a", encoding="utf-8") as manifest:
            while True:
                if max_frames and frame_index >= max_frames:
                    break
                ok, frame = capture.read()
                if not ok or frame is None:
                    break
                if frame_index % sample_stride != 0:
                    frame_index += 1
                    continue

                result = model.track(frame, persist=True, verbose=False)[0]
                saved += _save_matching_crops(
                    frame=frame,
                    frame_index=frame_index,
                    result=result,
                    output_dir=output_dir,
                    manifest=manifest,
                    label_filter=label_filter,
                    min_confidence=min_confidence,
                )
                frame_index += 1
    finally:
        capture.release()
    return saved


def _save_matching_crops(
    frame: Any,
    frame_index: int,
    result: Any,
    output_dir: Path,
    manifest: Any,
    label_filter: set[str],
    min_confidence: float,
) -> int:
    import cv2

    boxes = getattr(result, "boxes", None)
    if boxes is None or boxes.xyxy is None:
        return 0

    names = result.names
    xyxy = boxes.xyxy.cpu().numpy()
    cls = boxes.cls.cpu().numpy() if boxes.cls is not None else []
    conf = boxes.conf.cpu().numpy() if boxes.conf is not None else []
    track_ids = boxes.id.cpu().numpy().astype(int) if boxes.id is not None else None

    saved = 0
    frame_height, frame_width = frame.shape[:2]
    for index, box in enumerate(xyxy):
        label = str(names.get(int(cls[index]), int(cls[index]))) if len(cls) > index else "object"
        confidence = float(conf[index]) if len(conf) > index else 0.0
        if label not in label_filter or confidence < min_confidence:
            continue

        x1, y1, x2, y2 = _clip_box(box, frame_width, frame_height)
        if x2 <= x1 or y2 <= y1:
            continue
        track_id = int(track_ids[index]) if track_ids is not None else frame_index
        crop_dir = output_dir / label / f"track_{track_id}"
        crop_dir.mkdir(parents=True, exist_ok=True)
        crop_path = crop_dir / f"frame_{frame_index:06d}.jpg"
        if not cv2.imwrite(str(crop_path), frame[y1:y2, x1:x2]):
            continue
        manifest.write(
            json.dumps(
                {
                    "frame_index": frame_index,
                    "track_id": track_id,
                    "label": label,
                    "confidence": confidence,
                    "bbox_xyxy": [x1, y1, x2, y2],
                    "crop_path": str(crop_path),
                },
                ensure_ascii=False,
            )
            + "\n"
        )
        saved += 1
    return saved


def _clip_box(box: Any, frame_width: int, frame_height: int) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = [int(round(value)) for value in box]
    return (
        max(0, min(x1, frame_width)),
        max(0, min(y1, frame_height)),
        max(0, min(x2, frame_width)),
        max(0, min(y2, frame_height)),
    )


def normalize_source(source: str) -> str | int:
    return int(source) if source.isdigit() else source


if __name__ == "__main__":
    args = parse_args()
    total = collect_plate_sequences(
        source=normalize_source(args.source),
        model_path=args.model,
        output_dir=Path(args.output_dir),
        labels=args.labels.split(","),
        sample_stride=args.sample_stride,
        min_confidence=args.min_confidence,
        max_frames=args.max_frames,
    )
    print(f"Crops guardados: {total}")
