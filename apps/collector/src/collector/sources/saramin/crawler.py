from __future__ import annotations

import re
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

from common.schemas import JobPosting

from ..common.base import PlaywrightCrawler


class SaraminCrawler(PlaywrightCrawler):
    source_name = "saramin"
    base_url = "https://www.saramin.co.kr"

    def build_search_url(self, keyword: str, page_no: int) -> str:
        query = urlencode({"searchword": keyword, "recruitPage": page_no})
        return f"{self.base_url}/zf_user/search/recruit?{query}"

    async def crawl_page(self, page, keyword: str, page_no: int) -> list[JobPosting]:
        await page.goto(self.build_search_url(keyword, page_no), wait_until="domcontentloaded")
        await page.wait_for_load_state("networkidle")
        await self.scroll_to_bottom(page)

        cards = await page.locator(".item_recruit").all()
        postings: list[JobPosting] = []

        for card in cards:
            posting = await self._parse_card(card)
            if posting is not None:
                postings.append(posting)

        return postings

    async def _parse_card(self, card) -> JobPosting | None:
        title_link = card.locator(".job_tit a").first
        if await title_link.count() == 0:
            return None

        title = self._clean(await title_link.inner_text())
        href = await title_link.get_attribute("href")
        if not title or not href:
            return None

        url = urljoin(self.base_url, href)
        source_job_id = self._source_job_id(url)

        company = await self._text_or_none(card, ".corp_name a")
        conditions = await card.locator(".job_condition span").all_inner_texts()
        sectors = await card.locator(".job_sector a, .job_sector span").all_inner_texts()
        deadlines = await card.locator(".job_date .date, .job_date span").all_inner_texts()

        return JobPosting(
            source=self.source_name,
            source_job_id=source_job_id,
            title=title,
            company_name=company or "",
            company_name_normalized=self._normalize_company_name(company),
            url=url,
            location=self._pick(conditions, 0),
            experience_min=self._parse_experience_min(self._pick(conditions, 1)),
            salary_text=None,
            skills=[self._clean(item) for item in sectors if self._clean(item)],
            raw_payload={
                "conditions": [self._clean(item) for item in conditions],
                "sectors": [self._clean(item) for item in sectors],
                "deadline_text": [self._clean(item) for item in deadlines],
                "career_text": self._pick(conditions, 1),
                "education_text": self._pick(conditions, 2),
                "employment_type_text": self._pick(conditions, 3),
            },
        )

    async def _text_or_none(self, locator, selector: str) -> str | None:
        target = locator.locator(selector).first
        if await target.count() == 0:
            return None
        return self._clean(await target.inner_text())

    def _source_job_id(self, url: str) -> str:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        for key in ("rec_idx", "rec_seq", "idx"):
            if params.get(key):
                return params[key][0]
        return parsed.path.rstrip("/").split("/")[-1] or url

    def _pick(self, values: list[str], index: int) -> str | None:
        cleaned = [self._clean(value) for value in values if self._clean(value)]
        return cleaned[index] if len(cleaned) > index else None

    def _clean(self, text: str | None) -> str:
        return " ".join((text or "").split())

    def _normalize_company_name(self, name: str | None) -> str | None:
        cleaned = self._clean(name)
        return re.sub(r"\s+", "", cleaned).lower() if cleaned else None

    def _parse_experience_min(self, career_text: str | None) -> int | None:
        career_text = self._clean(career_text)
        if not career_text:
            return None
        if "신입" in career_text:
            return 0
        match = re.search(r"(\d+)\s*년", career_text)
        return int(match.group(1)) if match else None
