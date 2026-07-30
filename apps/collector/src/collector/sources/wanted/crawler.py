from __future__ import annotations

import re
from urllib.parse import urlencode, urljoin

import logging
logger = logging.getLogger(__name__)

from common.schemas import JobPosting

from ..common.base import PlaywrightCrawler
from ..common.dedup import is_duplicate


class WantedCrawler(PlaywrightCrawler):
    source_name = "wanted"
    base_url = "https://www.wanted.co.kr"

    # 카테고리 ID (직군 대분류) - 개발자는 518
    DEFAULT_CATEGORY_ID = 518

    def build_search_url(
        self,
        job_category_ids: list[int] | None = None,   # ?selected=660&selected=872 부분
        locations: list[str] | None = None,           # ?locations=all
        years_range: tuple[int, int] | None = None,   # ?years=0&years=3
        sort: str = "job.latest_order",
    ) -> str:
        params: list[tuple[str, str]] = []

        # 반복 키(selected=660&selected=872&selected=895)는
        # (key, value) 튜플을 여러 개 만들어서 리스트에 넣어야 함
        if job_category_ids:
            for cat_id in job_category_ids:
                params.append(("selected", str(cat_id)))

        if locations:
            for loc in locations:
                params.append(("locations", loc))
        else:
            params.append(("locations", "all"))

        if years_range:
            min_years, max_years = years_range
            params.append(("years", str(min_years)))
            params.append(("years", str(max_years)))

        params.append(("country", "kr"))
        params.append(("job_sort", sort))

        query_string = urlencode(params, doseq=False)
        # doseq=False인 이유: 이미 위에서 (key, value) 튜플을 개별로 풀어놨기 때문
        # doseq=True를 쓰려면 대신 {"selected": [660, 872, 895]} 형태의 dict로 넘겨야 함

        path = f"/wdlist/{self.DEFAULT_CATEGORY_ID}"
        return f"{self.base_url}{path}?{query_string}"

    async def crawl_page(self, page, keyword: str, page_no: int) -> list[JobPosting]:
        # 원티드 목록은 검색어가 아니라 카테고리/조건 기반이라 keyword는 사용하지 않음.
        await page.goto(self.build_search_url(), wait_until="domcontentloaded")
        await page.wait_for_selector('a[href^="/wd/"]')
        await page.wait_for_load_state("networkidle")
        await self.scroll_to_bottom(page)

        cards = await page.locator('li:has(a[href^="/wd/"])').all()
        postings: list[JobPosting] = []

        for card in cards:
            posting = await self._parse_card(card)

            if(is_duplicate("wanted", posting.url)):
                logger.warning(f"[원티드] 중복 공고 차단 : {posting.url}")
                continue

            if posting is not None:
                postings.append(posting)
        return postings

    async def _parse_card(self, card) -> JobPosting | None:
        link = card.locator('a[href^="/wd/"]').first
        if await link.count() == 0:
            return None

        href = await link.get_attribute("href")
        if not href:
            return None
        url = urljoin(self.base_url, href)

        # data-position-id/name 등은 북마크 버튼에 실려 있음 (해시된 CSS 클래스보다 안정적)
        bookmark = card.locator("button.bookmarkBtn").first
        if await bookmark.count() == 0:
            return None

        source_job_id = await bookmark.get_attribute("data-position-id")
        title = await bookmark.get_attribute("data-position-name")
        company = await bookmark.get_attribute("data-company-name")
        job_category = await bookmark.get_attribute("data-job-category")
        employment_type = await bookmark.get_attribute("data-position-employment-type")

        if not source_job_id or not title:
            return None

        location_text = await self._text_or_none(
            card, '[class*="CompanyNameWithLocationPeriod__location"]'
        )
        location, career_text, extra_text = self._split_location(location_text)

        return JobPosting(
            source=self.source_name,
            source_job_id=source_job_id,
            title=self._clean(title),
            company_name=company or "",
            company_name_normalized=self._normalize_company_name(company),
            url=url,
            location=location,
            job_category=job_category,
            experience_min=self._parse_experience_min(career_text),
            experience_max=self._parse_experience_max(career_text),
            salary_text=None,
            skills=[],
            raw_payload={
                "location_text": location_text,
                "career_text": career_text,
                "employment_type_text": extra_text,
                "employment_type": employment_type,
            },
        )

    async def _text_or_none(self, locator, selector: str) -> str | None:
        target = locator.locator(selector).first
        if await target.count() == 0:
            return None
        return self._clean(await target.inner_text())

    def _split_location(self, text: str | None) -> tuple[str | None, str | None, str | None]:
        # "서울 강남구 · 경력 3-7년" / "서울 구로구 · 경력 1-3년 · 계약직" 형태
        if not text:
            return None, None, None
        parts = [self._clean(part) for part in text.split("·")]
        location = parts[0] if len(parts) > 0 and parts[0] else None
        career_text = parts[1] if len(parts) > 1 and parts[1] else None
        extra_text = parts[2] if len(parts) > 2 and parts[2] else None
        return location, career_text, extra_text

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
        match = re.search(r"(\d+)\s*[-~]\s*(\d+)\s*년", career_text)
        if match:
            return int(match.group(1))
        match = re.search(r"(\d+)\s*년", career_text)
        return int(match.group(1)) if match else None

    def _parse_experience_max(self, career_text: str | None) -> int | None:
        career_text = self._clean(career_text)
        if not career_text:
            return None
        match = re.search(r"(\d+)\s*[-~]\s*(\d+)\s*년", career_text)
        return int(match.group(2)) if match else None
