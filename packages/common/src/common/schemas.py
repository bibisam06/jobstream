from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal


CompanySize = Literal["startup", "small", "midsize", "enterprise"]


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class JobPosting:
    source: str
    source_job_id: str
    title: str
    company_name: str
    url: str
    company_name_normalized: str | None = None
    company_size: CompanySize | None = None
    industry: str | None = None
    job_category: str | None = None
    description: str | None = None
    requirements: str | None = None
    preferred: str | None = None
    experience_min: int | None = None
    experience_max: int | None = None
    salary_text: str | None = None
    location: str | None = None
    posted_at: str | None = None
    deadline_at: str | None = None
    is_active: bool = True
    skills: list[str] = field(default_factory=list)
    raw_payload: dict[str, Any] = field(default_factory=dict)
    collected_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
