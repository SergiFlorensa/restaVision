from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class ModelMetadata:
    model_version: str
    model_path: str
    model_hash: str
    input_width: int
    input_height: int
    runtime: str
    quantization: str
    normalization: dict[str, Any] = field(default_factory=dict)
    registered_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class TableFeatureSnapshot:
    table_id: str
    current_state: str
    last_event_timestamp: datetime
    occupancy_duration_seconds: float
    confidence_score: float
    people_count: int
    model_version: str | None = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True, slots=True)
class AILineageEvent:
    event_id: str
    timestamp: datetime
    camera_id: str
    zone_id: str
    event_type: str
    confidence_score: float
    model_version: str
    table_id: str | None = None
    image_path: str | None = None
    latency_ms: float | None = None
    payload_json: dict[str, Any] = field(default_factory=dict)
    idempotency_key: str | None = None


class SQLiteFeatureStore:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        if self.database_path.parent != Path("."):
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.create_schema()

    def create_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS model_registry (
                    model_version TEXT PRIMARY KEY,
                    model_path TEXT NOT NULL,
                    model_hash TEXT NOT NULL,
                    input_width INTEGER NOT NULL,
                    input_height INTEGER NOT NULL,
                    runtime TEXT NOT NULL,
                    quantization TEXT NOT NULL,
                    normalization_json TEXT NOT NULL,
                    registered_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS table_features (
                    table_id TEXT PRIMARY KEY,
                    current_state TEXT NOT NULL,
                    last_event_timestamp TEXT NOT NULL,
                    occupancy_duration_seconds REAL NOT NULL,
                    confidence_score REAL NOT NULL,
                    people_count INTEGER NOT NULL,
                    model_version TEXT,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(model_version) REFERENCES model_registry(model_version)
                );

                CREATE TABLE IF NOT EXISTS ai_lineage_events (
                    event_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    camera_id TEXT NOT NULL,
                    zone_id TEXT NOT NULL,
                    table_id TEXT,
                    event_type TEXT NOT NULL,
                    model_version TEXT NOT NULL,
                    confidence_score REAL NOT NULL,
                    image_path TEXT,
                    latency_ms REAL,
                    payload_json TEXT NOT NULL,
                    idempotency_key TEXT UNIQUE,
                    FOREIGN KEY(model_version) REFERENCES model_registry(model_version)
                );

                CREATE INDEX IF NOT EXISTS idx_table_features_state
                    ON table_features(current_state);
                CREATE INDEX IF NOT EXISTS idx_ai_lineage_events_timestamp
                    ON ai_lineage_events(timestamp);
                CREATE INDEX IF NOT EXISTS idx_ai_lineage_events_table
                    ON ai_lineage_events(table_id);
                """)

    def register_model(self, metadata: ModelMetadata) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO model_registry (
                    model_version,
                    model_path,
                    model_hash,
                    input_width,
                    input_height,
                    runtime,
                    quantization,
                    normalization_json,
                    registered_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(model_version) DO UPDATE SET
                    model_path = excluded.model_path,
                    model_hash = excluded.model_hash,
                    input_width = excluded.input_width,
                    input_height = excluded.input_height,
                    runtime = excluded.runtime,
                    quantization = excluded.quantization,
                    normalization_json = excluded.normalization_json,
                    registered_at = excluded.registered_at
                """,
                (
                    metadata.model_version,
                    metadata.model_path,
                    metadata.model_hash,
                    metadata.input_width,
                    metadata.input_height,
                    metadata.runtime,
                    metadata.quantization,
                    json.dumps(metadata.normalization, sort_keys=True),
                    _to_iso(metadata.registered_at),
                ),
            )

    def get_model(self, model_version: str) -> ModelMetadata | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM model_registry WHERE model_version = ?",
                (model_version,),
            ).fetchone()
        return None if row is None else _model_from_row(row)

    def upsert_table_feature(self, snapshot: TableFeatureSnapshot) -> None:
        if snapshot.confidence_score < 0 or snapshot.confidence_score > 1:
            raise ValueError("confidence_score must be between 0 and 1.")
        if snapshot.occupancy_duration_seconds < 0:
            raise ValueError("occupancy_duration_seconds must be non-negative.")
        if snapshot.people_count < 0:
            raise ValueError("people_count must be non-negative.")

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO table_features (
                    table_id,
                    current_state,
                    last_event_timestamp,
                    occupancy_duration_seconds,
                    confidence_score,
                    people_count,
                    model_version,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(table_id) DO UPDATE SET
                    current_state = excluded.current_state,
                    last_event_timestamp = excluded.last_event_timestamp,
                    occupancy_duration_seconds = excluded.occupancy_duration_seconds,
                    confidence_score = excluded.confidence_score,
                    people_count = excluded.people_count,
                    model_version = excluded.model_version,
                    updated_at = excluded.updated_at
                """,
                (
                    snapshot.table_id,
                    snapshot.current_state,
                    _to_iso(snapshot.last_event_timestamp),
                    snapshot.occupancy_duration_seconds,
                    snapshot.confidence_score,
                    snapshot.people_count,
                    snapshot.model_version,
                    _to_iso(snapshot.updated_at),
                ),
            )

    def get_table_feature(self, table_id: str) -> TableFeatureSnapshot | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM table_features WHERE table_id = ?",
                (table_id,),
            ).fetchone()
        return None if row is None else _feature_from_row(row)

    def append_lineage_event(self, event: AILineageEvent) -> bool:
        if event.confidence_score < 0 or event.confidence_score > 1:
            raise ValueError("confidence_score must be between 0 and 1.")
        if event.latency_ms is not None and event.latency_ms < 0:
            raise ValueError("latency_ms must be non-negative.")

        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO ai_lineage_events (
                    event_id,
                    timestamp,
                    camera_id,
                    zone_id,
                    table_id,
                    event_type,
                    model_version,
                    confidence_score,
                    image_path,
                    latency_ms,
                    payload_json,
                    idempotency_key
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    _to_iso(event.timestamp),
                    event.camera_id,
                    event.zone_id,
                    event.table_id,
                    event.event_type,
                    event.model_version,
                    event.confidence_score,
                    event.image_path,
                    event.latency_ms,
                    json.dumps(event.payload_json, sort_keys=True),
                    event.idempotency_key,
                ),
            )
            return cursor.rowcount == 1

    def list_lineage_events(self, limit: int = 100) -> list[AILineageEvent]:
        if limit < 1:
            raise ValueError("limit must be greater than 0.")
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM ai_lineage_events
                ORDER BY timestamp DESC, event_id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [_lineage_from_row(row) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection


def _to_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


def _from_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _model_from_row(row: sqlite3.Row) -> ModelMetadata:
    return ModelMetadata(
        model_version=row["model_version"],
        model_path=row["model_path"],
        model_hash=row["model_hash"],
        input_width=row["input_width"],
        input_height=row["input_height"],
        runtime=row["runtime"],
        quantization=row["quantization"],
        normalization=json.loads(row["normalization_json"]),
        registered_at=_from_iso(row["registered_at"]),
    )


def _feature_from_row(row: sqlite3.Row) -> TableFeatureSnapshot:
    return TableFeatureSnapshot(
        table_id=row["table_id"],
        current_state=row["current_state"],
        last_event_timestamp=_from_iso(row["last_event_timestamp"]),
        occupancy_duration_seconds=row["occupancy_duration_seconds"],
        confidence_score=row["confidence_score"],
        people_count=row["people_count"],
        model_version=row["model_version"],
        updated_at=_from_iso(row["updated_at"]),
    )


def _lineage_from_row(row: sqlite3.Row) -> AILineageEvent:
    return AILineageEvent(
        event_id=row["event_id"],
        timestamp=_from_iso(row["timestamp"]),
        camera_id=row["camera_id"],
        zone_id=row["zone_id"],
        table_id=row["table_id"],
        event_type=row["event_type"],
        model_version=row["model_version"],
        confidence_score=row["confidence_score"],
        image_path=row["image_path"],
        latency_ms=row["latency_ms"],
        payload_json=json.loads(row["payload_json"]),
        idempotency_key=row["idempotency_key"],
    )
