from __future__ import annotations

import math
import re
import unicodedata
import wave
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AudioBuffer:
    path: str
    sample_rate_hz: int
    channels: int
    sample_width_bytes: int
    frame_count: int
    duration_ms: int
    rms: float
    peak: float


@dataclass(frozen=True, slots=True)
class VadSegment:
    start_ms: int
    end_ms: int
    rms: float


@dataclass(frozen=True, slots=True)
class VadResult:
    has_speech: bool
    speech_ratio: float
    speech_ms: int
    total_ms: int
    threshold: float
    rms: float
    peak: float
    segments: tuple[VadSegment, ...]
    reason: str


@dataclass(frozen=True, slots=True)
class TranscriptQualityResult:
    accepted: bool
    risk_level: str
    reasons: tuple[str, ...]
    normalized_text: str
    token_count: int
    unique_token_ratio: float
    confidence: float | None = None
    wer: float | None = None


@dataclass(frozen=True, slots=True)
class AudioReadResult:
    audio: AudioBuffer
    samples: tuple[float, ...]


def read_pcm16_wav(path: str | Path) -> AudioReadResult:
    wav_path = Path(path)
    with wave.open(str(wav_path), "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_rate_hz = wav_file.getframerate()
        sample_width = wav_file.getsampwidth()
        frame_count = wav_file.getnframes()
        raw = wav_file.readframes(frame_count)

    if sample_width != 2:
        raise ValueError("Only PCM16 WAV files are supported for local voice diagnostics.")
    if channels <= 0:
        raise ValueError("WAV file must contain at least one channel.")

    values = [
        int.from_bytes(raw[index : index + 2], "little", signed=True) / 32768.0
        for index in range(0, len(raw), 2)
    ]
    if channels > 1:
        mono = []
        for index in range(0, len(values), channels):
            frame = values[index : index + channels]
            if len(frame) == channels:
                mono.append(sum(frame) / channels)
        values = mono

    rms = _rms(values)
    peak = max((abs(sample) for sample in values), default=0.0)
    duration_ms = int(round((frame_count / sample_rate_hz) * 1000)) if sample_rate_hz else 0
    return AudioReadResult(
        audio=AudioBuffer(
            path=str(wav_path),
            sample_rate_hz=sample_rate_hz,
            channels=channels,
            sample_width_bytes=sample_width,
            frame_count=frame_count,
            duration_ms=duration_ms,
            rms=round(rms, 6),
            peak=round(peak, 6),
        ),
        samples=tuple(values),
    )


def simple_energy_vad(
    audio: AudioBuffer,
    samples: tuple[float, ...],
    *,
    frame_ms: int = 30,
    min_speech_ms: int = 350,
    min_speech_ratio: float = 0.08,
    absolute_threshold: float = 0.012,
) -> VadResult:
    if audio.sample_rate_hz <= 0:
        raise ValueError("sample_rate_hz must be positive.")
    if frame_ms <= 0:
        raise ValueError("frame_ms must be positive.")
    frame_size = max(1, int(audio.sample_rate_hz * frame_ms / 1000))
    segments: list[VadSegment] = []
    speech_ms = 0
    threshold = max(absolute_threshold, audio.rms * 0.35)
    current_start: int | None = None
    current_rms_values: list[float] = []

    for frame_index, start in enumerate(range(0, len(samples), frame_size)):
        frame = samples[start : start + frame_size]
        if not frame:
            continue
        frame_rms = _rms(frame)
        frame_start_ms = int(round(frame_index * frame_ms))
        frame_end_ms = min(audio.duration_ms, frame_start_ms + frame_ms)
        is_speech = frame_rms >= threshold
        if is_speech:
            speech_ms += max(0, frame_end_ms - frame_start_ms)
            if current_start is None:
                current_start = frame_start_ms
            current_rms_values.append(frame_rms)
        elif current_start is not None:
            segments.append(
                VadSegment(
                    start_ms=current_start,
                    end_ms=frame_start_ms,
                    rms=round(max(current_rms_values), 6),
                )
            )
            current_start = None
            current_rms_values = []

    if current_start is not None:
        segments.append(
            VadSegment(
                start_ms=current_start,
                end_ms=audio.duration_ms,
                rms=round(max(current_rms_values), 6),
            )
        )

    speech_ratio = speech_ms / audio.duration_ms if audio.duration_ms else 0.0
    has_speech = speech_ms >= min_speech_ms and speech_ratio >= min_speech_ratio
    if audio.duration_ms <= 0:
        reason = "empty_audio"
    elif has_speech:
        reason = "speech_detected"
    elif speech_ms < min_speech_ms:
        reason = "speech_too_short"
    else:
        reason = "speech_ratio_too_low"
    return VadResult(
        has_speech=has_speech,
        speech_ratio=round(speech_ratio, 4),
        speech_ms=int(speech_ms),
        total_ms=audio.duration_ms,
        threshold=round(threshold, 6),
        rms=audio.rms,
        peak=audio.peak,
        segments=tuple(segments),
        reason=reason,
    )


def evaluate_transcript_quality(
    transcript: str,
    *,
    confidence: float | None = None,
    reference_text: str | None = None,
    allow_phone_number: bool = False,
    min_tokens: int = 2,
    min_unique_token_ratio: float = 0.45,
    low_confidence_threshold: float = 0.55,
    max_wer: float = 0.35,
) -> TranscriptQualityResult:
    normalized = normalize_spanish_transcript(transcript)
    tokens = normalized.split()
    unique_ratio = len(set(tokens)) / len(tokens) if tokens else 0.0
    reasons: list[str] = []
    phone_like_transcript = allow_phone_number and _is_phone_like_transcript(normalized)
    if not normalized:
        reasons.append("empty_transcript")
    if len(tokens) < min_tokens and not phone_like_transcript:
        reasons.append("too_few_tokens")
    if tokens and unique_ratio < min_unique_token_ratio and not phone_like_transcript:
        reasons.append("repetitive_transcript")
    if confidence is not None and confidence < low_confidence_threshold:
        reasons.append("low_stt_confidence")

    wer = None
    if reference_text is not None:
        wer = word_error_rate(reference_text, transcript)
        if wer > max_wer:
            reasons.append("high_wer")

    accepted = not reasons
    risk_level = "low" if accepted else "medium" if reasons == ["high_wer"] else "high"
    return TranscriptQualityResult(
        accepted=accepted,
        risk_level=risk_level,
        reasons=tuple(reasons),
        normalized_text=normalized,
        token_count=len(tokens),
        unique_token_ratio=round(unique_ratio, 4),
        confidence=confidence,
        wer=wer,
    )


def _is_phone_like_transcript(normalized: str) -> bool:
    tokens = normalized.split()
    if not tokens:
        return False
    digit_tokens = [token for token in tokens if token.isdigit()]
    digit_count = sum(len(token) for token in digit_tokens)
    normalized_digits = "".join(digit_tokens)
    if digit_count != 9 and not (digit_count == 11 and normalized_digits.startswith("34")):
        return False
    non_digit_tokens = [token for token in tokens if not token.isdigit()]
    allowed_context = {
        "telefono",
        "movil",
        "contacto",
        "numero",
        "es",
        "mi",
        "el",
        "de",
        "del",
    }
    return all(token in allowed_context for token in non_digit_tokens)


def word_error_rate(reference: str, hypothesis: str) -> float:
    reference_tokens = normalize_spanish_transcript(reference).split()
    hypothesis_tokens = normalize_spanish_transcript(hypothesis).split()
    if not reference_tokens:
        return 0.0 if not hypothesis_tokens else 1.0
    distance = _edit_distance(reference_tokens, hypothesis_tokens)
    return round(distance / len(reference_tokens), 4)


def normalize_spanish_transcript(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower())
    without_accents = "".join(char for char in normalized if not unicodedata.combining(char))
    without_fillers = re.sub(r"\b(eh|em|mmm|mm|uh|um|vale|bueno)\b", " ", without_accents)
    number_words = {
        "cero": "0",
        "uno": "1",
        "una": "1",
        "dos": "2",
        "tres": "3",
        "cuatro": "4",
        "cinco": "5",
        "seis": "6",
        "siete": "7",
        "ocho": "8",
        "nueve": "9",
        "diez": "10",
    }
    for word, replacement in number_words.items():
        without_fillers = re.sub(rf"\b{word}\b", replacement, without_fillers)
    cleaned = re.sub(r"[^a-z0-9:+ ]+", " ", without_fillers)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _edit_distance(reference_tokens: list[str], hypothesis_tokens: list[str]) -> int:
    previous = list(range(len(hypothesis_tokens) + 1))
    for row_index, reference_token in enumerate(reference_tokens, start=1):
        current = [row_index]
        for column_index, hypothesis_token in enumerate(hypothesis_tokens, start=1):
            substitution_cost = 0 if reference_token == hypothesis_token else 1
            current.append(
                min(
                    previous[column_index] + 1,
                    current[column_index - 1] + 1,
                    previous[column_index - 1] + substitution_cost,
                )
            )
        previous = current
    return previous[-1]


def _rms(samples: tuple[float, ...] | list[float]) -> float:
    if not samples:
        return 0.0
    return math.sqrt(sum(sample * sample for sample in samples) / len(samples))
