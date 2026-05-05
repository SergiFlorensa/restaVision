from __future__ import annotations

import base64
import math
import re
import shutil
import subprocess
import sys
import wave
from dataclasses import dataclass, field, replace
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from typing import Protocol

DEFAULT_KOKORO_MODEL_PATH = "models/checkpoints/kokoro-v1.0.int8.onnx"
DEFAULT_KOKORO_VOICES_PATH = "models/checkpoints/voices-v1.0.bin"
DEFAULT_KOKORO_SPANISH_VOICE = "ef_dora"
DEFAULT_PIPER_MODEL_PATH = "models/checkpoints/piper/es_ES-davefx-medium.onnx"
DEFAULT_PIPER_CONFIG_PATH = "models/checkpoints/piper/es_ES-davefx-medium.onnx.json"
DEFAULT_PIPER_SPANISH_VOICE = "es_ES-davefx-medium"
DEFAULT_VOICE_PROFILE = "default"
CASTILIAN_NEUTRAL_VOICE_PROMPT = """\
Habla siempre en espanol peninsular estandar, con pronunciacion clara,
profesional y natural de Espana. Usa ritmo medio-lento, cadencia sobria,
vocales limpias, distincion peninsular entre s y z/c, y expresividad controlada.
Agrupa las palabras por sentido. No enfatices articulos, preposiciones,
conjunciones, posesivos antepuestos ni pronombres atonos salvo contraste.
Enfatiza solo datos operativos: hora, fecha, nombre, numero de personas,
telefono, alergias, cambios, cancelaciones y decisiones. Cierra las afirmaciones
con cadencia descendente; deja tono suspendido si la frase continua; usa subida
moderada en preguntas de confirmacion y tono serio, calmado y mas lento ante
alergias, quejas o errores.
"""

VOICE_PROFILE_ALIASES = {
    "castellano": "castilian_neutral",
    "castellano_neutro": "castilian_neutral",
    "es_es": "castilian_neutral",
    "peninsular": "castilian_neutral",
    "spain": "castilian_neutral",
}

VOICE_RENDERING_PROFILES: dict[str, dict[str, object]] = {
    "default": {
        "description": "Perfil neutro sin ajustes extra sobre el texto del agente.",
        "speed_multiplier": 1.0,
    },
    "castilian_neutral": {
        "description": (
            "Perfil de restaurante para castellano neutro de Espana: frases cortas, "
            "cadencia sobria y pronunciacion mas explicita en datos operativos."
        ),
        "speed_multiplier": 0.94,
        "system_prompt": CASTILIAN_NEUTRAL_VOICE_PROMPT,
    },
}


@dataclass(frozen=True, slots=True)
class TextToSpeechConfig:
    engine: str
    model_path: str | None = None
    voices_path: str | None = None
    voice: str | None = None
    language: str = "es"
    speed: float = 1.0
    style: str = "auto"
    voice_profile: str = DEFAULT_VOICE_PROFILE
    timeout_seconds: float = 30.0


@dataclass(frozen=True, slots=True)
class TextToSpeechResult:
    text: str
    engine: str
    voice: str | None
    output_path: str
    sample_rate_hz: int | None
    duration_ms: int | None
    synthesis_ms: int
    realtime_factor: float | None = None
    metadata: dict[str, object] = field(default_factory=dict)


class TextToSpeechAdapter(Protocol):
    config: TextToSpeechConfig

    def synthesize_to_file(self, text: str, output_path: str | Path) -> TextToSpeechResult: ...


class MockTextToSpeechAdapter:
    def __init__(
        self,
        *,
        sample_rate_hz: int = 16000,
        style: str = "auto",
        voice_profile: str = DEFAULT_VOICE_PROFILE,
    ) -> None:
        self.config = TextToSpeechConfig(
            engine="mock",
            voice="mock",
            style=style,
            voice_profile=_normalize_voice_profile(voice_profile),
        )
        self._sample_rate_hz = sample_rate_hz

    def synthesize_to_file(self, text: str, output_path: str | Path) -> TextToSpeechResult:
        started = perf_counter()
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        duration_seconds = min(2.4, max(0.45, len(text.split()) * 0.12))
        sample_count = int(self._sample_rate_hz * duration_seconds)
        samples = [
            0.16 * math.sin(2 * math.pi * 220 * index / self._sample_rate_hz)
            for index in range(sample_count)
        ]
        _write_float_wav(path, samples, self._sample_rate_hz)
        duration_ms = int(round(duration_seconds * 1000))
        return TextToSpeechResult(
            text=prepare_text_for_tts(
                text,
                style=self.config.style,
                voice_profile=self.config.voice_profile,
            ),
            engine=self.config.engine,
            voice=self.config.voice,
            output_path=str(path),
            sample_rate_hz=self._sample_rate_hz,
            duration_ms=duration_ms,
            synthesis_ms=_elapsed_ms(started),
            realtime_factor=None,
            metadata={"synthetic_tone": True},
        )


