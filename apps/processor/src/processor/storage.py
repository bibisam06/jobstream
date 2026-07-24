from __future__ import annotations

import json
from typing import Any

import psycopg2
from psycopg2.extras import Json

from common.config import DatabaseSettings



def get_connection():
    settins = DatabaseSettings()
    return psycopg2.connect(settins.dsn)


#회사 저장
def upsert_company(cur, posting: dict[str, Any]) -> int | None:
    name = posting.get("company_name")
    name_normalized = posting.get("company_name_normalized")
    if not name or not name_normalized:
        return None
    cur.execute(
        """
        INSERT INTO companies (name, name_normalized, company_size, industry)
        VALUES (%s, %s, %s, %s) ON CONFLICT (name_normalized) DO
        UPDATE
            SET name = EXCLUDED.name
            RETURNING company_id
        """,
        (name, name_normalized, posting.get("company_size"), posting.get("industry")),
    )
    return cur.fetchone()[0]

def upsert_job_posting(cur, posting: dict[str, Any], company_id : int | None) -> int:
    cur.execute(
        """
        INSERT INTO job_postings (source, source_job_id, company_id, title, job_category,
        description, requirements, preferred,
        experience_min, experience_max, salary_text, location, url,
        posted_at, deadline_at, is_active, raw_payload, collected_at)
        VALUES (%s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s) ON CONFLICT (source, source_job_id) DO
        UPDATE SET
            title = EXCLUDED.title,
            is_active = EXCLUDED.is_active,
            raw_payload = EXCLUDED.raw_payload,
            updated_at = now()
            RETURNING job_id
        """,
        (
            posting["source"], posting["source_job_id"], company_id,
            posting["title"], posting.get("job_category"),
            posting.get("description"), posting.get("requirements"), posting.get("preferred"),
            posting.get("experience_min"), posting.get("experience_max"),
            posting.get("salary_text"), posting.get("location"), posting["url"],
            posting.get("posted_at"), posting.get("deadline_at"),
            posting.get("is_active", True),
            Json(posting.get("raw_payload", {})),
            posting.get("collected_at"),
            ),
        )

    return cur.fetchone()[0]

def link_skills(cur, job_id: int, skills: list[str]) -> list[str]:
    """skills를 tech_stacks와 매칭해 job_tech_map에 연결.
    매칭 실패한 스킬명은 리스트로 반환 (5주차 사전 확장 때 참고용)."""
    unmatched: list[str] = []
    for skill in skills:
        cur.execute(
            """
            SELECT tech_id FROM tech_stacks
            WHERE lower(name) = lower(%s) OR lower(%s) = ANY(
                SELECT lower(a) FROM unnest(aliases) AS a
            )
            LIMIT 1
            """,
            (skill, skill),
        )
        row = cur.fetchone()
        if row is None:
            unmatched.append(skill)
            continue
        cur.execute(
            """
            INSERT INTO job_tech_map (job_id, tech_id, source_field)
            VALUES (%s, %s, 'skills')
            ON CONFLICT (job_id, tech_id) DO NOTHING
            """,
            (job_id, row[0]),
        )
    return unmatched


def save_posting(conn, posting: dict[str, Any]) -> list[str]:
    with conn.cursor() as cur:
        company_id = upsert_company(cur, posting)
        job_id = upsert_job_posting(cur, posting, company_id)
        unmatched = link_skills(cur, job_id, posting.get("skills", []))
    conn.commit()
    return unmatched