from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from services.proxemics.engine import (
    CrowdingAssessment,
    CrowdingLevel,
    ProxemicBand,
    ProxemicInteraction,
    StaffTableContact,
)


class VoicePriority(StrEnum):
    INFO = "info"
    ADVISORY = "advisory"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class VoiceMessage:
    event_type: str
    priority: VoicePriority
    text: str
    dedupe_key: str


class ProxemicVoiceFormatter:
    """Formats proxemic signals as restrained operational voice prompts."""

    def format_crowding(self, assessment: CrowdingAssessment) -> VoiceMessage | None:
        if assessment.level is CrowdingLevel.NORMAL:
            return None

        if assessment.level is CrowdingLevel.HIGH:
            priority = VoicePriority.WARNING
            text = (
                f"Zona {assessment.area_id} con densidad alta. "
                "Revisar flujo de sala y nuevas entradas."
            )
        else:
            priority = VoicePriority.ADVISORY
            text = f"Zona {assessment.area_id} con densidad elevada. Mantener seguimiento."

        return VoiceMessage(
            event_type="proxemic_crowding",
            priority=priority,
            text=text,
            dedupe_key=f"proxemic_crowding:{assessment.area_id}:{assessment.level.value}",
        )

    def format_staff_table_contact(self, contact: StaffTableContact) -> VoiceMessage | None:
        if contact.band not in {ProxemicBand.INTIMATE, ProxemicBand.PERSONAL}:
            return None

        return VoiceMessage(
            event_type="staff_table_contact",
            priority=VoicePriority.INFO,
            text=f"Mesa {contact.table_id} con atencion cercana registrada.",
            dedupe_key=f"staff_table_contact:{contact.table_id}:{contact.staff_track_id}",
        )

    def format_close_proximity(self, interaction: ProxemicInteraction) -> VoiceMessage | None:
        if interaction.band is not ProxemicBand.INTIMATE:
            return None
        if interaction.operational_label == "direct_service_contact":
            return None

        zone_text = f" en zona {interaction.zone_id}" if interaction.zone_id else ""
        return VoiceMessage(
            event_type="close_proximity_review",
            priority=VoicePriority.ADVISORY,
            text=f"Proximidad muy alta{zone_text}. Revisar si hay saturacion operativa.",
            dedupe_key=(
                "close_proximity_review:"
                f"{min(interaction.person_a_id, interaction.person_b_id)}:"
                f"{max(interaction.person_a_id, interaction.person_b_id)}"
            ),
        )


@dataclass(slots=True)
class VoiceMessageLimiter:
    cooldown_seconds: int = 300
    _last_emitted_at_by_key: dict[str, datetime] | None = None

    def should_emit(self, message: VoiceMessage, now: datetime) -> bool:
        if self.cooldown_seconds < 0:
            raise ValueError("cooldown_seconds must be non-negative.")
        if self._last_emitted_at_by_key is None:
            self._last_emitted_at_by_key = {}

        last_emitted_at = self._last_emitted_at_by_key.get(message.dedupe_key)
        if last_emitted_at is not None:
            elapsed_seconds = (now - last_emitted_at).total_seconds()
            if elapsed_seconds < self.cooldown_seconds:
                return False

        self._last_emitted_at_by_key[message.dedupe_key] = now
        return True