class CachedTextToSpeechAdapter:
    """File cache for deterministic agent replies.

    Restaurant calls reuse a small set of prompts. Caching those prompts makes a
    heavy natural TTS engine viable on CPU without changing the agent logic.
    """

    def __init__(self, base_adapter: TextToSpeechAdapter, cache_dir: str | Path) -> None:
        self.config = base_adapter.config
        self._base_adapter = base_adapter
        self._cache_dir = Path(cache_dir)

    def synthesize_to_file(self, text: str, output_path: str | Path) -> TextToSpeechResult:
        started = perf_counter()
        prepared_text = prepare_text_for_tts(
            text,
            style=self.config.style,
            voice_profile=self.config.voice_profile,
        )
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = self._cache_dir / f"{_tts_cache_key(self.config, prepared_text)}.wav"

        if cache_path.exists():
            if output.resolve() != cache_path.resolve():
                shutil.copyfile(cache_path, output)
            duration_ms, sample_rate_hz = _wav_duration(output)
            synthesis_ms = _elapsed_ms(started)
            realtime_factor = (
                round(synthesis_ms / duration_ms, 4) if duration_ms and duration_ms > 0 else None
            )
            return TextToSpeechResult(
                text=prepared_text,
                engine=self.config.engine,
                voice=self.config.voice,
                output_path=str(output),
                sample_rate_hz=sample_rate_hz,
                duration_ms=duration_ms,
                synthesis_ms=synthesis_ms,
                realtime_factor=realtime_factor,
                metadata={"cache_hit": True, "cache_path": str(cache_path)},
            )

        result = self._base_adapter.synthesize_to_file(prepared_text, cache_path)
        if output.resolve() != cache_path.resolve():
            shutil.copyfile(cache_path, output)
        synthesis_ms = _elapsed_ms(started)
        duration_ms, sample_rate_hz = _wav_duration(output)
        realtime_factor = (
            round(synthesis_ms / duration_ms, 4) if duration_ms and duration_ms > 0 else None
        )
        metadata = {
            **result.metadata,
            "cache_hit": False,
            "cache_path": str(cache_path),
            "raw_synthesis_ms": result.synthesis_ms,
        }
        return replace(
            result,
            output_path=str(output),
            sample_rate_hz=sample_rate_hz,
            duration_ms=duration_ms,
            synthesis_ms=synthesis_ms,
            realtime_factor=realtime_factor,
            metadata=metadata,
        )


