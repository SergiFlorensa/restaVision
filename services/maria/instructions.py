from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from re import search


class MariaIntent(StrEnum):
    ROOM_SUMMARY = "room_summary"
    TABLE_ATTENTION = "table_attention"
    TABLE_CLEANLINESS = "table_cleanliness"
    ZONE_CROWDING = "zone_crowding"
    PROXIMITY_REVIEW = "proximity_review"
    GENERIC_REVIEW = "generic_review"


@dataclass(frozen=True, slots=True)
class MariaInstruction:
    raw_text: str
    normalized_text: str
    intent: MariaIntent
    table_id: str | None = None
    zone_hint: str | None = None
    requires_multimodal_capture: bool = True


class MariaInstructionParser:
    """Lightweight parser for natural-language restaurant instructions."""

    def parse(self, text: str) -> MariaInstruction:
        normalized_text = self._normalize(text)
        table_id = self._extract_table_id(normalized_text)
        zone_hint = self._extract_zone_hint(normalized_text)
        intent = self._resolve_intent(normalized_text)

        return MariaInstruction(
            raw_text=text,
            normalized_text=normalized_text,
            intent=intent,
            table_id=table_id,
            zone_hint=zone_hint,
            requires_multimodal_capture=self._requires_capture(intent),
        )

    def _resolve_intent(self, normalized_text: str) -> MariaIntent:
        if any(token in normalized_text for token in ("resumen", "estado general", "sala")):
            return MariaIntent.ROOM_SUMMARY
        if any(token in normalized_text for token in ("atencion", "atendida", "esperando")):
            return MariaIntent.TABLE_ATTENTION
        if any(token in normalized_text for token in ("limpia", "sucia", "limpieza", "limpiar")):
            return MariaIntent.TABLE_CLEANLINESS
        if any(
            token in normalized_text for token in ("congestion", "saturada", "densidad", "barra")
        ):
            return MariaIntent.ZONE_CROWDING
        if any(token in normalized_text for token in ("proximidad", "cercania", "distancia")):
            return MariaIntent.PROXIMITY_REVIEW
        return MariaIntent.GENERIC_REVIEW

    @staticmethod
    def _requires_capture(intent: MariaIntent) -> bool:
        return intent in {
            MariaIntent.ROOM_SUMMARY,
            MariaIntent.TABLE_ATTENTION,
            MariaIntent.TABLE_CLEANLINESS,
            MariaIntent.ZONE_CROWDING,
            MariaIntent.PROXIMITY_REVIEW,
            MariaIntent.GENERIC_REVIEW,
        }

    @staticmethod
    def _extract_table_id(normalized_text: str) -> str | None:
        match = search(r"\bmesa\s+(\d{1,2})\b", normalized_text)
        if match is None:
            return None
        number = int(match.group(1))
        return f"table_{number:02d}"

    @staticmethod
    def _extract_zone_hint(normalized_text: str) -> str | None:
        for hint in ("barra", "entrada", "terraza", "pasillo", "cocina"):
            if hint in normalized_text:
                return hint
        return None

    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join(text.strip().lower().split())
