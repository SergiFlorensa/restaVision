from __future__ import annotations

import json
import re
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from time import perf_counter

from services.voice.response_compressor import DEFAULT_OLLAMA_GEMMA4_MODEL, DEFAULT_OLLAMA_URL

BACKGROUND_ADVISOR_SYSTEM_PROMPT = """\
Eres un asistente telefonico local de un restaurante en Espana.
Responde al cliente de forma breve, natural y operativa.
Mantienes el hilo de la llamada, pero solo dentro de reservas y consultas sencillas
del restaurante.
No confirmes reservas ni disponibilidad real.
Puedes anotar preferencias: ventana, terraza, zona tranquila, trona, retraso o accesibilidad.
Deriva al encargado solo en alergias, quejas, cambios de reserva, grupos grandes,
eventos, datos dudosos o decisiones que dependan de disponibilidad real.
Si el cliente espera, puedes mencionar que la carta u otra informacion del restaurante
esta en la web de La Piemontesa, pero no dictes URLs largas salvo que pregunte
expresamente.
Si faltan datos de reserva, pide solo el siguiente dato mas importante.
Maximo 35 palabras. Devuelve solo la frase final.
"""


@dataclass(frozen=True, slots=True)
class BackgroundAdviceRequest:
    call_id: str
    transcript: str
    intent: str
    reason: str
    conversation_context: tuple[str, ...] = ()
    reservation_context: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class BackgroundAdviceResult:
    request: BackgroundAdviceRequest
    reply_text: str | None
    status: str
    elapsed_ms: int
    metadata: dict[str, object] = field(default_factory=dict)


class BackgroundVoiceAdvisor:
    def request_advice(self, request: BackgroundAdviceRequest) -> None:
        raise NotImplementedError

    def consume_ready(self, call_id: str) -> BackgroundAdviceResult | None:
        raise NotImplementedError


class DisabledBackgroundVoiceAdvisor(BackgroundVoiceAdvisor):
    def request_advice(self, request: BackgroundAdviceRequest) -> None:
        return

    def consume_ready(self, call_id: str) -> BackgroundAdviceResult | None:
        return None


