from __future__ import annotations

from dataclasses import dataclass

from services.voice.models import VoiceIntent


@dataclass(frozen=True, slots=True)
class VoiceScenario:
    scenario_id: str
    intent: VoiceIntent
    label: str
    keywords: tuple[str, ...]
    reply_text: str
    risk: str
    requires_manager: bool = True
    interrupts_reservation: bool = False


CALL_SCENARIOS: tuple[VoiceScenario, ...] = (
    VoiceScenario(
        scenario_id="allergens",
        intent=VoiceIntent.SPECIAL_REQUEST,
        label="Alergias o restricciones alimentarias",
        keywords=(
            "alergia",
            "alergico",
            "celiaco",
            "gluten",
            "lactosa",
            "frutos secos",
            "vegano",
            "vegetariano",
        ),
        reply_text=(
            "Para alergias o restricciones alimentarias prefiero que lo confirme "
            "el encargado y evitar darle informacion incompleta."
        ),
        risk="high",
        interrupts_reservation=True,
    ),
    VoiceScenario(
        scenario_id="complaint",
        intent=VoiceIntent.COMPLAINT,
        label="Queja o reclamacion",
        keywords=("queja", "reclamacion", "reclamar", "mala experiencia", "devolucion"),
        reply_text="Lamento la situacion. Le paso con el encargado para atenderlo bien.",
        risk="high",
        interrupts_reservation=True,
    ),
    VoiceScenario(
        scenario_id="private_event",
        intent=VoiceIntent.SPECIAL_REQUEST,
        label="Evento privado o celebracion",
        keywords=("evento", "privado", "cumpleanos", "comunion", "boda", "empresa"),
        reply_text=(
            "Para eventos o grupos especiales le paso con el encargado, "
            "asi puede revisar capacidad, horario y condiciones."
        ),
        risk="medium",
        interrupts_reservation=True,
    ),
    VoiceScenario(
        scenario_id="late_arrival",
        intent=VoiceIntent.OPERATIONAL_NOTICE,
        label="Aviso de retraso",
        keywords=("llego tarde", "llegamos tarde", "retraso", "nos retrasamos"),
        reply_text="Tomo nota del aviso y le paso con el encargado para confirmar la reserva.",
        risk="medium",
        interrupts_reservation=True,
    ),
    VoiceScenario(
        scenario_id="opening_hours",
        intent=VoiceIntent.INFORMATION_REQUEST,
        label="Horario o cocina abierta",
        keywords=("horario", "abris", "abren", "cerrais", "cierran", "cocina abierta"),
        reply_text=(
            "Para no darle un horario incorrecto, le paso con el encargado "
            "o puedo tomar una solicitud de reserva."
        ),
        risk="low",
    ),
    VoiceScenario(
        scenario_id="menu_prices",
        intent=VoiceIntent.INFORMATION_REQUEST,
        label="Carta, menu o precios",
        keywords=("carta", "menu", "precio", "plato", "tapas", "vino"),
        reply_text=(
            "Ahora mismo no tengo la carta actualizada en el sistema. "
            "Le paso con el encargado para confirmarlo."
        ),
        risk="medium",
    ),
    VoiceScenario(
        scenario_id="location",
        intent=VoiceIntent.INFORMATION_REQUEST,
        label="Direccion o como llegar",
        keywords=("direccion", "ubicacion", "donde estais", "como llegar"),
        reply_text=("Para darle la direccion exacta y evitar errores, le paso con el encargado."),
        risk="low",
    ),
    VoiceScenario(
        scenario_id="parking",
        intent=VoiceIntent.INFORMATION_REQUEST,
        label="Aparcamiento",
        keywords=("parking", "aparcamiento", "aparcar"),
        reply_text="No tengo informacion fiable de aparcamiento. Le paso con el encargado.",
        risk="low",
    ),
    VoiceScenario(
        scenario_id="terrace",
        intent=VoiceIntent.SPECIAL_REQUEST,
        label="Terraza o zona concreta",
        keywords=("terraza", "fuera", "interior", "ventana"),
        reply_text=(
            "La preferencia de zona depende de disponibilidad real. "
            "Le paso con el encargado para confirmarlo."
        ),
        risk="medium",
    ),
    VoiceScenario(
        scenario_id="accessibility",
        intent=VoiceIntent.SPECIAL_REQUEST,
        label="Accesibilidad",
        keywords=("silla de ruedas", "accesible", "movilidad reducida", "carrito"),
        reply_text=("Para preparar bien la mesa y el acceso, le paso con el encargado."),
        risk="medium",
        interrupts_reservation=True,
    ),
    VoiceScenario(
        scenario_id="pets",
        intent=VoiceIntent.INFORMATION_REQUEST,
        label="Mascotas",
        keywords=("perro", "mascota", "mascotas"),
        reply_text="Para confirmar la politica de mascotas le paso con el encargado.",
        risk="low",
    ),
    VoiceScenario(
        scenario_id="children",
        intent=VoiceIntent.SPECIAL_REQUEST,
        label="Ninos, tronas o carritos",
        keywords=("trona", "nino", "bebe", "carrito"),
        reply_text=("Para preparar bien la mesa familiar le paso con el encargado."),
        risk="low",
    ),
    VoiceScenario(
        scenario_id="takeaway_delivery",
        intent=VoiceIntent.INFORMATION_REQUEST,
        label="Para llevar o delivery",
        keywords=("para llevar", "domicilio", "delivery", "glovo", "uber eats"),
        reply_text=(
            "No tengo configurado el servicio de pedidos para llevar. Le paso con el encargado."
        ),
        risk="medium",
    ),
    VoiceScenario(
        scenario_id="lost_item",
        intent=VoiceIntent.OPERATIONAL_NOTICE,
        label="Objeto perdido",
        keywords=("perdido", "olvidado", "cartera", "movil"),
        reply_text="Le paso con el encargado para revisar objetos perdidos.",
        risk="medium",
    ),
    VoiceScenario(
        scenario_id="supplier",
        intent=VoiceIntent.THIRD_PARTY,
        label="Proveedor o factura",
        keywords=("proveedor", "comercial", "factura", "albaran"),
        reply_text="Le paso con el encargado para temas de proveedores o facturacion.",
        risk="low",
    ),
    VoiceScenario(
        scenario_id="job_application",
        intent=VoiceIntent.THIRD_PARTY,
        label="Trabajo o curriculum",
        keywords=("trabajo", "empleo", "curriculum", "curriculo"),
        reply_text="Para empleo o curriculum le paso con el encargado.",
        risk="low",
    ),
    VoiceScenario(
        scenario_id="waitlist",
        intent=VoiceIntent.CHECK_AVAILABILITY,
        label="Lista de espera",
        keywords=("lista de espera", "apuntarme", "apuntar en cola"),
        reply_text=(
            "Puedo revisar disponibilidad, pero para lista de espera telefonica "
            "le paso con el encargado."
        ),
        risk="medium",
    ),
)


def classify_voice_scenario(normalized_text: str) -> VoiceScenario | None:
    for scenario in CALL_SCENARIOS:
        if any(keyword in normalized_text for keyword in scenario.keywords):
            return scenario
    return None