class KokoroOnnxTextToSpeechAdapter:
    """Local Kokoro ONNX adapter for advanced CPU-friendly TTS."""

    def __init__(self, config: TextToSpeechConfig) -> None:
        if not config.model_path:
            raise ValueError("Kokoro ONNX adapter requires model_path.")
        if not config.voices_path:
            raise ValueError("Kokoro ONNX adapter requires voices_path.")
        self.config = config
        self._engine: object | None = None

    def _get_engine(self) -> object:
        if self._engine is None:
            try:
                from kokoro_onnx import Kokoro
            except ModuleNotFoundError as exc:
                raise RuntimeError(
                    "kokoro-onnx is not installed. Install requirements/audio.txt."
                ) from exc
            model_path = Path(str(self.config.model_path))
            voices_path = Path(str(self.config.voices_path))
            if not model_path.exists():
                raise FileNotFoundError(
                    f"Kokoro model not found: {model_path}. "
                    "Run tools/download_kokoro_tts_assets.py first."
                )
            if not voices_path.exists():
                raise FileNotFoundError(
                    f"Kokoro voices file not found: {voices_path}. "
                    "Run tools/download_kokoro_tts_assets.py first."
                )
            self._engine = Kokoro(str(model_path), str(voices_path))
        return self._engine

    def synthesize_to_file(self, text: str, output_path: str | Path) -> TextToSpeechResult:
        started = perf_counter()
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        prepared_text = prepare_text_for_tts(
            text,
            style=self.config.style,
            voice_profile=self.config.voice_profile,
        )
        engine = self._get_engine()
        voice = self.config.voice or DEFAULT_KOKORO_SPANISH_VOICE
        samples, sample_rate_hz = engine.create(
            prepared_text,
            voice=voice,
            speed=self.config.speed,
            lang=self.config.language,
        )
        duration_ms = _write_float_wav(path, samples, int(sample_rate_hz))
        synthesis_ms = _elapsed_ms(started)
        realtime_factor = (
            round(synthesis_ms / duration_ms, 4) if duration_ms and duration_ms > 0 else None
        )
        return TextToSpeechResult(
            text=prepared_text,
            engine=self.config.engine,
            voice=voice,
            output_path=str(path),
            sample_rate_hz=int(sample_rate_hz),
            duration_ms=duration_ms,
            synthesis_ms=synthesis_ms,
            realtime_factor=realtime_factor,
            metadata={
                "model_path": str(self.config.model_path),
                "voices_path": str(self.config.voices_path),
                "language": self.config.language,
                "speed": self.config.speed,
                "voice_profile": self.config.voice_profile,
            },
        )


class PiperTextToSpeechAdapter:
    """Local Piper adapter for real es_ES voices."""

    def __init__(self, config: TextToSpeechConfig) -> None:
        if not config.model_path:
            raise ValueError("Piper adapter requires model_path.")
        if not config.voices_path:
            raise ValueError("Piper adapter requires voices_path/config path.")
        self.config = config

    def synthesize_to_file(self, text: str, output_path: str | Path) -> TextToSpeechResult:
        started = perf_counter()
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        prepared_text = prepare_text_for_tts(
            text,
            style=self.config.style,
            voice_profile=self.config.voice_profile,
        )
        model_path = Path(str(self.config.model_path))
        config_path = Path(str(self.config.voices_path))
        if not model_path.exists():
            raise FileNotFoundError(
                f"Piper model not found: {model_path}. "
                "Run tools/download_piper_tts_assets.py first."
            )
        if not config_path.exists():
            raise FileNotFoundError(
                f"Piper config not found: {config_path}. "
                "Run tools/download_piper_tts_assets.py first."
            )

        completed = subprocess.run(
            [
                _piper_binary_path(),
                "--model",
                str(model_path),
                "--config",
                str(config_path),
                "--output-file",
                str(path),
                "--length-scale",
                f"{_piper_length_scale_from_speed(self.config.speed):.3f}",
                "--sentence-silence",
                "0.18",
            ],
            input=prepared_text,
            capture_output=True,
            check=False,
            text=True,
            timeout=self.config.timeout_seconds,
        )
        if completed.returncode != 0:
            output = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
            raise RuntimeError(f"Piper failed with code {completed.returncode}: {output}")

        duration_ms, sample_rate_hz = _wav_duration(path)
        synthesis_ms = _elapsed_ms(started)
        realtime_factor = (
            round(synthesis_ms / duration_ms, 4) if duration_ms and duration_ms > 0 else None
        )
        return TextToSpeechResult(
            text=prepared_text,
            engine=self.config.engine,
            voice=self.config.voice,
            output_path=str(path),
            sample_rate_hz=sample_rate_hz,
            duration_ms=duration_ms,
            synthesis_ms=synthesis_ms,
            realtime_factor=realtime_factor,
            metadata={
                "model_path": str(model_path),
                "config_path": str(config_path),
                "language": self.config.language,
                "speed": self.config.speed,
                "voice_profile": self.config.voice_profile,
                "length_scale": _piper_length_scale_from_speed(self.config.speed),
            },
        )


