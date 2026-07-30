from __future__ import annotations

from urllib.parse import parse_qs, urlparse
import logging
import pytest
logger = logging.getLogger(__name__)

from collector.sources.saramin.crawler import SaraminCrawler

import fakeredis
from unittest.mock import AsyncMock, MagicMock

def crawler() -> SaraminCrawler:
    return SaraminCrawler()


def test_build_search_url_encodes_keyword_and_page():
    url = crawler().build_search_url("백엔드", 2)

    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    assert url.startswith("https://www.saramin.co.kr/zf_user/search/recruit?")
    assert query["searchword"] == ["백엔드"]
    assert query["recruitPage"] == ["2"]


def test_source_job_id_prefers_rec_idx_query_param():
    url = "https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=12345&rec_seq=1"
    assert crawler()._source_job_id(url) == "12345"


def test_source_job_id_falls_back_to_rec_seq_when_rec_idx_missing():
    url = "https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_seq=999"
    assert crawler()._source_job_id(url) == "999"


def test_source_job_id_falls_back_to_path_when_no_known_params():
    url = "https://www.saramin.co.kr/zf_user/jobs/view/12345"
    assert crawler()._source_job_id(url) == "12345"


def test_clean_collapses_whitespace_and_newlines():
    assert crawler()._clean("  백엔드  \n 개발자  ") == "백엔드 개발자"


def test_clean_handles_none():
    assert crawler()._clean(None) == ""


def test_normalize_company_name_removes_spaces_and_lowercases():
    assert crawler()._normalize_company_name("Toss Bank") == "tossbank"


def test_normalize_company_name_returns_none_for_empty_input():
    assert crawler()._normalize_company_name(None) is None
    assert crawler()._normalize_company_name("   ") is None


def test_parse_experience_min_returns_zero_for_entry_level():
    assert crawler()._parse_experience_min("신입") == 0


def test_parse_experience_min_extracts_years():
    assert crawler()._parse_experience_min("경력 3년") == 3


def test_parse_experience_min_returns_none_when_no_match():
    assert crawler()._parse_experience_min("경력무관") is None


def test_parse_experience_min_returns_none_for_empty_input():
    assert crawler()._parse_experience_min(None) is None


def test_pick_returns_cleaned_value_at_index():
    values = ["  서울  ", "", "3년"]
    assert crawler()._pick(values, 0) == "서울"
    assert crawler()._pick(values, 1) == "3년"


def test_pick_returns_none_when_index_out_of_range():
    assert crawler()._pick(["서울"], 5) is None


# test -> dedup 제거 로직 테스트
def test_dedup_removes_duplicates(monkeypatch):
    fake = fakeredis.FakeStrictRedis()
    monkeypatch.setattr("collector.sources.common.dedup.r", fake)

    from collector.sources.common.dedup import is_duplicate

    url = "https://example.com/job/1"

    assert is_duplicate("saramin", url) is False
    assert is_duplicate("wanted", url) is False


@pytest.mark.asyncio
async def test_crawl_page_logs_warning_on_duplicate(mocker, caplog):
    crawler = SaraminCrawler()

    fake_posting = MagicMock()
    fake_posting.url = "https://saramin.co.kr/job/12345"

    mocker.patch.object(crawler, "_parse_card", AsyncMock(return_value=fake_posting))
    mocker.patch.object(crawler, "scroll_to_bottom", AsyncMock())

    # is_duplicate를 True로 강제 → 무조건 중복 처리 경로 타게 함
    mocker.patch(
        "collector.sources.saramin.crawler.is_duplicate",
        return_value=True,
    )

    fake_card = MagicMock()
    fake_page = MagicMock()
    fake_page.goto = AsyncMock()
    fake_page.wait_for_load_state = AsyncMock()
    fake_page.locator.return_value.all = AsyncMock(return_value=[fake_card])

    caplog.set_level(logging.WARNING)

    result = await crawler.crawl_page(fake_page, keyword="백엔드", page_no=1)

    assert result == []  # 중복이라 postings에 안 들어감
    assert "중복 공고 차단" in caplog.text
    assert fake_posting.url in caplog.text