class OllamaBackgroundVoiceAdvisor(BackgroundVoiceAdvisor):
    def __init__(
        self,
        *,
        model: str = DEFAULT_OLLAMA_GEMMA4_MODEL,
        endpoint_url: str = DEFAULT_OLLAMA_URL,
        timeout_seconds: float = 20.0,
        num_thread: int | None = None,
        num_predict: int = 28,
        num_ctx: int = 256,
        keep_alive: str = "30m",
        temperature: float = 0.15,
        stream_early_stop: bool = True,
        min_stream_chars: int = 28,
        max_stream_chars: int = 220,
    ) -> None:
        self.model = model
        self.endpoint_url = endpoint_url
        self.timeout_seconds = timeout_seconds
        self.num_thread = num_thread
        self.num_predict = num_predict
        self.num_ctx = num_ctx
        self.keep_alive = keep_alive
        self.temperature = temperature
        self.stream_early_stop = stream_early_stop
        self.min_stream_chars = min_stream_chars
        self.max_stream_chars = max_stream_chars
        self._lock = threading.Lock()
        self._results: dict[str, BackgroundAdviceResult] = {}
        self._running: set[str] = set()

    def request_advice(self, request: BackgroundAdviceRequest) -> None:
        with self._lock:
            if request.call_id in self._running:
                return
            self._running.add(request.call_id)
        thread = threading.Thread(
            target=self._run,
            args=(request,),
            name=f"restauria-voice-advisor-{request.call_id}",
            daemon=True,
        )
        thread.start()

    def consume_ready(self, call_id: str) -> BackgroundAdviceResult | None:
        with self._lock:
            result = self._results.pop(call_id, None)
            if result is not None:
                self._running.discard(call_id)
            return result

    def _run(self, request: BackgroundAdviceRequest) -> None:
        started = perf_counter()
        try:
            reply_text = self._call_ollama(request)
            reply_text = _clean_reply(reply_text)
            status = "ready" if reply_text else "empty"
            metadata: dict[str, object] = {}
        except (OSError, TimeoutError, urllib.error.URLError, ValueError) as exc:
            reply_text = None
            status = "failed"
            metadata = {"error": str(exc)[:240], "error_type": type(exc).__name__}
        result = BackgroundAdviceResult(
            request=request,
            reply_text=reply_text,
            status=status,
            elapsed_ms=int(round((perf_counter() - started) * 1000)),
            metadata=metadata,
        )
        with self._lock:
            self._results[request.call_id] = result
            self._running.discard(request.call_id)

    def _call_ollama(self, request: BackgroundAdviceRequest) -> str:
        payload = {
            "model": self.model,
            "system": BACKGROUND_ADVISOR_SYSTEM_PROMPT,
            "prompt": _build_compact_prompt(request),
            "stream": self.stream_early_stop,
            "think": False,
            "options": {
                "temperature": self.temperature,
                "top_p": 0.85,
                "top_k": 20,
                "num_predict": self.num_predict,
                "num_ctx": self.num_ctx,
                "stop": ["\n"],
            },
            "keep_alive": self.keep_alive,
        }
        if self.num_thread is not None:
            payload["options"]["num_thread"] = self.num_thread
        request_payload = json.dumps(payload).encode("utf-8")
        http_request = urllib.request.Request(
            self.endpoint_url,
            data=request_payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(http_request, timeout=self.timeout_seconds) as response:
            if self.stream_early_stop:
                return self._read_streaming_response(response)
            response_payload = json.loads(response.read().decode("utf-8"))
        generated = response_payload.get("response")
        if not isinstance(generated, str):
            raise ValueError("Ollama response does not contain a text response.")
        return generated

    def _read_streaming_response(self, response: object) -> str:
        collected = ""
        for raw_line in response:
            if not raw_line:
                continue
            payload = json.loads(raw_line.decode("utf-8"))
            token = payload.get("response")
            if isinstance(token, str):
                collected += token
                early = _first_complete_sentence(
                    collected,
                    min_chars=self.min_stream_chars,
                    max_chars=self.max_stream_chars,
                )
                if early is not None:
                    return early
            if payload.get("done") is True:
                break
        return collected


def build_background_voice_advisor(
    provider: str,
    *,
    model: str = DEFAULT_OLLAMA_GEMMA4_MODEL,
    endpoint_url: str = DEFAULT_OLLAMA_URL,
    timeout_seconds: float = 20.0,
    num_thread: int | None = None,
    num_predict: int = 28,
    num_ctx: int = 256,
    keep_alive: str = "30m",
    temperature: float = 0.15,
    stream_early_stop: bool = True,
) -> BackgroundVoiceAdvisor:
    normalized = provider.strip().lower()
    if normalized in {"none", "off", "disabled"}:
        return DisabledBackgroundVoiceAdvisor()
    if normalized == "ollama":
        return OllamaBackgroundVoiceAdvisor(
            model=model,
            endpoint_url=endpoint_url,
            timeout_seconds=timeout_seconds,
            num_thread=num_thread,
            num_predict=num_predict,
            num_ctx=num_ctx,
            keep_alive=keep_alive,
            temperature=temperature,
            stream_early_stop=stream_early_stop,
        )
    raise ValueError(f"Unsupported background voice advisor provider: {provider}")


def _clean_reply(text: str) -> str | None:
    cleaned = text.strip().strip('"').strip("'")
    cleaned = re.sub(r"^\s*(respuesta telefonica|respuesta)\s*:\s*", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned or _contains_forbidden_meta(cleaned):
        return None
    return cleaned[:420]


def _first_complete_sentence(text: str, *, min_chars: int, max_chars: int) -> str | None:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) >= max_chars:
        return cleaned[:max_chars].rstrip(" ,;:") + "."
    if len(cleaned) < min_chars:
        return None
    match = re.search(r"(.+?[.!?])(?:\s|$)", cleaned)
    if match is None:
        return None
    sentence = match.group(1).strip()
    if len(sentence) < min_chars:
        return None
    return sentence


def _contains_forbidden_meta(text: str) -> bool:
    lowered = text.lower()
    return any(
        phrase in lowered for phrase in ("como modelo", "no puedo ayudarte", "respuesta telefonica")
    )


def _build_compact_prompt(request: BackgroundAdviceRequest) -> str:
    known_slots = {
        key: value
        for key, value in request.reservation_context.items()
        if value not in (None, False, "")
    }
    context = " | ".join(request.conversation_context[-3:])
    lines = [
        f"Cliente: {request.transcript}",
        f"Intencion: {request.intent}",
    ]
    if known_slots:
        lines.append(f"Datos: {json.dumps(known_slots, ensure_ascii=False)}")
    if context:
        lines.append(f"Contexto: {context}")
    lines.append("Respuesta telefonica breve:")
    return "\n".join(lines)
