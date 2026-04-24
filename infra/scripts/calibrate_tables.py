from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from services.vision.calibration import build_table_calibration, save_calibrations
from services.vision.geometry import FrameResolution


@dataclass(slots=True)
class PointSelector:
    window_name: str
    display_scale: float = 1.0
    points: list[list[float]] | None = None
    _base_frame: np.ndarray | None = None
    _preview_frame: np.ndarray | None = None

    def start(self, frame: np.ndarray) -> None:
        self.points = []
        self._base_frame = frame.copy()
        self._preview_frame = self._resize_for_display(self._base_frame)
        cv2 = _load_cv2()
        cv2.imshow(self.window_name, self._preview_frame)
        cv2.setMouseCallback(self.window_name, self._on_mouse)

    def undo(self) -> None:
        if not self.points:
            return
        self.points.pop()
        self._redraw()

    def reset(self) -> None:
        self.points = []
        self._redraw()

    def _on_mouse(self, event: int, x: int, y: int, flags: int, param: object) -> None:
        cv2 = _load_cv2()
        if event != cv2.EVENT_LBUTTONDOWN or self.points is None:
            return
        if len(self.points) >= 4:
            return
        original_x = x / self.display_scale
        original_y = y / self.display_scale
        self.points.append([original_x, original_y])
        self._redraw()

    def _redraw(self) -> None:
        if self._base_frame is None:
            return
        cv2 = _load_cv2()
        preview = self._resize_for_display(self._base_frame)
        scaled_points = [
            (round(point[0] * self.display_scale), round(point[1] * self.display_scale))
            for point in (self.points or [])
        ]
        for index, point in enumerate(scaled_points):
            cv2.circle(preview, point, 5, (0, 255, 0), -1)
            cv2.putText(
                preview,
                str(index + 1),
                (point[0] + 8, point[1] - 8),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2,
            )
        for first, second in zip(scaled_points, scaled_points[1:], strict=False):
            cv2.line(preview, first, second, (255, 0, 0), 2)
        if len(scaled_points) == 4:
            cv2.line(preview, scaled_points[-1], scaled_points[0], (255, 0, 0), 2)
        self._preview_frame = preview
        cv2.imshow(self.window_name, preview)

    def _resize_for_display(self, frame: np.ndarray) -> np.ndarray:
        if self.display_scale == 1.0:
            return frame.copy()
        cv2 = _load_cv2()
        return cv2.resize(
            frame,
            None,
            fx=self.display_scale,
            fy=self.display_scale,
            interpolation=cv2.INTER_AREA,
        )


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    cv2 = _load_cv2()
    source: int | str = args.source
    if isinstance(source, str) and source.isdigit():
        source = int(source)

    capture = cv2.VideoCapture(source)
    if not capture.isOpened():
        print(f"No se pudo abrir la fuente de video: {args.source}", file=sys.stderr)
        return 1

    ok, frame = capture.read()
    capture.release()
    if not ok or frame is None:
        print("No se pudo leer un frame de calibracion.", file=sys.stderr)
        return 1

    frame_resolution = FrameResolution(width=int(frame.shape[1]), height=int(frame.shape[0]))
    window_name = "RestaurIA - calibracion de mesas"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    selector = PointSelector(window_name=window_name, display_scale=args.display_scale)

    calibrations = []
    for table_id in args.table:
        print(
            f"\nMesa {table_id}: marca 4 esquinas. "
            "Orden recomendado: arriba-izquierda, arriba-derecha, abajo-derecha, abajo-izquierda."
        )
        print("Teclas: Enter/espacio guardar mesa, u deshacer, r reiniciar, q/Esc salir.")
        selector.start(frame)

        while True:
            key = cv2.waitKey(20) & 0xFF
            if key in {ord("q"), 27}:
                cv2.destroyWindow(window_name)
                return 130
            if key == ord("u"):
                selector.undo()
            if key == ord("r"):
                selector.reset()
            if key in {13, 32}:
                if selector.points is None or len(selector.points) != 4:
                    print("Debes marcar exactamente 4 puntos antes de guardar.")
                    continue
                calibration = build_table_calibration(
                    table_id=table_id,
                    source_points=selector.points,
                    frame_resolution=frame_resolution,
                    target_width=args.target_width,
                    target_height=args.target_height,
                    order_points=not args.keep_click_order,
                )
                calibrations.append(calibration)
                print(f"Mesa {table_id} calibrada: {calibration.source_points}")
                break

    cv2.destroyWindow(window_name)
    save_calibrations(args.output, calibrations)
    print(f"\nCalibracion guardada en: {Path(args.output).resolve()}")
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Marca 4 esquinas por mesa y guarda homografias RestaurIA en JSON.",
    )
    parser.add_argument("--source", default="0", help="Webcam index, ruta de video o URL RTSP.")
    parser.add_argument(
        "--table",
        action="append",
        required=True,
        help="ID de mesa a calibrar. Repetir para varias mesas.",
    )
    parser.add_argument(
        "--output",
        default="data/processed/table_calibrations.json",
        help="Ruta JSON de salida.",
    )
    parser.add_argument("--target-width", type=int, default=500)
    parser.add_argument("--target-height", type=int, default=500)
    parser.add_argument(
        "--display-scale",
        type=float,
        default=1.0,
        help="Escala de visualizacion; los clics se remapean al frame original.",
    )
    parser.add_argument(
        "--keep-click-order",
        action="store_true",
        help="No reordenar puntos automaticamente; usar exactamente el orden de clic.",
    )
    args = parser.parse_args(argv)
    if args.display_scale <= 0:
        parser.error("--display-scale must be greater than 0.")
    return args


def _load_cv2() -> Any:
    try:
        import cv2
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "OpenCV es necesario. Instala las dependencias de requirements/ml.txt."
        ) from exc
    return cv2


if __name__ == "__main__":
    raise SystemExit(main())
