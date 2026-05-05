from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


KOKORO_ASSETS = {
    "int8": {
        "model_name": "kokoro-v1.0.int8.onnx",
        "model_url": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.int8.onnx",
        "voices_name": "voices-v1.0.bin",
        "voices_url": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin",
    },
    "fp16": {
        "model_name": "kokoro-v1.0.fp16.onnx",
        "model_url": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.fp16.onnx",
        "voices_name": "voices-v1.0.bin",
        "voices_url": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin",
    },
    "full": {
        "model_name": "kokoro-v1.0.onnx",
        "model_url": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx",
        "voices_name": "voices-v1.0.bin",
        "voices_url": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin",
    },
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Descarga modelos Kokoro ONNX locales para TTS de RestaurIA."
    )
    parser.add_argument("--variant", choices=tuple(KOKORO_ASSETS), default="int8")
    parser.add_argument("--output-dir", type=Path, default=Path("models/checkpoints"))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    asset = KOKORO_ASSETS[args.variant]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    model_path = args.output_dir / str(asset["model_name"])
    voices_path = args.output_dir / str(asset["voices_name"])

    _download(str(asset["model_url"]), model_path, force=args.force)
    _download(str(asset["voices_url"]), voices_path, force=args.force)

    print("Kokoro TTS listo:")
    print(f"- modelo: {model_path}")
    print(f"- voces:  {voices_path}")
    if args.variant != "int8":
        print("Nota: para portatil CPU se recomienda empezar por --variant int8.")


def _download(url: str, path: Path, *, force: bool) -> None:
    if path.exists() and not force:
        print(f"Ya existe, no se descarga: {path}")
        return
    print(f"Descargando {path.name}...")
    with urllib.request.urlopen(url) as response:
        total = int(response.headers.get("Content-Length", "0"))
        downloaded = 0
        with path.open("wb") as output:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded * 100 / total
                    print(f"\r{pct:5.1f}% {downloaded / 1024 / 1024:7.1f} MB", end="")
    print()


if __name__ == "__main__":
    main()
