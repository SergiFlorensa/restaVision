from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from itertools import combinations
from math import hypot


class PersonRole(StrEnum):
    CUSTOMER = "customer"
    STAFF = "staff"
    UNKNOWN = "unknown"


class ProxemicBand(StrEnum):
    INTIMATE = "intimate"
    PERSONAL = "personal"
    SOCIAL = "social"
    PUBLIC = "public"
    OUT_OF_RANGE = "out_of_range"


class CrowdingLevel(StrEnum):
    NORMAL = "normal"
    ELEVATED = "elevated"
    HIGH = "high"


@dataclass(frozen=True, slots=True)
class ProxemicProfile:
    intimate_far_m: float = 0.45
    personal_far_m: float = 1.20
    social_far_m: float = 3.60
    public_far_m: float = 7.60
    distance_multiplier: float = 1.0

    def __post_init__(self) -> None:
        thresholds = [
            self.intimate_far_m,
            self.personal_far_m,
            self.social_far_m,
            self.public_far_m,
        ]
        if any(value <= 0 for value in thresholds):
            raise ValueError("Proxemic thresholds must be positive.")
        if thresholds != sorted(thresholds):
            raise ValueError("Proxemic thresholds must be monotonically increasing.")
        if self.distance_multiplier <= 0:
            raise ValueError("distance_multiplier must be positive.")

    def threshold_for(self, band: ProxemicBand) -> float:
        if band is ProxemicBand.INTIMATE:
            return self.intimate_far_m * self.distance_multiplier
        if band is ProxemicBand.PERSONAL:
            return self.personal_far_m * self.distance_multiplier
        if band is ProxemicBand.SOCIAL:
            return self.social_far_m * self.distance_multiplier
        if band is ProxemicBand.PUBLIC:
            return self.public_far_m * self.distance_multiplier
        raise ValueError("OUT_OF_RANGE does not have a finite threshold.")


@dataclass(frozen=True, slots=True)
class TrackedPerson:
    track_id: str
    role: PersonRole
    x_m: float
    y_m: float
    table_id: str | None = None
    zone_id: str | None = None
    group_id: str | None = None

    @property
    def position(self) -> tuple[float, float]:
        return (self.x_m, self.y_m)


@dataclass(frozen=True, slots=True)
class TableLocation:
    table_id: str
    x_m: float
    y_m: float
    occupied: bool = True
    zone_id: str | None = None

    @property
    def position(self) -> tuple[float, float]:
        return (self.x_m, self.y_m)


@dataclass(frozen=True, slots=True)
class ProxemicInteraction:
    person_a_id: str
    person_b_id: str
    role_a: PersonRole
    role_b: PersonRole
    distance_m: float
    band: ProxemicBand
    operational_label: str
    zone_id: str | None = None


@dataclass(frozen=True, slots=True)
class StaffTableContact:
    staff_track_id: str
    table_id: str
    distance_m: float
    band: ProxemicBand
    operational_label: str


@dataclass(frozen=True, slots=True)
class CrowdingAssessment:
    area_id: str
    person_count: int
    area_m2: float
    density_people_per_m2: float
    level: CrowdingLevel
    explanation: str


