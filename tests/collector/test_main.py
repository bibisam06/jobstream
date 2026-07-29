from __future__ import annotations

import json
import pytest

from collector.main import build_parser, run
from collector.sources.common.base import CrawlRequest
from common.schemas import JobPosting

def test_build_parser():
    parser = build_parser()
    args = parser.parse_args(["--keyword", "백엔드"])
    assert args.source == "saramin"


def test_build_parser_source_choices():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--keyword", "백엔드", "--source", "invalid"])


class FakeCrawler:
    async def crawl(self, request: CrawlRequest) -> list[JobPosting]:
        return [JobPosting(source="saramin", source_job_id="1", title="t",
                            company_name="c", url="http://x")]


async def test_run_writes_output_file(tmp_path, monkeypatch):
    import collector.main as main_module
    monkeypatch.setattr(main_module, "CRAWLERS", {"saramin": FakeCrawler})

    output_path = tmp_path / "out.jsonl"
    parser = build_parser()
    args = parser.parse_args(["--keyword", "백엔드", "--output", str(output_path)])

    result = await run(args)

    assert result == 0
    lines = output_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["source_job_id"] == "1"


async def test_run_prints_to_stdout_when_no_output(monkeypatch, capsys):
    import collector.main as main_module
    monkeypatch.setattr(main_module, "CRAWLERS", {"saramin": FakeCrawler})

    parser = build_parser()
    args = parser.parse_args(["--keyword", "백엔드"])

    result = await run(args)

    assert result == 0
    out = capsys.readouterr().out
    assert json.loads(out.strip())["source_job_id"] == "1"