class WindowsSapiTextToSpeechAdapter:
    """Windows local fallback using the built-in SAPI synthesizer."""

    def __init__(self, config: TextToSpeechConfig) -> None:
        self.config = config

    def synthesize_to_file(self, text: str, output_path: str | Path) -> TextToSpeechResult:
        started = perf_counter()
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        prepared_text = prepare_text_for_tts(
            text,
            style=self.config.style,
            voice_profile=self.config.voice_profile,
        )
        script = _windows_sapi_script(
            prepared_text,
            path,
            voice=self.config.voice,
            rate=_speech_rate_from_speed(self.config.speed),
        )
        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-EncodedCommand",
                _encode_powershell(script),
            ],
            capture_output=True,
            check=False,
            text=True,
            timeout=self.config.timeout_seconds,
        )
        if completed.returncode != 0:
            output = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
            raise RuntimeError(f"Windows SAPI failed with code {completed.returncode}: {output}")
        duration_ms, sample_rate_hz = _wav_duration(path)
        synthesis_ms = _elapsed_ms(started)
        realtime_factor = (
            round(synthesis_ms / duration_ms, 4) if duration_ms and duration_ms > 0 else None
        )
        return TextToSpeechResult(
            text=prepared_text,
            engine=self.config.engine,
            voice=self.config.voice,
            output_path=str(path),
            sample_rate_hz=sample_rate_hz,
            duration_ms=duration_ms,
            synthesis_ms=synthesis_ms,
            realtime_factor=realtime_factor,
            metadata={
                "provider": "System.Speech.Synthesis",
                "language": self.config.language,
                "speed": self.config.speed,
                "voice_profile": self.config.voice_profile,
            },
        )


def build_tts_adapter(
    engine: str,
    *,
    model_path: str | None = None,
    voices_path: str | None = None,
    voice: str | None = None,
    language: str = "es",
    speed: float = 1.0,
    style: str = "auto",
    voice_profile: str = DEFAULT_VOICE_PROFILE,
    timeout_seconds: float = 30.0,
    cache_dir: str | Path | None = None,
) -> TextToSpeechAdapter:
    normalized_engine = engine.strip().lower()
    normalized_profile = _normalize_voice_profile(voice_profile)
    profiled_speed = _apply_voice_profile_speed(speed, normalized_profile)
    if normalized_engine == "mock":
        adapter: TextToSpeechAdapter = MockTextToSpeechAdapter(
            style=style,
            voice_profile=normalized_profile,
        )
        return _with_cache(adapter, cache_dir)
    if normalized_engine in {"kokoro", "kokoro_onnx", "kokoro-onnx"}:
        adapter = KokoroOnnxTextToSpeechAdapter(
            TextToSpeechConfig(
                engine="kokoro_onnx",
                model_path=model_path or DEFAULT_KOKORO_MODEL_PATH,
                voices_path=voices_path or DEFAULT_KOKORO_VOICES_PATH,
                voice=voice or DEFAULT_KOKORO_SPANISH_VOICE,
                language=language,
                speed=profiled_speed,
                style=style,
                voice_profile=normalized_profile,
                timeout_seconds=timeout_seconds,
            )
        )
        return _with_cache(adapter, cache_dir)
    if normalized_engine == "piper":
        adapter = PiperTextToSpeechAdapter(
            TextToSpeechConfig(
                engine="piper",
                model_path=model_path or DEFAULT_PIPER_MODEL_PATH,
                voices_path=voices_path or DEFAULT_PIPER_CONFIG_PATH,
                voice=voice or DEFAULT_PIPER_SPANISH_VOICE,
                language=language,
                speed=profiled_speed,
                style=style,
                voice_profile=normalized_profile,
                timeout_seconds=timeout_seconds,
            )
        )
        return _with_cache(adapter, cache_dir)
    if normalized_engine in {"windows_sapi", "sapi", "windows"}:
        adapter = WindowsSapiTextToSpeechAdapter(
            TextToSpeechConfig(
                engine="windows_sapi",
                voice=voice,
                language=language,
                speed=profiled_speed,
                style=style,
                voice_profile=normalized_profile,
                timeout_seconds=timeout_seconds,
            )
        )
        return _with_cache(adapter, cache_dir)
    raise ValueError(f"Unsupported TTS engine: {engine}")


