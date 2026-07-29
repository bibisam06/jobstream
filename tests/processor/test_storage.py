from __future__ import annotations

from unittest.mock import MagicMock, call

from processor import storage


def test_upsert_company_returns_none_when_name_missing():
    cur = MagicMock()

    result = storage.upsert_company(cur, {"company_name_normalized": "toss"})

    assert result is None
    cur.execute.assert_not_called()


def test_upsert_company_returns_none_when_normalized_name_missing():
    cur = MagicMock()

    result = storage.upsert_company(cur, {"company_name": "Toss"})

    assert result is None
    cur.execute.assert_not_called()


def test_upsert_company_inserts_and_returns_company_id():
    cur = MagicMock()
    cur.fetchone.return_value = (42,)
    posting = {
        "company_name": "Toss",
        "company_name_normalized": "toss",
        "company_size": "startup",
        "industry": "fintech",
    }

    result = storage.upsert_company(cur, posting)

    assert result == 42
    cur.execute.assert_called_once()
    params = cur.execute.call_args[0][1]
    assert params == ("Toss", "toss", "startup", "fintech")


def test_upsert_job_posting_returns_job_id():
    cur = MagicMock()
    cur.fetchone.return_value = (7,)
    posting = {
        "source": "wanted",
        "source_job_id": "123",
        "title": "Backend Engineer",
        "url": "https://wanted.co.kr/123",
    }

    result = storage.upsert_job_posting(cur, posting, company_id=42)

    assert result == 7
    cur.execute.assert_called_once()
    params = cur.execute.call_args[0][1]
    assert params[0] == "wanted"
    assert params[1] == "123"
    assert params[2] == 42
    assert params[3] == "Backend Engineer"


def test_link_skills_returns_unmatched_and_inserts_matched():
    cur = MagicMock()
    cur.fetchone.side_effect = [(5,), None]

    unmatched = storage.link_skills(cur, job_id=1, skills=["Python", "Cobol"])

    assert unmatched == ["Cobol"]
    assert cur.execute.call_count == 3
    insert_call = cur.execute.call_args_list[1]
    assert insert_call == call(insert_call.args[0], (1, 5))


def test_link_skills_with_no_skills_does_nothing():
    cur = MagicMock()

    unmatched = storage.link_skills(cur, job_id=1, skills=[])

    assert unmatched == []
    cur.execute.assert_not_called()


def test_save_posting_orchestrates_upserts_and_commits(monkeypatch):
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur
    conn.cursor.return_value.__exit__.return_value = False

    monkeypatch.setattr(storage, "upsert_company", MagicMock(return_value=42))
    monkeypatch.setattr(storage, "upsert_job_posting", MagicMock(return_value=7))
    monkeypatch.setattr(storage, "link_skills", MagicMock(return_value=["unmatched-skill"]))

    posting = {"skills": ["Python", "unmatched-skill"]}
    unmatched = storage.save_posting(conn, posting)

    storage.upsert_company.assert_called_once_with(cur, posting)
    storage.upsert_job_posting.assert_called_once_with(cur, posting, 42)
    storage.link_skills.assert_called_once_with(cur, 7, ["Python", "unmatched-skill"])
    conn.commit.assert_called_once()
    assert unmatched == ["unmatched-skill"]


def test_save_posting_defaults_skills_to_empty_list(monkeypatch):
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__.return_value = cur

    monkeypatch.setattr(storage, "upsert_company", MagicMock(return_value=None))
    monkeypatch.setattr(storage, "upsert_job_posting", MagicMock(return_value=1))
    monkeypatch.setattr(storage, "link_skills", MagicMock(return_value=[]))

    storage.save_posting(conn, {})

    storage.link_skills.assert_called_once_with(cur, 1, [])
