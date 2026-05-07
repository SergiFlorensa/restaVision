from __future__ import annotations

from dataclasses import asdict, dataclass
from string import Formatter
from typing import Any


@dataclass(frozen=True, slots=True)
class VoiceReplyTemplate:
    action_name: str
    template: str
    intent: str
    tts_style: str = "auto"
    latency_tier: str = "hot_path"
    notes: str = ""

    @property
    def slot_names(self) -> tuple[str, ...]:
        return tuple(
            field_name for _, field_name, _, _ in Formatter().parse(self.template) if field_name
        )


VOICE_REPLY_TEMPLATES: dict[str, VoiceReplyTemplate] = {
    "utter_ask_intent": VoiceReplyTemplate(
        action_name="utter_ask_intent",
        intent="unknown",
        template="Desea reservar, cancelar o consultar disponibilidad? Que necesita?",
        tts_style="neutral",
        notes="Apertura de recuperacion cuando no se detecta intencion.",
    ),
    "utter_ask_party_size": VoiceReplyTemplate(
        action_name="utter_ask_party_size",
        intent="create_reservation",
        template="Para cuantas personas seria la mesa?",
        tts_style="neutral",
        notes="Pregunta de slot corto; no requiere LLM.",
    ),
    "utter_ask_requested_time": VoiceReplyTemplate(
        action_name="utter_ask_requested_time",
        intent="create_reservation",
        template="A que hora le gustaria la reserva?",
        tts_style="neutral",
        notes="Pregunta de hora; debe ser directa.",
    ),
    "utter_ask_customer_name": VoiceReplyTemplate(
        action_name="utter_ask_customer_name",
        intent="create_reservation",
        template="A que nombre dejamos la reserva?",
        tts_style="neutral",
        notes="Pregunta de nombre; mantener frase corta para STT de retorno.",
    ),
    "utter_ask_customer_name_spelling": VoiceReplyTemplate(
        action_name="utter_ask_customer_name_spelling",
        intent="create_reservation",
        template="Disculpe, para anotarlo bien, puede deletrearme el nombre letra a letra?",
        tts_style="repair",
        notes="Reparacion del slot nombre cuando hay rechazo o duda.",
    ),
    "utter_confirm_customer_name": VoiceReplyTemplate(
        action_name="utter_confirm_customer_name",
        intent="create_reservation",
        template="Entendido, {customer_name}. Es correcto el nombre?",
        tts_style="confirmation",
        notes="Readback obligatorio para nombres.",
    ),
    "utter_ask_phone": VoiceReplyTemplate(
        action_name="utter_ask_phone",
        intent="create_reservation",
        template="Me confirma un numero de telefono de contacto?",
        tts_style="neutral",
        notes="Pregunta de telefono; se valida despues por 9 digitos.",
    ),
    "utter_ask_reservation_identifier": VoiceReplyTemplate(
        action_name="utter_ask_reservation_identifier",
        intent="cancel_reservation",
        template="Me indica el nombre o telefono de la reserva, por favor?",
        tts_style="neutral",
        notes="Identificador minimo para cancelar o localizar reserva.",
    ),
    "utter_low_confidence_escalation": VoiceReplyTemplate(
        action_name="utter_low_confidence_escalation",
        intent="unknown",
        template="No he entendido la llamada. Le paso con el encargado.",
        tts_style="repair",
        notes="Salida segura ante baja confianza STT.",
    ),
    "utter_modify_requires_manager": VoiceReplyTemplate(
        action_name="utter_modify_requires_manager",
        intent="modify_reservation",
        template="Para modificar su reserva, le paso con el encargado y evitamos errores.",
        tts_style="serious",
        notes="Cambios de reserva requieren humano por riesgo operativo.",
    ),
    "utter_manager_transfer": VoiceReplyTemplate(
        action_name="utter_manager_transfer",
        intent="speak_to_manager",
        template="Un momento, le paso con el encargado.",
        tts_style="neutral",
        notes="Transferencia simple.",
    ),
    "utter_background_advice_bridge": VoiceReplyTemplate(
        action_name="utter_background_advice_bridge",
        intent="unknown",
        template=(
            "Entiendo. Lo compruebo un momento. "
            "Si quiere consultar la carta u otra informacion del restaurante, "
            "puede entrar en la web de La Piemontesa."
        ),
        tts_style="neutral",
        notes="Frase puente mientras Gemma prepara una respuesta lenta.",
    ),
    "utter_background_advice_ready": VoiceReplyTemplate(
        action_name="utter_background_advice_ready",
        intent="unknown",
        template="{reply_text}",
        tts_style="neutral",
        notes="Respuesta generada en segundo plano y validada para continuar la llamada.",
    ),
    "utter_service_pressure_transfer": VoiceReplyTemplate(
        action_name="utter_service_pressure_transfer",
        intent="create_reservation",
        template=(
            "La sala esta con mucha carga. Le paso con el encargado para confirmar bien la reserva."
        ),
        tts_style="serious",
        notes="Derivacion por carga operativa.",
    ),
    "utter_reject_reservation": VoiceReplyTemplate(
        action_name="utter_reject_reservation",
        intent="create_reservation",
        template=(
            "Ahora mismo no puedo garantizar esa mesa. "
            "Puedo dejar aviso al encargado o buscar otra hora."
        ),
        tts_style="serious",
        notes="Rechazo no definitivo con alternativa.",
    ),
    "action_confirm_reservation": VoiceReplyTemplate(
        action_name="action_confirm_reservation",
        intent="create_reservation",
        template=(
            "Reserva confirmada para {party_size} personas {spoken_time}, "
            "a nombre de {customer_name}. "
            "Muchas gracias, le esperamos en la Piemontesa de Passeig de Prim."
        ),
        tts_style="confirmation",
        notes="Confirmacion final con datos operativos.",
    ),
    "utter_reject_availability": VoiceReplyTemplate(
        action_name="utter_reject_availability",
        intent="check_availability",
        template=(
            "Ahora mismo no puedo garantizar disponibilidad para esa peticion. "
            "Puedo pasar aviso al encargado."
        ),
        tts_style="serious",
        notes="Consulta de disponibilidad negativa.",
    ),
    "utter_reservation_not_found": VoiceReplyTemplate(
        action_name="utter_reservation_not_found",
        intent="cancel_reservation",
        template="No localizo la reserva con esos datos. Le paso con el encargado.",
        tts_style="repair",
        notes="Evita cancelar datos incorrectos.",
    ),
    "action_cancel_reservation": VoiceReplyTemplate(
        action_name="action_cancel_reservation",
        intent="cancel_reservation",
        template="La reserva de {customer_name} ha sido cancelada. Gracias por avisar.",
        tts_style="confirmation",
        notes="Confirmacion de cancelacion.",
    ),
}


def render_voice_reply(action_name: str, **slots: object) -> str:
    template = VOICE_REPLY_TEMPLATES[action_name]
    return template.template.format(**slots)


def voice_reply_template_for(action_name: str) -> VoiceReplyTemplate:
    return VOICE_REPLY_TEMPLATES[action_name]


def export_voice_reply_catalog() -> list[dict[str, Any]]:
    return [
        {
            **asdict(template),
            "slot_names": list(template.slot_names),
        }
        for template in VOICE_REPLY_TEMPLATES.values()
    ]
