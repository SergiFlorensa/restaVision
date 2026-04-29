from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fine-tuning YOLO para detectar plate_empty y plate_full en RestaurIA."
    )
    parser.add_argument("--data", required=True, help="Ruta a dataset.yaml en formato YOLO detect.")
    parser.add_argument("--model", default="yolo11n.pt", help="Modelo base.")
    parser.add_argument("--project", default="runs/restauria_plate_states")
    parser.add_argument("--name", default="yolo11n_plate_states")
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--patience", type=int, default=10)
    parser.add_argument("--batch", type=int, default=4)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--export-openvino", action="store_true")
    return parser.parse_args()


def train_plate_state_detector(args: argparse.Namespace) -> Path:
    try:
        from ultralytics import YOLO
    except ModuleNotFoundError as exc:
        raise RuntimeError("Instala requirements/ml.txt para entrenar YOLO.") from exc

    data_path = Path(args.data)
    if not data_path.exists():
        raise FileNotFoundError(f"No existe el dataset YAML: {data_path}")

    model = YOLO(args.model)
    results = model.train(
        data=str(data_path),
        epochs=args.epochs,
        patience=args.patience,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        optimizer="AdamW",
        lr0=1e-3,
        weight_decay=0.01,
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        degrees=8.0,
        translate=0.08,
        scale=0.35,
        fliplr=0.5,
        flipud=0.0,
        mosaic=0.4,
        project=args.project,
        name=args.name,
        exist_ok=True,
    )
    save_dir = Path(results.save_dir)

    if args.export_openvino:
        best_model = save_dir / "weights" / "best.pt"
        if not best_model.exists():
            raise FileNotFoundError(f"No se encontró el modelo entrenado: {best_model}")
        YOLO(str(best_model)).export(format="openvino", imgsz=args.imgsz, dynamic=False)

    return save_dir


if __name__ == "__main__":
    output_dir = train_plate_state_detector(parse_args())
    print(f"Entrenamiento finalizado: {output_dir}")
