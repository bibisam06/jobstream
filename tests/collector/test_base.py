from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from collector.sources.common.base import PlaywrightCrawler
from common.schemas import JobPosting


class DummyCrawler(PlaywrightCrawler):
    source_name = "dummy"

    def __init__(self, crawl_page_mock=None, **kwargs):
        super().__init__(**kwargs)
        self._crawl_page_mock = crawl_page_mock or AsyncMock()

    async def crawl_page(self, page, keyword, page_no):
        return await self._crawl_page_mock(page, keyword, page_no)


def posting(source_job_id: str) -> JobPosting:
    return JobPosting(
        source="dummy", source_job_id=source_job_id, title="t", company_name="c", url="http://x"
    )


def test_dedupe_removes_duplicate_source_job_id():
    crawler = DummyCrawler()
    postings = [posting("1"), posting("2"), posting("1")]

    result = crawler._dedupe(postings)

    assert [p.source_job_id for p in result] == ["1", "2"]


def test_dedupe_keeps_original_order():
    crawler = DummyCrawler()
    postings = [posting("3"), posting("1"), posting("2")]

    result = crawler._dedupe(postings)

    assert [p.source_job_id for p in result] == ["3", "1", "2"]


async def test_crawl_page_with_retry_raises_after_max_retries(monkeypatch):
    monkeypatch.setattr("asyncio.sleep", AsyncMock())
    crawl_page_mock = AsyncMock(side_effect=RuntimeError("boom"))
    crawler = DummyCrawler(crawl_page_mock=crawl_page_mock)

    with pytest.raises(RuntimeError):
        await crawler._crawl_page_with_retry(page=object(), keyword="백엔드", page_no=1)

    assert crawl_page_mock.call_count == crawler.settings.max_retries


async def test_crawl_page_with_retry_returns_result_after_transient_failure(monkeypatch):
    monkeypatch.setattr("asyncio.sleep", AsyncMock())
    expected = [posting("1")]
    crawl_page_mock = AsyncMock(side_effect=[RuntimeError("boom"), expected])
    crawler = DummyCrawler(crawl_page_mock=crawl_page_mock)

    result = await crawler._crawl_page_with_retry(page=object(), keyword="백엔드", page_no=1)

    assert result == expected
    assert crawl_page_mock.call_count == 2


class FakePage:
    """window.scrollTo(...) 호출과 document.body.scrollHeight 조회를 구분해서
    height 조회일 때만 다음 높이값을 반환한다."""

    def __init__(self, heights):
        self._heights = iter(heights)
        self.height_check_calls = 0
        self.wait_for_timeout_calls = 0

    async def evaluate(self, script):
        if "scrollTo" in script:
            return None
        self.height_check_calls += 1
        return next(self._heights)

    async def wait_for_timeout(self, ms):
        self.wait_for_timeout_calls += 1


async def test_scroll_to_bottom_stops_when_height_unchanged():
    crawler = DummyCrawler()
    page = FakePage([100, 100])

    await crawler.scroll_to_bottom(page)

    assert page.height_check_calls == 2
    assert page.wait_for_timeout_calls == 1


async def test_scroll_to_bottom_stops_after_max_rounds_if_height_keeps_growing():
    crawler = DummyCrawler()
    page = FakePage([100, 200, 300, 400])

    await crawler.scroll_to_bottom(page, max_rounds=3)

    assert page.height_check_calls == 3
    assert page.wait_for_timeout_calls == 3
