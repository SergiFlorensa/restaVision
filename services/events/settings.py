from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - optional local convenience
    load_dotenv = None


@dataclass(frozen=True, slots=True)
class PersistenceSettings:
    enable_postgres: bool
    database_url: str | None

    @classmethod
    def from_environment(cls) -> PersistenceSettings:
        if load_dotenv is not None:
            load_dotenv()

        enable_postgres = _as_bool(os.getenv("ENABLE_POSTGRES"), default=False)
        database_url = os.getenv("DATABASE_URL")
        if enable_postgres and not database_url:
            raise RuntimeError("ENABLE_POSTGRES=true requires DATABASE_URL.")

        return cls(enable_postgres=enable_postgres, database_url=database_url)


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}
