from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from services.proxemics.engine import (
    CrowdingLevel,
    PersonRole,
    ProxemicAnalyzer,
    ProxemicBand,
    ProxemicProfile,
    TableLocation,
    TrackedPerson,
)
from services.proxemics.voice import ProxemicVoiceFormatter, VoiceMessageLimiter


def test_proxemic_analyzer_classifies_distance_bands() -> None:
    analyzer = ProxemicAnalyzer()

    assert analyzer.classify_distance(0.30) is ProxemicBand.INTIMATE
    assert analyzer.classify_distance(1.00) is ProxemicBand.PERSONAL
    assert analyzer.classify_distance(2.50) is ProxemicBand.SOCIAL
    assert analyzer.classify_distance(6.00) is ProxemicBand.PUBLIC
    assert analyzer.classify_distance(9.00) is ProxemicBand.OUT_OF_RANGE


def test_proxemic_profile_multiplier_adjusts_thresholds() -> None:
    analyzer = ProxemicAnalyzer(ProxemicProfile(distance_multiplier=0.80))

    assert analyzer.classify_distance(0.90) is ProxemicBand.PERSONAL
    assert analyzer.classify_distance(1.00) is ProxemicBand.SOCIAL


def test_pairwise_interactions_label_staff_customer_contact_without_sensitive_claims() -> None:
    analyzer = ProxemicAnalyzer()
    people = [
        TrackedPerson("staff_1", PersonRole.STAFF, x_m=0.0, y_m=0.0, zone_id="sala"),
        TrackedPerson("client_1", PersonRole.CUSTOMER, x_m=0.0, y_m=1.0, zone_id="sala"),
        TrackedPerson("client_2", PersonRole.CUSTOMER, x_m=0.0, y_m=4.0, zone_id="sala"),
    ]

    interactions = analyzer.pairwise_interactions(people)

    assert len(interactions) == 2
    staff_contact = next(
        interaction
        for interaction in interactions
        if {interaction.person_a_id, interaction.person_b_id} == {"staff_1", "client_1"}
    )
    assert staff_contact.band is ProxemicBand.PERSONAL
    assert staff_contact.operational_label == "direct_service_contact"
    assert "intrusion" not in staff_contact.operational_label


def test_staff_table_contacts_ignore_empty_tables_and_label_attention() -> None:
    analyzer = ProxemicAnalyzer()
    staff = [
        TrackedPerson("staff_1", PersonRole.STAFF, x_m=0.0, y_m=0.0),
        TrackedPerson("unknown_1", PersonRole.UNKNOWN, x_m=0.0, y_m=0.0),
    ]
    tables = [
        TableLocation("table_01", x_m=0.0, y_m=1.0, occupied=True),
        TableLocation("table_02", x_m=0.0, y_m=1.0, occupied=False),
    ]

    contacts = analyzer.staff_table_contacts(staff=staff, tables=tables)

    assert len(contacts) == 1
    assert contacts[0].table_id == "table_01"
    assert contacts[0].band is ProxemicBand.PERSONAL
    assert contacts[0].operational_label == "table_attention_contact"


def test_crowding_assessment_uses_neutral_operational_levels() -> None:
    analyzer = ProxemicAnalyzer()

    normal = analyzer.assess_crowding("barra", person_count=3, area_m2=12)
    elevated = analyzer.assess_crowding("barra", person_count=4, area_m2=10)
    high = analyzer.assess_crowding("barra", person_count=6, area_m2=10)

    assert normal.level is CrowdingLevel.NORMAL
    assert elevated.level is CrowdingLevel.ELEVATED
    assert high.level is CrowdingLevel.HIGH
    assert "Densidad alta" in high.explanation


def test_voice_formatter_outputs_restrained_messages_and_cooldown() -> None:
    analyzer = ProxemicAnalyzer()
    formatter = ProxemicVoiceFormatter()
    limiter = VoiceMessageLimiter(cooldown_seconds=300)
    now = datetime(2026, 4, 21, 18, 0, tzinfo=UTC)

    assessment = analyzer.assess_crowding("barra", person_count=6, area_m2=10)
    message = formatter.format_crowding(assessment)

    assert message is not None
    assert "densidad alta" in message.text.lower()
    assert "conflicto" not in message.text.lower()
    assert limiter.should_emit(message, now) is True
    assert limiter.should_emit(message, now + timedelta(seconds=30)) is False
    assert limiter.should_emit(message, now + timedelta(minutes=6)) is True


def test_voice_formatter_reviews_close_proximity_without_accusatory_language() -> None:
    analyzer = ProxemicAnalyzer()
    formatter = ProxemicVoiceFormatter()
    people = [
        TrackedPerson("client_1", PersonRole.CUSTOMER, x_m=0.0, y_m=0.0, zone_id="barra"),
        TrackedPerson("unknown_1", PersonRole.UNKNOWN, x_m=0.0, y_m=0.3, zone_id="barra"),
    ]

    interaction = analyzer.pairwise_interactions(people)[0]
    message = formatter.format_close_proximity(interaction)

    assert message is not None
    assert "Proximidad muy alta" in message.text
    assert "robo" not in message.text.lower()
    assert "intrusion" not in message.text.lower()


def test_proxemic_analyzer_validates_inputs() -> None:
    analyzer = ProxemicAnalyzer()

    with pytest.raises(ValueError, match="non-negative"):
        analyzer.classify_distance(-1)

    with pytest.raises(ValueError, match="area_m2"):
        analyzer.assess_crowding("zona", person_count=1, area_m2=0)

    with pytest.raises(ValueError, match="monotonically"):
        ProxemicProfile(intimate_far_m=2.0, personal_far_m=1.0)