def prepare_text_for_tts(
    text: str,
    *,
    style: str = "auto",
    voice_profile: str = DEFAULT_VOICE_PROFILE,
) -> str:
    prepared = " ".join(text.strip().split())
    if not prepared:
        return ""
    normalized_profile = _normalize_voice_profile(voice_profile)
    prepared = _normalize_spanish_tts_text(prepared)
    prepared = _normalize_structured_speech(prepared)
    prepared = _apply_voice_profile_text(prepared, normalized_profile)
    prepared = _apply_prosody_style(prepared, style=style)
    if prepared[-1] not in ".?!":
        prepared = f"{prepared}."
    prepared = _ensure_spanish_question_marks(prepared)
    prepared = _ensure_spanish_exclamation_marks(prepared)
    prepared = _capitalize_sentence_starts(prepared)
    return _clean_tts_spacing(prepared)


def _normalize_voice_profile(voice_profile: str | None) -> str:
    normalized = (voice_profile or DEFAULT_VOICE_PROFILE).strip().lower()
    normalized = VOICE_PROFILE_ALIASES.get(normalized, normalized)
    if normalized not in VOICE_RENDERING_PROFILES:
        allowed = ", ".join(sorted(VOICE_RENDERING_PROFILES))
        raise ValueError(f"Unsupported voice profile: {voice_profile}. Allowed: {allowed}")
    return normalized


def _apply_voice_profile_speed(speed: float, voice_profile: str) -> float:
    multiplier = float(VOICE_RENDERING_PROFILES[voice_profile]["speed_multiplier"])
    return round(speed * multiplier, 3)


def _apply_voice_profile_text(text: str, voice_profile: str) -> str:
    if voice_profile != "castilian_neutral":
        return text
    prepared = _normalize_castilian_restaurant_lexicon(text)
    prepared = _add_castilian_service_cadence(prepared)
    prepared = _add_castilian_information_focus(prepared)
    return prepared


def _normalize_spanish_tts_text(text: str) -> str:
    replacements = {
        "A que": "A qué",
        "a que": "a qué",
        "gustaria": "gustaría",
        "telefono": "teléfono",
        "Telefono": "Teléfono",
        "Si,": "Sí,",
        "si,": "sí,",
        "politica": "política",
        "direccion": "dirección",
        "informacion": "información",
        "situacion": "situación",
        "cancelacion": "cancelación",
        "facturacion": "facturación",
        "curriculum": "currículum",
        "celiaco": "celíaco",
        "celiaca": "celíaca",
        "alergeno": "alérgeno",
        "alergenos": "alérgenos",
    }
    normalized = text
    for source, target in replacements.items():
        if any(not char.isalnum() and char != " " for char in source):
            normalized = normalized.replace(source, target)
            continue
        normalized = re.sub(rf"\b{re.escape(source)}\b", target, normalized)
    return normalized


def _normalize_castilian_restaurant_lexicon(text: str) -> str:
    replacements = {
        r"\bok\b": "de acuerdo",
        r"\bvale\b": "de acuerdo",
        r"\bceliaco\b": "celíaco",
        r"\bceliaca\b": "celíaca",
        r"\bparking\b": "aparcamiento",
        r"\bteléfono móvil\b": "móvil",
        r"\btelefono movil\b": "móvil",
        r"\bcel\b": "móvil",
    }
    normalized = text
    for pattern, replacement in replacements.items():
        normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
    return normalized


def _add_castilian_service_cadence(text: str) -> str:
    cadenced = text
    cadenced = re.sub(
        r"\bPiemontesa Paseo de Prim,\s*diga\b",
        "Piemontesa Paseo de Prim, diga",
        cadenced,
        flags=re.IGNORECASE,
    )
    cadenced = re.sub(
        r"\bla\s+Piemontesa\s+de\s+Passeig\s+de\s+Prim\b",
        "la Piemontesa de Passeig de Prim",
        cadenced,
        flags=re.IGNORECASE,
    )
    cadenced = re.sub(
        r"\b(Perfecto|Disculpe|Entiendo|De acuerdo)\s+",
        r"\1. ",
        cadenced,
    )
    cadenced = re.sub(
        r"\b(le gustaria|le gustaría)\s+la\s+reserva\b",
        "le gustaría hacer la reserva",
        cadenced,
        flags=re.IGNORECASE,
    )
    cadenced = re.sub(
        r"\b(me dice|me confirma)\s+el\s+nombre\b",
        r"\1 su nombre",
        cadenced,
        flags=re.IGNORECASE,
    )
    return cadenced


