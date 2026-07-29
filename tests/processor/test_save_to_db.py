from __future__ import annotations

import sys
from unittest.mock import MagicMock

from processor import save_to_db


def test_main_saves_each_line_and_reports_unmatched_skills(tmp_path, monkeypatch, capsys):
    input_file = tmp_path / "postings.jsonl"
    input_file.write_text(
        '{"title": "A"}\n'
        "\n"  # blank lines are skipped
        '{"title": "B"}\n',
        encoding="utf-8",
    )

    fake_conn = MagicMock()
    monkeypatch.setattr(save_to_db, "get_connection", MagicMock(return_value=fake_conn))
    save_posting_mock = MagicMock(side_effect=[["react"], []])
    monkeypatch.setattr(save_to_db, "save_posting", save_posting_mock)
    monkeypatch.setattr(sys, "argv", ["save_to_db", "--input", str(input_file)])

    save_to_db.main()

    assert save_posting_mock.call_count == 2
    save_posting_mock.assert_any_call(fake_conn, {"title": "A"})
    save_posting_mock.assert_any_call(fake_conn, {"title": "B"})
    fake_conn.close.assert_called_once()

    output = capsys.readouterr().out
    assert "저장 완료: 2건" in output
    assert "react" in output


def test_main_omits_unmatched_summary_when_all_matched(tmp_path, monkeypatch, capsys):
    input_file = tmp_path / "postings.jsonl"
    input_file.write_text('{"title": "A"}\n', encoding="utf-8")

    fake_conn = MagicMock()
    monkeypatch.setattr(save_to_db, "get_connection", MagicMock(return_value=fake_conn))
    monkeypatch.setattr(save_to_db, "save_posting", MagicMock(return_value=[]))
    monkeypatch.setattr(sys, "argv", ["save_to_db", "--input", str(input_file)])

    save_to_db.main()

    output = capsys.readouterr().out
    assert "저장 완료: 1건" in output
    assert "매칭 안 된" not in output
