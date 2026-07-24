from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CollectorSettings:
    user_agent: str = os.getenv(
        "JOBSTREAM_USER_AGENT",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36",
    )
    request_timeout_ms: int = int(os.getenv("JOBSTREAM_REQUEST_TIMEOUT_MS", "30000"))
    navigation_timeout_ms: int = int(os.getenv("JOBSTREAM_NAVIGATION_TIMEOUT_MS", "45000"))
    scroll_pause_ms: int = int(os.getenv("JOBSTREAM_SCROLL_PAUSE_MS", "800"))
    max_retries: int = int(os.getenv("JOBSTREAM_MAX_RETRIES", "3"))

# 데이터베이스 관련 config 추가
@dataclass(frozen=True, slots=True)
class DatabaseSettings:
    host: str = os.getenv("POSTGRES_HOST", "localhost")
    port: int = int(os.getenv("POSTGRES_PORT", "5433"))
    user: str = os.getenv("POSTGRES_USER", "jobstream")
    password: str = os.getenv("POSTGRES_PASSWORD", "jobstream-dev")
    dbname: str = os.getenv("POSTGRES_DB", "jobstream")

    @property
    def dsn(self) -> str:
        return (
            f"host={self.host} port={self.port} "
            f"user={self.user} password={self.password} dbname={self.dbname}"
        )