def _add_castilian_information_focus(text: str) -> str:
    focused = text
    focused = re.sub(
        r"\breserva confirmada para\b",
        "reserva confirmada: para",
        focused,
        flags=re.IGNORECASE,
    )
    focused = re.sub(
        r"\b(tel[eé]fono|m[oó]vil)\s+((?:[a-záéíóúñ]+(?:\s|,\s*)?){3,})",
        lambda match: f"{match.group(1)}: {match.group(2).strip()}",
        focused,
        flags=re.IGNORECASE,
    )
    focused = re.sub(
        r"\b(\w+\s+(?:personas?|comensales?))\s+(el\s+\d{1,2}\s+de\s+\w+)",
        r"\1, \2",
        focused,
        flags=re.IGNORECASE,
    )
    focused = re.sub(
        r"\b(\d{1,2}\s+de\s+\w+)\s+(a\s+las\s+)",
        r"\1, \2",
        focused,
        flags=re.IGNORECASE,
    )
    focused = re.sub(
        r"\b(nombre|hora|fecha|alergia|al[eé]rgeno|cancelaci[oó]n|cambio)\s+(confirmad[ao])\b",
        r"\1 \2",
        focused,
        flags=re.IGNORECASE,
    )
    return focused


def _normalize_structured_speech(text: str) -> str:
    normalized = _normalize_dates(text)
    normalized = _normalize_times(normalized)
    normalized = _normalize_phone_numbers(normalized)
    normalized = _normalize_party_size(normalized)
    return normalized


def _normalize_dates(text: str) -> str:
    month_names = {
        1: "enero",
        2: "febrero",
        3: "marzo",
        4: "abril",
        5: "mayo",
        6: "junio",
        7: "julio",
        8: "agosto",
        9: "septiembre",
        10: "octubre",
        11: "noviembre",
        12: "diciembre",
    }

    def replace_date(match: re.Match[str]) -> str:
        day = int(match.group(1))
        month = int(match.group(2))
        if not 1 <= month <= 12:
            return match.group(0)
        return f"{day} de {month_names[month]}"

    return re.sub(r"\b(\d{1,2})/(\d{1,2})/\d{4}\b", replace_date, text)


