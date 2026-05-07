from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from time import perf_counter

DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
DEFAULT_OLLAMA_GEMMA4_MODEL = "gemma4:e2b-it-q4_K_M"

VOICE_REPLY_COMPRESSOR_SYSTEM_PROMPT = """\
Reescribe para una llamada de restaurante en espanol de Espana.
Maximo 18 palabras. No cambies datos. No inventes. Devuelve solo la frase final.
"""


@dataclass(frozen=True, slots=True)
class VoiceReplyCompressionConfig:
    provider: str = "none"
    model: str = DEFAULT_OLLAMA_GEMMA4_MODEL
    endpoint_url: str = DEFAULT_OLLAMA_URL
    timeout_seconds: float = 6.0
    max_output_chars: int = 320
    keep_alive: str = "30m"
    num_predict: int = 24
    num_ctx: int = 512
    num_thread: int | None = None
    enable_fast_path: bool = True


@dataclass(frozen=True, slots=True)
class VoiceReplyCompressionResult:
    input_text: str
    output_text: str
    provider: str
    model: str | None = None
    applied: bool = False
    elapsed_ms: int = 0
    metadata: dict[str, object] = field(default_factory=dict)


class VoiceReplyCompressor:
    def compress(self, text: str) -> VoiceReplyCompressionResult:
        started = perf_counter()
        return VoiceReplyCompressionResult(
            input_text=text,
            output_text=text,
            provider="none",
            applied=False,
            elapsed_ms=_elapsed_ms(started),
            metadata={"reason": "disabled"},
        )


class OllamaVoiceReplyCompressor:
    def __init__(self, config: VoiceReplyCompressionConfig) -> None:
        self.config = config
        self._memory_cache: dict[str, str] = {}

    def compress(self, text: str) -> VoiceReplyCompressionResult:
        started = perf_counter()
        stripped = " ".join(text.strip().split())
        if not stripped:
            return VoiceReplyCompressionResult(
                input_text=text,
                output_text=text,
                provider="ollama",
                model=self.config.model,
                applied=False,
                elapsed_ms=_elapsed_ms(started),
                metadata={"reason": "empty_text"},
            )
        if self.config.enable_fast_path:
            fast_candidate = _fast_restaurant_rewrite(stripped)
            if fast_candidate is not None:
                return VoiceReplyCompressionResult(
                    input_text=text,
                    output_text=fast_candidate,
                    provider="rules",
                    model=None,
                    applied=fast_candidate != stripped,
                    elapsed_ms=_elapsed_ms(started),
                    metadata={"reason": "fast_rule"},
                )
            cached_candidate = self._memory_cache.get(stripped)
            if cached_candidate is not None:
                return VoiceReplyCompressionResult(
                    input_text=text,
                    output_text=cached_candidate,
                    provider="cache",
                    model=self.config.model,
                    applied=cached_candidate != stripped,
                    elapsed_ms=_elapsed_ms(started),
                    metadata={"reason": "memory_cache"},
                )
        try:
            candidate = self._call_ollama(stripped)
        except (OSError, TimeoutError, urllib.error.URLError, ValueError) as exc:
            return VoiceReplyCompressionResult(
                input_text=text,
                output_text=text,
                provider="ollama",
                model=self.config.model,
                applied=False,
                elapsed_ms=_elapsed_ms(started),
                metadata={"fallback_reason": type(exc).__name__, "error": str(exc)[:240]},
            )

        candidate = _clean_model_output(candidate)
        accepted, reason = _accept_rewrite(
            original=stripped,
            candidate=candidate,
            max_output_chars=self.config.max_output_chars,
        )
        output_text = candidate if accepted else text
        if accepted:
            self._memory_cache[stripped] = candidate
        return VoiceReplyCompressionResult(
            input_text=text,
            output_text=output_text,
            provider="ollama",
            model=self.config.model,
            applied=accepted and candidate != stripped,
            elapsed_ms=_elapsed_ms(started),
            metadata={
                "accepted": accepted,
                "reason": reason,
                "candidate": candidate,
                "endpoint_url": self.config.endpoint_url,
            },
        )

    def _call_ollama(self, text: str) -> str:
        payload = {
            "model": self.config.model,
            "system": VOICE_REPLY_COMPRESSOR_SYSTEM_PROMPT,
            "prompt": f"Texto: {text}\nFrase:",
            "stream": False,
            "think": False,
            "options": {
                "temperature": 0.15,
                "top_p": 0.85,
                "top_k": 20,
                "num_predict": self.config.num_predict,
                "num_ctx": self.config.num_ctx,
                "stop": ["\n"],
            },
            "keep_alive": self.config.keep_alive,
        }
        if self.config.num_thread is not None:
            payload["options"]["num_thread"] = self.config.num_thread
        raw_payload = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.config.endpoint_url,
            data=raw_payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
        generated = response_payload.get("response")
        if not isinstance(generated, str):
            raise ValueError("Ollama response does not contain a text response.")
        return generated


