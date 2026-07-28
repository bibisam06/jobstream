# crawler/producer.py
from __future__ import annotations

import asyncio
import hashlib
import json
import logging

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError

from common.kafka_config import KAFKA_BOOTSTRAP_SERVERS, Topics
from common.schemas import JobPosting

logger = logging.getLogger(__name__)


class JobPostingProducer:
    def __init__(self, bootstrap_servers: str = KAFKA_BOOTSTRAP_SERVERS):
        self._producer: AIOKafkaProducer | None = None
        self._bootstrap_servers = bootstrap_servers

    async def start(self):
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._bootstrap_servers,
            value_serializer=lambda v: v.encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8"),
            acks="all",
            enable_idempotence=True,
            linger_ms=50,
        )
        await self._producer.start()
        logger.info("Kafka producer 시작됨")

    async def stop(self):
        if self._producer:
            await self._producer.stop()
            logger.info("Kafka producer 종료됨")

    def _validate(self, posting: JobPosting) -> str | None:
        """dataclass엔 자동 검증이 없어서 최소한의 방어 로직을 직접 둠.
        문제 있으면 에러 메시지 반환, 없으면 None."""
        if not posting.source or not posting.source_job_id:
            return "source 또는 source_job_id가 비어있음"
        if not posting.title:
            return "title이 비어있음"
        if not posting.company_name:
            return "company_name이 비어있음"
        return None

    async def send(self, posting: JobPosting) -> None:
        if not self._producer:
            raise RuntimeError("producer.start()를 먼저 호출해야 합니다")

        error = self._validate(posting)
        if error:
            logger.warning(f"검증 실패, 발행 스킵: {posting.source}:{posting.source_job_id} - {error}")
            return

        key = f"{posting.source}:{posting.source_job_id}"
        payload = json.dumps(posting.to_dict(), ensure_ascii=False)

        try:
            await self._producer.send_and_wait(
                topic=Topics.CRAWL_RAW,
                key=key,
                value=payload,
            )
            logger.debug(f"발행 성공: {key}")
        except KafkaError as e:
            logger.error(f"발행 실패: {key} - {e}")


async def run_wanted_crawl_and_produce():
    from collector.sources.wanted.crawler import WantedCrawler
    from collector.sources.common.base import CrawlRequest

    producer = JobPostingProducer()
    await producer.start()

    crawler = WantedCrawler()
    count = 0

    try:
        # crawl()이 브라우저 실행 + 재시도 + dedupe까지 전부 처리해줌
        postings = await crawler.crawl(
            CrawlRequest(keyword="", pages=1, headless=True)
        )

        for posting in postings:
            await producer.send(posting)
            count += 1
            if count % 50 == 0:
                logger.info(f"{count}건 발행 완료")
    finally:
        await producer.stop()
        logger.info(f"총 {count}건 발행, 크롤링 종료")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_wanted_crawl_and_produce())