def _normalize_times(text: str) -> str:
    text = re.sub(
        r"\ba\s+las\s+([01]?\d|2[0-3]):([0-5]\d)\b",
        lambda match: f"a {_time_for_speech(int(match.group(1)), int(match.group(2)))}",
        text,
        flags=re.IGNORECASE,
    )

    def replace_time(match: re.Match[str]) -> str:
        hour = int(match.group(1))
        minute = int(match.group(2))
        if hour > 23 or minute > 59:
            return match.group(0)
        return _time_for_speech(hour, minute)

    return re.sub(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", replace_time, text)


def _time_for_speech(hour: int, minute: int) -> str:
    display_hour = hour % 12 or 12
    hour_text = _number_for_speech(display_hour)
    if minute == 0:
        base = f"las {hour_text} en punto"
    elif minute == 15:
        base = f"las {hour_text} y cuarto"
    elif minute == 30:
        base = f"las {hour_text} y media"
    elif minute == 45:
        next_hour = (display_hour % 12) + 1
        base = f"las {_number_for_speech(next_hour)} menos cuarto"
    else:
        base = f"las {hour_text} y {_number_for_speech(minute)}"

    if 6 <= hour < 13:
        return f"{base} de la mañana"
    if 13 <= hour < 20:
        return f"{base} de la tarde"
    return f"{base} de la noche"


def _normalize_phone_numbers(text: str) -> str:
    def replace_phone(match: re.Match[str]) -> str:
        digits = re.sub(r"\D", "", match.group(0))
        if len(digits) < 9 or len(digits) > 12:
            return match.group(0)
        grouped_digits = [digits[index : index + 3] for index in range(0, len(digits), 3)]
        grouped_text = [
            " ".join(_digit_for_speech(digit) for digit in group) for group in grouped_digits
        ]
        return ", ".join(grouped_text)

    return re.sub(r"(?<!\d)(?:\d[\s-]?){9,12}(?!\d)", replace_phone, text)


def _normalize_party_size(text: str) -> str:
    return re.sub(
        r"\b(\d)\s+(personas?|comensales?)\b",
        lambda match: f"{_number_for_speech(int(match.group(1)))} {match.group(2)}",
        text,
        flags=re.IGNORECASE,
    )


def _apply_prosody_style(text: str, *, style: str) -> str:
    normalized_style = _infer_prosody_style(text) if style == "auto" else style
    lower = text.lower()

    if normalized_style == "repair":
        if not lower.startswith("disculpe.") and _is_repair_turn(lower):
            return f"Disculpe. {text}"
        return text

    if normalized_style == "confirmation" and lower.startswith("reserva confirmada"):
        return f"Perfecto. {text}"

    if normalized_style == "warm" and text.endswith("?") and "." not in lower:
        if not lower.startswith(("perfecto", "claro", "disculpe", "entiendo")):
            return f"Perfecto. {text}"

    if normalized_style == "serious" and "le paso con el encargado" in lower:
        if not lower.startswith(("entiendo.", "lamento")):
            return f"Entiendo. {text}"

    return text


def _infer_prosody_style(text: str) -> str:
    lower = text.lower()
    if _is_repair_turn(lower):
        return "repair"
    if any(
        token in lower
        for token in (
            "celíaco",
            "celiaco",
            "alergia",
            "alérgeno",
            "queja",
            "lamento",
            "le paso con el encargado",
        )
    ):
        return "serious"
    if lower.startswith(("reserva confirmada", "sí, puedo ofrecer", "si, puedo ofrecer")):
        return "confirmation"
    if text.endswith("?"):
        return "warm"
    return "neutral"


def _is_repair_turn(lower_text: str) -> bool:
    if "." in lower_text and not lower_text.startswith("disculpe."):
        return False
    return "no le he entendido" in lower_text or "puede repetirlo" in lower_text


def _ensure_spanish_question_marks(text: str) -> str:
    return re.sub(
        r"(^|(?<=[.!]\s))([^¿.!?][^.!?]*\?)",
        lambda match: f"{match.group(1)}¿{match.group(2)}",
        text,
    )


def _ensure_spanish_exclamation_marks(text: str) -> str:
    return re.sub(
        r"(^|(?<=[.?]\s))([^¡.!?][^.!?]*!)",
        lambda match: f"{match.group(1)}¡{match.group(2)}",
        text,
    )


def _clean_tts_spacing(text: str) -> str:
    cleaned = re.sub(r"\s+([,.?!])", r"\1", text)
    cleaned = re.sub(r"([¿¡])\s+", r"\1", cleaned)
    return re.sub(r"\s{2,}", " ", cleaned).strip()


def _capitalize_sentence_starts(text: str) -> str:
    return re.sub(
        r"(^|[.!?]\s+)([¿¡]?)([a-záéíóúñ])",
        lambda match: f"{match.group(1)}{match.group(2)}{match.group(3).upper()}",
        text,
    )


def _number_for_speech(number: int) -> str:
    numbers = {
        0: "cero",
        1: "una",
        2: "dos",
        3: "tres",
        4: "cuatro",
        5: "cinco",
        6: "seis",
        7: "siete",
        8: "ocho",
        9: "nueve",
        10: "diez",
        11: "once",
        12: "doce",
        13: "trece",
        14: "catorce",
        15: "quince",
        16: "dieciséis",
        17: "diecisiete",
        18: "dieciocho",
        19: "diecinueve",
        20: "veinte",
        21: "veintiuna",
        22: "veintidós",
        23: "veintitrés",
        24: "veinticuatro",
        25: "veinticinco",
        26: "veintiséis",
        27: "veintisiete",
        28: "veintiocho",
        29: "veintinueve",
        30: "treinta",
        31: "treinta y una",
        32: "treinta y dos",
        33: "treinta y tres",
        34: "treinta y cuatro",
        35: "treinta y cinco",
        36: "treinta y seis",
        37: "treinta y siete",
        38: "treinta y ocho",
        39: "treinta y nueve",
        40: "cuarenta",
        41: "cuarenta y una",
        42: "cuarenta y dos",
        43: "cuarenta y tres",
        44: "cuarenta y cuatro",
        45: "cuarenta y cinco",
        46: "cuarenta y seis",
        47: "cuarenta y siete",
        48: "cuarenta y ocho",
        49: "cuarenta y nueve",
        50: "cincuenta",
        51: "cincuenta y una",
        52: "cincuenta y dos",
        53: "cincuenta y tres",
        54: "cincuenta y cuatro",
        55: "cincuenta y cinco",
        56: "cincuenta y seis",
        57: "cincuenta y siete",
        58: "cincuenta y ocho",
        59: "cincuenta y nueve",
    }
    return numbers.get(number, str(number))


def _digit_for_speech(digit: str) -> str:
    digits = {
        "0": "cero",
        "1": "uno",
        "2": "dos",
        "3": "tres",
        "4": "cuatro",
        "5": "cinco",
        "6": "seis",
        "7": "siete",
        "8": "ocho",
        "9": "nueve",
    }
    return digits.get(digit, digit)


def _write_float_wav(path: Path, samples: object, sample_rate_hz: int) -> int:
    import numpy as np

    array = np.asarray(samples, dtype=np.float32)
    if array.ndim == 1:
        channels = 1
    elif array.ndim == 2:
        channels = int(array.shape[1])
    else:
        raise ValueError("TTS samples must be a 1D or 2D audio array.")
    clipped = np.clip(array, -1.0, 1.0)
    pcm = (clipped * 32767).astype("<i2").tobytes()
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate_hz)
        wav_file.writeframes(pcm)
    frame_count = array.shape[0]
    return int(round(frame_count * 1000 / sample_rate_hz))


