from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


PIPER_VOICES = {
    "davefx": {
        "model_name": "es_ES-davefx-medium.onnx",
        "config_name": "es_ES-davefx-medium.onnx.json",
        "base_url": (
            "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/davefx/medium"
        ),
    },
    "sharvard": {
        "model_name": "es_ES-sharvard-medium.onnx",
        "config_name": "es_ES-sharvard-medium.onnx.json",
        "base_url": (
            "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/sharvard/medium"
        ),
    },
    "carlfm": {
        "model_name": "es_ES-carlfm-x_low.onnx",
        "config_name": "es_ES-carlfm-x_low.onnx.json",
        "base_url": (
            "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/carlfm/x_low"
        ),
    },
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Descarga voces Piper es_ES locales para TTS de RestaurIA."
    )
    parser.add_argument("--voice", choices=tuple(PIPER_VOICES), default="davefx")
    parser.add_argument("--output-dir", type=Path, default=Path("models/checkpoints/piper"))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    asset = PIPER_VOICES[args.voice]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    model_path = args.output_dir / str(asset["model_name"])
    config_path = args.output_dir / str(asset["config_name"])
    base_url = str(asset["base_url"])

    _download(f"{base_url}/{asset['model_name']}", model_path, force=args.force)
    _download(f"{base_url}/{asset['config_name']}", config_path, force=args.force)

    print("Piper TTS listo:")
    print(f"- voz:    {args.voice}")
    print(f"- modelo: {model_path}")
    print(f"- config: {config_path}")


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
