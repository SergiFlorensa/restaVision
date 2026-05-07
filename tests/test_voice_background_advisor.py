from __future__ import annotations

from services.events.service import RestaurantMVPService
from services.voice.agent import VoiceReservationAgent
from services.voice.background_advisor import (
    BackgroundAdviceRequest,
    BackgroundAdviceResult,
    BackgroundVoiceAdvisor,
    OllamaBackgroundVoiceAdvisor,
    _first_complete_sentence,
    build_background_voice_advisor,
)
from tools.interactive_voice_call import (
    _is_short_conversation_reply,
    _should_accept_interactive_turn,
)


def test_voice_agent_bridges_complex_request_and_consumes_background_reply() -> None:
    advisor = _ImmediateBackgroundAdvisor(
        "Puedo anotar preferencia de ventana y zona tranquila. Si se retrasan, avisen."
    )
    agent = VoiceReservationAgent(RestaurantMVPService(), background_advisor=advisor)
    call = agent.start_call()

    result = agent.handle_turn(
        call.call_id,
        transcript=(
            "Quiero reservar una mesa cerca de la ventana porque viene una persona mayor "
            "y prefiere una zona tranquila, pero tambien saber si se puede cambiar la hora "
            "si llega tarde"
        ),
    )

    assert result.action_name == "utter_background_advice_bridge"
    assert result.reply_text.startswith("Entiendo. Lo compruebo un momento.")
    assert "La Piemontesa" in result.reply_text
    assert result.call.background_reply_status == "running"

    follow_up = agent.consume_background_reply(call.call_id)

    assert follow_up is not None
    assert follow_up.action_name == "utter_background_advice_ready"
    assert "zona tranquila" in follow_up.reply_text
    assert follow_up.action_payload["source"] == "background_advisor"
    captured_request = advisor.last_request
    assert captured_request is not None
    assert captured_request.conversation_context
    assert captured_request.reservation_context["phone_present"] is False


def test_interactive_call_accepts_short_confirmation_despite_short_vad() -> None:
    assert _is_short_conversation_reply("correcto")
    assert _is_short_conversation_reply("si correcto")
    assert not _is_short_conversation_reply("correcto mecer")


def test_interactive_call_accepts_short_yes_with_clear_audio_peak() -> None:
    call = VoiceReservationAgent(RestaurantMVPService()).start_call()
    vad = _Vad(has_speech=False, speech_ms=210, peak=0.08)
    quality = _Quality(accepted=False, normalized_text="si", token_count=1)

    assert _should_accept_interactive_turn(vad=vad, quality=quality, call=call)


def test_interactive_call_accepts_short_time_when_time_is_expected() -> None:
    agent = VoiceReservationAgent(RestaurantMVPService())
    call = agent.start_call()
    call.reservation_draft.party_size = 5
    vad = _Vad(has_speech=False, speech_ms=480, peak=0.057)
    quality = _Quality(accepted=True, normalized_text="2 del mediodia", token_count=3)

    assert _should_accept_interactive_turn(vad=vad, quality=quality, call=call)


def test_interactive_call_accepts_single_token_name_when_name_is_expected() -> None:
    agent = VoiceReservationAgent(RestaurantMVPService())
    call = agent.start_call()
    call.reservation_draft.party_size = 7
    call.reservation_draft.requested_time_text = "06/05/2026 14:00"
    vad = _Vad(has_speech=False, speech_ms=150, peak=0.073)
    quality = _Quality(accepted=False, normalized_text="juanito", token_count=1)

    assert _should_accept_interactive_turn(vad=vad, quality=quality, call=call)


def test_background_advisor_can_stop_on_first_useful_sentence() -> None:
    result = _first_complete_sentence(
        "Puedo anotar la preferencia de ventana. Para confirmar disponibilidad exacta...",
        min_chars=30,
        max_chars=120,
    )

    assert result == "Puedo anotar la preferencia de ventana."


def test_ollama_background_advisor_accepts_low_memory_runtime_settings() -> None:
    advisor = build_background_voice_advisor(
        "ollama",
        model="gemma4:e2b-it-q4_K_M",
        num_thread=4,
        num_predict=24,
        num_ctx=256,
        keep_alive="30m",
        temperature=0.1,
    )

    assert isinstance(advisor, OllamaBackgroundVoiceAdvisor)
    assert advisor.num_thread == 4
    assert advisor.num_predict == 24
    assert advisor.num_ctx == 256
    assert advisor.keep_alive == "30m"
    assert advisor.temperature == 0.1


class _Vad:
    def __init__(self, *, has_speech: bool, speech_ms: int, peak: float) -> None:
        self.has_speech = has_speech
        self.speech_ms = speech_ms
        self.peak = peak


class _Quality:
    def __init__(self, *, accepted: bool, normalized_text: str, token_count: int) -> None:
        self.accepted = accepted
        self.normalized_text = normalized_text
        self.token_count = token_count


class _ImmediateBackgroundAdvisor(BackgroundVoiceAdvisor):
    def __init__(self, reply_text: str) -> None:
        self._results: dict[str, BackgroundAdviceResult] = {}
        self._reply_text = reply_text
        self.last_request: BackgroundAdviceRequest | None = None

    def request_advice(self, request: BackgroundAdviceRequest) -> None:
        self.last_request = request
        self._results[request.call_id] = BackgroundAdviceResult(
            request=request,
            reply_text=self._reply_text,
            status="ready",
            elapsed_ms=42,
        )

    def consume_ready(self, call_id: str) -> BackgroundAdviceResult | None:
        return self._results.pop(call_id, None)