def build_voice_reply_compressor(
    provider: str,
    *,
    model: str = DEFAULT_OLLAMA_GEMMA4_MODEL,
    endpoint_url: str = DEFAULT_OLLAMA_URL,
    timeout_seconds: float = 6.0,
    max_output_chars: int = 320,
    keep_alive: str = "30m",
    num_predict: int = 24,
    num_ctx: int = 512,
    num_thread: int | None = None,
    enable_fast_path: bool = True,
) -> VoiceReplyCompressor | OllamaVoiceReplyCompressor:
    normalized_provider = provider.strip().lower()
    if normalized_provider in {"none", "off", "disabled"}:
        return VoiceReplyCompressor()
    if normalized_provider == "ollama":
        return OllamaVoiceReplyCompressor(
            VoiceReplyCompressionConfig(
                provider="ollama",
                model=model,
                endpoint_url=endpoint_url,
                timeout_seconds=timeout_seconds,
                max_output_chars=max_output_chars,
                keep_alive=keep_alive,
                num_predict=num_predict,
                num_ctx=num_ctx,
                num_thread=num_thread,
                enable_fast_path=enable_fast_path,
            )
        )
    raise ValueError(f"Unsupported voice reply compressor provider: {provider}")


def _accept_rewrite(
    *,
    original: str,
    candidate: str,
    max_output_chars: int,
) -> tuple[bool, str]:
    if not candidate:
        return False, "empty_candidate"
    if len(candidate) > max_output_chars:
        return False, "candidate_too_long"
    if "\n" in candidate:
        return False, "multiline_candidate"
    if _contains_forbidden_meta(candidate):
        return False, "meta_response"
    missing_tokens = _missing_critical_tokens(original, candidate)
    if missing_tokens:
        return False, f"missing_critical_tokens:{','.join(missing_tokens[:4])}"
    return True, "accepted"


def _missing_critical_tokens(original: str, candidate: str) -> list[str]:
    original_tokens = _critical_tokens(original)
    if not original_tokens:
        return []
    candidate_normalized = _normalize_for_compare(candidate)
    return [token for token in original_tokens if token not in candidate_normalized]


def _critical_tokens(text: str) -> list[str]:
    normalized = _normalize_for_compare(text)
    tokens = set(re.findall(r"\b\d{1,}\b", normalized))
    for marker in ("piemontesa", "passeig", "prim"):
        if marker in normalized:
            tokens.add(marker)
    return sorted(tokens)


def _fast_restaurant_rewrite(text: str) -> str | None:
    normalized = _normalize_for_compare(text)
    if len(text) <= 90 and not any(
        marker in normalized for marker in ("muchas gracias", "le esperamos")
    ):
        return text
    if "no he entendido bien" in normalized and "telefono" in normalized:
        return "No he entendido bien el telefono. Digame los nueve digitos, por favor."
    if "a que hora" in normalized and "reserva" in normalized:
        return "A que hora le gustaria la reserva?"
    if "reserva confirmada" in normalized:
        compact = text.replace("Muchas gracias, le esperamos", "Gracias, le esperamos")
        compact = compact.replace("  ", " ")
        return compact
    return None


def _contains_forbidden_meta(text: str) -> bool:
    lowered = text.lower()
    return any(
        phrase in lowered
        for phrase in (
            "respuesta optimizada",
            "respuesta oral",
            "aqui tienes",
            "como modelo",
            "no puedo",
        )
    )


def _clean_model_output(text: str) -> str:
    cleaned = text.strip().strip('"').strip("'")
    cleaned = re.sub(r"^\s*(respuesta oral optimizada|respuesta optimizada)\s*:\s*", "", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _normalize_for_compare(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _elapsed_ms(started: float) -> int:
    return int(round((perf_counter() - started) * 1000))
