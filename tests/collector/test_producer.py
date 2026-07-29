from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from collector.producer import JobPostingProducer
from common.schemas import JobPosting
from common.kafka_config import Topics

from collector.sources.common.base import CrawlRequest
from collector.producer import _crawl_and_produce

import collector.producer as producer_module
import collector.sources.wanted.crawler as wanted_crawler_module
import collector.sources.saramin.crawler as saramin_crawler_module


def test_validate_missing_source_returns_error():
    producer = JobPostingProducer()
    posting = JobPosting(source="", source_job_id="1", title="t", company_name="c", url="http://x")

    result = producer._validate(posting)
    assert result is not None


def test_validate_missing_title_returns_error():
    producer = JobPostingProducer()
    posting = JobPosting(source="wanted", source_job_id="1", title="", company_name="c", url="http://x")

    result = producer._validate(posting)
    assert result is not None


def test_validate_missing_company_name_returns_error():
    producer = JobPostingProducer()
    posting = JobPosting(source="wanted", source_job_id="1", title="t", company_name="", url="http://x")

    result = producer._validate(posting)
    assert result is not None


def test_validate_returns_none_when_all_fields_present():
    producer = JobPostingProducer()
    posting = JobPosting(source="wanted", source_job_id="1", title="t", company_name="c", url="http://x")

    result = producer._validate(posting)
    assert result is None


async def test_send_raises_when_producer_not_started():
    producer = JobPostingProducer()
    posting = JobPosting(source="wanted", source_job_id="1", title="t", company_name="c", url="http://x")
    with pytest.raises(RuntimeError):
        await producer.send(posting)


async def test_send_skips_publish_when_validation_fails():
    producer = JobPostingProducer()
    producer._producer = AsyncMock()
    posting = JobPosting(source="", source_job_id="1", title="t", company_name="c", url="http://x")

    await producer.send(posting)

    producer._producer.send_and_wait.assert_not_called()


async def test_send_publishes_valid_posting_with_correct_key_and_topic():
    producer = JobPostingProducer()
    producer._producer = AsyncMock()
    posting = JobPosting(source="wanted", source_job_id="1", title="t", company_name="c", url="http://x")

    await producer.send(posting)

    producer._producer.send_and_wait.assert_called_once()
    _, kwargs = producer._producer.send_and_wait.call_args
    assert kwargs["topic"] == Topics.CRAWL_RAW
    assert kwargs["key"] == "wanted:1"
    assert '"source_job_id": "1"' in kwargs["value"]

'''
_crawl_and_produce(crawler, request, producer)

mock crawler (crawl()이 posting 2~3개 리스트 반환)와 mock producer 넣고,
posting 개수만큼 producer.send()가 호출되는지, 반환값(count)이 posting 개수와 같은지
'''
class FakeCrawler:
    source_name = "fake"

    async def crawl(self, request):
        return [
            JobPosting(source="wanted", source_job_id=str(i), title="t", company_name="c", url="http://x")
            for i in range(3)
        ]

class FakeProducer:
    def __init__(self):
        self.sent = []

    async def send(self, posting):
        self.sent.append(posting)

async def test_crawl_and_produce():
    crawler = FakeCrawler()
    producer = FakeProducer()
    request = CrawlRequest(keyword="백엔드")

    #crawler.crawl(request)
    count = await _crawl_and_produce(crawler, request, producer)

    assert count == 3
    assert len(producer.sent) == 3

'''
run_all_crawls_and_produce(keyword, pages)

이게 제일 중요: wanted/saramin crawler를 각각 mock으로 바꿔치기(monkeypatch)해서
둘 다 성공하면 정상 종료
하나만 예외를 던지면 (crawl()이 Exception raise) → 나머지 하나는 정상 처리되고 전체는 에러 없이 끝나야 함
둘 다 예외를 던지면 → RuntimeError 발생해야 함
'''
class FakeSuccessCrawler:
    source_name = "fake"

    async def crawl(self, request):
        return [
            JobPosting(source="wanted", source_job_id="1", title="t", company_name="c", url="http://x")
        ]

class FakeFailingCrawler:
    source_name = "fake-fail"

    async def crawl(self, request):
        raise RuntimeError("crawl failed")


class FakeNoOpProducer:
    async def start(self):
        pass

    async def stop(self):
        pass

    async def send(self, posting):
        pass

async def test_run_all_crawls_raises_when_all_sources_fail(monkeypatch):
    monkeypatch.setattr(wanted_crawler_module, "WantedCrawler", FakeFailingCrawler)
    monkeypatch.setattr(saramin_crawler_module, "SaraminCrawler", FakeFailingCrawler)
    monkeypatch.setattr(producer_module, "JobPostingProducer", FakeNoOpProducer)

    with pytest.raises(RuntimeError):
        await producer_module.run_all_crawls_and_produce(keyword="백엔드", pages=1)


async def test_run_all_crawls_completes_when_both_sources_succeed(monkeypatch):
    monkeypatch.setattr(wanted_crawler_module, "WantedCrawler", FakeSuccessCrawler)
    monkeypatch.setattr(saramin_crawler_module, "SaraminCrawler", FakeSuccessCrawler)
    monkeypatch.setattr(producer_module, "JobPostingProducer", FakeNoOpProducer)

    await producer_module.run_all_crawls_and_produce(keyword="백엔드", pages=1)


async def test_run_all_crawls_continues_when_one_source_fails(monkeypatch):
    monkeypatch.setattr(wanted_crawler_module, "WantedCrawler", FakeFailingCrawler)
    monkeypatch.setattr(saramin_crawler_module, "SaraminCrawler", FakeSuccessCrawler)
    monkeypatch.setattr(producer_module, "JobPostingProducer", FakeNoOpProducer)

    await producer_module.run_all_crawls_and_produce(keyword="백엔드", pages=1)