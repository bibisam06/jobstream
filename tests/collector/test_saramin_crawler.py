from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from collector.sources.saramin.crawler import SaraminCrawler


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
