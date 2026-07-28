from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterable

from common.config import CollectorSettings
from common.logger import get_logger
from common.schemas import JobPosting


@dataclass(frozen=True, slots=True)
class CrawlRequest:
    keyword: str
    pages: int = 1
    headless: bool = True


class PlaywrightCrawler(ABC):
    source_name: str

    def __init__(self, settings: CollectorSettings | None = None) -> None:
        self.settings = settings or CollectorSettings()
        self.logger = get_logger(self.__class__.__name__)

    async def crawl(self, request: CrawlRequest) -> list[JobPosting]:
        from playwright.async_api import async_playwright

        postings: list[JobPosting] = []
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=request.headless)
            context = await browser.new_context(
                user_agent=self.settings.user_agent,
                locale="ko-KR",
                timezone_id="Asia/Seoul",
            )
            page = await context.new_page()
            page.set_default_timeout(self.settings.request_timeout_ms)
            page.set_default_navigation_timeout(self.settings.navigation_timeout_ms)

            try:
                for page_no in range(1, request.pages + 1):
                    postings.extend(await self._crawl_page_with_retry(page, request.keyword, page_no))
            finally:
                await context.close()
                await browser.close()

        return self._dedupe(postings)

    async def _crawl_page_with_retry(self, page, keyword: str, page_no: int) -> list[JobPosting]:
        last_error: Exception | None = None
        for attempt in range(1, self.settings.max_retries + 1):
            try:
                self.logger.info("crawl %s keyword=%s page=%s attempt=%s", self.source_name, keyword, page_no, attempt)
                return await self.crawl_page(page, keyword, page_no)
            except Exception as exc:  # Playwright raises several transient subclasses.
                last_error = exc
                wait_seconds = min(2**attempt, 10)
                self.logger.warning("crawl failed: %s; retrying in %ss", exc, wait_seconds)
                await asyncio.sleep(wait_seconds)

        raise RuntimeError(f"{self.source_name} page {page_no} failed after retries") from last_error

    async def scroll_to_bottom(self, page, max_rounds: int = 8) -> None:
        previous_height = 0
        for _ in range(max_rounds):
            current_height = await page.evaluate("document.body.scrollHeight")
            if current_height == previous_height:
                return
            previous_height = current_height
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(self.settings.scroll_pause_ms)

    @abstractmethod
    async def crawl_page(self, page, keyword: str, page_no: int) -> list[JobPosting]:
        raise NotImplementedError

    def _dedupe(self, postings: Iterable[JobPosting]) -> list[JobPosting]:
        seen: set[tuple[str, str]] = set()
        unique: list[JobPosting] = []
        for posting in postings:
            key = (posting.source, posting.source_job_id)
            if key in seen:
                continue
            seen.add(key)
            unique.append(posting)
        return unique
