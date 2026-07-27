# processor/consumer.py
from __future__ import annotations

import asyncio
import json
import logging

from aiokafka import AIOKafkaConsumer

from common.kafka_config import KAFKA_BOOTSTRAP_SERVERS, Topics
from common.schemas import JobPosting
from processor.storage import get_connection, save_posting
from processor.dlq_producer import DlqProducer

logger = logging.getLogger(__name__)


class JobPostingConsumer:
    def __init__(
        self,
        bootstrap_servers: str = KAFKA_BOOTSTRAP_SERVERS,
        group_id: str = "jobstream-processing-worker",
    ):
        self._bootstrap_servers = bootstrap_servers
        self._group_id = group_id
        self._consumer: AIOKafkaConsumer | None = None
        self._dlq_producer = DlqProducer()
        self._conn = None  # DB 커넥션 (동기)

    async def start(self):
        self._consumer = AIOKafkaConsumer(
            Topics.CRAWL_RAW,
            bootstrap_servers=self._bootstrap_servers,
            group_id=self._group_id,
            value_deserializer=lambda v: v.decode("utf-8"),
            key_deserializer=lambda k: k.decode("utf-8") if k else None,
            auto_offset_reset="earliest",
            enable_auto_commit=False,
        )
        await self._consumer.start()
        await self._dlq_producer.start()

        # DB 커넥션도 블로킹 I/O라서 스레드에서 생성
        self._conn = await asyncio.to_thread(get_connection)
        logger.info("Kafka consumer 시작됨")

    async def stop(self):
        if self._consumer:
            await self._consumer.stop()
        await self._dlq_producer.stop()
        if self._conn:
            await asyncio.to_thread(self._conn.close)
        logger.info("Kafka consumer 종료됨")

    def _parse(self, raw_value: str) -> dict:
        """JSON → dict. JobPosting(**data)로 한 번 걸러서 스키마 검증만 하고,
        실제 저장은 dict 그대로 넘김 (save_posting이 dict를 받으므로)."""
        data = json.loads(raw_value)      # JSONDecodeError 가능
        JobPosting(**data)                # TypeError 가능 (필드 불일치) — 검증 목적으로만 생성
        return data

    async def run(self):
        assert self._consumer is not None, "start()를 먼저 호출해야 합니다"

        async for message in self._consumer:
            key = message.key
            raw_value = message.value

            try:
                posting_dict = self._parse(raw_value)
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"파싱 실패, DLQ로 전송: {key} - {e}")
                await self._dlq_producer.send(
                    original_topic=message.topic,
                    original_key=key or "",
                    original_payload=raw_value,
                    error_type=type(e).__name__,
                    error_detail=str(e),
                )
                await self._consumer.commit()
                continue

            try:
                # ⭐ 동기 함수라서 to_thread로 감싸서 이벤트 루프 안 막게 함
                unmatched = await asyncio.to_thread(save_posting, self._conn, posting_dict)
                if unmatched:
                    logger.warning(f"매칭 안 된 기술스택: {unmatched}")
                await self._consumer.commit()
            except Exception as e:
                logger.error(f"DB 저장 실패, DLQ로 전송: {key} - {e}")
                await self._dlq_producer.send(
                    original_topic=message.topic,
                    original_key=key or "",
                    original_payload=raw_value,
                    error_type=type(e).__name__,
                    error_detail=str(e),
                )
                await self._consumer.commit()


async def main():
    consumer = JobPostingConsumer()
    await consumer.start()
    try:
        await consumer.run()
    finally:
        await consumer.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())