def _with_cache(
    adapter: TextToSpeechAdapter,
    cache_dir: str | Path | None,
) -> TextToSpeechAdapter:
    if cache_dir is None:
        return adapter
    return CachedTextToSpeechAdapter(adapter, cache_dir)


def _tts_cache_key(config: TextToSpeechConfig, prepared_text: str) -> str:
    payload = "|".join(
        (
            config.engine,
            config.model_path or "",
            config.voices_path or "",
            config.voice or "",
            config.language,
            f"{config.speed:.3f}",
            config.style,
            config.voice_profile,
            prepared_text,
        )
    )
    return sha256(payload.encode("utf-8")).hexdigest()[:24]


def _wav_duration(path: Path) -> tuple[int | None, int | None]:
    if not path.exists():
        return None, None
    with wave.open(str(path), "rb") as wav_file:
        frame_count = wav_file.getnframes()
        sample_rate_hz = wav_file.getframerate()
    if sample_rate_hz <= 0:
        return None, None
    return int(round(frame_count * 1000 / sample_rate_hz)), sample_rate_hz


def _speech_rate_from_speed(speed: float) -> int:
    if speed < 0.85:
        return -2
    if speed > 1.15:
        return 2
    return 0


def _piper_length_scale_from_speed(speed: float) -> float:
    if speed <= 0:
        return 1.0
    return min(1.35, max(0.75, 1 / speed))


def _piper_binary_path() -> str:
    binary = shutil.which("piper") or shutil.which("piper.exe")
    if binary:
        return binary
    candidate = Path(sys.executable).with_name("piper.exe")
    if candidate.exists():
        return str(candidate)
    raise RuntimeError("piper executable not found. Install requirements/audio.txt.")


def _windows_sapi_script(
    text: str,
    output_path: Path,
    *,
    voice: str | None,
    rate: int,
) -> str:
    text_b64 = _b64_utf8(text)
    path_b64 = _b64_utf8(str(output_path.resolve()))
    voice_b64 = _b64_utf8(voice or "")
    return f"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$text = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{text_b64}'))
$path = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{path_b64}'))
$voice = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{voice_b64}'))
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.Rate = {rate}
$synth.Volume = 95
if ($voice.Length -gt 0) {{
    $synth.SelectVoice($voice)
}}
$synth.SetOutputToWaveFile($path)
$synth.Speak($text) | Out-Null
$synth.Dispose()
"""


def _b64_utf8(value: str) -> str:
    return base64.b64encode(value.encode("utf-8")).decode("ascii")


def _encode_powershell(script: str) -> str:
    return base64.b64encode(script.encode("utf-16le")).decode("ascii")


def _elapsed_ms(started: float) -> int:
    return int(round((perf_counter() - started) * 1000))
