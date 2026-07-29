from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from collector.sources.wanted.crawler import WantedCrawler


def crawler() -> WantedCrawler:
    return WantedCrawler()


def test_build_search_url_uses_defaults_when_no_args_given():
    url = crawler().build_search_url()

    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    assert parsed.path == "/wdlist/518"
    assert query["locations"] == ["all"]
    assert query["country"] == ["kr"]
    assert query["job_sort"] == ["job.latest_order"]
    assert "selected" not in query
    assert "years" not in query


def test_build_search_url_repeats_selected_and_locations_params():
    url = crawler().build_search_url(
        job_category_ids=[660, 872],
        locations=["서울", "경기"],
        years_range=(0, 3),
    )

    query = parse_qs(urlparse(url).query)
    assert query["selected"] == ["660", "872"]
    assert query["locations"] == ["서울", "경기"]
    assert query["years"] == ["0", "3"]


def test_split_location_with_three_parts():
    location, career, extra = crawler()._split_location("서울 구로구 · 경력 1-3년 · 계약직")
    assert location == "서울 구로구"
    assert career == "경력 1-3년"
    assert extra == "계약직"


def test_split_location_with_two_parts():
    location, career, extra = crawler()._split_location("서울 강남구 · 경력 3-7년")
    assert location == "서울 강남구"
    assert career == "경력 3-7년"
    assert extra is None


def test_split_location_with_no_separator():
    location, career, extra = crawler()._split_location("서울")
    assert location == "서울"
    assert career is None
    assert extra is None


def test_split_location_returns_all_none_for_empty_text():
    assert crawler()._split_location(None) == (None, None, None)
    assert crawler()._split_location("") == (None, None, None)


def test_clean_collapses_whitespace():
    assert crawler()._clean("  서울   강남구  ") == "서울 강남구"


def test_normalize_company_name_removes_spaces_and_lowercases():
    assert crawler()._normalize_company_name("Wanted Lab") == "wantedlab"


def test_normalize_company_name_returns_none_for_empty_input():
    assert crawler()._normalize_company_name(None) is None


def test_parse_experience_min_and_max_for_range():
    c = crawler()
    assert c._parse_experience_min("경력 3-7년") == 3
    assert c._parse_experience_max("경력 3-7년") == 7


def test_parse_experience_min_for_single_year_without_max():
    c = crawler()
    assert c._parse_experience_min("경력 3년") == 3
    assert c._parse_experience_max("경력 3년") is None


def test_parse_experience_min_returns_zero_for_entry_level():
    c = crawler()
    assert c._parse_experience_min("신입") == 0
    assert c._parse_experience_max("신입") is None


def test_parse_experience_min_and_max_return_none_for_empty_input():
    c = crawler()
    assert c._parse_experience_min(None) is None
    assert c._parse_experience_max(None) is None