class ProxemicAnalyzer:
    """Computes neutral operational proximity signals from calibrated floor coordinates."""

    def __init__(self, profile: ProxemicProfile | None = None) -> None:
        self.profile = profile or ProxemicProfile()

    def classify_distance(self, distance_m: float) -> ProxemicBand:
        if distance_m < 0:
            raise ValueError("distance_m must be non-negative.")
        if distance_m <= self.profile.threshold_for(ProxemicBand.INTIMATE):
            return ProxemicBand.INTIMATE
        if distance_m <= self.profile.threshold_for(ProxemicBand.PERSONAL):
            return ProxemicBand.PERSONAL
        if distance_m <= self.profile.threshold_for(ProxemicBand.SOCIAL):
            return ProxemicBand.SOCIAL
        if distance_m <= self.profile.threshold_for(ProxemicBand.PUBLIC):
            return ProxemicBand.PUBLIC
        return ProxemicBand.OUT_OF_RANGE

    def distance(self, point_a: tuple[float, float], point_b: tuple[float, float]) -> float:
        return hypot(point_a[0] - point_b[0], point_a[1] - point_b[1])

    def pairwise_interactions(
        self,
        people: list[TrackedPerson],
        max_band: ProxemicBand = ProxemicBand.SOCIAL,
    ) -> list[ProxemicInteraction]:
        max_distance = self.profile.threshold_for(max_band)
        interactions: list[ProxemicInteraction] = []

        for person_a, person_b in combinations(people, 2):
            distance_m = self.distance(person_a.position, person_b.position)
            if distance_m > max_distance:
                continue

            band = self.classify_distance(distance_m)
            interactions.append(
                ProxemicInteraction(
                    person_a_id=person_a.track_id,
                    person_b_id=person_b.track_id,
                    role_a=person_a.role,
                    role_b=person_b.role,
                    distance_m=distance_m,
                    band=band,
                    operational_label=self._interaction_label(person_a, person_b, band),
                    zone_id=person_a.zone_id if person_a.zone_id == person_b.zone_id else None,
                )
            )

        return interactions

    def staff_table_contacts(
        self,
        staff: list[TrackedPerson],
        tables: list[TableLocation],
        max_band: ProxemicBand = ProxemicBand.SOCIAL,
    ) -> list[StaffTableContact]:
        max_distance = self.profile.threshold_for(max_band)
        contacts: list[StaffTableContact] = []

        for staff_member in staff:
            if staff_member.role is not PersonRole.STAFF:
                continue
            for table in tables:
                if not table.occupied:
                    continue
                distance_m = self.distance(staff_member.position, table.position)
                if distance_m > max_distance:
                    continue
                band = self.classify_distance(distance_m)
                contacts.append(
                    StaffTableContact(
                        staff_track_id=staff_member.track_id,
                        table_id=table.table_id,
                        distance_m=distance_m,
                        band=band,
                        operational_label=self._staff_table_label(band),
                    )
                )

        return contacts

    def assess_crowding(
        self,
        area_id: str,
        person_count: int,
        area_m2: float,
        elevated_density_people_per_m2: float = 0.33,
        high_density_people_per_m2: float = 0.50,
    ) -> CrowdingAssessment:
        if person_count < 0:
            raise ValueError("person_count must be non-negative.")
        if area_m2 <= 0:
            raise ValueError("area_m2 must be positive.")
        if elevated_density_people_per_m2 <= 0 or high_density_people_per_m2 <= 0:
            raise ValueError("Density thresholds must be positive.")
        if elevated_density_people_per_m2 >= high_density_people_per_m2:
            raise ValueError("Elevated density must be lower than high density.")

        density = person_count / area_m2
        if density >= high_density_people_per_m2:
            level = CrowdingLevel.HIGH
            explanation = "Densidad alta; revisar flujo operativo de la zona."
        elif density >= elevated_density_people_per_m2:
            level = CrowdingLevel.ELEVATED
            explanation = "Densidad elevada; monitorizar posible saturacion."
        else:
            level = CrowdingLevel.NORMAL
            explanation = "Densidad dentro del rango operativo esperado."

        return CrowdingAssessment(
            area_id=area_id,
            person_count=person_count,
            area_m2=area_m2,
            density_people_per_m2=density,
            level=level,
            explanation=explanation,
        )

    def _interaction_label(
        self,
        person_a: TrackedPerson,
        person_b: TrackedPerson,
        band: ProxemicBand,
    ) -> str:
        roles = {person_a.role, person_b.role}
        same_group = person_a.group_id is not None and person_a.group_id == person_b.group_id

        if PersonRole.STAFF in roles and PersonRole.CUSTOMER in roles:
            if band in {ProxemicBand.INTIMATE, ProxemicBand.PERSONAL}:
                return "direct_service_contact"
            if band is ProxemicBand.SOCIAL:
                return "nearby_service_presence"

        if same_group:
            return "same_group_proximity"

        if band is ProxemicBand.INTIMATE:
            return "close_proximity_review"
        if band is ProxemicBand.PERSONAL:
            return "personal_proximity"
        if band is ProxemicBand.SOCIAL:
            return "shared_social_area"
        return "public_co_presence"

    def _staff_table_label(self, band: ProxemicBand) -> str:
        if band in {ProxemicBand.INTIMATE, ProxemicBand.PERSONAL}:
            return "table_attention_contact"
        if band is ProxemicBand.SOCIAL:
            return "staff_near_table"
        return "staff_visible_from_table"
