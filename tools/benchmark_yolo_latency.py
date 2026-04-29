from __future__ import annotations

import argparse
import statistics
import time
from pathlib import Path

import numpy as np
from services.vision.yolo_detector import UltralyticsYoloDetector, YoloDetectorConfig


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Mide latencia local de YOLO en CPU para defender decisiones de rendimiento."
    )
    parser.add_argument("--model", default="yolo11n.pt")
    parser.add_argument(
        "--image",
        default="",
        help="Imagen local. Si se omite usa frame sintético.",
    )
    parser.add_argument("--image-size", type=int, default=320)
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--runs", type=int, default=20)
    parser.add_argument("--confidence", type=float, default=0.25)
    parser.add_argument("--max-detections", type=int, default=30)
    return parser.parse_args()


def benchmark_latency(args: argparse.Namespace) -> dict[str, float]:
    if args.runs <= 0:
        raise ValueError("runs must be positive.")
    if args.warmup < 0:
        raise ValueError("warmup must be >= 0.")

    frame = load_frame(args.image)
    detector = UltralyticsYoloDetector(
        YoloDetectorConfig(
            model_path=args.model,
            confidence_threshold=args.confidence,
            image_size=args.image_size,
            max_detections=args.max_detections,
        )
    )

    for _ in range(args.warmup):
        detector.detect(frame)

    latencies_ms: list[float] = []
    for _ in range(args.runs):
        started = time.perf_counter()
        detector.detect(frame)
        latencies_ms.append((time.perf_counter() - started) * 1000)

    return {
        "mean_ms": statistics.fmean(latencies_ms),
        "p50_ms": statistics.median(latencies_ms),
        "p95_ms": percentile(latencies_ms, 0.95),
        "min_ms": min(latencies_ms),
        "max_ms": max(latencies_ms),
        "fps_mean": 1000 / statistics.fmean(latencies_ms),
    }


def load_frame(image_path: str) -> np.ndarray:
    if not image_path:
        return np.zeros((480, 640, 3), dtype=np.uint8)

    try:
        import cv2
    except ModuleNotFoundError as exc:
        raise RuntimeError("OpenCV es necesario para cargar imágenes.") from exc

    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"No existe la imagen: {path}")
    frame = cv2.imread(str(path))
    if frame is None:
        raise RuntimeError(f"No se pudo leer la imagen: {path}")
    return frame


def percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * quantile)))
    return ordered[index]


if __name__ == "__main__":
    metrics = benchmark_latency(parse_args())
    for key, value in metrics.items():
        print(f"{key}: {value:.2f}")
